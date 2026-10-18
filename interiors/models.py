"""Models for interior design projects, rooms, items, options and moodboards.

This module provides the data structures to manage interior design and decoration
projects scoped to a workspace and associated with a property (House):

* :class:`InteriorProject`: Top-level interior project linked to a workspace and house.
* :class:`Room`: Specific spaces/divisions within an interior project.
* :class:`Item`: Furniture, appliances, decor, or fixed elements needed for a room.
* :class:`Option`: Purchase options and alternatives researched for an item.
* :class:`MoodboardImage`: Visual inspirations, palettes, and moodboard items for a room.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from accounts.models import Workspace
from properties.models import House


class Style(models.Model):
    """An interior design aesthetic or style (e.g. Scandinavian, Industrial).

    Attributes:
        name: Name of the interior design style.
        slug: Unique URL/identifier slug for filtering and tagging.
    """

    DEFAULT_STYLES = [
        ("Escandinavo", "escandinavo"),
        ("Industrial", "industrial"),
        ("Minimalista", "minimalista"),
        ("Japandi", "japandi"),
        ("Boho", "boho"),
        ("Clássico", "classico"),
        ("Contemporâneo", "contemporaneo"),
    ]

    name = models.CharField(
        max_length=80,
        verbose_name=_("name"),
    )
    slug = models.SlugField(
        max_length=80,
        unique=True,
        verbose_name=_("slug"),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("style")
        verbose_name_plural = _("styles")

    def __str__(self) -> str:
        """Return the style name."""
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensure slug is populated before saving."""
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class InteriorProject(models.Model):
    """An interior design or renovation project scoped to a workspace and house.

    Attributes:
        workspace: The workspace this project belongs to.
        house: The house/property being designed or renovated.
        title: The display title of the interior design project.
        budget: Optional overall monetary budget allocated for the project.
        currency: Currency code for the project budget and items (default: 'EUR').
        created_at: Timestamp when the project was created.
        updated_at: Timestamp when the project was last modified.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="interior_projects",
        verbose_name=_("workspace"),
    )
    house = models.ForeignKey(
        House,
        on_delete=models.CASCADE,
        related_name="interior_projects",
        verbose_name=_("house"),
    )
    title = models.CharField(
        max_length=160,
        verbose_name=_("title"),
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("budget"),
    )
    currency = models.CharField(
        max_length=3,
        default="EUR",
        verbose_name=_("currency"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        ordering = ("title",)
        verbose_name = _("interior project")
        verbose_name_plural = _("interior projects")

    def __str__(self) -> str:
        """Return a string representation of the interior project."""
        return self.title

    @property
    def budget_display(self) -> str:
        """Return the budget formatted with its currency or an em dash."""
        if self.budget is None:
            return "—"
        return f"{self.budget:,.2f} {self.currency}"

    @property
    def remaining_budget(self) -> Decimal | None:
        """Return remaining budget (budget - total_estimated_cost), or None if budget is unset."""
        if self.budget is None:
            return None
        return self.budget - self.total_estimated_cost

    @property
    def remaining_budget_display(self) -> str:
        """Return remaining budget formatted with currency or an em dash."""
        rem = self.remaining_budget
        if rem is None:
            return "—"
        return f"{rem:,.2f} {self.currency}"

    @property
    def budget_status(self) -> str:
        """Return 'under' if remaining budget >= 0, 'over' if negative, and 'unset' if budget is None."""
        rem = self.remaining_budget
        if rem is None:
            return "unset"
        if rem >= Decimal("0.00"):
            return "under"
        return "over"

    @property
    def total_estimated_cost(self) -> Decimal:
        """Calculate the total cost of all chosen options across all rooms."""
        total = Decimal("0.00")
        for room in self.rooms.all():
            total += room.total_estimated_cost
        return total

    @property
    def total_estimated_cost_display(self) -> str:
        """Return total estimated cost formatted with currency."""
        return f"{self.total_estimated_cost:,.2f} {self.currency}"

    @property
    def total_estimated_cost_with_fallback(self) -> Decimal:
        """Sum cost of chosen options, falling back to average of candidate options when unchosen."""
        total = Decimal("0.00")
        for room in self.rooms.all():
            total += room.total_estimated_cost_with_fallback
        return total

    @property
    def total_estimated_cost_with_fallback_display(self) -> str:
        """Return fallback estimated cost formatted with currency."""
        return f"{self.total_estimated_cost_with_fallback:,.2f} {self.currency}"


class Room(models.Model):
    """A specific division or space inside an interior project.

    Attributes:
        project: The parent interior project this room belongs to.
        name: Name of the room (e.g. 'Living Room', 'Master Bedroom').
        order: Ordering index for display purposes.
        priority: Priority tier for this room (ESSENTIAL, IMPORTANT, DESIRABLE, DREAM).
        budget: Optional dedicated financial budget allocated for this room.
        concept_title: Concept or aesthetic vision headline.
        concept_description: Narrative description of the room concept and mood.
        area_sqm: Total floor surface area in square meters.
        width_m: Room width in meters.
        length_m: Room length in meters.
        height_m: Ceiling height in meters.
        floor_material: Flooring material or finish (e.g. 'Hardwood', 'Microcement').
        floor_color_hex: Primary floor color hex code.
        baseboard_color_hex: Baseboard trim color hex code.
        ceiling_color_hex: Ceiling paint/finish color hex code.
        wall_color_hex: Primary wall paint/finish color hex code (e.g. '#F4F1EA').
        lighting_notes: Technical notes on natural light and lighting fixtures.
        palette_colors: List of structured palette colors [{"hex": "#F4F1EA", "role": "dominant"}, ...].
        created_at: Timestamp when the room was created.
        updated_at: Timestamp when the room was last modified.
    """

    class Priority(models.IntegerChoices):
        """Priority levels for rooms."""

        ESSENTIAL = 1, _("Essential")
        IMPORTANT = 2, _("Important")
        DESIRABLE = 3, _("Desirable")
        DREAM = 4, _("Dream")

    project = models.ForeignKey(
        InteriorProject,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name=_("project"),
    )
    name = models.CharField(
        max_length=120,
        verbose_name=_("name"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("order"),
    )
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.IMPORTANT,
        blank=True,
        verbose_name=_("priority"),
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("budget"),
    )
    concept_title = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("concept title"),
    )
    concept_description = models.TextField(
        blank=True,
        verbose_name=_("concept description"),
    )
    area_sqm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("area (sqm)"),
    )
    width_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("width (m)"),
    )
    length_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("length (m)"),
    )
    height_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("height (m)"),
    )
    floor_material = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("floor material"),
    )
    floor_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("floor color hex"),
    )
    baseboard_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("baseboard color hex"),
    )
    ceiling_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("ceiling color hex"),
    )
    wall_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("wall color hex"),
    )
    lighting_notes = models.TextField(
        blank=True,
        verbose_name=_("lighting notes"),
    )
    palette_colors = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("palette colors"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        ordering = ("order", "name")
        verbose_name = _("room")
        verbose_name_plural = _("rooms")

    def __str__(self) -> str:
        """Return the room name."""
        return self.name

    def clean(self) -> None:
        """Validate room fields such as palette colors structure and limit."""
        super().clean()
        if self.palette_colors:
            if not isinstance(self.palette_colors, list):
                raise ValidationError({"palette_colors": _("Palette colors must be a list.")})
            if len(self.palette_colors) > 7:
                raise ValidationError({"palette_colors": _("A maximum of 7 colors can be stored in the palette.")})
            for entry in self.palette_colors:
                if not isinstance(entry, dict) or "hex" not in entry:
                    raise ValidationError(
                        {"palette_colors": _("Each palette color must be an object containing a 'hex' key.")}
                    )

    @property
    def workspace(self) -> Workspace:
        """Return the workspace associated with this room."""
        return self.project.workspace

    @property
    def priority_display(self) -> str:
        """Return human-readable label for room priority."""
        return self.get_priority_display()

    @property
    def budget_display(self) -> str:
        """Return the room budget formatted with project currency or an em dash."""
        if self.budget is None:
            return "—"
        try:
            currency = self.project.currency
        except (AttributeError, ObjectDoesNotExist):
            currency = "EUR"
        return f"{self.budget:,.2f} {currency}"

    @property
    def items_by_priority(self) -> dict[int, list[Item]]:
        """Group room items by priority tier."""
        grouped: dict[int, list[Item]] = {p.value: [] for p in Item.Priority}
        for item in self.items.all():
            grouped.setdefault(item.priority, []).append(item)
        return grouped

    @property
    def total_estimated_cost(self) -> Decimal:
        """Calculate the sum of prices of chosen options for items in this room."""
        total = Decimal("0.00")
        for item in self.items.all():
            if item.price is not None:
                total += item.price
        return total

    @property
    def total_estimated_cost_display(self) -> str:
        """Return total room estimated cost formatted with currency."""
        currency = self.project.currency if self.project else "EUR"
        return f"{self.total_estimated_cost:,.2f} {currency}"

    @property
    def total_estimated_cost_with_fallback(self) -> Decimal:
        """Calculate total room estimated cost with fallback to option price averages."""
        total = Decimal("0.00")
        for item in self.items.all():
            fallback = item.estimated_cost_with_fallback
            if fallback is not None:
                total += fallback
        return total

    @property
    def total_estimated_cost_with_fallback_display(self) -> str:
        """Return fallback estimated cost formatted with currency."""
        currency = self.project.currency if self.project else "EUR"
        return f"{self.total_estimated_cost_with_fallback:,.2f} {currency}"


class Item(models.Model):
    """An object, piece of furniture, appliance, or decoration for a room.

    Attributes:
        room: The room where this item belongs.
        name: Name or description of the item (e.g. '3-Seater Sofa').
        category: Category of item (FURNITURE, APPLIANCE, DECOR, FIXED).
        priority: Importance level (ESSENTIAL, IMPORTANT, DESIRABLE, DREAM).
        status: Progress state (TODO, RESEARCHING, CHOSEN, PURCHASED).
        connection_type: Technical utility requirements (Electrical, Gas, Plumbing, etc.).
        requires_wall_anchor: Flag indicating if safety wall drilling/anchoring is required.
        depends_on: Another item this item technically or functionally depends on.
        dependency_type: Nature of dependency (Electrical, Plumbing, Structural, Functional).
        is_fixed: Flag indicating whether this is a fixed built-in fixture.
        is_custom_made: Flag indicating bespoke / custom carpentry or manufacturing.
        style: Aesthetic styles associated with this item.
        custom_style_text: Optional custom free-form style text.
        width_cm: Width specification in centimeters.
        depth_cm: Depth specification in centimeters.
        height_cm: Height specification in centimeters.
        material: Dominant materials or fabrication details.
        color_hex: Primary color hex code (e.g. '#A1B2C3').
        notes: Free-form notes and specifications.
        created_at: Timestamp when the item was created.
        updated_at: Timestamp when the item was last modified.
    """

    class Category(models.TextChoices):
        """Categories for interior items."""

        FURNITURE = "furniture", _("Furniture")
        APPLIANCE = "appliance", _("Appliance")
        DECOR = "decor", _("Decor")
        FIXED = "fixed", _("Fixed")

    class Priority(models.IntegerChoices):
        """Priority levels for interior items."""

        ESSENTIAL = 1, _("Essential")
        IMPORTANT = 2, _("Important")
        DESIRABLE = 3, _("Desirable")
        DREAM = 4, _("Dream")

    class Status(models.TextChoices):
        """Workflow status of an interior item."""

        TODO = "todo", _("To Do")
        RESEARCHING = "researching", _("Researching")
        CHOSEN = "chosen", _("Chosen")
        PURCHASED = "purchased", _("Purchased")

    class ConnectionType(models.TextChoices):
        """Technical connection requirements."""

        NONE = "none", _("None")
        ELECTRICAL_110 = "electrical_110", _("Electrical 110V")
        ELECTRICAL_220 = "electrical_220", _("Electrical 220V")
        GAS_GLP = "gas_glp", _("Gas GLP (Bottled)")
        GAS_NATURAL = "gas_natural", _("Gas Natural (Piped)")
        PLUMBING = "plumbing", _("Plumbing")

    class DependencyType(models.TextChoices):
        """Type of technical or functional dependency."""

        ELECTRICAL = "electrical", _("Electrical")
        PLUMBING = "plumbing", _("Plumbing")
        STRUCTURAL = "structural", _("Structural")
        FUNCTIONAL = "functional", _("Functional")

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("room"),
    )
    name = models.CharField(
        max_length=160,
        verbose_name=_("name"),
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.FURNITURE,
        blank=True,
        verbose_name=_("category"),
    )
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.IMPORTANT,
        blank=True,
        verbose_name=_("priority"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        blank=True,
        verbose_name=_("status"),
    )
    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        default=ConnectionType.NONE,
        blank=True,
        verbose_name=_("connection type"),
    )
    requires_wall_anchor = models.BooleanField(
        default=False,
        verbose_name=_("requires wall anchor"),
    )
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
        verbose_name=_("depends on"),
    )
    dependency_type = models.CharField(
        max_length=20,
        choices=DependencyType.choices,
        blank=True,
        verbose_name=_("dependency type"),
    )
    is_fixed = models.BooleanField(
        default=False,
        verbose_name=_("is fixed"),
    )
    is_custom_made = models.BooleanField(
        default=False,
        verbose_name=_("is custom made"),
    )
    style = models.ManyToManyField(
        Style,
        blank=True,
        related_name="items",
        verbose_name=_("styles"),
    )
    custom_style_text = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("custom style text"),
    )
    width_cm = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("width (cm)"),
    )
    depth_cm = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("depth (cm)"),
    )
    height_cm = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("height (cm)"),
    )
    material = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("material"),
    )
    color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("color hex"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        ordering = ("priority", "name")
        verbose_name = _("item")
        verbose_name_plural = _("items")

    def __str__(self) -> str:
        """Return the item name."""
        return self.name

    @property
    def workspace(self) -> Workspace:
        """Return the workspace associated with this item."""
        return self.room.project.workspace

    @property
    def priority_display(self) -> str:
        """Return human-readable label for priority."""
        return self.get_priority_display()

    @property
    def category_display(self) -> str:
        """Return human-readable label for category."""
        return self.get_category_display()

    @property
    def status_display(self) -> str:
        """Return human-readable label for status."""
        return self.get_status_display()

    @property
    def connection_type_display(self) -> str:
        """Return human-readable label for connection type."""
        return self.get_connection_type_display()

    @property
    def dependency_type_display(self) -> str:
        """Return human-readable label for dependency type."""
        return self.get_dependency_type_display()

    @property
    def styles_display(self) -> str:
        """Return comma-separated string of associated style names."""
        names = [s.name for s in self.style.all()]
        if self.custom_style_text:
            names.append(self.custom_style_text)
        return ", ".join(names) if names else "—"

    @property
    def chosen_option(self) -> Option | None:
        """Return the option marked as chosen, if any."""
        return self.options.filter(is_chosen=True).first()

    @property
    def price(self) -> Decimal | None:
        """Return the price of the chosen option, or None."""
        chosen = self.chosen_option
        return chosen.price if chosen else None

    @property
    def price_display(self) -> str:
        """Return the price of the chosen option formatted with currency."""
        chosen = self.chosen_option
        if chosen is None or chosen.price is None:
            return "—"
        return chosen.price_display

    @property
    def estimated_cost_with_fallback(self) -> Decimal | None:
        """Return chosen option price, or average price of available options if none chosen."""
        if self.price is not None:
            return self.price
        priced_options = [opt.price for opt in self.options.all() if opt.price is not None]
        if priced_options:
            return sum(priced_options) / Decimal(len(priced_options))
        return None

    @property
    def estimated_cost_with_fallback_display(self) -> str:
        """Return fallback cost formatted with currency or an em dash."""
        cost = self.estimated_cost_with_fallback
        if cost is None:
            return "—"
        try:
            currency = self.room.project.currency
        except (AttributeError, ObjectDoesNotExist):
            currency = "EUR"
        return f"{cost:,.2f} {currency}"


class Option(models.Model):
    """A purchase option or candidate product for an interior item.

    Attributes:
        item: The interior item this option is for.
        name: Name or description of the product option.
        price: Price of this purchase option.
        store: Store, retailer or vendor name.
        url: Direct link to the product listing.
        finish: Material finish or texture (e.g. 'Walnut', 'Bouclé').
        lead_time_days: Delivery lead time in days.
        fits_palette: Flag indicating whether this option aligns with room color palette.
        fits_style: Flag indicating whether this option matches room design style.
        selected_palette_color_hex: The specific palette color hex selected for this option.
        is_chosen: Whether this option was selected as the final choice.
        added_by: User who suggested/added this option.
        created_at: Timestamp when this option was created.
        updated_at: Timestamp when this option was last modified.
    """

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("item"),
    )
    name = models.CharField(
        max_length=160,
        verbose_name=_("name"),
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("price"),
    )
    store = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("store"),
    )
    url = models.URLField(
        blank=True,
        verbose_name=_("URL"),
    )
    finish = models.CharField(
        max_length=80,
        blank=True,
        verbose_name=_("finish"),
    )
    lead_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("lead time (days)"),
    )
    fits_palette = models.BooleanField(
        default=True,
        verbose_name=_("fits palette"),
    )
    fits_style = models.BooleanField(
        default=True,
        verbose_name=_("fits style"),
    )
    selected_palette_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("selected palette color hex"),
    )
    is_chosen = models.BooleanField(
        default=False,
        verbose_name=_("is chosen"),
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interior_options",
        verbose_name=_("added by"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        ordering = ("-is_chosen", "price", "name")
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def __str__(self) -> str:
        """Return the option name."""
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the option and ensure only one option is chosen per item."""
        super().save(*args, **kwargs)
        if self.is_chosen and self.item_id:
            Option.objects.filter(item_id=self.item_id, is_chosen=True).exclude(
                pk=self.pk
            ).update(is_chosen=False)

    @property
    def workspace(self) -> Workspace:
        """Return the workspace associated with this option."""
        return self.item.room.project.workspace

    @property
    def price_display(self) -> str:
        """Return the price formatted with its project currency or an em dash."""
        if self.price is None:
            return "—"
        try:
            currency = self.item.room.project.currency
        except (AttributeError, ObjectDoesNotExist):
            currency = "EUR"
        return f"{self.price:,.2f} {currency}"

    @property
    def primary_image(self) -> OptionImage | None:
        """Return the cover image or the first available option image."""
        cover = self.images.filter(is_cover=True).first()
        if cover is not None:
            return cover
        return self.images.first()

    @property
    def avg_rating(self) -> float | None:
        """Return the average rating score across all user reviews, or None if unrated."""
        ratings = list(self.ratings.all())
        if not ratings:
            return None
        return round(sum(r.score for r in ratings) / len(ratings), 1)

    @property
    def avg_rating_display(self) -> str:
        """Return formatted average rating string (e.g. '8.5/10') or an em dash."""
        avg = self.avg_rating
        if avg is None:
            return "—"
        return f"{avg:g}/10"

    @property
    def rating_count(self) -> int:
        """Return total number of ratings submitted for this option."""
        return self.ratings.count()


