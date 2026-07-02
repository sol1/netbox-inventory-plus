-- 40_cleanup.sql
--
-- Decommission the OLD netbox_inventory data once everything has been migrated to
-- netbox_inventory_plus by the earlier files in this transaction. The old plugin is
-- no longer in PLUGINS, so its django_content_type rows resolve model_class()=NULL
-- and any row still referencing them (journal entries, changelog, tags, ...) crashes
-- the NetBox UI with:  AttributeError: 'NoneType' object has no attribute
-- '_base_manager'.  This file removes every such reference and retires the old
-- content types, following the procedure in NetBox docs/plugins/removal.md.
--
-- Called by copy_inventory_to_plus.sh INSIDE the same transaction as the earlier
-- files (skip with --skip-cleanup). Consumes the _objmap temp table built by
-- 20_remap_links.sql. No transaction control and no psql meta-commands here.
--
-- NOTHING IS DESTROYED: every row deleted below is first archived into the
-- netbox_inventory_removed schema, and the 11 source netbox_inventory_* tables are
-- MOVED into that schema (ALTER TABLE ... SET SCHEMA), not dropped. To undo, INSERT
-- the archive rows back / move the tables back to public. Once satisfied, reclaim
-- the space with:  DROP SCHEMA netbox_inventory_removed CASCADE;
--
-- Rows removed here and their fate:
--   * extras_journalentry / taggeditem / imageattachment / subscription /
--     notification on old CTs             -> already copied onto _plus_ objects (20)
--   * extras_customfield_object_types / users_objectpermission_object_types /
--     extras_eventrule_object_types       -> already mirrored onto _plus_ CTs (20)
--   * core_objectchange (changed obj)     -> live objects copied onto _plus_ (30);
--     entries for objects DELETED before the migration have nothing to remap onto
--     and exist only in the archive afterwards
--   * core_objectchange (related obj)     -> remapped in place to the _plus_ object
--     (or NULLed when the related object no longer exists)
--   * extras_cachedvalue                  -> derived search-index data; run
--     `manage.py reindex netbox_inventory_plus` after the migration
--   * netbox_branching_changediff         -> branch diffs of old inventory objects;
--     unusable since the old plugin is unloaded (merging them would crash the same
--     way the UI does)
--   * netbox_branching_appliedchange      -> audit rows FK'd to the old changelog
--     entries being deleted
--   * auth_permission                     -> verified unassigned; _plus_ permissions
--     are created by Django migrations
--   * core_objecttype + django_content_type + django_migrations rows for the app

------------------------------------------------------------------------------
-- 0. Archive schema. Plain CREATE (no IF NOT EXISTS): a leftover schema from a
--    previous committed run aborts the transaction instead of silently mixing
--    two generations of archives.
------------------------------------------------------------------------------
CREATE SCHEMA netbox_inventory_removed;

CREATE TEMP TABLE _old_ct ON COMMIT DROP AS
  SELECT id FROM django_content_type WHERE app_label = 'netbox_inventory';

------------------------------------------------------------------------------
-- 1. Archive every row we are about to delete or modify.
------------------------------------------------------------------------------
CREATE TABLE netbox_inventory_removed.extras_journalentry AS
  SELECT * FROM extras_journalentry WHERE assigned_object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_taggeditem AS
  SELECT * FROM extras_taggeditem WHERE content_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_imageattachment AS
  SELECT * FROM extras_imageattachment WHERE object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_subscription AS
  SELECT * FROM extras_subscription WHERE object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_notification AS
  SELECT * FROM extras_notification WHERE object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_customfield_object_types AS
  SELECT * FROM extras_customfield_object_types WHERE contenttype_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.users_objectpermission_object_types AS
  SELECT * FROM users_objectpermission_object_types WHERE contenttype_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_eventrule_object_types AS
  SELECT * FROM extras_eventrule_object_types WHERE contenttype_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.extras_cachedvalue AS
  SELECT * FROM extras_cachedvalue WHERE object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.netbox_branching_changediff AS
  SELECT * FROM netbox_branching_changediff WHERE object_type_id IN (SELECT id FROM _old_ct);
-- changelog: rows whose CHANGED object is old inventory (deleted below), plus the
-- pre-update image of rows whose RELATED object is old inventory (remapped below)
CREATE TABLE netbox_inventory_removed.core_objectchange AS
  SELECT * FROM core_objectchange
  WHERE changed_object_type_id IN (SELECT id FROM _old_ct)
     OR related_object_type_id IN (SELECT id FROM _old_ct);
-- branching audit rows pointing at those changelog entries (FK to core_objectchange)
CREATE TABLE netbox_inventory_removed.netbox_branching_appliedchange AS
  SELECT ac.* FROM netbox_branching_appliedchange ac
  JOIN core_objectchange oc ON oc.id = ac.change_id
  WHERE oc.changed_object_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.auth_permission AS
  SELECT * FROM auth_permission WHERE content_type_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.core_objecttype AS
  SELECT * FROM core_objecttype WHERE contenttype_ptr_id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.django_content_type AS
  SELECT * FROM django_content_type WHERE id IN (SELECT id FROM _old_ct);
