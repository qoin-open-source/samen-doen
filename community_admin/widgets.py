from django.utils.html import escape

from cc3.cyclos.widgets import (
    CardMachineUserForeignKeyRawIdWidget, CardUserForeignKeyRawIdWidget, FulfillmentProfileForeignKeyRawIdWidget)
from .models import (
    CommunityCardMachineUserProxyModel, CommunityCardUserProxyModel, CommunityFulfillmentProfileProxyModel)


class CommunityCardMachineUserForeignKeyRawIdWidget(
        CardMachineUserForeignKeyRawIdWidget):
    """
    Overrides ``cc3.cyclos.widgets.CardMachineUserForeignKeyRawIdWidget``
    to provide a ``raw_id_fields`` option in admin interface classes for
    those places  where a user filtering by particular user types is needed.

    The widget actually will show a list of ``cyclos.User``s filtered to those
    who are in CYCLOS_CARD_MACHINE_MEMBER_GROUPS settings defined groups of
    users.
    """
    rel_to = CommunityCardMachineUserProxyModel

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
            if hasattr(obj, "cc3_profile") and obj.cc3_profile is not None:
                return "&nbsp;<strong>%s</strong>" % escape(obj.cc3_profile.business_name)
            return ''

        except (ValueError, self.rel.to.DoesNotExist):
            return ''


class CommunityCardUserForeignKeyRawIdWidget(CardUserForeignKeyRawIdWidget):
    """
    Overrides ``django.contrib.admin.widgets.ForeignKeyRawIdWidget`` to provide
    a ``raw_id_fields`` option in admin interface classes for those places
    where a user filtering by particular user types is needed.

    The widget actually will show a list of ``cyclos.User``s filtered to those
    who are in CYCLOS_CARD_USER_MEMBER_GROUPS settings defined groups of
    users.
    """
    rel_to = CommunityCardUserProxyModel


class CommunityFulfillmentProfileForeignKeyRawIdWidget(FulfillmentProfileForeignKeyRawIdWidget):
    rel_to = CommunityFulfillmentProfileProxyModel