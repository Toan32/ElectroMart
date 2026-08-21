/* cart.js - Shopping Cart State and Operations for ElectroMart */

// Define products dataset for easy mockups
const PRODUCTS = [
    { id: 'prod-01', name: 'MacBook Pro 14" M3 Pro', price: 54990000, category: 'laptop', image: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=400&q=80', specs: '18GB RAM / 512GB SSD / Space Black' },
    { id: 'prod-02', name: 'iPhone 15 Pro Max', price: 29990000, category: 'phone', image: 'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=400&q=80', specs: '256GB / Natural Titanium' },
    { id: 'prod-03', name: 'Sony WH-1000XM5', price: 7990000, category: 'accessory', image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=400&q=80', specs: 'ANC Noise Cancelling / Black' },
    { id: 'prod-04', name: 'iPad Pro 11" M2', price: 21990000, category: 'tablet', image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=400&q=80', specs: 'Wi-Fi 128GB / Space Gray' },
    { id: 'prod-05', name: 'Samsung Galaxy S24 Ultra', price: 26990000, category: 'phone', image: 'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=400&q=80', specs: '256GB / Titanium Gray' },
    { id: 'prod-06', name: 'ASUS ROG Zephyrus G14', price: 36990000, category: 'laptop', image: 'https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=400&q=80', specs: 'Ryzen 7 / 16GB / 512GB / RTX 4050' },
    { id: 'prod-07', name: 'Apple Watch Ultra 2', price: 21490000, category: 'accessory', image: 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=400&q=80', specs: 'GPS + Cellular / Ocean Band' },
    { id: 'prod-08', name: 'Keychron K8 Pro Mechanical Keyboard', price: 2450000, category: 'accessory', image: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=400&q=80', specs: 'Brown Switch / RGB / Bluetooth' }
];

// Mock promotion codes list
const PROMO_CODES = {
    'ELECTRO10': { type: 'percent', value: 10, minOrder: 10000000, desc: '10% off for orders from 10 million VND' },
    'EM500': { type: 'fixed', value: 500000, minOrder: 5000000, desc: '500,000 VND off for orders from 5 million VND' },
    'FREESHIP': { type: 'freeship', value: 0, minOrder: 0, desc: 'Free shipping nationwide' }
};

// Initialize Cart State
let cart = JSON.parse(localStorage.getItem('electromart_cart')) || [];
let activeDiscount = JSON.parse(localStorage.getItem('electromart_discount')) || null;

// Currency Formatter
function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
}

// Get Cart items
function getCart() {
    return cart;
}

// Get Total Items count (Sum of quantities)
function getCartCount() {
    return cart.reduce((total, item) => total + item.quantity, 0);
}

// Update Header Cart Badge
function updateCartBadge() {
    // Dynamically integrate with team's base.html navbar if it exists
    const cartLink = Array.from(document.querySelectorAll('.hact')).find(el => el.textContent.includes('Cart'));
    if (cartLink) {
        // Set href for testing if it's currently empty/hash
        if (cartLink.getAttribute('href') === '#' || !cartLink.getAttribute('href')) {
            cartLink.setAttribute('href', '/cart/');
        }
        
        let badge = cartLink.querySelector('#cartBadgeCount');
        if (!badge) {
            badge = document.createElement('b');
            badge.className = 'badge';
            badge.id = 'cartBadgeCount';
            cartLink.appendChild(badge);
        }
    }

    const badge = document.getElementById('cartBadgeCount');
    if (badge) {
        const count = getCartCount();
        badge.textContent = count;
        if (count > 0) {
            badge.classList.remove('hide');
            badge.style.display = 'flex';
        } else {
            badge.classList.add('hide');
            badge.style.display = 'none';
        }
    }
}

// Save cart to local storage and update UI
function saveCart() {
    localStorage.setItem('electromart_cart', JSON.stringify(cart));
    updateCartBadge();
}

// Add Item to Cart
function addToCart(productId) {
    const product = PRODUCTS.find(p => p.id === productId);
    if (!product) return;

    const existingItem = cart.find(item => item.id === productId);

    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            specs: product.specs,
            quantity: 1
        });
    }

    saveCart();
    showToast(`Added "${product.name}" to cart`, 'success');
}

// Update Item Quantity
function updateQuantity(productId, newQty) {
    newQty = parseInt(newQty);
    if (isNaN(newQty) || newQty < 1) return;
    
    const item = cart.find(item => item.id === productId);
    if (item) {
        item.quantity = newQty;
        saveCart();
        renderCartPage(); // Rerender if on cart page
    }
}

// Remove Item from Cart
function removeFromCart(productId) {
    const item = cart.find(item => item.id === productId);
    if (item) {
        cart = cart.filter(item => item.id !== productId);
        saveCart();
        showToast(`Removed "${item.name}" from cart`, 'info');
        renderCartPage(); // Rerender if on cart page
    }
}

// Clear Cart completely
function clearCart() {
    cart = [];
    activeDiscount = null;
    localStorage.removeItem('electromart_cart');
    localStorage.removeItem('electromart_discount');
    updateCartBadge();
}

// Get Subtotal
function getSubtotal() {
    return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
}

// Apply Promo Code
function applyPromoCode(code) {
    code = code.trim().toUpperCase();
    
    if (cart.length === 0) {
        showToast('Cart is empty, cannot apply promo code!', 'warning');
        return false;
    }

    const discountInfo = PROMO_CODES[code];
    if (!discountInfo) {
        showToast('Invalid promo code!', 'danger');
        return false;
    }

    const subtotal = getSubtotal();
    if (subtotal < discountInfo.minOrder) {
        showToast(`This code only applies to orders from ${formatCurrency(discountInfo.minOrder)}`, 'warning');
        return false;
    }

    // Calculate discount amount
    let amount = 0;
    if (discountInfo.type === 'percent') {
        amount = subtotal * (discountInfo.value / 100);
    } else if (discountInfo.type === 'fixed') {
        amount = discountInfo.value;
    } else if (discountInfo.type === 'freeship') {
        amount = 0; // Handled as shipping discount in checkout
    }

    activeDiscount = {
        code: code,
        type: discountInfo.type,
        value: discountInfo.value,
        amount: amount,
        desc: discountInfo.desc
    };

    localStorage.setItem('electromart_discount', JSON.stringify(activeDiscount));
    showToast(`Promo code "${code}" applied successfully!`, 'success');
    renderCartPage(); // Rerender if on cart page
    return true;
}

// Remove active promo code
function removePromoCode() {
    activeDiscount = null;
    localStorage.removeItem('electromart_discount');
    showToast('Promo code removed', 'info');
    renderCartPage();
}

// Render Cart Page DOM (if on cart.html)
function renderCartPage() {
    const cartContainer = document.getElementById('cartItemsList');
    if (!cartContainer) return; // Not on cart page

    const subtotalEl = document.getElementById('cartSubtotal');
    const discountRowEl = document.getElementById('discountRow');
    const discountValEl = document.getElementById('cartDiscount');
    const totalEl = document.getElementById('cartTotal');
    const checkoutBtn = document.getElementById('checkoutBtn');

    if (cart.length === 0) {
        cartContainer.innerHTML = `
            <div style="text-align: center; padding: var(--space-2xl) 0;">
                <span style="font-size: 4rem;">ðŸ›’</span>
                <h3 style="margin-top: var(--space-md); margin-bottom: var(--space-sm);">Your shopping cart is empty!</h3>
                <p style="color: var(--text-secondary); margin-bottom: var(--space-lg);">Add some awesome tech products to your cart.</p>
                <a href="/" class="btn btn-primary">Shop Now</a>
            </div>
        `;
        subtotalEl.textContent = '0Ä‘';
        discountRowEl.style.display = 'none';
        totalEl.textContent = '0Ä‘';
        if (checkoutBtn) checkoutBtn.disabled = true;
        return;
    }

    if (checkoutBtn) checkoutBtn.disabled = false;

    // Render items list
    cartContainer.innerHTML = cart.map(item => `
        <div class="cart-item" style="display: flex; align-items: center; gap: var(--space-md); padding: var(--space-md) 0; border-bottom: 1px solid var(--border-color);">
            <img src="${item.image}" alt="${item.name}" style="width: 80px; height: 80px; object-fit: cover; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
            <div style="flex-grow: 1;">
                <h4 style="font-size: 1rem; font-weight: 600; margin-bottom: var(--space-2xs);">${item.name}</h4>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: var(--space-2xs);">${item.specs}</p>
                <div style="font-weight: 700; color: var(--color-primary);">${formatCurrency(item.price)}</div>
            </div>
            <div style="display: flex; align-items: center; gap: var(--space-2xs);">
                <button class="btn btn-secondary btn-sm" onclick="updateQuantity('${item.id}', ${item.quantity - 1})" style="padding: 0.25rem 0.5rem;">-</button>
                <input type="number" class="form-control" value="${item.quantity}" min="1" onchange="updateQuantity('${item.id}', this.value)" style="width: 60px; text-align: center; padding: 0.25rem;">
                <button class="btn btn-secondary btn-sm" onclick="updateQuantity('${item.id}', ${item.quantity + 1})" style="padding: 0.25rem 0.5rem;">+</button>
            </div>
            <div style="text-align: right; min-width: 120px;">
                <div style="font-weight: 700; font-size: 1.05rem;">${formatCurrency(item.price * item.quantity)}</div>
                <button class="btn btn-outline btn-sm" onclick="removeFromCart('${item.id}')" style="border: none; color: var(--color-danger); padding: 0.25rem; font-size:0.8rem; margin-top:var(--space-2xs);">Remove</button>
            </div>
        </div>
    `).join('');

    // Update Summary
    const subtotal = getSubtotal();
    subtotalEl.textContent = formatCurrency(subtotal);

    let finalTotal = subtotal;

    // Recalculate discount based on new subtotal
    if (activeDiscount) {
        const discountInfo = PROMO_CODES[activeDiscount.code];
        if (discountInfo && subtotal >= discountInfo.minOrder) {
            let discAmt = 0;
            if (discountInfo.type === 'percent') {
                discAmt = subtotal * (discountInfo.value / 100);
            } else if (discountInfo.type === 'fixed') {
                discAmt = discountInfo.value;
            }
            activeDiscount.amount = discAmt;
            localStorage.setItem('electromart_discount', JSON.stringify(activeDiscount));

            discountRowEl.style.display = 'flex';
            discountValEl.textContent = `-${formatCurrency(discAmt)}`;
            finalTotal = subtotal - discAmt;

            // Render current applied coupon tag in form
            const promoTagEl = document.getElementById('appliedPromoTag');
            if (promoTagEl) {
                promoTagEl.innerHTML = `
                    <div style="display: inline-flex; align-items: center; gap: var(--space-xs); background-color: var(--color-success-light); color: var(--color-success); padding: var(--space-xs) var(--space-sm); border-radius: var(--radius-sm); font-size: 0.85rem; font-weight:600; margin-top:var(--space-xs);">
                        <span>ðŸ·ï¸ ${activeDiscount.code} (${activeDiscount.desc})</span>
                        <button onclick="removePromoCode()" style="background:none; border:none; color:var(--color-success); cursor:pointer; font-weight:700;">&times;</button>
                    </div>
                `;
            }
        } else {
            // Under minimum order now, auto remove code
            activeDiscount = null;
            localStorage.removeItem('electromart_discount');
            discountRowEl.style.display = 'none';
            const promoTagEl = document.getElementById('appliedPromoTag');
            if (promoTagEl) promoTagEl.innerHTML = '';
            showToast('Promo code removed because the cart does not meet the minimum requirements', 'warning');
        }
    } else {
        discountRowEl.style.display = 'none';
        const promoTagEl = document.getElementById('appliedPromoTag');
        if (promoTagEl) promoTagEl.innerHTML = '';
    }

    totalEl.textContent = formatCurrency(Math.max(0, finalTotal));
}

// Document Load trigger for badge count
document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    
    // If on index.html, load products list into page
    const productsGrid = document.getElementById('productsGrid');
    if (productsGrid) {
        renderProducts(PRODUCTS);
        
        // Category filtering setup
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('btn-primary'));
                filterBtns.forEach(b => b.classList.add('btn-secondary'));
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-primary');

                const category = btn.getAttribute('data-category');
                const filtered = category === 'all' ? PRODUCTS : PRODUCTS.filter(p => p.category === category);
                renderProducts(filtered);
            });
        });

        // Search bar setup
        const searchInput = document.getElementById('productSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                const filtered = PRODUCTS.filter(p => p.name.toLowerCase().includes(query) || p.specs.toLowerCase().includes(query));
                renderProducts(filtered);
            });
        }
    }

    // Initialize cart items if on cart.html page
    if (document.getElementById('cartItemsList')) {
        renderCartPage();

        // Promotion Form listener
        const promoForm = document.getElementById('promoCodeForm');
        if (promoForm) {
            promoForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const input = document.getElementById('promoCodeInput');
                if (input && input.value) {
                    applyPromoCode(input.value);
                    input.value = '';
                }
            });
        }
    }
});

