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

from pymongo import ASCENDING, DESCENDING, MongoClient

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


def ensure_sales_indexes(db):
    """Sales & Payment module (Backend/sales/db.py) - CV40."""
    orders = db['orders']
    # Unique: repo.next_order_number() reads the highest number and adds one,
    # so two orders placed in the same instant must not both be allowed to
    # save the same code.
    orders.create_index([('order_code', ASCENDING)], unique=True)
    orders.create_index([('order_no', DESCENDING)])
    orders.create_index([('status', ASCENDING), ('created_at', DESCENDING)])
    orders.create_index([('created_at', DESCENDING)])
    orders.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])
    orders.create_index([('phone', ASCENDING)])
    orders.create_index([('email', ASCENDING)])

    coupons = db['coupons']
    coupons.create_index([('code', ASCENDING)], unique=True)
    coupons.create_index([('is_active', ASCENDING)])


# TODO (other modules, not done in this pass):
#   def ensure_interaction_indexes(db): ...  # module Quan tri danh muc & Tuong tac


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    ensure_accounts_indexes(db)
    ensure_sales_indexes(db)
    print('Accounts & B2B and Sales indexes created on database "%s".' % DB_NAME)


if __name__ == '__main__':
    main()
