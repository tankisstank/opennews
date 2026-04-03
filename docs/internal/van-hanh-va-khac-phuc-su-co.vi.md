# Vận hành và khắc phục sự cố

Tài liệu này là runbook nội bộ cho các lỗi và thao tác vận hành thường gặp trong
OpenNews.

## 1. Thành phần cần theo dõi

- Scheduler backend
- PostgreSQL
- Neo4j
- Redis
- Web server
- Share PNG cache nếu dùng API snapshot

## 2. Dấu hiệu hệ thống khỏe mạnh

### Backend

- Có log `scheduler started`
- Có log `PostgreSQL schema ensured`
- Mỗi vòng chạy có `pipeline success`
- Nếu không có tin mới, hệ thống không crash và vòng tiếp theo vẫn chạy

### Web

- Mở được dashboard
- `/api/batches` trả về JSON
- `/api/batches/latest` hoặc `/api/records` trả dữ liệu hợp lệ
- Nếu bật share API, `/api/share/default` trả PNG

## 3. Sự cố thường gặp và cách xử lý

### Không kết nối được PostgreSQL

Biểu hiện:

- Backend log lỗi khi `ensure_schema`
- Web API trả lỗi 500 ở các route dữ liệu

Cách kiểm tra:

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d opennews
```

Hướng xử lý:

- Kiểm tra `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`
- Xác nhận container hoặc dịch vụ PostgreSQL đang chạy
- Kiểm tra database `opennews` đã được tạo chưa

### Neo4j không sẵn sàng

Biểu hiện:

- Pipeline vẫn có thể chạy một phần nhưng log báo bỏ qua bước `write_graph`
- Trend hoặc graph query không cập nhật

Cách kiểm tra:

- Xác nhận cổng `7474` và `7687`
- Đăng nhập Neo4j Browser
- Kiểm tra user/password trong `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

Lưu ý:

Workflow hiện có fallback nhất định nếu Neo4j chưa sẵn sàng, nhưng đây không
phải trạng thái tốt để vận hành lâu dài.

### Redis lỗi hoặc mất kết nối

Biểu hiện:

- Log ở bước `memory ingest failed` hoặc `memory aggregation failed`
- Trend không được tính đúng hoặc không cập nhật

Cách kiểm tra:

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

Hướng xử lý:

- Kiểm tra `REDIS_URL`
- Kiểm tra giới hạn bộ nhớ hoặc trạng thái container Redis

### Web không lên dù backend đang chạy

Biểu hiện:

- Không truy cập được dashboard
- API web server không phản hồi

Cách kiểm tra:

- Xác nhận đã build frontend trong `web/dist`
- Chạy lại `npm run build` trong thư mục `web`
- Kiểm tra log `web/server.py`
- Kiểm tra cổng `8080` hoặc cổng được chỉ định

### Share API lỗi render PNG

Biểu hiện:

- `/api/share/default` trả lỗi 500
- Log có thông tin `share render failed`

Hướng xử lý:

- Kiểm tra Playwright/Chromium đã được cài chưa
- Kiểm tra thư mục cache trong `SHARE_CACHE_DIR`
- Thử gọi lại với `refresh=true`
- Nếu cần cô lập lỗi, tắt share scheduler trước bằng `SHARE_SCHEDULER_ENABLED=false`

### Pipeline không có dữ liệu mới

Biểu hiện:

- Batch mới có `record_count = 0`
- Dashboard không có record mới

Điểm cần kiểm tra:

- Nguồn trong `config/sources.yaml` còn trả dữ liệu không
- Checkpoint có chặn mất dữ liệu mới không
- URL tin đã tồn tại trong `batch_records` nên bị deduplicate hay chưa
- Seed file có nội dung hợp lệ không

### Webhook notification lỗi

Biểu hiện:

- Log có `notification failed` với `sink=webhook`
- Telegram có thể vẫn gửi thành công nhưng webhook không nhận được payload

Cách kiểm tra:

- Kiểm tra `WEBHOOK_NOTIFICATIONS_ENABLED`, `WEBHOOK_URL`,
  `WEBHOOK_AUTH_HEADER`
- Kiểm tra endpoint đích có đang nhận `POST` JSON hay không
- Kiểm tra log destination đã sanitize để chắc đang trỏ đúng host

Hướng xử lý:

- Xác nhận URL webhook đúng và còn hoạt động
- Nếu dùng auth header, bảo đảm format là `Header-Name: value`
- Dùng endpoint thử nghiệm để kiểm tra từng payload trước khi nối production
- Nếu `NOTIFICATION_MAX_ATTEMPTS > 1`, một tin có thể tạo nhiều log failure cho
  cùng sink trước khi hệ thống bỏ qua sink đó

### Telegram notification lỗi

Biểu hiện:

