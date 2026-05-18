/**
 * Shared auth page UX — password toggle, alerts, org context, submit loading
 */
(function () {
    'use strict';

    function getOrgSlugFromPath() {
        const KNOWN = new Set([
            'login', 'dashboard', 'tickets', 'admin', 'head', 'projects',
            'notifications', 'forgot-password', 'reset-password', 'onboarding',
            'register', 'api', 'static', 'platform',
        ]);
        const parts = window.location.pathname.replace(/^\/+/, '').split('/');
        return parts[0] && !KNOWN.has(parts[0]) ? parts[0] : null;
    }

    function initPasswordToggle() {
        const toggle = document.getElementById('toggle-password');
        const input = document.getElementById('password');
        if (!toggle || !input) return;

        toggle.addEventListener('click', function () {
            const isPassword = input.getAttribute('type') === 'password';
            input.setAttribute('type', isPassword ? 'text' : 'password');
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye', !isPassword);
                icon.classList.toggle('fa-eye-slash', isPassword);
            }
            this.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        });
    }

    function setSubmitLoading(btn, loading, defaultHtml) {
        if (!btn) return;
        if (loading) {
            btn.disabled = true;
            if (!btn.dataset.defaultHtml) btn.dataset.defaultHtml = btn.innerHTML;
            btn.innerHTML = '<span class="auth-spinner" aria-hidden="true"></span> Signing in…';
        } else {
            btn.disabled = false;
            btn.innerHTML = defaultHtml || btn.dataset.defaultHtml || 'Sign in';
        }
    }

    function showAlert(id, message, type) {
        const el = document.getElementById(id);
        if (!el) return;
        el.className = 'auth-alert auth-alert--' + type + ' is-visible';
        const text = el.querySelector('.auth-alert-text');
        if (text) text.textContent = message;
    }

    function hideAlerts() {
        ['error-message', 'success-message'].forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.classList.remove('is-visible');
        });
    }

    function initOrgContext() {
        const chip = document.getElementById('org-context-chip');
        const slugEl = document.getElementById('org-slug-display');
        const urlEl = document.getElementById('org-url-hint');
        if (!chip) return;

        const bodySlug = (document.body.dataset.orgSlug || '').trim();
        const slug = bodySlug || getOrgSlugFromPath();
        const cfg = window.APP_CONFIG || {};
        const baseDomain = cfg.BASE_DOMAIN || window.location.hostname;
        const port = cfg.PORT;
        const portSuffix = port && port !== 80 && port !== 443 ? ':' + port : '';
        const protocol = cfg.PROTOCOL || window.location.protocol.replace(':', '');

        if (slug) {
            if (slugEl) slugEl.textContent = slug;
            if (urlEl) {
                urlEl.textContent = protocol + '://' + baseDomain + portSuffix + '/' + slug + '/login';
            }
            chip.style.display = 'flex';
            document.title = 'Sign in — ' + slug + ' | TrackMyTickets';
        }
    }

    function initForgotLink() {
        const link = document.getElementById('forgot-password-link');
        if (!link) return;
        const slug = (document.body.dataset.orgSlug || '').trim() || getOrgSlugFromPath();
        link.href = slug ? '/' + slug + '/forgot-password' : '/platform/forgot-password';
    }

    window.AuthLoginUI = {
        setSubmitLoading: setSubmitLoading,
        showAlert: showAlert,
        hideAlerts: hideAlerts,
    };

    document.addEventListener('DOMContentLoaded', function () {
        initPasswordToggle();
        initOrgContext();
        initForgotLink();

    });
})();
