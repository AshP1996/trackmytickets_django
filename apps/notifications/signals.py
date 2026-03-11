import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tickets.models import TicketHistory, TicketWatcher
from apps.notifications.models import Notification

logger = logging.getLogger('apps')


def _get_watchers_to_notify(ticket, exclude_user=None):
    """Get all watchers of a ticket, excluding the actor."""
    watcher_users = TicketWatcher.objects.filter(ticket=ticket).select_related('user')
    users = set()
    for w in watcher_users:
        if w.user and w.user != exclude_user:
            users.add(w.user)
    return users


def _create_notification(user, actor, ticket, notification_type, message):
    """Helper to create a notification safely."""
    try:
        Notification.objects.create(
            user=user,
            actor=actor,
            ticket=ticket,
            type=notification_type,
            message=message,
            link=f"/tickets/{ticket.ticket_id}"
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")


@receiver(post_save, sender=TicketHistory)
def create_notification_from_history(sender, instance, created, **kwargs):
    if not created:
        return

    ticket = instance.ticket
    actor = instance.user
    action = instance.action

    # Collect users to notify (watchers + specific targets)
    notified_users = set()

    # Import email service (lazy to avoid circular imports)
    from apps.notifications.email_service import (
        send_ticket_assigned_email,
        send_ticket_status_changed_email,
        send_ticket_comment_email,
    )

    # 1. Assignment Notification
    if action in ['assigned', 'reassigned'] and ticket.assigned_to:
        if ticket.assigned_to != actor:
            _create_notification(
                ticket.assigned_to, actor, ticket, 'assigned',
                f"You have been assigned to ticket {ticket.ticket_id}: {ticket.subject}"
            )
            notified_users.add(ticket.assigned_to)

            # ✉️ Send assignment email
            send_ticket_assigned_email(
                ticket, ticket.assigned_to, actor=actor,
                action='assigned' if action == 'assigned' else 'reassigned'
            )

    # 2. Comment Notification
    if action == 'added_comment':
        comment_text = instance.new_value or ''
        email_recipients = []

        # Notify assignee if they didn't write the comment
        if ticket.assigned_to and ticket.assigned_to != actor:
            _create_notification(
                ticket.assigned_to, actor, ticket, 'comment',
                f"New comment on ticket {ticket.ticket_id} by {actor.full_name if actor else 'System'}"
            )
            notified_users.add(ticket.assigned_to)
            email_recipients.append(ticket.assigned_to.email)

        # Notify ticket creator
        from apps.accounts.models import User
        try:
            creator = User.objects.filter(email=ticket.sender_email).first()
            if creator and creator != actor and creator not in notified_users:
                _create_notification(
                    creator, actor, ticket, 'comment',
                    f"New comment on ticket {ticket.ticket_id}"
                )
                notified_users.add(creator)
                if creator.email not in email_recipients:
                    email_recipients.append(creator.email)
        except Exception:
            pass

        # ✉️ Send comment email
        if email_recipients:
            is_internal = 'internal' in (instance.new_value or '').lower() if instance.new_value else False
            send_ticket_comment_email(
                ticket, comment_text, actor=actor,
                is_internal=is_internal, notify_emails=email_recipients
            )

    # 3. Status Change Notification
    if action == 'status_changed':
        new_status = instance.new_value or ''
        old_status = instance.old_value or ''
        status_display = new_status.replace('_', ' ').title()
        email_recipients = []

        if ticket.assigned_to and ticket.assigned_to != actor:
            _create_notification(
                ticket.assigned_to, actor, ticket, 'status_change',
                f"Ticket {ticket.ticket_id} status changed to {status_display}"
            )
            notified_users.add(ticket.assigned_to)
            email_recipients.append(ticket.assigned_to.email)

        # Notify ticket creator
        from apps.accounts.models import User
        try:
            creator = User.objects.filter(email=ticket.sender_email).first()
            if creator and creator != actor and creator not in notified_users:
                _create_notification(
                    creator, actor, ticket, 'status_change',
                    f"Ticket {ticket.ticket_id} is now {status_display}"
                )
                notified_users.add(creator)
                if creator.email not in email_recipients:
                    email_recipients.append(creator.email)
        except Exception:
            pass

        # ✉️ Send status change email
        if email_recipients:
            send_ticket_status_changed_email(
                ticket, old_status, new_status, actor=actor,
                notify_emails=email_recipients
            )

    # 4. Priority Change Notification
    if action == 'priority_changed':
        new_priority = instance.new_value or ''
        if ticket.assigned_to and ticket.assigned_to != actor:
            _create_notification(
                ticket.assigned_to, actor, ticket, 'priority_change',
                f"Ticket {ticket.ticket_id} priority changed to {new_priority.title()}"
            )
            notified_users.add(ticket.assigned_to)

    # 5. Merged Notification
    if action == 'merged':
        if ticket.assigned_to and ticket.assigned_to != actor:
            _create_notification(
                ticket.assigned_to, actor, ticket, 'merged',
                f"Ticket {ticket.ticket_id}: {instance.new_value}"
            )
            notified_users.add(ticket.assigned_to)

    # 6. Notify ALL WATCHERS who haven't been notified yet
    if action in ['assigned', 'reassigned', 'added_comment', 'status_changed', 'priority_changed', 'merged']:
        watchers_to_notify = _get_watchers_to_notify(ticket, exclude_user=actor)
        for watcher_user in watchers_to_notify:
            if watcher_user not in notified_users:
                action_display = action.replace('_', ' ').title()
                _create_notification(
                    watcher_user, actor, ticket, 'watcher',
                    f"[Watched] {action_display} on {ticket.ticket_id}: {ticket.subject}"
                )
