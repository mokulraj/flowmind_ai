from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.organizations.models import Organization


class Workflow(models.Model):
    """
    Represents a real-world business process.

    Every workflow belongs to exactly one organization.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        ARCHIVED = "ARCHIVED", "Archived"

    class Category(models.TextChoices):
        OPERATIONS = "OPERATIONS", "Operations"
        ORDER_FULFILLMENT = "ORDER_FULFILLMENT", "Order Fulfillment"
        CUSTOMER_SERVICE = "CUSTOMER_SERVICE", "Customer Service"
        FINANCE = "FINANCE", "Finance"
        HUMAN_RESOURCES = "HUMAN_RESOURCES", "Human Resources"
        IT = "IT", "IT"
        SALES = "SALES", "Sales"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workflows",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OPERATIONS,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workflows",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            models.Index(
                fields=["organization", "status"],
            ),
            models.Index(
                fields=["organization", "category"],
            ),
            models.Index(
                fields=["organization", "created_at"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_workflow_name_per_organization",
            ),
        ]

    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    """
    Represents an individual step in a workflow.
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    order = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
    )

    expected_duration = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
        help_text="Expected duration in minutes.",
    )

    department = models.CharField(
        max_length=255,
        blank=True,
    )

    responsible_role = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["order"]

        indexes = [
            models.Index(
                fields=["workflow", "order"],
            ),
            models.Index(
                fields=["workflow", "department"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "order"],
                name="unique_step_order_per_workflow",
            ),
            models.UniqueConstraint(
                fields=["workflow", "name"],
                name="unique_step_name_per_workflow",
            ),
        ]

    def __str__(self):
        return f"{self.workflow.name} → {self.name}"


class WorkflowConnection(models.Model):
    """
    Represents a directed connection between two workflow steps.

    Example:

        Verification → Payment
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="connections",
    )

    source_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="outgoing_connections",
    )

    target_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="incoming_connections",
    )

    condition = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional business condition for this transition.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["workflow"],
            ),
            models.Index(
                fields=["source_step"],
            ),
            models.Index(
                fields=["target_step"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "workflow",
                    "source_step",
                    "target_step",
                ],
                name="unique_workflow_connection",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.source_step_id == self.target_step_id:
            raise ValidationError(
                "A workflow step cannot connect to itself."
            )

        if (
            self.source_step_id
            and self.source_step.workflow_id != self.workflow_id
        ):
            raise ValidationError(
                "Source step must belong to this workflow."
            )

        if (
            self.target_step_id
            and self.target_step.workflow_id != self.workflow_id
        ):
            raise ValidationError(
                "Target step must belong to this workflow."
            )

    def __str__(self):
        return (
            f"{self.source_step.name} → "
            f"{self.target_step.name}"
        )