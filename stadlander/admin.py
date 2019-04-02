from django.contrib import admin

from adminsortable.admin import SortableAdmin

from .models import StadlanderProfile, CommunityWoonplaat, RewardCategory


class CommunityWoonplaatAdmin(admin.ModelAdmin):
    list_display = ('community', 'woonplaat')


class RewardCategoryAdmin(SortableAdmin):
    list_display = ('title', 'reward_first_ad', 'active')
    list_editable = ('reward_first_ad', 'active')


admin.site.register(StadlanderProfile)
admin.site.register(CommunityWoonplaat, CommunityWoonplaatAdmin)
admin.site.register(RewardCategory, RewardCategoryAdmin)
