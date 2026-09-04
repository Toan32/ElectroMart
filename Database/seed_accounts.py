"""Create the demo accounts for the Accounts & B2B module (CV41 / CV43).

seed_data.py owns categories/brands/products; this script owns the four
collections of Backend/accounts/db.py: users, addresses, wholesale_profiles,
quotations. Without it the site has no admin account at all - register.html
only ever creates a "retail" user (see accounts/views.py), so nothing can
reach the admin_required URLs.

    python Database/seed_accounts.py            # upsert, keeps other users
    python Database/seed_accounts.py --reset    # wipe the 4 collections first
    python Database/seed_accounts.py --quiet    # do not print the password table

Unlike seed_data.py this is NOT destructive by default: it matches an account
by email and updates it, so re-running is safe and accounts a teammate
registered by hand survive.

Django is bootstrapped (seed_data.py does not need it) because passwords must
be hashed by the very same django.contrib.auth.hashers that
repo.check_password() verifies with at login. Every write goes through
accounts.repo, so the document shape stays defined in one place.

Connection settings come from the environment, same convention as
seed_data.py:
    MONGO_URI       default mongodb://localhost:27017/
    MONGO_DB_NAME   default electromart_db
"""
import argparse
import os
import sys

import django

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', 'Backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electromart.settings')
django.setup()

from accounts import repo                                  # noqa: E402
from accounts.db import (ADDRESSES, QUOTATIONS, USERS,      # noqa: E402
                         WHOLESALE_PROFILES, get_db)
from create_indexes import ensure_accounts_indexes         # noqa: E402

# One shared password for every demo account: this database only ever lives on
# a team machine, and a single password keeps the demo script short.
DEMO_PASSWORD = 'Demo@1234'
ADMIN_PASSWORD = 'Admin@1234'

ADMINS = [
    ('admin@electromart.vn', 'Quan Tri Vien', ADMIN_PASSWORD),
]

# (email, full_name, addresses); an address is
# (receiver_name, phone, province, district, detail)
RETAIL = [
    ('an.nguyen@example.com', 'Nguyen Van An', [
        ('Nguyen Van An', '0901234567', 'TP Ho Chi Minh', 'Quan 1', '12 Nguyen Hue'),
        ('Nguyen Van An', '0901234567', 'TP Ho Chi Minh', 'Quan 7', '45 Nguyen Thi Thap'),
    ]),
    ('binh.tran@example.com', 'Tran Thi Binh', [
        ('Tran Thi Binh', '0912345678', 'Ha Noi', 'Cau Giay', '88 Xuan Thuy'),
    ]),
    ('cuong.le@example.com', 'Le Manh Cuong', [
        ('Le Manh Cuong', '0923456789', 'Da Nang', 'Hai Chau', '21 Le Duan'),
    ]),
    ('dung.pham@example.com', 'Pham Tien Dung', []),
    ('em.hoang@example.com', 'Hoang Thi Em', []),
    ('phuc.vo@example.com', 'Vo Hong Phuc', []),
    ('giang.do@example.com', 'Do Truong Giang', []),
]

# (email, full_name, company_name, tax_code, company_address, review)
# review: 'approved' -> role becomes wholesale, 'pending' -> sits in the admin
# queue, 'rejected' -> exercises the reject_reason path of CV63.
WHOLESALE = [
    ('mua.hang@techviet.vn', 'Nguyen Quoc Hung', 'Cong ty TNHH Tech Viet',
     '0312345678', '150 Vo Van Ngan, Thu Duc, TP Ho Chi Minh', 'approved'),
    ('sales@dienlanhmienbac.vn', 'Tran Van Kien', 'Cong ty CP Dien Lanh Mien Bac',
     '0107654321', '25 Tran Duy Hung, Cau Giay, Ha Noi', 'approved'),
    ('info@robotics-lab.vn', 'Le Thanh Nam', 'Robotics Lab JSC',
     '0409876543', '77 Nguyen Van Linh, Hai Chau, Da Nang', 'pending'),
    ('contact@linhkien-abc.vn', 'Pham Minh Tuan', 'Cong ty ABC',
     '0100000000', '5 Le Loi, Ninh Kieu, Can Tho', 'rejected'),
]

