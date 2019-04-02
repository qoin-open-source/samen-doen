"""
URL patterns for the views included in ``icare4u_front.auth``.

* User login at ``login/``.

This performs the 'SSO' (single sign on) functionality
"""

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from cc3.core.views import DirectTemplateView

from .views import (
    login, StadlanderPayDirectFormView, StadlanderAdCreateView,
    StadlanderAdUpdateView, StadlanderLinkAccountsFormView,
    StadlanderConfirmLinkDoneView)


urlpatterns = patterns(
    '',
    # override the default login mechanism
    url(r'^login/$', login, name='stadlander_login'),
    url(r'^pay-direct/$', login_required(StadlanderPayDirectFormView.as_view()),
        name='stadlander_pay_direct'),
    url(r'^place-ad/$', login_required(StadlanderAdCreateView.as_view()),
        name='stadlander_place_ad'),
    url(r'^edit-ad/(?P<pk>\d+)/$',
        login_required(StadlanderAdUpdateView.as_view()),
        name='stadlander_edit_ad'),
    url(r'^confirm-link/done/$',
        StadlanderConfirmLinkDoneView.as_view(
            template_name='stadlander/confirm_link_done.html'),
        name='stadlander_confirm_link_done'),
    url(r'^confirm-link/(?P<papi>\w+)/$',
        StadlanderLinkAccountsFormView.as_view(
            template_name='stadlander/confirm_link.html'),
        name='stadlander_confirm_link'),
    url(r'^no-link/$',
        DirectTemplateView.as_view(
            template_name='stadlander/confirm_link_refused.html'),
        name='stadlander_confirm_link_refused'),
)
