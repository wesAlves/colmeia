"""
Production settings for comeia project.
Optimized for deployment with PostgreSQL, WhiteNoise static delivery, containerization, and environment variable configuration.
"""
from __future__ import annotations

import os
from pathlib import Path

# Import all base settings
from comeia.settings import *

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# Security & Debug
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes", "t")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY", SECRET_KEY)

# Allowed Hosts
allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS") or os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,web")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]

# CSRF Trusted Origins
csrf_origins_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_env.split(",") if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        f"http://{host}" for host in ALLOWED_HOSTS if host not in ("*", "0.0.0.0")
    ] + [
        f"https://{host}" for host in ALLOWED_HOSTS if host not in ("*", "0.0.0.0")
    ]

# PostgreSQL Database Configuration
db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME", "comeia")
db_user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER", "comeia_user")
db_password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD", "")
db_host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST", "db")
db_port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT", "5432")

database_url = os.getenv("DATABASE_URL")
if database_url:
    try:
        import dj_database_url
        DATABASES = {
            "default": dj_database_url.config(
                default=database_url,
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
    except ImportError:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": db_host,
                "PORT": db_port,
                "CONN_MAX_AGE": 600,
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "CONN_MAX_AGE": 600,
        }
    }

# Static files management with WhiteNoise
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files management
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise middleware insertion
if "whitenoise.runserver_nostatic" not in INSTALLED_APPS:
    INSTALLED_APPS.insert(0, "whitenoise.runserver_nostatic")

if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    try:
        security_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
        MIDDLEWARE.insert(security_idx + 1, "whitenoise.middleware.WhiteNoiseMiddleware")
    except ValueError:
        MIDDLEWARE.insert(0, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Production Security Headers & Cookies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "yes")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")

# Email Backend configuration
# EMAIL_BACKEND = os.getenv(
#     "DJANGO_EMAIL_BACKEND",
#     "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend"
# )
# EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
# EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
# EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
# DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")