REJECT_REASON = 'Anh chup giay phep kinh doanh khong ro, vui long gui lai.'


def upsert_user(email, full_name, password, role):
    """Create the account, or bring an existing one back to a known-good state.

    An account left over from a manual test is usually is_active=False (its
    activation email was never opened) and may carry a failed-login lock, so
    an update has to clear those as well - otherwise the seeded password still
    would not get anyone in.
    """
    existing = repo.find_user_by_email(email)
    if existing is None:
        user = repo.create_user(full_name, email, password, role)
        created = True
    else:
        user = existing
        repo.set_password(user['_id'], password)
        repo.update_profile(user['_id'], full_name=full_name)
        repo.set_role(user['_id'], role)
        repo.set_hidden(user['_id'], False)
        created = False

    repo.reset_failed_login(user['_id'])
    # Demo accounts skip email activation on purpose: with no SMTP configured
    # the console backend only prints the link, so nobody could click it.
    user = repo.activate_user(user['_id'])
    return user, created


def seed(reset=False, quiet=False):
    db = get_db()

    if reset:
        for name in (USERS, ADDRESSES, WHOLESALE_PROFILES, QUOTATIONS):
            db[name].delete_many({})
        print('Cleared users, addresses, wholesale_profiles, quotations.')

    ensure_accounts_indexes(db)
    print('Accounts indexes ready.')

    rows = []

    admin_id = None
    for email, full_name, password in ADMINS:
        user, created = upsert_user(email, full_name, password, repo.ROLE_ADMIN)
        admin_id = admin_id or user['_id']
        rows.append(('admin', email, password, repo.ROLE_ADMIN,
                     'new' if created else 'updated'))

    for email, full_name, addresses in RETAIL:
        user, created = upsert_user(email, full_name, DEMO_PASSWORD, repo.ROLE_RETAIL)
        if not repo.list_addresses(user['_id']):
            for receiver, phone, province, district, detail in addresses:
                repo.add_address(user['_id'], receiver, phone, province, district, detail)
        rows.append(('retail', email, DEMO_PASSWORD, repo.ROLE_RETAIL,
                     'new' if created else 'updated'))

    for email, full_name, company, tax_code, company_address, review in WHOLESALE:
        # Role stays retail until approve_wholesale() flips it, exactly like a
        # real application going through the admin queue (REQ-35).
        user, created = upsert_user(email, full_name, DEMO_PASSWORD, repo.ROLE_RETAIL)

        profile = repo.get_wholesale_profile_by_user(user['_id'])
        if profile is None:
            profile = repo.create_wholesale_profile(
                user['_id'], company, tax_code, company_address, full_name)
        else:
            profile = repo.update_wholesale_application(
                profile['_id'], company, tax_code, company_address, full_name)

        if review == 'approved':
            repo.approve_wholesale(profile['_id'], admin_id)
        elif review == 'rejected':
            repo.reject_wholesale(profile['_id'], admin_id, REJECT_REASON)

        role = repo.find_user_by_id(user['_id'])['role']
        rows.append(('b2b/' + review, email, DEMO_PASSWORD, role,
                     'new' if created else 'updated'))

    from django.conf import settings
    print('Seeded %d accounts into "%s": %d admin, %d retail, %d B2B.'
          % (len(rows), settings.MONGO_DB_NAME,
             len(ADMINS), len(RETAIL), len(WHOLESALE)))

    if not quiet:
        print()
        print('%-14s %-28s %-12s %-10s %s'
              % ('KIND', 'EMAIL', 'PASSWORD', 'ROLE', 'STATE'))
        print('-' * 78)
        for kind, email, password, role, state in rows:
            print('%-14s %-28s %-12s %-10s %s' % (kind, email, password, role, state))
        print()
        print('Log in at %s/accounts/login/' % settings.SITE_BASE_URL)
        print('Admin pages: /admin/users/  /admin/products/  /admin-dashboard/')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Seed the ElectroMart demo accounts')
    ap.add_argument('--reset', action='store_true',
                    help='delete every user, address, wholesale profile and quotation first')
    ap.add_argument('--quiet', action='store_true',
                    help='do not print the credentials table')
    seed(**vars(ap.parse_args()))
