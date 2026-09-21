from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditLogService

from .validator import DatasetValidationError, DatasetValidator


class DatasetService:

    @staticmethod
    def validate_dataset(dataset):
        """
        Validate an uploaded Dataset and store the validation results.
        """

        if not dataset.file:
            raise ValidationError(
                "A dataset file is required."
            )

        dataset.status = dataset.Status.VALIDATING
        dataset.validation_message = ""
        dataset.save(
            update_fields=[
                "status",
                "validation_message",
                "updated_at",
            ]
        )

        try:
            result = DatasetValidator(
                dataset.file.path
            ).validate()

        except DatasetValidationError as exc:
            dataset.status = dataset.Status.FAILED
            dataset.validation_message = str(exc)
            dataset.validated_at = timezone.now()

            dataset.save(
                update_fields=[
                    "status",
                    "validation_message",
                    "validated_at",
                    "updated_at",
                ]
            )

            AuditLogService.create(
                organization=dataset.organization,
                user=dataset.uploaded_by,
                action=AuditLog.Action.RUN,
                object_type="Dataset",
                object_id=dataset.id,
                object_repr=str(dataset),
                description=(
                    f"Dataset validation failed for "
                    f"'{dataset.name}'."
                ),
                metadata={
                    "dataset_id": dataset.id,
                    "dataset_name": dataset.name,
                    "workflow_id": dataset.workflow_id,
                    "status": dataset.status,
                    "validation_message": dataset.validation_message,
                },
            )

            raise ValidationError(str(exc)) from exc

        dataset.row_count = result["row_count"]
        dataset.column_count = result["column_count"]
        dataset.missing_cells = result["missing_cells"]
        dataset.missing_percentage = result["missing_percentage"]
        dataset.duplicate_rows = result["duplicate_rows"]
        dataset.duplicate_percentage = result["duplicate_percentage"]
        dataset.quality_score = result["quality_score"]
        dataset.status = dataset.Status.VALIDATED
        dataset.validation_message = (
            "Dataset validation completed successfully."
        )
        dataset.validated_at = timezone.now()

        dataset.save(
            update_fields=[
                "row_count",
                "column_count",
                "missing_cells",
                "missing_percentage",
                "duplicate_rows",
                "duplicate_percentage",
                "quality_score",
                "status",
                "validation_message",
                "validated_at",
                "updated_at",
            ]
        )

        AuditLogService.create(
            organization=dataset.organization,
            user=dataset.uploaded_by,
            action=AuditLog.Action.RUN,
            object_type="Dataset",
            object_id=dataset.id,
            object_repr=str(dataset),
            description=(
                f"Validated dataset '{dataset.name}' successfully."
            ),
            metadata={
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "workflow_id": dataset.workflow_id,
                "row_count": result["row_count"],
                "column_count": result["column_count"],
                "missing_cells": result["missing_cells"],
                "missing_percentage": result["missing_percentage"],
                "duplicate_rows": result["duplicate_rows"],
                "duplicate_percentage": result["duplicate_percentage"],
                "quality_score": result["quality_score"],
                "status": dataset.status,
            },
        )

        return dataset
