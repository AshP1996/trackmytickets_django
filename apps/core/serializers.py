"""
Serializers for Core app models
"""
from rest_framework import serializers
from .models import ExternalDataSource, SchemaMapping, Feedback, Enquiry

class ExternalDataSourceSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = ExternalDataSource
        fields = [
            'id', 'name', 'type', 'type_display', 'host', 'port', 'database',
            'username', 'password', 'connection_string', 'ssl_enabled', 'ssl_cert_path',
            'connection_status', 'last_connection_test', 'connection_error',
            'metadata', 'is_active', 'last_sync_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'connection_status', 'last_connection_test', 'connection_error', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        datasource = ExternalDataSource(**validated_data)
        if password:
            datasource.set_password(password)
        datasource.save()
        return datasource
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class SchemaMappingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_key = serializers.CharField(source='project.key', read_only=True)
    
    class Meta:
        model = SchemaMapping
        fields = [
            'id', 'datasource', 'table_name', 'field_mapping', 'project', 
            'project_name', 'project_key', 'id_column', 'last_synced_id',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user_id', 'user_email', 'type', 'message', 'rating', 'created_at']
        read_only_fields = ['id', 'user_id', 'user_email', 'created_at']

class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['id', 'name', 'email', 'company', 'phone', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
