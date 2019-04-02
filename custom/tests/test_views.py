import json
import logging

from datetime import datetime
from decimal import Decimal

from mock import patch
from unittest.case import skip

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from cc3.cyclos.common import Transaction

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.tests.test_factories import (
    UserFactory, CC3ProfileFactory, CyclosGroupFactory, CyclosGroupSetFactory,
    CC3CommunityFactory, AuthUserProfileFactory)
from cc3.cyclos.backends import set_backend
from cc3.cyclos.models import CyclosGroupSet, CyclosGroup, CC3Profile
from cc3.rewards.tests.test_factories import UserCauseFactory

from ...profile.tests.test_factories import \
    IndividualProfileFactory, UserProfileFactory

LOG = logging.getLogger(__name__)


class CustomAccountTests(TestCase):

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

        self.profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1,
            terms_and_conditions=True,
            cyclos_group=cyclos_group_1)
        self.profile.first_login = False
        self.profile.save()
        self.user_cause = UserCauseFactory.create(consumer=self.profile.user)
        self.individual_profile = \
            IndividualProfileFactory.create(profile=self.profile)

    def test_update_profile_view(self):
        self.client.login(
            username=self.profile.user.username, password='testing')

        response = self.client.get(
            reverse('accounts-update-profile'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/update_my_profile.html')

    def test_account_home(self):

        self.client.login(
            username=self.profile.user.username, password='testing')
        LOG.critical(settings.LANGUAGE_CODE)
        response = self.client.get(
            reverse('accounts_home'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/accounts_home.html')

    def test_update_first_login_state(self):
        """
        Tests that before logging in, cc3 profile first_login is None, and
        after first login it is True. Lastly, after second login, it is False
        """
        test_profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=self.profile.community,
            terms_and_conditions=True,
            cyclos_group=self.profile.cyclos_group, first_login=None)

        self.assertEqual(test_profile.first_login, None)
        self.client.login(
            username=test_profile.user.username, password='testing')

        test_after_login_profile = CC3Profile.objects.get(pk=test_profile.pk)

        self.assertEqual(test_after_login_profile.first_login, True)
        self.client.logout()

        self.client.login(
            username=test_profile.user.username, password='testing')

        test_after_second_login_profile = CC3Profile.objects.get(
            pk=test_profile.pk)
        self.assertEqual(test_after_second_login_profile.first_login, False)


class CustomCreditTests(TestCase):
    """ Test if the credit view works as expected """

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

        self.profile = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1,
            terms_and_conditions=True, cyclos_group=cyclos_group_1)
        self.profile.first_login = False
        self.profile.save()

        self.individual_profile_1 = \
            IndividualProfileFactory.create(profile=self.profile)
        self.user_cause = UserCauseFactory.create(consumer=self.profile.user)

        self.profile_2 = AuthUserProfileFactory.create(
            web_payments_enabled=True, community=community_1,
            terms_and_conditions=True, cyclos_group=cyclos_group_1)
        self.individual_profile_2 = \
            IndividualProfileFactory.create(profile=self.profile_2)
        self.user_cause_2 = UserCauseFactory.create(
            consumer=self.profile_2.user)

    @patch('cc3.cyclos.backends.user_payment')
    def test_direct_payment_view_post(self, mock):
        """ Verify we can make payments using the DummyCyclosBackend """
        from cc3.marketplace.models import AdPaymentTransaction

        self.client.login(
            username=self.profile.user.username, password='testing')

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock.return_value = Transaction(
            sender=self.profile.user,
            recipient=self.profile_2.user,
            amount=10,
            created=datetime.now(),
            description='test_payment',
            transfer_id=63
        )

        response = self.client.post(
            reverse('accounts_pay_direct'),
            {
                'amount': '10',
                'contact_name': 'Foo bar (Test business)',
                'profile': self.profile_2.id,
                'description': 'test payment'
            })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse('accounts_home'))
        self.assertEqual(AdPaymentTransaction.objects.count(), 1)

        # Ensure the entries in the payment log are correct
        payment = AdPaymentTransaction.objects.latest('pk')
        self.assertEqual(payment.amount, Decimal('10.0'))
        self.assertEqual(payment.ad, None)
        self.assertEqual(payment.title, 'test payment')
        self.assertEqual(payment.sender, self.profile.user)
        self.assertEqual(payment.receiver, self.profile_2.user)
        self.assertEqual(payment.transfer_id, 63)
        self.assertEqual(payment.split_payment_total_amount, None)


class CustomContactNameAutoTestCase(TestCase):

    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.init_group = CyclosGroup.objects.create(
            id=1, name='init_group', initial=True)
        self.community = CC3CommunityFactory.create()
        self.groupset = CyclosGroupSet.objects.create(
            pk=settings.STADLANDER_GROUPSET_ID, name='Groupset',
            slug='groupset')
        self.groupset.groups.add(self.init_group)
        self.community.groupsets.add(self.groupset)

        self.profile_1 = UserProfileFactory.create(community=self.community,
                                                   cyclos_group=self.init_group)
        self.individual_profile_1 = IndividualProfileFactory.create(
            profile=self.profile_1)
        self.profile_2 = UserProfileFactory.create(community=self.community,
                                                   cyclos_group=self.init_group)
        self.individual_profile_2 = IndividualProfileFactory.create(
            profile=self.profile_2)
        self.profile_3 = UserProfileFactory.create(community=self.community,
                                                   cyclos_group=self.init_group)
        self.individual_profile_3 = IndividualProfileFactory.create(
            profile=self.profile_3)
        self.profile_firstname_1 = UserProfileFactory.create(
            community=self.community,
            first_name="John",
            last_name="Smith",
            cyclos_group=self.init_group,
        )
        self.individual_profile_firstname_1 = IndividualProfileFactory.create(
            profile=self.profile_firstname_1)

        self.profile_firstname_2 = UserProfileFactory.create(
            community=self.community,
            first_name="John",
            last_name="Dyke",
            cyclos_group=self.init_group,
        )
        self.individual_profile_firstname_2 = IndividualProfileFactory.create(
            profile=self.profile_firstname_2)
        self.profile_firstname_3 = UserProfileFactory.create(
            community=self.community,
            first_name="John",
            last_name="Smith-Black",
            cyclos_group=self.init_group,
        )
        self.individual_profile_firstname_3 = IndividualProfileFactory.create(
            profile=self.profile_firstname_3)
        self.profile_firstname_4 = UserProfileFactory.create(
            community=self.community,
            first_name="Jan de",
            last_name="Waar",
            cyclos_group=self.init_group,
        )
        self.individual_profile_firstname_4 = IndividualProfileFactory.create(
            profile=self.profile_firstname_4)

    def test_returned_data(self):
        """
        Tests the JSON data returned by the view.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        # Send a fragment of the string to search for coincidences in the
        # existent profiles. All factory-created profiles have 'CC3Profile' as
        # profile name, so 'CC3P' can be a good string to search for.
        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertIn('pk', data[0])
        self.assertIn('value', data[0])

    def test_dont_return_request_user(self):
        """
        Tests that the request user should not be returned in the search.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Only return 2 of the 3 created profiles (one is who makes the
        # request).
        self.assertEqual(len(data), 2)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_non_existent_community(self):
        """
        Tests returning a 404 error when the user tries to retrieve results
        from a community he doesn't belong to.
        """
        non_community = CC3CommunityFactory.create()
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': non_community.pk}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_invalid_community(self):
        """
        Tests returning a 404 error when the given community is not valid.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': 999}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=False)
    def test_community_results(self):
        """ Only contacts from own community !INTER_COMMUNITIES_TRANSACTIONS """
        new_community = CC3CommunityFactory.create()
        new_community.groupsets.add(self.groupset)

        member = UserProfileFactory.create(
            community=new_community, cyclos_group=self.init_group)
        IndividualProfileFactory.create(profile=member)

        profile = UserProfileFactory.create(
            community=new_community, cyclos_group=self.init_group)
        IndividualProfileFactory.create(profile=profile)

        self.client.login(
            username=profile.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': new_community.pk}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Must be only 1 user: the one we created above. No users from `setUp`
        # should be present here.
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['pk'], member.pk)

    @override_settings(INTER_COMMUNITIES_TRANSACTIONS=True)
    def test_results_include_all_communities(self):
        """ Contacts from all communities INTER_COMMUNITIES_TRANSACTIONS """
        another_community = CC3CommunityFactory.create()
        another_community.groupsets.add(self.groupset)

        profile = UserProfileFactory.create(
            community=another_community, cyclos_group=self.init_group)
        IndividualProfileFactory.create(profile=profile)

#        profile = CC3ProfileFactory.create(community=another_community)

        self.client.login(
            username=profile.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': another_community.pk}
        ), {'contact_name': "CC3P", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Must be at least 1 user, created above, plus users from `setUp`
        # should be present here.
        self.assertGreater(len(data), 1)

    def test_short_search_term_doesnt_return_users(self):
        """
        Tests that no results are returned for searches less than 5 chars.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "CC3", }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Only return 2 of the 3 created profiles (one is who makes the
        # request).
        self.assertEqual(len(data), 0)

    @skip("Multiple search terms for name shouldn't work now. Can revisit")
    def test_multiple_search_terms(self):
        """
        Tests that results are returned for searches with multiple words.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "John Smith Dyke Black", },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Only return 2 of the 3 created profiles (one is who makes the
        # request).
        self.assertEqual(len(data), 3)

    def test_continuation_of_search_terms(self):
        """
        Tests that results are returned for searches with multiple words.
        """
        self.client.login(
            username=self.profile_3.user.username, password='testing')

        response = self.client.get(reverse(
            'contact_name_auto',
            kwargs={'community': self.community.pk}
        ), {'contact_name': "Jan de", },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Only return 2 of the 3 created profiles (one is who makes the
        # request).
        self.assertEqual(len(data), 1)
