import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.translation import activate
from django.conf import settings

from icare4u_front.profile.tests.test_factories import \
    IndividualProfileFactory, UserProfileFactory

from ..models import StadlanderProfile, CommunityWoonplaat
from ..backends import StadlanderSSOBackend

from cc3.cyclos.tests.test_factories import CC3CommunityFactory
from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.models import CyclosGroupSet, CyclosGroup
from cc3.cyclos.models.account import User
from cc3.cyclos.backends import set_backend
from cc3.rewards.tests.test_factories import DefaultGoodCauseUserFactory
from cc3.rules.tests.test_factories import RuleFactory
from cc3.rules.utils import str_to_class

LOG = logging.getLogger(__name__)


class StadlanderActionsTestCase(TestCase):
    def setUp(self):
        self.backend = DummyCyclosBackend()
        set_backend(self.backend)

        self.sso_backend = StadlanderSSOBackend()
        activate('en')
        self.init_group = CyclosGroup.objects.create(
            id=1, name='init_group', initial=True)
        self.community = CC3CommunityFactory()
        self.comm_woon = CommunityWoonplaat.objects.create(
            community=self.community, woonplaat='Amsterdam')
        # don't really know why this is necessary, but ...
        try:
            self.groupset = CyclosGroupSet.objects.get(
                pk=settings.STADLANDER_GROUPSET_ID)
        except:
            self.groupset = CyclosGroupSet.objects.create(
                pk=settings.STADLANDER_GROUPSET_ID, name='Groupset',
                slug='groupset')
        self.groupset.groups.add(self.init_group)
        self.community.groupsets.add(self.groupset)
        self.user_profile = UserProfileFactory(community=self.community)

        self.individual_profile = IndividualProfileFactory(
            profile=self.user_profile)
        self.st_profile = StadlanderProfile.objects.create(
            rel_number=123, profile=self.user_profile)

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

    def tearDown(self):
        activate('nl')

    def test_pay_stadlander_perform(self):

        madule = self.rule.action_class[:self.rule.action_class.rindex(".")]
        klass = self.rule.action_class[self.rule.action_class.rindex(".") + 1:]
        action = str_to_class(madule, klass)

        # prepare kwargs
        parameters = self.rule.parameter_names.split(",")
        values = self.rule.parameter_values.split(",")
        kwargs = dict(zip(parameters, values))

        # add instance specific id
        kwargs[self.rule.instance_identifier] = 123  # = identity

        # hand over rule id, so that any rule field(s) can be used in
        # payment description
        kwargs['rule_id'] = self.rule.id

        # perform action as rule passed, and no limit to
        performed_result = json.loads(action.perform(**kwargs))
#       [
#           [
#               [],
#               {
#                   "persoonsnummer": 123,
#                   "sender": "stadlander",
#                   "rule_id": 2,
#                   "amount": "25",
#                   "cause_payment": "failed, User 3 is not
#                                     committed with any cause.",
#                   "payment": "success"
#               }
#           ],
#           {}
#       ]

        self.assertEqual(performed_result[0][1]['payment'], u'success')
        self.assertEqual(performed_result[0][1]['cause_payment'], u'success')
