from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

urlpatterns = (
    # Overview
    path('overview/', views.OverviewView.as_view(), name='overview'),
    # InventoryItemGroups
    path(
        'inventory-item-groups/',
        include(get_model_urls('netbox_inventory_plus', 'inventoryitemgroup', detail=False)),
    ),
    path(
        'inventory-item-groups/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'inventoryitemgroup')),
    ),
    # InventoryItemTypes
    path(
        'inventory-item-types/',
        include(get_model_urls('netbox_inventory_plus', 'inventoryitemtype', detail=False)),
    ),
    path(
        'inventory-item-types/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'inventoryitemtype')),
    ),
    # Assets
    path(
        'assets/',
        include(get_model_urls('netbox_inventory_plus', 'asset', detail=False)),
    ),
    path(
        'assets/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'asset')),
    ),
    path(
        'assets/<int:pk>/assign/',
        views.AssetAssignView.as_view(),
        name='asset_assign',
    ),
    path(
        'assets/device/create/',
        views.AssetDeviceCreateView.as_view(),
        name='asset_device_create',
    ),
    path(
        'assets/module/create/',
        views.AssetModuleCreateView.as_view(),
        name='asset_module_create',
    ),
    path(
        'assets/inventory-item/create/',
        views.AssetInventoryItemCreateView.as_view(),
        name='asset_inventoryitem_create',
    ),
    path(
        'assets/rack/create/',
        views.AssetRackCreateView.as_view(),
        name='asset_rack_create',
    ),
    path(
        'assets/device/<int:pk>/reassign/',
        views.AssetDeviceReassignView.as_view(),
        name='asset_device_reassign',
    ),
    path(
        'assets/module/<int:pk>/reassign/',
        views.AssetModuleReassignView.as_view(),
        name='asset_module_reassign',
    ),
    path(
        'assets/inventoryitem/<int:pk>/reassign/',
        views.AssetInventoryItemReassignView.as_view(),
        name='asset_inventoryitem_reassign',
    ),
    path(
        'assets/rack/<int:pk>/reassign/',
        views.AssetRackReassignView.as_view(),
        name='asset_rack_reassign',
    ),
    path(
        'assets/device/<int:pk>/create/',
        views.DeviceAssetCreateView.as_view(),
        name='device_asset_create',
    ),
    path(
        'assets/module/<int:pk>/create/',
        views.ModuleAssetCreateView.as_view(),
        name='module_asset_create',
    ),
    path(
        'assets/rack/<int:pk>/create/',
        views.RackAssetCreateView.as_view(),
        name='rack_asset_create',
    ),
    # Suppliers
    path(
        'suppliers/',
        include(get_model_urls('netbox_inventory_plus', 'supplier', detail=False)),
    ),
    path(
        'suppliers/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'supplier')),
    ),
    # BOMs
    path(
        'boms/',
        include(get_model_urls('netbox_inventory_plus', 'bom', detail=False)),
    ),
    path(
        'boms/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'bom')),
    ),
    path(
        'boms/<int:pk>/assign-assets/',
        views.AssignAssetsToBOMView.as_view(),
        name='bom_assign_assets',
    ),
    # Purchases
    path(
        'purchases/',
        include(get_model_urls('netbox_inventory_plus', 'purchase', detail=False)),
    ),
    path(
        'purchases/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'purchase')),
    ),
    path(
        'purchases/<int:pk>/add-bom/',
        views.PurchaseCreateBOMView.as_view(),
        name='purchase_create_bom'
    ),
    path(
        'purchases/<int:pk>/assign-assets/',
        views.AssignAssetsToPurchaseView.as_view(),
        name='purchase_assign_assets',
    ),
    path(
        'purchases/<int:pk>/assign-boms/',
        views.AssignBOMsToPurchaseView.as_view(),
        name='purchase_assign_boms',
    ),
    # Deliveries
    path(
        'deliveries/',
        include(get_model_urls('netbox_inventory_plus', 'delivery', detail=False)),
    ),
    path(
        'deliveries/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'delivery')),
    ),
    path(
        'deliveries/<int:pk>/add-purchase/',
        views.DeliveryCreatePurchaseView.as_view(),
        name='delivery_create_purchase',
    ),
    path(
        'deliveries/<int:pk>/assign-assets/',
        views.AssignAssetsToDeliveryView.as_view(),
        name='delivery_assign_assets',
    ),
    path(
        'deliveries/<int:pk>/assign-purchases/',
        views.AssignPurchasesToDeliveryView.as_view(),
        name='delivery_assign_purchases',
    ),
    # Couriers
    path(
        'couriers/',
        include(get_model_urls('netbox_inventory_plus', 'courier', detail=False)),
    ),
    path(
        'couriers/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'courier')),
    ),
    # Transfers
    path(
        'transfers/',
        include(get_model_urls('netbox_inventory_plus', 'transfer', detail=False)),
    ),
    path(
        'transfers/<int:pk>/',
        include(get_model_urls('netbox_inventory_plus', 'transfer')),
    ),
)
