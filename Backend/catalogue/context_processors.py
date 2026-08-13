"""Values every page needs: category menu and header counters."""
from . import repo
from .views import COMPARE_KEY, WISHLIST_KEY


def shop_context(request):
    return {
        'nav_categories': repo.category_tree(),
        'compare_count': len(request.session.get(COMPARE_KEY, [])),
        'wishlist_count': len(request.session.get(WISHLIST_KEY, [])),
    }
