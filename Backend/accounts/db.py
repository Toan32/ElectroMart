"""MongoDB connection for the Accounts & B2B module.

Reuses the same connect-once pattern as catalogue/db.py (one MongoClient per
process, its own internal pool). Index creation lives in
Database/create_indexes.py so that the Database folder owns the schema.
"""
from django.conf import settings
from pymongo import MongoClient

_client = None

# Collection names, kept here so the strings are not repeated across modules.
# See CV12_ClassDiagram_Account.txt for the attribute list of each one.
USERS = 'users'
ADDRESSES = 'addresses'
WHOLESALE_PROFILES = 'wholesale_profiles'
QUOTATIONS = 'quotations'


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]
