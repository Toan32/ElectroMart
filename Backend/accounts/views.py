"""Views for the Accounts & B2B module (Viec 9, 11, 12, 13, 14 / CV58, CV60,
CV61, CV62, CV63). Session-based auth, no django.contrib.auth - see
Backend/accounts/repo.py and Docs1GioiThieuChung.txt Phan V for why.
"""
import os
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import redirect, render

from . import bom_import, forms, mailer, repo
from .decorators import admin_required, current_user, login_required, owner_required, wholesale_required

ACTIVATION_HOURS = 24
RESET_HOURS = 1

LOGIN_NOTICES = {
    'registered': 'Account created. Please check your email to activate your account.',
    'registered_no_email': 'Account created, but the activation email could not be sent. '
                           'Please contact support to have your account activated.',
    'activated': 'Your account is now active. You can log in.',
    'reset_sent': 'If that email is registered, a reset link has been sent.',
    'password_reset': 'Your password has been changed. Please log in again.',
    'logged_out': 'You have been logged out.',
}


# ------------------------------------------------------------- register / login
def register(request):
    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Role stays "retail" no matter what is picked here - REQ-35
            # requires admin approval first; repo.approve_wholesale() is the
            # only place role actually switches to "wholesale".
            user = repo.create_user(data['full_name'], data['email'], data['password'], repo.ROLE_RETAIL)

            if data['account_type'] == 'wholesale':
                repo.create_wholesale_profile(
                    user['_id'], data['company_name'], data['tax_code'], '', data['full_name'])

            token = secrets.token_urlsafe(32)
            repo.set_activation_token(user['_id'], token, datetime.utcnow() + timedelta(hours=ACTIVATION_HOURS))
            sent = mailer.send_activation_email(user, token)

            # The account exists either way, so say so plainly instead of
            # telling someone to check an inbox nothing was delivered to.
            notice = 'registered' if sent else 'registered_no_email'
            return redirect('%s?notice=%s' % (_url('accounts_login'), notice))
        return render(request, 'accounts/register.html', {'form': form})
    return render(request, 'accounts/register.html', {'page_title': 'Register - ElectroMart'})


def activate(request, token):
    user = repo.find_user_by_activation_token(token)
    if user and user.get('activation_expires') and user['activation_expires'] > datetime.utcnow():
        repo.activate_user(user['_id'])
        repo.set_activation_token(user['_id'], None, None)
        return redirect('%s?notice=activated' % _url('accounts_login'))
    return render(request, 'accounts/login.html', {
        'page_title': 'Login - ElectroMart',
        'form_error': 'This activation link is invalid or has expired.',
    })


def login_view(request):
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        error = None
        user = None
        if form.is_valid():
            email, password = form.cleaned_data['email'], form.cleaned_data['password']
            user = repo.find_user_by_email(email)

            if user and repo.is_locked(user):
                error = 'This account is temporarily locked. Please try again later.'
            elif not user or not repo.check_password(password, user['password_hash']):
                # Same generic message whether the email exists or not, so a
                # visitor cannot use this form to discover registered emails.
                error = 'Email or password is incorrect.'
                if user:
                    repo.register_failed_login(user['_id'])
            elif user.get('is_hidden'):
                error = 'This account has been disabled. Please contact support.'
            elif not user.get('is_active'):
                error = 'Please activate your account first - check your email.'

            if error is None and user:
                repo.reset_failed_login(user['_id'])
                request.session['user_id'] = str(user['_id'])
                if form.cleaned_data.get('remember'):
                    request.session.set_expiry(60 * 60 * 24 * 14)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # until the browser closes
                _merge_cart_session(request)
                next_url = request.GET.get('next') or _url('accounts_profile')
                return redirect(next_url)
        else:
            error = 'Please enter a valid email and password.'
        return render(request, 'accounts/login.html', {'form_error': error})

    return render(request, 'accounts/login.html', {
        'page_title': 'Login - ElectroMart',
        'notice': LOGIN_NOTICES.get(request.GET.get('notice')),
    })


def logout_view(request):
    request.session.pop('user_id', None)
    return redirect('%s?notice=logged_out' % _url('accounts_login'))


def _merge_cart_session(request):
    """Placeholder hook for the Sales module's merge-cart-on-login step
    (Viec 9 step 4) - calls it only if that module has registered it, so
    accounts/ does not hard-depend on a module owned by a teammate."""
    merge = getattr(settings, 'CART_MERGE_ON_LOGIN', None)
    if callable(merge):
        merge(request)


