"""MongoDB connection for the Sales & Payment module (CV40).

Same connect-once pattern as catalogue/db.py and accounts/db.py: one
MongoClient per process, its own internal pool. Index creation lives in
Database/create_indexes.py so that the Database folder owns the schema.
"""
from django.conf import settings
from pymongo import MongoClient

_client = None

# Collection names, kept here so the strings are not repeated across modules.
# See CV11_ClassDiagram_Sales.txt for the attribute list of each one.
ORDERS = 'orders'
COUPONS = 'coupons'


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]
