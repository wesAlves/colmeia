"""URL configuration for the journal app."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/visits/new/",
        views.VisitCreateView.as_view(),
        name="visit_create",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/visits/<int:pk>/edit/",
        views.VisitUpdateView.as_view(),
        name="visit_update",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/visits/<int:pk>/delete/",
        views.VisitDeleteView.as_view(),
        name="visit_delete",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/notes/new/",
        views.NoteCreateView.as_view(),
        name="note_create",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/notes/<int:pk>/edit/",
        views.NoteUpdateView.as_view(),
        name="note_update",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/notes/<int:pk>/delete/",
        views.NoteDeleteView.as_view(),
        name="note_delete",
    ),
]