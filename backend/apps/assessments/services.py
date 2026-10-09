from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from typing import Any
from django.db import transaction
from django.utils import timezone
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.assessments.models import (
    Attempt, AttemptStatus, Assignment, GradeEntry, GradeSource, QuestionType,
    Quiz, QuizQuestion, Response, Rubric, Submission, SubmissionGrade, SubmissionStatus,
)
from apps.courses.models import Subtopic, SubtopicKind
from apps.programs.models import Class, ClassSubject

class AssessmentError(Exception):
    def __init__(self, message: str, code: str = "assessment_error") -> None:
        self.message = message; self.code = code; super().__init__(message)

def _dec(v) -> Decimal:
    return Decimal("0") if v is None else Decimal(str(v))

def enrollment_for_subject(*, user, subject):
    return (Enrollment.objects.filter(user=user, status=EnrollmentStatus.ACTIVE, class_ref__class_subjects__subject=subject)
            .select_related("class_ref", "cohort").distinct().first())

def require_enrollment(*, user, subject):
    enr = enrollment_for_subject(user=user, subject=subject)
    if not enr:
        raise AssessmentError("Enrollment required to attempt this assessment.", code="not_enrolled")
    return enr

def _ensure_subtopic_kind(subtopic: Subtopic, kind: str) -> None:
    if subtopic.kind == kind: return
    if subtopic.kind == SubtopicKind.SUBTOPIC:
        subtopic.kind = kind; subtopic.save(update_fields=["kind", "updated_at"]); return
    raise AssessmentError(f"Subtopic kind must be '{kind}', got '{subtopic.kind}'.", code="invalid_kind")

@transaction.atomic
def upsert_quiz(*, subtopic_id: str, title: str = "", instructions_json=None, settings=None, questions=None, release_scores: bool = True) -> Quiz:
    try:
        subtopic = Subtopic.objects.select_related("topic__subject").get(id=subtopic_id)
    except Subtopic.DoesNotExist as e:
        raise AssessmentError("Subtopic not found.", code="not_found") from e
    _ensure_subtopic_kind(subtopic, SubtopicKind.QUIZ)
    quiz, _ = Quiz.objects.get_or_create(subtopic=subtopic, defaults={"title": title or subtopic.title, "instructions_json": instructions_json or {}, "settings": settings or {}, "release_scores": release_scores})
    quiz.title = title or quiz.title or subtopic.title
    if instructions_json is not None: quiz.instructions_json = instructions_json
    if settings is not None: quiz.settings = settings
    quiz.release_scores = release_scores
    if questions is not None:
        quiz.questions.all().delete(); total = Decimal("0")
        for i, q in enumerate(questions):
            pts = _dec(q.get("points", 1))
            QuizQuestion.objects.create(quiz=quiz, prompt=q["prompt"], question_type=q.get("question_type", QuestionType.MCQ), choices=q.get("choices") or [], correct_answer=q.get("correct_answer") or {}, order=q.get("order", i), points=pts)
            total += pts
        quiz.points_total = total
    else:
        quiz.points_total = sum((_dec(q.points) for q in quiz.questions.all()), Decimal("0"))
    quiz.save()
    return Quiz.objects.prefetch_related("questions").get(pk=quiz.pk)

def get_quiz(quiz_id: str) -> Quiz:
    try:
        return Quiz.objects.prefetch_related("questions").select_related("subtopic").get(id=quiz_id)
    except Quiz.DoesNotExist as e:
        raise AssessmentError("Quiz not found.", code="not_found") from e

@transaction.atomic
def start_attempt(*, user, quiz_id: str) -> Attempt:
    quiz = get_quiz(quiz_id)
    enrollment = require_enrollment(user=user, subject=quiz.subtopic.topic.subject)
    settings = quiz.settings or {}; max_attempts = int(settings.get("attempts") or 1)
    existing = Attempt.objects.filter(quiz=quiz, user=user).order_by("-number")
    in_progress = existing.filter(status=AttemptStatus.IN_PROGRESS).first()
    if in_progress: return in_progress
    if existing.count() >= max_attempts: raise AssessmentError("No attempts remaining.", code="no_attempts")
    deadline = None
    tls = int(settings.get("time_limit_s") or 0)
    if tls > 0: deadline = timezone.now() + timedelta(seconds=tls)
    return Attempt.objects.create(quiz=quiz, enrollment=enrollment, user=user, number=existing.count()+1, deadline_at=deadline, status=AttemptStatus.IN_PROGRESS, max_score=quiz.points_total)

