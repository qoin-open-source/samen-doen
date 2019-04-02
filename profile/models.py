# encoding: utf-8
import datetime
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.utils import translation
from django.template.defaultfilters import slugify

from localflavor.generic.models import IBANField
from registration.signals import user_activated
from icare4u_front.loyaltylab.utils import notify_ll_of_new_user

from cc3.cards.models import CARD_REGISTRATION_CHOICE_SEND, CardRegistration, \
    Fulfillment
from cc3.cards.utils import mail_card_admins
from cc3.core.utils import UploadToSecure  # get_upload_to
from cc3.cyclos import backends
from cc3.cyclos.common import AccountException
from cc3.cyclos.models import (
    CC3Profile, CyclosAccount, CyclosGroup, CyclosGroupSet, User)
from cc3.cyclos.services import MemberNotFoundException
from cc3.cyclos.transactions import TransactionException
from cc3.invoices.models import Invoice, InvoiceLine, Currency, PaymentStatus
from cc3.mail.models import MAIL_TYPE_MONTHLY_INVOICE, MAIL_TYPE_SEND_USER_CARD
from cc3.mail.utils import send_mail_to
from cc3.rewards.models import (
    BusinessCauseSettings, UserCause, DefaultGoodCause)
from cc3.rewards.transactions import cause_reward
from cc3.rules.utils import last_month_first_of_month

from .managers import UserProfileManager
from .validators import swift_bic_validator

LOG = logging.getLogger(__name__)

GENDER_CHOICES = (
    ('M', _('Man')),
    ('F', _('Female')),
)

SEPA_XML_FILE_TYPES = (
    ('C', _('Credit')),
    ('D', _('Debit')),
)

USER_TYPES = (
    'individual',
    'business',
    'institution',
    'charity')

ID_TYPES = (
    ('', '-------'),
    ('P', _('paspoort')),
    ('R', _('rijbewijs')),
    ('I', _('identiteitskaart')),
    ('V', _('vreemdelingendocument'))
)


