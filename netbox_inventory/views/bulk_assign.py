from django.contrib import messages
from django.db.models import ForeignKey, ManyToManyField
from django.shortcuts import redirect
from django.urls import reverse

from netbox.views import generic
from utilities.query import count_related

from .. import filtersets, forms, models, tables

__all__ = (
    'BulkAssignView',
    'BulkAssignRelatedView',
    'AssignToAssetView',
    'AssignToDeliveryView',
    'AssignToPurchaseView',
    'AssignBOMsToPurchaseView',
    'AssignPurchasesToDeliveryView',
)


#
# Generic Bulk Assign Views
#


class BulkAssignView(generic.ObjectListView):
    """
    A generic view for bulk assignment of objects where the corresponding field exists
    on the target object.
    """

    queryset = None
    table = None
    filterset = None
    filterset_form = None
    template_name = 'netbox_inventory/bulk_assign.html'
    related_mapping = {}
    """
    related_mapping is represnted as a dict, and should be formatted as:
    related_mapping = {'name': (models.ModelForName, 'field_name_in_model'),}

    For example:
    related_mapping = {'bom': (models.BOM, 'bom'),}
    """

    def get_related_model_and_field(self, related_type):
        if related_type not in self.related_mapping:
            raise ValueError(f'Invalid related type: {related_type}')
        return self.related_mapping[related_type]

    def get_extra_context(self, request):
        related_type = request.GET.get('related_type')
        related_id = request.GET.get('related_id')
        related_name = request.GET.get('related_name')
        return {
            'related_type': related_type,
            'related_id': related_id,
            'related_name': related_name,
        }

    def post(self, request, *args, **kwargs):
        related_type = request.GET.get('related_type')
        related_id = request.GET.get('related_id')
        related_name = request.GET.get('related_name')
        object_ids = request.POST.getlist('pk')
        error_redirect_path = f'{request.path}?related_type={related_type}&related_id={related_id}&related_name={related_name}'

        if not related_type or not related_id or not object_ids:
            messages.error(request, 'No related object or items selected.')
            return redirect(error_redirect_path)

        try:
            related_model, related_field = self.get_related_model_and_field(
                related_type
            )
            related_instance = related_model.objects.get(pk=related_id)
        except ValueError:
            messages.error(request, f'Invalid related type: {related_type}.')
            return redirect(error_redirect_path)
        except related_model.DoesNotExist:
            messages.error(
                request, f'Related object with ID {related_id} does not exist.'
            )
            return redirect(error_redirect_path)

        field_object = self.queryset.model._meta.get_field(related_field)

        if isinstance(field_object, ForeignKey):
            objects = self.queryset.filter(pk__in=object_ids)
            for obj in objects:
                obj = self.queryset.get(pk=obj.pk)
                setattr(obj, related_field, related_instance)
                obj._in_bulk_assignment = True
                obj.full_clean()
                obj.save()
                obj._in_bulk_assignment = False
        elif isinstance(field_object, ManyToManyField):
            objects = self.queryset.filter(pk__in=object_ids)
            for obj in objects:
                obj = self.queryset.get(pk=obj.pk)
                getattr(obj, related_field).add(related_instance)
                obj._in_bulk_assignment = True
                obj.full_clean()
                obj.save()
                obj._in_bulk_assignment = False
        else:
            messages.error(request, 'Unsupported field type for bulk assignment.')
            return redirect(error_redirect_path)

        messages.success(
            request, f'Successfully assigned {objects.count()} items to {related_name}.'
        )
        return redirect(
            reverse(f'plugins:netbox_inventory:{related_type}', args=[related_id])
        )


class BulkAssignRelatedView(BulkAssignView):
    """
    A generic view for bulk assignment of objects where the corresponding field does not
    exist on the target object, and instead exists on the source object.
    """

    def post(self, request, *args, **kwargs):
        related_type = request.GET.get('related_type')
        related_id = request.GET.get('related_id')
        related_name = request.GET.get('related_name')
        object_ids = request.POST.getlist('pk')
        error_redirect_path = f'{request.path}?related_type={related_type}&related_id={related_id}&related_name={related_name}'

        if not related_type or not related_id or not object_ids:
            messages.error(request, 'No related object or BOMs selected.')
            return redirect(error_redirect_path)

        try:
            related_model, related_field = self.get_related_model_and_field(
                related_type
            )
            related_instance = related_model.objects.get(pk=related_id)
        except (ValueError, related_model.DoesNotExist):
            messages.error(request, 'Invalid related object or type.')
            return redirect(error_redirect_path)

        objects = self.queryset.filter(pk__in=object_ids)
        getattr(related_instance, related_field).add(*objects)

        messages.success(
            request, f'Successfully assigned {objects.count()} BOMs to {related_name}.'
        )
        return redirect(related_instance.get_absolute_url())


