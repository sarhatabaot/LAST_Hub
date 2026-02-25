from django.conf import settings
from django.db import models
from markdownx.models import MarkdownxField
import json
from pathlib import Path


class OperationalChecklistState(models.Model):
    STATE_UNKNOWN = "unknown"
    STATE_OPEN = "open"
    STATE_CLOSED = "closed"

    ACTION_OPEN = "open"
    ACTION_CLOSE = "close"

    ACTION_STATUS_SUCCESS = "success"
    ACTION_STATUS_FAILED = "failed"
    ACTION_STATUS_SKIPPED = "skipped"

    STATE_CHOICES = [
        (STATE_UNKNOWN, "Unknown"),
        (STATE_OPEN, "Open"),
        (STATE_CLOSED, "Closed"),
    ]

    ACTION_CHOICES = [
        (ACTION_OPEN, "Open"),
        (ACTION_CLOSE, "Close"),
    ]

    ACTION_STATUS_CHOICES = [
        (ACTION_STATUS_SUCCESS, "Success"),
        (ACTION_STATUS_FAILED, "Failed"),
        (ACTION_STATUS_SKIPPED, "Skipped"),
    ]

    items = models.JSONField(default=dict, blank=True)
    observatory_state = models.CharField(
        max_length=12,
        choices=STATE_CHOICES,
        default=STATE_UNKNOWN,
    )
    last_action = models.CharField(max_length=8, choices=ACTION_CHOICES, blank=True)
    last_action_status = models.CharField(
        max_length=8,
        choices=ACTION_STATUS_CHOICES,
        blank=True,
    )
    last_action_message = models.TextField(blank=True)
    last_action_at = models.DateTimeField(null=True, blank=True)
    last_action_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operations_actions",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operations_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def state_label(self):
        return dict(self.STATE_CHOICES).get(self.observatory_state, "Unknown")

    def action_label(self):
        return dict(self.ACTION_CHOICES).get(self.last_action, "")

    def action_status_label(self):
        return dict(self.ACTION_STATUS_CHOICES).get(self.last_action_status, "")


class AccountRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DENIED = "denied"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DENIED, "Denied"),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    organization = models.CharField(max_length=120, blank=True)
    justification = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class ManualPage(models.Model):
    slug = models.SlugField(max_length=120, unique=True, default="manual")
    title = models.CharField(max_length=200, default="Manual")
    section = models.CharField(max_length=200, blank=True, default="")
    content = MarkdownxField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


def get_mount_choices():
    """Dynamically load mount choices from mounts.json file."""
    BASE_DIR = Path(__file__).resolve().parent
    mounts_path = BASE_DIR / "data" / "mounts.json"
    
    with open(mounts_path, 'r') as f:
        mounts_data = json.load(f)
        # Use mount_id as both value and display text
        return [(mount['mount_id'], mount['mount_id']) for mount in mounts_data]


class MountConfiguration(models.Model):
    mount_id = models.CharField(max_length=3, choices=get_mount_choices, unique=True)
    enabled = models.BooleanField(default=True)
    reason = models.TextField(blank=True, help_text="Reason for disabling this mount (if disabled)")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mount_config_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mount Configuration"
        verbose_name_plural = "Mount Configurations"
        ordering = ['mount_id']

    def __str__(self):
        status = "Enabled" if self.enabled else f"Disabled ({self.reason or 'No reason provided'})"
        return f"{self.get_mount_id_display()}: {status}"


