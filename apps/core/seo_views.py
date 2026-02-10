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
    
    # Define all public pages with their priorities and change frequencies
    urls = [
        {
            'loc': base_url + '/',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '1.0'
        },
        {
            'loc': base_url + '/#features',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.8'
        },
        {
            'loc': base_url + '/#about',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.7'
        },
        {
            'loc': base_url + '/#promotion',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '0.9'
        },
        {
            'loc': base_url + '/#enquiry',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
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
