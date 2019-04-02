import logging

from django.forms import ValidationError
from django.test import TestCase
from django.utils.translation import activate
from django.conf import settings
from django.utils.translation import ugettext as _

from icare4u_front.profile.tests.test_factories import UserProfileFactory

from ..models import StadlanderProfile, CommunityWoonplaat, PotentialLinkFound
from ..backends import StadlanderSSOBackend

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.models import CyclosGroupSet, CyclosGroup
from cc3.cyclos.backends import set_backend

LOG = logging.getLogger(__name__)


class SSOBackendTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.sso_backend = StadlanderSSOBackend()
        activate('en')

        self.user_profile = UserProfileFactory()
        self.st_profile = StadlanderProfile.objects.create(
            rel_number=123, profile=self.user_profile)

        self.comm_woon = CommunityWoonplaat.objects.create(
            community=self.user_profile.community, woonplaat='Amsterdam')
        self.init_group = CyclosGroup.objects.create(
            id=1, name='init_group', initial=True)
        # don't really know why this is necessary, but ...
        try:
            self.groupset = CyclosGroupSet.objects.get(
                pk=settings.STADLANDER_GROUPSET_ID)
        except:
            self.groupset = CyclosGroupSet.objects.create(
                pk=settings.STADLANDER_GROUPSET_ID, name='Groupset',
                slug='groupset')
        self.groupset.groups.add(self.init_group)
        self.user_profile.community.groupsets.add(self.groupset)

    def tearDown(self):
        activate('nl')

    def test_get_user_from_sso_items_email_update(self):
        new_email = 'test-new-email@example.com'
        items = {'rel_number': 123, 'mail': new_email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        user = self.sso_backend.get_user_from_sso_items(items)
        self.assertEqual(user.email, new_email)

    def test_get_user_from_sso_items(self):
        items = {'rel_number': 123, 'mail': self.user_profile.user.email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        user = self.sso_backend.get_user_from_sso_items(items)
        self.assertEqual(user.email, self.user_profile.user.email)

    def test_get_user_from_sso_items_no_stadlanderprofile(self):
        """
        Test getting a user with no existing Stadlander profile, and a
        duplicate email address validation error.
        """
        items = {'rel_number': 456, 'mail': 'foo@bar.com',
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        user = self.sso_backend.get_user_from_sso_items(items)
        self.assertEqual(user.email, 'foo@bar.com')

        # Test second user with same email

        items = {'rel_number': 457, 'mail': 'foo@bar.com',
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        self.assertRaisesMessage(
            ValidationError,
            _("You are not able to log into the Samen-Doen site because your "
              "e-mailadres isn't unique"),
            self.sso_backend.get_user_from_sso_items, items)

    def test_get_user_from_sso_items_blank_dob(self):
        """
        Test a user where the date of birth is not supplied with the SSO login.
        """
        items = {'rel_number': 123, 'mail': self.user_profile.user.email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': ''}
        user = self.sso_backend.get_user_from_sso_items(items)
        self.assertEqual(user.email, self.user_profile.user.email)

    def test_get_user_from_sso_items_matching_email(self):
        """
        Test detects a User with matching email address if there's no existing
        Stadlander profile
        """
        unmatched_user_profile = UserProfileFactory()
        matching_email = unmatched_user_profile.user.email

        items = {'rel_number': 458, 'mail': matching_email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        self.assertRaises(
            PotentialLinkFound,
            self.sso_backend.get_user_from_sso_items, items)

    def test_get_user_from_sso_items_matching_email_already_taken(self):
        """
        Test rejects User with matching email address but existing
        different Stadlander profile
        """
        unmatched_user_profile = UserProfileFactory()

        #other_sl_profile = StadlanderProfile.objects.create(
        #    rel_number=459, profile=unmatched_user_profile)
        #matching_email = unmatched_user_profile.user.email

        items = {'rel_number': 459, 'mail': self.user_profile.user.email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        #user = self.sso_backend.get_user_from_sso_items(items)
        #self.assertEqual(user.username, '')
        self.assertRaisesMessage(
            ValidationError,
            _("You are not able to log into the Samen-Doen site because your "
              "e-mailadres isn't unique"),
            self.sso_backend.get_user_from_sso_items, items)
