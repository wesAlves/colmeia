"""Models describing houses, their features, photos and ratings.

A :class:`House` gains three new capabilities on top of the original design:

* :attr:`~House.agent_name` – the person responsible for the listing.
* :attr:`~House.price_per_sqm` – a computed metric for quick comparisons.
* :class:`HousePhoto` and :class:`Rating` – related models holding photos and
  per-user rankings.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _

from accounts.models import Workspace


class Feature(models.Model):
    """A reusable attribute a house can have, scoped to one workspace.

    Attributes:
        data_type: How the ``FeatureValue.value`` string must be interpreted.
        choices: Comma-separated options, only used when ``data_type`` is
            :attr:`DataType.CHOICE`.
        unit: Optional unit shown next to the value (``"m2"``, ``"EUR"``, ...).
        is_predefined: ``True`` for features seeded when the workspace was
            created, so the UI can distinguish them from user additions.
    """

    class DataType(models.TextChoices):
        """Supported value types for a feature."""

        BOOLEAN = "boolean", _("Yes / No")
        INTEGER = "integer", _("Number")
        TEXT = "text", _("Text")
        CHOICE = "choice", _("Choice")

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="features"
    )
    name = models.CharField(max_length=80)
    data_type = models.CharField(
        max_length=16, choices=DataType.choices, default=DataType.TEXT
    )
    choices = models.CharField(
        max_length=400,
        blank=True,
        help_text=_("Comma-separated list, only used for the 'Choice' type."),
    )
    unit = models.CharField(max_length=16, blank=True)
    description = models.TextField(blank=True)
    is_predefined = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("workspace", "name")
        ordering = ("order", "name")
        verbose_name = _("feature")
        verbose_name_plural = _("features")

    def __str__(self) -> str:
        return self.name

    @property
    def choice_list(self) -> list[str]:
        """Return :attr:`choices` as a clean list of strings."""
        return [c.strip() for c in self.choices.split(",") if c.strip()]

    def validate_value(self, raw: str) -> str:
        """Validate and normalise a raw string value for this feature.

        Args:
            raw: The value as entered by the user.

        Returns:
            The normalised string to store in :class:`FeatureValue`.

        Raises:
            ValidationError: If the value cannot be interpreted as
                :attr:`data_type`.
        """
        value = (raw or "").strip()
        if value == "":
            return ""

        if self.data_type == self.DataType.BOOLEAN:
            lowered = value.lower()
            if lowered in {"1", "true", "yes", "y", "on"}:
                return "true"
            if lowered in {"0", "false", "no", "n", "off"}:
                return "false"
            raise ValidationError(_("Enter yes or no."))

        if self.data_type == self.DataType.INTEGER:
            try:
                int(value)
            except ValueError as exc:
                raise ValidationError(_("Enter a whole number.")) from exc
            return value

        if self.data_type == self.DataType.CHOICE:
            options = self.choice_list
            if options and value not in options:
                raise ValidationError(
                    _("Value must be one of: %(options)s")
                    % {"options": ", ".join(options)}
                )
            return value

        return value

    def display_value(self, raw: str) -> str:
        """Return a human friendly representation of ``raw``."""
        if not raw:
            return "—"
        if self.data_type == self.DataType.BOOLEAN:
            return _("Yes") if raw == "true" else _("No")
        return f"{raw} {self.unit}".strip()


class House(models.Model):
    """A property candidate being tracked inside a workspace."""

    class Status(models.TextChoices):
        """Lifecycle of a house during the search."""

        NEW = "new", _("New")
        VISITED = "visited", _("Visited")
        SHORTLISTED = "shortlisted", _("Shortlisted")
        REJECTED = "rejected", _("Rejected")
        OFFER = "offer", _("Offer made")

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="houses"
    )
    title = models.CharField(max_length=160)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="EUR")
    property_type = models.CharField(max_length=80, blank=True)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    area_sqm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    lot_sqm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    year_built = models.PositiveSmallIntegerField(null=True, blank=True)
    listing_url = models.URLField(blank=True)
    agent_name = models.CharField(
        max_length=160,
        blank=True,
        help_text=_("Person responsible for the listing (agent, owner, …)."),
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NEW
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_houses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("house")
        verbose_name_plural = _("houses")
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self) -> str:
        return self.title

    @property
    def price_display(self) -> str:
        """Return the price formatted with its currency, or an em dash."""
        if self.price is None:
            return "—"
        return f"{self.price:,.0f} {self.currency}"

    @property
    def price_per_sqm(self) -> Decimal | None:
        """Return the price divided by the area, or ``None`` when unknown."""
        if self.price is None or self.area_sqm is None:
            return None
        if self.area_sqm <= 0:
            return None
        return (self.price / self.area_sqm).quantize(Decimal("0.01"))

    @property
    def price_per_sqm_display(self) -> str:
        """Human friendly ``price/m²`` string."""
        value = self.price_per_sqm
        if value is None:
            return "—"
        return f"{value:,.0f} {self.currency}/m²"

    @property
    def avg_rating(self) -> float | None:
        """Return the average rating across all users, or ``None``."""
        aggregate = self.ratings.aggregate(avg=Avg("score"))
        return aggregate["avg"]

    @property
    def avg_rating_display(self) -> str:
        """Format :attr:`avg_rating` for templates."""
        value = self.avg_rating
        if value is None:
            return "—"
        return f"{value:.1f}"

    @property
    def primary_photo(self) -> "HousePhoto | None":
        """Return the primary photo, or the most recent one as fallback."""
        photos = list(self.photos.all())
        if not photos:
            return None
        for photo in photos:
            if photo.is_primary:
                return photo
        return photos[0]

    def feature_map(self) -> dict[int, "FeatureValue"]:
        """Return a mapping of ``feature_id`` to :class:`FeatureValue`."""
        return {fv.feature_id: fv for fv in self.feature_values.select_related("feature")}


class FeatureValue(models.Model):
    """The value of one :class:`Feature` for one :class:`House`.

    Values are stored as strings.  See :meth:`Feature.validate_value` for the
    canonical way to validate and normalise them before saving.
    """

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="feature_values"
    )
    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("house", "feature")
        verbose_name = _("feature value")
        verbose_name_plural = _("feature values")

    def __str__(self) -> str:
        return f"{self.feature.name}: {self.value}"

    def clean(self) -> None:
        """Validate the value against the feature definition."""
        super().clean()
        if self.feature_id and self.value:
            try:
                self.value = self.feature.validate_value(self.value)
            except ValidationError as exc:
                raise ValidationError({"value": exc.messages}) from exc

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Normalise the value before persisting it."""
        if self.feature_id and self.value:
            self.value = self.feature.validate_value(self.value)
        super().save(*args, **kwargs)

    @property
    def display(self) -> str:
        """Return the value rendered for humans."""
        return self.feature.display_value(self.value)


class HousePhoto(models.Model):
    """A photo attached to a :class:`House`.

    Attributes:
        image: The uploaded image file, stored under ``media/houses/photos/``.
        caption: Optional caption shown under the thumbnail.
        is_primary: Whether this photo is the house cover.  Only one photo
            per house should have this flag set; the view enforces it.
    """

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to="houses/photos/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_photos",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_primary", "-uploaded_at")
        verbose_name = _("house photo")
        verbose_name_plural = _("house photos")

    def __str__(self) -> str:
        return self.caption or f"Photo of {self.house}"


class Rating(models.Model):
    """A per-user ranking of a house.

    Each member of the workspace can hold exactly one rating per house.
    The overall ranking shown in the UI is the average of every rating.
    """

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("Score from 1 (worst) to 10 (best)."),
    )
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("house", "user")
        ordering = ("-score", "user__username")
        verbose_name = _("rating")
        verbose_name_plural = _("ratings")

    def __str__(self) -> str:
        return f"{self.user} → {self.house}: {self.score}/10"