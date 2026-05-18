/**
 * Platform dashboard UI: panels, charts, analytics widgets.
 */
(function () {
    const PANEL_TITLES = {
        overview: 'Platform overview',
        organizations: 'Organizations',
        enquiries: 'Enquiries',
    };

    let charts = { growth: null, status: null, plan: null };
    let lastStats = null;

    const fmt = (n) => (n == null || Number.isNaN(n) ? '0' : Number(n).toLocaleString());
    const planLabel = (key) => {
        const labels = {
            starter_trial: 'Starter Trial',
            growth_cluster: 'Growth Cluster',
            free: 'Free',
        };
        return labels[key] || (key || 'Unknown').replace(/_/g, ' ');
    };
    const statusLabel = (key) => (key || 'unknown').replace(/_/g, ' ');

    function switchPanel(name) {
        document.querySelectorAll('.pd-panel').forEach((el) => {
            el.classList.toggle('active', el.id === `panel-${name}`);
        });
        document.querySelectorAll('.pd-nav-item[data-panel]').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.panel === name);
        });
        const title = document.getElementById('pd-page-title');
        if (title) title.textContent = PANEL_TITLES[name] || 'Dashboard';
        if (window.innerWidth < 900) {
            document.getElementById('pd-sidebar')?.classList.remove('open');
        }
    }

    window.switchPanel = switchPanel;

    function destroyChart(key) {
        if (charts[key]) {
            charts[key].destroy();
            charts[key] = null;
        }
    }

    function renderOrgGrowth(series) {
        const canvas = document.getElementById('chart-org-growth');
        if (!canvas || typeof Chart === 'undefined') return;
        destroyChart('growth');
        const labels = (series && series.length) ? series.map((r) => r.label) : ['No data'];
        const data = (series && series.length) ? series.map((r) => r.count) : [0];
        charts.growth = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'New organizations',
                    data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.12)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#6366f1',
                }],
            },
            options: chartOptions(false),
        });
    }

    function renderTicketStatus(byStatus) {
        const canvas = document.getElementById('chart-ticket-status');
        if (!canvas || typeof Chart === 'undefined') return;
        destroyChart('status');
        const entries = Object.entries(byStatus || {});
        const labels = entries.length ? entries.map(([k]) => statusLabel(k)) : ['No tickets'];
        const data = entries.length ? entries.map(([, v]) => v) : [1];
        const colors = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'];
        charts.status = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors.slice(0, labels.length), borderWidth: 0 }],
            },
            options: chartOptions(true),
        });
    }

    function renderPlanChart(byPlan) {
        const canvas = document.getElementById('chart-plan');
        if (!canvas || typeof Chart === 'undefined') return;
        destroyChart('plan');
        const entries = Object.entries(byPlan || {});
        const labels = entries.length ? entries.map(([k]) => planLabel(k)) : ['No orgs'];
        const data = entries.length ? entries.map(([, v]) => v) : [1];
        charts.plan = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b'],
                    borderWidth: 0,
                }],
            },
            options: chartOptions(true),
        });
    }

    function chartOptions(isDoughnut) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: isDoughnut,
                    position: 'bottom',
                    labels: { boxWidth: 10, padding: 12, font: { size: 11 } },
                },
            },
            scales: isDoughnut ? {} : {
                y: { beginAtZero: true, ticks: { precision: 0 } },
                x: { grid: { display: false } },
            },
        };
    }

    function renderTopOrgs(list) {
        const el = document.getElementById('top-orgs-list');
        if (!el) return;
        if (!list || !list.length) {
            el.innerHTML = '<p class="text-muted mb-0 small">No ticket data yet.</p>';
            return;
        }
        const base = window.location.origin;
        el.innerHTML = list.map((org, i) => `
            <div class="pd-top-org">
                <div class="pd-top-org-info">
                    <strong>${i + 1}. ${escapeHtml(org.name)}</strong>
                    <span>/${escapeHtml(org.subdomain)} · ${org.is_active ? '<span class="pd-badge pd-badge-success">Active</span>' : '<span class="pd-badge pd-badge-warning">Suspended</span>'}</span>
                </div>
                <div class="pd-top-org-stats">
                    <span title="Tickets"><i class="fas fa-ticket-alt"></i> ${fmt(org.tickets)}</span>
                    <span title="Users"><i class="fas fa-users"></i> ${fmt(org.users)}</span>
                    <a href="${base}/${org.subdomain}/dashboard" target="_blank" class="pd-btn pd-btn-secondary btn-sm" style="padding:0.25rem 0.5rem;font-size:0.7rem">Open</a>
                </div>
            </div>
        `).join('');
    }

    function renderRecentEnquiries(list) {
        const el = document.getElementById('recent-enquiries-list');
        if (!el) return;
        if (!list || !list.length) {
            el.innerHTML = '<p class="text-muted mb-0 small">No enquiries yet.</p>';
            return;
        }
        el.innerHTML = list.map((eq) => {
            const date = eq.created_at ? new Date(eq.created_at).toLocaleDateString() : '';
            const unread = !eq.is_read;
            return `
                <div class="pd-enquiry-item${unread ? ' unread' : ''}">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <div>
                            <strong>${escapeHtml(eq.name)}</strong>
                            ${unread ? '<span class="pd-badge pd-badge-danger ms-1">New</span>' : ''}
                            <div class="small text-muted">${escapeHtml(eq.email)}${eq.company ? ' · ' + escapeHtml(eq.company) : ''}</div>
                        </div>
                        <span class="small text-muted">${date}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderMiniStats(stats) {
        const el = document.getElementById('pd-mini-stats');
        if (!el) return;
        const extDb = stats.integrations?.external_databases ?? 0;
        const activeUsers = stats.users?.active ?? 0;
        const enq7 = stats.enquiries?.last_7_days ?? 0;
        const priority = stats.tickets?.by_priority || {};
        const priorityHtml = Object.entries(priority).slice(0, 4).map(([k, v]) =>
            `<span class="pd-mini-chip"><strong>${escapeHtml(statusLabel(k))}</strong> ${fmt(v)}</span>`
        ).join('') || '<span class="pd-mini-chip text-muted">No priority breakdown</span>';

        el.innerHTML = `
            <div class="pd-card">
                <div class="pd-card-header"><h3>Platform insights</h3></div>
                <div class="pd-card-body pd-mini-stats-body">
                    <div class="pd-mini-stat"><i class="fas fa-user-check"></i><div><span>Active users</span><strong>${fmt(activeUsers)}</strong></div></div>
                    <div class="pd-mini-stat"><i class="fas fa-database"></i><div><span>External DB connections</span><strong>${fmt(extDb)}</strong></div></div>
                    <div class="pd-mini-stat"><i class="fas fa-inbox"></i><div><span>Enquiries (7 days)</span><strong>${fmt(enq7)}</strong></div></div>
                    <div class="pd-mini-stat pd-mini-stat--wide"><i class="fas fa-flag"></i><div><span>Tickets by priority</span><div class="pd-mini-chips">${priorityHtml}</div></div></div>
                </div>
            </div>
        `;
    }

    function escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function applyStatsToDom(stats) {
        lastStats = stats;
        const orgs = stats.organizations || {};
        const users = stats.users || {};
        const tickets = stats.tickets || {};
        const enquiries = stats.enquiries || {};
        const projects = stats.projects || {};

        setText('total-orgs', fmt(orgs.total ?? stats.total_organizations));
        setText('meta-orgs', `${fmt(orgs.active ?? stats.active_organizations)} active · ${fmt(orgs.suspended)} suspended`);
        setText('total-users', fmt(users.total ?? stats.total_users));
        setText('meta-users', `${fmt(users.active)} active users`);
        setText('total-tickets', fmt(tickets.total ?? stats.total_tickets));
        setText('meta-tickets', 'includes external DB counts');
        setText('total-projects', fmt(projects.total));
        setText('total-enquiries', fmt(enquiries.total));
        setText('unread-enquiries', `${fmt(enquiries.unread)} unread`);
        setText('orgs-30d', fmt(orgs.last_30_days));
        setText('meta-suspended', `${fmt(orgs.suspended)} suspended total`);

        const badge = document.getElementById('nav-unread-badge');
        if (badge) {
            const unread = enquiries.unread || 0;
            badge.textContent = unread > 99 ? '99+' : String(unread);
            badge.style.display = unread > 0 ? 'inline-flex' : 'none';
        }

        const updated = document.getElementById('stats-updated-at');
        if (updated) updated.textContent = `Last updated ${new Date().toLocaleString()}`;

        renderOrgGrowth(orgs.growth);
        renderTicketStatus(tickets.by_status);
        renderPlanChart(orgs.by_plan);
        renderTopOrgs(stats.top_organizations);
        renderRecentEnquiries(enquiries.recent);
        renderMiniStats(stats);
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    window.renderPlatformAnalytics = applyStatsToDom;

    async function refreshAll() {
        const btn = document.getElementById('refresh-all-btn');
        if (btn) {
            btn.disabled = true;
            btn.querySelector('i')?.classList.add('fa-spin');
        }
        try {
            await loadPlatformStats();
            await loadOrganizations(currentOrgPage, currentOrgPageSize);
            await loadEnquiries(showUnreadOnly, currentEnqPage, currentEnqPageSize);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.querySelector('i')?.classList.remove('fa-spin');
            }
        }
    }

    window.logout = function logout() {
        localStorage.removeItem('platform_access_token');
        window.location.href = '/platform/login';
    };

    document.addEventListener('DOMContentLoaded', async function () {
        document.querySelectorAll('.pd-nav-item[data-panel]').forEach((btn) => {
            btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
        });
        document.querySelectorAll('[data-panel-jump]').forEach((btn) => {
            btn.addEventListener('click', () => switchPanel(btn.dataset.panelJump));
        });

        document.getElementById('pd-menu-toggle')?.addEventListener('click', () => {
            document.getElementById('pd-sidebar')?.classList.toggle('open');
        });

        document.getElementById('refresh-all-btn')?.addEventListener('click', refreshAll);

        try {
            const me = await platformAPI.getMe();
            const emailEl = document.getElementById('platform-admin-email-sidebar');
            if (emailEl && me.email) emailEl.textContent = me.email;
        } catch (e) {
            console.error('Failed to load admin profile', e);
        }
    });
})();
