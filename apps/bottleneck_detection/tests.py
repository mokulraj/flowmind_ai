import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.datasets.models import Dataset
from apps.organizations.models import Organization
from apps.workflows.models import (
    Workflow,
    WorkflowStep,
)

from .services.detector import (
    BottleneckDetectionError,
    BottleneckDetector,
)
from .services.pipeline import BottleneckPipeline


User = get_user_model()


class BottleneckDetectorTests(TestCase):

    def test_bottleneck_is_detected(self):
        analytics = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "average_duration": 12.0,
                },
                {
                    "step_name": "Packing",
                    "average_duration": 8.0,
                },
            ]
        )

        verification = WorkflowStep(
            name="Verification",
            expected_duration=5,
        )

        packing = WorkflowStep(
            name="Packing",
            expected_duration=8,
        )

        result = BottleneckDetector(
            analytics_dataframe=analytics,
            workflow_steps=[
                verification,
                packing,
            ],
        ).detect()

        verification_result = result[
            result["step_name"] == "Verification"
        ].iloc[0]

        self.assertEqual(
            verification_result["expected_duration"],
            5.0,
        )

        self.assertEqual(
            verification_result["duration_difference"],
            7.0,
        )

        self.assertEqual(
            verification_result["delay_ratio"],
            2.4,
        )

        self.assertEqual(
            verification_result["delay_percentage"],
            140.0,
        )

        self.assertTrue(
            verification_result["is_bottleneck"]
        )

        self.assertEqual(
            verification_result["bottleneck_severity"],
            "HIGH",
        )

    def test_normal_step_is_not_bottleneck(self):
        analytics = pd.DataFrame(
            [
                {
                    "step_name": "Packing",
                    "average_duration": 8.0,
                },
            ]
        )

        packing = WorkflowStep(
            name="Packing",
            expected_duration=8,
        )

        result = BottleneckDetector(
            analytics_dataframe=analytics,
            workflow_steps=[packing],
        ).detect()

        row = result.iloc[0]

        self.assertFalse(
            row["is_bottleneck"]
        )

        self.assertEqual(
            row["bottleneck_severity"],
            "NORMAL",
        )

    def test_critical_bottleneck(self):
        analytics = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "average_duration": 20.0,
                },
            ]
        )

        verification = WorkflowStep(
            name="Verification",
            expected_duration=5,
        )

        result = BottleneckDetector(
            analytics_dataframe=analytics,
            workflow_steps=[verification],
        ).detect()

        row = result.iloc[0]

        self.assertTrue(
            row["is_bottleneck"]
        )

        self.assertEqual(
            row["bottleneck_severity"],
            "CRITICAL",
        )

    def test_missing_analytics_column_is_rejected(self):
        analytics = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                },
            ]
        )

        verification = WorkflowStep(
            name="Verification",
            expected_duration=5,
        )

        with self.assertRaises(
            BottleneckDetectionError
        ):
            BottleneckDetector(
                analytics_dataframe=analytics,
                workflow_steps=[verification],
            ).detect()

    def test_unmatched_steps_are_rejected(self):
        analytics = pd.DataFrame(
            [
                {
                    "step_name": "Unknown Step",
                    "average_duration": 10,
                },
            ]
        )

        verification = WorkflowStep(
            name="Verification",
            expected_duration=5,
        )

        with self.assertRaises(
            BottleneckDetectionError
        ):
            BottleneckDetector(
                analytics_dataframe=analytics,
                workflow_steps=[verification],
            ).detect()


class BottleneckPipelineTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="bottleneck_test_user",
            email="bottleneck@test.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Bottleneck Test Organization",
            slug="bottleneck-test-organization",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
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
            "ORD-001,Verification,12,completed\n"
            "ORD-001,Packing,8,completed\n"
            "ORD-002,Order Received,2,completed\n"
            "ORD-002,Verification,10,completed\n"
            "ORD-002,Packing,9,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "order_fulfillment.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Order Fulfillment Test Dataset",
            file=uploaded_file,
            uploaded_by=self.user,
        )

        return dataset

    def test_pipeline_returns_bottleneck_results(self):
        dataset = self._create_dataset()

        result = BottleneckPipeline(
            dataset=dataset
        ).run()

        self.assertIn(
            "preprocessing",
            result,
        )

        self.assertIn(
            "duration_analytics",
            result,
        )

        self.assertIn(
            "bottlenecks",
            result,
        )

        bottlenecks = result["bottlenecks"]

        self.assertFalse(
            bottlenecks.empty
        )

        verification = bottlenecks[
            bottlenecks["step_name"] == "Verification"
        ].iloc[0]

        self.assertTrue(
            verification["is_bottleneck"]
        )

        self.assertEqual(
            verification["expected_duration"],
            5.0,
        )

        self.assertEqual(
            verification["bottleneck_severity"],
            "HIGH",
        )

    def tearDown(self):
        for dataset in Dataset.objects.all():
            if dataset.file:
                try:
                    file_path = dataset.file.path

                    if os.path.exists(file_path):
                        os.remove(file_path)

                except (ValueError, FileNotFoundError):
                    pass