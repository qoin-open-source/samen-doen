import datetime
import logging
import re

from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django_countries import countries

from localflavor.generic.forms import IBANFormField
from localflavor.nl.forms import NLZipCodeField

from cc3.core.forms import RestrictiveFileField
from cc3.core.models import Category
from cc3.core.widgets import CheckboxSelectMultipleCategoriesTree
from cc3.cyclos.forms import DEFAULT_PHONE_REGEX
from cc3.cyclos.models import CC3Community, User, CC3Profile
from cc3.cyclos.utils import check_cyclos_account

from .models import (
    UserProfile, IndividualProfile, BusinessProfile, GENDER_CHOICES,
    InstitutionProfile, CharityProfile, ID_TYPES)
from .utils import generate_username, squeeze_email, generate_mandate_id
from .validators import city_validator, swift_bic_validator
from .utils import is_default_email, is_default_firstname, is_default_lastname

LOG = logging.getLogger(__name__)
VAT_NUMBER_REGEX = '(NL)?[0-9]{9}B[0-9]{2}'

attrs_dict = {'class': 'required'}


class TermsAndConditionsForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs=dict(attrs_dict, maxlength=75,
                       placeholder=_(u'Email Address'))),
        label=_(u'Email Address'),
        error_messages={'required': _(u'Please enter your Email address')})
    email_confirmation = forms.EmailField(
        widget=forms.TextInput(
            attrs=dict(attrs_dict, maxlength=75,
                       placeholder=_(u'Confirm Email'))),
        label=_(u'Email Address (again)'),
        error_messages={'required': _(u'Please confirm your Email address')})

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, required=True, widget=forms.RadioSelect(),
        label=_(u'Gender'))

    reg_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs=dict(attrs_dict, render_value=False,
                       placeholder=_(u'Password'))),
        label=_(u"Password"),
        error_messages={'required': _(u'Please enter your chosen password')})
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(
            attrs=dict(attrs_dict, render_value=False,
                       placeholder=_(u'Confirm Password'))),
        label=_(u"Password (again)"),
        error_messages={'required': _(u'Please confirm your chosen password')})

    date_of_birth = forms.DateField(
        error_messages={'required': _(u'Please enter your date of birth')})

    city = forms.CharField(
        max_length=255, required=True, validators=[city_validator])
    address = forms.CharField(max_length=255, required=True)
    postal_code = NLZipCodeField(required=True)
    phone_number = forms.CharField(max_length=255, required=False)

    # iCare4u ``UserProfile`` fields.
    tussenvoegsel = forms.CharField(max_length=10, required=False)
    extra_address = forms.CharField(max_length=255, required=False)
    num_street = forms.IntegerField(
        max_value=99999, required=True,
        error_messages={'invalid': _(u'Please enter a valid house number')})
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, required=True, widget=forms.RadioSelect(),
        label=_(u'Gender'))
    terms_and_conditions = forms.BooleanField(required=True)

    class Meta:
        model = User
        localized_fields = ('__all__', )
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        super(TermsAndConditionsForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True

    def save(self, commit=True):
        """
        Overrides base class ``save`` method to properly save the objects in
        the database. Objects to be saved are:
            * ``User``
            * ``UserProfile`` - related to ``User``.
        """
        profile_attrs = {
            'city': self.cleaned_data.get('city', ''),
            'address': self.cleaned_data.get('address', ''),
            'postal_code': self.cleaned_data.get('postal_code', ''),
            'phone_number': self.cleaned_data.get('phone_number', ''),
            'mobile_number': self.cleaned_data.get('mobile_number', ''),
            'tussenvoegsel': self.cleaned_data.get('tussenvoegsel', ''),
            'extra_address': self.cleaned_data.get('extra_address', ''),
            'num_street': self.cleaned_data.get('num_street') or '',
            'gender': self.cleaned_data.get('gender', ''),
            'date_of_birth': self.cleaned_data.get('date_of_birth', ''),
            'terms_and_conditions': self.cleaned_data.get(
                'terms_and_conditions', ''),
            'wants_newsletter': self.cleaned_data.get('wants_newsletter', ''),
        }

        # Update `User` data.
        user = self.instance.profile.user
        user.email = self.cleaned_data.get('email')
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.set_password(self.cleaned_data.get('reg_password'))
        user.save()

        # Update `UserProfile` data.
        user_profile = self.instance.profile
        if 'wants_newsletter' in self.cleaned_data:
            user_profile.wants_newsletter = \
                self.cleaned_data.get('wants_newsletter')

        for key in profile_attrs.keys():
            setattr(user_profile, key, profile_attrs[key])

        user_profile.save()

        # belt and braces
        cc3_profile = CC3Profile.objects.get(user=user)
        cc3_profile.first_name = self.cleaned_data.get('first_name')
        cc3_profile.last_name = self.cleaned_data.get('last_name')
        cc3_profile.save()

        return user_profile

    def clean_first_name(self):
        first_name_changed = False

        if self.instance.pk and \
                self.instance.profile.user.first_name.lower() != \
                self.cleaned_data['first_name'].lower():
            first_name_changed = True

        if not first_name_changed:
            raise forms.ValidationError(
                _(u'Please change the generated first name to your own'))

        if self.cleaned_data['first_name'].strip() == "":
            raise forms.ValidationError(
                _(u'Please enter your first name'))

        return self.cleaned_data['first_name']

    def clean_last_name(self):
        last_name_changed = False

        if self.instance.pk and \
                self.instance.profile.user.last_name.lower() != \
                self.cleaned_data['last_name'].lower():
            last_name_changed = True

        if not last_name_changed:
            raise forms.ValidationError(
                _(u'Please change the generated last name to your own'))

        if self.cleaned_data['last_name'].strip() == "":
            raise forms.ValidationError(
                _(u"Please enter your last name"))

        return self.cleaned_data['last_name']

    def clean_email(self):
        email_changed = False

        if self.instance.pk and \
                self.instance.profile.user.email.lower() != \
                self.cleaned_data['email'].lower():
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

        if not email_changed:
            raise forms.ValidationError(
                _(u'Please change the generated email address to one where we '
                  u'can reach you'))

        return self.cleaned_data['email']

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

    def clean_terms_and_conditions(self):
        data = self.cleaned_data['terms_and_conditions']

        if data:
            return data
        else:
            raise forms.ValidationError(
                _(u'You must agree to the terms and conditions to be able to '
                  u'use the website'))

    # #2014 Display email address and password-related errors on top of the
    # affected form fields
    def clean(self):
        cleaned_data = super(TermsAndConditionsForm, self).clean()

        # Handle the email fields
        email = cleaned_data.get('email', None)
        email_confirmation = cleaned_data.get('email_confirmation', None)
        if email and email_confirmation and (email != email_confirmation):
            self.add_error('email', forms.ValidationError(
                _(u'Please enter the same email for both email and email '
                  u'confirmation.')))
            self.add_error('email_confirmation', forms.ValidationError(''))

        # Handle the password fields
        password = cleaned_data.get('reg_password', None)
        password_confirmation = cleaned_data.get(
            'password_confirmation', None)
        if password and password_confirmation and \
                password != password_confirmation:
            self.add_error('reg_password', forms.ValidationError(
                _(u'Please enter the same password for both password and '
                  u'password confirmation.')))
            self.add_error('password_confirmation', forms.ValidationError(''))
        return self.cleaned_data


class StadlanderTermsAndConditionsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'terms_and_conditions',
            'wants_newsletter',
        ]

    def clean_terms_and_conditions(self):
        data = self.cleaned_data['terms_and_conditions']

        if data:
            return data
        else:
            raise forms.ValidationError(
                _(u'You must agree to the terms and conditions to be able to '
                  u'use the website'))


