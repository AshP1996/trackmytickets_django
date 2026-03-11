"""
Centralized Email Notification Service for TrackMyTicket.
All email credentials are read dynamically from Django settings (which come from .env).
"""
import logging
import threading
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('apps')


def _get_base_context():
    """Base context available in all email templates."""
    return {
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'year': datetime.now().year,
    }


def send_templated_email(subject, template_name, context, to_emails, fail_silently=True):
    """
    Render an HTML email template and send it.
    Runs in a background thread to avoid blocking the request.
    """
    if not to_emails:
        return False

    if isinstance(to_emails, str):
        to_emails = [to_emails]

    full_context = _get_base_context()
    full_context.update(context)

    try:
        html_content = render_to_string(template_name, full_context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        if not from_email:
            logger.warning('DEFAULT_FROM_EMAIL not configured, skipping email')
            return False

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_emails)
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=fail_silently)
        logger.info(f'Email sent: "{subject}" to {to_emails}')
        return True
    except Exception as e:
        logger.error(f'Failed to send email "{subject}" to {to_emails}: {e}')
        return False


def _send_async(subject, template_name, context, to_emails):
    """Send email in a background thread so it doesn't block the HTTP response."""
    thread = threading.Thread(
        target=send_templated_email,
        args=(subject, template_name, context, to_emails),
        daemon=True,
    )
    thread.start()


# ============================================================================
# ORGANIZATION NOTIFICATIONS
# ============================================================================

def send_org_created_email(org, admin_email, admin_name, admin_password, notify_superadmin_email=None):
    """Send email when a new organization is created."""
    context = {
        'org_name': org.name,
        'subdomain': org.subdomain,
        'plan': getattr(org, 'plan', 'Free'),
        'admin_name': admin_name,
        'admin_email': admin_email,
        'admin_password': admin_password,
    }

    # Send to the new org admin
    _send_async(
        f'🏢 Welcome to TrackMyTicket — {org.name}',
        'emails/organization_created.html',
        context,
        [admin_email],
    )

    # Send to superadmin if specified
    if notify_superadmin_email:
        _send_async(
            f'🏢 New Organization Created: {org.name}',
            'emails/organization_created.html',
            context,
            [notify_superadmin_email],
        )


# ============================================================================
# USER NOTIFICATIONS
# ============================================================================

def send_user_welcome_email(user, password, org):
    """Send welcome email with login credentials to a new user."""
    context = {
        'user_name': user.full_name,
        'user_email': user.email,
        'password': password,
        'org_name': org.name,
        'subdomain': org.subdomain,
        'role': getattr(user, 'role', 'agent'),
        'department': getattr(user, 'department', None),
    }
    # Try to get department name
    if hasattr(user, 'department') and user.department:
        try:
            context['department'] = user.department.name if hasattr(user.department, 'name') else str(user.department)
        except Exception:
            context['department'] = None

    _send_async(
        f'👋 Welcome to {org.name} — TrackMyTicket',
        'emails/user_welcome.html',
        context,
        [user.email],
    )


def send_user_updated_email(user, changes, org):
    """Send email when a user's account is updated."""
    context = {
        'user_name': user.full_name,
        'org_name': org.name,
        'subdomain': org.subdomain,
        'changes': changes,
    }
    _send_async(
        f'🔄 Account Updated — TrackMyTicket',
        'emails/user_updated.html',
        context,
        [user.email],
    )


def send_user_deactivated_email(user, org):
    """Send email when a user's account is deactivated."""
    context = {
        'user_name': user.full_name,
        'org_name': org.name,
    }
    _send_async(
        '🚫 Account Deactivated — TrackMyTicket',
        'emails/user_deactivated.html',
        context,
        [user.email],
    )


# ============================================================================
# TICKET NOTIFICATIONS
# ============================================================================

def send_ticket_created_email(ticket, assignee_email=None):
    """Send email when a new ticket is created (to the assignee)."""
    if not assignee_email and ticket.assigned_to:
        assignee_email = ticket.assigned_to.email

    if not assignee_email:
        return

    subdomain = ''
    try:
        if hasattr(ticket, 'organization') and ticket.organization:
            subdomain = ticket.organization.subdomain
    except Exception:
        pass

    context = {
        'ticket_id': ticket.ticket_id or ticket.id,
        'subject': ticket.subject,
        'description': ticket.description or '',
        'priority': ticket.priority or 'medium',
        'ticket_type': getattr(ticket, 'ticket_type', 'Issue'),
        'sender_name': ticket.sender_name or '',
        'sender_email': ticket.sender_email or '',
        'project_name': ticket.project.name if hasattr(ticket, 'project') and ticket.project else '',
        'department_name': ticket.department.name if hasattr(ticket, 'department') and ticket.department else '',
        'subdomain': subdomain,
    }
    _send_async(
        f'🎫 New Ticket: {ticket.ticket_id} — {ticket.subject}',
        'emails/ticket_created.html',
        context,
        [assignee_email],
    )


