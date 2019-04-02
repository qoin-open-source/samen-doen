# -*- coding: utf-8 -*-

# Django settings for qoinware project.

import os

from django.utils.translation import ugettext_lazy as _

# Add import for filter: http://www.tiwoc.de/blog/2013/03/django-prevent-
# email-notification-on-suspiciousoperation/
from cc3.core.logging_filters import skip_suspicious_operations

from unipath import Path
from os.path import abspath, basename, dirname, join, normpath


ADMINS = (
    ('Stephen Wolff', 'stephen.wolff@qoin.org'),
    # ('Simon Woolf', 'simon.woolf@qoin.org'),
    # ('Alison Bloor', 'alison.bloor@gmail.com'),
    # ('Chin Dou', 'cdou.swsec@gmail.com'),
    ('Support @ Qoin', 'support@qoin.org'),
)

DJANGO_ROOT = dirname(dirname(abspath(__file__)))
PROJECT_DIR = Path(__file__).ancestor(2)
LOG_DIR = PROJECT_DIR.child('log')

VERIFICATION_DOCUMENTS_ROOT = normpath(
    join(DJANGO_ROOT, '..', 'verification_docs'))

DEBUG = False

ALLOWED_HOSTS = ['samen-doen.nl', 'localhost']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Amsterdam'

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
# Django docs: https://docs.djangoproject.com/en/dev/ref/settings/#
# std:setting-LANGUAGE_CODE

# English (UK)
# LANGUAGE_CODE = 'en-gb'

# Netherlands (Dutch)
LANGUAGE_CODE = 'nl'

# German
# LANGUAGE_CODE = 'de-de'

# French
# LANGUAGE_CODE = 'fr-fr'

ugettext = lambda s: s

LANGUAGES = [
    ('nl', ugettext('Dutch')),
    # ('en', ugettext('English')),
]

FORMAT_MODULE_PATH = 'icare4u_front.formats'

SITE_ID = 1

CONSTANCE_CONFIG = {}

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

LOCALE_PATHS = (
    os.path.join(PROJECT_DIR, 'locale'),
)

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# This funny guy can print integer numbers in the Django templates separating
# the thousands digits from the rest of the digits. That will cause several
# problems, for example when manipulating integer values passed by a Django
# template tag (custom or not) to a Javascript to process them. So: FALSE.
USE_THOUSAND_SEPARATOR = False


# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = PROJECT_DIR.ancestor(1).child('media')

STATIC_ROOT = PROJECT_DIR.ancestor(1).child('static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/assets/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    # include project static files
    PROJECT_DIR.child('static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'compressor.finders.CompressorFinder',
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/assets/admin/'
# Make this unique, and don't share it with anybody.


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [normpath(join(DJANGO_ROOT, 'templates')), ],
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.core.context_processors.debug',
                'django.core.context_processors.i18n',
                'django.core.context_processors.media',
                'django.core.context_processors.static',
                'django.core.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'django.core.context_processors.request',
                'django.core.context_processors.media',
                'django.core.context_processors.static',
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',

                'icare4u_front.context_processors.top_menu_items',
                'icare4u_front.context_processors.tandc_url',
                'icare4u_front.context_processors.stadlander',

                # NB ICare4u version of the user_cc3_profile context processor
                'cc3.core.context_processors.currency_symbol',
                'cc3.core.context_processors.cc3_system_name',
                'cc3.core.context_processors.getvars',
                'cc3.cyclos.context_processors.balance',
            ]
        }
    },
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

MIDDLEWARE_CLASSES = (
    'cms.middleware.utils.ApphookReloadMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'cms.middleware.multilingual.MultilingualURLMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'icare4u_front.profile.middleware.ProfileMiddleware',
    'cc3.accounts.middleware.CyclosAccountMiddleware',
    'cc3.accounts.middleware.UserStatusChangeMiddleware',
)

ROOT_URLCONF = 'icare4u_front.urls'


