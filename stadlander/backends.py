import logging
import random
from string import ascii_letters, digits

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import MultipleObjectsReturned
from django import forms
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.utils import timezone

from cc3.cyclos import backends
from cc3.cyclos.models import User, CyclosGroupSet

from .models import StadlanderProfile, CommunityWoonplaat, PotentialLinkFound
from .utils import check_papi_key
from ..profile.models import UserProfile, IndividualProfile, GENDER_CHOICES

LOG = logging.getLogger(__name__)


class StadlanderSSOBackend(ModelBackend):

    def authenticate(self, token=None):
        """
        Authenticate a user with Stadlander SSO PAPI-Key
         :param token: PAPI-Key (
         :return: User instance or None
         """
        LOG.debug("Stadlander authentication backend token {0}".format(token))
        if token:
            items = check_papi_key(token)
            LOG.info("Stadlander authentication backend items {0}".format(items))
            if items:
                return self.get_user_from_sso_items(items)
            else:
                raise forms.ValidationError(_(u"Your Stadlander session may have timed out"))

    def get_user_from_sso_items(self, items):
        # validation checks
        # must be single profile (identified by rel_number) matching user (by email)
        # find user, user_profile, individual_profile and stadlander_profile for rel_number and email

        # existing stadlander profile?
        try:
            stadlander_profile = StadlanderProfile.objects.get(
                rel_number=items['rel_number'],
            )
        except StadlanderProfile.DoesNotExist:
            stadlander_profile = None
        except MultipleObjectsReturned:
            # something wrong - more than one profile with the rel_number - shouldn't be possible from scratch
            raise forms.ValidationError(
                _(u"Sorry, your account details do not match those we have on file"))

        # stadlander profile exists
        if stadlander_profile:
            # rel_number same email as we have already?
            if stadlander_profile.profile.user.email.lower() != items['mail'].lower():
                # Check if this emailadres is already used, as we can't update the email to an existing address
                if User.objects.filter(email=items['mail']):
                    LOG.info(u"Stadlander authentication failed because email "
                        u"address on Django side ({0}) doesn't match SL side "
                        u"item {1}".format(
                            stadlander_profile.profile.user.email,
                            items['mail']))
                    raise forms.ValidationError(
                    _(u"You are not able to log into the Samen-Doen "
                      "site because your e-mailadres isn't unique"))

                # update users email address
                user = stadlander_profile.profile.user
                user.email = items['mail']
                user.save()

