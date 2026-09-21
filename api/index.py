import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onlineschool.settings')

from onlineschool.wsgi import application  # noqa: E402

try:
    from onlineschool.demo_bootstrap import ensure_demo_database  # noqa: E402
    ensure_demo_database()
except Exception as exc:  # never stop the site from starting because of the demo setup
    print('demo bootstrap failed: %r' % (exc,))

app = application
