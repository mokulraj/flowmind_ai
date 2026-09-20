import pandas as pd


class BottleneckDetectionError(Exception):
    """Raised when bottleneck analysis cannot be completed."""


class BottleneckDetector:
    """
    Compares actual step duration with expected workflow duration.
    """

    def __init__(
        self,
        analytics_dataframe,
        workflow_steps,
        step_column="step_name",
        average_duration_column="average_duration",
    ):
        if not isinstance(
            analytics_dataframe,
            pd.DataFrame,
        ):
            raise BottleneckDetectionError(
                "Analytics input must be a pandas DataFrame."
            )

        self.analytics_dataframe = (
            analytics_dataframe.copy()
        )

        self.workflow_steps = workflow_steps

        self.step_column = step_column
        self.average_duration_column = (
            average_duration_column
        )

    def detect(self):
        self._validate_columns()

        expected_durations = self._build_expected_duration_map()

        if not expected_durations:
            raise BottleneckDetectionError(
                "No workflow steps with expected durations were found."
            )

        result = self.analytics_dataframe.copy()

        result["expected_duration"] = result[
            self.step_column
        ].map(expected_durations)

        result = result.dropna(
            subset=["expected_duration"]
        )

        if result.empty:
            raise BottleneckDetectionError(
                "No analytics steps matched the workflow steps."
            )

        result["duration_difference"] = (
            result[self.average_duration_column]
            - result["expected_duration"]
        )

        result["delay_ratio"] = (
            result[self.average_duration_column]
            / result["expected_duration"]
        )

        result["delay_percentage"] = (
            (
                result["duration_difference"]
                / result["expected_duration"]
            )
            * 100
        )

        result["is_bottleneck"] = (
            result["delay_ratio"] >= 1.5
        )

        result["bottleneck_severity"] = (
            result.apply(
                self._calculate_severity,
                axis=1,
            )
        )

        numeric_columns = [
            "expected_duration",
            "duration_difference",
            "delay_ratio",
            "delay_percentage",
        ]

        result[numeric_columns] = result[
            numeric_columns
        ].round(2)

        result = result.sort_values(
            by="delay_percentage",
            ascending=False,
        )

        return result.reset_index(drop=True)

    def _validate_columns(self):
        required_columns = {
            self.step_column,
            self.average_duration_column,
        }

        missing_columns = (
            required_columns
            - set(self.analytics_dataframe.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )

            raise BottleneckDetectionError(
                f"Missing required column(s): {missing}"
            )

    def _build_expected_duration_map(self):
        expected_durations = {}

        for step in self.workflow_steps:
            if step.expected_duration is None:
                continue

            expected_durations[
                step.name
            ] = float(step.expected_duration)

        return expected_durations

    @staticmethod
    def _calculate_severity(row):
        if row["delay_ratio"] >= 3:
            return "CRITICAL"

        if row["delay_ratio"] >= 2:
            return "HIGH"

        if row["delay_ratio"] >= 1.5:
            return "MEDIUM"

        return "NORMAL"