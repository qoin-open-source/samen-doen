# -*- coding: utf-8 -*-
import logging

import datetime
import re

from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.utils.translation import ugettext as _

from django_countries import countries
from easy_thumbnails.widgets import ImageClearableFileInput
from localflavor.generic.forms import IBANFormField
from localflavor.nl.forms import NLZipCodeField

from cc3.cyclos import backends
from cc3.cyclos.forms import DEFAULT_PHONE_REGEX
from cc3.cyclos.models import CC3Community, CyclosGroup, CyclosGroupSet, User
from cc3.cyclos.utils import check_cyclos_account
from cc3.rewards.models import UserCause, DefaultGoodCause, BusinessCauseSettings
from icare4u_front.profile.forms import VAT_NUMBER_REGEX

from icare4u_front.profile.models import (
    UserProfile, IndividualProfile, BusinessProfile, GENDER_CHOICES,
    InstitutionProfile, CharityProfile, ID_TYPES)
from icare4u_front.profile.utils import generate_username, squeeze_email, \
    generate_mandate_id
from icare4u_front.profile.validators import (
    city_validator, swift_bic_validator)
from icare4u_front.stadlander.models import StadlanderProfile

from django.forms import modelformset_factory, TextInput, Select, ValidationError
from cc3.cards.models import Card, Fulfillment, CardNumber, CardType, CARD_STATUS_ACTIVE, CARD_FULLFILLMENT_CHOICE_NEW

from cc3.cards import models as cc3_card_models
from django.db import transaction
from ajax_select import make_ajax_field
from django.db import IntegrityError

from cc3.cards.admin_forms import CardForm
from django.forms import BaseInlineFormSet

from cc3.cards.views_api import register_card
from cc3.cards.models import Operator, Terminal
from cc3.cards.validators import operator_pin_validator, card_number_validator, \
    imei_number_validator, iccid_validator

from django.core.validators import URLValidator
from django.forms import ModelForm

LOG = logging.getLogger(__name__)

kvk_re = re.compile(r'\d{8}')

reward_percentage_choices = (
    (False, _('User enters points amount on terminal')),
    (True, _('User enters euro amount spent by customer on terminal')),
)


# class CommunityCustomBusinessChoiceField(forms.ModelChoiceField):
#     def label_from_instance(self, obj):
#         if hasattr(obj, "cc3_profile") and obj.cc3_profile is not None:
#             return "%s (%s)" % (obj.cc3_profile.business_name, obj.email)
#         return ""

class CommunityTerminalModelForm(forms.ModelForm):
    """
    ``CommunityTerminal`` model form with custom behavior. Using this
    form, the ``organisatie`` field will show the business name.
    """
    # business = CommunityCustomBusinessChoiceField(queryset=User.objects.all())
    name = forms.CharField(label=_("Terminal number (IMEI)"), max_length=15,
                           min_length=15, required=False,
                           validators=[imei_number_validator, ])


class CommunityOperatorModelForm(forms.ModelForm):
    """
    ``CommunityOperator`` model form with custom behavior. Using this
    form, the ``pin`` field must be a 4 digit number.
    """
    pin = forms.CharField(label=_("PIN"), max_length=4,
                          min_length=4, required=False,
                          validators=[operator_pin_validator, ])


