# encoding: utf-8
import datetime

from django.test import TestCase

from .test_factories import (
    HuurcontractFactory, PositoosFactory, StadlanderProfileFactory)

from ..models import Huurcontract


class CsvImportTempTests(TestCase):
    def setUp(self):
        self.old_einddatum = datetime.date(2014, 5, 31)
        self.old_datum_eind_afrekening = datetime.date(2014, 3, 31)
        self.old_bedrag_eind_afrekening = 123
        self.huurprijs = 500
        self.old_huurprijs = 400
        self.huurprijs_delta = self.huurprijs - self.old_huurprijs
        self.stadlander_profile_1 = StadlanderProfileFactory.create(
            rel_number='12345'
        )
        self.huurcontract_1 = HuurcontractFactory.create(
            datum_eind_afrekening=self.old_datum_eind_afrekening,
            bedrag_eind_afrekening=self.old_bedrag_eind_afrekening,
            huurprijs=self.huurprijs,
            ingangsdatum=datetime.date(2014, 6, 1),
            persoonsnummer='12345'
        )
        self.huurcontract_1_old = HuurcontractFactory.create(
            bedrag_eind_afrekening=self.old_bedrag_eind_afrekening,
            datum_eind_afrekening=self.old_datum_eind_afrekening,
            huurprijs=self.old_huurprijs,
            ingangsdatum=datetime.date(2014, 5, 1),
            einddatum=self.old_einddatum,
            persoonsnummer='12345'
        )

        huurcontract_1s = Huurcontract.objects.filter(
            persoonsnummer='12345'
        )

        # relate the contracts
        self.huurcontract_1.handle_duplicates(huurcontract_1s)

        self.stadlander_profile_2 = StadlanderProfileFactory.create(
            rel_number='54321'
        )
        self.huurcontract_2 = HuurcontractFactory.create(
            bedrag_eind_afrekening=self.old_bedrag_eind_afrekening,
            datum_eind_afrekening=self.old_datum_eind_afrekening,
            ingangsdatum=datetime.date(2014, 6, 1),
            huurprijs=self.huurprijs,
            persoonsnummer='54321'
        )
        # Test whether this one has been created - save should prevent it as no
        # StadlanderProfile.
        self.huurcontract_3 = HuurcontractFactory.create(
            bedrag_eind_afrekening=self.old_bedrag_eind_afrekening,
            datum_eind_afrekening=self.old_datum_eind_afrekening,
            ingangsdatum=datetime.date(2014, 6, 1),
            huurprijs=self.huurprijs,
            persoonsnummer='22222'
        )
        self.positoos_1 = PositoosFactory.create(
            vestigingnummer=123,
            persoonsnummer='12345'
        )
        self.positoos_2 = PositoosFactory.create(
            vestigingnummer=123,
            persoonsnummer='22222'
        )

    def test_old_einddatum(self):
        """
        Test that old_einddatum returns the date set for the child contract
        """
        old_einddatum = self.huurcontract_1.old_einddatum

        self.assertEqual(old_einddatum, self.old_einddatum)

    def test_no_old_einddatum(self):
        """
        Test that old_einddatum returns None if no child contract
        """
        old_einddatum = self.huurcontract_2.old_einddatum

        self.assertEqual(old_einddatum, None)

    def test_old_huurprijs(self):
        """
        Test that old_huurprijs returns the rent for the child contract
        """
        old_huurprijs = self.huurcontract_1.old_huurprijs

        self.assertEqual(old_huurprijs, self.old_huurprijs)

    def test_no_old_huurprijs(self):
        """
        Test that old_huurprijs returns None if no child contract
        """
        old_huurprijs = self.huurcontract_2.old_huurprijs

        self.assertEqual(old_huurprijs, None)

    def test_old_datum_eind_afrekening(self):
        """
        Test that old_datum_eind_afrekening returns the date set for the child
        contract.
        """
        old_datum_eind_afrekening = self.huurcontract_1.old_datum_eind_afrekening

        self.assertEqual(
            old_datum_eind_afrekening, self.old_datum_eind_afrekening)

    def test_no_old_datum_eind_afrekening(self):
        """
        Test that old_datum_eind_afrekening returns None if no child contract.
        """
        old_datum_eind_afrekening = self.huurcontract_2.old_datum_eind_afrekening

        self.assertEqual(old_datum_eind_afrekening, None)

    def test_old_bedrag_eind_afrekening(self):
        """
        Test that old_bedrag_eind_afrekening returns the date set for the child
        contract.
        """
        old_bedrag_eind_afrekening = self.huurcontract_1.bedrag_eind_afrekening

        self.assertEqual(
            old_bedrag_eind_afrekening, self.old_bedrag_eind_afrekening)

    def test_no_old_bedrag_eind_afrekening(self):
        """
        Test that old_bedrag_eind_afrekening returns None if no child contract.
        NB old_bedrag_eind_afrekening is a calculated property, and can be None
        if no child contracts.
        """
        self.assertEqual(self.huurcontract_2.old_bedrag_eind_afrekening, None)

    def test_huurprijs_delta(self):
        """
        Test that huurprijs_delta returns the difference in huurprijs with the
        child contract.
        """
        huurprijs_delta = self.huurcontract_1.huurprijs_delta

        self.assertEqual(huurprijs_delta, self.huurprijs_delta)

    def test_no_huurprijs_delta(self):
        """
        Test that huurprijs_delta returns None if no child contract.
        """
        huurprijs_delta = self.huurcontract_2.huurprijs_delta

        self.assertEqual(huurprijs_delta, None)

    def test_missing_stadlander_profile(self):
        """
        Test that huurcontact or positoos instance is *not* saved if no
        StadlanderProfile with the rel_number.
        """
        self.assertEqual(self.huurcontract_3.pk, None)
        self.assertEqual(self.positoos_2.pk, None)

    def test_positoos_with_stadlander_profile(self):
        """
        Test that positoos instance is saved if there is a
        StadlanderProfile with the rel_number.
        """
        self.assertNotEqual(self.positoos_1.pk, None)
