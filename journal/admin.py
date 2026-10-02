"""Admin registrations for the journal app."""

from __future__ import annotations

from django.contrib import admin

from .models import Note, Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    """Admin for visits."""

    list_display = ("house", "visited_at", "created_by", "created_at")
    list_filter = ("visited_at",)
    search_fields = ("house__title", "attendees", "experience")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin for notes."""

    list_display = ("title", "house", "created_by", "created_at")
    search_fields = ("title", "body", "house__title")