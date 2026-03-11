/* ===============================
   Tenant / Route Helpers
================================ */

(function () {
    const KNOWN_ROUTE_NAMES = new Set([
        'dashboard',
        'tickets',
        'admin',
        'head',
        'projects',
        'notifications',
        'forgot-password',
        'reset-password',
        'onboarding',
        'register',
        'api',
        'static',
        'platform'
    ]);

    function getCompanyNameFromPath() {
        const path = window.location.pathname.replace(/^\/+/, '');
        if (!path) return null;

        const parts = path.split('/');
        const firstPart = parts[0];

        if (!firstPart || KNOWN_ROUTE_NAMES.has(firstPart)) {
            return null;
        }

        return firstPart;
    }

    function formatApiError(errorData, status) {
        if (errorData.message) return errorData.message;
        if (errorData.error) return typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error);
        if (errorData.detail) {
            if (typeof errorData.detail === 'string') return errorData.detail;
            if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
                const parts = [];
                for (const [key, val] of Object.entries(errorData.detail)) {
                    const list = Array.isArray(val) ? val : [val];
                    parts.push(key + ': ' + list.join(', '));
                }
                return parts.length ? parts.join('; ') : 'Validation error';
            }
        }
        return status === 400 ? 'Validation error' : status === 403 ? 'Forbidden' : status === 404 ? 'Not found' : 'Request failed';
    }

    /* ===============================
       Auth / API Client
    ================================ */

    class AuthService {
        constructor(baseURL = '') {
            this.baseURL = baseURL;
            this.tokenKey = 'access_token';
        }

        /* ---------- Query Helpers ---------- */

        // DRF uses page_size; legacy UI sometimes passes per_page
        normalizePaginationParams(params = {}) {
            if (!params || typeof params !== 'object') return {};
            const out = { ...params };
            if (out.per_page != null && out.page_size == null) {
                out.page_size = out.per_page;
            }
            delete out.per_page;
            return out;
        }

        /* ---------- Tenant ---------- */

        getCompanyName() {
            const fromPage = typeof document !== 'undefined' && document.body && document.body.getAttribute('data-company-name');
            if (fromPage && fromPage.trim()) return fromPage.trim();
            return getCompanyNameFromPath() || 'default';
        }

        hasTenantContext() {
            // True only when URL path starts with a tenant slug (e.g. /acme/...)
            return Boolean(getCompanyNameFromPath());
        }

        /* ---------- Token ---------- */

        getToken() {
            return localStorage.getItem(this.tokenKey);
        }

        setToken(token) {
            localStorage.setItem(this.tokenKey, token);
        }

        clearToken() {
            localStorage.removeItem(this.tokenKey);
            localStorage.removeItem('user');
        }

        /* ---------- Endpoint Builder ---------- */

        buildEndpoint(endpoint) {
            // Auth routes are explicit
            if (endpoint.startsWith('/api/auth/')) {
                const company = this.getCompanyName();
                return `/api/${company}/auth/${endpoint.split('/api/auth/')[1]}`;
            }

            // Platform routes (no tenant)
            if (endpoint.startsWith('/api/platform/')) {
                return endpoint;
            }

            // Normal tenant APIs
            if (endpoint.startsWith('/api/')) {
                const company = this.getCompanyName();
                const parts = endpoint.split('/');
                parts.splice(2, 0, company);
                return parts.join('/');
            }

            return endpoint;
        }

        /* ---------- Core Request ---------- */

        async request(endpoint, options = {}) {
            const fullEndpoint = this.buildEndpoint(endpoint);
            const url = `${this.baseURL}${fullEndpoint}`;

            const headers = {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            };

            const token = this.getToken();
            if (token && token !== 'undefined' && token !== 'null') {
                headers['Authorization'] = `Bearer ${token}`;
            } else {
                // If token is explicitly undefined string, clear it
                if (token === 'undefined' || token === 'null') {
                    this.clearToken();
                }
                console.warn('No valid token found for request to:', fullEndpoint);
            }

            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                console.warn('Unauthorized (401). Clearing token and redirecting.');
                this.clearToken();
                // Redirect to login if not already there
                if (!window.location.pathname.includes('/login')) {
                    const company = this.getCompanyName();
                    window.location.href = `/${company}/login?next=${encodeURIComponent(window.location.pathname)}`;
                }
                throw new Error('Session expired. Please login again.');
            }

            if (!response.ok) {
                let errorData = {};
                try {
                    errorData = await response.json();
                } catch (_) { }
                const msg = formatApiError(errorData, response.status);
                throw new Error(msg);
            }

            return response.json();
        }

        /* ---------- FormData Request ---------- */

        async requestFormData(endpoint, options = {}) {
            const fullEndpoint = this.buildEndpoint(endpoint);
            const url = `${this.baseURL}${fullEndpoint}`;

            const headers = options.headers || {};
            const token = this.getToken();

            if (token && token !== 'undefined' && token !== 'null') {
                headers['Authorization'] = `Bearer ${token}`;
            } else {
                if (token === 'undefined' || token === 'null') {
                    this.clearToken();
                }
            }

            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                console.warn('Unauthorized (401). Clearing token and redirecting.');
                this.clearToken();
                if (!window.location.pathname.includes('/login')) {
                    const company = this.getCompanyName();
                    window.location.href = `/${company}/login?next=${encodeURIComponent(window.location.pathname)}`;
                }
                throw new Error('Session expired. Please login again.');
            }

            if (!response.ok) {
                let errorData = {};
                try {
                    errorData = await response.json();
                } catch (_) { }
                const msg = formatApiError(errorData, response.status);
                throw new Error(msg);
            }

            return response.json();
        }

        /* ===============================
           AUTH
        ================================ */

        async login(email, password) {
            // Ensure we explicitly use the company auth endpoint
            // api.js buildEndpoint logic handles /api/auth/ -> /api/{company}/auth/
            // providing user is on a company path or defaults to 'default'
            const endpoint = '/api/auth/login/';

            // Login should not send Authorization header
            const fullEndpoint = this.buildEndpoint(endpoint);
            const url = `${this.baseURL}${fullEndpoint}`;

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                let errorData = {};
                try {
                    errorData = await response.json();
                } catch (_) { }
                const msg = formatApiError(errorData, response.status) || 'Login failed';
                throw new Error(msg);
            }

            const data = await response.json();

            if (data.access_token) {
                this.setToken(data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));
                console.log('Token stored successfully');
            } else {
                console.error('No access_token in login response:', data);
            }

            return data;
        }

        async logout() {
            this.clearToken();
            return Promise.resolve();
        }

        async getCurrentUser() {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                return JSON.parse(userStr);
            }
            // Fallback or optional: fetch from API
            return this.request('/api/auth/me');
        }

        /* ===============================
           TICKETS
        ================================ */

        async getTickets(params = {}) {
            const queryString = new URLSearchParams(this.normalizePaginationParams(params)).toString();
            const url = queryString ? `/api/tickets/?${queryString}` : '/api/tickets/';
            return this.request(url);
        }

        async getTicket(ticketId) {
            return this.request(`/api/tickets/${ticketId}/`);
        }

        async createTicket(data) {
            return this.request('/api/tickets/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async createTicketWithFiles(formData) {
            return this.requestFormData('/api/tickets/', {
                method: 'POST',
                body: formData
            });
        }

        async updateTicket(ticketId, data) {
            return this.request(`/api/tickets/${ticketId}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteTicket(ticketId) {
            return this.request(`/api/tickets/${ticketId}/`, {
                method: 'DELETE'
            });
        }

        async getTicketStats() {
            return this.request('/api/tickets/stats/');
        }

        async getAdminDashboard() {
            return this.request('/api/admin/dashboard/');
        }

        async getStatuses() {
            return this.request('/api/tickets/statuses/');
        }

        async addComment(ticketId, comment, files = null, isInternal = false) {
            if (files && files.length > 0) {
                // Use FormData for file uploads
                const formData = new FormData();
                formData.append('comment', comment);
                formData.append('is_internal', isInternal);
                for (const file of files) {
                    formData.append('attachments', file);
                }
                return this.requestFormData(`/api/tickets/${ticketId}/comments/`, {
                    method: 'POST',
                    body: formData
                });
            }
            return this.request(`/api/tickets/${ticketId}/comments/`, {
                method: 'POST',
                body: JSON.stringify({ comment, is_internal: isInternal })
            });
        }

        async addCommentWithFiles(ticketId, formData) {
            return this.requestFormData(
                `/api/tickets/${ticketId}/comments/`,
                {
                    method: 'POST',
                    body: formData
                }
            );
        }

        async getProjects(params = {}) {
            const queryString = new URLSearchParams(this.normalizePaginationParams(params)).toString();
            const url = queryString ? `/api/projects/?${queryString}` : '/api/projects/';
            return this.request(url);
        }

        async getProject(id) {
            return this.request(`/api/projects/${id}/`);
        }

        // Backward-compatible alias used by templates/projects/detail.html
        async getProjectStats(projectId) {
            // Backend provides analytics at /projects/{id}/analytics/
            return this.request(`/api/projects/${projectId}/analytics/`);
        }

        // Workflow endpoint is not exposed; return a safe default for UI rendering
        async getProjectWorkflow(projectId) {
            // Keep UI stable without changing backend architecture
            return { states: ['open', 'in_progress', 'waiting', 'resolved', 'closed'] };
        }

        async getProjectLeadUsers() {
            // Returns all active org users for the project lead dropdown
            return this.request('/api/projects/lead_users/');
        }

        async createProject(data) {
            return this.request('/api/projects/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateProject(id, data) {
            return this.request(`/api/projects/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        }

        async deleteProject(id) {
            return this.request(`/api/projects/${id}/`, {
                method: 'DELETE'
            });
        }

        /* ===============================
           REPORTS
        ================================ */

        // Used by templates/admin/reports.html
        async getPerformanceReport() {
            // Derive from existing ticket stats endpoint.
            const stats = await this.getTicketStats();
            return {
                total_tickets: stats.total || 0,
                status_breakdown: stats.status_counts || {},
                // Not currently available in backend stats; keep null-safe for UI
                avg_response_time: null,
                avg_resolution_time: null,
            };
        }

        /* ===============================
           DEPARTMENTS
        ================================ */

        async getDepartments(params = {}) {
            const queryString = new URLSearchParams(this.normalizePaginationParams(params)).toString();
            const url = queryString ? `/api/auth/departments/?${queryString}` : '/api/auth/departments/';
            return this.request(url);
        }

        /** Returns a plain array of departments for dropdowns; handles paginated response. */
        async getDepartmentsList(params = {}) {
            const p = { ...params, page_size: params.page_size || 200 };
            const res = await this.getDepartments(p);
            return Array.isArray(res) ? res : (res.results || []);
        }

        /** Returns a plain array of projects for dropdowns; handles paginated response. */
        async getProjectsList(params = {}) {
            const p = { ...params, page_size: params.page_size || 200 };
            const res = await this.getProjects(p);
            return Array.isArray(res) ? res : (res.results || []);
        }

        async getDepartment(id) {
            return this.request(`/api/auth/departments/${id}/`);
        }

        async createDepartment(data) {
            return this.request('/api/auth/departments/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateDepartment(id, data) {
            return this.request(`/api/auth/departments/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        }

        async deleteDepartment(id) {
            return this.request(`/api/auth/departments/${id}/`, {
                method: 'DELETE'
            });
        }

        /* ===============================
           USERS
        ================================ */

        async getUsers(params = {}) {
            const queryString = new URLSearchParams(this.normalizePaginationParams(params)).toString();
            const url = queryString ? `/api/auth/users/?${queryString}` : '/api/auth/users/';
            return this.request(url);
        }

        /** Admin add-user: always use users endpoint. Legacy name kept for cached pages. */
        async registerUser(data) {
            return this.request('/api/auth/users/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        /** Create user via users list endpoint (admin add user). */
        async createUser(data) {
            return this.request('/api/auth/users/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateUser(id, data) {
            return this.request(`/api/auth/users/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteUser(id) {
            return this.request(`/api/auth/users/${id}/`, {
                method: 'DELETE'
            });
        }

        async getUserRoles(userId) {
            return this.request(`/api/auth/users/${userId}/roles/`);
        }

        async assignUserRole(userId, data) {
            return this.request(`/api/auth/users/${userId}/roles/assign/`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async removeUserRole(userId, roleId) {
            return this.request(`/api/auth/users/${userId}/roles/${roleId}/`, {
                method: 'DELETE'
            });
        }

        /* ===============================
           DEPARTMENT HEAD
        ================================ */

        async getDepartmentStats() {
            return this.request('/api/auth/department-head/stats/');
        }

        async getDepartmentTickets() {
            return this.request('/api/auth/department-head/tickets/');
        }

        async getDepartmentEmployees() {
            return this.request('/api/auth/department-head/employees/');
        }

        async assignTicket(ticketId, userId) {
            return this.request(`/api/tickets/${ticketId}/assign/`, {
                method: 'POST',
                body: JSON.stringify({ user_id: userId })
            });
        }

        async reassignTicket(ticketId, userId) {
            // Reassign is same as assign in most cases, or specific logic
            return this.request(`/api/tickets/${ticketId}/assign/`, {
                method: 'POST',
                body: JSON.stringify({ user_id: userId, reassign: true })
            });
        }


        /* ===============================
           DATA SOURCES
        ================================ */

        async getDataSources() {
            return this.request('/api/data-sources/');
        }

        async getDatabaseTypes() {
            return this.request('/api/data-sources/database_types/');
        }

        async testConnection(data) {
            return this.request('/api/data-sources/test_connection/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async createDataSource(data) {
            return this.request('/api/data-sources/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateDataSource(id, data) {
            return this.request(`/api/data-sources/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteDataSource(id) {
            return this.request(`/api/data-sources/${id}/`, {
                method: 'DELETE'
            });
        }

        async testDataSource(id) {
            return this.request(`/api/data-sources/${id}/test/`, {
                method: 'POST'
            });
        }

        async getDataSourceTables(id) {
            return this.request(`/api/data-sources/${id}/tables/`);
        }

        async getDataSourceSchema(id, tableName) {
            return this.request(`/api/data-sources/${id}/schema/?table=${encodeURIComponent(tableName)}`);
        }

        async syncDataSource(id) {
            return this.request(`/api/data-sources/${id}/sync/`, {
                method: 'POST'
            });
        }

        async getMappings(dataSourceId) {
            return this.request(`/api/mappings/?datasource=${dataSourceId}`);
        }

        async createMapping(dataSourceId, data) {
            return this.request('/api/mappings/', {
                method: 'POST',
                body: JSON.stringify({ ...data, datasource: dataSourceId })
            });
        }

        async deleteMapping(id) {
            return this.request(`/api/mappings/${id}/`, {
                method: 'DELETE'
            });
        }

        /* ===============================
           BULK ACTIONS & EXPORT
        ================================ */

        async bulkAction(data) {
            return this.request('/api/tickets/bulk-action/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async exportTicketsCSV(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const endpoint = queryString ? `/api/tickets/export/?${queryString}` : '/api/tickets/export/';
            const fullEndpoint = this.buildEndpoint(endpoint);
            const url = `${this.baseURL}${fullEndpoint}`;

            const token = this.getToken();
            const response = await fetch(url, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (!response.ok) throw new Error('Export failed');
            return response.blob();
        }

        /* ===============================
           WATCHERS
        ================================ */

        async watchTicket(ticketId) {
            return this.request(`/api/tickets/${ticketId}/watch/`, { method: 'POST' });
        }

        async unwatchTicket(ticketId) {
            return this.request(`/api/tickets/${ticketId}/unwatch/`, { method: 'POST' });
        }

        async getTicketWatchers(ticketId) {
            return this.request(`/api/tickets/${ticketId}/watchers/`);
        }

        /* ===============================
           MERGE
        ================================ */

        async mergeTicket(targetTicketId, sourceTicketId) {
            return this.request(`/api/tickets/${targetTicketId}/merge/`, {
                method: 'POST',
                body: JSON.stringify({ source_ticket_id: sourceTicketId })
            });
        }

        /* ===============================
           SECRETS / ENV VARS
        ================================ */

        async getSecrets() {
            return this.request('/api/auth/secrets/');
        }

        async createSecret(data) {
            // data: { key, value, scope }
            return this.request('/api/auth/secrets/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async getSecretValue(id) {
            // Returns the decrypted value
            return this.request(`/api/auth/secrets/${id}/`);
        }

        async deleteSecret(id) {
            return this.request(`/api/auth/secrets/${id}/`, { method: 'DELETE' });
        }

        /* ===============================
           TAGS
        ================================ */

        async getTags() {
            return this.request('/api/tags/');
        }

        async createTag(data) {
            return this.request('/api/tags/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async deleteTag(id) {
            return this.request(`/api/tags/${id}/`, { method: 'DELETE' });
        }

        /* ===============================
           SLA POLICIES
        ================================ */

        async getSLAPolicies() {
            return this.request('/api/sla-policies/');
        }

        async createSLAPolicy(data) {
            return this.request('/api/sla-policies/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateSLAPolicy(id, data) {
            return this.request(`/api/sla-policies/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteSLAPolicy(id) {
            return this.request(`/api/sla-policies/${id}/`, { method: 'DELETE' });
        }

        /* ===============================
           CANNED RESPONSES
        ================================ */

        async getCannedResponses(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `/api/canned-responses/?${queryString}` : '/api/canned-responses/';
            return this.request(url);
        }

        async createCannedResponse(data) {
            return this.request('/api/canned-responses/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateCannedResponse(id, data) {
            return this.request(`/api/canned-responses/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteCannedResponse(id) {
            return this.request(`/api/canned-responses/${id}/`, { method: 'DELETE' });
        }

        async useCannedResponse(id) {
            return this.request(`/api/canned-responses/${id}/use/`, { method: 'POST' });
        }

        /* ===============================
           KNOWLEDGE BASE
        ================================ */

        async getKBCategories() {
            return this.request('/api/kb/categories/');
        }

        async getKBArticles(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `/api/kb/articles/?${queryString}` : '/api/kb/articles/';
            return this.request(url);
        }

        async getKBArticle(id) {
            return this.request(`/api/kb/articles/${id}/`);
        }

        async createKBArticle(data) {
            return this.request('/api/kb/articles/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateKBArticle(id, data) {
            return this.request(`/api/kb/articles/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async deleteKBArticle(id) {
            return this.request(`/api/kb/articles/${id}/`, { method: 'DELETE' });
        }

        async markKBArticleHelpful(id, helpful = true) {
            return this.request(`/api/kb/articles/${id}/helpful/`, {
                method: 'POST',
                body: JSON.stringify({ helpful })
            });
        }

        /* ===============================
           AUDIT LOGS
        ================================ */

        async getAuditLogs(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `/api/audit-logs/?${queryString}` : '/api/audit-logs/';
            return this.request(url);
        }

        /* ===============================
           TICKET TYPES & SOURCES
        ================================ */

        async getTicketTypes() {
            return this.request('/api/tickets/types/');
        }

        async getTicketPriorities() {
            return this.request('/api/tickets/priorities/');
        }

        /* ===============================
           USER PROFILE & ORG SETTINGS
        ================================ */

        async changePassword(data) {
            return this.request('/api/auth/password-change/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        async updateProfile(data) {
            return this.request('/api/auth/profile/', {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        async getOrganizationSettings() {
            return this.request('/api/auth/organization/settings/');
        }

        async updateOrganizationSettings(data) {
            return this.request('/api/auth/organization/settings/', {
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        /* ===============================
           RECENT ACTIVITY
        ================================ */

        async getRecentActivity(limit = 50) {
            return this.request(`/api/tickets/recent-activity/?limit=${limit}`);
        }

        /* ===============================
           ATTACHMENTS
        ================================ */

        async downloadAttachment(ticketId, attachmentId) {
            const company = this.getCompanyName();
            const url = `${this.baseURL}/api/${company}/tickets/${ticketId}/attachments/${attachmentId}`;

            const token = this.getToken();

            const response = await fetch(url, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Download failed');
            }

            return response.blob();
        }
    }

    /* ===============================
       Export Singleton
    ================================ */

    const authService = new AuthService('');
    window.api = authService;
})();