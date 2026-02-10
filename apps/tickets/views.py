from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.db import models
from .models import Ticket, Project, Attachment, TicketHistory
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    ProjectSerializer, AttachmentSerializer
)
from apps.comments.models import Comment
from apps.comments.serializers import CommentSerializer
from apps.accounts.models import User
from django.utils import timezone
from datetime import datetime
import os

class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'ticket_id' # Allow looking up by ticket_id (e.g. SUP-1)
    # We might need custom lookup to support both ID and key, but let's stick to key or ID logic in get_object

    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'retrieve':
            return TicketDetailSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        return TicketDetailSerializer

    def get_queryset(self):
        # Scope to organization
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return Ticket.objects.none()
        
        queryset = Ticket.objects.filter(organization=self.request.organization)
        
        # Filter by user role
        user = self.request.user
        
        if user.role == 'manager':
            # Managers see tickets in their projects
            # We assume Project model is available via relation or we query it
            from apps.tickets.models import Project
            # Get projects where user is lead
            manager_projects = Project.objects.filter(organization=self.request.organization, lead_user=user)
            queryset = queryset.filter(project__in=manager_projects)
        # Admin and Agent see all tickets in organization (Agent logic per Flask app)
        
        return queryset

    def get_object(self):
        # Allow lookup by ID or Ticket Key
        queryset = self.get_queryset()
        # Prefetch history for activity timeline
        queryset = queryset.prefetch_related('history', 'history__user')
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        if lookup_value.isdigit():
             obj = get_object_or_404(queryset, id=int(lookup_value))
        else:
             obj = get_object_or_404(queryset, ticket_id__iexact=lookup_value)
             
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        # Generate ticket ID
        project = serializer.validated_data['project']
        # Ensure project belongs to organization
        if project.organization_id != self.request.organization.id:
            raise serializers.ValidationError({"project": "Project does not belong to this organization"})
            
        ticket_id = Ticket.generate_ticket_id(project.key, project.id)
        
        ticket = serializer.save(
            organization=self.request.organization,
            ticket_id=ticket_id,
            sender_email=self.request.user.email,
            sender_name=self.request.user.full_name
        )
        
        # Handle attachments
        files = self.request.FILES.getlist('attachments')
        if files:
            # Create upload directory
            # For now, simple local storage. In prod, use S3/storage backend
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            for f in files:
                # Save file
                filename = f.name
                # We should use a safer path
                path = default_storage.save(f'tickets/{ticket.ticket_id}/{filename}', ContentFile(f.read()))
                
                Attachment.objects.create(
                    ticket=ticket,
                    filename=filename,
                    filepath=path,
                    file_size=f.size,
                    mime_type=f.content_type
                )
                
        # History

        TicketHistory.objects.create(
            ticket=ticket,
            user=self.request.user,
            action='created',
            new_value='Ticket created'
        )

    def perform_update(self, serializer):
        ticket = serializer.instance
        old_status = ticket.status
        old_priority = ticket.priority
        old_assigned = ticket.assigned_to
        
        # Save the ticket
        serializer.save()
        
        # Track changes in history
        updated_ticket = serializer.instance
        
        # Status change
        if updated_ticket.status != old_status:
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action='status_changed',
                old_value=old_status,
                new_value=updated_ticket.status
            )
        
        # Priority change
        if updated_ticket.priority != old_priority:
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action='priority_changed',
                old_value=old_priority,
                new_value=updated_ticket.priority
            )
        
        # Assignment change
        if updated_ticket.assigned_to != old_assigned:
            action = 'unassigned' if not updated_ticket.assigned_to else ('assigned' if not old_assigned else 'reassigned')
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action=action,
                old_value=old_assigned.full_name if old_assigned else None,
                new_value=updated_ticket.assigned_to.full_name if updated_ticket.assigned_to else None
            )
        
        # Update closed_at if status changed to closed/resolved
        if updated_ticket.status in ['resolved', 'closed'] and not updated_ticket.closed_at:
            updated_ticket.closed_at = timezone.now()
            updated_ticket.save(update_fields=['closed_at'])

    @action(detail=False, methods=['get'])
    def statuses(self, request, company_name=None):
        """
        Return available ticket statuses
        """
        states = [
            {'id': 'open', 'name': 'Open'},
            {'id': 'in_progress', 'name': 'In Progress'},
            {'id': 'waiting', 'name': 'Waiting'},
            {'id': 'resolved', 'name': 'Resolved'},
            {'id': 'closed', 'name': 'Closed'}
        ]
        return Response(states)

    @action(detail=False, methods=['get'])
    def stats(self, request, company_name=None):
        queryset = self.get_queryset()
        total = queryset.count()
        my_assigned = queryset.filter(assigned_to=request.user).count()
        
        # Status Counts
        status_counts = queryset.values('status').annotate(count=Count('status'))
        status_data = {item['status']: item['count'] for item in status_counts}
        
        # Priority Counts
        priority_counts = queryset.values('priority').annotate(count=Count('priority'))
        priority_data = {item['priority']: item['count'] for item in priority_counts}
        
        return Response({
            'total': total,
            'my_assigned': my_assigned,
            'status_counts': status_data,
            'priority_counts': priority_data
        })

    @action(detail=True, methods=['post'])
    def comments(self, request, ticket_id=None, company_name=None):
        ticket = self.get_object()
        
        # Check permissions... logic similar to Flask
        
        comment_text = request.data.get('comment', '').strip()
        files = request.FILES.getlist('attachments')
        
        if not comment_text and not files:
            return Response({'error': 'Please enter a comment or attach a file'}, status=400)
            
        if not comment_text and files:
            comment_text = f'Attached {len(files)} file(s)'
            
        is_internal_raw = request.data.get('is_internal', False)
        if isinstance(is_internal_raw, str):
            is_internal = is_internal_raw.lower() == 'true'
        else:
            is_internal = bool(is_internal_raw)
        
        comment = Comment.objects.create(
            ticket=ticket,
            user=request.user,
            comment=comment_text,
            is_internal=is_internal
        )
        
        # Handle attachments for comments
        if files:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            for f in files:
                filename = f.name
                path = default_storage.save(f'tickets/{ticket.ticket_id}/{filename}', ContentFile(f.read()))
                
                Attachment.objects.create(
                    ticket=ticket,
                    comment=comment,
                    filename=filename,
                    filepath=path,
                    file_size=f.size,
                    mime_type=f.content_type
                )
                
        # History
        TicketHistory.objects.create(
            ticket=ticket,
            user=request.user,
            action='added_comment',
            new_value=f'{"Internal" if is_internal else "Public"} comment added'
        )
        
        return Response(CommentSerializer(comment).data, status=201)

    @action(detail=True, methods=['post'])
    def assign(self, request, ticket_id=None, company_name=None):
        ticket = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        try:
            user = User.objects.get(id=user_id, organization=request.organization)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
        old_assigned = ticket.assigned_to
        ticket.assigned_to = user
        ticket.save()
        
        # Create history entry
        TicketHistory.objects.create(
            ticket=ticket,
            user=request.user,
            action='assigned' if not old_assigned else 'reassigned',
            old_value=old_assigned.full_name if old_assigned else None,
            new_value=user.full_name
        )
        
        return Response(TicketDetailSerializer(ticket).data)

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
         if not hasattr(self.request, 'organization') or not self.request.organization:
            return Project.objects.none()
         return Project.objects.filter(organization=self.request.organization, is_active=True)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None, company_name=None):
        project = self.get_object()
        now = timezone.now()
        
        # CRITICAL: Filter tickets by organization for multi-tenancy
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)
        
        # 1. Project Stats - Filter by organization
        tickets = Ticket.objects.filter(project=project, organization=request.organization)
        total_tickets = tickets.count()
        resolved_tickets = tickets.filter(status__in=['resolved', 'closed']).count()
        completion_percentage = int((resolved_tickets / total_tickets * 100)) if total_tickets > 0 else 0
        
        # 2. Daily Progress (Last 30 Days)
        thirty_days_ago = now - timezone.timedelta(days=30)
        daily_qs = tickets.filter(status__in=['resolved', 'closed'], updated_at__gte=thirty_days_ago)\
                          .extra({'date': "date(updated_at)"})\
                          .values('date')\
                          .annotate(count=Count('id'))\
                          .order_by('date')
                          
        daily_labels = []
        daily_data = []
        
        # Fill dates
        current_date = thirty_days_ago.date()
        end_date = now.date()
        date_map = {item['date']: item['count'] for item in daily_qs}
        
        while current_date <= end_date:
            d_str = current_date.strftime('%Y-%m-%d')
            # Handle date object vs string from DB
            count = 0
            for k, v in date_map.items():
                if str(k) == d_str:
                    count = v
                    break
            
            daily_labels.append(d_str)
            daily_data.append(count)
            current_date += timezone.timedelta(days=1)

        # 3. Team Stats
        # Get all agents who have worked on this project
        # This is complex, let's simplify: Agents assigned to tickets in this project
        # CRITICAL: Filter by organization for multi-tenancy
        agents = User.objects.filter(
            assigned_tickets__project=project,
            organization=request.organization
        ).distinct()
        
        team_stats = []
        for agent in agents:
            assigned_count = tickets.filter(assigned_to=agent).count()
            agent_resolved = tickets.filter(assigned_to=agent, status__in=['resolved', 'closed'])
            resolved_count = agent_resolved.count()
            
            # Avg Resolution Time
            avg_time = 0
            resolved_with_time = agent_resolved.exclude(resolution_time_seconds__isnull=True)
            if resolved_with_time.exists():
                avg_seconds = resolved_with_time.aggregate(models.Avg('resolution_time_seconds'))['resolution_time_seconds__avg']
                if avg_seconds:
                    avg_time = round(avg_seconds / 3600, 1)
            
            team_stats.append({
                'name': agent.full_name,
                'department': agent.department, # CharField
                'assigned': assigned_count,
                'resolved': resolved_count,
                'avg_time_hours': avg_time
            })

        return Response({
            'project': {
                'name': project.name,
                'completion_percentage': completion_percentage,
                'start_date': project.start_date,
                'end_date': project.end_date
            },
            'daily_progress': {
                'labels': daily_labels,
                'data': daily_data
            },
            'team_stats': team_stats
        })
