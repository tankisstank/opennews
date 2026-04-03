# Implementation Plan / Kế hoạch triển khai: Per-News Processing Notifications

**Branch**: `001-batch-notify` | **Date**: 2026-04-03 | **Spec**: [spec.md](./spec.md)  
**Input**: Đặc tả tính năng từ `/specs/001-batch-notify/spec.md`

**Note / Ghi chú**: Tính năng này vẫn là một `feature`, không phải chỉ là
`task`, vì nó thêm capability runtime mới ở mức hành vi: phát event cho từng tin
đã xử lý xong, có sink Telegram/Webhook, cấu hình vận hành riêng, observability
riêng và success criteria riêng.

## Summary / Tóm tắt

Feature hiện đã triển khai đầy đủ theo phạm vi đã chốt: sau mỗi batch thành
công, mỗi tin mới đã được xử lý xong có thể phát ra Telegram và/hoặc webhook,
với Telegram dùng template, failure isolation theo từng sink và hỗ trợ chọn
ngôn ngữ đích như `vi-VN`. Quyết định kiến trúc được áp dụng là tái sử dụng
cùng LLM runtime/config đang dùng trong project cho bước dịch, nhưng chỉ áp
dụng ở presentation layer. Webhook vẫn giữ payload canonical để tránh phá
downstream contract.

## Current State Analysis / Phân tích hiện trạng

- **Đã có**: Notification runtime đã tồn tại trong `src/opennews/notify/`,
  `src/opennews/workflow/langgraph_pipeline.py`, `src/opennews/scheduler/polling_job.py`
  và `src/opennews/config.py`.
- **Đã có**: Bộ test cho notification đã tồn tại trong `tests/unit/` và
  `tests/integration/`, đủ làm baseline regression cho increment mới.
- **Đã có**: Telegram hiện render bằng template `default`, webhook dùng cùng
  `NewsProcessedEvent`, và failure isolation đã được chứng minh bằng test.
- **Đã có**: Increment ngôn ngữ đã thêm `TELEGRAM_PREFERRED_LANGUAGE`,
  localized notification view model, translation/localization path cho Telegram
  và log `requested_language`/`delivered_language`.
- **Điểm cần giữ ổn định**: Webhook payload contract hiện đã được document và
  test; phạm vi ngôn ngữ hiện tại tránh đổi shape payload canonical nếu chưa có
  nhu cầu downstream rõ ràng.
- **Có thể tái dùng**: Repo đã có `LLMConfig` / `LLMClient` và các pattern dịch
  nhãn chủ đề trong `src/opennews/agents/topic_refine_agent.py`; phạm vi này
  nên tái sử dụng cùng runtime LLM thay vì thêm translator stack mới.

**Planning implication / Hệ quả cho kế hoạch**: Feature này đã được chuẩn bị tài
liệu và phần baseline đã được triển khai. FR-022 chốt rõ hướng thiết kế:
translation đi qua cùng runtime LLM của project và chỉ nằm ở presentation
layer, nên mọi mở rộng tiếp theo phải ưu tiên tái sử dụng `LLMConfig` /
`LLMClient` thay vì thêm translator stack mới.

## Technical Context / Bối cảnh kỹ thuật

**Language/Version**: Python 3.10+  
**Primary Dependencies**: Notification package hiện có, LangGraph pipeline,
APScheduler, HTTP client hiện có cho outbound integration, `LLMConfig` /
`LLMClient` hiện có của project và pattern dịch nội dung hiện có trong codebase
nếu được tái dùng  
**Storage**: Không thêm persisted storage mới ở v1; dùng log runtime hiện có  
**Testing**: unittest-based unit/integration tests hiện có + manual verification
theo quickstart  
**Target Platform**: Linux server và local Docker/dev flow hiện có  
**Project Type**: Batch pipeline + web service  
**Performance Goals**: Phát notification cho từng tin trong vòng 60 giây sau khi
batch được ghi xong, không làm tăng thời gian một vòng polling vượt quá timeout
đã cấu hình kể cả khi có bước localize  
**Constraints**: Không làm fail pipeline nếu sink lỗi hoặc nếu localize lỗi; có
thể có nhiều message trong một batch; không đổi DB/schema/web API contract hiện
có; secret phải đi qua env/config; log phải che bớt secret; webhook canonical
contract cần giữ ổn định trong increment này; translation phải đi qua cùng LLM
runtime/config của project thay vì cấu hình tách riêng  
**Scale/Scope**: Một `NewsProcessedEvent` cho mỗi tin mới đã được xử lý thành
công trong batch; Telegram là sink ưu tiên và là nơi áp dụng ngôn ngữ đích ở
increment này; webhook là sink tùy chọn và vẫn giữ payload canonical

## Constitution Check / Kiểm tra hiến pháp

*GATE: Phải đạt trước Phase 0 research. Kiểm tra lại sau Phase 1 design.*

- **Data integrity**: PASS. Feature chỉ tiêu thụ metadata của batch và từng tin
  đã persisted thành công, không đổi ngữ nghĩa record, score, graph edge hay
  persisted payload.
- **Contract stability**: PASS với điều kiện contract outbound mới được mô tả
  riêng và không làm thay đổi contract hiện có của DB/web API.
- **Replayability and observability**: PASS. Notification phải bám theo
  `batch_id`/`batch_ts`/`news_id`, có log theo từng tin và sink; phần hỗ trợ ngôn
  ngữ phải bổ sung `requested_language`/`delivered_language` và vẫn replay được
  bằng seed + endpoint thử nghiệm.
- **Verification**: PASS. Baseline đã có unit test cho formatter/service và
  integration test cho scheduler-to-sink path; phần hỗ trợ ngôn ngữ đã được mở
  rộng trên cùng test suite thay vì tạo harness mới.
- **Operability**: PASS. Không thêm service mới; chỉ thêm outbound HTTP tích hợp
  vào luồng Python hiện có với feature flag, timeout và retry rõ ràng; bước
  localize phải có fallback để người vận hành vẫn nhận được tín hiệu.

## Project Structure / Cấu trúc dự án

### Documentation (this feature) / Tài liệu của tính năng

```text
specs/001-batch-notify/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── notification-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root) / Mã nguồn

```text
src/opennews/
├── config.py
├── agents/
│   └── topic_refine_agent.py
├── scheduler/
│   └── polling_job.py
├── workflow/
│   └── langgraph_pipeline.py
└── notify/
    ├── __init__.py
    ├── localization.py
    ├── models.py
    ├── service.py
    ├── telegram.py
    └── webhook.py

tests/
├── integration/
│   └── test_news_notifications.py
└── unit/
    ├── test_notification_service.py
    └── test_notification_formatters.py
```

**Structure Decision / Quyết định cấu trúc**: Giữ `src/opennews/notify/` là
điểm tập trung cho event model, formatter, sink policy và increment localize.
`langgraph_pipeline.py` tiếp tục chỉ trả structured batch summary cùng danh sách
news events canonical; `polling_job.py` chỉ điều phối dispatch sau khi pipeline
hoàn tất. Mọi localize cho Telegram là lớp dẫn xuất trong notification
service/adapter, với `src/opennews/notify/localization.py` là lớp adapter dùng
chung `LLMConfig` / `LLMClient` hiện có, tránh làm bẩn event canonical hoặc
webhook payload.

## Complexity Tracking / Theo dõi độ phức tạp

Không có vi phạm hiến pháp nào cần biện minh ở thời điểm lập plan.
