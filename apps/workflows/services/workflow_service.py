from django.db import transaction

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

        return Workflow.objects.create(
            organization=organization,
            name=name,
            description=description,
            category=category,
            status=status,
            created_by=user,
        )

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

        return WorkflowStep.objects.create(
            workflow=workflow,
            name=name,
            order=order,
            description=description,
            expected_duration=expected_duration,
            department=department,
            responsible_role=responsible_role,
        )

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

        return connection