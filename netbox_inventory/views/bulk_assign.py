from django.contrib import messages
from django.db.models import ForeignKey, ManyToManyField
from django.shortcuts import redirect
from django.urls import reverse

from netbox.views import generic

from .. import models, tables

__all__ = (
    'GenericBulkAssignView',
    'GenericBulkAssignNoFieldView',
    'AssetBulkAssignView',
    'BOMBulkAssignView',
    'DeliveryBulkAssignView',
    'DeliveryBulkAssignPurchasesView',
    'PurchaseBulkAssignView',
)


class GenericBulkAssignView(generic.ObjectListView):
    """
    A template view for bulk assignment of objects that have a corresponding field.
    """   
    queryset = None  
    table = None  
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
            raise ValueError(f"Invalid related type: {related_type}")
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
        error_redirect_path = f"{request.path}?related_type={related_type}&related_id={related_id}&related_name={related_name}"

        if not related_type or not related_id or not object_ids:
            messages.error(request, "No related object or items selected.")
            return redirect(error_redirect_path)

        try:
            related_model, related_field = self.get_related_model_and_field(related_type)
            related_instance = related_model.objects.get(pk=related_id)
        except ValueError:
            messages.error(request, f"Invalid related type: {related_type}.")
            return redirect(error_redirect_path)
        
        try:
            related_instance = related_model.objects.get(pk=related_id)
        except related_model.DoesNotExist:
            messages.error(request, f"Related object with ID {related_id} does not exist.")
            return redirect(error_redirect_path)
        
        field_object = self.queryset.model._meta.get_field(related_field)

        if isinstance(field_object, ForeignKey):
            objects = self.queryset.filter(pk__in=object_ids)
            objects.update(**{related_field: related_instance})
        elif isinstance(field_object, ManyToManyField):
            objects = self.queryset.filter(pk__in=object_ids)
            for obj in objects:
                getattr(obj, related_field).add(related_instance)
        else:
            messages.error(request, "Unsupported field type for bulk assignment.")
            return redirect(error_redirect_path)

        messages.success(request, f"Successfully assigned {objects.count()} items to {related_name}.")
        return redirect(reverse(f'plugins:netbox_inventory:{related_type}', args=[related_id]))
    

class GenericBulkAssignNoFieldView(GenericBulkAssignView):
    """
    A template view for bulk assignment of objects that do not have a corresponding field.
    """   
    def post(self, request, *args, **kwargs):
        related_type = request.GET.get('related_type')
        related_id = request.GET.get('related_id')
        related_name = request.GET.get('related_name')
        object_ids = request.POST.getlist('pk')
        error_redirect_path = f"{request.path}?related_type={related_type}&related_id={related_id}&related_name={related_name}"

        if not related_type or not related_id or not object_ids:
            messages.error(request, "No related object or BOMs selected.")
            return redirect(error_redirect_path)

        try:
            related_model, related_field = self.get_related_model_and_field(related_type)
            related_instance = related_model.objects.get(pk=related_id)
        except (ValueError, related_model.DoesNotExist):
            messages.error(request, "Invalid related object or type.")
            return redirect(error_redirect_path)
    
        objects = self.queryset.filter(pk__in=object_ids)
        getattr(related_instance, related_field).add(*objects)

        messages.success(request, f"Successfully assigned {objects.count()} BOMs to {related_name}.")
        return redirect(related_instance.get_absolute_url())
    

class AssetBulkAssignView(GenericBulkAssignView):
    queryset = models.Asset.objects.all()
    table = tables.AssetTable
    related_mapping = {
        'bom': (models.BOM, 'bom'),
        'delivery': (models.Delivery, 'delivery'),
        'purchase': (models.Purchase, 'purchase'),
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'assets'
        return context
    

class BOMBulkAssignView(GenericBulkAssignNoFieldView):
    queryset = models.BOM.objects.all()
    table = tables.BOMTable
    related_mapping = {
        'purchase': (models.Purchase, 'boms'), 
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'BOMs'
        return context


class DeliveryBulkAssignView(GenericBulkAssignView):
    queryset = models.Delivery.objects.all()
    table = tables.DeliveryTable
    related_mapping = {
        'purchase': (models.Purchase, 'purchases'),
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'deliveries'
        return context


class DeliveryBulkAssignPurchasesView(GenericBulkAssignNoFieldView):
    queryset = models.Purchase.objects.all()
    table = tables.PurchaseTable
    related_mapping = {
        'delivery': (models.Delivery, 'purchases'), 
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'purchases'
        return context


class PurchaseBulkAssignView(GenericBulkAssignView):
    queryset = models.Purchase.objects.all()
    table = tables.PurchaseTable
    related_mapping = {
        'bom': (models.BOM, 'boms'),
    }

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context['object_type_plural'] = 'purchases'
        return context