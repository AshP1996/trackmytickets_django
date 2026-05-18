/**
 * Shared utility functions for TrackMyTicket
 */

// Status Formatting
function getStatusClass(status) {
    const map = {
        'open': 'open',
        'in_progress': 'in-progress',
        'inprocess': 'in-progress',
        'waiting': 'waiting',
        'resolved': 'resolved',
        'closed': 'closed'
    };
    return map[status] || 'open';
}

function formatStatus(status) {
    if (!status) return '';
    return status.split('_').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');
}

function getStatusConfig(status) {
    const configs = {
        'open': { color: '#ffab00', icon: 'fa-circle' },
        'in_progress': { color: '#0052cc', icon: 'fa-spinner' },
        'inprocess': { color: '#0052cc', icon: 'fa-spinner' },
        'waiting': { color: '#ff5630', icon: 'fa-clock' },
        'resolved': { color: '#36b37e', icon: 'fa-check-circle' },
        'closed': { color: '#36b37e', icon: 'fa-check-circle' }
    };
    return configs[status] || { color: '#6b778c', icon: 'fa-circle' };
}

// Priority Formatting
function formatPriority(priority) {
    if (!priority) return '';
    return priority.charAt(0).toUpperCase() + priority.slice(1);
}

function getPriorityConfig(priority) {
    const configs = {
        'low': { icon: 'fa-arrow-down', color: '#36b37e' },
        'medium': { icon: 'fa-minus', color: '#ffab00' },
        'high': { icon: 'fa-arrow-up', color: '#ff5630' },
        'critical': { icon: 'fa-exclamation', color: '#de350b' }
    };
    return configs[priority] || configs.medium;
}

// Date Formatting
function formatDateTime(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        // Check for invalid date
        if (isNaN(date.getTime())) return '-';
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        console.error('Error formatting date:', e);
        return '-';
    }
}

function formatDate(dateString) {
    // Alias for formatDateTime or slightly different if needed
    // list.html used formatDate, details.html used formatDateTime
    return formatDateTime(dateString);
}


// File Size Formatting
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// String Truncation
function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// Export functions to global window object
window.getStatusClass = getStatusClass;
window.formatStatus = formatStatus;
window.getStatusConfig = getStatusConfig;
window.formatPriority = formatPriority;
window.getPriorityConfig = getPriorityConfig;
window.formatDateTime = formatDateTime;
window.formatDate = formatDate; // Alias
window.formatFileSize = formatFileSize;
window.truncate = truncate;

/* ===============================
   Searchable Dropdown (Combobox)
================================ */
class SearchableDropdown {
    constructor(selectElement) {
        this.select = selectElement;
        this.options = Array.from(selectElement.options);
        this.container = null;
        this.input = null;
        this.dropdown = null;

        this.init();
    }

    init() {
        // Prevent double initialization
        if (this.select.closest('.searchable-dropdown')) {
            return;
        }

        // Create container
        this.container = document.createElement('div');
        this.container.className = 'searchable-dropdown';
        this.container.style.position = 'relative';
        this.container.style.width = '100%';

        // Create input
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'form-control';

        // Handle placeholder
        const firstOption = this.options[0];
        const hasValue = firstOption && firstOption.value;
        this.input.placeholder = firstOption ? firstOption.text : 'Select...';

        // If the select has a value already selected (that isn't the placeholder), set it
        if (this.select.value && hasValue) {
            const selected = this.options.find(opt => opt.value === this.select.value);
            if (selected) this.input.value = selected.text;
        } else {
            this.input.value = '';
        }

        // Create dropdown list
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'dropdown-options';
        // Critical inline styles for robustness
        this.dropdown.style.display = 'none';
        this.dropdown.style.position = 'absolute';
        this.dropdown.style.top = '100%';
        this.dropdown.style.left = '0';
        this.dropdown.style.right = '0';
        this.dropdown.style.zIndex = '1000';
        this.dropdown.style.backgroundColor = 'white'; // Ensure opacity
        this.dropdown.style.border = '1px solid #ddd';
        this.dropdown.style.borderRadius = '0 0 4px 4px';
        this.dropdown.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
        this.dropdown.style.maxHeight = '200px';
        this.dropdown.style.overflowY = 'auto';

        // Build initial list
        this.renderOptions(this.options);

        // Insert into DOM
        this.select.parentNode.insertBefore(this.container, this.select);
        this.container.appendChild(this.input);
        this.container.appendChild(this.dropdown);
        this.container.appendChild(this.select);

        // Hide original select
        this.select.style.display = 'none';

        // Event Listeners
        this.input.addEventListener('input', () => this.filterOptions());

        this.input.addEventListener('focus', () => this.showAllOptions());
        this.input.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showAllOptions();
        });

        // Close when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.dropdown.classList.remove('show');
                this.dropdown.style.display = 'none';
                this.syncInputWithSelect();
            }
        });
    }

    syncInputWithSelect() {
        const selectedValue = this.select.value;
        const selectedOption = this.options.find(opt => opt.value === selectedValue);

        if (selectedOption && selectedOption.value) {
            this.input.value = selectedOption.text;
        } else {
            this.input.value = '';
        }
    }

    getSelectableOptions() {
        return this.options.filter(opt =>
            opt.value &&
            opt.value.trim() !== '' &&
            !opt.text.toLowerCase().includes('select ')
        );
    }

    showAllOptions() {
        this.options = Array.from(this.select.options);
        const selectable = this.getSelectableOptions();
        this.renderOptions(selectable);
        if (selectable.length > 0) {
            this.dropdown.classList.add('show');
            this.dropdown.style.display = 'block';
        }
    }

    renderOptions(options) {
        this.dropdown.innerHTML = '';

        const validOptions = options.filter(opt =>
            opt.value &&
            opt.value.trim() !== '' &&
            !opt.text.toLowerCase().includes('select ')
        );

        if (validOptions.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'dropdown-option no-results';
            noResults.textContent = 'No results found';
            this.dropdown.appendChild(noResults);
            // Don't show dropdown if no results and no query? No, show "No results" is better feedback.
            return;
        }

        validOptions.forEach(opt => {
            const div = document.createElement('div');
            div.className = 'dropdown-option';
            div.textContent = opt.text;
            div.dataset.value = opt.value;

            if (this.select.value === opt.value) {
                div.classList.add('selected');
            }

            div.addEventListener('click', () => {
                this.selectOption(opt.value, opt.text);
            });

            this.dropdown.appendChild(div);
        });
    }

    filterOptions() {
        this.options = Array.from(this.select.options);
        const query = this.input.value.toLowerCase().trim();

        if (query.length === 0) {
            this.showAllOptions();
            return;
        }

        const filtered = this.options.filter(opt =>
            opt.text.toLowerCase().includes(query)
        );
        this.renderOptions(filtered);
        this.dropdown.classList.add('show');
        this.dropdown.style.display = 'block';
    }

    selectOption(value, text) {
        this.select.value = value;
        this.input.value = text;
        this.dropdown.classList.remove('show');
        this.dropdown.style.display = 'none';

        // Trigger change event on original select for any listeners
        const event = new Event('change', { bubbles: true });
        this.select.dispatchEvent(event);
    }
}

window.SearchableDropdown = SearchableDropdown;
