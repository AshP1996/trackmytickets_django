/**
 * Enhanced Ticket Interaction Utilities
 * 
 * Provides inline editing, auto-save, mentions, and improved UX
 */

// Inline editing functionality
class InlineEditor {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            onSave: options.onSave || (() => { }),
            onCancel: options.onCancel || (() => { }),
            placeholder: options.placeholder || 'Click to edit',
            multiline: options.multiline || false,
            ...options
        };
        this.originalValue = element.textContent.trim();
        this.isEditing = false;
        this.init();
    }

    init() {
        this.element.style.cursor = 'pointer';
        this.element.addEventListener('click', () => this.startEdit());
    }

    startEdit() {
        if (this.isEditing) return;
        this.isEditing = true;
        this.originalValue = this.element.textContent.trim();

        const input = this.options.multiline ?
            document.createElement('textarea') :
            document.createElement('input');

        if (!this.options.multiline) {
            input.type = 'text';
        }
        input.value = this.originalValue;
        input.className = 'form-control';
        input.style.width = '100%';
        input.style.minHeight = this.options.multiline ? '100px' : 'auto';
        input.placeholder = this.options.placeholder;

        // Replace element with input
        this.element.style.display = 'none';
        this.element.parentNode.insertBefore(input, this.element);

        // Focus and select
        input.focus();
        if (!this.options.multiline) {
            input.select();
        }

        // Save on blur or Enter (if single line)
        input.addEventListener('blur', () => this.save(input));
        if (!this.options.multiline) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.save(input);
                } else if (e.key === 'Escape') {
                    this.cancel(input);
                }
            });
        } else {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.cancel(input);
                } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.save(input);
                }
            });
        }
    }

    save(input) {
        const newValue = input.value.trim();

        if (newValue !== this.originalValue && newValue) {
            this.element.textContent = newValue;
            this.options.onSave(newValue, this.originalValue);
        }

        this.cancel(input);
    }

    cancel(input) {
        input.remove();
        this.element.style.display = '';
        this.isEditing = false;
    }
}

// Auto-save comment drafts
class CommentDraftManager {
    constructor(textareaId, ticketId) {
        this.textarea = document.getElementById(textareaId);
        this.ticketId = ticketId;
        this.storageKey = `ticket_${ticketId}_comment_draft`;
        this.debounceTimer = null;
        this.init();
    }

    init() {
        // Load saved draft
        const saved = localStorage.getItem(this.storageKey);
        if (saved && this.textarea) {
            this.textarea.value = saved;
            this.showDraftIndicator();
        }

        // Auto-save on input
        if (this.textarea) {
            this.textarea.addEventListener('input', () => this.autoSave());
        }
    }

    autoSave() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            const value = this.textarea.value.trim();
            if (value) {
                localStorage.setItem(this.storageKey, value);
                this.showDraftIndicator();
            } else {
                localStorage.removeItem(this.storageKey);
                this.hideDraftIndicator();
            }
        }, 500);
    }

    showDraftIndicator() {
        let indicator = document.getElementById('draft-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'draft-indicator';
            indicator.className = 'text-xs text-tertiary';
            indicator.style.marginTop = 'var(--spacing-xs)';
            indicator.innerHTML = '<i class="fas fa-save"></i> Draft saved';
            this.textarea.parentNode.appendChild(indicator);
        }
        indicator.style.display = 'block';
    }

    hideDraftIndicator() {
        const indicator = document.getElementById('draft-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    clear() {
        localStorage.removeItem(this.storageKey);
        this.hideDraftIndicator();
    }
}

// @Mention functionality
class MentionManager {
    constructor(textarea, users) {
        this.textarea = textarea;
        this.users = users || [];
        this.mentionStart = -1;
        this.mentionEnd = -1;
        this.currentMentions = [];
        this.init();
    }

