import logging

from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, NoReverseMatch
from django.views.generic.base import RedirectView
from django.utils.translation import ugettext_lazy as _

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes

from ajax_select import urls as ajax_select_urls

from icare4u_front.community_admin.admin import admin_site

from icare4u_front.profile.views import (
    CommunityAdminEditProfileUpdateView, EditProfileUpdateView)
from stadlander.forms import (
    ICare4uPasswordResetForm, ICare4uPasswordChangeForm,
    ICare4uAuthenticationForm)
from .custom.views import (ICare4uCampaignView,
    ICare4uBusinessView, ICare4uBusinessMapView, ICare4uMarketplaceView,
    ICare4uMarketplaceSearchView, contact_name_auto, card_name_auto,
    ICare4uCampaignCreateView,
)
from stadlander.views import (
    StadlanderCheckPayDirectFormView, StadlanderCheckAdCreateView,
    StadlanderCheckAdUpdateView
)
from cc3.accounts.decorators import must_have_completed_profile

LOG = logging.getLogger(__name__)


handler500 = 'cc3.core.views.server_error'

admin.autodiscover()


def is_loaded(url_name):
    try:
        reverse(url_name)
        return True
    except NoReverseMatch:
        return False


urlpatterns = patterns(
    '',
    url(r'^500/$', 'django.views.defaults.server_error'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('django.contrib.auth.urls')),

    url(r'^tinymce/', include('tinymce.urls')),
#    url(r'^rosetta/', include('rosetta.urls')),

    # API endpoints.
    # url(r'^api/comm/', include('cc3.communityadmin.urls_api')),
    url(r'^api/', include('cc3.core.urls_api')),
    url(r'^api/auth/', include('djoser.urls')),
    url(r'^api/rekeningen/', include('cc3.accounts.urls_api')),
    url(r'^api/marketplace/', include('cc3.marketplace.urls_api')),
    url(r'^api/v1/cards/', include('cc3.cards.urls_api')),
    url(r'^api/v1/rewards/', include('cc3.rewards.urls_api')),
    url(r'^api/v1/files/', include('cc3.files.urls_api')),

    url(_(r'^api/rekeningen/contact_name_auto/$'),
        api_view(['GET', ])(permission_classes([permissions.IsAuthenticated, ])(
            contact_name_auto)),
        name='api_contact_name_auto'),
    url(_(r'^api/rekeningen/contact_name_auto/(?P<community>\d+)/$'),
        api_view(['GET', ])(permission_classes([permissions.IsAuthenticated, ])(
            contact_name_auto)),
        name='api_contact_name_auto'),
    url(_(r'^api/rekeningen/card_name_auto/(?P<community>\d+)/$'),
        api_view(['GET', ])(permission_classes([permissions.IsAuthenticated, ])(
            card_name_auto)),
        name='api_card_name_auto'),

    url(r'^ajax_select', include(ajax_select_urls)),
)

