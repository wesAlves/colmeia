"""Forms for visits and notes."""

from __future__ import annotations

from typing import Any

from django import forms

from .models import Note, Visit


class VisitForm(forms.ModelForm):
    """Create or update a :class:`Visit`."""

    class Meta:
        model = Visit
        fields = (
            "visited_at",
            "attendees",
            "overall_impression",
            "experience",
            "considerations",
        )
        widgets = {
            "visited_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "overall_impression": forms.Textarea(attrs={"rows": 3}),
            "experience": forms.Textarea(attrs={"rows": 5}),
            "considerations": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Apply a browser friendly datetime format to the widget."""
        super().__init__(*args, **kwargs)
        self.fields["visited_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]


class NoteForm(forms.ModelForm):
    """Create or update a :class:`Note`."""

    class Meta:
        model = Note
        fields = ("title", "body", "visit")
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args: Any, house=None, **kwargs: Any) -> None:
        """Limit the visit choices to the house being annotated."""
        super().__init__(*args, **kwargs)
        if house is not None:
            self.fields["visit"].queryset = house.visits.order_by("-visited_at")

