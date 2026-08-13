"""Template filters used by the storefront templates."""
from django import template

register = template.Library()


@register.filter
def money(value):
    """Format a price the way a Vietnamese shop shows it: 165000 -> 165,000 d"""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return '{:,}'.format(n) + ' \u20ab'


@register.filter
def stars(value):
    """Filled/empty star string for a rating score."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(5, n))
    return '\u2605' * n + '\u2606' * (5 - n)
