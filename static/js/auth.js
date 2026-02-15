/**
 * auth.js - Authentication Handling
 * Dependencies: api.js (window.api)
 */

(function () {
    'use strict';

    // UI Helpers
    const ui = {
        showError: (message) => {
            const el = document.getElementById('error-message');
            if (el) {
                el.textContent = message;
                el.style.display = 'block';
                // Auto-hide after 5 seconds
                setTimeout(() => el.style.display = 'none', 5000);
            } else {
                alert(message);
            }
        },
        showSuccess: (message) => {
            const el = document.getElementById('success-message');
            if (el) {
                el.textContent = message;
                el.style.display = 'block';
                setTimeout(() => el.style.display = 'none', 3000);
            }
        },
        setLoading: (btn, isLoading, originalText) => {
            if (isLoading) {
                btn.disabled = true;
                btn.textContent = 'Please wait...';
            } else {
                btn.disabled = false;
                btn.textContent = originalText || 'Submit';
            }
        }
    };

    // Main Initialization
    document.addEventListener('DOMContentLoaded', async function () {
        const loginForm = document.getElementById('login-form');
        const companyName = window.api ? window.api.getCompanyName() : null;

        // Redirect Logic: If logged in, go to dashboard
        // We defer this to ensure window.api is ready
        if (window.api && window.api.getToken()) {
            // Check if we are incorrectly on a login page
            if (window.location.pathname.endsWith('/login') || window.location.pathname === '/') {
                if (companyName) {
                    // Get user from storage to check role
                    const user = JSON.parse(localStorage.getItem('user') || '{}');
                    if (user.role === 'admin') {
                        window.location.href = `/${companyName}/admin/dashboard`;
                    } else {
                        window.location.href = `/${companyName}/dashboard`;
                    }
                } else {
                    console.warn('Logged in but no company context found.');
                }
            }
            return;
        }

        // Login Form Handler
        if (loginForm) {
            loginForm.addEventListener('submit', async function (e) {
                e.preventDefault();

                const emailInput = document.getElementById('email');
                const passwordInput = document.getElementById('password');
                const submitBtn = loginForm.querySelector('button[type="submit"]');
                const btnText = submitBtn.textContent;

                const email = emailInput.value.trim();
                const password = passwordInput.value;

                if (!email || !password) {
                    ui.showError('Please enter both email and password.');
                    return;
                }

                try {
                    ui.setLoading(submitBtn, true, btnText);

                    // API Call: delegating to AuthService
                    // This handles the POST /api/{company}/auth/login internally
                    const response = await window.api.login(email, password);

                    ui.showSuccess('Login successful! Redirecting...');

                    // Redirect based on role or default to dashboard
                    setTimeout(() => {
                        const currentCompany = window.api.getCompanyName();
                        if (response.user.role === 'admin') {
                            window.location.href = `/${currentCompany}/admin/dashboard`;
                        } else {
                            window.location.href = `/${currentCompany}/dashboard`;
                        }
                    }, 800);

                } catch (error) {
                    console.error('Login error:', error);
                    let msg = error.message;

                    // User-friendly error mapping
                    if (msg.includes('401') || msg.toLowerCase().includes('invalid')) {
                        msg = 'Invalid email or password. Please try again.';
                    } else if (msg.includes('404')) {
                        msg = 'Login service not found. Check your URL.';
                    } else if (msg.includes('500')) {
                        msg = 'Server error. Please try again later.';
                    }

                    ui.showError(msg);
                } finally {
                    ui.setLoading(submitBtn, false, btnText);
                }
            });
        }
    });

    // Logout Helper (Global)
    window.logout = function () {
        // Use the existing logout modal in base.html if available
        const logoutModal = document.getElementById('logoutModal');
        if (logoutModal && typeof bootstrap !== 'undefined') {
            const bsModal = new bootstrap.Modal(logoutModal);
            bsModal.show();
        } else {
            // Fallback to generic confirm if specific modal is missing
            if (window.showConfirm) {
                window.showConfirm(
                    'Confirm Logout',
                    'Are you sure you want to log out?',
                    function () {
                        window.api.logout();
                        const company = window.api.getCompanyName();
                        window.location.href = `/${company}/login`;
                    }
                );
            } else if (confirm('Are you sure you want to log out?')) {
                window.api.logout();
                const company = window.api.getCompanyName();
                window.location.href = `/${company}/login`;
            }
        }
    };

})();