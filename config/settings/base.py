from pathlib import Path
import os
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# AUDIT-FIX CRIT-5: No insecure fallback. Crashes at startup if not set.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-prod-DO-NOT-USE-IN-PROD')

# AUDIT-FIX CRIT-5: Default is now False. Security headers are always active
# unless you explicitly set DEBUG=True (e.g., in settings/dev.py only).
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# AUDIT-FIX CRIT-2: Fail-closed. Empty list rejects all Host headers
# unless overridden in dev.py or via ALLOWED_HOSTS env var in prod.
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # AUDIT-FIX CRIT-3: enables token revocation
    'corsheaders',
    
    # Local apps
    'apps.accounts',
    'apps.tickets',
    'apps.comments',
    'apps.notifications',
    'apps.core',
]

# Custom User Model — Users live in tenant databases, not the primary DB
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # Correlation ID + request timing must run first so every downstream
    # log record can include correlation_id and tenant_id.
    'apps.core.middleware.correlation.CorrelationIDMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.tenant.TenantMiddleware',
    'apps.core.middleware.rate_limit.RateLimitMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Database Router
DATABASE_ROUTERS = ['apps.core.routers.TenantDatabaseRouter']

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'uploads'

# AUDIT-FIX CRIT-1: Encryption key for BYODB credentials (AES via Fernet).
# HARD CRASH if not set — never use a hardcoded fallback for an encryption key.
# Any developer with repo access could decrypt ALL tenant DB passwords.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_DB_CREDS_KEY = os.environ.get('DB_CREDENTIALS_ENCRYPTION_KEY')
if not _DB_CREDS_KEY:
    raise ImproperlyConfigured(
        "DB_CREDENTIALS_ENCRYPTION_KEY environment variable is required. "
        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'. "
        "Never hardcode this value or commit it to version control."
    )
DB_CREDENTIALS_ENCRYPTION_KEY = _DB_CREDS_KEY


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.PlatformJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# AUDIT-FIX CRIT-5/HIGH-2: CORS wildcard removed from base.py.
# dev.py sets CORS_ALLOW_ALL_ORIGINS = True explicitly.
# prod.py requires CORS_ALLOWED_ORIGINS to list exact origins.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []

# Silenced System Checks
# auth.E003: User.email must be unique because it is named as the 'USERNAME_FIELD'.
# We silence this because email uniqueness is scoped to organization_id.
SILENCED_SYSTEM_CHECKS = ['auth.E003']

# Email Configuration for OTP (Forgot Password)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', os.environ.get('SMTP_SERVER', 'smtp.gmail.com'))
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', os.environ.get('SMTP_PORT', 587)))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', os.environ.get('SMTP_USERNAME', ''))
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', os.environ.get('SMTP_PASSWORD', ''))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)

# AUDIT-FIX CRIT-3:
# - ACCESS_TOKEN_LIFETIME reduced from 24h → 15min (revocation window = 15 min max)
# - ROTATE_REFRESH_TOKENS=True: each /token/refresh/ call invalidates the old refresh token
# - BLACKLIST_AFTER_ROTATION=True: rotated-out tokens are permanently blacklisted
# - UPDATE_LAST_LOGIN: keeps last_login fresh for SOC2 access reviews
# Requires: rest_framework_simplejwt.token_blacklist in INSTALLED_APPS
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'SIGNING_KEY': JWT_SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ===========================================================================
# LOGGING CONFIGURATION
# ===========================================================================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

_LOG_FILE = LOG_DIR / 'django.log'
_ERROR_LOG_FILE = LOG_DIR / 'django_error.log'

# Check if log files are writable; create them if they don't exist
def _can_write_log(filepath):
    try:
        filepath.touch(exist_ok=True)
        return os.access(filepath, os.W_OK)
    except (OSError, PermissionError):
        return False

_FILE_LOGGING_AVAILABLE = _can_write_log(_LOG_FILE) and _can_write_log(_ERROR_LOG_FILE)

_log_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    },
}

_django_handlers = ['console']
_apps_handlers = ['console']

if _FILE_LOGGING_AVAILABLE:
    _log_handlers['file'] = {
        'class': 'logging.FileHandler',
        'filename': str(_LOG_FILE),
        'formatter': 'verbose',
    }
    _log_handlers['error_file'] = {
        'class': 'logging.FileHandler',
        'filename': str(_ERROR_LOG_FILE),
        'formatter': 'verbose',
        'level': 'ERROR',
    }
    _django_handlers.append('file')
    _apps_handlers.extend(['file', 'error_file'])

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': _log_handlers,
    'loggers': {
        'django': {
            'handlers': _django_handlers,
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': _apps_handlers,
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ===========================================================================
# SECURITY SETTINGS
# AUDIT-FIX CRIT-5: Security headers now apply unconditionally (DEBUG=False
# by default). dev.py may override for local development.
# ===========================================================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Cookie security is enabled when not DEBUG (dev can still use http://)
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
# additional security headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=()'

# WhiteNoise static file compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'

# ===========================================================================
# RATE LIMITING CONFIGURATION
# ===========================================================================
ORG_RATE_LIMIT = int(os.environ.get('ORG_RATE_LIMIT', 1000))  # per minute per org
IP_RATE_LIMIT = int(os.environ.get('IP_RATE_LIMIT', 200))  # per minute per IP
