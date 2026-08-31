const formatCurrency = window.formatCurrency;

// Mock initial orders data for dashboard visual completeness
const MOCK_ORDERS = [
    {
        orderId: 'EM-582941',
        customerName: 'Minh Hoang Pham',
        phone: '0912345678',
        email: 'hoang.pm@gmail.com',
        address: '45 Le Loi Street, Ben Nghe Ward, District 1, Ho Chi Minh City',
        date: '19/08/2026 14:32:10',
        items: [
            { id: 'prod-06', name: 'ASUS ROG Zephyrus G14', price: 36990000, quantity: 1, image: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=400&q=80', specs: 'Ryzen 7 / 16GB / 512GB' },
            { id: 'prod-08', name: 'Keychron K8 Pro Mechanical Keyboard', price: 2450000, quantity: 1, image: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=400&q=80', specs: 'Brown Switch / RGB' }
        ],
        subtotal: 39440000,
        discount: 3944000, // 10% off by coupon
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
        date: '18/08/2026 09:15:45',
        items: [
            { id: 'prod-02', name: 'iPhone 15 Pro Max', price: 29990000, quantity: 1, image: 'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=400&q=80', specs: '256GB / Natural Titanium' }
        ],
        subtotal: 29990000,
        discount: 0,
        shippingFee: 0, // Free shipping
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
        date: '19/08/2026 18:20:00',
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
        date: '17/08/2026 11:05:12',
        items: [
            { id: 'prod-04', name: 'iPad Pro 11" M2', price: 21990000, quantity: 1, image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=400&q=80', specs: 'Wi-Fi 128GB / Space Gray' }
        ],
        subtotal: 21990000,
        discount: 500000, // 500k coupon
        shippingFee: 50000,
        total: 21540000,
        paymentMethod: 'cod',
        status: 'cancelled'
    }
];

// Load orders from localStorage or set defaults
function getOrders() {
    let orders = localStorage.getItem('electromart_orders');
    if (!orders || orders === '[]') {
        localStorage.setItem('electromart_orders', JSON.stringify(MOCK_ORDERS));
        return MOCK_ORDERS;
    }
    return JSON.parse(orders);
}

// Active Filter and Query states
let currentStatusFilter = 'all';
let currentSearchQuery = '';

document.addEventListener('DOMContentLoaded', () => {
    initAdminOrders();
});

function initAdminOrders() {
    const ordersTableBody = document.getElementById('adminOrdersTableBody');
    if (!ordersTableBody) return; // Not on admin-orders page

    // Populate table
    renderOrdersTable();

    // Setup filter links
    const filterTabs = document.querySelectorAll('.admin-filter-tab');
    filterTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            currentStatusFilter = tab.getAttribute('data-status');
            renderOrdersTable();
        });
    });

    // Setup search input
    const searchInput = document.getElementById('adminOrderSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearchQuery = e.target.value.toLowerCase().trim();
            renderOrdersTable();
        });
    }
}

