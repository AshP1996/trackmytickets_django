from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import PlatformAdmin, Organization
from apps.core.models import Enquiry
from apps.tickets.models import Ticket
from apps.accounts.models import User
from django.db.models import Count, Q
from django.contrib.auth import hashers

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

        refresh = RefreshToken.for_user(admin)
        
        # Add custom claim to distinguish platform admin
        refresh['is_platform_admin'] = True

        return Response({
            'refresh': str(refresh),
            'access_token': str(refresh.access_token),
            'user': {
                'id': admin.id,
                'email': admin.email,
                'role': 'platform_admin'
            }
        })

class PlatformMeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'id': request.user.id,
            'email': request.user.email,
            'role': 'platform_admin'
        })

class PlatformOrganizationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """List all organizations"""
        orgs = Organization.objects.all().order_by('-created_at')
        data = [{
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'email': org.email,
            'is_active': org.is_active,
            'plan': org.plan,
            'created_at': org.created_at.isoformat(),
        } for org in orgs]
        return Response({'organizations': data})
    
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
            is_active=True
        )
        
        # Create admin user
        admin_user = User.objects.create(
            email=admin_email,
            full_name=admin_name,
            organization=org,
            role='admin',
            is_active=True
        )
        admin_user.set_password(admin_password)
        admin_user.save()
        
        return Response({
            'id': org.id,
            'name': org.name,
            'subdomain': org.subdomain,
            'message': 'Organization created successfully'
        }, status=201)

class PlatformStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Organization stats
        org_count = Organization.objects.count()
        active_org_count = Organization.objects.filter(is_active=True).count()
        
        # User stats
        user_count = User.objects.count()
        
        # Ticket stats
        ticket_count = Ticket.objects.count()
        
        # Enquiry stats
        enquiry_count = Enquiry.objects.count()
        unread_enquiry_count = Enquiry.objects.filter(is_read=False).count()
        
        return Response({
            'organizations': {
                'total': org_count,
                'active': active_org_count
            },
            'users': {
                'total': user_count
            },
            'tickets': {
                'total': ticket_count
            },
            'enquiries': {
                'total': enquiry_count,
                'unread': unread_enquiry_count
            }
        })

class PlatformEnquiriesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_only = request.query_params.get('unread_only') == 'true'
        
        query = Enquiry.objects.all().order_by('-created_at')
        if unread_only:
            query = query.filter(is_read=False)
            
        data = [{
            'id': e.id,
            'name': e.name,
            'email': e.email,
            'company': e.company,
            'phone': e.phone,
            'message': e.message,
            'is_read': e.is_read,
            'created_at': e.created_at.isoformat()
        } for e in query]
        
        return Response({'enquiries': data})

class PlatformEnquiryReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            enquiry = Enquiry.objects.get(pk=pk)
            enquiry.is_read = True
            enquiry.save()
            return Response({'message': 'Enquiry marked as read'})
        except Enquiry.DoesNotExist:
            return Response({'error': 'Enquiry not found'}, status=404)

class PublicEnquiryView(views.APIView):
    """Public endpoint for landing page enquiry submissions"""
    permission_classes = [permissions.AllowAny]

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
    Reset platform admin password using OTP verification
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .email_utils import verify_reset_otp, clear_reset_otp
        
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        
        if not email or not otp or not new_password:
            return Response({
                'error': 'Email, OTP, and new password are required'
            }, status=400)
        
        # Find platform admin
        try:
            admin = PlatformAdmin.objects.get(email=email)
        except PlatformAdmin.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)
        
        # Verify OTP
        if not verify_reset_otp(admin, otp):
            return Response({
                'error': 'Invalid or expired OTP'
            }, status=401)
        
        # Reset password
        admin.set_password(new_password)
        clear_reset_otp(admin)
        
        return Response({
            'message': 'Password has been reset successfully'
        }, status=200)
