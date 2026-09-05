"""Data access layer for the Sales & Payment module (CV40, CV52-CV57).

Mirrors accounts/repo.py and catalogue/repo.py: no Django ORM, no models.py,
every function talks to MongoDB directly through db.py.

Replaces what used to live in localStorage on the browser side
(`electromart_orders` / `electromart_promotions` in Frontend/static/
sales_payment/js/shared.js), so the admin pages and the storefront finally
read the same data.

Two collections:
    orders   one document per placed order, line items embedded (an order line
             never changes after the fact, so embedding is right here - see
             the embed/reference table of CV22)
    coupons  one document per promo code, referenced by code from an order
"""
import re
from datetime import datetime, timedelta

from bson import ObjectId

from .db import COUPONS, ORDERS, get_db

# ------------------------------------------------------------- order status
# The values are the ones the existing templates and JS already use, so the
# badge classes in the GUI keep working unchanged.
STATUS_UNPAID = 'unpaid'
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_SHIPPING = 'shipping'
STATUS_COMPLETED = 'completed'
STATUS_CANCELLED = 'cancelled'

ORDER_STATUSES = [
    (STATUS_UNPAID, 'Unpaid'),
    (STATUS_PENDING, 'Pending'),
    (STATUS_CONFIRMED, 'Confirmed'),
    (STATUS_SHIPPING, 'Shipping'),
    (STATUS_COMPLETED, 'Completed'),
    (STATUS_CANCELLED, 'Cancelled'),
]
STATUS_LABELS = dict(ORDER_STATUSES)

# Which CSS badge each status uses in the admin table.
STATUS_BADGES = {
    STATUS_UNPAID: 'badge-danger',
    STATUS_PENDING: 'badge-warning',
    STATUS_CONFIRMED: 'badge-info',
    STATUS_SHIPPING: 'badge-primary',
    STATUS_COMPLETED: 'badge-success',
    STATUS_CANCELLED: 'badge-danger',
}

# A cancelled order never counts as revenue, and an unpaid one has not been
# collected yet - both KPI and the revenue chart exclude them.
REVENUE_STATUSES = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_SHIPPING, STATUS_COMPLETED]

# Status changes an admin is allowed to make (CV55). Kept server-side so a
# hand-crafted POST cannot move a cancelled order back into shipping.
ALLOWED_TRANSITIONS = {
    STATUS_UNPAID: [STATUS_CONFIRMED, STATUS_CANCELLED],
    STATUS_PENDING: [STATUS_CONFIRMED, STATUS_CANCELLED],
    STATUS_CONFIRMED: [STATUS_SHIPPING, STATUS_CANCELLED],
    STATUS_SHIPPING: [STATUS_COMPLETED, STATUS_CANCELLED],
    STATUS_COMPLETED: [],
    STATUS_CANCELLED: [],
}

PAYMENT_COD = 'cod'
PAYMENT_TRANSFER = 'transfer'
PAYMENT_LABELS = {PAYMENT_COD: 'Cash on delivery', PAYMENT_TRANSFER: 'Bank transfer'}

# ------------------------------------------------------------- coupon types
COUPON_PERCENT = 'percent'
COUPON_FIXED = 'fixed'
COUPON_FREESHIP = 'freeship'
COUPON_TYPES = [
    (COUPON_PERCENT, 'Percentage discount'),
    (COUPON_FIXED, 'Fixed amount discount'),
    (COUPON_FREESHIP, 'Free shipping'),
]
COUPON_TYPE_LABELS = dict(COUPON_TYPES)

# Shipping fees, matching the two radio options on the checkout page. The
# figures used to live only in checkout.js, so the total the customer saw and
# the total that got stored could drift apart; the server owns them now.
SHIPPING_STANDARD = 'standard'
SHIPPING_EXPRESS = 'express'
SHIPPING_FEES = {SHIPPING_STANDARD: 30000, SHIPPING_EXPRESS: 50000}
SHIPPING_LABELS = {SHIPPING_STANDARD: 'Standard delivery', SHIPPING_EXPRESS: 'Express delivery'}
FREE_SHIPPING_THRESHOLD = 20000000