    init() {
        this.textarea.addEventListener('input', (e) => this.handleInput(e));
        this.textarea.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    handleInput(e) {
        const value = this.textarea.value;
        const cursorPos = this.textarea.selectionStart;

        // Check for @mention
        const textBeforeCursor = value.substring(0, cursorPos);
        const match = textBeforeCursor.match(/@(\w*)$/);

        if (match) {
            this.mentionStart = cursorPos - match[0].length;
            this.mentionEnd = cursorPos;
            this.showMentionSuggestions(match[1]);
        } else {
            this.hideMentionSuggestions();
        }
    }

    handleKeydown(e) {
        const suggestions = document.getElementById('mention-suggestions');
        if (!suggestions || suggestions.style.display === 'none') return;

        const items = suggestions.querySelectorAll('.mention-item');
        const active = suggestions.querySelector('.mention-item.active');
        let activeIndex = active ? Array.from(items).indexOf(active) : -1;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = (activeIndex + 1) % items.length;
            this.setActiveSuggestion(items[activeIndex]);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
            this.setActiveSuggestion(items[activeIndex]);
        } else if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            if (active) {
                this.insertMention(active.dataset.userId, active.dataset.userName);
            }
        } else if (e.key === 'Escape') {
            this.hideMentionSuggestions();
        }
    }

    showMentionSuggestions(query) {
        const filtered = this.users.filter(user =>
            user.name.toLowerCase().includes(query.toLowerCase()) ||
            user.email.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5);

        if (filtered.length === 0) {
            this.hideMentionSuggestions();
            return;
        }

        let suggestions = document.getElementById('mention-suggestions');
        if (!suggestions) {
            suggestions = document.createElement('div');
            suggestions.id = 'mention-suggestions';
            suggestions.style.cssText = `
                position: absolute;
                background: white;
                border: 1px solid var(--color-border);
                border-radius: var(--radius-md);
                box-shadow: var(--shadow-lg);
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                margin-top: 4px;
            `;
            this.textarea.parentNode.style.position = 'relative';
            this.textarea.parentNode.appendChild(suggestions);
        }

        suggestions.innerHTML = filtered.map(user => `
            <div class="mention-item" 
                 data-user-id="${user.id}" 
                 data-user-name="${user.name}"
                 style="padding: var(--spacing-sm) var(--spacing-md); cursor: pointer; border-bottom: 1px solid var(--color-border-light);"
                 onmouseover="this.classList.add('active')"
                 onmouseout="this.classList.remove('active')"
                 onclick="window.MentionManager.insertMention(${user.id}, '${user.name}')">
                <div class="font-semibold">${user.name}</div>
                <div class="text-xs text-tertiary">${user.email}</div>
            </div>
        `).join('');

        suggestions.style.display = 'block';
        this.setActiveSuggestion(suggestions.querySelector('.mention-item'));
    }

    setActiveSuggestion(item) {
        const items = document.querySelectorAll('.mention-item');
        items.forEach(i => i.classList.remove('active'));
        if (item) {
            item.classList.add('active');
            item.style.backgroundColor = 'var(--color-bg-hover)';
        }
    }

    insertMention(userId, userName) {
        const value = this.textarea.value;
        const before = value.substring(0, this.mentionStart);
        const after = value.substring(this.mentionEnd);
        const mention = `@${userName} `;

        this.textarea.value = before + mention + after;
        this.textarea.selectionStart = this.textarea.selectionEnd = before.length + mention.length;
        this.textarea.focus();

        this.hideMentionSuggestions();
        this.currentMentions.push({ userId, userName, position: before.length });
    }

    hideMentionSuggestions() {
        const suggestions = document.getElementById('mention-suggestions');
        if (suggestions) {
            suggestions.style.display = 'none';
        }
    }

    getMentions() {
        return this.currentMentions;
    }
}

// Activity timeline component
class ActivityTimeline {
    constructor(containerId, activities) {
        this.container = document.getElementById(containerId);
        this.activities = activities || [];
        this.render();
    }

