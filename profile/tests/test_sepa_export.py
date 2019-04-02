import logging
import re

from copy import deepcopy
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from unittest.case import skip

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_save
from django.test import TestCase
from django.test.utils import override_settings

from xmltest import XMLAssertions
from mock import MagicMock, patch

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.backends import set_backend

from ..models import BusinessProfile, link_business_account
from ..sepa_export import SEPAExporter
from ..utils import SignalContextManager
from .test_factories import BusinessProfileFactory

LOG = logging.getLogger(__name__)


class SEPAExportTestCase(TestCase, XMLAssertions):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        # Copy the ``SEPA_SETTINGS`` dictionary to use it to override settings.
        self.sepa_settings = deepcopy(settings.SEPA_SETTINGS)

        with SignalContextManager(
                post_save, receiver=link_business_account,
                sender=BusinessProfile,
                dispatch_uid='icare4u_business_profile_save'):

            self.business_1 = BusinessProfileFactory.create()
            self.business_2 = BusinessProfileFactory.create()
            self.business_3 = BusinessProfileFactory.create()

            self.initial = date.today() - timedelta(days=30)
            self.today = date.today()

    def test_init_dates_sanity_check(self):
        """
        Tests the ``__init__`` method sanity check for dates.
        """
        # Passing the dates inverted (the final date is in the past and the
        # initial date is today) must raise an exception.
        LOG.warning("Info: SEPA test 1. test_init_dates_sanity_check: ")
        self.assertRaisesMessage(
            ValueError, 'Invalid dates passed to SEPA exporter.',
            SEPAExporter, date_from=self.today, date_to=self.initial)

    @skip('SEPA run no longer fails if no account_holder set, generates '
          'invoice instead, test needs revising')
    def test_empty_account_holder(self):
        """
        Tests that Businesses are ignored if they don't have their fields
        filled in.
        """
        # Passing the dates inverted (the final date is in the past and the
        # initial date is today) must raise an exception.
        LOG.warning("Info: SEPA test 2. test_empty_account_holder: ")
        BusinessProfile.objects.update(account_holder='')
        self.assertRaisesMessage(
            ValueError, 'No business profiles available in database.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_initiating_business_sanity_check(self):
        """
        Tests sanity check for the ``INITIATING_BUSINESS`` setting.
        """
        LOG.warning("Info: SEPA test 3. test_init_initiating_business_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['INITIATING_BUSINESS']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'INITIATING_BUSINESS or END_TO_END_ID not defined in project '
            'settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_name_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['NAME']`` setting.
        """
        LOG.warning("Info: SEPA test 4. test_init_creditor_name_sanity_check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['NAME']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR NAME not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_bic_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['BIC']`` setting.
        """
        LOG.warning("Info: SEPA test 5. test_init_creditor_bic_sanity_check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['BIC']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR BIC not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_iban_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['IBAN']`` setting.
        """
        LOG.warning("Info: SEPA test 6. test_init_creditor_iban_sanity_check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['IBAN']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR IBAN not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_ultimate_creditor_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['ULTIMATE_CREDITOR']`` setting.
        """
        LOG.warning("Info: SEPA test 7. test_init_ultimate_creditor_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['ULTIMATE_CREDITOR']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR ULTIMATE_CREDITOR not defined in project '
            'settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_identifier_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['IDENTIFIER']`` setting.
        """
        LOG.warning("Info: SEPA test 8. test_init_creditor_identifier_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['IDENTIFIER']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR IDENTIFIER not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_country_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['COUNTRY']`` setting.
        """
        LOG.warning("Info: SEPA test 9. test_init_creditor_country_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['COUNTRY']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR COUNTRY not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_street_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['STREET_NUMBER']``
        setting.
        """
        LOG.warning("Info: SEPA test 10. test_init_creditor_street_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['STREET_NUMBER']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR STREET_NUMBER not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @override_settings(SEPA_SETTINGS=None)
    def test_init_creditor_postcode_sanity_check(self):
        """
        Tests sanity check for the ``CREDITOR['POSTCODE_CITY']``
        setting.
        """
        LOG.warning("Info: SEPA test 11. test_init_creditor_postcode_sanity_"
                    "check: ")
        settings.SEPA_SETTINGS = self.sepa_settings
        # Remove the mandatory setting. Now is missing.
        del settings.SEPA_SETTINGS['CREDITOR']['POSTCODE_CITY']

        self.assertRaisesMessage(
            ImproperlyConfigured,
            'CREDITOR POSTCODE_CITY not defined in project settings.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    def test_init_business_profiles_sanity_check(self):
        """
        Tests the ``__init__`` method sanity check for ``BusinessProfile``s
        availability.
        """
        # Delete all existing ``BusinessProfiles`` in database.
        LOG.warning("Info: SEPA test 12. test_init_business_profiles_sanity_"
                    "check: ")
        [business.delete() for business in BusinessProfile.objects.all()]

        self.assertRaisesMessage(
            ValueError, 'No business profiles available in database.',
            SEPAExporter, date_from=self.initial, date_to=self.today)

    @patch('cc3.cyclos.backends.get_account_status')
    def test_classify_balances(self, mock):
        """
        Tests the ``_classify_balances`` method.

        The method iterates over the existent ``BusinessProfile``s, querying
        Cyclos for their ``accountStatus.balance`` and then putting
        them into the correspondent place: ``self.credit_transactions`` or
        ``self.debit_transactions`` in ``SEPAExporter`` class dictionaries.

        In this test, the Cyclos backend method ``get_account_status`` is being
        mocked, making it returning ``accountStatus.avaliableBalance``s of our
        own choice. We'll return this:

            - 150 Positoos for the ``business_1``.
            - -50 Positoos for the ``business_2``.
            - 200 Positoos for the ``business_3``.

        All this must result in ``business_1`` and ``business_3`` being
        classified as 'credit transactions' with an amount of 1.50 EUR and 2.00
        EUR, respectively, and ``business_2`` being classified as 'debit
        transaction' with an amount of 0.50 EUR.
        """
        LOG.warning("Info: SEPA test 13. test_classify_balances: ")
        account_status_1 = MagicMock()
        account_status_2 = MagicMock()
        account_status_3 = MagicMock()
        account_status_1.accountStatus.balance = Decimal('150.000000')
        account_status_2.accountStatus.balance = Decimal('-50.000000')
        account_status_3.accountStatus.balance = Decimal('200.000000')
        mock.side_effect = [
            account_status_1,
            account_status_2,
            account_status_3
        ]

        exporter = SEPAExporter(date_from=self.initial, date_to=self.today)

        self.assertDictEqual(
            exporter.credit_transactions,
            {
                self.business_1: Decimal('1.50'),
                self.business_3: Decimal('2.00'),
            })
        self.assertDictEqual(
            exporter.debit_transactions,
            {'FRST': {self.business_2: Decimal('0.50')}, 'RCUR': {}})

    @patch('cc3.cyclos.backends.get_account_status')
    def test_sepa_header(self, mock):
        """
        Tests the ``_sepa_header`` method.

        Read previous tests docs to see how this test is performed. Basically,
        we are giving here 3 businesses with a total positive amount of 400
        Positoos in balance, so they should be credited with a total amount of
        4 EUR. The SEPA header then must be built according to this amounts.
        """
        LOG.warning("Info: SEPA test 14. test_sepa_header: ")
        account_status_1 = MagicMock()
        account_status_2 = MagicMock()
        account_status_3 = MagicMock()
        account_status_1.accountStatus.balance = Decimal('150.000000')
        account_status_2.accountStatus.balance = Decimal('50.000000')
        account_status_3.accountStatus.balance = Decimal('200.000000')
        mock.side_effect = [
            account_status_1,
            account_status_2,
            account_status_3
        ]
        exporter = SEPAExporter(date_from=self.initial, date_to=self.today)

        header = exporter._sepa_header(Decimal('4.00'), 3)

        fields = header.sorted_fields()
        self.assertIn('sepa_header', fields)
        self.assertIn('message_id', fields)
        self.assertIn('creation_date_time', fields)
        self.assertIn('number_of_operations', fields)
        self.assertIn('checksum', fields)
        self.assertIn('initiating_party', fields)
        self.assertIn('creditor_agent', fields)

        self.assertEqual(header.checksum.value, Decimal('4.00'))
        self.assertIsNotNone(header.message_id.value)
        self.assertEqual(header.number_of_operations.value, 3)

    @patch('cc3.cyclos.backends.get_account_status')
    def test_transaction_description(self, mock):
        """
        Tests the ``transaction_description`` method.
        """
        LOG.warning("Info: SEPA test 15. test_transaction_description: ")
        account_status_1 = MagicMock()
        account_status_2 = MagicMock()
        account_status_3 = MagicMock()
        account_status_1.accountStatus.balance = Decimal('150.000000')
        account_status_2.accountStatus.balance = Decimal('50.000000')
        account_status_3.accountStatus.balance = Decimal('200.000000')
        mock.side_effect = [
            account_status_1,
            account_status_2,
            account_status_3
        ]

        exporter = SEPAExporter(date_from=self.initial, date_to=self.today)

        description = exporter.transaction_description(self.business_1)
        self.assertEqual(
            description,
            u'{0} - {1}'.format(exporter.end_to_end_id, self.business_1.pk))

    @patch('cc3.cyclos.backends.get_account_status')
    def test_sepa_xml_export_credit(self, mock):
        """
        Tests exporting of the SEPA credit data to XML.
        """
        LOG.warning("Info: SEPA test 16. test_sepa_xml_export_credit: ")
        account_status_1 = MagicMock()
        account_status_2 = MagicMock()
        account_status_3 = MagicMock()
        account_status_1.accountStatus.balance = Decimal('150.000000')
        account_status_2.accountStatus.balance = Decimal('50.000000')
        account_status_3.accountStatus.balance = Decimal('200.000000')
        mock.side_effect = [
            account_status_1,
            account_status_2,
            account_status_3
        ]

        exporter = SEPAExporter(date_from=self.initial, date_to=self.today)

        xml_string = exporter.build_direct_credit_xml()
        # Remove the 'xlmns' attribute, which is stopping us when trying to
        # retrieve any XML element.
        xml_string = re.sub('xmlns="[^"]+"', '', xml_string)

        # 'CstmrCdtTrfInitn', from the SEPA standard XML pain.001.001.03.
        self.assertXPathNodeCount(xml_string, 1, 'CstmrCdtTrfInitn')

        # The SEPA header.
        self.assertXPathNodeCount(xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr/MsgId')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr/CreDtTm')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr/NbOfTxs')
        self.assertXPathNodeText(
            xml_string, '3', 'CstmrCdtTrfInitn/GrpHdr/NbOfTxs')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr/CtrlSum')
        self.assertXPathNodeText(
            xml_string, '4.00', 'CstmrCdtTrfInitn/GrpHdr/CtrlSum')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/GrpHdr/InitgPty')

        # 'PmtInf' section.
        self.assertXPathNodeCount(xml_string, 1, 'CstmrCdtTrfInitn/PmtInf')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtInfId')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtMtd')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/BtchBookg')
        self.assertXPathNodeText(
            xml_string, 'false', 'CstmrCdtTrfInitn/PmtInf/BtchBookg')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/NbOfTxs')
        self.assertXPathNodeText(
            xml_string, '3', 'CstmrCdtTrfInitn/PmtInf/NbOfTxs')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/CtrlSum')
        self.assertXPathNodeText(
            xml_string, '4.00', 'CstmrCdtTrfInitn/PmtInf/CtrlSum')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtTpInf')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtTpInf/SvcLvl')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtTpInf/SvcLvl/Cd')
        self.assertXPathNodeText(
            xml_string, 'SEPA', 'CstmrCdtTrfInitn/PmtInf/PmtTpInf/SvcLvl/Cd')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtTpInf/LclInstrm')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/PmtTpInf/LclInstrm/Cd')
        self.assertXPathNodeText(
            xml_string, 'ACCEPT',
            'CstmrCdtTrfInitn/PmtInf/PmtTpInf/LclInstrm/Cd')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/ReqdExctnDt')
        self.assertXPathNodeText(
            xml_string, (self.today + relativedelta(days=5)).strftime(
                '%Y-%m-%d'),
            'CstmrCdtTrfInitn/PmtInf/ReqdExctnDt')

        # The 'debtor' 'Dbtr' subsection.
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/Dbtr')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/Dbtr/Nm')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['NAME'],
            'CstmrCdtTrfInitn/PmtInf/Dbtr/Nm')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/Dbtr/PstlAdr')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/Dbtr/PstlAdr/Ctry')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['COUNTRY'],
            'CstmrCdtTrfInitn/PmtInf/Dbtr/PstlAdr/Ctry')
        self.assertXPathNodeCount(
            xml_string, 2, 'CstmrCdtTrfInitn/PmtInf/Dbtr/PstlAdr/AdrLine')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['STREET_NUMBER'],
            'CstmrCdtTrfInitn/PmtInf/Dbtr/PstlAdr/AdrLine')

        # The 'DbtrAcct' section.
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAcct')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAcct/Id')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAcct/Id/IBAN')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['IBAN'],
            'CstmrCdtTrfInitn/PmtInf/DbtrAcct/Id/IBAN')

        # The 'DbtrAgt' section.
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAgt')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/BIC')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['BIC'],
            'CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/BIC')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/UltmtDbtr')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrCdtTrfInitn/PmtInf/UltmtDbtr/Nm')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['ULTIMATE_DEBTOR'],
            'CstmrCdtTrfInitn/PmtInf/UltmtDbtr/Nm')

        # The 'CdtTrfTxInf' sections. We have 3 transactions, so...
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/PmtId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/PmtId/EndToEndId')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Amt')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Amt/InstdAmt')
        self.assertXPathNodeAttributes(
            xml_string, {'Ccy': 'EUR'},
            'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Amt/InstdAmt')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAgt')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAgt/FinInstnId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAgt/FinInstnId/BIC')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Cdtr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAcct')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAcct/Id')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAcct/Id/IBAN')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/RmtInf')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/RmtInf/Ustrd')

    @patch('cc3.cyclos.backends.get_account_status')
    def test_sepa_xml_export_debit(self, mock):
        """
        Tests exporting of the SEPA direct debit data to XML
        """
        LOG.warning("Info: SEPA test 17. test_sepa_xml_export_debit: ")
        account_status_1 = MagicMock()
        account_status_2 = MagicMock()
        account_status_3 = MagicMock()
        account_status_1.accountStatus.balance = Decimal('-200.000000')
        account_status_2.accountStatus.balance = Decimal('-50.000000')
        account_status_3.accountStatus.balance = Decimal('-150.000000')
        mock.side_effect = [
            account_status_1,
            account_status_2,
            account_status_3
        ]

        exporter = SEPAExporter(date_from=self.initial, date_to=self.today)

        xml_string = exporter.build_direct_debit_xml()
        # Remove the 'xlmns' attribute, which is stopping us when trying to
        # retrieve any XML element.
        xml_string = re.sub('xmlns="[^"]+"', '', xml_string)

        # 'CstmrDrctDbtInitn', from the SEPA standard XML pain.008.001.02.
        self.assertXPathNodeCount(xml_string, 1, 'CstmrDrctDbtInitn')

        # The SEPA header.
        self.assertXPathNodeCount(xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr/MsgId')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr/CreDtTm')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr/NbOfTxs')
        self.assertXPathNodeText(
            xml_string, '3', 'CstmrDrctDbtInitn/GrpHdr/NbOfTxs')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr/CtrlSum')
        self.assertXPathNodeText(
            xml_string, '4.00', 'CstmrDrctDbtInitn/GrpHdr/CtrlSum')
        self.assertXPathNodeCount(
            xml_string, 1, 'CstmrDrctDbtInitn/GrpHdr/InitgPty')

        # 'PmtInf' section.
        self.assertXPathNodeCount(xml_string, 3, 'CstmrDrctDbtInitn/PmtInf')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtInfId')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtMtd')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/BtchBookg')
        self.assertXPathNodeText(
            xml_string, 'false', 'CstmrDrctDbtInitn/PmtInf/BtchBookg')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/NbOfTxs')
        self.assertXPathNodeText(
            xml_string, '1', 'CstmrDrctDbtInitn/PmtInf/NbOfTxs')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CtrlSum')
        self.assertXPathNodeText(
            xml_string, '2.00', 'CstmrDrctDbtInitn/PmtInf/CtrlSum')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/SvcLvl')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/SvcLvl/Cd')
        self.assertXPathNodeText(
            xml_string, 'SEPA', 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/SvcLvl/Cd')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/LclInstrm')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/LclInstrm/Cd')
        self.assertXPathNodeText(
            xml_string, 'CORE',
            'CstmrDrctDbtInitn/PmtInf/PmtTpInf/LclInstrm/Cd')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/PmtTpInf/SeqTp')
        self.assertXPathNodeText(
            xml_string, 'FRST',
            'CstmrDrctDbtInitn/PmtInf/PmtTpInf/SeqTp')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/ReqdColltnDt')
        self.assertXPathNodeText(
            xml_string, (self.today + relativedelta(days=5)).strftime(
                '%Y-%m-%d'),
            'CstmrDrctDbtInitn/PmtInf/ReqdColltnDt')

        # The 'creditor' 'Cdtr' subsection.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/Cdtr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/Cdtr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/Cdtr/Nm')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['CREDITOR']['NAME'],
            'CstmrDrctDbtInitn/PmtInf/Cdtr/Nm')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/Cdtr/PstlAdr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/Cdtr/PstlAdr/Ctry')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['CREDITOR']['COUNTRY'],
            'CstmrDrctDbtInitn/PmtInf/Cdtr/PstlAdr/Ctry')
        self.assertXPathNodeCount(
            xml_string, 6, 'CstmrDrctDbtInitn/PmtInf/Cdtr/PstlAdr/AdrLine')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['CREDITOR']['STREET_NUMBER'],
            'CstmrDrctDbtInitn/PmtInf/Cdtr/PstlAdr/AdrLine')

        # The 'CdtrAcct' subsections.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAcct')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAcct/Id')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAcct/Id/IBAN')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['CREDITOR']['IBAN'],
            'CstmrDrctDbtInitn/PmtInf/CdtrAcct/Id/IBAN')

        # The 'CdtrAgt' subsections.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAgt')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAgt/FinInstnId')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrAgt/FinInstnId/BIC')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['BIC'],
            'CstmrDrctDbtInitn/PmtInf/CdtrAgt/FinInstnId/BIC')

        # The 'UltmtCdtr' subsections.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/UltmtCdtr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/UltmtCdtr/Nm')
        self.assertXPathNodeText(
            xml_string, settings.SEPA_SETTINGS['DEBTOR']['ULTIMATE_DEBTOR'],
            'CstmrDrctDbtInitn/PmtInf/UltmtCdtr/Nm')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/ChrgBr')
        self.assertXPathNodeText(
            xml_string, 'SLEV',
            'CstmrDrctDbtInitn/PmtInf/ChrgBr')

        # The 'CdtrSchmeId' subsections.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId/Othr')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId/Othr/Id')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId/Othr/SchmeNm')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId/Othr/SchmeNm/Prtry')
        self.assertXPathNodeText(
            xml_string, 'SEPA',
            'CstmrDrctDbtInitn/PmtInf/CdtrSchmeId/Id/PrvtId/Othr/SchmeNm/Prtry')

        # The 'DrctDbtTxInf' subsections.
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/PmtId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/PmtId/EndToEndId')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/InstdAmt')
        self.assertXPathNodeAttributes(
            xml_string, {'Ccy': 'EUR'},
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/InstdAmt')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DrctDbtTx')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DrctDbtTx/MndtRltdInf')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DrctDbtTx/MndtRltdInf/'
            'MndtId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DrctDbtTx/MndtRltdInf/'
            'DtOfSgntr')
        self.assertXPathNodeText(
            xml_string, self.today.strftime('%Y-%m-%d'),
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DrctDbtTx/MndtRltdInf/'
            'DtOfSgntr')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAgt')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAgt/FinInstnId')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAgt/FinInstnId/BIC')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/Dbtr')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/Dbtr/Nm')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAcct')
        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAcct/Id')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/DbtrAcct/Id/IBAN')

        self.assertXPathNodeCount(
            xml_string, 3, 'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/RmtInf')
        self.assertXPathNodeCount(
            xml_string, 3,
            'CstmrDrctDbtInitn/PmtInf/DrctDbtTxInf/RmtInf/Ustrd')
