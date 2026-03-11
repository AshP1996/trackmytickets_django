# settings/dev.py — LOCAL DEVELOPMENT ONLY
# NEVER import or use these settings in production.
from .base import *  # noqa
import os

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]', 'testserver']

# Relax CORS for local frontend dev (e.g., Vite on :3000)
CORS_ALLOW_ALL_ORIGINS = True

# Bypass the ImproperlyConfigured crash for DB encryption key in local dev
# Generate your own: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if not os.environ.get('DB_CREDENTIALS_ENCRYPTION_KEY'):
    DB_CREDENTIALS_ENCRYPTION_KEY = 'WNMe9TXZfx5FPR9GintlzTudZJV0I94gp-mYS8oKYRA='

# Database — SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Shorten JWT lifetime to 1 hour in dev so tokens expire in a reasonable time
# while still being longer than 15min for developer ergonomics.
from datetime import timedelta
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
}
