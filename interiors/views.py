"""Class-based views for interior projects, rooms, items, options and moodboards."""

from __future__ import annotations

import json
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.mixins import (
    WorkspaceAccessMixin,
    WorkspaceFormMixin,
    WorkspaceQuerysetMixin,
)
from accounts.models import Workspace

from .forms import (
    BaseOptionImageFormSet,
    InteriorProjectForm,
    ItemForm,
    MoodboardImageForm,
    OptionForm,
    OptionImageForm,
    OptionImageFormSet,
    OptionRatingForm,
    RoomForm,
)
from .models import (
    InteriorProject,
    Item,
    MoodboardImage,
    Option,
    OptionImage,
    OptionRating,
    Room,
    Style,
)


class WorkspaceMemberRequiredMixin(
    LoginRequiredMixin, UserPassesTestMixin, WorkspaceAccessMixin
):
    """Enforce user authentication and workspace membership using Django auth mixins."""

    def test_func(self) -> bool:
        """Validate that the requesting user has valid membership in the workspace."""
        if not self.request.user.is_authenticated:
            return False
        slug = self.kwargs.get("workspace_slug")
        if not slug:
            return False
        workspace = get_object_or_404(Workspace, slug=slug)
        self.workspace = workspace
        membership = workspace.membership_for(self.request.user)
        if membership is None:
            return False
        if getattr(self, "require_owner", False) and not membership.can_manage:
            return False
        if getattr(self, "require_editor", False) and not membership.can_edit:
            return False
        self.membership = membership
        return True


