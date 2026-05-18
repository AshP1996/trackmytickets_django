"""
Production Settings for Ticket System
Domain: trackmyticket.luminoai.online (path-based tenants: /acme/login)

Bare VPS (non-Docker): Set DB_HOST=127.0.0.1, REDIS_URL=redis://127.0.0.1:6379/1
Or set USE_REDIS=False to use database sessions + LocMem cache (no Redis required).
"""
import os
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Public site (path-based org URLs: https://trackmyticket.luminoai.online/<org>/login)
PRIMARY_DOMAIN = os.environ.get('PRIMARY_DOMAIN', 'trackmyticket.luminoai.online').strip()
SITE_URL = os.environ.get('SITE_URL', f'https://{PRIMARY_DOMAIN}').rstrip('/')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@luminoai.online')

_SERVER_IP = os.environ.get('SERVER_IP', '').strip()
ALLOWED_HOSTS = [
    PRIMARY_DOMAIN,
    f'www.{PRIMARY_DOMAIN}',
    'luminoai.online',
    'www.luminoai.online',
]
if _SERVER_IP:
    ALLOWED_HOSTS.append(_SERVER_IP)
ALLOWED_HOSTS.extend(['localhost', 'demo.localhost', '127.0.0.1', 'web', 'nginx'])

_env_hosts = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]
if _env_hosts:
    ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS + _env_hosts))

_env_csrf = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
CSRF_TRUSTED_ORIGINS = _env_csrf or [SITE_URL]

_env_cors = [o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
CORS_ALLOWED_ORIGINS = _env_cors or [SITE_URL]

# Database — default to 127.0.0.1 for bare VPS (Docker uses DB_HOST=db)
USE_SQLITE = os.environ.get('USE_SQLITE', '').lower() in ('1', 'true', 'yes')
if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'ticket_system'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),  # 127.0.0.1 for bare VPS; 'db' for Docker
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,  # Connection pooling
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set in production")

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Proxy Settings (for Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

CORS_ALLOW_CREDENTIALS = True

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# WhiteNoise for static file serving (base.py already adds WhiteNoiseMiddleware)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@luminoai.online')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_error.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache & Session — Redis optional for bare VPS
# Set USE_REDIS=true + REDIS_URL when Redis is installed. Default: DB sessions + LocMem (no Redis).
_USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() in ('1', 'true', 'yes')
_REDIS_URL = (os.environ.get('REDIS_URL') or '').strip() or 'redis://127.0.0.1:6379/1'

if _USE_REDIS and _REDIS_URL:
    # Redis: sessions in cache, fast. Requires Redis running at REDIS_URL.
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': _REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
            },
            'KEY_PREFIX': 'ticket_system',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Fallback: LocMem cache + DB sessions (works without Redis)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'KEY_PREFIX': 'ticket_system',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Admin Configuration
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@luminoai.online')),
]
MANAGERS = ADMINS

# Performance Settings
CONN_MAX_AGE = 600
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
