# encoding: utf-8
from .local import *


#DATABASES['default']['ENGINE']='django.db.backends.sqlite3'
#DATABASES['default']['OPTIONS'] = {}

# uncomment line if using syncdb and migrate to create nose db
# DATABASES['default']['NAME'] = 'test_icare4u_front'

# comment back after then use something like the following to nose a test or three:
# REUSE_DB=1 python manage.py test ~/Documents/Development/qoin/icare4u_front/ --settings=icare4u_front.settings.test -v3


REMOTE_DATABASES = { # so that the test runner doesn't create a copy of this
    'cyclos': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cyclos',
        'USER': 'cyclos',
        'PASSWORD': 'cyclos',
        'HOST': 'localhost',
        'PORT': '',
    }
}

INSTALLED_APPS += (
    'django_nose',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SOUTH_TESTS_MIGRATE = False
CREDIT_LINE_EMAIL = 'test.icare4ucreditline@tradeqoin.com'

FIXTURE_DIRS = (os.path.join(PROJECT_DIR, 'fixtures', 'test_fixtures'), )
    #,PROJECT_DIR ('/path/to/proj_folder//',)

GOOGLE_ANALYTICS_ID = 'UA-xxxxxxxx-1'
