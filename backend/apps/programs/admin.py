from django.contrib import admin

from apps.programs.models import Class, ClassSubject, ClassTutor, Cohort, Program

admin.site.register(Program)
admin.site.register(Cohort)
admin.site.register(Class)
admin.site.register(ClassTutor)
admin.site.register(ClassSubject)
