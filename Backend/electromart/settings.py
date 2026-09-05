"""Django settings for ElectroMart.

The project uses MongoDB as its only database, accessed through pymongo
(see catalogue/db.py). Because the Django ORM is not used, DATABASES is left
empty and sessions are stored in signed cookies, so the site runs without
creating any relational database.

Folder layout:
    Backend/   Django project and application code
    Frontend/  templates and static assets
    Database/  schema, index script and seed data
"""
import os
from pathlib import Path

from .env import load_env

# Backend/electromart/settings.py -> Backend -> ProjectHK2
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / 'Frontend'

# Must happen before the os.environ.get() calls below, otherwise every value
# in .env is ignored and only the defaults here are used.
load_env(PROJECT_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key-change-before-deploy')
DEBUG = os.environ.get('DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*']

# ----------------------------------------------------------------- MongoDB
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')

INSTALLED_APPS = [
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'catalogue',
    'accounts',
    'interaction',
    'sales',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # interaction/views.py reports every review/comment outcome through
    # django.contrib.messages, and base.html renders them. Without this
    # middleware those calls raise MessageFailure instead of flashing.
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'electromart.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [FRONTEND_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'catalogue.context_processors.shop_context',
                'accounts.context_processors.account_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'electromart.wsgi.application'

# No relational database: every document lives in MongoDB.
DATABASES = {}

# Signed-cookie sessions avoid the need for a django_session table.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [FRONTEND_DIR / 'static']
STATIC_ROOT = PROJECT_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = PROJECT_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Products shown per page on a category listing
PAGE_SIZE = 24
# Maximum number of products that can be compared at once
COMPARE_LIMIT = 4

# ------------------------------------------------------------------- email
# Shared by the whole team through accounts/mailer.py (Viec 10 / CV59).
# Filling EMAIL_HOST_USER + EMAIL_HOST_PASSWORD in .env switches real SMTP
# delivery on; with them empty the console backend prints the message instead,
# so a teammate can still register without any mail account set up.
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'http://127.0.0.1:8000')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0') == '1'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# Gmail shows an app password as "abcd efgh ijkl mnop"; the spaces are only
# there for readability and SMTP AUTH rejects them, so drop them here rather
# than relying on everyone to paste it correctly.
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').replace(' ', '')
# Never let a request hang on an unreachable SMTP server.
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '15'))

# Gmail refuses to send as an address the authenticated account does not own,
# so the sender defaults to the SMTP user instead of a made-up no-reply@.
DEFAULT_FROM_EMAIL = (os.environ.get('DEFAULT_FROM_EMAIL')
                      or ('ElectroMart <%s>' % EMAIL_HOST_USER if EMAIL_HOST_USER
                          else 'ElectroMart <no-reply@electromart.vn>'))

EMAIL_ENABLED = bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
if EMAIL_ENABLED:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# TLS and SSL are alternatives, not both: port 587 uses TLS, port 465 uses SSL.
if EMAIL_USE_SSL:
    EMAIL_USE_TLS = False

# ----------------------------------------------------------------- logging
# CV59 step 3 asks for an email log. Django's default config only wires up the
# "django" logger, so accounts.mailer's INFO lines would never be printed;
# this makes every send attempt visible in the runserver terminal.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
