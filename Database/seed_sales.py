"""Seed the demo orders and promo codes for the Sales & Payment module (CV40).

seed_data.py owns categories/brands/products and seed_accounts.py owns the
account collections; this one owns `orders` and `coupons`.

    python Database/seed_sales.py            # upsert, keeps other orders
    python Database/seed_sales.py --reset    # wipe both collections first
    python Database/seed_sales.py --quiet    # no summary table

Replaces the seedDemoData() button that used to write four fake orders into
the browser's localStorage: those numbers were invented, unrelated to the
real product catalogue, and invisible to anyone else. The orders here are
built from actual products and actual seeded customers, so the dashboard
charts and the KPI tiles show something meaningful.

Not destructive by default, same convention as seed_accounts.py.

Connection settings come from the environment:
    MONGO_URI       default mongodb://localhost:27017/
    MONGO_DB_NAME   default electromart_db
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

import django

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', 'Backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electromart.settings')
django.setup()

from sales import repo                                     # noqa: E402
from sales.db import COUPONS, ORDERS, get_db               # noqa: E402
from create_indexes import ensure_sales_indexes            # noqa: E402

# (code, type, value, min_order, description)
COUPON_DATA = [
    ('ELECTRO10', repo.COUPON_PERCENT, 10, 10000000,
     '10% off orders from 10,000,000 d'),
    ('EM500', repo.COUPON_FIXED, 500000, 5000000,
     '500,000 d off orders from 5,000,000 d'),
    ('FREESHIP', repo.COUPON_FREESHIP, 0, 0,
     'Free shipping nationwide, no minimum'),
    ('WELCOME5', repo.COUPON_PERCENT, 5, 0,
     '5% off your first order, any value'),
]

# (customer email, hours ago, target status, coupon code, number of products)
# The statuses cover every badge the admin table can render, and the ages are
# spread over the last week so the revenue chart has a real shape.
ORDER_PLAN = [
    ('an.nguyen@example.com', 2, repo.STATUS_PENDING, 'ELECTRO10', 2),
    ('binh.tran@example.com', 20, repo.STATUS_CONFIRMED, '', 1),
    ('cuong.le@example.com', 30, repo.STATUS_SHIPPING, 'FREESHIP', 2),
    ('an.nguyen@example.com', 50, repo.STATUS_COMPLETED, '', 1),
    ('dung.pham@example.com', 74, repo.STATUS_COMPLETED, 'EM500', 3),
    ('mua.hang@techviet.vn', 96, repo.STATUS_COMPLETED, 'ELECTRO10', 2),
    ('em.hoang@example.com', 120, repo.STATUS_CANCELLED, '', 1),
    ('phuc.vo@example.com', 140, repo.STATUS_COMPLETED, '', 2),
    ('giang.do@example.com', 6, repo.STATUS_UNPAID, 'WELCOME5', 1),
    ('sales@dienlanhmienbac.vn', 160, repo.STATUS_COMPLETED, 'EM500', 4),
]

# How to walk a fresh order up to the status the plan asks for, since
# repo.update_status() only permits one legal step at a time.
PATH_TO = {
    repo.STATUS_UNPAID: [],
    repo.STATUS_PENDING: [],
    repo.STATUS_CONFIRMED: [repo.STATUS_CONFIRMED],
    repo.STATUS_SHIPPING: [repo.STATUS_CONFIRMED, repo.STATUS_SHIPPING],
    repo.STATUS_COMPLETED: [repo.STATUS_CONFIRMED, repo.STATUS_SHIPPING, repo.STATUS_COMPLETED],
    repo.STATUS_CANCELLED: [repo.STATUS_CANCELLED],
}


def seed_coupons(db, quiet):
    rows = []
    for code, ctype, value, min_order, description in COUPON_DATA:
        existing = repo.find_coupon(code)
        if existing:
            db[COUPONS].update_one({'_id': existing['_id']}, {'$set': {
                'type': ctype, 'value': value, 'min_order': min_order,
                'description': description}})
            rows.append((code, 'updated'))
        else:
            repo.create_coupon(code, ctype, value, min_order, description)
            rows.append((code, 'new'))
    if not quiet:
        for code, state in rows:
            print('  coupon %-12s %s' % (code, state))
    return len(rows)


def seed_orders(db, quiet):
    rnd = random.Random(2026)

    users = {u['email']: u for u in db['users'].find({}, {'email': 1, 'full_name': 1})}
    addresses = {a['user_id']: a for a in db['addresses'].find()}
    products = list(db['products'].find({}, {
        'name': 1, 'variants': 1, 'min_price': 1, 'images': 1, 'specifications': 1}))

    if not products:
        print('No products found - run "python Database/seed_data.py" first.')
        return 0
    if not users:
        print('No users found - run "python Database/seed_accounts.py" first.')
        return 0

    created = 0
    for index, (email, hours_ago, target_status, coupon_code, item_count) in enumerate(ORDER_PLAN):
        user = users.get(email)
        if not user:
            if not quiet:
                print('  skip %-28s (no such account)' % email)
            continue

        # Idempotency key: a stable tag per plan row. Matching on the computed
        # timestamp instead would never hit, because the timestamp is relative
        # to "now" and therefore different on every run.
        seed_tag = 'plan-%02d' % index
        if db[ORDERS].find_one({'seed_tag': seed_tag}):
            if not quiet:
                print('  order %-8s for %-24s already seeded' % (seed_tag, email))
            continue

        placed_at = datetime.utcnow() - timedelta(hours=hours_ago)

        picked = rnd.sample(products, min(item_count, len(products)))
        items = []
        for product in picked:
            variant = (product.get('variants') or [{}])[0]
            price = variant.get('retail_price') or product.get('min_price') or 0
            specs = product.get('specifications') or {}
            spec_text = ', '.join('%s: %s' % (k, v) for k, v in list(specs.items())[:2])
            items.append({
                'product_id': str(product['_id']),
                'name': product['name'],
                'price': int(price),
                'quantity': rnd.randint(1, 2),
                'image': (product.get('images') or [''])[0],
                'specs': spec_text,
            })

        address = addresses.get(user['_id'])
        order = repo.create_order(
            customer_name=user.get('full_name') or email,
            phone=(address or {}).get('phone') or '09%08d' % rnd.randint(0, 99999999),
            email=email,
            address=_format_address(address),
            items=items,
            payment_method=repo.PAYMENT_TRANSFER if target_status == repo.STATUS_UNPAID
            else rnd.choice([repo.PAYMENT_COD, repo.PAYMENT_TRANSFER]),
            user_id=user['_id'],
            coupon_code=coupon_code,
        )
        repo.register_coupon_use(order['coupon_code'])

        # Walk the order to its target status, then backdate it: create_order
        # stamps "now", but the chart needs orders spread over the week.
        for step in PATH_TO[target_status]:
            repo.update_status(order['_id'], step, note='Seeded history')

        db[ORDERS].update_one({'_id': order['_id']},
                              {'$set': {'created_at': placed_at, 'updated_at': placed_at,
                                        'seed_tag': seed_tag}})
        created += 1
        if not quiet:
            print('  order %-10s %-28s %-10s %s' % (
                order['order_code'], email, target_status,
                repo.format_vnd(order['total'])))

    return created


def _format_address(address):
    if not address:
        return 'Address not provided'
    return '%s, %s, %s' % (address.get('detail', ''), address.get('district', ''),
                           address.get('province', ''))


def seed(reset=False, quiet=False):
    db = get_db()

    if reset:
        for name in (ORDERS, COUPONS):
            db[name].delete_many({})
        print('Cleared orders and coupons.')

    ensure_sales_indexes(db)
    print('Sales indexes ready.')

    n_coupons = seed_coupons(db, quiet)
    n_orders = seed_orders(db, quiet)

    print('Coupons in place: %d. New orders created: %d. Orders total: %d.'
          % (n_coupons, n_orders, db[ORDERS].count_documents({})))

    if not quiet:
        kpis = repo.dashboard_kpis()
        print()
        print('Dashboard now shows:')
        print('  Total revenue      %s' % repo.format_vnd(kpis['total_revenue']))
        print('  Total orders       %d' % kpis['total_orders'])
        print('  Avg order value    %s' % repo.format_vnd(kpis['avg_order_value']))
        print('  Active promotions  %d' % kpis['active_promotions'])
        print()
        print('Admin pages: /admin/dashboard/  /admin/orders/  /admin/promotions/')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Seed the ElectroMart demo orders and promo codes')
    ap.add_argument('--reset', action='store_true', help='delete every order and coupon first')
    ap.add_argument('--quiet', action='store_true', help='do not print the per-row summary')
    seed(**vars(ap.parse_args()))