class ProjectListView(
    WorkspaceMemberRequiredMixin, WorkspaceQuerysetMixin, ListView
):
    """List all interior projects belonging to the active workspace."""

    model = InteriorProject
    template_name = "interiors/project_list.html"
    context_object_name = "projects"
    paginate_by = 25

    def get_queryset(self) -> QuerySet[InteriorProject]:
        """Fetch workspace interior projects with pre-fetched relations."""
        return (
            super()
            .get_queryset()
            .select_related("house", "workspace")
            .prefetch_related(
                "rooms",
                "rooms__items",
                "rooms__items__options",
                "rooms__moodboard_images",
            )
            .order_by("title")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add workspace and interior project list alias to template context."""
        context = super().get_context_data(**kwargs)
        context["interior_projects"] = context["projects"]
        return context


class ProjectDetailView(
    WorkspaceMemberRequiredMixin, WorkspaceQuerysetMixin, DetailView
):
    """Display details of an interior project including all associated rooms and costs."""

    model = InteriorProject
    template_name = "interiors/project_detail.html"
    context_object_name = "project"

    def get_queryset(self) -> QuerySet[InteriorProject]:
        """Retrieve the project with pre-fetched rooms, items, options and moodboard images."""
        return (
            super()
            .get_queryset()
            .select_related("house", "workspace")
            .prefetch_related(
                "rooms",
                "rooms__items",
                "rooms__items__style",
                "rooms__items__options",
                "rooms__moodboard_images",
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Expose workspace, filtered rooms list, filter parameters and estimated total costs."""
        context = super().get_context_data(**kwargs)
        project: InteriorProject = self.object

        priority_param = self.request.GET.get("priority", "").strip()
        status_param = self.request.GET.get("status", "").strip()
        style_param = self.request.GET.get("style", "").strip()

        rooms_qs = project.rooms.all().prefetch_related(
            "items",
            "items__style",
            "items__options",
            "moodboard_images",
        )

        if priority_param:
            try:
                rooms_qs = rooms_qs.filter(priority=int(priority_param))
            except ValueError:
                pass

        if status_param:
            rooms_qs = rooms_qs.filter(items__status=status_param).distinct()

        if style_param:
            if style_param.isdigit():
                rooms_qs = rooms_qs.filter(items__style__id=int(style_param)).distinct()
            else:
                rooms_qs = rooms_qs.filter(items__style__slug=style_param).distinct()

        rooms = list(rooms_qs)
        context["workspace"] = self.workspace
        context["rooms"] = rooms
        context["rooms_with_totals"] = [
            {
                "room": room,
                "total_estimated_cost": room.total_estimated_cost,
                "total_estimated_cost_display": room.total_estimated_cost_display,
            }
            for room in rooms
        ]
        context["total_estimated_cost"] = project.total_estimated_cost
        context["total_estimated_cost_display"] = project.total_estimated_cost_display

        # Filter dropdown data and active parameters
        context["filter_params"] = {
            "priority": priority_param,
            "status": status_param,
            "style": style_param,
        }
        context["room_priorities"] = Room.Priority.choices
        context["item_statuses"] = Item.Status.choices
        context["all_styles"] = Style.objects.all()
        return context


class ProjectCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Create a new interior project for the active workspace."""

    model = InteriorProject
    form_class = InteriorProjectForm
    template_name = "interiors/project_form.html"
    success_message = _("Interior project created successfully.")
    require_editor = True

    def form_valid(self, form: InteriorProjectForm) -> HttpResponse:
        """Associate the new interior project with the current workspace."""
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to the interior project detail view upon creation."""
        return str(
            reverse_lazy(
                "interiors:project_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class ProjectUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceQuerysetMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Edit an existing interior project."""

    model = InteriorProject
    form_class = InteriorProjectForm
    template_name = "interiors/project_form.html"
    success_message = _("Interior project updated successfully.")
    require_editor = True

    def get_queryset(self) -> QuerySet[InteriorProject]:
        """Limit editing to projects within the active workspace."""
        return super().get_queryset().select_related("house", "workspace")

    def get_success_url(self) -> str:
        """Redirect to the project detail view after saving changes."""
        return str(
            reverse_lazy(
                "interiors:project_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class RoomDetailView(WorkspaceMemberRequiredMixin, DetailView):
    """Show details of a room, including filtered items and moodboard images."""

    model = Room
    template_name = "interiors/room_detail.html"
    context_object_name = "room"

    def get_queryset(self) -> QuerySet[Room]:
        """Filter rooms by active workspace with related items, options, and moodboard images."""
        return (
            Room.objects.filter(project__workspace=self.workspace)
            .select_related("project", "project__workspace", "project__house")
            .prefetch_related(
                "items",
                "items__style",
                "items__options",
                "items__options__images",
                "items__options__added_by",
                "items__depends_on",
                "moodboard_images",
                "moodboard_images__added_by",
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Inject workspace, project, filtered items, filter parameters, and moodboard data into context."""
        context = super().get_context_data(**kwargs)
        room: Room = self.object

        category_param = self.request.GET.get("category", "").strip()
        priority_param = self.request.GET.get("priority", "").strip()
        status_param = self.request.GET.get("status", "").strip()
        style_param = self.request.GET.get("style", "").strip()
        conn_param = self.request.GET.get("connection_type", "").strip()

        items_qs = room.items.all().prefetch_related(
            "options",
            "options__images",
            "style",
            "depends_on",
        )

        if category_param:
            items_qs = items_qs.filter(category=category_param)

        if priority_param:
            try:
                items_qs = items_qs.filter(priority=int(priority_param))
            except ValueError:
                pass

        if status_param:
            items_qs = items_qs.filter(status=status_param)

        if style_param:
            if style_param.isdigit():
                items_qs = items_qs.filter(style__id=int(style_param))
            else:
                items_qs = items_qs.filter(style__slug=style_param)

        if conn_param:
            items_qs = items_qs.filter(connection_type=conn_param)

        context["workspace"] = self.workspace
        context["project"] = room.project
        context["items"] = list(items_qs.distinct())

        moodboard_items: list[dict[str, Any]] = []
        for img in room.moodboard_images.all().order_by("order"):
            moodboard_items.append(
                {
                    "type": "inspiration",
                    "image": img,
                    "caption": img.caption,
                    "hex": img.hex_color,
                    "id": img.id,
                    "pk": img.pk,
                    "order": img.order,
                    "is_cover": img.is_cover,
                }
            )

        for item in room.items.all().prefetch_related("options__images"):
            opt = item.chosen_option
            if opt and opt.primary_image and opt.primary_image.url:
                moodboard_items.append(
                    {
                        "type": "chosen_option",
                        "image": opt.primary_image,
                        "caption": opt.name,
                        "price": opt.price_display,
                        "hex": "",
                        "item": item,
                        "option": opt,
                    }
                )

        context["moodboard_items"] = moodboard_items
        context["moodboard_images"] = room.moodboard_images.all().order_by("order")
        context["total_estimated_cost"] = room.total_estimated_cost
        context["total_estimated_cost_display"] = room.total_estimated_cost_display

        # Filter parameters and choice options
        context["filter_params"] = {
            "category": category_param,
            "priority": priority_param,
            "status": status_param,
            "style": style_param,
            "connection_type": conn_param,
        }
        context["categories"] = Item.Category.choices
        context["priorities"] = Item.Priority.choices
        context["statuses"] = Item.Status.choices
        context["styles"] = Style.objects.all()
        context["connection_types"] = Item.ConnectionType.choices
        return context


class ItemDetailView(WorkspaceMemberRequiredMixin, DetailView):
    """Show details of an item, including all candidate purchase options and chosen option."""

    model = Item
    template_name = "interiors/item_detail.html"
    context_object_name = "item"

    def get_queryset(self) -> QuerySet[Item]:
        """Filter items by active workspace with related room, project, and options."""
        return (
            Item.objects.filter(room__project__workspace=self.workspace)
            .select_related(
                "room",
                "room__project",
                "room__project__workspace",
            )
            .prefetch_related(
                "options",
                "options__added_by",
                "options__images",
                "options__ratings",
                "options__ratings__user",
                "style",
                "depends_on",
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Inject workspace, room, project, options, user ratings and chosen option into context."""
        context = super().get_context_data(**kwargs)
        item: Item = self.object
        context["workspace"] = self.workspace
        context["room"] = item.room
        context["project"] = item.room.project
        options_list = list(
            item.options.all()
            .select_related("added_by")
            .prefetch_related("images", "ratings", "ratings__user")
        )
        context["options"] = options_list
        context["chosen_option"] = item.chosen_option

        user_ratings = {}
        if self.request.user.is_authenticated:
            for opt in options_list:
                for r in opt.ratings.all():
                    if r.user_id == self.request.user.id:
                        user_ratings[opt.id] = r
                        break
        context["user_ratings"] = user_ratings
        return context


class RoomCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Create a new room inside an interior project."""

    model = Room
    form_class = RoomForm
    template_name = "interiors/room_form.html"
    success_message = _("Room created successfully.")
    require_editor = True

    def get_project(self) -> InteriorProject:
        """Fetch the parent interior project verifying workspace scoping."""
        return get_object_or_404(
            InteriorProject,
            pk=self.kwargs.get("project_pk"),
            workspace=self.workspace,
        )

    def form_valid(self, form: RoomForm) -> HttpResponse:
        """Associate the new room with the parent interior project."""
        form.instance.project = self.get_project()
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the parent project to template context."""
        context = super().get_context_data(**kwargs)
        context["project"] = self.get_project()
        return context

    def get_success_url(self) -> str:
        """Redirect to room detail view upon creation."""
        return str(
            reverse_lazy(
                "interiors:room_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class RoomUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Update an existing room."""

    model = Room
    form_class = RoomForm
    template_name = "interiors/room_form.html"
    success_message = _("Room updated successfully.")
    require_editor = True

    def get_queryset(self) -> QuerySet[Room]:
        """Restrict room lookup to the current workspace."""
        return (
            Room.objects.filter(project__workspace=self.workspace)
            .select_related("project")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the parent project to template context."""
        context = super().get_context_data(**kwargs)
        context["project"] = self.object.project
        return context

    def get_success_url(self) -> str:
        """Redirect to room detail view after updating."""
        return str(
            reverse_lazy(
                "interiors:room_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class ItemCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Create a new item inside a room."""

    model = Item
    form_class = ItemForm
    template_name = "interiors/item_form.html"
    success_message = _("Item created successfully.")
    require_editor = True

    def get_room(self) -> Room:
        """Fetch the parent room verifying workspace scoping."""
        return get_object_or_404(
            Room,
            pk=self.kwargs.get("room_pk"),
            project__workspace=self.workspace,
        )

    def get_form_kwargs(self) -> dict[str, Any]:
        """Inject current room into form kwargs for depends_on scoping."""
        kwargs = super().get_form_kwargs()
        kwargs["room"] = self.get_room()
        return kwargs

    def form_valid(self, form: ItemForm) -> HttpResponse:
        """Associate the new item with the parent room."""
        form.instance.room = self.get_room()
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent room and project to template context."""
        context = super().get_context_data(**kwargs)
        room = self.get_room()
        context["room"] = room
        context["project"] = room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to item detail view upon creation."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class ItemUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Update an existing item."""

    model = Item
    form_class = ItemForm
    template_name = "interiors/item_form.html"
    success_message = _("Item updated successfully.")
    require_editor = True

    def get_queryset(self) -> QuerySet[Item]:
        """Restrict item lookup to current workspace."""
        return (
            Item.objects.filter(room__project__workspace=self.workspace)
            .select_related("room", "room__project")
        )

    def get_form_kwargs(self) -> dict[str, Any]:
        """Inject item's room into form kwargs for depends_on scoping."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object") and self.object:
            kwargs["room"] = self.object.room
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent room and project to template context."""
        context = super().get_context_data(**kwargs)
        context["room"] = self.object.room
        context["project"] = self.object.room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to item detail view after updating."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.pk,
                },
            )
        )


class OptionCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Create a new purchase option for an item along with multiple option images."""

    model = Option
    form_class = OptionForm
    template_name = "interiors/option_form.html"
    success_message = _("Purchase option added successfully.")
    require_editor = True

    def get_item(self) -> Item:
        """Fetch the parent item verifying workspace scoping."""
        return get_object_or_404(
            Item,
            pk=self.kwargs.get("item_pk"),
            room__project__workspace=self.workspace,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent item, room, project, and option image formset to template context."""
        context = super().get_context_data(**kwargs)
        item = self.get_item()
        context["item"] = item
        context["room"] = item.room
        context["project"] = item.room.project
        if "image_formset" not in context:
            if self.request.POST:
                context["image_formset"] = BaseOptionImageFormSet(
                    self.request.POST,
                    self.request.FILES,
                    instance=self.object,
                )
            else:
                context["image_formset"] = BaseOptionImageFormSet(instance=self.object)
        context["formset"] = context["image_formset"]
        return context

    def form_valid(self, form: OptionForm) -> HttpResponse:
        """Associate option with parent item, set added_by, and save image formset."""
        form.instance.item = self.get_item()
        form.instance.added_by = self.request.user
        formset = BaseOptionImageFormSet(
            self.request.POST,
            self.request.FILES,
        )
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(
                self.get_context_data(form=form, image_formset=formset)
            )

    def get_success_url(self) -> str:
        """Redirect to item detail view upon creation."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.item_id,
                },
            )
        )


class OptionUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Update an existing purchase option along with multiple option images."""

    model = Option
    form_class = OptionForm
    template_name = "interiors/option_form.html"
    success_message = _("Purchase option updated successfully.")
    require_editor = True

    def get_queryset(self) -> QuerySet[Option]:
        """Restrict option lookup to current workspace."""
        return (
            Option.objects.filter(item__room__project__workspace=self.workspace)
            .select_related("item", "item__room", "item__room__project")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent item, room, project, and option image formset to template context."""
        context = super().get_context_data(**kwargs)
        context["item"] = self.object.item
        context["room"] = self.object.item.room
        context["project"] = self.object.item.room.project
        if "image_formset" not in context:
            if self.request.POST:
                context["image_formset"] = BaseOptionImageFormSet(
                    self.request.POST,
                    self.request.FILES,
                    instance=self.object,
                )
            else:
                context["image_formset"] = BaseOptionImageFormSet(instance=self.object)
        context["formset"] = context["image_formset"]
        return context

    def form_valid(self, form: OptionForm) -> HttpResponse:
        """Save updated option and save associated option images formset."""
        formset = BaseOptionImageFormSet(
            self.request.POST,
            self.request.FILES,
            instance=self.object,
        )
        if formset.is_valid():
            self.object = form.save()
            formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(
                self.get_context_data(form=form, image_formset=formset)
            )

    def get_success_url(self) -> str:
        """Redirect to item detail view after updating."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.item_id,
                },
            )
        )


class OptionRatingCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Create a new evaluation rating and feedback for an option."""

    model = OptionRating
    form_class = OptionRatingForm
    template_name = "interiors/option_rating_form.html"
    success_message = _("Option evaluation submitted successfully.")

    def get_option(self) -> Option:
        """Fetch the target purchase option verifying workspace scoping."""
        return get_object_or_404(
            Option,
            pk=self.kwargs.get("option_pk"),
            item__room__project__workspace=self.workspace,
        )

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Redirect to update view if the requesting user already evaluated this option."""
        resp = self.setup_workspace(request, *args, **kwargs)
        if resp is not None:
            return resp
        if request.user.is_authenticated and hasattr(self, "workspace"):
            option = self.get_option()
            existing_rating = OptionRating.objects.filter(
                option=option,
                user=request.user,
            ).first()
            if existing_rating:
                return HttpResponseRedirect(
                    reverse_lazy(
                        "interiors:option_rating_update",
                        kwargs={
                            "workspace_slug": self.workspace.slug,
                            "pk": existing_rating.pk,
                        },
                    )
                )
        return super(WorkspaceAccessMixin, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form: OptionRatingForm) -> HttpResponse:
        """Inject option and user into rating instance."""
        form.instance.option = self.get_option()
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add option, item, room, project to template context."""
        context = super().get_context_data(**kwargs)
        option = self.get_option()
        context["option"] = option
        context["item"] = option.item
        context["room"] = option.item.room
        context["project"] = option.item.room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to the parent item detail view."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.option.item_id,
                },
            )
        )


class OptionRatingUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Update an existing evaluation rating for an option."""

    model = OptionRating
    form_class = OptionRatingForm
    template_name = "interiors/option_rating_form.html"
    success_message = _("Option evaluation updated successfully.")

    def get_queryset(self) -> QuerySet[OptionRating]:
        """Restrict lookup to ratings in current workspace authored by the requesting user."""
        return (
            OptionRating.objects.filter(
                option__item__room__project__workspace=self.workspace,
                user=self.request.user,
            )
            .select_related("option", "option__item", "option__item__room")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add option, item, room, project to template context."""
        context = super().get_context_data(**kwargs)
        option = self.object.option
        context["option"] = option
        context["item"] = option.item
        context["room"] = option.item.room
        context["project"] = option.item.room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to the parent item detail view."""
        return str(
            reverse_lazy(
                "interiors:item_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.option.item_id,
                },
            )
        )


class MoodboardImageCreateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Add a new moodboard inspiration image to a room."""

    model = MoodboardImage
    form_class = MoodboardImageForm
    template_name = "interiors/moodboard_image_form.html"
    success_message = _("Moodboard image added successfully.")
    require_editor = True

    def get_room(self) -> Room:
        """Fetch the parent room verifying workspace scoping."""
        return get_object_or_404(
            Room,
            pk=self.kwargs.get("room_pk"),
            project__workspace=self.workspace,
        )

    def form_valid(self, form: MoodboardImageForm) -> HttpResponse:
        """Associate the moodboard image with the room and set added_by."""
        form.instance.room = self.get_room()
        form.instance.added_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent room and project to template context."""
        context = super().get_context_data(**kwargs)
        room = self.get_room()
        context["room"] = room
        context["project"] = room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to room detail view upon creation."""
        return str(
            reverse_lazy(
                "interiors:room_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.room_id,
                },
            )
        )


class MoodboardImageUpdateView(
    WorkspaceMemberRequiredMixin,
    WorkspaceFormMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Update an existing moodboard inspiration image."""

    model = MoodboardImage
    form_class = MoodboardImageForm
    template_name = "interiors/moodboard_image_form.html"
    success_message = _("Moodboard image updated successfully.")
    require_editor = True

    def get_queryset(self) -> QuerySet[MoodboardImage]:
        """Restrict moodboard image lookup to current workspace."""
        return (
            MoodboardImage.objects.filter(room__project__workspace=self.workspace)
            .select_related("room", "room__project")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add parent room and project to template context."""
        context = super().get_context_data(**kwargs)
        context["room"] = self.object.room
        context["project"] = self.object.room.project
        return context

    def get_success_url(self) -> str:
        """Redirect to room detail view after updating."""
        return str(
            reverse_lazy(
                "interiors:room_detail",
                kwargs={
                    "workspace_slug": self.workspace.slug,
                    "pk": self.object.room_id,
                },
            )
        )


class MoodboardImageReorderView(WorkspaceMemberRequiredMixin, View):
    """Reorder moodboard inspiration images via AJAX POST."""

    require_editor = True

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        """Process reordered image IDs and update their order values in the database."""
        room_pk = kwargs.get("room_pk")

        ordered_ids: list[int] = []
        if request.content_type == "application/json" or (
            request.body
            and (request.body.strip().startswith(b"{") or request.body.strip().startswith(b"["))
        ):
            try:
                data = json.loads(request.body)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item:
                            ordered_ids.append(int(item["id"]))
                        elif str(item).isdigit():
                            ordered_ids.append(int(item))
                elif isinstance(data, dict):
                    raw_list = (
                        data.get("order")
                        or data.get("image_ids")
                        or data.get("images")
                        or data.get("items")
                        or []
                    )
                    if isinstance(raw_list, list):
                        for item in raw_list:
                            if isinstance(item, dict) and "id" in item:
                                ordered_ids.append(int(item["id"]))
                            elif str(item).isdigit():
                                ordered_ids.append(int(item))
                    if not room_pk and "room_pk" in data:
                        room_pk = data["room_pk"]
            except (json.JSONDecodeError, ValueError, TypeError):
                return JsonResponse(
                    {"status": "error", "message": "Invalid JSON payload."},
                    status=400,
                )
        else:
            raw_list = (
                request.POST.getlist("order[]")
                or request.POST.getlist("order")
                or request.POST.getlist("image_ids[]")
                or request.POST.getlist("image_ids")
            )
            for item in raw_list:
                if str(item).isdigit():
                    ordered_ids.append(int(item))

        queryset = MoodboardImage.objects.filter(
            room__project__workspace=self.workspace
        )
        if room_pk:
            queryset = queryset.filter(room_id=room_pk)

        images_by_id = {img.pk: img for img in queryset.filter(pk__in=ordered_ids)}
        updates: list[MoodboardImage] = []
        for index, img_id in enumerate(ordered_ids):
            if img_id in images_by_id:
                img = images_by_id[img_id]
                if img.order != index:
                    img.order = index
                    updates.append(img)

        if updates:
            MoodboardImage.objects.bulk_update(updates, ["order"])

        return JsonResponse(
            {
                "status": "success",
                "updated_count": len(updates),
                "ordered_ids": ordered_ids,
            }
        )


class RoomMoodboardView(WorkspaceMemberRequiredMixin, DetailView):
    """Presentation moodboard for a room displaying a clean visual mosaic and color palette."""

    model = Room
    template_name = "interiors/room_moodboard_presentation.html"
    context_object_name = "room"

    def get_queryset(self) -> QuerySet[Room]:
        """Fetch room scoped by active workspace with related items, options, and moodboard images."""
        return (
            Room.objects.filter(project__workspace=self.workspace)
            .select_related("project", "project__workspace", "project__house")
            .prefetch_related(
                "items",
                "items__options",
                "items__options__images",
                "moodboard_images",
                "moodboard_images__added_by",
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Inject presentation items, color palette, area and dimensions into context."""
        context = super().get_context_data(**kwargs)
        room: Room = self.object
        context["workspace"] = self.workspace
        context["project"] = room.project
        context["membership"] = self.membership

        presentation_items: list[dict[str, Any]] = []
        for img in room.moodboard_images.all().order_by("order"):
            presentation_items.append(
                {
                    "type": "inspiration",
                    "image": img,
                    "caption": img.caption,
                    "hex": img.hex_color,
                    "id": img.id,
                    "pk": img.pk,
                    "order": img.order,
                    "is_cover": img.is_cover,
                }
            )

        for item in room.items.all().prefetch_related("options__images"):
            opt = item.chosen_option
            if opt and opt.primary_image and opt.primary_image.url:
                presentation_items.append(
                    {
                        "type": "chosen_option",
                        "image": opt.primary_image,
                        "caption": opt.name,
                        "hex": "",
                        "item": item,
                        "option": opt,
                    }
                )

        context["presentation_items"] = presentation_items

        palette_colors: list[str] = []
        for color in (
            room.floor_color_hex,
            room.baseboard_color_hex,
            room.wall_color_hex,
            room.ceiling_color_hex,
        ):
            if color and color.strip():
                c = color.strip()
                if c not in palette_colors:
                    palette_colors.append(c)

        if isinstance(room.palette_colors, list):
            for entry in room.palette_colors:
                if isinstance(entry, dict) and entry.get("hex"):
                    hex_val = str(entry["hex"]).strip()
                    if hex_val and hex_val not in palette_colors:
                        palette_colors.append(hex_val)
                elif isinstance(entry, str) and entry.strip():
                    hex_val = entry.strip()
                    if hex_val not in palette_colors:
                        palette_colors.append(hex_val)

        for img in room.moodboard_images.all().order_by("order"):
            if img.hex_color and img.hex_color.strip():
                img_hex = img.hex_color.strip()
                if img_hex not in palette_colors:
                    palette_colors.append(img_hex)

        context["palette_colors"] = palette_colors
        context["structured_palette"] = (
            room.palette_colors if isinstance(room.palette_colors, list) else []
        )

        dim_parts: list[str] = []
        if room.width_m:
            dim_parts.append(f"{room.width_m}m")
        if room.length_m:
            dim_parts.append(f"{room.length_m}m")
        if room.height_m:
            dim_parts.append(f"{room.height_m}m")

        context["room_dimensions"] = " × ".join(dim_parts) if dim_parts else ""
        context["room_area"] = f"{room.area_sqm} m²" if room.area_sqm else ""
        return context


RoomMoodboardPresentationView = RoomMoodboardView


# Aliases for flexibility and naming consistency
InteriorProjectListView = ProjectListView
InteriorProjectDetailView = ProjectDetailView
InteriorProjectCreateView = ProjectCreateView
InteriorProjectUpdateView = ProjectUpdateView