- Log có `notification failed` với `sink=telegram`
- Batch vẫn hoàn tất nhưng không có tin nhắn gửi tới chat đích

Cách kiểm tra:

- Kiểm tra `NOTIFICATIONS_ENABLED`, `TELEGRAM_NOTIFICATIONS_ENABLED`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Kiểm tra bot có quyền gửi vào chat đó hay chưa

Hướng xử lý:

- Cấp lại bot token nếu nghi ngờ hết hiệu lực
- Xác nhận chat ID đúng môi trường cần kiểm thử
- Nếu cần cô lập lỗi, tắt Telegram sink riêng thay vì tắt toàn bộ scheduler

### Telegram localize không chạy đúng ngôn ngữ mong muốn

Biểu hiện:

- Đã đặt `TELEGRAM_PREFERRED_LANGUAGE=vi-VN` nhưng message vẫn ra nội dung gốc
- Log có `translation_status=fallback_source`

Cách kiểm tra:

- Kiểm tra `TELEGRAM_PREFERRED_LANGUAGE` có đang được set đúng không
- Kiểm tra `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` hoặc `config/llm.yaml`
  nếu đang kỳ vọng dịch thật
- Kiểm tra log `notification language` để xem `requested_language`,
  `delivered_language`, `fallback_reason`

Hướng xử lý:

- Nếu chỉ cần tín hiệu vận hành, có thể chấp nhận fallback canonical tạm thời
- Nếu cần message tiếng Việt thật, xác nhận translator/LLM đang hoạt động và
  còn quyền gọi API
- Nếu nội dung nguồn đã là tiếng Việt, `translation_status=not_needed` là hành
  vi bình thường chứ không phải lỗi

### Notification bị skip

Biểu hiện:

- Log có `notification dispatch skipped`
- Batch vẫn thành công nhưng không có outbound notification

Điểm cần kiểm tra:

- `NOTIFICATIONS_ENABLED` có đang bật không
- Batch đó có `record_count > 0` không
- Có sink nào đang bật thật sự không

Giải thích các skip reason thường gặp:

- `notifications_disabled`: master switch đang tắt
- `summary_not_eligible`: batch không đủ điều kiện phát notification
- `no_enabled_sinks`: không có sink đang bật hoặc được đăng ký

## 4. Truy vấn kiểm tra nhanh

### Xem các batch gần nhất

```sql
SELECT batch_id, batch_ts, created_at, record_count
FROM batches
ORDER BY batch_ts DESC
LIMIT 20;
```

### Xem record của một batch

```sql
SELECT id, news_id, news_url
FROM batch_records
WHERE batch_id = <batch_id>
ORDER BY id;
```

### Xem report gần nhất

```sql
SELECT batch_id, news_id, impact_level
FROM reports
ORDER BY id DESC
LIMIT 20;
```

## 5. Khi nào cần replay hoặc backfill

Cân nhắc replay/backfill khi:

- Đổi logic scoring hoặc feature extraction
- Đổi topic assignment hoặc refine label
- Đổi contract payload ảnh hưởng dữ liệu đã lưu
- Sửa lỗi làm batch trước đó ghi dữ liệu sai

Trước khi replay cần xác định:

- Phạm vi thời gian hoặc batch bị ảnh hưởng
- Cách deduplicate hiện tại có làm mất dữ liệu khi replay không
- Có cần dọn dữ liệu cũ hay ghi đè bằng batch mới không

## 6. Chuẩn log mong muốn

Khi sửa code, ưu tiên log được các thông tin sau:

- Batch ID hoặc batch timestamp
- Source hoặc endpoint nguồn tin
- Số lượng record trước và sau deduplicate
- Bước nào fail và fail vì lý do gì
- Sink nào fail: Telegram hay webhook
- Tin nào (`news_id`) bị fail khi phát notification
- Ngôn ngữ nào được yêu cầu và ngôn ngữ nào thực tế được gửi ra khi có
  localize Telegram
- Có fallback hay skip bước nào không

## 7. Escalation nội bộ

Cần dừng và trao đổi với cả nhóm nếu gặp một trong các tình huống sau:

- Không chắc migration dữ liệu có an toàn không
- Kết quả scoring thay đổi diện rộng nhưng chưa có baseline so sánh
- Thay đổi contract có thể ảnh hưởng dashboard hoặc consumer khác
- Muốn thêm service/dependency mới để giải quyết một vấn đề ngắn hạn

## 8. Sau khi xử lý sự cố

Nên làm đủ các bước sau:

- Ghi lại nguyên nhân gốc
- Chỉ ra batch hoặc khoảng thời gian bị ảnh hưởng
- Bổ sung test hoặc guardrail để lỗi không lặp lại
- Cập nhật lại tài liệu nội bộ nếu runbook còn thiếu
