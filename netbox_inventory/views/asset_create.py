from django.shortcuts import redirect

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


class ObjectAssetCreateView(generic.ObjectEditView):
    queryset = Asset.objects.all()
    form = AssetForm
    template_name = 'netbox_inventory/asset_edit.html'

    related_model = None

    @property
    def related_field(self):
        if not self.related_model:
            raise ValueError("The related_model attribute must be set in the subclass.")
        return self.related_model.__name__.lower()

    @property
    def related_type_field(self):
        return f"{self.related_field}_type"

    @property
    def related_object(self):
        if not hasattr(self, '_related_object'):
            self._related_object = self.related_model.objects.get(pk=self.kwargs.get('pk'))
        return self._related_object

    def get_object(self, **kwargs):
        kwargs = {
            self.related_type_field: getattr(self.related_object, f'{self.related_field}_type'),
        }
        return Asset(**kwargs)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context[self.related_field] = self.related_object
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(**kwargs)
        form = self.form(request.POST, request.FILES, instance=self.object)

        if form.is_valid():
            asset = form.save(commit=False)
            setattr(asset, self.related_field, self.related_object)
            asset.full_clean()
            asset.save()
            return_url = request.GET.get('return_url', '/')
            return redirect(return_url if return_url else '/')

        return self.render(request, form=form)


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


class DeviceAssetCreateView(ObjectAssetCreateView):
    related_model = Device


class ModuleAssetCreateView(ObjectAssetCreateView):
    related_model = Module


class InventoryItemAssetCreateView(ObjectAssetCreateView):
    related_model = InventoryItem


class RackAssetCreateView(ObjectAssetCreateView):
    related_model = Rack
