"""Views for houses, features, photos and ratings."""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Avg, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from accounts.mixins import (
    WorkspaceAccessMixin,
    WorkspaceFormMixin,
    WorkspaceQuerysetMixin,
)

from .forms import (
    FeatureForm,
    FeatureValueFormSetWithWorkspace,
    HouseForm,
    HousePhotoForm,
    RatingForm,
)
from .mixins import HouseScopedMixin
from .models import Feature, House, HousePhoto, Rating


class HouseListView(WorkspaceQuerysetMixin, ListView):
    """List every house in a workspace with optional status/query filters."""

    model = House
    template_name = "properties/house_list.html"
    context_object_name = "houses"
    paginate_by = 25

    def get_queryset(self) -> QuerySet[House]:
        """Filter by workspace, status, free-text search and annotate rating."""
        queryset = (
            super()
            .get_queryset()
            .annotate(_avg_rating=Avg("ratings__score"))
            .prefetch_related("photos")
        )
        status = self.request.GET.get("status", "").strip()
        if status in House.Status.values:
            queryset = queryset.filter(status=status)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(title__icontains=query) | queryset.filter(
                city__icontains=query
            )
        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Expose the status choices and active filters to the template."""
        context = super().get_context_data(**kwargs)
        context["status_choices"] = House.Status.choices
        context["current_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        return context


class HouseDetailView(WorkspaceQuerysetMixin, DetailView):
    """Show a house with its photos, ratings, feature values, visits and notes."""

    model = House
    template_name = "properties/house_detail.html"
    context_object_name = "house"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add every related collection needed by the detail template."""
        context = super().get_context_data(**kwargs)
        house: House = self.object
        context["feature_values"] = (
            house.feature_values.select_related("feature").order_by(
                "feature__order", "feature__name"
            )
        )
        context["photos"] = house.photos.select_related("uploaded_by").order_by(
            "-is_primary", "-uploaded_at"
        )
        context["ratings"] = house.ratings.select_related("user").order_by("-score")
        context["avg_rating"] = house.ratings.aggregate(avg=Avg("score"))["avg"]
        context["my_rating"] = house.ratings.filter(user=self.request.user).first()
        context["visits"] = house.visits.select_related("created_by").order_by(
            "-visited_at"
        )
        context["notes"] = house.notes.select_related("created_by").order_by(
            "-created_at"
        )
        return context


class HouseCreateView(WorkspaceFormMixin, SuccessMessageMixin, CreateView):
    """Create a house together with its feature values."""

    model = House
    form_class = HouseForm
    template_name = "properties/house_form.html"
    success_message = "House created."
    require_editor = True

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Instantiate the feature-value formset for the template."""
        context = super().get_context_data(**kwargs)
        if "feature_formset" not in context:
            context["feature_formset"] = FeatureValueFormSetWithWorkspace(
                self.request.POST if self.request.method == "POST" else None,
                instance=House(),
                workspace=self.workspace,
                prefix="features",
            )
        return context

    def form_valid(self, form: HouseForm) -> HttpResponse:
        """Validate the parent form and the feature formset together."""
        self.object = form.save(commit=False)
        self.object.workspace = self.workspace
        self.object.created_by = self.request.user
        self.object.save()

        formset = FeatureValueFormSetWithWorkspace(
            self.request.POST,
            instance=self.object,
            workspace=self.workspace,
            prefix="features",
        )
        if not formset.is_valid():
            return self.form_invalid(form)
        formset.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.object.pk},
        )


class HouseUpdateView(WorkspaceFormMixin, SuccessMessageMixin, UpdateView):
    """Update a house and its feature values."""

    model = House
    form_class = HouseForm
    template_name = "properties/house_form.html"
    success_message = "House updated."
    require_editor = True

    def get_queryset(self) -> QuerySet[House]:
        """Limit updates to houses of the current workspace."""
        return House.objects.filter(workspace=self.workspace)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Instantiate the feature-value formset for the template."""
        context = super().get_context_data(**kwargs)
        if "feature_formset" not in context:
            context["feature_formset"] = FeatureValueFormSetWithWorkspace(
                self.request.POST if self.request.method == "POST" else None,
                instance=self.object,
                workspace=self.workspace,
                prefix="features",
            )
        return context

    def form_valid(self, form: HouseForm) -> HttpResponse:
        """Validate the parent form and the feature formset together."""
        self.object = form.save()
        formset = FeatureValueFormSetWithWorkspace(
            self.request.POST,
            instance=self.object,
            workspace=self.workspace,
            prefix="features",
        )
        if not formset.is_valid():
            return self.form_invalid(form)
        formset.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.object.pk},
        )


class HouseDeleteView(WorkspaceAccessMixin, DeleteView):
    """Delete a house.  Editors only."""

    model = House
    template_name = "properties/house_confirm_delete.html"
    context_object_name = "house"
    require_editor = True

    def get_queryset(self) -> QuerySet[House]:
        """Limit deletions to houses of the current workspace."""
        return House.objects.filter(workspace=self.workspace)

    def get_success_url(self) -> str:
        """Redirect back to the house list."""
        return reverse_lazy(
            "properties:house_list", kwargs={"workspace_slug": self.workspace.slug}
        )


