"""
SEO-related views for robots.txt, sitemap.xml, and structured data
"""
from django.conf import settings
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET
from datetime import datetime


def _canonical_site_url(request):
    """Prefer SITE_URL in production so sitemap/robots match canonical domain."""
    configured = getattr(settings, 'SITE_URL', '').rstrip('/')
    if configured and configured != 'http://localhost:8000':
        return configured
    return f'{request.scheme}://{request.get_host()}'.rstrip('/')


@require_GET
def robots_txt(request):
    """Serve robots.txt file"""
    base_url = _canonical_site_url(request)
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /api/',
        'Disallow: /platform/admin/',
        'Disallow: /*/admin/',
        'Disallow: /static/admin/',
        '',
        '# Sitemap',
        f'Sitemap: {base_url}/sitemap.xml',
        '',
        '# Crawl delay (be polite to search engines)',
        'Crawl-delay: 1',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


@require_GET
def sitemap_xml(request):
    """Generate dynamic sitemap.xml"""
    base_url = _canonical_site_url(request)
    today = datetime.now().strftime('%Y-%m-%d')

    urls = [
        {'loc': f'{base_url}/', 'lastmod': today, 'changefreq': 'weekly', 'priority': '1.0'},
        {'loc': f'{base_url}/features', 'lastmod': today, 'changefreq': 'monthly', 'priority': '0.8'},
        {'loc': f'{base_url}/pricing', 'lastmod': today, 'changefreq': 'monthly', 'priority': '0.8'},
        {'loc': f'{base_url}/privacy-policy', 'lastmod': today, 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f'{base_url}/terms-of-service', 'lastmod': today, 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f'{base_url}/platform/login', 'lastmod': today, 'changefreq': 'monthly', 'priority': '0.6'},
    ]

    return TemplateResponse(
        request,
        'sitemap.xml',
        {'urls': urls},
        content_type='application/xml',
    )
