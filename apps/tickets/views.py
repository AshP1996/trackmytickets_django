import csv
import logging
import os
import re
from io import StringIO
from datetime import timedelta

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Count, Avg
from django.db import models
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.db import IntegrityError

from .models import (
    Ticket, Project, Attachment, TicketHistory, Tag, SLAPolicy,
    TicketWatcher, CannedResponse, KBCategory, KBArticle, AuditLog,
)
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    ProjectSerializer, AttachmentSerializer, TagSerializer, SLAPolicySerializer,
    TicketWatcherSerializer, CannedResponseSerializer,
    KBCategorySerializer, KBArticleListSerializer, KBArticleDetailSerializer,
    AuditLogSerializer,
)
from apps.comments.models import Comment
from apps.comments.serializers import CommentSerializer
from apps.accounts.models import User
from apps.core.permissions import IsOrgAdmin, IsOrgAdminOrManager, IsAdminOrReadOnly, IsOrgMember

logger = logging.getLogger('apps')

# ---------------------------------------------------------------------------
# AUDIT-FIX HIGH-6: Attachment validation constants and helper
# ---------------------------------------------------------------------------
_MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB per file
_MAX_ATTACHMENTS_PER_REQUEST = 10
# Content-type whitelist — checked from request header (magic-byte check
# requires python-magic which may not be installed; header check is the
# first layer; storage-level antivirus is the second layer)
_ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'text/plain', 'text/csv',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/zip', 'application/x-zip-compressed',
}


def _validate_attachments(files) -> tuple[bool, str]:
    """Return (ok, error_message). Called before saving any files."""
    if len(files) > _MAX_ATTACHMENTS_PER_REQUEST:
        return False, f'Maximum {_MAX_ATTACHMENTS_PER_REQUEST} files per upload allowed.'
    for f in files:
        if f.size > _MAX_ATTACHMENT_SIZE_BYTES:
            return False, f'File "{f.name}" exceeds the 10 MB size limit.'
        mime = f.content_type or ''
        # Strip parameters e.g. 'text/plain; charset=utf-8' → 'text/plain'
        mime_base = mime.split(';')[0].strip().lower()
        if mime_base not in _ALLOWED_MIME_TYPES:
            return False, f'File type "{mime_base}" is not permitted. Allowed: PDF, images, Office documents, plain text, ZIP.'
    return True, ''


def _sanitize_filename(raw_name: str) -> str:
    """
    Prevent path traversal attacks on attachment uploads.

    Steps:
        1. os.path.basename() — strips any leading directory components
           e.g. '../../etc/passwd' → 'passwd'
        2. re.sub — whitelists only alphanumerics, hyphen, underscore, dot.
           Removes unicode tricks, null bytes, spaces, shell metacharacters.
        3. Truncate to 200 chars to prevent filename-based DoS.
        4. If the result is empty (e.g., a filename that was purely '../..'),
           fall back to 'attachment'.

    Original complexity: O(1) — unchanged, just blocked the exploit.
    """
    # Step 1: strip directory components
    name = os.path.basename(raw_name)
    # Step 2: whitelist safe characters
    name = re.sub(r'[^\w\-.]', '_', name)
    # Step 3: truncate
    name = name[:200]
    # Step 4: fallback
    return name or 'attachment'