class UserProfile(CC3Profile):
    terms_and_conditions = models.BooleanField(
        default=False,
        help_text=_('Do you agree to the terms and conditions?'))
    tussenvoegsel = models.CharField(max_length=10, default='', blank=True)
    extra_address = models.CharField(
        _('Extra Address'), max_length=255, default='', blank=True)
    num_street = models.CharField(
        _('Street Number'), max_length=50, default='', blank=True)
    gender = models.CharField(
        _('Gender'), max_length=1, choices=GENDER_CHOICES, blank=True,
        default='')
    date_of_birth = models.DateField(
        _('Date of Birth'), null=True, blank=True)
    id_type = models.CharField(
        _('ID Types'), max_length=1, choices=ID_TYPES, blank=True, default='')
    document_number = models.CharField(
        _('Document Number'), max_length=50, default='', blank=True)
    expiration_date = models.DateField(
        _('Expiration Date'), null=True, blank=True)
    wants_newsletter = models.BooleanField(
        _("Wants Newsletter"), default=False)

    # Have inserted this `all_objects` manager, which therefore becomes the
    # default manager, to make non-viewable UserProfiles visible in Comm Admin
    #
    # UserProfile.objects continues to operate as before, i.e. 'viewable'
    # profiles only. But beware unwanted side-effects anywhere where
    # the default manager is implicitly used.
    # Notably ths includes cyclos.User.get_profile(), which used to fail
    # if the User was inactive, but will now work. That seems like nore
    # correct behaviour, but will of course bfeak anything that was
    # depending on the old behaviour
    #
    # (NB I believe related object lookups are unaffected:
    # UserProfileManager doesn't have 'use_for_related_fields' set,
    # so the plain django Manager would have been, and will continue to be,
    # used)
    all_objects = models.Manager()
    objects = UserProfileManager()

    class Meta:
        verbose_name = _(u'User profile')
        verbose_name_plural = _(u'User profiles')

    # check whether profile is individual or business
    def is_individual_profile(self):
        try:
            IndividualProfile.objects.get(profile=self)
            return True
        except IndividualProfile.DoesNotExist:
            return False

    def is_business_profile(self):
        try:
            BusinessProfile.objects.get(profile=self)
            return True
        except BusinessProfile.DoesNotExist:
            return False

    def is_institution_profile(self):
        try:
            InstitutionProfile.objects.get(profile=self)
            return True
        except InstitutionProfile.DoesNotExist:
            return False

    def is_charity_profile(self):
        try:
            CharityProfile.objects.get(profile=self)
            return True
        except CharityProfile.DoesNotExist:
            return False

    def get_profile_type(self, include_profile=False):
        """
        Used in templates as profile.get_profile_type to determine if
        it is a IndividualProfile, BusinessProfile, InstitutionProfile
        or CharityProfile

        In other places it can be called with the parameter
        'include_profile=True'
        to return a tuple ('user_type_string', <profile object>)

        When the user profile is not one of these ones,
        return None or (None, None)
        """
        for model, profile_type in ((IndividualProfile, 'individual'),
                                    (BusinessProfile, 'business'),
                                    (InstitutionProfile, 'institution'),
                                    (CharityProfile, 'charity')):
            try:
                profile = model.objects.get(profile=self)
                if include_profile:
                    return profile_type, profile
                else:
                    return profile_type
            except:
                pass

        return (None, None) if include_profile else None

    def is_stadlander_sso_user(self):
        from ..stadlander.models import StadlanderProfile
        try:
            # stadlander SSO users can always order a card
            StadlanderProfile.objects.get(profile=self)
            return True
        except StadlanderProfile.DoesNotExist:
            pass

        return False

    def can_order_card(self):
        if self.is_stadlander_sso_user():
            return True

        # check address is valid
        # (SEPA fields no longer required)
        if not self.num_street or not self.postal_code or \
                not self.city or not self.address:
            return False

        return True

    def pays_for_card(self):
        # No one pays for cards
        return False

    @property
    def name(self):
        """
        Returns the complete name of the profile owner.
        """
        if self.first_name and self.last_name:
            if self.tussenvoegsel:
                return u"{0} {1} {2}".format(
                    self.first_name, self.tussenvoegsel, self.last_name)
            else:
                return u"{0} {1}".format(self.first_name, self.last_name)
        else:
            return self.user.email

    @property
    def full_name(self):
        """
        """
        if self.is_business_profile():
            return u"{0}".format(self.business_name)
        else:
            return self.name

    def get_address_with_street_num(self):
        return u"{0} {1}".format(self.address, self.num_street)

    def create_new_stadlander_profile(self, rel_number):
        """Create SL profile and make reward payment"""
        from ..stadlander.models import StadlanderProfile
        sl = StadlanderProfile.objects.create(
            rel_number=rel_number,
            profile=self,
            )
        LOG.info("Created StadlanderProfile {0}".format(sl))
        # reward with X punten - ticket #1513
        # MUST ONLY HAPPEN when the profile is created for the first time.
        amount = settings.STADLANDER_SSO_REWARD_AMOUNT
        description = settings.STADLANDER_SSO_REWARD_DESCRIPTION
        sender = settings.STADLANDER_SSO_REWARD_SENDER

        # receiver was shadowing django.dispatch.receiver
        _receiver = self.user
        transaction = backends.user_payment(
            sender, _receiver, amount, description)

        # reward charity with percentage of the transaction.
        cause_reward(amount, _receiver, transaction.transfer_id)

    def get_total_donations(self):
        """For Charity, total of all Transactions where sender is
        an Individual
        """
        if self.is_charity_profile:
            sender_groups = getattr(settings,
                                    'CYCLOS_CUSTOMER_MEMBER_GROUPS', [])
            donations = self.user.payment_receiver.filter(
                sender__cc3_profile__cyclos_group__name__in=sender_groups)
            total_donations = donations.aggregate(models.Sum('amount'))
            return total_donations['amount__sum']
        return 0

    def get_geocode_address(self):
        return self.get_address_with_street_num() + ', ' + str(self.country) + \
            ', ' + self.postal_code


class IndividualProfile(models.Model):
    """
    iCare4u specific Individual CC3Profile model
    """
    profile = models.OneToOneField(
        UserProfile, null=True, related_name='individual_profile')
    # FIELD MOVED TO UserProfile
    # date_of_birth = models.DateField(
    #     null=True, blank=True, help_text=_('Date of birth'))
    nickname = models.CharField(max_length=255, default='', blank=True)
    account_holder = models.CharField(max_length=255, default='', blank=True)
    # repetition of fields in business profile
    iban = IBANField(verbose_name=_('IBAN number'), null=True, blank=True)
    bic_code = models.CharField(
        _('BIC code'), max_length=11, validators=[swift_bic_validator],
        null=True, blank=True)

    class Meta:
        verbose_name = _(u'individual profile')
        verbose_name_plural = _(u'individual profiles')
        ordering = ('profile',)

    def __unicode__(self):
        return u'{0}'.format(self.profile.full_name or str(self.pk))

    def save(self, **kwargs):
        """
        Overrides the base ``save`` method to sync the ``CyclosGroup`` for the
        related profile.
        """
        if not self.pk:
            group = getattr(settings, 'CYCLOS_CUSTOMER_MEMBER_GROUP', None)
            if group:
                try:
                    cyclos_group = CyclosGroup.objects.get(name=group)
                    self.profile.cyclos_group = cyclos_group
                    self.profile.save()
                except CyclosGroup.DoesNotExist:
                    LOG.critical(
                        u"Cyclos group '{0}' does not exist".format(group))
            else:
                LOG.critical(
                    u"'CYCLOS_CUSTOMER_MEMBER_GROUP' setting not defined")

        # individuals business_names always set to 'name'
        self.profile.business_name = self.profile.name

        if not self.profile.slug:
            self.update_slug()

        super(IndividualProfile, self).save(**kwargs)

        self.profile.save()

    def update_slug(self, override=False):
        if (not self.profile.slug or override):
            slug = slugify(self.profile.name)
            slug_count = 0
            test_slug = slug

            while UserProfile.objects.filter(slug=test_slug):
                slug_count += 1
                test_slug = u"{0}{1}".format(
                    slug, slug_count)

            self.profile.slug = test_slug
            self.profile.save()

    def set_good_cause(self):
        """
        Moved from card registration view,
        for re-use in SSO user creation
        """

        # Set the default good cause for the newly created user, if nothing
        # created one before.
        def_good_cause = None
        cc3_community = self.profile.community
        new_user = self.profile.user
        try:
            def_good_cause = DefaultGoodCause.objects.get(
                community=cc3_community).cause
        except DefaultGoodCause.DoesNotExist:
            LOG.critical(
                _(u"No default good cause exists for {0} community").format(
                    cc3_community))
        curr_good_cause = UserCause.objects.filter(consumer=new_user)
        if def_good_cause and not curr_good_cause:
            return UserCause.objects.create(
                consumer=new_user, cause=def_good_cause)

        if curr_good_cause:
            return curr_good_cause[0]


