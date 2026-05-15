from django.db import models
from django.utils import timezone
from apps.accounts.models import User, Department
import json
import re

# ============================================================================
# TAG MODEL
# ============================================================================
class Tag(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#6b778c')  # hex color
    organization_id = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tags'
        constraints = [
            models.UniqueConstraint(fields=['name', 'organization_id'], name='uq_tag_name_org')
        ]

    def __str__(self):
        return self.name

# ============================================================================
# SLA POLICY MODEL
# ============================================================================
class SLAPolicy(models.Model):
    name = models.CharField(max_length=100)
    organization_id = models.IntegerField(default=0)
    priority = models.CharField(max_length=20, db_index=True)  # low, medium, high, critical
    response_hours = models.IntegerField(default=24, help_text='Target first response time in hours')
    resolution_hours = models.IntegerField(default=72, help_text='Target resolution time in hours')
    escalation_hours = models.IntegerField(default=48, help_text='Hours before auto-escalation')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'sla_policies'
        constraints = [
            models.UniqueConstraint(fields=['organization_id', 'priority'], name='uq_sla_org_priority')
        ]

    def __str__(self):
        return f"{self.name} ({self.priority})"

# ============================================================================
# PROJECT MODEL
# ============================================================================
class Project(models.Model):
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=10)  # SUP, ENG
    organization_id = models.IntegerField(default=0)
    lead_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_projects')
    description = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    extension_date = models.DateTimeField(null=True, blank=True)
    default_assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_projects')
    ticket_sequence = models.PositiveIntegerField(default=0, help_text='Atomic counter for generating unique ticket IDs')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['key', 'organization_id'], name='uq_project_key_org')
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"

# ============================================================================
# WORKFLOW MODEL
# ============================================================================
class Workflow(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='workflow')
    states = models.TextField(null=True, blank=True)  # JSON array
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    STANDARD_STATES = ['open', 'in_progress', 'waiting', 'resolved', 'closed']

    class Meta:
        db_table = 'workflows'

# ============================================================================
# TICKET MODEL
# ============================================================================
class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    TYPE_CHOICES = [
        ('issue', 'Issue'),
        ('bug', 'Bug'),
        ('feature_request', 'Feature Request'),
        ('question', 'Question'),
        ('task', 'Task'),
    ]
    SOURCE_CHOICES = [
        ('web', 'Web'),
        ('email', 'Email'),
        ('api', 'API'),
        ('phone', 'Phone'),
    ]

    ticket_id = models.CharField(max_length=20)  # SUP-123
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tickets')
    organization_id = models.IntegerField(default=0)
    subject = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, default='open', choices=STATUS_CHOICES, db_index=True)
    priority = models.CharField(max_length=20, default='medium', choices=PRIORITY_CHOICES, db_index=True)
    
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    department_name = models.CharField(max_length=50, null=True, blank=True)
    
    sender_email = models.CharField(max_length=120)
    sender_name = models.CharField(max_length=100, null=True, blank=True)
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tickets')
    
    # Tags
    tags = models.ManyToManyField(Tag, blank=True, related_name='tickets')
    
    # Ticket type & source
    ticket_type = models.CharField(max_length=30, default='issue', choices=TYPE_CHOICES, db_index=True)
    source = models.CharField(max_length=30, default='web', choices=SOURCE_CHOICES)

    # Due date
    due_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # SLA Metrics
    first_response_at = models.DateTimeField(null=True, blank=True)
    first_response_time_seconds = models.IntegerField(null=True, blank=True)
    resolution_time_seconds = models.IntegerField(null=True, blank=True)
    sla_response_deadline = models.DateTimeField(null=True, blank=True)
    sla_resolution_deadline = models.DateTimeField(null=True, blank=True)
    sla_breach_at = models.DateTimeField(null=True, blank=True)
    
    # Email details
    email_message_id = models.CharField(max_length=200, null=True, blank=True)
    
    # Merge tracking
    merged_into = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='merged_tickets')
    is_merged = models.BooleanField(default=False)

    class Meta:
        db_table = 'tickets'
        constraints = [
            models.UniqueConstraint(fields=['ticket_id', 'organization_id'], name='uq_ticket_id_org')
        ]
        indexes = [
            models.Index(fields=['organization_id', 'status'], name='idx_ticket_org_status'),
            models.Index(fields=['organization_id', 'project'], name='idx_ticket_org_project'),
            models.Index(fields=['organization_id', 'assigned_to'], name='idx_ticket_assigned_org'),
            models.Index(fields=['organization_id', 'created_at'], name='idx_ticket_org_created'),
            models.Index(fields=['organization_id', 'priority'], name='idx_ticket_org_priority'),
            models.Index(fields=['organization_id', 'ticket_type'], name='idx_ticket_org_type'),
            models.Index(
                fields=['organization_id', 'sla_resolution_deadline'],
                name='idx_ticket_org_sla_deadline',
            ),
            models.Index(
                fields=['organization_id', 'due_date'],
                name='idx_ticket_org_due_date',
            ),
        ]

    def __str__(self):
        return f"{self.ticket_id}: {self.subject}"

    @property
    def is_sla_breached(self):
        """Check if any SLA deadline has been exceeded."""
        now = timezone.now()
        if self.status in ('resolved', 'closed'):
            return False
        if self.sla_response_deadline and not self.first_response_at and now > self.sla_response_deadline:
            return True
        if self.sla_resolution_deadline and now > self.sla_resolution_deadline:
            return True
        return False

    @property
    def is_overdue(self):
        """Check if ticket is past its due date."""
        if self.due_date and self.status not in ('resolved', 'closed'):
            return timezone.now() > self.due_date
        return False

    @classmethod
    def generate_ticket_id(cls, project_key, project_id):
        """Atomic ticket ID generation using Project.ticket_sequence counter.
        
        Uses F() expression for a single atomic UPDATE ... SET ticket_sequence =
        ticket_sequence + 1, which is safe under concurrent access on all backends
        (including SQLite).
        """
        from apps.tickets.models import Project
        from django.db.models import F

        # Atomically increment and retrieve the new sequence number
        Project.objects.filter(id=project_id).update(
            ticket_sequence=F('ticket_sequence') + 1
        )
        project = Project.objects.filter(id=project_id).values_list(
            'ticket_sequence', flat=True
        ).first()
        seq = project if project else 1
        return f"{project_key}-{seq}"

