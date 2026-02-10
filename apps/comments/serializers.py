from rest_framework import serializers
from .models import Comment
from apps.accounts.serializers import UserSerializer

class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'ticket', 'user', 'user_name', 'comment', 'is_internal', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']
