"""Data access layer for the Storefront module.

This file holds the core idea of the project: every component category owns a
different set of technical specification fields, declared in the category's
`spec_template`. Both the filter panel and the MongoDB query are generated at
run time from that declaration, so adding a new category does not require any
code change.
"""
from datetime import datetime, timezone

from bson import ObjectId
from django.conf import settings
from django.utils.text import slugify
from pymongo import ReturnDocument

from .db import (
    BRANDS,
    CATEGORIES,
    PRODUCTS,
    STOCK_MOVEMENTS,
    NEWS,
    SETTINGS,
    get_db,
)

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

def _category_oid(value):
    if isinstance(value, ObjectId):
        return value

    if not value:
        return None

    try:
        return ObjectId(str(value))
    except Exception:
        return None


def validate_spec_template(spec_template):
    """
    Validate CV65 specification template.

    Each field key must be present and unique inside one category.
    """
    if spec_template is None:
        return []

    if not isinstance(spec_template, list):
        raise ValueError('spec_template must be a list.')

    cleaned = []
    seen_keys = set()

    for index, item in enumerate(spec_template):
        if not isinstance(item, dict):
            raise ValueError(
                f'Specification field #{index + 1} is invalid.'
            )

        key = str(item.get('key', '')).strip()
        label = str(item.get('label', '')).strip()

        if not key:
            raise ValueError(
                f'Specification field #{index + 1} must have a key.'
            )

        if not label:
            raise ValueError(
                f'Specification field "{key}" must have a label.'
            )

        if key in seen_keys:
            raise ValueError(
                f'Duplicate specification key: {key}'
            )

        seen_keys.add(key)

        allowed_values = item.get('allowed_values', [])

        if not isinstance(allowed_values, list):
            allowed_values = []

        cleaned.append({
            'key': key,
            'label': label,
            'data_type': str(
                item.get('data_type', 'text')
            ).strip() or 'text',
            'unit': str(
                item.get('unit', '')
            ).strip(),
            'allowed_values': allowed_values,
            'is_filterable': bool(
                item.get('is_filterable', True)
            ),
            'display_order': int(
                item.get('display_order', index + 1)
            ),
        })

    return cleaned


def admin_list_categories():
    """
    Return every category, including hidden categories.
    Used by the admin TreeView.
    """
    return list(
        get_db()[CATEGORIES]
        .find({})
        .sort([
            ('display_order', 1),
            ('name', 1),
        ])
    )


def admin_get_category(category_id):
    oid = _category_oid(category_id)

    if not oid:
        return None

    return get_db()[CATEGORIES].find_one({
        '_id': oid
    })


def create_category(
    name,
    slug,
    parent_id=None,
    icon='',
    description='',
    display_order=0,
    spec_template=None,
):
    db = get_db()

    name = str(name or '').strip()
    slug = str(slug or '').strip()

    if not name:
        raise ValueError('Category name is required.')

    if not slug:
        raise ValueError('Category slug is required.')

    if db[CATEGORIES].find_one({'slug': slug}):
        raise ValueError(
            f'Category slug "{slug}" already exists.'
        )

    parent_oid = _category_oid(parent_id)

    ancestors = []
    level = 0

    if parent_id:
        if not parent_oid:
            raise ValueError('Invalid parent category.')

        parent = db[CATEGORIES].find_one({
            '_id': parent_oid
        })

        if not parent:
            raise ValueError(
                'Parent category does not exist.'
            )

        ancestors = (
            list(parent.get('ancestors', []))
            + [parent['_id']]
        )

        level = len(ancestors)

    clean_template = validate_spec_template(
        spec_template or []
    )

    doc = {
        'name': name,
        'slug': slug,
        'parent_id': parent_oid,
        'ancestors': ancestors,
        'level': level,
        'icon': str(icon or '').strip(),
        'description': str(description or '').strip(),
        'display_order': int(display_order or 0),
        'is_hidden': False,
        'spec_template': clean_template,
    }

    result = db[CATEGORIES].insert_one(doc)

    return db[CATEGORIES].find_one({
        '_id': result.inserted_id
    })