class BusinessProfile(models.Model):
    """
    iCare4u specific Business CC3Profile model.
    """
    profile = models.OneToOneField(
        UserProfile, null=True, related_name='business_profile')
    account_holder = models.CharField(max_length=255, default='', blank=True)
    iban = IBANField(verbose_name=_('IBAN number'), null=True, blank=True)
    bic_code = models.CharField(
        _('BIC code'), max_length=11, validators=[swift_bic_validator],
        null=True, blank=True)
    mandate_id = models.CharField(
        _('mandate ID'), max_length=35, null=True, blank=True)
    signature_date = models.DateField(
        _('date of signature'), null=True, blank=True)
    latest_payment_date = models.DateTimeField(
        null=True, blank=True,
        help_text=_('Time of the latest SEPA debit processing time.'))
    registration_number = models.CharField(max_length=14, default='', blank=True,
                                           help_text=_('KvK number'))
    vat_number = models.CharField(max_length=14, default='', blank=True,
                                  help_text=_('VAT Number'))

    class Meta:
        verbose_name = _(u'business profile')
        verbose_name_plural = _(u'business profiles')
        ordering = ('profile',)

    def __unicode__(self):
        return u'{0}'.format(self.profile.full_name or str(self.pk))

    def save(self, **kwargs):
        """
        Overrides the base ``save`` method to set ``CyclosGroup``
        and the ``CyclosGroupSet`` to the correct Positoos preselected one, if
        any.
        """
        if not self.profile.groupset:
            try:
                group_set = CyclosGroupSet.objects.get(prefix='PST')
                self.profile.groupset = group_set
                self.profile.save()
            except CyclosGroupSet.DoesNotExist:
                LOG.critical(u"Cyclos groupset 'PST' does not exist")

        if not self.pk:
            group = getattr(settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None)
            if group:
                try:
                    cyclos_group = CyclosGroup.objects.get(name=group)
                    self.profile.cyclos_group = cyclos_group
                    self.profile.save()
                except CyclosGroup.DoesNotExist:
                    LOG.critical(
                        u"Cyclos group '{0}' does not exist".format(group))
            else:
                LOG.critical(
                    u"'CYCLOS_BUSINESS_MEMBER_GROUP' setting not defined")

        if not self.profile.slug:
            # This is the THIRD time the ``CC3Profile`` is saved if all
            # conditions are met. 3 database hits for the same action... :(
            # [ was marked 'fix me', but there are other more hideous things
            # lurking in the system, like cyclos_group attached to two
            # different models. this is v rarely called
            self.profile.update_slug()

        super(BusinessProfile, self).save(**kwargs)

    def create_invoice(self, amount, invoice_description):
        """
        Create a euro invoice from Positoos BV (marked unpaid) for this
        business.
        """
        vat_rate = 0  # 1570, no VAT/BTW should be added for now.

        today = datetime.date.today()

        currency, created = Currency.objects.get_or_create(
            code='EUR',
            defaults={
                'name': 'Euro',
                'symbol': '€'
                }
            )
        nr_days_due = getattr(
            settings, "SEPA_EXPORT_CREDIT_INVOICE_DAYS_DUE", 15)
        sender, created = User.objects.get_or_create(
            username=getattr(settings,
                             "CC3_BANK_USER", "Positoos Reserve"))
        to_be_paid_status, created = PaymentStatus.objects.get_or_create(
            description="Pending", is_active=True, is_paid=False)
        if amount > 0:
            is_debit = True
        else:
            is_debit = False

        invoice_type = "debit" if is_debit else "credit"

        invoice = Invoice.objects.create(
            from_user=sender, to_user=self.profile.user,
            inv_date=today,
            due_date=today + datetime.timedelta(days=nr_days_due),
            currency=currency, payment_status=to_be_paid_status,
            invoice_type=invoice_type,
            automatic_invoice=True,
            admin_comment=u"Automatic invoice of type {0}".format(
                invoice_type))

        InvoiceLine.objects.create(
            invoice=invoice, description=invoice_description,
            quantity=1, amount=amount, tax_rate=vat_rate)
        LOG.info(
            u"Created {2} invoice from reserve to user {0}, total amount "
            u"invoice: {1}".format(
                self.profile.user, invoice.get_total_display(), invoice_type))

    def invoice_description(self, from_date, to_date, transactions,
                            reset_transfer_descriptions=[]):
        """
        For a date-range and a list of cc3.cyclos Transaction objects,
        give the proper description to be used for the invoice.

        Note that we only count since the most recent balance reset. This is
        currently determined based on the description of the transfer, as I've
        not yet been able to determine the transaction type id (it isn't
        returned in the Transaction object).
        """
        spent = 0
        spent_eur = 0
        received = 0
        received_eur = 0
        for transaction in transactions:
            if transaction.description in reset_transfer_descriptions:
                # Reset-transaction found
                spent = 0
                received = 0
                from_date = transaction.created.date()
                continue

            if transaction.amount > 0:
                received += transaction.amount
            else:
                spent += transaction.amount

        div_by = Decimal("100.00")

        if spent:
            spent = spent * Decimal("-1.0")
            spent_eur = spent / div_by
        if received:
            received_eur = received / div_by

        total = spent - received
        total_eur = Decimal("0.00")
        if total:
            total_eur = total / div_by

        is_debit = False
        if total > 0:
            is_debit = True

        if is_debit:
            af_bijschrijving = _(u'Afschrijving')
            receive_or_pay = _(u'betalen')
        else:
            af_bijschrijving = _(u'Bijschrijving')
            receive_or_pay = _(u'ontvangen')

        return _(u"{af_bijschrijving} maandelijkse verrekening {from_date} "
                 u"tot {to_date}.\n\n "
                 u"Uitgegeven Positoos: {spent} Positoos (€ {spent_eur})\n"
                 u"Ingenomen Positoos: {received} Positoos (€ "
                 u"{received_eur})\n"
                 u"Saldoverrekening: {plus}{total} Positoos te "
                 u"{receive_or_pay}, € {total_eur}").format(
            af_bijschrijving=af_bijschrijving,
            from_date=from_date.strftime('%d-%m-%Y'),
            to_date=to_date.strftime('%d-%m-%Y'),
            spent=format(spent, '.0f'), spent_eur=format(spent_eur, '.2f'),
            received=format(received, '.0f'),
            received_eur=format(received_eur, '.2f'),
            plus=u'+' if is_debit else '',
            total=format(total, '.0f'), receive_or_pay=receive_or_pay,
            total_eur=format(
                total_eur if is_debit else total_eur * Decimal("-1.0"), '.2f'))

    def reset_balance(self):
        """
        Resets the current user Positoos balance to zero.

        Taking into account the ``accountStatus.balance`` of the user, it makes
        a payment from or to the system for a similar amount, turning the
        balance equal to zero.
        """
        # Getting settings - defaulting to Positoos values if settings missing.
        debit_transfer_type_id = getattr(
            settings, 'SEPA_EXPORT_DEBIT_TRANSFER_TYPE_ID', 39)
        debit_transfer_description = getattr(
            settings, 'SEPA_EXPORT_DEBIT_TRANSFER_DESCRIPTION',
            "Bijschrijving na automatisch incasso")

        credit_transfer_type_id = getattr(
            settings, 'SEPA_EXPORT_CREDIT_TRANSFER_TYPE_ID', 36)
        credit_transfer_description = getattr(
            settings, 'SEPA_EXPORT_CREDIT_TRANSFER_DESCRIPTION',
            "Afschrijving na automatisch incasso")

        to_date = datetime.date.today()
        from_date = last_month_first_of_month()
        div_by = Decimal("100.00")

        try:
            balance = backends.get_account_status(
                self.profile.user.username).accountStatus.balance

            transactions = backends.transactions(
                username=self.profile.user.username,
                from_date=from_date, to_date=to_date)

        except MemberNotFoundException:
            LOG.error(u'Member not found (in Cyclos): {0}'.format(
                self.profile.user.username))
            return False
        LOG.info(u"Resetting balance for user {0}, current balance {1}".format(
                 self.profile.user.username, balance))
        if balance == 0:
            LOG.info(u"Not resetting balance, no transaction required as "
                     u"balance is already 0")
            return True

        invoice_description = self.invoice_description(
            from_date, to_date, transactions,
            reset_transfer_descriptions=[
                debit_transfer_description, credit_transfer_description])

        try:
            if balance > 0:
                # Positive balance. Move the cash from user to the system.
                # From Organisatie rekening (member) to Reserve account
                # (system),
                # Transfer type ID 36.
                # Transfer Type 'Take out of circulation'.
                LOG.info(u"Credit transfer, ID: {0}, {1}".format(
                         credit_transfer_type_id, credit_transfer_description))
                backends.to_system_payment(
                    self.profile.user.username, balance,
                    credit_transfer_description,
                    transfer_type_id=credit_transfer_type_id)
                LOG.info(_(u'Monthly balance for business {0} reconciled. {1} '
                           u'Positoos recovered by Cyclos system'.format(
                               self.profile.user.username, balance)))
                self.create_invoice(
                    (balance / div_by) * Decimal("-1.00"), invoice_description)
            else:
                # Negative balance. Move some cash from system to user.
                # From Reserve account (system) to Organisatie rekening
                # (member).
                # Transfer type ID 39.
                # Transfer Type 'Acquiring Positoos'.
                LOG.info(u"Debit transfer, ID: {0}, {1}".format(
                         debit_transfer_type_id, debit_transfer_description))
                backends.from_system_payment(
                    self.profile.user.username, -balance,
                    debit_transfer_description,
                    transfer_type_id=debit_transfer_type_id)
                LOG.info(_(u'Monthly balance for business {0} reconciled. {1} '
                           u'Positoos paid by Cyclos system'.format(
                               self.profile.user.username, balance)))
                self.create_invoice(
                    (balance / div_by) * Decimal("-1.00"), invoice_description)
        except TransactionException, e:
            LOG.error(u'Unable to perform balance reset. The transaction '
                      u'failed: {0}\nSure the user is a business?'.format(e))
            return False

        # notify the business by email
        site = Site.objects.get_current()
        link_url = "https://{0}{1}".format(
            site.domain, reverse('invoice_list'))

        if getattr(settings, "SEND_SEPA_MONTHLY_RESET_INVOICE", False):
            send_mail_to([self.profile, ],
                         MAIL_TYPE_MONTHLY_INVOICE,
                         translation.get_language(),
                         {
                             'invoice_text': invoice_description,
                             'contact_name': self.profile.name,
                             'business_name': self.profile.full_name,
                             'link_url': link_url,
                         })

        return True


