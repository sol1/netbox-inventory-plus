from django import template
from django.urls import NoReverseMatch
from django.utils.translation import gettext as _

from utilities.views import get_action_url

register = template.Library()


@register.inclusion_tag('netbox_inventory_plus/buttons/bulk_scan.html', takes_context=True)
def bulk_scan_button(context, model, action='bulk_scan', query_params=None):
    try:
        url = get_action_url(model, action=action)
        if query_params:
            url = f'{url}?{query_params.urlencode()}'
    except NoReverseMatch:
        url = None

    return {
        'label': _('Scan Selected'),
        'url': url,
        'htmx_navigation': context.get('htmx_navigation'),
    }
