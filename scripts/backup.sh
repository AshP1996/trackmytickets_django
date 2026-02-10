#!/bin/bash
# Database backup script
# Usage: ./scripts/backup.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

echo "=========================================="
echo "Backing up database..."
echo "=========================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create backup
docker-compose exec -T db pg_dump -U $DB_USER $DB_NAME > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

echo "Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Old backups cleaned up (kept last 7 days)"
echo "=========================================="
echo "Backup complete!"
echo "=========================================="

# Optional: Upload to S3
# if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
#     echo "Uploading to S3..."
#     aws s3 cp ${BACKUP_FILE}.gz s3://your-bucket/backups/
# fi
