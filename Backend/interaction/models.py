"""Document builders for the Interaction module.

The project uses PyMongo directly instead of Django ORM.
These helpers define the document shape before data is inserted into MongoDB.
"""

from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


def review_document(product_id, user_id, rating, title='', content='', images=None):
    rating = int(rating)

    if rating < 1 or rating > 5:
        raise ValueError('rating must be between 1 and 5')

    return {
        'product_id': product_id,
        'user_id': user_id,
        'rating': rating,
        'title': title.strip(),
        'content': content.strip(),
        'images': list(images or []),
        'is_hidden': False,
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }


def comment_document(product_id, user_id, content, parent_id=None):
    return {
        'product_id': product_id,
        'user_id': user_id,
        'parent_id': parent_id,
        'content': content.strip(),
        'is_hidden': False,
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }


def wishlist_document(user_id):
    return {
        'user_id': user_id,
        'product_ids': [],
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }


def feedback_document(name, email, subject, message, user_id=None):
    return {
        'user_id': user_id,
        'name': name.strip(),
        'email': email.strip().lower(),
        'subject': subject.strip(),
        'message': message.strip(),
        'status': 'new',
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }


def announcement_document(title, content, created_by=None):
    return {
        'title': title.strip(),
        'content': content.strip(),
        'created_by': created_by,
        'is_active': True,
        'created_at': now_utc(),
        'updated_at': now_utc(),
    }
