/**
 * Professional Animation Utilities
 * 
 * Lightweight JavaScript helpers for smooth, enterprise-grade animations
 */

// Skeleton loader for tables
function createSkeletonRow(columns = 8) {
    const row = document.createElement('tr');
    row.className = 'skeleton-row';
    row.innerHTML = Array(columns).fill(0).map(() => 
        '<td><div class="skeleton skeleton-text"></div></td>'
    ).join('');
    return row;
}

// Create skeleton loader for ticket list
function createTicketListSkeleton(count = 5) {
    const tbody = document.createElement('tbody');
    tbody.id = 'tickets-table';
    
    for (let i = 0; i < count; i++) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><div class="skeleton skeleton-text short"></div></td>
            <td>
                <div class="skeleton skeleton-text medium mb-1"></div>
                <div class="skeleton skeleton-text" style="width: 40%;"></div>
            </td>
            <td><div class="skeleton skeleton-badge"></div></td>
            <td><div class="skeleton skeleton-badge"></div></td>
            <td><div class="skeleton skeleton-text short"></div></td>
            <td><div class="skeleton skeleton-text short"></div></td>
            <td><div class="skeleton skeleton-text short"></div></td>
            <td><div class="skeleton skeleton-badge"></div></td>
        `;
        tbody.appendChild(row);
    }
    
    return tbody;
}

// Animate status change
function animateStatusChange(element, newStatus) {
    if (!element) return;
    
    element.classList.add('status-transition');
    
    setTimeout(() => {
        element.classList.remove('status-transition');
    }, 300);
}

// Smooth scroll to element
function smoothScrollTo(element, offset = 0) {
    if (!element) return;
    
    const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition - offset;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

// Fade in element
function fadeIn(element, duration = 200) {
    if (!element) return;
    
    element.style.opacity = '0';
    element.style.display = 'block';
    
    requestAnimationFrame(() => {
        element.style.transition = `opacity ${duration}ms ease-out`;
        element.style.opacity = '1';
    });
}

// Fade out element
function fadeOut(element, duration = 200, callback) {
    if (!element) return;
    
    element.style.transition = `opacity ${duration}ms ease-out`;
    element.style.opacity = '0';
    
    setTimeout(() => {
        element.style.display = 'none';
        if (callback) callback();
    }, duration);
}

// Slide in from direction
function slideIn(element, direction = 'up', duration = 200) {
    if (!element) return;
    
    const transforms = {
        up: 'translateY(20px)',
        down: 'translateY(-20px)',
        left: 'translateX(20px)',
        right: 'translateX(-20px)'
    };
    
    element.style.transform = transforms[direction] || transforms.up;
    element.style.opacity = '0';
    element.style.display = 'block';
    
    requestAnimationFrame(() => {
        element.style.transition = `transform ${duration}ms ease-out, opacity ${duration}ms ease-out`;
        element.style.transform = 'translate(0, 0)';
        element.style.opacity = '1';
    });
}

// Loading button state
function setButtonLoading(button, loading = true) {
    if (!button) return;
    
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = button.innerHTML.replace(/<i[^>]*>.*?<\/i>/, '') + '<i class="fas fa-spinner"></i>';
    } else {
        button.classList.remove('loading');
        button.disabled = false;
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    }
}

// Stagger animation for list items
function staggerAnimation(elements, delay = 50) {
    if (!elements || elements.length === 0) return;
    
    elements.forEach((element, index) => {
        if (element) {
            element.style.opacity = '0';
            element.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                element.style.transition = 'opacity 200ms ease-out, transform 200ms ease-out';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * delay);
        }
    });
}

// Pulse animation for attention
function pulse(element, count = 2) {
    if (!element) return;
    
    let current = 0;
    const interval = setInterval(() => {
        element.style.transform = 'scale(1.05)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 150);
        
        current++;
        if (current >= count) {
            clearInterval(interval);
        }
    }, 300);
}

// Shake animation for errors
function shake(element) {
    if (!element) return;
    
    element.style.animation = 'shake 0.5s ease-in-out';
    
    setTimeout(() => {
        element.style.animation = '';
    }, 500);
}

// Add shake keyframes if not exists
if (!document.getElementById('shake-keyframes')) {
    const style = document.createElement('style');
    style.id = 'shake-keyframes';
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
            20%, 40%, 60%, 80% { transform: translateX(4px); }
        }
    `;
    document.head.appendChild(style);
}

// Export for use in other scripts
window.AnimationUtils = {
    createSkeletonRow,
    createTicketListSkeleton,
    animateStatusChange,
    smoothScrollTo,
    fadeIn,
    fadeOut,
    slideIn,
    setButtonLoading,
    staggerAnimation,
    pulse,
    shake
};
