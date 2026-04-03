# Tasks / Danh sách công việc: Per-News Processing Notifications

**Input**: Tài liệu thiết kế từ `/specs/001-batch-notify/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/notification-contract.md`

**Tests**: Bắt buộc có unit/integration test vì thay đổi làm khác hành vi runtime.

**Organization**: Task được nhóm theo user story để mỗi story có thể được triển
khai và kiểm thử độc lập.

## Phase 1: Setup / Thiết lập ban đầu

**Purpose / Mục đích**: Chuẩn bị contract summary và khung cấu hình cho feature

- [x] T001 Xác định structured batch summary và danh sách `NewsProcessedEvent` trong `src/opennews/workflow/langgraph_pipeline.py`
- [x] T002 [P] Khai báo runtime settings cho feature flag và sink notification trong `src/opennews/config.py`
- [x] T003 [P] Tạo namespace notification, model nghiệp vụ và điểm mở cho Telegram template trong `src/opennews/notify/__init__.py` và `src/opennews/notify/models.py`
- [x] T004 [P] Ghi fixture/check helper cho `NewsProcessedEvent` trong `tests/unit/test_notification_service.py`

---

## Phase 2: Foundational / Nền tảng chặn luồng

**Purpose / Mục đích**: Hạ tầng chung cho mọi sink

- [x] T005 Tạo service điều phối delivery theo từng tin và từng sink trong `src/opennews/notify/service.py`
- [x] T006 [P] Bổ sung policy timeout/retry/sanitize log dùng chung trong `src/opennews/notify/service.py`
- [x] T007 [P] Viết unit test cho sink selection, per-news fan-out và failure isolation trong `tests/unit/test_notification_service.py`
- [x] T008 Cập nhật `src/opennews/scheduler/polling_job.py` để dùng structured summary và gọi notification service sau `run_once()`

**Checkpoint**: Scheduler có thể điều phối notification theo từng tin mà chưa cần
kênh cụ thể

---

## Phase 3: User Story 1 - Gửi Telegram cho từng tin đã xử lý xong (Priority: P1) 🎯 MVP

**Goal / Mục tiêu**: Phát `NewsProcessedEvent` ra Telegram cho người vận hành

**Independent Test / Kiểm thử độc lập**: Chạy pipeline với Telegram sink thử
nghiệm và xác nhận mỗi record mới sinh đúng một tin nhắn Telegram

### Tests for User Story 1 / Kiểm thử cho User Story 1 ⚠️

- [x] T009 [P] [US1] Viết unit test cho Telegram template rendering trong `tests/unit/test_notification_formatters.py`
- [x] T010 [P] [US1] Viết integration test cho scheduler-to-telegram path trong `tests/integration/test_news_notifications.py`

### Implementation for User Story 1 / Triển khai cho User Story 1

- [x] T011 [P] [US1] Quyết định và implement Telegram template rendering trong `src/opennews/notify/telegram.py` và `src/opennews/notify/service.py`
- [x] T012 [US1] Nối Telegram adapter vào notification service trong `src/opennews/notify/service.py`
- [x] T013 [US1] Mở rộng `src/opennews/workflow/langgraph_pipeline.py` để trả `batch_id`, `batch_ts` và danh sách tin đã persisted cho notification
- [x] T014 [US1] Cập nhật cấu hình và mô tả verification cho Telegram trong `README.md` và `docs/internal/khoi-dong-cuc-bo.vi.md`

**Checkpoint**: Telegram per-news notification hoạt động độc lập cho batch có dữ
liệu mới

---

## Phase 4: User Story 2 - Phát cùng event đó qua webhook (Priority: P2)

**Goal / Mục tiêu**: Phát cùng `NewsProcessedEvent` ra webhook cho hệ thống ngoài

**Independent Test / Kiểm thử độc lập**: Chạy pipeline với webhook sink thử
nghiệm và xác nhận mỗi record mới sinh đúng một webhook payload

### Tests for User Story 2 / Kiểm thử cho User Story 2 ⚠️

