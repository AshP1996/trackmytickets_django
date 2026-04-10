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
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'department', 'is_active',
                  'is_onboarded', 'created_at', 'last_login']
        read_only_fields = ['id', 'created_at', 'last_login', 'is_active', 'is_onboarded']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'role', 'department', 'is_active', 'is_onboarded']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for users to update their own profile (limited fields)."""
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'department', 'is_onboarded', 'created_at']
        read_only_fields = ['id', 'email', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'role', 'department']

    def validate_email(self, value):
        """Validate email uniqueness within the tenant database."""
        request = self.context.get('request')
        org = getattr(request, 'organization', None) if request else None
        qs = User.objects.filter(email__iexact=value)
        if org:
            from apps.core.routers import get_current_db_alias
            if get_current_db_alias() == 'default':
                qs = qs.filter(organization_id=org.id)
        if qs.exists():
            raise serializers.ValidationError('A user with this email already exists in this organization.')
        return value

    def validate_role(self, value):
        """Ensure role is valid."""
        valid_roles = ('admin', 'manager', 'department_head', 'agent')
        if value not in valid_roles:
            raise serializers.ValidationError(f'Role must be one of: {", ".join(valid_roles)}')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        request = self.context.get('request')
        organization = getattr(request, 'organization', None)

        from .services import UserProvisionService
        user, _ = UserProvisionService.create_user(
            email=validated_data.pop('email'),
            password=password,
            organization=organization,
            **validated_data
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters.')
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)


class DepartmentSerializer(serializers.ModelSerializer):
    default_assignee_name = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'default_assignee', 'default_assignee_name',
                  'sla_policy_id', 'is_active', 'ticket_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_default_assignee_name(self, obj):
        return obj.default_assignee.full_name if obj.default_assignee else None

    def get_ticket_count(self, obj):
        if hasattr(obj, 'ticket_count_annotated'):
            return obj.ticket_count_annotated
        return obj.tickets.count()