class FeatureListView(WorkspaceQuerysetMixin, ListView):
    """List the feature catalog of a workspace."""

    model = Feature
    template_name = "properties/feature_list.html"
    context_object_name = "features"

    def get_queryset(self) -> QuerySet[Feature]:
        """Return features ordered by their display order."""
        return super().get_queryset().order_by("order", "name")


class FeatureCreateView(WorkspaceFormMixin, SuccessMessageMixin, CreateView):
    """Add a custom feature to the workspace catalog."""

    model = Feature
    form_class = FeatureForm
    template_name = "properties/feature_form.html"
    success_message = "Feature created."
    require_editor = True

    def form_valid(self, form: FeatureForm) -> HttpResponse:
        """Attach the feature to the current workspace."""
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect back to the feature list."""
        return reverse_lazy(
            "properties:feature_list", kwargs={"workspace_slug": self.workspace.slug}
        )


class FeatureUpdateView(WorkspaceFormMixin, SuccessMessageMixin, UpdateView):
    """Edit a feature definition."""

    model = Feature
    form_class = FeatureForm
    template_name = "properties/feature_form.html"
    success_message = "Feature updated."
    require_editor = True

    def get_queryset(self) -> QuerySet[Feature]:
        """Limit updates to features of the current workspace."""
        return Feature.objects.filter(workspace=self.workspace)

    def get_success_url(self) -> str:
        """Redirect back to the feature list."""
        return reverse_lazy(
            "properties:feature_list", kwargs={"workspace_slug": self.workspace.slug}
        )


class FeatureDeleteView(WorkspaceAccessMixin, DeleteView):
    """Delete a feature and all its values."""

    model = Feature
    template_name = "properties/feature_confirm_delete.html"
    context_object_name = "feature"
    require_editor = True

    def get_queryset(self) -> QuerySet[Feature]:
        """Limit deletions to features of the current workspace."""
        return Feature.objects.filter(workspace=self.workspace)

    def get_success_url(self) -> str:
        """Redirect back to the feature list."""
        return reverse_lazy(
            "properties:feature_list", kwargs={"workspace_slug": self.workspace.slug}
        )


class RatingUpsertView(HouseScopedMixin, SuccessMessageMixin, FormView):
    """Create or update the current user's rating for a house.

    A single endpoint is used for both cases.  The form is pre-populated with
    the user's existing score when one is present, and the view uses
    :meth:`~django.db.models.query.QuerySet.update_or_create` to persist the
    result, so a user always has at most one rating per house.
    """

    form_class = RatingForm
    template_name = "properties/rating_form.html"
    success_message = "Rating saved."
    require_editor = True

    def get_initial(self) -> dict[str, Any]:
        """Pre-fill the form with the current user's existing rating, if any."""
        initial = super().get_initial()
        existing = Rating.objects.filter(
            house=self.house, user=self.request.user
        ).first()
        if existing is not None:
            initial["score"] = existing.score
            initial["comment"] = existing.comment
        return initial

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Expose the existing rating so the template can adapt its wording."""
        context = super().get_context_data(**kwargs)
        context["existing_rating"] = Rating.objects.filter(
            house=self.house, user=self.request.user
        ).first()
        return context

    def form_valid(self, form: RatingForm) -> HttpResponse:
        """Persist the rating for the current user and house."""
        Rating.objects.update_or_create(
            house=self.house,
            user=self.request.user,
            defaults={
                "score": form.cleaned_data["score"],
                "comment": form.cleaned_data["comment"],
            },
        )
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class RatingDeleteView(HouseScopedMixin, DeleteView):
    """Delete the current user's rating for a house."""

    model = Rating
    template_name = "properties/rating_confirm_delete.html"
    context_object_name = "rating"
    require_editor = True

    def get_object(self, queryset: QuerySet[Rating] | None = None) -> Rating:
        """Retrieve the current user's rating for the scoped house."""
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset)

    def get_queryset(self) -> QuerySet[Rating]:
        """Only allow deleting one's own rating."""
        return Rating.objects.filter(house=self.house, user=self.request.user)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class HousePhotoCreateView(HouseScopedMixin, SuccessMessageMixin, CreateView):
    """Upload a new photo for a house."""

    model = HousePhoto
    form_class = HousePhotoForm
    template_name = "properties/housephoto_form.html"
    success_message = "Photo uploaded."
    require_editor = True

    def form_valid(self, form: HousePhotoForm) -> HttpResponse:
        """Attach the photo to the house, set the uploader and enforce primary."""
        form.instance.house = self.house
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        if form.instance.is_primary:
            self.house.photos.exclude(pk=form.instance.pk).update(is_primary=False)
        return response

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class HousePhotoDeleteView(HouseScopedMixin, DeleteView):
    """Delete a photo from a house."""

    model = HousePhoto
    template_name = "properties/housephoto_confirm_delete.html"
    context_object_name = "photo"
    require_editor = True

    def get_queryset(self) -> QuerySet[HousePhoto]:
        """Limit deletions to photos of the current house."""
        return HousePhoto.objects.filter(house=self.house)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
