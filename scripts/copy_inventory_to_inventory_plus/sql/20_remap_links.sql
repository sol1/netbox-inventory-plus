-- 20_remap_links.sql
--
-- Re-point everything that was attached to the OLD netbox_inventory objects at the
-- freshly-copied netbox_inventory_plus objects: per-model config (custom fields,
-- object permissions) and per-object data (tags, journal entries, image
-- attachments, subscriptions, notifications).
--
-- Called by copy_inventory_to_plus.sh INSIDE the same transaction as
-- 10_copy_inventory.sql, so it REUSES that file's _map_* temp tables directly (the
-- exact old_id->new_id correspondence from the copy). No transaction control and no
-- psql meta-commands here. Old records are left intact; one new record is created
-- per old record. The _objmap temp table built here is ON COMMIT DROP and is also
-- consumed by 30_changelog.sql.

------------------------------------------------------------------------------
-- Combined object map keyed by content-type + object id, translating both the
-- object id and the content-type id from netbox_inventory -> _plus, built from the
-- copy's per-table maps.
------------------------------------------------------------------------------
CREATE TEMP TABLE _objmap ON COMMIT DROP AS
  SELECT old_ct.id AS old_ct, new_ct.id AS new_ct, m.old_id, m.new_id
  FROM (
              SELECT 'asset'              AS model, old_id, new_id FROM _map_asset
    UNION ALL SELECT 'bom',                          old_id, new_id FROM _map_bom
    UNION ALL SELECT 'courier',                      old_id, new_id FROM _map_courier
    UNION ALL SELECT 'delivery',                     old_id, new_id FROM _map_delivery
    UNION ALL SELECT 'inventoryitemgroup',           old_id, new_id FROM _map_inventoryitemgroup
    UNION ALL SELECT 'inventoryitemtype',            old_id, new_id FROM _map_inventoryitemtype
    UNION ALL SELECT 'purchase',                     old_id, new_id FROM _map_purchase
    UNION ALL SELECT 'supplier',                     old_id, new_id FROM _map_supplier
    UNION ALL SELECT 'transfer',                     old_id, new_id FROM _map_transfer
  ) m
  JOIN django_content_type old_ct
    ON old_ct.app_label = 'netbox_inventory'      AND old_ct.model = m.model
  JOIN django_content_type new_ct
    ON new_ct.app_label = 'netbox_inventory_plus' AND new_ct.model = m.model;

------------------------------------------------------------------------------
-- PER-MODEL config: mirror onto the _plus_ content types.
------------------------------------------------------------------------------

-- Custom-field assignments: make the same custom fields apply to the _plus_ models
-- so the already-copied custom_field_data renders/validates in the UI.
INSERT INTO extras_customfield_object_types (id, customfield_id, contenttype_id)
SELECT nextval(pg_get_serial_sequence('extras_customfield_object_types','id')),
       cfo.customfield_id, newct.id
FROM extras_customfield_object_types cfo
JOIN django_content_type oldct ON oldct.id = cfo.contenttype_id AND oldct.app_label = 'netbox_inventory'
JOIN django_content_type newct ON newct.app_label = 'netbox_inventory_plus' AND newct.model = oldct.model
ON CONFLICT (customfield_id, contenttype_id) DO NOTHING;

-- Object permissions: extend every permission that covers an old inventory model to
-- also cover the matching _plus_ model.
INSERT INTO users_objectpermission_object_types (id, objectpermission_id, contenttype_id)
SELECT nextval(pg_get_serial_sequence('users_objectpermission_object_types','id')),
       po.objectpermission_id, newct.id
FROM users_objectpermission_object_types po
JOIN django_content_type oldct ON oldct.id = po.contenttype_id AND oldct.app_label = 'netbox_inventory'
JOIN django_content_type newct ON newct.app_label = 'netbox_inventory_plus' AND newct.model = oldct.model
ON CONFLICT (objectpermission_id, contenttype_id) DO NOTHING;

-- Event rules: extend every event rule that fires on an old inventory model to also
-- fire on the matching _plus_ model.
INSERT INTO extras_eventrule_object_types (id, eventrule_id, contenttype_id)
SELECT nextval(pg_get_serial_sequence('extras_eventrule_object_types','id')),
       ero.eventrule_id, newct.id
FROM extras_eventrule_object_types ero
JOIN django_content_type oldct ON oldct.id = ero.contenttype_id AND oldct.app_label = 'netbox_inventory'
JOIN django_content_type newct ON newct.app_label = 'netbox_inventory_plus' AND newct.model = oldct.model
ON CONFLICT (eventrule_id, contenttype_id) DO NOTHING;

------------------------------------------------------------------------------
-- PER-OBJECT data: copy each record onto the remapped _plus_ object.
------------------------------------------------------------------------------

-- Tags
INSERT INTO extras_taggeditem (id, object_id, content_type_id, tag_id)
SELECT nextval(pg_get_serial_sequence('extras_taggeditem','id')),
       o.new_id, o.new_ct, ti.tag_id
FROM extras_taggeditem ti
JOIN _objmap o ON o.old_ct = ti.content_type_id AND o.old_id = ti.object_id
WHERE NOT EXISTS (
  SELECT 1 FROM extras_taggeditem x
  WHERE x.content_type_id = o.new_ct AND x.object_id = o.new_id AND x.tag_id = ti.tag_id);

-- Journal entries
INSERT INTO extras_journalentry (
    id, assigned_object_id, created, last_updated, kind, comments,
    assigned_object_type_id, created_by_id, custom_field_data)
SELECT nextval(pg_get_serial_sequence('extras_journalentry','id')),
       o.new_id, j.created, j.last_updated, j.kind, j.comments,
       o.new_ct, j.created_by_id, j.custom_field_data
FROM extras_journalentry j
JOIN _objmap o ON o.old_ct = j.assigned_object_type_id AND o.old_id = j.assigned_object_id;

-- Image attachments
INSERT INTO extras_imageattachment (
    id, object_id, image, image_height, image_width, name, created,
    object_type_id, last_updated, description)
SELECT nextval(pg_get_serial_sequence('extras_imageattachment','id')),
       o.new_id, i.image, i.image_height, i.image_width, i.name, i.created,
       o.new_ct, i.last_updated, i.description
FROM extras_imageattachment i
JOIN _objmap o ON o.old_ct = i.object_type_id AND o.old_id = i.object_id;

-- Subscriptions
INSERT INTO extras_subscription (id, created, object_id, object_type_id, user_id)
SELECT nextval(pg_get_serial_sequence('extras_subscription','id')),
       s.created, o.new_id, o.new_ct, s.user_id
FROM extras_subscription s
JOIN _objmap o ON o.old_ct = s.object_type_id AND o.old_id = s.object_id
ON CONFLICT (object_type_id, object_id, user_id) DO NOTHING;

-- Notifications
INSERT INTO extras_notification (
    id, created, read, object_id, event_type, object_type_id, object_repr, user_id)
SELECT nextval(pg_get_serial_sequence('extras_notification','id')),
       n.created, n.read, o.new_id, n.event_type, o.new_ct, n.object_repr, n.user_id
FROM extras_notification n
JOIN _objmap o ON o.old_ct = n.object_type_id AND o.old_id = n.object_id
ON CONFLICT (object_type_id, object_id, user_id) DO NOTHING;
