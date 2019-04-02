# somewhere convenient to put the transaction signal handler
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from cc3.core.models import Transaction
from icare4u_front.loyaltylab.utils import notify_ll_user_transaction


LOG = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction,
          dispatch_uid='icare4u_notify_ll_of_transaction')
def notify_ll_of_transaction(sender, instance, created, **kwargs):
    """
    Notified Loyalty Lab of every transaction
    """
    LOG.info("notify_ll_of_transaction triggered {0}, created: {1}".format(
        unicode(instance), unicode(created)))
    # TODO: probably not _every_ transaction!

    if created:
        notify_ll_user_transaction()
