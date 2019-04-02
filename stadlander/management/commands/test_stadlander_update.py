import logging

from django.core.management.base import BaseCommand, CommandError
from icare4u_front.stadlander.utils import update_stadlander_status

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
    help = 'Test SOAP call to make Stadlander user active / inactive (DISABLED)'

    def handle(self, *args, **options):
        error = None

        print 'disabled'

#        LOG.info(u'Test SOAP call to make Stadlander user active or inactive')
#
#        try:
#            update_stadlander_status('91165', "True")
#        except Exception, e:
#            print e
