from django.utils.translation import gettext as _

from netbox.object_actions import ObjectAction


class BulkScan(ObjectAction):
    """
    Scan or assign barcodes to multiple assets at once.
    """
    name = 'bulk_scan'
    label = _('Scan')
    multi = True
    permissions_required = {'change'}
    template_name = 'netbox_inventory/buttons/bulk_scan.html'
