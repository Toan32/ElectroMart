/* shared.js - Global JavaScript utilities for ElectroMart */

document.addEventListener('DOMContentLoaded', () => {
    // Clean up old Vietnamese mock data in localStorage to load English versions
    const promos = localStorage.getItem('electromart_promotions');
    if (promos && promos.includes('Giảm')) {
        localStorage.removeItem('electromart_promotions');
        localStorage.removeItem('electromart_discount');
    }
    const orders = localStorage.getItem('electromart_orders');
    if (orders && (orders.includes('Chờ') || orders.includes('Đã'))) {
        localStorage.removeItem('electromart_orders');
    }


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

function seedDemoData() {
    const demoPromos = [
        { code: 'ELECTRO10', type: 'percent', value: 10, minOrder: 10000000, desc: '10% off for orders from 10M VND', active: true },
        { code: 'EM500', type: 'fixed', value: 500000, minOrder: 5000000, desc: '500,000 VND off for orders from 5M VND', active: true },
        { code: 'FREESHIP', type: 'freeship', value: 0, minOrder: 0, desc: 'Free shipping nationwide', active: true }
    ];
    const demoOrders = [
        {
            orderId: 'EM-582941',
            customerName: 'Minh Hoang Pham',
            phone: '0912345678',
            email: 'hoang.pm@gmail.com',
            address: '45 Le Loi Street, Ben Nghe Ward, District 1, Ho Chi Minh City',
            date: new Date(Date.now() - 2 * 3600 * 1000).toLocaleString('en-US'),
            items: [
                { id: 'prod-06', name: 'ASUS ROG Zephyrus G14', price: 36990000, quantity: 1, image: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=400&q=80', specs: 'Ryzen 7 / 16GB / 512GB' },
                { id: 'prod-08', name: 'Keychron K8 Pro Mechanical Keyboard', price: 2450000, quantity: 1, image: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=400&q=80', specs: 'Brown Switch / RGB' }
            ],
            subtotal: 39440000,
            discount: 3944000,
            shippingFee: 30000,
            total: 35526000,
            paymentMethod: 'cod',
            status: 'pending'
        },
        {
            orderId: 'EM-817294',
            customerName: 'Khanh Linh Tran',
            phone: '0983214567',
            email: 'linh.ttk@yahoo.com',
            address: 'Apartment 1205, Sunrise City Apartment, District 7, Ho Chi Minh City',
            date: new Date(Date.now() - 24 * 3600 * 1000).toLocaleString('en-US'),
            items: [
                { id: 'prod-02', name: 'iPhone 15 Pro Max', price: 29990000, quantity: 1, image: 'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=400&q=80', specs: '256GB / Natural Titanium' }
            ],
            subtotal: 29990000,
            discount: 0,
            shippingFee: 0,
            total: 29990000,
            paymentMethod: 'transfer',
            status: 'completed'
        },
        {
            orderId: 'EM-124950',
            customerName: 'Hai Long Nguyen',
            phone: '0977665544',
            email: 'longnh@outlook.com',
            address: 'No. 12, Lane 82 Lang Road, Dong Da District, Hanoi',
            date: new Date(Date.now() - 12 * 3600 * 1000).toLocaleString('en-US'),
            items: [
                { id: 'prod-03', name: 'Sony WH-1000XM5', price: 7990000, quantity: 1, image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=400&q=80', specs: 'ANC Noise Cancelling / Black' }
            ],
            subtotal: 7990000,
            discount: 0,
            shippingFee: 30000,
            total: 8020000,
            paymentMethod: 'transfer',
            status: 'shipping'
        },
        {
            orderId: 'EM-904128',
            customerName: 'Hoang Yen Le',
            phone: '0909887766',
            email: 'yenlh@gmail.com',
            address: '246 Nguyen Chi Thanh Street, District 5, Ho Chi Minh City',
            date: new Date(Date.now() - 3 * 24 * 3600 * 1000).toLocaleString('en-US'),
            items: [
                { id: 'prod-04', name: 'iPad Pro 11" M2', price: 21990000, quantity: 1, image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=400&q=80', specs: 'Wi-Fi 128GB / Space Gray' }
            ],
            subtotal: 21990000,
            discount: 500000,
            shippingFee: 50000,
            total: 21540000,
            paymentMethod: 'cod',
            status: 'cancelled'
        }
    ];

    localStorage.setItem('electromart_promotions', JSON.stringify(demoPromos));
    localStorage.setItem('electromart_orders', JSON.stringify(demoOrders));
    showToast('Demo data seeded successfully! Reloading...', 'success');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}
window.seedDemoData = seedDemoData;

