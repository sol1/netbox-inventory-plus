from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_inventory'

router = NetBoxRouter()

# Assets
router.register('assets', views.AssetViewSet)
router.register('inventory-item-types', views.InventoryItemTypeViewSet)
router.register('inventory-item-groups', views.InventoryItemGroupViewSet)
router.register('dcim/devices', views.DeviceAssetViewSet)
router.register('dcim/modules', views.ModuleAssetViewSet)
router.register('dcim/inventory-items', views.InventoryItemAssetViewSet)

# Deliveries
router.register('suppliers', views.SupplierViewSet)
router.register('boms', views.BOMViewSet)
router.register('purchases', views.PurchaseViewSet)
router.register('deliveries', views.DeliveryViewSet)

# Transit
router.register('couriers', views.CourierViewSet)
router.register('transfers', views.TransferViewSet)

urlpatterns = router.urls
