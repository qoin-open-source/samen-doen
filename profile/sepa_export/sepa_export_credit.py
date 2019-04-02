from datetime import date
from dateutil.relativedelta import relativedelta

from libcomxml.core import XmlField

from sepa import sepa19, sepa34


def credit_transaction(creditor, amount, amount_identifier):
    # <CdtTrfTxInf> definition
    transaction_info = sepa34.CreditTransferInfo()

    credit_amount = sepa34.Amount()
    credit_amount.instructed_amount = XmlField(
        'InstdAmt', value=amount, attributes={'Ccy': 'EUR'})
    # <PmtId> definition
    payment_identifier = sepa19.PaymentIdentifier()
    # <EndToEndId>
    payment_identifier.feed({'end_to_end_identifier': amount_identifier})

    # <FinInstnId> definition
    agent_id = sepa19.AgentIdentifier()
    agent_id.feed({'bic': creditor.bic_code})

    # <CdtrAgt> definition
    creditor_agent = transaction_info.creditor_agent
    creditor_agent.feed({'agent_identifier': agent_id})

    # <PstlAdr> definition
    creditor_address = sepa19.PostalAddress()
    creditor_address.feed({
        'country': creditor.profile.country,
        'address_line': '{0}, {1}, {2}, {3}'.format(
            creditor.profile.address, creditor.profile.postal_code,
            creditor.profile.city, creditor.profile.country)
    })

    # <Cdtr> definition
    transaction_creditor = transaction_info.creditor
    transaction_creditor.feed({
        'entity_name': creditor.profile.full_name.encode('ascii', 'replace'),
        'postal_address': creditor_address
    })

    # <CdtrAcct><IBAN> definition
    account_id = sepa19.AccountIdentification()
    account_id.feed({'iban': creditor.iban})

    # <CdtrAcct> definition
    creditor_account = transaction_info.creditor_account
    creditor_account.feed({'account_identification': account_id})

    # <RmtInf> definition
    concept = sepa19.Concept()
    concept.feed({'unstructured': 'Saldo verrekening Positoos'})

    transaction_fields = {
        # <PmtId> insertion
        'payment_identifier': payment_identifier,
        # <Amt> insertion
        'amount': credit_amount,
        # <CdtrAgt> insertion
        'creditor_agent': creditor_agent,
        # <Cdtr> insertion
        'creditor': transaction_creditor,
        # <CdtrAcct> insertion
        'creditor_account': creditor_account,
        # <RmtInf> insertion
        'concept': concept,
    }
    transaction_info.feed(transaction_fields)

    return transaction_info


def credit_payments_info(nr_operations, checksum, debtor_settings,
                         total_credit_transactions, description):
    payments_info = sepa34.PaymentInformation()

    service_level = sepa19.ServiceLevel()
    service_level.feed({'code': 'SEPA'})  # Fixed value.

    local_instrument = sepa19.LocalInstrument()
    local_instrument.feed({'code': 'ACCEPT'})  # Fixed value.

    # <PmtTpInf> definition
    payment_type_info = sepa19.PaymentTypeInfo()
    payment_type_info.feed({
        'service_level': service_level,
        'local_instrument': local_instrument,
    })

    # <Dbtr> definition
    debtor = payments_info.debtor
    address = sepa19.PostalAddress()
    address.feed({
        'country': debtor_settings['COUNTRY'],
        'address_line_1': debtor_settings['STREET_NUMBER'].encode(
            'ascii', 'replace'),
        'address_line_2': debtor_settings['POSTCODE_CITY']
    })
    debtor.feed({
        'entity_name': debtor_settings['NAME'].encode('ascii', 'replace'),
        'postal_address': address,
    })

    # <UltmtDbtr> definition
    ultimate_debtor = payments_info.ultimate_debtor
    ultimate_debtor.feed({
        'entity_name': debtor_settings['ULTIMATE_DEBTOR'].encode(
            'ascii', 'replace')
    })

    # <DbtrAcct> definition
    debtor_account = payments_info.debtor_account
    debtor_iban = debtor_account.account_identification
    debtor_iban.feed({'iban': debtor_settings['IBAN']})
    debtor_account.feed({'account_identification': debtor_iban})

    # <DebtrAgt> definition
    debtor_agent = payments_info.debtor_agent
    agent_identifier = debtor_agent.agent_identifier
    agent_identifier.feed({'bic': debtor_settings['BIC']})
    debtor_agent.feed({'agent_identifier': agent_identifier})

    payments_fields = {
        # <PmtInfId>
        'payment_info_identifier': description,
        # <PmtMtd>
        'payment_method': 'TRF',  # Fixed value.
        # <BtchBookg>
        'batchbook': 'false' if total_credit_transactions > 1 else 'true',
        # <NbOfTxs>
        'number_of_operations': nr_operations,
        # <CtrlSum>
        'checksum': checksum,
        # <PmtTpInf> insertion
        'payment_type_info': payment_type_info,
        # <ReqdColltnDt>
        'collection_date': (date.today() + relativedelta(days=5)).isoformat(),
        # <Dbtr> insertion
        'debtor': debtor,
        # <DbtrAcct> insertion
        'debtor_account': debtor_account,
        # <DbtrAgt> insertion
        'debtor_agent': debtor_agent,
        # <ChrgBr>
        'charge_clausule': 'SLEV',  # Fixed value.
        # <UltmtDbtr> insertion
        'ultimate_debtor': ultimate_debtor,
    }

    payments_info.feed(payments_fields)
    return payments_info
