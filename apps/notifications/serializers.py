from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'message', 'type', 'is_read', 'link', 'created_at', 'actor_name']
        read_only_fields = ['id', 'created_at', 'message', 'type', 'link', 'actor_name']
        
    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else 'System'
