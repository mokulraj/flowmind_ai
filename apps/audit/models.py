from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        VIEW = "VIEW", "View"
        EXPORT = "EXPORT", "Export"
        GENERATE = "GENERATE", "Generate"
        RUN = "RUN", "Run"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    object_type = models.CharField(
        max_length=100,
    )

    object_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    object_repr = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"]
            ),
            models.Index(
                fields=["user", "-created_at"]
            ),
            models.Index(
                fields=["organization", "action"]
            ),
            models.Index(
                fields=["organization", "object_type"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.action} - "
            f"{self.object_type} - "
            f"{self.object_id}"
        )