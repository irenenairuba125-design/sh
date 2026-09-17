from django import template

from courses.category_colors import gradient_css

register = template.Library()


@register.filter
def category_gradient(category):
    return gradient_css(category)


@register.filter
def times(number):
    """{% for _ in 5|times %} - used to draw N star icons for a rating."""
    try:
        return range(int(number))
    except (TypeError, ValueError):
        return range(0)
