/* checkout.js - Checkout process and Payment simulation */

document.addEventListener('DOMContentLoaded', () => {
    initCheckoutPage();
});

// Setup default shipping fees
const SHIPPING_FEES = {
    'standard': 30000,
    'express': 50000
};

let activeShipping = 'standard';
let cartSubtotal = 0;
let discountAmt = 0;
let finalTotal = 0;

function initCheckoutPage() {
    const checkoutContainer = document.getElementById('checkoutItemsList');
    if (!checkoutContainer) return; // Not on checkout page

    // Load cart state
    const cartItems = getCart();
    const activeDiscount = JSON.parse(localStorage.getItem('electromart_discount'));

    if (cartItems.length === 0) {
        window.location.href = '/cart/';
        return;
    }

    // Render items summary
    checkoutContainer.innerHTML = cartItems.map(item => `
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; padding: var(--space-xs) 0; border-bottom: 1px dashed var(--border-color);">
            <span style="color: var(--text-secondary); max-width: 70%;">${item.name} <strong style="color: var(--text-primary);">x${item.quantity}</strong></span>
            <span style="font-weight: 600;">${formatCurrency(item.price * item.quantity)}</span>
        </div>
    `).join('');

    cartSubtotal = getSubtotal();
    discountAmt = activeDiscount ? activeDiscount.amount : 0;
    
    // Setup shipping method change event
    const shippingRadios = document.querySelectorAll('input[name="shipping_method"]');
    shippingRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            activeShipping = e.target.value;
            recalculateSummary();
        });
    });

    // Setup payment method change event
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');
    const transferInstructions = document.getElementById('transferInstructions');
    
    paymentRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'transfer') {
                transferInstructions.style.display = 'block';
            } else {
                transferInstructions.style.display = 'none';
            }
        });
    });

    // Checkout Form Submit
    const checkoutForm = document.getElementById('checkoutForm');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', (e) => {
            e.preventDefault();
            processOrderSubmit();
        });
    }

    recalculateSummary();
}

function recalculateSummary() {
    const subtotalEl = document.getElementById('summarySubtotal');
    const discountRow = document.getElementById('summaryDiscountRow');
    const discountEl = document.getElementById('summaryDiscount');
    const shippingEl = document.getElementById('summaryShipping');
    const totalEl = document.getElementById('summaryTotal');

    const shippingFee = SHIPPING_FEES[activeShipping];
    
    subtotalEl.textContent = formatCurrency(cartSubtotal);
    shippingEl.textContent = formatCurrency(shippingFee);

    if (discountAmt > 0) {
        discountRow.style.display = 'flex';
        discountEl.textContent = `-${formatCurrency(discountAmt)}`;
    } else {
        discountRow.style.display = 'none';
    }

    finalTotal = cartSubtotal - discountAmt + shippingFee;
    totalEl.textContent = formatCurrency(Math.max(0, finalTotal));
}

/* The order used to be built here and pushed into localStorage, which is why
   nobody but this browser ever saw it. It is now posted to
   sales/views.place_order, which recomputes every amount from the product
   prices in MongoDB and returns the stored order - so the admin's Order
   Management page shows it immediately, and a customer cannot edit the total
   before it is saved. */

function csrfToken() {
    const field = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return field ? field.value : '';
}

function postJson(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(payload || {})
    }).then(function (response) {
        return response.json().catch(function () {
            throw new Error('The server returned an unexpected response.');
        });
    });
}
window.postJson = postJson;

// Submit Order and open payment modal if bank transfer, or direct success page
function processOrderSubmit() {
    const name = document.getElementById('fullName').value.trim();
    const phone = document.getElementById('phoneNumber').value.trim();
    const email = document.getElementById('email').value.trim();
    const address = document.getElementById('address').value.trim();
    const paymentMethod = document.querySelector('input[name="payment_method"]:checked').value;

    // Validate phone number (basic)
    if (!/^\d{10,11}$/.test(phone)) {
        document.getElementById('phoneNumber').classList.add('is-invalid');
        return;
    } else {
        document.getElementById('phoneNumber').classList.remove('is-invalid');
    }

    const submitBtn = document.getElementById('placeOrderBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.dataset.label = submitBtn.textContent;
        submitBtn.textContent = 'Placing order...';
    }

    const activeDiscount = JSON.parse(localStorage.getItem('electromart_discount'));
    const payload = {
        customer_name: name,
        phone: phone,
        email: email,
        address: address,
        payment_method: paymentMethod,
        shipping_method: activeShipping,
        coupon_code: activeDiscount ? activeDiscount.code : '',
        items: getCart().map(function (item) {
            return {
                product_id: item.id,
                name: item.name,
                price: item.price,
                quantity: item.quantity,
                image: item.image,
                specs: item.specs
            };
        })
    };

    postJson('/checkout/place-order/', payload).then(function (data) {
        if (!data.ok) {
            throw new Error(data.error || 'The order could not be placed.');
        }
        const order = data.order;
        if (order.payment_method === 'cod') {
            clearCart();
            showOrderSuccess(order);
        } else {
            openPaymentModal(order);
        }
    }).catch(function (err) {
        if (window.showToast) {
            showToast(err.message, 'danger');
        } else {
            alert(err.message);
        }
    }).finally(function () {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = submitBtn.dataset.label || 'Place order';
        }
    });
}

let paymentTimer = null;
let timerSeconds = 300; // 5 minutes

