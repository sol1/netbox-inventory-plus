-- 10_copy_inventory.sql
--
-- Copy DATA from netbox_inventory_* into netbox_inventory_plus_*, remapping every
-- primary key via the target table's own identity sequence so copied rows never
-- collide with rows the plugin already created.
--
-- Called by copy_inventory_to_plus.sh INSIDE a single transaction. Contains NO
-- transaction control (no BEGIN/COMMIT/ROLLBACK) and no psql meta-commands, so the
-- orchestrator controls commit vs rollback. The old_id->new_id maps below are TEMP
-- tables that later files (20_remap_links.sql, 30_changelog.sql) reuse in the same
-- transaction; they are ON COMMIT DROP.

------------------------------------------------------------------------------
-- 1. Build old_id -> new_id maps. Each new_id comes from the TARGET table's
--    identity sequence, so it cannot collide with existing or future _plus_ ids.
------------------------------------------------------------------------------
CREATE TEMP TABLE _map_supplier ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_supplier','id')) AS new_id
  FROM netbox_inventory_supplier ORDER BY id;

CREATE TEMP TABLE _map_courier ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_courier','id')) AS new_id
  FROM netbox_inventory_courier ORDER BY id;

CREATE TEMP TABLE _map_bom ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_bom','id')) AS new_id
  FROM netbox_inventory_bom ORDER BY id;

CREATE TEMP TABLE _map_inventoryitemgroup ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_inventoryitemgroup','id')) AS new_id
  FROM netbox_inventory_inventoryitemgroup ORDER BY id;

CREATE TEMP TABLE _map_inventoryitemtype ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_inventoryitemtype','id')) AS new_id
  FROM netbox_inventory_inventoryitemtype ORDER BY id;

CREATE TEMP TABLE _map_purchase ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_purchase','id')) AS new_id
  FROM netbox_inventory_purchase ORDER BY id;

CREATE TEMP TABLE _map_delivery ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_delivery','id')) AS new_id
  FROM netbox_inventory_delivery ORDER BY id;

CREATE TEMP TABLE _map_transfer ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_transfer','id')) AS new_id
  FROM netbox_inventory_transfer ORDER BY id;

CREATE TEMP TABLE _map_asset ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_asset','id')) AS new_id
  FROM netbox_inventory_asset ORDER BY id;

CREATE TEMP TABLE _map_delivery_purchases ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_delivery_purchases','id')) AS new_id
  FROM netbox_inventory_delivery_purchases ORDER BY id;

CREATE TEMP TABLE _map_purchase_boms ON COMMIT DROP AS
  SELECT id AS old_id,
         nextval(pg_get_serial_sequence('netbox_inventory_plus_purchase_boms','id')) AS new_id
  FROM netbox_inventory_purchase_boms ORDER BY id;

------------------------------------------------------------------------------
-- 2. Copy rows, using the remapped primary keys and remapped internal FKs.
------------------------------------------------------------------------------

-- netbox_inventory_supplier -> netbox_inventory_plus_supplier  (no internal FKs)
INSERT INTO netbox_inventory_plus_supplier (
    id, created, last_updated, custom_field_data, name, slug, description, comments)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.slug, s.description, s.comments
FROM netbox_inventory_supplier s
JOIN _map_supplier m ON m.old_id = s.id;

-- netbox_inventory_courier -> netbox_inventory_plus_courier  (no internal FKs)
INSERT INTO netbox_inventory_plus_courier (
    id, created, last_updated, custom_field_data, name, slug, description, comments)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.slug, s.description, s.comments
FROM netbox_inventory_courier s
JOIN _map_courier m ON m.old_id = s.id;

-- netbox_inventory_bom -> netbox_inventory_plus_bom  (no internal FKs)
INSERT INTO netbox_inventory_plus_bom (
    id, created, last_updated, custom_field_data, name, status, description, comments)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.status, s.description, s.comments
FROM netbox_inventory_bom s
JOIN _map_bom m ON m.old_id = s.id;

-- netbox_inventory_inventoryitemgroup -> netbox_inventory_plus_inventoryitemgroup
--   parent_id -> inventoryitemgroup (self, remap)
INSERT INTO netbox_inventory_plus_inventoryitemgroup (
    id, created, last_updated, custom_field_data, name, comments, description,
    level, lft, parent_id, rght, tree_id)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.comments, s.description,
    s.level, s.lft,
    p.new_id,                 -- remap parent_id via _map_inventoryitemgroup
    s.rght, s.tree_id
FROM netbox_inventory_inventoryitemgroup s
JOIN _map_inventoryitemgroup m ON m.old_id = s.id
LEFT JOIN _map_inventoryitemgroup p ON p.old_id = s.parent_id;

-- netbox_inventory_inventoryitemtype -> netbox_inventory_plus_inventoryitemtype
--   inventoryitem_group_id -> inventoryitemgroup (remap); manufacturer_id external
INSERT INTO netbox_inventory_plus_inventoryitemtype (
    id, created, last_updated, custom_field_data, model, slug, part_number,
    description, comments, manufacturer_id, inventoryitem_group_id)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.model, s.slug, s.part_number,
    s.description,            -- NOT NULL in target
    s.comments,
    s.manufacturer_id,        -- external, keep as-is
    g.new_id                  -- remap inventoryitem_group_id
FROM netbox_inventory_inventoryitemtype s
JOIN _map_inventoryitemtype m ON m.old_id = s.id
LEFT JOIN _map_inventoryitemgroup g ON g.old_id = s.inventoryitem_group_id;

