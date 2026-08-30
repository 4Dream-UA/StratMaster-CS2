#!/usr/bin/env bash
# Restores a dump produced by backup_db.sh into the `db` compose service.
# DESTRUCTIVE: drops and recreates every object in the target database
# first. Confirms before running unless FORCE=1 is set.
#
# Usage:
#   ./scripts/restore_db.sh ./backups/stratmaster_20260831_030000.sql.gz

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DUMP_FILE="${1:?Usage: restore_db.sh <path-to-dump.sql.gz>}"
if [ ! -f "$DUMP_FILE" ]; then
  echo "No such file: $DUMP_FILE" >&2
  exit 1
fi

DB_USER="${POSTGRES_USER:-stratmaster}"
DB_NAME="${POSTGRES_DB:-stratmaster_db}"

if [ "${FORCE:-0}" != "1" ]; then
  read -r -p "This will ERASE the current contents of '$DB_NAME' and replace them with $DUMP_FILE. Type 'yes' to continue: " confirm
  [ "$confirm" = "yes" ] || { echo "Aborted."; exit 1; }
fi

gunzip -c "$DUMP_FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo "Restore complete from $DUMP_FILE."
