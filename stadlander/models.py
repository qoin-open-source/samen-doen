# -*- coding: utf-8 -*-
import datetime
import json
import logging

from adminsortable.models import Sortable
from cc3.cyclos.models.account import account_closed_signal, CC3Profile

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import EmailMessage
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import get_language, ugettext_lazy as _

from cc3.cyclos.models import CC3Community
from cc3.excelexport.utils import generate_xls
from cc3.files.models import FileTypeSetRun
from cc3.mail.utils import send_mail_to
from cc3.mail.models import MAIL_TYPE_NEW_STADLANDER_REGISTRATION
from cc3.marketplace.models import Ad
from cc3.rules.models import RuleStatus, ActionStatus


from icare4u_front.csvimporttemp.models import Huurcontract
from icare4u_front.profile.models import UserProfile
from icare4u_front.stadlander.utils import update_stadlander_status

LOG = logging.getLogger(__name__)


class StadlanderProfile(models.Model):
    """
    Stadlander users (who login via Stadlander) are identified by 'rel_number'
    returned by the Stadlander 'SSO' mechanism.

    They need a CC3Profile (and possibly other project specific profiles) for
    marketplace and ads etc.
    """
    """ extra fields for Stadlander SSO """
    profile = models.OneToOneField('profile.UserProfile')

    rel_number = models.IntegerField()

    def __unicode__(self):
        return u"{0} ({1})".format(self.rel_number, self.profile)

    def send_signup_notifications(self):

        # send email to new Stadlander tenant
        language = get_language()
        context = {
            'cc3_system_name': getattr(
                settings, "CC3_SYSTEM_NAME", "SamenDoen"),
            'user_profile': self.profile
        }

        # provide both member and profile for backward compatibility
        send_mail_to(
            recipients=(self.profile,),
            mail_type=MAIL_TYPE_NEW_STADLANDER_REGISTRATION,
            language=language,
            context=context)


class CommunityWoonplaat(models.Model):
    """
    Model used for mapping incoming stad/woonplaats SSO data about a user to a
    qoinware community.
    """
    community = models.ForeignKey(CC3Community)
    woonplaat = models.CharField(
        max_length=255,
        help_text=_(u"Woonplaat (residence) received in the Stadlander SSO "
                    u"info"))

    class Meta:
        unique_together = ('community', 'woonplaat')
        ordering = ['community', 'woonplaat']


class RewardCategory(Sortable):
    """
    Categories available for Stadlander tenents to base their reward payments
    to other individuals
    """
    title = models.CharField(max_length=100, help_text=(
        _(u'Reward Category title')))
    description = models.CharField(
        max_length=255, help_text=(_(u'Reward Category description')))
    reward_first_ad = models.BooleanField(
        default=False, help_text=(_(u'If True, user gets a reward for their '
                                    u'first advert in this category')))
    active = models.BooleanField(
        default=True, help_text=_(u'Marks this Reward Category as active'))

    class Meta(Sortable.Meta):
        verbose_name = _(u'Stadlander specifieke categorieën')
        verbose_name_plural = _(u'stadlander specifieke categorieën')
        ordering = ('order', 'title')

    def __unicode__(self):
        return u'{0}'.format(self.title)


class AdRewardCategory(models.Model):
    ad = models.ForeignKey(Ad)
    reward_category = models.ForeignKey(RewardCategory)


@receiver(post_save, sender=FileTypeSetRun, dispatch_uid='cc3_files_process')
def process_file_process(sender, instance, created, **kwargs):
    """
    Once an upload of a file has been completed, run any necessary post
    processing of the file to save data to specified model instances.
    """
    if created:
        # moved to separate function so that it can be run
        # from the shell for testing purposes
        send_rule_results_via_email(instance)


