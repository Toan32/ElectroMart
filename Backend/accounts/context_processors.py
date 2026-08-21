"""Makes the logged-in user available to every template (e.g. so base.html
can show "Hi, <name>" instead of a generic account icon), the same way
catalogue.context_processors exposes the category menu."""
from .decorators import current_user


def account_context(request):
    return {'current_user': current_user(request)}