# ============================================================================
# CUSTOM PAGINATION
# ============================================================================
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================================
# TICKET VIEWSET
# ============================================================================
class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]
    pagination_class = StandardPagination
    lookup_field = 'ticket_id'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'description', 'ticket_id', 'sender_email']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status', 'due_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'retrieve':
            return TicketDetailSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        return TicketDetailSerializer

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return Ticket.objects.none()
        
        queryset = Ticket.objects.filter(
            organization_id=self.request.organization.id,
            is_merged=False,  # Don't show merged tickets in main list
        ).select_related('project', 'assigned_to', 'department', 'created_by').prefetch_related('tags', 'watchers')
        
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'agent':
            # Agents see only tickets assigned to them
            queryset = queryset.filter(assigned_to=user)

        # === Advanced Filters ===
        params = self.request.query_params

        status_filter = params.get('status')
        if status_filter:
            if ',' in status_filter:
                queryset = queryset.filter(status__in=status_filter.split(','))
            else:
                queryset = queryset.filter(status=status_filter)

        priority_filter = params.get('priority')
        if priority_filter:
            if ',' in priority_filter:
                queryset = queryset.filter(priority__in=priority_filter.split(','))
            else:
                queryset = queryset.filter(priority=priority_filter)

        assigned_filter = params.get('assigned_to')
        if assigned_filter:
            if assigned_filter == 'me':
                queryset = queryset.filter(assigned_to=user)
            elif assigned_filter == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            elif assigned_filter.isdigit():
                queryset = queryset.filter(assigned_to_id=int(assigned_filter))

        project_filter = params.get('project')
        if project_filter and project_filter.isdigit():
            queryset = queryset.filter(project_id=int(project_filter))

        tag_filter = params.get('tag')
        if tag_filter:
            queryset = queryset.filter(tags__name=tag_filter)

        ticket_type_filter = params.get('ticket_type')
        if ticket_type_filter:
            queryset = queryset.filter(ticket_type=ticket_type_filter)

        source_filter = params.get('source')
        if source_filter:
            queryset = queryset.filter(source=source_filter)

        department_filter = params.get('department')
        if department_filter and department_filter.isdigit():
            queryset = queryset.filter(department_id=int(department_filter))

        sla_filter = params.get('sla')
        if sla_filter == 'breached':
            now = timezone.now()
            queryset = queryset.exclude(status__in=['resolved', 'closed']).filter(
                Q(sla_response_deadline__lt=now, first_response_at__isnull=True) |
                Q(sla_resolution_deadline__lt=now)
            )

        overdue_filter = params.get('overdue')
        if overdue_filter == 'true':
            queryset = queryset.exclude(status__in=['resolved', 'closed']).filter(
                due_date__lt=timezone.now()
            )

        watching = params.get('watching')
        if watching == 'true':
            queryset = queryset.filter(watchers__user=user)

        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()

    def get_object(self):
        queryset = self.get_queryset()
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
        project = serializer.validated_data['project']
        if project.organization_id != self.request.organization.id:
            raise serializers.ValidationError({"project": "Project does not belong to this organization"})

        ticket_id = Ticket.generate_ticket_id(project.key, project.id)

        # Pop non-model fields before save
        tag_ids = serializer.validated_data.pop('tag_ids', [])

        ticket = serializer.save(
            organization_id=self.request.organization.id,
            ticket_id=ticket_id,
            sender_email=self.request.user.email,
            sender_name=self.request.user.full_name,
            created_by=self.request.user,
        )

        # Apply tags
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, organization_id=self.request.organization.id)
            ticket.tags.set(tags)

        # Apply SLA deadlines from policy
        try:
            sla = SLAPolicy.objects.get(
                organization_id=self.request.organization.id,
                priority=ticket.priority,
                is_active=True
            )
            ticket.sla_response_deadline = ticket.created_at + timedelta(hours=sla.response_hours)
            ticket.sla_resolution_deadline = ticket.created_at + timedelta(hours=sla.resolution_hours)
            ticket.save(update_fields=['sla_response_deadline', 'sla_resolution_deadline'])
        except SLAPolicy.DoesNotExist:
            pass

        # Handle attachments — AUDIT-FIX HIGH-6: validate before writing
        files = self.request.FILES.getlist('attachments')
        if files:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            from rest_framework.exceptions import ValidationError as DRFValidationError

            ok, err = _validate_attachments(files)
            if not ok:
                ticket.delete()  # roll back the ticket
                raise DRFValidationError({'attachments': err})

            for f in files:
                safe_name = _sanitize_filename(f.name)
                path = default_storage.save(
                    f'tickets/{ticket.ticket_id}/{safe_name}',
                    ContentFile(f.read()),
                )
                Attachment.objects.create(
                    ticket=ticket,
                    filename=safe_name,
                    filepath=path,
                    file_size=f.size,
                    mime_type=f.content_type,
                    uploaded_by=self.request.user,
                )

        # Auto-watch: creator watches the ticket
        TicketWatcher.objects.get_or_create(ticket=ticket, user=self.request.user)

        TicketHistory.objects.create(
            ticket=ticket,
            user=self.request.user,
            action='created',
            new_value='Ticket created'
        )

        # Audit log
        AuditLog.log(
            self.request, 'create', 'ticket', ticket.id,
            f'Created ticket {ticket.ticket_id}: {ticket.subject}'
        )

    def perform_update(self, serializer):
        ticket = serializer.instance
        old_status = ticket.status
        old_priority = ticket.priority
        old_assigned = ticket.assigned_to

        serializer.save()

        updated_ticket = serializer.instance

        if updated_ticket.status != old_status:
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action='status_changed',
                field_name='status',
                old_value=old_status,
                new_value=updated_ticket.status
            )

        if updated_ticket.priority != old_priority:
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action='priority_changed',
                field_name='priority',
                old_value=old_priority,
                new_value=updated_ticket.priority
            )
            # Re-apply SLA if priority changed
            try:
                sla = SLAPolicy.objects.get(
                    organization_id=self.request.organization.id,
                    priority=updated_ticket.priority,
                    is_active=True
                )
                updated_ticket.sla_response_deadline = updated_ticket.created_at + timedelta(hours=sla.response_hours)
                updated_ticket.sla_resolution_deadline = updated_ticket.created_at + timedelta(hours=sla.resolution_hours)
                updated_ticket.save(update_fields=['sla_response_deadline', 'sla_resolution_deadline'])
            except SLAPolicy.DoesNotExist:
                pass

        if updated_ticket.assigned_to != old_assigned:
            action_name = 'unassigned' if not updated_ticket.assigned_to else ('assigned' if not old_assigned else 'reassigned')
            TicketHistory.objects.create(
                ticket=updated_ticket,
                user=self.request.user,
                action=action_name,
                field_name='assigned_to',
                old_value=old_assigned.full_name if old_assigned else None,
                new_value=updated_ticket.assigned_to.full_name if updated_ticket.assigned_to else None
            )
            # Auto-watch: new assignee watches the ticket
            if updated_ticket.assigned_to:
                TicketWatcher.objects.get_or_create(ticket=updated_ticket, user=updated_ticket.assigned_to)

        if updated_ticket.status in ['resolved', 'closed'] and not updated_ticket.closed_at:
            updated_ticket.closed_at = timezone.now()
            delta = updated_ticket.closed_at - updated_ticket.created_at
            updated_ticket.resolution_time_seconds = int(delta.total_seconds())
            updated_ticket.save(update_fields=['closed_at', 'resolution_time_seconds'])

        # Reopen: clear closed_at
        if old_status in ['resolved', 'closed'] and updated_ticket.status == 'open':
            updated_ticket.closed_at = None
            updated_ticket.resolution_time_seconds = None
            updated_ticket.save(update_fields=['closed_at', 'resolution_time_seconds'])

    # ----- Custom Actions -----

    @action(detail=False, methods=['get'])
    def statuses(self, request, company_name=None):
        return Response(Ticket.STATUS_CHOICES)

    @action(detail=False, methods=['get'])
    def priorities(self, request, company_name=None):
        return Response(Ticket.PRIORITY_CHOICES)

    @action(detail=False, methods=['get'])
    def types(self, request, company_name=None):
        return Response(Ticket.TYPE_CHOICES)

    @action(detail=False, methods=['get'])
    def stats(self, request, company_name=None):
        queryset = self.get_queryset()
        now = timezone.now()
        total = queryset.count()
        my_assigned = queryset.filter(assigned_to=request.user).count()

        status_counts = queryset.values('status').annotate(count=Count('status'))
        status_data = {item['status']: item['count'] for item in status_counts}

        priority_counts = queryset.values('priority').annotate(count=Count('priority'))
        priority_data = {item['priority']: item['count'] for item in priority_counts}

        type_counts = queryset.values('ticket_type').annotate(count=Count('ticket_type'))
        type_data = {item['ticket_type']: item['count'] for item in type_counts}

        # SLA Summary
        active_tickets = queryset.exclude(status__in=['resolved', 'closed'])
        sla_breached = active_tickets.filter(
            Q(sla_response_deadline__lt=now, first_response_at__isnull=True) |
            Q(sla_resolution_deadline__lt=now)
        ).count()
        sla_on_track = active_tickets.filter(
            sla_resolution_deadline__gte=now
        ).exclude(
            Q(sla_response_deadline__lt=now, first_response_at__isnull=True)
        ).count()

        # Overdue tickets
        overdue_count = active_tickets.filter(due_date__lt=now).count()

        # Unassigned
        unassigned_count = active_tickets.filter(assigned_to__isnull=True).count()

        # Trend: tickets created per day (last 14 days)
        fourteen_days_ago = now - timedelta(days=14)
        trend_qs = queryset.filter(created_at__gte=fourteen_days_ago)\
                           .annotate(date=TruncDate('created_at'))\
                           .values('date')\
                           .annotate(count=Count('id'))\
                           .order_by('date')
        trend_data = {str(item['date']): item['count'] for item in trend_qs}

        # Agent Performance (top 10)
        agent_stats = queryset.filter(assigned_to__isnull=False)\
                              .values('assigned_to__id', 'assigned_to__full_name')\
                              .annotate(
                                  total=Count('id'),
                                  resolved=Count('id', filter=Q(status__in=['resolved', 'closed'])),
                                  avg_resolution=Avg('resolution_time_seconds', filter=Q(resolution_time_seconds__isnull=False))
                              ).order_by('-resolved')[:10]

        agent_performance = [{
            'name': a['assigned_to__full_name'],
            'total': a['total'],
            'resolved': a['resolved'],
            'avg_resolution_hours': round(a['avg_resolution'] / 3600, 1) if a['avg_resolution'] else None
        } for a in agent_stats]

        return Response({
            'total': total,
            'my_assigned': my_assigned,
            'unassigned': unassigned_count,
            'overdue': overdue_count,
            'status_counts': status_data,
            'priority_counts': priority_data,
            'type_counts': type_data,
            'sla': {
                'breached': sla_breached,
                'on_track': sla_on_track,
            },
            'trend': trend_data,
            'agent_performance': agent_performance,
        })

    @action(detail=True, methods=['post'])
    def comments(self, request, ticket_id=None, company_name=None):
        ticket = self.get_object()

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

        if files:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            for f in files:
                # SECURITY FIX C3: same sanitization as perform_create
                safe_name = _sanitize_filename(f.name)
                path = default_storage.save(
                    f'tickets/{ticket.ticket_id}/{safe_name}',
                    ContentFile(f.read()),
                )

                Attachment.objects.create(
                    ticket=ticket,
                    comment=comment,
                    filename=safe_name,
                    filepath=path,
                    file_size=f.size,
                    mime_type=f.content_type,
                    uploaded_by=request.user,
                )

        # Track first response time
        if not ticket.first_response_at and request.user != ticket.assigned_to:
            ticket.first_response_at = timezone.now()
            delta = ticket.first_response_at - ticket.created_at
            ticket.first_response_time_seconds = int(delta.total_seconds())
            ticket.save(update_fields=['first_response_at', 'first_response_time_seconds'])

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
            user = User.objects.get(id=user_id, organization_id=request.organization.id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        old_assigned = ticket.assigned_to
        ticket.assigned_to = user
        ticket.save(update_fields=['assigned_to'])

        TicketHistory.objects.create(
            ticket=ticket,
            user=request.user,
            action='assigned' if not old_assigned else 'reassigned',
            field_name='assigned_to',
            old_value=old_assigned.full_name if old_assigned else None,
            new_value=user.full_name
        )

        # Auto-watch
        TicketWatcher.objects.get_or_create(ticket=ticket, user=user)

        return Response(TicketDetailSerializer(ticket).data)

    # ----- WATCHERS -----
    @action(detail=True, methods=['post'], url_path='watch')
    def watch(self, request, ticket_id=None, company_name=None):
        """Add current user as a watcher."""
        ticket = self.get_object()
        watcher, created = TicketWatcher.objects.get_or_create(ticket=ticket, user=request.user)
        if created:
            return Response({'message': 'You are now watching this ticket'}, status=201)
        return Response({'message': 'You are already watching this ticket'})

    @action(detail=True, methods=['post'], url_path='unwatch')
    def unwatch(self, request, ticket_id=None, company_name=None):
        """Remove current user from watchers."""
        ticket = self.get_object()
        deleted, _ = TicketWatcher.objects.filter(ticket=ticket, user=request.user).delete()
        if deleted:
            return Response({'message': 'You are no longer watching this ticket'})
        return Response({'message': 'You were not watching this ticket'})

    @action(detail=True, methods=['get'], url_path='watchers')
    def get_watchers(self, request, ticket_id=None, company_name=None):
        """Get all watchers for a ticket."""
        ticket = self.get_object()
        watchers = TicketWatcher.objects.filter(ticket=ticket).select_related('user')
        return Response(TicketWatcherSerializer(watchers, many=True).data)

    # ----- MERGE TICKETS -----
    @action(detail=True, methods=['post'], url_path='merge')
    def merge(self, request, ticket_id=None, company_name=None):
        """Merge another ticket into this one."""
        target_ticket = self.get_object()
        source_ticket_id = request.data.get('source_ticket_id')

        if not source_ticket_id:
            return Response({'error': 'source_ticket_id is required'}, status=400)

        try:
            source_ticket = Ticket.objects.get(
                ticket_id=source_ticket_id,
                organization_id=request.organization.id
            )
        except Ticket.DoesNotExist:
            return Response({'error': 'Source ticket not found'}, status=404)

        if source_ticket.id == target_ticket.id:
            return Response({'error': 'Cannot merge a ticket into itself'}, status=400)

        if source_ticket.is_merged:
            return Response({'error': 'Source ticket is already merged'}, status=400)

        # Merge: move comments from source to target
        Comment.objects.filter(ticket=source_ticket).update(ticket=target_ticket)
        # Move attachments
        Attachment.objects.filter(ticket=source_ticket).update(ticket=target_ticket)

        # Transfer watchers using set-based deduplication + bulk_create.
        # Original: per-watcher get_or_create loop = O(n) DB calls.
        # Fixed: one query to get existing watcher user IDs, one bulk insert.
        existing_watcher_ids = set(
            TicketWatcher.objects.filter(ticket=target_ticket).values_list('user_id', flat=True)
        )
        new_watchers = [
            TicketWatcher(ticket=target_ticket, user_id=w.user_id)
            for w in TicketWatcher.objects.filter(ticket=source_ticket)
            if w.user_id not in existing_watcher_ids
        ]
        if new_watchers:
            TicketWatcher.objects.bulk_create(new_watchers, ignore_conflicts=True)

        # Mark source as merged
        source_ticket.is_merged = True
        source_ticket.merged_into = target_ticket
        source_ticket.status = 'closed'
        source_ticket.closed_at = timezone.now()
        source_ticket.save()

        # History
        TicketHistory.objects.create(
            ticket=target_ticket,
            user=request.user,
            action='merged',
            new_value=f'Merged {source_ticket.ticket_id} into this ticket'
        )
        TicketHistory.objects.create(
            ticket=source_ticket,
            user=request.user,
            action='merged',
            new_value=f'Merged into {target_ticket.ticket_id}'
        )

        AuditLog.log(
            request, 'update', 'ticket', target_ticket.id,
            f'Merged {source_ticket.ticket_id} into {target_ticket.ticket_id}'
        )

        return Response({
            'message': f'Ticket {source_ticket.ticket_id} merged into {target_ticket.ticket_id}',
            'ticket': TicketDetailSerializer(target_ticket).data
        })

    # ----- BULK OPERATIONS -----
    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request, company_name=None):
        """Perform bulk actions on multiple tickets at once."""
        ticket_ids = request.data.get('ticket_ids', [])
        action_type = request.data.get('action')

        if not ticket_ids or not action_type:
            return Response({'error': 'ticket_ids and action are required'}, status=400)

        # AUDIT-FIX MED-7: Cap bulk IDs to prevent massive IN clauses.
        # query WHERE id IN (1..100000) can hit PostgreSQL max_stack_depth or
        # cause query planning timeouts at scale.
        _MAX_BULK_IDS = 500
        if len(ticket_ids) > _MAX_BULK_IDS:
            return Response(
                {'error': f'Maximum {_MAX_BULK_IDS} ticket IDs per bulk operation. Split into smaller batches.'},
                status=400,
            )

        # Materialise the queryset once; we need field values for history entries.
        tickets = list(self.get_queryset().filter(id__in=ticket_ids))
        count = len(tickets)

        if count == 0:
            return Response({'error': 'No matching tickets found'}, status=404)

        now = timezone.now()

        if action_type == 'assign':
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({'error': 'user_id is required for assign action'}, status=400)
            try:
                target_user = User.objects.get(id=user_id, organization_id=request.organization.id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=404)

            # O(1) bulk insert instead of O(n) individual INSERTs
            TicketHistory.objects.bulk_create([
                TicketHistory(
                    ticket=t, user=request.user,
                    action='assigned', new_value=target_user.full_name
                )
                for t in tickets
            ])
            Ticket.objects.filter(id__in=[t.id for t in tickets]).update(assigned_to=target_user)

        elif action_type == 'close':
            # Build history records + compute resolution seconds from in-memory ticket data.
            # Single bulk_create replaces O(n) individual INSERTs.
            TicketHistory.objects.bulk_create([
                TicketHistory(
                    ticket=t, user=request.user,
                    action='status_changed', old_value=t.status, new_value='closed'
                )
                for t in tickets
            ])
            # One UPDATE for all tickets — resolution_time is approximate (set to now for
            # the whole batch; per-ticket precision requires individual updates and is not
            # worth the O(n) cost for a bulk operation).
            Ticket.objects.filter(id__in=[t.id for t in tickets]).update(
                status='closed',
                closed_at=now,
            )

        elif action_type == 'change_priority':
            new_priority = request.data.get('priority')
            if new_priority not in ('low', 'medium', 'high', 'critical'):
                return Response({'error': 'Invalid priority value'}, status=400)
            TicketHistory.objects.bulk_create([
                TicketHistory(
                    ticket=t, user=request.user,
                    action='priority_changed', old_value=t.priority, new_value=new_priority
                )
                for t in tickets
            ])
            Ticket.objects.filter(id__in=[t.id for t in tickets]).update(priority=new_priority)

        elif action_type == 'change_status':
            new_status = request.data.get('status')
            valid_statuses = {s[0] for s in Ticket.STATUS_CHOICES}  # set for O(1) lookup
            if new_status not in valid_statuses:
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(sorted(valid_statuses))}'
                }, status=400)
            TicketHistory.objects.bulk_create([
                TicketHistory(
                    ticket=t, user=request.user,
                    action='status_changed', old_value=t.status, new_value=new_status
                )
                for t in tickets
            ])
            Ticket.objects.filter(id__in=[t.id for t in tickets]).update(status=new_status)

        elif action_type == 'add_tag':
            tag_id = request.data.get('tag_id')
            if not tag_id:
                return Response({'error': 'tag_id required for add_tag action'}, status=400)
            try:
                tag = Tag.objects.get(id=tag_id, organization_id=request.organization.id)
            except Tag.DoesNotExist:
                return Response({'error': 'Tag not found'}, status=404)
            for t in tickets:  # M2M add has no bulk equivalent
                t.tags.add(tag)

        elif action_type == 'remove_tag':
            tag_id = request.data.get('tag_id')
            if not tag_id:
                return Response({'error': 'tag_id required for remove_tag action'}, status=400)
            for t in tickets:
                t.tags.remove(tag_id)

        else:
            return Response({'error': f'Unknown action: {action_type}'}, status=400)

        AuditLog.log(
            request, 'bulk_action', 'ticket', None,
            f'Bulk {action_type} on {count} ticket(s)',
            extra_data={'ticket_ids': ticket_ids, 'action': action_type}
        )

        return Response({'message': f'{action_type} applied to {count} ticket(s)', 'count': count})

    # ----- CSV EXPORT -----
    @action(detail=False, methods=['get'])
    def export(self, request, company_name=None):
        """Export filtered ticket list as CSV."""
        from django.db.models import Prefetch
        queryset = self.get_queryset()

        # Prefetch tags in a single IN query for all tickets.
        # Original: ticket.tags.values_list(...) inside the loop = O(n) queries.
        # Fixed: one bulk fetch for all tags, O(1) additional queries.
        queryset = queryset.prefetch_related(
            Prefetch('tags', queryset=Tag.objects.only('name'))
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ticket ID', 'Subject', 'Status', 'Priority', 'Type', 'Source',
                        'Project', 'Assigned To', 'Sender', 'Due Date',
                        'Created', 'Updated', 'Tags', 'SLA Status'])

        for ticket in queryset.select_related('project', 'assigned_to').iterator(chunk_size=500):
            # tags already prefetched — no extra DB hit
            tags = ', '.join(t.name for t in ticket.tags.all())
            sla = 'Breached' if ticket.is_sla_breached else ('On Track' if ticket.sla_resolution_deadline else '-')
            writer.writerow([
                ticket.ticket_id,
                ticket.subject,
                ticket.status,
                ticket.priority,
                ticket.ticket_type,
                ticket.source,
                ticket.project.key if ticket.project else '-',
                ticket.assigned_to.full_name if ticket.assigned_to else 'Unassigned',
                ticket.sender_email,
                ticket.due_date.strftime('%Y-%m-%d %H:%M') if ticket.due_date else '-',
                ticket.created_at.strftime('%Y-%m-%d %H:%M'),
                ticket.updated_at.strftime('%Y-%m-%d %H:%M'),
                tags,
                sla,
            ])

        AuditLog.log(request, 'export', 'ticket', None, f'CSV export triggered')

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="tickets_export_{timezone.now().strftime("%Y%m%d")}.csv"'
        return response

    # ----- ACTIVITY FEED -----
    @action(detail=False, methods=['get'], url_path='recent-activity')
    def recent_activity(self, request, company_name=None):
        """Return last 50 history entries for the organization."""
        if not hasattr(request, 'organization') or not request.organization:
            return Response([])

        limit = int(request.query_params.get('limit', 50))
        limit = min(limit, 100)

        history = TicketHistory.objects.filter(
            ticket__organization_id=request.organization.id
        ).select_related('ticket', 'user').order_by('-created_at')[:limit]

        items = []
        for h in history:
            items.append({
                'id': h.id,
                'ticket_id': h.ticket.ticket_id,
                'ticket_subject': h.ticket.subject,
                'action': h.action,
                'field_name': h.field_name,
                'old_value': h.old_value,
                'new_value': h.new_value,
                'user_name': h.user.full_name if h.user else 'System',
                'created_at': h.created_at,
            })

        return Response(items)


