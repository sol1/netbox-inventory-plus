from datetime import date

from django.db import models
from django.forms import ValidationError
from django.urls import reverse

from netbox.models import NestedGroupModel, NetBoxModel
from netbox.models.features import ImageAttachmentsMixin

from ..choices import AssetStatusChoices, HardwareKindChoices
from ..utils import (
    asset_clear_old_hw,
    asset_set_new_hw,
    get_plugin_setting,
    get_prechange_field,
    get_status_for,
)


class InventoryItemGroup(NestedGroupModel):
    """
    Inventory Item Groups are groups of simmilar InventoryItemTypes.
    This allows you to, for example, have one Group for all your 10G-LR SFP
    pluggables, from different manufacturers/with different part numbers.
    Inventory Item Groups can be nested.
    """

    slug = None  # remove field that is defined on NestedGroupModel

    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        constraints = (
            models.UniqueConstraint(
                fields=('parent', 'name'), name='%(app_label)s_%(class)s_parent_name'
            ),
            models.UniqueConstraint(
                fields=('name',),
                name='%(app_label)s_%(class)s_name',
                condition=models.Q(parent__isnull=True),
                violation_error_message='A top-level group with this name already exists.',
            ),
        )

    def get_absolute_url(self):
        return reverse('plugins:netbox_inventory:inventoryitemgroup', args=[self.pk])


class InventoryItemType(NetBoxModel, ImageAttachmentsMixin):
    """
    Inventory Item Type is a model (make, part number) of an Inventory Item. In
    that it is simmilar to Device Type or Module Type.
    """

    manufacturer = models.ForeignKey(
        to='dcim.Manufacturer',
        on_delete=models.PROTECT,
        related_name='inventoryitem_types',
    )
    model = models.CharField(
        max_length=100,
    )
    slug = models.SlugField(
        max_length=100,
    )
    part_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Discrete part number (optional)',
        verbose_name='Part Number',
    )
    inventoryitem_group = models.ForeignKey(
        to='netbox_inventory.InventoryItemGroup',
        on_delete=models.SET_NULL,
        related_name='inventoryitem_types',
        blank=True,
        null=True,
        verbose_name='Inventory Item Group',
    )
    description = models.CharField(
        max_length=200,
        blank=True,
    )
    comments = models.TextField(
        blank=True,
    )

    clone_fields = [
        'manufacturer',
    ]

    class Meta:
        ordering = ['manufacturer', 'model']
        unique_together = [
            ['manufacturer', 'model'],
            ['manufacturer', 'slug'],
        ]

    def __str__(self):
        return self.model

    def get_absolute_url(self):
        return reverse('plugins:netbox_inventory:inventoryitemtype', args=[self.pk])


