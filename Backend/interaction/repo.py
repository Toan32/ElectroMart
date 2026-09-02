"""Data access layer for the Interaction module.

All data is stored directly in MongoDB through PyMongo.
No Django ORM is used.
"""

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .db import (
    REVIEWS,
    COMMENTS,
    WISHLISTS,
    FEEDBACK,
    ANNOUNCEMENTS,
    get_db,
)

from .models import (
    now_utc,
    review_document,
    comment_document,
    wishlist_document,
    feedback_document,
    announcement_document,
)


# ============================================================
# Helpers
# ============================================================

def _oid(value):
    """Accept ObjectId or string ObjectId."""
    if value is None:
        return None

    return value if isinstance(value, ObjectId) else ObjectId(value)


# ============================================================
# Review
# ============================================================

def create_review(product_id, user_id, rating, content=''):
    db = get_db()

    doc = review_document(
        product_id=_oid(product_id),
        user_id=_oid(user_id),
        rating=rating,
        content=content,
    )

    try:
        result = db[REVIEWS].insert_one(doc)
    except DuplicateKeyError:
        raise ValueError(
            'This user has already reviewed this product.'
        )

    doc['_id'] = result.inserted_id
    return doc


def get_review(review_id):
    return get_db()[REVIEWS].find_one({
        '_id': _oid(review_id)
    })


def get_user_review(product_id, user_id):
    return get_db()[REVIEWS].find_one({
        'product_id': _oid(product_id),
        'user_id': _oid(user_id),
    })


def list_reviews(product_id, include_hidden=False):
    query = {
        'product_id': _oid(product_id)
    }

    if not include_hidden:
        query['is_hidden'] = False

    return list(
        get_db()[REVIEWS]
        .find(query)
        .sort('created_at', -1)
    )


def update_review(review_id, rating=None, content=None):
    fields = {
        'updated_at': now_utc()
    }

    if rating is not None:
        rating = int(rating)

        if rating < 1 or rating > 5:
            raise ValueError(
                'rating must be between 1 and 5'
            )

        fields['rating'] = rating

    if content is not None:
        fields['content'] = content.strip()

    return get_db()[REVIEWS].find_one_and_update(
        {'_id': _oid(review_id)},
        {'$set': fields},
        return_document=ReturnDocument.AFTER,
    )


def set_review_hidden(review_id, is_hidden=True):
    return get_db()[REVIEWS].find_one_and_update(
        {'_id': _oid(review_id)},
        {
            '$set': {
                'is_hidden': bool(is_hidden),
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )


# ============================================================
# Comment
# ============================================================

def create_comment(
    product_id,
    user_id,
    content,
    parent_id=None
):
    db = get_db()

    product_oid = _oid(product_id)
    parent_oid = _oid(parent_id)

    # Nếu là reply thì comment cha phải tồn tại.
    if parent_oid is not None:
        parent = db[COMMENTS].find_one({
            '_id': parent_oid
        })

        if parent is None:
            raise ValueError(
                'Parent comment does not exist.'
            )

        # Không cho reply comment của product khác.
        if parent.get('product_id') != product_oid:
            raise ValueError(
                'Parent comment belongs to another product.'
            )

    doc = comment_document(
        product_id=product_oid,
        user_id=_oid(user_id),
        content=content,
        parent_id=parent_oid,
    )

    result = db[COMMENTS].insert_one(doc)

    doc['_id'] = result.inserted_id
    return doc


def get_comment(comment_id):
    return get_db()[COMMENTS].find_one({
        '_id': _oid(comment_id)
    })


def list_comments(product_id, include_hidden=False):
    query = {
        'product_id': _oid(product_id)
    }

    if not include_hidden:
        query['is_hidden'] = False

    return list(
        get_db()[COMMENTS]
        .find(query)
        .sort('created_at', 1)
    )


def set_comment_hidden(comment_id, is_hidden=True):
    return get_db()[COMMENTS].find_one_and_update(
        {'_id': _oid(comment_id)},
        {
            '$set': {
                'is_hidden': bool(is_hidden),
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )


# ============================================================
# Wishlist
# ============================================================

def get_wishlist(user_id):
    return get_db()[WISHLISTS].find_one({
        'user_id': _oid(user_id)
    })


def create_wishlist(user_id):
    db = get_db()

    doc = wishlist_document(
        user_id=_oid(user_id)
    )

    try:
        result = db[WISHLISTS].insert_one(doc)
    except DuplicateKeyError:
        return get_wishlist(user_id)

    doc['_id'] = result.inserted_id
    return doc


def add_to_wishlist(user_id, product_id):
    user_oid = _oid(user_id)
    product_oid = _oid(product_id)
    now = now_utc()

    return get_db()[WISHLISTS].find_one_and_update(
        {'user_id': user_oid},
        {
            '$setOnInsert': {
                'user_id': user_oid,
                'created_at': now,
            },
            '$set': {
                'updated_at': now,
            },
            '$addToSet': {
                'product_ids': product_oid,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def remove_from_wishlist(user_id, product_id):
    return get_db()[WISHLISTS].find_one_and_update(
        {
            'user_id': _oid(user_id)
        },
        {
            '$pull': {
                'product_ids': _oid(product_id)
            },
            '$set': {
                'updated_at': now_utc()
            },
        },
        return_document=ReturnDocument.AFTER,
    )


def is_in_wishlist(user_id, product_id):
    return get_db()[WISHLISTS].find_one({
        'user_id': _oid(user_id),
        'product_ids': _oid(product_id),
    }) is not None


# ============================================================
# Feedback
# ============================================================

def create_feedback(
    name,
    email,
    subject,
    message,
    user_id=None
):
    db = get_db()

    doc = feedback_document(
        name=name,
        email=email,
        subject=subject,
        message=message,
        user_id=_oid(user_id),
    )

    result = db[FEEDBACK].insert_one(doc)

    doc['_id'] = result.inserted_id
    return doc


def list_feedback(status=None):
    query = {}

    if status:
        query['status'] = status

    return list(
        get_db()[FEEDBACK]
        .find(query)
        .sort('created_at', -1)
    )


def update_feedback_status(feedback_id, status):
    allowed = {
        'new',
        'processing',
        'resolved',
    }

    if status not in allowed:
        raise ValueError(
            'Invalid feedback status.'
        )

    return get_db()[FEEDBACK].find_one_and_update(
        {'_id': _oid(feedback_id)},
        {
            '$set': {
                'status': status,
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )


# ============================================================
# Announcement
# ============================================================

def create_announcement(
    title,
    content,
    created_by=None
):
    db = get_db()

    doc = announcement_document(
        title=title,
        content=content,
        created_by=_oid(created_by),
    )

    result = db[ANNOUNCEMENTS].insert_one(doc)

    doc['_id'] = result.inserted_id
    return doc


def list_announcements(active_only=True):
    query = {}

    if active_only:
        query['is_active'] = True

    return list(
        get_db()[ANNOUNCEMENTS]
        .find(query)
        .sort('created_at', -1)
    )


def set_announcement_active(
    announcement_id,
    is_active=True
):
    return get_db()[ANNOUNCEMENTS].find_one_and_update(
        {'_id': _oid(announcement_id)},
        {
            '$set': {
                'is_active': bool(is_active),
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )