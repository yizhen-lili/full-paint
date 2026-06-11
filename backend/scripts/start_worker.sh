#!/usr/bin/env bash
# backend-worker entrypoint — Railway 部署用
#
# 不跑 alembic migration（避免兩個 service 同時 alembic upgrade race；
# 雖然 alembic 內部有 advisory lock，但 web 已負責 migration、worker 啟動時 schema 已就緒）。

set -euo pipefail

cd /app

# 背景啟動 healthcheck HTTP server（吃 PORT、回 200）—
# Railway 會 ping container PORT 判斷 service ready；
# Celery 不開 HTTP，沒這個 server 會卡 Deploying 直到 deploy timeout 被 kill。
python scripts/healthcheck_server.py &
HEALTH_PID=$!
echo "[start_worker] healthcheck HTTP server started (PID ${HEALTH_PID})"

echo "[start_worker] starting celery worker + embedded beat..."
# --beat：在這個單一 worker 內嵌啟動排程器（beat），定時任務才會被派發。
#   orders.check_payment_expired / custom.expire_quotes 等每 5 分鐘排程靠 beat 觸發；
#   沒有 beat 時 worker 雖在跑卻沒人排程，訂單/報價狀態永遠不會自動翻。
#   單一 worker（concurrency=1, solo）內嵌 beat 即可，不需另開 beat service。
# --schedule：beat 狀態檔放可寫的 /tmp（容器 /app 唯讀風險）。
exec celery -A core.celery_app worker \
    --beat \
    --schedule=/tmp/celerybeat-schedule \
    --loglevel=info \
    --concurrency=1 \
    --pool=solo