class InstitutionProfile(models.Model):
    """
    iCare4u specific Institution CC3Profile model.
    Made this an exact copy from BusinessProfile to start with
    """
    profile = models.OneToOneField(
        UserProfile, null=True, related_name='institution_profile')
    account_holder = models.CharField(max_length=255, default='', blank=True)
    iban = IBANField(verbose_name=_('IBAN number'), null=True, blank=True)
    bic_code = models.CharField(
        _('BIC code'), max_length=11, validators=[swift_bic_validator],
        null=True, blank=True)
    mandate_id = models.CharField(
        _('mandate ID'), max_length=35, null=True, blank=True)
    signature_date = models.DateField(
        _('date of signature'), null=True, blank=True)
    latest_payment_date = models.DateTimeField(
        null=True, blank=True,
        help_text=_('Time of the latest SEPA debit processing time.'))
    registration_number = models.CharField(max_length=14, default='', blank=True,
                                           help_text=_('KvK number'))
    vat_number = models.CharField(max_length=14, default='', blank=True,
                                  help_text=_('VAT Number'))

    class Meta:
        verbose_name = _(u'institution profile')
        verbose_name_plural = _(u'institution profiles')
        ordering = ('profile',)

    def __unicode__(self):
        return u'{0}'.format(self.profile.full_name or str(self.pk))

    def save(self, **kwargs):
        """
        Overrides the base ``save`` method to set ``CyclosGroup``
        and the ``CyclosGroupSet`` to the correct Positoos preselected one,
        if any.
        """
        if not self.profile.groupset:
            try:
                group_set = CyclosGroupSet.objects.get(prefix='PST')
                self.profile.groupset = group_set
                self.profile.save()
            except CyclosGroupSet.DoesNotExist:
                LOG.critical(u"Cyclos groupset 'PST' does not exist")

        if not self.pk:
            group = getattr(settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None)
            if group:
                try:
                    cyclos_group = CyclosGroup.objects.get(name=group)
                    self.profile.cyclos_group = cyclos_group
                    self.profile.save()
                except CyclosGroup.DoesNotExist:
                    LOG.critical(
                        u"Cyclos group '{0}' does not exist".format(group))
            else:
                LOG.critical(
                    u"'CYCLOS_INSTITUTION_MEMBER_GROUP' setting not defined")

        if not self.profile.slug:
            self.profile.update_slug()

        super(InstitutionProfile, self).save(**kwargs)

    def reset_balance(self):
        """
        Resets the current user Positoos balance to zero.

        Taking into account the ``accountStatus.balance`` of the user, it makes
        a payment from or to the system for a similar amount, turning the
        balance equal to zero.
        """

        # Getting settings - defaulting to Positoos values if settings missing.
        debit_transfer_type_id = getattr(
            settings, 'SEPA_EXPORT_DEBIT_TRANSFER_TYPE_ID', 39)
        debit_transfer_description = getattr(
            settings, 'SEPA_EXPORT_DEBIT_TRANSFER_DESCRIPTION',
            "Bijschrijving na automatisch incasso")

        credit_transfer_type_id = getattr(
            settings, 'SEPA_EXPORT_CREDIT_TRANSFER_TYPE_ID', 36)
        credit_transfer_description = getattr(
            settings, 'SEPA_EXPORT_CREDIT_TRANSFER_DESCRIPTION',
            "Afschrijving na automatisch incasso")

        vat_rate = getattr(settings, 'VAT_RATE', 21)

        try:
            balance = backends.get_account_status(
                self.profile.user.username).accountStatus.balance
        except MemberNotFoundException:
            LOG.error(u'Member not found (in Cyclos): {0}'.format(
                self.profile.user.username))
            return False
        LOG.info(u"Resetting balance for user {0}, current balance {1}".format(
                 self.profile.user.username, balance))
        if balance == 0:
            LOG.info(u"Not resetting balance, no transaction required as "
                     u"balance is already 0")
            return True

        try:
            if balance > 0:
                # Positive balance. Move the cash from user to the system.
                # From Organisatie rekening (member) to Reserve account
                # (system),
                # Transfer type ID 36.
                # Transfer Type 'Take out of circulation'.
                LOG.info(u"Credit transfer, ID: {0}, {1}".format(
                         credit_transfer_type_id, credit_transfer_description))
                backends.to_system_payment(
                    self.profile.user.username, balance,
                    credit_transfer_description,
                    transfer_type_id=credit_transfer_type_id)
                LOG.info(_(u'Monthly balance for business {0} reconciled. {1} '
                           u'Positoos recovered by Cyclos system'.format(
                               self.profile.user.username, balance)))

                # biz a/c b
                # Create euro invoice from Positoos BV (marked unpaid).
                today = datetime.date.today()

                currency, created = Currency.objects.get_or_create(
                    code='EUR',
                    defaults={
                        'name': 'Euro',
                        'symbol': '€'
                    }
                )
                nr_days_due = getattr(
                    settings, "SEPA_EXPORT_CREDIT_INVOICE_DAYS_DUE", 15)
                sender, created = User.objects.get_or_create(
                    username=getattr(settings,
                                     "CC3_BANK_USER", "Positoos Reserve"))
                to_be_paid_status = PaymentStatus.objects.filter(
                    is_active=True, is_paid=False)
                if not to_be_paid_status:
                    LOG.error(u"Payment status with 'is_active' True and "
                              u"'is_paid' False is not defined")
                    return False
                to_be_paid_status = to_be_paid_status[0]
                invoice_description = credit_transfer_description

                invoice_type = "SEPA export"
                invoice = Invoice.objects.create(
                    from_user=sender, to_user=self.profile.user,
                    inv_date=today,
                    due_date=today + datetime.timedelta(days=nr_days_due),
                    currency=currency, payment_status=to_be_paid_status,
                    automatic_invoice=True,
                    admin_comment=u"Automatic invoice of type {0}".format(
                        invoice_type))

                InvoiceLine.objects.create(
                    invoice=invoice, description=invoice_description,
                    quantity=1, amount=balance, tax_rate=vat_rate)
            else:
                # Negative balance. Move some cash from system to user.
                # From Reserve account (system) to Organisatie rekening
                # (member).
                # Transfer type ID 39.
                # Transfer Type 'Acquiring Positoos'.
                LOG.info(u"Debit transfer, ID: {0}, {1}".format(
                         debit_transfer_type_id, debit_transfer_description))
                backends.from_system_payment(
                    self.profile.user.username, -balance,
                    debit_transfer_description,
                    transfer_type_id=debit_transfer_type_id)
                LOG.info(_(u'Monthly balance for business {0} reconciled. {1} '
                           u'Positoos paid by Cyclos system'.format(
                               self.profile.user.username, balance)))
        except TransactionException, e:
            LOG.error(u'Unable to perform balance reset. The transaction '
                      u'failed: {0}\nSure the user is a business?'.format(e))
            return False

        return True


