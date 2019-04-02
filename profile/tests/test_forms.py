from datetime import date, timedelta

from django.db.models.signals import post_save
from django.forms import ValidationError
from django.test import TestCase
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.utils.translation import ugettext as _

from mock import patch

from cc3.core.tests.test_factories import CategoryFactory
from cc3.cyclos.models import CC3Profile
from cc3.cyclos.tests.test_factories import CC3CommunityFactory

from ..forms import (
    CommunityBusinessProfileForm, CommunityUserProfileForm, DateRangeForm,
    CommunityIndividualProfileForm)
from ..models import (
    BusinessProfile, IndividualProfile, UserProfile, link_business_account,
    link_individual_account)
from ..utils import SignalContextManager, generate_mandate_id


class DateRangeFormTestCase(TestCase):
    def setUp(self):
        self.form = DateRangeForm()

    def test_clean_date_from(self):
        """
        Tests the validation for the ``date_from`` field.
        """
        self.form.cleaned_data = {
            'date_from': date.today() + timedelta(days=30),
            'date_to': date.today()
        }

        self.assertRaisesMessage(
            ValidationError,
            _(u'Selected date must be in the past'),
            self.form.clean_date_from)

    def test_clean_date_to(self):
        """
        Tests the validation for the ``date_from`` field.
        """
        self.form.cleaned_data = {
            'date_from': date.today(),
            'date_to': date.today() + timedelta(days=30)
        }

        self.assertRaisesMessage(
            ValidationError,
            _(u'Selected date must be in the past or today, as much'),
            self.form.clean_date_to)

    def test_clean(self):
        """
        Tests the global validation of the form.
        """
        self.form.cleaned_data = {
            'date_from': date.today() - timedelta(days=10),
            'date_to': date.today() - timedelta(days=30)
        }

        self.assertRaisesMessage(
            ValidationError,
            _(u'Initial date must be in past of final date'),
            self.form.clean)


class CommunityUserProfileFormTestCase(TestCase):
    def setUp(self):
        self.community = CC3CommunityFactory.create()
        self.category = CategoryFactory.create()

        self.form = CommunityUserProfileForm()

        self.date_of_birth = date(1976, 11, 18)

        self.form_data = {
            'business_name': 'Maykin Media',
            'city': 'Amsterdam',
            'address': 'Herengracht',
            'postal_code': '1017BZ',
            'extra_address': '',
            'phone_number': '+31 (0)20 753 05 23',
            'company_website': 'http://www.maykinmedia.nl',
            'company_description': 'Web development studio.',
            'community': self.community,
            'categories': [self.category],
            'email': 'info@maykinmedia.nl',
            'first_name': 'Alex',
            'tussenvoegsel': 'de',
            'last_name': 'Landgraaf',
            'num_street': '416',
            'gender': 'M',
            'date_of_birth': self.date_of_birth,

        }

    @patch('cc3.cyclos.backends.search')
    def test_save_method(self, mock):
        """
        Tests ``save`` method (individual) overridden from base ``ModelForm``
        class to ensure that ``User`` and ``UserProfile`` are properly saved.
        """
        mock.return_value = []

        self.form.cleaned_data = self.form_data

        with SignalContextManager(
                post_save, receiver=link_individual_account, sender=CC3Profile,
                dispatch_uid='cc3_qoin_profile_save', reconnect=False):
            self.form.save()

        profiles = UserProfile.objects.all()
        self.assertGreater(len(profiles), 0)

        profile = profiles.latest('pk')
        self.assertEqual(
            profile.business_name, self.form.cleaned_data['business_name'])
        self.assertEqual(
            profile.city, self.form.cleaned_data['city'])
        self.assertEqual(profile.address, self.form.cleaned_data['address'])
        self.assertEqual(
            profile.postal_code, self.form.cleaned_data['postal_code'])
        self.assertEqual(
            profile.phone_number, self.form.cleaned_data['phone_number'])
        self.assertEqual(
            profile.company_website, self.form.cleaned_data['company_website'])
        self.assertEqual(
            profile.company_description,
            self.form.cleaned_data['company_description'])
        self.assertEqual(
            profile.community, self.form.cleaned_data['community'])
        self.assertEqual(
            profile.categories.all()[0],
            self.form.cleaned_data['categories'][0])
        self.assertEqual(profile.user.email, self.form.cleaned_data['email'])
        # No longer editable
        # self.assertEqual(
        #     profile.first_name, self.form.cleaned_data['first_name'])
        # self.assertEqual(
        #     profile.tussenvoegsel, self.form.cleaned_data['tussenvoegsel'])
        # self.assertEqual(
        #     profile.last_name, self.form.cleaned_data['last_name'])
        self.assertEqual(
            profile.num_street, self.form.cleaned_data['num_street'])
        self.assertEqual(profile.gender, self.form.cleaned_data['gender'])
        self.assertEqual(profile.date_of_birth, self.date_of_birth)

    @patch('cc3.cyclos.backends.search')
    def test_clean_email_exists_in_cyclos(self, mock):
        """
        Tests ``clean_email`` method when the email is already previously
        registered in Cyclos backend.
        """
        mock.return_value = [
            (
                99,
                'John Doe',
                'info@maykinmedia.nl',
                'infomaykinmedianl',
                '12'
            )
        ]

        self.form.cleaned_data = self.form_data

        self.assertRaisesMessage(
            ValidationError,
            _(u"There is already an account with this e-mail address in "
              u"our system."),
            self.form.clean_email)


