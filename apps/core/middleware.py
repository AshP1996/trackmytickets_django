import re
from django.http import JsonResponse
from apps.accounts.models import Organization

from django.conf import settings

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for admin, static, media, and SEO files
        if request.path.startswith('/admin/') or \
           request.path.startswith(settings.STATIC_URL) or \
           request.path.startswith(settings.MEDIA_URL) or \
           request.path in ['/robots.txt', '/sitemap.xml']:
            return None

        # Check if company_name is in kwargs (from URL pattern)
        company_name = view_kwargs.get('company_name')
        
        # If not in kwargs, try to extract from path
        if not company_name:
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 1:
                first_part = path_parts[0]
                # Skip known routes that are not company names
                known_routes = {'admin', 'api', 'static', 'media', 'platform', 'health'}
                if first_part not in known_routes and first_part:
                    # This could be a company name for web routes
                    company_name = first_part
                elif len(path_parts) >= 2 and path_parts[0] == 'api':
                    # api/company/.. (for API routes)
                    if path_parts[1] != 'platform':
                        company_name = path_parts[1]

        request.organization = None
        request.organization_id = None

        if company_name:
            try:
                # Normalize
                subdomain = company_name.lower().strip()
                organization = Organization.objects.filter(subdomain=subdomain, is_active=True).first()
                
                if organization:
                    request.organization = organization
                    request.organization_id = organization.id
                else:
                    return JsonResponse({'error': f'Organization not found for company: {company_name}'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        # Note: If no company_name, we don't set request.organization.
        # Views requiring it should check request.organization and return 400/404.
        
        return None
