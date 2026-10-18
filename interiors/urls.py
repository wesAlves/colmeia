"""URL configuration for the interiors app."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "interiors"

urlpatterns = [
    # Interior Projects
    path(
        "workspaces/<slug:workspace_slug>/interiors/",
        views.ProjectListView.as_view(),
        name="project_list",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/new/",
        views.ProjectCreateView.as_view(),
        name="project_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/<int:pk>/",
        views.ProjectDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/<int:pk>/edit/",
        views.ProjectUpdateView.as_view(),
        name="project_update",
    ),
    # Rooms
    path(
        "workspaces/<slug:workspace_slug>/interiors/<int:project_pk>/rooms/new/",
        views.RoomCreateView.as_view(),
        name="room_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/rooms/<int:pk>/",
        views.RoomDetailView.as_view(),
        name="room_detail",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/rooms/<int:pk>/edit/",
        views.RoomUpdateView.as_view(),
        name="room_update",
    ),
    # Items
    path(
        "workspaces/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/items/new/",
        views.ItemCreateView.as_view(),
        name="item_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/items/<int:pk>/",
        views.ItemDetailView.as_view(),
        name="item_detail",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/items/<int:pk>/edit/",
        views.ItemUpdateView.as_view(),
        name="item_update",
    ),
    # Purchase Options
    path(
        "workspaces/<slug:workspace_slug>/interiors/items/<int:item_pk>/options/new/",
        views.OptionCreateView.as_view(),
        name="option_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/options/<int:pk>/edit/",
        views.OptionUpdateView.as_view(),
        name="option_update",
    ),
    # Moodboard Images
    path(
        "workspaces/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/moodboard/new/",
        views.MoodboardImageCreateView.as_view(),
        name="moodboard_image_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/moodboard/<int:pk>/edit/",
        views.MoodboardImageUpdateView.as_view(),
        name="moodboard_image_update",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/moodboard/reorder/",
        views.MoodboardImageReorderView.as_view(),
        name="moodboard_image_reorder",
    ),
    path(
        "workspaces/<slug:workspace_slug>/interiors/moodboard/reorder/",
        views.MoodboardImageReorderView.as_view(),
        name="moodboard_image_reorder_general",
    ),
    # Aliases supporting 'w/<slug>/interiors/' for consistency with other apps
    path(
        "w/<slug:workspace_slug>/interiors/",
        views.ProjectListView.as_view(),
        name="project_list_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/new/",
        views.ProjectCreateView.as_view(),
        name="project_create_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/<int:pk>/",
        views.ProjectDetailView.as_view(),
        name="project_detail_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/<int:pk>/edit/",
        views.ProjectUpdateView.as_view(),
        name="project_update_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/<int:project_pk>/rooms/new/",
        views.RoomCreateView.as_view(),
        name="room_create_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/rooms/<int:pk>/",
        views.RoomDetailView.as_view(),
        name="room_detail_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/rooms/<int:pk>/edit/",
        views.RoomUpdateView.as_view(),
        name="room_update_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/items/new/",
        views.ItemCreateView.as_view(),
        name="item_create_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/items/<int:pk>/",
        views.ItemDetailView.as_view(),
        name="item_detail_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/items/<int:pk>/edit/",
        views.ItemUpdateView.as_view(),
        name="item_update_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/items/<int:item_pk>/options/new/",
        views.OptionCreateView.as_view(),
        name="option_create_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/options/<int:pk>/edit/",
        views.OptionUpdateView.as_view(),
        name="option_update_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/moodboard/new/",
        views.MoodboardImageCreateView.as_view(),
        name="moodboard_image_create_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/moodboard/<int:pk>/edit/",
        views.MoodboardImageUpdateView.as_view(),
        name="moodboard_image_update_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/rooms/<int:room_pk>/moodboard/reorder/",
        views.MoodboardImageReorderView.as_view(),
        name="moodboard_image_reorder_alias",
    ),
    path(
        "w/<slug:workspace_slug>/interiors/moodboard/reorder/",
        views.MoodboardImageReorderView.as_view(),
        name="moodboard_image_reorder_general_alias",
    ),
]
