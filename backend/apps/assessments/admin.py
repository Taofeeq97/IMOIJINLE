# Admin registrations intentionally minimal to avoid model-name drift during consolidation.
from django.contrib import admin

from apps.assessments.models import Assignment, Quiz, Submission

admin.site.register(Quiz)
admin.site.register(Assignment)
admin.site.register(Submission)
