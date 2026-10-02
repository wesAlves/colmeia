"""URL configuration for the accounts app."""

from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("workspaces/", views.WorkspaceListView.as_view(), name="workspace_list"),
    path("workspaces/new/", views.WorkspaceCreateView.as_view(), name="workspace_create"),
    path(
        "workspaces/<slug:workspace_slug>/",
        views.WorkspaceDetailView.as_view(),
        name="workspace_detail",
    ),
    path(
        "workspaces/<slug:workspace_slug>/edit/",
        views.WorkspaceUpdateView.as_view(),
        name="workspace_update",
    ),
    path(
        "workspaces/<slug:workspace_slug>/members/new/",
        views.MembershipCreateView.as_view(),
        name="membership_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/members/<int:pk>/delete/",
        views.MembershipDeleteView.as_view(),
        name="membership_delete",
    ),
]