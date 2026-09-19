from pathlib import Path

import dj_database_url
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-insecure-secret-key-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost,.vercel.app', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='https://*.vercel.app', cast=Csv())
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
_database_url = config('DATABASE_URL', default='')
if _database_url:
    DATABASES = {'default': dj_database_url.parse(_database_url, conn_max_age=0, ssl_require=True)}
    # Required when connecting through Supabase's transaction pooler (port 6543).
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
