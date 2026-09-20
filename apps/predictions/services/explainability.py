import pandas as pd
import shap


class ExplainabilityError(Exception):
    """Raised when model explainability cannot be generated."""


class PredictionExplainability:

    def __init__(self, model):
        self.model = model

    def explain(self, dataframe):
        if not self.model.is_trained:
            raise ExplainabilityError(
                "Model must be trained before explanations can be generated."
            )

        if not isinstance(dataframe, pd.DataFrame):
            raise ExplainabilityError(
                "Input data must be a pandas DataFrame."
            )

        missing_columns = [
            column
            for column in self.model.feature_columns
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise ExplainabilityError(
                "Missing feature columns: "
                + ", ".join(missing_columns)
            )

        features = dataframe[
            self.model.feature_columns
        ].copy()

        for column in self.model.feature_columns:
            features[column] = pd.to_numeric(
                features[column],
                errors="coerce",
            )

        if features.isnull().any().any():
            raise ExplainabilityError(
                "Feature data contains invalid or missing values."
            )

        try:
            explainer = shap.TreeExplainer(
                self.model.model
            )

            shap_values = explainer.shap_values(
                features
            )

        except Exception as exc:
            raise ExplainabilityError(
                f"Unable to generate SHAP explanation: {exc}"
            ) from exc

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        shap_values = pd.DataFrame(
            shap_values,
            columns=self.model.feature_columns,
            index=features.index,
        )

        return {
            "features": features,
            "shap_values": shap_values,
            "feature_importance": self._feature_importance(
                shap_values
            ),
        }

    def _feature_importance(self, shap_values):
        importance = (
            shap_values.abs()
            .mean()
            .sort_values(
                ascending=False
            )
            .reset_index()
        )

        importance.columns = [
            "feature",
            "mean_absolute_shap",
        ]

        importance[
            "mean_absolute_shap"
        ] = importance[
            "mean_absolute_shap"
        ].round(6)

        return importance