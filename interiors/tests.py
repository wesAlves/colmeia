from __future__ import annotations

import json
from decimal import Decimal

from io import BytesIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import Membership, Role, Workspace
from interiors.admin import (
    InteriorProjectAdmin,
    ItemAdmin,
    ItemInline,
    MoodboardImageAdmin,
    OptionAdmin,
    OptionImageAdmin,
    OptionImageInline,
    RoomAdmin,
    RoomInline,
)
from interiors.forms import (
    BaseOptionImageFormSet,
    InteriorProjectForm,
    ItemForm,
    MoodboardImageForm,
    OptionForm,
    OptionImageForm,
    OptionImageFormSet,
    RoomForm,
)
from interiors.models import (
    InteriorProject,
    Item,
    MoodboardImage,
    Option,
    OptionImage,
    Room,
)
from properties.models import House

User = get_user_model()


class InteriorModelsTest(TestCase):
    """Test suite for the models in the interiors app."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(username="designer", password="password")
        self.workspace = Workspace.objects.create(name="Design Workspace", created_by=self.user)
        self.house = House.objects.create(
            workspace=self.workspace,
            title="Sunny Villa",
            created_by=self.user,
        )

    def test_interior_project_creation_and_properties(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Main Renovation",
            budget=Decimal("25000.00"),
            currency="EUR",
        )
        self.assertEqual(str(project), "Main Renovation")
        self.assertEqual(project.budget_display, "25,000.00 EUR")

        # Test project with no budget
        no_budget_project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Minimal Project",
        )
        self.assertEqual(no_budget_project.budget_display, "—")

    def test_room_creation_and_ordering(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="House Interior",
        )
        room_b = Room.objects.create(
            project=project,
            name="Kitchen",
            order=2,
            area_sqm=Decimal("18.50"),
            width_m=Decimal("3.70"),
            length_m=Decimal("5.00"),
            height_m=Decimal("2.80"),
            floor_material="Polished Concrete",
            wall_color_hex="#F0EDE6",
            lighting_notes="Pendant tracks above kitchen island",
        )
        room_a = Room.objects.create(project=project, name="Living Room", order=1)

        self.assertEqual(str(room_a), "Living Room")
        self.assertEqual(room_a.workspace, self.workspace)
        self.assertEqual(room_b.area_sqm, Decimal("18.50"))
        self.assertEqual(room_b.width_m, Decimal("3.70"))
        self.assertEqual(room_b.length_m, Decimal("5.00"))
        self.assertEqual(room_b.height_m, Decimal("2.80"))
        self.assertEqual(room_b.floor_material, "Polished Concrete")
        self.assertEqual(room_b.wall_color_hex, "#F0EDE6")
        self.assertEqual(room_b.lighting_notes, "Pendant tracks above kitchen island")
        self.assertEqual(list(project.rooms.all()), [room_a, room_b])

    def test_item_choices_and_properties(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Decor Project",
        )
        room = Room.objects.create(project=project, name="Master Bedroom", order=1)
        item = Item.objects.create(
            room=room,
            name="King Bed Frame",
            category=Item.Category.FURNITURE,
            priority=Item.Priority.ESSENTIAL,
            status=Item.Status.RESEARCHING,
            is_fixed=False,
            is_custom_made=True,
            style="Scandinavian",
            width_cm=180,
            depth_cm=200,
            height_cm=110,
            material="Solid White Oak",
            color_hex="#D4B996",
            notes="Oak wood preferred",
        )

        self.assertEqual(str(item), "King Bed Frame")
        self.assertEqual(item.workspace, self.workspace)
        self.assertEqual(item.category_display, "Furniture")
        self.assertEqual(item.priority_display, "Essential")
        self.assertEqual(item.status_display, "Researching")
        self.assertTrue(item.is_custom_made)
        self.assertEqual(item.style, "Scandinavian")
        self.assertEqual(item.width_cm, 180)
        self.assertEqual(item.depth_cm, 200)
        self.assertEqual(item.height_cm, 110)
        self.assertEqual(item.material, "Solid White Oak")
        self.assertEqual(item.color_hex, "#D4B996")
        self.assertIsNone(item.chosen_option)
        self.assertIsNone(item.price)
        self.assertEqual(item.price_display, "—")

    def test_option_selection_and_project_cost_calculations(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Full Furnishing",
            budget=Decimal("5000.00"),
            currency="EUR",
        )
        room = Room.objects.create(project=project, name="Living Room")
        item1 = Item.objects.create(
            room=room,
            name="Sofa",
            category=Item.Category.FURNITURE,
            priority=Item.Priority.ESSENTIAL,
            status=Item.Status.CHOSEN,
        )
        item2 = Item.objects.create(
            room=room,
            name="Coffee Table",
            category=Item.Category.FURNITURE,
            priority=Item.Priority.IMPORTANT,
            status=Item.Status.CHOSEN,
        )

        option1_a = Option.objects.create(
            item=item1,
            name="Nordic 3-Seater",
            price=Decimal("1200.00"),
            store="IKEA",
            is_chosen=True,
            added_by=self.user,
        )
        Option.objects.create(
            item=item1,
            name="Luxury Velvet",
            price=Decimal("2500.00"),
            store="West Elm",
            is_chosen=False,
            added_by=self.user,
        )
        option2_a = Option.objects.create(
            item=item2,
            name="Round Oak Table",
            price=Decimal("350.00"),
            store="Zara Home",
            is_chosen=True,
            added_by=self.user,
        )

        self.assertEqual(str(option1_a), "Nordic 3-Seater")
        self.assertEqual(option1_a.workspace, self.workspace)
        self.assertEqual(option1_a.price_display, "1,200.00 EUR")

        self.assertEqual(item1.chosen_option, option1_a)
        self.assertEqual(item1.price, Decimal("1200.00"))
        self.assertEqual(item1.price_display, "1,200.00 EUR")

        self.assertEqual(room.total_estimated_cost, Decimal("1550.00"))
        self.assertEqual(room.total_estimated_cost_display, "1,550.00 EUR")

        self.assertEqual(project.total_estimated_cost, Decimal("1550.00"))
        self.assertEqual(project.total_estimated_cost_display, "1,550.00 EUR")

    def test_single_chosen_option_enforcement(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Single Chosen Test",
        )
        room = Room.objects.create(project=project, name="Dining Room")
        item = Item.objects.create(
            room=room,
            name="Dining Chairs",
            is_custom_made=False,
            style="Mid-Century",
        )

        opt1 = Option.objects.create(
            item=item,
            name="Chair Model A",
            price=Decimal("150.00"),
            finish="Solid Oak",
            lead_time_days=7,
            is_chosen=True,
            added_by=self.user,
        )
        self.assertTrue(opt1.is_chosen)
        self.assertEqual(opt1.finish, "Solid Oak")
        self.assertEqual(opt1.lead_time_days, 7)

        # Creating another option with is_chosen=True resets the first one
        opt2 = Option.objects.create(
            item=item,
            name="Chair Model B",
            price=Decimal("180.00"),
            finish="Bouclé Fabric",
            lead_time_days=14,
            is_chosen=True,
            added_by=self.user,
        )
        opt1.refresh_from_db()
        self.assertFalse(opt1.is_chosen)
        self.assertTrue(opt2.is_chosen)

        # Saving opt1 again with is_chosen=True resets opt2
        opt1.is_chosen = True
        opt1.save()
        opt2.refresh_from_db()
        self.assertTrue(opt1.is_chosen)
        self.assertFalse(opt2.is_chosen)

    def test_option_images_and_primary_image(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Decor Project",
        )
        room = Room.objects.create(project=project, name="Living Room")
        item = Item.objects.create(room=room, name="Armchair")
        option = Option.objects.create(item=item, name="Leather Chair", added_by=self.user)

        # No images yet
        self.assertIsNone(option.primary_image)

        # Add image 1 (not cover)
        dummy_file1 = SimpleUploadedFile("chair1.jpg", b"image1", content_type="image/jpeg")
        img1 = OptionImage.objects.create(option=option, image=dummy_file1, is_cover=False)
        self.assertEqual(option.primary_image, img1)
        self.assertEqual(str(img1), "Image for Leather Chair")
        self.assertTrue(bool(img1.url))

        # Add image 2 (is_cover=True)
        dummy_file2 = SimpleUploadedFile("chair2.jpg", b"image2", content_type="image/jpeg")
        img2 = OptionImage.objects.create(option=option, image=dummy_file2, is_cover=True)
        self.assertEqual(option.primary_image, img2)

    def test_moodboard_image_creation_and_properties(self) -> None:
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Inspiration Phase",
        )
        room = Room.objects.create(project=project, name="Bathroom")
        dummy_file = SimpleUploadedFile("palette.jpg", b"image_data", content_type="image/jpeg")

        moodboard = MoodboardImage.objects.create(
            room=room,
            image=dummy_file,
            caption="Warm beige tones",
            hex_color="#E8D8C8",
            order=2,
            is_cover=True,
            added_by=self.user,
        )

        self.assertEqual(str(moodboard), "Warm beige tones")
        self.assertEqual(moodboard.workspace, self.workspace)
        self.assertEqual(moodboard.color_display, "#E8D8C8")
        self.assertEqual(moodboard.order, 2)
        self.assertTrue(moodboard.is_cover)
        self.assertTrue(bool(moodboard.url))

        # Without caption or hex_color
        moodboard2 = MoodboardImage.objects.create(
            room=room,
            image=dummy_file,
            order=1,
            added_by=self.user,
        )
        self.assertEqual(str(moodboard2), "Moodboard image for Bathroom")
        self.assertEqual(moodboard2.color_display, "—")
        self.assertEqual(moodboard2.order, 1)
        self.assertFalse(moodboard2.is_cover)


class InteriorAdminTest(TestCase):
    """Test suite verifying Django admin registrations for the interiors app."""

    def test_admin_registrations_and_configurations(self) -> None:
        self.assertTrue(admin.site.is_registered(InteriorProject))
        self.assertTrue(admin.site.is_registered(Room))
        self.assertTrue(admin.site.is_registered(Item))
        self.assertTrue(admin.site.is_registered(Option))
        self.assertTrue(admin.site.is_registered(OptionImage))
        self.assertTrue(admin.site.is_registered(MoodboardImage))

        project_admin = admin.site._registry[InteriorProject]
        self.assertEqual(
            project_admin.list_display,
            ("title", "house", "budget_display", "total_estimated_cost_display"),
        )
        self.assertIn(RoomInline, project_admin.inlines)

        room_admin = admin.site._registry[Room]
        self.assertEqual(
            room_admin.list_display,
            (
                "name",
                "project",
                "order",
                "area_sqm",
                "width_m",
                "length_m",
                "height_m",
                "floor_material",
                "wall_color_hex",
                "total_estimated_cost_display",
            ),
        )
        self.assertIn(ItemInline, room_admin.inlines)

        item_admin = admin.site._registry[Item]
        self.assertEqual(
            item_admin.list_display,
            (
                "name",
                "room",
                "category",
                "priority_display",
                "status_display",
                "is_custom_made",
                "style",
                "material",
                "color_hex",
                "price_display",
            ),
        )

        option_admin = admin.site._registry[Option]
        self.assertEqual(
            option_admin.list_display,
            (
                "name",
                "item",
                "price_display",
                "store",
                "finish",
                "lead_time_days",
                "is_chosen",
                "added_by",
            ),
        )
        self.assertIn(OptionImageInline, option_admin.inlines)

        moodboard_admin = admin.site._registry[MoodboardImage]
        self.assertEqual(
            moodboard_admin.list_display,
            ("room", "caption", "color_display", "added_by"),
        )


class InteriorViewsTest(TestCase):
    """Test suite verifying CBVs, permissions, queries, and context in the interiors app."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="owner", password="password")
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.outsider = User.objects.create_user(username="outsider", password="password")

        self.workspace = Workspace.objects.create(name="Interior Workspace", created_by=self.owner)
        Membership.objects.create(workspace=self.workspace, user=self.viewer, role=Role.VIEWER)

        self.other_workspace = Workspace.objects.create(name="Other Workspace", created_by=self.outsider)

        self.house = House.objects.create(
            workspace=self.workspace,
            title="City Loft",
            created_by=self.owner,
        )
        self.other_house = House.objects.create(
            workspace=self.other_workspace,
            title="Other House",
            created_by=self.outsider,
        )

        self.project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Loft Interior",
            budget=Decimal("10000.00"),
            currency="EUR",
        )
        self.room = Room.objects.create(
            project=self.project,
            name="Living Room",
            order=1,
            area_sqm=Decimal("25.00"),
            width_m=Decimal("5.00"),
            length_m=Decimal("5.00"),
            height_m=Decimal("3.00"),
        )
        self.item = Item.objects.create(
            room=self.room,
            name="Modular Sofa",
            category=Item.Category.FURNITURE,
            priority=Item.Priority.ESSENTIAL,
            status=Item.Status.CHOSEN,
            width_cm=240,
            depth_cm=100,
            height_cm=85,
            material="Performance Velvet",
            color_hex="#4A6B82",
        )
        self.option = Option.objects.create(
            item=self.item,
            name="Sectional Grey",
            price=Decimal("1800.00"),
            store="Design Within Reach",
            is_chosen=True,
            added_by=self.owner,
        )
        self.option_image = OptionImage.objects.create(
            option=self.option,
            image=self._generate_test_image("sofa_opt.png"),
            is_cover=True,
        )
        self.moodboard = MoodboardImage.objects.create(
            room=self.room,
            image=self._generate_test_image("board.png"),
            caption="Nordic palette",
            hex_color="#D8C29D",
            added_by=self.owner,
        )

    def _generate_test_image(self, name: str = "test.png") -> SimpleUploadedFile:
        file = BytesIO()
        image = Image.new("RGBA", size=(50, 50), color=(200, 100, 50))
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type="image/png")

    def test_project_list_view_access_and_scoping(self) -> None:
        url = reverse("interiors:project_list", kwargs={"workspace_slug": self.workspace.slug})

        # Unauthenticated redirects to login
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Non-member gets 403 Forbidden
        self.client.login(username="outsider", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Member gets 200 OK and sees workspace project
        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.project, response.context["projects"])
        self.assertEqual(response.context["workspace"], self.workspace)
        self.assertEqual(response.template_name[0], "interiors/project_list.html")

    def test_project_detail_view_context_and_totals(self) -> None:
        url = reverse("interiors:project_detail", kwargs={"workspace_slug": self.workspace.slug, "pk": self.project.pk})

        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.context["workspace"], self.workspace)
        self.assertIn("rooms", response.context)
        self.assertEqual(list(response.context["rooms"]), [self.room])
        self.assertIn("rooms_with_totals", response.context)
        self.assertEqual(response.context["rooms_with_totals"][0]["total_estimated_cost"], Decimal("1800.00"))
        self.assertEqual(response.context["total_estimated_cost"], Decimal("1800.00"))
        self.assertEqual(response.template_name[0], "interiors/project_detail.html")

    def test_project_create_view_and_permissions(self) -> None:
        url = reverse("interiors:project_create", kwargs={"workspace_slug": self.workspace.slug})

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Owner creates a project
        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "interiors/project_form.html")

        post_data = {
            "title": "Kitchen Remodel",
            "house": self.house.pk,
            "budget": "15000.00",
            "currency": "EUR",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)

        new_project = InteriorProject.objects.get(title="Kitchen Remodel")
        self.assertEqual(new_project.workspace, self.workspace)
        self.assertEqual(new_project.house, self.house)
        self.assertEqual(new_project.budget, Decimal("15000.00"))

        # Verify success message
        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(any("Interior project created successfully" in str(m) for m in messages))

    def test_project_update_view(self) -> None:
        url = reverse(
            "interiors:project_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.project.pk},
        )

        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            "title": "Updated Loft Interior",
            "house": self.house.pk,
            "budget": "12000.00",
            "currency": "EUR",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Updated Loft Interior")
        self.assertEqual(self.project.budget, Decimal("12000.00"))

    def test_room_detail_view(self) -> None:
        url = reverse(
            "interiors:room_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.room.pk},
        )

        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.context["workspace"], self.workspace)
        self.assertIn(self.item, response.context["items"])
        self.assertIn(self.moodboard, response.context["moodboard_images"])
        self.assertEqual(response.context["total_estimated_cost"], Decimal("1800.00"))
        self.assertEqual(response.template_name[0], "interiors/room_detail.html")

        # Verify unified moodboard_items context
        moodboard_items = response.context["moodboard_items"]
        self.assertTrue(any(i["type"] == "inspiration" for i in moodboard_items))
        self.assertTrue(any(i["type"] == "chosen_option" for i in moodboard_items))

        insp_item = next(i for i in moodboard_items if i["type"] == "inspiration")
        self.assertEqual(insp_item["caption"], self.moodboard.caption)
        self.assertEqual(insp_item["hex"], self.moodboard.hex_color)

        chosen_item = next(i for i in moodboard_items if i["type"] == "chosen_option")
        self.assertEqual(chosen_item["caption"], self.option.name)
        self.assertEqual(chosen_item["price"], self.option.price_display)

    def test_item_detail_view(self) -> None:
        self.option.finish = "Italian Leather"
        self.option.lead_time_days = 21
        self.option.save()

        url = reverse(
            "interiors:item_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.item.pk},
        )

        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["item"], self.item)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["workspace"], self.workspace)
        self.assertIn(self.option, response.context["options"])
        self.assertEqual(response.context["chosen_option"], self.option)
        self.assertEqual(response.template_name[0], "interiors/item_detail.html")

        content = response.content.decode("utf-8")
        self.assertIn("Escolhido", content)
        self.assertIn("Italian Leather", content)
        self.assertIn("21 dias", content)

    def test_form_filters_house_by_workspace(self) -> None:
        form = InteriorProjectForm(workspace=self.workspace)
        houses = list(form.fields["house"].queryset)
        self.assertIn(self.house, houses)
        self.assertNotIn(self.other_house, houses)

    def test_forms_validation(self) -> None:
        # RoomForm
        room_form = RoomForm(
            data={
                "name": "Attic Office",
                "order": 3,
                "area_sqm": "15.20",
                "width_m": "3.80",
                "length_m": "4.00",
                "height_m": "2.60",
                "floor_material": "Herringbone Oak",
                "wall_color_hex": "#FAF6F0",
                "lighting_notes": "Skylight on North wall",
            },
            workspace=self.workspace,
        )
        self.assertTrue(room_form.is_valid())

        # ItemForm
        item_form = ItemForm(
            data={
                "name": "Standing Desk",
                "category": Item.Category.FURNITURE,
                "priority": Item.Priority.ESSENTIAL,
                "status": Item.Status.TODO,
                "is_fixed": False,
                "is_custom_made": True,
                "style": "Industrial Modern",
                "width_cm": 160,
                "depth_cm": 80,
                "height_cm": 120,
                "material": "Solid Walnut & Steel",
                "color_hex": "#5C4033",
                "notes": "Electric standing desk 160x80cm",
            },
            workspace=self.workspace,
        )
        self.assertTrue(item_form.is_valid())

        # OptionForm
        option_form = OptionForm(
            data={
                "name": "FlexiSpot E7",
                "price": "499.99",
                "store": "FlexiSpot",
                "url": "https://flexispot.com/e7",
                "finish": "Dark Walnut Top",
                "lead_time_days": 10,
                "is_chosen": True,
            },
            workspace=self.workspace,
        )
        self.assertTrue(option_form.is_valid())

        # OptionImageForm
        image = self._generate_test_image("opt.png")
        option_img_form = OptionImageForm(
            data={"is_cover": True},
            files={"image": image},
        )
        self.assertTrue(option_img_form.is_valid())

        # BaseOptionImageFormSet
        formset = BaseOptionImageFormSet(
            data={
                "images-TOTAL_FORMS": "5",
                "images-INITIAL_FORMS": "0",
                "images-MIN_NUM_FORMS": "0",
                "images-MAX_NUM_FORMS": "5",
                "images-0-is_cover": True,
            },
            files={"images-0-image": image},
            instance=self.option,
        )
        self.assertTrue(formset.is_valid())

        # MoodboardImageForm
        mb_image = self._generate_test_image("mood.png")
        moodboard_form = MoodboardImageForm(
            data={"caption": "Oak textures", "hex_color": "#D3B89D"},
            files={"image": mb_image},
            workspace=self.workspace,
        )
        self.assertTrue(moodboard_form.is_valid())

    def test_room_create_and_update_views(self) -> None:
        create_url = reverse(
            "interiors:room_create",
            kwargs={"workspace_slug": self.workspace.slug, "project_pk": self.project.pk},
        )

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        self.assertEqual(self.client.get(create_url).status_code, 403)

        # Owner gets 200
        self.client.login(username="owner", password="password")
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.template_name[0], "interiors/room_form.html")

        # Owner posts new room
        post_response = self.client.post(create_url, {"name": "Balcony Garden", "order": 4})
        self.assertEqual(post_response.status_code, 302)
        new_room = Room.objects.get(name="Balcony Garden")
        self.assertEqual(new_room.project, self.project)
        self.assertEqual(new_room.order, 4)
        self.assertRedirects(
            post_response,
            reverse(
                "interiors:room_detail",
                kwargs={"workspace_slug": self.workspace.slug, "pk": new_room.pk},
            ),
        )

        # Update room
        update_url = reverse(
            "interiors:room_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": new_room.pk},
        )
        update_response = self.client.post(update_url, {"name": "Sun Terrace", "order": 5})
        self.assertEqual(update_response.status_code, 302)
        new_room.refresh_from_db()
        self.assertEqual(new_room.name, "Sun Terrace")
        self.assertEqual(new_room.order, 5)

    def test_item_create_and_update_views(self) -> None:
        create_url = reverse(
            "interiors:item_create",
            kwargs={"workspace_slug": self.workspace.slug, "room_pk": self.room.pk},
        )

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        self.assertEqual(self.client.get(create_url).status_code, 403)

        # Owner gets 200
        self.client.login(username="owner", password="password")
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.template_name[0], "interiors/item_form.html")

        # Post item
        post_data = {
            "name": "Coffee Table",
            "category": Item.Category.FURNITURE,
            "priority": Item.Priority.DESIRABLE,
            "status": Item.Status.RESEARCHING,
            "is_fixed": False,
            "notes": "Walnut finish",
        }
        post_response = self.client.post(create_url, post_data)
        self.assertEqual(post_response.status_code, 302)
        new_item = Item.objects.get(name="Coffee Table")
        self.assertEqual(new_item.room, self.room)
        self.assertRedirects(
            post_response,
            reverse(
                "interiors:item_detail",
                kwargs={"workspace_slug": self.workspace.slug, "pk": new_item.pk},
            ),
        )

        # Update item
        update_url = reverse(
            "interiors:item_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": new_item.pk},
        )
        post_data["name"] = "Round Coffee Table"
        update_response = self.client.post(update_url, post_data)
        self.assertEqual(update_response.status_code, 302)
        new_item.refresh_from_db()
        self.assertEqual(new_item.name, "Round Coffee Table")

    def test_option_create_and_update_views(self) -> None:
        create_url = reverse(
            "interiors:option_create",
            kwargs={"workspace_slug": self.workspace.slug, "item_pk": self.item.pk},
        )

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        self.assertEqual(self.client.get(create_url).status_code, 403)

        # Owner gets 200
        self.client.login(username="owner", password="password")
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["item"], self.item)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.template_name[0], "interiors/option_form.html")

        # Post option with formset image
        image = self._generate_test_image("sofa.png")
        post_data = {
            "name": "Article Sven Sofa",
            "price": "1999.00",
            "store": "Article",
            "url": "https://article.com/sven",
            "is_chosen": False,
            "images-TOTAL_FORMS": "5",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "5",
            "images-0-image": image,
            "images-0-is_cover": True,
        }
        post_response = self.client.post(create_url, post_data)
        self.assertEqual(post_response.status_code, 302)
        new_opt = Option.objects.get(name="Article Sven Sofa")
        self.assertEqual(new_opt.item, self.item)
        self.assertEqual(new_opt.added_by, self.owner)
        self.assertEqual(new_opt.price, Decimal("1999.00"))
        self.assertEqual(new_opt.images.count(), 1)
        self.assertTrue(new_opt.primary_image.is_cover)
        self.assertRedirects(
            post_response,
            reverse(
                "interiors:item_detail",
                kwargs={"workspace_slug": self.workspace.slug, "pk": self.item.pk},
            ),
        )

        # Update option
        update_url = reverse(
            "interiors:option_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": new_opt.pk},
        )
        update_image = self._generate_test_image("sofa_updated.png")
        first_img = new_opt.images.first()
        update_post_data = {
            "name": "Article Sven Sofa",
            "price": "1899.00",
            "store": "Article",
            "url": "https://article.com/sven",
            "is_chosen": True,
            "images-TOTAL_FORMS": "5",
            "images-INITIAL_FORMS": "1",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "5",
            "images-0-id": str(first_img.id),
            "images-0-is_cover": False,
            "images-1-image": update_image,
            "images-1-is_cover": True,
        }
        update_response = self.client.post(update_url, update_post_data)
        self.assertEqual(update_response.status_code, 302)
        new_opt.refresh_from_db()
        self.assertEqual(new_opt.price, Decimal("1899.00"))
        self.assertTrue(new_opt.is_chosen)
        self.assertEqual(new_opt.images.count(), 2)
        self.assertTrue(new_opt.primary_image.is_cover)

    def test_moodboard_image_create_and_update_views(self) -> None:
        create_url = reverse(
            "interiors:moodboard_image_create",
            kwargs={"workspace_slug": self.workspace.slug, "room_pk": self.room.pk},
        )

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        self.assertEqual(self.client.get(create_url).status_code, 403)

        # Owner gets 200
        self.client.login(username="owner", password="password")
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.template_name[0], "interiors/moodboard_image_form.html")

        # Post moodboard image
        image = self._generate_test_image("palette.png")
        post_data = {
            "caption": "Earthy Tones & Natural Woods",
            "hex_color": "#C4A482",
            "image": image,
        }
        post_response = self.client.post(create_url, post_data)
        self.assertEqual(post_response.status_code, 302)
        new_mb = MoodboardImage.objects.get(caption="Earthy Tones & Natural Woods")
        self.assertEqual(new_mb.room, self.room)
        self.assertEqual(new_mb.added_by, self.owner)
        self.assertEqual(new_mb.hex_color, "#C4A482")
        self.assertRedirects(
            post_response,
            reverse(
                "interiors:room_detail",
                kwargs={"workspace_slug": self.workspace.slug, "pk": self.room.pk},
            ),
        )

        # Update moodboard image
        update_url = reverse(
            "interiors:moodboard_image_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": new_mb.pk},
        )
        post_data["caption"] = "Earthy Tones & Warm Woods"
        post_data["image"] = self._generate_test_image("palette_updated.png")
        update_response = self.client.post(update_url, post_data)
        self.assertEqual(update_response.status_code, 302)
        new_mb.refresh_from_db()
        self.assertEqual(new_mb.caption, "Earthy Tones & Warm Woods")

    def test_moodboard_image_reorder_view(self) -> None:
        reorder_url = reverse(
            "interiors:moodboard_image_reorder",
            kwargs={"workspace_slug": self.workspace.slug, "room_pk": self.room.pk},
        )

        mb1 = MoodboardImage.objects.create(
            room=self.room,
            image=self._generate_test_image("mb1.png"),
            caption="First Image",
            order=0,
            added_by=self.owner,
        )
        mb2 = MoodboardImage.objects.create(
            room=self.room,
            image=self._generate_test_image("mb2.png"),
            caption="Second Image",
            order=1,
            added_by=self.owner,
        )
        mb3 = MoodboardImage.objects.create(
            room=self.room,
            image=self._generate_test_image("mb3.png"),
            caption="Third Image",
            order=2,
            added_by=self.owner,
        )

        # Viewer without edit rights gets 403
        self.client.login(username="viewer", password="password")
        viewer_res = self.client.post(
            reorder_url,
            data=json.dumps({"order": [mb3.pk, mb1.pk, mb2.pk]}),
            content_type="application/json",
        )
        self.assertEqual(viewer_res.status_code, 403)

        # Owner reorders images via JSON
        self.client.login(username="owner", password="password")
        owner_res = self.client.post(
            reorder_url,
            data=json.dumps({"order": [mb3.pk, mb1.pk, mb2.pk]}),
            content_type="application/json",
        )
        self.assertEqual(owner_res.status_code, 200)
        json_data = owner_res.json()
        self.assertEqual(json_data["status"], "success")

        mb1.refresh_from_db()
        mb2.refresh_from_db()
        mb3.refresh_from_db()

        self.assertEqual(mb3.order, 0)
        self.assertEqual(mb1.order, 1)
        self.assertEqual(mb2.order, 2)

        # Test global reorder endpoint with form data
        global_reorder_url = reverse(
            "interiors:moodboard_image_reorder_general",
            kwargs={"workspace_slug": self.workspace.slug},
        )
        form_res = self.client.post(
            global_reorder_url,
            data={"order[]": [mb2.pk, mb3.pk, mb1.pk]},
        )
        self.assertEqual(form_res.status_code, 200)
        mb1.refresh_from_db()
        mb2.refresh_from_db()
        mb3.refresh_from_db()

        self.assertEqual(mb2.order, 0)
        self.assertEqual(mb3.order, 1)
        self.assertEqual(mb1.order, 2)
