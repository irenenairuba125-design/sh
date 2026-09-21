"""One gradient + one icon per category, used on category pills and course thumbnail
placeholders so the catalog reads as organized and colorful even before any teacher
uploads a real thumbnail photo."""

CATEGORY_COLORS = {
    'business': ('#F08A24', '#D06E0E'),
    'finance': ('#2E9E5B', '#1F7D45'),
    'technology': ('#4361EE', '#2F47C4'),
    'data': ('#7B4FE0', '#5E37B8'),
    'science': ('#1FA7C9', '#1585A3'),
    'health': ('#E5484D', '#C2343A'),
    'engineering': ('#5C6B7A', '#434F5B'),
    'education': ('#D9A400', '#B58700'),
    'arts_design': ('#D64F9B', '#B23A7D'),
    'languages': ('#12A594', '#0C8577'),
    'agriculture': ('#6BA33A', '#508428'),
    'career': ('#E26A4A', '#C14E31'),
    'law': ('#3E5C76', '#2E4457'),
    'other': ('#7A8794', '#5E6A76'),
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
