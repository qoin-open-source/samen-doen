from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core import mail
from django.db.models.signals import post_save
from django.test import TestCase
from django.test.utils import override_settings
# from django.utils.translation import ugettext as _

from mock import MagicMock, patch, ANY

from cc3.core.utils.test_backend import DummyCyclosBackend
from cc3.cyclos.common import Transaction, TransactionException
from cc3.cyclos.models import User
from cc3.cyclos.services import MemberNotFoundException
from cc3.cyclos.tests.test_factories import MailMessageFactory
from cc3.cyclos.backends import set_backend
from cc3.invoices.models import Invoice, InvoiceLine
from cc3.invoices.tests.test_factories import PaymentStatusFactory
from cc3.mail.models import MAIL_TYPE_MONTHLY_INVOICE, MailMessage
from cc3.rewards.models import BusinessCauseSettings

from ..models import BusinessProfile, link_business_account
from ..utils import SignalContextManager
from .test_factories import BusinessProfileFactory, CharityProfileFactory


class BusinessProfileTestCase(TestCase):
    def setUp(self):
        set_backend(DummyCyclosBackend())

        self.good_cause = CharityProfileFactory.create()
        self.business = BusinessProfileFactory.create()
        MailMessage.objects.all().delete()  # why is this needed??
        self.invoice_email = MailMessageFactory.create(
            type=MAIL_TYPE_MONTHLY_INVOICE,
            subject="Monthly invoice")

    def test_business_cause_settings_created(self):
        """
        Tests that a ``BusinessCauseSettings`` object is created for every new
        ``BusinessProfile`` by default.
        """
        with SignalContextManager(
                post_save, receiver=link_business_account,
                sender=BusinessProfile,
                dispatch_uid='icare4u_business_profile_save'):
            business_profile = BusinessProfileFactory.create()

        cause_settings = BusinessCauseSettings.objects.all()
        self.assertGreater(len(cause_settings), 0)

        cause_settings = BusinessCauseSettings.objects.latest('pk')
        self.assertEqual(cause_settings.user, business_profile.profile.user)

    # @skip('CharityProfile does not have reset balance function,
    # so this test is invalid now')
    # def test_reset_balance_assert_not_charity(self):
    #     """
    #     Tests the sanity check to avoid resetting charities balance in
    #     ``reset_balance`` method.
    #     """
    #     self.assertRaisesMessage(
    #         AssertionError,
    #         u'{0} is a charity. This method cannot be used with it'.format(
    #             self.good_cause.profile),
    #         self.good_cause.reset_balance)

    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.from_system_payment')
    @override_settings(SEPA_EXPORT_DEBIT_TRANSFER_TYPE_ID=None,
                       SEPA_EXPORT_DEBIT_TRANSFER_DESCRIPTION=None)
    def test_reset_balance_debit_settings(
            self, mock_from_system_payment, mock_get_account_status):
        """
        Tests auto-fallback to predefined settings when debit settings are not
        available in Django project.
        """
        # Delete the relevant settings. Now they are missing. `reset_balance`
        # method must be aware of this situation and set everything up to a
        # default values.
        del settings.SEPA_EXPORT_DEBIT_TRANSFER_DESCRIPTION
        del settings.SEPA_EXPORT_DEBIT_TRANSFER_TYPE_ID

        # Mock the Cyclos account balance to return a negative value (so, a
        # debit operation must be performed).
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('-150.000000')
        mock_get_account_status.return_value = account_status

        # Execute the `reset_balance` method.
        self.business.reset_balance()

        # Now check that the `backends.from_system_payment` method was called
        # with the correct params - so the `reset_balance` method set up all
        # the missing settings.
        mock_from_system_payment.assert_called_with(
            self.business.profile.user.username, Decimal('150.00'),
            "Bijschrijving na automatisch incasso", transfer_type_id=39)

    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    @override_settings(SEPA_EXPORT_CREDIT_TRANSFER_TYPE_ID=None,
                       SEPA_EXPORT_CREDIT_TRANSFER_DESCRIPTION=None)
    def test_reset_balance_credit_settings(
            self, mock_to_system_payment, mock_get_account_status):
        """
        Tests auto-fallback to predefined settings when credit settings are not
        available in Django project.
        """
        # Delete the relevant settings. Now they are missing. `reset_balance`
        # method must be aware of this situation and set everything up to a
        # default values.
        del settings.SEPA_EXPORT_CREDIT_TRANSFER_DESCRIPTION
        del settings.SEPA_EXPORT_CREDIT_TRANSFER_TYPE_ID

        # Mock the Cyclos account balance to return a positive value (so, a
        # credit operation must be performed).
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        # Execute the `reset_balance` method.
        self.business.reset_balance()

        # Now check that the `backends.from_system_payment` method was called
        # with the correct params - so the `reset_balance` method set up all
        # the missing settings.
        mock_to_system_payment.assert_called_with(
            self.business.profile.user.username, Decimal('150.00'),
            "Afschrijving na automatisch incasso", transfer_type_id=36)

    @patch('icare4u_front.profile.models.LOG.error')
    @patch('cc3.cyclos.backends.get_account_status')
    def test_reset_balance_missing_cyclos_user(
            self, mock_get_account_status, mock_log):
        """
        Tests the ``reset_balance`` method to make sure it returns ``None``,
        after an ``INFO`` message, if the user was missing in Cyclos database.
        """
        mock_get_account_status.side_effect = MemberNotFoundException

        self.assertFalse(self.business.reset_balance())
        mock_log.assert_called_with(
            u'Member not found (in Cyclos): {0}'.format(
                self.business.profile.user.username))

    @patch('icare4u_front.profile.models.LOG.error')
    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    def test_reset_balance_transaction_exception(
            self, mock_to_system_payment, mock_get_account_status, mock_log):
        """
        Tests the ``reset_balance`` method returns ``None``, after an ``INFO``
        message, if the transaction gets a ``TransactionException`` as a result
        """
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        mock_to_system_payment.side_effect = TransactionException

        self.assertFalse(self.business.reset_balance())
        mock_log.assert_called_with(
            u'Unable to perform balance reset. The transaction failed: {0}\n'
            u'Sure the user is a business?'.format(''))

    @patch('icare4u_front.profile.models.LOG.error')
    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    def test_reset_balance_no_payment_status(
            self, mock_to_system_payment, mock_get_account_status, mock_log):
        """
        Tests returning ``False`` when there are no active ``PaymentStatus``
        objects.
        """
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock_to_system_payment.return_value = Transaction(
            sender=self.business.profile.user,
            recipient=None,
            amount=Decimal('150.00'),
            created=datetime.now(),
            description='test_payment',
            transfer_id=36
        )

        self.assertTrue(self.business.reset_balance())
        # Payment status is created on-the-fly

    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    @override_settings(SEND_SEPA_MONTHLY_RESET_INVOICE=False)
    def test_reset_balance_credit_invoices_creation(
            self, mock_to_system_payment, mock_get_account_status):
        """
        Test creation of ``Invoice`` and ``InvoiceLine`` after a credit
        operation, and that invoice email is NOT sent.
        """
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock_to_system_payment.return_value = Transaction(
            sender=self.business.profile.user,
            recipient=None,
            amount=Decimal('150.00'),
            created=datetime.now(),
            description='test_payment',
            transfer_id=36
        )

        # Create a `PaymentStatus` instance
        PaymentStatusFactory.create(is_paid=False)

        self.assertTrue(self.business.reset_balance())

        # Check `Invoice` and `InvoiceLine`.
        invoice = Invoice.objects.latest('pk')
        # This also checks if the 'system user' was successfully created in the
        # absence of a predefined one.
        system_user = User.objects.get(username='Positoos Reserve')

        self.assertEqual(invoice.from_user, system_user)
        self.assertEqual(invoice.to_user, self.business.profile.user)

        invoice_line = InvoiceLine.objects.latest('pk')

        self.assertEqual(invoice_line.invoice, invoice)
        # Amount is in EUR and is a credit invoice, so / 100 * -1.0
        self.assertEqual(invoice_line.amount, Decimal('-1.5000'))
        # VAT rate has been set to 0 for the time being
        self.assertEqual(invoice_line.tax_rate, 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    @override_settings(SEND_SEPA_MONTHLY_RESET_INVOICE=True)
    def test_reset_balance_credit_invoices_creation_sends_email(
            self, mock_to_system_payment, mock_get_account_status):
        """
        Test creation of ``Invoice`` and ``InvoiceLine`` after a credit
        operation, and that invoice email is sent.
        """
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock_to_system_payment.return_value = Transaction(
            sender=self.business.profile.user,
            recipient=None,
            amount=Decimal('150.00'),
            created=datetime.now(),
            description='test_payment',
            transfer_id=36
        )

        # Create a `PaymentStatus` instance
        PaymentStatusFactory.create(is_paid=False)

        self.assertTrue(self.business.reset_balance())

        # Check `Invoice` and `InvoiceLine`.
        invoice = Invoice.objects.latest('pk')
        # This also checks if the 'system user' was successfully created in the
        # absence of a predefined one.
        system_user = User.objects.get(username='Positoos Reserve')

        self.assertEqual(invoice.from_user, system_user)
        self.assertEqual(invoice.to_user, self.business.profile.user)

        invoice_line = InvoiceLine.objects.latest('pk')

        self.assertEqual(invoice_line.invoice, invoice)
        # Amount is in EUR and is a credit invoice, so / 100 * -1.0
        self.assertEqual(invoice_line.amount, Decimal('-1.5000'))
        # VAT rate has been set to 0 for the time being
        self.assertEqual(invoice_line.tax_rate, 0)
        self.assertIn("Monthly invoice", mail.outbox[0].subject)

    @patch('cc3.cyclos.backends.get_account_status')
    @patch('cc3.cyclos.backends.to_system_payment')
    @patch('cc3.invoices.models.InvoiceLine.objects.create')
    @override_settings(VAT_RATE=None)
    def test_reset_balance_invoicing_settings(
            self, mock_invoice_line, mock_to_system_payment,
            mock_get_account_status):
        """
        Tests auto-fallback to predefined settings when VAT settings are not
        available in Django project.
        """
        # Delete the relevant settings. Now they are missing. `reset_balance`
        # method must be aware of this situation and set everything up to a
        # default values.
        del settings.VAT_RATE

        # Mock the Cyclos account balance to return a positive value (so, a
        # credit operation must be performed).
        account_status = MagicMock()
        account_status.accountStatus.balance = Decimal('150.000000')
        mock_get_account_status.return_value = account_status

        # Mock the ``user_payment`` method to avoid hitting Cyclos backend and
        # still have an expected nice response from it.
        mock_to_system_payment.return_value = Transaction(
            sender=self.business.profile.user,
            recipient=None,
            amount=Decimal('150.00'),
            created=datetime.now(),
            description='test_payment',
            transfer_id=36
        )

        # Create a `PaymentStatus` instance
        PaymentStatusFactory.create(is_paid=False)

        # Execute the `reset_balance` method.
        self.business.reset_balance()

        # Now check that the `backends.from_system_payment` method was called
        # with the correct params - so the `reset_balance` method set up all
        # the missing settings.
        invoice = Invoice.objects.latest('pk')
        mock_invoice_line.assert_called_with(
            invoice=invoice,
            quantity=1,
            description=ANY,
            amount=Decimal('-1.500'),
            tax_rate=0)