class DateRangeForm(forms.Form):
    export_type = forms.ChoiceField(choices=(
        ('credit', 'Credit'), ('debit', 'Debit')))
    date_from = forms.DateField(
        label=_('From date'), widget=widgets.AdminDateWidget())
    date_to = forms.DateField(
        label=_('To date'), widget=widgets.AdminDateWidget())

    def clean_date_from(self):
        """
        Ensures that the selected 'from' date is not in the future.
        """
        date_from = self.cleaned_data['date_from']

        if date_from > datetime.date.today():
            raise forms.ValidationError(
                _(u'Selected date must be in the past'))

        return date_from

    def clean_date_to(self):
        """
        Ensures that the selected 'to' date is not in the future.
        """
        date_to = self.cleaned_data['date_to']

        if date_to > datetime.date.today():
            raise forms.ValidationError(
                _(u'Selected date must be in the past or today, as much'))

        return date_to

    def clean(self):
        """
        Ensures that selected 'from' date is older than 'to' date.
        """
        cleaned_data = super(DateRangeForm, self).clean()

        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                _(u'Initial date must be in past of final date'))

        return cleaned_data


class CommunityUserProfileForm(forms.ModelForm):
    # ``CC3Profile`` fields.
    picture = RestrictiveFileField(
        required=False,
        valid_file_formats=['jpg', 'png', 'gif', 'jpeg'])
    business_name = forms.CharField(max_length=255, required=False)
    city = forms.CharField(
        max_length=255, required=True, validators=[city_validator])
    address = forms.CharField(max_length=255, required=True)
    postal_code = NLZipCodeField(required=True)
    country = forms.ChoiceField(choices=countries, required=False)
    phone_number = forms.CharField(max_length=255, required=False)
    company_website = forms.URLField(max_length=255, required=False)
    company_description = forms.CharField(
        widget=forms.Textarea, required=False)
    community = forms.ModelChoiceField(
        label=_(u'Communities'), required=False,
        queryset=CC3Community.objects.all(),
        widget=forms.Select(attrs={'disabled': 'disabled'}))
    categories = forms.ModelMultipleChoiceField(
        label=_(u'Categories'),
        queryset=Category.objects.active(),
        widget=CheckboxSelectMultipleCategoriesTree(
            attrs=dict(id='id_categories')),
        required=False)

    latitude = forms.DecimalField(max_digits=17, decimal_places=14,
                                  required=False)

    longitude = forms.DecimalField(max_digits=17, decimal_places=14,
                                   required=False)

    map_zoom = forms.IntegerField(required=False)

    # iCare4u ``UserProfile`` fields.
    tussenvoegsel = forms.CharField(max_length=10, required=False)
    extra_address = forms.CharField(max_length=255, required=False)
    num_street = forms.IntegerField(
        max_value=99999, required=True,
        error_messages={'invalid': _(u'Please enter a valid house number')})
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, required=True, widget=forms.RadioSelect(),
        label=_(u'Gender'))
    date_of_birth = forms.DateField(required=False)
    web_payments_enabled = forms.BooleanField(required=False)
    id_type = forms.ChoiceField(
        choices=ID_TYPES, label=_('Type of ID'), required=False)

    document_number = forms.CharField(
        label=_('Document Number'), required=False)

    expiration_date = forms.DateField(required=False)

    is_visible = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityUserProfileForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email_changed = False

        if self.instance.pk and \
                self.instance.profile.user.email.lower() != \
                self.cleaned_data['email'].lower():
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
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            if len(phone_number) != 10:
                raise forms.ValidationError(
                    _(u'A Dutch phone number always has exactly 10 digits.'))
            else:
                if not phone_number.isdigit():
                    raise forms.ValidationError(
                        _(u'A phone number must consist of numbers only.'))
        return phone_number

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

    def clean_date_of_birth(self):
        data = self.cleaned_data['date_of_birth']
        today = datetime.date.today()
        eighteen_years_ago = today + relativedelta(years=-18)

        if data and data > eighteen_years_ago:
            raise ValidationError(_("Please enter a valid date"))

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

    def save(self, commit=True):
        """
        Overrides base class ``save`` method to properly save the objects in
        the database. Objects to be saved are:
            * ``User``
            * ``UserProfile`` - related to ``User``.
        """
        profile_attrs = {
            # DISABLED after creation #2803
            # ... but see CommunityIndividualProfileForm.save() below
            # 'first_name': self.cleaned_data.get('first_name', ''),
            # 'last_name': self.cleaned_data.get('last_name', ''),
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
            # DISABLED after creation #2803
            # ... but see CommunityIndividualProfileForm.save() below
            # 'tussenvoegsel': self.cleaned_data.get('tussenvoegsel', ''),
            'picture': self.cleaned_data.get('picture', None),
            'extra_address': self.cleaned_data.get('extra_address', ''),
            'num_street': self.cleaned_data.get('num_street') or '',
            'country': self.cleaned_data.get('country', ''),
            # DISABLED after creation #2803
            'gender': self.cleaned_data.get('gender', ''),
            'date_of_birth': self.cleaned_data.get('date_of_birth', ''),
            'id_type': self.cleaned_data.get('id_type', ''),
            'document_number': self.cleaned_data.get('document_number', ''),
            'expiration_date': self.cleaned_data.get('expiration_date', None),
            'web_payments_enabled': self.cleaned_data.get(
                'web_payments_enabled', True),
            # 'is_visible': self.cleaned_data.get('is_visible', True),
            'latitude': self.cleaned_data.get('latitude', None),
            'longitude': self.cleaned_data.get('longitude', None),
            'map_zoom': self.cleaned_data.get('map_zoom', None),
        }

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
            user.save()

            # Create the `UserProfile` related to `User`.
            profile_attrs['user'] = user
            user_profile = UserProfile.objects.create(**profile_attrs)
        else:
            # Update `User` data.
            user = self.instance.profile.user

            user.email = self.cleaned_data.get('email')

            # DISABLED after creation #2803
            # user.first_name = self.cleaned_data.get('first_name')
            # user.last_name = self.cleaned_data.get('last_name')
            user.save()

            # Update `UserProfile` data.
            user_profile = self.instance.profile

            if not profile_attrs['community']:
                profile_attrs['community'] = user_profile.community
            if not profile_attrs['country']:
                profile_attrs['country'] = user_profile.country

            for key in profile_attrs.keys():
                setattr(user_profile, key, profile_attrs[key])

            user_profile.save()

        for category in self.cleaned_data.get('categories'):
            user_profile.categories.add(category)

        return user_profile


