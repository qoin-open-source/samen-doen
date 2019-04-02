"""
SEPA export module. Definition of classes and methods used to build a standard
ISO 20022 pain.008.001.02 and pain.001.001.03 XML documents.

Code browsing suggestion: XMLs are big and include a lot of different XML tags.
In order to know where each tag/variable is defined or set, you can search for
the XML tags in the code comments. The places where the Python SEPA library
classes are instantiated are commented as "definitions" and the places where
the values are actually added into the XML document are commented as
"insertions".
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal, getcontext
from cStringIO import StringIO

from sepa import sepa19, sepa34

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from cc3.cyclos import backends
from cc3.cyclos.services import MemberNotFoundException

import sepa_export_credit
import sepa_export_debit
from ..models import BusinessProfile

LOG = logging.getLogger(__name__)

COMMON_FIELDS = ['NAME', 'BIC', 'IBAN', 'IDENTIFIER',
                 'COUNTRY', 'STREET_NUMBER', 'POSTCODE_CITY']
CREDITOR_FIELDS = COMMON_FIELDS + ['ULTIMATE_CREDITOR']
DEBTOR_FIELDS = COMMON_FIELDS + ['ULTIMATE_DEBTOR']

getcontext().prec = 11


def export_sepa_to_xml(exporter, export_type):
    """
    Given a SEPAExporter and an export type, return the
    SEPA XML output.
    """
    xml_doc = StringIO()

    if export_type == 'debit':
        xml_doc.write(exporter.build_direct_debit_xml())
    else:
        xml_doc.write(exporter.build_direct_credit_xml())

    # Reconcile businesses balances before exiting.
    exporter.reset_businesses_balances()

    # Return the XML document as XML.
    data = xml_doc.getvalue()
    return data


class SEPAExporter(object):
    def __init__(self, date_from, date_to):
        # Sanity check for required fixed values data.
        self.settings = settings.SEPA_SETTINGS
        now = datetime.now()
        now = now.replace(microsecond=0)
        self.timestamp = now.isoformat()

        if 'INITIATING_BUSINESS' not in self.settings or \
                'END_TO_END_ID' not in self.settings:
            raise ImproperlyConfigured(
                'INITIATING_BUSINESS or END_TO_END_ID not defined in project '
                'settings.')

        for field in CREDITOR_FIELDS:
            if field not in self.settings['CREDITOR']:
                raise ImproperlyConfigured(
                    'CREDITOR {0} not defined in project settings.'.format(
                        field))

        for field in DEBTOR_FIELDS:
            if field not in self.settings['DEBTOR']:
                raise ImproperlyConfigured(
                    'DEBTOR {0} not defined in project settings.'.format(
                        field))

        self.description = u'{0} {1}'.format(
            self.settings['INITIATING_BUSINESS'], self.timestamp)

        if len(self.description) > 35:  # SEPA restriction
            raise ImproperlyConfigured(
                "Description length (initiating business + timestamp) is too "
                "long!")

        # Sanity check for dates.
        if date_to < date_from:
            LOG.error(u'Final date cannot be before initial date.')
            raise ValueError('Invalid dates passed to SEPA exporter.')

        self.end_to_end_id = u"{0} {1}".format(
            self.settings['END_TO_END_ID'], date_from.strftime('%m/%Y'))

        # Only process active businesses
        self.businesses = BusinessProfile.objects.exclude(
            profile__user__is_active=False)

        # Sanity check for businesses list.
        if not self.businesses:
            LOG.error(u'No business profiles available in database. '
                      u'No SEPA transfers can be exported.')
            raise ValueError('No business profiles available in database.')

        self.date_from = date_from
        self.date_to = date_to

        self.credit_transactions = {}
        self.debit_transactions = {
            'FRST': {},
            'RCUR': {},
        }

        self.total_debit_transactions = 0
        self.total_debit_transactions_rcur = 0
        self.total_credit_transactions = 0

        # Fill in all the data.
        self._classify_balances()

    def _classify_balances(self):
        """
        Given a couple of accepted dates and a queryset of all registered
        ``BusinessProfiles``, retrieves the balance for each business and
        classifies as currently debtors or creditors.

        This method is called during the class instantiation.
        """
        # only process businesses with account holder, IBAN, BIC, Mandate and
        # signature date filled in
        businesses_to_classify = self.businesses.exclude(
            iban__isnull=True).exclude(
            bic_code__isnull=True).exclude(mandate_id__isnull=True).exclude(
            signature_date__isnull=True).exclude(iban='').exclude(
            bic_code='').exclude(account_holder='')

        for business in businesses_to_classify:
            # ignore in case of exceptions
            available_balance = None

            try:
                available_balance = backends.get_account_status(
                    business.profile.user.username
                ).accountStatus.balance
            except MemberNotFoundException:
                LOG.error(u'Member not found (in Cyclos): {0}'.format(
                    business.profile.user.username))

            # Store the business and its balance in the correspondent group.

            # if current balance, ignore business
            if not available_balance:
                continue

            # Cast `available_balance` to `int` and deduct the amount of euros.
            euros = getattr(settings, 'CC3_CURRENCY_CONVERSION', 100)
            balance = Decimal(available_balance/euros).quantize(
                Decimal(10) ** -2)

            if balance > 0:
                self.credit_transactions[business] = balance
                self.total_credit_transactions += balance
            else:
                # Balances must always be positive.
                balance = -balance
                if not business.latest_payment_date:
                    self.debit_transactions['FRST'][business] = balance
                else:
                    self.debit_transactions['RCUR'][business] = balance
                    self.total_debit_transactions_rcur += balance
                self.total_debit_transactions += balance

                business.latest_payment_date = self.date_to
                business.save()
                # trigger balancing cyclos payment and invoice generation
                # could be via a signal, but i couldn't think of any reasons
                # for the overhead
                # update business balance to zero, and create invoice
                # business.sepa_export_credit_balance(balance)

    def _sepa_header(self, checksum, operations, initiating_business=None):
        """
        Builds the SEPA XML Group Header block.

        :param checksum: Integer representing the total amount of all
        operations to be transferred.
        :param operations: Integer representing the number of operations.
        :param initiating_business: String with the name of the company. If not
        provided, defaults to the one defined in settings.
        :return header: ``SepaHeader`` XmlModel object with the header data.
        """
        header = sepa19.SepaHeader()

        if not initiating_business:
            initiating_business = self.description

        header.initiating_party.feed({'entity_name': initiating_business})
        header_fields = {
            'message_id': uuid.uuid4().hex,
            'creation_date_time': datetime.today().isoformat(),
            'number_of_operations': operations,
            'checksum': checksum,
            'initiating_party': header.initiating_party,
        }

        header.feed(header_fields)

        return header

    def transaction_description(self, instance):
        return u"{0} - {1}".format(self.end_to_end_id, instance.id)

    #########################
    # SEPA DEBIT PAYMENTS ###
    #########################
    def _debit_transaction_info(self, debtor):
        """
        Builds the SEPA XML pain.008.001.02 Transaction Information block.

        :param debtor: The ``BusinessProfile`` object related with this
        transaction.
        :return transaction_info: ``DirectDebitOperationInfo`` XmlModel object
        with the transaction data.
        """
        amount = self.debit_transactions['FRST'].get(debtor)
        if not amount:
            amount = self.debit_transactions['RCUR'].get(debtor)

        return sepa_export_debit.debit_transaction(
            debtor, amount, self.transaction_description(debtor))

    def _debit_payments_info(self, payment_type='FRST', debtor=None):
        """
        Builds the SEPA XML pain.008.001.02 Payment Information block.

        :param payment_type: The type of SEPA payment. Can be one of: FRST,
        RCUR, FNAL or OOFF. By default, FRST.
        :return payments_info: ``PaymentInformation`` XmlModel object with the
        payment data.
        """
        if payment_type == 'FRST':
            operations = 1
            checksum = self.debit_transactions['FRST'].get(debtor)
        else:
            operations = len(self.debit_transactions['RCUR'])
            checksum = self.total_debit_transactions_rcur
        return sepa_export_debit.debit_payments_info(
            operations, checksum, self.settings['CREDITOR'],
            self.total_debit_transactions, self.description, payment_type)

    def build_direct_debit_xml(self):
        """
        Builds a SEPA XML ISO 20022 - pain.008.001.02 document.

        :return str(xml): The complete XML document, as a string object.
        """
        xml = sepa19.DirectDebitInitDocument()
        direct_debit = sepa19.DirectDebitInitMessage()

        # Document header.
        header = self._sepa_header(
            self.total_debit_transactions,
            len(self.debit_transactions['FRST']) + len(
                self.debit_transactions['RCUR']))

        # List container for all the payment info blocks <PmtInf>'s.
        global_payments_info = []

        # Generate all the 'FRST' sequence type payments.
        for debtor in self.debit_transactions['FRST'].keys():
            # 1) Create a FRST payment info block (without the transaction
            # info block on it).
            frst_payment_info = self._debit_payments_info(
                'FRST', debtor=debtor)
            # 2) Build the transaction info block <DrctDbtTxInf>.
            transaction_info = [self._debit_transaction_info(debtor)]
            # 3) Insert the transaction info block into the FRST payment info.
            frst_payment_info.feed({
                'direct_debit_operation_info': transaction_info
            })
            # 4) Append the payment info to the general list of payments in
            # the XML.
            global_payments_info += [frst_payment_info]

        # Now generate the 'RCUR' sequence type payments.
        # 1) Create the RCUR payments info block.
        rcur_payments_info = self._debit_payments_info('RCUR')
        rcur_transactions_info = []

        # 2) Build the transactions info block with all the payments included
        # <DrctDbtTxInf>.
        for debtor in self.debit_transactions['RCUR'].keys():
            rcur_transactions_info += [self._debit_transaction_info(debtor)]

        # 3) Insert the transactions info block into the RCUR payments info.
        # (Only if we had any).
        if rcur_transactions_info:
            rcur_payments_info.feed({
                'direct_debit_operation_info': rcur_transactions_info
            })
            # 4) Append the payments info to the general list of payments in
            # the XML.
            global_payments_info += [rcur_payments_info]

        data = {
            'sepa_header': header,
            'payment_information': global_payments_info
        }

        direct_debit.feed(data)
        xml.feed({
            'customer_direct_debit': direct_debit
        })

        xml.pretty_print = True
        xml.build_tree()

        return str(xml)

    ##########################
    # SEPA CREDIT PAYMENTS ###
    ##########################
    def build_direct_credit_xml(self):
        """
        Builds a SEPA XML ISO 20022 - pain.001.001.03 document.
        :return str(xml): The complete XML document, as a string object.
        """
        xml = sepa34.CustomerCreditTransferDocument()
        credit_ = sepa34.CustomerCreditTransfer()

        header = self._sepa_header(
            self.total_credit_transactions, len(self.credit_transactions))
        payments_info = self._credit_payments_info()

        transactions_info = []
        for creditor in self.credit_transactions.keys():
            transactions_info += [self._credit_transaction_info(creditor)]

        payments_info.feed({
            'credit_transfer_info': transactions_info
        })

        data = {
            'sepa_header': header,
            'payment_information': payments_info
        }

        credit_.feed(data)
        xml.feed({
            'customer_credit_transfer': credit_
        })

        xml.pretty_print = True
        xml.build_tree()

        return str(xml)

    def _credit_transaction_info(self, creditor):
        amount = self.credit_transactions.get(creditor)

        return sepa_export_credit.credit_transaction(
            creditor, amount, self.transaction_description(creditor))

    def _credit_payments_info(self):
        """
        Builds the SEPA XML pain.001.001.03 Payment Information block.

        :return payments_info: ``PaymentInformation`` XmlModel object with the
        payment data.
        """
        operations = len(self.credit_transactions)
        checksum = self.total_credit_transactions

        return sepa_export_credit.credit_payments_info(
            operations, checksum, self.settings['DEBTOR'],
            self.total_credit_transactions, self.description)

    def reset_businesses_balances(self):
        """
        Performs a ``BusinessProfile.reset_balance`` execution for any business
        in ``self.businesses``.

        WARNING: This must be ran *after* a successful SEPA export. Otherwise,
        the balances will be lost and a SEPA export operation cannot be tried
        again!
        """
        for business in self.businesses:
            business.reset_balance()
