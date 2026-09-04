from pathlib import Path
from uuid import uuid4

from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import Http404
from django.shortcuts import redirect

from catalogue import repo as catalogue_repo
from . import repo as interaction_repo


MAX_REVIEW_IMAGES = 5
MAX_REVIEW_IMAGE_SIZE = 5 * 1024 * 1024


def submit_review(request, product_slug):
    if request.method != 'POST':
        return redirect('product_detail', slug=product_slug)

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, 'Please login before submitting a review.')
        return redirect('accounts_login')

    product = catalogue_repo.get_product(product_slug)

    if not product:
        raise Http404('Product not found')

    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    uploaded_images = request.FILES.getlist('images')

    if not rating:
        messages.error(request, 'Please select a rating.')
        return redirect('product_detail', slug=product_slug)

    if interaction_repo.get_user_review(product['_id'], user_id):
        messages.error(request, 'This user has already reviewed this product.')
        return redirect('product_detail', slug=product_slug)

    saved_paths = []
    image_urls = []

    try:
        if len(uploaded_images) > MAX_REVIEW_IMAGES:
            raise ValueError(f'You can upload up to {MAX_REVIEW_IMAGES} images.')

        for image in uploaded_images:
            if not image.content_type or not image.content_type.startswith('image/'):
                raise ValueError('Only image files are allowed.')

            if image.size > MAX_REVIEW_IMAGE_SIZE:
                raise ValueError('Each review image must be 5 MB or smaller.')

            extension = Path(image.name).suffix.lower()
            filename = f'reviews/{product["_id"]}/{uuid4().hex}{extension}'
            saved_path = default_storage.save(filename, image)

            saved_paths.append(saved_path)
            image_urls.append(default_storage.url(saved_path))

        interaction_repo.create_review(
            product_id=product['_id'],
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
            images=image_urls,
        )

        messages.success(request, 'Your review has been submitted successfully.')

    except ValueError as exc:
        for saved_path in saved_paths:
            if default_storage.exists(saved_path):
                default_storage.delete(saved_path)

        messages.error(request, str(exc))

    return redirect('product_detail', slug=product_slug)

def submit_comment(request, product_slug):
    if request.method != 'POST':
        return redirect('product_detail', slug=product_slug)

    user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, 'Please login before posting a question.')
        return redirect('accounts_login')

    product = catalogue_repo.get_product(product_slug)

    if not product:
        raise Http404('Product not found')

    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id') or None

    if not content:
        messages.error(request, 'Please enter your question.')
        return redirect('product_detail', slug=product_slug)

    try:
        interaction_repo.create_comment(
            product_id=product['_id'],
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )

        messages.success(request, 'Your question has been posted successfully.')

    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('product_detail', slug=product_slug)