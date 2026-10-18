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
    OptionRatingAdmin,
    RoomAdmin,
    RoomInline,
    StyleAdmin,
)
from interiors.forms import (
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
from interiors.models import (
    InteriorProject,
    Item,
    MoodboardImage,
    Option,
    OptionImage,
    OptionRating,
    Room,
    Style,
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
        scandinavian_style = Style.objects.get(slug="escandinavo")
        item = Item.objects.create(
            room=room,
            name="King Bed Frame",
            category=Item.Category.FURNITURE,
            priority=Item.Priority.ESSENTIAL,
            status=Item.Status.RESEARCHING,
            connection_type=Item.ConnectionType.NONE,
            requires_wall_anchor=True,
            is_fixed=False,
            is_custom_made=True,
            custom_style_text="Nordic Custom",
            width_cm=180,
            depth_cm=200,
            height_cm=110,
            material="Solid White Oak",
            color_hex="#D4B996",
            notes="Oak wood preferred",
        )
        item.style.add(scandinavian_style)

        self.assertEqual(str(item), "King Bed Frame")
        self.assertEqual(item.workspace, self.workspace)
        self.assertEqual(item.category_display, "Furniture")
        self.assertEqual(item.priority_display, "Essential")
        self.assertEqual(item.status_display, "Researching")
        self.assertTrue(item.is_custom_made)
        self.assertTrue(item.requires_wall_anchor)
        self.assertIn(scandinavian_style, item.style.all())
        self.assertIn("Escandinavo", item.styles_display)
        self.assertIn("Nordic Custom", item.styles_display)
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
            custom_style_text="Mid-Century",
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
        self.assertTrue(admin.site.is_registered(Style))
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
                "priority_display",
                "budget_display",
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
                "connection_type_display",
                "requires_wall_anchor",
                "is_custom_made",
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
                "fits_palette",
                "fits_style",
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
        self.editor = User.objects.create_user(username="editor", password="password")
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.outsider = User.objects.create_user(username="outsider", password="password")

        self.workspace = Workspace.objects.create(name="Interior Workspace", created_by=self.owner)
        Membership.objects.create(workspace=self.workspace, user=self.editor, role=Role.EDITOR)
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
        # RoomForm with structured palette
        room_form = RoomForm(
            data={
                "name": "Attic Office",
                "order": 3,
                "priority": Room.Priority.ESSENTIAL,
                "budget": "5000.00",
                "concept_title": "Nordic Workspace",
                "concept_description": "Clean, light-filled attic studio",
                "area_sqm": "15.20",
                "width_m": "3.80",
                "length_m": "4.00",
                "height_m": "2.60",
                "floor_material": "Herringbone Oak",
                "floor_color_hex": "#E3D5C5",
                "baseboard_color_hex": "#FFFFFF",
                "ceiling_color_hex": "#FAFAFA",
                "wall_color_hex": "#FAF6F0",
                "lighting_notes": "Skylight on North wall",
                "palette_colors": '[{"hex": "#FAF6F0", "role": "dominant"}, {"hex": "#E3D5C5", "role": "secondary"}]',
            },
            workspace=self.workspace,
        )
        self.assertTrue(room_form.is_valid(), room_form.errors)

        # ItemForm
        industrial_style = Style.objects.get(slug="industrial")
        item_form = ItemForm(
            data={
                "name": "Standing Desk",
                "category": Item.Category.FURNITURE,
                "priority": Item.Priority.ESSENTIAL,
                "status": Item.Status.TODO,
                "connection_type": Item.ConnectionType.ELECTRICAL_220,
                "requires_wall_anchor": True,
                "is_fixed": False,
                "is_custom_made": True,
                "style": [industrial_style.pk],
                "custom_style_text": "Industrial Modern",
                "width_cm": 160,
                "depth_cm": 80,
                "height_cm": 120,
                "material": "Solid Walnut & Steel",
                "color_hex": "#5C4033",
                "notes": "Electric standing desk 160x80cm",
            },
            workspace=self.workspace,
        )
        self.assertTrue(item_form.is_valid(), item_form.errors)

        # OptionForm
        option_form = OptionForm(
            data={
                "name": "FlexiSpot E7",
                "price": "499.99",
                "store": "FlexiSpot",
                "url": "https://flexispot.com/e7",
                "finish": "Dark Walnut Top",
                "lead_time_days": 10,
                "fits_palette": True,
                "fits_style": True,
                "selected_palette_color_hex": "#5C4033",
                "is_chosen": True,
            },
            workspace=self.workspace,
        )
        self.assertTrue(option_form.is_valid(), option_form.errors)

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

    def test_room_moodboard_presentation_view(self) -> None:
        self.room.width_m = Decimal("4.50")
        self.room.length_m = Decimal("3.20")
        self.room.height_m = Decimal("2.80")
        self.room.area_sqm = Decimal("14.40")
        self.room.wall_color_hex = "#FAF8F5"
        self.room.save()

        # Add hex color to existing moodboard image
        self.moodboard.hex_color = "#C4A482"
        self.moodboard.order = 1
        self.moodboard.save()

        # Add another moodboard image with another hex color
        mb2 = MoodboardImage.objects.create(
            room=self.room,
            image=self._generate_test_image("mb_extra.png"),
            caption="Texture Inspiration",
            hex_color="#8C9A86",
            order=0,
            added_by=self.owner,
        )

        url = reverse(
            "interiors:room_moodboard_presentation",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.room.pk},
        )

        # Anonymous user gets redirected
        self.client.logout()
        res_anon = self.client.get(url)
        self.assertEqual(res_anon.status_code, 302)

        # Outsider gets 403 Forbidden
        self.client.login(username="outsider", password="password")
        res_outsider = self.client.get(url)
        self.assertEqual(res_outsider.status_code, 403)

        # Workspace member gets 200 OK
        self.client.login(username="owner", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "interiors/room_moodboard_presentation.html")

        # Verify context variables
        self.assertEqual(response.context["room"], self.room)
        self.assertEqual(response.context["project"], self.project)
        self.assertEqual(response.context["workspace"], self.workspace)
        self.assertIsNotNone(response.context["membership"])

        self.assertEqual(response.context["room_dimensions"], "4.50m × 3.20m × 2.80m")
        self.assertEqual(response.context["room_area"], "14.40 m²")

        # Verify presentation_items
        presentation_items = response.context["presentation_items"]
        self.assertEqual(len(presentation_items), 3)  # mb2, self.moodboard, chosen option

        # Check types
        insp_items = [i for i in presentation_items if i["type"] == "inspiration"]
        chosen_items = [i for i in presentation_items if i["type"] == "chosen_option"]
        self.assertEqual(len(insp_items), 2)
        self.assertEqual(len(chosen_items), 1)

        # Inspiration items order
        self.assertEqual(insp_items[0]["caption"], "Texture Inspiration")
        self.assertEqual(insp_items[1]["caption"], self.moodboard.caption)

        # Chosen item
        self.assertEqual(chosen_items[0]["caption"], self.option.name)

        # Verify palette_colors extracted from wall + moodboards
        palette_colors = response.context["palette_colors"]
        self.assertIn("#FAF8F5", palette_colors)
        self.assertIn("#8C9A86", palette_colors)
        self.assertIn("#C4A482", palette_colors)
        self.assertEqual(len(palette_colors), 3)

        # Verify HTML rendered content
        content = response.content.decode("utf-8")
        self.assertIn("Moodboard de Apresentação", content)
        self.assertIn("4.50m × 3.20m × 2.80m", content)
        self.assertIn("14.40 m²", content)
        self.assertIn("Paleta de Cores do Cômodo", content)
        self.assertIn("Escolhido", content)
        self.assertIn("Voltar para o Cômodo", content)
        self.assertIn("Editar Cômodo", content)

    def test_style_model_and_seeding(self) -> None:
        """Verify Style model creation, automatic slug generation, and standard styles."""
        # Check standard seeded styles
        self.assertTrue(Style.objects.filter(slug="japandi").exists())
        self.assertTrue(Style.objects.filter(slug="minimalista").exists())

        # Create custom style
        style = Style.objects.create(name="Warm Minimalist")
        self.assertEqual(style.slug, "warm-minimalist")
        self.assertEqual(str(style), "Warm Minimalist")

    def test_room_priority_budget_finishes_and_palette(self) -> None:
        """Verify room priority, budget, finishes and palette structure."""
        room = Room.objects.create(
            project=self.project,
            name="Living Studio",
            priority=Room.Priority.ESSENTIAL,
            budget=Decimal("12000.00"),
            concept_title="Organic Japandi Retreat",
            concept_description="Calm organic sanctuary with natural oak and neutral textiles",
            floor_color_hex="#D2B48C",
            baseboard_color_hex="#FFFFFF",
            wall_color_hex="#F5F2EB",
            ceiling_color_hex="#FAFAFA",
            palette_colors=[
                {"hex": "#F5F2EB", "role": "dominant"},
                {"hex": "#D2B48C", "role": "secondary"},
                {"hex": "#3E2723", "role": "accent"},
            ],
        )

        self.assertEqual(room.priority_display, "Essential")
        self.assertEqual(room.budget_display, "12,000.00 EUR")
        self.assertEqual(room.floor_color_hex, "#D2B48C")
        self.assertEqual(room.baseboard_color_hex, "#FFFFFF")
        self.assertEqual(room.wall_color_hex, "#F5F2EB")
        self.assertEqual(room.ceiling_color_hex, "#FAFAFA")
        self.assertEqual(len(room.palette_colors), 3)

        # Test items_by_priority property
        item_essential = Item.objects.create(
            room=room,
            name="Sofa Bed",
            priority=Item.Priority.ESSENTIAL,
        )
        item_desirable = Item.objects.create(
            room=room,
            name="Art Print",
            priority=Item.Priority.DESIRABLE,
        )

        grouped = room.items_by_priority
        self.assertIn(item_essential, grouped[Item.Priority.ESSENTIAL])
        self.assertIn(item_desirable, grouped[Item.Priority.DESIRABLE])
        self.assertEqual(len(grouped[Item.Priority.DREAM]), 0)

    def test_room_palette_validation(self) -> None:
        """Verify that room palette enforces max 7 colors and correct object format."""
        from django.core.exceptions import ValidationError

        invalid_room = Room(
            project=self.project,
            name="Overcolored Room",
            palette_colors=[{"hex": f"#{i:06x}"} for i in range(8)],
        )
        with self.assertRaises(ValidationError):
            invalid_room.clean()

        invalid_format_room = Room(
            project=self.project,
            name="Bad Format Room",
            palette_colors=["#FFFFFF"],
        )
        with self.assertRaises(ValidationError):
            invalid_format_room.clean()

    def test_item_technical_specs_and_dependencies(self) -> None:
        """Verify item technical requirements, wall anchoring, styles, and dependencies."""
        scand = Style.objects.get(slug="escandinavo")
        japandi = Style.objects.get(slug="japandi")

        parent_item = Item.objects.create(
            room=self.room,
            name="Kitchen Island Electrical Hub",
            category=Item.Category.FIXED,
            priority=Item.Priority.ESSENTIAL,
            connection_type=Item.ConnectionType.ELECTRICAL_220,
        )

        dependent_item = Item.objects.create(
            room=self.room,
            name="Built-In Induction Cooktop",
            category=Item.Category.APPLIANCE,
            priority=Item.Priority.ESSENTIAL,
            connection_type=Item.ConnectionType.ELECTRICAL_220,
            requires_wall_anchor=False,
            depends_on=parent_item,
            dependency_type=Item.DependencyType.ELECTRICAL,
            custom_style_text="Minimalist Tech",
        )
        dependent_item.style.add(scand, japandi)

        self.assertEqual(dependent_item.connection_type_display, "Electrical 220V")
        self.assertEqual(dependent_item.dependency_type_display, "Electrical")
        self.assertEqual(dependent_item.depends_on, parent_item)
        self.assertIn(scand, dependent_item.style.all())
        self.assertIn("Japandi", dependent_item.styles_display)
        self.assertIn("Minimalist Tech", dependent_item.styles_display)

    def test_option_palette_and_style_fit(self) -> None:
        """Verify option palette and style compatibility flags."""
        opt = Option.objects.create(
            item=self.item,
            name="Custom Oak Coffee Table",
            price=Decimal("450.00"),
            fits_palette=True,
            fits_style=False,
            selected_palette_color_hex="#D2B48C",
            added_by=self.owner,
        )
        self.assertTrue(opt.fits_palette)
        self.assertFalse(opt.fits_style)
        self.assertEqual(opt.selected_palette_color_hex, "#D2B48C")

    def test_project_detail_view_filtering(self) -> None:
        """Verify GET parameter filtering on ProjectDetailView (room priority, item status/style)."""
        scand = Style.objects.get(slug="escandinavo")
        boho = Style.objects.get(slug="boho")

        room_essential = Room.objects.create(
            project=self.project,
            name="Master Bedroom",
            priority=Room.Priority.ESSENTIAL,
        )
        item_boho = Item.objects.create(
            room=room_essential,
            name="Rattan Lamp",
            status=Item.Status.CHOSEN,
        )
        item_boho.style.add(boho)

        room_dream = Room.objects.create(
            project=self.project,
            name="Wine Cellar",
            priority=Room.Priority.DREAM,
        )
        item_scand = Item.objects.create(
            room=room_dream,
            name="Oak Rack",
            status=Item.Status.TODO,
        )
        item_scand.style.add(scand)

        self.client.login(username="owner", password="password")
        project_url = reverse(
            "interiors:project_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.project.pk},
        )

        # Filter by priority
        res_priority = self.client.get(f"{project_url}?priority=1")
        self.assertEqual(res_priority.status_code, 200)
        room_names = [r.name for r in res_priority.context["rooms"]]
        self.assertIn("Master Bedroom", room_names)
        self.assertNotIn("Wine Cellar", room_names)

        # Filter by item status
        res_status = self.client.get(f"{project_url}?status=todo")
        self.assertEqual(res_status.status_code, 200)
        room_names_status = [r.name for r in res_status.context["rooms"]]
        self.assertIn("Wine Cellar", room_names_status)
        self.assertNotIn("Master Bedroom", room_names_status)

        # Filter by style
        res_style = self.client.get(f"{project_url}?style=boho")
        self.assertEqual(res_style.status_code, 200)
        room_names_style = [r.name for r in res_style.context["rooms"]]
        self.assertIn("Master Bedroom", room_names_style)
        self.assertNotIn("Wine Cellar", room_names_style)

    def test_room_detail_view_filtering(self) -> None:
        """Verify GET parameter filtering on RoomDetailView for items."""
        japandi = Style.objects.get(slug="japandi")

        item1 = Item.objects.create(
            room=self.room,
            name="Smart Dishwasher",
            category=Item.Category.APPLIANCE,
            priority=Item.Priority.ESSENTIAL,
            status=Item.Status.TODO,
            connection_type=Item.ConnectionType.PLUMBING,
        )
        item1.style.add(japandi)

        item2 = Item.objects.create(
            room=self.room,
            name="Dining Pendant",
            category=Item.Category.DECOR,
            priority=Item.Priority.DESIRABLE,
            status=Item.Status.RESEARCHING,
            connection_type=Item.ConnectionType.ELECTRICAL_110,
        )

        self.client.login(username="owner", password="password")
        room_url = reverse(
            "interiors:room_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.room.pk},
        )

        # Filter by category
        res_cat = self.client.get(f"{room_url}?category=appliance")
        self.assertEqual(res_cat.status_code, 200)
        item_names = [i.name for i in res_cat.context["items"]]
        self.assertIn("Smart Dishwasher", item_names)
        self.assertNotIn("Dining Pendant", item_names)

        # Filter by connection type
        res_conn = self.client.get(f"{room_url}?connection_type=plumbing")
        self.assertEqual(res_conn.status_code, 200)
        item_names_conn = [i.name for i in res_conn.context["items"]]
        self.assertIn("Smart Dishwasher", item_names_conn)
        self.assertNotIn("Dining Pendant", item_names_conn)

        # Filter by style
        res_style = self.client.get(f"{room_url}?style=japandi")
        self.assertEqual(res_style.status_code, 200)
        item_names_style = [i.name for i in res_style.context["items"]]
        self.assertIn("Smart Dishwasher", item_names_style)
        self.assertNotIn("Dining Pendant", item_names_style)

    def test_project_budget_status_and_fallback_calculation(self) -> None:
        """Verify remaining budget, status indicators, and fallback price calculations."""
        # Project with budget 1000 EUR
        project = InteriorProject.objects.create(
            workspace=self.workspace,
            house=self.house,
            title="Budget Project",
            budget=Decimal("1000.00"),
            currency="EUR",
        )
        room = Room.objects.create(project=project, name="Guest Room")
        item1 = Item.objects.create(room=room, name="Bed Frame")
        item2 = Item.objects.create(room=room, name="Nightstand")

        # Initial state: no options chosen -> cost is 0.00, remaining budget is 1000.00, status "under"
        self.assertEqual(project.total_estimated_cost, Decimal("0.00"))
        self.assertEqual(project.remaining_budget, Decimal("1000.00"))
        self.assertEqual(project.remaining_budget_display, "1,000.00 EUR")
        self.assertEqual(project.budget_status, "under")

        # Item 1 has 2 candidate options (prices 400 and 600, avg 500), none chosen yet
        Option.objects.create(
            item=item1,
            name="Bed Option A",
            price=Decimal("400.00"),
            added_by=self.owner,
        )
        Option.objects.create(
            item=item1,
            name="Bed Option B",
            price=Decimal("600.00"),
            added_by=self.owner,
        )

        # Item 2 has chosen option price 300
        Option.objects.create(
            item=item2,
            name="Nightstand Chosen",
            price=Decimal("300.00"),
            is_chosen=True,
            added_by=self.owner,
        )

        # Chosen total is 300 (only item 2)
        self.assertEqual(project.total_estimated_cost, Decimal("300.00"))
        self.assertEqual(project.remaining_budget, Decimal("700.00"))
        self.assertEqual(project.budget_status, "under")

        # Fallback total is 300 (item 2 chosen) + 500 (item 1 avg) = 800
        self.assertEqual(item1.estimated_cost_with_fallback, Decimal("500.00"))
        self.assertEqual(item2.estimated_cost_with_fallback, Decimal("300.00"))
        self.assertEqual(room.total_estimated_cost_with_fallback, Decimal("800.00"))
        self.assertEqual(project.total_estimated_cost_with_fallback, Decimal("800.00"))
        self.assertEqual(project.total_estimated_cost_with_fallback_display, "800.00 EUR")

        # Now choose Bed Option B (600) + Nightstand (300) = 900
        opt_b = Option.objects.get(name="Bed Option B")
        opt_b.is_chosen = True
        opt_b.save()

        self.assertEqual(project.total_estimated_cost, Decimal("900.00"))
        self.assertEqual(project.remaining_budget, Decimal("100.00"))
        self.assertEqual(project.budget_status, "under")

        # If we reduce project budget to 800 EUR -> status becomes "over"
        project.budget = Decimal("800.00")
        project.save()
        self.assertEqual(project.remaining_budget, Decimal("-100.00"))
        self.assertEqual(project.budget_status, "over")

        # Project with no budget -> status "unset"
        project.budget = None
        project.save()
        self.assertIsNone(project.remaining_budget)
        self.assertEqual(project.remaining_budget_display, "—")
        self.assertEqual(project.budget_status, "unset")

    def test_option_rating_model_and_properties(self) -> None:
        """Verify OptionRating creation, uniqueness per user, and Option average rating properties."""
        opt = Option.objects.create(
            item=self.item,
            name="Velvet Armchair",
            price=Decimal("350.00"),
            added_by=self.owner,
        )
        self.assertIsNone(opt.avg_rating)
        self.assertEqual(opt.avg_rating_display, "—")
        self.assertEqual(opt.rating_count, 0)

        # Add first rating (8)
        r1 = OptionRating.objects.create(
            option=opt,
            user=self.owner,
            score=8,
            comment="Very comfy and stylish",
        )
        self.assertEqual(str(r1), f"8/10 by {self.owner} for {opt.name}")
        self.assertEqual(opt.avg_rating, 8.0)
        self.assertEqual(opt.avg_rating_display, "8/10")
        self.assertEqual(opt.rating_count, 1)

        # Add second rating (9) by editor
        OptionRating.objects.create(
            option=opt,
            user=self.editor,
            score=9,
            comment="Love the texture",
        )
        self.assertEqual(opt.avg_rating, 8.5)
        self.assertEqual(opt.avg_rating_display, "8.5/10")
        self.assertEqual(opt.rating_count, 2)

    def test_option_rating_form_validation(self) -> None:
        """Verify score range constraints in OptionRatingForm."""
        valid_form = OptionRatingForm(data={"score": 10, "comment": "Perfect!"})
        self.assertTrue(valid_form.is_valid())

        # Score out of bounds
        invalid_high = OptionRatingForm(data={"score": 11, "comment": "Too high"})
        self.assertFalse(invalid_high.is_valid())
        self.assertIn("score", invalid_high.errors)

        invalid_low = OptionRatingForm(data={"score": 0, "comment": "Too low"})
        self.assertFalse(invalid_low.is_valid())
        self.assertIn("score", invalid_low.errors)

    def test_option_rating_create_and_update_views(self) -> None:
        """Verify rating create view, update view, auto-redirect on duplicate, and permission scoping."""
        opt = Option.objects.create(
            item=self.item,
            name="Oak Sideboard",
            price=Decimal("750.00"),
            added_by=self.owner,
        )

        self.client.login(username="editor", password="password")
        create_url = reverse(
            "interiors:option_rating_create",
            kwargs={"workspace_slug": self.workspace.slug, "option_pk": opt.pk},
        )

        # GET create view
        res = self.client.get(create_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Rate Purchase Option")

        # POST create rating
        post_res = self.client.post(
            create_url,
            {"score": 9, "comment": "Excellent craftsmanship."},
        )
        self.assertEqual(post_res.status_code, 302)
        rating = OptionRating.objects.get(option=opt, user=self.editor)
        self.assertEqual(rating.score, 9)
        self.assertEqual(rating.comment, "Excellent craftsmanship.")

        # Trying to access create view again for same user should redirect to update view
        redirect_res = self.client.get(create_url)
        self.assertEqual(redirect_res.status_code, 302)
        update_url = reverse(
            "interiors:option_rating_update",
            kwargs={"workspace_slug": self.workspace.slug, "pk": rating.pk},
        )
        self.assertRedirects(redirect_res, update_url)

        # GET update view
        update_get_res = self.client.get(update_url)
        self.assertEqual(update_get_res.status_code, 200)
        self.assertContains(update_get_res, "Edit Option Rating")

        # POST update rating
        update_post_res = self.client.post(
            update_url,
            {"score": 10, "comment": "Changed mind, it is flawless!"},
        )
        self.assertEqual(update_post_res.status_code, 302)
        rating.refresh_from_db()
        self.assertEqual(rating.score, 10)
        self.assertEqual(rating.comment, "Changed mind, it is flawless!")

    def test_ui_rendering_project_and_item_detail(self) -> None:
        """Verify rendering of remaining budget, rating stars, and gallery modals in templates."""
        opt = Option.objects.create(
            item=self.item,
            name="Marble Console Table",
            price=Decimal("490.00"),
            is_chosen=True,
            added_by=self.owner,
        )
        OptionRating.objects.create(
            option=opt,
            user=self.owner,
            score=9,
            comment="Great stone veining",
        )

        # Create 2 photos for carousel and modal gallery test
        im = Image.new("RGB", (100, 100), color="blue")
        buf = BytesIO()
        im.save(buf, format="JPEG")
        img_file1 = SimpleUploadedFile("opt1.jpg", buf.getvalue(), content_type="image/jpeg")
        img_file2 = SimpleUploadedFile("opt2.jpg", buf.getvalue(), content_type="image/jpeg")

        OptionImage.objects.create(option=opt, image=img_file1, is_cover=True)
        OptionImage.objects.create(option=opt, image=img_file2, is_cover=False)

        self.client.login(username="owner", password="password")

        # Check item_detail rendering
        item_url = reverse(
            "interiors:item_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.item.pk},
        )
        item_res = self.client.get(item_url)
        self.assertEqual(item_res.status_code, 200)
        self.assertContains(item_res, "9/10")
        self.assertContains(item_res, "Avaliar Opção")
        self.assertContains(item_res, "Ver todas as fotos")
        self.assertContains(item_res, f"galleryModal{opt.pk}")
        self.assertContains(item_res, f"ratingModal{opt.pk}")

        # Check project_detail budget rendering
        project_url = reverse(
            "interiors:project_detail",
            kwargs={"workspace_slug": self.workspace.slug, "pk": self.project.pk},
        )
        project_res = self.client.get(project_url)
        self.assertEqual(project_res.status_code, 200)
        self.assertContains(project_res, "Remaining Budget")
        self.assertContains(project_res, "Budget Health")
