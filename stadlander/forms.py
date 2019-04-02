import logging
import re

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm
from django.db import models
from django.forms import ValidationError
from django.forms.widgets import CheckboxSelectMultiple
from django.utils.translation import ugettext as _

from .models import StadlanderProfile, RewardCategory, AdRewardCategory
from .widgets import StadlanderRewardCategoryCheckboxSelectMultiple

from cc3.accounts.forms import CC3PasswordChangeForm, CC3ProfileChoiceField
from cc3.accounts.utils import check_amount
from cc3.cyclos.models import CC3Profile
from cc3.marketplace.forms import AdForm

from django.utils.translation import get_language
from cc3.mail.utils import send_mail_to
from cc3.mail.models import MAIL_TYPE_PASSWORD_RESET
from django.core.urlresolvers import reverse
from icare4u_front.profile.models import UserProfile

LOG = logging.getLogger(__name__)

attrs_dict = {'class': 'required'}


class PAPIForm(forms.Form):
    """
    Validate the PAPI key in link returned by Stadlander
    """
    papi = forms.CharField(max_length=255, required=True)

    def __init__(self, *args, **kwargs):
        super(PAPIForm, self).__init__(*args, **kwargs)
        self.user_cache = None

    def clean_papi(self):
        data = self.cleaned_data['papi']

        # validate papi key is alphanumeric?
        valid_hash = re.finditer(r'(?=(\b[A-Fa-f0-9]{64}\b))', data)
        valid_data = len([match.group(1) for match in valid_hash]) > 0
        if valid_data:
            return data
        else:
            raise forms.ValidationError(
                _('Sorry, your account details do not match those we have on '
                  'file'))

    def clean(self):
        papi_key = self.cleaned_data.get('papi')

        if papi_key:
            self.user_cache = authenticate(token=papi_key)
            LOG.info("PAPIForm authenticated {0}".format(self.user_cache))

        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class StadlanderLinkAccountsForm(forms.Form):
    """Dummy form used to accept/decline linking of account"""
    pass

# 3300 Override the PasswordResetForm.send_mail method to use the mail template
# managed via the cc3.mail.models.MailMessage class
def send_mail(self, subject_template_name, email_template_name,
              context, from_email, to_email, html_email_template_name=None):
    language = get_language()

    user = context['user']
    protocol = context['protocol']
    domain = context['domain']
    suffix = reverse(
            'auth_password_reset_confirm',
            kwargs={
                'uidb64': context['uid'],
                'token': context['token'],
            })

    url = "{}://{}{}".format(protocol, domain, suffix)

    first_name = None
    last_name = None
    middle_initials = None

    if user is not None:
        try:
            profile = UserProfile.objects.get(user=user)
            first_name = profile.first_name
            last_name = profile.last_name
            middle_initials = profile.tussenvoegsel

            if middle_initials == '':
                middle_initials = None

        except UserProfile.DoesNotExist:
            pass

        if first_name is None or first_name == '':
            first_name = user.first_name
        if last_name is None or last_name == '':
            last_name = user.last_name

    email_context = {
        'link': url,
        'first_name': first_name,
        'last_name': last_name,
        'middle_initials': middle_initials,
    }

    if user is not None and hasattr(user, 'email') and user.email is not None:
        sent = send_mail_to(
            recipients=(),
            mail_type=MAIL_TYPE_PASSWORD_RESET,
            language=language,
            context=email_context,
            recipient_addresses=(user.email,))
    else:
        LOG.error("Cannot send activation email. User has no email address.")

PasswordResetForm.send_mail = send_mail

class ICare4uPasswordResetForm(PasswordResetForm):
    pass

#    def clean_email(self):
#        data = self.cleaned_data.get('email')
#
#        try:
#            StadlanderProfile.objects.get(profile__user__email=data)
#            raise forms.ValidationError(
#                _("Stadlander users may not reset their password here. "
#                  "Please do so on the Stadlander site"))
#        except StadlanderProfile.DoesNotExist:
#            pass
#
#        return data


class ICare4uPasswordChangeForm(CC3PasswordChangeForm):
    pass
#    def clean(self):
#        try:
#            StadlanderProfile.objects.get(profile__user=self.user)
#            raise forms.ValidationError(
#                _("Stadlander users may not change their password here. "
#                  "Please do so on the Stadlander site"))
#        except StadlanderProfile.DoesNotExist:
#            pass
#
#        return super(ICare4uPasswordChangeForm, self).clean()


class ICare4uAuthenticationForm(AuthenticationForm):
    pass
    # def clean(self):
    #     username = self.cleaned_data.get('username')
    #     try:
    #         StadlanderProfile.objects.get(
    #             models.Q(profile__user__username=username) |
    #             models.Q(profile__user__email=username)
    #         )
    #         raise forms.ValidationError(
    #             _("Stadlander users cannot login here. "
    #               "Please do so on the Stadlander site."))
    #     except StadlanderProfile.DoesNotExist:
    #         pass
    #
    #     return super(ICare4uAuthenticationForm, self).clean()


