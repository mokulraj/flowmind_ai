from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.organizations.models import Organization
from apps.workflows.models import Workflow


def dataset_upload_path(instance, filename):
    return (
        f"datasets/"
        f"organization_{instance.organization_id}/"
        f"workflow_{instance.workflow_id}/"
        f"{filename}"
    )


def validate_dataset_file(value):
    allowed_extensions = {".csv", ".xlsx", ".xls"}

    filename = value.name.lower()

    if not any(filename.endswith(extension) for extension in allowed_extensions):
        raise ValidationError(
            "Unsupported dataset format. Please upload a CSV or Excel file."
        )


class Dataset(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        VALIDATING = "VALIDATING", "Validating"
        VALIDATED = "VALIDATED", "Validated"
        FAILED = "FAILED", "Validation Failed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="datasets",
    )

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="datasets",
    )

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    file = models.FileField(
        upload_to=dataset_upload_path,
        validators=[validate_dataset_file],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
        help_text="File size in bytes.",
    )

    row_count = models.PositiveBigIntegerField(
        default=0,
        help_text="Number of data rows.",
    )

    column_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of columns.",
    )

    missing_cells = models.PositiveBigIntegerField(
        default=0,
        help_text="Total number of missing cells.",
    )

    missing_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Percentage of cells that are missing.",
    )

    duplicate_rows = models.PositiveBigIntegerField(
        default=0,
        help_text="Number of duplicate rows.",
    )

    duplicate_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Percentage of rows that are duplicates.",
    )

    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Data quality score from 0 to 100.",
    )

    validation_message = models.TextField(
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_datasets",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    validated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_dataset_name_per_organization",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="dataset_org_status_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="dataset_org_created_idx",
            ),
            models.Index(
                fields=["workflow", "status"],
                name="dataset_workflow_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.workflow_id and self.organization_id:
            if self.workflow.organization_id != self.organization_id:
                raise ValidationError(
                    {
                        "workflow": (
                            "The selected workflow must belong to the "
                            "selected organization."
                        )
                    }
                )

        if self.quality_score is not None:
            if self.quality_score < 0 or self.quality_score > 100:
                raise ValidationError(
                    {
                        "quality_score": (
                            "Quality score must be between 0 and 100."
                        )
                    }
                )

        if self.missing_percentage < 0 or self.missing_percentage > 100:
            raise ValidationError(
                {
                    "missing_percentage": (
                        "Missing percentage must be between 0 and 100."
                    )
                }
            )

        if self.duplicate_percentage < 0 or self.duplicate_percentage > 100:
            raise ValidationError(
                {
                    "duplicate_percentage": (
                        "Duplicate percentage must be between 0 and 100."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.workflow.name}"