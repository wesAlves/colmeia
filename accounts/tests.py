from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_custom_user_model_configured(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertEqual(get_user_model(), User)
