/* dashboard.js - Admin Dashboard Analytics and Metrics */

document.addEventListener('DOMContentLoaded', () => {
    renderDashboardStats();
    initDashboardCharts();
});

function renderDashboardStats() {
    const orders = window.getOrders ? window.getOrders() : [];

    const totalRevenueEl = document.getElementById('dashTotalRevenue');
    const totalOrdersEl = document.getElementById('dashTotalOrders');
    const avgOrderValEl = document.getElementById('dashAvgOrderValue');
    const activePromosEl = document.getElementById('dashActivePromotions');
    const recentOrdersTable = document.getElementById('dashRecentOrdersTable');

    if (!totalRevenueEl) return; // Not on dashboard page

    // 1. Calculate KPI Metrics
    // Revenue is calculated from all orders except "cancelled" and "unpaid"
    const completedRevenueOrders = orders.filter(o => o.status !== 'cancelled' && o.status !== 'unpaid');
    const totalRevenue = completedRevenueOrders.reduce((sum, o) => sum + o.total, 0);
    
    const activeOrdersCount = orders.filter(o => o.status !== 'cancelled').length;
    const avgOrderValue = activeOrdersCount > 0 ? (totalRevenue / activeOrdersCount) : 0;

    // Load promotions count
    const promotions = JSON.parse(localStorage.getItem('electromart_promotions')) || [];
    const activePromosCount = promotions.length > 0 ? promotions.length : 3; // default mock count

    // Write to DOM
    totalRevenueEl.textContent = window.formatCurrency ? window.formatCurrency(totalRevenue) : totalRevenue + 'đ';
    totalOrdersEl.textContent = orders.length;
    avgOrderValEl.textContent = window.formatCurrency ? window.formatCurrency(avgOrderValue) : avgOrderValue + 'đ';
    activePromosEl.textContent = activePromosCount;

    // 2. Render Recent Orders (limit to 5)
    const recentOrders = orders.slice(0, 5);
    
    if (recentOrders.length === 0) {
        recentOrdersTable.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: var(--space-md); color: var(--text-muted);">
                    No orders recorded yet.
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

    recentOrdersTable.innerHTML = recentOrders.map(order => {
        const st = statusClasses[order.status] || { text: 'Unknown', badge: 'badge-info' };
        return `
            <tr>
                <td><strong style="font-family: monospace; font-size:0.85rem;">${order.orderId}</strong></td>
                <td style="font-weight:600; font-size:0.85rem;">${order.customerName}</td>
                <td style="font-size:0.85rem; color: var(--text-secondary);">${order.date.split(' ')[0]}</td>
                <td style="font-weight: 700; font-size:0.85rem;">${window.formatCurrency ? window.formatCurrency(order.total) : order.total + 'đ'}</td>
                <td><span style="font-size:0.65rem; text-transform:none;" class="badge ${st.badge}">${st.text}</span></td>
            </tr>
        `;
    }).join('');
}

// Draw charts using Chart.js
function initDashboardCharts() {
    const revenueCtx = document.getElementById('revenueChartCanvas');
    const categoryCtx = document.getElementById('categoryChartCanvas');

    if (!revenueCtx || !categoryCtx) return;

    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js was not loaded via CDN.');
        return;
    }

    // Modern themes styling configurations
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? '#374151' : '#e2e8f0';
    const textColor = isDark ? '#d1d5db' : '#475569';

    // Chart 1: Revenue Line Chart (Mock 7-day trend based on current revenue)
    const revenueChart = new Chart(revenueCtx, {
        type: 'line',
        data: {
            labels: ['14/08', '15/08', '16/08', '17/08', '18/08', '19/08', '20/08'],
            datasets: [{
                label: 'Daily Revenue (VND)',
                data: [12000000, 24500000, 18200000, 21540000, 29990000, 43546000, 52000000],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#6366f1',
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: { 
                        color: textColor, 
                        font: { family: 'Outfit' },
                        callback: function(value) {
                            return (value / 1000000) + 'M';
                        }
                    }
                }
            }
        }
    });

    // Chart 2: Category distribution Donut Chart
    const categoryChart = new Chart(categoryCtx, {
        type: 'doughnut',
        data: {
            labels: ['Laptops', 'Phones', 'Accessories', 'Tablets'],
            datasets: [{
                data: [45, 35, 12, 8],
                backgroundColor: ['#6366f1', '#a855f7', '#10b981', '#0ea5e9'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textColor,
                        font: { family: 'Outfit', size: 11 },
                        padding: 15
                    }
                }
            },
            cutout: '70%'
        }
    });

    // Watch for Theme changes to update chart text colors
    const observer = new MutationObserver(() => {
        const isDarkNow = document.documentElement.getAttribute('data-theme') === 'dark';
        const newGridColor = isDarkNow ? '#374151' : '#e2e8f0';
        const newTextColor = isDarkNow ? '#d1d5db' : '#475569';

        revenueChart.options.scales.x.grid.color = newGridColor;
        revenueChart.options.scales.x.ticks.color = newTextColor;
        revenueChart.options.scales.y.grid.color = newGridColor;
        revenueChart.options.scales.y.ticks.color = newTextColor;
        revenueChart.update();

        categoryChart.options.plugins.legend.labels.color = newTextColor;
        categoryChart.update();
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
}

// Export render function to global scope
window.renderDashboardStats = renderDashboardStats;
