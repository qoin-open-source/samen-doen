from django.conf.urls import patterns, url

from .admin_views import (
    community_admin_close_account, community_admin_reset_email,
    community_admin_resend_activation
)
from cc3.cards.views_api import update_fulfillment_status

urlpatterns = patterns(
    '',
    url(
        r'^profile/userprofile/(?P<pk>\d+)/close_account/$',
        community_admin_close_account,
        name='community_admin_individualprofile_close_account'
    ),
    url(
        r'^profile/userprofile/(?P<pk>\d+)/resend_activation/$',
        community_admin_resend_activation,
        name='community_admin_individualprofile_resend_activation',
    ),
    url(
        r'^profile/reset-password/$',
        community_admin_reset_email,
        name='community_admin_profile_reset_password'
    ),
    url(r'^cards/fulfillment/update/$', update_fulfillment_status,
        name='community_admin_cards_fulfillment_update'),
)
