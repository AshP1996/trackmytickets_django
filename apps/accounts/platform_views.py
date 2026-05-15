import logging
from datetime import timedelta
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from .models import PlatformAdmin, Organization
from apps.core.models import Enquiry
from apps.tickets.models import Ticket
from apps.accounts.models import User
from django.db.models import Count, Q
from django.conf import settings
from apps.core.permissions import IsPlatformAdmin

logger = logging.getLogger('apps')

class PlatformLoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=400)

        admin = PlatformAdmin.objects.filter(email=email).first()

        if not admin:
            # Avoid timing attacks/enumeration
            return Response({'error': 'Invalid credentials'}, status=401)
        
        if not admin.check_password(password):
             return Response({'error': 'Invalid credentials'}, status=401)
             
        if not admin.is_active:
             return Response({'error': 'Account disabled'}, status=403)

        # Build JWT access token for PlatformAdmin WITHOUT touching the OutstandingToken table.
        # RefreshToken.for_user() stores a row in outstandingtoken with user FK → Django User only.
        # PlatformAdmin is a separate AbstractBaseUser; passing it causes a ValueError.
        # Solution: Use AccessToken() directly (no DB write) and inject custom claims.
        access_token = AccessToken()
        access_token['user_id'] = admin.id
        access_token['email'] = admin.email
        access_token['is_platform_admin'] = True
        # Expire according to configured lifetime
        access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(hours=1))
        access_token.set_exp(lifetime=access_token_lifetime)

        return Response({
            'access_token': str(access_token),
            'user': {
                'id': admin.id,
                'email': admin.email,
                'role': 'platform_admin'
            }
        })

class PlatformMeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        return Response({
            'id': request.user.id,
            'email': request.user.email,
            'role': 'platform_admin'
        })

class PlatformOrganizationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    
    
    def get(self, request):
        """List all organizations"""
        try:
            orgs = Organization.objects.all().order_by('-created_at')
        except Exception as e:
            logger.exception("PlatformOrganizationsView: failed to list organizations")
            return Response({'error': 'Failed to load organizations', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Pre-fetch active connectivity for efficiency
        from apps.core.models import ExternalDataSource
        from apps.core.connectors import get_connector
        from apps.tickets.models import Ticket, Project
        
        try:
            external_ds_map = {
                ds.organization_id: ds 
                for ds in ExternalDataSource.objects.filter(is_active=True, connection_status='connected')
            }
        except Exception as e:
            logger.warning(f"PlatformOrganizationsView: external_ds_map failed: {e}")
            external_ds_map = {}
        
        # Apply Pagination
        from apps.tickets.views import StandardPagination
        paginator = StandardPagination()
        try:
            result_page = paginator.paginate_queryset(orgs, request)
        except Exception as e:
            logger.exception("PlatformOrganizationsView: pagination failed")
            return Response({'error': 'Failed to paginate', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if result_page is None:
            result_page = []
        
        data = []
        for org in result_page:
            try:
                user_count = org.global_users.count()
            except Exception as e:
                logger.warning(f"Error counting global_users for org {org.id}: {e}")
                user_count = 0
            ticket_count = 0
            project_count = 0
            
            ds = external_ds_map.get(org.id)
            if ds:
                try:
                    # Connect to External DB
                    password = ds.get_password()
                    config = {
                        'host': ds.host,
                        'port': ds.port,
                        'database': ds.database,
                        'username': ds.username,
                        'password': password
                    }
                    connector = get_connector(ds.type, config)
                    
                    # Fetch counts
                    # Fallback to 0 if table doesn't exist (e.g. migration pending)
                    try:
                        t_res = connector.fetch_data("SELECT COUNT(*) as count FROM tickets")
                        if t_res: ticket_count = t_res[0].get('count', 0)
                        
                        p_res = connector.fetch_data("SELECT COUNT(*) as count FROM projects")
                        if p_res: project_count = p_res[0].get('count', 0)
                    except Exception as e:
                        logger.warning(f"Error fetching stats for Org {org.id} from External DB: {e}")
                        
                except Exception as e:
                    logger.warning(f"Error connecting to Org {org.id} External DB: {e}")
            else:
                # Default DB (tenant data may live in default when not BYODB)
                try:
                    ticket_count = Ticket.objects.filter(organization_id=org.id).count()
                    project_count = Project.objects.filter(organization_id=org.id).count()
                except Exception as e:
                    logger.warning(f"Error counting tickets/projects for org {org.id} on default DB: {e}")
                    ticket_count = 0
                    project_count = 0
            
            data.append({
                'id': org.id,
                'name': org.name,
                'subdomain': org.subdomain,
                'email': org.email,
                'is_active': org.is_active,
                'plan': org.plan,
                'created_at': org.created_at.isoformat(),
                'has_external_db': bool(ds),
                'stats': {
                    'users': user_count,
                    'tickets': ticket_count,
                    'projects': project_count
                }
            })
            
        return paginator.get_paginated_response(data)
    
    def post(self, request):
        """Create a new organization"""
        from .models import User
        
        name = request.data.get('name')
        subdomain = request.data.get('subdomain')
        email = request.data.get('email')
        admin_email = request.data.get('admin_email')
        admin_name = request.data.get('admin_name')
        admin_password = request.data.get('admin_password')
        plan = request.data.get('plan', 'free')
        cluster_id = request.data.get('cluster_id')
        
        if not all([name, subdomain, email, admin_email, admin_name, admin_password]):
            return Response({'error': 'All fields are required'}, status=400)
        
        # Check if subdomain already exists
        if Organization.objects.filter(subdomain=subdomain).exists():
            return Response({'error': 'Subdomain already exists'}, status=400)
        
        # Create organization
        org = Organization.objects.create(
            name=name,
            subdomain=subdomain,
            email=email,
            plan=plan,
            cluster_id=cluster_id if cluster_id else None,
            is_active=True
        )
        
        # New org has no tenant DB yet; user is created in default DB with organization_id.
        from apps.core.routers import set_current_db_alias, reset_current_db_alias
        set_current_db_alias('default')
        try:
            from apps.accounts.services import UserProvisionService
            admin_user, global_user = UserProvisionService.create_user(
                email=admin_email,
                password=admin_password,
                organization=org,
                full_name=admin_name,
                role='admin',
                is_active=True,
                organization_id=org.id,
            )
        finally:
            reset_current_db_alias()
        
        # ✉️ Send org creation email with credentials
        try:
            from apps.notifications.email_service import send_org_created_email
            superadmin_email = getattr(request.user, 'email', None)
            send_org_created_email(
                org, admin_email, admin_name, admin_password,
                notify_superadmin_email=superadmin_email
            )
        except Exception as e:
            logger.warning(f'Failed to send org creation email: {e}')
        
        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'admin_user': {
                'email': admin_user.email,
                'full_name': admin_user.full_name,
                # Password sent via email only — never in API response
            },
            'access_urls': {
                'login': f'/{org.subdomain}/login',
                'dashboard': f'/{org.subdomain}/dashboard',
            },
            'message': 'Organization created successfully'
        }, status=201)

class PublicOrganizationRegisterView(views.APIView):
    """
    Public endpoint for unauthenticated users to create an organization.
    Similar to PlatformOrganizationsView.post but without IsPlatformAdmin requirement.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # SEC-2: Rate limit public registration (5 per IP per hour)
        from django.core.cache import cache
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
        rate_key = f'register_rate:{client_ip}'
        attempts = cache.get(rate_key, 0)
        if attempts >= 5:
            return Response({
                'error': 'Too many registration attempts. Please try again later.'
            }, status=429)
        cache.set(rate_key, attempts + 1, timeout=3600)  # 1 hour window

        name = request.data.get('name')
        subdomain = request.data.get('subdomain')
        email = request.data.get('email')
        admin_email = request.data.get('admin_email')
        admin_name = request.data.get('admin_name')
        admin_password = request.data.get('admin_password')
        plan = request.data.get('plan', 'free')
        
        if not all([name, subdomain, email, admin_email, admin_name, admin_password]):
            return Response({'error': 'All fields are required'}, status=400)
        
        # Check if subdomain already exists
        if Organization.objects.filter(subdomain=subdomain).exists():
            return Response({'error': 'Subdomain already exists'}, status=400)
        
        # Check if email is already used for another organization globally
        if Organization.objects.filter(email=email).exists():
            return Response({'error': 'Organization with this email already exists'}, status=400)
            
        # Create organization
        org = Organization.objects.create(
            name=name,
            subdomain=subdomain,
            email=email,
            plan=plan,
            is_active=True
        )
        
        # New org has no tenant DB yet; user is created in default DB with organization_id.
        from apps.core.routers import set_current_db_alias, reset_current_db_alias
        set_current_db_alias('default')
        try:
            from apps.accounts.services import UserProvisionService
            admin_user, global_user = UserProvisionService.create_user(
                email=admin_email,
                password=admin_password,
                organization=org,
                full_name=admin_name,
                role='admin',
                is_active=True,
                organization_id=org.id,
            )
        except Exception as e:
            logger.error(f'Failed to create admin user during public registration: {e}')
            # Delete the org if user creation fails to prevent orphaned orgs
            org.delete()
            return Response({'error': 'Failed to create admin user. Please ensure the email is not already in use globally.'}, status=400)
        finally:
            reset_current_db_alias()
        
        # ✉️ Send org creation email with credentials
        try:
            from apps.notifications.email_service import send_org_created_email
            # No superadmin to notify for public registrations, just send to the new admin
            send_org_created_email(
                org, admin_email, admin_name, admin_password,
                notify_superadmin_email=None
            )
        except Exception as e:
            logger.warning(f'Failed to send org creation email during public registration: {e}')
        
        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'admin_user': {
                'email': admin_user.email,
                'full_name': admin_user.full_name,
                # Password sent via email only — never in API response
            },
            'access_urls': {
                'login': f'/{org.subdomain}/login',
                'dashboard': f'/{org.subdomain}/dashboard',
            },
            'message': 'Organization registered successfully'
        }, status=201)


class PlatformOrganizationDetailView(views.APIView):
    """GET, PUT, DELETE a single organization by primary key."""
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def _get_org(self, pk):
        try:
            return Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return None

    def get(self, request, pk):
        org = self._get_org(pk)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)

        from apps.accounts.models import User as TenantUser
        from apps.core.models import ExternalDataSource
        from apps.tickets.models import Ticket, Project
        from apps.core.routers import set_current_db_alias, reset_current_db_alias

        # Use tenant DB for BYODB orgs so users/tickets/projects are from the same DB
        db_alias = f'tenant_{org.id}'
        use_tenant_db = db_alias in settings.DATABASES
        if not use_tenant_db:
            ds = ExternalDataSource.objects.filter(
                organization=org, is_active=True, connection_status='connected'
            ).first()
            if ds:
                from apps.core.middleware.tenant import TenantMiddleware
                TenantMiddleware._register_tenant_db(db_alias, ds)
                use_tenant_db = db_alias in settings.DATABASES

        if use_tenant_db:
            set_current_db_alias(db_alias)
            try:
                users = TenantUser.objects.all()
                tickets = Ticket.objects.all()
                projects = Project.objects.all()
            finally:
                reset_current_db_alias()
        else:
            users = TenantUser.objects.filter(organization_id=org.id)
            tickets = Ticket.objects.filter(organization_id=org.id)
            projects = Project.objects.filter(organization_id=org.id)

        admin_user = users.filter(role='admin').first()

        stats = {
            'users': {
                'total': users.count(),
                'active': users.filter(is_active=True).count(),
                'by_role': {
                    role: users.filter(role=role).count()
                    for role in ['admin', 'manager', 'agent']
                }
            },
            'tickets': {
                'total': tickets.count(),
                'by_status': {
                    s: tickets.filter(status=s).count()
                    for s in ['open', 'in_progress', 'waiting', 'resolved', 'closed']
                }
            },
            'projects': {
                'total': projects.count(),
                'active': projects.filter(is_active=True).count(),
            }
        }

        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'email': org.email,
            'is_active': org.is_active,
            'plan': org.plan,
            'cluster_id': getattr(org, 'cluster_id', None),
            'created_at': org.created_at.isoformat(),
            'admin_user': {
                'email': admin_user.email if admin_user else None,
                'full_name': admin_user.full_name if admin_user else None,
                'role': admin_user.role if admin_user else None,
                'is_active': admin_user.is_active if admin_user else None,
            },
            'detailed_stats': stats,
            'access_urls': {
                'login': f'/{org.subdomain}/login',
                'dashboard': f'/{org.subdomain}/dashboard',
            }
        })

    def put(self, request, pk):
        org = self._get_org(pk)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)

        allowed_fields = ['name', 'email', 'plan', 'cluster_id', 'is_active']
        updated = []
        for field in allowed_fields:
            if field in request.data:
                val = request.data[field]
                # Validate subdomain uniqueness if updating subdomain (not exposed here but guard anyway)
                setattr(org, field, val)
                updated.append(field)

        if not updated:
            return Response({'error': 'No valid fields provided'}, status=400)

        org.save(update_fields=updated)
        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'email': org.email,
            'is_active': org.is_active,
            'plan': org.plan,
            'message': 'Organization updated successfully'
        })

    def delete(self, request, pk):
        org = self._get_org(pk)
        if not org:
            return Response({'error': 'Organization not found'}, status=404)

        org_name = org.name
        from apps.accounts.models import User as TenantUser, GlobalUser
        GlobalUser.objects.filter(organization=org).delete()
        TenantUser.objects.filter(organization_id=org.id).delete()
        org.delete()
        return Response({'message': f'Organization "{org_name}" deleted successfully'})


class PlatformOrganizationSuspendView(views.APIView):
    """PUT /organizations/{id}/suspend  →  suspend (is_active=False) or activate (is_active=True)."""
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def put(self, request, pk):
        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)

        suspend = request.data.get('suspend', True)
        org.is_active = not suspend
        org.save(update_fields=['is_active'])
        action = 'suspended' if suspend else 'activated'
        return Response({'message': f'Organization {action} successfully', 'is_active': org.is_active})


class PlatformEnquiryDetailView(views.APIView):
    """GET /enquiries/{id}  →  fetch a single enquiry by pk."""
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request, pk):
        try:
            enquiry = Enquiry.objects.get(pk=pk)
        except Enquiry.DoesNotExist:
            return Response({'error': 'Enquiry not found'}, status=404)

        return Response({
            'id': enquiry.id,
            'name': enquiry.name,
            'email': enquiry.email,
            'company': enquiry.company,
            'phone': enquiry.phone,
            'message': enquiry.message,
            'is_read': enquiry.is_read,
            'created_at': enquiry.created_at.isoformat()
        })


class PlatformStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        from apps.accounts.models import GlobalUser
        from apps.core.models import ExternalDataSource
        
        try:
            org_count = Organization.objects.count()
            active_org_count = Organization.objects.filter(is_active=True).count()
        except Exception as e:
            logger.warning(f"PlatformStatsView: org count failed: {e}")
            org_count = 0
            active_org_count = 0
        
        try:
            user_count = GlobalUser.objects.count()
        except Exception as e:
            logger.warning(f"PlatformStatsView: user count failed: {e}")
            user_count = 0
        
        try:
            enquiry_count = Enquiry.objects.count()
            unread_enquiry_count = Enquiry.objects.filter(is_read=False).count()
        except Exception as e:
            logger.warning(f"PlatformStatsView: enquiry count failed: {e}")
            enquiry_count = 0
            unread_enquiry_count = 0
        
        # Ticket stats (Tenant model - aggregated from all sources)
        from apps.core.connectors import get_connector
        
        # 1. Get IDs of organizations with active external data sources
        try:
            external_ds = list(ExternalDataSource.objects.filter(is_active=True, connection_status='connected'))
            external_org_ids = [ds.organization_id for ds in external_ds]
        except Exception as e:
            logger.warning(f"PlatformStatsView: failed to load external data sources: {e}")
            external_ds = []
            external_org_ids = []
        
        # 2. Count tickets in Default DB (for orgs NOT in external_org_ids)
        try:
            if external_org_ids:
                default_db_ticket_count = Ticket.objects.exclude(organization_id__in=external_org_ids).count()
            else:
                default_db_ticket_count = Ticket.objects.count()
        except Exception as e:
            logger.warning(f"PlatformStatsView: default DB ticket count failed: {e}")
            default_db_ticket_count = 0
        
        total_tickets = default_db_ticket_count
        
        # 3. Count tickets in External DBs
        for ds in external_ds:
            try:
                # Decrypt password
                password = ds.get_password()
                
                config = {
                    'host': ds.host,
                    'port': ds.port,
                    'database': ds.database,
                    'username': ds.username,
                    'password': password
                }
                
                connector = get_connector(ds.type, config)
                
                # Check if tickets table exists first? Or just try query
                # Different DBs might have different schemas if not managed by us.
                # Assuming standard schema for "Bring Your Own Database" feature implies we manage schema there too 
                # or user mapped it. 
                # If mapped, we should check SchemaMapping.
                # For this task, assuming standard table name 'tickets' or checking existence.
                
                # Simple count query
                # Note: This assumes the table is named 'tickets'.
                # In a real BYODB scenario, we might fallback to `connector.get_tables()` check.
                try:
                    results = connector.fetch_data("SELECT COUNT(*) as count FROM tickets")
                    if results:
                        # Result format depends on connector, usually list of dicts or tuples
                        # fetch_data returns list of dicts
                        count = results[0].get('count', 0)
                        total_tickets += count
                except Exception as e:
                    logger.warning(f"Error counting tickets for DS {ds.id}: {e}")
                    
            except Exception as e:
                logger.warning(f"Error connecting to DS {ds.id}: {e}")

        return Response({
            'organizations': {
                'total': org_count,
                'active': active_org_count
            },
            'users': {
                'total': user_count
            },
            'tickets': {
                'total': total_tickets
            },
            'enquiries': {
                'total': enquiry_count,
                'unread': unread_enquiry_count
            }
        })

class PlatformEnquiriesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        unread_only = request.query_params.get('unread_only') == 'true'
        
        query = Enquiry.objects.all().order_by('-created_at')
        if unread_only:
            query = query.filter(is_read=False)
            
        # Apply Pagination
        from apps.tickets.views import StandardPagination
        paginator = StandardPagination()
        result_page = paginator.paginate_queryset(query, request)
            
        data = [{
            'id': e.id,
            'name': e.name,
            'email': e.email,
            'company': e.company,
            'phone': e.phone,
            'message': e.message,
            'is_read': e.is_read,
            'created_at': e.created_at.isoformat()
        } for e in result_page]
        
        return paginator.get_paginated_response(data)

class PlatformEnquiryReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    def put(self, request, pk):
        try:
            enquiry = Enquiry.objects.get(pk=pk)
            enquiry.is_read = True
            enquiry.save()
            return Response({'message': 'Enquiry marked as read'})
        except Enquiry.DoesNotExist:
            return Response({'error': 'Enquiry not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class PublicEnquiryView(views.APIView):
    """Public endpoint for landing page enquiry submissions. CSRF exempt for unauthenticated POST."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        company = request.data.get('company', '').strip()
        phone = request.data.get('phone', '').strip()
        message = request.data.get('message', '').strip()

        if not name or not email or not message:
            return Response({'error': 'Name, email, and message are required'}, status=400)

        # Create enquiry
        enquiry = Enquiry.objects.create(
            name=name,
            email=email,
            company=company if company else None,
            phone=phone if phone else None,
            message=message,
            is_read=False
        )

        return Response({
            'message': 'Thank you for your enquiry! We will get back to you soon.',
            'id': enquiry.id
        }, status=201)


class PlatformForgotPasswordView(views.APIView):
    """
    Send OTP to platform admin's email for password reset
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .email_utils import create_reset_otp, send_otp_email
        
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required'}, status=400)
        
        # Find platform admin
        try:
            admin = PlatformAdmin.objects.get(email=email)
        except PlatformAdmin.DoesNotExist:
            # Don't reveal if admin exists or not (security best practice)
            return Response({
                'message': 'If an account with this email exists, an OTP has been sent.'
            }, status=200)
        
        # Generate and save OTP
        otp = create_reset_otp(admin)
        
        # Send OTP email
        email_sent = send_otp_email(admin.email, otp, user_type='platform_admin')
        
        if email_sent:
            return Response({
                'message': 'OTP has been sent to your email address. It will expire in 15 minutes.'
            }, status=200)
        else:
            return Response({
                'error': 'Failed to send email. Please try again later.'
            }, status=500)


class PlatformResetPasswordView(views.APIView):
    """
    Reset platform admin password using OTP verification.
    AUDIT-FIX SEC-4: Brute-force guard on OTP verification.
    AUDIT-FIX SEC-5: Password strength validation.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .email_utils import verify_reset_otp, clear_reset_otp
        from django.core.cache import cache

        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not email or not otp or not new_password:
            return Response({
                'error': 'Email, OTP, and new password are required'
            }, status=400)

        # SEC-5: Password strength validation
        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=400)

        # Find platform admin
        try:
            admin = PlatformAdmin.objects.get(email=email)
        except PlatformAdmin.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # SEC-4: Brute-force guard on OTP verification
        otp_attempts_key = f'platform_otp_attempts:{admin.id}'
        attempts = cache.get(otp_attempts_key, 0)
        MAX_OTP_ATTEMPTS = 5
        if attempts >= MAX_OTP_ATTEMPTS:
            logger.warning('platform_otp_brute_force_blocked admin_id=%s', admin.id)
            return Response({
                'error': 'Too many failed attempts. Please request a new OTP.'
            }, status=429)

        # Verify OTP
        if not verify_reset_otp(admin, otp):
            cache.set(otp_attempts_key, attempts + 1, timeout=900)
            return Response({
                'error': 'Invalid or expired OTP'
            }, status=401)

        # Success — clear attempt counter and reset password
        cache.delete(otp_attempts_key)
        admin.set_password(new_password)
        clear_reset_otp(admin)

        return Response({
            'message': 'Password has been reset successfully'
        }, status=200)
