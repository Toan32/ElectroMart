"""Catalogue & content views (Minh's module).

Storefront : home, category listing, product detail, search, compare,
             wishlist, news, FAQ, feedback.
Admin      : categories + spec templates (CV65), products and variants
             (CV66), inventory and stock movements (CV67), news and
             customer feedback (CV70), review/comment moderation (CV71).

Every admin page renders once and then talks to its own JSON endpoints, so
the page views carry @admin_required (redirect to login) and the endpoints
carry @admin_required_json (403 the fetch() can read) - both from
accounts/decorators.py, the same guard Tin's and Loc's admin pages use.

Reviews and Q&A live in the interaction app; this module only reads them
for product_detail.
"""
import json
from datetime import timezone as datetime_timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_datetime

from accounts import mailer as accounts_mailer
from accounts import repo as accounts_repo
from accounts.decorators import admin_required, admin_required_json, current_user
from interaction import repo as interaction_repo

from . import repo
from .db import PRODUCTS, get_db as get_catalogue_db

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


def _build_comment_threads(comments):
    """
    Convert the flat MongoDB comment list into display order
    while preserving unlimited parent/reply levels.

    Each comment receives:
    - id: string version of MongoDB _id
    - depth: nesting level (0 = root question)
    - indent_px: indentation prepared for the storefront UI
    """
    children_map = {}

    for comment in comments:
        comment['id'] = str(comment['_id'])

        parent_id = comment.get('parent_id')

        children_map.setdefault(
            parent_id,
            []
        ).append(comment)

    threaded_comments = []

    def walk(parent_id=None, depth=0):
        children = children_map.get(
            parent_id,
            []
        )

        for comment in children:
            comment['depth'] = depth

            # Limit visual indentation only; real depth is preserved.
            comment['indent_px'] = min(
                depth,
                5
            ) * 36

            threaded_comments.append(comment)

            walk(
                comment['_id'],
                depth + 1
            )

    walk()

    return threaded_comments


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

    # CV69: public users never receive hidden comments.
    # The owner still receives their own hidden comments so they can unhide them.
    all_comments = interaction_repo.list_comments(
        p['_id'],
        include_hidden=True,
    )

    current_user_id = request.session.get('user_id')
    comments = []
    author_cache = {}

    for comment in all_comments:
        is_owner = (
            bool(current_user_id)
            and str(comment.get('user_id')) == str(current_user_id)
        )

        if comment.get('is_hidden', False) and not is_owner:
            continue

        user_id = comment.get('user_id')
        user_key = str(user_id)

        if user_key not in author_cache:
            author_cache[user_key] = (
                accounts_repo.find_user_by_id(user_id)
                if user_id is not None
                else None
            )

        author = author_cache.get(user_key)
        is_admin_reply = bool(
            comment.get('is_admin_reply', False)
        )

        comment['is_owner'] = is_owner
        comment['is_admin_reply'] = is_admin_reply
        comment['author_name'] = (
            'ElectroMart Shop'
            if is_admin_reply
            else (
                author.get('full_name', 'Customer')
                if author
                else 'Customer'
            )
        )

        comments.append(comment)

    comment_threads = _build_comment_threads(
        comments
    )

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
        'comment_threads': comment_threads,
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

# -------------------------------------------------------------- CV70 News

def _news_aware_datetime(value):
    if value is not None and django_timezone.is_naive(value):
        return django_timezone.make_aware(value, datetime_timezone.utc)
    return value


def _news_display_item(item):
    """Prepare one MongoDB news document for storefront templates."""
    item = dict(item)
    type_key = item.get('type', '')
    item['type_key'] = type_key
    item['type'] = repo.NEWS_TYPES.get(type_key, type_key)

    publish_at = _news_aware_datetime(item.get('publish_at'))
    if publish_at:
        publish_at = django_timezone.localtime(publish_at)
        item['date'] = publish_at.strftime('%B %d, %Y')
    else:
        item['date'] = ''

    return item


def _parse_news_publish_at(raw_value, default=None):
    """Parse the HTML datetime-local value using the project timezone."""
    raw_value = str(raw_value or '').strip()
    if not raw_value:
        return default if default is not None else django_timezone.now()

    value = parse_datetime(raw_value)
    if value is None:
        raise ValueError('Publish date/time is invalid.')

    if django_timezone.is_naive(value):
        value = django_timezone.make_aware(
            value,
            django_timezone.get_current_timezone(),
        )

    return value


