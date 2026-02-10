from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.tickets.models import Ticket

# ============================================================================
# COMMENT MODEL
# ============================================================================
class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'comments'

    def __str__(self):
        return f"Comment by {self.user} on {self.ticket}"
