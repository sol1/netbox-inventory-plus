#!/bin/sh
#
# copy_inventory_to_plus.sh
#
# Orchestrates the full migration from the old netbox_inventory_* tables into the
# netbox_inventory_plus_* tables. The actual SQL lives in the sql/ directory next to
# this script; this script just wraps every sql/*.sql file in ONE transaction and
# either commits it (--live) or rolls it back (dry run, the default).
#
# The SQL files run IN ORDER (numeric filename prefix) and share one transaction, so
# later files reuse the temp maps built by earlier ones:
#     sql/10_copy_inventory.sql  - copy the table data, remapping primary keys
#     sql/20_remap_links.sql     - custom fields, permissions, event rules, tags,
#                                  journal entries, image attachments, subscriptions,
#                                  notifications
#     sql/30_changelog.sql       - copy core_objectchange (changelog) entries
#     sql/40_cleanup.sql         - decommission the OLD netbox_inventory data: archive
#                                  and delete every row referencing the old content
#                                  types (which crash the UI now that the old plugin
#                                  is unloaded), retire the content types, and move
#                                  the source tables into the netbox_inventory_removed
#                                  schema. Nothing is destroyed - see that file.
#
# Because it is one atomic transaction, the whole migration either lands or does not;
# a dry run exercises every step (including the remaps, which see the copy's
# uncommitted rows) and then rolls back.
#
# -----------------------------------------------------------------------------
# WHERE TO RUN THIS
# -----------------------------------------------------------------------------
# Run it ON THE DATABASE HOST as the postgres OS user (psql/pg_dump must reach the
# cluster locally with peer auth).
#
#     ssh <db-host>            # e.g. the NetBox Postgres server
#     sudo -iu postgres        # become the postgres OS user (or: su - postgres)
#     sh copy_inventory_to_plus.sh            # DRY RUN (default) - rolls back
#     sh copy_inventory_to_plus.sh --live     # actually commit the migration
#
# -----------------------------------------------------------------------------
# OPTIONS
# -----------------------------------------------------------------------------
#   --live              Commit the transaction. WITHOUT this flag the script does a
#                       DRY RUN: it runs every statement then ROLLS BACK, so nothing
#                       is persisted. Dry run is the default.
#   --skip-changelog    Do not run sql/30_changelog.sql (the changelog copy is large;
#                       one row per matched historical change). Default: run it.
#                       Implies --skip-cleanup: the cleanup deletes the old changelog
#                       entries, which would lose history if they were never copied.
#   --skip-cleanup      Do not run sql/40_cleanup.sql (leave the old netbox_inventory
#                       data in place). Default: run it. NOTE: while the old rows
#                       remain, NetBox views that touch them (journal, changelog,
#                       tags) crash with "'NoneType' object has no attribute
#                       '_base_manager'" because the old plugin is not loaded.
#   --dump-path PATH    Write the pre-run backup to PATH (a .sql file). Only used in
#                       --live mode. Parent dirs are created if needed.
#                       Default: $BACKUP_DIR/netbox_inventory_plus_<timestamp>.sql
#   --sql-dir DIR       Directory holding the numbered .sql files.
#                       Default: <dir of this script>/sql
#   -h, --help          Show usage and exit.
#
# Environment overrides:
#   NETBOX_DB    Database name (default: netbox)
#   BACKUP_DIR   Default backup directory (default: $HOME/netbox_plus_backups)
#
# -----------------------------------------------------------------------------
# KEY BEHAVIOURS
# -----------------------------------------------------------------------------
#   * DRY RUN BY DEFAULT. Pass --live to commit.
#   * ONE transaction across all SQL files. _plus_ FKs are DEFERRABLE INITIALLY
#     DEFERRED; this script runs SET CONSTRAINTS ALL IMMEDIATE just before finishing
#     so that even a dry run validates referential integrity.
#   * In --live mode a data-only backup of the current netbox_inventory_plus_*
#     contents is written first (see step 0 for the restore procedure).
#   * Source tables (netbox_inventory_*) are read, then RETIRED by the cleanup step:
#     moved (not dropped) into the netbox_inventory_removed schema, alongside
#     archive copies of every dependent row the cleanup deletes. With
#     --skip-cleanup the sources are never modified.
#   * APPEND, not replace: the migration is NOT idempotent. Run it ONCE against a
#     given _plus_ dataset. The cleanup makes an accidental second run fail fast
#     (the source tables are no longer in public); with --skip-cleanup a second
#     run copies the data a second time.
#   * After a live run with cleanup, run `manage.py reindex netbox_inventory_plus`
#     on the NetBox app host: the copied objects are not in the search index (the
#     old objects' index entries are removed by the cleanup).
#   * Primary keys are REMAPPED from the target sequences. nextval() is NOT
#     transactional, so EVERY run (including a dry run) permanently advances the
#     _plus_ id sequences; copied ids will have gaps. Harmless to NetBox.
#   * The backup only captures netbox_inventory_plus_* rows. The remap steps also
#     APPEND to extras_taggeditem / extras_journalentry / extras_imageattachment /
#     extras_subscription / extras_notification / core_objectchange; those inserts
#     are not captured by the backup. Undo them by deleting the new rows if needed.
#
set -eu

