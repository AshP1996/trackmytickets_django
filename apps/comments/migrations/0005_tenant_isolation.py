"""
Tenant Isolation Migration for comments app.
Removes db_constraint=False from Comment.user FK — User is now in the same tenant DB.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0004_alter_comment_options_comment_edited_at_and_more'),
        ('accounts', '0003_tenant_isolation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='comments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
