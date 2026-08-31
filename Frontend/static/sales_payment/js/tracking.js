/* tracking.js - Client Order Tracking Logic */

document.addEventListener('DOMContentLoaded', () => {
    initTrackingPage();
});

// Mapping of order statuses
const STATUS_MAP = {
    'unpaid': { text: 'Unpaid', class: 'badge-danger', step: 1 },
    'pending': { text: 'Pending', class: 'badge-warning', step: 1 },
    'confirmed': { text: 'Confirmed', class: 'badge-info', step: 2 },
    'shipping': { text: 'Shipping', class: 'badge-primary', step: 3 },
    'completed': { text: 'Completed', class: 'badge-success', step: 4 },
    'cancelled': { text: 'Cancelled', class: 'badge-danger', step: 0 }
};

function initTrackingPage() {
    const searchForm = document.getElementById('trackingSearchForm');
    const orderIdInput = document.getElementById('trackingOrderIdInput');

    if (!searchForm) return;

    // Check if Order ID is passed in URL query params (e.g., tracking.html?orderId=EM-123456)
    const urlParams = new URLSearchParams(window.location.search);
    const orderIdParam = urlParams.get('orderId');

    if (orderIdParam) {
        orderIdInput.value = orderIdParam.trim();
        trackOrder(orderIdParam.trim());
    }

    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const orderId = orderIdInput.value.trim();
        if (orderId) {
            trackOrder(orderId);
        } else {
            showToast('Please enter an order ID!', 'warning');
        }
    });
}

