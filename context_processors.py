from django.conf import settings

#from cms.models import Page


def top_menu_items(request):
    """Adds list of items to include in top menu (reverse ids from menu system)."""
    return {
        'top_menu_items': settings.TOP_MENU_ITEMS
    }

def tandc_url(request):
    """Adds terms and conditions url for language."""
    tandc_url = ''
#    try:
#        tandc_url = Page.objects.get(reverse_id='tandc', publisher_is_draft=False).get_absolute_url()
#    except Exception, e:
#        pass

    return {
        'tandc_url': tandc_url
    }

def stadlander(request):
    return  {
        'stadlander_url': settings.STADLANDER_URL,
        'stadlander_login_url': settings.STADLANDER_LOGIN_URL,
    }