usage() {
    cat <<'USAGE'
Usage: sh copy_inventory_to_plus.sh [options]

Runs every sql/*.sql file in one transaction to migrate netbox_inventory_* into
netbox_inventory_plus_* (data copy + link/config remap + changelog + old-data
cleanup). RUN ON THE DATABASE HOST as the postgres OS user:

    sudo -iu postgres            # or: su - postgres
    sh copy_inventory_to_plus.sh           # DRY RUN (default) - rolls back
    sh copy_inventory_to_plus.sh --live    # actually commit the migration

Options:
  --live              Commit the transaction (default is a dry run that rolls back).
  --skip-changelog    Skip sql/30_changelog.sql (the large changelog copy).
                      Implies --skip-cleanup (cleanup would delete uncopied history).
  --skip-cleanup      Skip sql/40_cleanup.sql (leave old netbox_inventory data in
                      place; UI views touching it keep crashing).
  --dump-path PATH    Write the pre-run backup to PATH (.sql file). --live only.
                      Default: $BACKUP_DIR/netbox_inventory_plus_<timestamp>.sql
  --sql-dir DIR       Directory of numbered .sql files (default: <script dir>/sql).
  -h, --help          Show this help and exit.

Environment:
  NETBOX_DB    Database name (default: netbox)
  BACKUP_DIR   Default backup directory (default: $HOME/netbox_plus_backups)
USAGE
}

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

LIVE=0
SKIP_CHANGELOG=0
SKIP_CLEANUP=0
DUMP_PATH=""
SQL_DIR="$SCRIPT_DIR/sql"

while [ $# -gt 0 ]; do
    case "$1" in
        --live)           LIVE=1 ;;
        --skip-changelog) SKIP_CHANGELOG=1 ;;
        --skip-cleanup)   SKIP_CLEANUP=1 ;;
        --dump-path)
            shift
            DUMP_PATH="${1:-}"
            [ -n "$DUMP_PATH" ] || { echo "ERROR: --dump-path requires a path" >&2; exit 2; }
            ;;
        --dump-path=*)    DUMP_PATH="${1#--dump-path=}" ;;
        --sql-dir)
            shift
            SQL_DIR="${1:-}"
            [ -n "$SQL_DIR" ] || { echo "ERROR: --sql-dir requires a path" >&2; exit 2; }
            ;;
        --sql-dir=*)      SQL_DIR="${1#--sql-dir=}" ;;
        -h|--help)        usage; exit 0 ;;
        *) echo "ERROR: unknown option: $1" >&2; echo "Try --help" >&2; exit 2 ;;
    esac
    shift
done

DB="${NETBOX_DB:-netbox}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/netbox_plus_backups}"

[ -d "$SQL_DIR" ] || { echo "ERROR: SQL directory not found: $SQL_DIR" >&2; exit 2; }

# The cleanup deletes the old inventory changelog entries; if the changelog copy is
# being skipped they were never duplicated, so deleting them would lose history.
if [ "$SKIP_CHANGELOG" -eq 1 ] && [ "$SKIP_CLEANUP" -eq 0 ]; then
    echo "NOTE: --skip-changelog implies --skip-cleanup (cleanup would delete the"
    echo "      old changelog entries that were never copied). Skipping cleanup."
    SKIP_CLEANUP=1
fi

# Collect the .sql files in filename order, honouring the skip flags.
SQL_FILES=""
for f in "$SQL_DIR"/*.sql; do
    [ -e "$f" ] || { echo "ERROR: no .sql files in $SQL_DIR" >&2; exit 2; }
    case "$f" in
        */30_changelog.sql) [ "$SKIP_CHANGELOG" -eq 1 ] && continue ;;
        */40_cleanup.sql)   [ "$SKIP_CLEANUP" -eq 1 ] && continue ;;
    esac
    SQL_FILES="$SQL_FILES $f"
