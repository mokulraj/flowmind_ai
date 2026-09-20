import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetectionError(Exception):
    """Raised when anomaly detection cannot be completed."""


class AnomalyDetector:
    """
    Detects unusual duration observations using Isolation Forest.
    """

    def __init__(
        self,
        dataframe,
        duration_column="duration_minutes",
        contamination=0.05,
        random_state=42,
    ):
        if not isinstance(dataframe, pd.DataFrame):
            raise AnomalyDetectionError(
                "Anomaly detection input must be a pandas DataFrame."
            )

        if not 0 < contamination < 0.5:
            raise AnomalyDetectionError(
                "Contamination must be greater than 0 and less than 0.5."
            )

        self.dataframe = dataframe.copy()
        self.duration_column = duration_column
        self.contamination = contamination
        self.random_state = random_state

    def detect(self):
        self._validate_columns()

        result = self.dataframe.copy()

        result[self.duration_column] = pd.to_numeric(
            result[self.duration_column],
            errors="coerce",
        )

        result = result.dropna(
            subset=[self.duration_column]
        )

        result = result[
            result[self.duration_column] >= 0
        ].copy()

        if result.empty:
            raise AnomalyDetectionError(
                "No valid duration observations were found."
            )

        if len(result) < 2:
            raise AnomalyDetectionError(
                "At least two duration observations are required."
            )

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )

        values = result[
            [self.duration_column]
        ]

        predictions = model.fit_predict(values)

        scores = model.decision_function(values)

        result["anomaly_prediction"] = predictions
        result["anomaly_score"] = scores

        result["is_anomaly"] = (
            result["anomaly_prediction"] == -1
        )

        result["anomaly_severity"] = (
            result["is_anomaly"].map(
                {
                    True: "ANOMALY",
                    False: "NORMAL",
                }
            )
        )

        result["anomaly_score"] = result[
            "anomaly_score"
        ].round(4)

        result = result.sort_values(
            by="anomaly_score",
            ascending=True,
        )

        return result.reset_index(drop=True)

    def _validate_columns(self):
        if self.duration_column not in self.dataframe.columns:
            raise AnomalyDetectionError(
                f"Missing required column: "
                f"{self.duration_column}"
            )