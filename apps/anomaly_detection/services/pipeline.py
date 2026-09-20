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

        return {
            "preprocessing": preprocessing_result,
            "anomalies": anomaly_results,
        }