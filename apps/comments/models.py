from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.tickets.models import Ticket

# ============================================================================
# COMMENT MODEL — lives in TENANT DB
# ============================================================================
class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='comments')
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user} on {self.ticket}"