#                raise forms.ValidationError(
#                    _(u"Sorry, your account details do not match those we have on file"))
        else:
            # Check if this email adress is already used,
            # if exactly one matching User found, and that User does not already
            # have a SL profile, offer to link accounts
            matches = User.objects.filter(email=items['mail'])
            if matches:
                LOG.info(u"Stadlander authentication backend found "
                         u"{0} matches for email {1}".format(matches.count(), items['mail']))
                if matches.count() == 1:
                    user = matches.all()[0]
                    if not StadlanderProfile.objects.filter(profile__user=user):
                        raise PotentialLinkFound
                # Stadlander doesn't ensure email addresses are unique (#1767)
                # if nore than one match found, or if the matching User has already
                # been linked to another SL, all bets are off
                raise forms.ValidationError(
                    _(u"You are not able to log into the Samen-Doen "
                      "site because your e-mailadres isn't unique"))

        # existing user with email supplied for stadlander profile?
        try:
            user = User.objects.get(email=items['mail'])
            # is it the same user as that of the profile?
            if stadlander_profile and stadlander_profile.profile.user != user:
                raise forms.ValidationError(
                    _(u"Sorry, your account details do not match those we have on file"))

            # update user from SSO info - NB duplicates CC3Profile first_name and last_name fields
            user.first_name = items['initials']
            user.last_name = items['last_name']
            user.save()

        except User.DoesNotExist:
            # create the user if none exists with the email address supplied for the profile
            user, created = self.get_or_create_user_from_email(items['mail'])

        # user cannot be None now, stadlander_profile can be -
        # so prepare data, and create get/create user_profile with user

        # prepare incoming data for new/updating profiles
        if items['gender'] == 'Man':
            gender = GENDER_CHOICES[0][0]
        else:
            gender = GENDER_CHOICES[1][0]

        # massage Stadlander date format into ISO8601
        if items['date_of_birth']:
            date_of_birth = timezone.datetime.strptime(items['date_of_birth'], "%Y-%m-%d")
        else:
            date_of_birth = None

        # get the community from the 'residence' field
        community_woonplaat = CommunityWoonplaat.objects.get(woonplaat__iexact=items['residence'])

        # check for StadlanderProfile with rel_number, if does not exist, then create, and set t&c to false
        cc3_community = community_woonplaat.community
        groupset = CyclosGroupSet.objects.get(pk=settings.STADLANDER_GROUPSET_ID)

        if not user.is_active:
            # activate Stadlander user #1775
            user.is_active = True
            user.save()

        user_profile, user_profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'terms_and_conditions': False,
                'community': cc3_community,
                'country': cc3_community.country,
                'groupset': groupset,
                'first_name': items['initials'],
                'last_name': items['last_name'],
                'address': items['street'],
                'postal_code': items['zip_code'],
                'city': items['residence'],
                'num_street': items['number'],
                'extra_address': items['addition'],
                'tussenvoegsel': items['insert'],
                'gender': gender,
                'date_of_birth': date_of_birth,
                # individuals not visible by default on marketplace
                'is_visible': False
            }
        )

        # make sure community is up to date
        if not user_profile_created:
            # update the community if not a new profile
            user_profile.community = cc3_community
            user_profile.first_name = items['initials']
            user_profile.last_name = items['last_name']

            user_profile.address = items['street']
            user_profile.postal_code = items['zip_code']
            user_profile.city = items['residence']
            user_profile.extra_address = items['addition']
            user_profile.num_street = items['number']
            user_profile.tussenvoegsel = items['insert']
            user_profile.gender = gender
            user_profile.date_of_birth = date_of_birth
            user_profile.business_name = user_profile.name
            user_profile.slug = slugify(user_profile.business_name)
            user_profile.save()

            LOG.info("Stadlander authentication backend updated ({0}) user".format(user.id))
        else:
            user_profile.business_name = user_profile.name
            user_profile.slug = slugify(user_profile.business_name)
            user_profile.save()
            LOG.info("Stadlander authentication backend created ({0}) user".format(user.id))

        individual_profile, individual_profile_created = IndividualProfile.objects.get_or_create(
            profile=user_profile)#, defaults={'date_of_birth': date_of_birth}
#        )

        # update profile details if not created
#        if not individual_profile_created:
#            individual_profile.date_of_birth = date_of_birth

        # create cyclos account with additional save to profile
        individual_profile.save()

        if not stadlander_profile:
            individual_profile.set_good_cause()

            user_profile.create_new_stadlander_profile(
                rel_number=items['rel_number'])

        return user

    def get_or_create_user_from_email(self, email):
        """

        :rtype : User or None
        """
        from cc3.accounts.utils import get_non_obvious_number

        try:
            return User.objects.get(email=email), False
        except User.DoesNotExist:
            # max length of username on cyclos side is 30 chars
            # user won't ever know their generated username
            username = slugify("%s" % email)[:30]
            username = "".join([ch for ch in username if ch in (ascii_letters + digits)])

            # generate hideous password
            password = ''.join(random.choice(ascii_letters + digits) for x in range(16))

            # check username doesn't already exist (on django side)
            test_username = username.ljust(4, '0')
            while True:
                list_of_members_with_username = User.objects.filter(username=test_username)
                if len(list_of_members_with_username) == 0:
                    break
                test_username = "%s%s" % (username, get_non_obvious_number(number_digits=4))

            username = test_username

            return User.objects.create_user(username, email, password), True

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
