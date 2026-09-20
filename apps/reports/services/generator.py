from django.db import transaction

from apps.analytics.services.pipeline import AnalyticsPipeline
from apps.simulations.models import Simulation

from ..models import Report


class ReportGenerationError(Exception):
    """Raised when a report cannot be generated."""


class ReportGenerationService:
    """
    Generates reports from FlowMind workflow, dataset,
    analytics, and simulation data.
    """

    @staticmethod
    def _validate_report(report):
        if not isinstance(report, Report):
            raise ReportGenerationError(
                "A valid Report instance is required."
            )

        if not report.organization_id:
            raise ReportGenerationError(
                "Report must belong to an organization."
            )

    @staticmethod
    def _workflow_summary(report):
        if not report.workflow:
            raise ReportGenerationError(
                "Workflow Summary reports require a workflow."
            )

        if report.workflow.organization_id != report.organization_id:
            raise ReportGenerationError(
                "Workflow does not belong to the report organization."
            )

        workflow = report.workflow
        steps = workflow.steps.all().order_by("order")

        return {
            "report_type": Report.ReportType.WORKFLOW_SUMMARY,
            "workflow": {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
            },
            "step_count": steps.count(),
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "description": step.description,
                    "order": step.order,
                    "expected_duration": (
                        float(step.expected_duration)
                        if step.expected_duration is not None
                        else None
                    ),
                    "department": step.department,
                    "responsible_role": step.responsible_role,
                }
                for step in steps
            ],
        }

    @staticmethod
    def _analytics(report):
        if not report.workflow:
            raise ReportGenerationError(
                "Analytics reports require a workflow."
            )

        if not report.dataset:
            raise ReportGenerationError(
                "Analytics reports require a dataset."
            )

        if report.workflow.organization_id != report.organization_id:
            raise ReportGenerationError(
                "Workflow does not belong to the report organization."
            )

        if report.dataset.organization_id != report.organization_id:
            raise ReportGenerationError(
                "Dataset does not belong to the report organization."
            )

        if report.dataset.workflow_id != report.workflow_id:
            raise ReportGenerationError(
                "Dataset does not belong to the report workflow."
            )

        try:
            pipeline_result = AnalyticsPipeline(
                report.dataset
            ).run()
        except Exception as exc:
            raise ReportGenerationError(
                f"Analytics generation failed: {exc}"
            ) from exc

        analytics_dataframe = pipeline_result[
            "duration_analytics"
        ]

        analytics_rows = []

        for row in analytics_dataframe.to_dict(
            orient="records"
        ):
            converted_row = {}

            for key, value in row.items():
                if hasattr(value, "item"):
                    value = value.item()

                converted_row[key] = value

            analytics_rows.append(converted_row)

        preprocessing = pipeline_result["preprocessing"]

        return {
            "report_type": Report.ReportType.ANALYTICS,
            "workflow": {
                "id": report.workflow.id,
                "name": report.workflow.name,
            },
            "dataset": {
                "id": report.dataset.id,
                "name": report.dataset.name,
            },
            "preprocessing": {
                "original_rows": preprocessing.get(
                    "original_rows"
                ),
                "cleaned_rows": preprocessing.get(
                    "cleaned_rows"
                ),
            },
            "duration_analytics": analytics_rows,
        }

    @staticmethod
    def _simulation(report):
        if not report.workflow:
            raise ReportGenerationError(
                "Simulation reports require a workflow."
            )

        if report.workflow.organization_id != report.organization_id:
            raise ReportGenerationError(
                "Workflow does not belong to the report organization."
            )

        simulation = (
            Simulation.objects.filter(
                organization=report.organization,
                workflow=report.workflow,
                status=Simulation.Status.COMPLETED,
            )
            .order_by("-created_at")
            .first()
        )

        if simulation is None:
            raise ReportGenerationError(
                "No completed simulation exists for this workflow."
            )

        return {
            "report_type": Report.ReportType.SIMULATION,
            "workflow": {
                "id": report.workflow.id,
                "name": report.workflow.name,
            },
            "simulation": {
                "id": simulation.id,
                "name": simulation.name,
                "description": simulation.description,
                "workload_change_percent": (
                    float(simulation.workload_change_percent)
                    if simulation.workload_change_percent is not None
                    else None
                ),
                "baseline_event_count": (
                    simulation.baseline_event_count
                ),
                "projected_event_count": (
                    simulation.projected_event_count
                ),
                "baseline_avg_duration": (
                    float(simulation.baseline_avg_duration)
                    if simulation.baseline_avg_duration is not None
                    else None
                ),
                "projected_avg_duration": (
                    float(simulation.projected_avg_duration)
                    if simulation.projected_avg_duration is not None
                    else None
                ),
                "baseline_total_duration": (
                    float(simulation.baseline_total_duration)
                    if simulation.baseline_total_duration is not None
                    else None
                ),
                "projected_total_duration": (
                    float(simulation.projected_total_duration)
                    if simulation.projected_total_duration is not None
                    else None
                ),
                "results": simulation.results,
            },
        }

    @staticmethod
    def _build_content(report, data):
        if report.report_type == Report.ReportType.WORKFLOW_SUMMARY:
            workflow = data["workflow"]

            lines = [
                f"Workflow Report: {workflow['name']}",
                "",
                (
                    "Description: "
                    f"{workflow['description'] or 'N/A'}"
                ),
                f"Total steps: {data['step_count']}",
                "",
                "Steps:",
            ]

            for step in data["steps"]:
                lines.append(
                    f"{step['order']}. {step['name']}"
                )

            return "\n".join(lines)

        if report.report_type == Report.ReportType.ANALYTICS:
            workflow = data["workflow"]
            dataset = data["dataset"]
            preprocessing = data["preprocessing"]

            lines = [
                f"Analytics Report: {workflow['name']}",
                "",
                f"Dataset: {dataset['name']}",
                (
                    "Original rows: "
                    f"{preprocessing['original_rows']}"
                ),
                (
                    "Cleaned rows: "
                    f"{preprocessing['cleaned_rows']}"
                ),
                "",
                "Step Analytics:",
            ]

            for row in data["duration_analytics"]:
                lines.append(
                    (
                        f"{row['step_name']}: "
                        f"{row['event_count']} events, "
                        f"average duration "
                        f"{row['average_duration']}"
                    )
                )

            return "\n".join(lines)

        if report.report_type == Report.ReportType.SIMULATION:
            simulation = data["simulation"]

            return "\n".join(
                [
                    (
                        "Simulation Report: "
                        f"{simulation['name']}"
                    ),
                    "",
                    (
                        "Workload change: "
                        f"{simulation['workload_change_percent']}%"
                    ),
                    (
                        "Baseline events: "
                        f"{simulation['baseline_event_count']}"
                    ),
                    (
                        "Projected events: "
                        f"{simulation['projected_event_count']}"
                    ),
                    (
                        "Baseline average duration: "
                        f"{simulation['baseline_avg_duration']}"
                    ),
                    (
                        "Projected average duration: "
                        f"{simulation['projected_avg_duration']}"
                    ),
                ]
            )

        raise ReportGenerationError(
            f"Unsupported report type: {report.report_type}"
        )

    @classmethod
    def generate(cls, report):
        cls._validate_report(report)

        report.status = Report.Status.GENERATING
        report.error_message = ""

        report.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

        try:
            with transaction.atomic():
                if report.report_type == Report.ReportType.WORKFLOW_SUMMARY:
                    data = cls._workflow_summary(report)

                elif report.report_type == Report.ReportType.ANALYTICS:
                    data = cls._analytics(report)

                elif report.report_type == Report.ReportType.SIMULATION:
                    data = cls._simulation(report)

                else:
                    raise ReportGenerationError(
                        f"Unsupported report type: "
                        f"{report.report_type}"
                    )

                report.content = cls._build_content(
                    report,
                    data,
                )

                report.data = data
                report.status = Report.Status.COMPLETED
                report.error_message = ""

                report.save(
                    update_fields=[
                        "content",
                        "data",
                        "status",
                        "error_message",
                        "updated_at",
                    ]
                )

                return report

        except ReportGenerationError as exc:
            report.status = Report.Status.FAILED
            report.error_message = str(exc)

            report.save(
                update_fields=[
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )

            raise

        except Exception as exc:
            report.status = Report.Status.FAILED
            report.error_message = str(exc)

            report.save(
                update_fields=[
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )

            raise ReportGenerationError(
                f"Report generation failed: {exc}"
            ) from exc