from django.db import models
from django.utils import timezone
from apps.accounts.models import User, Organization
from apps.tickets.models import Project
import json

# ============================================================================
# FEEDBACK MODEL
# ============================================================================
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    type = models.CharField(max_length=50) # 'bug', 'feature', 'improvement'
    message = models.TextField()
    rating = models.IntegerField(null=True, blank=True) # 1-5 stars
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'feedback'

    def __str__(self):
        return f"Feedback from {self.user} ({self.type})"

# ============================================================================
# ENQUIRY MODEL (Landing Page Contact Form)
# ============================================================================
class Enquiry(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(db_index=True)
    company = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'enquiries'

    def __str__(self):
        return f"Enquiry from {self.name} ({self.email})"

# ============================================================================
# EXTERNAL DATA SOURCE MODEL
# ============================================================================
class ExternalDataSource(models.Model):
    TYPE_CHOICES = [
        ('sqlite', 'SQLite'),
        ('postgres', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('mariadb', 'MariaDB'),
        ('mongodb', 'MongoDB'),
        ('sqlserver', 'Microsoft SQL Server'),
        ('oracle', 'Oracle Database'),
        ('redis', 'Redis'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='external_data_sources', db_index=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='sqlite')
    
    # Connection details
    host = models.CharField(max_length=200, null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    database = models.CharField(max_length=100)
    username = models.CharField(max_length=100, null=True, blank=True)
    password_encrypted = models.TextField(null=True, blank=True)  # Encrypted password
    
    # Advanced options
    connection_string = models.TextField(null=True, blank=True)  # For custom connection strings
    ssl_enabled = models.BooleanField(default=False)
    ssl_cert_path = models.CharField(max_length=500, null=True, blank=True)
    
    # Legacy field for backward compatibility
    credentials_ref = models.CharField(max_length=100, null=True, blank=True)
    
    # Connection status
    connection_status = models.CharField(max_length=20, default='untested')  # untested, connected, failed
    last_connection_test = models.DateTimeField(null=True, blank=True)
    connection_error = models.TextField(null=True, blank=True)
    
    # Metadata for database-specific configs
    metadata = models.JSONField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'external_data_sources'

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def set_password(self, raw_password):
        """Encrypt and store password"""
        from apps.core.utils.encryption import encrypt_password
        self.password_encrypted = encrypt_password(raw_password)
    
    def get_password(self):
        """Decrypt and return password"""
        if not self.password_encrypted:
            return None
        from apps.core.utils.encryption import decrypt_password
        return decrypt_password(self.password_encrypted)

# ============================================================================
# SCHEMA MAPPING MODEL
# ============================================================================
class SchemaMapping(models.Model):
    datasource = models.ForeignKey(ExternalDataSource, on_delete=models.CASCADE, related_name='schema_mappings', db_index=True)
    table_name = models.CharField(max_length=100)
    field_mapping = models.TextField() # JSON string
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='schema_mappings')
    id_column = models.CharField(max_length=100) # Column name for external row ID
    last_synced_id = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'schema_mappings'

    def __str__(self):
        return f"Mapping for {self.table_name} -> {self.project.key}"

    def get_field_mapping(self):
        if self.field_mapping:
            try:
                return json.loads(self.field_mapping)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}
