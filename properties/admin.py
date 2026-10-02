"""Admin registrations for the properties app."""

from __future__ import annotations

from django.contrib import admin

from .models import Feature, FeatureValue, House, HousePhoto, Rating


class FeatureValueInline(admin.TabularInline):
    """Inline feature values on the house admin page."""

    model = FeatureValue
    extra = 0
    autocomplete_fields = ("feature",)


class HousePhotoInline(admin.TabularInline):
    """Inline photos on the house admin page."""

    model = HousePhoto
    extra = 0
    fields = ("image", "caption", "is_primary")


class RatingInline(admin.TabularInline):
    """Inline ratings on the house admin page."""

    model = Rating
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    """Admin for houses."""

    list_display = (
        "title",
        "workspace",
        "city",
        "price_display",
        "price_per_sqm_display",
        "agent_name",
        "status",
        "avg_rating_display",
        "created_at",
    )
    list_filter = ("status", "workspace", "property_type")
    search_fields = ("title", "address", "city", "agent_name")
    inlines = [FeatureValueInline, HousePhotoInline, RatingInline]


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    """Admin for the feature catalog."""

    list_display = ("name", "workspace", "data_type", "is_predefined", "order")
    list_filter = ("workspace", "data_type", "is_predefined")
    search_fields = ("name",)


@admin.register(FeatureValue)
class FeatureValueAdmin(admin.ModelAdmin):
    """Admin for feature values."""

    list_display = ("house", "feature", "value")
    list_filter = ("feature",)
    search_fields = ("house__title", "value")


@admin.register(HousePhoto)
class HousePhotoAdmin(admin.ModelAdmin):
    """Admin for house photos."""

    list_display = ("house", "caption", "is_primary", "uploaded_by", "uploaded_at")
    list_filter = ("is_primary",)
    search_fields = ("house__title", "caption")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """Admin for ratings."""

    list_display = ("house", "user", "score", "updated_at")
    list_filter = ("score", "house__workspace")
    search_fields = ("house__title", "user__username", "comment")