    render() {
        if (!this.container) return;

        if (this.activities.length === 0) {
            this.container.innerHTML = '<p class="text-center text-tertiary">No activity yet</p>';
            return;
        }

        // Group activities by date
        const grouped = this.groupByDate(this.activities);

        this.container.innerHTML = Object.keys(grouped).map(date => `
            <div class="timeline-group" style="margin-bottom: var(--spacing-lg);">
                <div class="timeline-date" style="font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-tertiary); text-transform: uppercase; margin-bottom: var(--spacing-md); padding-bottom: var(--spacing-xs); border-bottom: 1px solid var(--color-border-light);">
                    ${this.formatDate(date)}
                </div>
                ${grouped[date].map(activity => this.renderActivity(activity)).join('')}
            </div>
        `).join('');
    }

    groupByDate(activities) {
        const grouped = {};
        activities.forEach(activity => {
            const date = new Date(activity.created_at).toDateString();
            if (!grouped[date]) {
                grouped[date] = [];
            }
            grouped[date].push(activity);
        });
        return grouped;
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid date';

        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
    }

    renderActivity(activity) {
        const icon = this.getActivityIcon(activity);
        const color = this.getActivityColor(activity);

        return `
            <div class="timeline-item" style="display: flex; gap: var(--spacing-md); padding: var(--spacing-sm) 0; position: relative;">
                <div class="timeline-icon" style="width: 32px; height: 32px; border-radius: 50%; background-color: ${color}; color: white; opacity: 0.8; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: var(--font-size-sm);">
                    ${icon}
                </div>
                <div class="timeline-content" style="flex: 1; padding-bottom: var(--spacing-sm);">
                    <div class="timeline-header" style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--spacing-xs);">
                        <div>
                            <span class="font-semibold">${activity.user_name || 'System'}</span>
                            <span class="text-tertiary">${this.formatAction(activity)}</span>
                        </div>
                        <span class="text-xs text-tertiary">${this.formatTime(activity.created_at)}</span>
                    </div>
                    ${this.formatDetails(activity)}
                </div>
            </div>
        `;
    }

    // ... helper methods ...
    getActivityIcon(activity) {
        const action = activity.action || '';
        if (action.includes('created')) return '<i class="fas fa-plus"></i>';
        if (action.includes('status')) return '<i class="fas fa-exchange-alt"></i>';
        if (action.includes('assigned')) return '<i class="fas fa-user-plus"></i>';
        if (action.includes('comment')) return '<i class="fas fa-comment"></i>';
        if (action.includes('priority')) return '<i class="fas fa-flag"></i>';
        return '<i class="fas fa-edit"></i>';
    }

    getActivityColor(activity) {
        const action = activity.action || '';
        if (action.includes('created')) return 'var(--color-status-resolved)';
        if (action.includes('status')) return 'var(--color-status-in-progress)';
        if (action.includes('assigned')) return 'var(--color-brand-primary)';
        if (action.includes('comment')) return 'var(--color-status-waiting)';
        return 'var(--color-text-tertiary)';
    }

    formatAction(activity) {
        return activity.action || 'made a change';
    }

    formatDetails(activity) {
        if (activity.field && activity.old_value && activity.new_value) {
            return `
                <div class="timeline-details" style="background-color: var(--color-bg-secondary); padding: var(--spacing-sm); border-radius: var(--radius-md); margin-top: var(--spacing-xs);">
                    <div class="text-xs text-tertiary mb-1">${activity.field}</div>
                    <div style="display: flex; gap: var(--spacing-sm); align-items: center;">
                        <span class="text-sm" style="text-decoration: line-through; color: var(--color-text-tertiary);">${activity.old_value}</span>
                        <i class="fas fa-arrow-right text-xs text-tertiary"></i>
                        <span class="text-sm font-medium">${activity.new_value}</span>
                    </div>
                </div>
            `;
        }
        return '';
    }

    formatTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '';

        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

// Export for global use
window.InlineEditor = InlineEditor;
window.CommentDraftManager = CommentDraftManager;
window.MentionManager = MentionManager;
window.ActivityTimeline = ActivityTimeline;
