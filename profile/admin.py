from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from cc3.cyclos.admin import CC3ProfileAdmin

from .models import (
    BusinessProfile, InstitutionProfile, CharityProfile, UserProfile,
    IndividualProfile, SEPAXMLFile)


def close_account(modeladmin, request, queryset):
    for obj in queryset:
        obj.profile.close_account()
close_account.short_description = _(u"Close selected accounts")


class UserProfileAdmin(CC3ProfileAdmin):
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'user__card_set__number__number',
        'user__terminal_set__name',
        'business_name',
        'first_name',
        'last_name',
        'address',
        'extra_address',
        'num_street',
        'phone_number',
        'mobile_number',
        'postal_code',
        'stadlanderprofile__rel_number',
    ]


class IndividualProfileAdmin(admin.ModelAdmin):
    list_display = ('profile', 'first_name', 'last_name', 'email', 'username')
    search_fields = (
        'profile__user__email',
        'profile__user__first_name',
        'profile__user__last_name',
        'profile__stadlanderprofile__rel_number',
        'profile__user__card_set__number__number',
        'profile__user__terminal_set__name',
        'profile__business_name',
        'profile__first_name',
        'profile__last_name',
        'profile__address',
        'profile__extra_address',
        'profile__num_street',
        'profile__phone_number',
        'profile__mobile_number',
        'profile__postal_code',
    )
    raw_id_fields = ('profile',)
    actions = [close_account]

    def first_name(self, obj):
        return obj.profile.first_name

    def last_name(self, obj):
        return obj.profile.last_name

    def email(self, obj):
        return obj.profile.user.email

    def username(self, obj):
        return obj.profile.user.username


class BusinessProfileAdmin(IndividualProfileAdmin):
    list_display = (
        'profile',
        'first_name',
        'last_name',
        'email',
        'username',
        'iban',
        'bic_code',
        'signature_date',
    )
    # search_fields = (
    #     'profile__user__email',
    #     'profile__user__first_name',
    #     'profile__user__last_name',
    #     'profile__business_name',
    # )
    readonly_fields = ('latest_payment_date',)
    raw_id_fields = ('profile',)


class InstitutionProfileAdmin(IndividualProfileAdmin):
    list_display = (
        'profile',
        'first_name',
        'last_name',
        'email',
        'username',
        'iban',
        'bic_code',
        'signature_date',
    )
    # search_fields = (
    #     'profile__user__email',
    #     'profile__user__first_name',
    #     'profile__user__last_name',
    #     'profile__business_name',
    # )
    readonly_fields = ('latest_payment_date',)
    raw_id_fields = ('profile',)


class CharityProfileAdmin(IndividualProfileAdmin):
    list_display = (
        'profile',
        'first_name',
        'last_name',
        'email',
        'username',
        'iban',
        'bic_code',
        'signature_date',
    )
    # search_fields = (
    #     'profile__user__email',
    #     'profile__user__first_name',
    #     'profile__user__last_name',
    #     'profile__business_name',
    # )
    readonly_fields = ('latest_payment_date',)
    raw_id_fields = ('profile',)


class SEPAXMLFileChangeList(ChangeList):
    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        return reverse('sepaxmlfile_download', kwargs={'pk': pk})


class SEPAXMLFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'file_date', 'file_type', 'generated_date', )
    list_filter = ('file_type',)
    date_hierarchy = 'file_date'

    def get_changelist(self, request, **kwargs):
        return SEPAXMLFileChangeList

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(SEPAXMLFile, SEPAXMLFileAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(IndividualProfile, IndividualProfileAdmin)
admin.site.register(BusinessProfile, BusinessProfileAdmin)
admin.site.register(InstitutionProfile, InstitutionProfileAdmin)
admin.site.register(CharityProfile, CharityProfileAdmin)
