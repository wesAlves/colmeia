<!-- README.md -->
# House Hunt Journal

A small Django application to journal a house search: track houses, their
features, visits, and personal notes.  All data lives inside a **workspace**
(the multi-tenant boundary), and workspaces can be shared between users.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install "Django>=5.0,<5.2"
python manage.py makemigrations accounts properties journal
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver