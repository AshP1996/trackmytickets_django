"""Template context for public site URLs and contact info."""
from django.conf import settings


def public_site(request):
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    return {
        'site_url': site_url,
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@luminoai.online'),
        'primary_domain': getattr(settings, 'PRIMARY_DOMAIN', 'trackmyticket.luminoai.online'),
        'google_site_verification': getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
    }
