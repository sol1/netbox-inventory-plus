import logging

from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from dcim.models import Device, InventoryItem, Module, Rack
from utilities.exceptions import AbortRequest

from .choices import AssetStatusChoices
from .models import Asset, Delivery, Transfer
from .utils import get_plugin_setting, get_status_for, is_equal_none

logger = logging.getLogger('netbox.netbox_inventory.signals')


@receiver(pre_save, sender=Device)
@receiver(pre_save, sender=Module)
@receiver(pre_save, sender=InventoryItem)
@receiver(pre_save, sender=Rack)
def prevent_update_serial_asset_tag(instance, **kwargs):
    """
    When a hardware (Device, Module, InventoryItem, Rack) has an Asset assigned and
    user changes serial or asset_tag on hardware, prevent that change
    and inform that change must be made on Asset instance instead.

    Only enforces if `sync_hardware_serial_asset_tag` setting is true.
    """
    try:
        # will raise RelatedObjectDoesNotExist if not set
        asset = instance.assigned_asset
    except Asset.DoesNotExist:
        return
    if not get_plugin_setting('sync_hardware_serial_asset_tag'):
        # don't enforce if sync not enabled
        return
    if instance.pk and (
        not is_equal_none(asset.serial, instance.serial)
        or not is_equal_none(asset.asset_tag, instance.asset_tag)
    ):
        raise AbortRequest(
            f'Cannot change {asset.kind} serial and asset tag if asset is assigned. Please update via inventory > asset instead.'
        )


@receiver(pre_delete, sender=Device)
@receiver(pre_delete, sender=Module)
@receiver(pre_delete, sender=InventoryItem)
@receiver(pre_delete, sender=Rack)
def free_assigned_asset(instance, **kwargs):
    """
    If a hardware (Device, Module, InventoryItem, Rack) has an Asset assigned and
    that hardware is deleted, update Asset.status to stored_status.

    Netbox handles deletion in a DB transaction, so if deletion failes for any
    reason, this status change will also be reverted.
    """
    stored_status = get_status_for('stored')
    if not stored_status:
        return
    try:
        # will raise RelatedObjectDoesNotExist if not set
        asset = instance.assigned_asset
    except Asset.DoesNotExist:
        return
    asset.snapshot()
    asset.status = stored_status
    # also unassign that item from asset
    setattr(asset, asset.kind, None)
    asset.full_clean()
    asset.save(clear_old_hw=False)
    logger.info(f'Asset marked as stored {asset}')


@receiver(post_save, sender=Delivery)
def handle_delivery_purchase_change(instance, created, **kwargs):
    """
    Update child Assets if Delivery Purchase has changed.
    """
    if not created:
        Asset.objects.filter(delivery=instance).update(purchase=None)

        for purchase in instance.purchases.all():
            Asset.objects.filter(delivery=instance).update(purchase=purchase)


@receiver(post_save, sender=Asset)
def close_bom_if_all_assets_delivered(instance, **kwargs):
    """
    Close BOM if all Assets are delivered.
    """
    if instance.bom:
        all_assets_delivered = not instance.bom.assets.filter(Q(delivery__isnull=True)).exists()
        if all_assets_delivered:
            instance.bom.status = 'closed'
            instance.bom.save()
            logger.info(f"BOM {instance.bom} marked as 'Closed' because all associated assets are delivered.")


@receiver(post_save, sender=Transfer)
def update_assets_status_on_pickup(instance, **kwargs):
    """
    Update the status of all transferred Assets to 'In Transit' when the pickup_date is set.
    """
    transit_status = get_status_for('transit')
    stored_status = get_status_for('stored')
    assets_to_update = instance.get_assets()

    if instance.pickup_date and not instance.received_date:
        assets_to_update.update(
            status=transit_status,
            storage_location=None
        )
    else:
        assets_to_update.update(
            status=stored_status,
            storage_location=instance.location
        )

@receiver(post_save, sender=Asset)
def update_asset_status(instance, **kwargs):
    planned_status = get_status_for('planned')
    ordered_status = get_status_for('ordered')
    stored_status = get_status_for('stored')

    if instance.purchase and instance.delivery:
        new_status = stored_status
    elif instance.purchase and not instance.delivery:
        new_status = ordered_status
    else:
        new_status = planned_status

    if instance.status != new_status:
        Asset.objects.filter(pk=instance.pk).update(status=new_status)