import logging
from django.db import transaction, IntegrityError
from apps.accounts.models import User, GlobalUser, Organization

logger = logging.getLogger('apps')

class UserProvisionService:
    """
    Handles synchronized provisioning of users entirely across the Hybrid Multi-Tenant User Architecture.
    Specifically:
      1) Creates the operational `User` strictly in the Tenant Database.
      2) Creates the `GlobalUser` directory object strictly in the Default platform Database.
    """

    @staticmethod
    def create_user(email, password, organization, **tenant_fields):
        email = email.lower().strip()
        # Ensure organization_id is set for shared default DB and for consistency
        tenant_fields.setdefault('organization_id', organization.id)
        try:
            with transaction.atomic():
                # 1) Create TenantUser in current DB (default or tenant_X from router)
                tenant_user = User.objects.create_user(
                    email=email,
                    password=password,
                    **tenant_fields
                )
                
                # 2) Create GlobalUser entry in Platform DB
                # Note: TenantDatabaseRouter automatically enforces GlobalUser to always 
                # reside in the 'default' DB, keeping it logically separated.
                global_user = GlobalUser.objects.using('default').create(
                    email=email,
                    organization=organization,
                    tenant_user_id=tenant_user.id,
                    status='active'
                )
                
                return tenant_user, global_user
                
        except IntegrityError as e:
            logger.error(f"Integrity error provisioning user {email} for org {organization.id}: {e}")
            raise ValueError("A user with this email already exists in this organization.")
        except Exception as e:
            logger.exception(f"Error provisioning user {email}")
            raise

    @staticmethod
    def sync_global_user(tenant_user, organization):
        """
        Validates if a GlobalUser exists for an authenticated TenantUser. 
        If missing, it auto-creates the GlobalUser record to synchronize the directory.
        """
        global_user, created = GlobalUser.objects.using('default').get_or_create(
            email=tenant_user.email,
            organization=organization,
            defaults={
                'tenant_user_id': tenant_user.id,
                'status': 'active' if tenant_user.is_active else 'inactive'
            }
        )
        # Self-healing missing IDs or out-of-sync status
        if not created and global_user.tenant_user_id != tenant_user.id:
            global_user.tenant_user_id = tenant_user.id
            global_user.save(update_fields=['tenant_user_id'])
            
        return global_user