# =============================================================== order code
def next_order_number():
    """Next sequential order number, e.g. 137 -> code EM-000137.

    Sequential rather than the random EM-582941 the old JS generated, so the
    admin list sorts sensibly. Two orders placed in the same instant could
    both read the same number, but order_code carries a unique index
    (Database/create_indexes.py) so the loser fails loudly instead of
    quietly overwriting - acceptable for a shop this size.
    """
    last = get_db()[ORDERS].find_one({}, {'order_no': 1}, sort=[('order_no', -1)])
    return ((last or {}).get('order_no') or 0) + 1


# ============================================================ product lookup
def resolve_product_refs(refs):
    """Map whatever the cart called a product onto the real product document.

    A ref is either a 24-character ObjectId hex string (what the admin seeder
    sends) or a part number (what the storefront's add-to-cart button sends).
    Both are looked up in one round trip rather than one query per line.
    """
    refs = [r for r in refs if r]
    if not refs:
        return {}

    oids, parts = [], []
    for ref in refs:
        try:
            oids.append(ObjectId(ref))
        except Exception:
            parts.append(ref)

    or_clauses = []
    if oids:
        or_clauses.append({'_id': {'$in': oids}})
    if parts:
        or_clauses.append({'part_number': {'$in': parts}})
    if not or_clauses:
        return {}

    found = get_db()['products'].find(
        or_clauses[0] if len(or_clauses) == 1 else {'$or': or_clauses},
        {'name': 1, 'part_number': 1, 'min_price': 1, 'variants': 1, 'is_hidden': 1})

    by_ref = {}
    for product in found:
        by_ref[str(product['_id'])] = product
        if product.get('part_number'):
            by_ref[product['part_number']] = product
    return by_ref


def product_price(product):
    """Authoritative unit price: the first variant's retail price, falling back
    to the product's min_price (the field the storefront cards display)."""
    variants = product.get('variants') or []
    if variants:
        price = variants[0].get('retail_price')
        if price:
            return int(price)
    return int(product.get('min_price') or 0)


# ==================================================================== order
def create_order(customer_name, phone, email, address, items, payment_method,
                 user_id=None, coupon_code='', note='',
                 shipping_method=SHIPPING_STANDARD):
    """Persist one order and return the stored document.

    `items` is a list of {product_id, name, price, quantity, image, specs}.
    Money is recomputed here from the item prices instead of trusting the
    numbers the browser posted - the old JS did the arithmetic client-side,
    which meant a customer could edit the total before it was saved.
    """
    db = get_db()
    now = datetime.utcnow()

    refs = [item.get('product_id') or item.get('id') or '' for item in items]
    resolved = resolve_product_refs(refs)

    clean_items = []
    for item, ref in zip(items, refs):
        qty = max(1, int(item.get('quantity') or 1))
        # The storefront's add-to-cart passes a part number, not an id (see
        # addToCartDirect in cart.js), so it is resolved to the real product
        # here - otherwise the category chart could never join an order line
        # back to its category.
        product = resolved.get(ref)
        if not product:
            raise ValueError('"%s" is no longer available.'
                             % (item.get('name') or ref or 'A product in your cart'))
        if product.get('is_hidden'):
            raise ValueError('"%s" is no longer on sale.' % product.get('name', ref))

        # The price comes from the database, never from the request: the cart
        # lives in the browser, so a posted price is attacker-controlled and
        # "price": 1 would otherwise buy anything for 1 dong (CV78).
        price = product_price(product)
        clean_items.append({
            'product_id': str(product['_id']),
            'part_number': product.get('part_number') or ref,
            'name': product.get('name') or item.get('name') or '',
            'price': price,
            'quantity': qty,
            'line_total': price * qty,
            'image': item.get('image') or '',
            'specs': item.get('specs') or '',
        })

    subtotal = sum(i['line_total'] for i in clean_items)
    coupon = find_coupon(coupon_code) if coupon_code else None
    discount, free_ship = coupon_effect(coupon, subtotal)
    if shipping_method not in SHIPPING_FEES:
        shipping_method = SHIPPING_STANDARD
    shipping_fee = shipping_fee_for(subtotal, free_ship, shipping_method)

    order_no = next_order_number()
    doc = {
        'order_no': order_no,
        'order_code': 'EM-%06d' % order_no,
        'user_id': ObjectId(user_id) if user_id else None,
        'customer_name': customer_name,
        'phone': phone,
        'email': (email or '').strip().lower(),
        'address': address,
        'note': note,
        'items': clean_items,
        'subtotal': subtotal,
        'coupon_code': coupon['code'] if coupon else '',
        'discount': discount,
        'shipping_method': shipping_method,
        'shipping_fee': shipping_fee,
        'total': max(0, subtotal - discount + shipping_fee),
        'payment_method': payment_method,
        # Bank transfer starts unpaid; COD is accepted straight away and waits
        # for the admin to confirm it (CV53).
        'status': STATUS_UNPAID if payment_method == PAYMENT_TRANSFER else STATUS_PENDING,
        'status_history': [{'status': STATUS_UNPAID if payment_method == PAYMENT_TRANSFER
                            else STATUS_PENDING, 'at': now, 'by': None, 'note': 'Order placed'}],
        'created_at': now,
        'updated_at': now,
    }
    result = db[ORDERS].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def get_order(order_id):
    return get_db()[ORDERS].find_one({'_id': _oid(order_id)})


