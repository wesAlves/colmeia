"""Signal handlers for the accounts app."""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Membership, Role, Workspace

DEFAULT_FEATURES: list[dict[str, str]] = [
    {"name": "Garden", "data_type": "boolean"},
    {"name": "Parking", "data_type": "boolean"},
    {"name": "Balcony", "data_type": "boolean"},
    {"name": "Elevator", "data_type": "boolean"},
    {"name": "Furnished", "data_type": "boolean"},
    {
        "name": "Heating",
        "data_type": "choice",
        "choices": "gas,electric,heat pump,district,none",
    },
    {"name": "Energy rating", "data_type": "choice", "choices": "A,B,C,D,E,F,G"},
    {
        "name": "Condition",
        "data_type": "choice",
        "choices": "new,good,needs work,to renovate",
    },
    {"name": "Noise level", "data_type": "choice", "choices": "quiet,moderate,noisy"},
    {"name": "Natural light", "data_type": "choice", "choices": "low,medium,high"},
    {"name": "Floor", "data_type": "integer"},
    {"name": "Year renovated", "data_type": "integer"},
]


@receiver(post_save, sender=Workspace)
def seed_default_features(sender, instance: Workspace, created: bool, **kwargs) -> None:
    """Populate a freshly created workspace with a sensible feature catalog.

    Runs only on creation so users can safely rename or remove features later.
    """
    if not created:
        return

    # Imported lazily to avoid a circular import at module load time.
    from properties.models import Feature

    Feature.objects.bulk_create(
        [
            Feature(
                workspace=instance,
                name=spec["name"],
                data_type=spec["data_type"],
                choices=spec.get("choices", ""),
                is_predefined=True,
                order=index,
            )
            for index, spec in enumerate(DEFAULT_FEATURES)
        ],
        ignore_conflicts=True,
    )


@receiver(post_save, sender=Workspace)
def ensure_owner_membership(sender, instance: Workspace, created: bool, **kwargs) -> None:
    """Guarantee the workspace creator always has an owner membership."""
    if not created or instance.created_by_id is None:
        return
    Membership.objects.get_or_create(
        workspace=instance,
        user=instance.created_by,
        defaults={"role": Role.OWNER},
    )
