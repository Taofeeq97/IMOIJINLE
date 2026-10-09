from django.contrib import admin

from apps.learning.models import (
    Answer,
    ItemProgress,
    Note,
    Question,
    SubjectProgress,
    VideoProgress,
)

admin.site.register(ItemProgress)
admin.site.register(VideoProgress)
admin.site.register(SubjectProgress)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Note)
