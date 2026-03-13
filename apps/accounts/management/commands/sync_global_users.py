"""
Management command to sync GlobalUser records for tenant Users that are missing them.

Run: python manage.py sync_global_users

Useful when users were created outside UserProvisionService (e.g. Django admin, scripts)
or when the hybrid architecture was not fully applied.
"""
from django.core.management.base import BaseCommand
from django.db import connections
from apps.accounts.models import User, GlobalUser, Organization
from apps.accounts.services import UserProvisionService


class Command(BaseCommand):
    help = 'Create missing GlobalUser records for tenant Users (hybrid architecture repair)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--org',
            type=int,
            help='Only process users from this organization ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        org_filter = options.get('org')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be made'))

        # Get orgs that have users in default DB (shared setup) or we need to scan
        orgs = Organization.objects.filter(is_active=True).order_by('id')
        if org_filter:
            orgs = orgs.filter(id=org_filter)
            if not orgs.exists():
                self.stderr.write(self.style.ERROR(f'Organization {org_filter} not found'))
                return

        total_synced = 0
        for org in orgs:
            # Users for this org (shared default DB: has organization_id)
            users = User.objects.filter(organization_id=org.id)
            for user in users:
                exists = GlobalUser.objects.using('default').filter(
                    email=user.email,
                    organization=org
                ).exists()
                if not exists:
                    if dry_run:
                        self.stdout.write(
                            f'Would create GlobalUser for: {user.email} (org={org.subdomain}, user_id={user.id})'
                        )
                    else:
                        try:
                            gu = UserProvisionService.sync_global_user(user, org)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Created GlobalUser for: {user.email} (org={org.subdomain})'
                                )
                            )
                            total_synced += 1
                        except Exception as e:
                            self.stderr.write(
                                self.style.ERROR(f'Failed for {user.email}: {e}')
                            )
                if dry_run and not exists:
                    total_synced += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would have synced {total_synced} users'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Synced {total_synced} GlobalUser(s)'))
