from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import User, Workspace


class UserModelTests(TestCase):
    def test_custom_user_model_configured(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertEqual(get_user_model(), User)


class RootViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123",
        )

    def test_unauthenticated_user_accessing_root_redirects_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, reverse("accounts:login"))

        # Follow redirect and verify login template is shown
        followed_response = self.client.get("/", follow=True)
        self.assertEqual(followed_response.status_code, 200)
        self.assertTemplateUsed(followed_response, "accounts/login.html")

    def test_authenticated_user_accessing_root_redirects_to_workspace_list(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("accounts:workspace_list"))

        # Follow redirect and verify workspace list template is shown
        followed_response = self.client.get("/", follow=True)
        self.assertEqual(followed_response.status_code, 200)
        self.assertTemplateUsed(followed_response, "accounts/workspace_list.html")
