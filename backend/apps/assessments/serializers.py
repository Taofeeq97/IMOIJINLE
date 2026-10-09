from rest_framework import serializers

from apps.assessments.models import (
    Assignment,
    Attempt,
    Quiz,
    QuizQuestion,
    Rubric,
    Submission,
    SubmissionGrade,
)


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "prompt",
            "question_type",
            "choices",
            "correct_answer",
            "order",
            "points",
        ]


class QuizQuestionPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = ["id", "prompt", "question_type", "choices", "order", "points"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    subtopic_id = serializers.UUIDField(source="subtopic.id", read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "subtopic_id",
            "title",
            "instructions_json",
            "settings",
            "points_total",
            "release_scores",
            "questions",
            "created_at",
            "updated_at",
        ]


class QuizPublicSerializer(serializers.ModelSerializer):
    questions = QuizQuestionPublicSerializer(many=True, read_only=True)
    subtopic_id = serializers.UUIDField(source="subtopic.id", read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "subtopic_id",
            "title",
            "instructions_json",
            "settings",
            "points_total",
            "release_scores",
            "questions",
        ]


class QuizUpsertSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    instructions_json = serializers.DictField(required=False, allow_null=True)
    settings = serializers.DictField(required=False, allow_null=True)
    release_scores = serializers.BooleanField(required=False, default=True)
    questions = serializers.ListField(child=serializers.DictField(), required=False)


class AttemptSerializer(serializers.ModelSerializer):
    quiz_id = serializers.UUIDField(source="quiz.id", read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "quiz_id",
            "number",
            "status",
            "started_at",
            "deadline_at",
            "submitted_at",
            "score",
            "auto_score",
            "max_score",
        ]


class ResponsesWriteSerializer(serializers.Serializer):
    responses = serializers.ListField(child=serializers.DictField(), allow_empty=True)


class RubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rubric
        fields = ["id", "title", "criteria"]


class AssignmentSerializer(serializers.ModelSerializer):
    subtopic_id = serializers.UUIDField(source="subtopic.id", read_only=True)
    rubric = RubricSerializer(read_only=True)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "subtopic_id",
            "title",
            "instructions_json",
            "due_at",
            "points",
            "allow_resubmit",
            "max_resubmits",
            "rubric",
            "release_grades_at",
            "created_at",
            "updated_at",
        ]


class AssignmentUpsertSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    instructions_json = serializers.DictField(required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    points = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=100)
    allow_resubmit = serializers.BooleanField(required=False, default=False)
    max_resubmits = serializers.IntegerField(required=False, default=0)
    rubric = serializers.DictField(required=False, allow_null=True)


class SubmissionWriteSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, default="")
    link = serializers.URLField(required=False, allow_blank=True, default="")


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_id = serializers.UUIDField(source="assignment.id", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment_id",
            "version",
            "text",
            "link",
            "submitted_at",
            "status",
        ]


class GradeWriteSerializer(serializers.Serializer):
    rubric_scores = serializers.DictField(required=False)
    raw_score = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    penalty = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=0)
    feedback_json = serializers.DictField(required=False)


class SubmissionGradeSerializer(serializers.ModelSerializer):
    submission_id = serializers.UUIDField(source="submission.id", read_only=True)

    class Meta:
        model = SubmissionGrade
        fields = [
            "id",
            "submission_id",
            "rubric_scores",
            "raw_score",
            "penalty",
            "final_score",
            "feedback_json",
            "graded_at",
            "released_at",
        ]


class ReleaseGradesSerializer(serializers.Serializer):
    submission_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, min_length=1
    )
