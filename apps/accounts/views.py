import logging

from rest_framework import generics, status, views, viewsets, permissions, filters
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from .models import User, Organization, Department
from .serializers import (
    UserSerializer, UserUpdateSerializer, RegisterSerializer, LoginSerializer,
    DepartmentSerializer, ChangePasswordSerializer, UserProfileSerializer,
)
from apps.core.permissions import IsOrgAdmin, IsOrgAdminOrManager, IsOrgMember
from apps.tickets.models import Ticket

logger = logging.getLogger('apps')


# ============================================================================
# AUTH VIEWS
# ============================================================================
class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            if not hasattr(request, 'organization') or not request.organization:
                return Response({'error': 'Organization not found'}, status=404)
            
            organization = request.organization
            # ContextVar set by TenantMiddleware → User query hits tenant DB
            # No organization filter needed: tenant DB = one org
            user = User.objects.filter(email__iexact=email).first()
            
            if user:
                if not user.check_password(password):
                    # Use a generic message to avoid email enumeration
                    return Response({'message': 'Invalid credentials'}, status=401)
                
                if not user.is_active:
                    return Response({'message': 'Account is inactive'}, status=403)
                
                from django.utils import timezone
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                from .services import UserProvisionService
                global_user = UserProvisionService.sync_global_user(user, organization)
                global_user.last_login = timezone.now()
                global_user.save(update_fields=['last_login'])

                refresh = RefreshToken.for_user(user)
                # SECURITY FIX C2: Bind token to org so downstream views can verify
                # the token was minted for THIS organization and was not replayed
                # from a different org's login endpoint.
                refresh['org_id'] = organization.id
                refresh['org_subdomain'] = organization.subdomain  # URL-side verification key
                # HYBRID ARCHITECTURE: Inject synchronized GlobalUser ID
                refresh['global_user_id'] = str(global_user.id)
                # Ensure the user_id claim explicitly points to the tenant DB ID
                refresh['user_id'] = user.id

                return Response({
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'user': UserSerializer(user).data,
                    'organization': {
                        'id': organization.id,
                        'name': organization.name,
                        'subdomain': organization.subdomain
                    }
                })
            
            return Response({'message': 'Invalid credentials'}, status=401)
        return Response(serializer.errors, status=400)


class RegisterView(generics.CreateAPIView):
    """Register a new user in the organization. Only org admins can do this."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin, IsOrgMember]

    def create(self, request, *args, **kwargs):
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization context missing'}, status=400)
        
        # Check user limit
        org = request.organization
        limits = org.get_limits()
        max_users = limits.get('max_users', 30)
        current_users = User.objects.count()
        if max_users > 0 and current_users >= max_users:
            return Response({
                'error': f'User limit reached ({max_users}). Upgrade your plan to add more users.'
            }, status=403)
        
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(views.APIView):
    """
    AUDIT-FIX HIGH-3: Blacklist the refresh token so it cannot be used to
    mint new access tokens after the user logs out.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'refresh_token is required'}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response({'error': str(e)}, status=400)
        logger.info('logout user_id=%s', request.user.id)
        return Response({'message': 'Logged out successfully'}, status=200)


class UserListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            from .serializers import RegisterSerializer
            return RegisterSerializer
        return UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]
    filter_backends = [filters.SearchFilter]

    def get_permissions(self):
        base = [permissions.IsAuthenticated(), IsOrgMember()]
        if self.request.method == 'POST':
            return base + [IsOrgAdmin()]
        return base + [IsOrgAdminOrManager()]

    search_fields = ['full_name', 'email', 'role']

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return User.objects.none()

        from apps.core.routers import get_current_db_alias
        if get_current_db_alias() == 'default':
            queryset = User.objects.filter(organization_id=self.request.organization.id)
        else:
            queryset = User.objects.all()

        # Filters
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department=department)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(email__icontains=search)
            )
        
        return queryset.order_by('full_name')

    def create(self, request, *args, **kwargs):
        logger.info('UserListView.create: request data keys=%s', list(request.data.keys()))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = getattr(request, 'organization', None)
        if not org:
            logger.warning('UserListView.create: organization scope missing')
            return Response({'error': 'Organization scope missing'}, status=400)

        email = serializer.validated_data.get('email', '')
        logger.info('UserListView.create: creating user email=%s org_id=%s', email, org.id if org else None)
        try:
            from .services import UserProvisionService
            dept = serializer.validated_data.get('department')
            if dept is not None and isinstance(dept, str):
                dept = dept.strip() or None
            user, global_user = UserProvisionService.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                organization=org,
                full_name=serializer.validated_data.get('full_name', ''),
                role=serializer.validated_data.get('role', 'agent'),
                department=dept,
                is_active=True
            )
        except ValueError as e:
            logger.warning('UserListView.create: ValueError %s', e)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('UserListView.create: unexpected error creating user')
            return Response(
                {'detail': getattr(e, 'message', str(e)) or 'Failed to create user.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        output_serializer = UserSerializer(user)
        logger.info('UserListView.create: user created id=%s', user.id)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_serializer_class(self):
        """
        AUDIT-FIX CRIT-4: Serve different serializers based on caller's role.
        Non-admins get a serializer WITHOUT the 'role' field, blocking privilege
        escalation. Admins get the full UserUpdateSerializer.
        """
        from apps.accounts.serializers import UserUpdateSerializer, UserProfileSerializer
        if self.request.user.role == 'admin':
            return UserUpdateSerializer  # includes role, is_active, department
        return UserProfileSerializer     # only full_name, department, is_onboarded

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return User.objects.none()

        org_qs = User.objects.all()  # Tenant DB has only this org's users

        # AUDIT-FIX HIGH-8: IDOR guard.
        # Non-admins (agents, managers) can only READ all users in their org,
        # but can only UPDATE/DELETE their OWN record.
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            if self.request.user.role not in ('admin',):
                return org_qs.filter(id=self.request.user.id)

        return org_qs

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Prevent self-deletion
        if instance.id == self.request.user.id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You cannot delete your own account.')
        # Soft delete
        instance.is_active = False
        instance.save(update_fields=['is_active'])


# ============================================================================
# USER ROLES VIEW
# ============================================================================
class UserRolesView(views.APIView):
    """Manage scoped roles for a user.
    GET    /users/{pk}/roles/            → list org role + scoped roles
    POST   /users/{pk}/roles/assign/     → assign a scoped role
    DELETE /users/{pk}/roles/{role_id}/  → remove a scoped role
    """
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def _get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk, **kwargs):
        user = self._get_user(pk)
        if not user:
            return Response({'error': 'User not found'}, status=404)

        from .models import UserRole
        scoped_roles = UserRole.objects.filter(user=user)
        scoped_data = []
        for sr in scoped_roles:
            scope_name = None
            if sr.scope_type == 'project' and sr.scope_id:
                try:
                    from apps.tickets.models import Project
                    scope_name = Project.objects.get(pk=sr.scope_id).name
                except Exception:
                    scope_name = f'Project #{sr.scope_id}'
            elif sr.scope_type == 'department' and sr.scope_id:
                try:
                    scope_name = Department.objects.get(pk=sr.scope_id).name
                except Exception:
                    scope_name = f'Department #{sr.scope_id}'
            elif sr.scope_type == 'organization':
                scope_name = getattr(request, 'organization', None)
                scope_name = scope_name.name if scope_name else 'Organization'

            scoped_data.append({
                'id': sr.id,
                'role': sr.role,
                'scope_type': sr.scope_type,
                'scope_id': sr.scope_id,
                'scope_name': scope_name,
            })

        return Response({
            'organization_role': user.role,
            'scoped_roles': scoped_data,
        })

    def post(self, request, pk, **kwargs):
        """Assign a new scoped role."""
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return Response({'error': 'Only admins can assign roles'}, status=403)

        user = self._get_user(pk)
        if not user:
            return Response({'error': 'User not found'}, status=404)

        from .models import UserRole
        role = request.data.get('role')
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')

        if not role or not scope_type:
            return Response({'error': 'role and scope_type are required'}, status=400)

        if scope_type == 'organization':
            scope_id = None

        try:
            sr, created = UserRole.objects.get_or_create(
                user=user, scope_type=scope_type, scope_id=scope_id,
                defaults={'role': role}
            )
            if not created:
                sr.role = role
                sr.save(update_fields=['role'])
            return Response({
                'id': sr.id,
                'role': sr.role,
                'scope_type': sr.scope_type,
                'scope_id': sr.scope_id,
                'message': 'Role assigned successfully',
            }, status=201 if created else 200)
        except Exception as e:
            logger.exception('UserRolesView.post: error assigning role')
            return Response({'error': str(e)}, status=500)

    def delete(self, request, pk, role_id=None, **kwargs):
        """Remove a scoped role."""
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return Response({'error': 'Only admins can remove roles'}, status=403)

        if not role_id:
            return Response({'error': 'role_id required'}, status=400)

        from .models import UserRole
        try:
            sr = UserRole.objects.get(pk=role_id, user_id=pk)
            sr.delete()
            return Response({'message': 'Role removed successfully'})
        except UserRole.DoesNotExist:
            return Response({'error': 'Role not found'}, status=404)


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================
class ChangePasswordView(views.APIView):
    """Allows authenticated users to change their own password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Current password is incorrect'}, status=400)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Generate new tokens so user doesn't get logged out
        refresh = RefreshToken.for_user(user)
        if hasattr(request, 'organization') and request.organization:
            refresh['org_id'] = request.organization.id
        
        return Response({
            'message': 'Password changed successfully',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        })


class UserProfileView(views.APIView):
    """Allows users to view and update their own profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_name=None):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request, company_name=None):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ForgotPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        from .email_utils import create_reset_otp, send_otp_email
        
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=400)
        
        try:
            organization = Organization.objects.get(subdomain=company_name)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)
        
        try:
            user = User.objects.get(email=email)  # Tenant DB scoped
        except User.DoesNotExist:
            return Response({
                'message': 'If an account with this email exists, an OTP has been sent.'
            }, status=200)
        
        otp = create_reset_otp(user)
        email_sent = send_otp_email(user.email, otp, user_type='user')
        
        if email_sent:
            return Response({
                'message': 'OTP has been sent to your email address. It will expire in 15 minutes.'
            })
        else:
            logger.error(f"Failed to send OTP email to {email}")
            return Response({
                'error': 'Failed to send email. Please try again later.'
            }, status=500)


class ResetPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        from .email_utils import verify_reset_otp, clear_reset_otp
        from django.core.cache import cache

        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not email or not otp or not new_password:
            return Response({
                'error': 'Email, OTP, and new password are required'
            }, status=400)

        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=400)

        try:
            organization = Organization.objects.get(subdomain=company_name)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)

        try:
            user = User.objects.get(email=email)  # Tenant DB scoped
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # AUDIT-FIX HIGH-7: Brute-force guard on OTP verification.
        # A 6-digit OTP without this can be brute-forced in <15 minutes
        # even with IP rate limiting (attackers can use distributed IPs).
        otp_attempts_key = f'otp_attempts:{user.id}'
        attempts = cache.get(otp_attempts_key, 0)
        MAX_OTP_ATTEMPTS = 5
        if attempts >= MAX_OTP_ATTEMPTS:
            logger.warning('otp_brute_force_blocked user_id=%s', user.id)
            return Response({
                'error': 'Too many failed attempts. Please request a new OTP.'
            }, status=429)

        if not verify_reset_otp(user, otp):
            # Increment attempt counter; expires with the OTP (15 minutes)
            cache.set(otp_attempts_key, attempts + 1, timeout=900)
            return Response({'error': 'Invalid or expired OTP'}, status=401)

        # Success — clear attempt counter and reset password
        cache.delete(otp_attempts_key)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        clear_reset_otp(user)

        return Response({'message': 'Password has been reset successfully'})


# ============================================================================
# DEPARTMENT VIEWS
# ============================================================================
class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return Department.objects.none()
        return Department.objects.all().order_by('name')  # Tenant DB scoped

    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        return super().get_permissions()


