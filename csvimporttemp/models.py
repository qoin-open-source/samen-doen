import datetime

import logging

from django.core.exceptions import ValidationError
from django.db import models

LOG = logging.getLogger(__name__)


def can_save(instance):
    from ..stadlander.models import StadlanderProfile

    try:
        StadlanderProfile.objects.get(rel_number=instance.persoonsnummer)
        return True
    except StadlanderProfile.DoesNotExist:
        pass
    except Exception, e:
        LOG.error(e)

    return False


class Huurcontract(models.Model):
    contractnummer = models.CharField(max_length=20)
    vestigingnummer = models.IntegerField()
    vhenummer = models.CharField(max_length=20, blank=True, default='')
    persoonsnummer = models.CharField(max_length=20, blank=True, default='')
    ingangsdatum = models.DateField(null=True, blank=True)
    einddatum = models.DateField(null=True, blank=True)
    incassowijze = models.CharField(max_length=1, blank=True, default='')
    huurprijs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    huurstand = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    WSNP = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bedrag_eind_afrekening = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    datum_eind_afrekening = models.DateField(null=True, blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return u"Huurcontract: persoonsnummer {0}".format(self.persoonsnummer)

    @property
    def ingangsdatum_first_of_month(self):
        return datetime.date(
            self.ingangsdatum.year, self.ingangsdatum.month, 1)

    # Is there a lambda (?) way of doing this?
    @property
    def old_einddatum(self):
        try:
            old_huurcontract = self.children.all().order_by('-einddatum')[0]
            return_value = old_huurcontract.einddatum
        except IndexError:  # Huurcontract.DoesNotExist:
            return None

        return return_value

    @property
    def old_huurprijs(self):
        try:
            old_huurcontract = self.children.all().order_by('-einddatum')[0]
            return_value = old_huurcontract.huurprijs
        except IndexError:  # Huurcontract.DoesNotExist:
            return None

        return return_value

    @property
    def old_datum_eind_afrekening(self):
        try:
            old_huurcontract = self.children.all().order_by('-einddatum')[0]
            return_value = old_huurcontract.datum_eind_afrekening
        except IndexError:  # Huurcontract.DoesNotExist:
            return None

        return return_value

    @property
    def old_bedrag_eind_afrekening(self):
        try:
            old_huurcontract = self.children.all().order_by('-einddatum')[0]
            return_value = old_huurcontract.bedrag_eind_afrekening
        except IndexError:  # Huurcontract.DoesNotExist:
            return None

        return return_value

    @property
    def huurprijs_delta(self):
        # Calculate difference between parent and child[0] huurprijs (rent)

        # get children - use most recent one
        try:
            old_huurcontract = self.children.all().order_by('-einddatum')[0]
            delta = self.huurprijs - old_huurcontract.huurprijs
        except IndexError:  # Huurcontract.DoesNotExist:
            return None

        return delta

    def handle_duplicates(self, existing_instances):
        # assumes > 0 count of existing_instances
        # find most recent ingangsdatum
        ordered_existing_instances = existing_instances.order_by(
            '-ingangsdatum')

        # most recent is 0, so use for comparison to find newest (ie parent)

        # treat the row with the most recent eingangdatum as the parent row
        if ordered_existing_instances[0].ingangsdatum > self.ingangsdatum:
            self.parent = ordered_existing_instances[0]
            self.save()
        else:
            # replace parents on existing instances as this one is newest
            for existing_instance in ordered_existing_instances:
                if existing_instance != self:
                    existing_instance.parent = self
                    existing_instance.save()

    def save(self, *args, **kwargs):
        if can_save(instance=self):
            super(Huurcontract, self).save(*args, **kwargs)


class Positoos(models.Model):
    vestigingnummer = models.IntegerField()
    persoonsnummer = models.CharField(max_length=20, blank=True, default='')
    klantrel_ingdat = models.DateField(null=True, blank=True)
    klantrel_einddat = models.DateField(null=True, blank=True)
    deelname_goudkaart = models.CharField(max_length=1, blank=True, default='')
    deelname_positoos = models.CharField(max_length=1, blank=True, default='')
    pasnummer = models.CharField(max_length=10)
    betaalregeling = models.CharField(max_length=1, blank=True, default='')
    overlastdossier = models.CharField(max_length=1, blank=True, default='')
    lid_bew_commissie = models.CharField(max_length=1, blank=True, default='')
    lid_klanten_panel = models.CharField(max_length=1, blank=True, default='')
    lid_vrijwilligerswerk = models.CharField(
        max_length=1, blank=True, default='')
    correspondentie_wijze = models.CharField(
        max_length=100, blank=True, default='')
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return u"Positoos: persoonsnummer {0}".format(self.persoonsnummer)

    def handle_duplicates(self, existing_instances):
        # assumes > 0 count of existing_instances
        # for existing_instance in existing_instances:
        if existing_instances[0] != self:
            self.parent = existing_instances[0]
            self.save()

    def save(self, *args, **kwargs):
        # check that model can be saved
        if can_save(instance=self):
            super(Positoos, self).save(*args, **kwargs)