def update_category(
    category_id,
    name,
    slug,
    parent_id=None,
    icon='',
    description='',
    display_order=0,
    spec_template=None,
):
    db = get_db()

    oid = _category_oid(category_id)

    if not oid:
        raise ValueError('Invalid category id.')

    category = db[CATEGORIES].find_one({
        '_id': oid
    })

    if not category:
        raise ValueError('Category does not exist.')

    name = str(name or '').strip()
    slug = str(slug or '').strip()

    if not name:
        raise ValueError('Category name is required.')

    if not slug:
        raise ValueError('Category slug is required.')

    duplicate_slug = db[CATEGORIES].find_one({
        'slug': slug,
        '_id': {'$ne': oid},
    })

    if duplicate_slug:
        raise ValueError(
            f'Category slug "{slug}" already exists.'
        )

    parent_oid = _category_oid(parent_id)

    new_ancestors = []

    if parent_id:
        if not parent_oid:
            raise ValueError('Invalid parent category.')

        if parent_oid == oid:
            raise ValueError(
                'A category cannot be its own parent.'
            )

        parent = db[CATEGORIES].find_one({
            '_id': parent_oid
        })

        if not parent:
            raise ValueError(
                'Parent category does not exist.'
            )

        # Prevent A -> child B -> parent back to A cycle.
        if oid in parent.get('ancestors', []):
            raise ValueError(
                'Cannot move a category under its descendant.'
            )

        new_ancestors = (
            list(parent.get('ancestors', []))
            + [parent['_id']]
        )

    clean_template = validate_spec_template(
        spec_template or []
    )

    db[CATEGORIES].update_one(
        {'_id': oid},
        {
            '$set': {
                'name': name,
                'slug': slug,
                'parent_id': parent_oid,
                'ancestors': new_ancestors,
                'level': len(new_ancestors),
                'icon': str(icon or '').strip(),
                'description': str(
                    description or ''
                ).strip(),
                'display_order': int(
                    display_order or 0
                ),
                'spec_template': clean_template,
            }
        },
    )

    # CV65:
    # If the category changes parent, all descendants must
    # receive the new ancestors path too.
    descendants = list(
        db[CATEGORIES].find({
            'ancestors': oid
        })
    )

    for child in descendants:
        old_path = list(
            child.get('ancestors', [])
        )

        try:
            own_index = old_path.index(oid)
        except ValueError:
            continue

        relative_path = old_path[
            own_index + 1:
        ]

        child_ancestors = (
            new_ancestors
            + [oid]
            + relative_path
        )

        db[CATEGORIES].update_one(
            {'_id': child['_id']},
            {
                '$set': {
                    'ancestors': child_ancestors,
                    'level': len(child_ancestors),
                }
            },
        )

    return db[CATEGORIES].find_one({
        '_id': oid
    })


def set_category_hidden(category_id, hidden=True):
    """
    CV65:
    Hiding a category also hides every descendant.

    Unhiding only unhides the selected category so that an
    intentionally-hidden child is not accidentally restored.
    """
    db = get_db()

    oid = _category_oid(category_id)

    if not oid:
        raise ValueError('Invalid category id.')

    if not db[CATEGORIES].find_one({'_id': oid}):
        raise ValueError('Category does not exist.')

    hidden = bool(hidden)

    if hidden:
        result = db[CATEGORIES].update_many(
            {
                '$or': [
                    {'_id': oid},
                    {'ancestors': oid},
                ]
            },
            {
                '$set': {
                    'is_hidden': True
                }
            },
        )
    else:
        result = db[CATEGORIES].update_one(
            {'_id': oid},
            {
                '$set': {
                    'is_hidden': False
                }
            },
        )

    return result.modified_count

def delete_category(category_id):
    db = get_db()

    oid = _category_oid(category_id)

    if not oid:
        raise ValueError('Invalid category id.')

    category = db[CATEGORIES].find_one({
        '_id': oid
    })

    if not category:
        raise ValueError('Category does not exist.')

    # Không xóa khi còn category con / descendant.
    child = db[CATEGORIES].find_one(
        {'ancestors': oid},
        {'_id': 1, 'name': 1},
    )

    if child:
        raise ValueError(
            'Cannot delete this category because it has child categories.'
        )

    # Không xóa khi product vẫn đang tham chiếu category.
    product = db[PRODUCTS].find_one(
        {'category_id': oid},
        {'_id': 1, 'name': 1},
    )

    if product:
        raise ValueError(
            'Cannot delete this category because it contains products.'
        )

    result = db[CATEGORIES].delete_one({
        '_id': oid
    })

    if result.deleted_count != 1:
        raise ValueError('Category could not be deleted.')

    return True

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


# --------------------------------------------------------- admin products (CV66)
def _product_oid(value):
    if isinstance(value, ObjectId):
        return value
    if not value:
        return None
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def admin_list_brands():
    """Return all brands for the Admin Product form."""
    return list(get_db()[BRANDS].find({}).sort('name', 1))


def admin_list_products():
    """Return every product, including hidden products, for admin management."""
    return list(
        get_db()[PRODUCTS]
        .find({})
        .sort([('created_at', -1), ('name', 1)])
    )


