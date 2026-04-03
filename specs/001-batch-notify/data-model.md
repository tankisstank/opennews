# Data Model: Per-News Processing Notifications

## 1. NewsProcessedEvent

Đại diện cho một tin đã được xử lý xong và đủ điều kiện để gửi notification.

| Field | Type | Required | Description |
|---|---|---:|---|
| `batch_id` | integer \| null | Yes | ID batch trong PostgreSQL; có thể `null` nếu chưa persist được |
| `batch_ts` | string | Yes | Timestamp nghiệp vụ của batch |
| `news_id` | string | Yes | ID duy nhất của tin |
| `news_url` | string | No | URL gốc của tin nếu có |
| `title` | string | No | Tiêu đề hiển thị cho người vận hành |
| `source` | string | No | Nguồn tin |
| `published_at` | string | No | Thời điểm phát hành của tin |
| `result` | string | Yes | Tóm tắt ngắn gọn việc xử lý đã hoàn tất |
| `completed_at` | string | Yes | Thời điểm phát event |
| `channels_requested` | list[string] | Yes | Danh sách sink được cấu hình cho tin này |
| `template_context` | object | No | Tập biến đầu vào để render Telegram template khi sink này được bật |
| `source_language` | string | No | Ngôn ngữ nguồn của nội dung human-readable nếu xác định được |
| `preferred_language` | string | No | Language tag người vận hành muốn nhận ở sink human-facing, ví dụ `vi-VN` |
| `localized_template_context` | object | No | Tập biến đã localize dùng để render Telegram message theo ngôn ngữ đích |

**Validation rules**

- `news_id`, `batch_ts` và `completed_at` phải có giá trị parse/đối chiếu được.
- `title` có thể thiếu nhưng khi đó formatter phải có nội dung fallback an toàn.
- Một `NewsProcessedEvent` chỉ được sinh cho record đã persisted thành công.
- `template_context` nếu có phải được derive từ event nguồn, không trở thành
  nguồn dữ liệu độc lập mới.
- `localized_template_context` nếu có chỉ là view model dẫn xuất cho delivery,
  không thay thế giá trị canonical trong event.
- `preferred_language` nếu có phải dùng language tag chuẩn hóa và được áp dụng
  theo policy của sink.

## 2. NotificationSinkConfig

Cấu hình nghiệp vụ cho một kênh nhận thông báo.

| Field | Type | Required | Description |
|---|---|---:|---|
| `kind` | enum(`telegram`, `webhook`) | Yes | Loại sink |
| `enabled` | boolean | Yes | Sink có tham gia gửi hay không |
| `destination` | string | Yes | Telegram chat target hoặc endpoint URL |
| `auth_present` | boolean | Yes | Có thông tin xác thực để gửi hay không |
| `timeout_seconds` | number | Yes | Giới hạn thời gian cho một lần thử |
| `max_attempts` | integer | Yes | Số lần thử tối đa cho mỗi event |
| `preferred_language` | string | No | Ngôn ngữ đích cho nội dung human-readable của sink |
| `fallback_to_source` | boolean | Yes | Có cho phép quay về nội dung canonical khi localize lỗi hay không |

## 3. DeliveryAttempt

Kết quả của một lần thử gửi một `NewsProcessedEvent` tới một sink.

| Field | Type | Required | Description |
|---|---|---:|---|
| `news_id` | string | Yes | Tin đang được gửi thông báo |
| `sink_kind` | string | Yes | Sink được gửi |
| `attempt_number` | integer | Yes | Lần thử thứ mấy |
| `status` | enum(`success`, `failed`, `skipped`) | Yes | Kết quả |
| `latency_ms` | integer | No | Thời gian gửi |
| `error_code` | string | No | Mã lỗi hoặc loại lỗi |
| `error_message` | string | No | Mô tả lỗi đã được sanitize |
| `requested_language` | string | No | Ngôn ngữ được yêu cầu cho lần gửi này |
| `delivered_language` | string | No | Ngôn ngữ thực tế đã được gửi ra sau khi áp dụng fallback nếu có |
| `translation_status` | enum(`not_needed`, `translated`, `fallback_source`, `failed`) | No | Trạng thái localize của attempt |

## 4. State transitions

```text
Batch completed successfully
-> Build NewsProcessedEvent for each persisted record
-> Resolve enabled sinks
-> Resolve preferred language and derive localized template context when needed
-> Attempt delivery per sink for each event
-> Log per-news per-sink outcome
-> Return summary without changing batch persistence outcome
```

## 5. Persistence impact

- Không thêm entity persisted mới trong v1.
- `NewsProcessedEvent` và `DeliveryAttempt` chỉ sống trong memory/runtime log.
