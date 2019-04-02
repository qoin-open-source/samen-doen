from django.conf.urls import patterns, url

from .views import ICare4uRegistrationView


urlpatterns = patterns(
    '',
    url(r'^register/$',
        ICare4uRegistrationView.as_view(),
        name='registration_register'),
    # url('^terms_and_conditions/$', terms_and_conditions_agreement,
    #     name='terms_and_conditions_agreement'),
)
