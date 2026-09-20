from apps.preprocessing.services.dataset_preprocessing import (
    DatasetPreprocessingService,
)

from .duration import DurationAnalytics


class AnalyticsPipeline:
    """
    Runs preprocessing followed by workflow duration analytics.
    """

    def __init__(
        self,
        dataset,
        step_column="step_name",
        duration_column="duration_minutes",
    ):
        self.dataset = dataset
        self.step_column = step_column
        self.duration_column = duration_column

    def run(self):
        preprocessing_result = (
            DatasetPreprocessingService(
                self.dataset
            ).process()
        )

        cleaned_dataframe = preprocessing_result[
            "dataframe"
        ]

        duration_result = DurationAnalytics(
            cleaned_dataframe,
            step_column=self.step_column,
            duration_column=self.duration_column,
        ).calculate()

        return {
            "preprocessing": preprocessing_result,
            "duration_analytics": duration_result,
        }