AUTHENTICATION_BACKENDS = (
    # Users in iCare4u / Positoos are authenticated via a SSO mechanism
    # they need to login to stadlander.nl and then click a link taking them to
    # <site>/nl/rekeningen/
    # The accounts view (rekeningen) is modified in samen doen to expect
    # a query string containing ?papi=123456778009.
    # Without this, users are pointing back at Stadlander to login.
    # With this, the key is used to send a SOAP request to stadlander for user
    # info.

    # Try authenticating via Stadlander SSO - if PAPI key available
    'icare4u_front.stadlander.backends.StadlanderSSOBackend',

    # Back end to authenticate user with email or username (rather than just
    # username - Django default)
    'cc3.registration.backends.EmailOrUsernameModelBackend',
)
#
# TEMPLATE_CONTEXT_PROCESSORS = (
#     'django.contrib.auth.context_processors.auth',
#     'django.contrib.messages.context_processors.messages',
#     'django.core.context_processors.i18n',
#     'django.core.context_processors.request',
#     'django.core.context_processors.media',
#     'django.core.context_processors.static',
#     'cms.context_processors.cms_settings',  # media',
#     'sekizai.context_processors.sekizai',
#     'icare4u_front.context_processors.top_menu_items',
#     'icare4u_front.context_processors.tandc_url',
#     'icare4u_front.context_processors.stadlander',
#     # NB ICare4u version of the user_cc3_profile context processor
#     'cc3.core.context_processors.currency_symbol',
#     'cc3.core.context_processors.cc3_system_name',
#     'cc3.core.context_processors.getvars',
#     'cc3.cyclos.context_processors.balance',
# )


# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'icare4u_front.wsgi.application'

# TEMPLATE_DIRS = (
#    PROJECT_DIR.child('templates'),
# )

INSTALLED_APPS = (
    # Django
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djangocms_admin_style',  # Needs to appear before 'django.contrib.admin'.

    # CC3 base framework
    'cc3',  # do not remove, or translations are lost on production server
    'cc3.core',
    'cc3.accounts',
    'cc3.billing',
    'cc3.cmscontent',
    'cc3.google_analytics',
    'cc3.marketplace',
    'cc3.communityadmin',
    'cc3.cyclos',
    'cc3.invoices',
    'cc3.mail',
    'cc3.cards',
    'cc3.rewards',
    'cc3.files',
    'cc3.rules',
    'cc3.statistics',

    # icare4u projects
    'icare4u_front.community_admin',
    'icare4u_front.profile',
    'icare4u_front.profile_registration',
    'icare4u_front.stadlander',
    'icare4u_front.csvimporttemp',
    'icare4u_front.loyaltylab',
    'icare4u_front.admin',

    # Django CMS
    'cms',
    'djangocms_file',  # could use django-filer alternative
    'djangocms_flash',  # could use django-filer alternative
    'djangocms_googlemap',
    'djangocms_inherit',
    'djangocms_link',
    'djangocms_picture',  # could use django-filer alternative
    'djangocms_snippet',
    'djangocms_teaser',  # could use django-filer alternative
    'djangocms_twitter',
    'djangocms_video',  # could use django-filer alternative
    'djangocms_text_ckeditor',  # tinymce plug seems broken?
#     # 'cmsplugin_vimeo',

    # 3rd party packages
    'ajax_select',
    'compressor',
    # 'contact_form',
    'django_nvd3',
    'endless_pagination',
    'easy_thumbnails',
    'form_designer',   # see FORM DESIGNER AI for 1.8
    'menus',
    'localflavor',
    #'mptt',
    'overextends',
    'pagination',
    'sekizai',
    'reversion',
    'registration',
#    'rosetta',
    'treebeard',
    'taggit',
    'tinymce',
    'adminsortable',
    'form_designer.contrib.cms_plugins.form_designer_form',
    'rest_framework',
    'rest_framework.authtoken',
    'djoser',

    # Moving django admin include below registration due to template issue for
    # front end password reset.
    'django.contrib.admin',

)

# Django cache backend.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': u'%(levelname)-8s %(asctime)s %(name)s %(message)s',
        },
        'simple': {
            'format': u'%(levelname)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        # http://www.tiwoc.de/blog/2013/03/django-prevent-email-notification-
        # on-suspiciousoperation/
        'skip_suspicious_operations': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_suspicious_operations,
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['skip_suspicious_operations', 'require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR.child('django.log'),
            'maxBytes': 1024*1024*5,
            'backupCount': 999,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django.request': {
            'handlers': ['log_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'icare4u_front': {
            'handlers': ['console', 'log_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'cc3': {
            'handlers': ['console', 'log_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'management_commands': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

FILE_UPLOAD_PERMISSIONS = 0644

# Denotes the maximum allowed file size in mega-bytes
MAX_FILE_SIZE = 10

#
# Django CMS settings.
#
CMS_PAGE_MEDIA_PATH = 'cms_page_media/'
CMS_PERMISSION = True
CMS_CONTENT_CACHE_DURATION = 0
CMS_TEMPLATES = (
    ('about_general.html',
     ugettext('General - Full page content with side menu')),
    ('about_general_2_columns.html',
     ugettext('General - 2 columns content with side menu')),
    ('homepage.html', ugettext('Home Page Template')),
    ('social_media_placeholder.html', ugettext('Social Media Page')),
)
# Placeholders configuration.
# This will prevent all placeholders showing all available plugins. With that,
# only certain plugins can be loaded in specific pages, avoiding users breaking
# the design with unwanted plugins.
CMS_PLACEHOLDER_CONF = {
    'main_section': {
        'plugins': [
            'CMSSectionCarouselPlugin',
        ],
        'name': ugettext('Top section'),
    },
    'center_section': {
        'plugins': [
            'CMSSectionColumnNoticePlugin',
            'CMSSectionColumnNewsPlugin',
            'TextPlugin',
        ],
        'name': ugettext('Center section'),
    },
    'social_media': {
        'plugins': ['CMSSocialMediaLinksPlugin'],
        'name': ugettext('Social Media links'),
    },
    'general_content': {
        'plugins': [
            'CMSNotificationPlugin',
            'PicturePlugin',
            'TextPlugin',
            'VimeoPlugin',
            'FormDesignerPlugin',
        ]
    },
    'column_1_content': {
        'plugins': [
            'CMSNotificationPlugin',
            'PicturePlugin',
            'TextPlugin',
            'VimeoPlugin'
        ]
    },
    'column_2_content': {
        'plugins': [
            'CMSNotificationPlugin',
            'PicturePlugin',
            'TextPlugin',
            'VimeoPlugin'
        ]
    },
}
# Add SEO Fields to page admin
# - https://django-cms.readthedocs.org/en/2.4.3/getting_started/
# configuration.html#cms-seo-fields
CMS_SEO_FIELDS = True


# Django CMS related: page IDs of pages for top level menu.
TOP_MENU_ITEMS = ['marketplace', 'about', 'faq']

# Django CMS related: page reverse ids for retrieving CMS page URLs.
CMS_PAGE_REVERSE_IDS = {
    'terms-and-conditions': 'tandc',
}

#
# Django Rosetta settings.
#
# ROSETTA_WSGI_AUTO_RELOAD = True


#
# Django authentication configuration.
#
LOGIN_REDIRECT_URL = '/rekeningen/'
LOGIN_URL = '/nl/login/'
AUTH_PROFILE_MODULE = 'profile.UserProfile'
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_OPEN = True


#
# CC3 Cyclos configuration.
#
# SDW Added 12.07.2012. Database settings altered above
CYCLOS_ENABLED = True
CYCLOS_URL = 'http://localhost:8080/cyclos'
# TODO get frontend urls for real systems
CYCLOS_FRONTEND_URL = 'http://precisevm:8080/cyclos'  # for links to front end
CYCLOS_WEBSERVICE_TRACE = False
ANONYMOUS_USER_ID = -1
CYCLOS_BANK_NAME = 'CC3 Credits Bank'
CYCLOS_BANK_USER_ID = -2
CYCLOS_FONDS_USER_ID = -3

# Needs to get group names from Cyclos, and not break if the name isn't there.
CYCLOS_CHARITY_MEMBER_GROUP = u'Goede Doelen'
CYCLOS_CUSTOMER_MEMBER_GROUP = u'Consumenten'
CYCLOS_CUSTOMER_MEMBER_GROUPS = [u'Consumenten', u'Consumenten 2']
CYCLOS_BUSINESS_MEMBER_GROUP = u'Organisaties'
CYCLOS_INSTITUTION_MEMBER_GROUP = u'Instituties'
CYCLOS_INACTIVE_MEMBER_GROUP = u'Inactive members'
CYCLOS_CARD_MACHINE_MEMBER_GROUPS = [CYCLOS_BUSINESS_MEMBER_GROUP,
                                     CYCLOS_INSTITUTION_MEMBER_GROUP,
                                     CYCLOS_CHARITY_MEMBER_GROUP]
CYCLOS_CARD_USER_MEMBER_GROUPS = CYCLOS_CUSTOMER_MEMBER_GROUPS + [
    CYCLOS_CHARITY_MEMBER_GROUP]

CYCLOS_CAMPAIGN_OWNER_GROUPS = [CYCLOS_INSTITUTION_MEMBER_GROUP,
                                CYCLOS_CHARITY_MEMBER_GROUP]

CURRENCY_SYMBOL = 'P'
CURRENCY_NAME = 'punten'
CYCLOS_CURRENCY_CODE = u'P'
CC3_SYSTEM_NAME = 'Samen Doen'
CC3_CURRENCY_MINIMUM = 1

# Number of CC3 currency units necessary to have 1 unit of official currency
# (euros, pounds, dollars...).
CC3_CURRENCY_CONVERSION = 100  # 100 Punten == 1 EUR

CC3_CURRENCY_INTEGER_ONLY = True

# REWARDS_FIXED_PERCENTAGE removed -- see tickets #3148, #3149, #3150

# Allowance of inter-communities transactions.
# If ``True``, a profile will be able to see other communities than the one he
# belongs to and transactions between different communities will be allowed.
INTER_COMMUNITIES_TRANSACTIONS = False
# override if INTER_COMMUNITIES_TRANSACTIONS is False
# allows members in the exception groups to perform inter community transactions
INTER_COMMUNITIES_TRANSACTIONS_MEMBER_GROUPS = \
    [CYCLOS_INSTITUTION_MEMBER_GROUP, ]

CONTACT_AUTO_MINIMUM_CHARS = 4

# CC3 applications settings.

INV_NO_PREFIX = 9999                # 'Prefix for invoice numbers'),
VAT_RATE = 21                       # 'VAT rate'),
VAT_STRING = 'BTW'                  # 'VAT string identifier, e.g. "VAT"'),
AUTO_INVOICE_AMOUNT = 25.00         # 'Amount to charge for auto invoices'),
AUTO_INVOICE_DUE_DATE_DAYS = 31     # 'Number of days the auto invoice is due'),
INVOICE_DRAW_PDF_MODULE = 'icare4u_front.profile.invoice_pdf'

# 16 is the ID in the 'clean' database
# NO LONGER USED.
# CC3_BANK_USER_ID = 16
CC3_BANK_USERNAME = 'cc3_bank_user'
# Community of site (default)
DEFAULT_COMMUNITY_ID = 1

# Shows business names when choosing a community member when placing Ads.
# Defaults to `False`.
COMMUNITY_ADMIN_SHOW_BUSINESS_NAMES = True
PROFILE_MAX_NUMBER_OF_LATEST_ADS = 100

# Show accounts with most recent transactions first with 'asc' (default) or
# last with 'desc'.
ACCOUNTS_VIEW_ORDER = 'desc'
ACCOUNTS_FORCE_COMPLETION = False

# cyclos transfer ids used in accounts views
REDEEM_TRANSFER_TYPE_ID = 31
GOOD_CAUSE_DONATION_TRANSFER_TYPE_ID = 32
PAY_DIRECT_TRANSFER_TYPE_ID = 33
SPEND_TRANSFER_TYPE_ID = 35
VOLUNTEER_PAYMENT_TRANSFER_TYPE_ID = 38

# Transactions containing this string in their description are excluded
# from all Transaction-based product charges
# If blank or missing, all transactions are included
BILLING_EXCLUDE_TRANSFERS_CONTAINING = "automatisch incasso"

# Closing accounts:
GROUPS_ALLOWED_TO_CLOSE_ACCOUNT = CYCLOS_CUSTOMER_MEMBER_GROUPS  # default is []
# Balance transfer when closing a user account
CLOSE_ACCOUNT_BALANCE_TRANSFER_TYPE_ID = 52
# Balance transfer on closing account
CLOSE_ACCOUNT_BALANCE_TRANSFER_DESC = \
    "Saldo overboeking i.v.m. opheffen account"

# Accounts needs approval by admins, or are automatically set up?
ADMINS_APPROVE_PROFILES = False

# If no Community is chosen, default to user's.
# TODO: currently risks strange pagination failure due to page links losing
# filters, #300, so can turn off to avoid that.
MARKETPLACE_DEFAULT_MY_COMMUNITY = True
# Don't default to user's if it's empty (feature suggested in Trac #249).
# Depends on MARKETPLACE_DEFAULT_MY_COMMUNITY being `True`.
MARKETPLACE_DEFAULT_MY_COMMUNITY_UNLESS_EMPTY = True

# Sort my community items before other communities
MARKETPLACE_SORT_MY_COMMUNITY_FIRST = True

# Maximum number of characters for an Ad description.
MARKETPLACE_AD_DESCRIPTION_LENGTH = 900

MARKETPLACE_PAGINATION_BY = 21

# mobile nunber is not mandatory for Samen Doen
MOBILE_NUMBER_MANDATORY = False

# custom validation of phone and mobile numbers
CUSTOM_PHONE_REGEX = r'^0[0-9]{9}$'
CUSTOM_PHONE_REGEX_DESC = _(u"10 digits starting with the area code, without "
                            u"punctuation")
CUSTOM_MOBILE_REGEX = r'^06[0-9]{8}$'
CUSTOM_MOBILE_REGEX_DESC = _(u"10 digits starting with 06, without punctuation")

# Google Maps API geo-coding region/country code.
SITE_REGION = 'nl'
MARKETPLACE_MAP_CENTER_LAT = 51.5243243
MARKETPLACE_MAP_CENTER_LNG = 4.2457638


# Project supports pricing.
PRICING_SUPPORT = True
# Project supports price options
PRICING_OPTION_SUPPORT = True

# PDF and documents generation corporative logo.
LOGO_IMG = os.path.join(PROJECT_DIR, 'static/img/logo.png')

# Blocking cards:
USERS_CAN_BLOCK_CARDS = True
# Ordering cards
CC3_CARDS_HANDLE_REPLACE_OLD = False

#
# CC3 Card API setting
#
CC3_CARDS_API_NEW_ACCOUNT_VIEW = \
    'icare4u_front.profile_registration.views.ICare4uCardsRegistrationView'
CC3CARDS_API_EMAIL_POSTFIX = 'positoos.nl'
CARD_ADMINISTRATOR_EMAILS = [
    'info@samen-doen.nl',
    'gert.meeder@qoin.org',
]

#
# Google analytics ID/Domain.
#
GOOGLE_ANALYTICS_ID = 'UA-xxxxxxxx-1'
GOOGLE_ANALYTICS_DOMAIN = 'community-currency.org'

#
# Emailing address.
#
DEFAULT_FROM_EMAIL = 'noreply@samen-doen.nl'
SERVER_EMAIL = 'noreply@samen-doen.nl'


THUMBNAIL_ALIASES = {
    # Use the target '' for project-wide aliases. Otherwise, the target should
    # be a string which defines the scope of the contained aliases:
    # - 'sprocket.Widget.image' would make the aliases available to only the
    #   'image' field of a 'Widget' model in an app named 'sprocket'.
    # - 'sprocket.Widget' would apply to any field in the 'Widget' model.
    # - 'sprocket' would target any field in any model in the app.
    '': {
        'adthumb': {'size': (81, 63), 'crop': True},
        'marketplacethumb': {'size': (44, 44), 'crop': True},
        'marketplacedetail': {'size': (660, 440), 'crop': True},
        'marketplacedetailprofile': {'size': (56, 56), 'crop': True},
        'profilepicture': {'size': (0, 90), 'crop': True},
    }
}

THUMBNAIL_DEBUG = False

#
# Django Form Designer configuration.
#
FORM_DESIGNER_FIELD_CLASSES = (
    ('localflavor.generic.forms.IBANFormField', _('IBAN number')),
    ('localflavor.nl.forms.NLZipCodeField', _('NL postcode')),
    ('django.forms.CharField', _('Text')),
    ('django.forms.EmailField', _('E-mail address')),
    ('django.forms.URLField', _('Web address')),
    ('django.forms.IntegerField', _('Number')),
    ('django.forms.DecimalField', _('Decimal number')),
    ('django.forms.BooleanField', _('Yes/No')),
    ('django.forms.DateField', _('Date')),
    ('django.forms.DateTimeField', _('Date & time')),
    ('django.forms.TimeField', _('Time')),
    ('django.forms.ChoiceField', _('Choice')),
    ('django.forms.MultipleChoiceField', _('Multiple Choice')),
    ('django.forms.ModelChoiceField', _('Model Choice')),
    ('django.forms.ModelMultipleChoiceField', _('Model Multiple Choice')),
    ('django.forms.RegexField', _('Regex')),
    ('django.forms.FileField', _('File')),
)

#
# Django TinyMCE configuration.
#

# NB Not used for CMS
TINYMCE_DEFAULT_CONFIG = {
    'plugins': "table,save,advhr,advimage,advlink,emotions,paste,"
               "insertdatetime,preview,searchreplace,print,directionality,"
               "fullscreen,noneditable,contextmenu",
    'theme': "advanced",
    'theme_advanced_toolbar_location': "top",
    'theme_advanced_toolbar_align': "left",
    'paste_use_dialog': False,
    'theme_advanced_buttons2_add': "fontselect,fontsizeselect,insertdate,"
                                   "inserttime,preview",
    'theme_advanced_buttons3_add': "separator,forecolor,backcolor,separator,"
                                   "pasteword,tablecontrols",
    'table_styles': "Header 1=header1;Header 2=header2;Header 3=header3",
    'table_cell_styles': "Header 1=header1;Header 2=header2;Header 3=header3;"
                         "Table Cell=tableCel1",
    'table_row_styles': "Header 1=header1;Header 2=header2;Header 3=header3;"
                        "Table Row=tableRow1",
    'table_cell_limit': 100,
    'table_row_limit': 15,
    'table_col_limit': 5,
    'cleanup': True,
    'relative_urls': False,

    'style_formats': [
        {'title': 'Read more', 'inline': 'div', 'classes': 'readmore'},
    ],
    'width': '100%',
    'height': '500px',
}

# USED for general front end users
TINYMCE_SIMPLE_CONFIG = {
    'theme': "advanced",
    'skin': "o2k7",
    'skin_variant': 'silver',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 10,
    'theme_advanced_buttons1': "bold,italic,underline,strikethrough,sub,sup,"
                               "numlist,bullist",
    'theme_advanced_buttons2': "",
    'theme_advanced_buttons3': "",
    'width': 470,

}


# CMS editing
CKEDITOR_SETTINGS = {
    'language': '{{ language }}',
    'toolbar_CMS': [
        ['Undo', 'Redo'],
        ['cmsplugins', '-', 'ShowBlocks'],
        ['Format', 'Styles', 'Source', 'Remove'],
        ['TextColor', 'BGColor', '-', 'PasteText', 'PasteFromWord'],
        ['Bold', 'Italic', 'Underline', '-', 'Subscript', 'Superscript', '-',
         'RemoveFormat'],
        ['JustifyLeft', 'JustifyCenter', 'JustifyRight'],
        ['Link', 'Unlink'],
        ['Maximize', ''],
        ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Table', ],
    ],
    'skin': 'moono',
}


SECRET_KEY = r"^m9(8tcwl6o4n&*m3*)+r1)4m787t@+2cc47pglm33&xe&qi@w"

# ---------------------------
# Stadlander SSO integration
# ---------------------------

# staging website
STADLANDER_URL = "https://acceptatie.stadlander.nl/"
# staging login page on
STADLANDER_LOGIN_URL = "https://acceptatie.stadlander.nl/mijn_stadlander.html"
# NB this page has the link back = "https://acceptatie.stadlander.nl/mijn_
# stadlander/qoin_staging.html"

STADLANDER_GROUPSET_ID = 1

STADLANDER_SSO_REWARD_AMOUNT = 250
STADLANDER_SSO_REWARD_DESCRIPTION = u'Beloning voor het activeren van uw ' \
                                    u'Samen Doen rekening'
STADLANDER_SSO_REWARD_SENDER = 'stadlander'

STADLANDER_AD_REWARD_AMOUNT = 25
STADLANDER_AD_REWARD_DESCRIPTION = u'Waardering voor het plaatsen van uw ' \
                                   u'eerste advertentie in de categorie {0}'
STADLANDER_AD_REWARD_SENDER = 'stadlander'

# staging wsdl
# STADLANDER_WSDL = "https://acceptatie.stadlander.nl/services.html?wsdl"
STADLANDER_WEB_SERVICE_URL = "https://acceptatie.stadlander.nl/services.html"
STADLANDER_WEB_SERVICE_API_CALL = "getQoinData"


# initially this was 10
# now it's 1 punten == 1 min
STADLANDER_MINUTES_TO_PUNTEN = 1

# staging STADLANDER links back to s
#
#   https://icare4u-stage.community-currency.org/nl/rekeningen/?papi=5339d86b96
# 26c392dd6d13ad298fb133fb889b214c2d164b2413fc4c07db5fce
#
# django redirects (needs logging in to)
#
#
#   http://localhost:8000/login/?next=/nl/rekeningen/%3Fpapi%3D6458db6dbe3e23d8
# cfec5f8f2ddcfedc12df2f8768c9db8cfd152f7a31918e2d
#
#
# there is a view currently served at /testing/ as i couldn't get the /login/
# url overriden successfully
#
#   http://localhost:8000/testing/login/?next=/nl/rekeningen/%3Fpapi%3D6458db6
# dbe3e23d8cfec5f8f2ddcfedc12df2f8768c9db8cfd152f7a31918e2d
#
#
# this view is a re-working of the django login view, but using GET rather than
#  POST to feed the Auth Form (icare4u_front.forms.PAPIForm)
#
# PAPIForm validates the 'next' GET parameter with a regex, to ensure that
# there is a papi key
#
# the view if the form is valid, then tries to retreive data from Stadlander
# via the SOAP call
# this is where i got stuck - no schema in the stadlander wsdl file
# so tried not parsing the wsdl, and then not successful with the other
# pysimplesoap SoapClient approach
# https://code.google.com/p/pysimplesoap/wiki/SoapClient


STADLANDER_TOBIAS_WEB_SERVICE_URL = \
    "https://csb02test.corporatieservicebus.nl/" \
    "Bus/V1/Router.svc/soap/RequestReply"



UPLOAD_MODELS = [
    'csvimporttemp.Huurcontract', 'csvimporttemp.Positoos'
]

# how long should files service token last for (seconds)
FILES_TOKEN_AGE = 60 * 60  # 1 hour

#
# SEPA Export settings
#
SEPA_SETTINGS = {
    'INITIATING_BUSINESS': 'Positoos B.V.',
    'END_TO_END_ID': 'Saldo Positoos',
    'CREDITOR': {
        'NAME': 'Positoos B.V., Administratie',
        'IBAN': 'NL15RABO0154443476',
        'BIC': 'RABONL2U',
        'ULTIMATE_CREDITOR': 'Rabobank',
        'IDENTIFIER': 'NL66ZZZ172728960000',
        'COUNTRY': 'NL',
        'STREET_NUMBER': 'Groenstraat 139/155',
        'POSTCODE_CITY': '5021LL Tilburg',
    },
    'DEBTOR': {
        'NAME': 'Positoos B.V., Administratie',
        'IBAN': 'NL15RABO0154443476',
        'BIC': 'RABONL2U',
        'ULTIMATE_DEBTOR': 'Rabobank',
        'IDENTIFIER': 'NL66ZZZ172728960000',
        'COUNTRY': 'NL',
        'STREET_NUMBER': 'Groenstraat 139/155',
        'POSTCODE_CITY': '5021LL Tilburg',
    },
}
# Credit due to SEPA reconciliation
SEPA_EXPORT_DEBIT_TRANSFER_TYPE_ID = 39
SEPA_EXPORT_DEBIT_TRANSFER_DESCRIPTION = "Bijschrijving na automatisch incasso"

# Debit due to SEPA reconciliation
SEPA_EXPORT_CREDIT_TRANSFER_TYPE_ID = 36
SEPA_EXPORT_CREDIT_TRANSFER_DESCRIPTION = "Afschrijving na automatisch incasso"

# Module path for custom stats SQL
STATS_CUSTOM_SQL_MODULE = 'icare4u_front.custom.sql.statistics'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication'
    ),
}

AJAX_LOOKUP_CHANNELS = {
    'number': ('cc3.cards.lookups', 'CardNumbersLookup')
}

# check a business is not trying to reward a charity is not trying to
BUSINESS_TO_CHARITY_REWARD_CHECK = True
# check an  institution is not trying to reward a charity is not trying to
INSTITUTION_TO_CHARITY_REWARD_CHECK = True
# 2946 hide individuals with no adverts
MARKETPLACE_INDIVIDUALS_HIDE_IF_NO_ADVERTS = True


# XLS Export field configuration
ADMIN_ACTION_EXPORT_XLS_FIELDS = {
    'global': {
        'col_width': 20,
        'fields': {
            'datetime.datetime': {
                'num_format': 'dd/mm/yyyy hh:mm',
                'filter': 'cc3.excelexport.filters.MakeTimezoneNaiveFilter',
                'unicode': False,
            },
            'datetime.date': {
                'num_format': 'dd/mm/yyyy',
                'unicode': False,
            },
        },
    },
    'icare4u_front.profile.models.UserProfile': {
        'fields': {
            'email': {
                'attr': 'user.email',
                'position': 4,
            },
            'user_id': {
                'attr': 'user.id',
                'position': 5,
            },
            # #3505 - remove balance for now due to performance issues
            # 'balance': {
            #     'attr': 'current_balance',
            #     'position': 6,
            # },
            'registration_date': {
                'attr': 'user.date_joined',
                'position': 6,
            },
            'deactivation_date': {
                'attr': 'user.last_deactivated',
                'position': 7,
            },
            'good_cause': {
                'attr': 'user.good_cause',
                'position': 8,
            }
        },
    },
}

# Card-related settings
MAX_CARD_NUMBER = 9999999999999999
MIN_CARD_NUMBER = 0
