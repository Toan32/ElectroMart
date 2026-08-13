"""Data access layer for the Storefront module.

This file holds the core idea of the project: every component category owns a
different set of technical specification fields, declared in the category's
`spec_template`. Both the filter panel and the MongoDB query are generated at
run time from that declaration, so adding a new category does not require any
code change.
"""
from django.conf import settings

from .db import BRANDS, CATEGORIES, PRODUCTS, get_db

SORTS = {
    'popular': [('sold_count', -1)],
    'newest': [('created_at', -1)],
    'price_asc': [('min_price', 1)],
    'price_desc': [('min_price', -1)],
    'name': [('name', 1)],
    'rating': [('avg_rating', -1), ('rating_count', -1)],
}
SORT_LABELS = [
    ('popular', 'Best selling'),
    ('newest', 'Newest'),
    ('price_asc', 'Price: low to high'),
    ('price_desc', 'Price: high to low'),
    ('rating', 'Top rated'),
    ('name', 'Name A - Z'),
]


# ---------------------------------------------------------------- categories
def category_tree():
    """Two-level category tree used by the header and the home page menu."""
    db = get_db()
    cats = list(db[CATEGORIES].find({'is_hidden': False}).sort('display_order', 1))
    by_parent = {}
    for c in cats:
        by_parent.setdefault(c.get('parent_id'), []).append(c)
    roots = by_parent.get(None, [])
    for r in roots:
        r['children'] = by_parent.get(r['_id'], [])
    return roots


def get_category(slug):
    return get_db()[CATEGORIES].find_one({'slug': slug, 'is_hidden': False})


def category_and_descendants(cat):
    """Category id plus every descendant, so filtering a parent still returns rows."""
    db = get_db()
    ids = [cat['_id']]
    ids += [c['_id'] for c in db[CATEGORIES].find({'ancestors': cat['_id']}, {'_id': 1})]
    return ids


def brands_of(category_ids):
    db = get_db()
    ids = db[PRODUCTS].distinct('brand_id', {'category_id': {'$in': category_ids},
                                             'is_hidden': False})
    return list(db[BRANDS].find({'_id': {'$in': ids}}).sort('name', 1))


# ------------------------------------------------- building the filter query
def filterable_fields(cat):
    tpl = cat.get('spec_template', []) if cat else []
    return [f for f in tpl if f.get('is_filterable')]


def spec_conditions(cat, params):
    """Read the query string and return {key: mongo_condition} per spec field.

    Parameter convention:
        number  : spec_<key>_min / spec_<key>_max
        select  : spec_<key> (may repeat for multiple values)
        boolean : spec_<key>=1

    Parameters that are not declared in spec_template are ignored, so a visitor
    cannot inject arbitrary conditions into the query.
    """
    conds = {}
    for f in filterable_fields(cat):
        key, dtype = f['key'], f.get('data_type', 'text')
        path = 'specifications.%s' % key

        if dtype == 'number':
            lo = _as_float(params.get('spec_%s_min' % key))
            hi = _as_float(params.get('spec_%s_max' % key))
            rng = {}
            if lo is not None:
                rng['$gte'] = lo
            if hi is not None:
                rng['$lte'] = hi
            if rng:
                conds[key] = {path: rng}

        elif dtype == 'boolean':
            raw = params.get('spec_%s' % key)
            if raw in ('1', 'true', 'True'):
                conds[key] = {path: True}
            elif raw in ('0', 'false', 'False'):
                conds[key] = {path: False}

        else:  # text / select
            vals = [v for v in params.getlist('spec_%s' % key) if v]
            allowed = f.get('allowed_values') or []
            if allowed:
                vals = [v for v in vals if v in allowed]
            if vals:
                conds[key] = {path: {'$in': vals}}
    return conds


def _as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def base_match(category_ids, params, brands=None):
    """Shared conditions: category, visibility, price range, brand, stock."""
    m = {'category_id': {'$in': category_ids}, 'is_hidden': False}

    lo = _as_float(params.get('price_min'))
    hi = _as_float(params.get('price_max'))
    if lo is not None or hi is not None:
        rng = {}
        if lo is not None:
            rng['$gte'] = lo
        if hi is not None:
            rng['$lte'] = hi
        m['min_price'] = rng

    slugs = [s for s in params.getlist('brand') if s]
    if slugs and brands is not None:
        ids = [b['_id'] for b in brands if b['slug'] in slugs]
        if ids:
            m['brand_id'] = {'$in': ids}

    if params.get('in_stock') == '1':
        m['total_stock'] = {'$gt': 0}
    return m


def build_query(category_ids, cat, params, brands=None):
    q = base_match(category_ids, params, brands)
    for cond in spec_conditions(cat, params).values():
        q.update(cond)
    return q


# ----------------------------------------------------- listing + facet counts
def list_products(query, sort_key, page, page_size=None):
    page_size = page_size or settings.PAGE_SIZE
    db = get_db()
    sort = SORTS.get(sort_key) or SORTS['popular']
    total = db[PRODUCTS].count_documents(query)
    items = list(db[PRODUCTS].find(query)
                 .sort(sort)
                 .skip((page - 1) * page_size)
                 .limit(page_size))
    return items, total


