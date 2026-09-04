"""Storefront views: home, category listing, product detail, search, compare, wishlist."""
import json
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from . import repo
from interaction import repo as interaction_repo

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
    reviews = interaction_repo.list_reviews(p['_id'])
    comments = interaction_repo.list_comments(p['_id'])

    questions = [
        comment for comment in comments
        if comment.get('parent_id') is None
    ]

    reply_map = {}

    for comment in comments:
        parent_id = comment.get('parent_id')

        if parent_id is not None:
            reply_map.setdefault(parent_id, []).append(comment)

    for question in questions:
        question['id'] = str(question['_id'])
        question['replies'] = reply_map.get(question['_id'], [])

    average_rating = (
        round(sum(r.get('rating', 0) for r in reviews) / len(reviews), 1)
        if reviews else 0
    )

    rating_distribution = []

    for star in range(5, 0, -1):
        count = sum(
            1 for r in reviews
            if int(r.get('rating', 0)) == star
        )

        percent = (
            round(count * 100 / len(reviews))
            if reviews else 0
        )

        rating_distribution.append({
            'star': star,
            'count': count,
            'percent': percent,
        })

    return render(request, 'product_detail.html', {
        'p': p,
        'category': cat,
        'spec_rows': spec_rows,
        'related': related,
        'reviews': reviews,
        'comments': comments,
        'questions': questions,
        'average_rating': average_rating,
        'rating_distribution': rating_distribution,
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

def _serialize_admin_category(category):
    return {
        'id': str(category['_id']),
        'name': category.get('name', ''),
        'slug': category.get('slug', ''),
        'parent_id': (
            str(category['parent_id'])
            if category.get('parent_id')
            else ''
        ),
        'ancestors': [
            str(item)
            for item in category.get('ancestors', [])
        ],
        'level': category.get('level', 0),
        'icon': category.get('icon', ''),
        'description': category.get('description', ''),
        'display_order': category.get('display_order', 0),
        'is_hidden': category.get('is_hidden', False),
        'spec_template': category.get('spec_template', []),
    }


def admin_categories_data(request):
    categories = repo.admin_list_categories()

    return JsonResponse({
        'categories': [
            _serialize_admin_category(category)
            for category in categories
        ],
        'count': len(categories),
    })

def admin_category_create(request):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        category = repo.create_category(
            name=request.POST.get('name'),
            slug=request.POST.get('slug'),
            parent_id=request.POST.get('parent_id') or None,
            spec_template=[],
        )

        return JsonResponse({
            'ok': True,
            'category': _serialize_admin_category(category),
        }, status=201)

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to create category.',
        }, status=500)

