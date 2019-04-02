import logging

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from ...sepa_export import SEPAExporter, export_sepa_to_xml
from ...models import SEPAXMLFile

LOG = logging.getLogger(__name__)

from datetime import date, timedelta


def get_first_day(dt, d_years=0, d_months=0):
    # d_years, d_months are "deltas" to apply to dt
    y, m = dt.year + d_years, dt.month + d_months
    a, m = divmod(m-1, 12)
    return date(y+a, m+1, 1)


def get_last_day(dt):
    return get_first_day(dt, 0, 1) + timedelta(-1)


class Command(BaseCommand):
    help = 'Auto create SEPA XML files'

    def handle(self, *args, **options):
        error = None

        LOG.info(u'Auto create SEPA xml files')
        # get first and last days of the month
        # http://code.activestate.com/recipes/476197-first-last-day-of-the-month/#c1
        d = date.today()
        date_from = get_first_day(d, d_months=-1)
        date_to = get_last_day(date_from)

        # Instantiate the exporter.
        exporter = SEPAExporter(date_from, date_to)

        # Build the XML documents.
        try:
            credit_file_xml = export_sepa_to_xml(exporter, 'credit')
            LOG.info(u'Auto create SEPA xml files: credit file created')
            credit_file_name = "{0}_{1}.xml".format(
                date_from.isoformat(), 'credit')
            sepa_xml_file = SEPAXMLFile(
                file_type='credit',
                file_date=date_from,
                generated_date=d,
            )
            sepa_xml_file.file.save(
                credit_file_name, ContentFile(credit_file_xml))
            sepa_xml_file.save()
            LOG.info(u'Auto create SEPA xml files: credit file saved')
        except ValueError as e:
            error = unicode(e)

        try:
            debit_file_xml = export_sepa_to_xml(exporter, 'debit')
            LOG.info(u'Auto create SEPA xml files: debit file created')
            debit_file_name = "{0}_{1}.xml".format(
                date_from.isoformat(), 'debit')
            sepa_xml_file = SEPAXMLFile(
                file_type='debit',
                file_date=date_from,
                generated_date=d,
            )
            sepa_xml_file.file.save(
                debit_file_name, ContentFile(debit_file_xml))
            sepa_xml_file.save()
            LOG.info(u'Auto create SEPA xml files: debit file saved')
        except ValueError as e:
            error = unicode(e)

        if error:
            raise CommandError(error)
