from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditLogService
from apps.preprocessing.services.dataset_preprocessing import (
    DatasetPreprocessingService,
)

from .detector import AnomalyDetector


class AnomalyPipeline:
    """
    Runs dataset preprocessing and then detects anomalous
    duration observations.
    """

    def __init__(
        self,
        dataset,
        duration_column="duration_minutes",
        contamination=0.05,
    ):
        self.dataset = dataset
        self.duration_column = duration_column
        self.contamination = contamination

    def run(self):
        preprocessing_service = DatasetPreprocessingService(
            dataset=self.dataset
        )

        preprocessing_result = (
            preprocessing_service.process()
        )

        cleaned_dataframe = preprocessing_result[
            "dataframe"
        ]

        detector = AnomalyDetector(
            dataframe=cleaned_dataframe,
            duration_column=self.duration_column,
            contamination=self.contamination,
        )

        anomaly_results = detector.detect()

        result = {
            "preprocessing": preprocessing_result,
            "anomalies": anomaly_results,
        }

        # Some existing anomaly-detection usage may use a
        # standalone dataset without an organization.
        # Preserve that behavior.
        if self.dataset.organization_id:
            anomaly_count = int(
                anomaly_results["is_anomaly"].sum()
            )

            AuditLogService.create(
                organization=self.dataset.organization,
                user=self.dataset.uploaded_by,
                action=AuditLog.Action.RUN,
                object_type="AnomalyDetection",
                object_id=self.dataset.id,
                object_repr=str(self.dataset),
                description=(
                    f"Anomaly detection completed for "
                    f"dataset '{self.dataset.name}'."
                ),
                metadata={
                    "dataset_id": self.dataset.id,
                    "dataset_name": self.dataset.name,
                    "workflow_id": self.dataset.workflow_id,
                    "duration_column": self.duration_column,
                    "contamination": self.contamination,
                    "processed_rows": len(anomaly_results),
                    "anomaly_count": anomaly_count,
                    "normal_count": (
                        len(anomaly_results) - anomaly_count
                    ),
                    "preprocessing_original_rows": (
                        preprocessing_result["original_rows"]
                    ),
                    "preprocessing_cleaned_rows": (
                        preprocessing_result["cleaned_rows"]
                    ),
                },
            )

        return result