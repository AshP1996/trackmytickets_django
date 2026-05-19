"""Reserved and deceptive subdomain rules for public org registration."""
import re

SUBDOMAIN_PATTERN = re.compile(r'^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$')

# Exact reserved slugs (path segments on the public site)
RESERVED_SUBDOMAINS = frozenset({
    'www', 'api', 'admin', 'platform', 'static', 'media', 'mail', 'ftp', 'cdn',
    'login', 'signin', 'signup', 'register', 'auth', 'oauth', 'account', 'accounts',
    'support', 'help', 'secure', 'security', 'verify', 'verification', 'update',
    'bank', 'banking', 'paypal', 'stripe', 'wallet', 'payment', 'billing', 'invoice',
    'google', 'gmail', 'microsoft', 'apple', 'amazon', 'facebook', 'meta', 'instagram',
    'whatsapp', 'telegram', 'netflix', 'office', 'outlook', 'yahoo', 'icloud',
    'password', 'reset', 'recover', 'download', 'files', 'root', 'system', 'config',
    'dev', 'staging', 'prod', 'production', 'test', 'demo', 'enquiry', 'features',
    'pricing', 'privacy-policy', 'terms-of-service', 'sitemap', 'robots',
})

# Block subdomains containing brand/phishing-adjacent terms
FORBIDDEN_SUBSTRINGS = (
    'paypal', 'google', 'gmail', 'microsoft', 'apple', 'amazon', 'facebook',
    'instagram', 'whatsapp', 'netflix', 'login', 'signin', 'verify', 'secure',
    'bank', 'wallet', 'password', 'support-team', 'helpdesk-official', 'account-',
    '-account', 'oauth', 'admin-', '-admin',
)


def normalize_subdomain(value):
    return (value or '').strip().lower()


def validate_organization_subdomain(subdomain):
    """
    Return (is_valid, error_message).
    Used for public registration and platform-admin org creation.
    """
    subdomain = normalize_subdomain(subdomain)
    if not subdomain:
        return False, 'Subdomain is required.'
    if len(subdomain) < 3:
        return False, 'Subdomain must be at least 3 characters.'
    if len(subdomain) > 63:
        return False, 'Subdomain must be 63 characters or fewer.'
    if not SUBDOMAIN_PATTERN.match(subdomain):
        return False, (
            'Subdomain may only use lowercase letters, numbers, and hyphens '
            '(cannot start or end with a hyphen).'
        )
    if subdomain in RESERVED_SUBDOMAINS:
        return False, 'This subdomain is reserved. Please choose a different name.'
    for term in FORBIDDEN_SUBSTRINGS:
        if term in subdomain:
            return False, (
                'This subdomain is not allowed because it may be confused with '
                'another brand or service. Please choose a unique organization name.'
            )
    return True, ''
