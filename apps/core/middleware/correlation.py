"""
Correlation ID + Observability Middleware

Responsibilities:
    1. Generate a UUID4 correlation ID for every incoming request (or accept one
       from the X-Correlation-ID header if the client/upstream LB already set it).
    2. Attach it to request.correlation_id.
    3. Inject it into all log records for this request via a custom logging Filter.
    4. Add X-Correlation-ID and X-Request-Duration-Ms to every response header.
    5. Log structured request metadata (tenant, user, path, status, duration).

This middleware intentionally uses NO external deps — just stdlib logging + Django.
Position in MIDDLEWARE: place BEFORE TenantMiddleware so the ID is present even
for requests that fail org resolution.
"""

import logging
import time
import uuid
from contextvars import ContextVar

logger = logging.getLogger('apps')

# ContextVar so the correlation ID is accessible from any function in the call stack
# without needing to thread it through every argument.
_correlation_id: ContextVar[str] = ContextVar('correlation_id', default='-')


def get_correlation_id() -> str:
    """Return the active correlation ID for this request context."""
    return _correlation_id.get()


class _CorrelationFilter(logging.Filter):
    """
    Logging filter that injects 'correlation_id' and 'tenant_id' into every
    LogRecord emitted during a request lifecycle. This allows log formatters
    to include these fields without modifying every log call site.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        # tenant_id is set by TenantMiddleware — best-effort; default to '-'
        record.tenant_id = getattr(record, 'tenant_id', '-')
        return True


# Install the filter once on the 'apps' logger so all child loggers inherit it.
_filter = _CorrelationFilter()
logger.addFilter(_filter)


class CorrelationIDMiddleware:
    """
    Django middleware (WSGI and ASGI compatible) that:
        - Generates / propagates a per-request correlation ID.
        - Measures total request wall-clock time.
        - Emits a structured JSON-like log line on request completion.
        - Appends X-Correlation-ID and X-Request-Duration-Ms to responses.
    """

    INCOMING_HEADER = 'HTTP_X_CORRELATION_ID'
    OUTGOING_HEADER_ID = 'X-Correlation-ID'
    OUTGOING_HEADER_DUR = 'X-Request-Duration-Ms'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ---- 1. Resolve or generate correlation ID ----
        raw = request.META.get(self.INCOMING_HEADER, '').strip()
        try:
            # Validate client-supplied ID is a real UUID to prevent header injection
            cid = str(uuid.UUID(raw)) if raw else str(uuid.uuid4())
        except ValueError:
            cid = str(uuid.uuid4())

        request.correlation_id = cid
        token = _correlation_id.set(cid)

        start_time = time.monotonic()

        # ---- 2. Process request ----
        response = self.get_response(request)

        # ---- 3. Measure duration ----
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # ---- 4. Structured completion log ----
        tenant_id = getattr(getattr(request, 'organization', None), 'id', '-')
        user_id = (
            request.user.id
            if hasattr(request, 'user') and request.user and request.user.is_authenticated
            else '-'
        )

        logger.info(
            'request_complete '
            'correlation_id=%s tenant_id=%s user_id=%s method=%s path=%s '
            'status=%s duration_ms=%s',
            cid, tenant_id, user_id,
            request.method, request.path,
            response.status_code, duration_ms,
        )

        # ---- 5. Inject into response headers ----
        response[self.OUTGOING_HEADER_ID] = cid
        response[self.OUTGOING_HEADER_DUR] = str(duration_ms)

        # ---- 6. Reset ContextVar when done (clean-up for persistent workers) ----
        _correlation_id.reset(token)

        return response
