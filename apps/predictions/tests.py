import pandas as pd
from django.test import SimpleTestCase

from .services.regressor import (
    DurationPredictionModel,
    PredictionError,
)


class DurationPredictionModelTests(
    SimpleTestCase
):

    def _training_data(self):
        return pd.DataFrame(
            [
                {
                    "workload": 10,
                    "queue_length": 1,
                    "previous_duration": 5,
                    "duration_minutes": 6,
                },
                {
                    "workload": 20,
                    "queue_length": 2,
                    "previous_duration": 6,
                    "duration_minutes": 8,
                },
                {
                    "workload": 30,
                    "queue_length": 3,
                    "previous_duration": 8,
                    "duration_minutes": 11,
                },
                {
                    "workload": 40,
                    "queue_length": 4,
                    "previous_duration": 11,
                    "duration_minutes": 14,
                },
                {
                    "workload": 50,
                    "queue_length": 5,
                    "previous_duration": 14,
                    "duration_minutes": 17,
                },
                {
                    "workload": 60,
                    "queue_length": 6,
                    "previous_duration": 17,
                    "duration_minutes": 20,
                },
            ]
        )

    def test_model_trains_successfully(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
                "queue_length",
                "previous_duration",
            ]
        )

        result = model.train(
            self._training_data()
        )

        self.assertEqual(
            result["training_rows"],
            6,
        )

        self.assertTrue(
            model.is_trained
        )

    def test_model_predicts_duration(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
                "queue_length",
                "previous_duration",
            ]
        )

        model.train(
            self._training_data()
        )

        prediction_data = pd.DataFrame(
            [
                {
                    "workload": 35,
                    "queue_length": 3,
                    "previous_duration": 9,
                },
            ]
        )

        result = model.predict(
            prediction_data
        )

        self.assertIn(
            "predicted_duration_minutes",
            result.columns,
        )

        self.assertEqual(
            len(result),
            1,
        )

        self.assertGreater(
            result.iloc[0][
                "predicted_duration_minutes"
            ],
            0,
        )

    def test_prediction_requires_training(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
            ]
        )

        prediction_data = pd.DataFrame(
            [
                {
                    "workload": 20,
                },
            ]
        )

        with self.assertRaises(
            PredictionError
        ):
            model.predict(
                prediction_data
            )

    def test_missing_columns_are_rejected(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
                "queue_length",
            ]
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 10,
                    "duration_minutes": 5,
                },
            ]
        )

        with self.assertRaises(
            PredictionError
        ):
            model.train(
                dataframe
            )

    def test_insufficient_training_data_is_rejected(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
            ]
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 10,
                    "duration_minutes": 5,
                },
            ]
        )

        with self.assertRaises(
            PredictionError
        ):
            model.train(
                dataframe
            )

    def test_invalid_training_rows_are_removed(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
            ]
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 10,
                    "duration_minutes": 5,
                },
                {
                    "workload": 20,
                    "duration_minutes": "invalid",
                },
                {
                    "workload": 30,
                    "duration_minutes": -5,
                },
                {
                    "workload": 40,
                    "duration_minutes": 10,
                },
            ]
        )

        result = model.train(
            dataframe
        )

        self.assertEqual(
            result["training_rows"],
            2,
        )

    def test_invalid_prediction_features_are_rejected(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
            ]
        )

        training_data = pd.DataFrame(
            [
                {
                    "workload": 10,
                    "duration_minutes": 5,
                },
                {
                    "workload": 20,
                    "duration_minutes": 8,
                },
            ]
        )

        model.train(
            training_data
        )

        prediction_data = pd.DataFrame(
            [
                {
                    "workload": "invalid",
                },
            ]
        )

        with self.assertRaises(
            PredictionError
        ):
            model.predict(
                prediction_data
            )