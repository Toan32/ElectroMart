"""Data access layer for the Accounts & B2B module.

Mirrors the repository pattern already used in catalogue/repo.py: no Django
ORM, no models.py, every function talks to MongoDB directly through db.py.
"User" is a plain MongoDB document (see CV12_ClassDiagram_Account.txt), not a
subclass of AbstractUser - the project has no relational database configured
(DATABASES = {} in settings.py), so login/registration are handled entirely
in this module with django.contrib.auth.hashers for password hashing and
request.session['user_id'] for the logged-in state.

Sections below follow the 4 collections from db.py: User, Address,
WholesaleProfile, Quotation.
"""
from datetime import datetime, timedelta

from bson import ObjectId
from django.contrib.auth.hashers import check_password as _check_password
from django.contrib.auth.hashers import make_password as _make_password

from .db import ADDRESSES, QUOTATIONS, USERS, WHOLESALE_PROFILES, get_db

# ---------------------------------------------------------------- constants
ROLE_RETAIL = 'retail'
ROLE_WHOLESALE = 'wholesale'
ROLE_ADMIN = 'admin'

APPROVAL_PENDING = 'pending'
APPROVAL_APPROVED = 'approved'
APPROVAL_REJECTED = 'rejected'

QUOTE_PENDING = 'pending'
QUOTE_QUOTED = 'quoted'
QUOTE_ACCEPTED = 'accepted'
QUOTE_REJECTED = 'rejected'
QUOTE_EXPIRED = 'expired'

MAX_FAILED_LOGIN = 5
LOCK_MINUTES = 15


# ------------------------------------------------------------ password hash
def hash_password(raw_password):
    """Thin wrapper so views.py never imports django.contrib.auth directly."""
    return _make_password(raw_password)


def check_password(raw_password, password_hash):
    return _check_password(raw_password, password_hash)


# -------------------------------------------------------------------- User
def create_user(full_name, email, raw_password, role=ROLE_RETAIL):
    db = get_db()
    now = datetime.utcnow()
    doc = {
        'full_name': full_name,
        'email': email.strip().lower(),
        'password_hash': hash_password(raw_password),
        'role': role,
        'is_active': False,       # flips to True once the activation email link is used
        'is_hidden': False,
        'email_verified': False,
        'avatar_url': '',
        'failed_login_count': 0,
        'locked_until': None,
        'created_at': now,
        'updated_at': now,
    }
    result = db[USERS].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def find_user_by_email(email):
    return get_db()[USERS].find_one({'email': email.strip().lower()})


def find_user_by_id(user_id):
    return get_db()[USERS].find_one({'_id': _oid(user_id)})


def activate_user(user_id):
    return _update_user(user_id, {'is_active': True, 'email_verified': True})


# --- one-time tokens for "activate account" / "forgot password" email links.
# Kept as fields on the user document itself (simpler than a separate
# collection for a project this size); each call overwrites the previous
# token so only the most recently sent link works.
def set_activation_token(user_id, token, expires_at):
    return _update_user(user_id, {'activation_token': token, 'activation_expires': expires_at})


def find_user_by_activation_token(token):
    return get_db()[USERS].find_one({'activation_token': token})


def set_reset_token(user_id, token, expires_at):
    return _update_user(user_id, {'reset_token': token, 'reset_expires': expires_at})


def find_user_by_reset_token(token):
    return get_db()[USERS].find_one({'reset_token': token})


def clear_reset_token(user_id):
    return _update_user(user_id, {'reset_token': None, 'reset_expires': None})


def update_profile(user_id, full_name=None, avatar_url=None):
    fields = {}
    if full_name is not None:
        fields['full_name'] = full_name
    if avatar_url is not None:
        fields['avatar_url'] = avatar_url
    if not fields:
        return None
    return _update_user(user_id, fields)


def set_password(user_id, raw_password):
    return _update_user(user_id, {'password_hash': hash_password(raw_password)})


def set_role(user_id, role):
    return _update_user(user_id, {'role': role})


def set_hidden(user_id, is_hidden):
    """Admin lock/hide an account - data is kept, never deleted (CV63)."""
    return _update_user(user_id, {'is_hidden': is_hidden})


# --- login attempt counter (CV58, "khoá form đăng nhập 15 phút sau 5 lần sai")
def is_locked(user):
    locked_until = user.get('locked_until')
    return bool(locked_until and locked_until > datetime.utcnow())


def register_failed_login(user_id):
    db = get_db()
    user = db[USERS].find_one({'_id': _oid(user_id)})
    count = (user.get('failed_login_count', 0) if user else 0) + 1
    fields = {'failed_login_count': count}
    if count >= MAX_FAILED_LOGIN:
        fields['locked_until'] = datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)
    return _update_user(user_id, fields)


def reset_failed_login(user_id):
    return _update_user(user_id, {'failed_login_count': 0, 'locked_until': None})


def _update_user(user_id, fields):
    db = get_db()
    fields = dict(fields, updated_at=datetime.utcnow())
    db[USERS].update_one({'_id': _oid(user_id)}, {'$set': fields})
    return db[USERS].find_one({'_id': _oid(user_id)})


# ----------------------------------------------------------------- Address
def list_addresses(user_id):
    return list(get_db()[ADDRESSES].find({'user_id': _oid(user_id)}).sort('is_default', -1))


def get_address(address_id):
    return get_db()[ADDRESSES].find_one({'_id': _oid(address_id)})


