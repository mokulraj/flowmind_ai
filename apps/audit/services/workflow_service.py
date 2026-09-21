from django.db import transaction

from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditLogService
from apps.organizations.services.permissions import (
    require_organization_role,
)

from ..models import (
    Workflow,
    WorkflowConnection,
    WorkflowStep,
)


class WorkflowService:
    """
    Business logic for workflow management.
    """

    @staticmethod
    @transaction.atomic
    def create_workflow(
        *,
        user,
        organization,
        name,
        description="",
        category=Workflow.Category.OPERATIONS,
        status=Workflow.Status.DRAFT,
    ):
        require_organization_role(
            user=user,
            organization=organization,
            allowed_roles=[
                "ADMIN",
                "MANAGER",
            ],
        )

        workflow = Workflow.objects.create(
            organization=organization,
            name=name,
            description=description,
            category=category,
            status=status,
            created_by=user,
        )

        AuditLogService.create(
            organization=organization,
            user=user,
            action=AuditLog.Action.CREATE,
            object_type="Workflow",
            object_id=workflow.id,
            object_repr=str(workflow),
            description=f"Created workflow '{workflow.name}'.",
            metadata={
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "category": workflow.category,
                "status": workflow.status,
            },
        )

        return workflow

    @staticmethod
    def get_workflow_for_user(
        *,
        user,
        workflow_id,
    ):
        """
        Retrieve a workflow only if the user belongs to
        the workflow's organization.
        """

        return Workflow.objects.filter(
            id=workflow_id,
            organization__members__user=user,
        ).select_related(
            "organization",
            "created_by",
        ).prefetch_related(
            "steps",
            "connections",
        ).first()

    @staticmethod
    @transaction.atomic
    def add_step(
        *,
        user,
        workflow,
        name,
        order,
        description="",
        expected_duration=None,
        department="",
        responsible_role="",
    ):
        require_organization_role(
            user=user,
            organization=workflow.organization,
            allowed_roles=[
                "ADMIN",
                "MANAGER",
                "ANALYST",
            ],
        )

        step = WorkflowStep.objects.create(
            workflow=workflow,
            name=name,
            order=order,
            description=description,
            expected_duration=expected_duration,
            department=department,
            responsible_role=responsible_role,
        )

        AuditLogService.create(
            organization=workflow.organization,
            user=user,
            action=AuditLog.Action.CREATE,
            object_type="WorkflowStep",
            object_id=step.id,
            object_repr=str(step),
            description=(
                f"Created workflow step '{step.name}' "
                f"for workflow '{workflow.name}'."
            ),
            metadata={
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "step_id": step.id,
                "step_name": step.name,
                "order": step.order,
            },
        )

        return step

    @staticmethod
    @transaction.atomic
    def connect_steps(
        *,
        user,
        workflow,
        source_step,
        target_step,
        condition="",
    ):
        require_organization_role(
            user=user,
            organization=workflow.organization,
            allowed_roles=[
                "ADMIN",
                "MANAGER",
                "ANALYST",
            ],
        )

        if source_step.workflow_id != workflow.id:
            raise ValueError(
                "Source step does not belong to the workflow."
            )

        if target_step.workflow_id != workflow.id:
            raise ValueError(
                "Target step does not belong to the workflow."
            )

        connection = WorkflowConnection(
            workflow=workflow,
            source_step=source_step,
            target_step=target_step,
            condition=condition,
        )

        connection.full_clean()
        connection.save()

        AuditLogService.create(
            organization=workflow.organization,
            user=user,
            action=AuditLog.Action.CREATE,
            object_type="WorkflowConnection",
            object_id=connection.id,
            object_repr=str(connection),
            description=(
                f"Connected workflow steps "
                f"'{source_step.name}' -> '{target_step.name}' "
                f"in workflow '{workflow.name}'."
            ),
            metadata={
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "connection_id": connection.id,
                "source_step_id": source_step.id,
                "source_step_name": source_step.name,
                "target_step_id": target_step.id,
                "target_step_name": target_step.name,
                "condition": connection.condition,
            },
        )

        return connection