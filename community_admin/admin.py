import logging

from django.utils.safestring import mark_safe

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.options import csrf_protect_m
from django.core import urlresolvers
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.http import HttpResponseRedirect, Http404
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.template.defaultfilters import slugify, floatformat
from django.utils.translation import ugettext as _

from cc3.billing.admin import (
    AssignedProductAdmin, InvoiceAdmin, InvoiceSetAdmin)
from cc3.billing.models import Product, AssignedProduct, Invoice, InvoiceSet
from cc3.cards.admin import (
    CardAdmin, CardNumberAdmin, OperatorAdmin, TerminalAdmin)
from cc3.cards.models import (
    Card, Operator, Terminal, Fulfillment,
    CARD_FULLFILLMENT_CHOICE_NEW, CARD_STATUS_CHOICES,
    CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED,
    CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED
)
from cc3.core.admin import TransactionAdmin
from cc3.core.models import Transaction
from cc3.cyclos.models import User
from cc3.cyclos.models.group import CyclosGroupSet, CyclosGroup
from cc3.cyclos.admin import (
    CardMachineUserAdmin, CardUserAdmin, FulfillmentProfileAdmin)
from cc3.excelexport.admin import admin_action_export_xls
from cc3.rewards.admin import BusinessCauseSettingsAdmin
from cc3.rewards.models import BusinessCauseSettings, UserCause
from cc3.statistics.admin import DashboardAdmin
from cc3.statistics.models import Dashboard

from icare4u_front.community_admin.forms import MiniOperatorForm, \
    CommunityTerminalModelForm, reward_percentage_choices, \
    CommunityOperatorModelForm
from icare4u_front.profile.models import (
    BusinessProfile, InstitutionProfile, CharityProfile,
    IndividualProfile, UserProfile)
from icare4u_front.profile.utils import generate_mandate_id
from icare4u_front.stadlander.models import StadlanderProfile

from .models import (
    CommunityCardMachineUserProxyModel, CommunityCardUserProxyModel,
    CommunityProductUserProfileProxyModel,
    CommunityFulfillmentProfileProxyModel
)
from .widgets import (
    CommunityCardMachineUserForeignKeyRawIdWidget,
    CommunityCardUserForeignKeyRawIdWidget,
    CommunityFulfillmentProfileForeignKeyRawIdWidget
)

from .forms import (
    CommunityBusinessProfileForm, CommunityFulfillmentForm,
    CommunityIndividualProfileForm, CommunityUserProfileForm,
    CommunityInstitutionProfileForm, CommunityCharityProfileForm,
    CommunityCardForm, CardBaseFormset, MiniCardForm, OperatorBaseFormset,
    TerminalBaseFormset, MiniTerminalForm)


LOG = logging.getLogger(__name__)


class CommunityUsersChangeList(ChangeList):
    """
    Custom ``admin.Changelist`` class to deliver an appropriate way of linking
    to ``BusinessProfile`` or ``IndividualProfile`` in users change list to
    edit a specific user, depending on which type the user is.
    """
    def url_for_result(self, result):
        """
        Overrides the base ``url_for_result`` method to provide a specific link
        for each type of user in the changelist.
        result is <class 'icare4u_front.profile.models.UserProfile'>
        """
        user_type, profile = result.get_profile_type(include_profile=True)

        if not user_type:
            user_type = 'user'

        if profile:
            profile_pk = profile.pk
        else:
            profile_pk = result.pk

        return reverse(
            'community_admin:community_{0}profile_change'.format(user_type),
            kwargs={'pk': profile_pk})

    def get_queryset(self, request):
        return super(
            CommunityUsersChangeList, self).get_queryset(request).distinct()


class CommunityAdminSite(admin.AdminSite):
    """
    Defines a Django admin site specific for CC3 Communities administration.
    """
    site_header = 'Community Administration'
    index_template = 'community_admin/index.html'
    app_index_template = 'community_admin/app_index.html'


class CommunityAdminStadlanderAdminMixin(object):
    """
    Mixin to limit Stadlander Admins to only see Stadlander users
    and their data

    May need to override:
      'stadlander_qs_filter': filter string used to limit get_queryset()
      ...
      TODO: more formfield_for_* stuff
      TODO: has_*_permission stuff ?
    """
    stadlander_qs_filter = 'groupset__id'

    def get_queryset(self, request):
        """
        Override queryset to filter admin to only have Stadlander users if
        admin user is in the 'Stadlander Admin' group
        """
        qs = super(
            CommunityAdminStadlanderAdminMixin, self).get_queryset(request)

        # stadlander admins group and permissions created using data migrations
        if request.user.groups.filter(name="Stadlander admins").count():
            stadlander_groupset = CyclosGroupSet.objects.get(prefix="STD")
            kwargs = {self.stadlander_qs_filter: stadlander_groupset.id}
            qs = qs.filter(**kwargs)

        return qs

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'user':
            if request.user.groups.filter(name="Stadlander admins").count():
                stadlander_groupset = CyclosGroupSet.objects.get(prefix="STD")
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__groupset__id=stadlander_groupset.id)

        return super(
            CommunityAdminStadlanderAdminMixin, self).formfield_for_foreignkey(
                db_field, request, **kwargs)


