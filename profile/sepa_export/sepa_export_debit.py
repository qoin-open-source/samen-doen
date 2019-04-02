from datetime import date
from dateutil.relativedelta import relativedelta

from sepa import sepa19


def debit_transaction(debtor, amount, amount_identifier):
    # <DrctDbtTxInf> definition
    transaction_info = sepa19.DirectDebitOperationInfo()
    transaction_info.instructed_amount.attributes['Ccy'] = 'EUR'

    # <PmtId> definition
    payment_identifier = sepa19.PaymentIdentifier()
    # <EndToEndId>
    payment_identifier.feed({'end_to_end_identifier': amount_identifier})

    # <MndtRltdInf> definition
    mandate_information = sepa19.MandateInformation()
    mandate_information.feed({
        # <MndtId>
        'mandate_identifier': debtor.mandate_id,
        # <DtOfSgntr>
        'date_of_sign': debtor.signature_date.isoformat(),
    })

    # <DrctDbtTx> definition
    direct_debit_operation = sepa19.DirectDebitOperation()
    direct_debit_operation.feed({
        # <MndtRltdInf>
        'mandate_information': mandate_information
    })

    # <FinInstnId> definition
    agent_id = sepa19.AgentIdentifier()
    agent_id.feed({'bic': debtor.bic_code})

    # <DbtrAgt> definition
    debtor_agent = transaction_info.debtor_agent
    debtor_agent.feed({'agent_identifier': agent_id})

    # <PstlAdr> definition
    debtor_address = sepa19.PostalAddress()
    debtor_address.feed({
        'country': debtor.profile.country,
        'address_line': '{0}, {1}, {2}, {3}'.format(
            debtor.profile.address.encode('ascii', 'replace'),
            debtor.profile.postal_code,
            debtor.profile.city.encode('ascii', 'replace'),
            debtor.profile.country)
    })

    # <Dbtr> definition
    transaction_debtor = transaction_info.debtor
    transaction_debtor.feed({
        'entity_name': debtor.profile.full_name.encode('ascii', 'replace'),
        'postal_address': debtor_address
    })

    # <DbtrAcct><IBAN> definition
    account_id = sepa19.AccountIdentification()
    account_id.feed({'iban': debtor.iban})

    # <DbtrAcct> definition
    debtor_account = transaction_info.debtor_account
    debtor_account.feed({'account_identification': account_id})

    # <RmtInf> definition
    concept = sepa19.Concept()
    concept.feed({'unstructured': 'Saldo verrekening Positoos'})

    transaction_fields = {
        # <PmtId> insertion
        'payment_identifier': payment_identifier,
        # <InstdAmt> insertion
        'instructed_amount': amount,
        # <DrctDbtTx> insertion
        'direct_debit_operation': direct_debit_operation,
        # <DbtrAgt> insertion
        'debtor_agent': debtor_agent,
        # <Dbtr> insertion
        'debtor': transaction_debtor,
        # <DbtrAcct> insertion
        'debtor_account': debtor_account,
        # <RmtInf> insertion
        'concept': concept,
    }

    transaction_info.feed(transaction_fields)

    return transaction_info


def debit_payments_info(nr_operations, checksum,
                        creditor_settings, total_debit_transactions,
                        description='My Payment', payment_type='FRST'):
    service_level = sepa19.ServiceLevel()
    service_level.feed({'code': 'SEPA'})  # Fixed value.

    local_instrument = sepa19.LocalInstrument()
    local_instrument.feed({'code': 'CORE'})  # Fixed value.

    # <PmtTpInf> definition
    payment_type_info = sepa19.PaymentTypeInfo()
    payment_type_info.feed({
        'service_level': service_level,
        'local_instrument': local_instrument,
        'sequence_type': payment_type
    })

    # <SchmeNm> definition
    creditor_scheme_name = sepa19.SchemeName()
    creditor_scheme_name.feed({'propietary': 'SEPA'})

    payments_info = sepa19.PaymentInformation()

    # <Cdtr> definition
    creditor = payments_info.creditor
    address = sepa19.PostalAddress()
    address.feed({
        'country': creditor_settings['COUNTRY'],
        'address_line_1': creditor_settings['STREET_NUMBER'],
        'address_line_2': creditor_settings['POSTCODE_CITY']
    })
    creditor.feed({
        'name_name': creditor_settings['NAME'],
        'postal_address': address,
    })

    # <CdtrAcct> definition
    creditor_account = payments_info.creditor_account
    creditor_iban = creditor_account.account_identification
    creditor_iban.feed({'iban': creditor_settings['IBAN']})
    creditor_account.feed({'account_identification': creditor_iban})

    # <CdtrAgt> definition
    creditor_agent = payments_info.creditor_agent
    agent_identifier = creditor_agent.agent_identifier
    agent_identifier.feed({'bic': creditor_settings['BIC']})
    creditor_agent.feed({'agent_identifier': agent_identifier})

    # <UltmtCdtr> definition
    ultimate_creditor = payments_info.ultimate_creditor
    ultimate_creditor.feed({
        'entity_name': creditor_settings['ULTIMATE_CREDITOR']
    })

    # <CdtrSchmeId> definition
    creditor_id = payments_info.creditor_identifier
    identification = creditor_id.identification
    person = identification.physical_person
    other = person.other
    other.feed({
        'identification': creditor_settings['IDENTIFIER'],
        'scheme_name': creditor_scheme_name
    })
    person.feed({'other': other})
    identification.feed({'physical_person': person})
    creditor_id.feed({'identification': identification})

    payments_fields = {
        # <PmtInfId>
        'payment_info_identifier': description,
        # <PmtMtd>
        'payment_method': 'DD',  # Fixed value.
        # <BtchBookg>
        'batchbook': 'false' if total_debit_transactions > 1 else 'true',
        # <NbOfTxs>
        'number_of_operations': nr_operations,
        # <CtrlSum>
        'checksum': checksum,
        # <PmtTpInf> insertion
        'payment_type_info': payment_type_info,
        # <ReqdColltnDt>
        'collection_date': (date.today() + relativedelta(days=5)).isoformat(),
        # <Cdtr> insertion
        'creditor': creditor,
        # <CdtrAcct> insertion
        'creditor_account': creditor_account,
        # <CdtrAgt> insertion
        'creditor_agent': creditor_agent,
        # <ChrgBr>
        'charge_clausule': 'SLEV',  # Fixed value.
        # <UltmtCdtr> insertion
        'ultimate_creditor': ultimate_creditor,
        # <CdtrSchmeId> insertion
        'creditor_identifier': creditor_id,
    }

    payments_info.feed(payments_fields)

    return payments_info
