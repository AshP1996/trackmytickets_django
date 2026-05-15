"""
SEO-related views for robots.txt, sitemap.xml, and structured data
"""
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET
from django.urls import reverse
from datetime import datetime


@require_GET
def robots_txt(request):
    """Serve robots.txt file"""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /platform/admin/",
        "Disallow: /*/admin/",
        "Disallow: /static/admin/",
        "",
        "# Sitemap",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
        "",
        "# Crawl delay (be polite to search engines)",
        "Crawl-delay: 1",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_GET
def sitemap_xml(request):
    """Generate dynamic sitemap.xml"""
    base_url = f"{request.scheme}://{request.get_host()}"
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Only include real, crawlable pages (not hash fragments)
    urls = [
        {
            'loc': base_url + '/',
            'lastmod': today,
            'changefreq': 'weekly',
            'priority': '1.0'
        },
        {
            'loc': base_url + '/features',
            'lastmod': today,
            'changefreq': 'monthly',
            'priority': '0.8'
        },
        {
            'loc': base_url + '/pricing',
            'lastmod': today,
            'changefreq': 'monthly',
            'priority': '0.8'
        },
        {
            'loc': base_url + '/privacy-policy',
            'lastmod': today,
            'changefreq': 'monthly',
            'priority': '0.5'
        },
        {
            'loc': base_url + '/terms-of-service',
            'lastmod': today,
            'changefreq': 'monthly',
            'priority': '0.5'
        },
        {
            'loc': base_url + '/platform/login',
            'lastmod': today,
            'changefreq': 'monthly',
            'priority': '0.6'
        },
    ]
    
    return TemplateResponse(
        request,
        'sitemap.xml',
        {'urls': urls},
        content_type='application/xml'
    )