class CharityProfile(models.Model):
    """
    iCare4u specific Charity CC3Profile model.
    Made this an exact copy from BusinessProfile to start with
    """
    profile = models.OneToOneField(
        UserProfile, null=True, related_name='charity_profile')
    account_holder = models.CharField(max_length=255, default='', blank=True)
    iban = IBANField(verbose_name=_('IBAN number'), null=True, blank=True)
    bic_code = models.CharField(
        _('BIC code'), max_length=11, validators=[swift_bic_validator],
        null=True, blank=True)
    mandate_id = models.CharField(
        _('mandate ID'), max_length=35, null=True, blank=True)
    signature_date = models.DateField(
        _('date of signature'), null=True, blank=True)
    latest_payment_date = models.DateTimeField(
        null=True, blank=True,
        help_text=_('Time of the latest SEPA debit processing time.'))
    registration_number = models.CharField(max_length=14, default='', blank=True,
                                           help_text=_('KvK number'))

    class Meta:
        verbose_name = _(u'charity profile')
        verbose_name_plural = _(u'charity profiles')
        ordering = ('profile',)

    def __unicode__(self):
        return u'{0}'.format(self.profile.full_name or str(self.pk))

    def save(self, **kwargs):
        """
        Overrides the base ``save`` method to set ``CyclosGroup``
        and the ``CyclosGroupSet`` to the correct Positoos preselected one, if
        any.
        """
        if not self.profile.groupset:
            try:
                group_set = CyclosGroupSet.objects.get(prefix='PST')
                self.profile.groupset = group_set
                self.profile.save()
            except CyclosGroupSet.DoesNotExist:
                LOG.critical(u"Cyclos groupset 'PST' does not exist")

        if not self.pk:
            group = getattr(
                settings, 'CYCLOS_CHARITY_MEMBER_GROUP', 'Goede Doelen')
            if group:
                try:
                    cyclos_group = CyclosGroup.objects.get(name=group)
                    self.profile.cyclos_group = cyclos_group
                    self.profile.save()
                except CyclosGroup.DoesNotExist:
                    LOG.critical(
                        u"Cyclos group '{0}' does not exist".format(group))
            else:
                LOG.critical(
                    u"'CYCLOS_CHARITY_MEMBER_GROUP' setting not defined")

        if not self.profile.slug:
            self.profile.update_slug()

        super(CharityProfile, self).save(**kwargs)


