#!/bin/bash
git pull

docker compose down
docker compose -f docker-compose.prod.yml up -d

docker exec -i n8n n8n import:workflow --input=/dev/stdin < workflows/check_schedule.json
docker exec -i n8n n8n import:workflow --input=/dev/stdin < workflows/lineup_polling.json

docker exec -i n8n n8n publish:workflow --id=8mXBR8hOSbupCuiu
docker exec -i n8n n8n publish:workflow --id=6lsXU37fHrr8G0xk

docker restart n8n

echo "✅ 배포 및 활성화 완료"
