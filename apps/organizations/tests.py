from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    OrganizationMember,
)
from apps.organizations.services.permissions import (
    get_membership,
    user_belongs_to_organization,
    user_has_organization_role,
)


class OrganizationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manager1",
            email="manager@example.com",
            password="TestPassword123!",
        )

        self.organization = Organization.objects.create(
            name="Acme Operations",
            slug="acme-operations",
            industry="Logistics",
        )

    def test_organization_creation(self):
        self.assertEqual(
            self.organization.name,
            "Acme Operations",
        )

        self.assertEqual(
            self.organization.slug,
            "acme-operations",
        )

    def test_membership_creation(self):
        membership = OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        self.assertEqual(
            membership.role,
            OrganizationMember.Role.MANAGER,
        )

        self.assertEqual(
            membership.organization,
            self.organization,
        )

        self.assertEqual(
            membership.user,
            self.user,
        )

    def test_user_belongs_to_organization(self):
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        self.assertTrue(
            user_belongs_to_organization(
                self.user,
                self.organization,
            )
        )

    def test_user_does_not_belong_to_other_organization(self):
        other_organization = Organization.objects.create(
            name="Other Company",
            slug="other-company",
            industry="Technology",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        self.assertFalse(
            user_belongs_to_organization(
                self.user,
                other_organization,
            )
        )

    def test_role_check(self):
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        self.assertTrue(
            user_has_organization_role(
                self.user,
                self.organization,
                [
                    OrganizationMember.Role.MANAGER,
                    OrganizationMember.Role.ADMIN,
                ],
            )
        )

        self.assertFalse(
            user_has_organization_role(
                self.user,
                self.organization,
                [
                    OrganizationMember.Role.VIEWER,
                ],
            )
        )

    def test_get_membership_blocks_other_organization(self):
        other_organization = Organization.objects.create(
            name="Other Company",
            slug="other-company",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.MANAGER,
        )

        with self.assertRaises(PermissionDenied):
            get_membership(
                self.user,
                other_organization,
            )