import logging

import factory

from cc3.cyclos.tests.test_factories import CC3ProfileFactory

# Suppress debug information from Factory Boy.
logging.getLogger('factory').setLevel(logging.WARN)


class HuurcontractFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'csvimporttemp.Huurcontract'

    vestigingnummer = factory.Sequence(lambda n: n)


class PositoosFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'csvimporttemp.Positoos'


class UserProfileFactory(CC3ProfileFactory):
    class Meta:
        model = 'profile.UserProfile'

    terms_and_conditions = True


class StadlanderProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'stadlander.StadlanderProfile'

    profile = factory.SubFactory(UserProfileFactory)
