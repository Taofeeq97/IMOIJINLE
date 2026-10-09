from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.courses.models import Subject, Subtopic
from apps.learning import services
from apps.learning.serializers import (
    AnswerCreateSerializer,
    AnswerSerializer,
    HeartbeatSerializer,
    NoteSerializer,
    NoteWriteSerializer,
    QuestionCreateSerializer,
    QuestionSerializer,
    VideoProgressSerializer,
)


class LearnPermission(RolePermission):
    required_action = "learn"


class MyLearningView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.my_learning_payload(request.user))


class SubjectLandingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        try:
            return Response(services.subject_landing_payload(user=request.user, slug=slug))
        except services.LearningError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"code": exc.code, "message": exc.message}, status=code)


class PlayerOutlineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            return Response(services.player_outline(user=request.user, subject_id=str(subject_id)))
        except services.LearningError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"code": exc.code, "message": exc.message}, status=code)


class SubtopicViewerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subtopic_id):
        try:
            return Response(services.viewer_payload(user=request.user, subtopic_id=str(subtopic_id)))
        except services.LearningError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"code": exc.code, "message": exc.message}, status=code)


class SubtopicHeartbeatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, subtopic_id):
        ser = HeartbeatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ip = services.heartbeat(
                user=request.user,
                subtopic_id=str(subtopic_id),
                delta_s=ser.validated_data.get("delta_s", 5),
                position_s=ser.validated_data.get("position_s"),
            )
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(
            {
                "time_spent_s": ip.time_spent_s,
                "status": ip.status,
                "can_complete": ip.time_spent_s >= ip.subtopic.min_time_s or ip.status == "completed",
                "min_time_s": ip.subtopic.min_time_s,
            }
        )


class SubtopicCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, subtopic_id):
        try:
            ip = services.complete_subtopic(user=request.user, subtopic_id=str(subtopic_id))
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(
            {
                "status": ip.status,
                "completed_at": ip.completed_at,
                "time_spent_s": ip.time_spent_s,
            }
        )


class SubtopicVideoProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, subtopic_id):
        ser = VideoProgressSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            vp = services.upsert_video_progress(
                user=request.user,
                subtopic_id=str(subtopic_id),
                **ser.validated_data,
            )
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        resume = max(0, vp.last_position_s - 3) if vp.watched_pct < 98 else 0
        return Response(
            {
                "last_position_s": vp.last_position_s,
                "resume_position_s": resume,
                "furthest_position_s": vp.furthest_position_s,
                "watched_pct": vp.watched_pct,
            }
        )


class SubjectQAView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            subject = Subject.objects.get(id=subject_id)
            services.assert_subject_access(user=request.user, subject=subject, allow_preview=True)
        except Subject.DoesNotExist:
            return Response({"code": "not_found", "message": "Not found"}, status=404)
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=403)
        qs = services.list_questions(
            subject_id=str(subject_id),
            subtopic_id=request.query_params.get("subtopic"),
            q=request.query_params.get("q") or "",
        )
        return Response(QuestionSerializer(qs[:100], many=True).data)

    def post(self, request, subject_id):
        ser = QuestionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            subject = Subject.objects.get(id=subject_id)
            subtopic = None
            if ser.validated_data.get("subtopic_id"):
                subtopic = Subtopic.objects.get(id=ser.validated_data["subtopic_id"])
            q = services.create_question(
                user=request.user,
                subject=subject,
                title=ser.validated_data["title"],
                body=ser.validated_data["body"],
                subtopic=subtopic,
            )
        except (Subject.DoesNotExist, Subtopic.DoesNotExist):
            return Response({"code": "not_found", "message": "Not found"}, status=404)
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=403)
        return Response(QuestionSerializer(q).data, status=status.HTTP_201_CREATED)


class QuestionAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, question_id):
        from apps.learning.models import Question

        ser = AnswerCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            question = Question.objects.select_related("subject").get(id=question_id)
            answer = services.create_answer(
                user=request.user, question=question, body=ser.validated_data["body"]
            )
        except Question.DoesNotExist:
            return Response({"code": "not_found", "message": "Not found"}, status=404)
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=403)
        return Response(AnswerSerializer(answer).data, status=status.HTTP_201_CREATED)


class SubtopicNotesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subtopic_id):
        try:
            notes = services.list_notes(user=request.user, subtopic_id=str(subtopic_id))
        except (Subtopic.DoesNotExist, services.LearningError) as exc:
            msg = getattr(exc, "message", "Not found")
            code = getattr(exc, "code", "not_found")
            return Response({"code": code, "message": msg}, status=400)
        return Response(NoteSerializer(notes, many=True).data)

    def post(self, request, subtopic_id):
        ser = NoteWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            note = services.upsert_note(
                user=request.user,
                subtopic_id=str(subtopic_id),
                body=ser.validated_data["body"],
                timestamp_s=ser.validated_data.get("timestamp_s"),
            )
        except (Subtopic.DoesNotExist, services.LearningError) as exc:
            msg = getattr(exc, "message", "Error")
            code = getattr(exc, "code", "error")
            return Response({"code": code, "message": msg}, status=400)
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


class NoteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, note_id):
        ser = NoteWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.learning.models import Note

        try:
            note = Note.objects.get(id=note_id, user=request.user)
            note = services.upsert_note(
                user=request.user,
                subtopic_id=str(note.subtopic_id),
                body=ser.validated_data["body"],
                timestamp_s=ser.validated_data.get("timestamp_s"),
                note_id=str(note.id),
            )
        except Note.DoesNotExist:
            return Response({"code": "not_found", "message": "Not found"}, status=404)
        except services.LearningError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(NoteSerializer(note).data)

    def delete(self, request, note_id):
        services.delete_note(user=request.user, note_id=str(note_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