def _news_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _admin_user(request):
    """The logged-in admin, or None.

    Three near-identical copies of this lookup used to live in this file
    (news, feedback, moderation). They all now defer to
    accounts.decorators.current_user, which is what @admin_required and the
    templates already use, so "who is an admin" is decided in one place.
    """
    user = current_user(request)
    if not user or user.get('role') != accounts_repo.ROLE_ADMIN:
        return None
    return user


def _serialize_news(item):
    publish_at = _news_aware_datetime(item.get('publish_at'))
    local_publish_at = (
        django_timezone.localtime(publish_at)
        if publish_at
        else None
    )

    if item.get('is_hidden', False):
        status = 'hidden'
    elif publish_at and publish_at > django_timezone.now():
        status = 'scheduled'
    else:
        status = 'published'

    return {
        'id': str(item.get('_id', '')),
        'title': item.get('title', ''),
        'slug': item.get('slug', ''),
        'type': item.get('type', ''),
        'type_label': repo.NEWS_TYPES.get(item.get('type', ''), item.get('type', '')),
        'summary': item.get('summary', ''),
        'content': item.get('content', ''),
        'publish_at': local_publish_at.isoformat() if local_publish_at else '',
        'is_hidden': bool(item.get('is_hidden', False)),
        'status': status,
        'created_by': str(item.get('created_by') or ''),
        'created_at': item.get('created_at').isoformat() if item.get('created_at') else '',
        'updated_at': item.get('updated_at').isoformat() if item.get('updated_at') else '',
    }


def news(request):
    selected_type = str(request.GET.get('type', 'all') or 'all').strip().lower()

    try:
        news_items = repo.list_public_news(selected_type)
    except ValueError:
        selected_type = 'all'
        news_items = repo.list_public_news()

    news_items = [_news_display_item(item) for item in news_items]

    return render(request, 'news.html', {
        'page_title': 'News - ElectroMart',
        'news_items': news_items,
        'news_types': repo.NEWS_TYPES,
        'selected_type': selected_type,
    })


def news_detail(request, slug):
    item = repo.get_public_news(slug)
    if not item:
        raise Http404('News article not found')

    item = _news_display_item(item)
    return render(request, 'news_detail.html', {
        'page_title': item.get('title', 'News') + ' - ElectroMart',
        'item': item,
    })


@admin_required
def admin_news(request):
    return render(request, 'admin_news.html', {
        'page_title': 'Manage News - ElectroMart',
        'admin_page': 'news',
    })


def admin_news_data(request):
    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'GET method required.'}, status=405)

    if not _admin_user(request):
        return JsonResponse({'ok': False, 'error': 'Admin access required.'}, status=403)

    items = repo.admin_list_news()
    return JsonResponse({
        'ok': True,
        'news': [_serialize_news(item) for item in items],
        'types': repo.NEWS_TYPES,
        'count': len(items),
    })


