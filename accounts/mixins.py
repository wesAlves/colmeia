"""Reusable view mixins enforcing workspace scoping and permissions."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Membership, Workspace


class WorkspaceAccessMixin:
    """Resolve ``workspace_slug`` and enforce membership on every request.

    Views using this mixin must accept a ``workspace_slug`` URL keyword
    argument.  After :meth:`dispatch` the following attributes are available:

    Attributes:
        workspace: The :class:`~accounts.models.Workspace` being accessed.
        membership: The requesting user's membership in that workspace.
        require_editor: Set to ``True`` on write views to forbid viewers.
    """

    workspace: Workspace
    membership: Membership
    require_editor: bool = False

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Authenticate, resolve the workspace and check the role."""
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        slug = kwargs.get("workspace_slug")
        self.workspace = get_object_or_404(Workspace, slug=slug)
        membership = self.workspace.membership_for(request.user)
        if membership is None:
            raise PermissionDenied("You are not a member of this workspace.")
        if self.require_editor and not membership.can_edit:
            raise PermissionDenied("You need editor rights to do that.")
        self.membership = membership
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Inject the workspace and membership into the template context."""
        context = super().get_context_data(**kwargs)
        context.setdefault("workspace", self.workspace)
        context.setdefault("membership", self.membership)
        return context


class WorkspaceFormMixin(WorkspaceAccessMixin):
    """Pass the current workspace to forms that need it for queryset filtering."""

    def get_form_kwargs(self) -> dict[str, Any]:
        """Add ``workspace`` to the form keyword arguments."""
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.workspace
        return kwargs


class WorkspaceQuerysetMixin(WorkspaceAccessMixin):
    """Restrict a view's queryset to the current workspace."""

    def get_queryset(self):
        """Return only objects belonging to the resolved workspace."""
        queryset = super().get_queryset()
        return queryset.filter(workspace=self.workspace)