- [x] T015 [P] [US2] Viết unit test cho webhook payload mapping trong `tests/unit/test_notification_formatters.py`
- [x] T016 [P] [US2] Viết integration test cho scheduler-to-webhook path trong `tests/integration/test_news_notifications.py`

### Implementation for User Story 2 / Triển khai cho User Story 2

- [x] T017 [P] [US2] Implement webhook notifier adapter trong `src/opennews/notify/webhook.py`
- [x] T018 [US2] Nối webhook adapter và multi-sink dispatch vào `src/opennews/notify/service.py`
- [x] T019 [US2] Cập nhật cấu hình và mô tả verification cho webhook trong `README.md` và `docs/internal/van-hanh-va-khac-phuc-su-co.vi.md`

**Checkpoint**: Webhook per-news notification hoạt động mà không phá vỡ Telegram
story

---

## Phase 5: User Story 3 - Lỗi gửi không làm hỏng pipeline chính (Priority: P3)

**Goal / Mục tiêu**: Gia cố khả năng vận hành và debug khi sink lỗi ở mức từng tin

**Independent Test / Kiểm thử độc lập**: Dùng sink giả lỗi, chạy pipeline, rồi
xác nhận batch vẫn hoàn tất và log chỉ ra tin nào, sink nào hỏng

### Tests for User Story 3 / Kiểm thử cho User Story 3 ⚠️

- [x] T020 [P] [US3] Viết integration test cho partial failure và retry policy trong `tests/integration/test_news_notifications.py`
- [x] T021 [P] [US3] Viết unit test cho log sanitization và skip policy trong `tests/unit/test_notification_service.py`

### Implementation for User Story 3 / Triển khai cho User Story 3

- [x] T022 [US3] Hoàn thiện structured logging per-news per-sink trong `src/opennews/notify/service.py`
- [x] T023 [US3] Bảo đảm scheduler không fail khi notification fail trong `src/opennews/scheduler/polling_job.py`
- [x] T024 [US3] Cập nhật runbook lỗi notification trong `docs/internal/van-hanh-va-khac-phuc-su-co.vi.md`
- [x] T025 [US3] Cập nhật quickstart/feature docs để phản ánh manual verification trong `specs/001-batch-notify/quickstart.md`

**Checkpoint**: Failure isolation cho per-news notification được chứng minh bằng
test và runbook

---

## Phase 6: Polish & Cross-Cutting Concerns / Hoàn thiện và mối quan tâm cắt ngang

- [x] T026 [P] Chạy và sửa toàn bộ test notification trong `tests/unit/` và `tests/integration/`
- [x] T027 Rà soát lại log message, redaction và naming consistency trong `src/opennews/notify/` và `src/opennews/scheduler/`
- [x] T028 [P] Đối chiếu tài liệu feature với tài liệu repo trong `README.md` và `docs/internal/`

---

## Phase 7: User Story 4 - Chọn ngôn ngữ gửi Telegram ra ngoài (Priority: P2)

**Goal / Mục tiêu**: Cho phép người vận hành chọn ngôn ngữ Telegram được gửi ra,
ví dụ `vi-VN`, mà không làm thay đổi event canonical hay webhook contract
hiện có

**Independent Test / Kiểm thử độc lập**: Cấu hình Telegram với ngôn ngữ đích
`vi-VN`, chạy pipeline có tin nguồn không phải tiếng Việt, rồi xác nhận message
Telegram hiển thị nội dung người đọc bằng tiếng Việt trong khi identifier vẫn
đối chiếu được với record gốc

### Tests for User Story 4 / Kiểm thử cho User Story 4 ⚠️

- [x] T029 [P] [US4] Viết unit test cho localized template context, language selection và fallback policy trong `tests/unit/test_notification_formatters.py` và `tests/unit/test_notification_service.py`
- [x] T030 [P] [US4] Viết integration test cho scheduler-to-telegram localized delivery với `vi-VN` trong `tests/integration/test_news_notifications.py`

### Implementation for User Story 4 / Triển khai cho User Story 4

