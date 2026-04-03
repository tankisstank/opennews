# Notification Contract

Tài liệu này mô tả contract outbound nội bộ cho feature per-news processing
notifications. Đây không phải public API của OpenNews, nhưng là contract giữa
pipeline runtime và các sink bên ngoài.

## 1. Common news-processed event

Mọi sink đều được derive từ cùng một event nghiệp vụ chuẩn hóa:

```json
{
  "event_type": "news_processed",
  "batch_id": 123,
  "batch_ts": "20260402_153001_123",
  "news_id": "seed-001",
  "title": "Fed hints at slower rate cuts",
  "source": "seed",
  "result": "news processed successfully",
  "completed_at": "2026-04-02T15:30:05Z"
}
```

Ngôn ngữ đích cho delivery, nếu có, được derive từ runtime config của sink và
không làm thay đổi event canonical ở trên.

## 2. Telegram sink contract

### Delivery rule

- Gửi một tin nhắn văn bản cho mỗi `NewsProcessedEvent`.
- Telegram là sink ưu tiên trong v1.
- Nội dung phải được render từ Telegram template.
- Nếu có cấu hình ngôn ngữ đích như `vi-VN`, phần nội dung human-readable phải
  được localize sang ngôn ngữ đó trước khi render template.
- Nội dung phải đủ để đối chiếu với log và batch trong DB.
- Failure của Telegram không được ngăn sink khác hoặc làm fail scheduler job.

### Template contract

- V1 chỉ chốt rằng Telegram message phải đi qua một template chuyên biệt.
- Cấu trúc chi tiết của template, wording và formatting sẽ được quyết định ở
  giai đoạn triển khai.
- Template tối thiểu phải có khả năng truy cập các biến từ `NewsProcessedEvent`
  như `batch_id`, `batch_ts`, `news_id`, `title`, `source`, `result`,
  `completed_at`.
- Nếu có localize, template phải nhận được bản biến đã localize cho các trường
  human-readable và vẫn giữ nguyên các identifier hoặc link canonical.

### Language handling

- `preferred_language` là cấu hình runtime của Telegram sink, không phải field
  persisted mới của record tin.
- Bước localize dùng cùng runtime cấu hình LLM hiện có của OpenNews; đây là
  translator path mặc định trong increment này.
- Nếu nội dung đã sẵn ở ngôn ngữ đích, hệ thống bỏ qua bước dịch dư thừa.
- Nếu localize lỗi, hệ thống được phép fallback sang nội dung canonical miễn là
  log nêu rõ requested language, delivered language và lý do fallback.

## 3. Webhook sink contract

### Delivery rule

- Gửi `POST` đúng một payload cho mỗi `NewsProcessedEvent`.
- Header xác thực là tùy chọn, nhưng nếu được cấu hình thì phải đi cùng request.
- Failure của webhook không được thay đổi kết quả batch.
- Increment localize này không thay đổi shape payload webhook canonical.

### Payload shape

```json
{
  "event_type": "news_processed",
  "batch": {
    "id": 123,
    "timestamp": "20260402_153001_123"
  },
  "news": {
    "id": "seed-001",
    "title": "Fed hints at slower rate cuts",
    "source": "seed"
  },
  "result": {
    "status": "success",
    "summary": "news processed successfully"
  },
  "meta": {
    "completed_at": "2026-04-02T15:30:05Z",
    "source": "opennews"
  }
}
```

## 4. Logging contract

Mỗi sink phải log được ít nhất:

- `batch_id`
- `batch_ts`
- `news_id`
- `sink_kind`
- `attempt_number`
- `status`
- `latency_ms` nếu có
- `error_code` hoặc mô tả lỗi đã sanitize nếu thất bại
- `requested_language` nếu feature language selection được bật
- `delivered_language` nếu khác với requested language hoặc có fallback
- `translation_status` khi localize được áp dụng cho sink đó

## 5. Non-goals for v1

- Không chuẩn hóa inbound acknowledgement từ phía receiver.
- Không lưu contract delivery history vào DB.
- Không hỗ trợ rich media hoặc interactive Telegram message.
- Không thêm rule lọc top-N, score threshold hoặc dedup notification ngoài phạm
  vi một lần xử lý batch hiện tại.
- Không chốt wording cuối cùng của Telegram template ở giai đoạn đặc tả này.
- Không localize webhook payload trong increment này.
