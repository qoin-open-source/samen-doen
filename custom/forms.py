from django import forms

from cc3.core.models import Category
from cc3.marketplace.forms import (BusinessFilterForm, MarketplaceForm,
                                   CampaignFilterForm)
from cc3.marketplace.models import AdType, CampaignCategory
from cc3.cyclos.models import CC3Community

from .widgets import MarketplaceCheckboxSelectMultiple

NO_PAGINATION_CHOICES = ((2000, 'No pagination'),)
PROFILE_TYPE_CHOICES = (
    (u'5,16',  'Spaarders',),
    (13, 'Spaardoelen',),
    (12, 'Winkeliers',),
    (14, 'Instellingen',),
)


class ICare4uMarketplaceFilterForm(MarketplaceForm):
    # override widgets (and choices)
    # overriding widgets in __init__ obliterates choices
    adtype = forms.ModelMultipleChoiceField(
        queryset=AdType.objects.filter(active=True),
        widget=MarketplaceCheckboxSelectMultiple, required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.for_ads(),
        widget=MarketplaceCheckboxSelectMultiple, required=False)
    profile_types = forms.MultipleChoiceField(
        choices=PROFILE_TYPE_CHOICES, widget=MarketplaceCheckboxSelectMultiple,
        required=False
    )
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects.all(),
        widget=MarketplaceCheckboxSelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ICare4uMarketplaceFilterForm, self).__init__(*args, **kwargs)
        del self.fields['paginate_by']

        if self.user.is_authenticated() and not self.user.is_superuser:
            if self.user.get_profile().is_individual_profile():
                self.fields['community'].widget.attrs['disabled'] = True


class ICare4uBusinessFilterForm(BusinessFilterForm):
    """
    Form for filtering profiles (aka businesses).

    Overrides the default one because Icare4u has different requirements
    """
    profile_types = forms.MultipleChoiceField(
        choices=PROFILE_TYPE_CHOICES, widget=MarketplaceCheckboxSelectMultiple,
        required=False)
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects.all(),
        widget=MarketplaceCheckboxSelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ICare4uBusinessFilterForm, self).__init__(*args, **kwargs)

        # Samen Doen does not show categories or ad types on the profiles
        # (aka businesses page)
        del self.fields['adtype']
        del self.fields['categories']        
        self.fields['sort_by'].widget = forms.HiddenInput()
        self.fields['sort_by'].required = False
        self.fields['from_price'].widget = forms.HiddenInput()
        self.fields['to_price'].widget = forms.HiddenInput()
        del self.fields['paginate_by']

        if self.user.is_authenticated() and not self.user.is_superuser:
            if self.user.get_profile().is_individual_profile():
                self.fields['community'].widget.attrs['disabled'] = True


class ICare4uCampaignFilterForm(CampaignFilterForm):
    """
    Form for filtering campaigns (aka activities).

    Overrides the default one because Icare4u has different requirements
    """
    categories = forms.ModelMultipleChoiceField(
        queryset=CampaignCategory.objects.for_campaigns(),
        widget=MarketplaceCheckboxSelectMultiple, required=False)
    community = forms.ModelMultipleChoiceField(
        queryset=CC3Community.objects.all(),
        widget=MarketplaceCheckboxSelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(ICare4uCampaignFilterForm, self).__init__(*args, **kwargs)
        del self.fields['paginate_by']


class ICare4uBusinessMapFilterForm(ICare4uBusinessFilterForm):
    """Override to prevent pagination

    Allows paginate_by to take a value not in the choices dropdown

    ... effectively 'no pagination'"""
    def __init__(self, *args, **kwargs):
        super(ICare4uBusinessMapFilterForm, self).__init__(*args, **kwargs)
        self.fields['paginate_by'] = forms.ChoiceField(
            choices=NO_PAGINATION_CHOICES, widget = forms.HiddenInput,
            initial=NO_PAGINATION_CHOICES[0][0])
