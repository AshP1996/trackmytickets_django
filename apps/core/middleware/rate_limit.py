"""
Rate Limit Middleware — atomic increment edition.

FIX for TOCTOU race in the original:
    Original pattern:
        count = cache.get(key)          # Thread A reads 999
        if count >= limit: block        # Thread A: 999 < 1000, continue
        cache.incr(key)                 # Thread A increments to 1000
        # Thread B also read 999 concurrently — BOTH pass the limit check!

    Fixed pattern:
        Use cache.add() to atomically set key=1 with TTL if absent,
        then cache.incr() for subsequent hits. The incr() return value
        IS the authoritative count. If it exceeds the limit, reject.

    This is correct on both Redis and Memcached backends.
    On Redis, both add and incr are atomic single-command operations.

COMPLEXITY:
    O(1) per request — two cache round-trips maximum (add + incr),
    or one if the key already exists (just incr).
"""

import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger('apps')


class RateLimitMiddleware:
    """
    Rate Limiting Middleware using Django cache (Redis recommended).
    Limits requests per organization AND per IP address.

    Runs via process_view so TenantMiddleware has already set request.organization.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.org_limit = getattr(settings, 'ORG_RATE_LIMIT', 1000)   # per window per org
        self.ip_limit = getattr(settings, 'IP_RATE_LIMIT', 200)       # per window per IP
        self.window = 60  # seconds

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        client_ip = self._get_client_ip(request)

        # Determine if this is a sensitive auth endpoint (stricter limit)
        path = request.path.rstrip('/')
        is_auth_endpoint = any(path.endswith(p) for p in (
            '/login', '/forgot-password', '/reset-password', '/register'
        ))
        effective_ip_limit = 10 if is_auth_endpoint else self.ip_limit

        # 1. Per-IP check
        if client_ip:
            key_suffix = ':auth' if is_auth_endpoint else ''
            if self._is_rate_limited(f'rl:ip:{client_ip}{key_suffix}', effective_ip_limit):
                logger.warning('ip_rate_limit_exceeded ip=%s auth=%s', client_ip, is_auth_endpoint)
                return self._rate_limit_response()

        # 2. Per-organization check
        org = getattr(request, 'organization', None)
        if org:
            if self._is_rate_limited(f'rl:org:{org.id}', self.org_limit):
                logger.warning('org_rate_limit_exceeded org_id=%s', org.id)
                return self._rate_limit_response(per_org=True)

        return None

    # ------------------------------------------------------------------

    def _is_rate_limited(self, key: str, limit: int) -> bool:
        """
        Atomically increment the request counter and check against the limit.

        cache.add()  — sets key=1 with TTL only if key does NOT exist (atomic).
        cache.incr() — atomically increments and returns the new value.

        If add() returns True the key was new, count is 1 → never rate-limited.
        If add() returns False the key existed; incr() gives the authoritative count.
        """
        try:
            added = cache.add(key, 1, timeout=self.window)
            if added:
                # Key was just created; this is the first request in the window.
                return False
            count = cache.incr(key)
            return count > limit
        except Exception:
            # Cache unavailable → fail open (let request through).
            logger.debug('rate_limit_cache_error key=%s', key)
            return False

    def _rate_limit_response(self, per_org: bool = False) -> JsonResponse:
        scope = 'organization' if per_org else 'IP'
        return JsonResponse(
            {
                'error': 'rate_limit_exceeded',
                'message': f'Too many requests from this {scope}. Please retry after {self.window}s.',
                'retry_after': self.window,
            },
            status=429,
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            # Trust only the *first* IP in the chain (closest to the client).
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