- [x] T031 [US4] Mở rộng runtime settings và notification models cho preferred language cùng translation status trong `src/opennews/config.py` và `src/opennews/notify/models.py`
- [x] T032 [US4] Thêm bước localize human-readable fields bằng shared `LLMConfig` / `LLMClient` trước khi render Telegram template trong `src/opennews/notify/localization.py`, `src/opennews/notify/service.py` và `src/opennews/notify/telegram.py`
- [x] T033 [P] [US4] Giữ webhook payload canonical trong khi bổ sung localized delivery path cho Telegram trong `src/opennews/notify/webhook.py` và `src/opennews/notify/models.py`
- [x] T034 [US4] Ghi log requested language, delivered language và fallback reason cho từng attempt trong `src/opennews/notify/service.py`
- [x] T035 [US4] Cập nhật tài liệu cấu hình, quickstart và runbook cho language selection trong `README.md`, `docs/internal/` và `specs/001-batch-notify/quickstart.md`

**Checkpoint**: Telegram có thể phát notification theo ngôn ngữ đích mà không
phá webhook contract hoặc failure isolation hiện có, đồng thời vẫn tái sử dụng
runtime LLM chung của project theo FR-022

---

## Dependencies & Execution Order / Phụ thuộc và thứ tự thực hiện

### Phase Dependencies / Phụ thuộc giữa các phase

- **Setup (Phase 1)**: Bắt đầu ngay
- **Foundational (Phase 2)**: Phụ thuộc Setup
- **User Story 1 (Phase 3)**: Phụ thuộc Phase 2
- **User Story 2 (Phase 4)**: Phụ thuộc Phase 2, có thể tái dùng hạ tầng từ US1
- **User Story 3 (Phase 5)**: Phụ thuộc US1 hoặc US2 đã có ít nhất một sink
- **Polish (Phase 6)**: Phụ thuộc các story mong muốn đã hoàn thành
- **User Story 4 (Phase 7)**: Phụ thuộc US1 và ưu tiên chạy sau baseline Telegram đã ổn định

### User Story Dependencies / Phụ thuộc giữa các story

- **US1**: MVP, không phụ thuộc story khác
- **US2**: Phụ thuộc shared notification service nhưng vẫn kiểm thử độc lập
- **US3**: Phụ thuộc ít nhất một sink đã tồn tại để mô phỏng lỗi delivery
- **US4**: Phụ thuộc Telegram sink đã hoạt động để mở rộng localize mà không đổi event canonical

### Parallel Opportunities / Cơ hội chạy song song

- `T002`, `T003`, `T004` có thể làm song song
- `T006`, `T007` có thể làm song song sau `T005`
- `T009` và `T010` có thể chuẩn bị song song trong US1
- `T015` và `T016` có thể chuẩn bị song song trong US2
- `T020` và `T021` có thể chuẩn bị song song trong US3
- `T029` và `T030` có thể chuẩn bị song song trong US4

## Implementation Strategy / Chiến lược triển khai

### MVP First / Làm MVP trước

1. Hoàn thành Phase 1 và 2
2. Hoàn thành US1 để có Telegram per-news notification
3. Xác minh bằng quickstart trước khi mở rộng webhook

### Incremental Delivery / Bàn giao tăng dần

1. Telegram trước để chốt event model và trải nghiệm người vận hành
2. Webhook sau để tận dụng event model đã ổn định
3. Failure isolation sau cùng để gia cố vận hành
4. Language selection cho Telegram sau khi baseline notification đã ổn định

## Notes / Ghi chú

- Không cần tạo lại bộ spec/plan/research/data-model/contracts cho feature này;
  chúng đã tồn tại và là baseline cần bám theo khi implement.
- Nếu trong lúc implement phát sinh nhu cầu lọc chỉ một số tin hoặc gộp message
  theo batch, cần mở rộng feature scope bằng spec update thay vì tự thêm vào task.
- Increment chọn ngôn ngữ hiện được chốt theo hướng Telegram-first; nếu muốn
  localize luôn webhook payload cần mở rộng spec vì có rủi ro ảnh hưởng contract
  downstream.
