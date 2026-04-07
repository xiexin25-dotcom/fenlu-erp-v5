#!/usr/bin/env bash
set -euo pipefail

echo "=== 分路链式工业互联网系统 V5.0 · 部署脚本 ==="

# Check .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env 文件不存在。请复制 .env.production.example 并修改密码:"
  echo "  cp .env.production.example .env"
  echo "  vim .env"
  exit 1
fi

# Check required vars
source .env
for var in POSTGRES_PASSWORD JWT_SECRET MINIO_PASSWORD; do
  val="${!var:-}"
  if [ -z "$val" ] || [[ "$val" == *"CHANGE_ME"* ]]; then
    echo "ERROR: 请修改 .env 中的 $var"
    exit 1
  fi
done

echo "[1/4] Building images..."
docker compose -f docker-compose.prod.yml build

echo "[2/4] Starting infrastructure..."
docker compose -f docker-compose.prod.yml up -d postgres redis minio
echo "Waiting for database..."
sleep 5

echo "[3/4] Running migrations..."
docker compose -f docker-compose.prod.yml --profile migrate run --rm migrate

echo "[4/4] Starting application..."
docker compose -f docker-compose.prod.yml up -d api-gateway web

echo ""
echo "=== 部署完成 ==="
echo "前端:  http://localhost:${WEB_PORT:-80}"
echo "API:   http://localhost:${WEB_PORT:-80}/api/health"
echo "MinIO: http://localhost:9001 (管理控制台)"
echo ""
echo "查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "停止服务: docker compose -f docker-compose.prod.yml down"
