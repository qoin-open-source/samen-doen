from registration.models import RegistrationProfile

from django.contrib.sites.models import RequestSite

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.timezone import now as datetime_now
from django.utils.translation import ugettext_lazy as _
from django.apps import apps


from icare4u_front.profile.models import IndividualProfile
from django.contrib.auth.forms import PasswordResetForm


@login_required
@permission_required('is_staff')
def community_admin_close_account(request, pk):

    # check pk is valid
    individual = get_object_or_404(IndividualProfile, pk=pk)

    # close account
    individual.profile.close_account()

    # return to list view with success message
    messages.info(request, _(u'{0} account successfully closed').format(
        individual.profile
    ))

    return HttpResponseRedirect(
        reverse('community_admin:profile_userprofile_changelist'))


@login_required
@permission_required('is_staff')
def community_admin_resend_activation(request, pk):
    # check pk is valid
    individual = get_object_or_404(IndividualProfile, pk=pk)

    # 2827
    user_profile = individual.profile
    user = user_profile.user
    registration_profile = None

    try:
        registration_profile = RegistrationProfile.objects.get(
            user__email=user.email)
    except RegistrationProfile.DoesNotExist:
        messages.error(
            request, _(u'{0} cannot resend activation, user has no '
                       u'Registration Profile').format(individual.profile))
        return HttpResponseRedirect(
            'community_admin:profile_userprofile_changelist')

    # reset date_joined, so that existing
    # registration profile mechanism logic is retained

    # save original date if not already saved
    if user_profile.original_date_joined is None:
        user_profile.original_date_joined = user.date_joined
        user_profile.save()

    # reset date_joined, so that activation can work
    user.date_joined = datetime_now()
    user.save()

    if apps.is_installed('django.contrib.sites'):
        site = apps.get_model('sites', 'Site').objects.get_current()
    else:
        site = RequestSite(request)

    if not RegistrationProfile.objects.resend_activation_mail(
            user.email, site, request):

        if registration_profile.activated:

            messages.error(request, _(u'{0} cannot resend activation, '
                                      u'user already has active Registration '
                                      u'Profile').format(individual.profile))
        else:
            messages.error(request, _(u'{0} cannot resend activation, unknown '
                                      u'error').format(individual.profile))

        return HttpResponseRedirect(
            'community_admin:profile_userprofile_changelist')

    # return to list view with success message
    messages.info(request, _(u'{0} activation successfully resent').format(
        individual.profile
    ))

    return HttpResponseRedirect(
        'community_admin:profile_userprofile_changelist')


@login_required
@permission_required('is_staff')
def community_admin_reset_email(request):
    """
    REST endpoint to reset a user's password given their email address
    """
    if 'email' in request.GET and request.GET['email'] is not None:
        email = request.GET['email']
        reset_form = PasswordResetForm({'email': email})
        if reset_form.is_valid():
            reset_form.save()
            # return to list view with success message
            messages.info(request, _(u'Reset password email sent to {}').format(
                email))
        else:
            # return to list view with success message
            messages.info(request, _(u'Failed to send password reset email'))
    else:
        # return to list view with success message
        messages.info(request, _(u'Failed to send password reset email'))

    return HttpResponseRedirect(
        reverse('community_admin:profile_userprofile_changelist'))