done

if [ "$LIVE" -eq 1 ]; then
    FINISH=COMMIT
    echo "Mode: LIVE - the transaction WILL be committed."
else
    FINISH=ROLLBACK
    echo "Mode: DRY RUN - the transaction will be rolled back; nothing is committed."
    echo "      (Pass --live to commit. Note: a dry run still advances the _plus_"
    echo "       id sequences, since nextval() is not rolled back in PostgreSQL.)"
fi
if [ "$SKIP_CHANGELOG" -eq 1 ]; then
    echo "Changelog: SKIPPED (sql/30_changelog.sql not included)."
fi
if [ "$SKIP_CLEANUP" -eq 1 ]; then
    echo "Cleanup: SKIPPED (sql/40_cleanup.sql not included; old netbox_inventory"
    echo "         data stays in place)."
fi
echo "SQL files (in order):"
for f in $SQL_FILES; do echo "    $f"; done

#-----------------------------------------------------------------------------
# 0. Back up the CURRENT contents of every netbox_inventory_plus_* table BEFORE
#    touching anything (LIVE runs only). This is a data-only snapshot of the rows
#    that exist now, written outside the database. The migration runs in one
#    transaction and rolls back on any error, so this backup only matters for undoing
#    an otherwise-SUCCESSFUL run.
#
#    To restore the _plus_ tables to this snapshot (DESTROYS post-backup rows):
#        psql -d netbox -v ON_ERROR_STOP=1 <<EOF
#        BEGIN;
#        SET CONSTRAINTS ALL DEFERRED;
#        TRUNCATE netbox_inventory_plus_asset,
#                 netbox_inventory_plus_delivery_purchases,
#                 netbox_inventory_plus_purchase_boms,
#                 netbox_inventory_plus_transfer,
#                 netbox_inventory_plus_delivery,
#                 netbox_inventory_plus_purchase,
#                 netbox_inventory_plus_inventoryitemtype,
#                 netbox_inventory_plus_inventoryitemgroup,
#                 netbox_inventory_plus_bom,
#                 netbox_inventory_plus_courier,
#                 netbox_inventory_plus_supplier
#                 RESTART IDENTITY;
#        \i <this-backup-file>
#        COMMIT;
#        EOF
#    pg_dump prints a "circular foreign-key constraints" warning for the
#    self-referencing inventoryitemgroup.parent_id - this is EXPECTED and harmless:
#    the restore above runs inside a transaction with constraints deferred.
#    NOTE: the backup does NOT capture the extras_*/core_objectchange rows the remap
#    steps append; delete those by request_id/time/id if you need to undo them.
#-----------------------------------------------------------------------------
if [ "$LIVE" -eq 1 ]; then
    if [ -n "$DUMP_PATH" ]; then
        BACKUP_FILE="$DUMP_PATH"
        mkdir -p "$(dirname "$BACKUP_FILE")"
    else
        mkdir -p "$BACKUP_DIR"
        BACKUP_FILE="$BACKUP_DIR/netbox_inventory_plus_$(date +%Y%m%d_%H%M%S).sql"
    fi
    echo "Backing up existing netbox_inventory_plus_* data to: $BACKUP_FILE"
    pg_dump -d "$DB" --data-only -t 'netbox_inventory_plus_*' > "$BACKUP_FILE"
    echo "Backup complete ($(wc -l < "$BACKUP_FILE") lines). Starting migration..."
