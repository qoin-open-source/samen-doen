import logging

# from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sites.shortcuts import get_current_site

from registration import signals
from registration.models import RegistrationProfile
from registration.backends.default.views import RegistrationView
from registration.backends.simple.views import RegistrationView as \
    SimpleRegistrationView

from cc3.cyclos.models import User, CommunityRegistrationCode

from icare4u_front.profile.models import (
    UserProfile, IndividualProfile)
from icare4u_front.profile.utils import generate_username, squeeze_email
from .forms import ICare4uRegistrationForm

from cc3.mail.utils import send_mail_to
from cc3.mail.models import MAIL_TYPE_NEW_REGISTRATION_USER
from django.utils.translation import get_language
from registration.models import RegistrationProfile
from django.conf import settings

from icare4u_front.profile.utils import get_tandc_page_url

LOG = logging.getLogger(__name__)


# #3300 Get the email template from the MailMessage model
# Overriding the RegistrationProfile.send_activation_email method
# To get the email template from the MailMessage model
def send_activation_email(self, site, request=None):
    context = {
        'activation_key': self.activation_key,
        'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
        'site': site,
    }

    language = get_language()

    if self.user is not None and hasattr(self.user, 'email') and self.user.email is not None:
        sent = send_mail_to(
            recipients=(),
            mail_type=MAIL_TYPE_NEW_REGISTRATION_USER,
            language=language,
            context=context,
            recipient_addresses=(self.user.email,))
    else:
        LOG.error("Cannot send activation email. User has no email address.")

RegistrationProfile.send_activation_email = send_activation_email


class ICare4uRegistrationView(RegistrationView):
    form_class = ICare4uRegistrationForm

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(
            form=form,
            tandc_url=get_tandc_page_url()
        )

        return self.render_to_response(context)

    def register(self, form):
        """
        Create an inactive user - which is then activated via a click

        NB - this user will need to be removed before any inactive user culling

        Create the new ``User`` and ``RegistrationProfile``, and
        returns the ``User`` (by calling
        ``RegistrationProfile.objects.create_inactive_user()``).

        based on original RegistrationView register method

        """
        cc3_community = form.cleaned_data['community']
        registration_code = None

        try:
            registration_code = CommunityRegistrationCode.objects.get(
                community=cc3_community)
        except CommunityRegistrationCode.DoesNotExist:
            LOG.critical(u"registration_code does not exist for "
                         u"community '{0}'".format(cc3_community))
            # TO DO make community code part of registration form, so that a
            # validation error can be raised
            # raise ValidationError(_("Cannot find the Community Code"))

        groupset = registration_code.groupset

        # get unused username (never shown to users)
        email = form.cleaned_data['email']

        username = generate_username(squeeze_email(email))

        first_name = form.cleaned_data['first_name']
        tussenvoegsel = form.cleaned_data['tussenvoegsel']
        last_name = form.cleaned_data['last_name']
        mobile_number = form.cleaned_data['mobile_number']
        phone_number = form.cleaned_data['phone_number']
        email = form.cleaned_data['email']
        password = form.cleaned_data['password_confirmation']

        site = get_current_site(self.request)
        new_auth_user = RegistrationProfile.objects.create_inactive_user(
            site, username=username, email=email, password=password)
        new_user = User.objects.get(pk=new_auth_user.id)

        # Create the `UserProfile`.
        icare4u_user_profile = UserProfile.objects.create(
            user=new_user,
            first_name=first_name,
            tussenvoegsel=tussenvoegsel,
            last_name=last_name,
            community=cc3_community,
            country=cc3_community.country,
            groupset=groupset,
            terms_and_conditions=form.cleaned_data['tandc_confirmation'],
            city=form.cleaned_data['city'],
            address=form.cleaned_data['address'],
            postal_code=form.cleaned_data['postal_code'],
            extra_address=form.cleaned_data['extra_address'],
            num_street=form.cleaned_data['num_street'],
            gender=form.cleaned_data['gender'],
            date_of_birth=form.cleaned_data.get('date_of_birth'),
            # default Samen Doen individuals are not visible on the marketplace
            is_visible=False,
            wants_newsletter=form.cleaned_data['wants_newsletter'],
            phone_number=phone_number,
            mobile_number=mobile_number,
        )
        icare4u_user_profile.business_name = icare4u_user_profile.name

        # Create the `IndividualProfile`.
        IndividualProfile.objects.create(
            profile=icare4u_user_profile,
        )

        signals.user_registered.send(
            sender=self.__class__, user=new_user, request=self.request)

        return new_user


class ICare4uCardsRegistrationView(SimpleRegistrationView):
    """
    Registration view user by the NFC cards system to register new cards.
    """
    def register(self, request, **cleaned_data):
        """
        Automatically create an active user with no activation link required.

        kwargs:
            ``community``: the ``CC3Community`` object which will be assigned
            to the new user CC3 profile.

            ``card_number``: the card number (the one printed in the card, not
            the UID number) which will be used to generate the username.

            ``password_confirmation``: the password for the new user.
        """
        cc3_community = cleaned_data['community']
        registration_code = None

        try:
            registration_code = CommunityRegistrationCode.objects.get(
                community=cc3_community)
        except CommunityRegistrationCode.DoesNotExist:
            LOG.critical(u"registration_code does not exist for "
                         u"community '{0}'".format(cc3_community))

        groupset = registration_code.groupset

        card_number = cleaned_data['card_number']
        username = '{0}{1}'.format(card_number, cc3_community.code)
        email = cleaned_data['email']
        password = cleaned_data['password_confirmation']

        # Create the user.
        User.objects.create_user(
            username=username, email=email, password=password,
            first_name=cc3_community.code, last_name=username)

        # Authenticate the user.
        new_user = authenticate(username=username, password=password)

        # Create Cyclos profile for the user.
        profile = UserProfile.objects.create(
            user=new_user,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            business_name=u'',
            community=cc3_community,
            country=cc3_community.country,
            groupset=groupset,
            # Users need to agree to terms and conditions if using the online
            # service.
            terms_and_conditions=False,
            # default Samen Doen individuals are not visible on the marketplace
            is_visible=False,
        )

        # Save the new individual profile to the Cyclos backend.
        individual_profile = IndividualProfile.objects.create(profile=profile)
        individual_profile.save()
        individual_profile.set_good_cause()

        # Send signal for newly created user.
        signals.user_registered.send(
            sender=self.__class__, user=new_user, request=request)

        return new_user, profile
