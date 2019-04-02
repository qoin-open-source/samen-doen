import json
from datetime import date

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from mock import patch
from rest_framework.status import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_405_METHOD_NOT_ALLOWED)

from cc3.cards.tests.test_factories import CardNumberFactory, OperatorFactory, \
    TerminalFactory, CardFactory
from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.models import User
from cc3.cyclos.tests.test_factories import (
    CommunityRegistrationCodeFactory, CyclosGroupFactory,
    CyclosGroupSetFactory, CC3CommunityFactory, UserFactory,
    AuthUserProfileFactory)

from icare4u_front.profile.models import IndividualProfile, UserProfile
from rest_framework.authtoken.models import Token


class ICare4uRegistrationViewTestCase(TestCase):
    """
    Test case for the web registration backend.
    """

    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)
        self.cyclos_group = CyclosGroupFactory.create(initial=True)
        self.cyclos_groupset = CyclosGroupSetFactory.create(
            groups=[self.cyclos_group])
        self.community = CC3CommunityFactory.create(groupsets=[self.cyclos_groupset])
        self.community_registration = CommunityRegistrationCodeFactory.create(
            community=self.community, groupset=self.cyclos_groupset)

        # self.factory = RequestFactory()

    @patch('cc3.cyclos.backends.search')
    def test_successful_registration_user_created(self, mock):
        """
        Tests the creation of a new user according with the web registration
        backend.
        """
        # Mock the function `cyclos.backends.search` used in
        # `profile.utils.generate_username` to accept our testing profile.
        mock.return_value = []

        response = self.client.post(
            reverse('registration_register'),
            {
                'community': self.community.pk,
                'email': 'john_doe@maykinmedia.nl',
                'email_confirmation': 'john_doe@maykinmedia.nl',
                'first_name': 'John',
                'tussenvoegsel': 'van',
                'last_name': 'Doe',
                'reg_password': 'testing400',
                'password_confirmation': 'testing400',
                'tandc_confirmation': True,
                'phone_number': '0123456789',
                'mobile_number': '0612312345',
                'city': 'Amsterdam',
                'address': 'Herengracht',
                'postal_code': '1017BN',
                'extra_address': '1',
                'num_street': '416',
                'gender': 'M',
                'date_of_birth': date(1976, 11, 18),
                'wants_newsletter': True
            })

        users = User.objects.all()
        user = users.latest('pk')

        self.assertEqual(user.email, 'john_doe@maykinmedia.nl')

        # Check the `IndividualProfile` stored data.
        individual_profiles = IndividualProfile.objects.all()
        self.assertEqual(len(individual_profiles), 1)

        individual_profile = individual_profiles.latest('pk')
        self.assertEqual(individual_profile.profile.date_of_birth,
                         date(1976, 11, 18))
        self.assertEqual(individual_profile.profile.first_name, 'John')
        self.assertEqual(individual_profile.profile.last_name, 'Doe')
        self.assertEqual(individual_profile.profile.tussenvoegsel, 'van')
        self.assertEqual(individual_profile.profile.extra_address, '1')
        self.assertEqual(individual_profile.profile.num_street, '416')
        self.assertEqual(individual_profile.profile.gender, 'M')
        self.assertEqual(
            individual_profile.profile.community,
            self.community)
        self.assertEqual(
            individual_profile.profile.groupset,
            self.cyclos_groupset)
        self.assertEqual(
            individual_profile.profile.user.email, 'john_doe@maykinmedia.nl')
        self.assertEqual(individual_profile.profile.terms_and_conditions, True)
        self.assertEqual(individual_profile.profile.phone_number, '0123456789')
        self.assertEqual(individual_profile.profile.mobile_number, '0612312345')
        self.assertEqual(individual_profile.profile.city, 'Amsterdam')
        self.assertEqual(individual_profile.profile.address, 'Herengracht')
        #  django local puts space in?
        self.assertEqual(individual_profile.profile.postal_code, '1017 BN')
        self.assertEqual(individual_profile.profile.web_payments_enabled, True)
        self.assertEqual(individual_profile.profile.wants_newsletter, True)


class ICare4uCardsRegistrationViewTestCase(TestCase):
    """
    Test case for the cards registration backend.
    """
#    urls = getattr(settings, 'TEST_URLS', 'cc3.core.utils.test_urls')

    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        admin_user_1 = UserFactory.create(
            is_staff=True, is_active=True, is_superuser=True)
        cyclos_group_1 = CyclosGroupFactory.create(
            initial=True, invoice_user=admin_user_1)
        cyclos_groupset_1 = CyclosGroupSetFactory.create(
            groups=[cyclos_group_1])
        community_1 = CC3CommunityFactory.create(groupsets=[cyclos_groupset_1])
        self.community_registration = CommunityRegistrationCodeFactory.create(
            community=community_1, groupset=cyclos_groupset_1)

        self.profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1)

        self.terminal_1 = TerminalFactory.create(business=self.profile.user)
        self.token_1 = Token.objects.create(user=self.profile.user)
        self.operator_1 = OperatorFactory(business=self.profile.user)
        self.client = self.client_class(HTTP_AUTHORIZATION='Token {0}'.format(
            self.token_1.key))

        self.card_number_1 = CardNumberFactory.create(number='55555')
        self.card_number_2 = CardNumberFactory.create(number='55556')
        self.card_number_3 = CardNumberFactory.create(number='55557')

    def test_successful_registration_user_created(self):
        """
        Tests the creation of a new user according with the cards registration
        backend.
        """

        response = self.client.post(
            reverse('api_cards_card_new_account_detail',
                    kwargs={'card_number': self.card_number_1.uid_number}))

        users = User.objects.all()
        user = users.latest('pk')

        self.assertEqual(
            user.username,
            self.card_number_1.number +
            self.community_registration.community.code)
        self.assertEqual(
            user.first_name, self.community_registration.community.code)
        self.assertEqual(user.last_name, user.username)

    def test_successful_registration_profile_created(self):
        """
        Tests the creation of a new Cyclos profile according with the cards
        registration backend.
        """
        response = self.client.post(
            reverse('api_cards_card_new_account_detail',
                    kwargs={'card_number': self.card_number_2.uid_number}))

        users = User.objects.all()
        user = users.latest('pk')
        individual_profiles = IndividualProfile.objects.all()
        individual_profile = individual_profiles.latest('pk')

        self.assertEqual(individual_profile.profile.first_name, user.first_name)
        self.assertEqual(individual_profile.profile.last_name, user.last_name)
        self.assertEqual(
            individual_profile.profile.community,
            self.community_registration.community)
        self.assertEqual(
            individual_profile.profile.country,
            self.community_registration.community.country)
        self.assertEqual(
            individual_profile.profile.groupset,
            self.community_registration.groupset)

    def test_successful_registration_individual_profile_created(self):
        """
        Tests the creation of an ``IndividualProfile`` according with the cards
        registration backend.
        """
        response = self.client.post(
            reverse('api_cards_card_new_account_detail',
                    kwargs={'card_number': self.card_number_3.uid_number}))

        profiles = UserProfile.objects.all()
        profile = profiles.latest('pk')

        individual_profiles = IndividualProfile.objects.all()
        self.assertGreater(len(individual_profiles), 0)

        individual_profile = IndividualProfile.objects.latest('pk')
        self.assertEqual(individual_profile.profile, profile)
