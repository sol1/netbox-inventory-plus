from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect

from netbox.views import generic

from .. import filtersets, forms, models, tables

__all__ = (
    'AssignAssetsToBOMView',
    'AssignAssetsToDeliveryView',
    'AssignAssetsToPurchaseView',
    'AssignBOMsToPurchaseView',
    'AssignPurchasesToDeliveryView',
)


# Bulk Assign Views
class AssignAssetsView(generic.ObjectListView):
    """
    Generic view to assign existing Assets to a parent object via a ForeignKey on the Asset model.
    """
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
        'purchase',
        'delivery',
    )
    table = tables.AssetTable
    filterset = filtersets.AssetFilterSet
    filterset_form = forms.AssetFilterForm

    template_name = 'netbox_inventory_plus/bulk_assign.html'
    parent_model = None
    parent_attr_name = None

    def dispatch(self, request, *args, **kwargs):
        self.parent = get_object_or_404(self.parent_model, pk=kwargs.pop('pk'))
        return super().dispatch(request, *args, **kwargs)

    def scope_queryset(self, queryset):
        raise NotImplementedError("Subclasses must implement scope_queryset() method.")

    def get_queryset(self, request):
        return self.scope_queryset(super().get_queryset(request))

    def get_extra_context(self, request):
        return {
            self.parent_attr_name: self.parent,
            'parent': self.parent,
            'object_type_plural': 'assets',
        }

    def post(self, request, *args, **kwargs):
        asset_ids = request.POST.getlist('pk')
        if not asset_ids:
            messages.error(request, 'No assets selected.')
            return redirect(request.get_full_path())

        assets = models.Asset.objects.filter(pk__in=asset_ids)
        for asset in assets:
            setattr(asset, self.parent_attr_name, self.parent)
            asset._in_bulk_assignment = True
            asset.full_clean()
            asset.save()
            asset._in_bulk_assignment = False

        messages.success(
            request,
            f'Successfully assigned {assets.count()} Assets to {self.parent}.',
        )
        return redirect(self.parent.get_absolute_url())


class AssignAssetsToBOMView(AssignAssetsView):
    parent_model = models.BOM
    parent_attr_name = 'bom'

    def scope_queryset(self, queryset):
        return self.queryset.filter(bom__isnull=True)

class AssignAssetsToPurchaseView(AssignAssetsView):
    parent_model = models.Purchase
    parent_attr_name = 'purchase'

    def scope_queryset(self, queryset):
        bom_ids = self.parent.boms.values_list('id', flat=True)
        return queryset.filter(bom_id__in=bom_ids, purchase__isnull=True)


class AssignAssetsToDeliveryView(AssignAssetsView):
    parent_model = models.Delivery
    parent_attr_name = 'delivery'

    def scope_queryset(self, queryset):
        purchase_ids = self.parent.purchases.values_list('id', flat=True)
        return queryset.filter(purchase_id__in=purchase_ids, delivery__isnull=True)


class AssignRelatedObjectsView(generic.ObjectListView):
    """
    Generic view to assign existing objects to a parent object via a ManyToMany field.
    """

    parent_model = None
    related_model = None
    related_field = None

    table = None
    filterset = None
    filterset_form = None
    template_name = 'netbox_inventory_plus/bulk_assign.html'

    def dispatch(self, request, *args, **kwargs):
        self.parent = get_object_or_404(self.parent_model, pk=kwargs.pop('pk'))
        return super().dispatch(request, *args, **kwargs)

    def annotate_queryset(self, queryset):
        return queryset.annotate(
            asset_count=Count('assets', distinct=True),
        )

    def get_queryset(self, request):
        assigned_ids = getattr(self.parent, self.related_field).values_list('id', flat=True)
        qs = self.related_model.objects.exclude(pk__in=assigned_ids)
        return self.annotate_queryset(qs)

    def get_extra_context(self, request):
        return {
            'parent': self.parent,
            'object_type_plural': self.related_model._meta.verbose_name_plural,
        }

    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist('pk')
        if not selected_ids:
            messages.error(request, f'No {self.related_model._meta.verbose_name} selected.')
            return redirect(request.get_full_path())

        related_objects = self.related_model.objects.filter(pk__in=selected_ids)
        getattr(self.parent, self.related_field).add(*related_objects)

        messages.success(
            request,
            f'Successfully assigned {related_objects.count()} '
            f'{self.related_model._meta.verbose_name_plural} to {self.parent}.',
        )
        return redirect(self.parent.get_absolute_url())


class AssignBOMsToPurchaseView(AssignRelatedObjectsView):
    parent_model = models.Purchase
    related_model = models.BOM
    related_field = 'boms'
    table = tables.BOMTable
    filterset = filtersets.BOMFilterSet
    filterset_form = forms.BOMFilterForm


class AssignPurchasesToDeliveryView(AssignRelatedObjectsView):
    parent_model = models.Delivery
    related_model = models.Purchase
    related_field = 'purchases'
    table = tables.PurchaseTable
    filterset = filtersets.PurchaseFilterSet
    filterset_form = forms.PurchaseFilterForm
