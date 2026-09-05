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

def create_review(product_id, user_id, rating, title='', content='', images=None):
    db = get_db()

    doc = review_document(
        product_id=_oid(product_id),
        user_id=_oid(user_id),
        rating=rating,
        title=title,
        content=content,
        images=images,
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



def admin_list_reviews(product_id=None, is_hidden=None):
    # CV71 moderation list.
    query = {}

    if product_id:
        query['product_id'] = _oid(product_id)

    if is_hidden is not None:
        query['is_hidden'] = bool(is_hidden)

    return list(
        get_db()[REVIEWS]
        .find(query)
        .sort('created_at', -1)
    )


def update_review(review_id, rating=None, title=None, content=None, images=None):
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

    if title is not None:
        fields['title'] = title.strip()

    if content is not None:
        fields['content'] = content.strip()

    if images is not None:
        fields['images'] = list(images)

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
    parent_id=None,
    is_admin_reply=False
):
    db = get_db()

    product_oid = _oid(product_id)
    parent_oid = _oid(parent_id)

    # If this is a reply, the parent comment must exist.
    if parent_oid is not None:
        parent = db[COMMENTS].find_one({
            '_id': parent_oid
        })

        if parent is None:
            raise ValueError(
                'Parent comment does not exist.'
            )

        # Do not allow replying to a comment from another product.
        if parent.get('product_id') != product_oid:
            raise ValueError(
                'Parent comment belongs to another product.'
            )

    doc = comment_document(
        product_id=product_oid,
        user_id=_oid(user_id),
        content=content,
        parent_id=parent_oid,
        is_admin_reply=is_admin_reply,
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



def admin_list_comments(product_id=None, is_hidden=None):
    # CV71 moderation list for technical Q&A/comments.
    query = {}

    if product_id:
        query['product_id'] = _oid(product_id)

    if is_hidden is not None:
        query['is_hidden'] = bool(is_hidden)

    return list(
        get_db()[COMMENTS]
        .find(query)
        .sort('created_at', -1)
    )


def update_comment(comment_id, user_id, product_id, content):
    content = (content or '').strip()

    if not content:
        raise ValueError(
            'Comment content cannot be empty.'
        )

    return get_db()[COMMENTS].find_one_and_update(
        {
            '_id': _oid(comment_id),
            'user_id': _oid(user_id),
            'product_id': _oid(product_id),
        },
        {
            '$set': {
                'content': content,
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
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


def set_own_comment_hidden(
    comment_id,
    user_id,
    product_id,
    is_hidden=True
):
    return get_db()[COMMENTS].find_one_and_update(
        {
            '_id': _oid(comment_id),
            'user_id': _oid(user_id),
            'product_id': _oid(product_id),
        },
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
    user_id=None,
    attachment=None,
):
    db = get_db()

    doc = feedback_document(
        name=name,
        email=email,
        subject=subject,
        message=message,
        user_id=_oid(user_id),
        attachment=attachment,
    )

    result = db[FEEDBACK].insert_one(doc)

    doc['_id'] = result.inserted_id
    return doc


def get_feedback(feedback_id):
    return get_db()[FEEDBACK].find_one({
        '_id': _oid(feedback_id)
    })


def list_feedback(status=None):
    query = {}

    if status:
        query['status'] = status

    return list(
        get_db()[FEEDBACK]
        .find(query)
        .sort('created_at', -1)
    )


def save_feedback_reply(
    feedback_id,
    message,
    replied_by=None,
    email_sent=False,
):
    message = str(message or '').strip()

    if not message:
        raise ValueError('Reply message cannot be empty.')

    reply = {
        'message': message,
        'replied_by': _oid(replied_by) if replied_by else None,
        'replied_at': now_utc(),
        'email_sent': bool(email_sent),
    }

    return get_db()[FEEDBACK].find_one_and_update(
        {'_id': _oid(feedback_id)},
        {
            '$set': {
                'admin_reply': reply,
                'updated_at': now_utc(),
            }
        },
        return_document=ReturnDocument.AFTER,
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
