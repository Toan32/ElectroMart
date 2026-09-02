"""Create indexes for collections that seed_data.py does not own.

seed_data.py already builds categories/brands/products and their indexes
(see ensure_indexes() there). This script is for the collections created at
runtime by the other modules instead of by the seeder - starting with the
Accounts & B2B module (CV41). Run it once after MongoDB is up:

    python Database/create_indexes.py

Connection settings come from the environment, same convention as
seed_data.py:
    MONGO_URI       default mongodb://localhost:27017/
    MONGO_DB_NAME   default electromart_db

Each other module should add its own `ensure_*_indexes(db)` function below
and call it from main() - keeps every collection's index list in one place
instead of scattered across the codebase.
"""
import os

from pymongo import ASCENDING, MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')


def ensure_accounts_indexes(db):
    """Accounts & B2B module (Backend/accounts/db.py) - CV41."""
    users = db['users']
    users.create_index([('email', ASCENDING)], unique=True)
    users.create_index([('role', ASCENDING), ('is_active', ASCENDING)])

    addresses = db['addresses']
    addresses.create_index([('user_id', ASCENDING)])

    wholesale = db['wholesale_profiles']
    wholesale.create_index([('user_id', ASCENDING)], unique=True)
    wholesale.create_index([('approval_status', ASCENDING)])
    wholesale.create_index([('tax_code', ASCENDING)])

    quotations = db['quotations']
    quotations.create_index([('user_id', ASCENDING)])
    quotations.create_index([('status', ASCENDING)])


# TODO (other modules, not done in this pass):
#   def ensure_orders_indexes(db): ...       # module Ban hang & Thanh toan


def ensure_interaction_indexes(db):
    """Interaction module - CV42."""

    # --------------------------------------------------------
    # Reviews
    # One user can review one product only once.
    # --------------------------------------------------------
    reviews = db['reviews']

    reviews.create_index(
        [
            ('product_id', ASCENDING),
            ('user_id', ASCENDING),
        ],
        unique=True,
        name='uniq_review_product_user',
    )

    reviews.create_index(
        [('product_id', ASCENDING)],
        name='idx_reviews_product',
    )

    reviews.create_index(
        [('user_id', ASCENDING)],
        name='idx_reviews_user',
    )

    # --------------------------------------------------------
    # Comments
    # parent_id references another comment for replies.
    # --------------------------------------------------------
    comments = db['comments']

    comments.create_index(
        [('product_id', ASCENDING)],
        name='idx_comments_product',
    )

    comments.create_index(
        [('user_id', ASCENDING)],
        name='idx_comments_user',
    )

    comments.create_index(
        [('parent_id', ASCENDING)],
        name='idx_comments_parent',
    )

    # --------------------------------------------------------
    # Wishlist
    # One wishlist document per user.
    # --------------------------------------------------------
    wishlists = db['wishlists']

    wishlists.create_index(
        [('user_id', ASCENDING)],
        unique=True,
        name='uniq_wishlist_user',
    )

    # --------------------------------------------------------
    # Feedback
    # --------------------------------------------------------
    feedback = db['feedback']

    feedback.create_index(
        [('user_id', ASCENDING)],
        name='idx_feedback_user',
    )

    feedback.create_index(
        [('status', ASCENDING)],
        name='idx_feedback_status',
    )

    # --------------------------------------------------------
    # Announcements
    # --------------------------------------------------------
    announcements = db['announcements']

    announcements.create_index(
        [('is_active', ASCENDING)],
        name='idx_announcements_active',
    )

    announcements.create_index(
        [('created_at', ASCENDING)],
        name='idx_announcements_created_at',
    )


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    ensure_accounts_indexes(db)
    ensure_interaction_indexes(db)

    print('Accounts & B2B indexes created on database "%s".' % DB_NAME)
    print('Interaction indexes created on database "%s".' % DB_NAME)


if __name__ == '__main__':
    main()
