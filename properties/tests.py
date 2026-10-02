from io import BytesIO
from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Membership, Role, Workspace
from properties.models import House, HousePhoto, Rating

User = get_user_model()


class PropertyViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.workspace = Workspace.objects.create(name="Test Workspace", created_by=self.user)
        Membership.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=Role.OWNER,
        )
        self.house = House.objects.create(
            workspace=self.workspace,
            title="Modern Villa",
            price=500000,
        )
        self.client.login(username="testuser", password="password")

    def _generate_test_image(self):
        file = BytesIO()
        image = Image.new("RGBA", size=(50, 50), color=(256, 0, 0))
        image.save(file, "png")
        file.name = "test.png"
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type="image/png")

    def test_house_photo_create_and_delete(self):
        create_url = reverse(
            "properties:photo_create",
            kwargs={"workspace_slug": self.workspace.slug, "house_pk": self.house.pk},
        )
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Photo")

        test_image = self._generate_test_image()
        post_response = self.client.post(
            create_url,
            {
                "image": test_image,
                "caption": "Front garden",
                "is_primary": True,
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(HousePhoto.objects.filter(house=self.house).count(), 1)
        photo = HousePhoto.objects.get(house=self.house)
        self.assertEqual(photo.caption, "Front garden")
        self.assertTrue(photo.is_primary)
        self.assertEqual(photo.uploaded_by, self.user)

        delete_url = reverse(
            "properties:photo_delete",
            kwargs={
                "workspace_slug": self.workspace.slug,
                "house_pk": self.house.pk,
                "pk": photo.pk,
            },
        )
        del_get_response = self.client.get(delete_url)
        self.assertEqual(del_get_response.status_code, 200)

        del_post_response = self.client.post(delete_url)
        self.assertEqual(del_post_response.status_code, 302)
        self.assertEqual(HousePhoto.objects.filter(house=self.house).count(), 0)

    def test_rating_upsert_and_delete(self):
        rating_url = reverse(
            "properties:rating_upsert",
            kwargs={"workspace_slug": self.workspace.slug, "house_pk": self.house.pk},
        )
        response = self.client.get(rating_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rate This House")

        post_response = self.client.post(
            rating_url,
            {
                "score": 9,
                "comment": "Great layout and location",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(Rating.objects.filter(house=self.house).count(), 1)
        rating = Rating.objects.get(house=self.house)
        self.assertEqual(rating.score, 9)
        self.assertEqual(rating.user, self.user)

        # Update rating
        post_update_response = self.client.post(
            rating_url,
            {
                "score": 10,
                "comment": "Even better after thinking about it",
            },
        )
        self.assertEqual(post_update_response.status_code, 302)
        rating.refresh_from_db()
        self.assertEqual(rating.score, 10)

        # Delete rating
        delete_url = reverse(
            "properties:rating_delete",
            kwargs={"workspace_slug": self.workspace.slug, "house_pk": self.house.pk},
        )
        del_get_response = self.client.get(delete_url)
        self.assertEqual(del_get_response.status_code, 200)

        del_post_response = self.client.post(delete_url)
        self.assertEqual(del_post_response.status_code, 302)
        self.assertEqual(Rating.objects.filter(house=self.house).count(), 0)

        # Deleting again returns 404
        del_again_response = self.client.get(delete_url)
        self.assertEqual(del_again_response.status_code, 404)
