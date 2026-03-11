"""
Tenant Isolation Migration for notifications app.
Removes db_constraint=False from Notification.user and Notification.actor FKs.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_alter_notification_actor_alter_notification_user'),
        ('accounts', '0003_tenant_isolation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='notification',
            name='actor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='actor_notifications',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
