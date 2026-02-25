from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin

from hub.models import AccountRequest, ManualPage, OperationalChecklistState, MountConfiguration


@admin.register(OperationalChecklistState)
class OperationalChecklistStateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "observatory_state",
        "updated_at",
        "updated_by",
        "last_action",
        "last_action_status",
        "last_action_at",
        "last_action_by",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccountRequest)
class AccountRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "organization")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ManualPage)
class ManualPageAdmin(MarkdownxModelAdmin):
    list_display = ("title", "section", "slug", "updated_at")
    search_fields = ("title", "section", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(MountConfiguration)
class MountConfigurationAdmin(admin.ModelAdmin):
    list_display = ("mount_id", "enabled", "reason", "updated_at", "updated_by")
    list_filter = ("enabled", "mount_id")
    search_fields = ("mount_id", "reason")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            'fields': ('mount_id', 'enabled', 'reason')
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


