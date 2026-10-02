"""Forms for authentication, workspaces and memberships."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Membership, Role, User, Workspace


class SignUpForm(UserCreationForm):
    """Registration form for new users."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


class WorkspaceForm(forms.ModelForm):
    """Create or update a workspace."""

    class Meta:
        model = Workspace
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MembershipForm(forms.ModelForm):
    """Add or edit a member of a workspace."""

    class Meta:
        model = Membership
        fields = ("user", "role")

    def __init__(self, *args, workspace: Workspace | None = None, **kwargs) -> None:
        """Limit the user choices to people that are not members yet."""
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        if workspace is not None:
            existing = workspace.memberships.values_list("user_id", flat=True)
            queryset = User.objects.exclude(pk__in=existing).order_by("username")
            if self.instance.pk:
                queryset = queryset | User.objects.filter(pk=self.instance.user_id)
            self.fields["user"].queryset = queryset

    def clean_user(self) -> User:
        """Validate uniqueness of the (workspace, user) pair."""
        user = self.cleaned_data["user"]
        if self.workspace is None:
            return user
        qs = Membership.objects.filter(workspace=self.workspace, user=user)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This user is already a member.")
        return user

    def clean_role(self) -> str:
        """Prevent demoting the last owner of a workspace."""
        role = self.cleaned_data["role"]
        if (
                self.instance.pk
                and self.instance.role == Role.OWNER
                and role != Role.OWNER
                and self.workspace is not None
                and self.workspace.memberships.filter(role=Role.OWNER).count() <= 1
        ):
            raise forms.ValidationError("A workspace must keep at least one owner.")
        return role
