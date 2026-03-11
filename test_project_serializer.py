import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
# Enable logging for django.db.backends
if not settings.configured:
    settings.LOGGING = {
        'version': 1,
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],
                'class': 'logging.StreamHandler',
            }
        },
        'loggers': {
            'django.db.backends': {
                'level': 'DEBUG',
                'handlers': ['console'],
            }
        }
    }

django.setup()

from apps.tickets.serializers import ProjectSerializer
from apps.accounts.models import Organization
from django.db import connection

org = Organization.objects.get(subdomain='audit-test')
print("Org:", org.id)

data = {
    "name": "Audit Platform",
    "key": "APT-SQLLOG",
    "description": "Just another project"
}

serializer = ProjectSerializer(data=data)
if serializer.is_valid():
    try:
        settings.DEBUG = True
        serializer.save(organization_id=org.id)
        print("Success:", serializer.instance.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Queries executed:")
        for q in connection.queries:
            print(q['sql'])
else:
    print("Invalid:", serializer.errors)
