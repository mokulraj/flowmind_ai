import pandas as pd
from sklearn.ensemble import RandomForestRegressor


class PredictionError(Exception):
    """Raised when prediction cannot be completed."""


class DurationPredictionModel:
    """
    Trains a regression model to predict workflow step duration.

    The initial implementation uses numeric input features and
    predicts duration in minutes.
    """

    def __init__(
        self,
        feature_columns,
        target_column="duration_minutes",
        random_state=42,
        n_estimators=100,
    ):
        if not feature_columns:
            raise PredictionError(
                "At least one feature column is required."
            )

        self.feature_columns = list(
            feature_columns
        )

        self.target_column = target_column
        self.random_state = random_state
        self.n_estimators = n_estimators

        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )

        self.is_trained = False

    def train(self, dataframe):
        self._validate_training_dataframe(
            dataframe
        )

        features = dataframe[
            self.feature_columns
        ].copy()

        target = dataframe[
            self.target_column
        ].copy()

        features = features.apply(
            pd.to_numeric,
            errors="coerce",
        )

        target = pd.to_numeric(
            target,
            errors="coerce",
        )

        valid_rows = (
            features.notna().all(axis=1)
            & target.notna()
            & (target >= 0)
        )

        features = features.loc[valid_rows]
        target = target.loc[valid_rows]

        if len(features) < 2:
            raise PredictionError(
                "At least two valid training observations are required."
            )

        self.model.fit(
            features,
            target,
        )

        self.is_trained = True

        return {
            "training_rows": len(features),
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
        }

    def predict(self, dataframe):
        if not self.is_trained:
            raise PredictionError(
                "The prediction model must be trained before prediction."
            )

        self._validate_prediction_dataframe(
            dataframe
        )

        features = dataframe[
            self.feature_columns
        ].copy()

        features = features.apply(
            pd.to_numeric,
            errors="coerce",
        )

        if features.isna().any().any():
            raise PredictionError(
                "Prediction features contain invalid or missing values."
            )

        predictions = self.model.predict(
            features
        )

        result = dataframe.copy()

        result["predicted_duration_minutes"] = (
            predictions.round(2)
        )

        return result

    def _validate_training_dataframe(
        self,
        dataframe,
    ):
        self._validate_dataframe_type(
            dataframe
        )

        required_columns = set(
            self.feature_columns
        )

        required_columns.add(
            self.target_column
        )

        self._raise_for_missing_columns(
            dataframe,
            required_columns,
        )

    def _validate_prediction_dataframe(
        self,
        dataframe,
    ):
        self._validate_dataframe_type(
            dataframe
        )

        required_columns = set(
            self.feature_columns
        )

        self._raise_for_missing_columns(
            dataframe,
            required_columns,
        )

    @staticmethod
    def _validate_dataframe_type(
        dataframe,
    ):
        if not isinstance(
            dataframe,
            pd.DataFrame,
        ):
            raise PredictionError(
                "Prediction input must be a pandas DataFrame."
            )

    @staticmethod
    def _raise_for_missing_columns(
        dataframe,
        required_columns,
    ):
        missing_columns = (
            required_columns
            - set(dataframe.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )

            raise PredictionError(
                f"Missing required column(s): {missing}"
            )