// Render the orders list in table
function renderOrdersTable() {
    const tableBody = document.getElementById('adminOrdersTableBody');
    if (!tableBody) return;

    const orders = getOrders();
    
    // Filter
    let filtered = orders;
    if (currentStatusFilter !== 'all') {
        filtered = filtered.filter(o => o.status === currentStatusFilter);
    }
    if (currentSearchQuery) {
        filtered = filtered.filter(o => 
            o.orderId.toLowerCase().includes(currentSearchQuery) || 
            o.customerName.toLowerCase().includes(currentSearchQuery) ||
            o.phone.includes(currentSearchQuery)
        );
    }

    if (filtered.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: var(--space-xl); color: var(--text-muted);">
                    No orders found!
                </td>
            </tr>
        `;
        return;
    }

    const statusClasses = {
        'unpaid': { text: 'Unpaid', badge: 'badge-danger' },
        'pending': { text: 'Pending', badge: 'badge-warning' },
        'confirmed': { text: 'Confirmed', badge: 'badge-info' },
        'shipping': { text: 'Shipping', badge: 'badge-primary' },
        'completed': { text: 'Completed', badge: 'badge-success' },
        'cancelled': { text: 'Cancelled', badge: 'badge-danger' }
    };

    tableBody.innerHTML = filtered.map(order => {
        const st = statusClasses[order.status] || { text: 'Unknown', badge: 'badge-info' };
        return `
            <tr>
                <td><strong style="font-family: monospace; font-size:0.95rem;">${order.orderId}</strong></td>
                <td>
                    <div style="font-weight:600;">${order.customerName}</div>
                    <div style="font-size:0.75rem; color:var(--text-secondary);">${order.phone}</div>
                </td>
                <td style="font-size: 0.85rem; color: var(--text-secondary);">${order.date.split(' ')[0]}</td>
                <td style="font-weight: 700; color:var(--color-primary);">${formatCurrency(order.total)}</td>
                <td><span style="font-size:0.7rem; text-transform:none;" class="badge ${st.badge}">${st.text}</span></td>
                <td><span style="font-size:0.85rem;">${order.paymentMethod === 'cod' ? 'COD' : 'VietQR'}</span></td>
                <td>
                    <div style="display:flex; gap:var(--space-2xs);">
                        <button class="btn btn-secondary btn-sm" onclick="showOrderDetailAdmin('${order.orderId}')">Details</button>
                        <button class="btn btn-primary btn-sm" onclick="showStatusEditAdmin('${order.orderId}')" style="background-color: var(--color-secondary);">Update</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Show Order Detail Modal (Admin side)
function showOrderDetailAdmin(orderId) {
    const orders = getOrders();
    const order = orders.find(o => o.orderId === orderId);
    if (!order) return;

    const modalBody = document.getElementById('adminDetailModalBody');
    if (!modalBody) return;

    const statusTexts = {
        'unpaid': 'Unpaid',
        'pending': 'Pending',
        'confirmed': 'Confirmed',
        'shipping': 'Shipping',
        'completed': 'Completed',
        'cancelled': 'Cancelled'
    };

    const itemsHTML = order.items.map(item => `
        <div style="display:flex; align-items:center; gap:var(--space-sm); padding:var(--space-2xs) 0; border-bottom: 1px solid var(--border-color);">
            <img src="${item.image}" alt="${item.name}" style="width:40px; height:40px; object-fit:contain; background:#ffffff; padding:2px; border-radius:var(--radius-xs); border:1px solid var(--border-color);">
            <div style="flex-grow:1;">
                <div style="font-weight:600; font-size:0.85rem;">${item.name}</div>
                <div style="font-size:0.75rem; color:var(--text-secondary);">${item.specs}</div>
            </div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">${formatCurrency(item.price)} x ${item.quantity}</div>
            <div style="font-weight:600; font-size:0.85rem; min-width:80px; text-align:right;">${formatCurrency(item.price * item.quantity)}</div>
        </div>
    `).join('');

    modalBody.innerHTML = `
        <div style="display:grid; grid-template-columns: 1.2fr 1fr; gap:var(--space-lg); font-size:0.9rem;">
            <!-- Customer & Delivery -->
            <div>
                <h4 style="font-weight:700; margin-bottom:var(--space-xs); border-bottom:1px solid var(--border-color); padding-bottom:var(--space-3xs);">Customer Information</h4>
                <p style="margin-bottom:var(--space-3xs);"><strong>Customer:</strong> ${order.customerName}</p>
                <p style="margin-bottom:var(--space-3xs);"><strong>Phone:</strong> ${order.phone}</p>
                <p style="margin-bottom:var(--space-3xs);"><strong>Email:</strong> ${order.email}</p>
                <p style="margin-bottom:var(--space-3xs);"><strong>Shipping Address:</strong> ${order.address}</p>
                <p style="margin-bottom:var(--space-3xs);"><strong>Order Date:</strong> ${order.date}</p>
                <p style="margin-bottom:var(--space-3xs);"><strong>Payment Method:</strong> ${order.paymentMethod === 'cod' ? 'Cash on Delivery (COD)' : 'Bank Transfer (VietQR)'}</p>
                <p style="margin-bottom:0;"><strong>Status:</strong> <strong style="color:var(--color-primary);">${statusTexts[order.status] || order.status}</strong></p>
            </div>

            <!-- Items Cost -->
            <div>
                <h4 style="font-weight:700; margin-bottom:var(--space-xs); border-bottom:1px solid var(--border-color); padding-bottom:var(--space-3xs);">Purchased Products</h4>
                <div style="max-height:160px; overflow-y:auto; padding-right:var(--space-3xs); margin-bottom:var(--space-sm);">
                    ${itemsHTML}
                </div>
                <div style="display:flex; flex-direction:column; gap:var(--space-2xs); font-size:0.85rem;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:var(--text-secondary);">Subtotal:</span>
                        <span>${formatCurrency(order.subtotal)}</span>
                    </div>
                    ${order.discount > 0 ? `
                    <div style="display:flex; justify-content:space-between; color:var(--color-success);">
                        <span>Discount:</span>
                        <span>-${formatCurrency(order.discount)}</span>
                    </div>
                    ` : ''}
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:var(--text-secondary);">Shipping Fee:</span>
                        <span>${formatCurrency(order.shippingFee)}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-weight:700; font-size:0.95rem; border-top:1px solid var(--border-color); padding-top:var(--space-2xs);">
                        <span>Total Revenue:</span>
                        <span style="color:var(--color-primary);">${formatCurrency(order.total)}</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    openModal('adminDetailModal');
}

// Show Status Update Edit Modal
function showStatusEditAdmin(orderId) {
    const orders = getOrders();
    const order = orders.find(o => o.orderId === orderId);
    if (!order) return;

    const modalBody = document.getElementById('adminStatusModalBody');
    if (!modalBody) return;

    modalBody.innerHTML = `
        <div style="font-size:0.9rem;">
            <p style="margin-bottom:var(--space-sm);">Update processing status for order <strong style="color:var(--color-primary); font-family:monospace;">${order.orderId}</strong> of customer <strong>${order.customerName}</strong>.</p>
            
            <div class="form-group">
                <label class="form-label" for="adminStatusSelect">New Status</label>
                <select class="form-select" id="adminStatusSelect">
                    <option value="unpaid" ${order.status === 'unpaid' ? 'selected' : ''}>Unpaid (Bank Transfer)</option>
                    <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Pending Approval (COD)</option>
                    <option value="confirmed" ${order.status === 'confirmed' ? 'selected' : ''}>Confirmed & Preparing Package</option>
                    <option value="shipping" ${order.status === 'shipping' ? 'selected' : ''}>Shipping</option>
                    <option value="completed" ${order.status === 'completed' ? 'selected' : ''}>Completed (Delivered)</option>
                    <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                </select>
            </div>
            
            <input type="hidden" id="adminStatusOrderId" value="${order.orderId}">
        </div>
    `;

    openModal('adminStatusModal');
}

// Save Order Status Update
function saveOrderStatusAdmin() {
    const orderId = document.getElementById('adminStatusOrderId').value;
    const newStatus = document.getElementById('adminStatusSelect').value;

    let orders = getOrders();
    const idx = orders.findIndex(o => o.orderId === orderId);
    if (idx !== -1) {
        orders[idx].status = newStatus;
        localStorage.setItem('electromart_orders', JSON.stringify(orders));
        
        closeModal('adminStatusModal');
        showToast(`Successfully updated order ${orderId} status!`, 'success');
        
        // Refresh tables/views
        renderOrdersTable();
        
        // If on admin-dashboard, refresh dashboard stats
        if (typeof renderDashboardStats === 'function') {
            renderDashboardStats();
        }
    }
}

// Make functions globally available
window.showOrderDetailAdmin = showOrderDetailAdmin;
window.showStatusEditAdmin = showStatusEditAdmin;
window.saveOrderStatusAdmin = saveOrderStatusAdmin;
window.getOrders = getOrders;