#
# Bulk Assign Views
#


class AssignToAssetView(BulkAssignView):
    queryset = models.Asset.objects.prefetch_related(
        'device_type__manufacturer',
        'module_type__manufacturer',
        'inventoryitem_type__manufacturer',
        'rack_type__manufacturer',
        'device__role',
        'module__module_bay',
        'module__module_type',
        'inventoryitem__role',
        'rack__role',
        'owner',
        'bom',
        'purchase',
        'purchase__supplier',
        'delivery',
        'storage_site',
        'storage_location',
    )
    table = tables.AssetTable
    filterset = filtersets.AssetFilterSet
    filterset_form = forms.AssetFilterForm
    related_mapping = {
        'bom': (models.BOM, 'bom'),
        'delivery': (models.Delivery, 'delivery'),
        'purchase': (models.Purchase, 'purchase'),
        'transfer': (models.Transfer, 'transfer'),
    }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        related_type = request.GET.get('related_type')
        if related_type and related_type in self.related_mapping:
            _, related_field = self.related_mapping[related_type]
            # Exclude objects that are already assigned to the related object
            filter_kwargs = {f"{related_field}__isnull": True}
            queryset = queryset.filter(**filter_kwargs)
        return queryset

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'assets'
        return context


class AssignToDeliveryView(BulkAssignView):
    queryset = models.Delivery.objects.annotate(
        asset_count=count_related(models.Asset, 'delivery'),
    )
    table = tables.DeliveryTable
    filterset = filtersets.DeliveryFilterSet
    filterset_form = forms.DeliveryFilterForm
    related_mapping = {
        'purchase': (models.Purchase, 'purchases'),
    }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        related_type = request.GET.get('related_type')
        if related_type and related_type in self.related_mapping:
            _, related_field = self.related_mapping[related_type]
            # Exclude objects that are already assigned to the related object
            filter_kwargs = {f"{related_field}__isnull": True}
            queryset = queryset.filter(**filter_kwargs)
        return queryset

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'deliveries'
        return context


class AssignToPurchaseView(BulkAssignView):
    queryset = models.Purchase.objects.annotate(
        asset_count=count_related(models.Asset, 'purchase'),
        delivery_count=count_related(models.Delivery, 'purchases'),
    )
    table = tables.PurchaseTable
    filterset = filtersets.PurchaseFilterSet
    filterset_form = forms.PurchaseFilterForm
    related_mapping = {
        'bom': (models.BOM, 'boms'),
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'purchases'
        return context


#
# Bulk Assign Related Views
#


class AssignBOMsToPurchaseView(BulkAssignRelatedView):
    queryset = models.BOM.objects.annotate(
        purchase_count=count_related(models.Purchase, 'boms'),
        asset_count=count_related(models.Asset, 'bom'),
    )
    table = tables.BOMTable
    filterset = filtersets.BOMFilterSet
    filterset_form = forms.BOMFilterForm
    related_mapping = {
        'purchase': (models.Purchase, 'boms'),
    }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        related_id = request.GET.get('related_id')
        if related_id:
            # Exclude BOMs already assigned to this purchase
            queryset = queryset.exclude(purchases__id=related_id)
        return queryset

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'BOMs'
        return context


class AssignPurchasesToDeliveryView(BulkAssignRelatedView):
    queryset = models.Purchase.objects.annotate(
        asset_count=count_related(models.Asset, 'purchase'),
        delivery_count=count_related(models.Delivery, 'purchases'),
    )
    table = tables.PurchaseTable
    filterset = filtersets.PurchaseFilterSet
    filterset_form = forms.PurchaseFilterForm
    related_mapping = {
        'delivery': (models.Delivery, 'purchases'),
    }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        related_id = request.GET.get('related_id')
        if related_id:
            # Exclude Purchases already assigned to this delivery
            queryset = queryset.exclude(orders__id=related_id)
        return queryset

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'purchases'
        return context
