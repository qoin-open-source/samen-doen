# encoding: utf-8
from .base import *

# NB in production / staging, Yaybu creates a hosting_settings.py which contains the settings.


ADMINS = (
    ('Stephen Wolff', 'stephen.wolff@qoin.org'),
    # ('Simon Woolf', 'simon.woolf@qoin.org'),
)
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'icare4u_front',
        'USER': 'icare4u_front',
        'PASSWORD': 'icare4u_front',
        'HOST': 'localhost',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=INNODB',
        },
    }
}

CARD_ADMINISTRATOR_EMAILS += (
    'gert.meeder@qoin.org',
)

#
# SMTP server settings.
#
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 25
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@samen-doen.nl'
SERVER_EMAIL = 'noreply@samen-doen.nl'
CREDIT_LINE_EMAIL = 'creditline@noreply@samen-doen.nl'

try:
    from hosting_settings import *
    # Can't manipulate dicts yet..
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL),
    }
except ImportError:
    pass