def send_ticket_deleted_email(ticket_id, subject, creator_email, deleter_name, org):
    """Send email when a ticket is deleted."""
    if not creator_email:
        return

    context = {
        'ticket_id': ticket_id,
        'subject': subject,
        'deleter_name': deleter_name,
        'org_name': org.name if org else '',
        'subdomain': org.subdomain if org else '',
    }
    
    # Notify just the creator; the deleter already knows they deleted it
    # But as per user request "who created the ticket and who deleted the ticket send notification"
    _send_async(
        f'🗑️ Ticket Deleted: {ticket_id} — {subject}',
        'emails/ticket_deleted.html',
        context,
        [creator_email],
    )


def send_ticket_assigned_email(ticket, assignee, actor=None, action='assigned'):
    """Send email when a ticket is assigned/reassigned."""
    if not assignee or not hasattr(assignee, 'email'):
        return

    subdomain = ''
    try:
        if hasattr(ticket, 'organization') and ticket.organization:
            subdomain = ticket.organization.subdomain
    except Exception:
        pass

    context = {
        'ticket_id': ticket.ticket_id or ticket.id,
        'subject': ticket.subject,
        'priority': ticket.priority or 'medium',
        'status': ticket.status or 'open',
        'actor_name': actor.full_name if actor and hasattr(actor, 'full_name') else 'System',
        'action': action,
        'subdomain': subdomain,
    }
    _send_async(
        f'👤 Ticket {action}: {ticket.ticket_id} — {ticket.subject}',
        'emails/ticket_assigned.html',
        context,
        [assignee.email],
    )


def send_ticket_status_changed_email(ticket, old_status, new_status, actor=None, notify_emails=None):
    """Send email when a ticket status changes."""
    if not notify_emails:
        notify_emails = []
        if ticket.assigned_to and hasattr(ticket.assigned_to, 'email'):
            notify_emails.append(ticket.assigned_to.email)

    if not notify_emails:
        return

    subdomain = ''
    try:
        if hasattr(ticket, 'organization') and ticket.organization:
            subdomain = ticket.organization.subdomain
    except Exception:
        pass

    context = {
        'ticket_id': ticket.ticket_id or ticket.id,
        'subject': ticket.subject,
        'old_status': old_status,
        'new_status': new_status,
        'old_status_display': (old_status or '').replace('_', ' ').title(),
        'new_status_display': (new_status or '').replace('_', ' ').title(),
        'priority': ticket.priority or 'medium',
        'actor_name': actor.full_name if actor and hasattr(actor, 'full_name') else 'System',
        'assigned_to_name': ticket.assigned_to.full_name if ticket.assigned_to else '',
        'subdomain': subdomain,
    }
    _send_async(
        f'🔄 Status Changed: {ticket.ticket_id} → {context["new_status_display"]}',
        'emails/ticket_status_changed.html',
        context,
        notify_emails,
    )


def send_ticket_comment_email(ticket, comment_text, actor=None, is_internal=False, notify_emails=None):
    """Send email when a comment is added to a ticket."""
    if not notify_emails:
        notify_emails = []
        if ticket.assigned_to and hasattr(ticket.assigned_to, 'email'):
            notify_emails.append(ticket.assigned_to.email)

    if not notify_emails:
        return

    subdomain = ''
    try:
        if hasattr(ticket, 'organization') and ticket.organization:
            subdomain = ticket.organization.subdomain
    except Exception:
        pass

    context = {
        'ticket_id': ticket.ticket_id or ticket.id,
        'subject': ticket.subject,
        'comment_text': comment_text,
        'actor_name': actor.full_name if actor and hasattr(actor, 'full_name') else 'Someone',
        'is_internal': is_internal,
        'subdomain': subdomain,
    }
    _send_async(
        f'💬 New Comment on {ticket.ticket_id}: {ticket.subject}',
        'emails/ticket_comment.html',
        context,
        notify_emails,
    )


# ============================================================================
# FORGOT PASSWORD OTP
# ============================================================================

def send_forgot_password_otp_email(email, otp, user_name=''):
    """Send HTML OTP email for password reset."""
    context = {
        'otp': otp,
        'user_name': f' {user_name}' if user_name else '',
    }
    _send_async(
        '🔑 Password Reset OTP — TrackMyTicket',
        'emails/forgot_password_otp.html',
        context,
        [email],
    )


# ============================================================================
# FEEDBACK
# ============================================================================

def send_feedback_email(feedback, org, admin_emails=None):
    """Send email to org admins when feedback is submitted."""
    if not admin_emails:
        try:
            from apps.accounts.models import User
            admins = User.objects.filter(role='admin', is_active=True).values_list('email', flat=True)
            admin_emails = list(admins)
        except Exception:
            admin_emails = []

    if not admin_emails:
        return

    context = {
        'user_name': feedback.user.full_name if hasattr(feedback, 'user') and feedback.user else 'Anonymous',
        'user_email': feedback.user.email if hasattr(feedback, 'user') and feedback.user else '',
        'rating': getattr(feedback, 'rating', 0),
        'feedback_text': getattr(feedback, 'message', '') or getattr(feedback, 'text', ''),
        'submitted_at': feedback.created_at.strftime('%b %d, %Y %H:%M') if hasattr(feedback, 'created_at') else '',
        'subdomain': org.subdomain if org else '',
        'org_name': org.name if org else '',
    }
    _send_async(
        f'📝 New Feedback from {context["user_name"]}',
        'emails/feedback_received.html',
        context,
        admin_emails,
    )