class StadlanderPayDirectForm(forms.Form):
    """ Stadlander tenant payment form
    """
    reward_category = forms.ModelChoiceField(
        queryset=RewardCategory.objects.filter(active=True),
        required=False
    )
    reward_category_quantity = forms.IntegerField(required=False)
    other_activity = forms.CharField(max_length=40, required=False)
    other_activity_quantity = forms.IntegerField(required=False)
    bonus = forms.IntegerField(required=False)
    profile = CC3ProfileChoiceField(
        queryset=CC3Profile.viewable.all().order_by('first_name', 'last_name'),
        widget=forms.HiddenInput(),
        error_messages={
            'required': '',
        })
    contact_name = forms.CharField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=255)),
        label=_(u'Contact Name <br />(business)'),
        help_text=_(u'Person to contact'),
        error_messages={
            'required': _(u'Please enter the Contact Name at the company you '
                          u'wish to pay')
        })
    # NB need dynamic way of specifying max amount (ie current balance / credit
    # limit of user).
    amount = forms.IntegerField(
        label=_(u'Amount'),
        help_text=_(u"Amount to pay"),
        error_messages={'required': _(u'Please enter an amount to pay')},
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')  # Cache the user object you pass in
        # And carry on to init the form.
        super(StadlanderPayDirectForm, self).__init__(*args, **kwargs)

    def clean_amount(self):
        """
        Validate that an amount > settings CC3_CURRENCY_MINIMUM has been entered
        :return:
        """
        amount = self.cleaned_data.get('amount', None)
        return check_amount(amount, self.user.username)

    def clean(self):
        cleaned_data = super(StadlanderPayDirectForm, self).clean()

        amount = cleaned_data.get('amount', None)
        reward_category = cleaned_data.get('reward_category', None)
        reward_category_quantity = cleaned_data.get(
            'reward_category_quantity', None)
        other_activity = cleaned_data.get('other_activity', None)
        other_activity_quantity = cleaned_data.get(
            'other_activity_quantity', None)
        bonus = cleaned_data.get('bonus', None)

        if reward_category is None and other_activity is None:
            msg = _(
                u"Please select a reward category and/or enter other activity.")
            self._errors["reward_category"] = self.error_class([msg])
            self._errors["other_activity"] = self.error_class([msg])

            # These fields are no longer valid. Remove them from the
            # cleaned data.
            del cleaned_data["reward_category"]
            del cleaned_data["other_activity"]

        if reward_category is not None and reward_category_quantity is None:
            msg = _(u"Please enter a quantity next to the reward category")
            self._errors["reward_category_quantity"] = self.error_class([msg])
            del cleaned_data["reward_category_quantity"]

        if reward_category is None and reward_category_quantity is not None:
            msg = _(u"Please select a reward when entering a quantity")
            self._errors["reward_category"] = self.error_class([msg])
            del cleaned_data["reward_category"]

        if other_activity.strip() != u'' and other_activity_quantity is None:
            msg = _(u"Please enter a quantity next to the other activity")
            self._errors["other_activity_quantity"] = self.error_class([msg])
            del cleaned_data["other_activity_quantity"]

        if other_activity.strip() == u'' and \
                other_activity_quantity is not None:
            msg = _(u"Please enter an other activity when entering a quantity")
            self._errors["other_activity"] = self.error_class([msg])
            del cleaned_data["other_activity"]

        stadlander_minutes_to_punten = getattr(
            settings, "STADLANDER_MINUTES_TO_PUNTEN", 10)

        punten = 0
        if reward_category_quantity is not None:
            punten += reward_category_quantity * stadlander_minutes_to_punten

        if other_activity_quantity is not None:
            punten += other_activity_quantity * stadlander_minutes_to_punten

        if bonus is not None:
            punten += bonus
            # bonus now just an absolute quantity. not related to minutes
            # see #2493

        if amount != punten:
            raise ValidationError(_(
                "The amount entered on the form has been tampered with, "
                "please use the calculated values"))

        return cleaned_data


class StadlanderAdForm(AdForm):
    reward_category = forms.ModelMultipleChoiceField(
        queryset=RewardCategory.objects.filter(active=True),
        widget=StadlanderRewardCategoryCheckboxSelectMultiple,
        label=_(u"Reward Categories"),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(StadlanderAdForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # if editing - do not use custom stadlander reward widget
            self.fields['reward_category'] = forms.ModelMultipleChoiceField(
                queryset=RewardCategory.objects.filter(active=True),
                widget=CheckboxSelectMultiple,
                label=_(u"Reward Categories"),
                required=False
            )
            self.fields['reward_category'].initial = [
                c.reward_category for c in AdRewardCategory.objects.filter(
                    ad=self.instance)
            ]
