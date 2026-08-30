#!/usr/bin/env bash
# Dumps the Postgres database running in the `db` compose service to a
# timestamped, gzip-compressed file in ./backups (created if missing).
# Safe to run while the app is live — pg_dump takes a consistent
# snapshot without blocking writers.
#
# Usage:
#   ./scripts/backup_db.sh              # dumps to ./backups/
#   BACKUP_DIR=/mnt/backups ./scripts/backup_db.sh
#
# Scheduling (pick whichever fits how this is actually deployed):
#   - Linux/systemd host: a systemd timer or `cron` entry running this
#     script daily is the simplest option — e.g. `0 3 * * *` for 3am.
#   - Already on a managed Postgres provider: prefer its own automated
#     backup/point-in-time-recovery feature over this script; it's more
#     robust than a nightly dump and doesn't need a separate schedule.
# Retention: this script keeps the last 14 daily dumps and deletes older
# ones — adjust KEEP_DAYS below if that's not enough runway.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/stratmaster_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Reads POSTGRES_USER / POSTGRES_DB from .env via docker compose's own
# env handling — no credentials duplicated in this script. --clean
# --if-exists makes the dump self-contained for restore_db.sh: it drops
# each object before recreating it, so restoring doesn't fail on a
# database that isn't empty.
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-stratmaster}" --clean --if-exists "${POSTGRES_DB:-stratmaster_db}" \
  | gzip > "$OUT_FILE"

echo "Backup written: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"

# Prune anything older than KEEP_DAYS.
find "$BACKUP_DIR" -name 'stratmaster_*.sql.gz' -mtime "+${KEEP_DAYS}" -delete
