from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditLogService
from apps.organizations.models import OrganizationMember
from apps.preprocessing.services.dataset_preprocessing import (
    DatasetPreprocessingService,
)

from .duration import DurationAnalytics


class AnalyticsPipeline:
    """
    Runs the complete analytics workflow for a dataset.
    """

    def __init__(self, dataset):
        self.dataset = dataset

    def run(self):
        preprocessing = DatasetPreprocessingService(
            self.dataset
        ).process()

        duration_analytics = DurationAnalytics(
            preprocessing["dataframe"]
        ).calculate()

        result = {
            "preprocessing": preprocessing,
            "duration_analytics": duration_analytics,
        }

        # Some existing analytics usage creates a standalone
        # Dataset without an organization. Preserve that behavior.
        if self.dataset.organization_id:
            audit_user = None

            if self.dataset.uploaded_by_id:
                is_member = OrganizationMember.objects.filter(
                    organization_id=self.dataset.organization_id,
                    user_id=self.dataset.uploaded_by_id,
                ).exists()

                if is_member:
                    audit_user = self.dataset.uploaded_by

            AuditLogService.create(
                organization=self.dataset.organization,
                user=audit_user,
                action=AuditLog.Action.RUN,
                object_type="Analytics",
                object_id=self.dataset.id,
                object_repr=str(self.dataset),
                description=(
                    f"Analytics completed for dataset "
                    f"'{self.dataset.name}'."
                ),
                metadata={
                    "dataset_id": self.dataset.id,
                    "dataset_name": self.dataset.name,
                    "workflow_id": self.dataset.workflow_id,
                    "step_count": len(duration_analytics),
                    "original_rows": preprocessing[
                        "original_rows"
                    ],
                    "cleaned_rows": preprocessing[
                        "cleaned_rows"
                    ],
                    "rows_removed": preprocessing[
                        "rows_removed"
                    ],
                    "original_columns": preprocessing[
                        "original_columns"
                    ],
                    "cleaned_columns": preprocessing[
                        "cleaned_columns"
                    ],
                },
            )

        return result