from django.contrib import admin
from django.urls import path, include
from apps.core.health import health_check
from apps.core.seo_views import robots_txt, sitemap_xml

urlpatterns = [
    # Health check endpoint
    path('health/', health_check, name='health_check'),
    
    # SEO Routes (must be before multi-tenant routes)
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    
    path('admin/', admin.site.urls),
    # API Routes - Multi-tenant (debug before generic to avoid capture)
    path('api/<str:company_name>/auth/', include('apps.accounts.urls')),
    path('api/<str:company_name>/debug/', include('apps.core.debug_urls')),
    path('api/<str:company_name>/', include('apps.tickets.urls')),
    path('api/<str:company_name>/', include('apps.notifications.urls')),
    path('api/<str:company_name>/', include('apps.core.urls')),  # Data sources, feedback, etc.
    
    # Platform API
    path('api/platform/', include('apps.accounts.platform_urls')),

    # Web Routes (HTML)
    path('', include('apps.core.web_urls')), # Landing + Platform
    path('<str:company_name>/', include('apps.accounts.web_urls')),
    path('<str:company_name>/', include('apps.tickets.web_urls')),
    path('<str:company_name>/', include('apps.notifications.web_urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