def send_rule_results_via_email(instance):
    # generate report based on filetypesetrun and email
    headers = ['persoonsnummer', 'contractnummer', 'qoinware_username',
               'rule_name', 'reward', 'action_result']
    data = []

    rule_results_list = json.loads(instance.rule_results)
    for rule_results_item in rule_results_list:
        for rule_results_dict in rule_results_item:
            rule_status_list = []
            reward = 0
            persoonsnummer = rule_results_dict['identity']
            contractnummer = None
            try:
                stadlander_profile = StadlanderProfile.objects.get(
                    rel_number=persoonsnummer)
                stadlander_profile_username = stadlander_profile.profile.user.username
            except StadlanderProfile.DoesNotExist:
                stadlander_profile = None
                stadlander_profile_username = None
            except MultipleObjectsReturned:
                stadlander_profile = None
                stadlander_profile_username = "**--Multiple--**"

            if rule_results_dict['result']:
                rule_status = RuleStatus.objects.get(
                    pk=rule_results_dict['result'])
                rule = rule_status.rule

                if rule_status.content_type.model_class() == Huurcontract:
                    huurcontract = Huurcontract.objects.get(
                        pk=rule_status.object_id)
                    contractnummer = huurcontract.contractnummer
                # most hideous of hideous hacks. VERY SPECIFIC
                if len(rule.parameter_values.split(',')) > 1:
                    reward = rule.parameter_values.split(',')[1]
                try:
                    action_status = ActionStatus.objects.filter(
                        rule_status=rule_status
                    )[0].performed
                except Exception, e:
                    LOG.error(e)
                    action_status = ""

                rule_status_list += [
                    persoonsnummer, contractnummer,
                    stadlander_profile_username, rule.name,
                    reward, action_status]
            else:
                rule_status_list += [
                    persoonsnummer, contractnummer,
                    stadlander_profile_username, None,
                    reward, None]

            data.append(rule_status_list)
    LOG.debug(data)

    # add headers as the generate_xls function doesnt' do this...
    # TODO fix headers in generate_xls
    data.insert(0, headers)
    attachment = generate_xls(data, headers, 'UTF-8')
    attachment_filename = 'Report{0}.xls'.format(
        datetime.datetime.today().date()
    )
    email_addresses = instance.filetypeset.email_addresses.strip()
    if email_addresses:
        email_address_list = [x.strip() for x in email_addresses.split(',')]

        msg = EmailMessage(
            u'Rules report {0}'.format(datetime.datetime.today().date()),
            u'',
            settings.DEFAULT_FROM_EMAIL,
            email_address_list
        )

        msg.attach(attachment_filename, attachment.getvalue(),
                   'application/ms-excel')
        msg.send()

    # keep a file-based record of the report in case of email issues
    with open(settings.LOG_DIR.child(attachment_filename), "w") as xls_file:
        xls_file.write(attachment.getvalue())


class PotentialLinkFound(Exception):
    """Custom exception, thrown by authentication backend if non-SL
       user with matching email found
    """
    pass


@receiver(post_save, sender=StadlanderProfile,
          dispatch_uid='icare4u_stadlander_profile_create_user_email')
def email_stadlander_on_creation(sender, instance, created, **kwargs):
    """
    Emails a user for this ``StadlanderProfile`` when it is created.
    """
    if created:
        instance.send_signup_notifications()
        LOG.info("email_stadlander_on_creation DONE (%s)" % instance.pk)
        try:
            rel_number_str = "%s" % instance.rel_number
            LOG.info("update_stadlander_status (%s)" % rel_number_str)
            update_stadlander_status(rel_number_str, 'True')
        except Exception, e:
            LOG.error(e.message)


@receiver(account_closed_signal, sender=CC3Profile)
def handle_account_closed_signal(sender, instance, **kwargs):
    rel_number = None
    # try and update external system when an account is closed
    try:
        LOG.info("handle_account_closed_signal (profile id %s)" % instance.pk)
        stadlander_profile = StadlanderProfile.objects.get(
            profile_id=instance.pk)
        rel_number = stadlander_profile.rel_number
        update_stadlander_status("%s" % rel_number, 'False')
    except Exception, e:
        LOG.error("handle_account_closed_signal {0} exception {1}{2}".format(
            rel_number, e.args, e.message))
        LOG.error("handle_account_closed_signal {0} exception".format(
            e
        ))