class CommunityBusinessProfileForm(CommunityUserProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False)
    signature_date = forms.DateField(required=False)
    registration_number = forms.CharField(
        max_length=14, help_text=_('VAT Number'), required=False)
    vat_number = forms.CharField(max_length=14, help_text=_('VAT Number'),
                                 required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityBusinessProfileForm, self).__init__(*args, **kwargs)

        self.fields['business_name'].required = True
        del self.fields['is_visible']

    def clean_vat_number(self):
        data = self.cleaned_data.get('vat_number', '')
        if data:
            vat_number_re = re.compile(VAT_NUMBER_REGEX)
            if not vat_number_re.match(data):
                error_msg = _("Please enter a valid VAT Number")
                raise forms.ValidationError(error_msg)

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
            'vat_number': self.cleaned_data.get('vat_number', '')
        }

        if not self.instance.pk:
            business_profile = BusinessProfile.objects.create(**business_attrs)
        else:
            business_profile = self.instance

            # not editable after creation
            business_attrs.pop('signature_date')

            for key in business_attrs.keys():
                setattr(business_profile, key, business_attrs[key])

            business_profile.save()

        return business_profile


class CommunityInstitutionProfileForm(CommunityUserProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False)
    signature_date = forms.DateField(required=False)
    registration_number = forms.CharField(
        max_length=14, help_text=_('VAT Number'), required=False)
    vat_number = forms.CharField(max_length=14, help_text=_('VAT Number'),
                                 required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityInstitutionProfileForm, self).__init__(*args, **kwargs)

        self.fields['business_name'].required = True
        self.fields['business_name'].label = _('Institution name')

    def clean_vat_number(self):
        data = self.cleaned_data.get('vat_number', '')
        if data:
            vat_number_re = re.compile(VAT_NUMBER_REGEX)
            if not vat_number_re.match(data):
                error_msg = _("Please enter a valid VAT Number")
                raise forms.ValidationError(error_msg)

        return data

    def save(self, commit=True):
        user_profile = super(
            CommunityInstitutionProfileForm, self).save(commit)

        institution_attrs = {
            'profile': user_profile,
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', ''),
            'mandate_id': generate_mandate_id(user_profile.user),
            'signature_date': self.cleaned_data.get('signature_date', ''),
            'vat_number': self.cleaned_data.get('vat_number', '')
        }

        if not self.instance.pk:
            institution_profile = InstitutionProfile.objects.create(
                **institution_attrs)
        else:
            institution_profile = self.instance

            # not editable after creation
            institution_attrs.pop('signature_date')

            for key in institution_attrs.keys():
                setattr(institution_profile, key, institution_attrs[key])

            institution_profile.save()

        return institution_profile


