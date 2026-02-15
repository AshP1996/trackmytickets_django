import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

class RateLimitMiddleware:
    """
    Simple Rate Limiting Middleware using Redis
    Limits requests per organization
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Default limit: 1000 requests per minute per org
        self.rate_limit = getattr(settings, 'ORG_RATE_LIMIT', 1000)
        self.window = 60  # seconds

    def __call__(self, request):
        if not hasattr(request, 'organization') or not request.organization:
            return self.get_response(request)

        org_id = request.organization.id
        client_ip = self.get_client_ip(request)
        
        # Key format: rate_limit:org_id
        key = f"rate_limit:{org_id}"
        
        # Increment counter
        try:
            # Use Redis atomic increment
            current_count = cache.incr(key)
            
            # If this is the first request, set expiry
            if current_count == 1:
                cache.touch(key, self.window)
                
            if current_count > self.rate_limit:
                return JsonResponse({
                    'error': 'Rate limit exceeded', 
                    'message': 'Too many requests. Please try again later.'
                }, status=429)
                
        except Exception:
            # If cache fails, fail open (allow request)
            pass

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