@transaction.atomic
def save_responses(*, user, attempt_id: str, responses: list[dict]) -> Attempt:
    try:
        attempt = Attempt.objects.select_related("quiz").prefetch_related("quiz__questions").get(id=attempt_id)
    except Attempt.DoesNotExist as e:
        raise AssessmentError("Attempt not found.", code="not_found") from e
    if attempt.user_id != user.id: raise AssessmentError("Forbidden.", code="forbidden")
    if attempt.status != AttemptStatus.IN_PROGRESS: raise AssessmentError("Attempt is not in progress.", code="not_in_progress")
    now = timezone.now()
    if attempt.deadline_at and now > attempt.deadline_at:
        attempt.status = AttemptStatus.EXPIRED; attempt.save(update_fields=["status","updated_at"]); raise AssessmentError("Attempt expired.", code="expired")
    qmap = {str(q.id): q for q in attempt.quiz.questions.all()}
    for row in responses:
        qid = str(row.get("question_id")); question = qmap.get(qid)
        if not question: raise AssessmentError(f"Unknown question {qid}.", code="invalid_question")
        Response.objects.update_or_create(attempt=attempt, question=question, defaults={"answer": row.get("answer") or {}, "autosaved_at": now})
    return attempt

def _score_response(question: QuizQuestion, answer: dict):
    correct = question.correct_answer or {}; qtype = question.question_type; pts = _dec(question.points)
    if qtype == QuestionType.MCQ:
        got = str((answer or {}).get("choice_id","")).strip(); expect = str(correct.get("choice_id","")).strip(); ok = bool(got) and got == expect
        return (pts if ok else Decimal("0"), ok)
    if qtype == QuestionType.TRUE_FALSE:
        got = (answer or {}).get("value"); expect = correct.get("value")
        if isinstance(got, str): got = got.lower() in ("true","1","yes")
        if isinstance(expect, str): expect = expect.lower() in ("true","1","yes")
        ok = got is not None and bool(got) is bool(expect)
        return (pts if ok else Decimal("0"), ok)
    if qtype == QuestionType.SHORT:
        got = str((answer or {}).get("text","")).strip().lower(); expect = str(correct.get("text","")).strip().lower(); ok = bool(expect) and got == expect
        return (pts if ok else Decimal("0"), ok)
    return Decimal("0"), False

@transaction.atomic
def submit_attempt(*, user, attempt_id: str) -> Attempt:
    try:
        attempt = (Attempt.objects.select_related("quiz","enrollment","quiz__subtopic__topic__subject").prefetch_related("quiz__questions","responses").get(id=attempt_id))
    except Attempt.DoesNotExist as e:
        raise AssessmentError("Attempt not found.", code="not_found") from e
    if attempt.user_id != user.id: raise AssessmentError("Forbidden.", code="forbidden")
    if attempt.status not in (AttemptStatus.IN_PROGRESS, AttemptStatus.EXPIRED): raise AssessmentError("Attempt already submitted.", code="already_submitted")
    responses = {str(r.question_id): r for r in attempt.responses.all()}; auto_total = Decimal("0"); max_total = Decimal("0")
    for question in attempt.quiz.questions.all():
        max_total += _dec(question.points); resp = responses.get(str(question.id)); answer = resp.answer if resp else {}
        score, ok = _score_response(question, answer)
        if resp:
            resp.score = score; resp.is_correct = ok; resp.save(update_fields=["score","is_correct","updated_at"])
        else:
            Response.objects.create(attempt=attempt, question=question, answer={}, score=score, is_correct=ok, autosaved_at=timezone.now())
        auto_total += score
    attempt.auto_score = auto_total; attempt.score = auto_total; attempt.max_score = max_total or attempt.quiz.points_total
    attempt.submitted_at = timezone.now(); attempt.status = AttemptStatus.GRADED; attempt.save()
    if attempt.enrollment_id: upsert_grade_entry_from_attempt(attempt)
    return attempt

