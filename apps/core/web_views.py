from django.views.generic import TemplateView
from django.conf import settings
import os

class BaseWebContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inject all URL kwargs into context (e.g., company_name, ticket_id)
        # This makes {{ ticket_id }} available in templates matching Flask behavior
        context.update(self.kwargs)
        
        # Inject standard config
        # Get port from request if available, otherwise default
        request_port = self.request.get_port() if hasattr(self.request, 'get_port') else None
        context['BASE_URL'] = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
        context['BASE_DOMAIN'] = context['BASE_URL']
        context['PORT'] = request_port if request_port and request_port != 80 else (9000 if settings.DEBUG else 80)
        context['PROTOCOL'] = 'https' if self.request.is_secure() else 'http'
        
        # If company_name is missing but we are in a tenant context (checked helper)
        if 'company_name' not in context:
            # Try to get from request if middleware set it (though middleware is usually for API)
            if hasattr(self.request, 'organization') and self.request.organization:
                context['company_name'] = self.request.organization.subdomain
                
        return context

class RenderTemplateView(BaseWebContextMixin, TemplateView):
    pass
