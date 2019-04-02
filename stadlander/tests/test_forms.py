import logging
import random
import string

from django.forms import ValidationError
from django.test import TestCase
from django.utils.translation import activate

from ..forms import (PAPIForm)

LOG = logging.getLogger(__name__)


class PAPIFormTestCase(TestCase):
    """
    Test case for ``PAPIForm`` Form class.
    """

    def setUp(self):
        self.form = PAPIForm()

        self.papi_key = ''.join(random.choice(string.hexdigits) for _ in range(64))
        self.test_data = {
            'papi': self.papi_key
        }

        activate('en')

    def tearDown(self):
        activate('nl')

    def test_clean_papi(self):
        """
        Test the ``clean_papi`` function
        A valid URL in the GET from Stadlander should include ?papi=<hash>
        If it does, the PAPI data is returned
        """
        self.form.cleaned_data = self.test_data
        self.assertEqual(self.form.clean_papi(), self.test_data['papi'])

    def test_clean_empty_papi(self):
        """
        Test the ``clean_papi`` function raises a validation error if PAPI is
        empty

        Currently THIS FAILS
        """
        self.test_data['papi'] = ""
        self.form.cleaned_data = self.test_data

        # error = self.form.clean_papi()
        # LOG.info(error)
        self.assertRaisesMessage(
            ValidationError,
            u"[u'Sorry, your account details do not match those we have on "
            u"file']",
            self.form.clean_papi)

    def test_get_user(self):
        pass