class SEPAXMLFile(models.Model):
    """ Model to hold record of generated SEPA XML files available
    for download via admin """
    file = models.FileField(
        upload_to=UploadToSecure('sepa_xml_files'), max_length=500,
        editable=False)
    file_date = models.DateField(editable=False)
    file_type = models.CharField(
        max_length=10, choices=SEPA_XML_FILE_TYPES, blank=True, default='',
        editable=False)
    generated_date = models.DateField(editable=False)

    class Meta:
        ordering = ('generated_date',)
        verbose_name = _('SEPA XML file')
        verbose_name_plural = _('SEPA XML files')

    def __unicode__(self):
        return self.file.name


@receiver(post_save, sender=IndividualProfile,
          dispatch_uid='icare4u_individual_profile_save')
def link_individual_account(sender, instance, created, **kwargs):
    if instance.profile.first_name and instance.profile.last_name:
        try:
            instance.profile.cyclos_account.save()
        except CyclosAccount.DoesNotExist:
            # 'legacy' accounts
            LOG.debug(u'Existing account without a linked Cyclos account, '
                      u'creating new account in Cyclos')
            CyclosAccount.objects.create(cc3_profile=instance.profile)


@receiver(post_save, sender=BusinessProfile,
          dispatch_uid='icare4u_business_profile_save')
