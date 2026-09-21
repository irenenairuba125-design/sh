import hashlib
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import dj_database_url
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_DEV_KEY = 'dev-insecure-secret-key-change-me'
SECRET_KEY = config('SECRET_KEY', default=_DEV_KEY).strip().strip('"').strip("'").strip()
if not SECRET_KEY or SECRET_KEY == _DEV_KEY:
    # A missing/empty key must never crash the site, and the dev default is public (it is in
    # the repo). When a database URL is configured, derive a private key from it instead.
    _db_for_key = config('DATABASE_URL', default='')
    if _db_for_key:
        SECRET_KEY = hashlib.sha256(('qiora-secret-key|' + _db_for_key).encode()).hexdigest()
    else:
        SECRET_KEY = _DEV_KEY
# Vercel sets VERCEL=1 automatically; never run with debug pages on there.
DEBUG = config('DEBUG', default=not os.environ.get('VERCEL'), cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost,.vercel.app', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='https://*.vercel.app', cast=Csv())
if os.environ.get('VERCEL'):
    # On Vercel: never trust local-only values pasted from .env.example.
    DEBUG = False
    ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ['.vercel.app']
    CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + ['https://*.vercel.app']
# Vercel terminates HTTPS in front of Django
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'core',
    'accounts',
    'courses',
    'payments',
    'quizzes',
    'certificates',
    'reviews',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'accounts.middleware.BlockedUserMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'onlineschool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'onlineschool.wsgi.application'

# Local dev uses SQLite. On Vercel there is no persistent disk, so set DATABASE_URL to a
# hosted Postgres (Neon, Supabase, ...) in the Vercel project's environment variables.
def _clean_database_url(url):
    """Tolerate what people paste from Supabase: surrounding quotes, and Prisma-only
    options like ?pgbouncer=true that psycopg2 rejects."""
    url = url.strip().strip('"').strip("'").strip()
    parts = urlsplit(url)
    prisma_only = {'pgbouncer', 'connection_limit', 'pool_timeout', 'schema'}
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in prisma_only]
    return urlunsplit(parts._replace(query=urlencode(query)))


_database_url = config('DATABASE_URL', default='')
if _database_url:
    if '[YOUR-PASSWORD]' in _database_url or '[' in _database_url.split('@')[0]:
        raise ImproperlyConfigured(
            'DATABASE_URL still contains the [YOUR-PASSWORD] placeholder. '
            'Replace it, including the square brackets, with your real database password.'
        )
    try:
        _database_url = _clean_database_url(_database_url)
        DATABASES = {'default': dj_database_url.parse(_database_url, conn_max_age=0, ssl_require=True)}
    except Exception as exc:
        raise ImproperlyConfigured(
            'DATABASE_URL is not a valid Postgres URL. If your password contains symbols such as '
            '@ # / : ? reset it to letters and numbers only. (%s)' % type(exc).__name__
        ) from None
    # Required when connecting through Supabase's transaction pooler (port 6543).
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            # Vercel's disk is read-only except /tmp, so a demo database lives there (it resets
            # on cold starts; set DATABASE_URL for permanent data).
            'NAME': '/tmp/qiora.sqlite3' if os.environ.get('VERCEL') else BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Serve app/admin static files straight from their folders so no collectstatic build step is needed.
WHITENOISE_USE_FINDERS = True

# Public media: course thumbnails, logos, certificate images. Safe to serve directly.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Protected media: lesson videos and notes. NEVER served directly by a public URL -
# only through the permission-checked views in courses/views.py. This is what makes
# "can't watch unless you paid" actually true instead of just hidden in the UI.
PROTECTED_MEDIA_ROOT = BASE_DIR / 'protected_media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:post_login'
LOGOUT_REDIRECT_URL = 'core:home'

# --- Pesapal (MTN MoMo / Airtel Money / Visa / Mastercard for Uganda) ---
PESAPAL_ENV = config('PESAPAL_ENV', default='sandbox')
PESAPAL_CONSUMER_KEY = config('PESAPAL_CONSUMER_KEY', default='')
PESAPAL_CONSUMER_SECRET = config('PESAPAL_CONSUMER_SECRET', default='')
PESAPAL_IPN_ID = config('PESAPAL_IPN_ID', default='')
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000')

# Send request errors to stdout so they show up in Vercel's function logs.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False}},
}
