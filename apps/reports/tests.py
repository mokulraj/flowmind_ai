from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.organizations.models import Organization
from apps.workflows.models import Workflow

from .models import Report


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