def admin_category_update(request, category_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        current = repo.admin_get_category(category_id)

        if not current:
            return JsonResponse({
                'ok': False,
                'error': 'Category does not exist.',
            }, status=404)

        category = repo.update_category(
            category_id=category_id,
            name=request.POST.get('name'),
            slug=request.POST.get('slug'),
            parent_id=request.POST.get('parent_id') or None,

            # Giữ nguyên các field CV65 chưa edit ở modal này
            icon=current.get('icon', ''),
            description=current.get('description', ''),
            display_order=current.get('display_order', 0),
            spec_template=current.get('spec_template', []),
        )

        return JsonResponse({
            'ok': True,
            'category': _serialize_admin_category(category),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to update category.',
        }, status=500)

def admin_category_hidden(request, category_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        hidden_value = (
            request.POST.get('hidden', 'true')
            .strip()
            .lower()
        )

        hidden = hidden_value in (
            '1',
            'true',
            'yes',
            'on',
        )

        repo.set_category_hidden(
            category_id,
            hidden=hidden,
        )

        category = repo.admin_get_category(
            category_id
        )

        return JsonResponse({
            'ok': True,
            'category': (
                _serialize_admin_category(category)
                if category
                else None
            ),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to change category visibility.',
        }, status=500)

def _parse_spec_allowed_values(value):
    return [
        item.strip()
        for item in str(value or '').split(',')
        if item.strip()
    ]


def _save_category_spec_template(category, spec_template):
    return repo.update_category(
        category_id=category['_id'],
        name=category.get('name', ''),
        slug=category.get('slug', ''),
        parent_id=category.get('parent_id'),

        icon=category.get('icon', ''),
        description=category.get('description', ''),
        display_order=category.get('display_order', 0),

        spec_template=spec_template,
    )


def _spec_field_from_request(request, display_order):
    data_type = (
        request.POST.get('data_type', 'text')
        .strip()
        .lower()
    )

    if data_type not in {
        'text',
        'number',
        'select',
        'boolean',
    }:
        raise ValueError('Invalid specification data type.')

    return {
        'key': request.POST.get('key', '').strip(),
        'label': request.POST.get('label', '').strip(),
        'data_type': data_type,
        'unit': request.POST.get('unit', '').strip(),

        'allowed_values': _parse_spec_allowed_values(
            request.POST.get('allowed_values')
        ),

        'is_filterable': (
            request.POST.get('is_filterable') == 'on'
        ),

        'display_order': display_order,
    }


def admin_category_spec_create(request, category_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        category = repo.admin_get_category(category_id)

        if not category:
            return JsonResponse({
                'ok': False,
                'error': 'Category does not exist.',
            }, status=404)

        fields = list(
            category.get('spec_template', [])
        )

        field = _spec_field_from_request(
            request,
            len(fields) + 1,
        )

        fields.append(field)

        updated = _save_category_spec_template(
            category,
            fields,
        )

        return JsonResponse({
            'ok': True,
            'category': _serialize_admin_category(
                updated
            ),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to add specification field.',
        }, status=500)


def admin_category_spec_update(
    request,
    category_id,
    field_key,
):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        category = repo.admin_get_category(category_id)

        if not category:
            return JsonResponse({
                'ok': False,
                'error': 'Category does not exist.',
            }, status=404)

        fields = list(
            category.get('spec_template', [])
        )

        found = False
        updated_fields = []

        for index, field in enumerate(fields):
            if field.get('key') == field_key:
                found = True

                replacement = _spec_field_from_request(
                    request,
                    field.get(
                        'display_order',
                        index + 1,
                    ),
                )

                updated_fields.append(replacement)

            else:
                updated_fields.append(field)

        if not found:
            return JsonResponse({
                'ok': False,
                'error': 'Specification field does not exist.',
            }, status=404)

        updated = _save_category_spec_template(
            category,
            updated_fields,
        )

        return JsonResponse({
            'ok': True,
            'category': _serialize_admin_category(
                updated
            ),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to update specification field.',
        }, status=500)


def admin_category_spec_delete(
    request,
    category_id,
    field_key,
):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        category = repo.admin_get_category(category_id)

        if not category:
            return JsonResponse({
                'ok': False,
                'error': 'Category does not exist.',
            }, status=404)

        old_fields = list(
            category.get('spec_template', [])
        )

        fields = [
            field
            for field in old_fields
            if field.get('key') != field_key
        ]

        if len(fields) == len(old_fields):
            return JsonResponse({
                'ok': False,
                'error': 'Specification field does not exist.',
            }, status=404)

        # Re-number display order after deletion.
        for index, field in enumerate(fields, start=1):
            field['display_order'] = index

        updated = _save_category_spec_template(
            category,
            fields,
        )

        return JsonResponse({
            'ok': True,
            'category': _serialize_admin_category(
                updated
            ),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to delete specification field.',
        }, status=500)

def admin_category_delete(request, category_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        repo.delete_category(category_id)

        return JsonResponse({
            'ok': True,
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to delete category.',
        }, status=500)

def admin_categories(request):
    return render(request, 'admin_categories.html', {
        'page_title': 'Manage Categories - ElectroMart'
    })

# ---------------------------------------------------------- admin products CV66
def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value.__class__.__name__ == 'ObjectId':
        return str(value)
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def _serialize_admin_product(product, categories=None, brands=None):
    categories = categories or {}
    brands = brands or {}
    category = categories.get(product.get('category_id'))
    brand = brands.get(product.get('brand_id'))

    return _json_safe({
        'id': str(product['_id']),
        'name': product.get('name', ''),
        'slug': product.get('slug', ''),
        'part_number': product.get('part_number', ''),
        'category_id': str(product['category_id']) if product.get('category_id') else '',
        'category_name': category.get('name', '') if category else '',
        'brand_id': str(product['brand_id']) if product.get('brand_id') else '',
        'brand_name': brand.get('name', '') if brand else '',
        'description': product.get('description', ''),
        'min_price': product.get('min_price', 0),
        'list_price': product.get('list_price', 0),
        'specifications': product.get('specifications', {}),
        'variants': product.get('variants', []),
        'images': product.get('images', []),
        'datasheet_url': product.get('datasheet_url', ''),
        'total_stock': product.get('total_stock', 0),
        'is_hidden': product.get('is_hidden', False),
        'status': 'inactive' if product.get('is_hidden', False) else 'active',
        'created_at': product.get('created_at'),
        'updated_at': product.get('updated_at'),
    })


def _parse_json_object(raw_value, field_name):
    if raw_value in (None, ''):
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    try:
        value = json.loads(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must contain valid JSON.')
    if not isinstance(value, dict):
        raise ValueError(f'{field_name} must be a JSON object.')
    return value


def _parse_json_array(raw_value, field_name):
    if raw_value in (None, ''):
        return []
    if isinstance(raw_value, list):
        return raw_value
    try:
        value = json.loads(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must contain valid JSON.')
    if not isinstance(value, list):
        raise ValueError(f'{field_name} must be a JSON array.')
    return value


# CV66 upload rules: generous enough for product media, strict enough to reject wrong files.
_CV66_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
_CV66_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_CV66_MAX_PDF_BYTES = 20 * 1024 * 1024


def _validate_product_uploads(image_files, datasheet):
    for upload in image_files:
        extension = Path(upload.name or '').suffix.lower()
        content_type = str(getattr(upload, 'content_type', '') or '').lower()

        if extension not in _CV66_IMAGE_EXTENSIONS:
            raise ValueError(
                f'Image "{upload.name}" must be JPG, JPEG, PNG, WEBP or GIF.'
            )
        if content_type and not content_type.startswith('image/'):
            raise ValueError(f'File "{upload.name}" is not an image.')
        if upload.size > _CV66_MAX_IMAGE_BYTES:
            raise ValueError(f'Image "{upload.name}" must not exceed 10 MB.')

    if datasheet:
        extension = Path(datasheet.name or '').suffix.lower()
        content_type = str(getattr(datasheet, 'content_type', '') or '').lower()

        if extension != '.pdf':
            raise ValueError('Datasheet must be a PDF file.')
        if content_type and content_type not in ('application/pdf', 'application/x-pdf'):
            raise ValueError('Datasheet must be a PDF file.')
        if datasheet.size > _CV66_MAX_PDF_BYTES:
            raise ValueError('Datasheet PDF must not exceed 20 MB.')


def _save_product_upload(upload, folder):
    extension = Path(upload.name or '').suffix.lower()
    storage_name = default_storage.save(
        f'products/{folder}/{uuid4().hex}{extension}',
        upload,
    )
    return storage_name, default_storage.url(storage_name)


def _delete_storage_names(storage_names):
    for storage_name in storage_names:
        try:
            default_storage.delete(storage_name)
        except Exception:
            pass


def _storage_name_from_media_url(url):
    value = str(url or '')
    media_url = str(settings.MEDIA_URL or '/media/')
    if not media_url.startswith('/'):
        media_url = '/' + media_url
    if not media_url.endswith('/'):
        media_url += '/'

    if value.startswith(media_url):
        return value[len(media_url):].lstrip('/')
    return None


def _save_product_media_from_request(request):
    image_files = list(request.FILES.getlist('images'))
    datasheet = request.FILES.get('datasheet')

    _validate_product_uploads(image_files, datasheet)

    saved_names = []
    image_urls = []
    datasheet_url = None

    try:
        for upload in image_files:
            storage_name, url = _save_product_upload(upload, 'images')
            saved_names.append(storage_name)
            image_urls.append(url)

        if datasheet:
            storage_name, datasheet_url = _save_product_upload(
                datasheet,
                'datasheets',
            )
            saved_names.append(storage_name)

        return image_urls, datasheet_url, saved_names
    except Exception:
        _delete_storage_names(saved_names)
        raise


def _product_hidden_from_status(request, default=None):
    raw = request.POST.get('status')
    if raw is None:
        return default
    raw = raw.strip().lower()
    if raw not in ('active', 'inactive'):
        raise ValueError('Product status must be active or inactive.')
    return raw == 'inactive'


def admin_products(request):
    return render(request, 'admin_products.html', {
        'page_title': 'Manage Products - ElectroMart'
    })


def admin_products_data(request):
    products = repo.admin_list_products()
    categories = {item['_id']: item for item in repo.admin_list_categories()}
    brands = {item['_id']: item for item in repo.admin_list_brands()}

    return JsonResponse({
        'ok': True,
        'products': [
            _serialize_admin_product(product, categories, brands)
            for product in products
        ],
        'categories': [
            {
                'id': str(category['_id']),
                'name': category.get('name', ''),
                'slug': category.get('slug', ''),
                'level': category.get('level', 0),
                'is_hidden': category.get('is_hidden', False),
            }
            for category in categories.values()
        ],
        'brands': [
            {
                'id': str(brand['_id']),
                'name': brand.get('name', ''),
                'slug': brand.get('slug', ''),
            }
            for brand in brands.values()
        ],
        'count': len(products),
    })


def admin_product_detail(request, product_id):
    product = repo.admin_get_product(product_id)
    if not product:
        return JsonResponse({
            'ok': False,
            'error': 'Product does not exist.',
        }, status=404)

    categories = repo.category_map([product])
    brands = repo.brand_map([product])
    return JsonResponse({
        'ok': True,
        'product': _serialize_admin_product(product, categories, brands),
    })


def admin_category_spec_template(request, category_id):
    category = repo.admin_get_category(category_id)
    if not category:
        return JsonResponse({
            'ok': False,
            'error': 'Category does not exist.',
        }, status=404)

    return JsonResponse({
        'ok': True,
        'category': {
            'id': str(category['_id']),
            'name': category.get('name', ''),
            'spec_template': _json_safe(category.get('spec_template', [])),
        },
    })


def admin_product_create(request):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    saved_names = []

    try:
        image_urls, datasheet_url, saved_names = (
            _save_product_media_from_request(request)
        )

        product = repo.create_product(
            name=request.POST.get('name'),
            part_number=request.POST.get('part_number'),
            category_id=request.POST.get('category_id'),
            brand_id=request.POST.get('brand_id') or None,
            min_price=request.POST.get('min_price', 0),
            description=request.POST.get('description', ''),
            specifications=_parse_json_object(
                request.POST.get('specifications'),
                'Specifications',
            ),
            slug=request.POST.get('slug') or None,
            is_hidden=_product_hidden_from_status(request, False),
            images=image_urls,
            datasheet_url=datasheet_url or '',
        )

        categories = repo.category_map([product])
        brands = repo.brand_map([product])
        return JsonResponse({
            'ok': True,
            'product': _serialize_admin_product(product, categories, brands),
        }, status=201)

    except ValueError as exc:
        _delete_storage_names(saved_names)
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        _delete_storage_names(saved_names)
        return JsonResponse({
            'ok': False,
            'error': 'Unable to create product.',
        }, status=500)


def admin_product_update(request, product_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    saved_names = []
    old_datasheet_storage_name = None

    try:
        current = repo.admin_get_product(product_id)
        if not current:
            return JsonResponse({
                'ok': False,
                'error': 'Product does not exist.',
            }, status=404)

        new_image_urls, new_datasheet_url, saved_names = (
            _save_product_media_from_request(request)
        )

        images = None
        if new_image_urls:
            images = list(current.get('images', [])) + new_image_urls

        datasheet_url = None
        if new_datasheet_url is not None:
            datasheet_url = new_datasheet_url
            old_datasheet_storage_name = _storage_name_from_media_url(
                current.get('datasheet_url', '')
            )

        raw_specs = request.POST.get('specifications')
        specifications = (
            current.get('specifications', {})
            if raw_specs is None
            else _parse_json_object(raw_specs, 'Specifications')
        )

        product = repo.update_product(
            product_id=product_id,
            name=request.POST.get('name', current.get('name', '')),
            part_number=request.POST.get(
                'part_number', current.get('part_number', '')
            ),
            category_id=request.POST.get(
                'category_id', str(current.get('category_id', ''))
            ),
            brand_id=request.POST.get(
                'brand_id', str(current.get('brand_id') or '')
            ) or None,
            min_price=request.POST.get(
                'min_price', current.get('min_price', 0)
            ),
            description=request.POST.get(
                'description', current.get('description', '')
            ),
            specifications=specifications,
            slug=request.POST.get('slug') or current.get('slug'),
            is_hidden=_product_hidden_from_status(
                request,
                current.get('is_hidden', False),
            ),
            images=images,
            datasheet_url=datasheet_url,
        )

        if old_datasheet_storage_name:
            _delete_storage_names([old_datasheet_storage_name])

        categories = repo.category_map([product])
        brands = repo.brand_map([product])
        return JsonResponse({
            'ok': True,
            'product': _serialize_admin_product(product, categories, brands),
        })

    except ValueError as exc:
        _delete_storage_names(saved_names)
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        _delete_storage_names(saved_names)
        return JsonResponse({
            'ok': False,
            'error': 'Unable to update product.',
        }, status=500)


def admin_product_variants(request, product_id):
    """CV66: save the complete JS-managed variant + tier-pricing array."""
    if request.method == 'GET':
        product = repo.admin_get_product(product_id)
        if not product:
            return JsonResponse({
                'ok': False,
                'error': 'Product does not exist.',
            }, status=404)

        categories = repo.category_map([product])
        brands = repo.brand_map([product])
        return JsonResponse({
            'ok': True,
            'product': _serialize_admin_product(product, categories, brands),
            'variants': _json_safe(product.get('variants', [])),
        })

    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'GET or POST method required.',
        }, status=405)

    try:
        content_type = str(request.content_type or '').lower()

        if 'application/json' in content_type:
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except (UnicodeDecodeError, ValueError):
                raise ValueError('Variant request must contain valid JSON.')

            if not isinstance(payload, dict):
                raise ValueError('Variant request must be a JSON object.')

            variants = payload.get('variants', [])
        else:
            variants = _parse_json_array(
                request.POST.get('variants'),
                'Variants',
            )

        product = repo.set_product_variants(
            product_id,
            variants,
        )

        categories = repo.category_map([product])
        brands = repo.brand_map([product])

        return JsonResponse({
            'ok': True,
            'product': _serialize_admin_product(product, categories, brands),
            'variants': _json_safe(product.get('variants', [])),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to save product variants.',
        }, status=500)


def admin_product_hidden(request, product_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        raw = str(request.POST.get('hidden', 'true')).strip().lower()
        if raw not in ('1', '0', 'true', 'false', 'yes', 'no', 'on', 'off'):
            raise ValueError('Hidden value must be true or false.')

        hidden = raw in ('1', 'true', 'yes', 'on')
        product = repo.set_product_hidden(product_id, hidden)
        categories = repo.category_map([product])
        brands = repo.brand_map([product])

        return JsonResponse({
            'ok': True,
            'product': _serialize_admin_product(product, categories, brands),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to change product visibility.',
        }, status=500)
    
# ---------------------------------------------------------- admin inventory CV67
def _serialize_inventory_item(item):
    return _json_safe({
        'product_id': item.get('product_id'),
        'product_name': item.get('product_name', ''),
        'product_part_number': item.get('product_part_number', ''),
        'product_hidden': item.get('product_hidden', False),
        'sku': item.get('sku', ''),
        'variant_name': item.get('variant_name', ''),
        'stock_qty': item.get('stock_qty', 0),
        'reorder_level': item.get('reorder_level', 0),
        'warehouse_location': item.get('warehouse_location', ''),
        'status': item.get('status', 'in'),
    })


def _serialize_stock_movement(movement):
    return _json_safe({
        'id': movement.get('_id'),
        'product_id': movement.get('product_id'),
        'product_name': movement.get('product_name', ''),
        'sku': movement.get('sku', ''),
        'variant_name': movement.get('variant_name', ''),
        'type': movement.get('type', ''),
        'quantity': movement.get('quantity', 0),
        'reason': movement.get('reason', ''),
        'stock_before': movement.get('stock_before', 0),
        'stock_after': movement.get('stock_after', 0),
        'reorder_level': movement.get('reorder_level', 0),
        'warehouse_location': movement.get('warehouse_location', ''),
        'created_at': movement.get('created_at'),
    })


def admin_inventory(request):
    return render(request, 'admin_inventory.html', {
        'page_title': 'Manage Inventory - ElectroMart',
    })


def admin_inventory_data(request):
    items = repo.admin_inventory_items()
    low_stock = repo.admin_low_stock_items()

    return JsonResponse({
        'ok': True,
        'items': [
            _serialize_inventory_item(item)
            for item in items
        ],
        'low_stock_count': len(low_stock),
        'count': len(items),
    })


def admin_inventory_low_stock(request):
    items = repo.admin_low_stock_items()

    return JsonResponse({
        'ok': True,
        'items': [
            _serialize_inventory_item(item)
            for item in items
        ],
        'count': len(items),
    })


def admin_inventory_movements(request):
    sku = request.GET.get('sku', '')
    limit = request.GET.get('limit', 100)

    movements = repo.admin_inventory_movements(
        sku=sku,
        limit=limit,
    )

    return JsonResponse({
        'ok': True,
        'movements': [
            _serialize_stock_movement(movement)
            for movement in movements
        ],
        'count': len(movements),
        'sku': sku,
    })


def admin_inventory_adjust(request):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    try:
        item, movement = repo.apply_inventory_movement(
            product_id=request.POST.get('product_id'),
            sku=request.POST.get('sku'),
            movement_type=request.POST.get('movement_type'),
            quantity=request.POST.get('quantity'),
            reason=request.POST.get('reason'),
            reorder_level=request.POST.get('reorder_level'),
            warehouse_location=request.POST.get('warehouse_location'),
        )

        return JsonResponse({
            'ok': True,
            'item': _serialize_inventory_item(item),
            'movement': _serialize_stock_movement(movement),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to update inventory.',
        }, status=500)


# ------------------------------------------------------------- sales_payment module
def cart(request):
    return render(request, 'sales_payment/cart.html', {'page_title': 'Giỏ hàng - ElectroMart'})


def checkout(request):
    return render(request, 'sales_payment/checkout.html', {'page_title': 'Thanh toán - ElectroMart'})


def tracking(request):
    return render(request, 'sales_payment/tracking.html', {'page_title': 'Tra cứu đơn hàng - ElectroMart'})


def admin_dashboard(request):
    return render(request, 'sales_payment/admin-dashboard.html')


def admin_orders(request):
    return render(request, 'sales_payment/admin-orders.html')


def admin_promotions(request):
    return render(request, 'sales_payment/admin-promotions.html')