class CommunityUserProfileForm(forms.ModelForm):
    # ``CC3Profile`` fields.
    cyclos_group = forms.ModelChoiceField(
        label=_(u'Cyclos group'),
        queryset=CyclosGroup.objects.all(),
        help_text=_(u'Select the user group for this profile'))
    community = forms.ModelChoiceField(
        label=_(u'Community'), required=True,
        queryset=CC3Community.objects.all())
    gender = forms.ChoiceField(
        label=_(u'Gender'), choices=GENDER_CHOICES, required=False)
    date_of_birth = forms.DateField(label=_(u'Date of birth'), widget=widgets.AdminDateWidget(),
                                    required=False)
    business_name = forms.CharField(label=_(u"Business name"), max_length=255, required=False)
    city = forms.CharField(
        label=_("City"), max_length=255, required=False, validators=[city_validator])
    address = forms.CharField(label=_(u"Street address"), max_length=255, required=False)
    postal_code = NLZipCodeField(label=_(u"Postal code"), required=False)
    country = forms.ChoiceField(label=_(u"Country"), choices=countries, required=False)
    phone_number = forms.CharField(label=_(u"Phone number"), max_length=255, required=False)
    mobile_number = forms.CharField(label=_(u"Mobile number"), max_length=255, required=False)

    # #2842 Moving this to CommunityNonIndividualProfileForm as it is not
    # relevant for individual users
    #company_website = forms.URLField(max_length=255, required=False)
    #company_description = forms.CharField(
    #    widget=forms.Textarea, required=False)
    #is_visible = forms.BooleanField(required=False)

    picture = forms.ImageField(label=_(u"Picture"), required=False, widget=ImageClearableFileInput)
    picture_clear = forms.BooleanField(required=False)
    picture_height = forms.IntegerField(required=False)
    picture_width = forms.IntegerField(required=False)

    # iCare4u ``UserProfile`` fields.
    tussenvoegsel = forms.CharField(label=_(u"Surname prefix"), max_length=10, required=False)
    extra_address = forms.CharField(label=_(u"Extra address"), max_length=255, required=False)
    num_street = forms.IntegerField(
        label=_(u"Street number"), max_value=99999, required=False,
        error_messages={'invalid': _(u'Please enter a valid house number')})
    web_payments_enabled = forms.BooleanField(required=False)
    groupset = forms.ModelChoiceField(
        label=_(u'Groupset'), queryset=CyclosGroupSet.objects.all())
    id_type = forms.ChoiceField(
        choices=ID_TYPES, label=_(u'Type of ID'), required=False)

    document_number = forms.CharField(
        label=_(u'Document number'), required=False)

    expiration_date = forms.DateField(
        label=_(u"Expiration date"), required=False,
        widget=widgets.AdminDateWidget())

    account_first_activated = forms.DateTimeField(
        required=False, label=_(u'Date First Activated'))

    account_last_deactivated = forms.DateTimeField(
        required=False, label=_(u'Date Last Deactivated'))

    account_last_login = forms.DateTimeField(
        required=False, label=_(u'Date Last Login'))

    class Meta:
        model = User
        fields = (
            'cyclos_group',
            'email',
            'first_name',
            'tussenvoegsel',
            'last_name',
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityUserProfileForm, self).__init__(*args, **kwargs)

        self.fields['email'].required = True
        self.fields['email'].label = _("E-mail address")
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

        if self.instance.pk:
            del self.fields['web_payments_enabled']
            self.fields['cyclos_group'] = forms.CharField(
                label=_(u'Cyclos groups'), required=True,
                widget=forms.TextInput(attrs={'readonly': 'readonly'}))

            if hasattr(self.instance, 'cc3_profile') and self.instance.cc3_profile:
                self.fields['cyclos_group'].value = self.instance.cc3_profile.cyclos_group
        self.fields['account_first_activated'].widget.attrs['readonly'] = True
        self.fields['account_last_deactivated'].widget.attrs['readonly'] = True
        self.fields['account_last_login'].widget.attrs['readonly'] = True

    def clean_email(self):

        email_changed = False

        if self.instance.pk and \
                self.instance.email != self.cleaned_data['email']:
            email_changed = True

        if not self.instance.pk or email_changed:
            # Validate that email doesn't already exist in Cyclos.
            validation_message = check_cyclos_account(
                self.cleaned_data['email'])
            if validation_message:
                raise forms.ValidationError(validation_message)

            # Validate that the email doesn't already exist in Django.
            try:
                User.objects.get(email=self.cleaned_data['email'])
                raise forms.ValidationError(
                    _(u'This email has already been registered'))
            except User.DoesNotExist:
                pass

        return self.cleaned_data['email']

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

        return self.cleaned_data['mobile_number']

    def clean_date_of_birth(self):
        data = self.cleaned_data['date_of_birth']
        today = datetime.date.today()
        eighteen_years_ago = today + relativedelta(years=-18)

        if data and data > eighteen_years_ago:
            raise forms.ValidationError(_("Please enter a valid date"))

        return data

    def clean_document_number(self):
        data = self.cleaned_data.get('document_number', '')
        if data and not data.isalnum():
            error_msg = _("Please enter a valid Document Number")
            raise forms.ValidationError(error_msg)

        return data

    def clean_expiration_date(self):
        date = self.cleaned_data['expiration_date']
        if date and date < datetime.date.today():
            raise forms.ValidationError(_("The date cannot be in the past!"))
        return date

#    def clean_registration_number(self):
    # need to validate kvk number for anyone but individuals.
    # don't know if user is an individual or not inside an individual
    # field clean
