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

    async getOrganizations() {
        return this.request('/api/platform/organizations', { method: 'GET' });
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

    async getEnquiries(unreadOnly = false) {
        const params = unreadOnly ? '?unread_only=true' : '';
        return this.request(`/api/platform/enquiries${params}`, { method: 'GET' });
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
    if (alert && text) {
        text.textContent = message;
        alert.style.display = 'block';
        setTimeout(() => {
            if (alert) alert.style.display = 'none';
        }, 5000);
    }
    // Also show toast if available
    console.log('Success:', message);
}

function showError(message) {
    const alert = document.getElementById('error-message');
    const text = document.getElementById('error-text');
    if (alert && text) {
        text.textContent = message;
        alert.style.display = 'block';
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
        console.log('Platform stats:', stats); // Debug
        document.getElementById('total-orgs').textContent = stats.organizations?.total || stats.total_organizations || 0;
        document.getElementById('total-users').textContent = stats.users?.total || stats.total_users || 0;
        document.getElementById('total-tickets').textContent = stats.tickets?.total || stats.total_tickets || 0;
        document.getElementById('active-orgs').textContent = stats.organizations?.active || stats.active_organizations || 0;

        // Update enquiries stats if elements exist
        const totalEnquiriesEl = document.getElementById('total-enquiries');
        const unreadEnquiriesEl = document.getElementById('unread-enquiries');
        if (totalEnquiriesEl) {
            totalEnquiriesEl.textContent = stats.enquiries?.total || 0;
        }
        if (unreadEnquiriesEl) {
            const unread = stats.enquiries?.unread || 0;
            unreadEnquiriesEl.textContent = `${unread} unread`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load organizations
async function loadOrganizations() {
    const container = document.getElementById('orgs-container');
    container.innerHTML = '<div class="loading"><div class="spinner"></div><span style="margin-left: var(--spacing-sm);">Loading organizations...</span></div>';

    try {
        const response = await platformAPI.getOrganizations();
        const orgs = response.organizations || [];

        if (orgs.length === 0) {
            container.innerHTML = '<div class="text-center p-4"><p class="text-tertiary">No organizations found. Create your first organization.</p></div>';
            return;
        }

        // Get base URL for generating access URLs
        const baseUrl = window.location.origin;

        container.innerHTML = `
            <table class="table" style="margin: 0;">
                <thead>
                    <tr>
                        <th>Organization</th>
                        <th>Subdomain</th>
                        <th>Access URL</th>
                        <th>Plan</th>
                        <th>Status</th>
                        <th>Stats</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${orgs.map(org => {
            const loginUrl = `${baseUrl}/${org.subdomain}/login`;
            const dashboardUrl = `${baseUrl}/${org.subdomain}/dashboard`;
            return `
                        <tr>
                            <td>
                                <div class="font-semibold">${org.name || 'N/A'}</div>
                                <div class="text-tertiary text-sm">${org.email || 'N/A'}</div>
                            </td>
                            <td>
                                <code>${org.subdomain}</code>
                            </td>
                            <td>
                                <div class="text-sm">
                                    <div style="word-break: break-all;">
                                        <a href="${loginUrl}" target="_blank" style="color: var(--color-brand-primary); text-decoration: none; font-size: 11px;">
                                            <i class="fas fa-external-link-alt"></i> ${loginUrl}
                                        </a>
                                    </div>
                                    <div class="text-tertiary" style="font-size: 10px; margin-top: 4px;">
                                        Dashboard: <a href="${dashboardUrl}" target="_blank" style="color: var(--color-brand-primary);">${dashboardUrl}</a>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="badge ${org.plan === 'growth_cluster' ? 'badge-status-resolved' : 'badge-status-in-progress'}">${org.plan === 'growth_cluster' ? 'Growth Cluster' : 'Starter Trial'}</span>
                                ${org.has_external_db ? '<span class="badge" style="background-color: var(--color-brand-secondary); margin-left: 4px;" title="External Database Connected"><i class="fas fa-database"></i> BYODB</span>' : ''}
                            </td>
                            <td>
                                ${org.is_active ? '<span class="badge badge-status-resolved">Active</span>' : '<span class="badge" style="background-color: var(--color-bg-tertiary);">Suspended</span>'}
                            </td>
                            <td>
                                <div class="text-sm">
                                    <div>👥 ${org.stats?.users || 0} users</div>
                                    <div>🎫 ${org.stats?.tickets || 0} tickets</div>
                                    <div>📁 ${org.stats?.projects || 0} projects</div>
                                </div>
                            </td>
                            <td>
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-secondary" onclick="window.viewOrganization(${org.id})" title="View Details" type="button">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    ${org.is_active ?
                    `<button class="btn btn-sm btn-warning" onclick="window.suspendOrganization(${org.id}, true)" title="Suspend" type="button">
                                            <i class="fas fa-pause"></i>
                                        </button>` :
                    `<button class="btn btn-sm btn-success" onclick="window.suspendOrganization(${org.id}, false)" title="Activate" type="button">
                                            <i class="fas fa-play"></i>
                                        </button>`
                }
                                    <button class="btn btn-sm btn-danger" onclick="window.deleteOrganization(${org.id})" title="Delete" type="button">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
        }).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Error loading organizations: ${error.message}</div>`;
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

        // Refresh organizations list and stats
        loadOrganizations();
        loadPlatformStats();

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
                loadOrganizations();
                loadPlatformStats();
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
                loadOrganizations();
                loadPlatformStats();
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
let showUnreadOnly = false;
async function loadEnquiries(unreadOnly = false) {
    showUnreadOnly = unreadOnly;
    const container = document.getElementById('enquiries-container');
    if (!container) return;

    container.innerHTML = '<div class="loading"><div class="spinner"></div><span style="margin-left: var(--spacing-sm);">Loading enquiries...</span></div>';

    try {
        const response = await platformAPI.getEnquiries(unreadOnly);
        const enquiries = response.enquiries || [];

        // Update button text
        const showUnreadBtn = document.getElementById('show-unread-btn');
        if (showUnreadBtn) {
            showUnreadBtn.innerHTML = unreadOnly
                ? '<i class="fas fa-filter"></i> Show All'
                : '<i class="fas fa-filter"></i> Show Unread Only';
        }

        if (enquiries.length === 0) {
            container.innerHTML = '<div class="text-center p-4"><p class="text-tertiary">No enquiries found.</p></div>';
            return;
        }

        container.innerHTML = `
            <table class="table" style="margin: 0;">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Company</th>
                        <th>Phone</th>
                        <th>Message</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${enquiries.map(enquiry => `
                        <tr style="${enquiry.is_read ? '' : 'background-color: #f0f9ff;'}">
                            <td><strong>${enquiry.name}</strong></td>
                            <td><a href="mailto:${enquiry.email}">${enquiry.email}</a></td>
                            <td>${enquiry.company || '-'}</td>
                            <td>${enquiry.phone || '-'}</td>
                            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${enquiry.message}">${enquiry.message}</td>
                            <td>${new Date(enquiry.created_at).toLocaleDateString()}</td>
                            <td>
                                ${enquiry.is_read
                ? '<span class="badge badge-status-resolved">Read</span>'
                : '<span class="badge" style="background-color: var(--color-primary);">Unread</span>'
            }
                            </td>
                            <td>
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-secondary" onclick="viewEnquiry(${enquiry.id})" title="View Details" type="button">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    ${!enquiry.is_read ? `
                                        <button class="btn btn-sm btn-primary" onclick="markEnquiryRead(${enquiry.id})" title="Mark as Read" type="button">
                                            <i class="fas fa-check"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Error loading enquiries: ${error.message}</div>`;
    }
}

async function viewEnquiry(enquiryId) {
    try {
        const response = await platformAPI.getEnquiries(false);
        const enquiry = response.enquiries?.find(e => e.id === enquiryId);

        if (!enquiry) {
            showError('Enquiry not found');
            return;
        }

        const details = `
Enquiry Details:

Name: ${enquiry.name}
Email: ${enquiry.email}
Company: ${enquiry.company || 'Not provided'}
Phone: ${enquiry.phone || 'Not provided'}
Date: ${new Date(enquiry.created_at).toLocaleString()}
Status: ${enquiry.is_read ? 'Read' : 'Unread'}

Message:
${enquiry.message}
        `.trim();

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

    // Search
    const searchInput = document.getElementById('search-orgs');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('#orgs-container tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
});
