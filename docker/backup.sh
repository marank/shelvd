#!/bin/sh
# Nightly pg_dump of the app database, run by the "backup" service in compose.yml.
# Dumps (custom format, restore with pg_restore) go to /var/lib/postgresql/backups in the
# "backups" volume; dumps older than BACKUP_KEEP_DAYS are deleted.
set -eu

dir=/var/lib/postgresql/backups
time="${BACKUP_TIME:-02:30}"
keep="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$dir"

dump() {
  file="$dir/${PGDATABASE}-$(date -u +%Y%m%dT%H%M%SZ).dump"
  echo "backup: writing $file"
  # Write to a temp name first, so a failed dump never looks like a valid one.
  pg_dump --format=custom --file="$file.partial"
  mv "$file.partial" "$file"
  find "$dir" -name "*.dump" -mtime +"$keep" -print -delete
  find "$dir" -name "*.partial" -mmin +60 -delete
}

if [ "${1:-}" = "now" ]; then
  dump
  exit 0
fi

echo "backup: daily at $time (container time zone), keeping $keep days"
last=""
while :; do
  now="$(date +%H:%M)"
  today="$(date +%F)"
  if [ "$now" = "$time" ] && [ "$last" != "$today" ]; then
    if dump; then last="$today"; else echo "backup: FAILED" >&2; fi
  fi
  sleep 30
done