class CommunityCharityProfileForm(CommunityUserProfileForm):
    iban = IBANFormField(label=_('IBAN number'), required=False)
    bic_code = forms.CharField(
        label=_('BIC code'), validators=[swift_bic_validator], required=False)
    account_holder = forms.CharField(
        max_length=255, required=False, help_text=_('Account holder name'))
    mandate_id = forms.CharField(label=_('mandate ID'), required=False)
    signature_date = forms.DateField(required=False)
    registration_number = forms.CharField(
        max_length=14, help_text=_('VAT Number'), required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityCharityProfileForm, self).__init__(*args, **kwargs)

        self.fields['business_name'].required = True
        self.fields['business_name'].label = _('Charity name')

    def save(self, commit=True):
        user_profile = super(CommunityCharityProfileForm, self).save(commit)

        charity_attrs = {
            'profile': user_profile,
            'iban': self.cleaned_data.get('iban', ''),
            'bic_code': self.cleaned_data.get('bic_code', ''),
            'account_holder': self.cleaned_data.get('account_holder', ''),
            'mandate_id': generate_mandate_id(user_profile.user),
            'signature_date': self.cleaned_data.get('signature_date', '')
        }

        if not self.instance.pk:
            charity_profile = CharityProfile.objects.create(**charity_attrs)
        else:
            charity_profile = self.instance

            # not editable after creation
            charity_attrs.pop('signature_date')

            for key in charity_attrs.keys():
                setattr(charity_profile, key, charity_attrs[key])

            charity_profile.save()

        return charity_profile