function openPaymentModal(order) {
    const modalId = 'paymentModal';
    const qrImage = document.getElementById('vietQRImg');
    const qrAmount = document.getElementById('qrAmountText');
    const qrDesc = document.getElementById('qrDescText');
    const qrTimer = document.getElementById('qrTimerText');

    // Create a VietQR image using free API img.vietqr.io
    // Bank ID: MBBank (MB), Account Name: ELECTROMART STORE, Account No: 8888999999
    const bankId = 'MB';
    const accountNo = '8888999999';
    const accountName = 'ELECTROMART STORE';
    const description = `EM ${order.order_code.replace('EM-', '')}`;
    
    // URL format for VietQR API
    const vietQRUrl = `https://img.vietqr.io/image/${bankId}-${accountNo}-print.png?amount=${order.total}&addInfo=${encodeURIComponent(description)}&accountName=${encodeURIComponent(accountName)}`;
    
    qrImage.src = vietQRUrl;
    qrAmount.textContent = formatCurrency(order.total);
    qrDesc.textContent = description;
    
    // Set order object to local modal scope
    window.currentPendingOrder = order;

    // Start timer countdown
    timerSeconds = 300;
    qrTimer.textContent = '05:00';
    if (paymentTimer) clearInterval(paymentTimer);

    paymentTimer = setInterval(() => {
        timerSeconds--;
        const mins = Math.floor(timerSeconds / 60).toString().padStart(2, '0');
        const secs = (timerSeconds % 60).toString().padStart(2, '0');
        qrTimer.textContent = `${mins}:${secs}`;

        if (timerSeconds <= 0) {
            clearInterval(paymentTimer);
            showToast('Payment session expired!', 'danger');
            closeModal(modalId);
        }
    }, 1000);

    openModal(modalId);
}

// Customer says the transfer is done: the server moves the order from
// "unpaid" to "confirmed" (sales/repo.mark_paid), so the admin sees the
// payment too. Marking it only in localStorage left the two sides disagreeing.
function simulatePaymentSuccess() {
    if (!window.currentPendingOrder) return;

    const order = window.currentPendingOrder;
    postJson('/checkout/' + encodeURIComponent(order.order_code) + '/confirm-transfer/', {})
        .then(function (data) {
            if (!data.ok) {
                throw new Error(data.error || 'The payment could not be confirmed.');
            }
            clearInterval(paymentTimer);
            closeModal('paymentModal');
            clearCart();
            showToast('Bank transfer payment confirmed successfully!', 'success');
            showOrderSuccess(data.order);
        })
        .catch(function (err) {
            if (window.showToast) {
                showToast(err.message, 'danger');
            } else {
                alert(err.message);
            }
        });
}

// Show success view
function showOrderSuccess(order) {
    const contentArea = document.querySelector('.checkout-layout') || document.querySelector('.cart-layout');
    if (!contentArea) return;

    contentArea.innerHTML = `
        <div class="card card-glass" style="grid-column: span 2; padding: var(--space-2xl); text-align: center; max-width: 650px; margin: 0 auto;">
            <span style="font-size: 5rem;">ðŸŽ‰</span>
            <h2 style="font-size: 2rem; font-weight: 800; margin-top: var(--space-md); color: var(--color-success);">Order Placed Successfully!</h2>
            <p style="color: var(--text-secondary); margin-top: var(--space-xs); margin-bottom: var(--space-xl);">
                Thank you for shopping at ElectroMart. Your order ID is: 
                <strong style="color: var(--color-primary); font-size: 1.25rem; display: block; margin-top: var(--space-2xs); font-family: monospace;">${order.order_code}</strong>
            </p>

            <div style="text-align: left; background-color: var(--bg-tertiary); padding: var(--space-lg); border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: var(--space-xl); font-size:0.95rem;">
                <h4 style="border-bottom: 1px dashed var(--border-color); padding-bottom: var(--space-xs); margin-bottom: var(--space-sm); font-weight: 700;">Delivery Information</h4>
                <p style="margin-bottom:var(--space-2xs);"><strong>Customer:</strong> ${order.customer_name}</p>
                <p style="margin-bottom:var(--space-2xs);"><strong>Phone Number:</strong> ${order.phone}</p>
                <p style="margin-bottom:var(--space-2xs);"><strong>Shipping Address:</strong> ${order.address}</p>
                <p style="margin-bottom:var(--space-2xs);"><strong>Total Amount:</strong> <strong style="color: var(--color-primary);">${formatCurrency(order.total)}</strong></p>
                <p style="margin-bottom:var(--space-2xs);"><strong>Payment Method:</strong> ${order.payment_method === 'cod' ? 'Cash on Delivery (COD)' : 'Bank Transfer (VietQR)'}</p>
                <p style="margin-bottom:var(--space-2xs);"><strong>Initial Status:</strong> <span class="badge ${order.status === 'confirmed' ? 'badge-success' : 'badge-warning'}">${order.status_label}</span></p>
            </div>

            <div style="display: flex; gap: var(--space-md); justify-content: center;">
                <a href="/" class="btn btn-secondary">Continue Shopping</a>
                <a href="/tracking/?order_code=${order.order_code}&contact=${encodeURIComponent(order.phone)}" class="btn btn-primary">Track Order &rarr;</a>
            </div>
        </div>
    `;

    // Reset heading
    const mainHeading = document.querySelector('.main-content h1');
    if (mainHeading) mainHeading.textContent = 'Order Confirmation';
}

// Make globally available
window.simulatePaymentSuccess = simulatePaymentSuccess;

