"""User, workspace and membership models.

A *workspace* is the multi-tenant boundary: every house, feature, visit and
note belongs to exactly one workspace, and users only ever see data from
workspaces they are a member of.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model.

    Declared up-front so the project can extend it later without a painful
    migration.  Currently it adds nothing beyond :class:`AbstractUser`.
    """


class Role(models.TextChoices):
    """Roles a member can hold inside a workspace."""

    OWNER = "owner", _("Owner")
    EDITOR = "editor", _("Editor")
    VIEWER = "viewer", _("Viewer")


class Workspace(models.Model):
    """A shared space where members collaborate on a house search.

    Attributes:
        name: Human readable name, e.g. ``"Lisbon house hunt 2025"``.
        slug: URL friendly identifier, used in every tenant-scoped URL.
        description: Optional free-form description of the search.
        created_by: The user that created the workspace.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = _("workspace")
        verbose_name_plural = _("workspaces")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Ensure the slug is always populated before saving."""
        if not self.slug:
            base = slugify(self.name) or "workspace"
            slug = base
            counter = 2
            while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def membership_for(self, user) -> "Membership | None":
        """Return the membership of ``user`` in this workspace, if any."""
        if not user.is_authenticated:
            return None
        return self.memberships.filter(user=user).select_related("user").first()

    def is_member(self, user) -> bool:
        """Return ``True`` when ``user`` belongs to this workspace."""
        return self.membership_for(user) is not None


class Membership(models.Model):
    """Links a :class:`User` to a :class:`Workspace` with a specific role."""

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.EDITOR
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "user")
        ordering = ("workspace", "user__username")
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")

    def __str__(self) -> str:
        return f"{self.user} @ {self.workspace} ({self.role})"

    @property
    def can_edit(self) -> bool:
        """Return ``True`` when the member may create/update content."""
        return self.role in {Role.OWNER, Role.EDITOR}

    @property
    def can_manage(self) -> bool:
        """Return ``True`` when the member may manage the workspace itself."""
        return self.role == Role.OWNER