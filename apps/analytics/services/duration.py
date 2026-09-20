import pandas as pd


class AnalyticsError(Exception):
    """Raised when analytics cannot be calculated."""


class DurationAnalytics:
    """
    Calculates duration statistics for workflow steps.
    """

    def __init__(
        self,
        dataframe,
        step_column="step_name",
        duration_column="duration_minutes",
    ):
        if not isinstance(dataframe, pd.DataFrame):
            raise AnalyticsError(
                "Input must be a pandas DataFrame."
            )

        self.dataframe = dataframe.copy()
        self.step_column = step_column
        self.duration_column = duration_column

    def calculate(self):
        self._validate_columns()

        dataframe = self.dataframe.copy()

        dataframe[self.duration_column] = pd.to_numeric(
            dataframe[self.duration_column],
            errors="coerce",
        )

        dataframe = dataframe.dropna(
            subset=[
                self.step_column,
                self.duration_column,
            ]
        )

        if dataframe.empty:
            raise AnalyticsError(
                "No valid duration data is available."
            )

        dataframe = dataframe[
            dataframe[self.duration_column] >= 0
        ]

        if dataframe.empty:
            raise AnalyticsError(
                "No non-negative duration values are available."
            )

        grouped = (
            dataframe
            .groupby(self.step_column)[self.duration_column]
            .agg(
                event_count="count",
                average_duration="mean",
                median_duration="median",
                minimum_duration="min",
                maximum_duration="max",
                total_duration="sum",
            )
            .reset_index()
        )

        grouped = grouped.sort_values(
            by="average_duration",
            ascending=False,
        )

        numeric_columns = [
            "average_duration",
            "median_duration",
            "minimum_duration",
            "maximum_duration",
            "total_duration",
        ]

        grouped[numeric_columns] = grouped[
            numeric_columns
        ].round(2)

        return grouped.reset_index(drop=True)

    def _validate_columns(self):
        required_columns = {
            self.step_column,
            self.duration_column,
        }

        missing_columns = (
            required_columns
            - set(self.dataframe.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )

            raise AnalyticsError(
                f"Missing required column(s): {missing}"
            )