class CommunityUserAdmin(CommunityAdminStadlanderAdminMixin, admin.ModelAdmin):
    """ ModelAdmin for the ``UserProfile`` model """
    actions = [admin_action_export_xls, ]
    list_per_page = 10
    list_display = (
        'userid',
        'name',
        'gender2',
        'date_of_birth',
        'business_name',
        'email',
        'community2',
        'cyclos_group2',
        'is_active_lookup',
        'current_balance2',
        'wants_newsletter2',
    )
    search_fields = (
        'first_name',
        'last_name',
        'user__email',
        'user__first_name',
        'user__last_name',
        'business_name',
        'address',
        'extra_address',
        'num_street',
        'user__card_set__number__number',
        'phone_number',
        'mobile_number',
        'postal_code',
        'stadlanderprofile__rel_number',
        'user__terminal_set__name',
    )
    list_filter = ('community', 'cyclos_group', 'wants_newsletter',
                   'user__is_active', 'gender')
    filter_horizontal = ('categories',)

    individual_profile_on_create_url_name = \
        'community_admin:community_individualprofile_change'
    business_profile_on_create_url_name = \
        'community_admin:community_businessprofile_change'
    institution_profile_on_create_url_name = \
        'community_admin:community_institutionprofile_change'

    def userid(self, obj):
        return obj.user.id
    userid.short_description = u"User ID"

    def gender2(self, obj):
        if obj.gender == 'M':
            return 'M'
        if obj.gender == 'F':
            return 'V'
        else:
            return None
    gender2.short_description = u"m/v"

    def name(self, obj):
        if hasattr(obj, 'tussenvoegsel') and obj.tussenvoegsel is not None:
            return obj.first_name + " " + obj.tussenvoegsel + \
                   " " + obj.last_name
        else:
            return obj.first_name + " " + obj.last_name
    name.short_description = _(u"Name")

    def email(self, obj):
        return obj.user.email
    email.short_description = _(u"Email address")

    def community2(self, obj):
        return obj.community

    community2.short_description = _(u"Community")

    def cyclos_group2(self, obj):
        return obj.cyclos_group

    cyclos_group2.short_description = _(u"Cyclos Group?")

    def is_active_lookup(self, obj):
        return obj.user.is_active
    is_active_lookup.short_description = _(u'Active?')
    is_active_lookup.boolean = True

    def current_balance2(self, obj):
        current_balance = obj.current_balance
        try:
            return mark_safe("<div style='text-align:right'>" +
                             str(floatformat(current_balance, 0)) +
                             "&nbsp;&nbsp;&nbsp;</div>")
        except:
            return current_balance
    current_balance2.short_description = _(u"Current Balance")

    def wants_newsletter2(self, obj):
        return obj.wants_newsletter
    wants_newsletter2.short_description = _(u"Wants Newsletter?")
    wants_newsletter2.boolean = True

    def get_actions(self, request):
        # #3503 Disable delete and deactivate
        actions = super(CommunityUserAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']

        return actions

    def get_changelist(self, request, **kwargs):
        """
        Overrides the base ``get_changelist`` method to provide a specific link
        for each type of user in the changelist.
        """
        return CommunityUsersChangeList

    def changelist_view(self, request, extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("User Profiles")
        return super(CommunityUserAdmin, self).changelist_view(
            request, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _(u"Add new user")
        return super(CommunityUserAdmin, self).add_view(
            request, form_url=form_url, extra_context=extra_context)

    @csrf_protect_m
    @transaction.atomic
    def userprofile_add_view(self, request):
        """
        Custom admin view to create ``UserProfile`` objects.

        ``UserProfile`` is the base user in iCare4u. Once it is created, the
        system will redirect to the correspondent specific profile change view.
        """
        if request.method == 'POST':
            form = CommunityUserProfileForm(request.POST)
            if form.is_valid():
                profile = form.save()
                messages.success(
                    request,
                    _(u'Base user profile created for {0} user. Please, fill '
                      u'up the specific profile data.').format(
                          profile.cyclos_group))
                if profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None):
                    # Create the related `BusinessProfile` and redirect to the
                    # correspondent admin view to complete edition.
                    business = BusinessProfile.objects.create(
                        profile=profile,
                        mandate_id=generate_mandate_id(profile.user)
                    )

                    return HttpResponseRedirect(
                        reverse(
                            self.business_profile_on_create_url_name,
                            kwargs={'pk': business.pk}))
                elif profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None):
                    # Create the related `InstitutionProfile` and redirect to
                    # the corresponding admin view to complete edition.
                    institution = InstitutionProfile.objects.create(
                        profile=profile,
                        mandate_id=generate_mandate_id(profile.user)
                    )
                    return HttpResponseRedirect(
                        reverse(
                            self.institution_profile_on_create_url_name,
                            kwargs={'pk': institution.pk}))
                elif profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None):
                    charity = CharityProfile.objects.create(
                        profile=profile,
                        mandate_id=generate_mandate_id(profile.user)
                    )
                    return HttpResponseRedirect(
                        reverse(
                            'community_admin:community_charityprofile_change',
                            kwargs={'pk': charity.pk}))
                elif profile.cyclos_group.name in getattr(
                        settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', None):
                    # Samen Doen individuals not visible by default in
                    # marketplace
                    profile.is_visible = False
                    profile.business_name = profile.name
                    profile.slug = slugify(profile.name)
                    profile.save()
                    individual = IndividualProfile.objects.create(
                        profile=profile)
                    return HttpResponseRedirect(
                        reverse(
                            self.individual_profile_on_create_url_name,
                            kwargs={'pk': individual.pk}))
                else:
                    return HttpResponseRedirect(
                        reverse(
                            'community_admin:profile_userprofile_changelist'))
        else:
            form = CommunityUserProfileForm()

        context = {
            'title': _('Add new user'),
            'form': form,
            'app_label': _('Users'),
            'media': self.media,
        }
        return render_to_response(
            'community_admin/add_user.html', context, RequestContext(request))

    @csrf_protect_m
    @transaction.atomic
    def userprofile_change_view(self, request, pk):
        """
        Custom admin view to edit ``UserProfile`` objects.
        """
        profile = get_object_or_404(UserProfile, pk=pk)

        profile_type, profile_obj = profile.get_profile_type(
            include_profile=True)

        if request.method == 'POST':
            # deal with deleting pictures manually
            post_data = request.POST.copy()
            post_data['picture_clear'] = request.POST.get(
                'picture-clear', None)
            form = CommunityUserProfileForm(
                post_data, request.FILES, instance=profile.user)
            if form.is_valid():
                form.save()
                messages.success(request, _(u'User profile edited.'))

                if profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_BUSINESS_MEMBER_GROUP', None):
                    # Create the related `BusinessProfile` and redirect to the
                    # correspondent admin view to complete edition.
                    business = BusinessProfile.objects.create(profile=profile)
                    return HttpResponseRedirect(
                        reverse(
                            self.business_profile_on_create_url_name,
                            kwargs={'pk': business.pk}))
                elif profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_INSTITUTION_MEMBER_GROUP', None):
                    # Create the related `InstitutionProfile` and redirect to
                    # the correspondent admin view to complete edition.
                    institution = InstitutionProfile.objects.create(
                        profile=profile)
                    return HttpResponseRedirect(
                        reverse(
                            self.institution_profile_on_create_url_name,
                            kwargs={'pk': institution.pk}))
                elif profile.cyclos_group.name == getattr(
                        settings, 'CYCLOS_CHARITY_MEMBER_GROUP', None):
                    # Create the related `CharityProfile` and redirect to the
                    # correspondent admin view to complete edition.
                    charity = CharityProfile.objects.create(profile=profile)
                    return HttpResponseRedirect(
                        reverse(
                            'community_admin:community_charityprofile_change',
                            kwargs={'pk': charity.pk}))
                elif profile.cyclos_group.name in getattr(
                        settings, 'CYCLOS_CUSTOMER_MEMBER_GROUPS', None):
                    profile.business_name = profile.name
                    profile.slug = slugify(profile.name)
                    profile.save()
                    individual = IndividualProfile.objects.create(
                        profile=profile)
                    return HttpResponseRedirect(
                        reverse(
                            self.individual_profile_on_create_url_name,
                            kwargs={'pk': individual.pk}))
                else:
                    return HttpResponseRedirect(
                        reverse(
                            'community_admin:profile_userprofile_changelist'))
        else:
            if not profile_type:
                messages.warning(
                    request,
                    _(u'This profile is incomplete. Please, relate it to a'
                      u' Cyclos group to complete edition.'))

            initial_data = {
                'cyclos_group': profile.cyclos_group,
                'tussenvoegsel': profile.tussenvoegsel,
                'community': profile.community,
                'gender': profile.gender,
                'name': profile.name,
                'city': profile.city,
                'address': profile.address,
                'postal_code': profile.postal_code,
                'country': profile.country,
                'phone_number': profile.phone_number,
                'mobile_number': profile.mobile_number,
                'groupset': profile.groupset,
                'company_website': profile.company_website,
                'company_description': profile.company_description,
                'picture': profile.picture,
                'picture_height': profile.picture_height,
                'picture_width': profile.picture_width,
                'extra_address': profile.extra_address,
                'num_street': profile.num_street,
                'web_payments_enabled': profile.web_payments_enabled,
            }
            form = CommunityUserProfileForm(
                instance=profile.user, initial=initial_data)

        context = {
            'profile': profile,
            'title': _(u'Edit Profile {0}'.format(profile)),
            'form': form,
            'app_label': _('Users'),
            'media': self.media,
        }
        return render_to_response(
            'community_admin/change_userprofile_user.html', context,
            RequestContext(request))

    @csrf_protect_m
    @transaction.atomic
    def business_profile_change_view(self, request, pk):
        """
        Custom admin view to edit ``BusinessProfile`` objects.
        """
        business = get_object_or_404(BusinessProfile, pk=pk)
        user = None

        if hasattr(business, 'profile') and\
            business.profile is not None and\
                hasattr(business.profile, 'user'):
            user = business.profile.user
            business_cause_settings = get_object_or_404(
                BusinessCauseSettings, user=user)
        else:
            LOG.error('The business profile {} has no matching '
                      'BusinessCauseSettings object.'.format(str(business)))
            raise Http404()

        if not user:
            LOG.error('The business profile {} has no matching user.'.format(
                str(business)))
            raise Http404()

        # TODO: convert function name to lower case (PEP8)
        # TODO:  Do the same for CardInlineFormset
        OperatorInlineFormSet = inlineformset_factory(
            User,
            Operator,
            form=MiniOperatorForm,
            formset=OperatorBaseFormset,
            fields=('name', 'pin'),
            extra=1,
            can_delete=True
        )

        TerminalInlineFormSet = inlineformset_factory(
            User,
            Terminal,
            form=MiniTerminalForm,
            formset=TerminalBaseFormset,
            fields=('name', 'icc_id', 'comments'),
            extra=1,
            can_delete=True
        )

        # create formsets
        operator_inline_formset = OperatorInlineFormSet(instance=user)
        terminal_inline_formset = TerminalInlineFormSet(instance=user)

        if request.method == 'POST':
            # deal with deleting pictures manually
            post_data = request.POST.copy()
            post_data['picture_clear'] = request.POST.get(
                'picture-clear', None)

            form = CommunityBusinessProfileForm(
                post_data, request.FILES, instance=user)

                # if POST data overwrite formsets
            operator_inline_formset = OperatorInlineFormSet(
                post_data, instance=user)
            terminal_inline_formset = TerminalInlineFormSet(
                post_data, instance=user)

            if form.is_valid() and\
                    operator_inline_formset.is_valid() and\
                    terminal_inline_formset.is_valid():
                try:
                    form.save()
                    operator_inline_formset.save()
                    terminal_inline_formset.save()
                    messages.success(request, _(u'Business profile edited.'))
                except IntegrityError as ie:
                    messages.error(request, _(u'A database error occurred.'))
                    LOG.error(ie)
                return HttpResponseRedirect(
                    reverse('community_admin:profile_userprofile_changelist'))
        else:

            account_first_activated = user.first_activated
            account_last_deactivated = user.last_deactivated
            account_last_login = user.last_login

            initial_data = {
                'user_id': user.id,
                'first_name': business.profile.first_name,
                'last_name': business.profile.last_name,
                'cyclos_group': business.profile.cyclos_group,
                'tussenvoegsel': business.profile.tussenvoegsel,
                'community': business.profile.community,
                'gender': business.profile.gender,
                'date_of_birth': business.profile.date_of_birth,
                'id_type': business.profile.id_type,
                'document_number': business.profile.document_number,
                'expiration_date': business.profile.expiration_date,
                'business_name': business.profile.business_name,
                'city': business.profile.city,
                'address': business.profile.address,
                'postal_code': business.profile.postal_code,
                'country': business.profile.country,
                'phone_number': business.profile.phone_number,
                'mobile_number': business.profile.mobile_number,
                'registration_number': business.registration_number,
                'company_website': business.profile.company_website,
                'company_description': business.profile.company_description,
                'picture': business.profile.picture,
                'picture_height': business.profile.picture_height,
                'picture_width': business.profile.picture_width,
                'extra_address': business.profile.extra_address,
                'num_street': business.profile.num_street,
                'web_payments_enabled': business.profile.web_payments_enabled,
                'iban': business.iban,
                'bic_code': business.bic_code,
                'account_holder': business.account_holder,
                'mandate_id': business.mandate_id,
                'vat_number': business.vat_number,
                'signature_date': business.signature_date,
                'groupset': business.profile.groupset,
                'is_visible': business.profile.is_visible,
                'transaction_percentage':
                    business_cause_settings.transaction_percentage,
                'reward_percentage': business_cause_settings.reward_percentage,
                'account_first_activated': account_first_activated,
                'account_last_deactivated': account_last_deactivated,
                'account_last_login': account_last_login,
            }
            form = CommunityBusinessProfileForm(
                instance=user, initial=initial_data)

        inline_formsets = {
            'operator_inline_formset': operator_inline_formset,
            'terminal_inline_formset': terminal_inline_formset,
        }

        context = {
            'profile': business.profile,
            'title': _(u'Edit business user {0}').format(business.profile),
            'form': form,
            'app_label': _('Users'),
            'media': self.media,
            'inline_formsets': inline_formsets,
        }
        return render_to_response(
            'community_admin/change_business_user.html', context,
            RequestContext(request))

    @csrf_protect_m
    @transaction.atomic
    def institution_profile_change_view(self, request, pk):
        """
        Custom admin view to edit ``InstitutionProfile`` objects.
        """
        institution = get_object_or_404(InstitutionProfile, pk=pk)
        user = institution.profile.user

        # TODO: convert function name to lower case (PEP8)
        # TODO:  Do the same for CardInlineFormset
        OperatorInlineFormSet = inlineformset_factory(
            User,
            Operator,
            form=MiniOperatorForm,
            formset=OperatorBaseFormset,
            fields=('name', 'pin'),
            extra=1,
            can_delete=True
        )

        TerminalInlineFormSet = inlineformset_factory(
            User,
            Terminal,
            form=MiniTerminalForm,
            formset=TerminalBaseFormset,
            fields=('name', 'icc_id', 'comments'),
            extra=1,
            can_delete=True
        )

        # create formsets
        operator_inline_formset = OperatorInlineFormSet(instance=user)
        terminal_inline_formset = TerminalInlineFormSet(instance=user)

        if request.method == 'POST':
            # deal with deleting pictures manually
            post_data = request.POST.copy()
            post_data['picture_clear'] = request.POST.get(
                'picture-clear', None)

            form = CommunityInstitutionProfileForm(
                post_data, request.FILES, instance=user)

            # if POST data, overwrite formsets
            operator_inline_formset = OperatorInlineFormSet(
                post_data, instance=user)
            terminal_inline_formset = TerminalInlineFormSet(
                post_data, instance=user)

            if form.is_valid() and \
                    operator_inline_formset.is_valid() and \
                    terminal_inline_formset.is_valid():
                try:
                    form.save()
                    operator_inline_formset.save()
                    terminal_inline_formset.save()
                    messages.success(request, _(u'Institution profile edited.'))
                except IntegrityError as ie:
                    messages.error(request, _(u'A database error occurred.'))
                    LOG.error(ie)
                return HttpResponseRedirect(
                    reverse('community_admin:profile_userprofile_changelist'))
        else:
            account_first_activated = user.first_activated
            account_last_deactivated = user.last_deactivated
            account_last_login = user.last_login

            initial_data = {
                'user_id': user.id,
                'first_name': institution.profile.first_name,
                'last_name': institution.profile.last_name,
                'cyclos_group': institution.profile.cyclos_group,
                'tussenvoegsel': institution.profile.tussenvoegsel,
                'community': institution.profile.community,
                'gender': institution.profile.gender,
                'date_of_birth': institution.profile.date_of_birth,
                'id_type': institution.profile.id_type,
                'document_number': institution.profile.document_number,
                'expiration_date': institution.profile.expiration_date,
                'business_name': institution.profile.business_name,
                'city': institution.profile.city,
                'address': institution.profile.address,
                'postal_code': institution.profile.postal_code,
                'country': institution.profile.country,
                'phone_number': institution.profile.phone_number,
                'mobile_number': institution.profile.mobile_number,
                'registration_number': institution.registration_number,
                'company_website': institution.profile.company_website,
                'company_description': institution.profile.company_description,
                'picture': institution.profile.picture,
                'picture_height': institution.profile.picture_height,
                'picture_width': institution.profile.picture_width,
                'extra_address': institution.profile.extra_address,
                'num_street': institution.profile.num_street,
                'web_payments_enabled':
                    institution.profile.web_payments_enabled,
                'iban': institution.iban,
                'bic_code': institution.bic_code,
                'account_holder': institution.account_holder,
                'mandate_id': institution.mandate_id,
                'vat_number': institution.vat_number,
                'signature_date': institution.signature_date,
                'groupset': institution.profile.groupset,
                'is_visible': institution.profile.is_visible,
                'account_first_activated': account_first_activated,
                'account_last_deactivated': account_last_deactivated,
                'account_last_login': account_last_login,
            }
            form = CommunityInstitutionProfileForm(
                instance=user, initial=initial_data)

        inline_formsets = {
            'operator_inline_formset': operator_inline_formset,
            'terminal_inline_formset': terminal_inline_formset,
        }

        context = {
            'profile': institution.profile,
            'title':  _(u'Edit institution user {0}'.format(
                institution.profile)),
            'form': form,
            'app_label': _('Users'),
            'media': self.media,
            'inline_formsets': inline_formsets,
        }
        return render_to_response(
            'community_admin/change_business_user.html', context,
            RequestContext(request))

    @csrf_protect_m
    @transaction.atomic
    def charity_profile_change_view(self, request, pk):
        """
        Custom admin view to edit ``CharityProfile`` objects.
        """
        charity = get_object_or_404(CharityProfile, pk=pk)
        user = charity.profile.user

        # TODO: convert function name to lower case (PEP8)
        # TODO:  Do the same for CardInlineFormset
        OperatorInlineFormSet = inlineformset_factory(
            User,
            Operator,
            form=MiniOperatorForm,
            formset=OperatorBaseFormset,
            fields=('name', 'pin'),
            extra=1,
            can_delete=True
        )

        TerminalInlineFormSet = inlineformset_factory(
            User,
            Terminal,
            form=MiniTerminalForm,
            formset=TerminalBaseFormset,
            fields=('name', 'icc_id', 'comments'),
            extra=1,
            can_delete=True
        )

        CardInlineFormSet = inlineformset_factory(
            User,
            Card,
            form=MiniCardForm,
            formset=CardBaseFormset,
            fields=('number', 'status'),
            extra=1,
            can_delete=True
        )

        # create formsets
        card_inline_formset = CardInlineFormSet(instance=user)
        operator_inline_formset = OperatorInlineFormSet(instance=user)
        terminal_inline_formset = TerminalInlineFormSet(instance=user)

        if request.method == 'POST':
            # deal with deleting pictures manually
            post_data = request.POST.copy()
            post_data['picture_clear'] = request.POST.get(
                'picture-clear', None)
            form = CommunityCharityProfileForm(
                post_data, request.FILES, instance=user)

            # if POST data, overwrite formsets
            card_inline_formset = CardInlineFormSet(post_data, instance=user)
            operator_inline_formset = OperatorInlineFormSet(
                post_data, instance=user)
            terminal_inline_formset = TerminalInlineFormSet(
                post_data, instance=user)

            if form.is_valid() and \
                    card_inline_formset.is_valid() and \
                    operator_inline_formset.is_valid() and \
                    terminal_inline_formset.is_valid():
                try:
                    form.save()
                    card_inline_formset.save()
                    operator_inline_formset.save()
                    terminal_inline_formset.save()
                    messages.success(request, _(u'Charity profile edited.'))
                except IntegrityError as ie:
                    messages.error(request, _(u'A database error occurred.'))
                    LOG.error(ie)
                return HttpResponseRedirect(
                        reverse(
                            'community_admin:profile_userprofile_changelist'))
        else:
            account_first_activated = user.first_activated
            account_last_deactivated = user.last_deactivated
            account_last_login = user.last_login

            initial_data = {
                'user_id': user.id,
                'first_name': charity.profile.first_name,
                'last_name': charity.profile.last_name,
                'cyclos_group': charity.profile.cyclos_group,
                'tussenvoegsel': charity.profile.tussenvoegsel,
                'community': charity.profile.community,
                'gender': charity.profile.gender,
                'date_of_birth': charity.profile.date_of_birth,
                'id_type': charity.profile.id_type,
                'document_number': charity.profile.document_number,
                'expiration_date': charity.profile.expiration_date,
                'business_name': charity.profile.business_name,
                'city': charity.profile.city,
                'address': charity.profile.address,
                'postal_code': charity.profile.postal_code,
                'country': charity.profile.country,
                'phone_number': charity.profile.phone_number,
                'mobile_number': charity.profile.mobile_number,
                'registration_number': charity.registration_number,
                'company_website': charity.profile.company_website,
                'company_description': charity.profile.company_description,
                'picture': charity.profile.picture,
                'picture_height': charity.profile.picture_height,
                'picture_width': charity.profile.picture_width,
                'extra_address': charity.profile.extra_address,
                'num_street': charity.profile.num_street,
                'web_payments_enabled': charity.profile.web_payments_enabled,
                'iban': charity.iban,
                'bic_code': charity.bic_code,
                'account_holder': charity.account_holder,
                'mandate_id': charity.mandate_id,
                'signature_date': charity.signature_date,
                'groupset': charity.profile.groupset,
                'is_visible': charity.profile.is_visible,
                'account_first_activated': account_first_activated,
                'account_last_deactivated': account_last_deactivated,
                'account_last_login': account_last_login,
            }
            form = CommunityCharityProfileForm(
                instance=charity.profile.user, initial=initial_data)

        # must be done if there is a POST, but it is invalid
        # this was indented, but shouldn't have been
        inline_formsets = {
            'card_inline_formset': card_inline_formset,
            'operator_inline_formset': operator_inline_formset,
            'terminal_inline_formset': terminal_inline_formset,
        }

        context = {
            'profile': charity.profile,
            'title':  _(u'Edit charity user {0}'.format(charity.profile)),
            'form': form,
            'app_label': _('Users'),
            'media': self.media,
            'inline_formsets': inline_formsets,
        }
        return render_to_response(
            'community_admin/change_business_user.html', context,
            # same template is ok for business, institution and charity?
            RequestContext(request))

    @csrf_protect_m
    @transaction.atomic
    def individual_profile_change_view(self, request, pk):
        """
        Custom admin view to edit ``IndividualProfile`` objects.
        """
        individual = get_object_or_404(IndividualProfile, pk=pk)
        user = individual.profile.user

        CardInlineFormSet = inlineformset_factory(
            User,
            Card,
            form=MiniCardForm,
            formset=CardBaseFormset,
            fields=('number', 'status'),
            extra=1,
            can_delete=True
        )

        # create formsets
        card_inline_formset = CardInlineFormSet(
            instance=user,
            formset_element_id='inline_card_set')

        if request.method == 'POST':
            # deal with deleting pictures manually
            post_data = request.POST.copy()
            post_data['picture_clear'] = request.POST.get(
                'picture-clear', None)
            form = CommunityIndividualProfileForm(
                post_data, request.FILES, instance=individual.profile.user)

            # if POST data, overwrite formsets
            card_inline_formset = CardInlineFormSet(
                post_data, instance=user, formset_element_id='inline_card_set')

            if form.is_valid() and card_inline_formset.is_valid():
                try:
                    form.save()
                    card_inline_formset.save()
                    messages.success(request, _(u'Individual profile edited.'))
                except IntegrityError as ie:
                    messages.error(request, _(u'A database error occurred.'))
                    LOG.error(ie)
                return HttpResponseRedirect(
                    reverse('community_admin:profile_userprofile_changelist'))
        else:
            try:
                cause = user.usercause.cause
            except ObjectDoesNotExist:
                cause = None

            try:
                donation_percent = user.usercause.donation_percent
            except ObjectDoesNotExist:
                donation_percent = None

            if not donation_percent:
                donation_percent = \
                    individual.profile.community.default_donation_percent

            try:
                stadlander_profile = StadlanderProfile.objects.get(
                    profile=individual.profile)
                rel_number = stadlander_profile.rel_number
            except StadlanderProfile.DoesNotExist:
                rel_number = None

            user_cause = UserCause.objects.filter(
                consumer=user)

            account_first_activated = user.first_activated
            account_last_deactivated = user.last_deactivated
            account_last_login = user.last_login

            initial_data = {
                'user_id': user.id,
                'first_name': individual.profile.first_name,
                'last_name': individual.profile.last_name,
                'cyclos_group': individual.profile.cyclos_group,
                'tussenvoegsel': individual.profile.tussenvoegsel,
                'community': individual.profile.community,
                'gender': individual.profile.gender,
                # individuals never a business name - only ever have 'name'
                # 'name' set on registration from firstname, lastname, and
                # tussenvoegsel if not none
                'business_name': individual.profile.name,
                'city': individual.profile.city,
                'address': individual.profile.address,
                'postal_code': individual.profile.postal_code,
                'country': individual.profile.country,
                'phone_number': individual.profile.phone_number,
                'mobile_number': individual.profile.mobile_number,
                'company_website': individual.profile.company_website,
                'company_description': individual.profile.company_description,
                'picture': individual.profile.picture,
                'picture_height': individual.profile.picture_height,
                'picture_width': individual.profile.picture_width,
                'extra_address': individual.profile.extra_address,
                'num_street': individual.profile.num_street,
                'web_payments_enabled':
                    individual.profile.web_payments_enabled,
                'date_of_birth': individual.profile.date_of_birth,
                'nickname': individual.nickname,
                'iban': individual.iban,
                'bic_code': individual.bic_code,
                'account_holder': individual.account_holder,
                'good_cause': cause,
                'donation_percent': donation_percent,
                'groupset': individual.profile.groupset,
                'rel_number': rel_number,
                'is_visible': individual.profile.is_visible,
                'wants_newsletter': individual.profile.wants_newsletter,
                'account_first_activated': account_first_activated,
                'account_last_deactivated': account_last_deactivated,
                'account_last_login': account_last_login,
            }

            form = CommunityIndividualProfileForm(
                instance=user, initial=initial_data)

        inline_formsets = {
            'card_inline_formset': card_inline_formset,
        }

        context = {
            'profile': individual.profile,
            'title': _(u'Edit individual user {0}').format(individual.profile),
            'form': form,
            'app_label': _('Users'),
            'stadlander_groupset': settings.STADLANDER_GROUPSET_ID,
            'individual': individual,
            'media': self.media,
            'min_donation_percent':
                individual.profile.community.min_donation_percent,
            'max_donation_percent':
                individual.profile.community.max_donation_percent,
            'inline_formsets': inline_formsets,
        }
        return render_to_response(
            'community_admin/change_individual_user.html', context,
            RequestContext(request))

    def get_urls(self):
        urls = super(CommunityUserAdmin, self).get_urls()
        custom_urls = [
            url(r'^add/$',
                self.admin_site.admin_view(self.userprofile_add_view),
                name='community_userprofile_add'),
            url(r'^(?P<pk>\d+)/',
                self.admin_site.admin_view(self.userprofile_change_view),
                name='community_userprofile_change'),
            url(r'^business/(?P<pk>\d+)/',
                self.admin_site.admin_view(self.business_profile_change_view),
                name='community_businessprofile_change'),
            url(r'^institution/(?P<pk>\d+)/',
                self.admin_site.admin_view(
                    self.institution_profile_change_view),
                name='community_institutionprofile_change'),
            url(r'^charity/(?P<pk>\d+)/',
                self.admin_site.admin_view(self.charity_profile_change_view),
                name='community_charityprofile_change'),
            url(r'^individual/(?P<pk>\d+)/',
                self.admin_site.admin_view(
                    self.individual_profile_change_view),
                name='community_individualprofile_change'),
        ]
        return custom_urls + urls


class CommunityCardAdmin(CommunityAdminStadlanderAdminMixin, CardAdmin):
    stadlander_qs_filter = 'owner__cc3_profile__groupset__id'
    list_display_links = None
    list_filter = ()

    list_display = (
        'card_num',
        'uid_num',
        'name',
        'userid',
        'email',
        'activ_date',
        'status',
    )

    ordering = ('-activation_date', 'number__number')

    add_form = CommunityCardForm
    add_form_template = 'community_admin/add_card.html'
    change_list_template = 'community_admin/cards/card/change_list.html'

    def activ_date(self, obj):
        if obj.activation_date is not None:
            return obj.activation_date.strftime("%d/%m/%Y %H:%M:%S")
        else:
            return None

    activ_date.admin_order_field = 'activation_date'
    activ_date.short_description = _(u"Date of first activation")

    def status(self, obj):
        return CARD_STATUS_CHOICES[obj.status]

    status.short_description = _(u"Status")

    def userid(self, obj):
        return obj.owner.id
    userid.short_description = _(u"User ID")

    def card_num(self, obj):
        return obj.number.number

    card_num.admin_order_field = 'number__number'
    card_num.short_description = _(u"Card number")

    def uid_num(self, obj):
        return obj.number.uid_number

    uid_num.short_description = _(u"Card UID")

    def email(self, obj):
        """
        Overrides the already customized ``email`` method in ``CardAdmin``
        class to redirect with the links to the different profile types we have
        in iCare4u.
        """
        try:
            pk = obj.owner.cc3_profile.userprofile.individual_profile.pk
            email_url = reverse(
                'community_admin:community_individualprofile_change',
                args=(pk,))
        except ObjectDoesNotExist:
            pk = obj.owner.cc3_profile.userprofile.pk
            email_url = reverse(
                'community_admin:community_userprofile_change',
                args=(pk,))

        return u'<a href="{0}">{1}</a>'.format(email_url, obj.owner.email)

    def name(self, obj):
        """
        Overrides the already customized ``name`` method in ``CardAdmin`` class
        to redirect with the links to the different profile types we have in
        iCare4u.
        """
        try:
            pk = obj.owner.cc3_profile.userprofile.individual_profile.pk
            name_url = reverse(
                'community_admin:community_individualprofile_change',
                args=(pk,))
        except ObjectDoesNotExist:
            pk = obj.owner.cc3_profile.userprofile.pk
            name_url = reverse(
                'community_admin:community_userprofile_change',
                args=(pk,))

        if obj.owner.cc3_profile.userprofile.tussenvoegsel:
            return u'<a href="{0}">{1} {2} {3}</a>'.format(
                name_url, obj.owner.cc3_profile.first_name,
                obj.owner.cc3_profile.userprofile.tussenvoegsel,
                obj.owner.cc3_profile.last_name)
        else:
            return u'<a href="{0}">{1} {2}</a>'.format(
                name_url, obj.owner.cc3_profile.first_name,
                obj.owner.cc3_profile.last_name)

    email.short_description = _(u"Email address")
    email.allow_tags = True

    name.short_description = _(u"Name")
    name.allow_tags = True

    def get_actions(self, request):
        # have to do this to remove the action from the dropdown (even
        # though we have removed delete permission)
        actions = super(
            CommunityCardAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Linked cards")
        return super(CommunityCardAdmin, self).changelist_view(
            request, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Connect card")
        return super(CommunityCardAdmin, self).add_view(
            request, form_url=form_url, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        if 'fulfillment' in request.GET and request.GET['fulfillment']:
            fulfillment_change_list_url = reverse(
                "community_admin:cards_fulfillment_changelist")
            return HttpResponseRedirect(fulfillment_change_list_url)
        else:
            return self.response_post_save_add(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
        return super(CommunityCardAdmin, self).get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Overrides base ``formfield_for_foreignkey`` method to get magnifying
        glass to appear for owners.
        """
        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = CommunityCardUserForeignKeyRawIdWidget(
                db_field.rel, self.admin_site, using=db)

        return db_field.formfield(**kwargs)

    def save_model(self, request, obj, form, change):
        messages.add_message(
            request, messages.SUCCESS, _(u"Card successfully connected"))
        super(CommunityCardAdmin, self).save_model(request, obj, form, change)


class CommunityTransactionAdmin(CommunityAdminStadlanderAdminMixin,
                                TransactionAdmin):
    stadlander_qs_filter = 'sender__cc3_profile__groupset__id'


class CommunityTerminalAdmin(CommunityAdminStadlanderAdminMixin, TerminalAdmin):
    stadlander_qs_filter = 'business__cc3_profile__groupset__id'

    list_display = (
        'name',
        'icc_id',
        'last_seen_date2',
        'business_name',
        'user_id',
        'comments',
    )

    exclude = ('removed_date',)

    form = CommunityTerminalModelForm

    change_form_template = 'community_admin/cards/terminal/change_form.html'

    search_fields = (
        'name',
        'icc_id',
        'business__cc3_profile__business_name',
    )

    def changelist_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Card Terminals")
        return super(
            CommunityTerminalAdmin, self
        ).changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}
        if object_id:
            extra_context['edit_terminal'] = True
        return super(CommunityTerminalAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context)

    def get_actions(self, request):
        # Disable delete
        actions = super(CommunityTerminalAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_queryset(self, request):
        """
        Override queryset to filter out 'removed' terminals
        """
        qs = super(CommunityTerminalAdmin, self).get_queryset(request)
        return qs.filter(removed_date__isnull=True)

    def get_cardmachineuser_rawid_widget(self, db_field, db):
        """
        Split out from formfield_for_foreignkey() so overriding is simpler
        """
        return CommunityCardMachineUserForeignKeyRawIdWidget(
            db_field.rel, self.admin_site, using=db)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Prevent community admins from deleting terminals
        """
        return False

    def user_id(self, obj):
        if obj.business:
            return obj.business.id
        else:
            return '-'
    user_id.short_description = _(u"User ID")

    def business_name(self, obj):
        if hasattr(obj, 'business') and obj.business is not None:
            if hasattr(obj.business, 'cc3_profile') and \
                            obj.business.cc3_profile is not None:
                return obj.business.cc3_profile.business_name

        return None
    business_name.short_description = _(u"Business name")

    def last_seen_date2(self, obj):
        if obj.last_seen_date:
            return obj.last_seen_date.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return '-'

    last_seen_date2.short_description = _('Date last seen')


class CommunityOperatorAdmin(CommunityAdminStadlanderAdminMixin, OperatorAdmin):
    stadlander_qs_filter = 'business__cc3_profile__groupset__id'
    change_form_template = 'community_admin/cards/operator/change_form.html'

    form = CommunityOperatorModelForm
    fields = (
        'name',
        'pin',
        'business',
        'creation_date',
        'last_login_date',
    )

    list_display = (
        'name',
        'pin',
        'business_name2',
        'user_id',
    )
    raw_id_fields = ('business', )
    search_fields = (
        'business__first_name',
        'business__last_name',
        'business__cc3_profile__business_name',
        'business__id',
    )

    def business_name2(self, obj):
        if hasattr(obj, 'business') and obj.business is not None:
            if hasattr(obj.business, 'cc3_profile') and \
                    obj.business.cc3_profile is not None:
                return obj.business.cc3_profile.business_name
        return ''
    business_name2.short_description = _(u"Business name")

    def user_id(self, obj):
        if obj.business:
            return obj.business.id
        else:
            return '-'
    user_id.short_description = _(u"User ID")

    def changelist_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Operators")
        return super(
            CommunityOperatorAdmin, self
        ).changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}
        if object_id:
            extra_context['edit_operator'] = True
        return super(CommunityOperatorAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Overrides base ``formfield_for_foreignkey`` method to filter users only
        by their membership to 'business' group.
        """
        # This will act in the case the ``raw_id_fields`` feature is NOT used.
        if db_field.name == 'business':
            cyclos_groups = None

            try:
                cyclos_groups = CyclosGroup.objects.filter(
                    name__in=settings.CYCLOS_CARD_MACHINE_MEMBER_GROUPS)
                kwargs['queryset'] = User.objects.filter(
                    cc3_profile__cyclos_group__in=cyclos_groups)
            except AttributeError:
                LOG.critical(
                    "Django setting CYCLOS_CARD_MACHINE_MEMBER_GROUPS "
                    "not defined.")
            finally:
                if not cyclos_groups:
                    kwargs['queryset'] = User.objects.none()
                    LOG.critical('Card Machine Cyclos groups do not exist.')

        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = CommunityCardMachineUserForeignKeyRawIdWidget(
                db_field.rel, self.admin_site, using=db)

        return db_field.formfield(**kwargs)

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(
            super(CommunityOperatorAdmin, self).get_readonly_fields(
                request, obj))
        if obj:
            ro_fields.append('name')
            # readonly field prevents formfield_for_foreignkey above from
            # being called, so disabling in the template
            # ro_fields.append('business')
        return ro_fields


class CommunityBusinessCauseSettingsAdmin(CommunityAdminStadlanderAdminMixin,
                                          BusinessCauseSettingsAdmin):
    stadlander_qs_filter = 'user__cc3_profile__groupset__id'
    raw_id_fields = ("user", )
    change_list_template = 'community_admin/rewards/change_list.html'
    change_form_template = 'community_admin/rewards/change_form.html'
    list_display = (
        'business_name',
        'user_id2',
        'reward_percentage2',
        'transaction_percentage',
    )

    def user_id2(self, obj):
        if hasattr(obj, 'user') and obj.user is not None:
            return obj.user.id
        return ''
    user_id2.short_description = _(u"User ID")

    def business_name(self, obj):
        if hasattr(obj, 'user') and obj.user is not None and \
                hasattr(obj.user, 'cc3_profile') and \
                obj.user.cc3_profile is not None:
            return obj.user.business_name
        else:
            return ''

    business_name.short_description = _(u"Business name")

    def reward_percentage2(self, obj):
        if obj.reward_percentage:
            return reward_percentage_choices[1][1]

        return reward_percentage_choices[0][1]

    reward_percentage2.short_description = _("Optie")

    def changelist_view(self, request, extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _('Business Cause Settings')
        return super(
            CommunityBusinessCauseSettingsAdmin, self
        ).changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _('Add Business Cause Settings')
        return super(CommunityBusinessCauseSettingsAdmin, self).add_view(
            request, form_url=form_url, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(
                is_active=True).order_by('cc3_profile__business_name')
        return super(
            CommunityBusinessCauseSettingsAdmin, self
        ).formfield_for_foreignkey(db_field, request, **kwargs)


class CommunityDashboardAdmin(DashboardAdmin):

    change_list_template = 'community_admin/dashboard_change_list.html'

    def has_add_permission(self, request):
        return False


class CommunityCardMachineUserAdmin(CardMachineUserAdmin):
    list_display = (
        'user_id',
        'name',
        'email2',
        'business_name',
    )

    def user_id(self, obj):
        return obj.id

    user_id.short_description = _(u"User ID")

    def name(self, obj):
        if hasattr(obj, 'cc3_profile') and obj.cc3_profile is not None and \
                hasattr(obj.cc3_profile, 'userprofile') and \
                        obj.cc3_profile.userprofile is not None:
            return obj.first_name + " " + \
                   obj.cc3_profile.userprofile.tussenvoegsel + " " + \
                   obj.last_name
        else:
            return obj.first_name + " " + obj.last_name

    name.short_description = _(u"Name")

    def email2(self, obj):
        return obj.email

    email2.short_description = _(u"Email address")

    def business_name(self, obj):
        if hasattr(obj, 'cc3_profile') and obj.cc3_profile is not None:
            return obj.cc3_profile.business_name
        else:
            return None

    business_name.short_description = _(u"Business name")

    def changelist_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Select a user")
        return super(
            CommunityCardMachineUserAdmin, self
        ).changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False


class CommunityCardUserAdmin(CardUserAdmin):
    list_display = (
        'user_id',
        'name',
        'email2',
        'business_name',
    )

    search_fields = (
        'first_name',
        'last_name',
        'email',
        'username',
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(
            CommunityCardUserAdmin, self
        ).get_search_results(request, queryset, search_term)

        try:
            queryset |= User.objects.filter(
                cc3_profile__business_name__icontains=search_term)
        except:
            pass

        return queryset, use_distinct

    def business_name(self, obj):
        if hasattr(obj, 'cc3_profile') and obj.cc3_profile is not None:
            return obj.cc3_profile.business_name
        else:
            return None

    business_name.short_description = _(u"Business name")

    def email2(self, obj):
        return obj.email

    email2.short_description = _(u"Email address")

    def name(self, obj):
        if hasattr(obj, 'cc3_profile') and \
                obj.cc3_profile is not None and \
                hasattr(obj.cc3_profile, 'userprofile') and \
                obj.cc3_profile.userprofile is not None:
            return obj.first_name + " " + \
                   obj.cc3_profile.userprofile.tussenvoegsel + " " + \
                   obj.last_name
        else:
            return obj.first_name + " " + obj.last_name

    name.short_description = _(u"Name")

    def user_id(self, obj):
        return obj.id

    user_id.short_description = _(u"User ID")

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Select a user")
        return super(
            CommunityCardUserAdmin, self
        ).changelist_view(request, extra_context=extra_context)


class CommunityFulfillmentProfileAdmin(FulfillmentProfileAdmin):
    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context['title'] = _("Select a user")
        return super(
            CommunityFulfillmentProfileAdmin, self
        ).changelist_view(request, extra_context=extra_context)


############################################
# billing app
############################################

class CommunityInvoiceAdmin(InvoiceAdmin):
    # Comm Admins can only generate and export Invoices via admin actions
    # so restrict access

    class Media:
        css = {
            "all": ("css/admin_hide_inline_unicode.css",)
        }

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CommunityInvoiceSetAdmin(InvoiceSetAdmin):
    # Comm Admins can only generate and export Invoices via admin actions
    # so restrict access
    readonly_fields = ['generated_at', 'sent_at', 'sent_to', ]

    class Media:
        css = {
            "all": ("css/admin_hide_inline_unicode.css",)
        }

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        # have to do this to remove the action from the dropdown (even
        # though we have removed delete permission)
        actions = super(
            CommunityInvoiceSetAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class CommunityAssignedProductAdmin(AssignedProductAdmin):
    # Comm Admins can only assign products via CommunityAssignProductsAdmin
    # so restrict direct access
    model = AssignedProduct

    # def has_add_permission(self, request):
    #    return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        # have to do this to remove the action from the dropdown (even
        # though we have removed delete permission)
        actions = super(
            CommunityAssignedProductAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_profile_change_url(self, obj):
        user_type, specific_profile = obj.user_profile.user.get_profile(
            ).get_profile_type(include_profile=True)
        return reverse(
            'community_admin:community_{0}profile_change'.format(user_type),
            kwargs={'pk': specific_profile.pk})

    def response_post_save_change(self, request, obj):
        """
        Override redirect after the 'Save' button has been pressed
        when editing an existing object so it goes back to the profile page.
        """
        redirect_url = self.get_profile_change_url(obj)
        return HttpResponseRedirect(redirect_url)

    def response_post_save_add(self, request, obj):
        """
        Override redirect after the 'Save' button has been pressed
        when adding a new object so it goes back to the profile page.
        """
        redirect_url = self.get_profile_change_url(obj)
        return HttpResponseRedirect(redirect_url)

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(
            super(CommunityAssignedProductAdmin, self).get_readonly_fields(
                request, obj))
        if obj:
            if obj.product:
                if obj.product.auto_qty_type:
                    ro_fields.append('quantity')
            if obj.product:
                if obj.product.auto_assign_type:
                    ro_fields.extend(['product', 'user_profile',
                                      'start_date', 'end_date',
                                      'next_invoice_date'])
        return ro_fields

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(auto_assign_type='')
        return super(CommunityAssignedProductAdmin,
                     self).formfield_for_foreignkey(
                        db_field, request, **kwargs)


class AssignedProductInline(admin.TabularInline):
    model = AssignedProduct
    fields = [
        'product',
        'quantity', 'discount_percent', 'start_date', 'end_date',
        'billing_frequency', 'next_invoice_date',
    ]
    readonly_fields = ['billing_frequency', ]


class CommunityAssignProductsAdmin(admin.ModelAdmin):
    model = CommunityProductUserProfileProxyModel

    class Media:
        css = {
            "all": ("css/admin_hide_inline_unicode.css",)
        }

    def assigned_products(self, obj):
        return ", ".join(
            [ap.product.name for ap in obj.assigned_products.all()])

    list_filter = [
        ('cyclos_group', admin.RelatedOnlyFieldListFilter),
        ]
    list_display = [
        'business_name', 'cyclos_group', 'assigned_products',
        ]
    inlines = [
        AssignedProductInline,
        ]
    fields = [
        'first_name', 'last_name', 'business_name', 'cyclos_group',
        ]
    readonly_fields = [
        'first_name', 'last_name', 'business_name', 'cyclos_group',
        ]
    search_fields = (
        'first_name',
        'last_name',
        'user__email',
        'user__first_name',
        'user__last_name',
        'business_name',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        # have to do this to remove the action from the dropdown (even
        # though we have removed delete permission)
        actions = super(
            CommunityAssignProductsAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class CommunityFulfillmentAdmin(admin.ModelAdmin):
    class Meta:
        model = Fulfillment

    add_form_template = 'community_admin/add_fulfillment.html'
    add_form = CommunityFulfillmentForm

    change_list_template = 'community_admin/cards/fulfillment/change_list.html'
    change_form_template = 'community_admin/cards/fulfillment/change_form.html'

    # #3421 Override the fields to display in the change list view
    # #3445 Add options field
    list_display = ('fid',
                    'name',
                    'user_id',
                    'email2',
                    'address',
                    'request_date',
                    'status',
                    'options'
                    )
    ordering = ('-status', '-id',)
    raw_id_fields = ('profile',)
    actions = [admin_action_export_xls]
    search_fields = (
        'profile__first_name',
        'profile__last_name',
        'profile__user__first_name',
        'profile__user__last_name',
        'profile__business_name',
    )
    CARD_FULLFILLMENT_CONNECT = '0'
    CARD_FULLFILLMENT_REJECT = '1'
    CARD_FULLFILLMENT_NOACTION = '2'

    OPTIONS_CHOICES = (
        (CARD_FULLFILLMENT_NOACTION, _("--------------")),
        (CARD_FULLFILLMENT_CONNECT, _("Connect Card")),
        (CARD_FULLFILLMENT_REJECT, _("Reject Request")),
    )

    def __init__(self, *args, **kwargs):
        super(CommunityFulfillmentAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None,)

    def get_actions(self, request):
        actions = super(CommunityFulfillmentAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    # 3421 Functions for returning custom fields in the change list view
    def name(self, obj):
        if hasattr(obj.profile, 'userprofile') and \
                        obj.profile.userprofile is not None:
            return obj.profile.first_name + " " + \
                   obj.profile.userprofile.tussenvoegsel + " " + \
                   obj.profile.last_name
        else:
            return obj.profile.first_name + " " + obj.profile.last_name

            # 3421 Utility function to build an address string from the
            # relevant CC3Profile fields

    def options(self, obj):
        if obj.status == CARD_FULLFILLMENT_CHOICE_NEW:
            html = '<select>{}</select>'
            option = '<option value="{}"{}>{}</option>'
            options = ''
            for opt in self.OPTIONS_CHOICES:
                if opt[0] == self.CARD_FULLFILLMENT_NOACTION:
                    options += option.format(opt[0], ' selected', opt[1])
                else:
                    options += option.format(opt[0], '', opt[1])
            return html.format(options)
        else:
            return ''

    options.allow_tags = True

    def user_id(self, obj):
        return obj.profile.user.id

    user_id.short_description = _(u"User ID")

    def email2(self, obj):
        return obj.profile.user.email

    def build_address(self, obj):
        if obj is not None and \
                hasattr(obj, 'profile') and \
                hasattr(obj.profile, 'userprofile'):

            if obj.profile.userprofile is not None:
                return '{} {} {}\n{} {}'.format(
                    obj.profile.address,
                    obj.profile.userprofile.num_street,
                    obj.profile.userprofile.extra_address,
                    obj.profile.postal_code,
                    obj.profile.city
                )
            else:
                return '{}\n{} {}'.format(
                    obj.profile.address,
                    obj.profile.postal_code,
                    obj.profile.city
                )
        else:
            return None

    def address(self, obj):
        return self.build_address(obj)

    def request_date(self, obj):
        return obj.creation_date.strftime("%d/%m/%Y")

    def status(self, obj):
        return obj.status

    def fid(self, obj):
        return obj.id

    name.short_description = _("name")
    email2.short_description = _("email")
    address.short_description = _("address")
    request_date.short_description = _("request date")
    fid.short_description = _("#")
    options.short_description = _("options")

    # 3421 **END** Functions for returning custom fields in the change list view

    # # 3421 Function to add extra context data
    # Specifically, the select value to trigger the Card add view popup
    # and the URL to that view
    def changelist_view(self, request, extra_context=None):
        if not extra_context:
            extra_context = {}

        extra_context_update = {
            'self_url': request.path,
            'new_card_popup_trigger_value': self.CARD_FULLFILLMENT_CONNECT,
            'fulfillment_reject_trigger_value': self.CARD_FULLFILLMENT_REJECT,
            'fulfillment_cancel_status':
                CARD_FULLFILLMENT_CHOICE_ACCOUNT_CLOSED,
            'card_add_url': urlresolvers.reverse(
                "community_admin:cards_card_add"),
            'fulfillment_update_url': urlresolvers.reverse(
                "community_admin_cards_fulfillment_update"),
            'title': _(u"Fulfillments"),
        }
        extra_context.update(extra_context_update)
        return super(CommunityFulfillmentAdmin, self).changelist_view(
            request, extra_context=extra_context)

    # # 3421 Function to add extra context data
    # Specifically, the select value to trigger the Card add view popup,
    # the URL to that view, and the user.id corresponding to the
    # Fulfillment object
    def change_view(self, request, object_id, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}
        if object_id:
            try:
                obj = Fulfillment.objects.get(id=object_id)
                if obj:
                    if hasattr(obj, 'profile'):
                        owner = obj.profile.user
                        if owner:
                            extra_context['owner'] = owner.id
            except Fulfillment.DoesNotExist:
                extra_context['owner'] = None
        else:
            extra_context['owner'] = None

        extra_context['new_card_popup_trigger_value'] = \
            CARD_FULLFILLMENT_CHOICE_MANUALLY_PROCESSED

        extra_context['card_add_url'] = urlresolvers.reverse(
            "community_admin:cards_card_add")

        return super(CommunityFulfillmentAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        # This acts in the case we are using ``raw_id_feature``.
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = CommunityFulfillmentProfileForeignKeyRawIdWidget(
                db_field.rel, self.admin_site, using=db)

        return db_field.formfield(**kwargs)

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
        return super(CommunityFulfillmentAdmin, self).get_form(
            request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.status = CARD_FULLFILLMENT_CHOICE_NEW

        super(CommunityFulfillmentAdmin, self).save_model(
            request, obj, form, change)


class CommunityCardNumberAdmin(CardNumberAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin_site = CommunityAdminSite(name='community_admin')
admin_site.register(UserProfile, CommunityUserAdmin)
admin_site.register(Card, CommunityCardAdmin)

# #3421 Remove the ability to manage card numbers in community admin
# admin_site.register(CardNumber, CommunityCardNumberAdmin)

admin_site.register(Transaction, CommunityTransactionAdmin)
admin_site.register(Terminal, CommunityTerminalAdmin)
admin_site.register(BusinessCauseSettings, CommunityBusinessCauseSettingsAdmin)
admin_site.register(Operator, CommunityOperatorAdmin)
admin_site.register(Dashboard, CommunityDashboardAdmin)
admin_site.register(CommunityCardUserProxyModel,
                    CommunityCardUserAdmin)
admin_site.register(CommunityCardMachineUserProxyModel,
                    CommunityCardMachineUserAdmin)
admin_site.register(CommunityProductUserProfileProxyModel,
                    CommunityAssignProductsAdmin)
admin_site.register(AssignedProduct, CommunityAssignedProductAdmin)
admin_site.register(Invoice, CommunityInvoiceAdmin)
admin_site.register(InvoiceSet, CommunityInvoiceSetAdmin)
admin_site.register(Fulfillment, CommunityFulfillmentAdmin)
admin_site.register(CommunityFulfillmentProfileProxyModel,
                    CommunityFulfillmentProfileAdmin)