class CommunityBusinessProfileFormTestCase(TestCase):
    def setUp(self):
        self.community = CC3CommunityFactory.create()
        self.category = CategoryFactory.create()

        self.form = CommunityBusinessProfileForm()
        self.form_data = {
            'business_name': 'Maykin Media',
            'city': 'Amsterdam',
            'address': 'Herengracht',
            'postal_code': '1017BZ',
            'extra_address': '',
            'phone_number': '+31 (0)20 753 05 23',
            'company_website': 'http://www.maykinmedia.nl',
            'company_description': 'Web development studio.',
            'community': self.community,
            'categories': [self.category],
            'email': 'info@maykinmedia.nl',
            'first_name': 'Alex',
            'tussenvoegsel': 'de',
            'last_name': 'Landgraaf',
            'num_street': '416',
            'gender': 'M',
            'date_of_birth': None,
            'iban': 'NL39RABO0300065264',
            'bic_code': 'RABONL78342',
            'signature_date': date.today()
        }

    @patch('cc3.cyclos.backends.search')
    def test_save_method(self, mock):
        """
        Tests the ``save`` method (business) overridden from base ``ModelForm``
        class to ensure that ``User``, ``UserProfile`` and ``BusinessProfile``
        are properly saved.
        """
        mock.return_value = []

        self.form.cleaned_data = self.form_data

        with SignalContextManager(
                post_save, receiver=link_business_account,
                sender=BusinessProfile,
                dispatch_uid='icare4u_business_profile_save'):
            self.form.save()

        business_profiles = BusinessProfile.objects.all()
        self.assertGreater(len(business_profiles), 0)

        business_profile = business_profiles.latest('pk')
        self.assertEqual(
            business_profile.profile.business_name,
            self.form.cleaned_data['business_name'])
        self.assertEqual(
            business_profile.profile.city, self.form.cleaned_data['city'])
        self.assertEqual(
            business_profile.profile.address,
            self.form.cleaned_data['address'])
        self.assertEqual(
            business_profile.profile.postal_code,
            self.form.cleaned_data['postal_code'])
        self.assertEqual(
            business_profile.profile.phone_number,
            self.form.cleaned_data['phone_number'])
        self.assertEqual(
            business_profile.profile.company_website,
            self.form.cleaned_data['company_website'])
        self.assertEqual(
            business_profile.profile.company_description,
            self.form.cleaned_data['company_description'])
        self.assertEqual(
            business_profile.profile.community,
            self.form.cleaned_data['community'])
        self.assertEqual(
            business_profile.profile.categories.all()[0],
            self.form.cleaned_data['categories'][0])
        self.assertEqual(
            business_profile.profile.user.email,
            self.form.cleaned_data['email'])
        # no longer editable
        # self.assertEqual(
        #     business_profile.profile.first_name,
        #     self.form.cleaned_data['first_name'])
        # self.assertEqual(
        #     business_profile.profile.tussenvoegsel,
        #     self.form.cleaned_data['tussenvoegsel'])
        # self.assertEqual(
        #     business_profile.profile.last_name,
        #     self.form.cleaned_data['last_name'])
        self.assertEqual(
            business_profile.profile.num_street,
            self.form.cleaned_data['num_street'])
        self.assertEqual(
            business_profile.profile.gender, self.form.cleaned_data['gender'])

        self.assertEqual(
            business_profile.iban, self.form.cleaned_data['iban'])
        self.assertEqual(
            business_profile.bic_code, self.form.cleaned_data['bic_code'])

        # MANDATE ID is SDxxxxxx where xxxxxxx is the zero padded auth_user id
        # 2911
        self.assertEqual(
            business_profile.mandate_id,
            generate_mandate_id(business_profile.profile.user)
        )


