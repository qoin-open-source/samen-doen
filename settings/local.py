# encoding: utf-8
from .base import *


# NB in production, Yaybu creates a hosting_settings.py which contains the
# production settings.

DEBUG = True
# update settings that depend on DEBUG (which was previously False)
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG
LOGGING['loggers']['icare4u_front']['level'] = 'DEBUG' if DEBUG else 'INFO'
LOGGING['loggers']['cc3']['level'] = 'DEBUG' if DEBUG else 'INFO'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'icare4u_front',
        'USER': 'icare4u_front',
        'PASSWORD': 'icare4u_front',
        'HOST': '127.0.0.1',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=INNODB',
        },
    }
}

ADMINS = (
    ('Dev Example', 'dev@example.com'),
)
MANAGERS = ADMINS

# uncomment to use the Debug Toolbar
#INSTALLED_APPS += (
#    'debug_toolbar',
#)

# Use a dummy backend to catch outgoing mails.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SUPPORT_EMAIL = 'dev@example.com'
CREDIT_LINE_EMAIL = 'dev@example.com'

# Deactivate South migrations during local unit testing to save time.
SOUTH_TESTS_MIGRATE = False

# CC3/Cyclos local settings.
CYCLOS_URL = 'http://localhost:8080/cyclos'
CYCLOS_WEBSERVICE_TRACE = True
CYCLOS_FRONTEND_URL = 'http://localhost:8080/cyclos'
CC3_BANK_USER_ID = 16

REMOTE_DATABASES = {  # So that the test runner doesn't create a copy of this
    'cyclos': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'icare4u_cyclos',
        'USER': 'cyclos3',
        'PASSWORD': 'cyclos3',
        'HOST': '',
        'PORT': '',
    }
}

# Set up a dummy cache system for development.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Easy-thumbnail package debugging activated.
THUMBNAIL_DEBUG = True

# Deactivate static media files compression.
COMPRESS_ENABLED = False

LOCALE_PATHS = (
    os.path.join(PROJECT_DIR, 'locale'),
)

SECRET_KEY = '~*secret-key*~'  # No need for a "real" key in the dev environment.

TEST_URLS = 'icare4u_front.urls'

# SSO Settings
STADLANDER_URL = "https://acceptatie.stadlander.nl/"
STADLANDER_LOGIN_URL = "https://acceptatie.stadlander.nl/mijn_stadlander.html"
STADLANDER_WEB_SERVICE_URL = "https://acceptatie.stadlander.nl/services.html"

CARD_ADMINISTRATOR_EMAILS = [
    'stephen.wolff@qoin.org',
]

# Lastly, import sensitive or machine-specific dev settings.
try:
    from .secret import *
except ImportError:
    print ("WARNING: Could not find any secret or machine-specific settings. "
           "See icare4u_front/settings/README.rst if you wish to add some.")
