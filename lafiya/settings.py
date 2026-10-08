"""Django settings for the Lafiya AI MVP."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env(path):
    """Minimal .env loader so the MVP has no extra dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-lafiya-ai-mvp"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
CSRF_TRUSTED_ORIGINS = []

# Render sets RENDER_EXTERNAL_HOSTNAME (e.g. lafiya.onrender.com) on web services.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "mamacare",
    "immunitrack",
    "climateguard",
    "alerts",
    "navigator",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lafiya.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.lafiya",
            ],
        },
    },
]

WSGI_APPLICATION = "lafiya.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
# Production (Render): PostgreSQL from DATABASE_URL. Render's disk is wiped on every deploy,
# so SQLite cannot be used there.
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(
        os.environ["DATABASE_URL"], conn_max_age=600, conn_health_checks=True
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "landing"

# --- N-ATLaS -----------------------------------------------------------------
# The N-ATLAS-Kit gateway (chat + Hausa/Igbo/Yoruba/English speech-to-text), or any
# OpenAI-compatible server running N-ATLaS (e.g. vLLM). When unset, Lafiya falls back
# to its grounded template engine and browser speech so the demo works offline.
NATLAS = {
    "API_URL": os.environ.get("NATLAS_BASE_URL") or os.environ.get("NATLAS_API_URL", ""),
    "API_KEY": os.environ.get("NATLAS_API_KEY", ""),
    "MODEL": os.environ.get("NATLAS_MODEL", "NCAIR1/N-ATLaS"),
    "TIMEOUT": int(os.environ.get("NATLAS_TIMEOUT", "60")),
}
# Tests never talk to the real gateway (it costs GPU credit) - they use a local fake.
if "test" in sys.argv[1:2]:
    NATLAS["API_URL"] = NATLAS["API_KEY"] = ""

MAX_VOICE_UPLOAD_BYTES = 10 * 1024 * 1024
# Read answers aloud with the gateway's voices (POST /v1/audio/speech): web player + WhatsApp voice replies.
SPOKEN_REPLIES = os.environ.get("LAFIYA_SPOKEN_REPLIES", "1") == "1"
# Let N-ATLaS write the daily Intelligence Loop alerts. Off by default to save GPU credit:
# alerts then use the localized templates (conversations still use N-ATLaS).
NATLAS_FOR_ALERTS = os.environ.get("LAFIYA_NATLAS_FOR_ALERTS", "0") == "1"

# NAIC PS02 "challenge mode": voice input only through the official N-ATLaS ASR
# (no browser speech-recognition fallback).
CHALLENGE_MODE = os.environ.get("LAFIYA_CHALLENGE_MODE", "0") == "1"

# --- WhatsApp voice-note channel (Twilio) ------------------------------------
# Inbound webhook: <PUBLIC_BASE_URL>/whatsapp/twilio/  (set it in the Twilio console)
TWILIO = {
    "ACCOUNT_SID": os.environ.get("TWILIO_ACCOUNT_SID", ""),
    "AUTH_TOKEN": os.environ.get("TWILIO_AUTH_TOKEN", ""),
    "WHATSAPP_FROM": os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),  # Twilio sandbox number
    "VALIDATE_SIGNATURE": os.environ.get("TWILIO_VALIDATE_SIGNATURE", "1") == "1",
}
if "test" in sys.argv[1:2]:
    TWILIO["ACCOUNT_SID"] = TWILIO["AUTH_TOKEN"] = ""

# Public https URL of this server (e.g. an ngrok/cloudflared tunnel); used to verify Twilio signatures.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "") or (f"https://{RENDER_HOST}" if RENDER_HOST else "")
# Process WhatsApp messages in a background thread so Twilio's 15 s webhook timeout is never hit.
WHATSAPP_ASYNC = os.environ.get("WHATSAPP_ASYNC", "1") == "1"
if PUBLIC_BASE_URL:
    from urllib.parse import urlparse

    ALLOWED_HOSTS.append(urlparse(PUBLIC_BASE_URL).hostname)
    CSRF_TRUSTED_ORIGINS.append(PUBLIC_BASE_URL.rstrip("/"))

# --- ClimateGuard -----------------------------------------------------------
# Live weather comes from Open-Meteo (free, no key). If the network is not
# available, deterministic seasonal simulation is used and labelled as such.
CLIMATE_LIVE_WEATHER = os.environ.get("CLIMATE_LIVE_WEATHER", "1") == "1"

# --- Data protection (NDPA 2023) --------------------------------------------
# Aggregated counts below this threshold are suppressed in exports and the API.
ANON_MIN_CELL = int(os.environ.get("ANON_MIN_CELL", "5"))