def admin_news_create(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST method required.'}, status=405)

    admin_user = _admin_user(request)
    if not admin_user:
        return JsonResponse({'ok': False, 'error': 'Admin access required.'}, status=403)

    try:
        item = repo.create_news(
            title=request.POST.get('title'),
            news_type=request.POST.get('type'),
            summary=request.POST.get('summary'),
            content=request.POST.get('content'),
            publish_at=_parse_news_publish_at(request.POST.get('publish_at')),
            slug=request.POST.get('slug') or None,
            created_by=admin_user.get('_id'),
            is_hidden=_news_bool(request.POST.get('is_hidden'), False),
        )
        return JsonResponse({'ok': True, 'news': _serialize_news(item)}, status=201)
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Unable to create news article.'}, status=500)


def admin_news_update(request, news_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST method required.'}, status=405)

    if not _admin_user(request):
        return JsonResponse({'ok': False, 'error': 'Admin access required.'}, status=403)

    try:
        current = repo.admin_get_news(news_id)
        if not current:
            return JsonResponse({'ok': False, 'error': 'News article does not exist.'}, status=404)

        publish_at = _parse_news_publish_at(
            request.POST.get('publish_at'),
            default=current.get('publish_at'),
        )

        item = repo.update_news(
            news_id=news_id,
            title=request.POST.get('title', current.get('title', '')),
            news_type=request.POST.get('type', current.get('type', '')),
            summary=request.POST.get('summary', current.get('summary', '')),
            content=request.POST.get('content', current.get('content', '')),
            publish_at=publish_at,
            slug=request.POST.get('slug') or current.get('slug'),
            is_hidden=(
                _news_bool(request.POST.get('is_hidden'))
                if 'is_hidden' in request.POST
                else current.get('is_hidden', False)
            ),
        )
        return JsonResponse({'ok': True, 'news': _serialize_news(item)})
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Unable to update news article.'}, status=500)


def admin_news_hidden(request, news_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST method required.'}, status=405)

    if not _admin_user(request):
        return JsonResponse({'ok': False, 'error': 'Admin access required.'}, status=403)

    try:
        item = repo.set_news_hidden(
            news_id,
            _news_bool(request.POST.get('hidden'), True),
        )
        return JsonResponse({'ok': True, 'news': _serialize_news(item)})
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Unable to change news visibility.'}, status=500)


def admin_news_delete(request, news_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST method required.'}, status=405)

    if not _admin_user(request):
        return JsonResponse({'ok': False, 'error': 'Admin access required.'}, status=403)

    try:
        repo.delete_news(news_id)
        return JsonResponse({'ok': True})
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Unable to delete news article.'}, status=500)


_CV70_FEEDBACK_EXTENSIONS = {
    '.jpg',
    '.jpeg',
    '.png',
    '.pdf',
    '.doc',
    '.docx',
}
_CV70_FEEDBACK_MAX_BYTES = 10 * 1024 * 1024
_CV70_FEEDBACK_SUBJECTS = {
    'product',
    'website',
    'order',
    'technical',
    'suggestion',
    'other',
}


def _feedback_context(form=None, error=''):
    return {
        'page_title': 'Feedback - ElectroMart',
        'feedback_form': form or {},
        'feedback_error': error,
    }


def feedback(request):
    if request.method == 'GET':
        context = _feedback_context()
        context['feedback_success'] = (
            request.GET.get('sent') == '1'
        )
        return render(request, 'feedback.html', context)

    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'GET or POST method required.',
        }, status=405)

    name = str(request.POST.get('name') or '').strip()
    email = str(request.POST.get('email') or '').strip().lower()
    subject = str(request.POST.get('subject') or '').strip().lower()
    message = str(request.POST.get('content') or '').strip()
    attachment = request.FILES.get('attachment')

    form_values = {
        'name': name,
        'email': email,
        'subject': subject,
        'content': message,
    }

    saved_name = None

    try:
        if not name:
            raise ValueError('Full name is required.')

        if len(name) > 120:
            raise ValueError('Full name must not exceed 120 characters.')

        if not email:
            raise ValueError('Email is required.')

        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('Please enter a valid email address.')

        if subject not in _CV70_FEEDBACK_SUBJECTS:
            raise ValueError('Please select a valid feedback subject.')

        if not message:
            raise ValueError('Feedback message is required.')

        if len(message) > 1000:
            raise ValueError(
                'Feedback message must not exceed 1000 characters.'
            )

        attachment_meta = None

        if attachment:
            extension = Path(
                attachment.name or ''
            ).suffix.lower()

            if extension not in _CV70_FEEDBACK_EXTENSIONS:
                raise ValueError(
                    'Attachment must be JPG, JPEG, PNG, PDF, DOC or DOCX.'
                )

            if attachment.size > _CV70_FEEDBACK_MAX_BYTES:
                raise ValueError(
                    'Attachment must not exceed 10 MB.'
                )

            saved_name = default_storage.save(
                f'feedback/{uuid4().hex}{extension}',
                attachment,
            )

            attachment_meta = {
                'original_name': str(attachment.name or ''),
                'storage_name': saved_name,
                'url': default_storage.url(saved_name),
                'content_type': str(
                    getattr(attachment, 'content_type', '') or ''
                ),
                'size': int(attachment.size or 0),
            }

        interaction_repo.create_feedback(
            name=name,
            email=email,
            subject=subject,
            message=message,
            user_id=request.session.get('user_id'),
            attachment=attachment_meta,
        )

        return redirect('/feedback/?sent=1')

    except ValueError as exc:
        if saved_name and default_storage.exists(saved_name):
            default_storage.delete(saved_name)

        return render(
            request,
            'feedback.html',
            _feedback_context(
                form=form_values,
                error=str(exc),
            ),
            status=400,
        )

    except Exception:
        if saved_name and default_storage.exists(saved_name):
            default_storage.delete(saved_name)

        return render(
            request,
            'feedback.html',
            _feedback_context(
                form=form_values,
                error='Unable to submit feedback. Please try again.',
            ),
            status=500,
        )

def faq(request):
    faq_items = repo.get_faq_items()

    return render(request, 'faq.html', {
        'page_title': 'FAQ - ElectroMart',
        'faq_items': faq_items,
    })

# ============================================================
# CV70 - Admin Feedback / Email Reply
# ============================================================

_CV70_FEEDBACK_STATUSES = {
    'new',
    'processing',
    'resolved',
}

_CV70_FEEDBACK_SUBJECT_LABELS = {
    'product': 'Product feedback',
    'website': 'Website experience',
    'order': 'Order or delivery',
    'technical': 'Technical support',
    'suggestion': 'Suggestion',
    'other': 'Other',
}




def _serialize_feedback(item):
    attachment = item.get('attachment') or {}
    admin_reply = item.get('admin_reply') or {}

    created_at = item.get('created_at')
    updated_at = item.get('updated_at')
    replied_at = admin_reply.get('replied_at')

    return {
        'id': str(item.get('_id', '')),
        'user_id': str(item.get('user_id') or ''),
        'name': item.get('name', ''),
        'email': item.get('email', ''),
        'subject': item.get('subject', ''),
        'subject_label': _CV70_FEEDBACK_SUBJECT_LABELS.get(
            item.get('subject', ''),
            item.get('subject', ''),
        ),
        'message': item.get('message', ''),
        'status': item.get('status', 'new'),
        'attachment': {
            'original_name': attachment.get('original_name', ''),
            'url': attachment.get('url', ''),
            'content_type': attachment.get('content_type', ''),
            'size': int(attachment.get('size', 0) or 0),
        } if attachment else None,
        'admin_reply': {
            'message': admin_reply.get('message', ''),
            'replied_by': str(admin_reply.get('replied_by') or ''),
            'replied_at': replied_at.isoformat() if replied_at else '',
            'email_sent': bool(admin_reply.get('email_sent', False)),
        } if admin_reply else None,
        'created_at': created_at.isoformat() if created_at else '',
        'updated_at': updated_at.isoformat() if updated_at else '',
    }


@admin_required
def admin_feedback(request):
    return render(request, 'admin_feedback.html', {
        'page_title': 'Manage Feedback - ElectroMart',
        'admin_page': 'feedback',
    })


def admin_feedback_data(request):
    if request.method != 'GET':
        return JsonResponse({
            'ok': False,
            'error': 'GET method required.',
        }, status=405)

    if not _admin_user(request):
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    status = str(
        request.GET.get('status') or ''
    ).strip().lower()

    if status and status not in _CV70_FEEDBACK_STATUSES:
        return JsonResponse({
            'ok': False,
            'error': 'Invalid feedback status.',
        }, status=400)

    items = interaction_repo.list_feedback(
        status=status or None
    )

    return JsonResponse({
        'ok': True,
        'feedback': [
            _serialize_feedback(item)
            for item in items
        ],
        'count': len(items),
    })


def admin_feedback_status(request, feedback_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    if not _admin_user(request):
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    status = str(
        request.POST.get('status') or ''
    ).strip().lower()

    try:
        updated = interaction_repo.update_feedback_status(
            feedback_id,
            status,
        )

        if not updated:
            return JsonResponse({
                'ok': False,
                'error': 'Feedback does not exist.',
            }, status=404)

        return JsonResponse({
            'ok': True,
            'feedback': _serialize_feedback(updated),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to update feedback status.',
        }, status=400)


def admin_feedback_reply(request, feedback_id):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    admin_user = _admin_user(request)

    if not admin_user:
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    reply_message = str(
        request.POST.get('message') or ''
    ).strip()

    if not reply_message:
        return JsonResponse({
            'ok': False,
            'error': 'Reply message cannot be empty.',
        }, status=400)

    if len(reply_message) > 5000:
        return JsonResponse({
            'ok': False,
            'error': 'Reply message must not exceed 5000 characters.',
        }, status=400)

    try:
        feedback_item = interaction_repo.get_feedback(
            feedback_id
        )
    except Exception:
        feedback_item = None

    if not feedback_item:
        return JsonResponse({
            'ok': False,
            'error': 'Feedback does not exist.',
        }, status=404)

    to_email = str(
        feedback_item.get('email') or ''
    ).strip().lower()

    if not to_email:
        return JsonResponse({
            'ok': False,
            'error': 'Feedback has no reply email address.',
        }, status=400)

    subject_label = _CV70_FEEDBACK_SUBJECT_LABELS.get(
        feedback_item.get('subject', ''),
        feedback_item.get('subject', '') or 'Feedback',
    )

    email_sent = accounts_mailer.send_mail(
        to_email=to_email,
        subject=f'Re: Your ElectroMart feedback - {subject_label}',
        template_name='feedback_reply_email.html',
        context={
            'customer_name': feedback_item.get('name', 'Customer'),
            'feedback_subject': subject_label,
            'feedback_message': feedback_item.get('message', ''),
            'reply_message': reply_message,
        },
    )

    try:
        updated = interaction_repo.save_feedback_reply(
            feedback_id=feedback_id,
            message=reply_message,
            replied_by=admin_user.get('_id'),
            email_sent=email_sent,
        )

        if email_sent:
            updated = interaction_repo.update_feedback_status(
                feedback_id,
                'resolved',
            ) or updated

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': (
                'Email was sent but the feedback reply could not be saved.'
                if email_sent
                else 'Unable to save the feedback reply.'
            ),
            'email_sent': bool(email_sent),
        }, status=500)

    if not email_sent:
        return JsonResponse({
            'ok': False,
            'error': (
                'The reply could not be sent by email. '
                'It was saved for retry and the feedback was not marked resolved.'
            ),
            'email_sent': False,
            'feedback': _serialize_feedback(updated),
        }, status=502)

    return JsonResponse({
        'ok': True,
        'email_sent': True,
        'feedback': _serialize_feedback(updated),
    })



