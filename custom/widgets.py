# encoding: utf-8
from itertools import chain

from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cc3.marketplace.common import AD_STATUS_ACTIVE

class MarketplaceCheckboxSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = []
        # Normalize to strings
        str_values = set([force_text(v) for v in value])

        for i, (option_value, option_label) in enumerate(chain(
                self.choices, choices)):

            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''
            output.append(self.render_checkbox(
                final_attrs, option_value, option_label, str_values, name,
                label_for))

        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for):
        checkbox = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = checkbox.render(name, option_value)
        option_label = force_text(option_label)

        return format_html(
            '<div class="form-group"><div class="checkbox">'
            '<label{0}>{1}<span> {2}</span></label></div></div>', label_for,
            rendered_cb, option_label
        )


class OfferWantCheckboxSelectMultiple(MarketplaceCheckboxSelectMultiple):
    """
    Extend Django CheckboxSelectMultiple to show numbers of 'items' next to
    choices.
    """
    def render(self, name, value, attrs=None, choices=()):
        from cc3.marketplace.models import Ad
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = []
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices,
                                                               choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if id_:
                final_attrs = dict(final_attrs, id='{0}_{1}'.format(id_, i))
                label_for = format_html(' for="{0}_{1}"', id_, i)
            else:
                label_for = ''

            ad_type_count = Ad.objects.filter(
                adtype__pk=option_value, status=AD_STATUS_ACTIVE).count()
            output.append(self.render_checkbox(
                final_attrs, option_value,
                u"{0} ({1})".format(_(option_label), ad_type_count),
                str_values, name, label_for))

        return mark_safe('\n'.join(output))