class CommunityIndividualProfileFormTestCase(TestCase):
    def setUp(self):
        self.community = CC3CommunityFactory.create()
        self.category = CategoryFactory.create()

        self.form = CommunityIndividualProfileForm()
        self.form_data = {
            'business_name': 'Maykin Media',
            'city': 'Amsterdam',
            'address': 'Herengracht',
            'postal_code': '1017BZ',
            'extra_address': '',
            'phone_number': '+31 (0)20 753 05 23',
            'company_website': 'http://www.maykinmedia.nl',
            'company_description': 'Web development studio.',
            'community': self.community,
            'categories': [self.category],
            'email': 'info@maykinmedia.nl',
            'first_name': 'Alex',
            'tussenvoegsel': 'de',
            'last_name': 'Landgraaf',
            'num_street': '416',
            'gender': 'M',
            'date_of_birth': date.today() - timedelta(days=7300),
            'nickname': 'alex'
        }

    @patch('cc3.cyclos.backends.search')
    def test_save_method(self, mock):
        """
        Tests ``save`` method (individual) overridden from base ``ModelForm``
        class to ensure that ``User``, ``UserProfile`` and ``IndividualProfile``
        are properly saved.
        """
        mock.return_value = []

        self.form.cleaned_data = self.form_data

        with SignalContextManager(
                post_save, receiver=link_individual_account,
                sender=IndividualProfile,
                dispatch_uid='icare4u_individual_profile_save'):
            self.form.save()

        individual_profiles = IndividualProfile.objects.all()
        self.assertGreater(len(individual_profiles), 0)

        individual_profile = individual_profiles.latest('pk')
        self.assertEqual(
            individual_profile.profile.business_name,
            individual_profile.profile.name)
        self.assertEqual(
            individual_profile.profile.city, self.form.cleaned_data['city'])
        self.assertEqual(
            individual_profile.profile.address,
            self.form.cleaned_data['address'])
        self.assertEqual(
            individual_profile.profile.postal_code,
            self.form.cleaned_data['postal_code'])
        self.assertEqual(
            individual_profile.profile.phone_number,
            self.form.cleaned_data['phone_number'])
        self.assertEqual(
            individual_profile.profile.company_website,
            self.form.cleaned_data['company_website'])
        self.assertEqual(
            individual_profile.profile.company_description,
            self.form.cleaned_data['company_description'])
        self.assertEqual(
            individual_profile.profile.community,
            self.form.cleaned_data['community'])
        self.assertEqual(
            individual_profile.profile.categories.all()[0],
            self.form.cleaned_data['categories'][0])
        self.assertEqual(
            individual_profile.profile.user.email,
            self.form.cleaned_data['email'])
        # no longer editable, so not in form cleaned_data
        # self.assertEqual(
        #     individual_profile.profile.first_name,
        #     self.form.cleaned_data['first_name'])
        # self.assertEqual(
        #     individual_profile.profile.tussenvoegsel,
        #     self.form.cleaned_data['tussenvoegsel'])
        # self.assertEqual(
        #     individual_profile.profile.last_name,
        #     self.form.cleaned_data['last_name'])
        self.assertEqual(
            individual_profile.profile.num_street,
            self.form.cleaned_data['num_street'])
        self.assertEqual(
            individual_profile.profile.gender,
            self.form.cleaned_data['gender'])

        self.assertEqual(
            individual_profile.profile.date_of_birth,
            date.today() - timedelta(days=7300))
        self.assertEqual(individual_profile.nickname, 'alex')
