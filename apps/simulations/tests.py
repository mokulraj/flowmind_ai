from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.simulations.models import Simulation
from apps.simulations.services.engine import (
    SimulationEngine,
    SimulationEngineError,
)
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

    def create_simulation(self, **kwargs):
        defaults = {
            "organization": self.organization,
            "workflow": self.workflow,
            "name": "Test Simulation",
        }

        defaults.update(kwargs)

        return Simulation.objects.create(**defaults)

    def test_simulation_can_be_created(self):
        simulation = self.create_simulation(
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
        simulation = self.create_simulation(
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
        simulation = self.create_simulation(
            name="Order Fulfillment Scenario",
        )

        self.assertEqual(
            str(simulation),
            "Order Fulfillment Scenario",
        )

    def test_simulation_can_store_results(self):
        simulation = self.create_simulation(
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
        simulation = self.create_simulation(
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
        simulation = self.create_simulation(
            name="Workload Reduction",
            workload_change_percent=-20.0,
        )

        self.assertEqual(
            simulation.workload_change_percent,
            -20.0,
        )

    def test_simulation_relationships_are_preserved(self):
        simulation = self.create_simulation(
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


class SimulationEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="engine_user",
            email="engine@example.com",
            password="TestPassword123!",
            role=User.Role.ADMIN,
        )

        self.organization = Organization.objects.create(
            name="Engine Test Organization",
            slug="engine-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=User.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Engine Workflow",
            description="Workflow used for engine tests.",
        )

        self.engine = SimulationEngine()

    def create_simulation(self, **kwargs):
        defaults = {
            "organization": self.organization,
            "workflow": self.workflow,
            "name": "Engine Simulation",
        }

        defaults.update(kwargs)

        return Simulation.objects.create(**defaults)

    def test_engine_projects_event_count_by_workload_percentage(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        result = self.engine.run(
            simulation,
            baseline_event_count=5000,
        )

        self.assertEqual(
            result.baseline_event_count,
            5000,
        )
        self.assertEqual(
            result.projected_event_count,
            6000,
        )

    def test_engine_projects_total_duration_by_workload_percentage(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        result = self.engine.run(
            simulation,
            baseline_total_duration=10000.0,
        )

        self.assertEqual(
            result.baseline_total_duration,
            10000.0,
        )
        self.assertEqual(
            result.projected_total_duration,
            12000.0,
        )

    def test_engine_keeps_average_duration_constant(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        result = self.engine.run(
            simulation,
            baseline_avg_duration=12.5,
        )

        self.assertEqual(
            result.baseline_avg_duration,
            12.5,
        )
        self.assertEqual(
            result.projected_avg_duration,
            12.5,
        )

    def test_engine_supports_workload_reduction(self):
        simulation = self.create_simulation(
            workload_change_percent=-20.0,
        )

        result = self.engine.run(
            simulation,
            baseline_event_count=5000,
            baseline_total_duration=10000.0,
        )

        self.assertEqual(
            result.projected_event_count,
            4000,
        )
        self.assertEqual(
            result.projected_total_duration,
            8000.0,
        )

    def test_engine_supports_zero_workload_change(self):
        simulation = self.create_simulation(
            workload_change_percent=0.0,
        )

        result = self.engine.run(
            simulation,
            baseline_event_count=5000,
            baseline_avg_duration=12.5,
            baseline_total_duration=10000.0,
        )

        self.assertEqual(
            result.projected_event_count,
            5000,
        )
        self.assertEqual(
            result.projected_avg_duration,
            12.5,
        )
        self.assertEqual(
            result.projected_total_duration,
            10000.0,
        )

    def test_engine_uses_values_from_simulation_when_not_provided(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
            baseline_event_count=5000,
            baseline_avg_duration=12.5,
            baseline_total_duration=10000.0,
        )

        result = self.engine.run(simulation)

        self.assertEqual(
            result.projected_event_count,
            6000,
        )
        self.assertEqual(
            result.projected_avg_duration,
            12.5,
        )
        self.assertEqual(
            result.projected_total_duration,
            12000.0,
        )

    def test_engine_marks_simulation_completed(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        result = self.engine.run(
            simulation,
            baseline_event_count=5000,
        )

        self.assertEqual(
            result.status,
            Simulation.Status.COMPLETED,
        )

    def test_engine_persists_results(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        self.engine.run(
            simulation,
            baseline_event_count=5000,
            baseline_avg_duration=12.5,
            baseline_total_duration=10000.0,
        )

        simulation.refresh_from_db()

        self.assertEqual(
            simulation.projected_event_count,
            6000,
        )

        self.assertEqual(
            simulation.results["baseline_event_count"],
            5000,
        )

        self.assertEqual(
            simulation.results["projected_event_count"],
            6000,
        )

        self.assertEqual(
            simulation.results["event_count_change"],
            1000,
        )

        self.assertEqual(
            simulation.results["projected_total_duration"],
            12000.0,
        )

    def test_engine_rejects_non_simulation_object(self):
        with self.assertRaises(SimulationEngineError):
            self.engine.run("invalid")

    def test_engine_rejects_workload_change_of_negative_100(self):
        simulation = self.create_simulation(
            workload_change_percent=-100.0,
        )

        with self.assertRaises(SimulationEngineError):
            self.engine.run(
                simulation,
                baseline_event_count=5000,
            )

    def test_engine_rejects_negative_baseline_event_count(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        with self.assertRaises(SimulationEngineError):
            self.engine.run(
                simulation,
                baseline_event_count=-1,
            )

    def test_engine_rejects_non_numeric_baseline_event_count(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        with self.assertRaises(SimulationEngineError):
            self.engine.run(
                simulation,
                baseline_event_count="5000",
            )

    def test_engine_rejects_negative_total_duration(self):
        simulation = self.create_simulation(
            workload_change_percent=20.0,
        )

        with self.assertRaises(SimulationEngineError):
            self.engine.run(
                simulation,
                baseline_total_duration=-100.0,
            )