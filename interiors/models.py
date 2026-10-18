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
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Workspace
from properties.models import House


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


class Room(models.Model):
    """A specific division or space inside an interior project.

    Attributes:
        project: The parent interior project this room belongs to.
        name: Name of the room (e.g. 'Living Room', 'Master Bedroom').
        order: Ordering index for display purposes.
        area_sqm: Total floor surface area in square meters.
        width_m: Room width in meters.
        length_m: Room length in meters.
        height_m: Ceiling height in meters.
        floor_material: Flooring material or finish (e.g. 'Hardwood', 'Microcement').
        wall_color_hex: Primary wall paint/finish color hex code (e.g. '#F4F1EA').
        lighting_notes: Technical notes on natural light and lighting fixtures.
        created_at: Timestamp when the room was created.
        updated_at: Timestamp when the room was last modified.
    """

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
    wall_color_hex = models.CharField(
        max_length=7,
        blank=True,
        verbose_name=_("wall color hex"),
    )
    lighting_notes = models.TextField(
        blank=True,
        verbose_name=_("lighting notes"),
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

    @property
    def workspace(self) -> Workspace:
        """Return the workspace associated with this room."""
        return self.project.workspace

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


class Item(models.Model):
    """An object, piece of furniture, appliance, or decoration for a room.

    Attributes:
        room: The room where this item belongs.
        name: Name or description of the item (e.g. '3-Seater Sofa').
        category: Category of item (FURNITURE, APPLIANCE, DECOR, FIXED).
        priority: Importance level (ESSENTIAL, IMPORTANT, DESIRABLE, DREAM).
        status: Progress state (TODO, RESEARCHING, CHOSEN, PURCHASED).
        is_fixed: Flag indicating whether this is a fixed built-in fixture.
        is_custom_made: Flag indicating bespoke / custom carpentry or manufacturing.
        style: Aesthetic or design style (e.g. 'Scandinavian', 'Industrial').
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
        verbose_name=_("category"),
    )
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.IMPORTANT,
        verbose_name=_("priority"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name=_("status"),
    )
    is_fixed = models.BooleanField(
        default=False,
        verbose_name=_("is fixed"),
    )
    is_custom_made = models.BooleanField(
        default=False,
        verbose_name=_("is custom made"),
    )
    style = models.CharField(
        max_length=80,
        blank=True,
        verbose_name=_("style"),
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
