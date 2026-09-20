from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.datasets.models import Dataset
from apps.organizations.models import Organization
from apps.simulations.models import Simulation
from apps.workflows.models import Workflow

from .models import Report
from .services.generator import (
    ReportGenerationError,
    ReportGenerationService,
)


User = get_user_model()


class ReportModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportuser",
            email="reportuser@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Report Test Organization",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Report Test Workflow",
            created_by=self.user,
        )

    def test_create_report(self):
        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            created_by=self.user,
            title="Workflow Summary",
            description="Test workflow report.",
            report_type=Report.ReportType.WORKFLOW_SUMMARY,
            status=Report.Status.DRAFT,
            output_format=Report.Format.HTML,
            content="Test report content.",
            data={
                "event_count": 100,
                "avg_duration": 12.5,
            },
        )

        self.assertEqual(report.title, "Workflow Summary")
        self.assertEqual(report.organization, self.organization)
        self.assertEqual(report.workflow, self.workflow)
        self.assertEqual(report.created_by, self.user)
        self.assertEqual(report.status, Report.Status.DRAFT)
        self.assertEqual(report.output_format, Report.Format.HTML)
        self.assertEqual(report.data["event_count"], 100)

    def test_report_can_exist_without_workflow(self):
        report = Report.objects.create(
            organization=self.organization,
            created_by=self.user,
            title="Organization Report",
            report_type=Report.ReportType.ANALYTICS,
        )

        self.assertIsNone(report.workflow)

    def test_report_can_reference_dataset(self):
        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            uploaded_by=self.user,
            name="Test Dataset",
        )

        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            dataset=dataset,
            created_by=self.user,
            title="Dataset Report",
            report_type=Report.ReportType.ANALYTICS,
        )

        self.assertEqual(report.dataset, dataset)

    def test_default_values(self):
        report = Report.objects.create(
            organization=self.organization,
            title="Default Report",
        )

        self.assertEqual(
            report.report_type,
            Report.ReportType.WORKFLOW_SUMMARY,
        )

        self.assertEqual(
            report.status,
            Report.Status.DRAFT,
        )

        self.assertEqual(
            report.output_format,
            Report.Format.HTML,
        )

        self.assertEqual(report.content, "")
        self.assertEqual(report.error_message, "")
        self.assertEqual(report.data, {})

    def test_report_string_representation(self):
        report = Report.objects.create(
            organization=self.organization,
            title="My Test Report",
        )

        self.assertEqual(str(report), "My Test Report")

    def test_report_ordering(self):
        first = Report.objects.create(
            organization=self.organization,
            title="First Report",
        )

        second = Report.objects.create(
            organization=self.organization,
            title="Second Report",
        )

        reports = list(Report.objects.all())

        self.assertEqual(reports[0], second)
        self.assertEqual(reports[1], first)

    def test_report_type_choices(self):
        valid_types = {
            choice[0]
            for choice in Report.ReportType.choices
        }

        self.assertIn(
            Report.ReportType.WORKFLOW_SUMMARY,
            valid_types,
        )

        self.assertIn(
            Report.ReportType.ANALYTICS,
            valid_types,
        )

        self.assertIn(
            Report.ReportType.SIMULATION,
            valid_types,
        )

        self.assertIn(
            Report.ReportType.AI_INSIGHT,
            valid_types,
        )

    def test_report_status_choices(self):
        valid_statuses = {
            choice[0]
            for choice in Report.Status.choices
        }

        self.assertEqual(
            valid_statuses,
            {
                "DRAFT",
                "GENERATING",
                "COMPLETED",
                "FAILED",
            },
        )

    def test_report_format_choices(self):
        valid_formats = {
            choice[0]
            for choice in Report.Format.choices
        }

        self.assertEqual(
            valid_formats,
            {
                "HTML",
                "JSON",
                "PDF",
                "CSV",
            },
        )


class ReportGenerationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="generatoruser",
            email="generator@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Generator Organization",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            description="Order processing workflow.",
            created_by=self.user,
        )

        self.workflow.steps.create(
            name="Order Received",
            description="Receive order.",
            order=1,
            expected_duration=2,
        )

        self.workflow.steps.create(
            name="Verification",
            description="Verify order.",
            order=2,
            expected_duration=5,
        )

    def test_workflow_summary_report_is_generated(self):
        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            created_by=self.user,
            title="Workflow Summary",
            report_type=Report.ReportType.WORKFLOW_SUMMARY,
        )

        result = ReportGenerationService.generate(report)
        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Report.Status.COMPLETED,
        )

        self.assertIn(
            "Order Fulfillment",
            result.content,
        )

        self.assertEqual(
            result.data["step_count"],
            2,
        )

        self.assertEqual(
            len(result.data["steps"]),
            2,
        )

    def test_workflow_summary_requires_workflow(self):
        report = Report.objects.create(
            organization=self.organization,
            created_by=self.user,
            title="Missing Workflow",
            report_type=Report.ReportType.WORKFLOW_SUMMARY,
        )

        with self.assertRaises(ReportGenerationError):
            ReportGenerationService.generate(report)

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            Report.Status.FAILED,
        )

        self.assertIn(
            "require a workflow",
            report.error_message,
        )

    def test_analytics_report_is_generated_from_dataset(self):
        csv_content = (
            "Order ID,Step Name,Duration (Minutes),Status\n"
            "ORD-001,Verification,10,completed\n"
            "ORD-001,Verification,20,completed\n"
            "ORD-001,Packing,8,completed\n"
            "ORD-002,Packing,12,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "orders.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            uploaded_by=self.user,
            name="Analytics Dataset",
            file=uploaded_file,
        )

        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            dataset=dataset,
            created_by=self.user,
            title="Analytics Report",
            report_type=Report.ReportType.ANALYTICS,
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"
            file_path.write_bytes(
                csv_content.encode("utf-8")
            )

            with patch.object(
                type(dataset.file),
                "path",
                new_callable=lambda: property(
                    lambda self: str(file_path)
                ),
            ):
                result = ReportGenerationService.generate(
                    report
                )

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Report.Status.COMPLETED,
        )

        self.assertEqual(
            result.data["dataset"]["name"],
            "Analytics Dataset",
        )

        analytics = result.data[
            "duration_analytics"
        ]

        self.assertEqual(
            len(analytics),
            2,
        )

        verification = next(
            row
            for row in analytics
            if row["step_name"] == "Verification"
        )

        self.assertEqual(
            verification["event_count"],
            2,
        )

        self.assertEqual(
            verification["average_duration"],
            15.0,
        )

        self.assertIn(
            "Analytics Report",
            result.content,
        )

    def test_analytics_report_requires_dataset(self):
        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            created_by=self.user,
            title="Missing Dataset",
            report_type=Report.ReportType.ANALYTICS,
        )

        with self.assertRaises(ReportGenerationError):
            ReportGenerationService.generate(report)

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            Report.Status.FAILED,
        )

        self.assertIn(
            "require a dataset",
            report.error_message,
        )

    def test_simulation_report_uses_latest_completed_simulation(
        self,
    ):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="20 Percent Workload",
            workload_change_percent=20,
            baseline_event_count=100,
            projected_event_count=120,
            baseline_avg_duration=10,
            projected_avg_duration=10,
            baseline_total_duration=1000,
            projected_total_duration=1200,
            status=Simulation.Status.COMPLETED,
            results={
                "workload_factor": 1.2,
            },
        )

        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            created_by=self.user,
            title="Simulation Report",
            report_type=Report.ReportType.SIMULATION,
        )

        result = ReportGenerationService.generate(report)
        result.refresh_from_db()

        self.assertEqual(
            result.status,
            Report.Status.COMPLETED,
        )

        self.assertEqual(
            result.data["simulation"]["id"],
            simulation.id,
        )

        self.assertEqual(
            result.data["simulation"][
                "projected_event_count"
            ],
            120,
        )

        self.assertIn(
            "20.0%",
            result.content,
        )

    def test_simulation_report_requires_completed_simulation(
        self,
    ):
        report = Report.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            created_by=self.user,
            title="Missing Simulation",
            report_type=Report.ReportType.SIMULATION,
        )

        with self.assertRaises(ReportGenerationError):
            ReportGenerationService.generate(report)

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            Report.Status.FAILED,
        )

        self.assertIn(
            "No completed simulation",
            report.error_message,
        )

    def test_unsupported_report_type_fails(self):
        report = Report.objects.create(
            organization=self.organization,
            created_by=self.user,
            title="Unsupported Report",
            report_type=Report.ReportType.BOTTLENECK,
        )

        with self.assertRaises(ReportGenerationError):
            ReportGenerationService.generate(report)

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            Report.Status.FAILED,
        )

        self.assertIn(
            "Unsupported report type",
            report.error_message,
        )

        def test_cross_organization_workflow_is_rejected(self):
            other_organization = Organization.objects.create(
            name="Other Workflow Organization",
            slug="other-workflow-organization",
        )

            other_workflow = Workflow.objects.create(
                organization=other_organization,
                name="Other Workflow",
                created_by=self.user,
            )

            report = Report.objects.create(
                organization=self.organization,
                workflow=other_workflow,
                created_by=self.user,
                title="Cross Organization Report",
                report_type=Report.ReportType.WORKFLOW_SUMMARY,
            )

            with self.assertRaises(ReportGenerationError):
                ReportGenerationService.generate(report)

            report.refresh_from_db()

            self.assertEqual(
                report.status,
                Report.Status.FAILED,
            )

        def test_cross_organization_dataset_is_rejected(self):
            other_organization = Organization.objects.create(
                name="Other Dataset Organization",
                slug="other-dataset-organization",
            )

            other_workflow = Workflow.objects.create(
                organization=other_organization,
                name="Other Workflow",
                created_by=self.user,
            )

            dataset = Dataset.objects.create(
                organization=other_organization,
                workflow=other_workflow,
                uploaded_by=self.user,
                name="Other Dataset",
            )

            report = Report.objects.create(
                organization=self.organization,
                workflow=self.workflow,
                dataset=dataset,
                created_by=self.user,
                title="Cross Organization Dataset",
                report_type=Report.ReportType.ANALYTICS,
            )

            with self.assertRaises(ReportGenerationError):
                ReportGenerationService.generate(report)

            report.refresh_from_db()

            self.assertEqual(
                report.status,
                Report.Status.FAILED,
            )