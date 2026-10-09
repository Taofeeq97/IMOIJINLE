from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class QuestionType(models.TextChoices):
    MCQ = "mcq", "Multiple choice"
    TRUE_FALSE = "true_false", "True / False"
    SHORT = "short", "Short answer"


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    SUBMITTED = "submitted", "Submitted"
    GRADED = "graded", "Graded"
    EXPIRED = "expired", "Expired"


class SubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    GRADED = "graded", "Graded"
    RETURNED = "returned", "Returned"
    RESUBMIT_REQUESTED = "resubmit_requested", "Resubmit requested"


class GradeSource(models.TextChoices):
    AUTO = "auto", "Auto"
    MANUAL = "manual", "Manual"
    OVERRIDE = "override", "Override"


class Quiz(BaseModel):
    subtopic = models.OneToOneField(
        "courses.Subtopic", on_delete=models.CASCADE, related_name="quiz"
    )
    title = models.CharField(max_length=200)
    instructions_json = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    points_total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    release_scores = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class QuizQuestion(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    question_type = models.CharField(
        max_length=16, choices=QuestionType.choices, default=QuestionType.MCQ
    )
    choices = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)
    points = models.DecimalField(max_digits=8, decimal_places=2, default=1)

    class Meta:
        ordering = ["order", "created_at"]


class Attempt(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    enrollment = models.ForeignKey(
        "admissions.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quiz_attempts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS
    )
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    auto_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    seed = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "user", "number"], name="uniq_attempt_quiz_user_number"
            )
        ]


class Response(BaseModel):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="responses")
    answer = models.JSONField(default=dict, blank=True)
    autosaved_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    feedback_json = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"], name="uniq_response_attempt_question"
            )
        ]


class Rubric(BaseModel):
    title = models.CharField(max_length=200, blank=True)
    criteria = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return self.title or f"Rubric {self.id}"


class Assignment(BaseModel):
    subtopic = models.OneToOneField(
        "courses.Subtopic", on_delete=models.CASCADE, related_name="assignment"
    )
    title = models.CharField(max_length=200)
    instructions_json = models.JSONField(default=dict, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    points = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    allow_resubmit = models.BooleanField(default=False)
    max_resubmits = models.PositiveIntegerField(default=0)
    rubric = models.ForeignKey(
        Rubric, null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments"
    )
    release_grades_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.title


class Submission(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    enrollment = models.ForeignKey(
        "admissions.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment_submissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_submissions"
    )
    version = models.PositiveIntegerField(default=1)
    text = models.TextField(blank=True)
    link = models.URLField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT
    )

    class Meta:
        ordering = ["-submitted_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "user", "version"],
                name="uniq_submission_assignment_user_version",
            )
        ]


class SubmissionGrade(BaseModel):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name="grade")
    rubric_scores = models.JSONField(default=dict, blank=True)
    raw_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    penalty = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    final_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    feedback_json = models.JSONField(default=dict, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grades_given",
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)


class GradeEntry(BaseModel):
    enrollment = models.ForeignKey(
        "admissions.Enrollment", on_delete=models.CASCADE, related_name="grade_entries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grade_entries"
    )
    class_ref = models.ForeignKey(
        "programs.Class", on_delete=models.CASCADE, related_name="grade_entries"
    )
    subject = models.ForeignKey(
        "courses.Subject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grade_entries",
    )
    subtopic = models.ForeignKey(
        "courses.Subtopic",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="grade_entries",
    )
    item_type = models.CharField(max_length=32)
    item_id = models.UUIDField()
    title = models.CharField(max_length=200, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    source = models.CharField(
        max_length=16, choices=GradeSource.choices, default=GradeSource.MANUAL
    )
    released = models.BooleanField(default=False)
    attempt_id = models.UUIDField(null=True, blank=True)
    submission_id = models.UUIDField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "item_type", "item_id"],
                name="uniq_grade_entry_enrollment_item",
            )
        ]
        ordering = ["title", "created_at"]