# ============================================================
# CV71 - Admin Moderation
# Review / Comment / Feedback
# ============================================================

_CV71_CONTENT_SECTIONS = {
    'reviews',
    'comments',
    'feedback',
}




def _cv71_hidden_filter(status):
    value = str(status or '').strip().lower()

    if value in ('', 'all'):
        return None

    if value == 'visible':
        return False

    if value == 'hidden':
        return True

    raise ValueError(
        'Status must be all, visible or hidden.'
    )


def _cv71_user_summary(user_id):
    if not user_id:
        return {
            'id': '',
            'name': 'Unknown user',
            'email': '',
            'role': '',
        }

    try:
        user = accounts_repo.find_user_by_id(user_id)
    except Exception:
        user = None

    if not user:
        return {
            'id': str(user_id),
            'name': 'Unknown user',
            'email': '',
            'role': '',
        }

    return {
        'id': str(user.get('_id', '')),
        'name': user.get('full_name', '') or 'User',
        'email': user.get('email', ''),
        'role': user.get('role', ''),
    }


def _cv71_product_map():
    return {
        item['_id']: item
        for item in repo.admin_list_products()
    }


def _cv71_product_summary(product_id, product_map=None):
    product_map = (
        product_map
        if product_map is not None
        else _cv71_product_map()
    )

    product = product_map.get(product_id)

    if not product:
        return {
            'id': str(product_id or ''),
            'name': 'Unknown product',
            'slug': '',
        }

    return {
        'id': str(product.get('_id', '')),
        'name': product.get('name', ''),
        'slug': product.get('slug', ''),
    }


