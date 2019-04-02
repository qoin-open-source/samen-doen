# encoding: utf-8
import logging
import mimetypes
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse, reverse_lazy
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView, UpdateView
from django.views.generic.detail import BaseDetailView

from braces.views import SuperuserRequiredMixin

from cc3.communityadmin.views import CommunityMixin

from icare4u_front.stadlander.models import StadlanderProfile
from .forms import (
    TermsAndConditionsForm, CommunityBusinessProfileForm,
    CommunityIndividualProfileForm, CommunityInstitutionProfileForm,
    CommunityCharityProfileForm, StadlanderTermsAndConditionsForm)
from .models import (UserProfile, IndividualProfile, BusinessProfile,
                     InstitutionProfile, CharityProfile, SEPAXMLFile)
from .utils import get_tandc_page_url

LOG = logging.getLogger(__name__)


class TermsAndConditionsFormView(UpdateView):
    """
    Ask user to agree to terms and conditions before allowing to continue in
    the site.
    """
    template_name = 'profile/user_profile_terms_and_conditions_form.html'

    def get_success_url(self):
        return reverse('accounts_home')

    def get_object(self, queryset=None):
        try:
            profile = UserProfile.objects.get(
                user__username=self.request.user)

            # Now save the profile as a class attribute to be used everywhere.
            self.profile = profile
        except UserProfile.DoesNotExist:
            raise Http404

        profile_type, obj = profile.get_profile_type(include_profile=True)
        if not obj:
            return Http404

        return obj

    def get_initial(self):
        data = model_to_dict(self.object)
        data.update(model_to_dict(self.object.profile.user))
        data.update(model_to_dict(self.object.profile))

        return data

    def get_form(self, form_class=None):
        return TermsAndConditionsForm(**self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super(
            TermsAndConditionsFormView, self).get_context_data(**kwargs)

        # Pass the URL of the terms and conditions CMS page to the template
        context['tandc_url'] = get_tandc_page_url()
        context['cc3_profile'] = self.profile

        return context


class StadlanderTermsAndConditionsFormView(FormView):
    """
    Ask user to agree to terms and conditions before allowing to continue in
    the site.
    """
    template_name = 'profile/stadlander_terms_and_conditions_form.html'
    success_url = reverse_lazy('accounts_home')

    def get_form(self, form_class):
        try:
            cc3_profile = UserProfile.objects.get(user=self.request.user)
        except UserProfile.DoesNotExist:
            cc3_profile = None

        return StadlanderTermsAndConditionsForm(
            instance=cc3_profile, **self.get_form_kwargs())

    def form_valid(self, form):
        form.save()
        return super(StadlanderTermsAndConditionsFormView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(StadlanderTermsAndConditionsFormView, self).get_context_data(**kwargs)
        # Pass the URL of the terms and conditions CMS page to the template
        context['tandc_url'] = get_tandc_page_url()
        return context


class ProfileUpdateView(UpdateView):
    """
    Generic class to update member profiles.
    """
    profile = None

    def get_initial(self):
        data = model_to_dict(self.object)
        data.update(model_to_dict(self.object.profile.user))
        data.update(model_to_dict(self.object.profile))

        return data

    def get_form(self, form_class=None):
        if isinstance(self.object, IndividualProfile):
            return CommunityIndividualProfileForm(**self.get_form_kwargs())
        elif isinstance(self.object, BusinessProfile):
            return CommunityBusinessProfileForm(**self.get_form_kwargs())
        elif isinstance(self.object, InstitutionProfile):
            return CommunityInstitutionProfileForm(**self.get_form_kwargs())
        elif isinstance(self.object, CharityProfile):
            return CommunityCharityProfileForm(**self.get_form_kwargs())
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super(ProfileUpdateView, self).get_context_data(**kwargs)

        context['cc3_profile'] = self.profile

        # default map center north pole or there abouts
        context['map_centre_lat'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LAT', 0)
        context['map_centre_lng'] = getattr(
            settings, 'MARKETPLACE_MAP_CENTER_LNG', 0)
        return context


class EditProfileUpdateView(ProfileUpdateView):
    """
    Users personal profile edition view.
    """
    template_name = 'accounts/update_my_profile.html'
    success_url = reverse_lazy('accounts-update-profile')

    def __init__(self, **kwargs):
        # allow it to work with Django 1.8 - specify a fields attribute
        self.fields = ()
        super(EditProfileUpdateView, self).__init__(**kwargs)

    def get(self, request, *args, **kwargs):

        # if the user must update their profile, set the appropriate message
        if request.session.get('must_update_profile', False):
            messages.add_message(
                self.request, messages.WARNING,
                _('You must complete your profile'))

        return super(EditProfileUpdateView, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        try:
            profile = UserProfile.objects.get(
                user__username=self.request.user)

            # Now save the profile as a class attribute to be used everywhere.
            self.profile = profile
        except UserProfile.DoesNotExist:
            raise Http404

        profile_type, obj = profile.get_profile_type(include_profile=True)
        if not obj:
            return Http404

        return obj

    def form_valid(self, form):
        form.cleaned_data[
            'web_payments_enabled'] = self.profile.web_payments_enabled
        r = super(EditProfileUpdateView, self).form_valid(form)
        if 'must_update_profile' in self.request.session:
            del self.request.session['must_update_profile']
            return HttpResponseRedirect(reverse('accounts_home'))
        return r


class CommunityAdminEditProfileUpdateView(CommunityMixin, ProfileUpdateView):
    """
    Community admins users profile edition view.
    """
    template_name = 'communityadmin/edit_member.html'
    success_url = reverse_lazy('communityadmin_ns:memberlist')
    profile = None

    def __init__(self, **kwargs):
        # allow it to work with Django 1.8 - specify a fields attribute

        self.fields = ()
        super(CommunityAdminEditProfileUpdateView, self).__init__(**kwargs)

    def get_object(self, queryset=None):
        try:
            profile = UserProfile.objects.get(
                user__username=self.kwargs['username'])

            # Now save the profile as a class attribute to be used everywhere.
            self.profile = profile
        except UserProfile.DoesNotExist:
            raise Http404

        profile_type, obj = profile.get_profile_type(include_profile=True)
        if not obj:
            return Http404

        return obj

    def get_context_data(self, **kwargs):
        context = super(
            CommunityAdminEditProfileUpdateView, self).get_context_data(
                **kwargs)

        try:
            cyclos_id = self.profile.cyclos_account.cyclos_id

            comms = '/do/admin/flatMemberRecords?global=false&elementId={0}' \
                    '&typeId=1'.format(cyclos_id)
            context['comms_url'] = settings.CYCLOS_FRONTEND_URL + comms

            limit = '/do/admin/editCreditLimit?memberId={0}'.format(cyclos_id)
            context['limit_url'] = settings.CYCLOS_FRONTEND_URL + limit
        except ObjectDoesNotExist:
            context['comms_url'] = ''
            context['limit_url'] = ''

        return context


class CreateProfileSelectView(CommunityMixin, TemplateView):
    """
    Offers the community admin user to select which kind of profile he wants to
    create: ``BusinessProfile``, ``IndividualProfile`` or Good cause.
    """
    template_name = 'communityadmin/create_profile_select.html'


class CreateIndividualProfile(CommunityMixin, FormView):
    """
    Shows a form to create a ``BusinessProfile`` from the community admin.
    """
    form_class = CommunityIndividualProfileForm
    template_name = 'communityadmin/create_member.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:memberlist')

    def get_context_data(self, **kwargs):
        context = super(CreateIndividualProfile, self).get_context_data(
            **kwargs)

        context['individual'] = True
        return context

    def form_valid(self, form):
        form.save()
        messages.info(
            self.request, _('Individual Profile successfully created'))

        return super(CreateIndividualProfile, self).form_valid(form)


class CreateBusinessProfile(CommunityMixin, FormView):
    """
    Shows a form to create a ``BusinessProfile`` from the community admin.
    """
    form_class = CommunityBusinessProfileForm
    template_name = 'communityadmin/create_member.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:memberlist')

    def get_context_data(self, **kwargs):
        context = super(CreateBusinessProfile, self).get_context_data(
            **kwargs)

        context['business'] = True

        return context

    def form_valid(self, form):
        form.save()
        messages.info(self.request, _('Business Profile successfully created'))

        return super(CreateBusinessProfile, self).form_valid(form)


class CreateInstitutionProfile(CommunityMixin, FormView):
    """
    Shows a form to create a ``InstitutionProfile`` from the community admin.
    """
    form_class = CommunityInstitutionProfileForm
    template_name = 'communityadmin/create_member.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:memberlist')

    def form_valid(self, form):
        form.save()
        messages.info(self.request,
                      _('Institution Profile successfully created'))

        return super(CreateInstitutionProfile, self).form_valid(form)


class CreateCharityProfile(CommunityMixin, FormView):
    """
    Shows a form to create a ``CharityProfile`` from the community admin.
    """
    form_class = CommunityCharityProfileForm
    template_name = 'communityadmin/create_member.html'

    def get_success_url(self):
        return reverse('communityadmin_ns:memberlist')

    def form_valid(self, form):
        form.save()
        messages.info(self.request, _('Charity Profile successfully created'))

        return super(CreateCharityProfile, self).form_valid(form)


class SEPAXMLFileView(SuperuserRequiredMixin, BaseDetailView):
    model = SEPAXMLFile

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        sepaxmlfile = self.get_object().file
        path = sepaxmlfile.path
        wrapper = FileWrapper(open(path, "r"))
        content_type = mimetypes.guess_type(path)[0]

        response = HttpResponse(wrapper, content_type=content_type)
        response['Content-Length'] = os.path.getsize(path)
        response['Content-Disposition'] = 'attachment; filename={0}'.format(
            smart_str(os.path.basename(path)))

        return response


@login_required
@permission_required('is_superuser')
def admin_close_account(request, pk):

    # check pk is valid
    individual = get_object_or_404(IndividualProfile, pk=pk)

    # close account
    individual.profile.close_account()

    # return to list view with success message
    messages.info(request, _('{0} account successfully closed'.format(
        individual.profile
    )))

    return HttpResponseRedirect(
        reverse('admin:profile_individualprofile_changelist'))