def admin_get_product(product_id):
    oid = _product_oid(product_id)
    if not oid:
        return None
    return get_db()[PRODUCTS].find_one({'_id': oid})


def _clean_number(value, field_label):
    if value is None or value == '':
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_label} must be a number.')
    return int(number) if number.is_integer() else number


def _clean_boolean(value, field_label):
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in ('1', 'true', 'yes', 'on'):
        return True
    if raw in ('0', 'false', 'no', 'off'):
        return False
    raise ValueError(f'{field_label} must be true or false.')


def validate_product_specifications(category, specifications):
    """Validate product specification values against the category spec_template.

    Unknown keys are rejected. Blank values are omitted. Number/boolean/select
    fields are converted and validated according to the declaration created in
    CV65; text fields are stored as trimmed strings.
    """
    if specifications is None:
        specifications = {}
    if not isinstance(specifications, dict):
        raise ValueError('Specifications must be an object.')

    template = category.get('spec_template', []) if category else []
    by_key = {str(field.get('key')): field for field in template if field.get('key')}

    unknown = [key for key in specifications if key not in by_key]
    if unknown:
        raise ValueError(
            'Unknown specification field(s): ' + ', '.join(sorted(unknown))
        )

    cleaned = {}
    for key, raw_value in specifications.items():
        field = by_key[key]
        label = field.get('label') or key
        data_type = str(field.get('data_type', 'text')).strip().lower()

        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            continue

        if data_type == 'number':
            cleaned[key] = _clean_number(raw_value, label)
        elif data_type == 'boolean':
            cleaned[key] = _clean_boolean(raw_value, label)
        elif data_type == 'select':
            value = str(raw_value).strip()
            allowed = [str(item) for item in (field.get('allowed_values') or [])]
            if allowed and value not in allowed:
                raise ValueError(
                    f'{label} must be one of: {", ".join(allowed)}.'
                )
            cleaned[key] = value
        else:
            cleaned[key] = str(raw_value).strip()

    return cleaned


def _resolve_product_category(category_id):
    oid = _category_oid(category_id)
    if not oid:
        raise ValueError('Invalid product category.')
    category = get_db()[CATEGORIES].find_one({'_id': oid})
    if not category:
        raise ValueError('Product category does not exist.')
    return category


def _resolve_product_brand(brand_id):
    if not brand_id:
        return None
    oid = _category_oid(brand_id)
    if not oid:
        raise ValueError('Invalid product brand.')
    brand = get_db()[BRANDS].find_one({'_id': oid})
    if not brand:
        raise ValueError('Product brand does not exist.')
    return brand


def _clean_product_identity(name, part_number, slug=None):
    name = str(name or '').strip()
    part_number = str(part_number or '').strip()
    product_slug = slugify(str(slug or '').strip() or name)

    if not name:
        raise ValueError('Product name is required.')
    if not part_number:
        raise ValueError('Product SKU is required.')
    if not product_slug:
        raise ValueError('Product slug is required.')

    return name, part_number, product_slug


def create_product(
    name,
    part_number,
    category_id,
    brand_id=None,
    min_price=0,
    description='',
    specifications=None,
    slug=None,
    is_hidden=False,
    images=None,
    datasheet_url='',
):
    """Create a CV66 product while keeping the storefront schema intact."""
    db = get_db()
    name, part_number, product_slug = _clean_product_identity(
        name, part_number, slug
    )
    category = _resolve_product_category(category_id)
    brand = _resolve_product_brand(brand_id)
    price = _clean_number(min_price, 'Base price')
    price = 0 if price is None else price
    if price < 0:
        raise ValueError('Base price cannot be negative.')

    if db[PRODUCTS].find_one({'slug': product_slug}):
        raise ValueError(f'Product slug "{product_slug}" already exists.')
    if db[PRODUCTS].find_one({'part_number': part_number}):
        raise ValueError(f'Product SKU "{part_number}" already exists.')

    clean_specs = validate_product_specifications(category, specifications)
    now = datetime.now(timezone.utc)

    doc = {
        'name': name,
        'slug': product_slug,
        'part_number': part_number,
        'category_id': category['_id'],
        'brand_id': brand['_id'] if brand else None,
        'description': str(description or '').strip(),
        'min_price': price,
        'list_price': price,
        'specifications': clean_specs,
        'variants': [],
        'images': list(images or []),
        'datasheet_url': str(datasheet_url or ''),
        'total_stock': 0,
        'sold_count': 0,
        'avg_rating': 0,
        'rating_count': 0,
        'is_featured': False,
        'is_hidden': bool(is_hidden),
        'created_at': now,
        'updated_at': now,
    }

    result = db[PRODUCTS].insert_one(doc)
    return db[PRODUCTS].find_one({'_id': result.inserted_id})