function trackOrder(orderId) {
    const resultsContainer = document.getElementById('trackingResults');
    if (!resultsContainer) return;

    // Load orders list
    const allOrders = JSON.parse(localStorage.getItem('electromart_orders')) || [];
    const order = allOrders.find(o => o.orderId.toLowerCase() === orderId.toLowerCase());

    if (!order) {
        resultsContainer.innerHTML = `
            <div class="card" style="padding: var(--space-2xl); text-align: center;">
                <span style="font-size: 3rem;">🔎</span>
                <h4 style="margin-top: var(--space-md); margin-bottom: var(--space-xs);">Order not found!</h4>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">Please verify your order ID (e.g. EM-123456) or contact support.</p>
            </div>
        `;
        return;
    }

    // Determine active steps
    const statusInfo = STATUS_MAP[order.status] || { text: 'Unknown', class: 'badge-info', step: 1 };
    const currentStep = statusInfo.step;

    // Build timeline HTML
    let timelineHTML = '';
    if (order.status === 'cancelled') {
        timelineHTML = `
            <div style="background-color: var(--color-danger-light); color: var(--color-danger); padding: var(--space-md); border-radius: var(--radius-md); text-align: center; font-weight: 600; margin-bottom: var(--space-xl);">
                This order has been cancelled.
            </div>
        `;
    } else {
        timelineHTML = `
            <div class="timeline-container" style="display: flex; justify-content: space-between; align-items: center; position: relative; margin: var(--space-xl) 0 var(--space-2xl) 0; padding: 0 var(--space-md);">
                <!-- Progress Line Behind -->
                <div style="position: absolute; top: 15px; left: 8%; right: 8%; height: 4px; background-color: var(--border-color); z-index: 1;">
                    <div style="height: 100%; width: ${((currentStep - 1) / 3) * 100}%; background-color: var(--color-primary); transition: width var(--transition-slow);"></div>
                </div>

                <!-- Step 1 -->
                <div class="timeline-step" style="text-align: center; position: relative; z-index: 2; flex: 1;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background-color: ${currentStep >= 1 ? 'var(--color-primary)' : 'var(--bg-secondary)'}; border: 3px solid ${currentStep >= 1 ? 'var(--color-primary)' : 'var(--border-color)'}; color: ${currentStep >= 1 ? '#ffffff' : 'var(--text-muted)'}; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-weight: 700; font-size:0.85rem;">
                        ${currentStep >= 1 ? '✓' : '1'}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: ${currentStep >= 1 ? 'var(--text-primary)' : 'var(--text-muted)'};">Ordered</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${order.date.split(' ')[0]}</div>
                </div>

                <!-- Step 2 -->
                <div class="timeline-step" style="text-align: center; position: relative; z-index: 2; flex: 1;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background-color: ${currentStep >= 2 ? 'var(--color-primary)' : 'var(--bg-secondary)'}; border: 3px solid ${currentStep >= 2 ? 'var(--color-primary)' : 'var(--border-color)'}; color: ${currentStep >= 2 ? '#ffffff' : 'var(--text-muted)'}; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-weight: 700; font-size:0.85rem;">
                        ${currentStep >= 2 ? '✓' : '2'}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: ${currentStep >= 2 ? 'var(--text-primary)' : 'var(--text-muted)'};">Confirmed</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${currentStep >= 2 ? 'Approved' : 'Processing'}</div>
                </div>

                <!-- Step 3 -->
                <div class="timeline-step" style="text-align: center; position: relative; z-index: 2; flex: 1;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background-color: ${currentStep >= 3 ? 'var(--color-primary)' : 'var(--bg-secondary)'}; border: 3px solid ${currentStep >= 3 ? 'var(--color-primary)' : 'var(--border-color)'}; color: ${currentStep >= 3 ? '#ffffff' : 'var(--text-muted)'}; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-weight: 700; font-size:0.85rem;">
                        ${currentStep >= 3 ? '✓' : '3'}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: ${currentStep >= 3 ? 'var(--text-primary)' : 'var(--text-muted)'};">Shipping</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${currentStep >= 3 ? 'In Transit' : 'Packaging'}</div>
                </div>

                <!-- Step 4 -->
                <div class="timeline-step" style="text-align: center; position: relative; z-index: 2; flex: 1;">
                    <div style="width: 32px; height: 32px; border-radius: 50%; background-color: ${currentStep >= 4 ? 'var(--color-success)' : 'var(--bg-secondary)'}; border: 3px solid ${currentStep >= 4 ? 'var(--color-success)' : 'var(--border-color)'}; color: ${currentStep >= 4 ? '#ffffff' : 'var(--text-muted)'}; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-weight: 700; font-size:0.85rem;">
                        ${currentStep >= 4 ? '✓' : '4'}
                    </div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: ${currentStep >= 4 ? 'var(--color-success)' : 'var(--text-muted)'};">Delivered</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${currentStep >= 4 ? 'Completed' : 'Shipping'}</div>
                </div>
            </div>
        `;
    }

    // Build items detail list
    const itemsDetailHTML = order.items.map(item => `
        <div style="display:flex; align-items:center; gap:var(--space-md); padding:var(--space-sm) 0; border-bottom: 1px solid var(--border-color);">
            <img src="${item.image}" alt="${item.name}" style="width:50px; height:50px; object-fit:contain; background:#ffffff; padding:2px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
            <div style="flex-grow:1;">
                <h5 style="font-size:0.9rem; font-weight:600; margin-bottom: 2px;">${item.name}</h5>
                <p style="font-size:0.75rem; color:var(--text-secondary);">${item.specs}</p>
            </div>
            <div style="font-size:0.85rem; color:var(--text-secondary);">${formatCurrency(item.price)} x ${item.quantity}</div>
            <div style="font-weight:700; font-size:0.9rem; min-width:90px; text-align:right;">${formatCurrency(item.price * item.quantity)}</div>
        </div>
    `).join('');

    resultsContainer.innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:var(--space-xl); align-items: start;">
            <!-- Left Panel: Status timeline & actions -->
            <div class="card" style="padding:var(--space-lg); grid-column: span 2; background-color: var(--bg-secondary);">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid var(--border-color); padding-bottom:var(--space-sm); margin-bottom:var(--space-md);">
                    <h3 style="font-size:1.15rem; font-weight:700;">Order Status <code style="font-size:1rem; color:var(--color-primary); font-family:monospace; margin-left:var(--space-xs);">${order.orderId}</code></h3>
                    <span class="badge ${statusInfo.class}" style="font-size:0.8rem;">${statusInfo.text}</span>
                </div>
                
                ${timelineHTML}
            </div>

            <!-- Left Details -->
            <div class="card" style="padding:var(--space-lg); background-color: var(--bg-secondary);">
                <h4 style="font-size:1rem; font-weight:700; margin-bottom:var(--space-md); border-bottom:1px solid var(--border-color); padding-bottom:var(--space-xs);">Order Details</h4>
                <div style="max-height: 250px; overflow-y:auto; padding-right:var(--space-xs);">
                    ${itemsDetailHTML}
                </div>
                
                <div style="margin-top:var(--space-md); display:flex; flex-direction:column; gap:var(--space-xs); font-size:0.9rem;">
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
                    <div style="display:flex; justify-content:space-between; padding-top:var(--space-xs); border-top: 1px solid var(--border-color); font-weight:700; font-size:1.05rem;">
                        <span>Total Payment:</span>
                        <span style="color:var(--color-primary);">${formatCurrency(order.total)}</span>
                    </div>
                </div>
            </div>

            <!-- Right: Shipping/Customer Info -->
            <div class="card" style="padding:var(--space-lg); background-color: var(--bg-secondary);">
                <h4 style="font-size:1rem; font-weight:700; margin-bottom:var(--space-md); border-bottom:1px solid var(--border-color); padding-bottom:var(--space-xs);">Delivery Information</h4>
                <div style="display:flex; flex-direction:column; gap:var(--space-sm); font-size:0.9rem;">
                    <div>
                        <div style="font-weight:600; color:var(--text-secondary); font-size:0.8rem; margin-bottom:2px;">RECIPIENT</div>
                        <div>${order.customerName}</div>
                    </div>
                    <div>
                        <div style="font-weight:600; color:var(--text-secondary); font-size:0.8rem; margin-bottom:2px;">PHONE NUMBER</div>
                        <div>${order.phone}</div>
                    </div>
                    <div>
                        <div style="font-weight:600; color:var(--text-secondary); font-size:0.8rem; margin-bottom:2px;">EMAIL</div>
                        <div>${order.email}</div>
                    </div>
                    <div>
                        <div style="font-weight:600; color:var(--text-secondary); font-size:0.8rem; margin-bottom:2px;">SHIPPING ADDRESS</div>
                        <div>${order.address}</div>
                    </div>
                    <div>
                        <div style="font-weight:600; color:var(--text-secondary); font-size:0.8rem; margin-bottom:2px;">PAYMENT METHOD</div>
                        <div>${order.paymentMethod === 'cod' ? 'Cash on Delivery (COD)' : 'Bank Transfer (VietQR)'}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