class OptionRating(models.Model):
    """An evaluation and numerical score (1-10) for a purchase option.

    Attributes:
        option: The option being evaluated.
        user: The user providing the rating and feedback.
        score: Rating score from 1 to 10.
        comment: Optional short feedback comment.
        created_at: Timestamp when rating was submitted.
        updated_at: Timestamp when rating was last updated.
    """

    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name="ratings",
        verbose_name=_("option"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="option_ratings",
        verbose_name=_("user"),
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_("score"),
    )
    comment = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("comment"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        ordering = ("-score",)
        unique_together = ("option", "user")
        verbose_name = _("option rating")
        verbose_name_plural = _("option ratings")

    def __str__(self) -> str:
        """Return string representation of the option rating."""
        return f"{self.score}/10 by {self.user} for {self.option.name}"


class OptionImage(models.Model):
    """An uploaded photo or rendering associated with a purchase option.

    Attributes:
        option: The parent purchase option.
        image: Uploaded product photo file.
        is_cover: Flag indicating if this image is selected as cover/primary image.
        uploaded_at: Timestamp when this image was uploaded.
    """

    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("option"),
    )
    image = models.ImageField(
        upload_to="interiors/options/",
        verbose_name=_("image"),
    )
    is_cover = models.BooleanField(
        default=False,
        verbose_name=_("is cover"),
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("uploaded at"),
    )

    class Meta:
        ordering = ("-is_cover", "uploaded_at")
        verbose_name = _("option image")
        verbose_name_plural = _("option images")

    def __str__(self) -> str:
        """Return string representation of the option image."""
        return f"Image for {self.option.name}"

    @property
    def url(self) -> str:
        """Return image URL if file exists."""
        return self.image.url if self.image else ""


