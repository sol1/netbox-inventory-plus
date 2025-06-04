from dcim.models import Device, InventoryItem, Module, Rack
from netbox.views import generic

from ..forms import AssetForm
from ..forms.create import *
from ..models import Asset

__all__ = (
    'AssetDeviceCreateView',
    'AssetModuleCreateView',
    'AssetInventoryItemCreateView',
    'AssetRackCreateView',
    'DeviceAssetCreateView',
    'ModuleAssetCreateView',
    'InventoryItemAssetCreateView',
    'RackAssetCreateView',
)


class AssetCreateView(generic.ObjectEditView):
    template_name = 'netbox_inventory/asset_create.html'
    asset = None

    def _load_asset(self, request):
        asset_id = request.GET.get('asset_id')
        if asset_id:
            try:
                self.asset = Asset.objects.get(pk=asset_id)
            except Asset.DoesNotExist:
                self.asset = None

    def dispatch(self, request, *args, **kwargs):
        self._load_asset(request)
        return super().dispatch(request, *args, **kwargs)

    def alter_object(self, obj, request, url_args, url_kwargs):
        obj.assigned_asset = self.asset
        return super().alter_object(obj, request, url_args, url_kwargs)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context['asset'] = self.asset
        return context


class AssetDeviceCreateView(AssetCreateView):
    queryset = Device.objects.all()
    form = AssetDeviceCreateForm

    def get_object(self, **kwargs):
        return Device(assigned_asset=self.asset)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context['template_extends'] = 'dcim/device_edit.html'
        return context


class AssetModuleCreateView(AssetCreateView):
    queryset = Module.objects.all()
    form = AssetModuleCreateForm

    def get_object(self, **kwargs):
        return Module(assigned_asset=self.asset)


class AssetInventoryItemCreateView(AssetCreateView):
    queryset = InventoryItem.objects.all()
    form = AssetInventoryItemCreateForm

    def get_object(self, **kwargs):
        return InventoryItem(assigned_asset=self.asset)


class AssetRackCreateView(AssetCreateView):
    queryset = Rack.objects.all()
    form = AssetRackCreateForm

    def get_object(self, **kwargs):
        return Rack(assigned_asset=self.asset)


class DeviceAssetCreateView(AssetCreateView):
    queryset = Device.objects.all()
    form = AssetForm
    template_name = 'netbox_inventory/asset_edit.html'

    def get_object(self, **kwargs):
        device = self.queryset.get(pk=kwargs.get('pk'))
        return Asset(device_type=device.device_type)


class ModuleAssetCreateView(AssetCreateView):
    queryset = Module.objects.all()
    form = AssetForm
    template_name = 'netbox_inventory/asset_edit.html'

    def get_object(self, **kwargs):
        module = self.queryset.get(pk=kwargs.get('pk'))
        return Asset(module_type=module.module_type)


class InventoryItemAssetCreateView(AssetCreateView):
    queryset = InventoryItem.objects.all()
    form = AssetForm
    template_name = 'netbox_inventory/asset_edit.html'

    def get_object(self, **kwargs):
        inventoryitem = self.queryset.get(pk=kwargs.get('pk'))
        return Asset(inventoryitem_type=inventoryitem.inventoryitem_type)


class RackAssetCreateView(AssetCreateView):
    queryset = Rack.objects.all()
    form = AssetForm
    template_name = 'netbox_inventory/asset_edit.html'

    def get_object(self, **kwargs):
        rack = self.queryset.get(pk=kwargs.get('pk'))
        return Asset(rack_type=rack.rack_type)
