import logging
import unittest

from django.test import TestCase

from ..utils import ll_list_instructions, ll_get_employee_data


class LoyaltyLabUtilsTestCase(TestCase):
    """Tests for util functions that interact with Loyalty Lab's SOAP service
    """
    def setUp(self):
        # turn off ridiculous amount of logging from pysimplesoap.simplexml
        logging.disable(logging.DEBUG)

    @unittest.skip("To be reviewed...")
    def test_list_instructions(self):
        """Test list_intsructions returns at least one"""
        instructions = ll_list_instructions()
        self.assertNotEqual(0, len(instructions))

    @unittest.skip("To be reviewed...")
    def test_employee_data(self):
        """Test employee data is returned"""
        salary, contract_end_date = ll_get_employee_data(
            name='Mickey Mouse',
            monthly_salary='3000',
            contract_start_date='2010-01-01',
        )
        self.assertEqual(salary, '36000')

