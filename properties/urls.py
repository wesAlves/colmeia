"""URL configuration for the properties app."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    # Houses ------------------------------------------------------------------
    path(
        "w/<slug:workspace_slug>/houses/",
        views.HouseListView.as_view(),
        name="house_list",
    ),
    path(
        "w/<slug:workspace_slug>/houses/new/",
        views.HouseCreateView.as_view(),
        name="house_create",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:pk>/",
        views.HouseDetailView.as_view(),
        name="house_detail",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:pk>/status/",
        views.HouseStatusUpdateView.as_view(),
        name="house_status_update",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:pk>/favorite/",
        views.HouseFavoriteToggleView.as_view(),
        name="house_favorite_toggle",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:pk>/edit/",
        views.HouseUpdateView.as_view(),
        name="house_update",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:pk>/delete/",
        views.HouseDeleteView.as_view(),
        name="house_delete",
    ),
    # Feature catalog ---------------------------------------------------------
    path(
        "w/<slug:workspace_slug>/features/",
        views.FeatureListView.as_view(),
        name="feature_list",
    ),
    path(
        "w/<slug:workspace_slug>/features/new/",
        views.FeatureCreateView.as_view(),
        name="feature_create",
    ),
    path(
        "w/<slug:workspace_slug>/features/<int:pk>/edit/",
        views.FeatureUpdateView.as_view(),
        name="feature_update",
    ),
    path(
        "w/<slug:workspace_slug>/features/<int:pk>/delete/",
        views.FeatureDeleteView.as_view(),
        name="feature_delete",
    ),
    # Ratings -----------------------------------------------------------------
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/rating/",
        views.RatingUpsertView.as_view(),
        name="rating_upsert",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/rating/delete/",
        views.RatingDeleteView.as_view(),
        name="rating_delete",
    ),
    # Photos ------------------------------------------------------------------
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/photos/new/",
        views.HousePhotoCreateView.as_view(),
        name="photo_create",
    ),
    path(
        "w/<slug:workspace_slug>/houses/<int:house_pk>/photos/<int:pk>/delete/",
        views.HousePhotoDeleteView.as_view(),
        name="photo_delete",
    ),
]
