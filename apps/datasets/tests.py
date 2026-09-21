from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, SimpleTestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.organizations.models import (
    Organization,
    OrganizationMember,
)
from apps.workflows.models import Workflow

from .models import Dataset
from .services.dataset_service import DatasetService
from .services.validator import (
    DatasetValidationError,
    DatasetValidator,
)


class DatasetValidatorTests(SimpleTestCase):

    def test_valid_csv_is_analyzed(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                    "status": "completed",
                },
                {
                    "order_id": "ORD-002",
                    "step_name": "Packing",
                    "duration_minutes": 8.0,
                    "status": "completed",
                },
                {
                    "order_id": "ORD-003",
                    "step_name": "Shipping",
                    "duration_minutes": 10.0,
                    "status": "completed",
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["column_count"], 4)
        self.assertEqual(result["missing_cells"], 0)
        self.assertEqual(result["duplicate_rows"], 0)
        self.assertEqual(result["quality_score"], 100.0)

    def test_missing_values_are_detected(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
                {
                    "order_id": "ORD-002",
                    "step_name": None,
                    "duration_minutes": 8.0,
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["column_count"], 3)
        self.assertEqual(result["missing_cells"], 1)
        self.assertLess(result["quality_score"], 100.0)

    def test_duplicate_rows_are_detected(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["duplicate_rows"], 1)

    def test_unsupported_file_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.txt"
            file_path.write_text("hello")

            with self.assertRaises(DatasetValidationError):
                DatasetValidator(file_path).validate()


class DatasetServiceAuditTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="datasetuser",
            email="dataset@example.com",
            password="TestPassword123!",
        )

        self.organization = Organization.objects.create(
            name="Dataset Operations",
            slug="dataset-operations",
            industry="Logistics",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ANALYST,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

    def create_dataset(self, filename="orders.csv"):
        file_content = (
            b"order_id,step_name,duration_minutes,status\n"
            b"ORD-001,Verification,12.5,completed\n"
            b"ORD-002,Packing,8.0,completed\n"
            b"ORD-003,Shipping,10.0,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            filename,
            file_content,
            content_type="text/csv",
        )

        return Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Orders Dataset",
            description="Dataset audit test.",
            file=uploaded_file,
            uploaded_by=self.user,
        )

    def test_dataset_validation_creates_audit_log(self):
        dataset = self.create_dataset()

        DatasetService.validate_dataset(dataset)

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            object_type="Dataset",
            object_id=dataset.id,
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.RUN,
        )

        self.assertEqual(
            audit_log.object_repr,
            str(dataset),
        )

        self.assertEqual(
            audit_log.description,
            "Validated dataset 'Orders Dataset' successfully.",
        )

    def test_dataset_validation_audit_log_uses_dataset_organization(self):
        dataset = self.create_dataset()

        DatasetService.validate_dataset(dataset)

        audit_log = AuditLog.objects.get(
            object_type="Dataset",
            object_id=dataset.id,
        )

        self.assertEqual(
            audit_log.organization_id,
            dataset.organization_id,
        )

        self.assertEqual(
            audit_log.user,
            dataset.uploaded_by,
        )

    def test_dataset_validation_audit_log_contains_validation_metadata(self):
        dataset = self.create_dataset()

        DatasetService.validate_dataset(dataset)

        audit_log = AuditLog.objects.get(
            object_type="Dataset",
            object_id=dataset.id,
        )

        self.assertEqual(
            audit_log.metadata["dataset_id"],
            dataset.id,
        )

        self.assertEqual(
            audit_log.metadata["dataset_name"],
            dataset.name,
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            dataset.workflow_id,
        )

        self.assertEqual(
            audit_log.metadata["row_count"],
            3,
        )

        self.assertEqual(
            audit_log.metadata["column_count"],
            4,
        )

        self.assertEqual(
            audit_log.metadata["missing_cells"],
            0,
        )

        self.assertEqual(
            audit_log.metadata["duplicate_rows"],
            0,
        )

        self.assertEqual(
            audit_log.metadata["quality_score"],
            100.0,
        )

        self.assertEqual(
            audit_log.metadata["status"],
            Dataset.Status.VALIDATED,
        )

    def test_failed_dataset_validation_creates_audit_log(self):
        uploaded_file = SimpleUploadedFile(
            "orders.txt",
            b"invalid dataset format",
            content_type="text/plain",
        )

        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Invalid Dataset",
            description="Invalid dataset audit test.",
            file=uploaded_file,
            uploaded_by=self.user,
        )

        with self.assertRaises(Exception):
            DatasetService.validate_dataset(dataset)

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            object_type="Dataset",
            object_id=dataset.id,
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.RUN,
        )

        self.assertEqual(
            audit_log.metadata["dataset_id"],
            dataset.id,
        )

        self.assertEqual(
            audit_log.metadata["dataset_name"],
            dataset.name,
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            dataset.workflow_id,
        )

        self.assertEqual(
            audit_log.metadata["status"],
            Dataset.Status.FAILED,
        )