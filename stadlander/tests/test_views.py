from mock import patch, Mock
import random
import string

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend
from cc3.cyclos.models import CyclosGroupSet, CyclosGroup
from cc3.rewards.tests.test_factories import DefaultGoodCauseUserFactory
from cc3.rules.tests.test_factories import RuleFactory
from cc3.cyclos.models.account import User
from cc3.cyclos.tests.test_factories import CC3CommunityFactory

from icare4u_front.profile.tests.test_factories import (
    UserProfileFactory, IndividualProfileFactory)

from ..models import (PotentialLinkFound, StadlanderProfile,
                      CommunityWoonplaat)


class StadlanderViewTestCase(TestCase):
    """
    Test case for the Stadlander backend.
    """
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.papi_key = ''.join(random.choice(string.hexdigits)
                                for _ in range(64))
        self.sl_login_url = reverse('stadlander_login')

        self.init_group = CyclosGroup.objects.create(
            id=1, name='init_group', initial=True)
        self.community = CC3CommunityFactory()
        self.comm_woon = CommunityWoonplaat.objects.create(
            community=self.community, woonplaat='Amsterdam')
        # don't really know why this is necessary, but ...
        try:
            self.groupset = CyclosGroupSet.objects.get(
                pk=settings.STADLANDER_GROUPSET_ID)
        except CyclosGroupSet.DoesNotExist:
            self.groupset = CyclosGroupSet.objects.create(
                pk=settings.STADLANDER_GROUPSET_ID, name='Groupset',
                slug='groupset')
        self.groupset.groups.add(self.init_group)
        self.community.groupsets.add(self.groupset)
        self.user_profile = UserProfileFactory(community=self.community)

        self.individual_profile = IndividualProfileFactory(
            profile=self.user_profile)
        self.defaultgoodcause = DefaultGoodCauseUserFactory.create(
            community=self.user_profile.community
        )
        # set a default good cause for the profile
        self.individual_profile.set_good_cause()
        self.rule = RuleFactory.create(
            action_class=u"icare4u_front.stadlander.actions.PayStadlander",
            parameter_names=u"sender,amount",
            parameter_values="stadlander,25",
            process_model=ContentType.objects.get_for_model(User),
            instance_identifier='persoonsnummer',
        )

        self.user = self.user_profile.user

        self.factory = RequestFactory()

    def get_login_url(self, papi):
        return "{0}?papi={1}".format(self.sl_login_url, papi)

    def get_confirm_link_url(self, papi):
        return reverse('stadlander_confirm_link',
                       kwargs={'papi': self.papi_key})

    @patch('icare4u_front.stadlander.views.check_papi_key')
    @patch('icare4u_front.stadlander.backends.check_papi_key')
    @patch('icare4u_front.stadlander.backends.StadlanderSSOBackend.get_user_from_sso_items')
    def test_exception_redirects_to_confirm_page(
            self, get_user_mock, check_papi_mock, views_check_papi_mock):
        """
        Tests redirection to link confirmation when exception is raised
        """
        rel_number = 12345
        # get_user_mock.side_effect = PotentialLinkFound(
        #             self.user, rel_number, self.papi_key)
        get_user_mock.side_effect = PotentialLinkFound
        check_papi_mock.return_value = {'rel_number': 12345,
                                        'mail': self.user.email}
        views_check_papi_mock.return_value = {'rel_number': 12345,
                                              'mail': self.user.email}
        url = self.get_login_url(self.papi_key)
        response = self.client.get(url)
        self.assertRedirects(response, self.get_confirm_link_url(self.papi_key))

    @patch('icare4u_front.stadlander.views.check_papi_key')
    def test_confirm_link_view_get(self, views_check_papi_mock):
        """
        Tests GET on confirm_link view displays confirmation form
        """
        views_check_papi_mock.return_value = {'rel_number': 12345,
                                              'mail': self.user.email}
        response = self.client.get(
            self.get_confirm_link_url(self.papi_key))
        self.assertTemplateUsed(response, "stadlander/confirm_link.html")
        self.assertContains(response, self.user.email)

    @patch('icare4u_front.stadlander.views.check_papi_key')
    @patch('icare4u_front.stadlander.backends.check_papi_key')
    def test_confirm_link_view_post_yes(self,
                                        check_papi_mock, views_check_papi_mock):
        """
        Tests hitting "yes" redirects to Done page, creates SL profile,
        updates groupset and logs in the user
        """
        items = {'rel_number': 12345, 'mail': self.user.email,
                 'initials': 'ABC', 'last_name': 'Example',
                 'first_name': 'Test', 'street': 'Streetname',
                 'zip_code': '1234AA', 'residence': 'Amsterdam',
                 'addition': '', 'number': '416', 'insert': '',
                 'gender': 'Male', 'date_of_birth': '1980-06-01'}
        check_papi_mock.return_value = items
        views_check_papi_mock.return_value = items
        self.user_profile.groupset = None
        self.user_profile.save()
        response = self.client.post(
            self.get_confirm_link_url(self.papi_key),
            {
                'link_yes': 1
            }, follow=True)
        self.assertTemplateUsed(response, "stadlander/confirm_link_done.html")
        self.assertIn('_auth_user_id', self.client.session)
        sl_profiles = StadlanderProfile.objects.filter(
                        profile=self.user_profile, rel_number=12345)
        self.assertEqual(sl_profiles.count(), 1)
        # TODO not currently working -- why not?
        # self.assertEqual(self.user_profile.groupset, self.groupset)

    @patch('icare4u_front.stadlander.views.check_papi_key')
    def test_confirm_link_view_post_no(self, views_check_papi_mock):
        """
        Tests hitting "no" redirects to "refused" page
        """
        views_check_papi_mock.return_value = {'rel_number': 12345,
                                              'mail': self.user.email}
        response = self.client.post(
            self.get_confirm_link_url(self.papi_key),
            {
                'link_no': 1
            })
        self.assertRedirects(response,
                             reverse('stadlander_confirm_link_refused'))
