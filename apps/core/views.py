"""
API Views for Core app
"""
import logging
from datetime import timedelta

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework.views import APIView

from .models import ExternalDataSource, SchemaMapping, Feedback, Enquiry
from .serializers import ExternalDataSourceSerializer, SchemaMappingSerializer, FeedbackSerializer, EnquirySerializer
from .connectors import get_connector, DATABASE_CONFIGS
from apps.accounts.models import User
from apps.tickets.models import Ticket

logger = logging.getLogger('apps')

class ExternalDataSourceViewSet(viewsets.ModelViewSet):
    serializer_class = ExternalDataSourceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Only org admins can create/update/delete data sources."""
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'test_connection', 'test'):
            from apps.core.permissions import IsOrgAdmin
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        return super().get_permissions()
    
    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return ExternalDataSource.objects.none()
        return ExternalDataSource.objects.filter(organization_id=self.request.organization.id)
    
    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id)
    
    @action(detail=False, methods=['get'])
    def database_types(self, request, company_name=None):
        """
        Get list of supported database types with their configurations
        """
        return Response(DATABASE_CONFIGS)
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request, company_name=None):
        """
        Test database connection without saving
        """
        try:
            db_type = request.data.get('type')
            config = {
                'host': request.data.get('host'),
                'port': request.data.get('port'),
                'database': request.data.get('database'),
                'username': request.data.get('username'),
                'password': request.data.get('password'),
                'ssl_enabled': request.data.get('ssl_enabled', False),
                'connection_string': request.data.get('connection_string'),
            }
            
            connector = get_connector(db_type, config)
            result = connector.test_connection()
            connector.close()
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e),
                'details': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'details': {'error': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None, company_name=None):
        """
        Test connection for an existing data source
        """
        datasource = self.get_object()
        
        try:
            config = {
                'host': datasource.host,
                'port': datasource.port,
                'database': datasource.database,
                'username': datasource.username,
                'password': datasource.get_password(),
                'ssl_enabled': datasource.ssl_enabled,
                'connection_string': datasource.connection_string,
            }
            
            connector = get_connector(datasource.type, config)
            result = connector.test_connection()
            connector.close()
            
            # Update connection status
            datasource.connection_status = 'connected' if result['success'] else 'failed'
            datasource.last_connection_test = timezone.now()
            datasource.connection_error = None if result['success'] else result['message']
            datasource.save()
            
            return Response(result)
            
        except Exception as e:
            datasource.connection_status = 'failed'
            datasource.last_connection_test = timezone.now()
            datasource.connection_error = str(e)
            datasource.save()
            
            return Response({
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {'error': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def tables(self, request, pk=None, company_name=None):
        """
        Get list of tables/collections from data source
        """
        datasource = self.get_object()
        
        try:
            config = {
                'host': datasource.host,
                'port': datasource.port,
                'database': datasource.database,
                'username': datasource.username,
                'password': datasource.get_password(),
                'ssl_enabled': datasource.ssl_enabled,
            }
            
            connector = get_connector(datasource.type, config)
            tables = connector.get_tables()
            connector.close()
            
            return Response({'tables': tables})
            
        except Exception as e:
            return Response({
                'error': f'Failed to get tables: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def schema(self, request, pk=None, company_name=None):
        """
        Get schema for a specific table
        """
        datasource = self.get_object()
        table_name = request.query_params.get('table')
        
        if not table_name:
            return Response({'error': 'table parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            config = {
                'host': datasource.host,
                'port': datasource.port,
                'database': datasource.database,
                'username': datasource.username,
                'password': datasource.get_password(),
                'ssl_enabled': datasource.ssl_enabled,
            }
            
            connector = get_connector(datasource.type, config)
            schema = connector.get_schema(table_name)
            connector.close()
            
            return Response({'schema': schema})
            
        except Exception as e:
            return Response({
                'error': f'Failed to get schema: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SchemaMappingViewSet(viewsets.ModelViewSet):
    serializer_class = SchemaMappingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        datasource_id = self.request.query_params.get('datasource')
        if datasource_id:
            return SchemaMapping.objects.filter(datasource_id=datasource_id)
        
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return SchemaMapping.objects.none()
        return SchemaMapping.objects.filter(datasource__organization_id=self.request.organization.id)

class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Feedback.objects.filter(user_id=self.request.user.id)
    
    def perform_create(self, serializer):
        feedback = serializer.save(
            user_id=self.request.user.id,
            user_email=self.request.user.email,
        )
        try:
            from apps.notifications.email_service import send_feedback_email
            if hasattr(self.request, 'organization'):
                send_feedback_email(feedback, self.request.organization)
        except Exception as e:
            logger.warning(f'Failed to send feedback email: {e}')

class EnquiryViewSet(viewsets.ModelViewSet):
    """Enquiries are only accessible by platform admins (no org scoping)."""
    serializer_class = EnquirySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Only platform admins can access enquiries."""
        from apps.core.permissions import IsPlatformAdmin
        return [permissions.IsAuthenticated(), IsPlatformAdmin()]

    def get_queryset(self):
        return Enquiry.objects.all().order_by('-created_at')

