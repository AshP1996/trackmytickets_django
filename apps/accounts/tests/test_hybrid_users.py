import pytest
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User, GlobalUser, Organization
from apps.accounts.services import UserProvisionService
from apps.tickets.models import Ticket, Project

class HybridUserArchitectureTests(TestCase):
    def setUp(self):
        # 1. Create Organization (Platform DB)
        self.org_a = Organization.objects.create(
            name='Alpha Corp',
            subdomain='alpha',
            email='admin@alpha.com'
        )
        self.org_b = Organization.objects.create(
            name='Beta Inc',
            subdomain='beta',
            email='admin@beta.com'
        )

        # 2. Synchronized Provisioning
        self.user_a, self.global_a = UserProvisionService.create_user(
            email='emp@alpha.com',
            password='Password123!',
            organization=self.org_a,
            full_name='Alpha Employee',
            role='agent'
        )
        
        self.user_b, self.global_b = UserProvisionService.create_user(
            email='emp@beta.com',
            password='Password123!',
            organization=self.org_b,
            full_name='Beta Employee',
            role='agent'
        )

    def test_tenant_db_row_creation(self):
        """Test 1: Ensure tenant DB row exists and has no organization_id leakage"""
        # User should exist in the default/tenant DB context
        tenant_user = User.objects.get(email='emp@alpha.com')
        self.assertEqual(tenant_user.full_name, 'Alpha Employee')
        # organization_id was dropped from the model, so AttributeError should be raised if accessed
        with self.assertRaises(AttributeError):
            org_id = tenant_user.organization_id

    def test_globaluser_synchronization(self):
        """Test 2: Ensure GlobalUser row exists and is strictly routed to Default DB"""
        gu = GlobalUser.objects.get(email='emp@alpha.com')
        self.assertEqual(gu.organization, self.org_a)
        self.assertEqual(gu.status, 'active')

    def test_system_id_matching(self):
        """Test 3: Ensure IDs match correctly between Global and Tenant architectures"""
        gu = GlobalUser.objects.get(email='emp@alpha.com')
        self.assertEqual(gu.tenant_user_id, self.user_a.id)

    def test_ticket_references_tenant_user(self):
        """Test 4: Ensure operational data like Tickets correctly reference the Tenant User"""
        project = Project.objects.create(
            organization_id=self.org_a.id,
            name='Alpha Core',
            key='ALPH'
        )
        ticket = Ticket.objects.create(
            organization_id=self.org_a.id,
            project=project,
            subject='Hybrid Test',
            created_by=self.user_a
        )
        
        # Verify foreign key resolves completely inside the operational boundary
        self.assertEqual(ticket.created_by.email, 'emp@alpha.com')
        self.assertEqual(ticket.created_by.full_name, 'Alpha Employee')

    def test_cross_tenant_jwt_isolation(self):
        """Test 5: Ensure User from Org A cannot access Org B"""
        client = APIClient()
        
        # 1. Authorize as Org A (Alpha)
        response = client.post(f'/api/{self.org_a.subdomain}/auth/login/', {
            'email': 'emp@alpha.com',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data['access_token']
        
        # 2. Attempt to hit Org B's API using Org A's token
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        beta_response = client.get(f'/api/{self.org_b.subdomain}/auth/me/')
        
        import json
        self.assertIn('Forbidden', json.loads(beta_response.content)['error'])
