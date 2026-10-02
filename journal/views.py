"""Views for creating, updating and deleting visits and notes."""

from __future__ import annotations

from typing import Any

from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from properties.mixins import HouseScopedMixin
from properties.models import House

from .forms import NoteForm, VisitForm
from .models import Note, Visit


class VisitCreateView(HouseScopedMixin, SuccessMessageMixin, CreateView):
    """Record a new visit to a house."""

    model = Visit
    form_class = VisitForm
    template_name = "journal/visit_form.html"
    success_message = "Visit recorded."
    require_editor = True

    def form_valid(self, form: VisitForm) -> HttpResponse:
        """Bind the visit to its house and author."""
        form.instance.house = self.house
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class VisitUpdateView(HouseScopedMixin, SuccessMessageMixin, UpdateView):
    """Edit a recorded visit."""

    model = Visit
    form_class = VisitForm
    template_name = "journal/visit_form.html"
    success_message = "Visit updated."
    require_editor = True

    def get_queryset(self):
        """Limit edits to visits of the current house."""
        return Visit.objects.filter(house=self.house)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class VisitDeleteView(HouseScopedMixin, DeleteView):
    """Delete a visit."""

    model = Visit
    template_name = "journal/visit_confirm_delete.html"
    context_object_name = "visit"
    require_editor = True

    def get_queryset(self):
        """Limit deletions to visits of the current house."""
        return Visit.objects.filter(house=self.house)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class NoteCreateView(HouseScopedMixin, SuccessMessageMixin, CreateView):
    """Add a free-form note to a house."""

    model = Note
    form_class = NoteForm
    template_name = "journal/note_form.html"
    success_message = "Note saved."
    require_editor = True

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the house so the visit dropdown can be filtered."""
        kwargs = super().get_form_kwargs()
        kwargs["house"] = self.house
        return kwargs

    def form_valid(self, form: NoteForm) -> HttpResponse:
        """Bind the note to its house and author."""
        form.instance.house = self.house
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class NoteUpdateView(HouseScopedMixin, SuccessMessageMixin, UpdateView):
    """Edit a note."""

    model = Note
    form_class = NoteForm
    template_name = "journal/note_form.html"
    success_message = "Note updated."
    require_editor = True

    def get_queryset(self):
        """Limit edits to notes of the current house."""
        return Note.objects.filter(house=self.house)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass the house so the visit dropdown can be filtered."""
        kwargs = super().get_form_kwargs()
        kwargs["house"] = self.house
        return kwargs

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )


class NoteDeleteView(HouseScopedMixin, DeleteView):
    """Delete a note."""

    model = Note
    template_name = "journal/note_confirm_delete.html"
    context_object_name = "note"
    require_editor = True

    def get_queryset(self):
        """Limit deletions to notes of the current house."""
        return Note.objects.filter(house=self.house)

    def get_success_url(self) -> str:
        """Redirect to the house detail page."""
        return reverse_lazy(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