class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_name=None):
        if not hasattr(request, 'organization') or not request.organization:
             return Response({'error': 'Organization not found'}, status=404)
        
        org = request.organization
        now = timezone.now()

        from apps.core.routers import get_current_db_alias
        if get_current_db_alias() == 'default':
            tickets = Ticket.objects.filter(organization_id=org.id)
            users = User.objects.filter(organization_id=org.id)
        else:
            tickets = Ticket.objects.all()
            users = User.objects.all()
        
        # Key Counts
        total_tickets = tickets.count()
        open_tickets = tickets.filter(status='open').count()
        in_progress_tickets = tickets.filter(status__in=['in_progress', 'inprocess']).count()
        resolved_tickets = tickets.filter(status='resolved').count()
        closed_tickets = tickets.filter(status='closed').count()
        total_users = users.count()

        # 1. Active Users (Logged in last 24h) - assuming last_login is updated
        active_threshold = now - timedelta(hours=24)
        active_users = users.filter(last_login__gte=active_threshold).count()

        # 2. SLA Breaches (Open > 24h)
        sla_threshold = now - timedelta(hours=24)
        sla_breaches = tickets.filter(status='open', created_at__lt=sla_threshold).count()

        # 3. Avg Resolution Time (in hours)
        resolved_tickets_with_time = tickets.exclude(resolution_time_seconds__isnull=True)
        avg_resolution_seconds = resolved_tickets_with_time.aggregate(models.Avg('resolution_time_seconds'))['resolution_time_seconds__avg']
        avg_resolution_hours = round(avg_resolution_seconds / 3600, 1) if avg_resolution_seconds else 0
        
        # Charts
        # 1. Status Distribution
        status_qs = tickets.values('status').annotate(count=Count('status'))
        status_data = {item['status']: item['count'] for item in status_qs}
        
        # 2. Priority Distribution
        priority_qs = tickets.values('priority').annotate(count=Count('priority'))
        priority_data = {item['priority']: item['count'] for item in priority_qs}
        
        # 3. Department Distribution where department name is not null
        dept_qs = tickets.values('department__name').annotate(count=Count('department'))
        dept_data = {}
        for item in dept_qs:
             name = item['department__name'] or 'Unassigned'
             dept_data[name] = item['count']

        # 4. Ticket Trends (Last 7 Days)
        seven_days_ago = now - timedelta(days=6)
        trend_qs = tickets.filter(created_at__gte=seven_days_ago)\
                          .annotate(date=TruncDate('created_at'))\
                          .values('date')\
                          .annotate(count=Count('id'))\
                          .order_by('date')
        
        # Fill in missing dates
        trend_data = {}
        current_date = seven_days_ago.date()
        end_date = now.date()
        while current_date <= end_date:
            trend_data[current_date.strftime('%Y-%m-%d')] = 0
            current_date += timedelta(days=1)
            
        for item in trend_qs:
            # item['date'] might be string or date object depending on DB backend
            d = item['date']
            if isinstance(d, str):
                key = d
            else:
                key = d.strftime('%Y-%m-%d')
            if key in trend_data:
                trend_data[key] = item['count']

        # Plan Details
        limits = org.get_limits()
        plan_details = {
            'name': org.plan,
            'max_users': limits.get('max_users', 30),
            'enabled_connectors': limits.get('enabled_connectors', []),
            'cluster_id': org.cluster_id
        }

        return Response({
             'total_tickets': total_tickets,
             'open_tickets': open_tickets,
             'in_progress_tickets': in_progress_tickets,
             'resolved_tickets': resolved_tickets,
             'closed_tickets': closed_tickets,
             'total_users': total_users,
             'active_users': active_users,
             'sla_breaches': sla_breaches,
             'avg_resolution_hours': avg_resolution_hours,
             'status_distribution': status_data,
             'priority_distribution': priority_data,
             'department_distribution': dept_data,
             'ticket_trends': trend_data,
             'plan_details': plan_details
        })
