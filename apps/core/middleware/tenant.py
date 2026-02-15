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

        # Reset DB alias at start of request
        from apps.core.routers import reset_current_db_alias, set_current_db_alias
        reset_current_db_alias()

        if company_name:
            try:
                # Normalize
                subdomain = company_name.lower().strip()
                organization = Organization.objects.filter(subdomain=subdomain, is_active=True).first()
                
                if organization:
                    request.organization = organization
                    request.organization_id = organization.id
                    
                    # Check for External Data Source
                    # We look for an active data source for this organization
                    from apps.core.models import ExternalDataSource
                    # Prioritize by type if needed, or just take the first active one that isn't untested/failed if possible?
                    # For now, simple: first active
                    data_source = ExternalDataSource.objects.filter(
                        organization=organization, 
                        is_active=True,
                        connection_status='connected'
                    ).first()
                    
                    if data_source:
                        # Configure connection dynamically
                        from apps.core.connectors import get_connector
                        db_alias = f"tenant_{organization.id}"
                        
                        # Check if connection already exists in settings, if not add it
                        if db_alias not in settings.DATABASES:
                            # Start with default config to ensure all required keys (TIME_ZONE, etc.) are present
                            default_config = settings.DATABASES['default'].copy()
                            
                            # Construct Django DATABASE config
                            db_config = {
                                **default_config,
                                'ENGINE': f'django.db.backends.{data_source.type}',
                                'NAME': data_source.database,
                                'USER': data_source.username,
                                'PASSWORD': data_source.get_password(),
                                'HOST': data_source.host,
                                'PORT': data_source.port,
                                'CONN_MAX_AGE': 600,
                            }
                            
                            # Adjust ENGINE for Postgres, etc.
                            if data_source.type == 'postgres':
                                db_config['ENGINE'] = 'django.db.backends.postgresql'
                            elif data_source.type == 'mysql':
                                db_config['ENGINE'] = 'django.db.backends.mysql'
                            elif data_source.type == 'sqlite':
                                db_config['ENGINE'] = 'django.db.backends.sqlite3'
                                db_config['OPTIONS'] = {} # clear specific options like connect_timeout
                                
                            settings.DATABASES[db_alias] = db_config
                            
                        # Set alias for Router
                        set_current_db_alias(db_alias)
                        
                else:
                    return JsonResponse({'error': f'Organization not found for company: {company_name}'}, status=404)
            except Exception as e:
                import traceback
                print(f"Middleware Error: {e}")
                traceback.print_exc()
                return JsonResponse({'error': str(e)}, status=500)
        
        # Note: If no company_name, we don't set request.organization.
        # Views requiring it should check request.organization and return 400/404.
        
        return None
