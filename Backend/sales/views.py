"""Views for the Sales & Payment module (CV52-CV57).

The three admin pages used to be standalone HTML documents with their own
sidebar and a hard-coded "Admin User" box, reading their data out of
localStorage. They now render through the shared admin layout
(Frontend/templates/admin/base_admin.html) behind accounts.decorators's
@admin_required, so there is one admin account - the one Loc's module
authenticates - for every admin page in the project.
"""
import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, current_user

from . import repo

ADMIN_NOTICES = {
    'status_updated': 'Order status updated.',
    'promo_created': 'Promo code created.',
    'promo_toggled': 'Promo code updated.',
    'promo_deleted': 'Promo code deleted.',
}


# =========================================================== admin: dashboard
@admin_required
def admin_dashboard(request):
    """Analytics dashboard (CV57 / REQ-13).

    Every number and both charts come from the orders collection now; the
    old page drew a hard-coded 7-day line and a fixed 45/35/12/8 donut.
    """
    revenue_chart = repo.revenue_last_days(7)
    category_chart = repo.sales_by_category()

    return render(request, 'admin/sales_dashboard.html', {
        'page_title': 'Analytics Dashboard - ElectroMart Admin',
        'admin_page': 'dashboard',
        'kpis': repo.dashboard_kpis(),
        'recent_orders': [repo.decorate(o) for o in repo.recent_orders(5)],
        'top_products': repo.top_products(5),
        # json_script in the template would need a dict; these go straight
        # into Chart.js so they are serialised here once.
        'revenue_chart_json': json.dumps(revenue_chart),
        'category_chart_json': json.dumps(category_chart),
        'has_chart_data': any(revenue_chart['values']) or bool(category_chart['values']),
        'notice': ADMIN_NOTICES.get(request.GET.get('notice')),
    })


# ============================================================== admin: orders
@admin_required
def admin_orders(request):
    """Order management (CV55 / REQ-08).

    Filtering and searching moved from JS to the query string, so a filtered
    list can be bookmarked and shared - and so the browser never has to hold
    every order in memory.
    """
    status = request.GET.get('status') or 'all'
    q = (request.GET.get('q') or '').strip()

    orders = [repo.decorate(o) for o in repo.list_orders(status=status, q=q)]
    counts = repo.status_counts()

    # Built here rather than in the template: a Django template cannot look a
    # dict up by a loop variable without a custom filter.
    tabs = [{'value': value, 'label': label, 'count': counts.get(value, 0)}
            for value, label in [('all', 'All')] + repo.ORDER_STATUSES]

    return render(request, 'admin/sales_orders.html', {
        'page_title': 'Order Management - ElectroMart Admin',
        'admin_page': 'orders',
        'orders': orders,
        'status': status,
        'q': q,
        'tabs': tabs,
        'notice': ADMIN_NOTICES.get(request.GET.get('notice')),
        'error': request.GET.get('error'),
    })


@admin_required
def admin_order_detail(request, order_id):
    order = repo.get_order(order_id)
    if not order:
        return redirect(reverse('admin_orders'))
    return render(request, 'admin/sales_order_detail.html', {
        'page_title': 'Order %s - ElectroMart Admin' % order['order_code'],
        'admin_page': 'orders',
        'order': repo.decorate(order),
    })


@admin_required
def admin_order_status(request, order_id):
    """Apply a status change from the order list or the detail page."""
    if request.method != 'POST':
        return redirect(reverse('admin_orders'))

    admin = current_user(request)
    try:
        repo.update_status(order_id, request.POST.get('status'),
                           admin_id=admin['_id'], note=request.POST.get('note', ''))
        query = '?notice=status_updated'
    except ValueError as exc:
        query = '?error=%s' % exc

    back = request.POST.get('next') or reverse('admin_orders')
    return redirect(back.split('?')[0] + query)


# ========================================================== admin: promotions
@admin_required
def admin_promotions(request):
    """Promo code management (CV56 / REQ-07)."""
    form_error = None
    if request.method == 'POST':
        try:
            repo.create_coupon(
                request.POST.get('code'),
                request.POST.get('type'),
                request.POST.get('value') or 0,
                request.POST.get('min_order') or 0,
                request.POST.get('description'),
            )
            return redirect('%s?notice=promo_created' % reverse('admin_promotions'))
        except (ValueError, TypeError) as exc:
            form_error = str(exc)

    coupons = repo.list_coupons()
    for coupon in coupons:
        coupon['id'] = str(coupon['_id'])
        coupon['type_label'] = repo.COUPON_TYPE_LABELS.get(coupon['type'], coupon['type'])

    return render(request, 'admin/sales_promotions.html', {
        'page_title': 'Promotion Campaigns - ElectroMart Admin',
        'admin_page': 'promotions',
        'coupons': coupons,
        'coupon_types': repo.COUPON_TYPES,
        'form_error': form_error,
        # Keep what was typed so a rejected form does not clear itself.
        'form_data': request.POST if request.method == 'POST' else {},
        'notice': ADMIN_NOTICES.get(request.GET.get('notice')),
    })


