from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.simulations.models import Simulation
from apps.workflows.models import Workflow


class SimulationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="simulation_user",
            email="simulation@example.com",
            password="TestPassword123!",
            role=User.Role.ADMIN,
        )

        self.organization = Organization.objects.create(
            name="Simulation Test Organization",
            slug="simulation-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=User.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Simulation Workflow",
            description="Workflow used for simulation tests.",
        )

    def test_simulation_can_be_created(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="20 Percent Workload Increase",
            description="Test workload scenario.",
            workload_change_percent=20.0,
        )

        self.assertEqual(simulation.organization, self.organization)
        self.assertEqual(simulation.workflow, self.workflow)
        self.assertEqual(
            simulation.name,
            "20 Percent Workload Increase",
        )
        self.assertEqual(
            simulation.workload_change_percent,
            20.0,
        )
        self.assertEqual(
            simulation.status,
            Simulation.Status.DRAFT,
        )

    def test_simulation_defaults_are_applied(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Default Simulation",
        )

        self.assertEqual(
            simulation.workload_change_percent,
            0.0,
        )
        self.assertEqual(
            simulation.baseline_event_count,
            0,
        )
        self.assertEqual(
            simulation.projected_event_count,
            0,
        )
        self.assertEqual(
            simulation.baseline_avg_duration,
            0.0,
        )
        self.assertEqual(
            simulation.projected_avg_duration,
            0.0,
        )
        self.assertEqual(
            simulation.baseline_total_duration,
            0.0,
        )
        self.assertEqual(
            simulation.projected_total_duration,
            0.0,
        )
        self.assertEqual(
            simulation.status,
            Simulation.Status.DRAFT,
        )
        self.assertEqual(
            simulation.results,
            {},
        )
        self.assertEqual(
            simulation.notes,
            "",
        )

    def test_simulation_string_representation(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Order Fulfillment Scenario",
        )

        self.assertEqual(
            str(simulation),
            "Order Fulfillment Scenario",
        )

    def test_simulation_can_store_results(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Results Test",
            results={
                "projected_delay": 12.5,
                "affected_steps": 2,
            },
        )

        simulation.refresh_from_db()

        self.assertEqual(
            simulation.results["projected_delay"],
            12.5,
        )
        self.assertEqual(
            simulation.results["affected_steps"],
            2,
        )

    def test_simulation_status_can_change(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Status Test",
        )

        simulation.status = Simulation.Status.RUNNING
        simulation.save()

        simulation.refresh_from_db()

        self.assertEqual(
            simulation.status,
            Simulation.Status.RUNNING,
        )

        simulation.status = Simulation.Status.COMPLETED
        simulation.save()

        simulation.refresh_from_db()

        self.assertEqual(
            simulation.status,
            Simulation.Status.COMPLETED,
        )

    def test_simulation_supports_negative_workload_change(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Workload Reduction",
            workload_change_percent=-20.0,
        )

        self.assertEqual(
            simulation.workload_change_percent,
            -20.0,
        )

    def test_simulation_relationships_are_preserved(self):
        simulation = Simulation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            name="Relationship Test",
        )

        self.assertIn(
            simulation,
            self.organization.simulations.all(),
        )

        self.assertIn(
            simulation,
            self.workflow.simulations.all(),
        )