def link_business_account(sender, instance, created, **kwargs):
    if instance.profile.first_name and instance.profile.last_name:
        try:
            instance.profile.cyclos_account.save()
        except CyclosAccount.DoesNotExist:
            # 'Legacy' accounts
            LOG.debug(u'Existing account without a linked Cyclos account, '
                      u'creating new account in Cyclos')

            group = getattr(settings, 'CYCLOS_BUSINESS_MEMBER_GROUP',
                            u'Organisaties')
            try:
                # Assign the account to the 'business' group.
                cyclos_group = CyclosGroup.objects.get(
                    name=group)
                cyclos_account = CyclosAccount.objects.create(
                    cc3_profile=instance.profile, cyclos_group=cyclos_group.id)
                LOG.info(u'Created Cyclos account {0} for profile {1} in '
                         u'Cyclos group {2}'.format(
                             cyclos_account.cyclos_id,
                             cyclos_account.cc3_profile, cyclos_group.name))
            except CyclosGroup.DoesNotExist:
                LOG.critical(u'Cyclos group not present.')
            except AccountException, e:
                LOG.error(e)


@receiver(post_save, sender=InstitutionProfile,
          dispatch_uid='icare4u_institution_profile_save')
def link_institution_account(sender, instance, created, **kwargs):
    if instance.profile.first_name and instance.profile.last_name:
        try:
            instance.profile.cyclos_account.save()
        except CyclosAccount.DoesNotExist:
            # 'Legacy' accounts
            LOG.debug(u'Existing account without a linked Cyclos account, '
                      u'creating new account in Cyclos')

            group = getattr(settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP',
                            u'Instituties')

            try:
                # Assign the account to the 'business' group.
                cyclos_group = CyclosGroup.objects.get(
                    name=group)
                cyclos_account = CyclosAccount.objects.create(
                    cc3_profile=instance.profile, cyclos_group=cyclos_group.id)
                LOG.info(u'Created Cyclos account {0} for profile {1} in '
                         u'Cyclos group {2}'.format(
                             cyclos_account.cyclos_id,
                             cyclos_account.cc3_profile, cyclos_group.name))
            except CyclosGroup.DoesNotExist:
                LOG.critical(u'Cyclos group not present.')
            except AccountException, e:
                LOG.error(e)