def update_product(
    product_id,
    name,
    part_number,
    category_id,
    brand_id=None,
    min_price=0,
    description='',
    specifications=None,
    slug=None,
    is_hidden=None,
    images=None,
    datasheet_url=None,
):
    """Update editable CV66 product fields without replacing unrelated data."""
    db = get_db()
    oid = _product_oid(product_id)
    if not oid:
        raise ValueError('Invalid product id.')

    current = db[PRODUCTS].find_one({'_id': oid})
    if not current:
        raise ValueError('Product does not exist.')

    name, part_number, product_slug = _clean_product_identity(
        name, part_number, slug or current.get('slug')
    )
    category = _resolve_product_category(category_id)
    brand = _resolve_product_brand(brand_id)
    price = _clean_number(min_price, 'Base price')
    price = 0 if price is None else price
    if price < 0:
        raise ValueError('Base price cannot be negative.')

    duplicate_slug = db[PRODUCTS].find_one({
        'slug': product_slug,
        '_id': {'$ne': oid},
    })
    if duplicate_slug:
        raise ValueError(f'Product slug "{product_slug}" already exists.')

    duplicate_sku = db[PRODUCTS].find_one({
        'part_number': part_number,
        '_id': {'$ne': oid},
    })
    if duplicate_sku:
        raise ValueError(f'Product SKU "{part_number}" already exists.')

    clean_specs = validate_product_specifications(category, specifications)

    changes = {
        'name': name,
        'slug': product_slug,
        'part_number': part_number,
        'category_id': category['_id'],
        'brand_id': brand['_id'] if brand else None,
        'description': str(description or '').strip(),
        'min_price': price,
        'specifications': clean_specs,
        'updated_at': datetime.now(timezone.utc),
    }
    if 'list_price' not in current:
        changes['list_price'] = price
    if is_hidden is not None:
        changes['is_hidden'] = bool(is_hidden)
    if images is not None:
        changes['images'] = list(images)
    if datasheet_url is not None:
        changes['datasheet_url'] = str(datasheet_url or '')

    db[PRODUCTS].update_one({'_id': oid}, {'$set': changes})
    return db[PRODUCTS].find_one({'_id': oid})



def _clean_nonnegative_number(value, field_label, required=True):
    number = _clean_number(value, field_label)
    if number is None:
        if required:
            raise ValueError(f'{field_label} is required.')
        return None
    if number < 0:
        raise ValueError(f'{field_label} cannot be negative.')
    return number


def _clean_nonnegative_int(value, field_label, required=True):
    number = _clean_nonnegative_number(value, field_label, required=required)
    if number is None:
        return None
    if isinstance(number, float) and not number.is_integer():
        raise ValueError(f'{field_label} must be a whole number.')
    return int(number)


def validate_product_variants(variants):
    """Validate CV66 variants and tier-pricing before MongoDB is updated."""
    if variants is None:
        return []
    if not isinstance(variants, list):
        raise ValueError('Variants must be a list.')

    cleaned = []
    seen_skus = set()

    for index, item in enumerate(variants, start=1):
        if not isinstance(item, dict):
            raise ValueError(f'Variant #{index} is invalid.')

        sku = str(item.get('sku', '')).strip()
        option_name = str(
            item.get('option_name', item.get('name', ''))
        ).strip()

        if not sku:
            raise ValueError(f'Variant #{index} SKU is required.')
        if sku in seen_skus:
            raise ValueError(f'Duplicate variant SKU: {sku}')
        seen_skus.add(sku)

        if not option_name:
            raise ValueError(f'Variant "{sku}" name is required.')

        retail_price = _clean_nonnegative_number(
            item.get('retail_price', item.get('price')),
            f'Variant "{sku}" price',
        )

        list_price = _clean_nonnegative_number(
            item.get('list_price', retail_price),
            f'Variant "{sku}" list price',
        )

        stock_qty = _clean_nonnegative_int(
            item.get('stock_qty', item.get('stock', 0)),
            f'Variant "{sku}" stock',
        )

        raw_active = item.get('is_active')
        if raw_active is None:
            raw_active = str(item.get('status', 'active')).lower() != 'inactive'
        is_active = _clean_boolean(raw_active, f'Variant "{sku}" active status')

        raw_tiers = item.get('price_tiers') or []
        if not isinstance(raw_tiers, list):
            raise ValueError(f'Variant "{sku}" price tiers must be a list.')

        price_tiers = []
        seen_min_qty = set()

        for tier_index, tier in enumerate(raw_tiers, start=1):
            if not isinstance(tier, dict):
                raise ValueError(
                    f'Variant "{sku}" tier #{tier_index} is invalid.'
                )

            min_qty = _clean_nonnegative_int(
                tier.get('min_qty'),
                f'Variant "{sku}" tier #{tier_index} minimum quantity',
            )
            if min_qty < 1:
                raise ValueError(
                    f'Variant "{sku}" tier #{tier_index} minimum quantity '
                    'must be at least 1.'
                )
            if min_qty in seen_min_qty:
                raise ValueError(
                    f'Variant "{sku}" has duplicate minimum quantity {min_qty}.'
                )
            seen_min_qty.add(min_qty)

            tier_price = _clean_nonnegative_number(
                tier.get('price'),
                f'Variant "{sku}" tier #{tier_index} price',
            )

            price_tiers.append({
                'min_qty': min_qty,
                'price': tier_price,
            })

        price_tiers.sort(key=lambda row: row['min_qty'])

        variant = {
            'sku': sku,
            'option_name': option_name,
            'retail_price': retail_price,
            'list_price': list_price,
            'price_tiers': price_tiers,
            'stock_qty': stock_qty,
            'is_active': is_active,
        }

        # Preserve inventory fields already used by seeded documents when present.
        if 'reorder_level' in item:
            variant['reorder_level'] = _clean_nonnegative_int(
                item.get('reorder_level', 0),
                f'Variant "{sku}" reorder level',
            )
        if 'warehouse_location' in item:
            variant['warehouse_location'] = str(
                item.get('warehouse_location') or ''
            ).strip()

        cleaned.append(variant)

    return cleaned


