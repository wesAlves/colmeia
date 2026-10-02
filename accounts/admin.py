"""Admin registrations for the accounts app."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Membership, User, Workspace


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin for the custom user model."""


class MembershipInline(admin.TabularInline):
    """Inline memberships on the workspace admin page."""

    model = Membership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Admin for workspaces."""

    list_display = ("name", "slug", "created_by", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin for memberships."""

    list_display = ("workspace", "user", "role", "joined_at")
    list_filter = ("role", "workspace")
    autocomplete_fields = ("user", "workspace")


# =============================================================================
# properties/__init__.py
# =============================================================================
"""Properties app: houses, feature catalog and feature values."""
