"""
Configuration Django de NotePro.

Toutes les valeurs sensibles (clé secrète, base de données, clé de chiffrement)
sont lues depuis l'environnement (fichier .env en développement, variables
d'environnement de l'hébergeur en production). Rien de sensible n'est versionné.
"""
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# --------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-key-ne-pas-utiliser-en-production"
    else:
        raise RuntimeError("La variable d'environnement SECRET_KEY est obligatoire en production.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Hébergement Render : l'adresse publique du service est fournie automatiquement
RENDER_HOTE = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOTE:
    ALLOWED_HOSTS.append(RENDER_HOTE)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOTE}")

# Nom de l'établissement (application mono-établissement)
ETABLISSEMENT_NOM = os.environ.get("ETABLISSEMENT_NOM", "Établissement scolaire")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "axes",  # protection contre le brute-force sur la connexion
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # NotePro
    "core",
    "accounts",
    "scolarite",
    "edt",
    "notes",
    "absences",
    "cahier",
    "bulletins",
    "messagerie",
    "dashboard",
    "finances",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Toutes les pages exigent une connexion sauf celles marquées @login_not_required
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "core.middleware.ForcePasswordChangeMiddleware",
    # Doit être en dernier (documentation django-axes)
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.notepro",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Base de données : PostgreSQL via DATABASE_URL
# (SQLite uniquement en secours pour un essai local rapide)
# --------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Authentification
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # doit être en premier
    "django.contrib.auth.backends.ModelBackend",
    "accounts.backends.TelephoneBackend",  # connexion par numéro de téléphone
]

# Argon2 : algorithme de hachage recommandé (OWASP)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# django-axes : 5 échecs => blocage 15 minutes (par couple identifiant + IP)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # heures
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "accounts/verrouille.html"

# Sessions : expiration à la fermeture du navigateur et après 8 h
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True

# --------------------------------------------------------------------------
# Sécurité HTTP (activée automatiquement hors DEBUG)
# --------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --------------------------------------------------------------------------
# Chiffrement des données sensibles au repos (champs EncryptedTextField)
# FIELD_ENCRYPTION_KEYS : une ou plusieurs clés Fernet séparées par des
# virgules. La première chiffre ; toutes déchiffrent (rotation de clés).
# --------------------------------------------------------------------------
FIELD_ENCRYPTION_KEYS = env_list("FIELD_ENCRYPTION_KEYS")
if not FIELD_ENCRYPTION_KEYS:
    if DEBUG:
        # Clé de développement fixe : NE JAMAIS l'utiliser en production
        FIELD_ENCRYPTION_KEYS = ["l9Zf8gd_hwdzfDDS70eg1QqVr9YrcaSVHad9WBEDn3g="]
    else:
        raise RuntimeError("FIELD_ENCRYPTION_KEYS est obligatoire en production.")

# --------------------------------------------------------------------------
# Fichiers
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# Fichiers privés (justificatifs d'absence) : JAMAIS servis directement par
# le serveur web. Ils sont lus par une vue qui vérifie les droits d'accès.
PRIVATE_MEDIA_ROOT = Path(os.environ.get("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))
JUSTIFICATIF_MAX_OCTETS = 5 * 1024 * 1024  # 5 Mo
FILE_UPLOAD_MAX_MEMORY_SIZE = JUSTIFICATIF_MAX_OCTETS
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --------------------------------------------------------------------------
# RGPD : durées de conservation (en jours) utilisées par `purge_rgpd`
# --------------------------------------------------------------------------
RGPD_CONSERVATION = {
    "notifications": int(os.environ.get("RGPD_NOTIFICATIONS_JOURS", 180)),
    "messages": int(os.environ.get("RGPD_MESSAGES_JOURS", 365)),
    "justificatifs": int(os.environ.get("RGPD_JUSTIFICATIFS_JOURS", 365)),
    "journal_acces": int(os.environ.get("RGPD_JOURNAL_JOURS", 365)),
}

# --------------------------------------------------------------------------
# API REST pour l'application mobile (Django REST Framework + JWT)
# --------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle", "rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "600/min", "anon": "30/min", "connexion": "10/min"},
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
# Application web Expo (développement) ; l'app native n'a pas besoin de CORS
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081")
CORS_URLS_REGEX = r"^/api/.*$"

# Liens de téléchargement signés (bulletins, reçus, documents) : durée de validité
LIEN_FICHIER_SECONDES = 300

# Paiements en ligne : "sandbox" (simulation) tant qu'aucun prestataire n'est intégré
PAIEMENT_FOURNISSEUR = os.environ.get("PAIEMENT_FOURNISSEUR", "sandbox")

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.environ.get("TIME_ZONE", "Africa/Abidjan")
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# E-mail (optionnel : notifications par e-mail si configuré)
# --------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "notepro@localhost")

# --------------------------------------------------------------------------
# Journalisation
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
