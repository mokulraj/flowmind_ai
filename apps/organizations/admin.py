from django.contrib import admin

from .models import Organization, OrganizationMember


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "industry",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
        "industry",
    )

    list_filter = (
        "industry",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "user",
        "role",
        "joined_at",
    )

    search_fields = (
        "organization__name",
        "user__email",
        "user__username",
    )

    list_filter = (
        "role",
        "organization",
        "joined_at",
    )

    readonly_fields = (
        "joined_at",
    )