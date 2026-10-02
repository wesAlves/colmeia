"""Reusable view mixins for the properties app.

``HouseScopedMixin`` resolves the parent :class:`~properties.models.House` from
a ``house_pk`` URL keyword argument and re-uses the workspace scoping provided
by :class:`accounts.mixins.WorkspaceAccessMixin`.  Both ``properties`` and
``journal`` views build on it.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from accounts.mixins import WorkspaceAccessMixin

from .models import House


class HouseScopedMixin(WorkspaceAccessMixin):
    """Resolve the parent :class:`House` from the ``house_pk`` URL kwarg.

    After :meth:`dispatch` the attribute :attr:`house` is available.  The
    house is always fetched inside the resolved workspace, so cross-workspace
    access is impossible.
    """

    house: House

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Resolve the house before delegating to the parent dispatch."""
        response = super().dispatch(request, *args, **kwargs)
        self.house = get_object_or_404(
            House, pk=kwargs.get("house_pk"), workspace=self.workspace
        )
        return response

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Inject the house into the template context."""
        context = super().get_context_data(**kwargs)
        context.setdefault("house", self.house)
        return context