# Khởi động cục bộ

Tài liệu này dành cho lập trình viên cần chạy OpenNews trên máy cá nhân để phát
triển hoặc kiểm thử.

## 1. Thành phần cần có

OpenNews hiện dùng các thành phần sau:

- Python 3.10+
- Node.js để build frontend Vite
- PostgreSQL
- Neo4j
- Redis
- Tùy chọn: Playwright Chromium cho API sinh ảnh PNG

## 2. Hai cách chạy được hỗ trợ

### Cách 1: chạy toàn bộ bằng Docker Compose

Phù hợp khi cần dựng nhanh môi trường gần production.

```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f web
```

Dừng môi trường:

```bash
docker compose -f docker/docker-compose.yml down
```

Mặc định web dashboard chạy tại `http://localhost:8080`.

### Cách 2: chạy app cục bộ, hạ tầng bằng container hoặc dịch vụ máy local

Phù hợp khi cần debug Python/Vue trực tiếp.

Tạo môi trường Python:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
```

Cài frontend:

```bash
cd web
npm install
cd ..
```

Nếu dùng API `/api/share/default`, cài runtime cho Playwright một lần:

```bash
pip install playwright
playwright install chromium
```

Khởi chạy hạ tầng tối thiểu:

```bash
docker run -d --name opennews-pg -p 5432:5432 -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=opennews postgres:16-alpine
docker run -d --name opennews-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/Aa123456 neo4j:5-community
docker run -d --name opennews-redis -p 6379:6379 redis:7-alpine
```

Chạy pipeline scheduler:

```bash
PYTHONPATH=src python -m opennews.main
```

Build frontend:

```bash
cd web
npm run build
cd ..
```

Chạy web server:

```bash
PYTHONPATH=src python web/server.py --port 8080
```

## 3. Script tiện lợi của repo

Repo có `build.sh` để kiểm tra phụ thuộc, khởi động backend, build frontend và
chạy web server trong một lệnh. Script này hữu ích khi làm việc trên môi trường
Unix-like.

```bash
./build.sh
```

## 4. Biến môi trường quan trọng

Các biến cấu hình được khai báo trong `src/opennews/config.py`.

Nhóm quan trọng nhất:

- `NEWS_POLL_INTERVAL_MIN`: chu kỳ polling của scheduler
- `BATCH_SIZE`: số lượng tin tối đa mỗi vòng
- `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `REDIS_URL`
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- `SOURCES_CONFIG_PATH`, `LLM_CONFIG_PATH`, `CHECKPOINT_FILE`
- `SHARE_API_ENABLED`, `SHARE_SCHEDULER_ENABLED`, `SHARE_CACHE_DIR`
- `NOTIFICATIONS_ENABLED`, `NOTIFICATION_TIMEOUT_SECONDS`, `NOTIFICATION_MAX_ATTEMPTS`
- `TELEGRAM_NOTIFICATIONS_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_TEMPLATE_NAME`, `TELEGRAM_PREFERRED_LANGUAGE`
- `WEBHOOK_NOTIFICATIONS_ENABLED`, `WEBHOOK_URL`, `WEBHOOK_AUTH_HEADER`

## 5. Kiểm tra môi trường đã lên đúng chưa

Dấu hiệu backend ổn:

- Scheduler log báo đã khởi động
- PostgreSQL schema được tạo thành công
- Sau vòng chạy đầu tiên có log `pipeline success`
- Nếu bật Telegram notification và có record mới, sẽ thấy log `notification success`
  theo từng tin và chat đích đã được che bớt

Dấu hiệu web ổn:

- Mở được dashboard tại cổng web
- `GET /api/batches` trả JSON hợp lệ
- Nếu bật share API, `GET /api/share/default` trả về PNG

## 6. Những điểm cần lưu ý khi chạy local

- Lần chạy đầu có thể tải model NLP khá nặng, nên thời gian khởi động sẽ dài.
- Nếu dùng Docker backend với mô hình offline, cache Hugging Face phải có sẵn.
- Các giá trị secret và endpoint LLM không nên giữ cứng cho môi trường thật;
  ưu tiên override bằng biến môi trường.
- `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` chỉ nên cấp qua env khi cần kiểm
  thử notification, không commit vào repo.
- `WEBHOOK_AUTH_HEADER` nếu dùng phải theo format `Header-Name: value`.
- `config/sources.yaml` có thể được tạo tự động nếu chưa tồn tại.

## 7. Kiểm thử nhanh Telegram notification

Ví dụ bật notification local:

```bash
export NOTIFICATIONS_ENABLED=true
export TELEGRAM_NOTIFICATIONS_ENABLED=true
export TELEGRAM_BOT_TOKEN=<your-bot-token>
export TELEGRAM_CHAT_ID=<your-chat-id>
export TELEGRAM_TEMPLATE_NAME=default
PYTHONPATH=src python -m opennews.main
```

Kỳ vọng:

- Batch có record mới sẽ gửi một tin nhắn Telegram cho mỗi tin đã processed
- Nếu batch không có record mới thì không gửi tin nhắn
- Log backend cho biết tin nào gửi thành công hoặc thất bại

Kiểm thử gửi Telegram bằng tiếng Việt:

```bash
export NOTIFICATIONS_ENABLED=true
export TELEGRAM_NOTIFICATIONS_ENABLED=true
export TELEGRAM_BOT_TOKEN=<your-bot-token>
export TELEGRAM_CHAT_ID=<your-chat-id>
export TELEGRAM_TEMPLATE_NAME=default
export TELEGRAM_PREFERRED_LANGUAGE=vi-VN
PYTHONPATH=src python -m opennews.main
```

Kỳ vọng thêm:

- Nếu nội dung nguồn không phải tiếng Việt, phần nội dung human-readable trong
  Telegram sẽ được localize sang tiếng Việt trước khi render template
- Nếu translator không sẵn sàng hoặc dịch lỗi, message vẫn được gửi theo
  fallback canonical và log sẽ có `requested_language`, `delivered_language`,
  `translation_status`

## 8. Kiểm thử nhanh Webhook notification

Ví dụ bật webhook local:

```bash
export NOTIFICATIONS_ENABLED=true
export WEBHOOK_NOTIFICATIONS_ENABLED=true
export WEBHOOK_URL=https://example.com/opennews-hook
export WEBHOOK_AUTH_HEADER="Authorization: Bearer <token>"
PYTHONPATH=src python -m opennews.main
```

Kỳ vọng:

- Batch có record mới sẽ gửi một webhook payload cho mỗi tin đã processed
- Có thể bật webhook đồng thời với Telegram
- Nếu không gửi được, log sẽ cho biết sink `webhook` bị lỗi và host đích đã được sanitize

## 9. Checklist onboard nhanh

- Đọc xong tài liệu này
- Chạy được PostgreSQL, Neo4j, Redis
- Chạy được `python -m opennews.main`
- Chạy được `python web/server.py --port 8080`
- Mở được dashboard và thấy dữ liệu hoặc ít nhất API trả về đúng dạng
