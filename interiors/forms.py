"""Forms for interior projects, rooms, items and options."""

from __future__ import annotations

import json
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import Workspace
from properties.models import House

from .models import (
    InteriorProject,
    Item,
    MoodboardImage,
    Option,
    OptionImage,
    OptionRating,
    Room,
    Style,
)


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

    priority = forms.TypedChoiceField(
        choices=Room.Priority.choices,
        coerce=int,
        initial=Room.Priority.IMPORTANT,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    palette_colors = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control font-monospace small",
                "rows": 3,
                "placeholder": _(
                    '[{"hex": "#F4F1EA", "role": "dominant"}, {"hex": "#8B7355", "role": "accent"}]'
                ),
            }
        ),
        help_text=_(
            "Optional JSON list of up to 7 color objects with 'hex' keys."
        ),
    )

    class Meta:
        model = Room
        fields = (
            "name",
            "order",
            "priority",
            "budget",
            "concept_title",
            "concept_description",
            "area_sqm",
            "width_m",
            "length_m",
            "height_m",
            "floor_material",
            "floor_color_hex",
            "baseboard_color_hex",
            "ceiling_color_hex",
            "wall_color_hex",
            "lighting_notes",
            "palette_colors",
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
            "priority": forms.Select(attrs={"class": "form-select"}),
            "budget": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
            "concept_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Japandi Serenity, Warm Organic Modernism"),
                }
            ),
            "concept_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Atmosphere, design intention, textures and mood..."),
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
            "floor_color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#E3D5C5",
                    "maxlength": 7,
                }
            ),
            "baseboard_color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#FFFFFF",
                    "maxlength": 7,
                }
            ),
            "ceiling_color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#FAFAFA",
                    "maxlength": 7,
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
        """Initialize form, keep workspace reference, and format initial palette_colors."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        if self.instance and self.instance.pk and self.instance.palette_colors:
            if isinstance(self.instance.palette_colors, (list, dict)):
                self.initial["palette_colors"] = json.dumps(
                    self.instance.palette_colors, indent=2, ensure_ascii=False
                )

    def clean_priority(self) -> int:
        """Ensure priority defaults to IMPORTANT if omitted."""
        val = self.cleaned_data.get("priority")
        if val in (None, ""):
            return Room.Priority.IMPORTANT
        return int(val)

    def clean_palette_colors(self) -> list[dict[str, Any]]:
        """Validate and parse palette_colors input into a list of max 7 color dicts."""
        data = self.cleaned_data.get("palette_colors")
        if not data:
            return []
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    _("Invalid JSON format for palette colors: %(error)s"),
                    params={"error": str(exc)},
                )
        else:
            parsed = data

        if not isinstance(parsed, list):
            raise ValidationError(_("Palette colors must be provided as a JSON list."))

        if len(parsed) > 7:
            raise ValidationError(
                _("A maximum of 7 colors can be stored in the palette (received %(count)d)."),
                params={"count": len(parsed)},
            )

        validated: list[dict[str, Any]] = []
        for item in parsed:
            if isinstance(item, str):
                item = {"hex": item.strip()}
            if not isinstance(item, dict) or "hex" not in item:
                raise ValidationError(
                    _("Each palette color must be an object with at least a 'hex' key.")
                )
            validated.append(item)
        return validated


class ItemForm(forms.ModelForm):
    """Create or update an :class:`Item` within a room."""

    style = forms.ModelMultipleChoiceField(
        queryset=Style.objects.all(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={"class": "form-select", "size": "4"}
        ),
        label=_("Styles"),
    )

    class Meta:
        model = Item
        fields = (
            "name",
            "category",
            "priority",
            "status",
            "is_fixed",
            "is_custom_made",
            "connection_type",
            "requires_wall_anchor",
            "depends_on",
            "dependency_type",
            "style",
            "custom_style_text",
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
            "connection_type": forms.Select(attrs={"class": "form-select"}),
            "requires_wall_anchor": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "depends_on": forms.Select(attrs={"class": "form-select"}),
            "dependency_type": forms.Select(attrs={"class": "form-select"}),
            "custom_style_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Custom Organic Japandi"),
                }
            ),
            "is_fixed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_custom_made": forms.CheckboxInput(attrs={"class": "form-check-input"}),
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
        self,
        *args: Any,
        workspace: Workspace | None = None,
        room: Room | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize form, keep workspace reference, and scope depends_on choices."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.room = room or (self.instance.room if self.instance and self.instance.pk else None)

        depends_qs = Item.objects.all()
        if self.room:
            depends_qs = depends_qs.filter(room__project=self.room.project)
        elif self.workspace:
            depends_qs = depends_qs.filter(room__project__workspace=self.workspace)

        if self.instance and self.instance.pk:
            depends_qs = depends_qs.exclude(pk=self.instance.pk)

        self.fields["depends_on"].queryset = depends_qs
        self.fields["depends_on"].empty_label = _("— No dependency —")

    def clean_category(self) -> str:
        """Ensure category defaults to FURNITURE if omitted."""
        return self.cleaned_data.get("category") or Item.Category.FURNITURE

    def clean_priority(self) -> int:
        """Ensure priority defaults to IMPORTANT if omitted."""
        val = self.cleaned_data.get("priority")
        if val in (None, ""):
            return Item.Priority.IMPORTANT
        return int(val)

    def clean_status(self) -> str:
        """Ensure status defaults to TODO if omitted."""
        return self.cleaned_data.get("status") or Item.Status.TODO

    def clean_connection_type(self) -> str:
        """Ensure connection type defaults to NONE if omitted."""
        return self.cleaned_data.get("connection_type") or Item.ConnectionType.NONE


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
            "fits_palette",
            "fits_style",
            "selected_palette_color_hex",
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
            "fits_palette": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "fits_style": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "selected_palette_color_hex": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "#F4F1EA",
                    "maxlength": 7,
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


class OptionRatingForm(forms.ModelForm):
    """Form to submit or edit an evaluation rating (1-10) for a purchase option."""

    score = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
                "max": 10,
                "placeholder": "1 - 10",
            }
        ),
        label=_("Score (1 to 10)"),
        help_text=_("Rate this option between 1 and 10."),
    )

    class Meta:
        model = OptionRating
        fields = ("score", "comment")
        widgets = {
            "comment": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. Great quality and fits our budget!"),
                    "maxlength": 255,
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