CREATE TABLE netbox_inventory_removed.django_migrations AS
  SELECT * FROM django_migrations WHERE app = 'netbox_inventory';

------------------------------------------------------------------------------
-- 2. Changelog: delete entries whose changed object is old inventory (the live
--    ones were copied onto _plus_ by 30_changelog.sql), then fix surviving
--    entries that merely RELATE to an old inventory object - remap to the _plus_
--    object when it exists, otherwise clear the reference.
------------------------------------------------------------------------------
-- netbox_branching_appliedchange FKs the changelog entries being deleted
DELETE FROM netbox_branching_appliedchange ac
USING core_objectchange oc
WHERE oc.id = ac.change_id
  AND oc.changed_object_type_id IN (SELECT id FROM _old_ct);

DELETE FROM core_objectchange
WHERE changed_object_type_id IN (SELECT id FROM _old_ct);

UPDATE core_objectchange oc
SET related_object_type_id = o.new_ct,
    related_object_id      = o.new_id
FROM _objmap o
WHERE oc.related_object_type_id = o.old_ct
  AND oc.related_object_id      = o.old_id;

UPDATE core_objectchange
SET related_object_type_id = NULL,
    related_object_id      = NULL
WHERE related_object_type_id IN (SELECT id FROM _old_ct);

------------------------------------------------------------------------------
-- 3. Delete every remaining row referencing the old content types.
------------------------------------------------------------------------------
DELETE FROM extras_journalentry   WHERE assigned_object_type_id IN (SELECT id FROM _old_ct);
DELETE FROM extras_taggeditem     WHERE content_type_id         IN (SELECT id FROM _old_ct);
DELETE FROM extras_imageattachment WHERE object_type_id         IN (SELECT id FROM _old_ct);
DELETE FROM extras_subscription   WHERE object_type_id          IN (SELECT id FROM _old_ct);
DELETE FROM extras_notification   WHERE object_type_id          IN (SELECT id FROM _old_ct);
DELETE FROM extras_customfield_object_types      WHERE contenttype_id IN (SELECT id FROM _old_ct);
DELETE FROM users_objectpermission_object_types  WHERE contenttype_id IN (SELECT id FROM _old_ct);
DELETE FROM extras_eventrule_object_types        WHERE contenttype_id IN (SELECT id FROM _old_ct);
DELETE FROM extras_cachedvalue         WHERE object_type_id IN (SELECT id FROM _old_ct);
DELETE FROM netbox_branching_changediff WHERE object_type_id IN (SELECT id FROM _old_ct);

-- Model-level permissions (verified unassigned to any user/group; the m2m deletes
-- are defensive in case assignments exist in another environment).
DELETE FROM auth_group_permissions
  WHERE permission_id IN (SELECT id FROM auth_permission WHERE content_type_id IN (SELECT id FROM _old_ct));
DELETE FROM users_group_permissions
  WHERE permission_id IN (SELECT id FROM auth_permission WHERE content_type_id IN (SELECT id FROM _old_ct));
DELETE FROM users_user_user_permissions
  WHERE permission_id IN (SELECT id FROM auth_permission WHERE content_type_id IN (SELECT id FROM _old_ct));
DELETE FROM auth_permission WHERE content_type_id IN (SELECT id FROM _old_ct);

------------------------------------------------------------------------------
-- 4. Retire the content types themselves. core_objecttype is a child table of
--    django_content_type (multi-table inheritance), so it goes first. Finally
--    forget the app's schema migrations.
------------------------------------------------------------------------------
DELETE FROM core_objecttype     WHERE contenttype_ptr_id IN (SELECT id FROM _old_ct);
DELETE FROM django_content_type WHERE id                 IN (SELECT id FROM _old_ct);
DELETE FROM django_migrations   WHERE app = 'netbox_inventory';

------------------------------------------------------------------------------
-- 5. Move the source tables out of public into the archive schema (indexes,
--    constraints and owned sequences move with them). Also makes an accidental
--    second run of this migration fail fast at 10_copy_inventory.sql instead of
--    duplicating data. Children move before parents (FK order is irrelevant for
--    SET SCHEMA, but keep a readable order).
------------------------------------------------------------------------------
ALTER TABLE netbox_inventory_delivery_purchases SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_purchase_boms      SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_asset              SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_transfer           SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_delivery           SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_purchase           SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_inventoryitemtype  SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_inventoryitemgroup SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_bom                SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_courier            SET SCHEMA netbox_inventory_removed;
ALTER TABLE netbox_inventory_supplier           SET SCHEMA netbox_inventory_removed;
