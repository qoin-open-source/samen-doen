import string

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import ugettext as _

from django_countries.data import COUNTRIES


def swift_bic_validator(value):
    """
    Validation for ISO 9362:2009 (SWIFT-BIC).

    Shamelessly copied from the deprecated package 'django-iban':
    https://github.com/benkonrath/django-iban

    Should be included in 'django-localflavor' some day. Until then, this can
    remain here for practical purposes (not having repeated dependencies).
    """

    if not value:
        return

    # Length is 8 or 11.
    swift_bic_length = len(value)
    if swift_bic_length != 8 and swift_bic_length != 11:
        raise ValidationError(
            _('A SWIFT-BIC is either 8 or 11 characters long.'))

    # First 4 letters are A - Z.
    institution_code = value[:4]
    for x in institution_code:
        if x not in string.ascii_uppercase:
            raise ValidationError(
                _('{0} is not a valid SWIFT-BIC Institution Code.').format(
                    institution_code))

    # Letters 5 and 6 consist of an ISO 3166-1 alpha-2 country code.
    country_code = value[4:6]
    if country_code not in COUNTRIES:
        raise ValidationError(
            _('{0} is not a valid SWIFT-BIC Country Code.').format(
                country_code))


# Validator for Dutch cities (only letters, spaces, apostrophes and dashes).
city_validator = RegexValidator(
    regex=r"^[a-zA-Z '-]+$", message=_('Please enter a valid city'),
    code='invalid_city')