def get_order_by_code(order_code):
    return get_db()[ORDERS].find_one({'order_code': (order_code or '').strip().upper()})


def find_order_for_tracking(order_code, phone_or_email):
    """Guest order lookup (CV54).

    The code alone is not enough to open someone else's order, so the phone
    number or email on the order has to match as well.
    """
    order = get_order_by_code(order_code)
    if not order:
        return None
    needle = (phone_or_email or '').strip().lower()
    if not needle:
        return None
    if needle in (order.get('phone', '').strip().lower(), order.get('email', '').strip().lower()):
        return order
    return None


def list_orders(status=None, q='', limit=200):
    """Admin order list (CV55), newest first."""
    query = {}
    if status and status != 'all':
        query['status'] = status
    if q:
        # re.escape for the same reason as accounts/views.py: an unbalanced
        # bracket typed in the search box must not reach $regex raw.
        safe = re.escape(q.strip())
        query['$or'] = [
            {'order_code': {'$regex': safe, '$options': 'i'}},
            {'customer_name': {'$regex': safe, '$options': 'i'}},
            {'phone': {'$regex': safe, '$options': 'i'}},
            {'email': {'$regex': safe, '$options': 'i'}},
        ]
    return list(get_db()[ORDERS].find(query).sort('created_at', -1).limit(limit))


def list_orders_by_user(user_id, limit=50):
    return list(get_db()[ORDERS].find({'user_id': _oid(user_id)})
                .sort('created_at', -1).limit(limit))


def status_counts():
    """One count per status, for the filter tabs."""
    rows = get_db()[ORDERS].aggregate([{'$group': {'_id': '$status', 'n': {'$sum': 1}}}])
    counts = {status: 0 for status, _ in ORDER_STATUSES}
    total = 0
    for row in rows:
        if row['_id'] in counts:
            counts[row['_id']] = row['n']
        total += row['n']
    counts['all'] = total
    return counts


def update_status(order_id, new_status, admin_id=None, note=''):
    """Move an order to `new_status`, refusing a transition that is not allowed.

    Returns the updated document, or raises ValueError so the view can show
    the reason instead of silently doing nothing.
    """
    order = get_order(order_id)
    if not order:
        raise ValueError('Order not found.')
    current = order.get('status')
    if new_status == current:
        return order
    if new_status not in ALLOWED_TRANSITIONS.get(current, []):
        raise ValueError('Cannot change an order from "%s" to "%s".'
                         % (STATUS_LABELS.get(current, current),
                            STATUS_LABELS.get(new_status, new_status)))

    now = datetime.utcnow()
    return get_db()[ORDERS].find_one_and_update(
        {'_id': _oid(order_id)},
        {'$set': {'status': new_status, 'updated_at': now},
         '$push': {'status_history': {'status': new_status, 'at': now,
                                      'by': _oid(admin_id) if admin_id else None,
                                      'note': note}}},
        return_document=True,
    )


def mark_paid(order_id):
    """Bank transfer confirmed (CV53) - unpaid becomes confirmed."""
    return update_status(order_id, STATUS_CONFIRMED, note='Bank transfer received')


def allowed_next_statuses(order):
    return [(s, STATUS_LABELS[s]) for s in ALLOWED_TRANSITIONS.get(order.get('status'), [])]


# =================================================================== coupon
def list_coupons(active_only=False):
    query = {'is_active': True} if active_only else {}
    return list(get_db()[COUPONS].find(query).sort('created_at', -1))


def find_coupon(code):
    if not code:
        return None
    return get_db()[COUPONS].find_one({'code': code.strip().upper()})


