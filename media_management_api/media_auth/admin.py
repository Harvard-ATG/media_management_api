from django.contrib import admin

from .models import Application


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "client_id", "client_secret", "description", "created")


admin.site.register(Application, ApplicationAdmin)