def set_product_variants(product_id, variants):
    """Replace one product's variant array atomically and refresh stock/price summary."""
    db = get_db()
    oid = _product_oid(product_id)
    if not oid:
        raise ValueError('Invalid product id.')

    current = db[PRODUCTS].find_one({'_id': oid})
    if not current:
        raise ValueError('Product does not exist.')

    clean_variants = validate_product_variants(variants)
    total_stock = sum(item.get('stock_qty', 0) for item in clean_variants)

    changes = {
        'variants': clean_variants,
        'total_stock': total_stock,
        'updated_at': datetime.now(timezone.utc),
    }

    active_prices = [
        item['retail_price']
        for item in clean_variants
        if item.get('is_active', True)
    ]
    if not active_prices:
        active_prices = [
            item['retail_price']
            for item in clean_variants
        ]

    if active_prices:
        changes['min_price'] = min(active_prices)

    db[PRODUCTS].update_one(
        {'_id': oid},
        {'$set': changes},
    )

    return db[PRODUCTS].find_one({'_id': oid})

def set_product_hidden(product_id, hidden=True):
    """CV66 uses hide/unhide instead of deleting product documents."""
    db = get_db()
    oid = _product_oid(product_id)
    if not oid:
        raise ValueError('Invalid product id.')
    if not db[PRODUCTS].find_one({'_id': oid}, {'_id': 1}):
        raise ValueError('Product does not exist.')

    db[PRODUCTS].update_one(
        {'_id': oid},
        {'$set': {
            'is_hidden': bool(hidden),
            'updated_at': datetime.now(timezone.utc),
        }},
    )
    return db[PRODUCTS].find_one({'_id': oid})


# -------------------------------------------------------- admin inventory (CV67)
def _inventory_status(stock_qty, reorder_level):
    stock_qty = int(stock_qty or 0)
    reorder_level = int(reorder_level or 0)

    if stock_qty <= 0:
        return 'out'
    if stock_qty <= reorder_level:
        return 'low'
    return 'in'


def admin_inventory_items():
    """Flatten product variants into SKU-level inventory rows for Admin CV67."""
    rows = []

    products = get_db()[PRODUCTS].find({}).sort([
        ('name', 1),
        ('part_number', 1),
    ])

    for product in products:
        for variant in product.get('variants', []) or []:
            sku = str(variant.get('sku', '')).strip()
            if not sku:
                continue

            stock_qty = int(variant.get('stock_qty', 0) or 0)
            reorder_level = int(variant.get('reorder_level', 0) or 0)

            rows.append({
                'product_id': product['_id'],
                'product_name': product.get('name', ''),
                'product_part_number': product.get('part_number', ''),
                'product_hidden': bool(product.get('is_hidden', False)),
                'sku': sku,
                'variant_name': variant.get('option_name', '') or 'Standard',
                'stock_qty': stock_qty,
                'reorder_level': reorder_level,
                'warehouse_location': str(
                    variant.get('warehouse_location', '') or ''
                ),
                'status': _inventory_status(stock_qty, reorder_level),
            })

    return rows


