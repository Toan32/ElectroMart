/* admin-promotions.js - Admin Promotion Codes Management Logic */

const DEFAULT_PROMOTIONS = [
    { code: 'ELECTRO10', type: 'percent', value: 10, minOrder: 10000000, desc: '10% off for orders from 10M VND', active: true },
    { code: 'EM500', type: 'fixed', value: 500000, minOrder: 5000000, desc: '500,000 VND off for orders from 5M VND', active: true },
    { code: 'FREESHIP', type: 'freeship', value: 0, minOrder: 0, desc: 'Free shipping nationwide', active: true }
];

function getPromotions() {
    let promos = localStorage.getItem('electromart_promotions');
    if (!promos || promos === '[]') {
        localStorage.setItem('electromart_promotions', JSON.stringify(DEFAULT_PROMOTIONS));
        return DEFAULT_PROMOTIONS;
    }
    return JSON.parse(promos);
}

document.addEventListener('DOMContentLoaded', () => {
    initAdminPromotions();
});

function initAdminPromotions() {
    const promoListContainer = document.getElementById('adminPromoList');
    if (!promoListContainer) return; // Not on promotions management page

    // Render list
    renderPromotionsList();

    // Form submit listener
    const addPromoForm = document.getElementById('addPromoForm');
    if (addPromoForm) {
        addPromoForm.addEventListener('submit', (e) => {
            e.preventDefault();
            addNewPromotion();
        });
    }

    // Type select listener to toggle value field suffix
    const typeSelect = document.getElementById('promoType');
    const valueSuffix = document.getElementById('promoValueSuffix');
    if (typeSelect && valueSuffix) {
        typeSelect.addEventListener('change', () => {
            if (typeSelect.value === 'percent') {
                valueSuffix.textContent = '%';
            } else if (typeSelect.value === 'fixed') {
                valueSuffix.textContent = 'đ';
            } else {
                valueSuffix.textContent = '-';
            }
        });
    }
}

function renderPromotionsList() {
    const container = document.getElementById('adminPromoList');
    if (!container) return;

    const promotions = getPromotions();

    if (promotions.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: var(--space-xl); color: var(--text-muted);">
                No promo codes created yet!
            </div>
        `;
        return;
    }

    container.innerHTML = promotions.map(promo => {
        let typeText = 'Percentage';
        let valText = `${promo.value}%`;
        
        if (promo.type === 'fixed') {
            typeText = 'Fixed Amount';
            valText = window.formatCurrency ? window.formatCurrency(promo.value) : promo.value + 'đ';
        } else if (promo.type === 'freeship') {
            typeText = 'Free Shipping';
            valText = 'Freeship';
        }

        return `
            <div class="card card-glass promo-card" style="padding:var(--space-md); border-left: 4px solid var(--color-secondary); display:flex; flex-direction:column; justify-content:space-between; height: 100%; background-color: var(--bg-secondary);">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:var(--space-xs);">
                        <strong style="font-family: monospace; font-size:1.15rem; color:var(--color-primary); background-color: var(--color-primary-light); padding:var(--space-2xs) var(--space-xs); border-radius: var(--radius-xs);">${promo.code}</strong>
                        <span class="badge ${promo.active ? 'badge-success' : 'badge-warning'}" style="font-size:0.6rem; text-transform:none;">${promo.active ? 'Active' : 'Inactive'}</span>
                    </div>
                    <p style="font-weight:700; font-size:0.95rem; margin-bottom:2px;">Type: ${typeText}</p>
                    <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:var(--space-2xs);">Value: <strong style="color:var(--color-secondary);">${valText}</strong></p>
                    <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:var(--space-sm);">Min Order: ${window.formatCurrency ? window.formatCurrency(promo.minOrder) : promo.minOrder + 'đ'}</p>
                    <p style="font-size:0.85rem; font-style:italic; color:var(--text-secondary); background:var(--bg-primary); padding:var(--space-2xs); border-radius:var(--radius-xs); border:1px solid var(--border-color);">${promo.desc}</p>
                </div>
                <div style="margin-top:var(--space-md); display:flex; gap:var(--space-xs); justify-content:flex-end;">
                    <button class="btn btn-outline btn-sm" onclick="togglePromoStatus('${promo.code}')" style="font-size:0.75rem; border-color:var(--border-color); color:var(--text-secondary);">${promo.active ? 'Disable' : 'Enable'}</button>
                    <button class="btn btn-danger btn-sm" onclick="deletePromotion('${promo.code}')" style="font-size:0.75rem; padding: 0.25rem 0.5rem;">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

function addNewPromotion() {
    const code = document.getElementById('promoCode').value.trim().toUpperCase();
    const type = document.getElementById('promoType').value;
    const value = parseInt(document.getElementById('promoValue').value) || 0;
    const minOrder = parseInt(document.getElementById('promoMinOrder').value) || 0;
    const desc = document.getElementById('promoDesc').value.trim();

    // Check code duplicate
    let promos = getPromotions();
    if (promos.some(p => p.code === code)) {
        showToast('This promo code already exists!', 'danger');
        return;
    }

    const newPromo = {
        code: code,
        type: type,
        value: type === 'freeship' ? 0 : value,
        minOrder: minOrder,
        desc: desc || `Discount order with code ${code}`,
        active: true
    };

    promos.unshift(newPromo);
    localStorage.setItem('electromart_promotions', JSON.stringify(promos));

    // Clear Form & Close Modal
    document.getElementById('addPromoForm').reset();
    closeModal('addPromoModal');
    
    showToast(`Successfully added promo code "${code}"!`, 'success');
    renderPromotionsList();
}

function togglePromoStatus(code) {
    let promos = getPromotions();
    const idx = promos.findIndex(p => p.code === code);
    if (idx !== -1) {
        promos[idx].active = !promos[idx].active;
        localStorage.setItem('electromart_promotions', JSON.stringify(promos));
        showToast(`Successfully ${promos[idx].active ? 'enabled' : 'disabled'} code "${code}"!`, 'info');
        renderPromotionsList();
    }
}

function deletePromotion(code) {
    if (confirm(`Are you sure you want to delete promo code "${code}"?`)) {
        let promos = getPromotions();
        promos = promos.filter(p => p.code !== code);
        localStorage.setItem('electromart_promotions', JSON.stringify(promos));
        showToast(`Successfully deleted promo code "${code}"!`, 'info');
        renderPromotionsList();
    }
}

// Make functions globally available
window.togglePromoStatus = togglePromoStatus;
window.deletePromotion = deletePromotion;
