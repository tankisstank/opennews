# Research: Per-News Processing Notifications

## Decision 1: Ghi nhận thay đổi ở cấp feature, không phải task

- **Decision**: Ghi nhận per-news notification như một feature độc lập trong
  Speckit.
- **Rationale**: Thay đổi này thêm hành vi runtime mới, contract outbound mới,
  cấu hình vận hành, observability, rollback và kiểm thử riêng. Nếu chỉ ghi
  thành task, các nghĩa vụ này dễ bị bỏ sót.
- **Alternatives considered**:
  - Ghi thành task trong một feature pipeline chung: thiếu chỗ mô tả success
    criteria và acceptance scenario riêng.
  - Chỉ cập nhật runbook: không đủ để dẫn dắt thiết kế và task implementation.

## Decision 2: Phân tích hiện trạng trước khi lên kế hoạch triển khai

- **Decision**: Kiểm tra codebase hiện tại trước khi chốt plan chi tiết để phân
  biệt rõ phần đã chuẩn bị và phần chưa được implement.
- **Rationale**: Feature này đã có artifact Speckit từ trước; nếu không rà lại
  mã nguồn thực tế sẽ dễ sinh plan lặp hoặc giả định sai rằng notification code
  đã tồn tại.
- **Findings snapshot**:
  - Đã có tài liệu feature trong `specs/001-batch-notify/`.
  - Đã có `src/opennews/notify/`, wiring trong scheduler/pipeline và test suite
    cho Telegram, webhook và failure isolation.
  - Đã có outbound language selection cho Telegram với
    `TELEGRAM_PREFERRED_LANGUAGE`, localized template context và structured log
    cho requested/delivered language.
  - Đã có `src/opennews/notify/localization.py` để tái sử dụng `LLMConfig` /
    `LLMClient` của project cho translation ở presentation layer.
  - Telegram hiện có đường localize human-readable content; webhook payload vẫn
    là canonical event mapping theo đúng phạm vi đã chốt.
- **Alternatives considered**:
  - Bỏ qua bước rà hiện trạng và lập plan từ spec: nhanh hơn nhưng dễ lệch với
    codebase.

## Decision 3: Phát notification ở scheduler layer sau khi pipeline trả danh sách news events

- **Decision**: Để `run_once()` trả một structured batch summary cùng danh sách
  các `NewsProcessedEvent`, còn `polling_job.py` quyết định có gửi notification
  hay không.
- **Rationale**: Cách này giữ outbound notification tách khỏi graph workflow,
  giúp cô lập lỗi sink, đơn giản hóa retry policy và tránh biến notification
  thành dependency chặn luồng persist dữ liệu.
- **Alternatives considered**:
  - Thêm node `notify` vào cuối LangGraph workflow: làm outbound HTTP thành một
    phần của đường chạy dữ liệu chính.
  - Gửi thẳng trong `dump_output_node`: biết được `batch_id` nhưng làm coupling
    chặt với persistence path và khó điều phối nhiều sink.

## Decision 4: V1 gửi cho từng tin mới đã persisted thành công

- **Decision**: Mỗi tin mới được xử lý xong và persisted thành công trong batch
  sẽ sinh một notification event riêng.
- **Rationale**: Phù hợp trực tiếp với nhu cầu "bất kỳ tin nào trong batch" và
  cho phép Telegram phản ánh từng tin thay vì chỉ tóm tắt cả batch.
- **Alternatives considered**:
  - Chỉ gửi một summary cho cả batch: không còn bám đúng scope mới.
  - Chỉ gửi cho top-N tin: cần thêm rule lọc chưa được yêu cầu ở v1.

## Decision 5: Telegram là sink ưu tiên, webhook là sink bổ sung

- **Decision**: Ưu tiên Telegram ở user story và implementation plan; webhook là
  kênh tùy chọn dùng cùng event model.
- **Rationale**: Đây là kênh mang lại giá trị trực tiếp cho người vận hành hiện
  tại và giúp kiểm chứng trải nghiệm nhanh hơn.
- **Alternatives considered**:
  - Ưu tiên webhook trước: tốt cho tích hợp hệ thống nhưng chưa đúng nhu cầu
    hiện tại của người dùng.

## Decision 6: Telegram message phải đi qua template, nhưng chưa chốt template cụ thể

- **Decision**: Chỉ khóa yêu cầu "Telegram dùng template" trong spec; nội dung
  và biến cụ thể của template sẽ được quyết định ở giai đoạn triển khai.
- **Rationale**: Tránh hard-code format quá sớm nhưng vẫn bảo đảm kiến trúc có
  điểm mở rõ ràng cho việc thay đổi thông điệp sau này.
- **Alternatives considered**:
  - Chốt template ngay trong spec: quá sớm khi chưa đi vào thiết kế chi tiết.
  - Không nhắc tới template ở spec: dễ dẫn tới implementation hard-code.

## Decision 7: Không thêm persisted delivery store ở v1

- **Decision**: Không lưu delivery attempt vào PostgreSQL trong phiên bản đầu.
- **Rationale**: Log runtime đã đủ cho nhu cầu debug ban đầu; thêm bảng mới sẽ
  tăng scope, migration và chi phí vận hành không cần thiết.
- **Alternatives considered**:
  - Lưu lịch sử notification vào DB: hữu ích cho audit nhưng chưa cần thiết để
    giải quyết bài toán hiện tại.

