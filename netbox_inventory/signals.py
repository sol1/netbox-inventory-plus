import logging

from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from dcim.models import (
    Device,
    DeviceType,
    InventoryItem,
    Module,
    ModuleType,
    Rack,
    RackType,
)
from utilities.exceptions import AbortRequest

from .models import Asset, Delivery, InventoryItemType, Transfer
from .utils import (
    get_plugin_setting,
    get_prechange_field,
    get_status_for,
    is_equal_none,
)

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

    bom = instance.bom
    # check if bom is set and not already closed
    if bom and bom.status != 'closed':
        all_assets_delivered = not bom.assets.filter(
            Q(delivery__isnull=True)
        ).exists()
        if all_assets_delivered:
            bom.status = 'closed'
            bom.full_clean()
            bom.save()
            logger.info(
                f"BOM {bom} marked as 'Closed' because all associated assets are delivered."
            )


@receiver(post_save, sender=Transfer)
def update_assets_status_on_pickup(instance, **kwargs):
    """
    Update the status of all transferred Assets to 'In Transit' when the pickup_date is set.
    """
    transit_status = get_status_for('transit')
    stored_status = get_status_for('stored')
    assets_to_update = instance.get_assets()

    if instance.pickup_date and not instance.received_date:
        assets_to_update.update(status=transit_status, storage_location=None)
    else:
        assets_to_update.update(
            status=stored_status, storage_location=instance.location
        )


@receiver(post_save, sender=DeviceType)
@receiver(post_save, sender=ModuleType)
@receiver(post_save, sender=InventoryItemType)
@receiver(post_save, sender=RackType)
def update_asset_eol_dates(sender, instance, **kwargs):
    """
    Update the eol_date of all Assets when the eol_date of the corresponding hardware
    type is changed.
    """
    if not get_plugin_setting('sync_hardware_eol_date'):
        return

    if 'eol_date' not in instance.cf:
        return

    eol_date = instance.cf.get('eol_date', None)
    if sender == DeviceType:
        hw_field = 'device_type'
    elif sender == ModuleType:
        hw_field = 'module_type'
    # elif sender == InventoryItemType:
    #     hw_field = 'inventoryitem_type'
    elif sender == RackType:
        hw_field = 'rack_type'
    else:
        return

    assets_to_update = Asset.objects.filter(**{hw_field: instance})
    for asset in assets_to_update:
        asset.eol_date = eol_date
        asset.full_clean()
        asset.save()


@receiver(post_save, sender=Delivery)
def update_assets_delivery_site_location(instance, created, **kwargs):
    """
    Update the delivery site and location of all Assets when the delivery site or location of the
    Delivery is changed. Only update Assets that are still matched to the old delivery site and
    location.
    - when asset is saved if old delivery is different from new delivery update site/location else
    nothing
    - if delivery site/location is change update assets only if the current asset site/location the
    same as the old delivery site/location
    """
    if not created:
        old_delivery_site = get_prechange_field(instance, 'delivery_site')
        old_delivery_location = get_prechange_field(instance, 'delivery_location')

        if (
            instance.delivery_site != old_delivery_site
            or instance.delivery_location != old_delivery_location
        ):
            Asset.objects.filter(
                Q(storage_site_id=old_delivery_site)
                & Q(storage_location_id=old_delivery_location)
            ).update(
                storage_site_id=instance.delivery_site,
                storage_location_id=instance.delivery_location,
            )