# ------------------------------------------------------------ forgot password
def forgot_password(request):
    if request.method == 'POST':
        form = forms.ForgotPasswordForm(request.POST)
        if form.is_valid():
            user = repo.find_user_by_email(form.cleaned_data['email'])
            if user:
                token = secrets.token_urlsafe(32)
                repo.set_reset_token(user['_id'], token, datetime.utcnow() + timedelta(hours=RESET_HOURS))
                mailer.send_password_reset_email(user, token)
            # Same redirect whether or not the email was found (Viec 17 -
            # do not reveal which emails are registered).
            return redirect('%s?notice=reset_sent' % _url('accounts_login'))
        return render(request, 'accounts/forgot_password.html', {'form': form})
    return render(request, 'accounts/forgot_password.html', {'page_title': 'Forgot password - ElectroMart'})


def reset_password(request, token):
    user = repo.find_user_by_reset_token(token)
    valid = bool(user and user.get('reset_expires') and user['reset_expires'] > datetime.utcnow())

    if request.method == 'POST':
        if not valid:
            return render(request, 'accounts/reset_password.html', {'invalid': True})
        form = forms.ResetPasswordForm(request.POST)
        if form.is_valid():
            repo.set_password(user['_id'], form.cleaned_data['password'])
            repo.clear_reset_token(user['_id'])
            return redirect('%s?notice=password_reset' % _url('accounts_login'))
        return render(request, 'accounts/reset_password.html', {'form': form, 'valid': True})

    return render(request, 'accounts/reset_password.html', {
        'page_title': 'Reset password - ElectroMart', 'valid': valid, 'invalid': not valid})


# ------------------------------------------------------------------- profile
@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'page_title': 'My account - ElectroMart', 'user': current_user(request)})


@login_required
def edit_profile(request):
    user = current_user(request)
    if request.method == 'POST':
        form = forms.ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            avatar_url = user.get('avatar_url', '')
            avatar = form.cleaned_data.get('avatar')
            if avatar:
                avatar_url = _save_avatar(user['_id'], avatar)
            repo.update_profile(
                user['_id'], 
                full_name=form.cleaned_data['full_name'], 
                avatar_url=avatar_url, 
                phone=form.cleaned_data.get('phone', '')
            )
            return redirect('accounts_profile')
        return render(request, 'accounts/edit_profile.html', {'form': form, 'user': user})
    return render(request, 'accounts/edit_profile.html', {
        'page_title': 'Edit profile - ElectroMart', 'user': user})


