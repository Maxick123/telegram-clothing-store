#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_RETENTION_DAYS:=7}"

mkdir -p "$BACKUP_DIR"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
pg_dump --format=custom --file="$BACKUP_DIR/${POSTGRES_DB}-${timestamp}.dump" "$POSTGRES_DB"
find "$BACKUP_DIR" -type f -name "${POSTGRES_DB}-*.dump" -mtime "+$BACKUP_RETENTION_DAYS" -delete
