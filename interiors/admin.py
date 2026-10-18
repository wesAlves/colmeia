"""Admin registrations for the interiors app."""

from __future__ import annotations

from django.contrib import admin

from .models import (
    InteriorProject,
    Item,
    MoodboardImage,
    Option,
    OptionImage,
    Room,
)


class RoomInline(admin.TabularInline):
    """Inline rooms on the interior project admin page."""

    model = Room
    extra = 1
    fields = (
        "name",
        "order",
        "area_sqm",
        "width_m",
        "length_m",
        "height_m",
        "floor_material",
        "wall_color_hex",
    )


class ItemInline(admin.TabularInline):
    """Inline items on the room admin page."""

    model = Item
    extra = 1
    fields = (
        "name",
        "category",
        "priority",
        "status",
        "is_fixed",
        "is_custom_made",
        "style",
        "material",
        "color_hex",
    )


class OptionImageInline(admin.TabularInline):
    """Inline product photos on the option admin page."""

    model = OptionImage
    extra = 1
    fields = ("image", "is_cover", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(InteriorProject)
class InteriorProjectAdmin(admin.ModelAdmin):
    """Admin configuration for interior projects."""

    list_display = (
        "title",
        "house",
        "budget_display",
        "total_estimated_cost_display",
    )
    list_select_related = ("house", "workspace")
    list_filter = ("workspace", "house")
    search_fields = ("title", "house__title")
    inlines = [RoomInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Admin configuration for rooms."""

    list_display = (
        "name",
        "project",
        "order",
        "area_sqm",
        "width_m",
        "length_m",
        "height_m",
        "floor_material",
        "wall_color_hex",
        "total_estimated_cost_display",
    )
    list_select_related = ("project", "project__workspace")
    list_filter = ("project__workspace", "project")
    search_fields = ("name", "project__title", "floor_material")
    inlines = [ItemInline]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin configuration for items."""

    list_display = (
        "name",
        "room",
        "category",
        "priority_display",
        "status_display",
        "is_custom_made",
        "style",
        "material",
        "color_hex",
        "price_display",
    )
    list_select_related = ("room", "room__project")
    list_filter = (
        "category",
        "priority",
        "status",
        "is_fixed",
        "is_custom_made",
        "room__project",
    )
    search_fields = (
        "name",
        "room__name",
        "room__project__title",
        "material",
        "style",
    )


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    """Admin configuration for item options."""

    list_display = (
        "name",
        "item",
        "price_display",
        "store",
        "finish",
        "lead_time_days",
        "is_chosen",
        "added_by",
    )
    list_select_related = ("item", "item__room", "item__room__project", "added_by")
    list_filter = ("is_chosen", "store", "added_by", "item__room__project")
    search_fields = ("name", "store", "item__name", "finish")
    inlines = [OptionImageInline]


@admin.register(OptionImage)
class OptionImageAdmin(admin.ModelAdmin):
    """Admin configuration for standalone option images."""

    list_display = ("option", "image", "is_cover", "uploaded_at")
    list_select_related = ("option", "option__item")
    list_filter = ("is_cover", "uploaded_at")
    search_fields = ("option__name", "option__item__name")


@admin.register(MoodboardImage)
class MoodboardImageAdmin(admin.ModelAdmin):
    """Admin configuration for moodboard images."""

    list_display = (
        "room",
        "caption",
        "color_display",
        "added_by",
    )
    list_select_related = ("room", "room__project", "added_by")
    list_filter = ("room__project", "added_by")
    search_fields = ("caption", "room__name")