def _cv71_recalculate_product_rating(product_id):
    visible_reviews = interaction_repo.list_reviews(
        product_id,
        include_hidden=False,
    )

    rating_count = len(visible_reviews)

    avg_rating = (
        round(
            sum(
                int(review.get('rating', 0))
                for review in visible_reviews
            ) / rating_count,
            1,
        )
        if rating_count
        else 0
    )

    get_catalogue_db()[PRODUCTS].update_one(
        {'_id': product_id},
        {
            '$set': {
                'avg_rating': avg_rating,
                'rating_count': rating_count,
            }
        },
    )

    return {
        'avg_rating': avg_rating,
        'rating_count': rating_count,
    }


def _cv71_serialize_review(item, product_map=None):
    product = _cv71_product_summary(
        item.get('product_id'),
        product_map,
    )
    user = _cv71_user_summary(
        item.get('user_id')
    )

    created_at = item.get('created_at')
    updated_at = item.get('updated_at')

    return {
        'id': str(item.get('_id', '')),
        'kind': 'review',
        'product': product,
        'user': user,
        'rating': int(item.get('rating', 0) or 0),
        'title': item.get('title', ''),
        'content': item.get('content', ''),
        'images': list(item.get('images') or []),
        'is_hidden': bool(item.get('is_hidden', False)),
        'status': (
            'hidden'
            if item.get('is_hidden')
            else 'visible'
        ),
        'created_at': (
            created_at.isoformat()
            if created_at
            else ''
        ),
        'updated_at': (
            updated_at.isoformat()
            if updated_at
            else ''
        ),
    }


