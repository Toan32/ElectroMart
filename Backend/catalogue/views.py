"""Storefront views: home, category listing, product detail, search, compare, wishlist."""
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from . import repo

COMPARE_KEY = 'compare'
WISHLIST_KEY = 'wishlist'


def _int(value, default=1, low=1):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return n if n >= low else default


def _decorate(products):
    """Attach display-only fields: brand name, discount percentage, stock flag."""
    brands = repo.brand_map(products)
    for p in products:
        b = brands.get(p.get('brand_id'))
        p['brand_name'] = b['name'] if b else ''
        lp, mp = p.get('list_price') or 0, p.get('min_price') or 0
        p['discount_percent'] = round((lp - mp) * 100 / lp) if lp > mp else 0
        p['in_stock'] = (p.get('total_stock') or 0) > 0
    return products


def _querystring(params, **overrides):
    """Keep the current filters when changing page or sort order."""
    data = params.copy()
    for k, v in overrides.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    pairs = []
    for k in data:
        for v in data.getlist(k):
            if v != '':
                pairs.append((k, v))
    return urlencode(pairs)


def _page_range(page, total_pages, width=2):
    lo = max(1, page - width)
    hi = min(total_pages, page + width)
    return list(range(lo, hi + 1))


def _format_spec(v):
    if isinstance(v, bool):
        return 'Yes' if v else 'No'
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def home(request):
    blocks = repo.home_blocks()
    for key in blocks:
        _decorate(blocks[key])
    return render(request, 'home.html', {
        'featured': blocks['featured'],
        'bestseller': blocks['bestseller'],
        'newest': blocks['newest'],
        'page_title': 'ElectroMart - Genuine electronic components',
    })


