from django.test import SimpleTestCase

from apps.accounts.subdomain_policy import validate_organization_subdomain


class SubdomainPolicyTests(SimpleTestCase):
    def test_valid_subdomain(self):
        ok, _ = validate_organization_subdomain('acme-corp')
        self.assertTrue(ok)

    def test_reserved_subdomain(self):
        ok, msg = validate_organization_subdomain('paypal')
        self.assertFalse(ok)
        self.assertIn('reserved', msg.lower())

    def test_brand_substring_blocked(self):
        ok, _ = validate_organization_subdomain('acme-google-support')
        self.assertFalse(ok)
