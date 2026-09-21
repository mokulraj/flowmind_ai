import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import TestCase, SimpleTestCase

from apps.datasets.models import Dataset
from apps.organizations.models import (
    Organization,
    OrganizationMember,
)
from apps.workflows.models import (
    Workflow,
    WorkflowStep,
)

from .services.pipeline import PredictionPipeline
from .services.regressor import (
    DurationPredictionModel,
    PredictionError,
)
from .services.explainability import (
    ExplainabilityError,
    PredictionExplainability,
)


User = get_user_model()


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

    def test_feature_importance_requires_training(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
                "queue_length",
            ]
        )

        with self.assertRaises(
            PredictionError
        ):
            model.get_feature_importance()

    def test_feature_importance_is_returned(self):
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

        result = model.get_feature_importance()

        self.assertEqual(
            len(result),
            3,
        )

        self.assertIn(
            "feature",
            result.columns,
        )

        self.assertIn(
            "importance",
            result.columns,
        )

        self.assertEqual(
            set(result["feature"]),
            {
                "workload",
                "queue_length",
                "previous_duration",
            },
        )

        self.assertTrue(
            (
                result["importance"] >= 0
            ).all()
        )

        self.assertAlmostEqual(
            result["importance"].sum(),
            1.0,
            places=4,
        )


class PredictionExplainabilityTests(
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

    def _trained_model(self):
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

        return model

    def test_explanation_requires_trained_model(self):
        model = DurationPredictionModel(
            feature_columns=[
                "workload",
                "queue_length",
                "previous_duration",
            ]
        )

        explainer = PredictionExplainability(
            model
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 35,
                    "queue_length": 3,
                    "previous_duration": 9,
                }
            ]
        )

        with self.assertRaises(
            ExplainabilityError
        ):
            explainer.explain(
                dataframe
            )

    def test_shap_explanation_is_generated(self):
        model = self._trained_model()

        explainer = PredictionExplainability(
            model
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 35,
                    "queue_length": 3,
                    "previous_duration": 9,
                },
                {
                    "workload": 45,
                    "queue_length": 4,
                    "previous_duration": 12,
                },
            ]
        )

        result = explainer.explain(
            dataframe
        )

        self.assertIn(
            "features",
            result,
        )

        self.assertIn(
            "shap_values",
            result,
        )

        self.assertIn(
            "feature_importance",
            result,
        )

        self.assertEqual(
            result["features"].shape,
            (2, 3),
        )

        self.assertEqual(
            result["shap_values"].shape,
            (2, 3),
        )

        self.assertEqual(
            list(
                result["shap_values"].columns
            ),
            [
                "workload",
                "queue_length",
                "previous_duration",
            ],
        )

        self.assertEqual(
            len(
                result["feature_importance"]
            ),
            3,
        )

        self.assertIn(
            "feature",
            result["feature_importance"].columns,
        )

        self.assertIn(
            "mean_absolute_shap",
            result["feature_importance"].columns,
        )

    def test_shap_explanation_rejects_missing_features(
        self
    ):
        model = self._trained_model()

        explainer = PredictionExplainability(
            model
        )

        dataframe = pd.DataFrame(
            [
                {
                    "workload": 35,
                    "queue_length": 3,
                }
            ]
        )

        with self.assertRaises(
            ExplainabilityError
        ):
            explainer.explain(
                dataframe
            )


class PredictionPipelineTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="prediction_test_user",
            email="prediction@test.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Prediction Test Organization",
            slug="prediction-test-organization",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ANALYST,
        )

        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Order Received",
            order=1,
            expected_duration=2,
        )

        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Verification",
            order=2,
            expected_duration=5,
        )

        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Packing",
            order=3,
            expected_duration=8,
        )

    def _create_dataset(self):
        csv_content = (
            "order_id,step_name,duration_minutes,status\n"
            "ORD-001,Order Received,2,completed\n"
            "ORD-001,Verification,5,completed\n"
            "ORD-001,Packing,8,completed\n"
            "ORD-002,Order Received,3,completed\n"
            "ORD-002,Verification,6,completed\n"
            "ORD-002,Packing,9,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "prediction_test.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        return Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Prediction Test Dataset",
            file=uploaded_file,
            uploaded_by=self.user,
        )

    def test_prediction_pipeline_returns_predictions(
        self
    ):
        dataset = self._create_dataset()

        result = PredictionPipeline(
            dataset=dataset
        ).run()

        self.assertIn(
            "preprocessing",
            result,
        )

        self.assertIn(
            "training",
            result,
        )

        self.assertIn(
            "predictions",
            result,
        )

        self.assertIn(
            "explainability",
            result,
        )

        predictions = result[
            "predictions"
        ]

        explainability = result[
            "explainability"
        ]

        self.assertFalse(
            predictions.empty
        )

        self.assertIn(
            "predicted_duration_minutes",
            predictions.columns,
        )

        self.assertEqual(
            len(predictions),
            6,
        )

        self.assertTrue(
            (
                predictions[
                    "predicted_duration_minutes"
                ]
                > 0
            ).all()
        )

        self.assertIn(
            "features",
            explainability,
        )

        self.assertIn(
            "shap_values",
            explainability,
        )

        self.assertIn(
            "feature_importance",
            explainability,
        )

        self.assertEqual(
            len(
                explainability[
                    "features"
                ]
            ),
            6,
        )

        self.assertEqual(
            len(
                explainability[
                    "shap_values"
                ]
            ),
            6,
        )

        self.assertEqual(
            list(
                explainability[
                    "shap_values"
                ].columns
            ),
            [
                "step_order",
            ],
        )

    def test_pipeline_rejects_dataset_without_step_name(
        self
    ):
        csv_content = (
            "order_id,duration_minutes,status\n"
            "ORD-001,5,completed\n"
            "ORD-002,6,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "invalid_prediction.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Invalid Prediction Dataset",
            file=uploaded_file,
            uploaded_by=self.user,
        )

        with self.assertRaises(
            PredictionError
        ):
            PredictionPipeline(
                dataset=dataset
            ).run()

    def tearDown(self):
        for dataset in Dataset.objects.all():
            if dataset.file:
                try:
                    file_path = dataset.file.path

                    if os.path.exists(file_path):
                        os.remove(file_path)

                except (
                    ValueError,
                    FileNotFoundError,
                ):
                    pass
