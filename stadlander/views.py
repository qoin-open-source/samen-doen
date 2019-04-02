import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseBadRequest)
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import FormView

from .forms import (PAPIForm, StadlanderPayDirectForm,
                    StadlanderAdForm, StadlanderLinkAccountsForm)
from .utils import check_papi_key

from cc3.accounts.views import PayDirectFormView
from cc3.marketplace.views import (
    MarketplaceAdCreateView, MarketplaceAdUpdateView
)
from cc3.cyclos import backends
from cc3.cyclos.common import TransactionException
from cc3.cyclos.models import User, CyclosGroupSet
from cc3.core.models import Transaction
from cc3.core.views import DirectTemplateView

from .models import AdRewardCategory, StadlanderProfile, PotentialLinkFound
from icare4u_front.profile.models import UserProfile

LOG = logging.getLogger(__name__)


@never_cache
def login(request, template_name='stadlander/login.html',
          redirect_field_name=None,
          authentication_form=PAPIForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    Only return a response to the user if they need to accept
    terms and conditions

    otherwise if not authenticated, return to Stadlander,
    or if authenticated and t&c ticked for user, redirect to accounts_home
    (or LOGIN_REDIRECT_URL?)

    :param request:
    :param template_name:
    :param redirect_field_name:
    :param authentication_form:
    :param current_app:
    :param extra_context:
    :return:
    """

    # ignore next for redirect_to [see original django login view]

    redirect_to = getattr(
        settings, 'LOGIN_REDIRECT_URL', reverse('accounts_home'))

    # however, if the account has just been linked, use the
    # confirm_link_done view
    if request.GET.has_key('justlinked'):
        redirect_to = reverse('stadlander_confirm_link_done')

    LOG.debug("Stadlander login: if successful, "
              "will redirect to {0}".format(redirect_to))

    # NB django login view uses POST, we're using GET here as
    # PAPI key is in query string
    if 'papi' in request.GET:
        form = authentication_form(data=request.GET)

        try:
            if form.is_valid():
                auth_login(request, form.get_user())

                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

                # TODO add check if user has checked the terms and conditions
                # (if auth form has created a new user,
                # need a default of t&c not checked)
                LOG.info("Stadlander login successful, "
                         "redirecting to {0}".format(redirect_to))
                return HttpResponseRedirect(redirect_to)
        except PotentialLinkFound:
            # Have found a SD user with matching email address: redirect to the
            # confirmation form so user can choose to link accounts
            papi = request.GET['papi']
            LOG.info(u"Stadlander login, potential link found: "
                     u"papi={0}".format(papi))
            confirmation_form = reverse(
                'stadlander_confirm_link', kwargs={'papi': papi})
            return HttpResponseRedirect(confirmation_form)
    else:
        form = authentication_form()

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'STADLANDER_LOGIN_URL': settings.STADLANDER_LOGIN_URL
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


class StadlanderLinkAccountsFormView(FormView):
    template_name = 'stadlander/confirm_link.html'
    form_class = StadlanderLinkAccountsForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.papi = kwargs['papi']
            self.sl_items = check_papi_key(self.papi)
            self.link_user = User.objects.get(email=self.sl_items['mail'])
            LOG.info(u"Offering to link existing user {0} "
                     u"to rel_number {1}".format(self.link_user.username,
                                                 self.sl_items['rel_number']))
        except Exception as e:
            LOG.exception(e)
            LOG.error("Stadlander account link form call was invalid")

            # TODO something better?
            return HttpResponseBadRequest('Invalid request')
        return super(StadlanderLinkAccountsFormView, self).dispatch(
            request, *args, **kwargs)

    def get_success_url(self):
        return "{0}?papi={1}&justlinked=1".format(reverse('stadlander_login'),
                                                  self.papi)

    def form_valid(self, form):
        """
        If the 'Yes' button was submitted, create the SL profile to link
        the accounts. If 'No', redirect to appropriate page
        """
        if 'link_yes' in form.data:
            LOG.info("Offer to link account ACCEPTED")

            # create SL profile to link the accounts
            user_profile = self.link_user.get_profile()
            # If user has a good cause already, leave it alone;
            # if not, use the default one for their comminuty
            user_profile.individual_profile.set_good_cause()
            rel_number = self.sl_items['rel_number']
            user_profile.create_new_stadlander_profile(rel_number=rel_number)
            # change groupset to Stadlander groupset
            LOG.debug("Linking accounts: groupset was {0}".format(
                user_profile.groupset))
            user_profile.groupset = CyclosGroupSet.objects.get(
                pk=settings.STADLANDER_GROUPSET_ID)
            user_profile.save()
            LOG.debug("Linking accounts: updated groupset to {0}".format(
                user_profile.groupset))

            # now log in that user via the normal route
            login_url = self.get_success_url()

            return HttpResponseRedirect(login_url)
        elif 'link_no' in form.data:
            LOG.info("Offer to link account DECLINED")
            return HttpResponseRedirect(
                reverse('stadlander_confirm_link_refused'))

        LOG.error("StadlanderLinkAccountsFormView: shouldn't get here")

        return super(StadlanderLinkAccountsFormView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(
            StadlanderLinkAccountsFormView, self).get_context_data(**kwargs)
        context['username'] = self.link_user.username
        context['full_name'] = self.link_user.get_profile().full_name
        context['email'] = self.link_user.email
        return context


def icare4u_password_reset(request):
    """
    Wrap password change form so we can prevent Stadlander users from changing
    their password
    :param request:
    :return:
    """
    pass


class StadlanderCheckPayDirectFormView(PayDirectFormView):

    def dispatch(self, request, *args, **kwargs):
        try:
            user_profile = self.request.user.get_profile()
            # prevent stadlander tenants from accessing the standard
            # pay direct view
            if user_profile.is_stadlander_sso_user():
                return HttpResponseRedirect(reverse('stadlander_pay_direct'))
        except UserProfile.DoesNotExist:
            # ignore UserProfile does not exist errors -
            # these only happen during tests if data is ok
            pass

        return super(StadlanderCheckPayDirectFormView, self).dispatch(
            request, *args, **kwargs)


class StadlanderPayDirectFormView(FormView):
    template_name = 'stadlander/pay_direct.html'
    success_url = reverse_lazy('accounts_pay_direct')
    form_class = StadlanderPayDirectForm

    def get_form(self, form_class):
        """
        Overrides the base ``get_form`` method. Returns a form initialised with
        the user info for credit check.
        """
        cc3_profile = self.request.user.get_cc3_profile()

        if cc3_profile and cc3_profile.web_payments_enabled:
            kwargs = self.get_form_kwargs()
            kwargs['user'] = self.request.user
            return form_class(**kwargs)
        return None

    def _perform_payment(self, data):
        sender = self.request.user
        receiver = data['profile'].user
        amount = data['amount']

        description_elements = []

        reward_category = data.get('reward_category', None)
        reward_category_quantity = data.get('reward_category_quantity', None)
        other_activity = data.get('other_activity', None)
        other_activity_quantity = data.get('other_activity_quantity', None)
        bonus = data.get('bonus', None)

        if reward_category:
            description_elements.append(
                (reward_category, reward_category_quantity))

        if other_activity:
            description_elements.append(
                (other_activity, other_activity_quantity))

        if bonus:
            description_elements.append(
                (u'bonus', bonus))

        description = u"".join(
            [u"{0} ({1}) | ".format(
                description_element[0], description_element[1])
             for description_element in description_elements])

        description = description[:-3]  # knock off last pipe

        try:
            # Cyclos transaction request.
            transaction = backends.user_payment(
                sender, receiver, amount, description)
            # Log the payment
            Transaction.objects.create(
                amount=amount,
                sender=sender,
                receiver=receiver,
                transfer_id=transaction.transfer_id,
            )
            messages.add_message(
                self.request, messages.SUCCESS,
                _('Payment made successfully.'))
        except TransactionException, e:
            error_message = _('Could not make payment at this time.')

            if 'NOT_ENOUGH_CREDITS' in e.args[0]:
                error_message = _('You do not have sufficient credit to '
                                  'complete the payment plus the '
                                  'transaction fee.')
            messages.add_message(self.request, messages.ERROR, error_message)

    def form_valid(self, form):
        # prevent duplicate payments if using modal dialog box
        # with confirmation (and timeout for double clicks)
        if self.request.is_ajax():
            # if we're dealing with ajax, wait for 2nd submit,
            # where POST has 'confirmed key'
            if not ('confirmed' in self.request.POST):
                data = json.dumps({
                    'success': True,
                    'full_name': form.cleaned_data['profile'].full_name})
                return HttpResponse(data, {
                    'content_type': 'application/json',
                })

        self._perform_payment(form.cleaned_data)

        return super(StadlanderPayDirectFormView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            data = json.dumps(form.errors)
            response_kwargs = {
                'status': 400,
                'content_type': 'application/json'
            }
            return HttpResponse(data, **response_kwargs)

        return super(StadlanderPayDirectFormView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(
            StadlanderPayDirectFormView, self).get_context_data(**kwargs)
        context['stadlander_minutes_to_punten'] = getattr(
            settings, "STADLANDER_MINUTES_TO_PUNTEN", 10)
        context['min_contact_auto'] = getattr(
            settings, "CONTACT_AUTO_MINIMUM_CHARS", 1)
        return context


class StadlanderCheckAdCreateView(MarketplaceAdCreateView):
    success_url = reverse_lazy('accounts_my_ads')

    def dispatch(self, request, *args, **kwargs):
        try:
            user_profile = self.request.user.get_profile()
            # prevent stadlander tenants from accessing the standard
            # pay direct view
            if user_profile.is_stadlander_sso_user():
                return HttpResponseRedirect(reverse('stadlander_place_ad'))
        except UserProfile.DoesNotExist:
            # ignore UserProfile does not exist errors -
            # these only happen during tests if data is ok
            pass

        return super(StadlanderCheckAdCreateView, self).dispatch(
            request, *args, **kwargs)


class StadlanderAdCreateView(MarketplaceAdCreateView):
    template_name = 'stadlander/place_ad.html'
    form_class = StadlanderAdForm

    def post(self, request, *args, **kwargs):
        from .actions import PayStadlander

        return_val = super(StadlanderAdCreateView, self).post(
            request, *args, **kwargs)
        if self.object:
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            if form.is_valid():
                for reward_category in form.cleaned_data['reward_category']:
                    AdRewardCategory.objects.create(
                        ad=self.object,
                        reward_category=reward_category
                    )
                    ads_in_reward_category = AdRewardCategory.objects.filter(
                        ad__created_by=self.object.created_by,
                        reward_category=reward_category
                    ).count()
                    if ads_in_reward_category == 1:
                        user_profile = self.request.user.get_profile()
                        sso_profile = StadlanderProfile.objects.get(
                            profile=user_profile
                        )
                        amount = getattr(
                            settings, "STADLANDER_AD_REWARD_AMOUNT", 25)
                        description = getattr(
                            settings, "STADLANDER_AD_REWARD_DESCRIPTION", None)
                        reward_category_title = reward_category.title
                        if not description:
                            description = u'Waardering voor het plaatsen van ' \
                                          u'uw eerste advertentie in de ' \
                                          u'categorie {0}'.format(
                                              reward_category_title)
                        else:
                            description = description.format(
                                reward_category_title)
                        # make reward payment
                        action = PayStadlander().perform(
                            persoonsnummer=sso_profile.rel_number,
                            amount=amount,
                            description=description,
                            sender=getattr(
                                settings,
                                "STADLANDER_AD_REWARD_SENDER",
                                'stadlander'
                            )
                        )
                        messages.add_message(request, messages.INFO, _(
                            u"U heeft van Stadlander {0} Positoos waardering "
                            u"gekregen omdat u een advertentie in de "
                            u"Stadlander categorie '{1}' heeft geplaatst"
                        ).format(amount, reward_category_title))

                        LOG.info(
                            "AdRewardCategory made payment: {0}".format(action))

        return return_val

    def get_context_data(self, **kwargs):
        context = super(
            StadlanderAdCreateView, self).get_context_data(**kwargs)
        context['reward_amount'] = getattr(
            settings, "STADLANDER_AD_REWARD_AMOUNT", 10)
        return context


class StadlanderCheckAdUpdateView(MarketplaceAdUpdateView):
    def dispatch(self, request, *args, **kwargs):
        user_profile = self.request.user.get_profile()
        # prevent stadlander tenants from accessing the standard pay direct view
        if user_profile.is_stadlander_sso_user():
            return HttpResponseRedirect(
                reverse('stadlander_edit_ad', kwargs={'pk': kwargs['pk']}))

        return super(StadlanderCheckAdUpdateView, self).dispatch(
            request, *args, **kwargs)


class StadlanderAdUpdateView(MarketplaceAdUpdateView):
    template_name = 'stadlander/edit_ad.html'
    form_class = StadlanderAdForm

    def post(self, request, *args, **kwargs):

        return_val = super(StadlanderAdUpdateView, self).post(
            request, *args, **kwargs)
        if self.object:
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            if form.is_valid():
                old_ad_reward_categories = AdRewardCategory.objects.filter(
                    ad=self.object
                )
                old_ad_reward_categories.delete()
                # save fresh reward categories
                for reward_category in form.cleaned_data['reward_category']:
                    AdRewardCategory.objects.create(
                        ad=self.object,
                        reward_category=reward_category
                    )

        return return_val


class StadlanderConfirmLinkDoneView(DirectTemplateView):
    pass
