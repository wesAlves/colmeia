from io import BytesIO
from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Membership, Role, Workspace
from properties.models import Feature, FeatureValue, House, HousePhoto, Rating

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