def add_address(user_id, receiver_name, phone, province, district, detail,
                 is_default=False):
    db = get_db()
    if is_default or not list_addresses(user_id):
        # First address for a user is always the default one.
        _clear_default_address(user_id)
        is_default = True
    doc = {
        'user_id': _oid(user_id),
        'receiver_name': receiver_name,
        'phone': phone,
        'province': province,
        'district': district,
        'detail': detail,
        'is_default': is_default,
    }
    result = db[ADDRESSES].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def update_address(address_id, **fields):
    db = get_db()
    db[ADDRESSES].update_one({'_id': _oid(address_id)}, {'$set': fields})
    return db[ADDRESSES].find_one({'_id': _oid(address_id)})


def delete_address(address_id):
    return get_db()[ADDRESSES].delete_one({'_id': _oid(address_id)}).deleted_count


def set_default_address(user_id, address_id):
    """Guarantee only one default address per user (REQ-33)."""
    _clear_default_address(user_id)
    return update_address(address_id, is_default=True)


def _clear_default_address(user_id):
    get_db()[ADDRESSES].update_many({'user_id': _oid(user_id)}, {'$set': {'is_default': False}})


# --------------------------------------------------------- WholesaleProfile
def create_wholesale_profile(user_id, company_name, tax_code, company_address,
                              contact_person):
    db = get_db()
    doc = {
        'user_id': _oid(user_id),
        'company_name': company_name,
        'tax_code': tax_code,
        'company_address': company_address,
        'contact_person': contact_person,
        'approval_status': APPROVAL_PENDING,
        'reject_reason': '',
        'submitted_at': datetime.utcnow(),
        'reviewed_at': None,
        'reviewed_by': None,
    }
    result = db[WHOLESALE_PROFILES].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def get_wholesale_profile_by_user(user_id):
    return get_db()[WHOLESALE_PROFILES].find_one({'user_id': _oid(user_id)})


def update_wholesale_application(profile_id, company_name, tax_code, company_address,
                                  contact_person):
    """Lets a customer complete/correct their application while it is still
    pending - e.g. the quick sign-up at registration only collects
    company_name + tax_code, so the full form (CV61) fills in the rest."""
    db = get_db()
    return db[WHOLESALE_PROFILES].find_one_and_update(
        {'_id': _oid(profile_id)},
        {'$set': {
            'company_name': company_name, 'tax_code': tax_code,
            'company_address': company_address, 'contact_person': contact_person,
        }},
        return_document=True,
    )


def list_pending_wholesale():
    return list(get_db()[WHOLESALE_PROFILES].find({'approval_status': APPROVAL_PENDING}))


def approve_wholesale(profile_id, admin_id):
    db = get_db()
    profile = db[WHOLESALE_PROFILES].find_one_and_update(
        {'_id': _oid(profile_id)},
        {'$set': {
            'approval_status': APPROVAL_APPROVED,
            'reject_reason': '',
            'reviewed_at': datetime.utcnow(),
            'reviewed_by': _oid(admin_id),
        }},
        return_document=True,
    )
    if profile:
        set_role(profile['user_id'], ROLE_WHOLESALE)
    return profile


def reject_wholesale(profile_id, admin_id, reason):
    """`reason` is required (CV14/CV63): the admin must justify a rejection."""
    if not reason or not reason.strip():
        raise ValueError('reject_reason is required')
    db = get_db()
    return db[WHOLESALE_PROFILES].find_one_and_update(
        {'_id': _oid(profile_id)},
        {'$set': {
            'approval_status': APPROVAL_REJECTED,
            'reject_reason': reason.strip(),
            'reviewed_at': datetime.utcnow(),
            'reviewed_by': _oid(admin_id),
        }},
        return_document=True,
    )


def is_approved_wholesale(user_id):
    profile = get_wholesale_profile_by_user(user_id)
    return bool(profile and profile['approval_status'] == APPROVAL_APPROVED)


# ---------------------------------------------------------------- Quotation
def create_quotation(user_id, items):
    """`items` is a list of QuoteItem dicts (embedded, see CV12).

    Each item: {part_number, product_id, quantity, note, unit_price, matched}
    """
    db = get_db()
    doc = {
        'user_id': _oid(user_id),
        'status': QUOTE_PENDING,
        'valid_until': None,
        'order_id': None,
        'created_at': datetime.utcnow(),
        'items': items,
    }
    result = db[QUOTATIONS].insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def get_quotation(quotation_id):
    return get_db()[QUOTATIONS].find_one({'_id': _oid(quotation_id)})


def list_quotations_by_user(user_id):
    return list(get_db()[QUOTATIONS].find({'user_id': _oid(user_id)}).sort('created_at', -1))


def submit_quote_prices(quotation_id, items, valid_until):
    """Admin fills in unit_price per line and a validity date (CV62 step 3)."""
    db = get_db()
    return db[QUOTATIONS].find_one_and_update(
        {'_id': _oid(quotation_id)},
        {'$set': {'items': items, 'valid_until': valid_until, 'status': QUOTE_QUOTED}},
        return_document=True,
    )


def accept_quotation(quotation_id, order_id):
    """Customer accepts the quote -> it turns into an order (CV62 step 4)."""
    db = get_db()
    return db[QUOTATIONS].find_one_and_update(
        {'_id': _oid(quotation_id)},
        {'$set': {'status': QUOTE_ACCEPTED, 'order_id': _oid(order_id)}},
        return_document=True,
    )


# ----------------------------------------------------------------- helpers
def _oid(value):
    """Accept both an ObjectId and its string form, like catalogue does for slugs."""
    return value if isinstance(value, ObjectId) else ObjectId(value)
