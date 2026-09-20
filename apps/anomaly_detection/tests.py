import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, SimpleTestCase

from apps.datasets.models import Dataset
from apps.organizations.models import Organization
from apps.workflows.models import Workflow

from .services.detector import (
    AnomalyDetectionError,
    AnomalyDetector,
)
from .services.pipeline import AnomalyPipeline


User = get_user_model()


class AnomalyDetectorTests(SimpleTestCase):

    def test_anomaly_is_detected(self):
        dataframe = pd.DataFrame(
            [
                {"duration_minutes": 5.0},
                {"duration_minutes": 5.2},
                {"duration_minutes": 5.5},
                {"duration_minutes": 5.1},
                {"duration_minutes": 5.3},
                {"duration_minutes": 31.0},
            ]
        )

        result = AnomalyDetector(
            dataframe=dataframe,
            contamination=0.2,
        ).detect()

        anomaly_rows = result[
            result["is_anomaly"]
        ]

        self.assertGreaterEqual(
            len(anomaly_rows),
            1,
        )

        self.assertTrue(
            (
                anomaly_rows["duration_minutes"]
                == 31.0
            ).any()
        )

    def test_normal_data_is_processed(self):
        dataframe = pd.DataFrame(
            [
                {"duration_minutes": 5.0},
                {"duration_minutes": 5.1},
                {"duration_minutes": 5.2},
                {"duration_minutes": 5.3},
                {"duration_minutes": 5.4},
                {"duration_minutes": 5.5},
            ]
        )

        result = AnomalyDetector(
            dataframe=dataframe,
            contamination=0.2,
        ).detect()

        self.assertEqual(
            len(result),
            6,
        )

        self.assertIn(
            "anomaly_score",
            result.columns,
        )

        self.assertIn(
            "is_anomaly",
            result.columns,
        )

    def test_missing_duration_column_is_rejected(self):
        dataframe = pd.DataFrame(
            [
                {"step_name": "Verification"},
            ]
        )

        with self.assertRaises(
            AnomalyDetectionError
        ):
            AnomalyDetector(
                dataframe=dataframe,
            ).detect()

    def test_invalid_contamination_is_rejected(self):
        dataframe = pd.DataFrame(
            [
                {"duration_minutes": 5.0},
                {"duration_minutes": 6.0},
            ]
        )

        with self.assertRaises(
            AnomalyDetectionError
        ):
            AnomalyDetector(
                dataframe=dataframe,
                contamination=0.5,
            )

    def test_invalid_duration_values_are_removed(self):
        dataframe = pd.DataFrame(
            [
                {"duration_minutes": 5.0},
                {"duration_minutes": "invalid"},
                {"duration_minutes": -10.0},
                {"duration_minutes": 6.0},
            ]
        )

        result = AnomalyDetector(
            dataframe=dataframe,
            contamination=0.2,
        ).detect()

        self.assertEqual(
            len(result),
            2,
        )

        self.assertTrue(
            (result["duration_minutes"] >= 0).all()
        )

    def test_too_few_observations_are_rejected(self):
        dataframe = pd.DataFrame(
            [
                {"duration_minutes": 5.0},
            ]
        )

        with self.assertRaises(
            AnomalyDetectionError
        ):
            AnomalyDetector(
                dataframe=dataframe,
            ).detect()


class AnomalyPipelineTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="anomaly_test_user",
            email="anomaly@test.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Anomaly Test Organization",
            slug="anomaly-test-organization",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

    def _create_dataset(self):
        csv_content = (
            "order_id,step_name,duration_minutes,status\n"
            "ORD-001,Verification,5,completed\n"
            "ORD-002,Verification,5.2,completed\n"
            "ORD-003,Verification,5.1,completed\n"
            "ORD-004,Verification,5.4,completed\n"
            "ORD-005,Verification,5.3,completed\n"
            "ORD-006,Verification,31,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "anomaly_test.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Anomaly Test Dataset",
            file=uploaded_file,
            uploaded_by=self.user,
        )

        return dataset

    def test_pipeline_returns_anomaly_results(self):
        dataset = self._create_dataset()

        result = AnomalyPipeline(
            dataset=dataset,
            contamination=0.2,
        ).run()

        self.assertIn(
            "preprocessing",
            result,
        )

        self.assertIn(
            "anomalies",
            result,
        )

        anomalies = result["anomalies"]

        self.assertFalse(
            anomalies.empty
        )

        anomaly_rows = anomalies[
            anomalies["is_anomaly"]
        ]

        self.assertGreaterEqual(
            len(anomaly_rows),
            1,
        )

        self.assertTrue(
            (
                anomaly_rows["duration_minutes"]
                == 31.0
            ).any()
        )

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