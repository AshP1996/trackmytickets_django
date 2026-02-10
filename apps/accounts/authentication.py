from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from apps.accounts.models import PlatformAdmin, User

class PlatformJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        # Check if token has the platform admin claim
        if validated_token.get('is_platform_admin'):
            try:
                user_id = validated_token.get('user_id')
                if not user_id:
                    raise InvalidToken('Token contained no recognizable user identification')
                
                user = PlatformAdmin.objects.get(id=user_id)
            except PlatformAdmin.DoesNotExist:
                raise AuthenticationFailed('User not found', code='user_not_found')
            except KeyError:
                raise InvalidToken('Token contained no recognizable user identification')

            if not user.is_active:
                raise AuthenticationFailed('User is inactive', code='user_inactive')

            return user
        
        # For Tenant Users - explicitly get user by ID from token
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                # Fallback to default behavior
                return super().get_user(validated_token)
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found', code='user_not_found')
            
            if not user.is_active:
                raise AuthenticationFailed('User is inactive', code='user_inactive')
            
            return user
        except (KeyError, TypeError):
            # Fallback to default JWT behavior if user_id not in token
            return super().get_user(validated_token)
