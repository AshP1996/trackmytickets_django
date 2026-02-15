/**
 * Data Sources Management JavaScript
 */

let currentSourceId = null;
let databaseTypes = {};

// Database setup guides
const SETUP_GUIDES = {
    sqlite: `
        <h4><i class="fas fa-database"></i> SQLite Setup Guide</h4>
        <p>SQLite is a file-based database that doesn't require a server.</p>
        
        <h5>Requirements:</h5>
        <ul>
            <li>Database file path (e.g., <code>/path/to/database.db</code>)</li>
            <li>Read permissions on the file</li>
        </ul>
        
        <h5>Example Configuration:</h5>
        <pre><code>Database Path: /var/data/tickets.db</code></pre>
        
        <div class="alert alert-info">
            <strong>Note:</strong> SQLite is perfect for small to medium datasets and doesn't require network configuration.
        </div>
    `,
    postgres: `
        <h4><i class="fas fa-elephant"></i> PostgreSQL Setup Guide</h4>
        
        <h5>Requirements:</h5>
        <ul>
            <li>PostgreSQL server (version 9.6+)</li>
            <li>Database created</li>
            <li>User with SELECT permissions</li>
            <li>Network access to server</li>
        </ul>
        
        <h5>Create Database User:</h5>
        <pre><code>CREATE USER ticket_reader WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE your_database TO ticket_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ticket_reader;</code></pre>
        
        <h5>Firewall Configuration:</h5>
        <p>Ensure port 5432 is accessible from your application server.</p>
        
        <h5>Connection String Example:</h5>
        <pre><code>Host: db.example.com
Port: 5432
Database: production_db
Username: ticket_reader
Password: secure_password</code></pre>
    `,
    mysql: `
        <h4><i class="fas fa-database"></i> MySQL/MariaDB Setup Guide</h4>
        
        <h5>Requirements:</h5>
        <ul>
            <li>MySQL 5.7+ or MariaDB 10.2+</li>
            <li>Database created</li>
            <li>User with SELECT permissions</li>
            <li>Network access to server</li>
        </ul>
        
        <h5>Create Database User:</h5>
        <pre><code>CREATE USER 'ticket_reader'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON your_database.* TO 'ticket_reader'@'%';
FLUSH PRIVILEGES;</code></pre>
        
        <h5>Firewall Configuration:</h5>
        <p>Ensure port 3306 is accessible from your application server.</p>
        
        <h5>Connection Example:</h5>
        <pre><code>Host: mysql.example.com
Port: 3306
Database: tickets_db
Username: ticket_reader
Password: secure_password</code></pre>
    `,
    mongodb: `
        <h4><i class="fas fa-leaf"></i> MongoDB Setup Guide</h4>
        
        <h5>Requirements:</h5>
        <ul>
            <li>MongoDB 4.0+</li>
            <li>Database and collection created</li>
            <li>User with read permissions (optional for local instances)</li>
            <li>Network access to server</li>
        </ul>
        
        <h5>Create Database User:</h5>
        <pre><code>use your_database
db.createUser({
  user: "ticket_reader",
  pwd: "secure_password",
  roles: [{ role: "read", db: "your_database" }]
})</code></pre>
        
        <h5>Connection Example:</h5>
        <pre><code>Host: mongodb.example.com
Port: 27017
Database: tickets
Username: ticket_reader (optional)
Password: secure_password (optional)</code></pre>
        
        <div class="alert alert-warning">
            <strong>Note:</strong> MongoDB uses collections instead of tables. Schema mapping works differently for NoSQL databases.
        </div>
    `
};

// Field templates for each database type
const FIELD_TEMPLATES = {
    sqlite: ['database'],
    postgres: ['host', 'port', 'database', 'username', 'password', 'ssl'],
    mysql: ['host', 'port', 'database', 'username', 'password', 'ssl'],
    mariadb: ['host', 'port', 'database', 'username', 'password', 'ssl'],
    mongodb: ['host', 'port', 'database', 'username', 'password', 'ssl'],
    sqlserver: ['host', 'port', 'database', 'username', 'password', 'ssl'],
    oracle: ['host', 'port', 'database', 'username', 'password'],
    redis: ['host', 'port', 'password', 'database']
};