class CommunityIndividualProfileForm(CommunityUserProfileForm):
    mobile_number = forms.CharField(max_length=15, required=False)
    nickname = forms.CharField(max_length=255, required=False)

    is_visible = forms.BooleanField(
        required=False,
        label=_('Zichtbaar voor anderen'),
        help_text=_('Maak mij zichtbaar op de marktplaats')
    )
    wants_newsletter = forms.BooleanField(
        required=False,
        label=_('Newsletter'),
        help_text=_('I would like to receive the newsletter')
    )

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name'
        )

    def __init__(self, *args, **kwargs):
        """
        Overrides base class ``__init__`` method to define the ``User`` related
        fields as 'required'.
        """
        super(CommunityIndividualProfileForm, self).__init__(*args, **kwargs)
        self.fields['date_of_birth'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_email(self):
        cleaned_email = super(
            CommunityIndividualProfileForm, self).clean_email()

        if is_default_email(cleaned_email.lower()):
            raise forms.ValidationError(
                _(u'Enter your email address'))
        return cleaned_email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if self.instance.pk and \
                self.instance.profile.user:
            if is_default_firstname(first_name, self.instance.profile.user):
                raise forms.ValidationError(
                    _(u'Enter your first name'))
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if self.instance.pk and \
                self.instance.profile.user:
            if is_default_lastname(last_name, self.instance.profile.user):
                raise forms.ValidationError(
                    _(u'Enter your last name'))
        return last_name

    def save(self, commit=True):
        user_profile = super(CommunityIndividualProfileForm, self).save(commit)

        # individuals _are_ allowed to edit their name fields (#3154)
        user_profile.tussenvoegsel = self.cleaned_data.get('tussenvoegsel',
                                                           '')
        user_profile.first_name = self.cleaned_data.get('first_name', '')
        user_profile.last_name = self.cleaned_data.get('last_name', '')
        user_profile.user.first_name = self.cleaned_data.get('first_name', '')
        user_profile.user.last_name = self.cleaned_data.get('last_name', '')

        # 3014 Comment out this line as it causes the is_visible to be set to
        # False every time the profile is saved independently of the current
        # value of the field. Morevover, the field is not even present on the
        # form, so it doesn't really make sense to retrieve its value

        # individuals have to explicitly set whether they're visible on the
        # marketplace or not
        # user_profile.is_visible = self.cleaned_data.get('is_visible', False)

        if 'wants_newsletter' in self.cleaned_data:
            user_profile.wants_newsletter = \
                self.cleaned_data.get('wants_newsletter')
        # individuals need business name and slug to be set for marketplace
        user_profile.business_name = user_profile.name
        # user_profile.slug = slugify(user_profile.name)
        user_profile.save()
        user_profile.user.save()

        individual_attrs = {
            'profile': user_profile,
            'nickname': self.cleaned_data.get('nickname', ''),
        }

        if not self.instance.pk:
            individual_profile = IndividualProfile.objects.create(
                **individual_attrs)
        else:
            individual_profile = self.instance

            for key in individual_attrs.keys():
                setattr(individual_profile, key, individual_attrs[key])

            individual_profile.save()

        return individual_profile