def _cv71_serialize_comment(item, product_map=None):
    product = _cv71_product_summary(
        item.get('product_id'),
        product_map,
    )
    user = _cv71_user_summary(
        item.get('user_id')
    )

    created_at = item.get('created_at')
    updated_at = item.get('updated_at')

    return {
        'id': str(item.get('_id', '')),
        'kind': 'comment',
        'product': product,
        'user': user,
        'parent_id': str(item.get('parent_id') or ''),
        'content': item.get('content', ''),
        'is_admin_reply': bool(
            item.get('is_admin_reply', False)
        ),
        'is_hidden': bool(item.get('is_hidden', False)),
        'status': (
            'hidden'
            if item.get('is_hidden')
            else 'visible'
        ),
        'created_at': (
            created_at.isoformat()
            if created_at
            else ''
        ),
        'updated_at': (
            updated_at.isoformat()
            if updated_at
            else ''
        ),
    }


@admin_required
def admin_moderation(request):
    return render(request, 'admin_moderation.html', {
        'page_title': 'Content Moderation - ElectroMart',
        'admin_page': 'moderation',
    })


def admin_moderation_data(request):
    if request.method != 'GET':
        return JsonResponse({
            'ok': False,
            'error': 'GET method required.',
        }, status=405)

    if not _admin_user(request):
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    section = str(
        request.GET.get('section') or 'reviews'
    ).strip().lower()

    if section not in _CV71_CONTENT_SECTIONS:
        return JsonResponse({
            'ok': False,
            'error': 'Invalid moderation section.',
        }, status=400)

    product_id = str(
        request.GET.get('product_id') or ''
    ).strip()

    status = str(
        request.GET.get('status') or ''
    ).strip().lower()

    product_map = _cv71_product_map()

    products = [
        {
            'id': str(item['_id']),
            'name': item.get('name', ''),
            'slug': item.get('slug', ''),
        }
        for item in product_map.values()
    ]

    try:
        if section == 'reviews':
            hidden = _cv71_hidden_filter(status)

            items = interaction_repo.admin_list_reviews(
                product_id=product_id or None,
                is_hidden=hidden,
            )

            rows = [
                _cv71_serialize_review(
                    item,
                    product_map,
                )
                for item in items
            ]

        elif section == 'comments':
            hidden = _cv71_hidden_filter(status)

            items = interaction_repo.admin_list_comments(
                product_id=product_id or None,
                is_hidden=hidden,
            )

            rows = [
                _cv71_serialize_comment(
                    item,
                    product_map,
                )
                for item in items
            ]

        else:
            if product_id:
                return JsonResponse({
                    'ok': False,
                    'error': (
                        'Product filter is not applicable '
                        'to feedback.'
                    ),
                }, status=400)

            if status not in (
                '',
                'all',
                'new',
                'processing',
                'resolved',
            ):
                return JsonResponse({
                    'ok': False,
                    'error': 'Invalid feedback status.',
                }, status=400)

            items = interaction_repo.list_feedback(
                status=(
                    None
                    if status in ('', 'all')
                    else status
                )
            )

            rows = [
                _serialize_feedback(item)
                for item in items
            ]

        return JsonResponse({
            'ok': True,
            'section': section,
            'items': rows,
            'products': products,
            'count': len(rows),
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to load moderation data.',
        }, status=500)