def product_list(request, slug):
    cat = repo.get_category(slug)
    if not cat:
        raise Http404('Category not found')

    cat_ids = repo.category_and_descendants(cat)
    brands = repo.brands_of(cat_ids)
    params = request.GET

    query = repo.build_query(cat_ids, cat, params, brands)
    sort_key = params.get('sort', 'popular')
    page = _int(params.get('page'))

    items, total = repo.list_products(query, sort_key, page)
    _decorate(items)

    counts = repo.facet_counts(cat_ids, cat, params, brands)
    ranges = repo.numeric_ranges(cat_ids, cat)

    # Build the filter panel: one entry per field, with options and counts
    panel = []
    for f in repo.filterable_fields(cat):
        key, dtype = f['key'], f.get('data_type', 'text')
        entry = {'key': key, 'label': f['label'], 'unit': f.get('unit', ''),
                 'data_type': dtype}
        if dtype == 'number':
            lo, hi = ranges.get(key, (None, None))
            entry['range_min'] = lo
            entry['range_max'] = hi
            entry['value_min'] = params.get('spec_%s_min' % key, '')
            entry['value_max'] = params.get('spec_%s_max' % key, '')
        elif dtype == 'boolean':
            entry['checked'] = params.get('spec_%s' % key) == '1'
            entry['count'] = counts.get(key, {}).get(True, 0)
        else:
            chosen = set(params.getlist('spec_%s' % key))
            c = counts.get(key, {})
            values = f.get('allowed_values') or sorted(c.keys())
            entry['options'] = [{'value': v, 'count': c.get(v, 0), 'checked': v in chosen}
                                for v in values]
        panel.append(entry)

    chosen_brands = set(params.getlist('brand'))
    brand_options = [{'slug': b['slug'], 'name': b['name'],
                      'checked': b['slug'] in chosen_brands} for b in brands]

    total_pages = max(1, -(-total // settings.PAGE_SIZE))
    has_filter = any(k for k in params if k not in ('sort', 'page'))

    return render(request, 'product_list.html', {
        'category': cat,
        'products': items,
        'total': total,
        'panel': panel,
        'brand_options': brand_options,
        'sort_key': sort_key,
        'sort_labels': repo.SORT_LABELS,
        'page': page,
        'total_pages': total_pages,
        'page_range': _page_range(page, total_pages),
        'qs_base': _querystring(params, page=None),
        'qs_no_sort': _querystring(params, sort=None, page=None),
        'price_min': params.get('price_min', ''),
        'price_max': params.get('price_max', ''),
        'in_stock': params.get('in_stock') == '1',
        'has_filter': has_filter,
        'page_title': cat['name'] + ' - ElectroMart',
    })


def product_detail(request, slug):
    p = repo.get_product(slug)
    if not p:
        raise Http404('Product not found')
    _decorate([p])

    cat = repo.category_map([p]).get(p['category_id'])
    spec_rows = []
    if cat:
        for f in cat.get('spec_template', []):
            if f['key'] in p.get('specifications', {}):
                spec_rows.append({'label': f['label'],
                                  'value': _format_spec(p['specifications'][f['key']]),
                                  'unit': f.get('unit', '')})

    related = _decorate(repo.related_products(p))
    return render(request, 'product_detail.html', {
        'p': p,
        'category': cat,
        'spec_rows': spec_rows,
        'related': related,
        'in_compare': p['slug'] in request.session.get(COMPARE_KEY, []),
        'in_wishlist': p['slug'] in request.session.get(WISHLIST_KEY, []),
        'page_title': p['name'] + ' - ElectroMart',
    })


def search(request):
    q = (request.GET.get('q') or '').strip()
    page = _int(request.GET.get('page'))
    items, total = ([], 0)
    if q:
        items, total = repo.search_products(q, page, request.GET.get('sort', 'relevance'))
        _decorate(items)
    total_pages = max(1, -(-total // settings.PAGE_SIZE))
    return render(request, 'search.html', {
        'q': q,
        'products': items,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'page_range': _page_range(page, total_pages),
        'page_title': ('Search: %s' % q) if q else 'Search',
    })


def search_suggest(request):
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'items': []})
    return JsonResponse({'items': [{
        'name': i['name'],
        'part_number': i.get('part_number', ''),
        'price': i.get('min_price', 0),
        'url': '/product/%s/' % i['slug'],
    } for i in repo.suggest(q)]})


# ----------------------------------------------------------- compare & wishlist
def _toggle(request, key, slug, limit=None):
    lst = list(request.session.get(key, []))
    if slug in lst:
        lst.remove(slug)
        added = False
    else:
        if limit and len(lst) >= limit:
            return lst, False, True
        lst.append(slug)
        added = True
    request.session[key] = lst
    request.session.modified = True
    return lst, added, False


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def compare_toggle(request, slug):
    lst, added, full = _toggle(request, COMPARE_KEY, slug, settings.COMPARE_LIMIT)
    if _is_ajax(request):
        return JsonResponse({'count': len(lst), 'added': added, 'full': full,
                             'limit': settings.COMPARE_LIMIT})
    return redirect(request.META.get('HTTP_REFERER', '/'))


def wishlist_toggle(request, slug):
    lst, added, _ = _toggle(request, WISHLIST_KEY, slug)
    if _is_ajax(request):
        return JsonResponse({'count': len(lst), 'added': added})
    return redirect(request.META.get('HTTP_REFERER', '/'))


def compare(request):
    items = _decorate(repo.products_by_slugs(request.session.get(COMPARE_KEY, [])))

    # The comparison table is built from the union of the specification keys
    # of whichever products are currently selected.
    labels, rows = {}, []
    for cat in repo.category_map(items).values():
        for f in cat.get('spec_template', []):
            labels.setdefault(f['key'], f)
    for key, f in sorted(labels.items(), key=lambda kv: kv[1].get('display_order', 0)):
        values = [_format_spec(p.get('specifications', {}).get(key, '-')) for p in items]
        rows.append({'label': f['label'], 'unit': f.get('unit', ''), 'values': values,
                     'differs': len({str(v) for v in values}) > 1})
    return render(request, 'compare.html', {
        'products': items, 'rows': rows, 'page_title': 'Compare products'})


def compare_clear(request):
    request.session[COMPARE_KEY] = []
    return redirect('compare')


def wishlist(request):
    items = _decorate(repo.products_by_slugs(request.session.get(WISHLIST_KEY, [])))
    return render(request, 'wishlist.html',
                  {'products': items, 'page_title': 'Wishlist'})

def news(request):
    selected_type = request.GET.get('type', 'all')

    news_items = [
        {
            'title': 'ElectroMart launches new STM32 development kits',
            'type': 'Product News',
            'date': 'August 20, 2026',
            'summary': 'Explore the latest STM32 development boards now available at ElectroMart.',
            'image_text': 'STM32',
        },
        {
            'title': 'Scheduled system maintenance this weekend',
            'type': 'Announcement',
            'date': 'August 18, 2026',
            'summary': 'Some ElectroMart services may be temporarily unavailable during maintenance.',
            'image_text': 'NOTICE',
        },
        {
            'title': 'How to choose the right capacitor for your project',
            'type': 'Technical Guide',
            'date': 'August 15, 2026',
            'summary': 'A practical guide to capacitance, voltage rating, tolerance and capacitor types.',
            'image_text': 'GUIDE',
        },
        {
            'title': 'New sensor modules added to our catalogue',
            'type': 'Product News',
            'date': 'August 12, 2026',
            'summary': 'Discover newly added temperature, humidity, pressure and motion sensors.',
            'image_text': 'SENSOR',
        },
        {
            'title': 'Holiday shipping schedule update',
            'type': 'Announcement',
            'date': 'August 10, 2026',
            'summary': 'Important information about shipping and order processing during the holiday period.',
            'image_text': 'UPDATE',
        },
        {
            'title': 'Understanding resistor color codes',
            'type': 'Technical Guide',
            'date': 'August 8, 2026',
            'summary': 'Learn how to quickly identify resistor values using standard color bands.',
            'image_text': 'RESISTOR',
        },
    ]

    news_types = [
        'All',
        'Product News',
        'Announcement',
        'Technical Guide',
    ]

    if selected_type != 'all':
        filtered_items = [
            item for item in news_items
            if item['type'].lower().replace(' ', '-') == selected_type
        ]
    else:
        filtered_items = news_items

    return render(request, 'news.html', {
        'page_title': 'News - ElectroMart',
        'news_items': filtered_items,
        'news_types': news_types,
        'selected_type': selected_type,
    })

def feedback(request):
    return render(request, 'feedback.html', {
        'page_title': 'Feedback - ElectroMart',
    })

def faq(request):
    return render(request, 'faq.html', {
        'page_title': 'FAQ - ElectroMart',
    })

def admin_categories(request):
    return render(request, 'admin_categories.html', {
        'page_title': 'Manage Categories - ElectroMart'
    })

def admin_products(request):
    return render(request, 'admin_products.html', {
        'page_title': 'Manage Products - ElectroMart'
    })
    
def admin_inventory(request):
    return render(request, 'admin_inventory.html')