// Platform Admin API Client
class PlatformAPIClient {
    constructor() {
        this.baseURL = (window.APP_CONFIG && window.APP_CONFIG.BASE_URL) ? window.APP_CONFIG.BASE_URL : window.location.origin;
        this.token = localStorage.getItem('platform_access_token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('platform_access_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('platform_access_token');
        window.location.href = '/platform/login';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
                ...(options.headers || {})
            }
        };

        try {
            const response = await fetch(url, config);
            const contentType = response.headers.get('content-type');
            let data;

            // Try to parse as JSON first
            try {
                const text = await response.text();
                if (text) {
                    data = JSON.parse(text);
                } else {
                    data = {};
                }
            } catch (parseError) {
                // If not JSON, check content type
                if (contentType && contentType.includes('application/json')) {
                    throw new Error('Failed to parse JSON response');
                } else {
                    // Non-JSON response - might be HTML error page
                    throw new Error(`Server returned invalid response format (${contentType || 'unknown'})`);
                }
            }

            if (!response.ok) {
                if (response.status === 401) {
                    this.clearToken();
                    throw new Error('Authentication failed. Please login again.');
                }
                const errorMsg = data.error || data.msg || data.message || `Request failed with status ${response.status}`;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            // Re-throw with more context if it's a network error
            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new Error('Network error: Could not connect to server');
            }
            throw error;
        }
    }

    async getMe() {
        return this.request('/api/platform/me', { method: 'GET' });
    }

    async getOrganizations(page = 1, pageSize = 10, search = '') {
        let query = `?page=${page}&page_size=${pageSize}`;
        if (search) query += `&search=${encodeURIComponent(search)}`;
        return this.request(`/api/platform/organizations${query}`, { method: 'GET' });
    }

    async getEnquiries(unreadOnly = false, page = 1, pageSize = 10) {
        let query = `?page=${page}&page_size=${pageSize}`;
        if (unreadOnly) query += '&unread_only=true';
        return this.request(`/api/platform/enquiries${query}`, { method: 'GET' });
    }

    async createOrganization(data) {
        return this.request('/api/platform/organizations', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getOrganization(orgId) {
        return this.request(`/api/platform/organizations/${orgId}`, { method: 'GET' });
    }

    async updateOrganization(orgId, data) {
        return this.request(`/api/platform/organizations/${orgId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async suspendOrganization(orgId, suspend = true) {
        return this.request(`/api/platform/organizations/${orgId}/suspend`, {
            method: 'PUT',
            body: JSON.stringify({ suspend })
        });
    }

    async deleteOrganization(orgId) {
        return this.request(`/api/platform/organizations/${orgId}`, { method: 'DELETE' });
    }

    async getStats() {
        return this.request('/api/platform/stats', { method: 'GET' });
    }

    async markEnquiryRead(enquiryId) {
        return this.request(`/api/platform/enquiries/${enquiryId}/read`, {
            method: 'PUT'
        });
    }
}

const platformAPI = new PlatformAPIClient();

// Utility functions for alerts (must be available globally)
function showSuccess(message) {
    const alert = document.getElementById('success-message');
    const text = document.getElementById('success-text');
    const err = document.getElementById('error-message');
    if (err) err.classList.remove('show');
    if (alert && text) {
        text.textContent = message;
        alert.classList.add('show');
        setTimeout(() => alert.classList.remove('show'), 5000);
    }
}

function showError(message) {
    const alert = document.getElementById('error-message');
    const text = document.getElementById('error-text');
    const ok = document.getElementById('success-message');
    if (ok) ok.classList.remove('show');
    if (alert && text) {
        text.textContent = message;
        alert.classList.add('show');
    }
    console.error('Error:', message);
}

// Make utility functions globally accessible
window.showSuccess = showSuccess;
window.showError = showError;

// Check authentication
async function checkPlatformAuth() {
    if (!platformAPI.token) {
        window.location.href = '/platform/login';
        return false;
    }

    try {
        await platformAPI.getMe();
        return true;
    } catch (error) {
        window.location.href = '/platform/login';
        return false;
    }
}

// Load platform stats
async function loadPlatformStats() {
    try {
        const stats = await platformAPI.getStats();
        if (typeof window.renderPlatformAnalytics === 'function') {
            window.renderPlatformAnalytics(stats);
            return;
        }
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        set('total-orgs', stats.organizations?.total ?? stats.total_organizations ?? 0);
        set('total-users', stats.users?.total ?? stats.total_users ?? 0);
        set('total-tickets', stats.tickets?.total ?? stats.total_tickets ?? 0);
        set('total-enquiries', stats.enquiries?.total ?? 0);
        set('unread-enquiries', `${stats.enquiries?.unread ?? 0} unread`);
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load platform analytics.');
    }
}
let currentOrgPage = 1;
let currentOrgPageSize = 10;
let currentOrgSearch = '';

async function loadOrganizations(page = 1, pageSize = 10) {
    currentOrgPage = page;
    currentOrgPageSize = pageSize;

    const container = document.getElementById('orgs-container');
    container.innerHTML = `
        <div class="loading">
            <div class="d-flex flex-column align-items-center">
                <div class="spinner mb-3"></div>
                <span class="text-tertiary">Loading organizations...</span>
            </div>
        </div>`;

    try {
        const response = await platformAPI.getOrganizations(page, pageSize, currentOrgSearch);

        // Handle paginated response: DRF returns { count, next, previous, results }
        let orgs = [];
        if (Array.isArray(response.results)) {
            orgs = response.results;
        } else if (Array.isArray(response.organizations)) {
            orgs = response.organizations;
        } else if (response && typeof response.results === 'object' && Array.isArray(response.results.organizations)) {
            orgs = response.results.organizations;
        }
        const totalCount = response.count != null ? response.count : orgs.length;
        const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

        if (orgs.length === 0) {
            container.innerHTML = '<div class="text-center p-5"><p class="text-tertiary mb-0">No organizations found.</p></div>';
            return;
        }

        // Get base URL for generating access URLs
        const baseUrl = window.location.origin;

        let html = `
            <div class="table-responsive">
                <table class="pd-table table table-hover">
                    <thead>
                        <tr>
                            <th>Organization</th>
                            <th>Subdomain</th>
                            <th>Access URL</th>
                            <th>Plan</th>
                            <th>Status</th>
                            <th>Stats</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${orgs.map(org => {
            const loginUrl = `${baseUrl}/${org.subdomain}/login`;
            const dashboardUrl = `${baseUrl}/${org.subdomain}/dashboard`;
            return `
                        <tr>
                            <td class="px-4 py-3">
                                <div class="font-semibold text-dark">${org.name || 'N/A'}</div>
                                <div class="text-tertiary text-sm">${org.email || 'N/A'}</div>
                            </td>
                            <td class="px-4 py-3">
                                <code class="px-2 py-1 bg-light rounded text-primary">${org.subdomain}</code>
                            </td>
                            <td class="px-4 py-3">
                                <div class="d-flex flex-column gap-1">
                                    <a href="${loginUrl}" target="_blank" class="text-decoration-none text-sm d-flex align-items-center gap-1 text-primary">
                                        <i class="fas fa-external-link-alt fa-xs"></i> Login
                                    </a>
                                    <a href="${dashboardUrl}" target="_blank" class="text-decoration-none text-sm d-flex align-items-center gap-1 text-tertiary hover-text-primary">
                                        <i class="fas fa-tachometer-alt fa-xs"></i> Dashboard
                                    </a>
                                </div>
                            </td>
                            <td class="px-4 py-3">
                                <span class="badge ${org.plan === 'growth_cluster' ? 'badge-status-resolved' : 'badge-status-in-progress'} rounded-pill fw-normal px-3 py-2 border">
                                    ${org.plan === 'growth_cluster' ? 'Growth Cluster' : 'Starter Trial'}
                                </span>
                                ${org.has_external_db ? '<span class="badge bg-info text-white rounded-pill ms-1" title="External Database Connected"><i class="fas fa-database"></i> BYODB</span>' : ''}
                            </td>
                            <td class="px-4 py-3">
                                ${org.is_active
                    ? '<span class="status-indicator status-open"><span class="status-dot"></span>Active</span>'
                    : '<span class="status-indicator status-closed"><span class="status-dot"></span>Suspended</span>'}
                            </td>
                            <td class="px-4 py-3">
                                <div class="d-flex gap-3 text-sm text-tertiary">
                                    <span title="Users"><i class="fas fa-users me-1"></i>${org.stats?.users || 0}</span>
                                    <span title="Tickets"><i class="fas fa-ticket-alt me-1"></i>${org.stats?.tickets || 0}</span>
                                    <span title="Projects"><i class="fas fa-folder me-1"></i>${org.stats?.projects || 0}</span>
                                </div>
                            </td>
                            <td class="px-4 py-3 text-end">
                                <div class="d-flex justify-content-end gap-2">
                                    <button class="btn btn-icon btn-sm btn-light" onclick="window.viewOrganization(${org.id})" title="View Details">
                                        <i class="fas fa-eye text-secondary"></i>
                                    </button>
                                    ${org.is_active ?
                    `<button class="btn btn-icon btn-sm btn-light" onclick="window.suspendOrganization(${org.id}, true)" title="Suspend">
                                            <i class="fas fa-pause text-warning"></i>
                                        </button>` :
                    `<button class="btn btn-icon btn-sm btn-light" onclick="window.suspendOrganization(${org.id}, false)" title="Activate">
                                            <i class="fas fa-play text-success"></i>
                                        </button>`
                }
                                    <button class="btn btn-icon btn-sm btn-light" onclick="window.deleteOrganization(${org.id})" title="Delete">
                                        <i class="fas fa-trash text-danger"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
        }).join('')}
                    </tbody>
                </table>
            </div>
            
            <!-- Pagination Controls -->
            <div class="d-flex justify-content-between align-items-center mt-4 px-2">
                <div class="d-flex align-items-center gap-3">
                    <span class="text-tertiary text-sm">Rows per page:</span>
                    <select class="form-select form-select-sm" style="width: 70px;" onchange="loadOrganizations(1, this.value)">
                        <option value="5" ${pageSize == 5 ? 'selected' : ''}>5</option>
                        <option value="10" ${pageSize == 10 ? 'selected' : ''}>10</option>
                        <option value="25" ${pageSize == 25 ? 'selected' : ''}>25</option>
                        <option value="50" ${pageSize == 50 ? 'selected' : ''}>50</option>
                    </select>
                    <span class="text-tertiary text-sm">
                        ${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, totalCount)} of ${totalCount}
                    </span>
                </div>
                
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-secondary" 
                        ${!response.previous ? 'disabled' : ''} 
                        onclick="loadOrganizations(${page - 1}, ${pageSize})">
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    ${Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            // Logic to show generic page numbers locally around current page could be added here
            // For now, simple 1-5 or based on total pages
            let p = i + 1;
            if (totalPages > 5) {
                if (page > 3) p = page - 2 + i;
                if (p > totalPages) return '';
            }
            return ''; // Simplified: just Prev/Next for now to be safe, or implement full logic
        }).join('')}
                     <button class="btn btn-sm btn-outline-secondary" 
                        ${!response.next ? 'disabled' : ''} 
                        onclick="loadOrganizations(${page + 1}, ${pageSize})">
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger m-4"><i class="fas fa-exclamation-circle me-2"></i>Error loading organizations: ${error.message}</div>`;
    }
}

// Create organization
function showCreateOrgModal() {
    const modal = new bootstrap.Modal(document.getElementById('createOrgModal'));
    modal.show();

    // Auto-lowercase subdomain
    const subdomainInput = document.getElementById('org-subdomain');
    if (subdomainInput) {
        subdomainInput.addEventListener('input', function () {
            this.value = this.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
        });
    }
}

async function createOrganization(data) {
    try {
        const submitBtn = document.getElementById('create-org-btn-submit');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

        const result = await platformAPI.createOrganization(data);

        // Close create modal
        bootstrap.Modal.getInstance(document.getElementById('createOrgModal')).hide();
        document.getElementById('create-org-form').reset();

        // Prepare organization details for display
        // Use window.location.origin to ensure path-based URLs (no subdomains)
        const companyName = result.subdomain || data.subdomain;
        const loginUrl = result.login_url || `${window.location.origin}/${companyName}/login`;
        const dashboardUrl = result.access_url || `${window.location.origin}/${companyName}/dashboard`;
        const adminEmail = result.admin_user?.email || data.admin_email;
        const adminPassword = result.admin_user?.password || data.admin_password;

        // Display success modal with all details
        const detailsHtml = `
            <div class="mb-4">
                <h6 class="text-success mb-3"><i class="fas fa-check-circle"></i> Organization Created Successfully!</h6>
                
                <div class="card mb-3" style="background: var(--color-bg-secondary);">
                    <div class="card-body">
                        <h6 class="card-title">Organization Details</h6>
                        <table class="table table-sm mb-0">
                            <tr>
                                <td><strong>Company Name:</strong></td>
                                <td>${result.organization?.name || data.name}</td>
                            </tr>
                            <tr>
                                <td><strong>Subdomain:</strong></td>
                                <td><code>${result.subdomain || data.subdomain}</code></td>
                            </tr>
                            <tr>
                                <td><strong>Contact Email:</strong></td>
                                <td>${result.organization?.email || data.email}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                
                <div class="card mb-3" style="background: #fff3cd; border: 2px solid #ffc107;">
                    <div class="card-body">
                        <h6 class="card-title"><i class="fas fa-key"></i> Admin Credentials</h6>
                        <table class="table table-sm mb-0">
                            <tr>
                                <td><strong>Email:</strong></td>
                                <td><code style="background: white; padding: 4px 8px; border-radius: 4px;">${adminEmail}</code></td>
                            </tr>
                            <tr>
                                <td><strong>Password:</strong></td>
                                <td><code style="background: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: #d63384;">${adminPassword}</code></td>
                            </tr>
                        </table>
                        <div class="alert alert-warning mt-2 mb-0" style="font-size: 12px;">
                            <i class="fas fa-exclamation-triangle"></i> <strong>Important:</strong> Save these credentials. You'll need them to login.
                        </div>
                    </div>
                </div>
                
                <div class="card" style="background: #d1ecf1; border: 2px solid #0dcaf0;">
                    <div class="card-body">
                        <h6 class="card-title"><i class="fas fa-link"></i> Access URLs</h6>
                        <div class="mb-2">
                            <strong>Login URL:</strong><br>
                            <a href="${loginUrl}" target="_blank" style="word-break: break-all; color: var(--color-brand-primary);">
                                ${loginUrl} <i class="fas fa-external-link-alt"></i>
                            </a>
                        </div>
                        <div>
                            <strong>Dashboard URL:</strong><br>
                            <a href="${dashboardUrl}" target="_blank" style="word-break: break-all; color: var(--color-brand-primary);">
                                ${dashboardUrl} <i class="fas fa-external-link-alt"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Populate and show success modal
        document.getElementById('org-created-details').innerHTML = detailsHtml;

        // Setup copy credentials button
        const copyBtn = document.getElementById('copy-credentials-btn');
        copyBtn.onclick = function () {
            const credentialsText = `Organization: ${result.organization?.name || data.name}
Subdomain: ${result.subdomain || data.subdomain}
Login URL: ${loginUrl}
Dashboard URL: ${dashboardUrl}

Admin Credentials:
Email: ${adminEmail}
Password: ${adminPassword}`;

            navigator.clipboard.writeText(credentialsText).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Credentials';
                }, 2000);
            }).catch(() => {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = credentialsText;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy Credentials';
                }, 2000);
            });
        };

        // Show success modal
        const successModal = new bootstrap.Modal(document.getElementById('orgCreatedModal'));
        successModal.show();

        // Also show toast notification
        showSuccess(`Organization "${result.organization?.name || data.name}" created successfully!`);

        // Refresh list and stats after a short delay so the new org is committed and visible
        setTimeout(() => {
            loadOrganizations(1, currentOrgPageSize);
            loadPlatformStats();
        }, 200);

        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    } catch (error) {
        // Extract user-friendly error message
        let errorMessage = error.message;
        if (errorMessage.includes('Subdomain') || errorMessage.includes('subdomain')) {
            errorMessage = errorMessage.replace(/Failed to create organization: /g, '');
        }
        showError(errorMessage || 'Failed to create organization. Please check your input and try again.');
        const submitBtn = document.getElementById('create-org-btn-submit');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-plus"></i> Create Organization';
    }
}

async function suspendOrganization(orgId, suspend) {
    window.showConfirm(
        suspend ? 'Suspend Organization' : 'Activate Organization',
        `Are you sure you want to ${suspend ? 'suspend' : 'activate'} this organization?`,
        async () => {
            try {
                await platformAPI.suspendOrganization(orgId, suspend);
                showSuccess(`Organization ${suspend ? 'suspended' : 'activated'} successfully`);
                setTimeout(() => {
                    loadOrganizations(1, currentOrgPageSize);
                    loadPlatformStats();
                }, 150);
            } catch (error) {
                showError('Failed to update organization: ' + error.message);
            }
        },
        suspend // isDestructive only if suspending
    );
}

async function deleteOrganization(orgId) {
    window.showConfirm(
        'Delete Organization',
        'Are you sure you want to delete this organization? This action cannot be undone and will delete all associated data!',
        async () => {
            try {
                await platformAPI.deleteOrganization(orgId);
                showSuccess('Organization deleted successfully');
                setTimeout(() => {
                    loadOrganizations(1, currentOrgPageSize);
                    loadPlatformStats();
                }, 150);
            } catch (error) {
                showError('Failed to delete organization: ' + error.message);
            }
        },
        true // isDestructive
    );
}

async function viewOrganization(orgId) {
    try {
        const response = await platformAPI.getOrganization(orgId);
        console.log('Organization response:', response); // Debug

        // API returns organization dict directly (not nested)
        const org = response;
        const stats = response.detailed_stats || response.stats || {};

        // Get access URLs (from API response or generate)
        // Use window.location.origin to ensure path-based URLs (no subdomains)
        const loginUrl = response.access_urls?.login || `${window.location.origin}/${org.subdomain}/login`;
        const dashboardUrl = response.access_urls?.dashboard || `${window.location.origin}/${org.subdomain}/dashboard`;

        // Get admin user info
        const adminUser = response.admin_user || {};

        const details = `
═══════════════════════════════════════════════════════
   ORGANIZATION DETAILS
═══════════════════════════════════════════════════════

Company Name: ${org.name || 'N/A'}
Subdomain: ${org.subdomain || 'N/A'}
Contact Email: ${org.email || 'N/A'}
Plan: ${org.plan || 'free'}
Status: ${org.is_active ? 'Active' : 'Suspended'}
Cluster ID: ${org.cluster_id || 'None'}
Created: ${org.created_at ? new Date(org.created_at).toLocaleDateString() : 'N/A'}

═══════════════════════════════════════════════════════
   ADMIN CREDENTIALS
═══════════════════════════════════════════════════════

Admin Email: ${adminUser.email || 'N/A'}
Admin Name: ${adminUser.full_name || 'N/A'}
Admin Role: ${adminUser.role || 'admin'}
Admin Status: ${adminUser.is_active ? 'Active' : 'Inactive'}

Note: Password was set during organization creation.
If you need to reset it, use the user management page.

═══════════════════════════════════════════════════════
   ACCESS URLs
═══════════════════════════════════════════════════════

Login URL:
${loginUrl}

Dashboard URL:
${dashboardUrl}

═══════════════════════════════════════════════════════
   STATISTICS
═══════════════════════════════════════════════════════

Users:
- Total: ${stats.users?.total || stats.users || 0}
- Active: ${stats.users?.active || 0}
- By Role: ${JSON.stringify(stats.users?.by_role || {})}

Tickets:
- Total: ${stats.tickets?.total || stats.tickets || 0}
- By Status: ${JSON.stringify(stats.tickets?.by_status || {})}

Projects:
- Total: ${stats.projects?.total || stats.projects || 0}
- Active: ${stats.projects?.active || 0}

═══════════════════════════════════════════════════════
        `.trim();

        window.showAlert('Organization Details', details);
    } catch (error) {
        console.error('Error loading organization:', error);
        showError('Failed to load organization details: ' + (error.message || 'Unknown error'));
    }
}

// Load enquiries
let currentEnqPage = 1;
let currentEnqPageSize = 10;
let showUnreadOnly = false;

async function loadEnquiries(unreadOnly = false, page = 1, pageSize = 10) {
    showUnreadOnly = unreadOnly;
    currentEnqPage = page;
    currentEnqPageSize = pageSize;

    const container = document.getElementById('enquiries-container');
    if (!container) return;

    container.innerHTML = `
        <div class="loading">
            <div class="d-flex flex-column align-items-center">
                <div class="spinner mb-3"></div>
                <span class="text-tertiary">Loading enquiries...</span>
            </div>
        </div>`;

    try {
        const response = await platformAPI.getEnquiries(unreadOnly, page, pageSize);
        let enquiries = [];
        if (Array.isArray(response.results)) {
            enquiries = response.results;
        } else if (Array.isArray(response.enquiries)) {
            enquiries = response.enquiries;
        } else if (response && typeof response.results === 'object' && Array.isArray(response.results.enquiries)) {
            enquiries = response.results.enquiries;
        }
        const totalCount = response.count != null ? response.count : enquiries.length;
        const totalPages = Math.ceil(totalCount / pageSize);

        // Update button text
        const showUnreadBtn = document.getElementById('show-unread-btn');
        if (showUnreadBtn) {
            showUnreadBtn.innerHTML = unreadOnly
                ? '<i class="fas fa-filter"></i> Show All'
                : '<i class="fas fa-filter"></i> Show Unread Only';
        }

        if (enquiries.length === 0) {
            container.innerHTML = '<div class="text-center p-5"><p class="text-tertiary mb-0">No enquiries found.</p></div>';
            return;
        }

        let html = `
            <div class="table-responsive">
                <table class="pd-table table table-hover">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Company</th>
                            <th>Phone</th>
                            <th>Message</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${enquiries.map(enquiry => `
                        <tr style="${enquiry.is_read ? '' : 'background-color: var(--color-bg-secondary);'}">
                            <td class="px-4 py-3"><strong>${enquiry.name}</strong></td>
                            <td class="px-4 py-3"><a href="mailto:${enquiry.email}" class="text-primary text-decoration-none">${enquiry.email}</a></td>
                            <td class="px-4 py-3 text-tertiary">${enquiry.company || '-'}</td>
                            <td class="px-4 py-3 text-tertiary">${enquiry.phone || '-'}</td>
                            <td class="px-4 py-3 text-tertiary" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${enquiry.message}">${enquiry.message}</td>
                            <td class="px-4 py-3 text-tertiary">${new Date(enquiry.created_at).toLocaleDateString()}</td>
                            <td class="px-4 py-3">
                                ${enquiry.is_read
                ? '<span class="badge bg-light text-secondary rounded-pill border fw-normal px-3">Read</span>'
                : '<span class="badge bg-primary text-white rounded-pill fw-normal px-3">Unread</span>'
            }
                            </td>
                            <td class="px-4 py-3 text-end">
                                <div class="d-flex justify-content-end gap-2">
                                    <button class="btn btn-icon btn-sm btn-light" onclick="viewEnquiry(${enquiry.id})" title="View Details">
                                        <i class="fas fa-eye text-secondary"></i>
                                    </button>
                                    ${!enquiry.is_read ? `
                                        <button class="btn btn-icon btn-sm btn-light" onclick="markEnquiryRead(${enquiry.id})" title="Mark as Read">
                                            <i class="fas fa-check text-primary"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                    </tbody>
                </table>
            </div>
            
            <!-- Pagination Controls -->
            <div class="d-flex justify-content-between align-items-center mt-4 px-2">
                <div class="d-flex align-items-center gap-3">
                    <span class="text-tertiary text-sm">Rows per page:</span>
                    <select class="form-select form-select-sm" style="width: 70px;" onchange="loadEnquiries(${unreadOnly}, 1, this.value)">
                        <option value="5" ${pageSize == 5 ? 'selected' : ''}>5</option>
                        <option value="10" ${pageSize == 10 ? 'selected' : ''}>10</option>
                        <option value="25" ${pageSize == 25 ? 'selected' : ''}>25</option>
                        <option value="50" ${pageSize == 50 ? 'selected' : ''}>50</option>
                    </select>
                    <span class="text-tertiary text-sm">
                        ${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, totalCount)} of ${totalCount}
                    </span>
                </div>
                
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-secondary" 
                        ${!response.previous ? 'disabled' : ''} 
                        onclick="loadEnquiries(${unreadOnly}, ${page - 1}, ${pageSize})">
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    ${Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let p = i + 1;
                if (totalPages > 5) {
                    if (page > 3) p = page - 2 + i;
                    if (p > totalPages) return '';
                }
                return '';
            }).join('')}
                     <button class="btn btn-sm btn-outline-secondary" 
                        ${!response.next ? 'disabled' : ''} 
                        onclick="loadEnquiries(${unreadOnly}, ${page + 1}, ${pageSize})">
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger m-4"><i class="fas fa-exclamation-circle me-2"></i>Error loading enquiries: ${error.message}</div>`;
    }
}

async function viewEnquiry(enquiryId) {
    try {
        // Fetch single enquiry from the new detail endpoint
        const enquiry = await platformAPI.request(`/api/platform/enquiries/${enquiryId}`, { method: 'GET' });

        const details = `Enquiry Details:\n\nName: ${enquiry.name}\nEmail: ${enquiry.email}\nCompany: ${enquiry.company || 'Not provided'}\nPhone: ${enquiry.phone || 'Not provided'}\nDate: ${new Date(enquiry.created_at).toLocaleString()}\nStatus: ${enquiry.is_read ? 'Read' : 'Unread'}\n\nMessage:\n${enquiry.message}`.trim();

        window.showAlert('Enquiry Details', details);
    } catch (error) {
        showError('Failed to load enquiry: ' + error.message);
    }
}

async function markEnquiryRead(enquiryId) {
    try {
        await platformAPI.markEnquiryRead(enquiryId);
        showSuccess('Enquiry marked as read');
        loadEnquiries(showUnreadOnly);
        loadPlatformStats();
    } catch (error) {
        showError('Failed to mark enquiry as read: ' + error.message);
    }
}

// Make functions globally accessible for onclick handlers
window.viewOrganization = viewOrganization;
window.suspendOrganization = suspendOrganization;
window.deleteOrganization = deleteOrganization;
window.showCreateOrgModal = showCreateOrgModal;
window.createOrganization = createOrganization;
window.loadOrganizations = loadOrganizations;
window.loadEnquiries = loadEnquiries;
window.viewEnquiry = viewEnquiry;
window.markEnquiryRead = markEnquiryRead;

// ─── Dialog helpers (Bootstrap modal-based) ───────────────────────────────────
// Creates transient modal elements so we don't need separate HTML placeholders.

window.showAlert = function (title, message) {
    // Remove any previous instance
    document.getElementById('_platformAlertModal')?.remove();
    const el = document.createElement('div');
    el.id = '_platformAlertModal';
    el.className = 'modal fade';
    el.tabIndex = -1;
    el.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <pre style="white-space:pre-wrap;word-break:break-word;font-size:0.875rem;background:#f8f9fa;border-radius:8px;padding:1rem;max-height:60vh;overflow-y:auto;">${message}</pre>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>`;
    document.body.appendChild(el);
    const m = new bootstrap.Modal(el);
    el.addEventListener('hidden.bs.modal', () => el.remove());
    m.show();
};

window.showConfirm = function (title, message, onConfirm, isDestructive = false) {
    document.getElementById('_platformConfirmModal')?.remove();
    const el = document.createElement('div');
    el.id = '_platformConfirmModal';
    el.className = 'modal fade';
    el.tabIndex = -1;
    el.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">${message}</div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn ${isDestructive ? 'btn-danger' : 'btn-primary'}" id="_confirmOk">Confirm</button>
                </div>
            </div>
        </div>`;
    document.body.appendChild(el);
    const m = new bootstrap.Modal(el);
    el.querySelector('#_confirmOk').addEventListener('click', () => {
        m.hide();
        onConfirm();
    });
    el.addEventListener('hidden.bs.modal', () => el.remove());
    m.show();
};

// Initialize
document.addEventListener('DOMContentLoaded', async function () {
    const isAuthenticated = await checkPlatformAuth();
    if (!isAuthenticated) return;

    loadPlatformStats();
    loadOrganizations();
    loadEnquiries();

    // Create org button
    const createBtn = document.getElementById('create-org-btn');
    if (createBtn) {
        createBtn.addEventListener('click', showCreateOrgModal);
    }

    // Create org form
    const createForm = document.getElementById('create-org-form');
    if (createForm) {
        createForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const orgData = {
                name: formData.get('name'),
                subdomain: formData.get('subdomain'),
                email: formData.get('email'),
                admin_email: formData.get('admin_email'),
                admin_name: formData.get('admin_name'),
                admin_password: formData.get('admin_password'),
                plan: formData.get('plan') || 'starter_trial',
                cluster_id: formData.get('cluster_id') || null
            };
            createOrganization(orgData);
        });
    }

    // Search (server-side via API)
    const searchInput = document.getElementById('search-orgs');
    if (searchInput) {
        let searchDebounce;
        searchInput.addEventListener('input', function () {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                currentOrgSearch = this.value.trim();
                loadOrganizations(1, currentOrgPageSize);
            }, 350);
        });
    }
});

window.loadPlatformStats = loadPlatformStats;
