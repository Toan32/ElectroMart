/* shared.js - Global JavaScript utilities for ElectroMart */

document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initActiveLinks();
    initGlobalNavLinks();
    initModals();
});

/* ==========================================================================
   GLOBAL NAVBAR LINKS MAPPING (Django URLs integration)
   ========================================================================== */
function initGlobalNavLinks() {
    // 1. Cart link mapping
    const cartLink = Array.from(document.querySelectorAll('.hact')).find(el => el.textContent.includes('Cart'));
    if (cartLink) {
        cartLink.setAttribute('href', '/cart/');
    }

    // 2. Track order link mapping
    const trackLinks = Array.from(document.querySelectorAll('a')).filter(el => el.textContent.toLowerCase().includes('track order'));
    trackLinks.forEach(link => {
        link.setAttribute('href', '/tracking/');
    });
}

/* Theme is always light - dark mode removed */

/* ==========================================================================
   MOBILE NAVIGATION
   ========================================================================== */
function initMobileNav() {
    // Customer mobile nav toggle
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('is-active');
            mobileMenuBtn.textContent = navLinks.classList.contains('is-active') ? '✕' : '☰';
        });
    }

    // Admin sidebar toggle
    const adminToggleBtn = document.querySelector('.admin-toggle-btn');
    const adminSidebar = document.querySelector('.admin-sidebar');
    
    if (adminToggleBtn && adminSidebar) {
        adminToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            adminSidebar.classList.toggle('is-active');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (adminSidebar.classList.contains('is-active') && !adminSidebar.contains(e.target) && e.target !== adminToggleBtn) {
                adminSidebar.classList.remove('is-active');
            }
        });
    }
}

/* ==========================================================================
   ACTIVE LINK HIGHLIGHTING
   ========================================================================== */
function initActiveLinks() {
    const currentPath = window.location.pathname;
    
    // Highlight client nav links
    const clientLinks = document.querySelectorAll('.nav-links a');
    clientLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && href !== '/' && currentPath.includes(href)) {
            link.classList.add('active');
        } else if (href === '/' && currentPath === '/') {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Highlight admin menu links
    const adminLinks = document.querySelectorAll('.admin-menu-item a');
    adminLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath.includes(href)) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

/* ==========================================================================
   TOAST NOTIFICATION SYSTEM
   ========================================================================== */
function showToast(message, type = 'info') {
    // Create container if not exists
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Icon mapping
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'danger') icon = '❌';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 3s
    setTimeout(() => {
        toast.classList.add('toast-fade-out');
        toast.addEventListener('animationend', () => {
            toast.remove();
            if (container.children.length === 0) {
                container.remove();
            }
        });
    }, 3000);
}

/* ==========================================================================
   MODAL UTILITIES
   ========================================================================== */
function initModals() {
    // Setup listeners for modal triggers
    const modalCloses = document.querySelectorAll('.modal-close, [data-modal-close]');
    modalCloses.forEach(close => {
        close.addEventListener('click', () => {
            const modal = close.closest('.modal');
            if (modal) closeModal(modal);
        });
    });

    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        const backdrop = modal.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', () => {
                closeModal(modal);
            });
        }
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden'; // Disable page scrolling
    }
}

function closeModal(modalElement) {
    let modal = modalElement;
    if (typeof modalElement === 'string') {
        modal = document.getElementById(modalElement);
    }
    if (modal) {
        modal.classList.remove('is-open');
        // Check if any other modal is open before enabling scrolling
        const openModals = document.querySelectorAll('.modal.is-open');
        if (openModals.length === 0) {
            document.body.style.overflow = '';
        }
    }
}

// Export functions to global scope
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;

function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })
        .format(amount)
        .replace(/\s?₫/, 'đ');
}
window.formatCurrency = formatCurrency;

/* seedDemoData() lived here: it filled localStorage with four fake
   orders and three promo codes for the old standalone admin pages.
   Orders and coupons are real MongoDB collections now - use
   "python Database/seed_sales.py" to load sample data instead. */

