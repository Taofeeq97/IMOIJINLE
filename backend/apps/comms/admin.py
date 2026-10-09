from django.contrib import admin

from apps.comms.models import Announcement, EmailLog, Notification, NotificationPreference

admin.site.register(Announcement)
admin.site.register(Notification)
admin.site.register(NotificationPreference)
admin.site.register(EmailLog)
