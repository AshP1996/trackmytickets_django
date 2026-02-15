from django.db import models
from django.utils import timezone
from apps.accounts.models import User, Organization, Department
import json
import re

# ============================================================================
# PROJECT MODEL
# ============================================================================
class Project(models.Model):
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=10) # SUP, ENG
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects', db_constraint=False)
    lead_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_projects', db_constraint=False)
    description = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    extension_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['key', 'organization'], name='uq_project_key_org')
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"

# ============================================================================
# WORKFLOW MODEL
# ============================================================================
class Workflow(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='workflow')
    states = models.TextField(null=True, blank=True) # JSON array
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    STANDARD_STATES = ['open', 'in_progress', 'waiting', 'resolved', 'closed']

    class Meta:
        db_table = 'workflows'

# ============================================================================
# TICKET MODEL
# ============================================================================
class Ticket(models.Model):
    ticket_id = models.CharField(max_length=20) # SUP-123
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tickets')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='tickets', db_constraint=False)
    subject = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, default='open', db_index=True)
    priority = models.CharField(max_length=20, default='medium', db_index=True)
    
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets', db_constraint=False)
    # department_str for backward compatibility if needed, but we should rely on FK
    department_name = models.CharField(max_length=50, null=True, blank=True) 
    
    sender_email = models.CharField(max_length=120)
    sender_name = models.CharField(max_length=100, null=True, blank=True)
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets', db_constraint=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA Metrics
    first_response_at = models.DateTimeField(null=True, blank=True)
    first_response_time_seconds = models.IntegerField(null=True, blank=True)
    resolution_time_seconds = models.IntegerField(null=True, blank=True)
    
    # Email details
    email_message_id = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'tickets'
        constraints = [
            models.UniqueConstraint(fields=['ticket_id', 'organization'], name='uq_ticket_id_org')
        ]
        indexes = [
            models.Index(fields=['organization', 'status'], name='idx_ticket_org_status'),
            models.Index(fields=['organization', 'project'], name='idx_ticket_org_project'),
            models.Index(fields=['organization', 'assigned_to'], name='idx_ticket_assigned_org'),
            models.Index(fields=['organization', 'created_at'], name='idx_ticket_org_created'),
        ]

    def __str__(self):
        return f"{self.ticket_id}: {self.subject}"

    @classmethod
    def generate_ticket_id(cls, project_key, project_id):
        last_ticket = cls.objects.filter(project_id=project_id).order_by('-id').first()
        
        if not last_ticket:
            return f"{project_key}-1"
            
        try:
            parts = last_ticket.ticket_id.split('-')
            if len(parts) >= 2 and parts[-1].isdigit():
                next_num = int(parts[-1]) + 1
                return f"{project_key}-{next_num}"
        except Exception:
            pass
            
        count = cls.objects.filter(project_id=project_id).count()
        return f"{project_key}-{count + 1}"

# ============================================================================
# TICKET HISTORY MODEL
# ============================================================================
class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_actions', db_constraint=False)
    action = models.CharField(max_length=50)
    old_value = models.CharField(max_length=200, null=True, blank=True)
    new_value = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ticket_history'

# ============================================================================
# ATTACHMENT MODEL
# ============================================================================
class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    comment = models.ForeignKey('comments.Comment', on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments')
    filename = models.CharField(max_length=200)
    filepath = models.CharField(max_length=500)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'attachments'