urlpatterns += i18n_patterns(
    '',
    url(r'^login/$', auth_views.login,
        {'template_name': 'registration/login.html',
         'authentication_form': ICare4uAuthenticationForm},
        name='auth_login'),
    url(r'^password_reset/$', auth_views.password_reset,
        {'password_reset_form': ICare4uPasswordResetForm},
        name="auth_password_reset"),
    url(r'^password_change/$', auth_views.password_change,
        {'password_change_form': ICare4uPasswordChangeForm},
        name="auth_password_change"),
    url(r'^', include('cc3.registration.backends.icare4u.urls')),

    # Profile terms and conditions and registration view
    url(r'^', include('icare4u_front.profile_registration.urls')),
    url(r'^', include('icare4u_front.profile.urls')),
    url(r'^community_admin/', include('icare4u_front.community_admin.urls')),

    url(r'^', include('cc3.core.urls')),

    # TODO: USE dynamic cc3.accounts root url rather than hard coded accounts
    # to avoid issues if DjangoCMS apphook page url changes accounts to dutch
    # equivalent.
    url(_(r'^rekeningen/profile/$'), login_required(
        EditProfileUpdateView.as_view()), name='profile_update'),
    url(r'^rekeningen/pay-direct/$',
        login_required(must_have_completed_profile(
            StadlanderCheckPayDirectFormView.as_view())),
        name='stadlander_pay_direct_check'),
    url(_(r'^rekeningen/place-ad/$'),
        login_required(StadlanderCheckAdCreateView.as_view()),
        name='accounts_place_ad'),
    url(_(r'^rekeningen/edit-ad/(?P<pk>\d+)/$'),
        login_required(StadlanderCheckAdUpdateView.as_view()),
        name='accounts_edit_ad'),
    # override contact name auto, to mask pending members
    url(_(r'^rekeningen/contact_name_auto/$'),
        login_required(must_have_completed_profile(contact_name_auto)),
        name='contact_name_auto'),
    url(_(r'^rekeningen/contact_name_auto/(?P<community>\d+)/$'),
        login_required(must_have_completed_profile(contact_name_auto)),
        name='contact_name_auto'),
    url(_(r'^rekeningen/card_name_auto/(?P<community>\d+)/$'),
        login_required(must_have_completed_profile(card_name_auto)),
        name='card_name_auto'),

    # custom versions of create/edit campaign
    url(r'^rekeningen/new-activity/$',
        login_required(must_have_completed_profile(
            ICare4uCampaignCreateView.as_view())),
        name='accounts-new-campaign'),

    url(r'^comm/editmember/(?P<username>\w+)/$',
        CommunityAdminEditProfileUpdateView.as_view(), name='editmember'),
    url(r'^comm/', include('cc3.communityadmin.urls',
                           namespace='communityadmin_ns')),
    url(r'^cards/', include('cc3.cards.urls')),
    url(r'^rewards/', include('cc3.rewards.urls')),
    url(r'^community_admin/', include(admin_site.urls)),
    url(r'^content/', include('cc3.cmscontent.urls')),
    url(r'^billing/', include('cc3.billing.urls')),

    # stadlander login for SSO
    url(r'^stadlander/', include('icare4u_front.stadlander.urls')),

    # override marketplace view to use custom views
    # also, for SD, marketplace 'home' is profiles, not ads
    url(r'^vraagenaanbod/$', ICare4uBusinessView.as_view()),
    url(r'^vraagenaanbod/ads/$', ICare4uMarketplaceView.as_view()),
    url(r'^vraagenaanbod/search/$', ICare4uMarketplaceSearchView.as_view()),
    url(r'^vraagenaanbod/profielen/$', ICare4uBusinessView.as_view()),
    url(r'^vraagenaanbod/activities/$', ICare4uCampaignView.as_view()),
    url(r'^vraagenaanbod/profielen/map/$', ICare4uBusinessMapView.as_view()),
    url('^vraagenaanbod/', include('cc3.marketplace.urls')),
    url('^rekeningen/', include('cc3.accounts.urls')),

    # Django CMS related URLs. Keep it at the end of the list.
    url(r'^', include('cms.urls')),
)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = patterns(
        '',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {
                'document_root': settings.MEDIA_ROOT,
                'show_indexes': True
            }),

        url(r'', include('django.contrib.staticfiles.urls')),
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
            {
                'document_root': settings.STATIC_ROOT,
                'show_indexes': True
            }),
        (r'^favicon\.ico$',  RedirectView.as_view(
            url=settings.STATIC_URL+'images/favicon.ico')),
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ) + urlpatterns

# For switching languages and javascript-translations ###

urlpatterns += patterns(
    '',
    (r'^i18n/', include('django.conf.urls.i18n')),
)

urlpatterns += patterns(
    '',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog',
     {'packages': ('cc3.marketplace',)}),
    (r'^forms/', include('form_designer.urls')),  # Cannot install via PyPI.
    # Needs upgrading for DJango 1.8 - see django-form-designer-ai
)


# Conditional loading of accounts & marketplace apps (if not done via
# Django-CMS) ###

if not is_loaded('accounts_home'):
    from cc3.accounts.urls import urlpatterns as accounts
    LOG.critical("Adding accounts urls outside Django-CMS")
    urlpatterns += i18n_patterns(
        '',
        url('^rekeningen/', include(accounts)))


if not is_loaded('marketplace'):
    from cc3.marketplace.urls import urlpatterns as market
    LOG.warning("Adding marketplace urls outside Django-CMS")
    urlpatterns += patterns(
        '',
        url('^vraagenaanbod/', include(market))
    )


# monkey patch DjangoCMS to add way to get at Page object
#from menus.base import NavigationNode
#from cms.models.pagemodel import Page
#NavigationNode.page_instance = lambda u: Page.objects.filter(pk=u.id)[0]
