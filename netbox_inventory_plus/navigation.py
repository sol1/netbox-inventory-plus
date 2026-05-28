from netbox.plugins import (
    PluginMenu,
    PluginMenuButton,
    PluginMenuItem,
    get_plugin_config,
)

#
# Overview
#

overview_items = (
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:overview',
        link_text='Overview',
    ),
)


#
# Assets
#

inventoryitemgroup_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:inventoryitemgroup_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_inventoryitemgroup'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:inventoryitemgroup_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_inventoryitemgroup'],
    ),
]

inventoryitemtype_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:inventoryitemtype_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_inventoryitemtype'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:inventoryitemtype_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_inventoryitemtype'],
    ),
]

asset_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:asset_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_asset'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:asset_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_asset'],
    ),
]

assets_items = (
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:asset_list',
        link_text='Assets',
        permissions=['netbox_inventory_plus.view_asset'],
        buttons=asset_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:inventoryitemtype_list',
        link_text='Inventory Item Types',
        permissions=['netbox_inventory_plus.view_inventoryitemtype'],
        buttons=inventoryitemtype_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:inventoryitemgroup_list',
        link_text='Inventory Item Groups',
        permissions=['netbox_inventory_plus.view_inventoryitemgroup'],
        buttons=inventoryitemgroup_buttons,
    ),
)


#
# Deliveries
#

supplier_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:supplier_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_supplier'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:supplier_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_supplier'],
    ),
]

bom_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:bom_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_bom'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:bom_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_bom'],
    ),
]

purchase_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:purchase_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_purchase'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:purchase_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_purchase'],
    ),
]

delivery_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:delivery_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_delivery'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:delivery_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_delivery'],
    ),
]

deliveries_items = (
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:supplier_list',
        link_text='Suppliers',
        permissions=['netbox_inventory_plus.view_supplier'],
        buttons=supplier_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:bom_list',
        link_text='BOMs',
        permissions=['netbox_inventory_plus.view_bom'],
        buttons=bom_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:purchase_list',
        link_text='Purchases',
        permissions=['netbox_inventory_plus.view_purchase'],
        buttons=purchase_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:delivery_list',
        link_text='Deliveries',
        permissions=['netbox_inventory_plus.view_delivery'],
        buttons=delivery_buttons,
    ),
)


#
# Transit
#

courier_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:courier_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_courier'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:courier_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_courier'],
    ),
]

transfer_buttons = [
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:transfer_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        permissions=['netbox_inventory_plus.add_transfer'],
    ),
    PluginMenuButton(
        link='plugins:netbox_inventory_plus:transfer_bulk_import',
        title='Import',
        icon_class='mdi mdi-upload',
        permissions=['netbox_inventory_plus.add_transfer'],
    ),
]

transit_items = (
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:courier_list',
        link_text='Couriers',
        permissions=['netbox_inventory_plus.view_courier'],
        buttons=courier_buttons,
    ),
    PluginMenuItem(
        link='plugins:netbox_inventory_plus:transfer_list',
        link_text='Transfers',
        permissions=['netbox_inventory_plus.view_transfer'],
        buttons=transfer_buttons,
    ),
)


#
# Menu
#

if get_plugin_config('netbox_inventory_plus', 'top_level_menu'):
    # add a top level entry
    menu = PluginMenu(
        label='Inventory',
        groups=(
            ('Overview', overview_items),
            ('Asset Management', assets_items),
            ('Deliveries', deliveries_items),
            ('Transit', transit_items),
        ),
        icon_class='mdi mdi-clipboard-text-multiple-outline',
    )
else:
    # display under plugins
    menu_items = assets_items + deliveries_items
