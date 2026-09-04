from pathlib import Path

from bson.errors import InvalidId
from uuid import uuid4

from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import Http404, JsonResponse
from django.shortcuts import redirect

from accounts import repo as accounts_repo
from catalogue import repo as catalogue_repo
from catalogue.db import PRODUCTS, get_db as get_catalogue_db
from . import repo as interaction_repo


MAX_REVIEW_IMAGES = 5
MAX_REVIEW_IMAGE_SIZE = 5 * 1024 * 1024


# ============================================================
# CV68 - Product Rating Recalculation
# ============================================================

def _recalculate_product_rating(product_id):
    reviews = interaction_repo.list_reviews(product_id)

    rating_count = len(reviews)

    avg_rating = (
        round(
            sum(
                int(review.get('rating', 0))
                for review in reviews
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

    return avg_rating, rating_count


# ============================================================
# CV68 - Submit Review
# ============================================================

def submit_review(request, product_slug):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before submitting a review.'
        )

        return redirect('accounts_login')

    product = catalogue_repo.get_product(product_slug)

    if not product:
        raise Http404('Product not found')

    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    uploaded_images = request.FILES.getlist('images')

    if not rating:
        messages.error(
            request,
            'Please select a rating.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    if interaction_repo.get_user_review(
        product['_id'],
        user_id,
    ):
        messages.error(
            request,
            'This user has already reviewed this product.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    saved_paths = []
    image_urls = []

    try:
        if len(uploaded_images) > MAX_REVIEW_IMAGES:
            raise ValueError(
                f'You can upload up to '
                f'{MAX_REVIEW_IMAGES} images.'
            )

        for image in uploaded_images:
            if (
                not image.content_type
                or not image.content_type.startswith('image/')
            ):
                raise ValueError(
                    'Only image files are allowed.'
                )

            if image.size > MAX_REVIEW_IMAGE_SIZE:
                raise ValueError(
                    'Each review image must be '
                    '5 MB or smaller.'
                )

            extension = Path(
                image.name
            ).suffix.lower()

            filename = (
                f'reviews/{product["_id"]}/'
                f'{uuid4().hex}{extension}'
            )

            saved_path = default_storage.save(
                filename,
                image,
            )

            saved_paths.append(
                saved_path
            )

            image_urls.append(
                default_storage.url(saved_path)
            )

        interaction_repo.create_review(
            product_id=product['_id'],
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
            images=image_urls,
        )

        _recalculate_product_rating(
            product['_id']
        )

        messages.success(
            request,
            'Your review has been submitted successfully.'
        )

    except ValueError as exc:
        for saved_path in saved_paths:
            if default_storage.exists(saved_path):
                default_storage.delete(saved_path)

        messages.error(
            request,
            str(exc),
        )

    return redirect(
        'product_detail',
        slug=product_slug,
    )


# ============================================================
# CV68 - Get Current User Review
# ============================================================

def my_review(request, product_slug):
    user_id = request.session.get('user_id')

    if not user_id:
        return JsonResponse({
            'authenticated': False,
            'exists': False,
        })

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        return JsonResponse({
            'error': 'Product not found',
        }, status=404)

    review = interaction_repo.get_user_review(
        product['_id'],
        user_id,
    )

    if not review:
        return JsonResponse({
            'authenticated': True,
            'exists': False,
        })

    return JsonResponse({
        'authenticated': True,
        'exists': True,
        'review': {
            'rating': review.get(
                'rating',
                0,
            ),
            'title': review.get(
                'title',
                '',
            ),
            'content': review.get(
                'content',
                '',
            ),
            'is_hidden': review.get(
                'is_hidden',
                False,
            ),
        },
    })


# ============================================================
# CV68 - Edit Review
# ============================================================

def edit_review(request, product_slug):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before editing a review.'
        )

        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    review = interaction_repo.get_user_review(
        product['_id'],
        user_id,
    )

    if not review:
        messages.error(
            request,
            'You have not reviewed this product.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    rating = request.POST.get('rating')
    title = request.POST.get(
        'title',
        '',
    ).strip()

    content = request.POST.get(
        'content',
        '',
    ).strip()

    if not rating:
        messages.error(
            request,
            'Please select a rating.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    try:
        interaction_repo.update_review(
            review['_id'],
            rating=rating,
            title=title,
            content=content,
        )

        _recalculate_product_rating(
            product['_id']
        )

        messages.success(
            request,
            'Your review has been updated successfully.'
        )

    except ValueError as exc:
        messages.error(
            request,
            str(exc),
        )

    return redirect(
        'product_detail',
        slug=product_slug,
    )


# ============================================================
# CV68 - Hide Review
# ============================================================

def hide_review(request, product_slug):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before hiding a review.'
        )

        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    review = interaction_repo.get_user_review(
        product['_id'],
        user_id,
    )

    if not review:
        messages.error(
            request,
            'You have not reviewed this product.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    interaction_repo.set_review_hidden(
        review['_id'],
        True,
    )

    _recalculate_product_rating(
        product['_id']
    )

    messages.success(
        request,
        'Your review has been hidden.'
    )

    return redirect(
        'product_detail',
        slug=product_slug,
    )


# ============================================================
# CV68 - Unhide Review
# ============================================================

def unhide_review(request, product_slug):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login first.'
        )

        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    review = interaction_repo.get_user_review(
        product['_id'],
        user_id,
    )

    if not review:
        messages.error(
            request,
            'You have not reviewed this product.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    interaction_repo.set_review_hidden(
        review['_id'],
        False,
    )

    _recalculate_product_rating(
        product['_id']
    )

    messages.success(
        request,
        'Your review is visible again.'
    )

    return redirect(
        'product_detail',
        slug=product_slug,
    )


# ============================================================
# CV42 / CV69 - Submit Comment / Question / Shop Reply
# ============================================================

def submit_comment(request, product_slug):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before posting a question.'
        )

        return redirect('accounts_login')

    try:
        account_user = accounts_repo.find_user_by_id(
            user_id
        )
    except (ValueError, TypeError, InvalidId):
        account_user = None

    if not account_user:
        request.session.pop('user_id', None)
        messages.error(
            request,
            'Your login session is no longer valid. Please login again.'
        )
        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    content = request.POST.get(
        'content',
        '',
    ).strip()

    parent_id = (
        request.POST.get('parent_id')
        or None
    )

    if not content:
        messages.error(
            request,
            'Please enter your question or reply.'
        )

        return redirect(
            'product_detail',
            slug=product_slug,
        )

    # CV69: the server decides whether this is an official shop reply.
    # Clients cannot promote their own comment by posting a flag.
    is_admin_reply = bool(
        parent_id
        and account_user.get('role') == accounts_repo.ROLE_ADMIN
    )

    try:
        interaction_repo.create_comment(
            product_id=product['_id'],
            user_id=user_id,
            content=content,
            parent_id=parent_id,
            is_admin_reply=is_admin_reply,
        )

        messages.success(
            request,
            (
                'Shop reply has been posted successfully.'
                if is_admin_reply
                else (
                    'Your reply has been posted successfully.'
                    if parent_id
                    else 'Your question has been posted successfully.'
                )
            )
        )

    except (ValueError, TypeError, InvalidId) as exc:
        messages.error(
            request,
            str(exc),
        )

    return redirect(
        'product_detail',
        slug=product_slug,
    )

# ============================================================
# CV69 - Edit Own Comment / Reply
# ============================================================

def edit_comment(request, product_slug, comment_id):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before editing a comment.'
        )
        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    content = request.POST.get(
        'content',
        '',
    ).strip()

    if not content:
        messages.error(
            request,
            'Comment content cannot be empty.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    try:
        updated = interaction_repo.update_comment(
            comment_id=comment_id,
            user_id=user_id,
            product_id=product['_id'],
            content=content,
        )

    except (ValueError, TypeError, InvalidId):
        messages.error(
            request,
            'Invalid comment.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    if not updated:
        messages.error(
            request,
            'Comment not found or you do not have permission to edit it.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    messages.success(
        request,
        'Your comment has been updated successfully.'
    )

    return redirect(
        'product_detail',
        slug=product_slug,
    )

# ============================================================
# CV69 - Hide Own Comment / Reply
# ============================================================

def hide_comment(request, product_slug, comment_id):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login before hiding a comment.'
        )
        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    try:
        updated = interaction_repo.set_own_comment_hidden(
            comment_id=comment_id,
            user_id=user_id,
            product_id=product['_id'],
            is_hidden=True,
        )
    except (ValueError, TypeError, InvalidId):
        messages.error(
            request,
            'Invalid comment.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    if not updated:
        messages.error(
            request,
            'Comment not found or you do not have permission to hide it.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    messages.success(
        request,
        'Your comment has been hidden.'
    )

    return redirect(
        'product_detail',
        slug=product_slug,
    )


# ============================================================
# CV69 - Unhide Own Comment / Reply
# ============================================================

def unhide_comment(request, product_slug, comment_id):
    if request.method != 'POST':
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(
            request,
            'Please login first.'
        )
        return redirect('accounts_login')

    product = catalogue_repo.get_product(
        product_slug
    )

    if not product:
        raise Http404('Product not found')

    try:
        updated = interaction_repo.set_own_comment_hidden(
            comment_id=comment_id,
            user_id=user_id,
            product_id=product['_id'],
            is_hidden=False,
        )
    except (ValueError, TypeError, InvalidId):
        messages.error(
            request,
            'Invalid comment.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    if not updated:
        messages.error(
            request,
            'Comment not found or you do not have permission to unhide it.'
        )
        return redirect(
            'product_detail',
            slug=product_slug,
        )

    messages.success(
        request,
        'Your comment is visible again.'
    )

    return redirect(
        'product_detail',
        slug=product_slug,
    )