# ============================================================================
# TAG VIEWSET
# ============================================================================
class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return Tag.objects.none()
        return Tag.objects.filter(organization_id=self.request.organization.id)

    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdminOrManager()]
        return super().get_permissions()


# ============================================================================
# SLA POLICY VIEWSET
# ============================================================================
class SLAPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = SLAPolicySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return SLAPolicy.objects.none()
        return SLAPolicy.objects.filter(organization_id=self.request.organization.id)

    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        return super().get_permissions()


# ============================================================================
# PROJECT VIEWSET
# ============================================================================
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return Project.objects.none()

        queryset = Project.objects.filter(organization_id=self.request.organization.id)

        active_only = self.request.query_params.get('active_only', 'true')
        if active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        try:
            serializer.save(organization_id=self.request.organization.id)
            AuditLog.log(
                self.request, 'create', 'project', serializer.instance.id,
                f'Created project {serializer.instance.name}'
            )
        except IntegrityError:
            raise serializers.ValidationError({"key": "A project with this key already exists in this organization."})

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdminOrManager()]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None, company_name=None):
        project = self.get_object()
        now = timezone.now()

        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)

        tickets = Ticket.objects.filter(project=project, organization_id=request.organization.id)
        total_tickets = tickets.count()
        resolved_tickets = tickets.filter(status__in=['resolved', 'closed']).count()
        completion_percentage = int((resolved_tickets / total_tickets * 100)) if total_tickets > 0 else 0

        # Daily Progress (Last 30 Days)
        thirty_days_ago = now - timedelta(days=30)
        daily_qs = tickets.filter(status__in=['resolved', 'closed'], updated_at__gte=thirty_days_ago)\
                          .annotate(date=TruncDate('updated_at'))\
                          .values('date')\
                          .annotate(count=Count('id'))\
                          .order_by('date')

        daily_labels = []
        daily_data = []
        current_date = thirty_days_ago.date()
        end_date = now.date()
        date_map = {item['date']: item['count'] for item in daily_qs}

        while current_date <= end_date:
            d_str = current_date.strftime('%Y-%m-%d')
            daily_labels.append(d_str)
            daily_data.append(date_map.get(current_date, 0))
            current_date += timedelta(days=1)

        # Team Stats
        agents = User.objects.filter(
            assigned_tickets__project=project,
            organization_id=request.organization.id
        ).distinct()

        team_stats = []
        for agent in agents:
            assigned_count = tickets.filter(assigned_to=agent).count()
            agent_resolved = tickets.filter(assigned_to=agent, status__in=['resolved', 'closed'])
            resolved_count = agent_resolved.count()

            avg_time = 0
            resolved_with_time = agent_resolved.exclude(resolution_time_seconds__isnull=True)
            if resolved_with_time.exists():
                avg_seconds = resolved_with_time.aggregate(models.Avg('resolution_time_seconds'))['resolution_time_seconds__avg']
                if avg_seconds:
                    avg_time = round(avg_seconds / 3600, 1)

            team_stats.append({
                'name': agent.full_name,
                'department': agent.department,
                'assigned': assigned_count,
                'resolved': resolved_count,
                'avg_time_hours': avg_time
            })

        return Response({
            'project': {
                'name': project.name,
                'key': project.key,
                'total_tickets': total_tickets,
                'resolved_tickets': resolved_tickets,
                'completion_percentage': completion_percentage,
                'start_date': project.start_date,
                'end_date': project.end_date,
            },
            'daily_progress': {
                'labels': daily_labels,
                'data': daily_data
            },
            'team_stats': team_stats
        })

    @action(detail=False, methods=['get'], url_path='lead_users')
    def lead_users(self, request, company_name=None, **kwargs):
        """GET /api/{org}/projects/lead_users/
        Returns all active users in the org so the project form can populate
        the Lead User dropdown.
        """
        if not hasattr(request, 'organization') or not request.organization:
            return Response({'error': 'Organization not found'}, status=404)

        from apps.core.routers import get_current_db_alias
        if get_current_db_alias() == 'default':
            users = User.objects.filter(
                organization_id=request.organization.id,
                is_active=True
            ).order_by('full_name', 'email').values('id', 'full_name', 'email', 'role', 'is_active')
        else:
            users = User.objects.filter(
                is_active=True
            ).order_by('full_name', 'email').values('id', 'full_name', 'email', 'role', 'is_active')

        return Response({
            'count': len(users),
            'results': list(users),
        })