# ============================================================================
# TICKET WATCHER MODEL
# ============================================================================
class TicketWatcher(models.Model):
    """Allows users to watch/subscribe to ticket updates."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='watchers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_tickets')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ticket_watchers'
        constraints = [
            models.UniqueConstraint(fields=['ticket', 'user'], name='uq_ticket_watcher')
        ]

    def __str__(self):
        return f"{self.user.full_name} watching {self.ticket.ticket_id}"

# ============================================================================
# TICKET HISTORY MODEL
# ============================================================================
class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_actions')
    action = models.CharField(max_length=50)
    field_name = models.CharField(max_length=50, null=True, blank=True)
    old_value = models.CharField(max_length=200, null=True, blank=True)
    new_value = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ticket_history'
        ordering = ['-created_at']

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
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'attachments'

# ============================================================================
# CANNED RESPONSE MODEL
# ============================================================================
class CannedResponse(models.Model):
    """Pre-defined response templates for quick replies."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    organization_id = models.IntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    is_shared = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'canned_responses'
        ordering = ['-usage_count', 'title']

    def __str__(self):
        return self.title

# ============================================================================
# KNOWLEDGE BASE MODELS
# ============================================================================
class KBCategory(models.Model):
    """Knowledge base article categories."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(null=True, blank=True)
    organization_id = models.IntegerField(default=0)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'kb_categories'
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['slug', 'organization_id'], name='uq_kb_cat_slug_org')
        ]

    def __str__(self):
        return self.name


class KBArticle(models.Model):
    """Knowledge base articles for self-service support."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, null=True, blank=True)
    category = models.ForeignKey(KBCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    organization_id = models.IntegerField(default=0)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='draft', choices=STATUS_CHOICES, db_index=True)
    tags = models.CharField(max_length=500, null=True, blank=True)  # comma-separated tags
    views_count = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'kb_articles'
        ordering = ['-is_pinned', '-published_at']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['organization_id', 'category']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['slug', 'organization_id'], name='uq_kb_article_slug_org')
        ]

    def __str__(self):
        return self.title

# ============================================================================
# AUDIT LOG MODEL
# ============================================================================
class AuditLog(models.Model):
    """System-wide audit log for tracking important actions."""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('user_created', 'User Created'),
        ('export', 'Export'),
        ('bulk_action', 'Bulk Action'),
        ('settings_change', 'Settings Change'),
    ]
    
    organization_id = models.IntegerField(default=0)
    user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'action']),
            models.Index(fields=['organization_id', 'resource_type']),
            models.Index(fields=['user_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.resource_type} (User ID {self.user_id})"

    @classmethod
    def log(cls, request, action, resource_type, resource_id=None, description='', extra_data=None):
        """Convenience method to create an audit log entry."""
        org = getattr(request, 'organization', None)
        if not org:
            return None
        
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
        
        return cls.objects.create(
            organization_id=org.id,
            user_id=request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            description=description,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            extra_data=extra_data,
        )