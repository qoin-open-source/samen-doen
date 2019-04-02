import re
from string import ascii_letters, digits

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.translation import get_language

from cms.models import Page

from cc3.accounts.utils import get_non_obvious_number
from cc3.cyclos import backends
from cc3.cyclos.models import User


class SignalContextManager(object):
    """
    Context manager to temporarily disconnect a model from a signal.

    Used in conjunction with the ``with`` Python keyword, it provides a simple
    way to disable signal reception for specified receivers.

    Example:
        ```
        with SignalContextManager(
                post_save, receiver=link_business_account,
                sender=BusinessProfile,
                dispatch_uid='icare4u_business_profile_save'):

            business_profile = BusinessProfile.save()
        ```

        In the previous example, the receiver function `link_business_account`
        was NOT triggered on saving the `BusinessProfile` model.
    """
    def __init__(self, signal, receiver=None, sender=None, dispatch_uid=None,
                 reconnect=True):
        """
        :param signal: The signal to be treated.
        :param receiver: The receiver function which will catch the signal.
        :param sender: The model which sends the signal.
        :param dispatch_uid: The dispatch UID to identify the signal (if any
        was defined).
        :param reconnect: If ``True``, the signal handler will be reconnected
        on context manager exit. If ``False``, it won't be reconnected ever.
        """
        self.signal = signal
        self.receiver = receiver
        self.sender = sender
        self.dispatch_uid = dispatch_uid
        self.reconnect = reconnect

    def __enter__(self):
        self.signal.disconnect(
            receiver=self.receiver,
            sender=self.sender,
            dispatch_uid=self.dispatch_uid,
            weak=False
        )

    def __exit__(self, type, value, traceback):
        if self.reconnect:
            self.signal.connect(
                receiver=self.receiver,
                sender=self.sender,
                dispatch_uid=self.dispatch_uid,
                weak=False
            )


def squeeze_email(email):
    """
    Creates a username by squeezing the given email from the user during
    registration process.
    """
    # Max length of username on cyclos side is 30 chars.
    # User won't ever know their generated username.
    username = slugify(email)[:30]
    username = "".join(
        [ch for ch in username if ch in (ascii_letters + digits)])

    return username


def generate_username(username):
    """
    Given a string ``username``, it queries the database to check if there
    is already a ``User`` with that username. If so, tries to generate a
    new username with a random number.

    It will repeat the process recursively, if necessary, until a unique
    username is set.
    """
    test_username = username.ljust(4, '0')

    # max cyclos username length is 30, so if recursing, then use max 26 chars
    # of username passed in with 4 digits, otherwise an invalid cyclos username
    # is generated
    try:
        User.objects.get(username=test_username)
        test_username = "{0}{1}".format(
            username[:26], get_non_obvious_number(number_digits=4))
        return generate_username(test_username)
    except User.DoesNotExist:
        # Check now the Cyclos backend, in search for existing
        # users with this username.
        if not backends.search(username=test_username):
            # Nice username for the new user. It doesn't exist in Django DB,
            # nor in Cyclos DB.
            return test_username
        else:
            # There was another previous user registered with this username in
            # Cyclos DB. Retry.
            test_username = "{0}{1}".format(
                username[:26], get_non_obvious_number(number_digits=4))
            return generate_username(test_username)


def generate_mandate_id(user):
    """
    Given a user, return a string with the format

    SDxxxxxx

    where xxxxxx is the zero padded auth_user id

    :param user:
    :return:
    """

    mandate_id = "{0}".format(user.id)
    return "SD{0}".format(mandate_id.zfill(6))


def is_default_email(email):
    """
    Return true if the provided email address ends with @example.org, false otherwise
    """
    return email.endswith('@example.org')


def is_default_firstname(firstname, user):
    """
        Return true if the provided firstname is equal to the one generated via the card registration workflow
        """
    if user is not None and hasattr(user, 'cc3_profile'):
        if user.cc3_profile is not None and hasattr(user.cc3_profile,
                                                    'community') and user.cc3_profile.community is not None:
            if firstname == user.cc3_profile.community.code:
                return True

    return False


def is_default_lastname(lastname, user):
    """
    Return true if the provided lastname is equal to the one generated via the card registration workflow
    """
    if user is not None and hasattr(user, 'cc3_profile'):
        if user.cc3_profile is not None and hasattr(user.cc3_profile, 'community') and user.cc3_profile.community is not None:
            # If the last name starts with 0 to 16 numbers and ends with the user's community
            # code, then it is the default user name which is also used as a lastname
            pat = r'^\d{{1,16}}{}$'.format(user.cc3_profile.community.code)
            p = re.compile(pat)

            if p.match(lastname) is not None:
                return True

    return False


def get_tandc_page_url():
    """
    Function to get the URL of the 'term-and-conditions' CMS page
    The actual reverse id is specified in the CMS_PAGE_REVERSE_IDS settings dictionary
    """
    return get_cms_page_url(settings.CMS_PAGE_REVERSE_IDS['terms-and-conditions'])


def get_cms_page_url(reverse_id):
    """
    Function to get the URL of a custom CMS page based on its reverse ID
    """
    try:
        # Get the page based on its reverse id. Reverse ids are dynamically set in Django CMS.
        # Retrieve the reverse id from settings.
        page = Page.objects.get(reverse_id=reverse_id, publisher_is_draft=False)
        url = page.get_absolute_url(language=get_language())
    except Page.DoesNotExist:
        url = ''
    return url
