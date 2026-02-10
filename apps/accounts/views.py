from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import User, Organization
from .serializers import UserSerializer, UserUpdateSerializer, RegisterSerializer, LoginSerializer

class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, company_name):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Organization handled by middleware
            if not hasattr(request, 'organization') or not request.organization:
                 return Response({'error': 'Organization not found'}, status=404)
            
            organization = request.organization
            
            # Manual Authentication
            # Use iexact for case-insensitive email matching
            user = User.objects.filter(email__iexact=email, organization=organization).first()
            
            if user:
                if not user.check_password(password):
                     print(f"Login failed: Invalid password for {email}")
                     return Response({'message': 'Invalid credentials (password mismatch)'}, status=401)
                
                if not user.is_active:
                    print(f"Login failed: Inactive user {email}")
                    return Response({'message': 'Account is inactive'}, status=403)
                
                refresh = RefreshToken.for_user(user)
                refresh['org_id'] = organization.id # Add org context to token
                
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
            
            print(f"Login failed: User {email} not found in org {organization.subdomain}")
            return Response({'message': f'Invalid credentials (user not found in {organization.subdomain})'}, status=401)
        return Response(serializer.errors, status=400)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated] # Admin only in Flask

    def create(self, request, *args, **kwargs):
        # We need to inject organization_id from request context
        if not hasattr(request, 'organization') or not request.organization:
             return Response({'error': 'Organization context missing'}, status=400)
        
        # Check permissions (simple check for now, can be improved with UserRole)
        if request.user.organization_id != request.organization.id:
            return Response({'error': 'You can only register users for your own organization'}, status=403)
            
        data = request.data.copy()
        data['organization_id'] = request.organization.id
        
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

class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Scope to organization
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return User.objects.none()
        return User.objects.filter(organization=self.request.organization)

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    
    def get_queryset(self):
         if not hasattr(self.request, 'organization') or not self.request.organization:
            return User.objects.none()
         return User.objects.filter(organization=self.request.organization)

class ForgotPasswordView(views.APIView):
    """
    Send OTP to user's email for password reset
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, company_name):
        from .email_utils import create_reset_otp, send_otp_email
        
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required'}, status=400)
        
        # Get organization
        try:
            organization = Organization.objects.get(subdomain=company_name)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)
        
        # Find user in this organization
        try:
            user = User.objects.get(email=email, organization=organization)
        except User.DoesNotExist:
            # Don't reveal if user exists or not (security best practice)
            return Response({
                'message': 'If an account with this email exists, an OTP has been sent.'
            }, status=200)
        
        # Generate and save OTP
        otp = create_reset_otp(user)
        
        # Send OTP email
        email_sent = send_otp_email(user.email, otp, user_type='user')
        
        if email_sent:
            return Response({
                'message': 'OTP has been sent to your email address. It will expire in 15 minutes.'
            }, status=200)
        else:
            return Response({
                'error': 'Failed to send email. Please try again later.'
            }, status=500)

class ResetPasswordView(views.APIView):
    """
    Reset password using OTP verification
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, company_name):
        from .email_utils import verify_reset_otp, clear_reset_otp
        
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        
        if not email or not otp or not new_password:
            return Response({
                'error': 'Email, OTP, and new password are required'
            }, status=400)
        
        # Get organization
        try:
            organization = Organization.objects.get(subdomain=company_name)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)
        
        # Find user
        try:
            user = User.objects.get(email=email, organization=organization)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)
        
        # Verify OTP
        if not verify_reset_otp(user, otp):
            return Response({
                'error': 'Invalid or expired OTP'
            }, status=401)
        
        # Reset password
        user.set_password(new_password)
        clear_reset_otp(user)
        
        return Response({
            'message': 'Password has been reset successfully'
        }, status=200)

from rest_framework import viewsets
from .models import Department
from .serializers import DepartmentSerializer

class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
         if not hasattr(self.request, 'organization') or not self.request.organization:
            return Department.objects.none()
         return Department.objects.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

from apps.tickets.models import Ticket
from .models import Department
from django.db.models import Count, Q

class DepartmentHeadStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
             return Response({'error': 'Organization not found'}, status=404)
        
        user = request.user
        if not user.department:
            return Response({'error': 'User has no department assigned'}, status=400)
            
        try:
            dept = Department.objects.get(name=user.department, organization=request.organization)
        except Department.DoesNotExist:
            return Response({'error': f'Department "{user.department}" not found in organization'}, status=404)
            
        tickets = Ticket.objects.filter(organization=request.organization, department=dept)
        
        stats = {
            'total': tickets.count(),
            'open': tickets.filter(status='open').count(),
            'inprocess': tickets.filter(status__in=['in_progress', 'inprocess']).count(),
            'reopen': tickets.filter(status__in=['reopen', 'reopened']).count(),
            'closed': tickets.filter(status__in=['resolved', 'closed']).count(),
            'unassigned': tickets.filter(assigned_to__isnull=True).count()
        }
        
        # Employee Performance
        # Employees are Users who have the same department string
        employees = User.objects.filter(organization=request.organization, department=user.department)
        employee_performance = []
        
        for emp in employees:
            emp_tickets = tickets.filter(assigned_to=emp)
            employee_performance.append({
                'employee': UserSerializer(emp).data,
                'assigned': emp_tickets.count(),
                'inprocess': emp_tickets.filter(status__in=['in_progress', 'inprocess']).count(),
                'closed': emp_tickets.filter(status__in=['resolved', 'closed']).count()
            })
            
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
            dept = Department.objects.get(name=user.department, organization=request.organization)
        except Department.DoesNotExist:
             return Response({'error': f'Department "{user.department}" not found'}, status=404)
            
        tickets = Ticket.objects.filter(organization=request.organization, department=dept).order_by('-created_at')
        
        data = []
        for t in tickets:
            data.append({
                'id': t.id,
                'ticket_id': t.ticket_id,
                'subject': t.subject,
                'status': t.status,
                'priority': t.priority,
                'created_at': t.created_at,
                'assigned_to': t.assigned_to.id if t.assigned_to else None,
                'assigned_to_name': t.assigned_to.full_name if t.assigned_to else None
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
            
        return User.objects.filter(organization=self.request.organization, department=user.department)
