"""Views for authentication and workspace management."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import MembershipForm, SignUpForm, WorkspaceForm
from .mixins import WorkspaceAccessMixin
from .models import Membership, Workspace


class RootView(View):
    """Redirect unauthenticated users to login and authenticated users to workspace list."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("accounts:workspace_list")
        return redirect("accounts:login")


class SignUpView(SuccessMessageMixin, CreateView):
    """Register a new user and log them in immediately."""

    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:workspace_list")
    success_message = "Welcome! Your account has been created."

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        """Log the freshly created user in."""
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class WorkspaceListView(LoginRequiredMixin, ListView):
    """List every workspace the current user belongs to."""

    template_name = "accounts/workspace_list.html"
    context_object_name = "workspaces"

    def get_queryset(self) -> QuerySet[Workspace]:
        """Return only the workspaces of the requesting user."""
        return (
            Workspace.objects.filter(memberships__user=self.request.user)
            .select_related("created_by")
            .order_by("name")
        )


class WorkspaceCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new workspace owned by the current user."""

    model = Workspace
    form_class = WorkspaceForm
    template_name = "accounts/workspace_form.html"
    success_message = "Workspace created."

    def form_valid(self, form: WorkspaceForm) -> HttpResponse:
        """Attach the creator and redirect to the workspace detail page."""
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to the newly created workspace."""
        return reverse_lazy("accounts:workspace_detail", kwargs={"workspace_slug": self.object.slug})


class WorkspaceDetailView(WorkspaceAccessMixin, DetailView):
    """Show a workspace overview and its members."""

    model = Workspace
    template_name = "accounts/workspace_detail.html"
    context_object_name = "workspace"

    def get_object(self, queryset=None) -> Workspace:
        """Return the workspace resolved by the access mixin."""
        return self.workspace

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the member list to the context."""
        context = super().get_context_data(**kwargs)
        context["members"] = self.workspace.memberships.select_related("user")
        context["membership_form"] = MembershipForm(workspace=self.workspace)
        return context


class WorkspaceUpdateView(
    WorkspaceAccessMixin, SuccessMessageMixin, UpdateView
):
    """Edit workspace metadata.  Owners only."""

    model = Workspace
    form_class = WorkspaceForm
    template_name = "accounts/workspace_form.html"
    success_message = "Workspace updated."
    require_owner = True

    def get_object(self, queryset=None) -> Workspace:
        """Return the workspace resolved by the access mixin."""
        return self.workspace

    def get_success_url(self) -> str:
        """Redirect back to the workspace detail page."""
        return reverse_lazy(
            "accounts:workspace_detail", kwargs={"workspace_slug": self.workspace.slug}
        )


class MembershipCreateView(WorkspaceAccessMixin, SuccessMessageMixin, CreateView):
    """Invite an existing user into the workspace.  Owners only."""

    model = Membership
    form_class = MembershipForm
    template_name = "accounts/membership_form.html"
    success_message = "Member added."
    require_owner = True

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the workspace so the user queryset can be filtered."""
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.workspace
        return kwargs

    def form_valid(self, form: MembershipForm) -> HttpResponse:
        """Bind the membership to the current workspace."""
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect back to the workspace detail page."""
        return reverse_lazy(
            "accounts:workspace_detail", kwargs={"workspace_slug": self.workspace.slug}
        )


class MembershipDeleteView(WorkspaceAccessMixin, DeleteView):
    """Remove a member from the workspace.  Owners only."""

    model = Membership
    template_name = "accounts/membership_confirm_delete.html"
    context_object_name = "membership"
    require_owner = True

    def get_queryset(self) -> QuerySet[Membership]:
        """Limit deletions to memberships of the current workspace."""
        return Membership.objects.filter(workspace=self.workspace)

    def get_success_url(self) -> str:
        """Redirect back to the workspace detail page."""
        return reverse_lazy(
            "accounts:workspace_detail", kwargs={"workspace_slug": self.workspace.slug}
        )
