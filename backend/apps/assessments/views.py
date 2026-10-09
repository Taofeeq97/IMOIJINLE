from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.accounts.policies import can
from apps.assessments import services
from apps.assessments.serializers import (
    AssignmentSerializer,
    AssignmentUpsertSerializer,
    AttemptSerializer,
    GradeWriteSerializer,
    QuizPublicSerializer,
    QuizSerializer,
    QuizUpsertSerializer,
    ReleaseGradesSerializer,
    ResponsesWriteSerializer,
    SubmissionGradeSerializer,
    SubmissionSerializer,
    SubmissionWriteSerializer,
)


class TeachPermission(RolePermission):
    required_action = "teach"


class GradePermission(RolePermission):
    required_action = "grade"


class LearnPermission(RolePermission):
    required_action = "learn"


def _err(exc: services.AssessmentError):
    code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "not_enrolled": status.HTTP_403_FORBIDDEN,
    }
    http = code_map.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return Response({"code": exc.code, "message": exc.message}, status=http)


class SubtopicQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subtopic_id):
        from apps.assessments.models import Quiz

        try:
            quiz = Quiz.objects.prefetch_related("questions").get(subtopic_id=subtopic_id)
        except Quiz.DoesNotExist:
            return Response({"code": "not_found", "message": "No quiz"}, status=404)
        if can(request.user, "teach") or can(request.user, "grade"):
            return Response(QuizSerializer(quiz).data)
        if not can(request.user, "learn"):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        return Response(QuizPublicSerializer(quiz).data)

    def post(self, request, subtopic_id):
        if not can(request.user, "teach"):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        ser = QuizUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            quiz = services.upsert_quiz(subtopic_id=str(subtopic_id), **ser.validated_data)
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(QuizSerializer(quiz).data, status=status.HTTP_200_OK)


class QuizDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quiz_id):
        try:
            quiz = services.get_quiz(str(quiz_id))
        except services.AssessmentError as exc:
            return _err(exc)
        if can(request.user, "teach") or can(request.user, "grade"):
            return Response(QuizSerializer(quiz).data)
        if not can(request.user, "learn"):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        return Response(QuizPublicSerializer(quiz).data)


class QuizAttemptsView(APIView):
    permission_classes = [IsAuthenticated, LearnPermission]

    def post(self, request, quiz_id):
        try:
            attempt = services.start_attempt(user=request.user, quiz_id=str(quiz_id))
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(AttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


class AttemptResponsesView(APIView):
    permission_classes = [IsAuthenticated, LearnPermission]

    def put(self, request, attempt_id):
        ser = ResponsesWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            attempt = services.save_responses(
                user=request.user,
                attempt_id=str(attempt_id),
                responses=ser.validated_data["responses"],
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(AttemptSerializer(attempt).data)


class AttemptSubmitView(APIView):
    permission_classes = [IsAuthenticated, LearnPermission]

    def post(self, request, attempt_id):
        try:
            attempt = services.submit_attempt(user=request.user, attempt_id=str(attempt_id))
        except services.AssessmentError as exc:
            return _err(exc)
        data = AttemptSerializer(attempt).data
        if attempt.quiz.release_scores:
            data["released"] = True
        else:
            data["score"] = None
            data["auto_score"] = None
            data["released"] = False
        return Response(data)


class AttemptReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id):
        is_staff = can(request.user, "teach") or can(request.user, "grade")
        try:
            payload = services.review_attempt(
                user=request.user, attempt_id=str(attempt_id), is_staff=is_staff
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(payload)


class SubtopicAssignmentView(APIView):
    permission_classes = [IsAuthenticated, TeachPermission]

    def post(self, request, subtopic_id):
        ser = AssignmentUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            assignment = services.upsert_assignment(
                subtopic_id=str(subtopic_id), **ser.validated_data
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(AssignmentSerializer(assignment).data)


class AssignmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id):
        from apps.assessments.models import Assignment

        try:
            assignment = Assignment.objects.select_related("rubric", "subtopic").get(
                id=assignment_id
            )
        except Assignment.DoesNotExist:
            return Response({"code": "not_found", "message": "Not found"}, status=404)
        return Response(AssignmentSerializer(assignment).data)


class AssignmentSubmissionsView(APIView):
    permission_classes = [IsAuthenticated, LearnPermission]

    def post(self, request, assignment_id):
        ser = SubmissionWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            submission = services.submit_assignment(
                user=request.user,
                assignment_id=str(assignment_id),
                text=ser.validated_data.get("text") or "",
                link=ser.validated_data.get("link") or "",
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class GradingQueueView(APIView):
    permission_classes = [IsAuthenticated, GradePermission]

    def get(self, request):
        rows = services.grading_queue(
            class_id=request.query_params.get("class_id"),
            assignment_id=request.query_params.get("assignment_id"),
        )
        return Response({"results": rows})


class SubmissionGradeView(APIView):
    permission_classes = [IsAuthenticated, GradePermission]

    def put(self, request, submission_id):
        ser = GradeWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            grade = services.grade_submission(
                grader=request.user,
                submission_id=str(submission_id),
                **ser.validated_data,
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(SubmissionGradeSerializer(grade).data)


class ReleaseGradesView(APIView):
    permission_classes = [IsAuthenticated, GradePermission]

    def post(self, request):
        ser = ReleaseGradesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        results = services.release_grades(
            submission_ids=[str(x) for x in ser.validated_data["submission_ids"]]
        )
        return Response({"results": results})


class ClassGradebookView(APIView):
    permission_classes = [IsAuthenticated, GradePermission]

    def get(self, request, class_id):
        try:
            payload = services.class_gradebook(
                class_id=str(class_id),
                subject_id=request.query_params.get("subject_id"),
            )
        except services.AssessmentError as exc:
            return _err(exc)
        return Response(payload)


class MyGradesView(APIView):
    permission_classes = [IsAuthenticated, LearnPermission]

    def get(self, request):
        rows = services.student_released_grades(
            user=request.user, class_id=request.query_params.get("class_id")
        )
        return Response({"results": rows})


class SubmissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, submission_id):
        if can(request.user, "grade") or can(request.user, "teach"):
            from apps.assessments.models import Submission

            try:
                s = Submission.objects.select_related("grade", "assignment").get(id=submission_id)
            except Submission.DoesNotExist:
                return Response({"code": "not_found", "message": "Not found"}, status=404)
            data = SubmissionSerializer(s).data
            if hasattr(s, "grade") and s.grade:
                data["grade"] = SubmissionGradeSerializer(s.grade).data
            return Response(data)
        try:
            return Response(
                services.get_submission_for_student(
                    user=request.user, submission_id=str(submission_id)
                )
            )
        except services.AssessmentError as exc:
            return _err(exc)
