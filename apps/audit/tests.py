from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.organizations.models import (
    Organization,
    OrganizationMember,
)
from apps.workflows.models import (
    Workflow,
    WorkflowConnection,
    WorkflowStep,
)
from apps.workflows.services.workflow_service import WorkflowService


class WorkflowModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manager1",
            email="manager@example.com",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPassword123!",
        )

        self.organization = Organization.objects.create(
            name="Acme Operations",
            slug="acme-operations",
            industry="Logistics",
        )

        self.other_organization = Organization.objects.create(
            name="Other Operations",
            slug="other-operations",
            industry="Technology",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        OrganizationMember.objects.create(
            organization=self.other_organization,
            user=self.other_user,
            role=OrganizationMember.Role.MANAGER,
        )

    def test_workflow_creation(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            description="Order fulfillment process.",
            category=Workflow.Category.ORDER_FULFILLMENT,
            status=Workflow.Status.DRAFT,
            created_by=self.user,
        )

        self.assertEqual(
            workflow.organization,
            self.organization,
        )

        self.assertEqual(
            workflow.created_by,
            self.user,
        )

    def test_workflow_step_creation(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        step = WorkflowStep.objects.create(
            workflow=workflow,
            name="Verification",
            order=1,
            expected_duration=5,
            department="Operations",
            responsible_role="Verification Specialist",
        )

        self.assertEqual(
            step.workflow,
            workflow,
        )

        self.assertEqual(
            step.order,
            1,
        )

    def test_connection_between_steps(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        first_step = WorkflowStep.objects.create(
            workflow=workflow,
            name="Order Received",
            order=1,
        )

        second_step = WorkflowStep.objects.create(
            workflow=workflow,
            name="Verification",
            order=2,
        )

        connection = WorkflowConnection.objects.create(
            workflow=workflow,
            source_step=first_step,
            target_step=second_step,
        )

        self.assertEqual(
            connection.source_step,
            first_step,
        )

        self.assertEqual(
            connection.target_step,
            second_step,
        )

    def test_service_creates_workflow(self):
        workflow = WorkflowService.create_workflow(
            user=self.user,
            organization=self.organization,
            name="Customer Support",
        )

        self.assertEqual(
            workflow.name,
            "Customer Support",
        )

        self.assertEqual(
            workflow.organization,
            self.organization,
        )

    def test_user_cannot_access_other_organization_workflow(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Private Workflow",
            created_by=self.user,
        )

        result = WorkflowService.get_workflow_for_user(
            user=self.other_user,
            workflow_id=workflow.id,
        )

        self.assertIsNone(result)

    def test_service_creates_workflow_audit_log(self):
        workflow = WorkflowService.create_workflow(
            user=self.user,
            organization=self.organization,
            name="Audited Workflow",
            description="Workflow for audit testing.",
            category=Workflow.Category.ORDER_FULFILLMENT,
            status=Workflow.Status.DRAFT,
        )

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            object_type="Workflow",
            object_id=workflow.id,
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.CREATE,
        )

        self.assertEqual(
            audit_log.object_repr,
            str(workflow),
        )

        self.assertEqual(
            audit_log.description,
            "Created workflow 'Audited Workflow'.",
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            workflow.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_name"],
            "Audited Workflow",
        )

        self.assertEqual(
            audit_log.metadata["category"],
            workflow.category,
        )

        self.assertEqual(
            audit_log.metadata["status"],
            workflow.status,
        )

    def test_direct_workflow_model_creation_does_not_create_audit_log(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Direct Workflow",
            created_by=self.user,
        )

        audit_logs = AuditLog.objects.filter(
            organization=self.organization,
            object_type="Workflow",
            object_id=workflow.id,
        )

        self.assertEqual(
            audit_logs.count(),
            0,
        )

    def test_workflow_creation_and_audit_log_share_organization(self):
        workflow = WorkflowService.create_workflow(
            user=self.user,
            organization=self.organization,
            name="Organization Audit Workflow",
        )

        audit_log = AuditLog.objects.get(
            object_type="Workflow",
            object_id=workflow.id,
        )

        self.assertEqual(
            workflow.organization_id,
            audit_log.organization_id,
        )

        self.assertEqual(
            audit_log.organization,
            self.organization,
        )

    def test_workflow_creation_audit_log_is_attributed_to_creator(self):
        workflow = WorkflowService.create_workflow(
            user=self.user,
            organization=self.organization,
            name="Creator Audit Workflow",
        )

        audit_log = AuditLog.objects.get(
            object_type="Workflow",
            object_id=workflow.id,
        )

        self.assertEqual(
            audit_log.user,
            workflow.created_by,
        )

    def test_service_creates_workflow_step_audit_log(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        step = WorkflowService.add_step(
            user=self.user,
            workflow=workflow,
            name="Verification",
            order=1,
            expected_duration=5,
            department="Operations",
            responsible_role="Verification Specialist",
        )

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            object_type="WorkflowStep",
            object_id=step.id,
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.CREATE,
        )

        self.assertEqual(
            audit_log.object_repr,
            str(step),
        )

        self.assertEqual(
            audit_log.description,
            (
                "Created workflow step 'Verification' "
                "for workflow 'Order Fulfillment'."
            ),
        )

    def test_workflow_step_audit_log_uses_workflow_organization(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        step = WorkflowService.add_step(
            user=self.user,
            workflow=workflow,
            name="Verification",
            order=1,
        )

        audit_log = AuditLog.objects.get(
            object_type="WorkflowStep",
            object_id=step.id,
        )

        self.assertEqual(
            audit_log.organization_id,
            workflow.organization_id,
        )

    def test_workflow_step_audit_log_contains_step_metadata(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        step = WorkflowService.add_step(
            user=self.user,
            workflow=workflow,
            name="Packing",
            order=3,
        )

        audit_log = AuditLog.objects.get(
            object_type="WorkflowStep",
            object_id=step.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            workflow.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_name"],
            workflow.name,
        )

        self.assertEqual(
            audit_log.metadata["step_id"],
            step.id,
        )

        self.assertEqual(
            audit_log.metadata["step_name"],
            step.name,
        )

        self.assertEqual(
            audit_log.metadata["order"],
            step.order,
        )

    def test_service_creates_workflow_connection_audit_log(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        source_step = workflow.steps.create(
            name="Order Received",
            order=1,
        )

        target_step = workflow.steps.create(
            name="Verification",
            order=2,
        )

        connection = WorkflowService.connect_steps(
            user=self.user,
            workflow=workflow,
            source_step=source_step,
            target_step=target_step,
        )

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            object_type="WorkflowConnection",
            object_id=connection.id,
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.CREATE,
        )

        self.assertEqual(
            audit_log.object_repr,
            str(connection),
        )

        self.assertEqual(
            audit_log.description,
            (
                "Connected workflow steps "
                "'Order Received' -> 'Verification' "
                "in workflow 'Order Fulfillment'."
            ),
        )

    def test_workflow_connection_audit_log_contains_step_metadata(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        source_step = workflow.steps.create(
            name="Order Received",
            order=1,
        )

        target_step = workflow.steps.create(
            name="Verification",
            order=2,
        )

        connection = WorkflowService.connect_steps(
            user=self.user,
            workflow=workflow,
            source_step=source_step,
            target_step=target_step,
            condition="Payment approved",
        )

        audit_log = AuditLog.objects.get(
            object_type="WorkflowConnection",
            object_id=connection.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            workflow.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_name"],
            workflow.name,
        )

        self.assertEqual(
            audit_log.metadata["connection_id"],
            connection.id,
        )

        self.assertEqual(
            audit_log.metadata["source_step_id"],
            source_step.id,
        )

        self.assertEqual(
            audit_log.metadata["source_step_name"],
            source_step.name,
        )

        self.assertEqual(
            audit_log.metadata["target_step_id"],
            target_step.id,
        )

        self.assertEqual(
            audit_log.metadata["target_step_name"],
            target_step.name,
        )

        self.assertEqual(
            audit_log.metadata["condition"],
            "Payment approved",
        )

    def test_workflow_connection_audit_log_uses_workflow_organization(self):
        workflow = Workflow.objects.create(
            organization=self.organization,
            name="Order Fulfillment",
            created_by=self.user,
        )

        source_step = workflow.steps.create(
            name="Order Received",
            order=1,
        )

        target_step = workflow.steps.create(
            name="Verification",
            order=2,
        )

        connection = WorkflowService.connect_steps(
            user=self.user,
            workflow=workflow,
            source_step=source_step,
            target_step=target_step,
        )

        audit_log = AuditLog.objects.get(
            object_type="WorkflowConnection",
            object_id=connection.id,
        )

        self.assertEqual(
            audit_log.organization_id,
            workflow.organization_id,
        )