def upsert_grade_entry_from_attempt(attempt: Attempt):
    if not attempt.enrollment_id: return None
    quiz = attempt.quiz; subject = quiz.subtopic.topic.subject
    entry, _ = GradeEntry.objects.update_or_create(enrollment=attempt.enrollment, item_type="quiz", item_id=quiz.id, defaults={
        "user": attempt.user, "class_ref": attempt.enrollment.class_ref, "subject": subject, "subtopic": quiz.subtopic,
        "title": quiz.title, "score": attempt.score, "max_score": attempt.max_score, "source": GradeSource.AUTO,
        "released": bool(quiz.release_scores), "attempt_id": attempt.id,
    })
    return entry

def review_attempt(*, user, attempt_id: str, is_staff: bool = False) -> dict[str, Any]:
    try:
        attempt = Attempt.objects.select_related("quiz","quiz__subtopic").prefetch_related("quiz__questions","responses__question").get(id=attempt_id)
    except Attempt.DoesNotExist as e:
        raise AssessmentError("Attempt not found.", code="not_found") from e
    if attempt.user_id != user.id and not is_staff: raise AssessmentError("Forbidden.", code="forbidden")
    released = attempt.quiz.release_scores or is_staff
    if attempt.status == AttemptStatus.IN_PROGRESS and not is_staff: raise AssessmentError("Attempt not submitted yet.", code="not_submitted")
    payload = {"id": str(attempt.id), "quiz_id": str(attempt.quiz_id), "status": attempt.status, "number": attempt.number, "submitted_at": attempt.submitted_at, "released": released}
    if released:
        payload["score"] = float(attempt.score) if attempt.score is not None else None
        payload["max_score"] = float(attempt.max_score)
        payload["auto_score"] = float(attempt.auto_score) if attempt.auto_score is not None else None
        resp_map = {str(r.question_id): r for r in attempt.responses.all()}; responses = []
        for q in attempt.quiz.questions.all():
            r = resp_map.get(str(q.id))
            responses.append({"question_id": str(q.id), "prompt": q.prompt, "question_type": q.question_type, "points": float(q.points), "answer": r.answer if r else {}, "score": float(r.score) if r and r.score is not None else None, "is_correct": r.is_correct if r else None, "correct_answer": q.correct_answer if released else None, "choices": q.choices})
        payload["responses"] = responses
    else:
        payload["message"] = "Scores not released yet."
    return payload

@transaction.atomic
def upsert_assignment(*, subtopic_id: str, title: str = "", instructions_json=None, due_at=None, points=100, allow_resubmit: bool = False, max_resubmits: int = 0, rubric=None) -> Assignment:
    try:
        subtopic = Subtopic.objects.select_related("topic__subject").get(id=subtopic_id)
    except Subtopic.DoesNotExist as e:
        raise AssessmentError("Subtopic not found.", code="not_found") from e
    _ensure_subtopic_kind(subtopic, SubtopicKind.ASSIGNMENT)
    assignment, _ = Assignment.objects.get_or_create(subtopic=subtopic, defaults={"title": title or subtopic.title, "instructions_json": instructions_json or {}, "due_at": due_at, "points": _dec(points), "allow_resubmit": allow_resubmit, "max_resubmits": max_resubmits})
    assignment.title = title or assignment.title or subtopic.title
    if instructions_json is not None: assignment.instructions_json = instructions_json
    assignment.due_at = due_at; assignment.points = _dec(points); assignment.allow_resubmit = allow_resubmit; assignment.max_resubmits = max_resubmits
    if rubric is not None:
        criteria = rubric.get("criteria") or []
        if assignment.rubric_id:
            r = assignment.rubric; r.title = rubric.get("title") or r.title or assignment.title; r.criteria = criteria; r.save()
        else:
            r = Rubric.objects.create(title=rubric.get("title") or assignment.title, criteria=criteria); assignment.rubric = r
    assignment.save()
    return Assignment.objects.select_related("rubric","subtopic").get(pk=assignment.pk)