async function loadDatabaseTypes() {
    try {
        databaseTypes = await api.getDatabaseTypes();
        renderDatabaseTypeOptions();
    } catch (error) {
        console.error('Error loading database types:', error);
        // Fallback to hardcoded types
        databaseTypes = {
            sqlite: { name: 'SQLite', default_port: null, icon: 'fa-database', color: '#003B57' },
            postgres: { name: 'PostgreSQL', default_port: 5432, icon: 'fa-elephant', color: '#336791' },
            mysql: { name: 'MySQL', default_port: 3306, icon: 'fa-database', color: '#4479A1' },
            mongodb: { name: 'MongoDB', default_port: 27017, icon: 'fa-leaf', color: '#47A248' }
        };
        renderDatabaseTypeOptions();
    }
}

function renderDatabaseTypeOptions() {
    const select = document.getElementById('db-type-select');
    if (!select) return;

    select.innerHTML = '<option value="">Select database type...</option>';

    for (const [key, config] of Object.entries(databaseTypes)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = config.name;
        if (key === 'sqlite') {
            option.selected = true;
        }
        select.appendChild(option);
    }

    // Trigger change to show default fields
    if (select.value === 'sqlite') {
        onDatabaseTypeChange();
    }
}

function onDatabaseTypeChange() {
    const select = document.getElementById('db-type-select');
    const dbType = select.value;
    const description = document.getElementById('db-type-description');
    const dynamicFields = document.getElementById('dynamic-fields');

    if (!dbType) {
        description.textContent = '';
        dynamicFields.innerHTML = '';
        return;
    }

    const config = databaseTypes[dbType];
    description.textContent = config.description || '';

    // Render dynamic fields
    const fields = FIELD_TEMPLATES[dbType] || [];
    let html = '';

    for (const field of fields) {
        if (field === 'database') {
            const label = dbType === 'sqlite' ? 'Database File Path' : 'Database Name';
            const placeholder = dbType === 'sqlite' ? '/path/to/database.db' : 'database_name';
            html += `
                <div class="mb-3">
                    <label class="form-label">${label}</label>
                    <input type="text" class="form-control" name="database" required placeholder="${placeholder}">
                </div>
            `;
        } else if (field === 'host') {
            html += `
                <div class="mb-3">
                    <label class="form-label">Host</label>
                    <input type="text" class="form-control" name="host" required placeholder="db.example.com">
                </div>
            `;
        } else if (field === 'port') {
            html += `
                <div class="mb-3">
                    <label class="form-label">Port</label>
                    <input type="number" class="form-control" name="port" value="${config.default_port || ''}" placeholder="${config.default_port || ''}">
                </div>
            `;
        } else if (field === 'username') {
            html += `
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" class="form-control" name="username" placeholder="db_user">
                </div>
            `;
        } else if (field === 'password') {
            html += `
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" class="form-control" name="password" placeholder="••••••••">
                    <small class="form-text text-muted">Password will be encrypted before storage</small>
                </div>
            `;
        } else if (field === 'ssl') {
            html += `
                <div class="mb-3 form-check">
                    <input type="checkbox" class="form-check-input" name="ssl_enabled" id="ssl-enabled">
                    <label class="form-check-label" for="ssl-enabled">Enable SSL/TLS</label>
                </div>
            `;
        }
    }

    // Add setup guide link
    if (SETUP_GUIDES[dbType]) {
        html += `
            <div class="mb-3">
                <button type="button" class="btn btn-sm btn-outline-info" onclick="showSetupGuide('${dbType}')">
                    <i class="fas fa-book"></i> View Setup Guide
                </button>
            </div>
        `;
    }

    dynamicFields.innerHTML = html;
}

function showSetupGuide(dbType) {
    const modal = new bootstrap.Modal(document.getElementById('setupGuideModal'));
    document.getElementById('setup-guide-title').textContent = `${databaseTypes[dbType].name} Setup Guide`;
    document.getElementById('setup-guide-content').innerHTML = SETUP_GUIDES[dbType] || '<p>No setup guide available for this database type.</p>';
    modal.show();
}

