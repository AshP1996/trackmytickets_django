from rest_framework import serializers
from .models import User, Organization, Department, UserRole

class OrganizationSerializer(serializers.ModelSerializer):
    limits = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'subdomain', 'email', 'is_active', 'cluster_id', 'plan', 'limits', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'limits']

    def get_limits(self, obj):
        return obj.get_limits()

class UserSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    organization_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'department', 'is_active', 
                  'is_onboarded', 'created_at', 'organization', 'organization_id']
        read_only_fields = ['id', 'created_at', 'is_active', 'is_onboarded']
        extra_kwargs = {
            'organization_id': {'write_only': True}
        }

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'role', 'department', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    organization_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'role', 'department', 'organization_id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        organization_id = validated_data.pop('organization_id')
        organization = Organization.objects.get(pk=organization_id)
        
        user = User.objects.create(
            organization=organization,
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'default_assignee', 'sla_policy_id', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