@receiver(post_save, sender=CharityProfile,
          dispatch_uid='icare4u_charity_profile_save')
def link_charity_account(sender, instance, created, **kwargs):
    if instance.profile.first_name and instance.profile.last_name:
        try:
            instance.profile.cyclos_account.save()
        except CyclosAccount.DoesNotExist:
            # 'Legacy' accounts
            LOG.debug(u'Existing account without a linked Cyclos account, '
                      u'creating new account in Cyclos')

            group = getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP',
                            u'Goede Doelen')

            try:
                # Assign the account to the 'business' group.
                cyclos_group = CyclosGroup.objects.get(
                    name=group)
                cyclos_account = CyclosAccount.objects.create(
                    cc3_profile=instance.profile, cyclos_group=cyclos_group.id)
                LOG.info(u'Created Cyclos account {0} for profile {1} in '
                         u'Cyclos group {2}'.format(
                             cyclos_account.cyclos_id,
                             cyclos_account.cc3_profile, cyclos_group.name))
            except CyclosGroup.DoesNotExist:
                LOG.critical(u'Cyclos group not present.')
            except AccountException, e:
                LOG.error(e)


@receiver(post_save, sender=BusinessProfile,
          dispatch_uid='icare4u_business_profile_create_cause_settings')
def create_business_cause_settings(sender, instance, created, **kwargs):
    """
    Creates a ``rewards.BusinessCauseSettings`` object for this
    ``BusinessProfile`` when it is created.
    """
    if created:
        try:
            BusinessCauseSettings.objects.create(
                user=instance.profile.user,
                transaction_percentage=Decimal('5.00'),
                reward_percentage=True
            )
        except IntegrityError, e:
            LOG.error(
                u'Unable to create a default BusinessCauseSettings for {0}. '
                u'{1}'.format(instance, e))


def activate_set_default_good_cause(sender, user, request, **kwargs):
    LOG.info("activate_set_default_good_cause triggered {0}, {1}".format(
        sender, user
    ))

    user_profile = UserProfile.objects.get(user__pk=user.id)

    # If user has a good cause already, leave it alone
    # if not, use the default one for their community
    if user_profile.individual_profile is not None:
        user_profile.individual_profile.set_good_cause()


def order_new_card_on_activation(sender, user, request, **kwargs):
    LOG.info("order_new_card_on_activation triggered {0}, {1}".format(
        sender, user
    ))

    card_user = User.objects.get(pk=user.id)
    user_profile = UserProfile.objects.get(user__pk=user.id)

    # avoid double signal
    number_of_cards = CardRegistration.objects.filter(
        owner=card_user,
        registration_choice=CARD_REGISTRATION_CHOICE_SEND
    ).count()

    if number_of_cards == 0:
        card_registration = CardRegistration.objects.create(
            owner=card_user,
            registration_choice=CARD_REGISTRATION_CHOICE_SEND)

        mail_type_choice = MAIL_TYPE_SEND_USER_CARD
        # start fulfillment process
        Fulfillment.objects.create(
            profile=user_profile,
            card_registration=card_registration,
            status='New'
        )
        # send an email about the card request
        mail_card_admins(user_profile, mail_type_choice,
                         translation.get_language())


def notify_ll_on_activation(sender, user, request, **kwargs):
    LOG.info("notify_ll_on_activation triggered {0}, {1}".format(
        sender, user
    ))

    # TODO: session var or UserProfile field to record the fact that LL
    # have been notified

    user_profile = UserProfile.objects.get(user__pk=user.id)

    # TODO -- poss. need to check type of user and treat accordingly?
    notify_ll_of_new_user()


# There's a bug in registration that causes the user_activated signal to be
# sent twice, so these handlers need to cope with being called more than once
# for the same event.
# (NB. Using a unique dispatch_uid only prevents the handler from being
# registered more than once; the signal will still be received twice.)

# connect the signal to the set default good cause function
user_activated.connect(activate_set_default_good_cause)

# connect the signal to order a new card when a user activates their account
user_activated.connect(order_new_card_on_activation)

# connect the signal to notify Loyalty Lab when user activates
user_activated.connect(notify_ll_on_activation,
                       dispatch_uid='icare4u_notify_ll_new_user')