// Render products list helper (for index.html)
function renderProducts(items) {
    const productsGrid = document.getElementById('productsGrid');
    if (!productsGrid) return;

    if (items.length === 0) {
        productsGrid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: var(--space-2xl) 0;">
                <span style="font-size: 3rem;">ðŸ”</span>
                <h4 style="margin-top: var(--space-md);">No matching products found!</h4>
            </div>
        `;
        return;
    }

    productsGrid.innerHTML = items.map(product => `
        <div class="card card-interactive product-card" style="display:flex; flex-direction:column; height: 100%;">
            <div style="position:relative; padding-top: 75%; background-color: var(--bg-tertiary); overflow: hidden;">
                <img src="${product.image}" alt="${product.name}" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; transition: transform var(--transition-normal);">
                <span class="badge badge-info" style="position:absolute; top: var(--space-xs); left: var(--space-xs); font-size:0.65rem; background: var(--glass-bg); backdrop-filter:blur(5px); color: var(--text-primary); border:1px solid var(--glass-border);">${product.category.toUpperCase()}</span>
            </div>
            <div class="card-body" style="display:flex; flex-direction:column; flex-grow:1; padding: var(--space-md);">
                <h4 class="product-title" style="font-size: 0.95rem; font-weight: 700; margin-bottom: var(--space-2xs); line-height: 1.4; min-height: 2.8em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${product.name}</h4>
                <p style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: var(--space-sm);">${product.specs}</p>
                <div style="margin-top:auto; display:flex; justify-content:space-between; align-items:center; gap:var(--space-xs);">
                    <div style="font-weight: 800; color: var(--color-primary); font-size: 1.1rem;">${formatCurrency(product.price)}</div>
                    <button class="btn btn-primary btn-sm" onclick="addToCart('${product.id}')" style="padding: 0.4rem 0.6rem; font-size: 0.8rem;">Add ðŸ›’</button>
                </div>
            </div>
        </div>
    `).join('');
}

// Make functions available globally
function addToCartDirect(id, name, price, image, specs) {
    const existingItem = cart.find(item => item.id === id);
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({
            id: id,
            name: name,
            price: price,
            image: image,
            specs: specs,
            quantity: 1
        });
    }
    saveCart();
    // Show a clean toast notification or alert
    if (window.showToast) {
        window.showToast(`ÄÃ£ thÃªm ${name} vÃ o giá» hÃ ng!`, 'success');
    } else {
        alert(`ÄÃ£ thÃªm ${name} vÃ o giá» hÃ ng!`);
    }
}
window.addToCartDirect = addToCartDirect;
window.addToCart = addToCart;
window.updateQuantity = updateQuantity;
window.removeFromCart = removeFromCart;
window.removePromoCode = removePromoCode;
window.formatCurrency = formatCurrency;

