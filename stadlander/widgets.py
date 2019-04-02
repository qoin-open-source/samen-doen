# encoding: utf-8
from itertools import chain

from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class StadlanderRewardCategoryCheckboxSelectMultiple(CheckboxSelectMultiple):
    """ Very specific
    """
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []

        final_attrs = self.build_attrs(attrs, name=name)
        id_ = final_attrs.get('id', None)
        output = ['<ul>']
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
            output.append('<li>')
            output.append(self.render_checkbox(
                final_attrs, option_value, option_label, str_values, name,
                label_for))
            output.append('</li>')
        output.append('</ul>')
        return mark_safe('\n'.join(output))

    def render_checkbox(self, final_attrs, option_value, option_label,
                        str_values, name, label_for):

        from .models import RewardCategory

        checkbox = CheckboxInput(
            final_attrs, check_test=lambda value: value in str_values)
        option_value = force_text(option_value)
        rendered_cb = checkbox.render(name, option_value)
        option_label = force_text(option_label)

        # could do this in one go possibly above
        reward_category = RewardCategory.objects.get(pk=option_value)
        if reward_category.reward_first_ad:
            reward_text = mark_safe(
                u"<span class='alert alert-info' style='padding:2px;'>Voor "
                u"deze categorie geldt een extra waardering *</span>")
            return format_html(
                u'<div class="element checkbox-container"><label{0}>'
                u'{1} {2} - {3}</label>'
                u'</div><div class="clearfix"></div>', label_for,
                rendered_cb, option_label,
                reward_text
            )
        else:
            return format_html(
                u'<div class="element checkbox-container"><label{0}>'
                u'{1} {2}</label><span class="clearfix"></span>'
                u'</div>', label_for,
                rendered_cb, option_label
            )
