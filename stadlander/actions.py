import json
import logging

from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
from cc3.rewards.transactions import cause_reward
from cc3.rules.models import Rule

from .models import StadlanderProfile

LOG = logging.getLogger(__name__)


def jsonify(*args, **kwargs):
    return json.dumps((args, kwargs))  # Tuples are faster to create


class PayStadlander(object):

    @staticmethod
    def perform(*args, **kwargs):
        # does an active SSO person exist for personnumber == relnumber?
        LOG.info(u"Action PayStadlander perform called with {0} ".format(
            jsonify(args, kwargs)))

        sso_profile = None
        try:
            sso_profile = StadlanderProfile.objects.get(
                rel_number=kwargs['persoonsnummer'],
                profile__user__is_active=True
            )
        except StadlanderProfile.DoesNotExist:
            LOG.error(
                u'PayStadlander failed. '
                u'Persoonsnummer {0} does not have a StadlanderProfile.'.format(
                    kwargs['persoonsnummer']))
            kwargs['payment'] = \
                u'PayStadlander action failed, Persoonsnummer {0} does not ' \
                u'have a StadlanderProfile.'.format(kwargs['persoonsnummer'])
            kwargs['cause_payment'] = \
                u'PayStadlander actionfailed, Persoonsnummer {0} does not ' \
                u'have a StadlanderProfile.'.format(kwargs['persoonsnummer'])
        except Exception, e:
            LOG.error(e)
            kwargs['payment'] = \
                u'PayStadlander action failed, Unexpected error {0}.'.format(e)
            kwargs['cause_payment'] = \
                u'PayStadlander action failed, Unexpected error {0}.'.format(e)

        if sso_profile:
            description = kwargs.get('description', None)
            if not description:
                rule = Rule.objects.get(pk=kwargs['rule_id'])
                description = u"{0} ({1})".format(rule.description, rule.name)

            transaction = None
            amount = int(kwargs['amount'])
            receiver_user = sso_profile.profile.user
            receiver = receiver_user.username
            try:
                transaction = backends.user_payment(
                    kwargs['sender'], receiver, amount, description)

                kwargs['payment'] = u'success'
            except TransactionException as e:
                LOG.warning(u'Unable to perform the stadlander reward '
                            u'transaction: {0}'.format(e))
                kwargs['payment'] = u'failed {0}'.format(e)

            try:
                if transaction:
                    cause_reward(amount, receiver_user, transaction.transfer_id)
                    kwargs['cause_payment'] = u'success'
                else:
                    LOG.error(
                        u'Donation in action PayStadlander failed. '
                        u'Stadlander Reward payment failed.'.format(
                            receiver_user))
                    kwargs['cause_payment'] = \
                        u'failed, User {0} Stadlander Reward payment ' \
                        u'failed.'.format(receiver_user)
            except Exception, e:
                LOG.error(
                    u'Donation in action PayStadlander failed. '
                    u'User {0} is not committed with any cause.'.format(
                        sso_profile.profile.user.pk))
                kwargs['cause_payment'] = \
                    u'failed, User {0} is not committed with any ' \
                    u'cause.'.format(receiver_user)

        return jsonify(args, kwargs)
