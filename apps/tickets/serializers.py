from rest_framework import serializers
from .models import Ticket, Project, TicketHistory, Attachment
from apps.comments.models import Comment
from apps.accounts.serializers import UserSerializer

class ProjectSerializer(serializers.ModelSerializer):
    lead_user_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'key', 'description', 'is_active', 'lead_user', 'lead_user_name', 'created_at']
        
    def get_lead_user_name(self, obj):
        return obj.lead_user.full_name if obj.lead_user else None

class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Attachment
        fields = ['id', 'filename', 'file_size', 'mime_type', 'uploaded_at', 'filepath']
        read_only_fields = ['id', 'filename', 'file_size', 'mime_type', 'uploaded_at', 'filepath']

class TicketHistorySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketHistory
        fields = ['id', 'action', 'old_value', 'new_value', 'created_at', 'user_name']
        
    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else 'System'

class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'comment', 'is_internal', 'created_at', 'user_name', 'attachments']
        
    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else 'Unknown'

class TicketListSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source='project.key', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'status', 'priority', 'project_key', 
                  'assigned_to_name', 'created_at', 'sender_email']
        
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

class TicketDetailSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source='project.key', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    allowed_transitions = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'description', 'status', 'priority', 
                  'project_id', 'project_key', 'project_name', 'assigned_to', 
                  'assigned_to_name', 'sender_email', 'sender_name', 'department',
                  'created_at', 'updated_at', 'comments', 'history', 'attachments',
                  'allowed_transitions']
        read_only_fields = ['id', 'ticket_id', 'project_key', 'project_name', 'sender_email', 'sender_name', 'created_at', 'updated_at', 'history', 'comments', 'attachments']
                  
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None
        
    def get_allowed_transitions(self, obj):
        # TODO: Port get_allowed_transitions_for_ticket logic
        return []

class TicketCreateSerializer(serializers.ModelSerializer):
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'subject', 'description', 'priority', 'project', 'department', 
                  'assigned_to', 'attachments', 'created_at']
        read_only_fields = ['id', 'ticket_id', 'created_at']
        extra_kwargs = {
            'project': {'required': True}
        }
