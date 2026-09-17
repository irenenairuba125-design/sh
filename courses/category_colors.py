"""One gradient + one icon per category, used on category pills and course thumbnail
placeholders so the catalog reads as organized and colorful even before any teacher
uploads a real thumbnail photo."""

CATEGORY_COLORS = {
    'legal_writing': ('#0FA898', '#0C8A7D'),
    'moot_court': ('#5B5FEF', '#4347C4'),
    'case_law': ('#F2A93B', '#D98E1F'),
    'constitutional': ('#3E5C76', '#2E4457'),
    'contract': ('#EF6F5B', '#D14F3B'),
    'criminal': ('#C4425A', '#9E2F45'),
    'research': ('#2FB6C7', '#1F93A2'),
    'bar_prep': ('#8E5BEF', '#6E3FC4'),
    'human_rights': ('#E85D8A', '#C43F6B'),
    'adr': ('#2EAE6B', '#1E8A52'),
    'internship': ('#5D7A99', '#435C77'),
    'international': ('#2E86AB', '#1F6A87'),
    'family_land': ('#B5723B', '#8F5527'),
}
DEFAULT_GRADIENT = ('#0FA898', '#0C8A7D')


def gradient_css(category):
    start, end = CATEGORY_COLORS.get(category, DEFAULT_GRADIENT)
    return f'linear-gradient(135deg, {start}, {end})'
