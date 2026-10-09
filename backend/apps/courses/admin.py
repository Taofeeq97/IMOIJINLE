from django.contrib import admin

from apps.courses.models import (
    Subject,
    Subtopic,
    SubtopicContent,
    SubtopicResource,
    Topic,
    UploadSession,
    VideoAsset,
)

admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(Subtopic)
admin.site.register(SubtopicContent)
admin.site.register(SubtopicResource)
admin.site.register(VideoAsset)
admin.site.register(UploadSession)
