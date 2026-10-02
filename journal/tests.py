from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Membership, Role, Workspace
from journal.models import Note, Visit
from properties.models import House

User = get_user_model()


class JournalViewsTest(TestCase):
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
            title="Sunny Apartment",
            price=250000,
        )
        self.client.login(username="testuser", password="password")

    def test_visit_create_view_get_and_post(self):
        url = reverse(
            "journal:visit_create",
            kwargs={"workspace_slug": self.workspace.slug, "house_pk": self.house.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log House Visit")

        post_data = {
            "visited_at": "2026-10-02T14:30",
            "attendees": "Alice, Bob",
            "overall_impression": "Loved the natural light",
            "experience": "The neighborhood was quiet.",
            "considerations": "Check heating system",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(Visit.objects.filter(house=self.house).count(), 1)
        visit = Visit.objects.get(house=self.house)
        self.assertEqual(visit.created_by, self.user)
        self.assertEqual(visit.attendees, "Alice, Bob")

    def test_visit_update_and_delete(self):
        visit = Visit.objects.create(
            house=self.house,
            visited_at=timezone.now(),
            attendees="Alice",
            overall_impression="Nice place",
            created_by=self.user,
        )
        edit_url = reverse(
            "journal:visit_update",
            kwargs={
                "workspace_slug": self.workspace.slug,
                "house_pk": self.house.pk,
                "pk": visit.pk,
            },
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        post_response = self.client.post(
            edit_url,
            {
                "visited_at": "2026-10-02T15:00",
                "attendees": "Alice & Charlie",
                "overall_impression": "Updated impression",
                "experience": "",
                "considerations": "",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        visit.refresh_from_db()
        self.assertEqual(visit.attendees, "Alice & Charlie")

        delete_url = reverse(
            "journal:visit_delete",
            kwargs={
                "workspace_slug": self.workspace.slug,
                "house_pk": self.house.pk,
                "pk": visit.pk,
            },
        )
        del_get_response = self.client.get(delete_url)
        self.assertEqual(del_get_response.status_code, 200)

        del_post_response = self.client.post(delete_url)
        self.assertEqual(del_post_response.status_code, 302)
        self.assertEqual(Visit.objects.filter(house=self.house).count(), 0)

    def test_note_create_update_delete(self):
        create_url = reverse(
            "journal:note_create",
            kwargs={"workspace_slug": self.workspace.slug, "house_pk": self.house.pk},
        )
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Note")

        post_response = self.client.post(
            create_url,
            {
                "title": "Roof inspection",
                "body": "Need to check if the roof has recent leaks.",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(Note.objects.filter(house=self.house).count(), 1)
        note = Note.objects.get(house=self.house)
        self.assertEqual(note.title, "Roof inspection")
        self.assertEqual(note.created_by, self.user)

        edit_url = reverse(
            "journal:note_update",
            kwargs={
                "workspace_slug": self.workspace.slug,
                "house_pk": self.house.pk,
                "pk": note.pk,
            },
        )
        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.status_code, 200)

        edit_post_response = self.client.post(
            edit_url,
            {
                "title": "Roof inspection updated",
                "body": "Roof was inspected and is fine.",
            },
        )
        self.assertEqual(edit_post_response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.title, "Roof inspection updated")

        delete_url = reverse(
            "journal:note_delete",
            kwargs={
                "workspace_slug": self.workspace.slug,
                "house_pk": self.house.pk,
                "pk": note.pk,
            },
        )
        del_get_response = self.client.get(delete_url)
        self.assertEqual(del_get_response.status_code, 200)

        del_post_response = self.client.post(delete_url)
        self.assertEqual(del_post_response.status_code, 302)
        self.assertEqual(Note.objects.filter(house=self.house).count(), 0)
