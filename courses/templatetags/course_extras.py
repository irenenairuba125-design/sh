from django import template
from django.templatetags.static import static

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


STOCK_PHOTOS = ['phones.jpg', 'justice.jpg', 'gavel.jpg', 'library.jpg']


@register.filter
def stock_photo(course_id):
    """Default cover photo for a course with no uploaded thumbnail (varies by course id)."""
    try:
        name = STOCK_PHOTOS[int(course_id) % len(STOCK_PHOTOS)]
    except (TypeError, ValueError):
        name = STOCK_PHOTOS[0]
    return static('core/photos/' + name)
