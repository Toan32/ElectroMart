"""MongoDB connection shared by the whole process.

MongoClient already keeps an internal connection pool, so one instance per
process is enough. Index creation lives in Database/create_indexes.py so that
the Database folder owns the schema.
"""
from django.conf import settings
from pymongo import MongoClient

_client = None

# Collection names, kept here so the strings are not repeated across modules
CATEGORIES = 'categories'
BRANDS = 'brands'
PRODUCTS = 'products'


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]
