"""
Tenant Isolation Migration for tickets app.

Converts all Organization ForeignKeys → IntegerField using SeparateDatabaseAndState.
Also removes db_constraint=False from User/Department FKs (now same DB).
Drops and recreates all related indexes and constraints.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_add_sla_due_date_indexes'),
        ('accounts', '0003_tenant_isolation'),
    ]

    operations = [
        # ── Step 1: Remove old constraints that reference Organization FK ──
        migrations.RemoveConstraint(model_name='kbarticle', name='uq_kb_article_slug_org'),
        migrations.RemoveConstraint(model_name='kbcategory', name='uq_kb_cat_slug_org'),
        migrations.RemoveConstraint(model_name='project', name='uq_project_key_org'),
        migrations.RemoveConstraint(model_name='slapolicy', name='uq_sla_org_priority'),
        migrations.RemoveConstraint(model_name='tag', name='uq_tag_name_org'),
        migrations.RemoveConstraint(model_name='ticket', name='uq_ticket_id_org'),

        # Remove old indexes
        migrations.RemoveIndex(model_name='auditlog', name='audit_logs_organiz_9c5b7f_idx'),
        migrations.RemoveIndex(model_name='auditlog', name='audit_logs_organiz_d52064_idx'),
        migrations.RemoveIndex(model_name='kbarticle', name='kb_articles_organiz_1a5efc_idx'),
        migrations.RemoveIndex(model_name='kbarticle', name='kb_articles_organiz_cbdb32_idx'),
        migrations.RemoveIndex(model_name='project', name='projects_organiz_896a0c_idx'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_status'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_project'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_assigned_org'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_created'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_priority'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_type'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_sla_deadline'),
        migrations.RemoveIndex(model_name='ticket', name='idx_ticket_org_due_date'),

        # ── Step 2: Convert all organization ForeignKeys → IntegerField (state-only) ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # AuditLog
                migrations.RemoveField(model_name='auditlog', name='organization'),
                migrations.AddField(model_name='auditlog', name='organization_id',
                    field=models.IntegerField(default=0)),
                # CannedResponse
                migrations.RemoveField(model_name='cannedresponse', name='organization'),
                migrations.AddField(model_name='cannedresponse', name='organization_id',
                    field=models.IntegerField(default=0)),
                # KBArticle
                migrations.RemoveField(model_name='kbarticle', name='organization'),
                migrations.AddField(model_name='kbarticle', name='organization_id',
                    field=models.IntegerField(default=0)),
                # KBCategory
                migrations.RemoveField(model_name='kbcategory', name='organization'),
                migrations.AddField(model_name='kbcategory', name='organization_id',
                    field=models.IntegerField(default=0)),
                # Project
                migrations.RemoveField(model_name='project', name='organization'),
                migrations.AddField(model_name='project', name='organization_id',
                    field=models.IntegerField(default=0)),
                # SLAPolicy
                migrations.RemoveField(model_name='slapolicy', name='organization'),
                migrations.AddField(model_name='slapolicy', name='organization_id',
                    field=models.IntegerField(default=0)),
                # Tag
                migrations.RemoveField(model_name='tag', name='organization'),
                migrations.AddField(model_name='tag', name='organization_id',
                    field=models.IntegerField(default=0)),
                # Ticket
                migrations.RemoveField(model_name='ticket', name='organization'),
                migrations.AddField(model_name='ticket', name='organization_id',
                    field=models.IntegerField(default=0)),
            ],
            database_operations=[
                # No DB changes — column organization_id already exists in all tables
            ],
        ),

        # ── Step 3: Remove db_constraint=False from User/Department FKs ──
        # User and Department are now in the same tenant DB, so real FKs are safe.
        migrations.AlterField(
            model_name='attachment',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cannedresponse',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='kbarticle',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='project',
            name='default_assignee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='default_projects', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='project',
            name='lead_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='led_projects', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='assigned_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_tickets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='accounts.department'),
        ),
        migrations.AlterField(
            model_name='tickethistory',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_actions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticketwatcher',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='watched_tickets', to=settings.AUTH_USER_MODEL),
        ),

        # ── Step 4: Recreate indexes with organization_id IntegerField ──
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['organization_id', 'action'], name='audit_logs_organiz_9c5b7f_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['organization_id', 'resource_type'], name='audit_logs_organiz_d52064_idx'),
        ),
        migrations.AddIndex(
            model_name='kbarticle',
            index=models.Index(fields=['organization_id', 'status'], name='kb_articles_organiz_1a5efc_idx'),
        ),
        migrations.AddIndex(
            model_name='kbarticle',
            index=models.Index(fields=['organization_id', 'category'], name='kb_articles_organiz_cbdb32_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['organization_id'], name='projects_organiz_896a0c_idx'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'status'], name='idx_ticket_org_status'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'project'], name='idx_ticket_org_project'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'assigned_to'], name='idx_ticket_assigned_org'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'created_at'], name='idx_ticket_org_created'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'priority'], name='idx_ticket_org_priority'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'ticket_type'], name='idx_ticket_org_type'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'sla_resolution_deadline'], name='idx_ticket_org_sla_deadline'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['organization_id', 'due_date'], name='idx_ticket_org_due_date'),
        ),

        # ── Step 5: Recreate constraints with organization_id IntegerField ──
        migrations.AddConstraint(
            model_name='kbarticle',
            constraint=models.UniqueConstraint(fields=['slug', 'organization_id'], name='uq_kb_article_slug_org'),
        ),
        migrations.AddConstraint(
            model_name='kbcategory',
            constraint=models.UniqueConstraint(fields=['slug', 'organization_id'], name='uq_kb_cat_slug_org'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=['key', 'organization_id'], name='uq_project_key_org'),
        ),
        migrations.AddConstraint(
            model_name='slapolicy',
            constraint=models.UniqueConstraint(fields=['organization_id', 'priority'], name='uq_sla_org_priority'),
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(fields=['name', 'organization_id'], name='uq_tag_name_org'),
        ),
        migrations.AddConstraint(
            model_name='ticket',
            constraint=models.UniqueConstraint(fields=['ticket_id', 'organization_id'], name='uq_ticket_id_org'),
        ),
    ]
