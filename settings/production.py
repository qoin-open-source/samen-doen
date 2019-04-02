# encoding: utf-8
from base import *


# ============================
# Server Exim set to listen on localhost - no u or p
# ============================
EMAIL_HOST = 'mail.authsmtp.com'
EMAIL_HOST_USER = 'ac73555'
EMAIL_HOST_PASSWORD = 'beck_gay_cindy_mile!'
EMAIL_PORT = 25
EMAIL_USE_TLS = False

DEFAULT_FROM_EMAIL = 'noreply@samen-doen.nl'
SERVER_EMAIL = 'noreply@samen-doen.nl'

# Static media files compression activated.
COMPRESS_ENABLED = True


# ============================
# Yaybu settings import
# ============================
# NB in production, Yaybu creates a hosting_settings.py which contains the more secret production settings.
try:
    from hosting_settings import *
    # Can't manipulate dicts yet..
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL),
    }
except ImportError:
    pass

