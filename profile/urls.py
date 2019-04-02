from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import (
    CreateBusinessProfile, CreateIndividualProfile, CreateProfileSelectView,
    TermsAndConditionsFormView, SEPAXMLFileView, CreateInstitutionProfile,
    CreateCharityProfile, admin_close_account, StadlanderTermsAndConditionsFormView)


urlpatterns = patterns(
    '',
    url('^terms_and_conditions/$',
        login_required(TermsAndConditionsFormView.as_view()),
        name='terms_and_conditions_agreement'),
    url('^terms_and_conditions/stadlander/$',
        login_required(StadlanderTermsAndConditionsFormView.as_view()),
        name='terms_and_conditions_agreement_stadlander'),
    url('^comm/addmember/$', CreateProfileSelectView.as_view(),
        name='community_admin_create_profile_select'),
    url('^comm/addmember/business/$', CreateBusinessProfile.as_view(),
        name='community_admin_create_business_profile'),
    url('^comm/addmember/institution/$', CreateInstitutionProfile.as_view(),
        name='community_admin_create_institution_profile'),
    url('^comm/addmember/charity/$', CreateCharityProfile.as_view(),
        name='community_admin_create_charity_profile'),
    url('^comm/addmember/individual/$', CreateIndividualProfile.as_view(),
        name='community_admin_create_individual_profile'),
    url(
        regex=r'^admin/sepaxmlfile/(?P<pk>\d+)/download/$',
        view=SEPAXMLFileView.as_view(),
        name='sepaxmlfile_download'
    ),

    url(
        r'^admin/profile/individualprofile/(?P<pk>\d+)/close_account/$',
        admin_close_account, name='admin_individualprofile_close_account'
    )

)