def _save_avatar(user_id, uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower() or '.jpg'
    rel_path = 'avatars/%s%s' % (user_id, ext)
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    return settings.MEDIA_URL + rel_path


@login_required
def change_password(request):
    user = current_user(request)
    if request.method == 'POST':
        form = forms.ChangePasswordForm(request.POST)
        if form.is_valid():
            if not repo.check_password(form.cleaned_data['current_password'], user['password_hash']):
                form.add_error('current_password', 'Current password is incorrect.')
            else:
                repo.set_password(user['_id'], form.cleaned_data['password'])
                return redirect('accounts_profile')
        return render(request, 'accounts/change_password.html', {'form': form})
    return render(request, 'accounts/change_password.html', {'page_title': 'Change password - ElectroMart'})


# --------------------------------------------------------------- address book
@login_required
def address_book(request):
    user = current_user(request)
    addresses = repo.list_addresses(user['_id'])
    for a in addresses:
        a['id'] = str(a['_id'])  # Django templates forbid "_id" in {{ }}
    return render(request, 'accounts/address_book.html', {
        'page_title': 'Address book - ElectroMart', 'addresses': addresses})


@login_required
def address_add(request):
    user = current_user(request)
    if request.method == 'POST':
        form = forms.AddressForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            repo.add_address(user['_id'], d['receiver_name'], d['phone'], d['province'],
                             d['district'], d['detail'], d['is_default'])
            return redirect('accounts_address_book')
        addresses = repo.list_addresses(user['_id'])
        for a in addresses:
            a['id'] = str(a['_id'])  # template's {% url %} tags need this - was missing, caused 500
        return render(request, 'accounts/address_book.html', {
            'addresses': addresses, 'form': form})
    return redirect('accounts_address_book')


def _owner_of_address(request, address_id):
    """Used by @owner_required below: resolves who an address belongs to so
    a logged-in user cannot edit/delete another customer's address just by
    changing the id in the URL (Viec 15 / CV64, REQ-33)."""
    addr = repo.get_address(address_id)
    return addr['user_id'] if addr else None


@owner_required(_owner_of_address)
def address_edit(request, address_id):
    if request.method == 'POST':
        form = forms.AddressForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            repo.update_address(address_id, receiver_name=d['receiver_name'], phone=d['phone'],
                                province=d['province'], district=d['district'], detail=d['detail'])
            if d['is_default']:
                repo.set_default_address(current_user(request)['_id'], address_id)
    return redirect('accounts_address_book')


@owner_required(_owner_of_address)
def address_delete(request, address_id):
    if request.method == 'POST':
        repo.delete_address(address_id)
    return redirect('accounts_address_book')


@owner_required(_owner_of_address)
def address_set_default(request, address_id):
    if request.method == 'POST':
        repo.set_default_address(current_user(request)['_id'], address_id)
    return redirect('accounts_address_book')


# -------------------------------------------------------------------- B2B
@login_required
def wholesale_register(request):
    """Registering with account_type=wholesale (Viec 9) pre-creates a
    profile from just company_name + tax_code (that quick form has no
    address field). Here the customer supplies the rest - as long as the
    application is still "pending" it is completed/corrected in place
    instead of blocked, so nobody gets stuck with a blank address they can
    never fill in."""
    user = current_user(request)
    existing = repo.get_wholesale_profile_by_user(user['_id'])
    if existing and existing['approval_status'] != repo.APPROVAL_PENDING:
        return redirect('accounts_wholesale_status')

    # A first-time applicant has no profile yet, but the template still reads
    # initial.company_name (etc.) as a filter argument, and a bare {} makes
    # that lookup raise VariableDoesNotExist -> HTTP 500. Always hand the
    # template a dict that has those keys.
    initial = existing or {'company_name': '', 'tax_code': '',
                           'company_address': '', 'contact_person': ''}

    if request.method == 'POST':
        form = forms.WholesaleRegisterForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            if existing:
                repo.update_wholesale_application(existing['_id'], d['company_name'], d['tax_code'],
                                                   d['company_address'], d['contact_person'])
            else:
                repo.create_wholesale_profile(user['_id'], d['company_name'], d['tax_code'],
                                              d['company_address'], d['contact_person'])
            return redirect('accounts_wholesale_status')
        return render(request, 'accounts/wholesale_register.html', {'form': form, 'initial': initial})

    return render(request, 'accounts/wholesale_register.html', {
        'page_title': 'Business account - ElectroMart', 'initial': initial})


@login_required
def wholesale_status(request):
    user = current_user(request)
    return render(request, 'accounts/wholesale_status.html', {
        'page_title': 'Business account status - ElectroMart',
        'profile': repo.get_wholesale_profile_by_user(user['_id']),
    })


# --------------------------------------------------------------------- RFQ
@wholesale_required
def rfq_create(request):
    if request.method == 'POST':
        user = current_user(request)
        rows = []
        if request.FILES.get('bom_file'):
            try:
                rows = bom_import.match_part_numbers(bom_import.read_bom(request.FILES['bom_file']))
            except bom_import.BomImportError as e:
                return render(request, 'accounts/rfq_form.html', {'bom_error': str(e)})
        else:
            part_numbers = request.POST.getlist('part_number[]')
            quantities = request.POST.getlist('quantity[]')
            notes = request.POST.getlist('note[]')
            manual_rows = [
                {'part_number': pn.strip(), 'quantity': int(q or 1), 'note': note}
                for pn, q, note in zip(part_numbers, quantities, notes) if pn.strip()
            ]
            rows = bom_import.match_part_numbers(manual_rows) if manual_rows else []

        if not rows:
            return render(request, 'accounts/rfq_form.html', {'bom_error': 'Please add at least one component.'})

        repo.create_quotation(user['_id'], rows)
        return redirect('accounts_rfq_list')
    return render(request, 'accounts/rfq_form.html', {'page_title': 'Request for Quotation - ElectroMart'})


@wholesale_required
def rfq_list(request):
    user = current_user(request)
    quotations = repo.list_quotations_by_user(user['_id'])
    for q in quotations:
        q['id'] = str(q['_id'])  # Django templates forbid "_id" in {{ }}
    return render(request, 'accounts/rfq_list.html', {
        'page_title': 'My RFQs - ElectroMart', 'quotations': quotations})


# ------------------------------------------------------- my orders / my reviews
# Two panels the profile sidebar has always linked to with href="#". They read
# the sales and interaction modules through their own repos (read-only) - no
# other module's data-access code is changed.
@login_required
def my_orders(request):
    """Every order the logged-in customer has placed, newest first (CV54 /
    REQ-30 seen from the account, not the guest-tracking form)."""
    from sales import repo as sales_repo

    user = current_user(request)
    orders = [sales_repo.decorate(o) for o in sales_repo.list_orders_by_user(user['_id'])]
    return render(request, 'accounts/my_orders.html', {
        'page_title': 'My orders - ElectroMart', 'user': user, 'orders': orders})


@login_required
def my_reviews(request):
    """Every product review the logged-in customer has written (CV68), with the
    product it belongs to. The owner sees their hidden reviews too; editing
    still happens on the product page."""
    from catalogue import repo as catalogue_repo
    from interaction import repo as interaction_repo

    user = current_user(request)
    reviews = interaction_repo.list_reviews_by_user(user['_id'])
    products = catalogue_repo.products_by_ids([r['product_id'] for r in reviews])
    for r in reviews:
        r['id'] = str(r['_id'])
        product = products.get(str(r['product_id']))
        r['product_name'] = product['name'] if product else 'Product no longer available'
        r['product_slug'] = product.get('slug') if product else None
    return render(request, 'accounts/my_reviews.html', {
        'page_title': 'My reviews - ElectroMart', 'user': user, 'reviews': reviews})


# ------------------------------------------------------------------- Admin
@admin_required
def admin_manage_user(request):
    role = request.GET.get('role') or None
    status = request.GET.get('status') or None
    q = (request.GET.get('q') or '').strip()

    query = {}
    if role:
        query['role'] = role
    if status == 'active':
        query['is_hidden'] = False
    elif status == 'locked':
        query['is_hidden'] = True
    if q:
        # re.escape so a search box character that means something in regex
        # syntax (e.g. an unbalanced "(") cannot reach $regex raw - Mongo
        # rejects an invalid pattern with a 500 error otherwise (found in
        # Viec 17 security testing / CV78).
        safe_q = re.escape(q)
        query['$or'] = [{'full_name': {'$regex': safe_q, '$options': 'i'}},
                        {'email': {'$regex': safe_q, '$options': 'i'}}]

    db = repo.get_db()
    users = list(db[repo.USERS].find(query).sort('created_at', -1))
    pending = {p['user_id']: p for p in repo.list_pending_wholesale()}
    for u in users:
        u['id'] = str(u['_id'])
        wp = pending.get(u['_id'])
        u['wholesale_status'] = 'pending' if wp else None
        u['wholesale_profile_id'] = str(wp['_id']) if wp else None

    if status == 'pending_b2b':
        users = [u for u in users if u['wholesale_status'] == 'pending']

    return render(request, 'admin/manage_user.html', {
        'page_title': 'Manage users - ElectroMart', 'users': users})


@admin_required
def admin_toggle_lock(request, user_id):
    if request.method == 'POST':
        user = repo.find_user_by_id(user_id)
        if user:
            repo.set_hidden(user_id, not user.get('is_hidden'))
    return redirect('admin_manage_user')


@admin_required
def admin_wholesale_review(request, profile_id):
    if request.method == 'POST':
        admin = current_user(request)
        decision = request.POST.get('decision')
        if decision == 'approve':
            profile = repo.approve_wholesale(profile_id, admin['_id'])
        else:
            reason = (request.POST.get('reject_reason') or '').strip()
            if not reason:
                return redirect('admin_manage_user')  # JS already enforces this; ignore a bare bypass
            profile = repo.reject_wholesale(profile_id, admin['_id'], reason)
        if profile:
            user = repo.find_user_by_id(profile['user_id'])
            mailer.send_b2b_approval_email(user, decision == 'approve', request.POST.get('reject_reason', ''))
    return redirect('admin_manage_user')


# ------------------------------------------------------------- Admin: RFQ
# The customer side of RFQ (rfq_create / rfq_list) shipped in Viec 14; this
# is the admin side (CV62): read an RFQ, put a wholesale unit price on every
# line, set how long the quote is valid, and send it back. repo.py already
# had submit_quote_prices() waiting for a caller - this is it.
RFQ_NOTICES = {
    'quote_sent': 'The quotation was sent to the customer by email.',
}


@admin_required
def admin_rfq_list(request):
    status = request.GET.get('status') or None
    quotations = repo.list_quotations(status)

    db = repo.get_db()
    ids = list({q['user_id'] for q in quotations})
    users = {u['_id']: u for u in db[repo.USERS].find({'_id': {'$in': ids}})} if ids else {}
    for q in quotations:
        q['id'] = str(q['_id'])
        customer = users.get(q['user_id'])
        q['customer_name'] = customer.get('full_name') if customer else '(unknown user)'
        q['customer_email'] = customer.get('email') if customer else ''
        q['line_count'] = len(q.get('items', []))

    return render(request, 'admin/manage_rfq.html', {
        'page_title': 'Manage RFQs - ElectroMart',
        'admin_page': 'rfqs',
        'quotations': quotations,
        'status_filter': status or '',
        'statuses': [repo.QUOTE_PENDING, repo.QUOTE_QUOTED, repo.QUOTE_ACCEPTED,
                     repo.QUOTE_REJECTED, repo.QUOTE_EXPIRED],
        'notice': RFQ_NOTICES.get(request.GET.get('notice')),
    })


@admin_required
def admin_rfq_detail(request, quotation_id):
    try:
        quotation = repo.get_quotation(quotation_id)
    except Exception:
        quotation = None  # a malformed id in the URL, not a real 500
    if not quotation:
        return redirect('admin_rfq_list')
    customer = repo.find_user_by_id(quotation['user_id'])

    # A quote can only be priced once, while it is still pending. After that
    # the page is read-only (the customer may already have acted on it).
    if request.method == 'POST' and quotation['status'] == repo.QUOTE_PENDING:
        error, priced_items, valid_until = _read_quote_form(request, quotation)
        if error:
            return render(request, 'admin/rfq_detail.html', {
                'page_title': 'RFQ detail - ElectroMart', 'admin_page': 'rfqs',
                'quotation': _decorate_quotation(quotation), 'customer': customer,
                'error': error,
            })
        repo.submit_quote_prices(quotation_id, priced_items, valid_until)
        if customer:
            mailer.send_rfq_quoted_email(customer, repo.get_quotation(quotation_id))
        return redirect('%s?notice=quote_sent' % _url('admin_rfq_list'))

    return render(request, 'admin/rfq_detail.html', {
        'page_title': 'RFQ detail - ElectroMart', 'admin_page': 'rfqs',
        'quotation': _decorate_quotation(quotation), 'customer': customer,
    })


def _read_quote_form(request, quotation):
    """Pull one unit price per line + a validity date out of request.POST.

    Returns (error_message, priced_items, valid_until); error_message is None
    when every field is acceptable.
    """
    prices = request.POST.getlist('unit_price[]')
    items = quotation.get('items', [])
    priced = []
    for i, item in enumerate(items):
        raw = prices[i].strip() if i < len(prices) else ''
        try:
            unit_price = float(raw)
        except ValueError:
            return 'Please enter a unit price (a number, 0 or more) for every line.', None, None
        if unit_price < 0:
            return 'A unit price cannot be negative.', None, None
        priced.append(dict(item, unit_price=unit_price))

    valid_raw = (request.POST.get('valid_until') or '').strip()
    if not valid_raw:
        return 'Please choose a date until which this quote stays valid.', None, None
    try:
        valid_until = datetime.strptime(valid_raw, '%Y-%m-%d')
    except ValueError:
        return 'The quote validity date is not a valid date.', None, None
    if valid_until.date() < datetime.utcnow().date():
        return 'The quote validity date is in the past.', None, None

    return None, priced, valid_until


def _decorate_quotation(quotation):
    """Add the string id and per-line / grand totals the template needs
    (Django templates cannot multiply unit_price by quantity themselves)."""
    quotation['id'] = str(quotation['_id'])
    grand_total = 0
    for item in quotation.get('items', []):
        unit_price = item.get('unit_price')
        if unit_price is None:
            item['line_total'] = None
        else:
            item['line_total'] = unit_price * item.get('quantity', 0)
            grand_total += item['line_total']
    quotation['grand_total'] = grand_total if quotation['status'] != repo.QUOTE_PENDING else None
    return quotation


def _url(name):
    from django.urls import reverse
    return reverse(name)
