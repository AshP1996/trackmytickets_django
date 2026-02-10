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

    /* ===============================
       Auth / API Client
    ================================ */

    class AuthService {
        constructor(baseURL = '') {
            this.baseURL = baseURL;
            this.tokenKey = 'access_token';
        }

        /* ---------- Tenant ---------- */

        getCompanyName() {
            return getCompanyNameFromPath() || 'default';
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
                const msg = errorData.message || errorData.error || errorData.detail || 'Request failed';
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
                const msg = errorData.message || errorData.error || errorData.detail || 'Request failed';
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
                const msg = errorData.message || errorData.error || errorData.detail || 'Login failed';
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
            const queryString = new URLSearchParams(params).toString();
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

        async addComment(ticketId, comment, isInternal = false) {
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

        async getProjects() {
            return this.request('/api/projects/');
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
           DEPARTMENTS
        ================================ */

        async getDepartments() {
            return this.request('/api/auth/departments/');
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
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `/api/auth/users/?${queryString}` : '/api/auth/users/';
            return this.request(url);
        }

        async registerUser(data) {
            return this.request('/api/auth/register/', {
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