def admin_low_stock_items():
    """MongoDB query for SKUs at/below reorder level, including out-of-stock."""
    pipeline = [
        {'$unwind': '$variants'},
        {
            '$match': {
                '$expr': {
                    '$lte': [
                        {'$ifNull': ['$variants.stock_qty', 0]},
                        {'$ifNull': ['$variants.reorder_level', 0]},
                    ]
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'product_id': '$_id',
                'product_name': '$name',
                'product_hidden': '$is_hidden',
                'sku': '$variants.sku',
                'variant_name': '$variants.option_name',
                'stock_qty': {'$ifNull': ['$variants.stock_qty', 0]},
                'reorder_level': {
                    '$ifNull': ['$variants.reorder_level', 0]
                },
                'warehouse_location': {
                    '$ifNull': ['$variants.warehouse_location', '']
                },
            }
        },
        {'$sort': {'stock_qty': 1, 'product_name': 1, 'sku': 1}},
    ]

    rows = list(get_db()[PRODUCTS].aggregate(pipeline))

    for row in rows:
        row['status'] = _inventory_status(
            row.get('stock_qty', 0),
            row.get('reorder_level', 0),
        )

    return rows


def admin_inventory_movements(sku=None, limit=100):
    """Return newest CV67 stock movements, optionally filtered by SKU."""
    query = {}

    sku = str(sku or '').strip()
    if sku:
        query['sku'] = sku

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, 500))

    return list(
        get_db()[STOCK_MOVEMENTS]
        .find(query)
        .sort('created_at', -1)
        .limit(limit)
    )


def _find_inventory_variant(product, sku):
    sku = str(sku or '').strip()

    for index, variant in enumerate(product.get('variants', []) or []):
        if str(variant.get('sku', '')).strip() == sku:
            return index, variant

    return None, None


def apply_inventory_movement(
    product_id,
    sku,
    movement_type,
    quantity,
    reason,
    reorder_level=None,
    warehouse_location=None,
):
    """Apply stock IN/OUT/ADJUST and record one stock_movements document.

    IN / OUT expect a positive quantity.
    ADJUST accepts a signed integer, so +5 and -3 are both valid.
    The product's total_stock is adjusted in the same product update.
    """
    db = get_db()

    oid = _product_oid(product_id)
    if not oid:
        raise ValueError('Invalid product id.')

    sku = str(sku or '').strip()
    if not sku:
        raise ValueError('SKU is required.')

    movement_type = str(movement_type or '').strip().upper()
    if movement_type not in ('IN', 'OUT', 'ADJUST'):
        raise ValueError('Movement type must be IN, OUT or ADJUST.')

    reason = str(reason or '').strip()
    if not reason:
        raise ValueError('Reason is required.')

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise ValueError('Quantity must be a whole number.')

    if movement_type in ('IN', 'OUT') and quantity <= 0:
        raise ValueError('Quantity must be greater than 0.')

    if movement_type == 'ADJUST' and quantity == 0:
        raise ValueError('Adjustment quantity cannot be 0.')

    delta = quantity
    if movement_type == 'OUT':
        delta = -quantity

    product = db[PRODUCTS].find_one({'_id': oid})
    if not product:
        raise ValueError('Product does not exist.')

    _, variant = _find_inventory_variant(product, sku)
    if not variant:
        raise ValueError('Variant SKU does not exist on this product.')

    stock_before = int(variant.get('stock_qty', 0) or 0)
    stock_after = stock_before + delta

    if stock_after < 0:
        raise ValueError(
            f'Insufficient stock. Current stock for "{sku}" is {stock_before}.'
        )

    current_reorder = int(variant.get('reorder_level', 0) or 0)
    if reorder_level in (None, ''):
        clean_reorder = current_reorder
    else:
        clean_reorder = _clean_nonnegative_int(
            reorder_level,
            'Reorder level',
        )

    current_warehouse = str(
        variant.get('warehouse_location', '') or ''
    )
    clean_warehouse = (
        current_warehouse
        if warehouse_location is None
        else str(warehouse_location or '').strip()
    )

    now = datetime.now(timezone.utc)

    # Optimistic condition on the current stock prevents silent lost updates.
    result = db[PRODUCTS].update_one(
        {
            '_id': oid,
            'variants': {
                '$elemMatch': {
                    'sku': sku,
                    'stock_qty': stock_before,
                }
            },
        },
        {
            '$set': {
                'variants.$.stock_qty': stock_after,
                'variants.$.reorder_level': clean_reorder,
                'variants.$.warehouse_location': clean_warehouse,
                'updated_at': now,
            },
            '$inc': {
                'total_stock': delta,
            },
        },
    )

    if result.modified_count != 1:
        raise ValueError(
            'Stock changed while you were editing. Reload inventory and try again.'
        )

    movement = {
        'product_id': oid,
        'product_name': product.get('name', ''),
        'sku': sku,
        'variant_name': variant.get('option_name', '') or 'Standard',
        'type': movement_type,
        'quantity': delta,
        'reason': reason,
        'stock_before': stock_before,
        'stock_after': stock_after,
        'reorder_level': clean_reorder,
        'warehouse_location': clean_warehouse,
        'created_at': now,
    }

    try:
        movement_id = db[STOCK_MOVEMENTS].insert_one(movement).inserted_id
    except Exception:
        # Best-effort compensation if the history write fails.
        db[PRODUCTS].update_one(
            {
                '_id': oid,
                'variants': {
                    '$elemMatch': {
                        'sku': sku,
                        'stock_qty': stock_after,
                    }
                },
            },
            {
                '$set': {
                    'variants.$.stock_qty': stock_before,
                    'variants.$.reorder_level': current_reorder,
                    'variants.$.warehouse_location': current_warehouse,
                    'updated_at': datetime.now(timezone.utc),
                },
                '$inc': {
                    'total_stock': -delta,
                },
            },
        )
        raise

    movement['_id'] = movement_id

    updated_product = db[PRODUCTS].find_one({'_id': oid})
    _, updated_variant = _find_inventory_variant(updated_product, sku)

    item = {
        'product_id': oid,
        'product_name': updated_product.get('name', ''),
        'product_part_number': updated_product.get('part_number', ''),
        'product_hidden': bool(updated_product.get('is_hidden', False)),
        'sku': sku,
        'variant_name': updated_variant.get('option_name', '') or 'Standard',
        'stock_qty': int(updated_variant.get('stock_qty', 0) or 0),
        'reorder_level': int(updated_variant.get('reorder_level', 0) or 0),
        'warehouse_location': str(
            updated_variant.get('warehouse_location', '') or ''
        ),
    }
    item['status'] = _inventory_status(
        item['stock_qty'],
        item['reorder_level'],
    )

    return item, movement


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

