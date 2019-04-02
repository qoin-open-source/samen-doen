import re

from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _

from localflavor.nl.forms import NLZipCodeField

from cc3.cyclos.forms import DEFAULT_PHONE_REGEX
from cc3.cyclos.models.community import CC3Community
from cc3.registration.forms import BaseRegistrationForm

from ..profile.models import GENDER_CHOICES


class ICare4uRegistrationForm(BaseRegistrationForm):
    # ``CC3Profile`` fields.
    first_name = forms.CharField(
        max_length=30, label=_(u'First name'), error_messages={
            'required': _(u'Please enter your first name')})
    last_name = forms.CharField(
        max_length=30, label=_(u'Last name'), error_messages={
            'required': _(u'Please enter your last name')})
    community = forms.ModelChoiceField(
        label=_(u'Communities'),
        queryset=CC3Community.objects.all(),
        widget=forms.RadioSelect(),
        empty_label=None,
        error_messages={'required': _(u'Please choose the community where you '
                                      u'want to save Positoos.')})
    city = forms.CharField(
        max_length=255, label=_(u'City'),
        error_messages={'required': _(u'Please enter your city')})
    address = forms.CharField(
        max_length=255, label=_(u'Address'),
        error_messages={'required': _(u'Please enter your address')})
    postal_code = NLZipCodeField(
        label=_(u'Postal Code'),
        error_messages={'required': _(u'Please enter your postal code')})

    # iCare4u ``UserProfile`` fields.
    tussenvoegsel = forms.CharField(
        max_length=10, required=False, label=_(u'Tussenvoegsel'))

    phone_number = forms.CharField(
        max_length=255, required=False, label=_(u'Phone number'))

    mobile_number = forms.CharField(
        max_length=255, required=False, label=_(u'Mobile number'))

    extra_address = forms.CharField(
        max_length=255, required=False, label=_(u'Extra address'))

    num_street = forms.CharField(
        max_length=50, label=_(u'Street Number'),
        error_messages={'required': _(u'Please enter your street number')})
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, widget=forms.RadioSelect(), label=_(u'Gender'))
    wants_newsletter = forms.BooleanField(required=False)

    # iCare4u ``IndividualProfile`` fields.
    date_of_birth = forms.DateField(
        error_messages={'required': _(u'Please enter your date of birth')})

    def clean_reg_password(self):
        """
        Overrides the ``BaseRegistrationForm.clean_reg_password`` method to get
        rid of the numbers checking. Passwords can be without numbers. For more
        information, check Trac ticket #1825.
        """
        data = self.cleaned_data['reg_password']

        if len(data) < 8:
            raise forms.ValidationError(
                _(u"Please enter a password that is at least 8 characters "
                  u"long."))

        return data

    def clean_phone_number(self):
        data = self.cleaned_data.get('phone_number', '').strip()
        # remove internal spaces
        data = ''.join(data.split())
        if data:
            phone_re = re.compile(getattr(settings, 'CUSTOM_PHONE_REGEX',
                                          DEFAULT_PHONE_REGEX))
            if not phone_re.match(data):
                error_msg = _("Please enter a valid Phone Number")
                extra_msg = getattr(settings, 'CUSTOM_PHONE_REGEX_DESC', None)
                if extra_msg:
                    error_msg += u" ({0})".format(extra_msg)
                raise forms.ValidationError(error_msg)

        return data

    def clean_mobile_number(self):
        data = self.cleaned_data.get('mobile_number', '').strip()
        # remove internal spaces
        data = ''.join(data.split())
        if getattr(settings, 'MOBILE_NUMBER_MANDATORY', True):
            if not data:
                raise forms.ValidationError(
                    _("Please enter your Mobile Number"))

            if getattr(settings, 'MOBILE_NUMBER_MIN_LENGTH', None):
                if len(data.strip()) < settings.MOBILE_NUMBER_MIN_LENGTH:
                    raise forms.ValidationError(
                        _('Please enter a mobile number of at least {0} '
                          'digits'.format(settings.MOBILE_NUMBER_MIN_LENGTH)))

            if getattr(settings, 'MOBILE_NUMBER_MAX_LENGTH', None):
                if len(data.strip()) > settings.MOBILE_NUMBER_MAX_LENGTH:
                    raise forms.ValidationError(
                        _('Please enter a mobile number of at most {0} '
                          'digits'.format(settings.MOBILE_NUMBER_MAX_LENGTH)))

        # only validate number is there is one
        if data:
            mobile_re = re.compile(getattr(settings, 'CUSTOM_MOBILE_REGEX',
                                           DEFAULT_PHONE_REGEX))
            if not mobile_re.match(data):
                error_msg = _("Please enter a valid Mobile Number")
                extra_msg = getattr(settings, 'CUSTOM_MOBILE_REGEX_DESC', None)
                if extra_msg:
                    error_msg += u" ({0})".format(extra_msg)
                raise forms.ValidationError(error_msg)

        return data
