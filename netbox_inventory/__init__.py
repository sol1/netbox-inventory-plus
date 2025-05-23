from netbox.plugins import PluginConfig

from .version import __version__


class NetBoxInventoryConfig(PluginConfig):
    name = 'netbox_inventory'
    verbose_name = 'NetBox Inventory'
    version = __version__
    description = 'Inventory asset management in NetBox'
    author = 'Matej Vadnjal'
    author_email = 'matej.vadnjal@arnes.si'
    base_url = 'inventory'
    min_version = '4.2.1'
    default_settings = {
        'top_level_menu': True,
        'planned_status_name': 'planned',
        'planned_additional_status_names': [],
        'ordered_status_name': 'ordered',
        'ordered_additional_status_names': [],
        'retired_status_name': 'retired',
        'retired_additional_status_names': [],
        'stored_status_name': 'stored',
        'stored_additional_status_names': [
            'retired',
        ],
        'transit_status_name': 'transit',
        'transit_additional_status_names': [],
        'used_status_name': 'used',
        'used_additional_status_names': [],
        'sync_hardware_serial_asset_tag': False,
        'sync_hardware_eol_date': True,
        'asset_sync_ignored_custom_fields': [],
        'asset_import_create_purchase': False,
        'asset_import_create_device_type': False,
        'asset_import_create_module_type': False,
        'asset_import_create_inventoryitem_type': False,
        'asset_import_create_rack_type': False,
        'asset_import_create_tenant': False,
        'asset_disable_editing_fields_for_tags': {},
        'asset_disable_deletion_for_tags': [],
        'asset_custom_fields_search_filters': {},
        'asset_warranty_expire_warning_days': 90,
        'prefill_asset_name_create_inventoryitem': False,
        'prefill_asset_tag_create_inventoryitem': False,
    }

    def ready(self):
        super().ready()
        from . import signals  # noqa: F401


config = NetBoxInventoryConfig