@admin_required
def admin_promotion_toggle(request, coupon_id):
    if request.method == 'POST':
        try:
            repo.toggle_coupon(coupon_id)
        except ValueError:
            pass
    return redirect('%s?notice=promo_toggled' % reverse('admin_promotions'))


@admin_required
def admin_promotion_delete(request, coupon_id):
    if request.method == 'POST':
        repo.delete_coupon(coupon_id)
    return redirect('%s?notice=promo_deleted' % reverse('admin_promotions'))


# ======================================================== storefront: orders
def place_order(request):
    """Turn the browser's cart into a real order (CV52 / REQ-29).

    checkout.js used to append the order to localStorage, which is why the
    admin never saw it. It now posts the cart here as JSON and gets the
    stored order back. The cart itself stays client-side until CV51 moves
    it - only the moment of ordering has to be authoritative.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Malformed request.'}, status=400)

    items = payload.get('items') or []
    if not items:
        return JsonResponse({'ok': False, 'error': 'Your cart is empty.'}, status=400)

    required = ('customer_name', 'phone', 'email', 'address')
    missing = [f for f in required if not (payload.get(f) or '').strip()]
    if missing:
        return JsonResponse({'ok': False, 'error': 'Missing: %s' % ', '.join(missing)}, status=400)

    payment_method = payload.get('payment_method') or repo.PAYMENT_COD
    if payment_method not in repo.PAYMENT_LABELS:
        return JsonResponse({'ok': False, 'error': 'Unknown payment method.'}, status=400)

    user = current_user(request)
    try:
        order = repo.create_order(
            customer_name=payload['customer_name'].strip(),
            phone=payload['phone'].strip(),
            email=payload['email'].strip(),
            address=payload['address'].strip(),
            items=items,
            payment_method=payment_method,
            user_id=user['_id'] if user else None,
            coupon_code=payload.get('coupon_code') or '',
            note=payload.get('note') or '',
            shipping_method=payload.get('shipping_method') or repo.SHIPPING_STANDARD,
        )
    except ValueError as exc:
        # e.g. a cart still holding a product that has since been hidden.
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    repo.register_coupon_use(order['coupon_code'])

    return JsonResponse({'ok': True, 'order': _order_json(order)})


def confirm_transfer(request, order_code):
    """The bank-transfer "I have paid" step of the checkout modal (CV53)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)

    order = repo.get_order_by_code(order_code)
    if not order:
        return JsonResponse({'ok': False, 'error': 'Order not found.'}, status=404)
    try:
        order = repo.mark_paid(order['_id'])
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    return JsonResponse({'ok': True, 'order': _order_json(order)})


def apply_coupon(request):
    """Validate a promo code against the real coupons collection (CV52)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required.'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Malformed request.'}, status=400)

    subtotal = int(payload.get('subtotal') or 0)
    return JsonResponse(repo.apply_coupon(
        payload.get('code', ''), subtotal,
        payload.get('shipping_method') or repo.SHIPPING_STANDARD))


def track_order(request):
    """Guest order tracking (CV54 / REQ-30) - reads the database now."""
    order = None
    error = None
    order_code = (request.GET.get('order_code') or '').strip()
    contact = (request.GET.get('contact') or '').strip()

    if order_code:
        if not contact:
            error = 'Enter the phone number or email used on the order.'
        else:
            found = repo.find_order_for_tracking(order_code, contact)
            if found:
                order = repo.decorate(found)
            else:
                error = 'No order matches that code and contact detail.'

    my_orders = []
    user = current_user(request)
    if user:
        my_orders = [repo.decorate(o) for o in repo.list_orders_by_user(user['_id'])]

    return render(request, 'sales_payment/tracking.html', {
        'page_title': 'Track your order - ElectroMart',
        'order': order,
        'error': error,
        'order_code': order_code,
        'contact': contact,
        'my_orders': my_orders,
    })


def _order_json(order):
    """Only the fields the checkout page needs back - never the whole document,
    which also holds the internal user_id and status history."""
    return {
        'order_code': order['order_code'],
        'customer_name': order['customer_name'],
        'phone': order['phone'],
        'email': order['email'],
        'address': order['address'],
        'subtotal': order['subtotal'],
        'discount': order['discount'],
        'shipping_fee': order['shipping_fee'],
        'total': order['total'],
        'payment_method': order['payment_method'],
        'shipping_method': order.get('shipping_method', ''),
        'status': order['status'],
        'status_label': repo.STATUS_LABELS.get(order['status'], order['status']),
        'items': [{'name': i['name'], 'price': i['price'], 'quantity': i['quantity'],
                   'line_total': i['line_total']} for i in order['items']],
    }
