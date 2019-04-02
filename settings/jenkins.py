# Django Jenkins CI settings for the iCare4u project.

# encoding: utf-8
from .base import *


DEBUG = True

TEST = True

ALLOWED_HOSTS = ['127.0.0.1:8000', 'localhost:8000']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jenkins_icare4u',
        'USER': 'jenkins_icare4u',
        'PASSWORD': 'jenkins_icare4u',
        'HOST': '127.0.0.1',
        'PORT': '',
    }
}


ADMINS = (
    ('Stephen Wolff', 'stephen.wolff@qoin.org'),
)

MANAGERS = ADMINS

# add a secret key, jenkins failing for non-obvious reason, so this is a guess
SECRET_KEY = 'snuo2gn&8+qf9mq*ixr+=7cu1fd2f-y_vvv1o_&_r7%y%v^e4a'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SUPPORT_EMAIL_LIST = ['dev@example.com']
SERVER_EMAIL = 'dev@example.com'
DEFAULT_FROM_EMAIL = 'dev@example.com'
SUPPORT_EMAIL = 'dev@example.com'

# URLs set used on testing CC3 apps. Overrides `cc3.core.utils.test_urls`,
# which is used by standalone CC3 test suite.
TEST_URLS = 'icare4u_front.urls'

# Django-Jenkins
INSTALLED_APPS += (
    'django_jenkins',
)

PROJECT_APPS = (
    'icare4u_front.csvimporttemp',
    'icare4u_front.profile',
    'icare4u_front.profile_registration',
    'icare4u_front.stadlander',
    'icare4u_front.loyaltylab',
    'cc3.core',
    'cc3.cyclos',
    'cc3.invoices',
    'cc3.mail',
    'cc3.marketplace',
    'cc3.accounts',
    'cc3.communityadmin',
    'cc3.cards',
    'cc3.files',
    'cc3.rewards',
    'cc3.rules',
    'cc3.cmscontent',
    'cc3.billing',
)

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pylint',
    'django_jenkins.tasks.run_pep8',
)


GOOGLE_ANALYTICS_ID = 'UA-xxxxxxxx-1'


# Set up a dummy cache system for development.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Logging settings for Jenkins.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'icare4u_front': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'cc3': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    }
}
