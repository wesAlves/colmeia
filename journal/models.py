"""Models capturing the experience of visiting a house."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from properties.models import House


class Visit(models.Model):
    """A single visit to a house, capturing the experience and impressions.

    Attributes:
        overall_impression: A quick gut-feeling summary of the visit.
        experience: Free-form narration of how the visit went.
        considerations: Notes about practical details and follow-up questions.
    """

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="visits"
    )
    visited_at = models.DateTimeField()
    attendees = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("People present during the visit, comma separated."),
    )
    overall_impression = models.TextField(blank=True)
    experience = models.TextField(
        blank=True, help_text=_("What the visit felt like, in your own words.")
    )
    considerations = models.TextField(
        blank=True, help_text=_("Practical notes, doubts and follow-up questions.")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_visits",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-visited_at",)
        verbose_name = _("visit")
        verbose_name_plural = _("visits")

    def __str__(self) -> str:
        return f"Visit to {self.house} on {self.visited_at:%Y-%m-%d}"


class Note(models.Model):
    """A free-form note attached to a house and optionally to a visit."""

    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="notes")
    visit = models.ForeignKey(
        Visit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("note")
        verbose_name_plural = _("notes")

    def __str__(self) -> str:
        return self.title or f"Note on {self.house}"