def create_coupon(code, coupon_type, value, min_order, description):
    """Add a promo code (CV56). Raises ValueError on bad input so the view can
    render the message next to the form."""
    code = (code or '').strip().upper()
    if not re.match(r'^[A-Z0-9]{3,20}$', code):
        raise ValueError('Code must be 3-20 characters, letters and digits only.')
    if find_coupon(code):
        raise ValueError('That code already exists.')
    if coupon_type not in COUPON_TYPE_LABELS:
        raise ValueError('Unknown discount type.')

    value = int(value or 0)
    min_order = int(min_order or 0)
    if coupon_type == COUPON_PERCENT and not 1 <= value <= 100:
        raise ValueError('A percentage discount must be between 1 and 100.')
    if coupon_type == COUPON_FIXED and value <= 0:
        raise ValueError('A fixed discount must be greater than 0.')
    if coupon_type == COUPON_FREESHIP:
        value = 0
    if min_order < 0:
        raise ValueError('Minimum order cannot be negative.')

    doc = {
        'code': code,
        'type': coupon_type,
        'value': value,
        'min_order': min_order,
        'description': (description or '').strip(),
        'is_active': True,
        'used_count': 0,
        'created_at': datetime.utcnow(),
    }
    result = get_db()[COUPONS].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def toggle_coupon(coupon_id):
    coupon = get_db()[COUPONS].find_one({'_id': _oid(coupon_id)})
    if not coupon:
        raise ValueError('Promo code not found.')
    return get_db()[COUPONS].find_one_and_update(
        {'_id': _oid(coupon_id)},
        {'$set': {'is_active': not coupon.get('is_active', False)}},
        return_document=True,
    )


def delete_coupon(coupon_id):
    return get_db()[COUPONS].delete_one({'_id': _oid(coupon_id)}).deleted_count


def coupon_effect(coupon, subtotal):
    """Return (discount_amount, free_shipping) for a coupon on a subtotal.

    An inactive coupon or an order below its minimum has no effect - the same
    rule the checkout page and the admin order both need, which is why it
    lives here instead of in either view.
    """
    if not coupon or not coupon.get('is_active'):
        return 0, False
    if subtotal < coupon.get('min_order', 0):
        return 0, False

    ctype = coupon.get('type')
    if ctype == COUPON_PERCENT:
        return int(subtotal * coupon.get('value', 0) / 100), False
    if ctype == COUPON_FIXED:
        # Never discount more than the order is worth.
        return min(int(coupon.get('value', 0)), subtotal), False
    if ctype == COUPON_FREESHIP:
        return 0, True
    return 0, False


def shipping_fee_for(subtotal, free_ship=False, shipping_method=SHIPPING_STANDARD):
    """Free above the threshold or with a freeship coupon, otherwise the fee of
    the chosen delivery option."""
    if free_ship or subtotal >= FREE_SHIPPING_THRESHOLD:
        return 0
    return SHIPPING_FEES.get(shipping_method, SHIPPING_FEES[SHIPPING_STANDARD])


def apply_coupon(code, subtotal, shipping_method=SHIPPING_STANDARD):
    """Checkout "apply code" step. Returns a dict the page can render directly."""
    coupon = find_coupon(code)
    if not coupon:
        return {'ok': False, 'error': 'This promo code does not exist.'}
    if not coupon.get('is_active'):
        return {'ok': False, 'error': 'This promo code is no longer active.'}
    if subtotal < coupon.get('min_order', 0):
        return {'ok': False,
                'error': 'This code needs a minimum order of %s.' % format_vnd(coupon['min_order'])}

    discount, free_ship = coupon_effect(coupon, subtotal)
    shipping_fee = shipping_fee_for(subtotal, free_ship, shipping_method)
    return {'ok': True, 'code': coupon['code'], 'discount': discount,
            'free_shipping': free_ship, 'description': coupon.get('description', ''),
            'shipping_fee': shipping_fee,
            'total': max(0, subtotal - discount + shipping_fee)}


def register_coupon_use(code):
    if code:
        get_db()[COUPONS].update_one({'code': code}, {'$inc': {'used_count': 1}})