async function testConnectionFromForm() {
    const form = document.getElementById('data-source-form');
    const formData = new FormData(form);
    const resultSpan = document.getElementById('connection-test-result');
    const testBtn = document.getElementById('test-connection-btn');

    testBtn.disabled = true;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    resultSpan.innerHTML = '';

    const data = {
        type: formData.get('type'),
        host: formData.get('host'),
        port: formData.get('port') ? parseInt(formData.get('port')) : null,
        database: formData.get('database'),
        username: formData.get('username'),
        password: formData.get('password'),
        ssl_enabled: formData.get('ssl_enabled') === 'on'
    };

    try {
        const result = await api.testConnection(data);
        if (result.success) {
            resultSpan.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Connection successful!</span>';
            if (result.details) {
                resultSpan.innerHTML += `<br><small class="text-muted">Version: ${result.details.version || 'N/A'}</small>`;
            }
        } else {
            resultSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${result.message}</span>`;
        }
    } catch (error) {
        resultSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${error.message}</span>`;
    } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
    }
}

async function loadDataSources() {
    try {
        const dataSources = await api.getDataSources();
        const dataSourcesList = dataSources.results || dataSources || [];
        renderDataSources(dataSourcesList);
    } catch (error) {
        showError('Failed to load data sources: ' + error.message);
    }
}