def facet_counts(category_ids, cat, params, brands=None):
    """Count how many products remain for each option of each filter.

    For a given field the count applies every OTHER active condition but drops
    the condition of the field itself, so the visitor still sees the sibling
    options instead of only the one already selected. Everything runs in a
    single aggregate call through $facet, so one round trip to the database.
    """
    fields = filterable_fields(cat)
    if not fields:
        return {}

    base = base_match(category_ids, params, brands)
    conds = spec_conditions(cat, params)

    facets = {}
    for f in fields:
        key, dtype = f['key'], f.get('data_type', 'text')
        if dtype == 'number':
            continue  # numeric fields show a min-max range, not per-value counts
        m = dict(base)
        for other_key, cond in conds.items():
            if other_key != key:
                m.update(cond)
        facets['f_' + key] = [
            {'$match': m},
            {'$group': {'_id': '$specifications.%s' % key, 'n': {'$sum': 1}}},
        ]

    if not facets:
        return {}

    # The leading $match narrows the input before the pipeline branches out,
    # which keeps $facet cheap.
    pipeline = [{'$match': {'category_id': {'$in': category_ids}, 'is_hidden': False}},
                {'$facet': facets}]
    res = list(get_db()[PRODUCTS].aggregate(pipeline))
    if not res:
        return {}

    out = {}
    for name, rows in res[0].items():
        key = name[2:]
        out[key] = {r['_id']: r['n'] for r in rows if r['_id'] is not None}
    return out


def numeric_ranges(category_ids, cat):
    """Real min-max of every numeric field, used as placeholders in the inputs."""
    fields = [f for f in filterable_fields(cat) if f.get('data_type') == 'number']
    if not fields:
        return {}
    group = {'_id': None}
    for f in fields:
        group['min_' + f['key']] = {'$min': '$specifications.%s' % f['key']}
        group['max_' + f['key']] = {'$max': '$specifications.%s' % f['key']}
    rows = list(get_db()[PRODUCTS].aggregate([
        {'$match': {'category_id': {'$in': category_ids}, 'is_hidden': False}},
        {'$group': group},
    ]))
    if not rows:
        return {}
    r = rows[0]
    return {f['key']: (r.get('min_' + f['key']), r.get('max_' + f['key'])) for f in fields}


# -------------------------------------------------------------------- search
def search_products(keyword, page, sort_key='relevance', page_size=None):
    page_size = page_size or settings.PAGE_SIZE
    db = get_db()
    query = {'$text': {'$search': keyword}, 'is_hidden': False}
    total = db[PRODUCTS].count_documents(query)
    cur = db[PRODUCTS].find(query, {'score': {'$meta': 'textScore'}})
    if sort_key in SORTS:
        cur = cur.sort(SORTS[sort_key])
    else:
        cur = cur.sort([('score', {'$meta': 'textScore'})])
    items = list(cur.skip((page - 1) * page_size).limit(page_size))
    return items, total


def suggest(keyword, limit=8):
    """Type-ahead: prefix matches on name/part number first, then the text index."""
    db = get_db()
    rx = {'$regex': '^%s' % _escape_regex(keyword), '$options': 'i'}
    items = list(db[PRODUCTS].find(
        {'is_hidden': False, '$or': [{'name': rx}, {'part_number': rx}]},
        {'name': 1, 'slug': 1, 'part_number': 1, 'min_price': 1},
    ).limit(limit))
    if len(items) < limit:
        seen = {i['_id'] for i in items}
        more = db[PRODUCTS].find(
            {'$text': {'$search': keyword}, 'is_hidden': False},
            {'name': 1, 'slug': 1, 'part_number': 1, 'min_price': 1,
             'score': {'$meta': 'textScore'}},
        ).sort([('score', {'$meta': 'textScore'})]).limit(limit)
        for m in more:
            if m['_id'] not in seen:
                items.append(m)
            if len(items) >= limit:
                break
    return items


def _escape_regex(s):
    return ''.join('\\' + c if c in r'.^$*+?()[]{}|\\' else c for c in s)


# ------------------------------------------------------------------ products
def get_product(slug):
    return get_db()[PRODUCTS].find_one({'slug': slug, 'is_hidden': False})


def products_by_slugs(slugs):
    if not slugs:
        return []
    docs = {d['slug']: d for d in get_db()[PRODUCTS].find({'slug': {'$in': list(slugs)}})}
    return [docs[s] for s in slugs if s in docs]


def related_products(product, limit=5):
    return list(get_db()[PRODUCTS].find({
        'category_id': product['category_id'],
        '_id': {'$ne': product['_id']},
        'is_hidden': False,
    }).sort([('sold_count', -1)]).limit(limit))


def home_blocks():
    db = get_db()
    common = {'is_hidden': False}
    return {
        'featured': list(db[PRODUCTS].find({**common, 'is_featured': True})
                         .sort([('sold_count', -1)]).limit(10)),
        'bestseller': list(db[PRODUCTS].find(common)
                           .sort([('sold_count', -1)]).limit(10)),
        'newest': list(db[PRODUCTS].find(common)
                       .sort([('created_at', -1)]).limit(5)),
    }


def brand_map(products):
    ids = {p.get('brand_id') for p in products if p.get('brand_id')}
    if not ids:
        return {}
    return {b['_id']: b for b in get_db()[BRANDS].find({'_id': {'$in': list(ids)}})}


def category_map(products):
    ids = {p.get('category_id') for p in products if p.get('category_id')}
    if not ids:
        return {}
    return {c['_id']: c for c in get_db()[CATEGORIES].find({'_id': {'$in': list(ids)}})}
