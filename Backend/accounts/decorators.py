"""Access-control decorators, meant to be reused by every module (Viec 15 /
CV64), not just accounts/views.py. Session-based, since the project has no
django.contrib.auth: the logged-in user's id lives in
request.session['user_id'] (set by views.login_view on success).

Usage in any app's views.py::

    from accounts.decorators import login_required, admin_required

    @login_required
    def my_view(request):
        ...
"""
from functools import wraps

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect

from . import repo


def current_user(request):
    """Return the logged-in user's document, or None. Cached per-request
    so the several decorators/templates that call this do not each hit
    MongoDB again."""
    if not hasattr(request, '_cached_user'):
        user_id = request.session.get('user_id')
        request._cached_user = repo.find_user_by_id(user_id) if user_id else None
    return request._cached_user


def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user or user.get('is_hidden'):
            return redirect('%s?next=%s' % (_login_url(), request.path))
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user:
            return redirect('%s?next=%s' % (_login_url(), request.path))
        if user.get('role') != repo.ROLE_ADMIN:
            return HttpResponseForbidden('Admin access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required_json(view_func):
    """Same rule as admin_required, but for the fetch() endpoints behind an
    admin page (CV65-CV67, CV70, CV71).

    admin_required answers with a redirect, which a fetch() follows and then
    tries to parse the login page as JSON. These endpoints have to fail with a
    status the caller can act on instead, so they get their own decorator
    rather than being left unguarded.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user or user.get('role') != repo.ROLE_ADMIN:
            return JsonResponse({'ok': False, 'error': 'Admin access required.'},
                                status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def wholesale_required(view_func):
    """Only an APPROVED wholesale account may pass - a pending/rejected
    application is treated the same as a retail customer (CV61)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = current_user(request)
        if not user:
            return redirect('%s?next=%s' % (_login_url(), request.path))
        if user.get('role') != repo.ROLE_WHOLESALE or not repo.is_approved_wholesale(user['_id']):
            return HttpResponseForbidden('This page is only available to approved business accounts.')
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(get_owner_id):
    """Block a logged-in user from reaching another user's private data by
    editing an id straight in the URL (e.g. /accounts/addresses/<id>/edit/).
    `get_owner_id(request, *args, **kwargs)` must return the resource's
    owner user_id; an admin may always pass through."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = current_user(request)
            if not user:
                return redirect('%s?next=%s' % (_login_url(), request.path))
            if user.get('role') != repo.ROLE_ADMIN:
                owner_id = get_owner_id(request, *args, **kwargs)
                if owner_id is None or str(owner_id) != str(user['_id']):
                    return HttpResponseForbidden('You do not have access to this resource.')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _login_url():
    from django.urls import reverse
    return reverse('accounts_login')