# ================================================ dashboard & reports (CV57)
def dashboard_kpis():
    """Total revenue, order count, average order value, active promo count."""
    db = get_db()
    rows = list(db[ORDERS].aggregate([
        {'$match': {'status': {'$in': REVENUE_STATUSES}}},
        {'$group': {'_id': None, 'revenue': {'$sum': '$total'}, 'n': {'$sum': 1}}},
    ]))
    revenue = rows[0]['revenue'] if rows else 0
    counted = rows[0]['n'] if rows else 0
    return {
        'total_revenue': revenue,
        'total_orders': db[ORDERS].count_documents({}),
        'avg_order_value': int(revenue / counted) if counted else 0,
        'active_promotions': db[COUPONS].count_documents({'is_active': True}),
    }


def revenue_last_days(days=7):
    """Revenue per day for the line chart, including days with no orders.

    Mongo only returns the days that have data, so the gaps are filled in
    here - otherwise the chart would silently compress a quiet day away and
    misrepresent the trend.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)

    rows = get_db()[ORDERS].aggregate([
        {'$match': {'status': {'$in': REVENUE_STATUSES}, 'created_at': {'$gte': start}}},
        {'$group': {'_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                    'revenue': {'$sum': '$total'}}},
    ])
    by_day = {row['_id']: row['revenue'] for row in rows}

    labels, values = [], []
    for i in range(days):
        day = start + timedelta(days=i)
        labels.append(day.strftime('%d/%m'))
        values.append(by_day.get(day.strftime('%Y-%m-%d'), 0))
    return {'labels': labels, 'values': values}


def sales_by_category(limit=6):
    """Revenue share per category, for the donut chart.

    Order lines store product_id as a string, so they are looked up against
    the products collection to find each one's category.
    """
    from bson import ObjectId as _OID
    db = get_db()

    rows = db[ORDERS].aggregate([
        {'$match': {'status': {'$in': REVENUE_STATUSES}}},
        {'$unwind': '$items'},
        {'$group': {'_id': '$items.product_id', 'revenue': {'$sum': '$items.line_total'}}},
    ])
    revenue_by_product = {row['_id']: row['revenue'] for row in rows if row['_id']}
    if not revenue_by_product:
        return {'labels': [], 'values': []}

    oids = []
    for pid in revenue_by_product:
        try:
            oids.append(_OID(pid))
        except Exception:
            continue

    products = db['products'].find({'_id': {'$in': oids}}, {'category_id': 1})
    category_of = {str(p['_id']): p.get('category_id') for p in products}

    names = {c['_id']: c['name'] for c in db['categories'].find({}, {'name': 1})}

    totals = {}
    for pid, revenue in revenue_by_product.items():
        cat_id = category_of.get(pid)
        label = names.get(cat_id, 'Other')
        totals[label] = totals.get(label, 0) + revenue

    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return {'labels': [k for k, _ in ordered], 'values': [v for _, v in ordered]}


def recent_orders(limit=5):
    return list(get_db()[ORDERS].find().sort('created_at', -1).limit(limit))


def top_products(limit=5):
    """Best sellers by quantity, for the report table (CV57)."""
    rows = get_db()[ORDERS].aggregate([
        {'$match': {'status': {'$in': REVENUE_STATUSES}}},
        {'$unwind': '$items'},
        {'$group': {'_id': '$items.name',
                    'qty': {'$sum': '$items.quantity'},
                    'revenue': {'$sum': '$items.line_total'}}},
        {'$sort': {'qty': -1}},
        {'$limit': limit},
    ])
    return [{'name': r['_id'], 'qty': r['qty'], 'revenue': r['revenue']} for r in rows]


# ================================================================== helpers
def format_vnd(amount):
    """1234000 -> "1.234.000d". Templates use the |vnd filter instead; this is
    for messages built in Python."""
    return '{:,}'.format(int(amount or 0)).replace(',', '.') + 'd'


def decorate(order):
    """Add the display-only fields the templates need."""
    order['id'] = str(order['_id'])
    order['status_label'] = STATUS_LABELS.get(order.get('status'), order.get('status'))
    order['status_badge'] = STATUS_BADGES.get(order.get('status'), 'badge-info')
    order['payment_label'] = PAYMENT_LABELS.get(order.get('payment_method'), order.get('payment_method'))
    order['shipping_label'] = SHIPPING_LABELS.get(order.get('shipping_method'), '')
    order['item_count'] = sum(i.get('quantity', 0) for i in order.get('items', []))
    order['next_statuses'] = allowed_next_statuses(order)
    return order


def _oid(value):
    """Accept both an ObjectId and its string form, like the other repos do."""
    return value if isinstance(value, ObjectId) else ObjectId(value)