class MoodboardImage(models.Model):
    """An inspiration image or visual reference for a room's moodboard.

    Attributes:
        room: The room this moodboard image belongs to.
        image: Uploaded image file.
        caption: Optional caption or description.
        hex_color: Hex color code (e.g. '#A1B2C3') extracted from the image.
        order: Sequence ordering for displaying the moodboard mosaic.
        is_cover: Flag indicating if this image is selected as cover image.
        added_by: User who uploaded the image.
        created_at: Timestamp when the moodboard image was added.
    """

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="moodboard_images",
        verbose_name=_("room"),
    )
    image = models.ImageField(
        upload_to="interiors/moodboard/",
        verbose_name=_("image"),
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("caption"),
    )
    hex_color = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("hex color"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("order"),
    )
    is_cover = models.BooleanField(
        default=False,
        verbose_name=_("is cover"),
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="moodboard_images",
        verbose_name=_("added by"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        ordering = ("order", "-created_at")
        verbose_name = _("moodboard image")
        verbose_name_plural = _("moodboard images")

    def __str__(self) -> str:
        """Return a string representation for the moodboard image."""
        return self.caption or f"Moodboard image for {self.room.name}"

    @property
    def workspace(self) -> Workspace:
        """Return the workspace associated with this moodboard image."""
        return self.room.project.workspace

    @property
    def color_display(self) -> str:
        """Return the hex color or an em dash."""
        return self.hex_color if self.hex_color else "—"

    @property
    def url(self) -> str:
        """Return the URL of the uploaded image if present."""
        return self.image.url if self.image else ""
