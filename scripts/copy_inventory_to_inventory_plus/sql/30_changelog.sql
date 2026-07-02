-- 30_changelog.sql
--
-- Copy core_objectchange (changelog) entries for the migrated objects onto the new
-- _plus_ objects. Old entries are left intact; one new entry is created per old
-- entry whose changed object is an inventory object. The related object is remapped
-- too when it is an inventory object.
--
-- Called by copy_inventory_to_plus.sh INSIDE the same transaction as the earlier
-- files; it consumes the _objmap temp table built in 20_remap_links.sql. No
-- transaction control and no psql meta-commands here. This step is large (one row
-- per matched historical change) and can be skipped with the orchestrator's
-- --skip-changelog flag.
--
-- LIMITATION: prechange_data / postchange_data are copied verbatim. Those JSON
-- snapshots may still contain the OLD object ids inside their field values; they are
-- not rewritten here.

INSERT INTO core_objectchange (
    id, time, user_name, request_id, action, changed_object_id,
    related_object_id, object_repr, postchange_data, changed_object_type_id,
    related_object_type_id, user_id, prechange_data, message)
SELECT
    nextval(pg_get_serial_sequence('core_objectchange','id')),
    oc.time, oc.user_name, oc.request_id, oc.action,
    cmap.new_id,                                        -- remapped changed_object_id
    COALESCE(rmap.new_id, oc.related_object_id),        -- remap related_object_id if inventory
    oc.object_repr, oc.postchange_data,
    cmap.new_ct,                                        -- remapped changed_object_type_id
    COALESCE(rmap.new_ct, oc.related_object_type_id),   -- remap related_object_type_id if inventory
    oc.user_id, oc.prechange_data, oc.message
FROM core_objectchange oc
JOIN _objmap cmap
  ON cmap.old_ct = oc.changed_object_type_id
 AND cmap.old_id = oc.changed_object_id
LEFT JOIN _objmap rmap
  ON rmap.old_ct = oc.related_object_type_id
 AND rmap.old_id = oc.related_object_id;
