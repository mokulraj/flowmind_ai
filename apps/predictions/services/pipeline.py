from apps.preprocessing.services.dataset_preprocessing import (
    DatasetPreprocessingService,
)

from .explainability import (
    PredictionExplainability,
)
from .regressor import (
    DurationPredictionModel,
    PredictionError,
)


class PredictionPipeline:

    def __init__(self, dataset):
        self.dataset = dataset

    def run(self):
        preprocessing_result = (
            DatasetPreprocessingService(
                dataset=self.dataset
            ).process()
        )

        dataframe = preprocessing_result[
            "dataframe"
        ]

        feature_dataframe = self._prepare_features(
            dataframe
        )

        model = DurationPredictionModel(
            feature_columns=[
                "step_order",
            ]
        )

        training_result = model.train(
            feature_dataframe
        )

        predictions = model.predict(
            feature_dataframe[
                [
                    "step_order",
                ]
            ]
        )

        explainability = PredictionExplainability(
            model=model
        ).explain(
            feature_dataframe[
                [
                    "step_order",
                ]
            ]
        )

        return {
            "preprocessing": preprocessing_result,
            "training": training_result,
            "predictions": predictions,
            "explainability": explainability,
        }

    def _prepare_features(self, dataframe):
        required_columns = [
            "step_name",
            "duration_minutes",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in dataframe.columns
        ]

        if missing_columns:
            raise PredictionError(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

        workflow_steps = (
            self.dataset.workflow.steps
            .all()
            .order_by("order")
        )

        step_order_map = {
            step.name: index
            for index, step in enumerate(
                workflow_steps,
                start=1,
            )
        }

        result = dataframe.copy()

        result["step_order"] = (
            result["step_name"]
            .map(step_order_map)
        )

        result["duration_minutes"] = (
            result["duration_minutes"]
            .pipe(
                lambda series:
                __import__(
                    "pandas"
                ).to_numeric(
                    series,
                    errors="coerce",
                )
            )
        )

        result = result.dropna(
            subset=[
                "step_order",
                "duration_minutes",
            ]
        )

        result = result[
            result["duration_minutes"] >= 0
        ]

        if len(result) < 2:
            raise PredictionError(
                "At least two valid rows are required "
                "for prediction."
            )

        return result.reset_index(
            drop=True
        )