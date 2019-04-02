import datetime
import logging

from django.contrib import messages
from django.contrib.messages.api import get_messages
from django.core.urlresolvers import reverse
from django.db.models import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from cc3.rewards.models import (UserCause, DefaultGoodCause)

from icare4u_front.stadlander.models import StadlanderProfile
from .models import IndividualProfile

from .utils import get_tandc_page_url, is_default_email

LOG = logging.getLogger('icare4u_front.profile.middleware')


class ProfileMiddleware(object):
    avoidable_views = [
        'StadlanderConfirmLinkDoneView',
        'StadlanderTermsAndConditionsFormView',
        'TermsAndConditionsFormView',
        'logout',
        'SelectCauseListView',
        'SearchCauseListView',
        'JoinCauseView',
        'EditProfileUpdateView',
    ]

    """
    causes_message = _('Save for yourself and for a savings goal of your '
                        'choice. Currently you save towards %(target). Do '
                        'you want to save for another savings goal? Then '
                        'select one of the following savings goals')
    """
    causes_message = _('Save for yourself and for a savings goal of your '
                       'choice. Do you want to save for another savings '
                       'goal? Then select one of the following savings '
                       'goals')

    terms_message = _('You must agree to the terms and conditions to start '
                      'using the site.')

    def _get_default_good_cause(self, user):
        cc3_community = user.cc3_profile.community

        try:
            def_good_cause = DefaultGoodCause.objects.get(
                community=cc3_community).cause

            return def_good_cause
        except DefaultGoodCause.DoesNotExist:
            LOG.critical(
                _(u"No default good cause exists for {0} community").format(
                    cc3_community))

    def _redirect_to_good_causes_view(self, request):
        """
        Checks if a given profile has selected any good cause to donate.
        Redirects to the good profile selection view if not.
        """
        redirect_to_good_causes = False
        try:
            UserCause.objects.get(consumer=request.user)
        except UserCause.DoesNotExist:
            redirect_to_good_causes = True

        if request.session.has_key('first_login') and \
                request.session['first_login']:
            redirect_to_good_causes = True

        if redirect_to_good_causes:
            default_good_cause = self._get_default_good_cause(request.user)

            get_messages(request).used = True  # Clean messages list.
            messages.add_message(
                request, messages.SUCCESS, self.causes_message % {
                    'target': default_good_cause})

            # unflag this redirect so it doesn't happen again
            request.session['first_login'] = False

            return HttpResponseRedirect(reverse('causes_list'))

    def _redirect_to_profile_update_view(self, request):
        """
        Checks if a given profile has a *@example.com email address.
        Redirects to the profile update view if it is the case
        """
        if is_default_email(request.user.email):
            request.session['must_update_profile'] = True
            return HttpResponseRedirect(reverse('profile_update'))

    def _redirect_to_terms_view(self, request, profile, tandc_url):
        """
        Checks if a given profile has accepted the site terms and conditions.
        Redirects to the terms and conditions view if not except if
        the requested URL matches that of CMS page that contains terms and
        conditions text.
        """
        if not profile.terms_and_conditions:
            if request.get_full_path() != tandc_url:
                # https://support.community-currency.org/ticket/3487
                # no longer want to show error before form save
                # get_messages(request).used = True  # Clean messages list.
                # messages.add_message(request, messages.ERROR,
                # self.terms_message)
                # check if user has a Stadlander profile
                try:
                    stadlander_profile = StadlanderProfile.objects.get(
                        profile=profile)
                except:
                    stadlander_profile = None

                if stadlander_profile:
                    return HttpResponseRedirect(
                        reverse('terms_and_conditions_agreement_stadlander'))
                else:
                    return HttpResponseRedirect(
                        reverse('terms_and_conditions_agreement'))

    def process_view(self, request, view_func, view_args, view_kwargs):
        response = None

        if view_func.func_name not in self.avoidable_views:
            if request.user.is_authenticated() and not \
                    request.user.is_superuser:
                try:
                    profile = request.user.cc3_profile.userprofile
                except ObjectDoesNotExist:
                    return

                if request.is_ajax():
                    return response

                try:
                    IndividualProfile.objects.get(profile=profile)
                    tandc_url = get_tandc_page_url()

                    response = self._redirect_to_terms_view(
                        request, profile, tandc_url)

                    if not response and request.get_full_path() != tandc_url:
                        response = \
                            self._redirect_to_profile_update_view(request)

                    if not response and request.get_full_path() != tandc_url:
                        response = self._redirect_to_good_causes_view(request)

                except IndividualProfile.DoesNotExist:
                    try:
                        StadlanderProfile.objects.get(profile=profile)

                        response = self._redirect_to_good_causes_view(request)
                        if not response:
                            response = self._redirect_to_terms_view(
                                request, profile)
                    except StadlanderProfile.DoesNotExist:
                        pass

        return response
