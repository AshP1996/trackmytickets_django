from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.tickets.models import Ticket

# ============================================================================
# NOTIFICATION MODEL
# ============================================================================
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_index=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actor_notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    type = models.CharField(max_length=50) # 'assigned', 'comment', 'status_change', 'generic'
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False, db_index=True)
    link = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"Notification for {self.user}: {self.message}"