# ============================================================================
# DEPARTMENT HEAD VIEWS
# ============================================================================
class DepartmentHeadStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)
        
        user = request.user
        if not user.department:
            return Response({'error': 'User has no department assigned'}, status=400)
            
        try:
            dept = Department.objects.get(name=user.department)
        except Department.DoesNotExist:
            return Response({'error': f'Department "{user.department}" not found in organization'}, status=404)

        # N+1 FIX: Replace 7 separate COUNT queries with a single annotated aggregate.
        # Original: tickets.count(), tickets.filter(status='open').count() × 6 = 7 queries.
        # Fixed: one annotated aggregate → one round-trip. O(7) → O(1) DB calls.
        from django.db.models import Count, Q as StatusQ
        ticket_qs = Ticket.objects.filter(department=dept)  # Tenant DB scoped
        agg = ticket_qs.aggregate(
            total=Count('id'),
            open=Count('id', filter=StatusQ(status='open')),
            in_progress=Count('id', filter=StatusQ(status__in=['in_progress', 'inprocess'])),
            reopen=Count('id', filter=StatusQ(status__in=['reopen', 'reopened'])),
            resolved=Count('id', filter=StatusQ(status='resolved')),
            closed=Count('id', filter=StatusQ(status='closed')),
            unassigned=Count('id', filter=StatusQ(assigned_to__isnull=True)),
        )
        stats = {
            'total':       agg['total'],
            'open':        agg['open'],
            'in_progress': agg['in_progress'],
            'reopen':      agg['reopen'],
            'resolved':    agg['resolved'],
            'closed':      agg['closed'],
            'unassigned':  agg['unassigned'],
        }

        # N+1 FIX: Per-employee stats also aggregated in a single grouped query.
        # Original: for emp in employees: emp_tickets.count() × 4 statuses = 4n queries.
        # Fixed: one .values('assigned_to').annotate(...) → one round-trip. O(4n) → O(1).
        emp_agg = (
            ticket_qs
            .filter(assigned_to__isnull=False)
            .values('assigned_to__id', 'assigned_to__full_name')
            .annotate(
                assigned=Count('id'),
                in_progress=Count('id', filter=StatusQ(status__in=['in_progress', 'inprocess'])),
                resolved=Count('id', filter=StatusQ(status='resolved')),
                closed=Count('id', filter=StatusQ(status='closed')),
            )
        )
        employee_performance = [
            {
                'employee': {
                    'id': row['assigned_to__id'],
                    'full_name': row['assigned_to__full_name'],
                },
                'assigned':    row['assigned'],
                'in_progress': row['in_progress'],
                'resolved':    row['resolved'],
                'closed':      row['closed'],
            }
            for row in emp_agg
        ]

        return Response({
            'department_stats': stats,
            'employee_performance': employee_performance
        })


class DepartmentHeadTicketsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)
             
        user = request.user
        if not user.department:
            return Response({'error': 'User has no department assigned'}, status=400)
            
        try:
            dept = Department.objects.get(name=user.department)
        except Department.DoesNotExist:
            return Response({'error': f'Department "{user.department}" not found'}, status=404)
            
        tickets = Ticket.objects.filter(
            department=dept
        ).select_related('assigned_to').order_by('-created_at')
        
        data = []
        for t in tickets:
            data.append({
                'id': t.id,
                'ticket_id': t.ticket_id,
                'subject': t.subject,
                'status': t.status,
                'priority': t.priority,
                'created_at': t.created_at,
                'updated_at': t.updated_at,
                'assigned_to': t.assigned_to.id if t.assigned_to else None,
                'assigned_to_name': t.assigned_to.full_name if t.assigned_to else None,
            })
            
        return Response({'tickets': data})


class DepartmentHeadEmployeesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return User.objects.none()
            
        user = self.request.user
        if not user.department:
            return User.objects.none()
            
        return User.objects.filter(
            department=user.department
        ).order_by('full_name')


# ============================================================================
# ORGANIZATION SETTINGS VIEW
# ============================================================================
class OrganizationSettingsView(views.APIView):
    """Manage organization settings. Only admins can update."""
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)
        
        org = request.organization
        import json
        settings_data = {}
        if org.settings:
            try:
                settings_data = json.loads(org.settings)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'email': org.email,
            'plan': org.plan,
            'settings': settings_data,
            'limits': org.get_limits(),
        })

    def patch(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)
        
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return Response({'error': 'Only admins can update organization settings'}, status=403)
        
        org = request.organization
        import json
        
        # Update allowed fields
        if 'name' in request.data:
            org.name = request.data['name']
        if 'email' in request.data:
            org.email = request.data['email']
        if 'settings' in request.data:
            org.settings = json.dumps(request.data['settings'])
        
        org.save()
        
        settings_data = {}
        if org.settings:
            try:
                settings_data = json.loads(org.settings)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return Response({
            'message': 'Settings updated successfully',
            'settings': settings_data,
        })