# ============================================================
# CV70 - News / FAQ content
# ============================================================

NEWS_TYPES = {
    'product-news': 'Product News',
    'announcement': 'Announcement',
    'technical-guide': 'Technical Guide',
}


def _news_oid(value):
    if isinstance(value, ObjectId):
        return value
    if not value:
        return None
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _normalize_news_type(value):
    raw = str(value or '').strip().lower()
    if raw in NEWS_TYPES:
        return raw

    for key, label in NEWS_TYPES.items():
        if raw == label.lower():
            return key

    raise ValueError('Invalid news type.')


def _clean_news_fields(title, news_type, summary, content, slug=None):
    title = str(title or '').strip()
    summary = str(summary or '').strip()
    content = str(content or '').strip()
    news_type = _normalize_news_type(news_type)
    news_slug = slugify(str(slug or '').strip() or title)

    if not title:
        raise ValueError('News title is required.')
    if not news_slug:
        raise ValueError('News slug is required.')
    if not summary:
        raise ValueError('News summary is required.')
    if not content:
        raise ValueError('News content is required.')

    return title, news_type, summary, content, news_slug


def create_news(
    title,
    news_type,
    summary,
    content,
    publish_at=None,
    slug=None,
    created_by=None,
    is_hidden=False,
):
    """Create one news article.

    Scheduled publishing does not need a background job: storefront queries
    only return articles whose ``publish_at`` is less than or equal to now.
    """
    db = get_db()
    title, news_type, summary, content, news_slug = _clean_news_fields(
        title,
        news_type,
        summary,
        content,
        slug,
    )

    if db[NEWS].find_one({'slug': news_slug}):
        raise ValueError(f'News slug "{news_slug}" already exists.')

    now = datetime.now(timezone.utc)
    publish_at = publish_at or now
    if not isinstance(publish_at, datetime):
        raise ValueError('publish_at must be a datetime.')
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=timezone.utc)

    created_by_oid = _news_oid(created_by) if created_by else None

    doc = {
        'title': title,
        'slug': news_slug,
        'type': news_type,
        'summary': summary,
        'content': content,
        'publish_at': publish_at,
        'created_by': created_by_oid,
        'is_hidden': bool(is_hidden),
        'created_at': now,
        'updated_at': now,
    }

    result = db[NEWS].insert_one(doc)
    return db[NEWS].find_one({'_id': result.inserted_id})