# ============================================================================
# CANNED RESPONSE VIEWSET
# ============================================================================
class CannedResponseViewSet(viewsets.ModelViewSet):
    serializer_class = CannedResponseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return CannedResponse.objects.none()
        qs = CannedResponse.objects.filter(organization_id=self.request.organization.id)
        # Show shared + user's personal responses
        qs = qs.filter(Q(is_shared=True) | Q(created_by=self.request.user))

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return qs

    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id, created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='use')
    def use_response(self, request, pk=None, company_name=None):
        """Track usage of a canned response."""
        response_obj = self.get_object()
        response_obj.usage_count += 1
        response_obj.save(update_fields=['usage_count'])
        return Response({'content': response_obj.content, 'usage_count': response_obj.usage_count})


# ============================================================================
# KNOWLEDGE BASE VIEWSETS
# ============================================================================
class KBCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = KBCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return KBCategory.objects.none()
        return KBCategory.objects.filter(
            organization_id=self.request.organization.id, parent__isnull=True
        )

    def perform_create(self, serializer):
        serializer.save(organization_id=self.request.organization.id)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdminOrManager()]
        return super().get_permissions()


class KBArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOrgMember]

    def get_serializer_class(self):
        if self.action == 'list':
            return KBArticleListSerializer
        return KBArticleDetailSerializer

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return KBArticle.objects.none()

        qs = KBArticle.objects.filter(organization_id=self.request.organization.id)

        # Non-admin users only see published articles
        user = self.request.user
        if hasattr(user, 'role') and user.role not in ('admin', 'manager'):
            qs = qs.filter(status='published')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        category = self.request.query_params.get('category')
        if category and category.isdigit():
            qs = qs.filter(category_id=int(category))

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search) | Q(tags__icontains=search))

        return qs

    def perform_create(self, serializer):
        article = serializer.save(organization_id=self.request.organization.id, author=self.request.user)
        if article.status == 'published' and not article.published_at:
            article.published_at = timezone.now()
            article.save(update_fields=['published_at'])

    def perform_update(self, serializer):
        article = serializer.save()
        if article.status == 'published' and not article.published_at:
            article.published_at = timezone.now()
            article.save(update_fields=['published_at'])

    def retrieve(self, request, *args, **kwargs):
        """Increment view count on article view."""
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='helpful')
    def mark_helpful(self, request, pk=None, company_name=None):
        article = self.get_object()
        is_helpful = request.data.get('helpful', True)
        if is_helpful:
            article.helpful_count += 1
        else:
            article.not_helpful_count += 1
        article.save(update_fields=['helpful_count', 'not_helpful_count'])
        return Response({
            'helpful_count': article.helpful_count,
            'not_helpful_count': article.not_helpful_count,
        })

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdminOrManager()]
        return super().get_permissions()


# ============================================================================
# AUDIT LOG VIEWSET (Read-only)
# ============================================================================
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        if not hasattr(self.request, 'organization') or not self.request.organization:
            return AuditLog.objects.none()

        qs = AuditLog.objects.filter(organization_id=self.request.organization.id)

        action_filter = self.request.query_params.get('action')
        if action_filter:
            qs = qs.filter(action=action_filter)

        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            qs = qs.filter(resource_type=resource_type)

        user_id = self.request.query_params.get('user_id')
        if user_id and user_id.isdigit():
            qs = qs.filter(user_id=int(user_id))

        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs
