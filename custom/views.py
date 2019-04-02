import json
import logging
import re
import string
from string import digits

from rest_framework.request import Request as RESTRequest

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from cc3.cards.models import Card
from cc3.cyclos.models import CC3Community, User
from cc3.marketplace.views import (
    CampaignView, CampaignCreateView,
    BusinessView, MarketplaceView, MarketplaceSearchListView)
from .forms import (
    ICare4uMarketplaceFilterForm, ICare4uBusinessFilterForm,
    ICare4uBusinessMapFilterForm, ICare4uCampaignFilterForm)
from ..profile.models import (
    IndividualProfile, CharityProfile, UserProfile)

LOG = logging.getLogger(__name__)

tokenize_regex = re.compile(r'[%s\s]+' % re.escape(string.punctuation))


class ICare4uMarketplaceView(MarketplaceView):
    paginate_by = getattr(settings, 'MARKETPLACE_PAGINATION_BY', 12)
    form_class = ICare4uMarketplaceFilterForm

    def apply_profile_type_filter(self, queryset, profile_types):
        cyclos_group_pks = []
        if profile_types:
            for profile_type in profile_types:
                if profile_type.find(','):
                    sub_profile_types = profile_type.split(',')
                    for sub_profile_type in sub_profile_types:
                        cyclos_group_pks.append(sub_profile_type)
                else:
                    cyclos_group_pks.append(profile_type)

            queryset = queryset.filter(
                created_by__cyclos_group__pk__in=cyclos_group_pks
            )
        return queryset


class ICare4uMarketplaceSearchView(MarketplaceSearchListView):
    form_class = ICare4uMarketplaceFilterForm


class ICare4uCampaignView(CampaignView):
    form_class = ICare4uCampaignFilterForm


class ICare4uBusinessView(BusinessView):
    paginate_by = 24
    form_class = ICare4uBusinessFilterForm

    def apply_categories_filter(self, businesses, categories):
        """Samen Doen profiles never filtered by categories"""
        return businesses

    def apply_profile_type_filter(self, businesses, profile_types):
        cyclos_group_pks = []

        if profile_types:
            for profile_type in profile_types:
                if profile_type.find(','):
                    sub_profile_types = profile_type.split(',')
                    for sub_profile_type in sub_profile_types:
                        cyclos_group_pks.append(sub_profile_type)
                else:
                    cyclos_group_pks.append(profile_type)

            businesses = businesses.filter(
                cyclos_group__pk__in=cyclos_group_pks
            )
        return businesses


class ICare4uBusinessMapView(ICare4uBusinessView):
    start_tab = "businesses_map"
    paginate_by = 2000  # effectively 'no pagination'
    require_location = True
    form_class = ICare4uBusinessMapFilterForm

    def get_context_data(self, **kwargs):
        context = super(ICare4uBusinessMapView,
                        self).get_context_data(**kwargs)

        context['no_pagination'] = True

        # default map center north pole or there abouts
        context['map_centre_lat'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LAT', 0)
        context['map_centre_lng'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LNG', 0)
        context['search_on_map'] = True
        return context


class ICare4uCampaignCreateView(CampaignCreateView):

    def get_initial(self):
        initial = super(ICare4uCampaignCreateView, self).get_initial()
        profile = self.request.user.get_profile()
        initial['num_street'] = profile.num_street
        initial['extra_address'] = profile.extra_address
        return initial


def get_payees(request, ordered_user_pks=None):
    # Troeven payments are generally to Individuals ... so now samen doen
    if ordered_user_pks:
        payees = list(IndividualProfile.objects.filter(
            profile__user__is_active=True,
            profile__pk__in=ordered_user_pks
        ).values_list('profile__pk', flat=True))
        # ... but Individuals may also pay Good Causes
        if request.user.get_profile().is_individual_profile():
            payees.extend(list(CharityProfile.objects.filter(
                profile__user__is_active=True,
                profile__pk__in=ordered_user_pks
            ).values_list('profile__pk', flat=True)))
    else:
        payees = list(IndividualProfile.objects.filter(
            profile__user__is_active=True
        ).values_list('profile__pk', flat=True))
        # ... but Individuals may also pay Good Causes
        if request.user.get_profile().is_individual_profile():
            payees.extend(list(CharityProfile.objects.filter(
                profile__user__is_active=True
            ).values_list('profile__pk', flat=True)))

    return payees


# AJAX info views
def contact_name_auto(request, community=None):
    """
    Returns contact name with business for valid email address.
    Returns data for the autocomplete field.

    Data is formatted as lines with three columns separated by tabs:
        1. Completion data.
        2. Formatted data.
        3. URL.

    For Troeven the following rules apply:
    - Good Causes can pay Individuals (in their own Community)
    - Institutions can pay Individuals (in any Community)
    - Individuals can pay Individuals OR Good Causes (in their own Community)
    - Businesses don't pay direct

    https://support.community-currency.org/ticket/2815 requests Troeven solution
    be applied to Samen Doen
    """

    is_ajax = request.is_ajax()
    is_rest_framework = isinstance(request, RESTRequest)
    if not (is_ajax or is_rest_framework):
        return HttpResponseForbidden(_('This is only available to web pages'))

    contact_name_filter = request.GET.get('contact_name')
    min_contact_name_auto = getattr(settings, "CONTACT_AUTO_MINIMUM_CHARS", 1)
    if len(contact_name_filter) < min_contact_name_auto:
        return HttpResponse('[]', content_type='application/json')

    # if search term is only a number, return the card search
    try:
        contact_name_filter = int(contact_name_filter)
        return card_name_auto(request, community)
    except ValueError:
        pass

    # take a chance and remove anything after a bracket,
    # as likely to be business name returned by this function
    if '(' in contact_name_filter:
        contact_name_filter = contact_name_filter[:contact_name_filter.find(
            '(') - 1]

    # get candidate profile ids via raw SQL
    from django.db import connection
    cursor = connection.cursor()
    sql_string = """
        SELECT
            p.id FROM
                cyclos_cc3profile p JOIN

                profile_userprofile up ON
                    p.id = up.`cc3profile_ptr_id`
        WHERE

            TRIM(
                CONCAT(p.first_name, ' ',tussenvoegsel,(
                    CASE tussenvoegsel WHEN '' THEN '' ELSE ' ' END
                ),p.last_name)) LIKE %s
            OR p.business_name like %s

        ORDER BY
            p.last_name, TRIM(
                CONCAT(p.first_name, ' ', IFNULL(tussenvoegsel,'')));
    """

    cursor.execute(sql_string, [u"%{0}%".format(contact_name_filter),
                                u"%{0}%".format(contact_name_filter)])
    ordered_user_pks = [x[0] for x in cursor.fetchall()]

    payees = get_payees(request, ordered_user_pks)

    # NB UserProfile objects inherits from CC3Profile viewable, but excludes
    # good causes
    profiles = UserProfile.objects.filter(pk__in=payees)
    profiles = profiles.exclude(user=request.user).distinct()
    request_user = User.objects.get(pk=request.user.id)
    profile = request_user.get_profile()
    if community:
        inter_communities_transactions_allowed = \
            profile.inter_communities_transactions_allowed()
    else:
        inter_communities_transactions_allowed = True

    if not inter_communities_transactions_allowed:
        community = get_object_or_404(CC3Community, pk=community)
        if profile.community != community:
            # Users cannot perform operations in foreign communities.
            raise Http404

        profiles = profiles.filter(community=community)

    profile_names = list(profiles.distinct().values_list(
        'pk',
        'first_name',
        'tussenvoegsel',
        'last_name',
        'user__email',
        'user__pk',
        'business_name'
    ))
    user_pk_list = [profile_name_data[5] for profile_name_data in profile_names]

    # get user card data - order in reverse so dictionary conversion gets oldest
    card_data = Card.objects.filter(
        owner__pk__in=user_pk_list,
        status='A'
    ).values_list('owner__pk', 'number__number').order_by('-creation_date')
    card_number_dict = dict((a[0], a[1]) for a in card_data)

    data = []
    for (profile_pk, first_name, tussenvoegsel, last_name,
            email, user_pk, business_name) in profile_names:
        if business_name:
            appendage = u'{0} ({1})'.format(business_name, email)
        else:
            card_number = card_number_dict.get(user_pk, None)
            if card_number:
                bracketed_details = u"{0}, {1}".format(email, card_number)
            else:
                bracketed_details = email

            if tussenvoegsel.strip() != '':
                appendage = u'{0} {1} {2} ({3})'.format(
                    first_name, tussenvoegsel, last_name, bracketed_details)
            else:
                appendage = u'{0} {1} ({2})'.format(
                    first_name, last_name, bracketed_details)

        data.append({'pk': profile_pk, 'value': appendage})

    data.sort()
    json_data = json.dumps(data)

    return HttpResponse(json_data, content_type='application/json')


def card_name_auto(request, community=None):
    """
    Returns contact name with business for valid email address.
    Returns data for the autocomplete field (if search term has no spaces and
    numeric).

    Data is formatted as lines with three columns separated by tabs:
        1. Completion data.
        2. Formatted data.
        3. URL.
    """
    is_ajax = request.is_ajax()
    is_rest_framework = isinstance(request, RESTRequest)
    if not (is_ajax or is_rest_framework):
        return HttpResponseForbidden(_('This is only available to web pages'))

    contact_name_filter = request.GET.get('contact_name')
    contact_name_filter_check = "".join(
        [ch for ch in contact_name_filter if ch in digits])

    # ignore requests less than 4 chars and where not all digits
    if len(contact_name_filter) < 4 or (
            contact_name_filter != contact_name_filter_check):
        return HttpResponse('{}', content_type='application/json')

    payees = get_payees(request)

    profiles = UserProfile.objects.filter(pk__in=payees)
    user_pk_list = profiles.distinct().values('user_id')

    # get user card data - order in reverse so dictionary conversion gets oldest
    card_data = Card.objects.filter(
        owner__pk__in=user_pk_list,
        status='A',
        number__number__icontains=contact_name_filter
    ).values_list('owner__pk', 'number__number').order_by('-creation_date')
    card_number_dict = dict((a[0], a[1]) for a in card_data)

    # refresh the user_pk_list after the card filter
    user_pk_list = [a[0] for a in card_data]

    profiles = profiles.filter(user_id__in=user_pk_list)
    profiles = profiles.exclude(user=request.user).distinct().order_by(
        'first_name', 'last_name')
    request_user = User.objects.get(pk=request.user.id)
    profile = request_user.get_profile()
    if community:
        inter_communities_transactions_allowed = \
            profile.inter_communities_transactions_allowed()
    else:
        inter_communities_transactions_allowed = True

    if not inter_communities_transactions_allowed:
        community = get_object_or_404(CC3Community, pk=community)
        if request.user.cc3_profile.community != community:
            # Users cannot perform operations in foreign communities.
            raise Http404

        profiles = profiles.filter(community=community)

    profile_names = list(profiles.distinct().values_list(
        'pk',
        'first_name',
        'tussenvoegsel',
        'last_name',
        'user__email',
        'user__pk'
    ))

    data = []
    for e in profile_names:
        card_number = card_number_dict.get(e[5], None)
        if card_number:
            bracketed_details = u"{0}, {1}".format(e[4], card_number)
        else:
            bracketed_details = e[4]

        if e[2].strip() != '':
            appendage = u'{0} {1} {2} ({3})'.format(
                e[1], e[2], e[3], bracketed_details)
        else:
            appendage = u'{0} {1} ({2})'.format(
                e[1], e[3], bracketed_details)

        data.append({'pk': e[0], 'value': appendage})

    data.sort()
    json_data = json.dumps(data)

    return HttpResponse(json_data, content_type='application/json')
