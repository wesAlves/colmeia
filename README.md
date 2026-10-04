<!-- README.md -->
# House Hunt Journal

A small Django application to journal a house search: track houses, their
features, visits, and personal notes.  All data lives inside a **workspace**
(the multi-tenant boundary), and workspaces can be shared between users.

## Quickstart (Development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Production with Docker Compose (PostgreSQL)

Run the full stack with orchestrated PostgreSQL and Gunicorn web service:

```bash
# 1. Review/customize environment configuration (.env)
cp .env.example .env

# 2. Build and launch all services in background
docker compose up -d --build

# 3. Create a superuser inside the container (optional)
docker compose exec web python manage.py createsuperuser
```