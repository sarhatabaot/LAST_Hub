from django.contrib import admin

from hub.models import AccountRequest, OperationalChecklistState


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
