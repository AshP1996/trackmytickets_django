"""
Tenant Isolation Migration for accounts app.

Converts User.organization and Department.organization from ForeignKey → IntegerField.
The underlying DB column (organization_id) is UNCHANGED — only Django's migration
state is updated via SeparateDatabaseAndState operations.

Also removes old UniqueConstraints and email unique logic that referenced the FK.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_organization_plan'),
    ]

    operations = [
        # ── Step 1: Remove old constraints that reference the FK ──
        migrations.RemoveConstraint(
            model_name='department',
            name='uq_department_name_org',
        ),
        migrations.RemoveConstraint(
            model_name='user',
            name='uq_user_email_org',
        ),

        # ── Step 2: Convert ForeignKey → IntegerField (state-only) ──
        # The actual DB column stays the same: organization_id INTEGER.
        # We use SeparateDatabaseAndState so Django doesn't remake the table.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='user',
                    name='organization',
                ),
                migrations.AddField(
                    model_name='user',
                    name='organization_id',
                    field=models.IntegerField(default=0),
                ),
                migrations.RemoveField(
                    model_name='department',
                    name='organization',
                ),
                migrations.AddField(
                    model_name='department',
                    name='organization_id',
                    field=models.IntegerField(default=0),
                ),
            ],
            database_operations=[
                # No DB changes needed — column already exists as organization_id
            ],
        ),

        # ── Step 3: Make email unique per DB (each tenant DB = one org) ──
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True, db_index=True),
        ),
    ]
