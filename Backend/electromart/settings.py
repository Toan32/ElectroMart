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

# Backend/electromart/settings.py -> Backend -> ProjectHK2
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / 'Frontend'

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key-change-before-deploy')
DEBUG = os.environ.get('DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*']

# ----------------------------------------------------------------- MongoDB
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'catalogue',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
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
                'catalogue.context_processors.shop_context',
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

MEDIA_URL = 'media/'
MEDIA_ROOT = PROJECT_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Products shown per page on a category listing
PAGE_SIZE = 24
# Maximum number of products that can be compared at once
COMPARE_LIMIT = 4
