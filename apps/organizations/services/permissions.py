from django.core.exceptions import PermissionDenied

from ..models import OrganizationMember


def get_membership(user, organization):
    """
    Return the user's membership in an organization.

    Raises:
        PermissionDenied: if the user does not belong to the
        organization.
    """

    if not user.is_authenticated:
        raise PermissionDenied(
            "Authentication is required."
        )

    try:
        return OrganizationMember.objects.get(
            user=user,
            organization=organization,
        )
    except OrganizationMember.DoesNotExist as exc:
        raise PermissionDenied(
            "You do not have access to this organization."
        ) from exc


def user_belongs_to_organization(user, organization):
    """
    Check whether a user belongs to an organization.
    """

    if not user.is_authenticated:
        return False

    return OrganizationMember.objects.filter(
        user=user,
        organization=organization,
    ).exists()


def user_has_organization_role(
    user,
    organization,
    allowed_roles,
):
    """
    Check whether a user has one of the supplied roles.
    """

    if not user.is_authenticated:
        return False

    return OrganizationMember.objects.filter(
        user=user,
        organization=organization,
        role__in=allowed_roles,
    ).exists()


def require_organization_role(
    user,
    organization,
    allowed_roles,
):
    """
    Require a user to have one of the specified organization roles.

    Raises:
        PermissionDenied: if the user lacks the required role.
    """

    if not user_has_organization_role(
        user=user,
        organization=organization,
        allowed_roles=allowed_roles,
    ):
        raise PermissionDenied(
            "You do not have the required organization permission."
        )