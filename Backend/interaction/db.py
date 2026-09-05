"""MongoDB connection for the Interaction module.

MongoClient keeps its own connection pool, so one shared client
per process is enough.

Indexes for these collections are created in:
Database/create_indexes.py
"""

from django.conf import settings
from pymongo import MongoClient


_client = None


# ============================================================
# Interaction collection names - CV42
# ============================================================

REVIEWS = 'reviews'
COMMENTS = 'comments'
WISHLISTS = 'wishlists'
FEEDBACK = 'feedback'
ANNOUNCEMENTS = 'announcements'


def get_client():
    global _client

    if _client is None:
        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000
        )

    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]