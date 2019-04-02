from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import activate, ugettext_lazy as _

from ..validators import swift_bic_validator


class SwiftBicValidatorTestCase(TestCase):
    def setUp(self):
        activate('en')

    def tearDown(self):
        activate('nl')

    def test_characters_number(self):
        """
        Tests that the SWIFT code is invalid if it's formed by a number of
        characters different than 8 or 11.
        """
        self.assertRaisesMessage(
            ValidationError,
            _('A SWIFT-BIC is either 8 or 11 characters long.'),
            swift_bic_validator, 'ABCDEF3')

    def test_wrong_institution_code(self):
        """
        Tests that SWIFT code is invalid if the first 4 characters are not
        letters from A to Z.
        """
        code = '12345678'

        self.assertRaisesMessage(
            ValidationError,
            _('1234 is not a valid SWIFT-BIC Institution Code.'),
            swift_bic_validator, code)

    def test_wrong_country_code(self):
        """
        Tests that SWIFT code is invalid if the 5th and 6th characters are not
        a valid ISO country code.
        """
        code = 'ABCDXX12'

        self.assertRaisesMessage(
            ValidationError,
            _('XX is not a valid SWIFT-BIC Country Code.'),
            swift_bic_validator, code)
