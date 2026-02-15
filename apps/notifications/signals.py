from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tickets.models import TicketHistory
from apps.notifications.models import Notification

@receiver(post_save, sender=TicketHistory)
def create_notification_from_history(sender, instance, created, **kwargs):
    if not created:
        return

    ticket = instance.ticket
    actor = instance.user
    action = instance.action
    
    # 1. Assignment Notification
    if action in ['assigned', 'reassigned'] and ticket.assigned_to:
        # Notify the assigned user
        if ticket.assigned_to != actor:
            Notification.objects.create(
                user=ticket.assigned_to,
                actor=actor,
                ticket=ticket,
                type='assigned',
                message=f"You have been assigned to ticket {ticket.ticket_id}: {ticket.subject}",
                link=f"/tickets/{ticket.ticket_id}"
            )

    # 2. Comment Notification
    if action == 'added_comment':
        # Notify assignee if they didn't write the comment
        if ticket.assigned_to and ticket.assigned_to != actor:
             Notification.objects.create(
                user=ticket.assigned_to,
                actor=actor,
                ticket=ticket,
                type='comment',
                message=f"New comment on ticket {ticket.ticket_id} by {actor.full_name if actor else 'System'}",
                link=f"/tickets/{ticket.ticket_id}"
            )
            
        # Notify ticket creator (sender) if they are a registered user and didn't write the comment
        # Note: sender_email is text, but we can try to find user by email or if we have a created_by field?
        # Ticket model doesn't have created_by FK, just sender_email.
        # But we do have users.
        # Let's check if sender_email matches a User in the same organization
        from apps.accounts.models import User
        try:
            creator = User.objects.filter(email=ticket.sender_email, organization=ticket.organization).first()
            if creator and creator != actor and creator != ticket.assigned_to:
                 Notification.objects.create(
                    user=creator,
                    actor=actor,
                    ticket=ticket,
                    type='comment',
                    message=f"New comment on ticket {ticket.ticket_id}",
                    link=f"/tickets/{ticket.ticket_id}"
                )
        except Exception:
            pass