#        data = self.cleaned_data.get('registration_number', '').strip()
#        # if included, registration_number is mandatory KvK number
#        if self.cleanedcyclos_group.name == getattr(
#                settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None):
#
#        if not data:
#            raise forms.ValidationError(_("Please enter your KvK Number"))
#
#        if len(data) != 8 or not kvk_re.match(data):
#            raise forms.ValidationError(
#                _('KvK number should be 8 digits'))
#
#        return data

    def save(self, commit=True):
        """
        Overrides base class ``save`` method to properly save the objects in
        the database. Objects to be saved are:
            * ``User``
            * ``UserProfile`` - related to ``User``.
        """

        profile_attrs = {
            'first_name': self.cleaned_data.get('first_name', ''),
            'last_name': self.cleaned_data.get('last_name', ''),
            'business_name': self.cleaned_data.get('business_name', ''),
            'city': self.cleaned_data.get('city', ''),
            'address': self.cleaned_data.get('address', ''),
            'postal_code': self.cleaned_data.get('postal_code', ''),
            'phone_number': self.cleaned_data.get('phone_number', ''),
            'mobile_number': self.cleaned_data.get('mobile_number', ''),
            'company_website': self.cleaned_data.get('company_website', ''),
            'company_description': self.cleaned_data.get(
                'company_description', ''),
            'community': self.cleaned_data.get('community', None),
            'tussenvoegsel': self.cleaned_data.get('tussenvoegsel', ''),
            'picture_height': self.cleaned_data.get('picture_height', None),
            'picture_width': self.cleaned_data.get('picture_width', None),
            'extra_address': self.cleaned_data.get('extra_address', ''),
            'num_street': self.cleaned_data.get('num_street') or '',
            'country': self.cleaned_data.get('country', None),
            'gender': self.cleaned_data.get('gender', ''),
            'date_of_birth': self.cleaned_data.get('date_of_birth', ''),
            'id_type': self.cleaned_data.get('id_type', ''),
            'document_number': self.cleaned_data.get('document_number', ''),
            'expiration_date': self.cleaned_data.get('expiration_date', None),
            # #2842 web payments enabled should always be True
            'web_payments_enabled': True,
            #'web_payments_enabled': self.cleaned_data.get(
            #    'web_payments_enabled', True),

            # #2842 Make cyclos_group readonly in change form
            #'cyclos_group': self.cleaned_data.get('cyclos_group', None),

            # #2842 Groupset should not be editable for non-individual users
            #'groupset': self.cleaned_data.get('groupset', None),

            'is_visible': self.cleaned_data.get('is_visible', False),
        }

        if self.cleaned_data.get('picture', None):
            profile_attrs['picture'] = self.cleaned_data.get('picture')
        elif self.cleaned_data.get('picture_clear', None):
            profile_attrs['picture'] = None
            profile_attrs['picture_height'] = None
            profile_attrs['picture_width'] = None

        # #2842 Make cyclos_group readonly in change form
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'cc3_profile'):
                cyclos_group = self.instance.cc3_profile.cyclos_group
            else:
                cyclos_group = None
        else:
            cyclos_group = self.cleaned_data.get('cyclos_group')
        profile_attrs['cyclos_group'] = cyclos_group

        # #2842 Allow editing the groupset attribute ONLY IF
        # we are creating a new account or the user is in one of the consumer groups
        if self.instance is None or self.instance.pk is None or\
                (cyclos_group and cyclos_group.name in getattr(
                 settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS')):
            profile_attrs['groupset'] = self.cleaned_data.get('groupset', None)

        # #2842 web payments enabled should always be True
        # attribute already set in profile_attrs
        # if cyclos_group and cyclos_group.name == getattr(
        #         settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP'):
        #     profile_attrs['web_payments_enabled'] = True

        if 'wants_newsletter' in self.cleaned_data:
            profile_attrs['wants_newsletter'] = self.cleaned_data.get(
                'wants_newsletter')

        # Create a new object or update the existent one.
        if not self.instance.pk:
            # Generate the username, as usual in CC3 projects.
            username = generate_username(
                squeeze_email(self.cleaned_data.get('email')))

            # Create the `User`.
            user = User.objects.create(
                username=username,
                email=self.cleaned_data.get('email'),
                first_name=self.cleaned_data.get('first_name'),
                last_name=self.cleaned_data.get('last_name')
            )

            # Create the `UserProfile` related to `User`.
            profile_attrs['user'] = user
            user_profile = UserProfile(**profile_attrs)
            # NB line above does not save the profile to the database!
            user_profile.save()
        else:
            # Update `User` data.
            # user = self.instance       (doesn't seem to work for checking
            # whether email address has changed -- not sure why!)
            user = User.objects.get(pk=self.instance.pk)

            new_email = self.cleaned_data.get('email')
            old_email = user.email
            if old_email != new_email:
                LOG.info(
                    "User {0} changing email address from {1} to {2}".format(
                        user.username, old_email, new_email))
            user.email = new_email
            user.first_name = self.cleaned_data.get('first_name')
            user.last_name = self.cleaned_data.get('last_name')
            user.save()

            # Update `UserProfile` data.
            user_profile = self.instance.cc3_profile.userprofile

            if not profile_attrs['community']:
                profile_attrs['community'] = user_profile.community
            if not profile_attrs['country']:
                profile_attrs['country'] = user_profile.country

            for key in profile_attrs.keys():
                setattr(user_profile, key, profile_attrs[key])

            group = backends.get_group(old_email)
            if group != cyclos_group.id:
                LOG.info(u"Changing user {0} group from {1} to {2}".format(
                    user.username, group, cyclos_group.id))
                backends.update_group(
                    self.instance.cc3_profile.cyclos_account.cyclos_id,
                    cyclos_group.id,
                    _(u"Group changed by community admin user."))

            user_profile.save()

        return user_profile


class CommunityNonIndividualProfileForm(CommunityUserProfileForm):
    user_id = forms.IntegerField(required=True, min_value=1)
    # #2842 Extracted non-individual user fields from parent class
    company_website = forms.CharField(label=_(u"Company website"), max_length=255, required=False)
    company_description = forms.CharField(
       label=_(u"Company description"), widget=forms.Textarea, required=False)
    is_visible = forms.BooleanField(label=_(u"Is visible"), required=False)

    # #2842 Groupset should not be visible to non-individual users
    exclude = ('groupset',)

    def __init__(self, *args, **kwargs):
        super(CommunityNonIndividualProfileForm, self).__init__(*args, **kwargs)
        # Remove excluded fields
        [self.fields.pop(f) for f in self.fields.keys() if f in self.exclude]

    # #3171 Remove the client-side validation of the company website and make it more user-friendly
    def clean_company_website(self):
        url = self.cleaned_data.get('company_website')

        # If the provided URL is not blank
        if url != '':
            # If the provided URL does not start with the http:// or https:// prefix
            # add the prefix to the URL
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
                self.cleaned_data['company_website'] = url
            # Get a handle to the validator
            validator = URLValidator()
            # Validate the URL
            try:
                validator(url)
            except ValidationError:
                # If invalid, set an error on the field
                self.add_error('company_website', forms.ValidationError(_("Please enter a valid website address.")))
        return url


class CommunityBusinessProfileForm(CommunityNonIndividualProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        label=_(u"Account holder"), max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False,
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    signature_date = forms.DateField(
        label=_(u"Signature date"), required=False, widget=widgets.AdminDateWidget())
    registration_number = forms.CharField(label=_('KvK number'), required=False,
                                          max_length=14)
    vat_number = forms.CharField(label=_('VAT Number'), required=False,
                                 max_length=14)

    reward_percentage = forms.BooleanField(label=_("reward percentage"),
                                           help_text=_('The reward is either entered on the terminal as an absolute amount of points or as a percentage of the transaction.'),
                                           required=False,
                                           initial=False)
    transaction_percentage = forms.DecimalField(label=_("transaction percentage"),
                                                help_text=_("Percentage of each transaction to be rewarded in points."),
                                                required=False, initial=0)

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityBusinessProfileForm, self).__init__(*args, **kwargs)
        self.fields['business_name'].required = True
        self.fields['reward_percentage'].widget = forms.RadioSelect(
            choices=reward_percentage_choices)

    def clean(self):
        cleaned_data = super(CommunityBusinessProfileForm, self).clean()

        if cleaned_data['reward_percentage'] is False:
            cleaned_data['transaction_percentage'] = 0

        return cleaned_data

    def clean_vat_number(self):
        data = self.cleaned_data.get('vat_number', '')
        if data:
            vat_number_re = re.compile(VAT_NUMBER_REGEX)
            if not vat_number_re.match(data):
                error_msg = _("Please enter a valid VAT Number")
                raise forms.ValidationError(error_msg)
        return data

    def clean_transaction_percentage(self):
        transaction_percentage = self.cleaned_data.get('transaction_percentage', '0')

        try:
            float(transaction_percentage)
        except Exception:
            error_msg = _("Enter a number between 0 and 100")
            raise forms.ValidationError(error_msg)

        if transaction_percentage < 0 or transaction_percentage > 100:
            error_msg = _("Enter a number between 0 and 100")
            raise forms.ValidationError(error_msg)
        else:
            return round(transaction_percentage, 2)

    def clean_registration_number(self):
        data = self.cleaned_data.get('registration_number', '').strip()
        # if included, registration_number is mandatory KvK number
        if data:
            if len(data) != 8 or not kvk_re.match(data):
                raise forms.ValidationError(
                    _('KvK number should be 8 digits'))

        return data

    def save(self, commit=True):
        user_profile = super(CommunityBusinessProfileForm, self).save(commit)

        business_attrs = {
            'profile': user_profile,
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', ''),
            'mandate_id': generate_mandate_id(user_profile.user),
            'signature_date': self.cleaned_data.get('signature_date', ''),
            'registration_number': self.cleaned_data.get('registration_number', ''),
            'vat_number': self.cleaned_data.get('vat_number', ''),
        }

        business_cause_settings_attrs = {
            'user': user_profile.user,
            'reward_percentage': self.cleaned_data.get('reward_percentage', False),
            'transaction_percentage': self.cleaned_data.get('transaction_percentage','0'),
        }

        if not self.instance.pk:
            business = BusinessProfile.objects.create(**business_attrs)
            BusinessCauseSettings.objects.create(**business_cause_settings_attrs)
        else:
            business = self.instance.cc3_profile.userprofile.business_profile

            for key in business_attrs.keys():
                setattr(business, key, business_attrs[key])

            business.save()

            business_cause_settings = self.instance.cc3_profile.user.businesscausesettings
            for key in business_cause_settings_attrs.keys():
                setattr(business_cause_settings, key, business_cause_settings_attrs[key])

            business_cause_settings.save()

        return business


class CommunityInstitutionProfileForm(CommunityNonIndividualProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False,
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    signature_date = forms.DateField(
        required=False, widget=widgets.AdminDateWidget())
    registration_number = forms.CharField(label=_('KvK number'), required=False,
                                          max_length=14)
    vat_number = forms.CharField(label=_('VAT Number'), required=False,
                                 max_length=14)

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityInstitutionProfileForm, self).__init__(*args, **kwargs)

        self.fields['business_name'].required = True

    def clean_vat_number(self):
        data = self.cleaned_data.get('vat_number', '')
        if data:
            vat_number_re = re.compile(VAT_NUMBER_REGEX)
            if not vat_number_re.match(data):
                error_msg = _("Please enter a valid VAT Number")
                raise forms.ValidationError(error_msg)

        return data

    def clean_registration_number(self):
        data = self.cleaned_data.get('registration_number', '').strip()
        # if included, registration_number is mandatory KvK number
        if data:
            if len(data) != 8 or not kvk_re.match(data):
                raise forms.ValidationError(
                    _('KvK number should be 8 digits'))

        return data

    def save(self, commit=True):
        user_profile = super(CommunityInstitutionProfileForm, self).save(commit)

        institution_attrs = {
            'profile': user_profile,
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', ''),
            'mandate_id': generate_mandate_id(user_profile.user),
            'signature_date': self.cleaned_data.get('signature_date', ''),
            'registration_number': self.cleaned_data.get('registration_number', ''),
            'vat_number': self.cleaned_data.get('vat_number', '')
        }

        if not self.instance.pk:
            institution = InstitutionProfile.objects.create(**institution_attrs)
        else:
            institution = \
                self.instance.cc3_profile.userprofile.institution_profile
            for key in institution_attrs.keys():
                setattr(institution, key, institution_attrs[key])

            institution.save()

        return institution


class CommunityCharityProfileForm(CommunityNonIndividualProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False,
                                 widget=forms.TextInput(
                                     attrs={'readonly': 'readonly'}))
    signature_date = forms.DateField(
        required=False, widget=widgets.AdminDateWidget())
    registration_number = forms.CharField(label=_('KvK number'), required=False,
                                          max_length=14)

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityCharityProfileForm, self).__init__(*args, **kwargs)

        self.fields['business_name'].required = True

    def clean_registration_number(self):
        data = self.cleaned_data.get('registration_number', '').strip()
        # if included, registration_number is mandatory KvK number
        if data:
            if len(data) != 8 or not kvk_re.match(data):
                raise forms.ValidationError(
                    _('KvK number should be 8 digits'))

        return data

    def save(self, commit=True):
        user_profile = super(CommunityCharityProfileForm, self).save(commit)

        charity_attrs = {
            'profile': user_profile,
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', ''),
            'mandate_id': generate_mandate_id(user_profile.user),
            'signature_date': self.cleaned_data.get('signature_date', ''),
            'registration_number': self.cleaned_data.get('registration_number', '')
        }

        if not self.instance.pk:
            charity = CharityProfile.objects.create(**charity_attrs)
        else:
            charity = self.instance.cc3_profile.userprofile.charity_profile
            for key in charity_attrs.keys():
                setattr(charity, key, charity_attrs[key])

            charity.save()

        return charity


class CommunityIndividualProfileForm(CommunityUserProfileForm):
    user_id = forms.IntegerField(required=True, min_value=1)
    # Retrieve the Cyclos 'good causes' group, if any.
    charity_group = getattr(
        settings, 'CYCLOS_CHARITY_MEMBER_GROUP', 'Goede Doelen')

    # moving to UserProfileForm
    #    date_of_birth = forms.DateField(widget=widgets.AdminDateWidget())
    nickname = forms.CharField(max_length=255, required=False)
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    good_cause = forms.ModelChoiceField(
        label=_('Selected Good cause'),
        queryset=User.objects.filter(
            cc3_profile__cyclos_group__name=charity_group,
            is_active=True
        ))
    # #3234 enabling community admins to view edit percentage donation to user cause
    donation_percent = forms.IntegerField(
        label=_('Donation percentage'), show_hidden_initial=True)
    # #2476 create SL profile if SL groupset selected
    rel_number = forms.IntegerField(required=False,
                                    label=_('Stadlander rel number'),
                                    help_text=_(u'Stadlander groupset only'))
    wants_newsletter = forms.BooleanField(
        required=False,
        label=_('Newsletter'),
        help_text=_('Wants to receive newsletter'))

    def __init__(self, *args, **kwargs):
        """
        Store the old groupset so we know if it changes
        """
        super(CommunityIndividualProfileForm, self).__init__(*args, **kwargs)
        try:
            self.old_groupset = self.instance.cc3_profile.groupset
        except:
            self.old_groupset = None

        # 2876 only show active good causes accounts in the right community
        cc3_community = self.instance.cc3_profile.community
        self.fields['good_cause'].queryset = \
            self.fields['good_cause'].queryset.filter(
                cc3_profile__community=cc3_community)

        # show business name with (email address)
        # asterisk the default good choice for the community
        try:
            default_good_cause = DefaultGoodCause.objects.get(
                community=cc3_community).cause

        except DefaultGoodCause.DoesNotExist:
            default_good_cause = None
            LOG.critical(
                _(u"No default good cause exists for {0} community").format(
                    cc3_community))

        # style the query set
        if default_good_cause:
            self.fields['good_cause'].label_from_instance = \
                lambda obj: obj == default_good_cause and \
                "* %s (%s)" % (obj.cc3_profile.business_name, obj.email) or \
                "%s (%s)" % (obj.cc3_profile.business_name, obj.email)
        else:
            self.fields['good_cause'].label_from_instance = \
                lambda obj: "%s (%s)" % (obj.cc3_profile.business_name,
                                         obj.email)

    def clean(self):
        """
        rel_number is required iff groupset is the Stadlander groupset
        """
        # LOG.debug(self.cleaned_data)
        groupset = self.cleaned_data.get('groupset')
        rel_number = self.cleaned_data.get('rel_number', None)
        if groupset.id == settings.STADLANDER_GROUPSET_ID:
            if not rel_number:
                if 'rel_number' not in self._errors:
                    self._errors["rel_number"] = self.error_class([_(
                        u"You must supply a rel_number for "
                        u"Stadlander groupset")])
            else:
                # check rel_number isn't already linked to another profile
                if StadlanderProfile.objects.filter(
                    rel_number=rel_number).exclude(
                        profile__user=self.instance).count():
                    self._errors["rel_number"] = self.error_class([_(
                        u"rel_number is already in use")])
                    del self.cleaned_data['rel_number']
        else:
            if rel_number:
                self._errors["rel_number"] = self.error_class([_(
                    u"rel_number should be empty for non-Stadlander groupset")])
                del self.cleaned_data['rel_number']

        community = self.instance.cc3_profile.community
        if community:
            if self.cleaned_data['donation_percent'] > community.max_donation_percent:
                self._errors['donation_percent'] = self.error_class([_(
                    u'Donation percentage must not exceed {0}%'.format(
                        community.max_donation_percent))])
                del self.cleaned_data['donation_percent']
            elif self.cleaned_data['donation_percent'] < community.min_donation_percent:
                self._errors['donation_percent'] = self.error_class([_(
                    u'Donation percentage must be at least {0}%'.format(
                        community.min_donation_percent))])
                del self.cleaned_data['donation_percent']

        return self.cleaned_data

    def save(self, commit=True):
        user_profile = super(CommunityIndividualProfileForm, self).save(commit)
        user_profile.business_name = user_profile.name
        user_profile.save()

        if user_profile.groupset.id == settings.STADLANDER_GROUPSET_ID:
            # create or update Stadlander profile with rel_number
            rel_number = self.cleaned_data.get('rel_number', '')
            try:
                sl_profile = StadlanderProfile.objects.get(
                    profile=user_profile)
                if sl_profile.rel_number != rel_number:
                    sl_profile.rel_number = rel_number
                    sl_profile.save()
                    LOG.info(u"Updated rel_number for StadlanderProfile "
                             u"{0}".format(sl_profile))
            except StadlanderProfile.DoesNotExist:
                sl_profile = StadlanderProfile.objects.create(
                    profile=user_profile,
                    rel_number=rel_number)
                LOG.info(u"Created StadlanderProfile {0}".format(
                    sl_profile))

        # if groupset changed from Sstadlander,
        # may need to delete Stadlander profile
        if self.old_groupset != user_profile.groupset:
            if self.old_groupset.id == settings.STADLANDER_GROUPSET_ID:
                # delete Stadlander profile
                LOG.info(u"User {0} moved out of Stadlander groupset. "
                         u"Deleting StadlanderProfile".format(
                            user_profile.user.username))
                for sl_profile in StadlanderProfile.objects.filter(
                                                    profile=user_profile):
                    sl_profile.delete()
            else:
                if user_profile.groupset.id == settings.STADLANDER_GROUPSET_ID:
                    LOG.info(u"User {0} moved into Stadlander "
                             u"groupset.".format(user_profile.user.username))

        individual_attrs = {
            'profile': user_profile,
            'nickname': self.cleaned_data.get('nickname', ''),
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', '')
        }

        if not self.instance.pk:
            individual = IndividualProfile.objects.create(
                **individual_attrs)
        else:
            individual = \
                self.instance.cc3_profile.userprofile.individual_profile

            for key in individual_attrs.keys():
                setattr(individual, key, individual_attrs[key])

            individual.save()

        # Save the selected 'good cause', if any.
        good_cause = self.cleaned_data.get('good_cause', None)
        donation_percent = self.cleaned_data.get('donation_percent', None)

        if good_cause:
            try:
                user_cause = UserCause.objects.get(consumer=user_profile.user)
                user_cause.cause = good_cause
                user_cause.donation_percent = donation_percent
                user_cause.save()
            except UserCause.DoesNotExist:
                UserCause.objects.create(
                    consumer=user_profile.user, cause=good_cause)

        return individual


class CommunityFulfillmentForm(ModelForm):
    class Meta:
        model = Fulfillment
        fields = ('profile',)
        labels = {
            'profile': _(u"User profile"),
        }


class CommunityCardForm(ModelForm):
    class Meta:
        model = Card
        fields = ('number', 'owner', 'fulfillment')
        labels = {
            'owner': _(u"User profile"),
        }

    number = make_ajax_field(CardNumber, 'number', 'number')
    fulfillment = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super(CommunityCardForm, self).__init__(*args, **kwargs)
        self.fields['fulfillment'].widget = forms.HiddenInput()
        self.fields['number'].validators = [card_number_validator,]
        self.fields['number'].required = True
        self.fields['owner'].required = True

    # Validate that the received card number has not changed
    def clean(self):
        cleaned_data = super(CommunityCardForm, self).clean()

        number = self.cleaned_data.get('number', None)

        if number:
            if CardNumber.objects.filter(number=number).exists():
                if Card.objects.filter(number__number=number).exists():
                    self.add_error('number', forms.ValidationError(
                                            _(u'This card is already connected to another user')))
            else:
                self.add_error('number', forms.ValidationError(
                                        _(u'This card number does not exist')))

        fid = self.cleaned_data.get('fulfillment')
        f = None

        if fid:
            try:
                f = Fulfillment.objects.get(id=fid)

                # Check if the fulfillment object is in the right state
                if f.status != cc3_card_models.CARD_FULLFILLMENT_CHOICE_NEW:
                    self.add_error('fulfillment', forms.ValidationError(_('Fulfillment must be new.')))
            except Fulfillment.DoesNotExist:
                self.add_error('fulfillment', forms.ValidationError(_('Invalid fulfillment id.')))

        owner = self.cleaned_data.get('owner', None)

        if owner is not None and f is not None:
            if f.profile.user != owner:
                self.add_error('fulfillment', forms.ValidationError(
                    _('Fulfillment and owner fields do not pertain to the same user.')))
                self.add_error('owner', forms.ValidationError(
                    _('Fulfillment and owner fields do not pertain to the same user.')))

        profile = None

        if owner is not None and hasattr(owner, 'cc3_profile') and owner.cc3_profile is not None:
            profile = owner.cc3_profile
        # elif f is not None and hasattr(f, 'profile') and f.profile is not None:
        #     profile = f.profile

        if profile is not None:
            if profile.cyclos_group.name not in settings.CYCLOS_CARD_USER_MEMBER_GROUPS:
                self.add_error('owner', forms.ValidationError(_('User not in card user member group.')))
        # else:
        #     self.add_error('owner', forms.ValidationError(
        #         _('User has no profile.')))

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        if self.instance.pk is None:
            card = super(CommunityCardForm, self).save(commit=False)
            try:
                # #3449 Card type is always default
                # Card status is always active (on creation)
                # Activation date automatic
                card.card_type = CardType.objects.get(default=True)
                card.status = CARD_STATUS_ACTIVE;
                card.activation_date = datetime.datetime.now()
                card.save()
                self.save_m2m();

                fid = self.cleaned_data.get('fulfillment')

                # Make creating cards without linking to a fulfillment possible for now
                if fid is not None and fid != '':
                    f = Fulfillment.objects.get(id=fid)
                    if f.status == CARD_FULLFILLMENT_CHOICE_NEW:
                        f.status = cc3_card_models.CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED
                        f.card = card
                        f.save()
                    else:
                        LOG.error(_("Cannot connect a new Card based on a non-new Fulfillment."))
                        raise ValidationError(_("Cannot connect a new Card based on a non-new Fulfillment."))

            except CardType.MultipleObjectsReturned as e:
                LOG.error(e + " " +_("More than one default card type returned."))
            except Fulfillment.DoesNotExist as e:
                LOG.error(e + " " + _(" Fulfillment with id: {} does not exist.").format(fid))
            except IntegrityError as e:
                LOG.error(e)
            return card


class MiniTerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['name', 'icc_id', 'comments',]

    name = forms.CharField(label=_("Terminal number (IMEI)"), max_length=15,
                           min_length=15, required=False,
                           validators=[imei_number_validator, ])
    icc_id = forms.CharField(label=_("SIM card number (ICCID)"), required=False,
                             max_length=20, validators=[iccid_validator, ])
    comments = forms.CharField(max_length=250, required=False)

    def __init__(self, *args, **kwargs):
        super(MiniTerminalForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['name'].widget.attrs['readonly'] = True
        self.fields['comments'].widget = forms.Textarea()
        self.fields['comments'].widget.attrs = {
                                            'rows': 1,
        }

        # Error messages already provided in the validator
        self.fields['name'].error_messages={
            'max_length': '',
            'min_length': '',
        }

        # Error messages already provided in the validator
        self.fields['icc_id'].error_messages = {
            'max_length': '',
            'min_length': '',
        }

    def clean(self):
        try:
            name = self.cleaned_data['name']

            if name:
                if self.instance is None or self.instance.pk is None:
                    terminal = Terminal.objects.get(name=name)

                    if terminal.business == self.instance.business:
                        self._errors['name'] = self.error_class([_(
                            u'This terminal is already assigned to this user')])
                        del self.cleaned_data['name']
                    elif terminal.business is not None:
                        self._errors['name'] = self.error_class([_(
                            u'This terminal is assigned to another user')])
                        del self.cleaned_data['name']
                    elif terminal.removed_date is not None:
                        self._errors['name'] = self.error_class([_(
                            u'This terminal has been removed')])
                        del self.cleaned_data['name']
        except KeyError:
            raise ValidationError(_("Invalid form submitted"))
        except Terminal.DoesNotExist:
            self._errors['name'] = self.error_class([_(
                u'This terminal does not exist')])
            del self.cleaned_data['name']

    def save(self, commit=True):
        try:
            name = self.cleaned_data['name']
            icc_id = self.cleaned_data['icc_id']
            comments = self.cleaned_data['comments']
        except KeyError as e:
            return

        if name:
            # If the form corresponds to an existing instance
            if self.instance is not None:
                if self.instance.pk is not None:
                    self.instance.icc_id = icc_id
                    self.instance.comments = comments
                    self.instance.save()
                # else, create a new instance
                else:
                    try:
                        terminal = Terminal.objects.get(name=name)
                        terminal.icc_id = icc_id
                        terminal.comments = comments
                        terminal.business = self.instance.business
                        terminal.save()
                    except Terminal.DoesNotExist:
                        pass

    # TODO: Investigate how to genericize this function in a pythonic way
    def delete_terminal(self):
        """
        Function to disconnect the operator from the business
        """
        if self.instance is not None and self.instance.pk is not None:
            self.instance.business = None
            self.instance.last_seen_date = None
            self.instance.save()


# TODO: Investigate how to genericize this class in a pythonic way
class TerminalBaseFormset(BaseInlineFormSet):

    # Default value for the inline formset element id
    # Need to provide a custom value in case there are multiple
    # inline formsets within the same HTML document
    formset_element_id = "terminal_inline_set"

    def __init__(self, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None, queryset=None,
                 formset_element_id=None, **kwargs):
        super(TerminalBaseFormset, self).__init__(
            data=data, files=files, instance=instance, save_as_new=save_as_new,
            prefix=prefix, queryset=queryset, **kwargs)
        if formset_element_id is not None:
            self.formset_element_id = formset_element_id

    # Calls each form's save function, except for the last "extra" form
    def save(self, commit=True):
        for i, form in enumerate(self.forms):
            if i < len(self.forms) - 1:
                # Check if the form has a the number and status field values
                # in its cleaned data. This is to account for
                # unsaved forms that have been deleted
                if 'name' in form.cleaned_data and\
                    'icc_id' in form.cleaned_data and \
                        'comments' in form.cleaned_data:
                    form.save()

        # For each deleted form, delete the operator
        for deleted in self.deleted_forms:
            if 'name' in deleted.cleaned_data and \
                'icc_id' in deleted.cleaned_data and \
                    'comments' in deleted.cleaned_data:
                deleted.delete_terminal()


class MiniOperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = ['name', 'pin',]

    name = forms.CharField(max_length=50, required=False)
    pin = forms.CharField(max_length=4, required=False,
                          validators=[operator_pin_validator, ])

    def __init__(self, *args, **kwargs):
        super(MiniOperatorForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['name'].widget.attrs['readonly'] = True

    def clean(self):
        try:
            name = self.cleaned_data['name']
            pin = self.cleaned_data['pin']

            if name and pin:
                # For existing instances, make name uneditable on server side
                if self.instance.pk is not None:
                    if name != self.instance.name:
                        self._errors['name'] = self.error_class([_(
                            u'Name is incorrect')])
                        del self.cleaned_data['name']
                # Check if the name is already registered for the given business
                # Performing this check this way for a lack of a better solution
                # e.g. harnessing the unique validation from the Operator model
                elif Operator.objects.filter(
                        name=name, business=self.instance.business).exists():
                    self._errors['name'] = self.error_class([_(
                        u'Name already exists')])
                    del self.cleaned_data['name']
        except KeyError:
            raise forms.ValidationError(_('Invalid form submitted'))

    def save(self, commit=True):
        try:
            name = self.cleaned_data['name']
            pin = self.cleaned_data['pin']
        except KeyError:
            return

        if name and pin:
            # If the form corresponds to an existing instance
            if self.instance is not None and self.instance.pk is not None:
                self.instance.pin = pin
                self.instance.save()
            # else, create a new instance
            else:
                Operator.objects.create(name=name,
                                        business=self.instance.business,
                                        pin=pin)

    # TODO: Investigate how to genericize this function in a pythonic way
    def delete_operator(self):
        """
        Function to delete the operator
        """
        if self.instance is not None and self.instance.pk is not None:
            self.instance.delete()


# TODO: Investigate how to genericize this class in a pythonic way
class OperatorBaseFormset(BaseInlineFormSet):

    # Default value for the inline formset element id
    # Need to provide a custom value in case there are multiple
    # inline formsets within the same HTML document
    formset_element_id = "operator_inline_set"

    def __init__(self, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None, queryset=None,
                 formset_element_id=None, **kwargs):
        super(OperatorBaseFormset, self).__init__(
            data=data, files=files, instance=instance, save_as_new=save_as_new,
            prefix=prefix, queryset=queryset, **kwargs)
        if formset_element_id is not None:
            self.formset_element_id = formset_element_id

    # Calls each form's save function, except for the last "extra" form
    def save(self, commit=True):
        for i, form in enumerate(self.forms):
            if i < len(self.forms)-1:
                # Check if the form has a the number and status field values
                # in its cleaned data. This is to account for
                # unsaved forms that have been deleted
                if 'name' in form.cleaned_data and 'pin' in form.cleaned_data:
                    form.save()

        # For each deleted form, delete the operator
        for deleted in self.deleted_forms:
            if 'name' in deleted.cleaned_data and 'pin' in deleted.cleaned_data:
                deleted.delete_operator()


class MiniCardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['status', 'number', ]

    number = forms.CharField(max_length=16, min_length=1, required=False,
                             validators=[card_number_validator,])
    status_names = (cc3_card_models.CARD_STATUS_ACTIVE,
                    cc3_card_models.CARD_STATUS_BLOCKED)
    # Variable used to maintain information about the card retrieved from the DB
    # across the clean() and save() function
    existing_card = None

    def __init__(self, *args, **kwargs):
        super(MiniCardForm, self).__init__(*args, **kwargs)

        # #3012 Make card number uneditable
        if self.instance and self.instance.pk:
            self.fields['number'].widget = TextInput()
            self.fields['number'].widget.attrs['readonly'] = True
        # If the form does not correspond to an existing instance
        # Enable editing
        else:
            self.fields['number'].widget = TextInput()

        # #3421 Limit card statuses to Block/Unblock
        card_status_choices = [status
                               for status in cc3_card_models.CARD_STATUS_CHOICES
                               if status[0] in self.status_names]
        self.fields['status'].widget = Select(choices=card_status_choices)

    def clean(self):
        try:
            number = self.cleaned_data['number']
            status = self.cleaned_data['status']

            if number and status:
                # #3012 For existing instances, make card number uneditable
                if self.instance.pk is not None:
                    if number != str(self.instance.number.number):
                        self._errors['number'] = self.error_class([_(
                            u'Card number is incorrect')])
                        del self.cleaned_data['number']
                # If the form does not correspond to an existing instance
                else:
                    # Check in the DB if a card with the provided number exists
                    self.existing_card = Card.objects.get(number__number=number)

                    # If the card's owner is the current user then
                    # no need to add it
                    if self.existing_card.owner == self.cleaned_data['owner']:
                        self._errors['number'] = self.error_class(
                            [_(u'This card is already added')])
                        del self.cleaned_data['number']
                    else:
                        self._errors['number'] = self.error_class(
                            [_(u'This card is owned by another user')])
                        del self.cleaned_data['number']

                # #3421 Limit card statuses to Block/Unblock
                if status not in self.status_names:
                    self._errors['status'] = self.error_class([_(
                        u'Card status is incorrect')])
                    del self.cleaned_data['number']
        except KeyError:
            pass
        except Card.DoesNotExist:
            pass

        return self.cleaned_data

    def save(self, commit=True):
        try:
            number = self.cleaned_data['number']
            status = self.cleaned_data['status']
            owner = self.cleaned_data['owner']
        except KeyError:
            return

        if not number or not status or not owner:
            return

        # If the form corresponds to an existing instance
        if self.instance is not None and self.instance.pk is not None:
            self.instance.owner = owner
            self.instance.status = status
            self.instance.save()
        # Else, if the form corresponds to newly entered data
        # that corresponds to an existing card
        # Note: the self.existing_card variable is set in the clean() method
        # This is to avoid querying the database twice
        elif self.existing_card is not None:
            self.existing_card.owner = owner
            self.existing_card.status = status
            self.existing_card.save()
        # If the form data corresponds to a new card to be created,
        # Create it
        else:
            try:
                card_number = CardNumber.objects.get(number=long(number))
                register_card(card_number, owner, status=status)
            except CardNumber.DoesNotExist as e:
                LOG.error(e)
                raise ValidationError(_("Card number does not exist."))

    # TODO: Investigate how to genericize this function in a pythonic way
    def delete_card(self):
        """
        Function to delete the card
        """
        if self.instance is not None and self.instance.pk is not None:
            self.instance.delete()


# TODO: Investigate how to genericize this class in a pythonic way
class CardBaseFormset(BaseInlineFormSet):

    # Default value for the inline formset element id
    # Need to provide a custom value in case there are multiple
    # inline formsets within the same HTML document
    formset_element_id = "card_inline_set"

    def __init__(self, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None, queryset=None,
                 formset_element_id=None, **kwargs):
        super(CardBaseFormset, self).__init__(
            data=data, files=files, instance=instance, save_as_new=save_as_new,
            prefix=prefix, queryset=queryset, **kwargs)
        if formset_element_id is not None:
            self.formset_element_id = formset_element_id

    # Calls each form's save function, except for the last "extra" form
    def save(self, commit=True):
        for i, form in enumerate(self.forms):
            if i < len(self.forms)-1:
                # Check if the form has a the number and status field values
                # in its cleaned data. This is to account for
                # unsaved forms that have been deleted
                if 'number' in form.cleaned_data and \
                        'status' in form.cleaned_data:
                    form.save()

        # For each deleted form, delete the card
        for deleted in self.deleted_forms:
            if 'number' in deleted.cleaned_data and \
                    'status' in deleted.cleaned_data:
                deleted.delete_card()