@transaction.atomic
def submit_assignment(*, user, assignment_id: str, text: str = "", link: str = "") -> Submission:
    try:
        assignment = Assignment.objects.select_related("subtopic__topic__subject").get(id=assignment_id)
    except Assignment.DoesNotExist as e:
        raise AssessmentError("Assignment not found.", code="not_found") from e
    enrollment = require_enrollment(user=user, subject=assignment.subtopic.topic.subject)
    latest = Submission.objects.filter(assignment=assignment, user=user).order_by("-version").first()
    if latest and latest.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED):
        if not assignment.allow_resubmit: raise AssessmentError("Already submitted.", code="already_submitted")
        if assignment.max_resubmits and latest.version >= assignment.max_resubmits + 1: raise AssessmentError("Resubmit limit reached.", code="resubmit_limit")
        version = latest.version + 1
    elif latest and latest.status == SubmissionStatus.DRAFT:
        latest.text = text; latest.link = link; latest.submitted_at = timezone.now(); latest.status = SubmissionStatus.SUBMITTED; latest.enrollment = enrollment; latest.save(); return latest
    else:
        version = 1
    if not text and not link: raise AssessmentError("Provide text and/or link.", code="empty_submission")
    return Submission.objects.create(assignment=assignment, enrollment=enrollment, user=user, version=version, text=text, link=link, submitted_at=timezone.now(), status=SubmissionStatus.SUBMITTED)

def grading_queue(*, class_id=None, assignment_id=None):
    qs = (Submission.objects.filter(status=SubmissionStatus.SUBMITTED).select_related("assignment","assignment__subtopic","assignment__rubric","user","enrollment","enrollment__class_ref").order_by("submitted_at"))
    if assignment_id: qs = qs.filter(assignment_id=assignment_id)
    if class_id: qs = qs.filter(enrollment__class_ref_id=class_id).distinct()
    rows = []
    for s in qs[:200]:
        rows.append({"submission_id": str(s.id), "assignment_id": str(s.assignment_id), "assignment_title": s.assignment.title, "subtopic_id": str(s.assignment.subtopic_id), "student_id": str(s.user_id), "student_email": s.user.email, "student_name": f"{s.user.first_name} {s.user.last_name}".strip() or s.user.email, "submitted_at": s.submitted_at, "version": s.version, "text": s.text, "link": s.link, "points": float(s.assignment.points), "rubric": ({"id": str(s.assignment.rubric_id), "title": s.assignment.rubric.title, "criteria": s.assignment.rubric.criteria} if s.assignment.rubric_id else None), "class_id": str(s.enrollment.class_ref_id) if s.enrollment_id else None})
    return rows

@transaction.atomic
def grade_submission(*, grader, submission_id: str, rubric_scores=None, raw_score=None, feedback_json=None, penalty=0) -> SubmissionGrade:
    try:
        submission = Submission.objects.select_related("assignment","assignment__rubric","assignment__subtopic__topic__subject","enrollment").get(id=submission_id)
    except Submission.DoesNotExist as e:
        raise AssessmentError("Submission not found.", code="not_found") from e
    rubric_scores = rubric_scores or {}
    if raw_score is None and rubric_scores and submission.assignment.rubric_id:
        raw = Decimal("0")
        for _cid, row in rubric_scores.items():
            raw += _dec(row.get("points", 0) if isinstance(row, dict) else row)
        raw_score = raw
    elif raw_score is None:
        raise AssessmentError("raw_score or rubric_scores required.", code="missing_score")
    final = max(Decimal("0"), _dec(raw_score) - _dec(penalty)); now = timezone.now()
    grade, _ = SubmissionGrade.objects.update_or_create(submission=submission, defaults={"rubric_scores": rubric_scores, "raw_score": _dec(raw_score), "penalty": _dec(penalty), "final_score": final, "feedback_json": feedback_json or {}, "graded_by": grader, "graded_at": now})
    submission.status = SubmissionStatus.GRADED; submission.save(update_fields=["status","updated_at"]); return grade

@transaction.atomic
def release_grades(*, submission_ids: list[str]):
    now = timezone.now(); results = []
    grades = SubmissionGrade.objects.filter(submission_id__in=submission_ids).select_related("submission","submission__assignment","submission__assignment__subtopic__topic__subject","submission__enrollment","submission__user")
    found = {str(g.submission_id): g for g in grades}
    for sid in submission_ids:
        grade = found.get(str(sid))
        if not grade: results.append({"submission_id": sid, "ok": False, "error": "not_found"}); continue
        grade.released_at = now; grade.save(update_fields=["released_at","updated_at"]); upsert_grade_entry_from_submission(grade, released=True)
        results.append({"submission_id": sid, "ok": True, "final_score": float(grade.final_score), "released_at": now})
    return results

