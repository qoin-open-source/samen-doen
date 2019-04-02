from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from cc3.cards.admin import FulfillmentAdmin
from cc3.cards.models import Fulfillment
from cc3.cyclos.models import UserStatusChangeHistory


class UserChangeHistoryInLine(admin.TabularInline):
    model = UserStatusChangeHistory
    fk_name = 'user'
    can_delete = False
    extra = 0
    ordering = ('-timestamp',)
    verbose_name_plural = _(u'User activation/deactivation history')

    readonly_fields = ('change_author', 'timestamp', 'activate',)

    def __init__(self, *args, **kwargs):
        super(UserChangeHistoryInLine, self).__init__(*args, **kwargs)
        self.model._meta.get_field('change_author').verbose_name = \
            _(u'Change author')
        self.model._meta.get_field('timestamp').verbose_name = _(u'Timestamp')
        self.model._meta.get_field('activate').verbose_name = _(u'Activate')

    def has_add_permission(self, request):
        return False


class Icare4uUserAdmin(UserAdmin):
    inlines = [
        UserChangeHistoryInLine,
    ]
    filter_horizontal = ('user_permissions', 'groups')
    save_on_top = True
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff',
                    'last_login', 'is_active')
    template = 'admin/edit_inline/tabular.html'

    readonly_fields = ('last_login', 'date_joined',)


class Icare4uFulfillmentAdmin(FulfillmentAdmin):
    pass


admin.site.unregister(User)
admin.site.register(User, Icare4uUserAdmin)

admin.site.unregister(Fulfillment)
admin.site.register(Fulfillment, Icare4uFulfillmentAdmin)
