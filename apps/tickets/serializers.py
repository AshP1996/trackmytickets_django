from rest_framework import serializers
from .models import (
    Ticket, Project, TicketHistory, Attachment, Tag, SLAPolicy,
    TicketWatcher, CannedResponse, KBCategory, KBArticle, AuditLog,
)
from apps.comments.models import Comment
from apps.accounts.serializers import UserSerializer


# ============================================================================
# TAG SERIALIZER
# ============================================================================
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']
        read_only_fields = ['id']


# ============================================================================
# SLA POLICY SERIALIZER
# ============================================================================
class SLAPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAPolicy
        fields = ['id', 'name', 'priority', 'response_hours', 'resolution_hours',
                  'escalation_hours', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


# ============================================================================
# PROJECT SERIALIZER
# ============================================================================
class ProjectSerializer(serializers.ModelSerializer):
    lead_user_name = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    open_ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'key', 'description', 'is_active', 'lead_user',
                  'lead_user_name', 'default_assignee', 'start_date', 'end_date',
                  'ticket_count', 'open_ticket_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_lead_user_name(self, obj):
        return obj.lead_user.full_name if obj.lead_user else None

    def get_ticket_count(self, obj):
        return obj.tickets.count()

    def get_open_ticket_count(self, obj):
        return obj.tickets.exclude(status__in=['resolved', 'closed']).count()


# ============================================================================
# ATTACHMENT SERIALIZER
# ============================================================================
class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.DateTimeField(read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'filename', 'file_size', 'mime_type', 'uploaded_at',
                  'filepath', 'uploaded_by_name']
        read_only_fields = ['id', 'filename', 'file_size', 'mime_type',
                           'uploaded_at', 'filepath']

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.full_name if obj.uploaded_by else None


# ============================================================================
# TICKET HISTORY SERIALIZER
# ============================================================================
class TicketHistorySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketHistory
        fields = ['id', 'action', 'field_name', 'old_value', 'new_value',
                  'created_at', 'user_name']

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else 'System'


# ============================================================================
# COMMENT SERIALIZER (override from comments app for ticket detail)
# ============================================================================
class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'comment', 'is_internal', 'created_at', 'user_name', 'attachments']

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else 'Unknown'


# ============================================================================
# TICKET WATCHER SERIALIZER
# ============================================================================
class TicketWatcherSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = TicketWatcher
        fields = ['id', 'user', 'user_name', 'user_email', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else None

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


# ============================================================================
# TICKET LIST SERIALIZER
# ============================================================================
class TicketListSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source='project.key', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    sla_status = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    watcher_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'status', 'priority', 'ticket_type',
                  'source', 'project_key', 'assigned_to_name', 'created_at',
                  'updated_at', 'due_date', 'sender_email', 'tags', 'sla_status',
                  'is_overdue', 'is_merged', 'watcher_count']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_sla_status(self, obj):
        if obj.is_sla_breached:
            return 'breached'
        if obj.sla_resolution_deadline or obj.sla_response_deadline:
            return 'on_track'
        return None

    def get_watcher_count(self, obj):
        return obj.watchers.count()


# ============================================================================
# TICKET DETAIL SERIALIZER
# ============================================================================
class TicketDetailSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    allowed_transitions = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    sla_status = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    watchers = TicketWatcherSerializer(many=True, read_only=True)
    merged_tickets_info = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'description', 'status', 'priority',
                  'ticket_type', 'source', 'due_date',
                  'project_id', 'project_key', 'project_name', 'assigned_to',
                  'assigned_to_name', 'created_by_name', 'sender_email', 'sender_name',
                  'department', 'department_name',
                  'created_at', 'updated_at', 'closed_at',
                  'comments', 'history', 'attachments', 'watchers',
                  'allowed_transitions', 'tags', 'sla_status', 'is_overdue',
                  'sla_response_deadline', 'sla_resolution_deadline',
                  'first_response_at', 'first_response_time_seconds',
                  'resolution_time_seconds',
                  'is_merged', 'merged_into', 'merged_tickets_info']
        read_only_fields = ['id', 'ticket_id', 'project_key', 'project_name',
                           'sender_email', 'sender_name', 'created_at', 'updated_at',
                           'history', 'comments', 'attachments', 'closed_at']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None

    def get_allowed_transitions(self, obj):
        """Return valid next statuses based on the current ticket status."""
        TRANSITIONS = {
            'open': ['in_progress', 'closed'],
            'in_progress': ['waiting', 'resolved', 'closed'],
            'waiting': ['in_progress', 'resolved', 'closed'],
            'resolved': ['closed', 'open'],
            'closed': ['open'],
        }
        return TRANSITIONS.get(obj.status, [])

    def get_sla_status(self, obj):
        if obj.is_sla_breached:
            return 'breached'
        if obj.sla_resolution_deadline or obj.sla_response_deadline:
            return 'on_track'
        return None

    def get_merged_tickets_info(self, obj):
        """Show tickets that were merged into this one."""
        merged = obj.merged_tickets.all()
        if not merged.exists():
            return []
        return [{'ticket_id': t.ticket_id, 'subject': t.subject} for t in merged]


# ============================================================================
# TICKET CREATE SERIALIZER
# ============================================================================
class TicketCreateSerializer(serializers.ModelSerializer):
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'description', 'priority',
                  'ticket_type', 'source', 'due_date',
                  'project', 'department', 'assigned_to',
                  'attachments', 'tag_ids', 'created_at']
        read_only_fields = ['id', 'ticket_id', 'created_at']
        extra_kwargs = {
            'project': {'required': True}
        }

    def create(self, validated_data):
        """
        Attachments are handled manually in the view using request.FILES.
        Remove them from validated_data so DRF doesn't try to assign the
        raw InMemoryUploadedFile list to the related field.
        """
        validated_data.pop('attachments', None)
        return super().create(validated_data)


# ============================================================================
# CANNED RESPONSE SERIALIZER
# ============================================================================
class CannedResponseSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CannedResponse
        fields = ['id', 'title', 'content', 'category', 'is_shared',
                  'usage_count', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None


# ============================================================================
# KNOWLEDGE BASE SERIALIZERS
# ============================================================================
class KBCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = KBCategory
        fields = ['id', 'name', 'slug', 'description', 'parent', 'order',
                  'is_active', 'article_count', 'children', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_article_count(self, obj):
        return obj.articles.filter(status='published').count()

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        if children.exists():
            return KBCategorySerializer(children, many=True).data
        return []


class KBArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = KBArticle
        fields = ['id', 'title', 'slug', 'excerpt', 'category', 'category_name',
                  'author_name', 'status', 'tags', 'views_count', 'helpful_count',
                  'is_pinned', 'published_at', 'updated_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else None


class KBArticleDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = KBArticle
        fields = ['id', 'title', 'slug', 'content', 'excerpt', 'category',
                  'category_name', 'author_name', 'status', 'tags',
                  'views_count', 'helpful_count', 'not_helpful_count',
                  'is_pinned', 'published_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'views_count', 'helpful_count',
                           'not_helpful_count', 'created_at', 'updated_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else None


# ============================================================================
# AUDIT LOG SERIALIZER
# ============================================================================
class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'resource_type', 'resource_id', 'description',
                  'user_name', 'ip_address', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        if not obj.user_id:
            return 'System'
        try:
            from apps.accounts.models import User
            user = User.objects.filter(id=obj.user_id).values_list('full_name', flat=True).first()
            return user or f'User #{obj.user_id}'
        except Exception:
            return f'User #{obj.user_id}'
