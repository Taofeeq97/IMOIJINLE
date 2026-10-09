from rest_framework import serializers

from apps.learning.models import Answer, Note, Question


class HeartbeatSerializer(serializers.Serializer):
    delta_s = serializers.IntegerField(required=False, min_value=0, max_value=60, default=5)
    position_s = serializers.IntegerField(required=False, min_value=0)


class VideoProgressSerializer(serializers.Serializer):
    position_s = serializers.IntegerField(min_value=0)
    duration_s = serializers.IntegerField(required=False, min_value=0, default=0)
    rate = serializers.FloatField(required=False, default=1.0)
    segments = serializers.ListField(
        required=False, child=serializers.ListField(child=serializers.FloatField())
    )
    device_id = serializers.CharField(required=False, allow_blank=True)
    client_ts = serializers.IntegerField(required=False, default=0)


class QuestionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    subtopic_id = serializers.UUIDField(required=False)


class AnswerCreateSerializer(serializers.Serializer):
    body = serializers.CharField()


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "subtopic", "body", "timestamp_s", "created_at", "updated_at"]
        read_only_fields = ["id", "subtopic", "created_at", "updated_at"]


class NoteWriteSerializer(serializers.Serializer):
    body = serializers.CharField()
    timestamp_s = serializers.IntegerField(required=False, allow_null=True)


class AnswerSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = ["id", "body", "is_instructor", "upvote_count", "author_name", "created_at"]

    def get_author_name(self, obj: Answer) -> str:
        u = obj.author
        name = f"{u.first_name} {u.last_name}".strip()
        return name or u.email


class QuestionSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "subject",
            "subtopic",
            "title",
            "body",
            "upvote_count",
            "is_resolved",
            "author_name",
            "answers",
            "created_at",
        ]

    def get_author_name(self, obj: Question) -> str:
        u = obj.author
        name = f"{u.first_name} {u.last_name}".strip()
        return name or u.email
