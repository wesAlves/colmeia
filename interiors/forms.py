"""Forms for interior projects, rooms, items and options."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import Workspace
from properties.models import House

from .models import InteriorProject, Item, MoodboardImage, Option, OptionImage, Room


class InteriorProjectForm(forms.ModelForm):
    """Create or update an :class:`InteriorProject`.

    Attributes:
        workspace: The workspace used to restrict the house choices.
    """

    class Meta:
        model = InteriorProject
        fields = ("title", "house", "budget", "currency")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Full Renovation or Living Room Redesign"),
                }
            ),
            "house": forms.Select(attrs={"class": "form-select"}),
            "budget": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "currency": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "EUR"}
            ),
        }

    def __init__(
        self, *args: Any, workspace: Workspace | None = None, **kwargs: Any
    ) -> None:
        """Filter house choices by workspace and configure selection options."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        if workspace is not None:
            self.fields["house"].queryset = House.objects.filter(workspace=workspace)
        self.fields["house"].empty_label = _("— Choose house —")


class RoomForm(forms.ModelForm):
    """Create or update a :class:`Room` within an interior project."""

    class Meta:
        model = Room
        fields = (
            "name",
            "order",
            "area_sqm",
            "width_m",
            "length_m",
            "height_m",
            "floor_material",
            "wall_color_hex",
            "lighting_notes",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Living Room, Master Bedroom, Kitchen"),
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "min": 0,
                }
            ),
            "area_sqm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "width_m": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "length_m": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "height_m": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "floor_material": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Hardwood, Microcement, Polished Concrete, Tile"),
                }
            ),
            "wall_color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#F4F1EA",
                    "maxlength": 7,
                }
            ),
            "lighting_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Natural lighting orientation, fixtures, warm dimming..."),
                }
            ),
        }

    def __init__(
        self, *args: Any, workspace: Workspace | None = None, **kwargs: Any
    ) -> None:
        """Initialize form and keep workspace reference."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace


class ItemForm(forms.ModelForm):
    """Create or update an :class:`Item` within a room."""

    class Meta:
        model = Item
        fields = (
            "name",
            "category",
            "priority",
            "status",
            "is_fixed",
            "is_custom_made",
            "style",
            "width_cm",
            "depth_cm",
            "height_cm",
            "material",
            "color_hex",
            "notes",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Dining Table, Pendant Light, Bookshelf"),
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_fixed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_custom_made": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "style": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Scandinavian, Mid-Century, Industrial, Japandi"),
                }
            ),
            "width_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "min": 0,
                }
            ),
            "depth_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "min": 0,
                }
            ),
            "height_cm": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "min": 0,
                }
            ),
            "material": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Solid Oak, Bouclé Fabric, Brass, Linen"),
                }
            ),
            "color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#D8C7B5",
                    "maxlength": 7,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Optional specifications, dimensions or design notes..."),
                }
            ),
        }

    def __init__(
        self, *args: Any, workspace: Workspace | None = None, **kwargs: Any
    ) -> None:
        """Initialize form and keep workspace reference."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace


class OptionForm(forms.ModelForm):
    """Create or update an :class:`Option` candidate purchase for an item."""

    class Meta:
        model = Option
        fields = (
            "name",
            "price",
            "store",
            "url",
            "finish",
            "lead_time_days",
            "is_chosen",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. IKEA STRANDMON Wing Chair, Zara Home Linen Rug"),
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "store": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. IKEA, Zara Home, West Elm, Amazon"),
                }
            ),
            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://...",
                }
            ),
            "finish": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Walnut, Bouclé, Matte Black, Travertine"),
                }
            ),
            "lead_time_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "14",
                    "min": 0,
                }
            ),
            "is_chosen": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(
        self, *args: Any, workspace: Workspace | None = None, **kwargs: Any
    ) -> None:
        """Initialize form and keep workspace reference."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace


class OptionImageForm(forms.ModelForm):
    """Form for adding or editing an image attachment on an Option."""

    class Meta:
        model = OptionImage
        fields = ("image", "is_cover")
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_cover": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


BaseOptionImageFormSet = forms.inlineformset_factory(
    Option,
    OptionImage,
    form=OptionImageForm,
    extra=5,
    max_num=5,
    can_delete=True,
)
OptionImageFormSet = BaseOptionImageFormSet


class MoodboardImageForm(forms.ModelForm):
    """Create or update a :class:`MoodboardImage` for a room."""

    class Meta:
        model = MoodboardImage
        fields = ("image", "caption", "hex_color")
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "caption": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Scandinavian palette, warm minimalist textures"),
                }
            ),
            "hex_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#D8C7B5",
                    "maxlength": 7,
                }
            ),
        }

    def __init__(
        self, *args: Any, workspace: Workspace | None = None, **kwargs: Any
    ) -> None:
        """Initialize form and keep workspace reference."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace


ProjectForm = InteriorProjectForm