class Asset(NetBoxModel, ImageAttachmentsMixin):
    """
    An Asset represents a piece of hardware we want to keep track of. It has a
    make (model, part number) that is one of: Device Type, Module Type,
    InventoryItem Type or Rack Type.

    Asset must have a serial number, can have an asset tag (inventory number). It
    must have one of DeviceType, ModuleType, InventoryItemType, RackType. It can have
    a storage location (instance of Location). There are also fields to keep track of
    purchase and warranty info.

    An asset that is in use, can be assigned to a Device, Module, InventoryItem or
    Rack.
    """

    #
    # fields that identify asset
    #
    name = models.CharField(
        help_text='Can be used to quickly identify a particular asset',
        max_length=128,
        blank=True,
        null=False,
        default='',
    )
    description = models.CharField(
        max_length=200,
        blank=True,
    )
    asset_tag = models.CharField(
        help_text='Identifier assigned by owner',
        max_length=50,
        blank=True,
        null=True,
        default=None,
        verbose_name='Asset Tag',
    )
    serial = models.CharField(
        help_text='Identifier assigned by manufacturer',
        max_length=60,
        verbose_name='Serial Number',
        blank=True,
        null=True,
        default=None,
    )

    #
    # status fields
    #
    status = models.CharField(
        max_length=30,
        choices=AssetStatusChoices,
        help_text='Asset lifecycle status',
    )

    #
    # hardware type fields
    #
    device_type = models.ForeignKey(
        to='dcim.DeviceType',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
        verbose_name='Device Type',
    )
    module_type = models.ForeignKey(
        to='dcim.ModuleType',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
        verbose_name='Module Type',
    )
    inventoryitem_type = models.ForeignKey(
        to='netbox_inventory.InventoryItemType',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Inventory Item Type',
    )
    rack_type = models.ForeignKey(
        to='dcim.RackType',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
        verbose_name='Rack Type',
    )

    #
    # used fields
    #
    device = models.OneToOneField(
        to='dcim.Device',
        on_delete=models.SET_NULL,
        related_name='assigned_asset',
        blank=True,
        null=True,
    )
    module = models.OneToOneField(
        to='dcim.Module',
        on_delete=models.SET_NULL,
        related_name='assigned_asset',
        blank=True,
        null=True,
    )
    inventoryitem = models.OneToOneField(
        to='dcim.InventoryItem',
        on_delete=models.SET_NULL,
        related_name='assigned_asset',
        blank=True,
        null=True,
        verbose_name='Inventory Item',
    )
    rack = models.OneToOneField(
        to='dcim.Rack',
        on_delete=models.SET_NULL,
        related_name='assigned_asset',
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        help_text='Tenant using this asset',
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
    )
    contact = models.ForeignKey(
        help_text='Contact using this asset',
        to='tenancy.Contact',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
    )
    storage_site = models.ForeignKey(
        help_text='Site where this asset is stored when not in use',
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Storage Site',
    )
    storage_location = models.ForeignKey(
        help_text='Location where this asset is stored when not in use',
        to='dcim.Location',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Storage Location',
    )

    #
    # purchase info
    #
    owner = models.ForeignKey(
        help_text='Who owns this asset',
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True,
    )
    bom = models.ForeignKey(
        help_text='BOM this asset is part of',
        to='netbox_inventory.BOM',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
        verbose_name='BOM',
    )
    delivery = models.ForeignKey(
        help_text='Delivery this asset was part of',
        to='netbox_inventory.Delivery',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
    )
    transfer = models.ForeignKey(
        help_text='Transfer this asset is part of',
        to='netbox_inventory.Transfer',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
    )
    purchase = models.ForeignKey(
        help_text='Purchase through which this asset was purchased',
        to='netbox_inventory.Purchase',
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
    )
    warranty_start = models.DateField(
        help_text='First date warranty for this asset is valid',
        blank=True,
        null=True,
        verbose_name='Warranty Start',
    )
    warranty_end = models.DateField(
        help_text='Last date warranty for this asset is valid',
        blank=True,
        null=True,
        verbose_name='Warranty End',
    )
    eol_date = models.DateField(
        help_text='Date when this asset is no longer supported',
        blank=True,
        null=True,
        verbose_name='End of Life Date',
    )

    comments = models.TextField(
        blank=True,
    )

    clone_fields = [
        'name',
        'asset_tag',
        'status',
        'device_type',
        'module_type',
        'inventoryitem_type',
        'owner',
        'purchase',
        'delivery',
        'warranty_start',
        'warranty_end',
        'eol_date',
        'tenant',
        'contact',
        'storage_site',
        'storage_location',
        'comments',
    ]

    @property
    def kind(self):
        if self.device_type_id:
            return 'device'
        elif self.module_type_id:
            return 'module'
        elif self.inventoryitem_type_id:
            return 'inventoryitem'
        elif self.rack_type_id:
            return 'rack'
        assert False, f'Invalid hardware kind detected for asset {self.pk}'

    def get_kind_display(self):
        return dict(HardwareKindChoices)[self.kind]

    @property
    def hardware_type(self):
        return (
            self.device_type
            or self.module_type
            or self.inventoryitem_type
            or self.rack_type
            or None
        )

    @property
    def hardware(self):
        return self.device or self.module or self.inventoryitem or self.rack or None

    @property
    def installed_site(self):
        device = self.installed_device
        if device:
            return device.site
        if self.rack:
            return self.rack.site

    @property
    def installed_location(self):
        device = self.installed_device
        if device:
            return device.location
        if self.rack:
            return self.rack.location

    @property
    def installed_rack(self):
        device = self.installed_device
        if device:
            return device.rack
        if self.rack:
            return self.rack

    @property
    def installed_device(self):
        if self.kind == 'rack':
            return None
        elif self.kind == 'device':
            return self.device
        elif self.hardware:
            return self.hardware.device
        else:
            return None

    @property
    def current_site(self):
        installed = self.installed_site
        if installed:
            return installed
        return self.storage_site

    @property
    def current_location(self):
        installed = self.installed_location
        if installed:
            return installed
        return self.storage_location

    @property
    def current_date(self):
        return date.today()

    @property
    def warranty_remaining(self):
        """
        How many days are left in warranty period.
        Returns negative duration if warranty expired
        Return None if warranty_end not defined
        """
        if self.warranty_end:
            return self.warranty_end - date.today()
        return None

    @property
    def warranty_elapsed(self):
        """
        How many days have passed in warranty period.
        Returns negative duration if period has not started yet
        Return None if warranty_start not defined
        """
        if self.warranty_start:
            return date.today() - self.warranty_start
        return None

    @property
    def warranty_total(self):
        if self.warranty_end and self.warranty_start:
            return self.warranty_end - self.warranty_start
        return None

    @property
    def warranty_progress(self):
        """
        Percentage of warranty elapsed
        Returns > 100 if warranty has expired, < 0 if not started yet and None
        if warranty_start or warranty_end not set.
        """
        if not self.warranty_start or not self.warranty_end:
            return None
        return int(100 * (self.warranty_elapsed / self.warranty_total))

    @property
    def eol_remaining(self):
        """
        How many days are left in time period before EOL.
        Returns negative duration if EOL is reached
        Return None if eol_date not defined
        """
        if self.eol_date:
            return self.eol_date - date.today()
        return None

    @property
    def eol_progress(self):
        """
        Percentage of time elapsed until EOL.
        Returns > 100 if EOL has passed, < 0 if EOL is far in the future, and None
        if eol_date is not set.
        """
        if not self.eol_date:
            return None
        total_duration = (self.eol_date - self.current_date).days
        elapsed_duration = (self.current_date - self.current_date).days  # Always 0
        if total_duration <= 0:
            return 100  # EOL has passed
        return int(100 * (elapsed_duration / total_duration))

    def clean(self):
        self.clean_delivery()
        self.clean_warranty_dates()
        self.validate_hardware_types()
        self.validate_hardware()
        self.update_status()
        self.update_location()
        self.infer_storage_site()
        self.sync_hardware_eol()
        return super().clean()

    def save(self, clear_old_hw=True, *args, **kwargs):
        self.update_hardware_used(clear_old_hw)
        return super().save(*args, **kwargs)

    def clean_delivery(self):
        if self.delivery and not self.purchase:
            self.purchase = self.delivery.purchases.first()
        if self.delivery:
            if self.purchase and self.purchase not in self.delivery.purchases.all():
                raise ValidationError(
                    {
                        'purchase': 'The selected purchase is not associated with the delivery.'
                    }
                )

    def clean_warranty_dates(self):
        if (
            self.warranty_start
            and self.warranty_end
            and self.warranty_end <= self.warranty_start
        ):
            raise ValidationError(
                {'warranty_end': 'Warranty end date must be after warranty start date.'}
            )

    def validate_hardware_types(self):
        """
        Ensure only one device/module_type/inventoryitem_type/rack_type is set at a time.
        """
        if (
            sum(
                map(
                    bool,
                    [
                        self.device_type,
                        self.module_type,
                        self.inventoryitem_type,
                        self.rack_type,
                    ],
                )
            )
            > 1
        ):
            raise ValidationError(
                'Only one of device type, module type inventory item type and rack type can be set for the same asset.'
            )
        if (
            not self.device_type
            and not self.module_type
            and not self.inventoryitem_type
            and not self.rack_type
        ):
            raise ValidationError(
                'One of device type, module type, inventory item type or rack type must be set.'
            )

    def validate_hardware(self):
        """
        Ensure only one device/module is set at a time and it matches device/module_type.
        """
        kind = self.kind
        _type = getattr(self, kind + '_type')
        hw = getattr(self, kind)
        hw_others = dict(HardwareKindChoices).keys() - [kind]

        # e.g.: self.device_type and self.device.device_type must match
        # InventoryItem does not have FK to InventoryItemType
        if kind != 'inventoryitem':
            if not getattr(self, '_in_reassign', False):
                # but don't check if we are reassigning asset to another device
                if hw and _type != getattr(hw, kind + '_type'):
                    raise ValidationError(
                        {
                            kind: f'{kind} type of {kind} does not match {kind} type of asset'
                        }
                    )
        # ensure only one hardware is set and that it is correct kind
        # e.g. if self.device_type is set, we cannot have self.module or self.inventoryitem set
        for hw_other in hw_others:
            if getattr(self, hw_other):
                raise ValidationError(
                    f'Cannot set {hw_other} for asset that is a {kind}'
                )

    def update_status(self):
        """
        If asset was assigned or unassigned to a particular device, module, inventoryitem, rack
        update asset.status. Depending on plugin configuration.
        """
        # Retired: Asset is retired; do not change status automatically
        if self.status == get_status_for('retired'):
            return

        new_hw = getattr(self, self.kind)
        old_status = get_prechange_field(self, 'status')
        used_status = get_status_for('used')
        stored_status = get_status_for('stored')
        ordered_status = get_status_for('ordered')
        planned_status = get_status_for('planned')

        # Manual/Bulk Assignment: Status has been set manually or Asset is part of bulk assignment;
        # do not change it
        if not getattr(self, '_in_bulk_assignment', False) and old_status != self.status:
            return

        # Used: Asset was assigned
        if used_status and new_hw:
            self.status = used_status
            return

        # Stored: Unassigned but fully delivered and purchased
        if stored_status and self.delivery and not new_hw:
            self.status = stored_status
            return

        # Ordered: Purchase just got created
        if ordered_status and self.purchase:
            self.status = ordered_status
            return

        # Planned: Default status
        self.status = planned_status

    def update_location(self):
        """
        Update the location of the Asset based on the location of the assigned Delivery. Only
        update if the assigned Delivery changes.
        """
        old_delivery = get_prechange_field(self, 'delivery')
        new_delivery = self.delivery
        new_hw = getattr(self, self.kind)

        if old_delivery != new_delivery:
            if new_delivery and not new_hw:
                self.storage_site = new_delivery.delivery_site
                self.storage_location = new_delivery.delivery_location

    def infer_storage_site(self):
        """
        If only storage_location is set, infer storage_site from it
        """
        if self.storage_location and not self.storage_site:
            self.storage_site = self.storage_location.site
            return

    def update_hardware_used(self, clear_old_hw=True):
        """
        If assigning as device, module, inventoryitem or rack set serial and
        asset_tag on it. Also remove them if unasigning.
        """
        if not get_plugin_setting('sync_hardware_serial_asset_tag'):
            return None
        old_hw = get_prechange_field(self, self.kind)
        new_hw = getattr(self, self.kind)
        if old_hw:
            old_hw.snapshot()
        if new_hw:
            new_hw.snapshot()
        old_serial = get_prechange_field(self, 'serial')
        old_asset_tag = get_prechange_field(self, 'asset_tag')
        if not new_hw and old_hw and clear_old_hw:
            # unassigned existing asset, nothing asssigned now
            asset_clear_old_hw(old_hw)
        elif new_hw and old_hw != new_hw:
            # assigned something new
            if old_hw and clear_old_hw:
                # but first clear previous hw data
                asset_clear_old_hw(old_hw)
            asset_set_new_hw(asset=self, hw=new_hw)
        elif self.serial != old_serial or self.asset_tag != old_asset_tag:
            # just changed asset's serial or asset_tag, update assigned hw
            if new_hw:
                asset_set_new_hw(asset=self, hw=new_hw)

    def sync_hardware_eol(self):
        """
        Sync asset's eol_date from corresponding hardware type if plugin setting is enabled.
        Do not sync if eol_date is set manually and the hardware type is not set again.
        """
        if not get_plugin_setting('sync_hardware_eol_date'):
            return

        old_eol_date = get_prechange_field(self, 'eol_date')
        new_eol_date = getattr(self, 'eol_date')
        if old_eol_date and isinstance(old_eol_date, str):
            old_eol_date = date.fromisoformat(old_eol_date)
        if new_eol_date and isinstance(new_eol_date, str):
            new_eol_date = date.fromisoformat(new_eol_date)

        if old_eol_date != new_eol_date:
            # eol_date changed manually, do not sync
            return

        hw_type = self.hardware_type
        if hw_type:
            eol_date = hw_type.cf.get('eol_date') if hasattr(hw_type, 'cf') else None
            self.eol_date = eol_date if eol_date else None

    def get_absolute_url(self):
        return reverse('plugins:netbox_inventory:asset', args=[self.pk])

    def get_status_color(self):
        return AssetStatusChoices.colors.get(self.status)

    def __str__(self):
        if self.serial:
            return f'{self.hardware_type} {self.serial}'
        else:
            return f'{self.hardware_type} (id:{self.id})'

    class Meta:
        ordering = (
            'device_type',
            'module_type',
            'inventoryitem_type',
            'rack_type',
            'serial',
        )
        constraints = (
            models.UniqueConstraint(
                fields=('device_type', 'serial'),
                name='unique_device_type_serial',
            ),
            models.UniqueConstraint(
                fields=('module_type', 'serial'),
                name='unique_module_type_serial',
            ),
            models.UniqueConstraint(
                fields=('inventoryitem_type', 'serial'),
                name='unique_inventoryitem_type_serial',
            ),
            models.UniqueConstraint(
                fields=('rack_type', 'serial'),
                name='unique_rack_type_serial',
            ),
            models.UniqueConstraint(
                fields=('owner', 'asset_tag'),
                name='unique_owner_asset_tag',
            ),
            models.UniqueConstraint(
                'asset_tag',
                condition=models.Q(owner__isnull=True),
                name='unique_asset_tag',
                violation_error_message='Asset with this Asset Tag and no Owner already exists.',
            ),
        )