## Decision 8: Chuẩn hóa một event model dùng chung cho mọi sink

- **Decision**: Tạo một model nghiệp vụ trung tâm cho `NewsProcessedEvent` rồi
  map sang Telegram message hoặc webhook payload.
- **Rationale**: Giảm drift giữa các sink, giúp test một lần cho dữ liệu nguồn
  và chỉ format khác nhau ở lớp adapter.
- **Alternatives considered**:
  - Mỗi sink tự đọc thẳng từ pipeline state: dễ lặp logic và khó bảo trì.

## Decision 9: Chọn ngôn ngữ gửi ra là phần mở rộng của feature hiện có, không chỉ là task lẻ

- **Decision**: Ghi nhận outbound language selection như một mở rộng của cùng
  feature notification, với spec/plan/tasks riêng trong cùng thư mục feature.
- **Rationale**: Yêu cầu này làm thay đổi hành vi người dùng nhìn thấy, mở thêm
  config runtime, policy fallback, observability và tiêu chí chấp nhận; nếu chỉ
  thêm như task kỹ thuật sẽ thiếu chỗ mô tả contract hành vi.
- **Alternatives considered**:
  - Chỉ thêm note vào README hoặc runbook: không đủ để mô tả ranh giới và test
    độc lập của phần localize.

## Decision 10: Ưu tiên localize Telegram trước, giữ webhook canonical ở phạm vi hiện tại

- **Decision**: Áp dụng lựa chọn ngôn ngữ cho Telegram trước; webhook tiếp tục
  giữ payload canonical/source-language cho đến khi có spec riêng cho
  downstream consumer.
- **Rationale**: Nhu cầu mới nhắm vào trải nghiệm đọc của người vận hành
  ("gửi cho tôi"), trong khi webhook đã có contract và integration test ổn định.
  Giữ webhook canonical giúp tránh breaking change không cần thiết.
- **Alternatives considered**:
  - Localize luôn cả webhook: bao phủ rộng hơn nhưng dễ phá contract downstream.
  - Hoãn toàn bộ localize cho tất cả sink: không giải quyết nhu cầu hiện tại.

## Decision 11: Dịch nội dung human-readable trước khi render Telegram template

- **Decision**: Dùng `NewsProcessedEvent` canonical làm nguồn, derive localized
  fields hoặc localized template context trước khi render Telegram template.
- **Rationale**: Cách này giữ template là bước trình bày cuối cùng, giúp đổi
  template mà không phải đổi contract event nguồn, đồng thời tách rõ dữ liệu gốc
  và dữ liệu localize.
- **Alternatives considered**:
  - Dịch toàn bộ message sau khi render template: dễ khóa cứng wording và khó
    kiểm soát phần identifier/link không nên dịch.
  - Ghi đè thẳng vào event canonical: làm mờ ranh giới giữa dữ liệu gốc và dữ
    liệu dẫn xuất.

## Decision 12: Nếu localize lỗi thì fallback sang nội dung canonical nhưng không mất notification

- **Decision**: Khi không tạo được bản dịch theo ngôn ngữ đã chọn, hệ thống vẫn
  tiếp tục delivery bằng fallback canonical và log rõ requested language,
  delivered language cùng lý do fallback.
- **Rationale**: Với notification vận hành, bỏ lỡ tín hiệu quan trọng thường tệ
  hơn việc tạm thời đọc nội dung gốc. Quy tắc này cũng bám nguyên tắc failure
  isolation đã có.
- **Alternatives considered**:
  - Bỏ qua message nếu không dịch được: giữ đúng ngôn ngữ hơn nhưng làm mất tín
    hiệu vận hành.
  - Fail cả sink khi localize lỗi: trái với yêu cầu resilience hiện có.

## Decision 13: Dùng cùng LLM runtime/config của project cho translation

- **Decision**: Translation/localization của notification dùng cùng
  `LLMConfig` / `LLMClient` và provider/model runtime đang được cấu hình cho
  project, và đây là hướng đã được triển khai, thay vì thêm một translator
  service hay dependency riêng.
- **Rationale**: Giảm số lượng cấu hình cần vận hành, giữ chất lượng dịch nhất
  quán với năng lực LLM đã được chấp nhận trong project, và tránh mở thêm một
  stack tích hợp mới chỉ cho nhu cầu localize message.
- **Alternatives considered**:
  - Dùng translator API riêng: có thể rẻ hơn ở một số tình huống nhưng tăng
    complexity vận hành và làm phân mảnh cấu hình.
  - Dùng rule-based/local dictionary: không đủ linh hoạt cho ngữ cảnh tin tài
    chính và message vận hành.

## Decision 14: Translation chỉ áp dụng ở presentation layer, không mở rộng sang canonical data

- **Decision**: Chỉ localize các output human-facing như Telegram message; DB
  payload, graph data, webhook payload và các machine-facing contract vẫn giữ
  canonical/source form. Đây là ranh giới kiến trúc hiện đang được áp dụng.
- **Rationale**: Giữ ranh giới dữ liệu gốc rõ ràng, giảm rủi ro breaking change
  cho downstream consumer, và cho phép rollback/fallback đơn giản khi localize
  lỗi.
- **Alternatives considered**:
  - Dịch toàn bộ project/canonical data: phạm vi quá rộng, tăng rủi ro drift dữ
    liệu và regression ở nhiều bề mặt.