else
    echo "Dry run: skipping backup."
fi

# Build one transaction: BEGIN, each SQL file via \i, force FK validation, then
# COMMIT or ROLLBACK. Piped into a single psql session so the temp maps created in
# the first file are visible to the later files.
{
    echo "BEGIN;"
    for f in $SQL_FILES; do
        printf '\\echo -- running %s\n' "$f"
        printf '\\i %s\n' "$f"
    done
    echo "SET CONSTRAINTS ALL IMMEDIATE;"
    echo "$FINISH;"
} | psql -d "$DB" -v ON_ERROR_STOP=1

echo "Transaction finished with: $FINISH"

echo "Row counts per target table (committed state; unchanged after a dry run):"
psql -d "$DB" -A -F'	' -c "
    SELECT relname AS table, n_live_tup AS approx_rows
    FROM pg_stat_user_tables
    WHERE relname LIKE 'netbox_inventory_plus_%'
    ORDER BY relname;"

echo "Rows linked to netbox_inventory_plus content types (committed state):"
psql -d "$DB" -A -F'	' -c "
    WITH plus AS (SELECT id FROM django_content_type WHERE app_label='netbox_inventory_plus')
    SELECT 'customfield_object_types' AS item, count(*) FROM extras_customfield_object_types WHERE contenttype_id IN (SELECT id FROM plus)
    UNION ALL SELECT 'objectpermission_object_types', count(*) FROM users_objectpermission_object_types WHERE contenttype_id IN (SELECT id FROM plus)
    UNION ALL SELECT 'taggeditem',      count(*) FROM extras_taggeditem      WHERE content_type_id         IN (SELECT id FROM plus)
    UNION ALL SELECT 'journalentry',    count(*) FROM extras_journalentry    WHERE assigned_object_type_id IN (SELECT id FROM plus)
    UNION ALL SELECT 'imageattachment', count(*) FROM extras_imageattachment WHERE object_type_id           IN (SELECT id FROM plus)
    UNION ALL SELECT 'subscription',    count(*) FROM extras_subscription    WHERE object_type_id           IN (SELECT id FROM plus)
    UNION ALL SELECT 'notification',    count(*) FROM extras_notification    WHERE object_type_id           IN (SELECT id FROM plus)
    UNION ALL SELECT 'objectchange',    count(*) FROM core_objectchange      WHERE changed_object_type_id   IN (SELECT id FROM plus)
    ORDER BY 1;"

echo "Old netbox_inventory remnants (all counts should be 0 after a live cleanup run):"
psql -d "$DB" -A -F'	' -c "
    WITH old AS (SELECT id FROM django_content_type WHERE app_label='netbox_inventory')
    SELECT 'content_types' AS item, count(*) FROM old
    UNION ALL SELECT 'source_tables_in_public', count(*) FROM pg_tables
        WHERE schemaname='public' AND tablename LIKE 'netbox\_inventory\_%' AND tablename NOT LIKE 'netbox\_inventory\_plus\_%'
    UNION ALL SELECT 'journalentry',    count(*) FROM extras_journalentry    WHERE assigned_object_type_id IN (SELECT id FROM old)
    UNION ALL SELECT 'taggeditem',      count(*) FROM extras_taggeditem      WHERE content_type_id         IN (SELECT id FROM old)
    UNION ALL SELECT 'objectchange',    count(*) FROM core_objectchange
        WHERE changed_object_type_id IN (SELECT id FROM old) OR related_object_type_id IN (SELECT id FROM old)
    UNION ALL SELECT 'cachedvalue',     count(*) FROM extras_cachedvalue     WHERE object_type_id           IN (SELECT id FROM old)
    ORDER BY 1;"

if [ "$LIVE" -eq 1 ] && [ "$SKIP_CLEANUP" -eq 0 ]; then
    cat <<'REMINDER'
NEXT STEPS after this live migration:
  * On the NetBox app host, rebuild the search index for the copied objects:
        manage.py reindex netbox_inventory_plus
  * The old data is archived in the netbox_inventory_removed schema. Once you are
    satisfied with the migration, reclaim the space with:
        DROP SCHEMA netbox_inventory_removed CASCADE;
REMINDER
fi
