from django.views.generic import TemplateView
from django.conf import settings


class BaseWebContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Inject all URL kwargs into context (e.g., company_name, ticket_id, project_id)
        context.update(self.kwargs)

        # ── BASE_URL / BASE_DOMAIN ──────────────────────────────────────────────
        # Use Host header as the most reliable source (works for localhost:8000,
        # trackmyticket.luminoai.online, etc.).  Fall back to the first ALLOWED_HOSTS entry
        # only if the header is missing, and ultimately to 'localhost'.
        host_header = self.request.get_host()  # e.g. "localhost:8000" or "trackmyticket.luminoai.online"

        if ':' in host_header:
            host_part, port_str = host_header.rsplit(':', 1)
            try:
                port_num = int(port_str)
            except ValueError:
                host_part = host_header
                port_num = 443 if self.request.is_secure() else 80
        else:
            host_part = host_header
            port_num = 443 if self.request.is_secure() else 80

        context['BASE_URL'] = host_header          # full "host:port" string
        context['BASE_DOMAIN'] = host_part         # domain only, no port
        context['PORT'] = port_num
        context['PROTOCOL'] = 'https' if self.request.is_secure() else 'http'

        # ── company_name fallback ───────────────────────────────────────────────
        # If the URL pattern didn't supply company_name (e.g. platform pages),
        # try to derive it from the middleware or leave it blank so templates
        # can render the correct "no org" state instead of the fake "default" slug.
        if 'company_name' not in context or not context.get('company_name'):
            if hasattr(self.request, 'organization') and self.request.organization:
                context['company_name'] = self.request.organization.subdomain
            else:
                context['company_name'] = ''   # blank — templates must guard with {% if company_name %}

        return context


class RenderTemplateView(BaseWebContextMixin, TemplateView):
    pass
