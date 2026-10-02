from __future__ import annotations
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'
    verbose_name = "Accounts"

    def ready(self) -> None:
        """Import signal handlers when the app registry is ready."""
        from . import signals  # noqa: F401