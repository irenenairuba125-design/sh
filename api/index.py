import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onlineschool.settings')

from onlineschool.wsgi import application  # noqa: E402

app = application
