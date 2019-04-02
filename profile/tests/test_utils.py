from django.test import TestCase

from mock import patch

from cc3.cyclos.tests.test_factories import UserFactory

from ..utils import generate_username, squeeze_email


class SqueezeEmailTestCase(TestCase):
    """
    Test case for the ``squeeze_email`` function.
    """
    def test_squeeze_email(self):
        """
        Tests the string returned by the function.

        - The string must be reduced to 30 characters.
        - The function must remove all non-alphanumeric characters.
        """
        value = squeeze_email('informative-address@icare4u-services.com')

        self.assertEqual(value, 'informativeaddressicare4user')


class GenerateUsernameTestCase(TestCase):
    """
    Test case for the ``generate_username`` function.
    """
    def setUp(self):
        self.user = UserFactory.create()

    @patch('cc3.cyclos.backends.search')
    def test_new_user_successful(self, mock):
        """
        Tests the function when a new username is given.
        """
        # Cyclos search for existent user will return empty result.
        mock.return_value = []

        value = generate_username('testuser')
        self.assertEqual(value, 'testuser')

    @patch('cc3.cyclos.backends.search')
    def test_new_user_exists_django(self, mock):
        """
        Tests the function for a username which was already registered in
        Django backend.
        """
        # Cyclos search for existent user will return empty result.
        mock.return_value = []

        value = generate_username(self.user.username)

        self.assertNotEqual(value, self.user.username)

        # Return value must contain the given username followed by 4 digits.
        self.assertIn(self.user.username, value)
        self.assertTrue(len(value), len(self.user.username) + 4)

    @patch('cc3.cyclos.backends.search')
    def test_new_user_exists_cyclos(self, mock):
        """
        Tests the function for a username which was already registered in
        Cyclos backend.
        """
        # Mocked Cyclos backend responses:
        # Cyclos search for existent user will return the username as result on
        # first iteration of the ``generate_username`` function and an empty
        # result on second iteration, as expected when the given username is
        # tweaked by the function to don't match any existent username.
        mock.side_effect = [
            [
                (
                    99,
                    'John Doe',
                    'info@maykinmedia.nl',
                    'infomaykinmedianl',
                    '12'
                )
            ],
            [],
        ]

        value = generate_username('infomaykinmedianl')

        self.assertNotEqual(value, 'infomaykinmedianl')

        # Return value must contain the given username followed by 4 digits.
        self.assertIn('infomaykinmedianl', value)
        self.assertTrue(len(value), len('infomaykinmedianl') + 4)