function renderDataSources(dataSources) {
    const tbody = document.getElementById('data-sources-table');
    if (dataSources.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No data sources configured</td></tr>';
        return;
    }

    tbody.innerHTML = dataSources.map(ds => {
        const statusBadge = ds.connection_status === 'connected' ? 'success' :
            ds.connection_status === 'failed' ? 'danger' : 'secondary';
        const statusText = ds.connection_status === 'connected' ? 'Connected' :
            ds.connection_status === 'failed' ? 'Failed' : 'Untested';

        return `
            <tr>
                <td><strong>${ds.name}</strong></td>
                <td><span class="badge bg-info">${ds.type_display || ds.type}</span></td>
                <td><code>${ds.host ? `${ds.host}:${ds.port}` : ds.database}</code></td>
                <td><code>${ds.database}</code></td>
                <td>
                    <span class="badge bg-${statusBadge}">${statusText}</span>
                    ${ds.connection_status === 'failed' ? `<br><small class="text-danger">${ds.connection_error || ''}</small>` : ''}
                </td>
                <td>${ds.mapping_count || 0}</td>
                <td>${ds.last_sync_at ? new Date(ds.last_sync_at).toLocaleString() : 'Never'}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="testDataSource(${ds.id})" title="Test Connection">
                        <i class="fas fa-plug"></i>
                    </button>
                    <button class="btn btn-sm btn-info" onclick="manageMappings(${ds.id})" title="Manage Mappings">
                        <i class="fas fa-table"></i>
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="toggleDataSource(${ds.id}, ${ds.is_active})">
                        <i class="fas fa-${ds.is_active ? 'ban' : 'check'}"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDataSource(${ds.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function testDataSource(sourceId) {
    try {
        const result = await api.testDataSource(sourceId);
        if (result.success) {
            showSuccess('Connection test successful!');
        } else {
            showError(`Connection test failed: ${result.message}`);
        }
        loadDataSources();
    } catch (error) {
        showError('Connection test failed: ' + error.message);
    }
}

async function manageMappings(sourceId) {
    currentSourceId = sourceId;
    try {
        const mappings = await api.getMappings(sourceId);
        const mappingsList = document.getElementById('mappings-list');
        if (mappings.length === 0) {
            mappingsList.innerHTML = '<div class="text-muted text-center py-3">No mappings configured</div>';
        } else {
            mappingsList.innerHTML = mappings.map(m => `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${m.table_name}</strong> → ${m.project_name || 'Unknown Project'}
                        <br><small class="text-muted">ID Column: ${m.id_column} | Last Synced: ${m.last_synced_id || 'None'}</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteMapping(${m.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        }
        const modal = new bootstrap.Modal(document.getElementById('manageMappingsModal'));
        modal.show();
    } catch (error) {
        showError('Failed to load mappings: ' + error.message);
    }
}

function showAddMappingModal() {
    loadProjects();
    const modal = new bootstrap.Modal(document.getElementById('addMappingModal'));
    modal.show();
}

async function loadProjects() {
    try {
        const response = await api.getProjects();
        const projectsList = response.results || response.projects || response || [];
        const select = document.getElementById('mapping-project-select');
        if (Array.isArray(projectsList)) {
            select.innerHTML = projectsList.map(p =>
                `<option value="${p.id}">${p.name} (${p.key})</option>`
            ).join('');
        }
    } catch (error) {
        showError('Failed to load projects: ' + error.message);
    }
}

async function toggleDataSource(sourceId, isActive) {
    try {
        await api.updateDataSource(sourceId, { is_active: !isActive });
        showSuccess('Data source updated');
        loadDataSources();
    } catch (error) {
        showError('Failed to update data source: ' + error.message);
    }
}

async function deleteDataSource(sourceId) {
    window.showConfirm(
        'Delete Data Source',
        'Are you sure you want to delete this data source? All mappings will be deleted.',
        async () => {
            try {
                await api.deleteDataSource(sourceId);
                showSuccess('Data source deleted successfully');
                loadDataSources();
            } catch (error) {
                showError('Failed to delete data source: ' + error.message);
            }
        },
        true // isDestructive
    );
}

async function deleteMapping(mappingId) {
    window.showConfirm(
        'Delete Mapping',
        'Are you sure you want to delete this mapping?',
        async () => {
            try {
                await api.deleteMapping(mappingId);
                showSuccess('Mapping deleted successfully');
                manageMappings(currentSourceId);
                loadDataSources();
            } catch (error) {
                showError('Failed to delete mapping: ' + error.message);
            }
        },
        true // isDestructive
    );
}

// Event listeners
document.addEventListener('DOMContentLoaded', function () {
    loadDatabaseTypes();
    loadDataSources();

    // Database type change
    const dbTypeSelect = document.getElementById('db-type-select');
    if (dbTypeSelect) {
        dbTypeSelect.addEventListener('change', onDatabaseTypeChange);
    }

    // Test connection button
    const testBtn = document.getElementById('test-connection-btn');
    if (testBtn) {
        testBtn.addEventListener('click', testConnectionFromForm);
    }

    // Add Data Source button handler
    const addBtn = document.getElementById('add-data-source-btn');
    if (addBtn) {
        addBtn.addEventListener('click', function () {
            const modalElement = document.getElementById('addDataSourceModal');
            const form = document.getElementById('data-source-form');
            if (form) form.reset();

            let modal = bootstrap.Modal.getInstance(modalElement);
            if (!modal) {
                modal = new bootstrap.Modal(modalElement, {
                    backdrop: true,
                    keyboard: true,
                    focus: true
                });
            }
            modal.show();

            // Trigger database type change to show default fields
            setTimeout(() => onDatabaseTypeChange(), 100);
        });
    }

    // Data source form submission
    document.getElementById('data-source-form').addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const dataSourceData = {
            name: formData.get('name'),
            type: formData.get('type'),
            host: formData.get('host') || null,
            port: formData.get('port') ? parseInt(formData.get('port')) : null,
            database: formData.get('database'),
            username: formData.get('username') || null,
            password: formData.get('password') || null,
            ssl_enabled: formData.get('ssl_enabled') === 'on'
        };

        try {
            await api.createDataSource(dataSourceData);
            showSuccess('Data source created successfully');
            bootstrap.Modal.getInstance(document.getElementById('addDataSourceModal')).hide();
            e.target.reset();
            loadDataSources();
        } catch (error) {
            showError('Failed to create data source: ' + error.message);
        }
    });

    // Mapping form submission
    document.getElementById('mapping-form').addEventListener('submit', async function (e) {
        e.preventDefault();
        if (!currentSourceId) return;

        const formData = new FormData(e.target);
        let fieldMapping;
        try {
            fieldMapping = JSON.parse(formData.get('field_mapping'));
        } catch (error) {
            showError('Invalid JSON in field mapping');
            return;
        }

        const mappingData = {
            table_name: formData.get('table_name'),
            id_column: formData.get('id_column'),
            project_id: parseInt(formData.get('project_id')),
            field_mapping: fieldMapping
        };

        try {
            await api.createMapping(currentSourceId, mappingData);
            showSuccess('Mapping created successfully');
            bootstrap.Modal.getInstance(document.getElementById('addMappingModal')).hide();
            e.target.reset();
            manageMappings(currentSourceId);
            loadDataSources();
        } catch (error) {
            showError('Failed to create mapping: ' + error.message);
        }
    });
});

// Make functions globally accessible
window.manageMappings = manageMappings;
window.showAddMappingModal = showAddMappingModal;
window.testDataSource = testDataSource;
window.toggleDataSource = toggleDataSource;
window.deleteDataSource = deleteDataSource;
window.deleteMapping = deleteMapping;
window.showSetupGuide = showSetupGuide;
