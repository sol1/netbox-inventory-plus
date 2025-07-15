from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

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

    def validate_object(self, request):
        if isinstance(self.related_object, Rack) and not self.related_object.rack_type:
            messages.error(
                request,
                "Cannot create Asset: the selected Rack does not have an assigned rack_type."
            )
            return False

        if isinstance(self.related_object, InventoryItem):
            if not hasattr(self.related_object, 'inventoryitem_type') or not self.related_object.inventoryitem_type:
                messages.error(
                    request,
                    "Cannot create Asset: the selected Inventory Item does not have an assigned inventoryitem_type."
                )
                return False

        return True

    def get_object(self, **kwargs):
        related_type = getattr(self.related_object, f'{self.related_field}_type', None)
        return Asset(**{self.related_type_field: related_type})

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context[self.related_field] = self.related_object
        context['object_asset_create'] = True
        context['return_url'] = self.related_object.get_absolute_url()
        return context

    def render_form(self, request, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "object": self.object,
                **self.get_extra_context(request, self.object)
            }
        )

    def get(self, request, *args, **kwargs):
        if not self.validate_object(request):
            return redirect(
                request.GET.get('return_url') or self.related_object.get_absolute_url()
            )

        self.object = self.get_object(**kwargs)
        form = self.form(
            instance=self.object,
            related_object=self.related_object,
            related_field=self.related_field,
        )

        return self.render_form(request, form)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(**kwargs)
        form = self.form(
            request.POST,
            request.FILES,
            instance=self.object,
            related_object=self.related_object,
            related_field=self.related_field,
        )

        if form.is_valid():
            asset = form.save(commit=False)
            setattr(asset, self.related_field, self.related_object)

            try:
                asset.full_clean()
                asset.save()
                messages.success(
                    request,
                    f"A new Asset: {asset} has been created and assigned to {self.related_object}."
                )
                return redirect(request.GET.get('return_url', '/'))
            except ValidationError as e:
                messages.error(
                    request,
                    f"Could not create Asset: {e.message_dict.get(self.related_field, e.messages)[0]}"
                )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return self.render_form(request, form)


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


class RackAssetCreateView(ObjectAssetCreateView):
    related_model = Rack
