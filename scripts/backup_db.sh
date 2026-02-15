#!/bin/bash
# Backup script for PostgreSQL database
# Usage: ./backup_db.sh

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="backup_${TIMESTAMP}.sql.gz"

mkdir -p $BACKUP_DIR

echo "Starting backup for ${DB_NAME:-trackmytickets}..."

# Use pg_dump to create a backup
PGPASSWORD=${DB_PASSWORD:-TrackMyTickets2026!} pg_dump \
    -h ${DB_HOST:-db} \
    -p ${DB_PORT:-5432} \
    -U ${DB_USER:-ticketuser} \
    ${DB_NAME:-trackmytickets} | gzip > "${BACKUP_DIR}/${FILENAME}"

if [ $? -eq 0 ]; then
    echo "Backup successful: ${BACKUP_DIR}/${FILENAME}"
    # Keep only last 7 days backups
    find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
else
    echo "Backup failed!"
    exit 1
fi
