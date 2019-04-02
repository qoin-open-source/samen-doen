from django.db import models
from django.utils.translation import ugettext_lazy as _

from cc3.billing.models import Product
from cc3.cyclos.models import User, CC3Profile


class CommunityCardMachineUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'card machine' users (defined by setting
    CYCLOS_CARD_MACHINE_MEMBER_GROUPS).

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'auth'
        verbose_name = _('User (Card Machine)')
        verbose_name_plural = _('Users (Card Machine)')

    @property
    def cc3_profile(self):
        return CC3Profile.objects.get(user=self)


class CommunityCardUserProxyModel(User):
    """
    This is a proxy ``models.Model`` class. It is being used to provide a nice
    filter in those ``ModelAdmin``s which require to show ``User``s filtered by
    those who are 'card machine' users (defined by setting
    CYCLOS_CARD_USER_MEMBER_GROUPS).

    Workarounds the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    """
    class Meta:
        proxy = True
        app_label = 'auth'
        verbose_name = _('User (Card)')
        verbose_name_plural = _('Users (Card)')

    @property
    def cc3_profile(self):
        return CC3Profile.objects.get(user=self)


class CommunityFulfillmentProfileProxyModel(CC3Profile):
    class Meta:
        proxy = True
        app_label = 'accounts'
        verbose_name = _('Profile (Fulfillment)')
        verbose_name_plural = _('Profiles (Fulfillment)')


class ProductUserManager(models.Manager):
    def get_queryset(self):
        valid_groups = Product.objects.values_list(
            'user_groups', flat=True).distinct()
        return super(ProductUserManager, self).get_queryset().filter(
            cyclos_group_id__in=valid_groups)


class CommunityProductUserProfileProxyModel(CC3Profile):
    """
    This is a proxy ``models.Model`` class. It is being used to provide the
    'Assign products to users' page in billing app

    Works around the Django design which only allows to register one admin
    interface per model, avoiding raising ``AlreadyRegistered`` exception.
    Also pre-filters the users so that only those who can have products
    assigned to them are shown in the list
    """
    objects = ProductUserManager()

    class Meta:
        proxy = True
        app_label = 'billing'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
