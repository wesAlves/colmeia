"""Forms for houses, features, photos and ratings."""

from __future__ import annotations

from typing import Any

from django import forms
from django.forms import inlineformset_factory

from accounts.models import Workspace

from .models import Feature, FeatureValue, House, HousePhoto, Rating


class HouseForm(forms.ModelForm):
    """Create or update a :class:`House`."""

    class Meta:
        model = House
        fields = (
            "title",
            "address",
            "city",
            "country",
            "price",
            "currency",
            "property_type",
            "bedrooms",
            "bathrooms",
            "area_sqm",
            "lot_sqm",
            "year_built",
            "listing_url",
            "agent_name",
            "status",
        )
        widgets = {
            "address": forms.TextInput(attrs={"size": 60}),
        }

    def __init__(self, *args: Any, workspace: Workspace | None = None, **kwargs: Any) -> None:
        """Store the workspace for later use by the inline formset."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace


class FeatureForm(forms.ModelForm):
    """Create or update a :class:`Feature`."""

    class Meta:
        model = Feature
        fields = ("name", "data_type", "choices", "unit", "description", "order")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: Any, workspace: Workspace | None = None, **kwargs: Any) -> None:
        """Keep a reference to the owning workspace."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace

    def clean(self) -> dict[str, Any]:
        """Ensure choice features declare their options."""
        cleaned = super().clean()
        if (
                cleaned.get("data_type") == Feature.DataType.CHOICE
                and not cleaned.get("choices", "").strip()
        ):
            self.add_error("choices", "Choices are required for the 'Choice' type.")
        return cleaned


class FeatureValueForm(forms.ModelForm):
    """Edit the value of a feature for a house."""

    class Meta:
        model = FeatureValue
        fields = ("feature", "value")
        widgets = {"value": forms.TextInput()}

    def __init__(self, *args: Any, workspace: Workspace | None = None, **kwargs: Any) -> None:
        """Restrict the feature choices to the current workspace."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        if workspace is not None:
            self.fields["feature"].queryset = Feature.objects.filter(
                workspace=workspace
            ).order_by("order", "name")


FeatureValueFormSet = inlineformset_factory(
    House,
    FeatureValue,
    form=FeatureValueForm,
    fields=("feature", "value"),
    extra=1,
    can_delete=True,
)


class FeatureValueFormSetWithWorkspace(FeatureValueFormSet):  # type: ignore[misc]
    """Formset variant that forwards the workspace to every child form."""

    def __init__(self, *args: Any, workspace: Workspace | None = None, **kwargs: Any) -> None:
        """Store the workspace before instantiating the child forms."""
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index: int) -> dict[str, Any]:
        """Pass the workspace into each child form."""
        kwargs = super().get_form_kwargs(index)
        kwargs["workspace"] = self.workspace
        return kwargs


class HousePhotoForm(forms.ModelForm):
    """Upload a new photo for a house."""

    class Meta:
        model = HousePhoto
        fields = ("image", "caption", "is_primary")
        widgets = {
            "caption": forms.TextInput(attrs={"size": 60}),
        }


class RatingForm(forms.Form):
    """Upsert the current user's rating for a house.

    Declared as a plain :class:`~django.forms.Form` (not a ``ModelForm``)
    because the view is responsible for binding it to the correct
    ``(house, user)`` pair via :func:`~django.db.models.query.QuerySet.update_or_create`.
    """

    score = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={"min": 1, "max": 10}),
        help_text="1 (worst) to 10 (best).",
    )
    comment = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"size": 60}),
    )
