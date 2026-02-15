from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import json
import re

# ============================================================================
# PLATFORM ADMIN MODEL
# ============================================================================
class PlatformAdmin(AbstractBaseUser):
    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    # last_login is provided by AbstractBaseUser
    
    # OTP for Password Reset
    reset_otp = models.CharField(max_length=6, null=True, blank=True)
    reset_otp_expires_at = models.DateTimeField(null=True, blank=True)
    
    objects = BaseUserManager() # Simple manager
    
    USERNAME_FIELD = 'email'
    
    class Meta:
        db_table = 'platform_admins'

    def __str__(self):
        return self.email
    
    # Required for Django admin and JWT authentication
    @property
    def is_staff(self):
        return self.is_active
    
    @property
    def is_superuser(self):
        return self.is_active
    
    def has_perm(self, perm, obj=None):
        return self.is_active
    
    def has_module_perms(self, app_label):
        return self.is_active


# ============================================================================
# ORGANIZATION (TENANT) MODEL
# ============================================================================
class Organization(models.Model):
    name = models.CharField(max_length=200)
    subdomain = models.CharField(max_length=100, unique=True, db_index=True)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Cluster-style SaaS fields
    cluster_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    plan = models.CharField(max_length=20, default='starter_trial')
    limits = models.TextField(null=True, blank=True) # JSON string
    
    # Organization-specific settings
    settings = models.TextField(null=True, blank=True) # JSON string
    
    class Meta:
        db_table = 'organizations'

    def __str__(self):
        return self.name

    def get_limits(self):
        if self.limits:
            try:
                return json.loads(self.limits)
            except (json.JSONDecodeError, TypeError):
                pass
        return self.get_default_limits(self.plan)

    def set_limits(self, limits_dict):
        self.limits = json.dumps(limits_dict)
        self.save()

    @staticmethod
    def get_default_limits(plan='starter_trial'):
        defaults = {
            'starter_trial': {
                'max_tickets_per_month': 100,
                'max_users': 30,
                'enabled_connectors': ['email'],
                'max_storage_mb': 100
            },
            'growth_cluster': {
                'max_tickets_per_month': -1,  # Unlimited
                'max_users': 200,
                'enabled_connectors': ['email', 'api', 'webhook'],
                'max_storage_mb': 1000,
                'has_dedicated_db': True
            }
        }
        return defaults.get(plan, defaults['starter_trial'])

# ============================================================================
# USER MANAGER
# ============================================================================
class UserManager(BaseUserManager):
    def create_user(self, email, organization_id, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        organization = Organization.objects.get(pk=organization_id)
        user = self.model(email=email, organization=organization, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # We need a default organization for superuser if enforcing organization_id
        # For simplicity in Django Admin, we might make organization null=True temporarily or handle it differently.
        # However, sticking to the schema:
        raise NotImplementedError("Use create_user with an organization_id. Superusers in this system are PlatformAdmins or need an Org.")

# ============================================================================
# USER MODEL
# ============================================================================
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='users')
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, default='agent') # admin, manager, agent
    department = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # OTP for Password Reset
    reset_otp = models.CharField(max_length=6, null=True, blank=True)
    reset_otp_expires_at = models.DateTimeField(null=True, blank=True)

    # Django Admin requirements
    is_staff = models.BooleanField(default=False) # For accessing Django Admin

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name'] # email and password are required by default

    class Meta:
        db_table = 'users'
        constraints = [
            models.UniqueConstraint(fields=['email', 'organization'], name='uq_user_email_org')
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"

# ============================================================================
# DEPARTMENT MODEL
# ============================================================================
class Department(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='departments')
    default_assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_departments')
    sla_policy_id = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        constraints = [
            models.UniqueConstraint(fields=['name', 'organization'], name='uq_department_name_org')
        ]

    def __str__(self):
        return self.name

# ============================================================================
# USER ROLE MODEL
# ============================================================================
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scoped_roles')
    role = models.CharField(max_length=20)
    scope_type = models.CharField(max_length=20) # organization, department, project
    scope_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'user_roles'
        constraints = [
            models.UniqueConstraint(fields=['user', 'scope_type', 'scope_id'], name='uq_user_role_scope')
        ]

# ============================================================================
# ORGANIZATION SECRET MODEL
# ============================================================================
class OrganizationSecret(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='secrets')
    key = models.CharField(max_length=100)
    encrypted_value = models.TextField()
    scope = models.CharField(max_length=20) # email, whatsapp, db, api
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization_secrets'
        constraints = [
            models.UniqueConstraint(fields=['organization', 'key'], name='uq_org_secret_key')
        ]
