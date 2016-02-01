from django.contrib import admin
from .models import Application, Token

class TokensInline(admin.StackedInline):
    extra = 0
    verbose_name = 'Token'
    model = Token

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_id', 'client_secret', 'description', 'created')
    inlines = (TokensInline,)

class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'user_profile', 'key', 'scope', 'created')

admin.site.register(Token, TokenAdmin)
admin.site.register(Application, ApplicationAdmin)
