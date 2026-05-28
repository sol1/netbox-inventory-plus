from netbox.views import misc

__all__ = (
    'OverviewView',
)

class OverviewView(misc.HomeView):
    """
    Overview dashboard for the plugin
    """
    template_name = 'netbox_inventory_plus/overview.html'