# ============================================================================
# ORGANIZATION SECRETS VIEW
# ============================================================================
class OrganizationSecretView(views.APIView):
    """CRUD for OrganizationSecret (env vars / secrets).
    GET  /api/{org}/auth/secrets/          → list (values masked)
    POST /api/{org}/auth/secrets/          → create
    GET  /api/{org}/auth/secrets/{id}/     → reveal decrypted value
    DELETE /api/{org}/auth/secrets/{id}/   → delete
    """
    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]

    def _get_fernet(self):
        """Return a Fernet cipher using the same key as ExternalDataSource."""
        import base64, os
        from cryptography.fernet import Fernet
        raw_key = os.environ.get('DB_CREDENTIALS_ENCRYPTION_KEY', '')
        if not raw_key:
            return None
        # Pad/truncate to 32 bytes, then base64url-encode for Fernet
        padded = raw_key.encode()[:32].ljust(32, b'\x00')
        fernet_key = base64.urlsafe_b64encode(padded)
        return Fernet(fernet_key)

    def _encrypt(self, value: str) -> str:
        f = self._get_fernet()
        if f:
            return f.encrypt(value.encode()).decode()
        # Fallback: store as-is (not recommended for prod)
        return value

    def _decrypt(self, encrypted: str) -> str:
        f = self._get_fernet()
        if f:
            try:
                return f.decrypt(encrypted.encode()).decode()
            except Exception:
                return '(decryption failed)'
        return encrypted

    def _mask(self, encrypted: str) -> str:
        """Show only last 4 chars of the raw encrypted string prefix."""
        try:
            raw = self._decrypt(encrypted)
            if len(raw) > 4:
                return '****' + raw[-4:]
            return '****'
        except Exception:
            return '****'

    def get(self, request, company_name, pk=None):
        from .models import OrganizationSecret
        org = getattr(request, 'organization', None)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)

        if pk:
            # Return decrypted value for a specific secret
            try:
                secret = OrganizationSecret.objects.get(pk=pk, organization=org)
            except OrganizationSecret.DoesNotExist:
                return Response({'error': 'Not found'}, status=404)
            return Response({
                'id': secret.id,
                'key': secret.key,
                'value': self._decrypt(secret.encrypted_value),
                'scope': secret.scope,
                'updated_at': secret.updated_at.isoformat(),
            })

        # List all secrets with masked values
        secrets = OrganizationSecret.objects.filter(organization=org).order_by('key')
        return Response([{
            'id': s.id,
            'key': s.key,
            'scope': s.scope,
            'value_masked': self._mask(s.encrypted_value),
            'updated_at': s.updated_at.isoformat(),
        } for s in secrets])

    def post(self, request, *args, **kwargs):
        from .models import OrganizationSecret
        org = getattr(request, 'organization', None)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)

        key = request.data.get('key', '').strip()
        value = request.data.get('value', '').strip()
        scope = request.data.get('scope', 'api').strip()

        if not key or not value:
            return Response({'error': 'key and value are required'}, status=400)

        encrypted = self._encrypt(value)
        secret, created = OrganizationSecret.objects.update_or_create(
            organization=org, key=key,
            defaults={'encrypted_value': encrypted, 'scope': scope}
        )
        return Response({
            'id': secret.id,
            'key': secret.key,
            'scope': secret.scope,
            'value_masked': self._mask(encrypted),
            'updated_at': secret.updated_at.isoformat(),
            'message': 'Secret saved successfully'
        }, status=201 if created else 200)

    def delete(self, request, company_name, pk=None):
        from .models import OrganizationSecret
        org = getattr(request, 'organization', None)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)
        if not pk:
            return Response({'error': 'pk required'}, status=400)
        try:
            secret = OrganizationSecret.objects.get(pk=pk, organization=org)
        except OrganizationSecret.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        secret.delete()
        return Response({'message': 'Secret deleted'})