def upsert_grade_entry_from_submission(grade: SubmissionGrade, *, released: bool):
    submission = grade.submission
    if not submission.enrollment_id: return None
    assignment = submission.assignment; subject = assignment.subtopic.topic.subject
    entry, _ = GradeEntry.objects.update_or_create(enrollment=submission.enrollment, item_type="assignment", item_id=assignment.id, defaults={
        "user": submission.user, "class_ref": submission.enrollment.class_ref, "subject": subject, "subtopic": assignment.subtopic,
        "title": assignment.title, "score": grade.final_score, "max_score": assignment.points, "source": GradeSource.MANUAL,
        "released": released, "submission_id": submission.id,
    })
    return entry

def class_gradebook(*, class_id: str, subject_id=None):
    try: klass = Class.objects.get(id=class_id)
    except Class.DoesNotExist as e: raise AssessmentError("Class not found.", code="not_found") from e
    entries = GradeEntry.objects.filter(class_ref=klass).select_related("user","subject","subtopic","enrollment")
    if subject_id: entries = entries.filter(subject_id=subject_id)
    columns = {}; students = {}
    for e in entries:
        key = f"{e.item_type}:{e.item_id}"
        columns.setdefault(key, {"item_type": e.item_type, "item_id": str(e.item_id), "title": e.title, "max_score": float(e.max_score), "subject_id": str(e.subject_id) if e.subject_id else None})
        uid = str(e.user_id)
        students.setdefault(uid, {"user_id": uid, "email": e.user.email, "name": f"{e.user.first_name} {e.user.last_name}".strip() or e.user.email, "enrollment_id": str(e.enrollment_id), "grades": {}})
        students[uid]["grades"][key] = {"score": float(e.score) if e.score is not None else None, "max_score": float(e.max_score), "released": e.released, "source": e.source}
    for enr in Enrollment.objects.filter(class_ref=klass, status=EnrollmentStatus.ACTIVE).select_related("user"):
        uid = str(enr.user_id)
        students.setdefault(uid, {"user_id": uid, "email": enr.user.email, "name": f"{enr.user.first_name} {enr.user.last_name}".strip() or enr.user.email, "enrollment_id": str(enr.id), "grades": {}})
    subject_ids = list(ClassSubject.objects.filter(class_ref=klass).values_list("subject_id", flat=True))
    return {"class_id": str(klass.id), "class_name": klass.name, "subject_ids": [str(s) for s in subject_ids], "columns": list(columns.values()), "students": list(students.values())}

def student_released_grades(*, user, class_id=None):
    qs = GradeEntry.objects.filter(user=user, released=True).select_related("subject","subtopic")
    if class_id: qs = qs.filter(class_ref_id=class_id)
    return [{"id": str(e.id), "item_type": e.item_type, "item_id": str(e.item_id), "title": e.title, "score": float(e.score) if e.score is not None else None, "max_score": float(e.max_score), "subject_id": str(e.subject_id) if e.subject_id else None, "subtopic_id": str(e.subtopic_id) if e.subtopic_id else None} for e in qs]

def get_submission_for_student(*, user, submission_id: str):
    try:
        submission = Submission.objects.select_related("assignment","grade","assignment__rubric").get(id=submission_id, user=user)
    except Submission.DoesNotExist as e:
        raise AssessmentError("Submission not found.", code="not_found") from e
    payload = {"id": str(submission.id), "assignment_id": str(submission.assignment_id), "status": submission.status, "text": submission.text, "link": submission.link, "submitted_at": submission.submitted_at, "version": submission.version}
    grade = getattr(submission, "grade", None)
    if grade and grade.released_at:
        payload["grade"] = {"final_score": float(grade.final_score), "raw_score": float(grade.raw_score), "rubric_scores": grade.rubric_scores, "feedback_json": grade.feedback_json, "released_at": grade.released_at, "max_score": float(submission.assignment.points)}
    return payload