def admin_moderation_review_hidden(
    request,
    review_id,
):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    if not _admin_user(request):
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    try:
        review = interaction_repo.get_review(
            review_id
        )

        if not review:
            return JsonResponse({
                'ok': False,
                'error': 'Review does not exist.',
            }, status=404)

        hidden = _news_bool(
            request.POST.get('hidden'),
            True,
        )

        updated = interaction_repo.set_review_hidden(
            review_id,
            hidden,
        )

        stats = _cv71_recalculate_product_rating(
            review['product_id']
        )

        return JsonResponse({
            'ok': True,
            'review': _cv71_serialize_review(
                updated,
                _cv71_product_map(),
            ),
            'rating': stats,
        })

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to change review visibility.',
        }, status=500)


def admin_moderation_comment_hidden(
    request,
    comment_id,
):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    if not _admin_user(request):
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    try:
        comment = interaction_repo.get_comment(
            comment_id
        )

        if not comment:
            return JsonResponse({
                'ok': False,
                'error': 'Comment does not exist.',
            }, status=404)

        hidden = _news_bool(
            request.POST.get('hidden'),
            True,
        )

        updated = interaction_repo.set_comment_hidden(
            comment_id,
            hidden,
        )

        return JsonResponse({
            'ok': True,
            'comment': _cv71_serialize_comment(
                updated,
                _cv71_product_map(),
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
            'error': 'Unable to change comment visibility.',
        }, status=500)


def admin_moderation_comment_reply(
    request,
    comment_id,
):
    if request.method != 'POST':
        return JsonResponse({
            'ok': False,
            'error': 'POST method required.',
        }, status=405)

    admin_user = _admin_user(request)

    if not admin_user:
        return JsonResponse({
            'ok': False,
            'error': 'Admin access required.',
        }, status=403)

    content = str(
        request.POST.get('content') or ''
    ).strip()

    if not content:
        return JsonResponse({
            'ok': False,
            'error': 'Reply content cannot be empty.',
        }, status=400)

    if len(content) > 3000:
        return JsonResponse({
            'ok': False,
            'error': 'Reply content must not exceed 3000 characters.',
        }, status=400)

    try:
        parent = interaction_repo.get_comment(
            comment_id
        )

        if not parent:
            return JsonResponse({
                'ok': False,
                'error': 'Comment does not exist.',
            }, status=404)

        if parent.get('is_hidden'):
            return JsonResponse({
                'ok': False,
                'error': 'Cannot reply to a hidden comment.',
            }, status=400)

        reply = interaction_repo.create_comment(
            product_id=parent['product_id'],
            user_id=admin_user['_id'],
            content=content,
            parent_id=parent['_id'],
            is_admin_reply=True,
        )

        return JsonResponse({
            'ok': True,
            'reply': _cv71_serialize_comment(
                reply,
                _cv71_product_map(),
            ),
        }, status=201)

    except ValueError as exc:
        return JsonResponse({
            'ok': False,
            'error': str(exc),
        }, status=400)

    except Exception:
        return JsonResponse({
            'ok': False,
            'error': 'Unable to post shop reply.',
        }, status=500)


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


@admin_required_json
def admin_categories_data(request):
    categories = repo.admin_list_categories()

    return JsonResponse({
        'categories': [
            _serialize_admin_category(category)
            for category in categories
        ],
        'count': len(categories),
    })

@admin_required_json
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

@admin_required_json
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

@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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

@admin_required_json
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

# CV65-CV67: these three pages, and every fetch() endpoint below them, used
# to be reachable by anyone who knew the URL - /admin/products/create/ would
# happily create a product for a logged-out visitor. They now use the same
# guard as every other admin page in the project.
@admin_required
def admin_categories(request):
    return render(request, 'admin_categories.html', {
        'page_title': 'Manage Categories - ElectroMart',
        'admin_page': 'categories',
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


@admin_required
def admin_products(request):
    return render(request, 'admin_products.html', {
        'page_title': 'Manage Products - ElectroMart',
        'admin_page': 'products',
    })


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required
def admin_inventory(request):
    return render(request, 'admin_inventory.html', {
        'page_title': 'Manage Inventory - ElectroMart',
        'admin_page': 'inventory',
    })


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


@admin_required_json
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


# tracking, admin_dashboard, admin_orders and admin_promotions moved to
# sales/views.py (CV54-CV57): they now read the orders and coupons
# collections and render through the shared admin layout, instead of being
# static renders of a standalone page fed by localStorage.