from cc3.cyclos.managers import ViewableProfileManager


class UserProfileManager(ViewableProfileManager):

    def get_good_causes_queryset(self):
        queryset = super(UserProfileManager, self).get_queryset()
        return queryset.filter(charity_profile__isnull=False)

    # def for_user(self, user):
    #     if user.groups.filter(name="Stadlander admins").count():
    #         from cc3.cyclos.groups import CyclosGroupSet
    #         stadlander_groupset = CyclosGroupSet.objects.get(prefix="STD")
    #         return self.get_queryset().filter(
    #             groupset__id=stadlander_groupset.id,
    #         )
    #
    #     return self.get_queryset()
