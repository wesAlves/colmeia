from io import BytesIO
from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Membership, Role, Workspace
from properties.models import (
    Favorite,
    Feature,
    FeatureValue,
    House,
    HousePhoto,
    Rating,
)

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
                "love_score": 8,
                "comment": "Great layout and location",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(Rating.objects.filter(house=self.house).count(), 1)
        rating = Rating.objects.get(house=self.house)
        self.assertEqual(rating.score, 9)
        self.assertEqual(rating.love_score, 8)
        self.assertEqual(rating.user, self.user)

        # Update rating
        post_update_response = self.client.post(
            rating_url,
            {
                "score": 10,
                "love_score": 10,
                "comment": "Even better after thinking about it",
            },
        )
        self.assertEqual(post_update_response.status_code, 302)
        rating.refresh_from_db()
        self.assertEqual(rating.score, 10)
        self.assertEqual(rating.love_score, 10)

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

    def test_house_create_get(self):
        url = reverse(
            "properties:house_create",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Link Feature")
        self.assertContains(response, "Populate All Features")
        self.assertContains(response, "empty-feature-form-template")
        self.assertContains(response, "workspace-features-data")

    def test_house_create_post_with_various_feature_data_types(self):
        bool_feature = Feature.objects.create(
            workspace=self.workspace,
            name="Has Balcony",
            data_type=Feature.DataType.BOOLEAN,
        )
        choice_feature = Feature.objects.create(
            workspace=self.workspace,
            name="Heating System",
            data_type=Feature.DataType.CHOICE,
            choices="Gas, Electric, Heat Pump, Solar",
        )
        int_feature = Feature.objects.create(
            workspace=self.workspace,
            name="Number of Parking Spaces",
            data_type=Feature.DataType.INTEGER,
            unit="spaces",
        )
        text_feature = Feature.objects.create(
            workspace=self.workspace,
            name="Special Notes",
            data_type=Feature.DataType.TEXT,
        )

        url = reverse(
            "properties:house_create",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        initial_house_count = House.objects.filter(workspace=self.workspace).count()

        post_data = {
            "title": "Suburban Oasis",
            "price": "420000",
            "currency": "EUR",
            "property_type": "house",
            "status": "active",
            "features-TOTAL_FORMS": "4",
            "features-INITIAL_FORMS": "0",
            "features-MIN_NUM_FORMS": "0",
            "features-MAX_NUM_FORMS": "1000",
            "features-0-feature": str(bool_feature.pk),
            "features-0-value": "true",
            "features-0-id": "",
            "features-1-feature": str(choice_feature.pk),
            "features-1-value": "Heat Pump",
            "features-1-id": "",
            "features-2-feature": str(int_feature.pk),
            "features-2-value": "2",
            "features-2-id": "",
            "features-3-feature": str(text_feature.pk),
            "features-3-value": "Close to metro station",
            "features-3-id": "",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            House.objects.filter(workspace=self.workspace).count(),
            initial_house_count + 1,
        )
        new_house = House.objects.get(title="Suburban Oasis")
        self.assertEqual(new_house.feature_values.count(), 4)

        f_map = {fv.feature: fv.value for fv in new_house.feature_values.all()}
        self.assertEqual(f_map[bool_feature], "true")
        self.assertEqual(f_map[choice_feature], "Heat Pump")
        self.assertEqual(f_map[int_feature], "2")
        self.assertEqual(f_map[text_feature], "Close to metro station")

    def test_feature_form_choice_validation(self):
        from properties.forms import FeatureForm

        # Choice type without choices should fail validation
        form_invalid = FeatureForm(
            data={
                "name": "Invalid Choice Feature",
                "data_type": Feature.DataType.CHOICE,
                "choices": "",
            },
            workspace=self.workspace,
        )
        self.assertFalse(form_invalid.is_valid())
        self.assertIn("choices", form_invalid.errors)

        # Choice type with choices should pass
        form_valid = FeatureForm(
            data={
                "name": "Valid Choice Feature",
                "data_type": Feature.DataType.CHOICE,
                "choices": "Option A, Option B",
            },
            workspace=self.workspace,
        )
        self.assertTrue(form_valid.is_valid())

    def test_house_create_post_with_features(self):
        feature = Feature.objects.filter(workspace=self.workspace).first()
        if not feature:
            feature = Feature.objects.create(
                workspace=self.workspace,
                name="Garden",
                data_type=Feature.DataType.BOOLEAN,
            )

        url = reverse(
            "properties:house_create",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        initial_house_count = House.objects.filter(workspace=self.workspace).count()

        post_data = {
            "title": "Cozy Cottage",
            "price": "350000",
            "currency": "EUR",
            "property_type": "house",
            "status": "active",
            "features-TOTAL_FORMS": "1",
            "features-INITIAL_FORMS": "0",
            "features-MIN_NUM_FORMS": "0",
            "features-MAX_NUM_FORMS": "1000",
            "features-0-feature": str(feature.pk),
            "features-0-value": "true",
            "features-0-id": "",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            House.objects.filter(workspace=self.workspace).count(),
            initial_house_count + 1,
        )
        new_house = House.objects.get(title="Cozy Cottage")
        self.assertEqual(new_house.feature_values.count(), 1)
        fv = new_house.feature_values.first()
        self.assertEqual(fv.feature, feature)
        self.assertEqual(fv.value, "true")

    def test_house_create_duplicate_features_does_not_create_orphaned_house(self):
        feature = Feature.objects.filter(workspace=self.workspace).first()
        if not feature:
            feature = Feature.objects.create(
                workspace=self.workspace,
                name="Garden",
                data_type=Feature.DataType.BOOLEAN,
            )

        url = reverse(
            "properties:house_create",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        initial_house_count = House.objects.filter(workspace=self.workspace).count()

        # Submit two rows with the same feature (duplicate)
        post_data = {
            "title": "Invalid House",
            "price": "200000",
            "currency": "EUR",
            "property_type": "house",
            "status": "active",
            "features-TOTAL_FORMS": "2",
            "features-INITIAL_FORMS": "0",
            "features-MIN_NUM_FORMS": "0",
            "features-MAX_NUM_FORMS": "1000",
            "features-0-feature": str(feature.pk),
            "features-0-value": "true",
            "features-0-id": "",
            "features-1-feature": str(feature.pk),
            "features-1-value": "false",
            "features-1-id": "",
        }
        response = self.client.post(url, post_data)
        # Should stay on page due to formset validation error and NOT create a house
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            House.objects.filter(workspace=self.workspace).count(),
            initial_house_count,
        )
        self.assertFalse(House.objects.filter(title="Invalid House").exists())

    def test_house_status_update_shortcut(self):
        url = reverse(
            "properties:house_status_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        self.assertEqual(self.house.status, House.Status.NEW)

        # Update to visited
        response = self.client.post(url, {"status": House.Status.VISITED})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse(
                "properties:house_detail",
                kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
            ),
        )
        self.house.refresh_from_db()
        self.assertEqual(self.house.status, House.Status.VISITED)

        # Update to shortlisted with next param
        next_url = reverse("properties:house_list", kwargs={"workspace_slug": self.workspace.slug})
        response = self.client.post(url, {"status": House.Status.SHORTLISTED, "next": next_url})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, next_url)
        self.house.refresh_from_db()
        self.assertEqual(self.house.status, House.Status.SHORTLISTED)

    def test_house_status_update_invalid_status(self):
        url = reverse(
            "properties:house_status_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        initial_status = self.house.status
        response = self.client.post(url, {"status": "non_existent_status"})
        self.assertEqual(response.status_code, 302)
        self.house.refresh_from_db()
        self.assertEqual(self.house.status, initial_status)

    def test_house_status_update_viewer_forbidden(self):
        viewer = User.objects.create_user(username="viewer", password="password")
        Membership.objects.create(
            workspace=self.workspace,
            user=viewer,
            role=Role.VIEWER,
        )
        self.client.login(username="viewer", password="password")

        url = reverse(
            "properties:house_status_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        response = self.client.post(url, {"status": House.Status.OFFER})
        self.assertEqual(response.status_code, 403)
        self.house.refresh_from_db()
        self.assertNotEqual(self.house.status, House.Status.OFFER)

    def test_house_detail_and_list_render_status_shortcut(self):
        detail_url = reverse(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        status_update_url = reverse(
            "properties:house_status_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        self.assertContains(response, status_update_url)

        list_url = reverse(
            "properties:house_list",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, status_update_url)

    def test_favorite_model_and_house_helpers(self):
        user2 = User.objects.create_user(username="user2", password="password")
        Membership.objects.create(
            workspace=self.workspace,
            user=user2,
            role=Role.EDITOR,
        )

        self.assertFalse(self.house.is_favorited_by(self.user))
        self.assertFalse(self.house.is_favorited_by(user2))
        self.assertEqual(self.house.favorite_count, 0)

        # Create favorite
        fav = Favorite.objects.create(house=self.house, user=self.user)
        self.assertIn("favorited", str(fav))
        self.assertTrue(self.house.is_favorited_by(self.user))
        self.assertFalse(self.house.is_favorited_by(user2))
        self.assertEqual(self.house.favorite_count, 1)

    def test_lovable_rating_calculation(self):
        # Initial: no rating, no favorites
        self.assertIsNone(self.house.lovable_rating)
        self.assertEqual(self.house.lovable_rating_display, "—")
        self.assertIsNone(self.house.lovable_percentage)

        # Add second member to workspace (total 2 members)
        user2 = User.objects.create_user(username="user2", password="password")
        Membership.objects.create(
            workspace=self.workspace,
            user=user2,
            role=Role.EDITOR,
        )

        # Adding a favorite has NO effect on lovable rating
        fav1 = Favorite.objects.create(house=self.house, user=self.user)
        self.assertIsNone(self.house.lovable_rating)
        self.assertEqual(self.house.lovable_rating_display, "—")
        self.assertIsNone(self.house.lovable_percentage)

        # Rating with love_score 7/10
        r1 = Rating.objects.create(house=self.house, user=self.user, score=8, love_score=7)
        self.assertEqual(self.house.lovable_rating, 7.0)
        self.assertEqual(self.house.lovable_rating_display, "7.0")
        self.assertEqual(self.house.lovable_percentage, 70)
        self.assertEqual(self.house.avg_rating, 8.0)

        # Second member adds rating with love_score 10/10 (average love_score = (7 + 10) / 2 = 8.5)
        r2 = Rating.objects.create(house=self.house, user=user2, score=10, love_score=10)
        self.assertEqual(self.house.lovable_rating, 8.5)
        self.assertEqual(self.house.lovable_rating_display, "8.5")
        self.assertEqual(self.house.lovable_percentage, 85)
        self.assertEqual(self.house.avg_rating, 9.0)

        # Third rating without love_score (love_score is None) -> avg love score stays 8.5
        user3 = User.objects.create_user(username="user3", password="password")
        Membership.objects.create(workspace=self.workspace, user=user3, role=Role.EDITOR)
        r3 = Rating.objects.create(house=self.house, user=user3, score=6, love_score=None)
        self.assertEqual(self.house.lovable_rating, 8.5)
        self.assertEqual(self.house.avg_rating, 8.0)

        # Favorite deletion does not change lovable rating
        fav1.delete()
        self.assertEqual(self.house.lovable_rating, 8.5)

    def test_house_favorite_toggle_view(self):
        url = reverse(
            "properties:house_favorite_toggle",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )

        # Toggle on (standard POST)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Favorite.objects.filter(house=self.house, user=self.user).exists())

        # Toggle off (standard POST with next URL)
        next_url = reverse("properties:house_list", kwargs={"workspace_slug": self.workspace.slug})
        response = self.client.post(url, {"next": next_url})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, next_url)
        self.assertFalse(Favorite.objects.filter(house=self.house, user=self.user).exists())

        # Toggle via AJAX/JSON header
        ajax_response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(ajax_response.status_code, 200)
        json_data = ajax_response.json()
        self.assertTrue(json_data["favorited"])
        self.assertEqual(json_data["favorite_count"], 1)

    def test_house_list_filter_favorites(self):
        house2 = House.objects.create(
            workspace=self.workspace,
            title="Seaside Cottage",
            price=300000,
        )
        # Favorite only self.house
        Favorite.objects.create(house=self.house, user=self.user)

        list_url = reverse(
            "properties:house_list",
            kwargs={"workspace_slug": self.workspace.slug},
        )

        # Standard list contains both houses
        response = self.client.get(list_url)
        self.assertContains(response, "Modern Villa")
        self.assertContains(response, "Seaside Cottage")

        # Filtered by favorites contains only self.house
        fav_response = self.client.get(list_url, {"favorites": "1"})
        self.assertContains(fav_response, "Modern Villa")
        self.assertNotContains(fav_response, "Seaside Cottage")

    def test_house_detail_and_list_render_favorite_and_lovable_rating(self):
        Favorite.objects.create(house=self.house, user=self.user)
        Rating.objects.create(house=self.house, user=self.user, score=9, love_score=8)

        detail_url = reverse(
            "properties:house_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.house.pk},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lovable Rating")
        self.assertContains(response, "Favorited")
        self.assertContains(response, "8.0")

        list_url = reverse(
            "properties:house_list",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "bi-heart-fill text-danger")
        self.assertContains(list_response, "8.0")
