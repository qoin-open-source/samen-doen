from datetime import date

import factory

from cc3.cyclos.tests.test_factories import CC3ProfileFactory


class UserProfileFactory(CC3ProfileFactory):
    class Meta:
        model = 'profile.UserProfile'

    terms_and_conditions = True


class IndividualProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'profile.IndividualProfile'

    profile = factory.SubFactory(UserProfileFactory)


class BusinessProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'profile.BusinessProfile'

    account_holder = 'Test account 123'
    profile = factory.SubFactory(UserProfileFactory)
    iban = 'GB82 WEST 1234 5698 7654 32'
    bic_code = 'BARCGB23034'
    mandate_id = factory.Sequence(lambda n: '{num:035d}'.format(num=n))
    signature_date = date.today()


class CharityProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'profile.CharityProfile'

    account_holder = 'Test account 999'
    profile = factory.SubFactory(UserProfileFactory)
    iban = 'NL24 RABO 0133 4434 93'
    bic_code = 'BARCGB23034'
    mandate_id = factory.Sequence(lambda n: '{num:035d}'.format(num=n))
    signature_date = date.today()