def list_public_news(news_type=None):
    query = {
        'is_hidden': False,
        'publish_at': {'$lte': datetime.now(timezone.utc)},
    }

    if news_type and str(news_type).strip().lower() != 'all':
        query['type'] = _normalize_news_type(news_type)

    return list(
        get_db()[NEWS]
        .find(query)
        .sort([('publish_at', -1), ('created_at', -1)])
    )


def get_public_news(slug):
    return get_db()[NEWS].find_one({
        'slug': str(slug or '').strip(),
        'is_hidden': False,
        'publish_at': {'$lte': datetime.now(timezone.utc)},
    })


def admin_list_news():
    return list(
        get_db()[NEWS]
        .find({})
        .sort([('publish_at', -1), ('created_at', -1)])
    )


def admin_get_news(news_id):
    oid = _news_oid(news_id)
    if not oid:
        return None
    return get_db()[NEWS].find_one({'_id': oid})


def update_news(
    news_id,
    title,
    news_type,
    summary,
    content,
    publish_at,
    slug=None,
    is_hidden=None,
):
    db = get_db()
    oid = _news_oid(news_id)
    if not oid:
        raise ValueError('Invalid news id.')

    current = db[NEWS].find_one({'_id': oid})
    if not current:
        raise ValueError('News article does not exist.')

    title, news_type, summary, content, news_slug = _clean_news_fields(
        title,
        news_type,
        summary,
        content,
        slug or current.get('slug'),
    )

    duplicate = db[NEWS].find_one({
        'slug': news_slug,
        '_id': {'$ne': oid},
    })
    if duplicate:
        raise ValueError(f'News slug "{news_slug}" already exists.')

    if not isinstance(publish_at, datetime):
        raise ValueError('publish_at must be a datetime.')
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=timezone.utc)

    fields = {
        'title': title,
        'slug': news_slug,
        'type': news_type,
        'summary': summary,
        'content': content,
        'publish_at': publish_at,
        'updated_at': datetime.now(timezone.utc),
    }
    if is_hidden is not None:
        fields['is_hidden'] = bool(is_hidden)

    db[NEWS].update_one({'_id': oid}, {'$set': fields})
    return db[NEWS].find_one({'_id': oid})


def set_news_hidden(news_id, hidden=True):
    oid = _news_oid(news_id)
    if not oid:
        raise ValueError('Invalid news id.')

    updated = get_db()[NEWS].find_one_and_update(
        {'_id': oid},
        {
            '$set': {
                'is_hidden': bool(hidden),
                'updated_at': datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise ValueError('News article does not exist.')
    return updated


def delete_news(news_id):
    oid = _news_oid(news_id)
    if not oid:
        raise ValueError('Invalid news id.')

    result = get_db()[NEWS].delete_one({'_id': oid})
    if result.deleted_count != 1:
        raise ValueError('News article does not exist.')
    return True


def get_setting(key, default=None):
    doc = get_db()[SETTINGS].find_one({'key': str(key or '').strip()})
    return doc.get('value', default) if doc else default


def set_setting(key, value):
    key = str(key or '').strip()
    if not key:
        raise ValueError('Setting key is required.')

    now = datetime.now(timezone.utc)
    get_db()[SETTINGS].update_one(
        {'key': key},
        {
            '$set': {
                'value': value,
                'updated_at': now,
            },
            '$setOnInsert': {
                'created_at': now,
            },
        },
        upsert=True,
    )
    return get_db()[SETTINGS].find_one({'key': key})


def get_faq_items(active_only=True):
    items = get_setting('faq', [])
    if not isinstance(items, list):
        return []

    cleaned = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if active_only and not item.get('is_active', True):
            continue

        question = str(item.get('question', '')).strip()
        answer = str(item.get('answer', '')).strip()
        if not question or not answer:
            continue

        cleaned.append({
            'question': question,
            'answer': answer,
            'display_order': int(item.get('display_order', index + 1)),
            'is_active': bool(item.get('is_active', True)),
        })

    cleaned.sort(key=lambda item: (item['display_order'], item['question'].lower()))
    return cleaned


def set_faq_items(items):
    if not isinstance(items, list):
        raise ValueError('FAQ items must be a list.')

    cleaned = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f'FAQ item #{index + 1} is invalid.')

        question = str(item.get('question', '')).strip()
        answer = str(item.get('answer', '')).strip()
        if not question:
            raise ValueError(f'FAQ item #{index + 1} requires a question.')
        if not answer:
            raise ValueError(f'FAQ item #{index + 1} requires an answer.')

        cleaned.append({
            'question': question,
            'answer': answer,
            'display_order': int(item.get('display_order', index + 1)),
            'is_active': bool(item.get('is_active', True)),
        })

    set_setting('faq', cleaned)
    return get_faq_items(active_only=False)