-- netbox_inventory_purchase -> netbox_inventory_plus_purchase
--   supplier_id -> supplier (remap)
INSERT INTO netbox_inventory_plus_purchase (
    id, created, last_updated, custom_field_data, name, date, description,
    delivery_instructions, comments, supplier_id, status)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.date, s.description,
    s.delivery_instructions,  -- NOT NULL in target
    s.comments,
    sup.new_id,               -- remap supplier_id
    s.status
FROM netbox_inventory_purchase s
JOIN _map_purchase m ON m.old_id = s.id
LEFT JOIN _map_supplier sup ON sup.old_id = s.supplier_id;

-- netbox_inventory_delivery -> netbox_inventory_plus_delivery
--   receiving_contact_id / delivery_location_id / delivery_site_id all external
INSERT INTO netbox_inventory_plus_delivery (
    id, created, last_updated, custom_field_data, name, date, description,
    comments, receiving_contact_id, delivery_location_id, delivery_site_id)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.date, s.description,
    s.comments,
    s.receiving_contact_id,   -- external, keep as-is
    s.delivery_location_id,   -- external, keep as-is
    s.delivery_site_id        -- external, keep as-is
FROM netbox_inventory_delivery s
JOIN _map_delivery m ON m.old_id = s.id;

-- netbox_inventory_transfer -> netbox_inventory_plus_transfer
--   courier_id -> courier (remap); location/recipient/sender/site external
INSERT INTO netbox_inventory_plus_transfer (
    id, created, last_updated, custom_field_data, name, shipping_number,
    instructions, status, pickup_date, received_date, comments,
    courier_id, location_id, recipient_id, sender_id, site_id)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.shipping_number,
    s.instructions, s.status, s.pickup_date, s.received_date, s.comments,
    c.new_id,                 -- remap courier_id
    s.location_id, s.recipient_id, s.sender_id, s.site_id   -- external, keep as-is
FROM netbox_inventory_transfer s
JOIN _map_transfer m ON m.old_id = s.id
LEFT JOIN _map_courier c ON c.old_id = s.courier_id;

-- netbox_inventory_asset -> netbox_inventory_plus_asset
--   inventoryitem_type_id -> inventoryitemtype (remap)
--   purchase_id -> purchase (remap)
--   delivery_id -> delivery (remap)
--   bom_id -> bom (remap); transfer_id -> transfer (remap)
--   description is NOT NULL in target and must be copied
--   eol_date/rack_id/rack_type_id/storage_site_id are external/scalar refs
--   all other *_id columns are external NetBox refs, kept as-is
INSERT INTO netbox_inventory_plus_asset (
    id, created, last_updated, custom_field_data, name, asset_tag, serial,
    status, warranty_start, warranty_end, comments, contact_id, device_id,
    device_type_id, inventoryitem_id, inventoryitem_type_id, module_id,
    module_type_id, owner_id, purchase_id, storage_location_id, tenant_id,
    delivery_id, description, eol_date, rack_id, rack_type_id, storage_site_id,
    bom_id, transfer_id)
SELECT m.new_id, s.created, s.last_updated, s.custom_field_data, s.name, s.asset_tag, s.serial,
    s.status, s.warranty_start, s.warranty_end, s.comments, s.contact_id, s.device_id,
    s.device_type_id, s.inventoryitem_id,
    itype.new_id,             -- remap inventoryitem_type_id
    s.module_id,
    s.module_type_id, s.owner_id,
    pur.new_id,               -- remap purchase_id
    s.storage_location_id, s.tenant_id,
    del.new_id,               -- remap delivery_id
    s.description,            -- NOT NULL in target
    s.eol_date,
    s.rack_id,                -- external, keep as-is
    s.rack_type_id,           -- external, keep as-is
    s.storage_site_id,        -- external, keep as-is
    bom.new_id,               -- remap bom_id
    tr.new_id                 -- remap transfer_id
FROM netbox_inventory_asset s
JOIN _map_asset m ON m.old_id = s.id
LEFT JOIN _map_inventoryitemtype itype ON itype.old_id = s.inventoryitem_type_id
LEFT JOIN _map_purchase pur ON pur.old_id = s.purchase_id
LEFT JOIN _map_delivery del ON del.old_id = s.delivery_id
LEFT JOIN _map_bom bom ON bom.old_id = s.bom_id
LEFT JOIN _map_transfer tr ON tr.old_id = s.transfer_id;

-- netbox_inventory_delivery_purchases -> netbox_inventory_plus_delivery_purchases (m2m)
--   delivery_id -> delivery (remap); purchase_id -> purchase (remap)
INSERT INTO netbox_inventory_plus_delivery_purchases (
    id, delivery_id, purchase_id)
SELECT m.new_id,
    d.new_id,                 -- remap delivery_id
    p.new_id                  -- remap purchase_id
FROM netbox_inventory_delivery_purchases s
JOIN _map_delivery_purchases m ON m.old_id = s.id
LEFT JOIN _map_delivery d ON d.old_id = s.delivery_id
LEFT JOIN _map_purchase p ON p.old_id = s.purchase_id;

-- netbox_inventory_purchase_boms -> netbox_inventory_plus_purchase_boms (m2m)
--   purchase_id -> purchase (remap); bom_id -> bom (remap)
INSERT INTO netbox_inventory_plus_purchase_boms (
    id, purchase_id, bom_id)
SELECT m.new_id,
    p.new_id,                 -- remap purchase_id
    b.new_id                  -- remap bom_id
FROM netbox_inventory_purchase_boms s
JOIN _map_purchase_boms m ON m.old_id = s.id
LEFT JOIN _map_purchase p ON p.old_id = s.purchase_id
LEFT JOIN _map_bom b ON b.old_id = s.bom_id;
