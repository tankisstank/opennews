# Feature Specification / Đặc tả tính năng: Per-News Processing Notifications

**Feature Branch**: `001-batch-notify`  
**Created**: 2026-04-02  
**Updated**: 2026-04-03  
**Status**: Implemented  
**Input**: Mô tả người dùng: "Gửi thông báo/ tin nhắn khi OpenNews xử lý xong bất kỳ tin nào trong batch qua Telegram và/ hoặc webhook. Telegram sẽ là ưu tiên hiện tại."

## User Scenarios & Testing / Kịch bản người dùng và kiểm thử *(bắt buộc)*

### User Story 1 - Gửi Telegram cho từng tin đã xử lý xong (Priority: P1)

Là người vận hành, tôi muốn nhận tin nhắn Telegram cho từng tin vừa được
OpenNews xử lý xong trong một batch, để tôi có thể theo dõi các tin mới quan
trọng ngay trên Telegram mà không cần tự mở dashboard hay dò log.

**Why this priority / Vì sao ưu tiên mức này**: Telegram là kênh ưu tiên hiện
tại vì phục vụ trực tiếp nhu cầu theo dõi của con người và là điểm chạm rõ nhất
để xác nhận giá trị của feature.

**Independent Test / Kiểm thử độc lập**: Cấu hình bot và chat thử nghiệm, chạy
một vòng pipeline tạo ra ít nhất hai record mới, rồi xác nhận mỗi record tạo ra
đúng một tin nhắn Telegram có thể đối chiếu được với dữ liệu batch.

**Acceptance Scenarios / Kịch bản chấp nhận**:

1. **Given** Telegram notification được bật và batch có nhiều tin mới,
   **When** vòng pipeline hoàn tất thành công, **Then** hệ thống gửi một tin
   nhắn Telegram riêng cho từng tin đã được xử lý xong trong batch đó.
2. **Given** Telegram notification được bật nhưng batch không có record mới,
   **When** vòng pipeline kết thúc, **Then** hệ thống không gửi tin nhắn nào.

---

### User Story 2 - Phát cùng event đó qua webhook (Priority: P2)

Là người vận hành hoặc hệ thống downstream, tôi muốn cùng thông tin từng tin đã
xử lý xong có thể được đẩy ra webhook, để nối OpenNews với automation hoặc hệ
thống khác ngoài Telegram.

**Why this priority / Vì sao ưu tiên mức này**: Webhook mở rộng khả năng tích
hợp nhưng không phải nhu cầu ưu tiên bằng Telegram trong giai đoạn hiện tại.

**Independent Test / Kiểm thử độc lập**: Cấu hình endpoint nhận thử, chạy một
vòng pipeline có record mới, rồi xác nhận endpoint nhận đúng một payload cho mỗi
tin được xử lý xong.

**Acceptance Scenarios / Kịch bản chấp nhận**:

1. **Given** webhook được bật và batch có record mới, **When** vòng pipeline
   hoàn tất thành công, **Then** hệ thống gửi một webhook payload riêng cho mỗi
   tin đã xử lý xong.
2. **Given** cả Telegram và webhook cùng được bật, **When** một tin được xử lý
   xong trong batch, **Then** cùng một event nghiệp vụ được map ra cả hai sink
   thay vì chỉ ưu tiên một sink duy nhất.

---

### User Story 3 - Lỗi gửi không làm hỏng pipeline chính (Priority: P3)

Là người vận hành, tôi muốn lỗi gửi notification cho một hoặc nhiều tin được
thấy rõ và chẩn đoán được nhưng không làm hỏng pipeline chính, để batch vẫn
được ghi và vòng polling tiếp theo vẫn tiếp tục.

**Why this priority / Vì sao ưu tiên mức này**: Đây là guardrail vận hành bắt
buộc theo hiến pháp dự án, đặc biệt quan trọng khi số lần gửi tăng lên theo số
tin trong batch.

**Independent Test / Kiểm thử độc lập**: Dùng sink giả lỗi hoặc timeout, chạy
một vòng pipeline có nhiều record mới, rồi xác nhận dữ liệu batch vẫn tồn tại và
log chỉ rõ tin nào, sink nào bị lỗi.

**Acceptance Scenarios / Kịch bản chấp nhận**:

1. **Given** một sink trả lỗi cho một tin, **When** hệ thống đang phát
   notification cho các tin trong batch, **Then** pipeline vẫn hoàn tất và tiếp
   tục thử gửi cho các tin khác theo policy đã định.
2. **Given** Telegram thành công nhưng webhook thất bại cho cùng một tin,
   **When** delivery kết thúc, **Then** hệ thống ghi nhận trạng thái theo từng
   sink để người vận hành biết sink nào cần sửa.

---

### User Story 4 - Chọn ngôn ngữ gửi Telegram ra ngoài (Priority: P2)

Là người vận hành, tôi muốn chọn ngôn ngữ của nội dung notification Telegram,
ví dụ `vi-VN`, để hệ thống chuyển ngữ nội dung hiển thị sang đúng ngôn ngữ tôi
muốn trước khi gửi cho tôi.

**Why this priority / Vì sao ưu tiên mức này**: Telegram là kênh ưu tiên hiện
tại và là nơi người vận hành đọc trực tiếp. Nếu không có lựa chọn ngôn ngữ,
giá trị theo dõi real-time vẫn có nhưng trải nghiệm đọc hiểu và hành động sẽ
thấp hơn đáng kể.

**Independent Test / Kiểm thử độc lập**: Cấu hình Telegram sink với ngôn ngữ
đích `vi-VN`, chạy một vòng pipeline với ít nhất một tin có nội dung nguồn
không phải tiếng Việt, rồi xác nhận message Telegram thể hiện nội dung
người-đọc bằng tiếng Việt trong khi các định danh như `batch_id`, `news_id` và
link vẫn đối chiếu được với record gốc.

**Acceptance Scenarios / Kịch bản chấp nhận**:

1. **Given** Telegram notification được bật và ngôn ngữ đích được chọn là
   `vi-VN`, **When** một tin được xử lý xong và đủ điều kiện gửi, **Then** nội
   dung người đọc trong message Telegram được chuyển ngữ sang tiếng Việt trước
   khi gửi đi.
2. **Given** ngôn ngữ đích trùng với ngôn ngữ nội dung đã có sẵn, **When**
   message được dựng, **Then** hệ thống không tạo bản dịch dư thừa và vẫn gửi
   đúng một message cho tin đó.
3. **Given** hệ thống tạm thời không tạo được bản dịch cho ngôn ngữ đã chọn,
   **When** delivery vẫn tiếp tục, **Then** batch không bị fail và log ghi rõ
   đã áp dụng fallback nào cho message đó.

---

### Edge Cases / Trường hợp biên

- Batch có nhiều tin mới nên số notification tăng theo số record.
- Batch chạy thành công nhưng `record_count = 0`.
- Chỉ Telegram hoặc chỉ webhook được bật.
- Một số tin trong batch gửi thành công, một số tin thất bại do sink timeout.
- Tin thiếu trường hiển thị như `title` hoặc `url` nên message phải fallback.
- Secret/token cấu hình thiếu hoặc sai nhưng scheduler vẫn phải tiếp tục chạy
  các vòng sau.
- Giá trị ngôn ngữ đích không hợp lệ hoặc không được hỗ trợ.
- Nội dung nguồn đã là tiếng Việt nhưng người vận hành vẫn chọn `vi-VN`.
- Cùng một batch bật cả Telegram và webhook, trong đó Telegram được localize
  còn webhook vẫn giữ payload canonical để tránh phá downstream contract.
- Dịch thất bại hoặc timeout nhưng Telegram vẫn phải áp dụng fallback đã định
  thay vì làm hỏng batch.

## Data Lineage & Operational Impact / Dòng dữ liệu và tác động vận hành *(bắt buộc với thay đổi liên quan pipeline, storage, scheduler hoặc API)*

- **Upstream Inputs**: Kết quả của một vòng `run_once()`, gồm metadata batch và
  danh sách các tin đã được xử lý/persist thành công trong batch đó.
- **Affected Pipeline Stages / APIs**: `src/opennews/workflow/langgraph_pipeline.py`,
  `src/opennews/scheduler/polling_job.py`, runtime config trong
  `src/opennews/config.py` và module notification mới chịu trách nhiệm phát event
  theo từng tin ra Telegram và/hoặc webhook, đồng thời derive phần nội dung đã
  localize cho sink human-facing khi có cấu hình ngôn ngữ đích.
- **Persisted Data Impact**: Không thay đổi schema PostgreSQL, Neo4j, Redis hay
  web API ở v1. Dữ liệu mới chỉ là outbound request, dữ liệu localize trong
  runtime và log vận hành.
- **Observability Plan**: Log theo từng tin và từng sink với tối thiểu
  `batch_id`, `batch_ts`, `news_id`, `sink_kind`, trạng thái delivery, số lần
  retry, destination đã được sanitize và khi có áp dụng ngôn ngữ đích thì thêm
  `requested_language`, `delivered_language`, trạng thái dịch hoặc fallback.
- **Replay / Rollback Plan**: Có thể replay bằng seed/staging endpoint để tạo
  lại các tin mẫu. Có thể rollback nhanh bằng feature flag tổng, tắt từng sink
  riêng lẻ hoặc đưa ngôn ngữ đích về chế độ mặc định/canonical mà không cần
  migration dữ liệu.

## Requirements / Yêu cầu *(bắt buộc)*

### Functional Requirements / Yêu cầu chức năng

- **FR-001**: Hệ thống MUST cung cấp feature flag để bật hoặc tắt toàn bộ per-news
  processing notification ở runtime.
- **FR-002**: Hệ thống MUST chỉ phát notification cho các tin đã được xử lý xong
  trong một batch thành công và đã persisted thành công.
- **FR-003**: Hệ thống MUST tạo một event chuẩn hóa cho từng tin, chứa tối thiểu
  `batch_id`, `batch_ts`, `news_id`, `title` hoặc nội dung thay thế, `source`,
  trạng thái xử lý và thời điểm phát thông báo.
- **FR-004**: Hệ thống MUST ưu tiên hỗ trợ Telegram như sink chính trong v1.
- **FR-005**: Hệ thống MUST xây dựng nội dung tin nhắn Telegram từ một template
  chuyên biệt thay vì hard-code trực tiếp trong luồng gửi.
- **FR-006**: Cấu trúc chi tiết của template Telegram MAY được quyết định ở giai
  đoạn triển khai, nhưng feature này MUST chừa rõ điểm mở để thay đổi template
  mà không phải đổi contract event nguồn.
- **FR-007**: Hệ thống MUST hỗ trợ webhook như một sink tùy chọn cho cùng event
  nghiệp vụ theo từng tin.
- **FR-008**: Hệ thống MUST cho phép bật đồng thời Telegram và webhook cho cùng
  một tin đã xử lý xong.
- **FR-009**: Hệ thống MUST gửi tối đa một notification cho mỗi sink trên mỗi
  tin trong cùng một lần xử lý batch, trừ khi retry policy yêu cầu thử lại.
- **FR-010**: Hệ thống MUST cô lập lỗi theo sink và theo tin; lỗi gửi của một
  sink hoặc một tin không được làm hỏng persistence, graph write hoặc vòng
  polling hiện tại.
- **FR-011**: Hệ thống MUST log được kết quả gửi notification theo từng tin và
  từng sink với metadata đủ để debug mà không lộ secret.
- **FR-012**: Hệ thống MUST định nghĩa timeout, retry và fallback rõ ràng cho
  outbound notification để tránh treo vòng scheduler khi batch có nhiều tin.
- **FR-013**: Hệ thống MUST cập nhật tài liệu cấu hình, kiểm thử và runbook khi
  thêm per-news notification.
- **FR-014**: Hệ thống MUST giữ nguyên contract hiện có của batch payload, DB
  schema, graph write và web API trừ khi có thay đổi được nêu rõ trong feature
  này.
- **FR-015**: Hệ thống MUST cho phép chọn ngôn ngữ đích cho nội dung
  notification human-facing bằng một language tag chuẩn hóa, ví dụ `vi-VN`.
- **FR-016**: Khi Telegram có cấu hình ngôn ngữ đích và nội dung người đọc của
  tin chưa ở ngôn ngữ đó, hệ thống MUST chuyển ngữ các trường human-readable
  cần thiết trước khi render Telegram template.
- **FR-017**: Hệ thống MUST giữ nguyên các định danh và dữ liệu canonical của
  event nguồn; bản localize chỉ là dữ liệu dẫn xuất dùng cho delivery, không
  thay thế record gốc đã persisted.
- **FR-018**: Hệ thống MUST tránh dịch lặp khi nội dung đã sẵn ở ngôn ngữ đích
  hoặc đã có dữ liệu localize phù hợp.
- **FR-019**: Nếu bước localize hoặc dịch thất bại, hệ thống MUST không làm hỏng
  pipeline chính; hệ thống MUST áp dụng fallback đã định và log đủ ngữ cảnh để
  chẩn đoán.
- **FR-020**: Trong phạm vi hiện tại, hỗ trợ ngôn ngữ đích MUST ưu tiên Telegram;
  webhook MAY tiếp tục phát payload canonical để giữ ổn định cho downstream
  consumer.
- **FR-021**: Hệ thống MUST cập nhật tài liệu feature và test coverage khi thêm
  lựa chọn ngôn ngữ gửi notification.
- **FR-022**: Hệ thống MUST tái sử dụng cùng runtime cấu hình LLM hiện có của
  OpenNews cho bước translation/localization thay vì đưa thêm một translator
  stack riêng trong phạm vi hiện tại.

### Key Entities / Thực thể chính *(thêm nếu tính năng có liên quan dữ liệu)*

- **NewsProcessedEvent**: Bản tóm tắt nghiệp vụ cho một tin đã được xử lý xong
  trong một batch và đủ điều kiện phát ra ngoài.
- **Notification Sink**: Một đích nhận thông báo độc lập như Telegram hoặc
  webhook, có trạng thái bật/tắt và thông tin cấu hình riêng.
- **Delivery Attempt**: Kết quả của một lần gửi một `NewsProcessedEvent` tới một
  sink cụ thể.
- **Notification Language Preference**: Cấu hình chọn ngôn ngữ đích cho nội dung
  human-facing của một sink, ví dụ `vi-VN`.
- **Localized Notification Content**: Bộ dữ liệu hiển thị đã được chuyển ngữ từ
  event canonical để render message Telegram theo ngôn ngữ người vận hành.

## Success Criteria / Tiêu chí thành công *(bắt buộc)*

### Measurable Outcomes / Kết quả đo được

- **SC-001**: Khi Telegram sink được bật và batch có record mới, mỗi record mới
  tạo ra đúng một tin nhắn Telegram trong vòng 60 giây sau khi batch được ghi
  xong.
- **SC-002**: Khi webhook sink được bật, mỗi record mới tạo ra đúng một webhook
  payload có thể đối chiếu với batch và tin tương ứng.
- **SC-003**: Trong kịch bản một sink lỗi, vòng pipeline vẫn hoàn tất và dữ liệu
  của toàn bộ batch vẫn truy xuất được từ PostgreSQL/Neo4j ở 100% lần kiểm thử.
- **SC-004**: Người vận hành có thể xác định đúng tin và batch liên quan chỉ từ
  nội dung notification và log tương ứng trong một lần đối chiếu.
- **SC-005**: Khi feature flag tắt, hệ thống không phát sinh outbound
  notification nào trong suốt vòng pipeline.
- **SC-006**: Khi Telegram được cấu hình ngôn ngữ đích `vi-VN` và batch chứa tin
  có nội dung nguồn ở ngôn ngữ khác, 100% Telegram notification thành công trong
  bộ kiểm thử chấp nhận phải hiển thị phần nội dung người đọc bằng tiếng Việt.
- **SC-007**: Trong kịch bản localize lỗi, 100% lần kiểm thử vẫn hoàn tất batch
  thành công và tạo được log cho từng attempt nêu rõ ngôn ngữ đã yêu cầu và
  fallback đã áp dụng.

## Assumptions / Giả định

- V1 gửi notification cho mọi tin mới đã được xử lý thành công trong batch, chưa
  có rule lọc theo score, source hay topic.
- Telegram là kênh ưu tiên về trải nghiệm và kiểm thử, nên nội dung message cho
  Telegram được tối ưu trước webhook.
- Template Telegram sẽ được quyết định khi đi vào phát triển; hiện tại feature
  chỉ chốt rằng message phải đi qua cơ chế template hóa.
- V1 không lưu lịch sử delivery vào DB; log runtime là nguồn quan sát chính.
- Secret và token sẽ được cấp qua biến môi trường hoặc config runtime hiện có,
  không commit vào repository.
- Nếu một tin thiếu một số trường hiển thị, hệ thống sẽ dùng fallback an toàn
  thay vì bỏ cả batch.
- Phạm vi hiện tại ưu tiên localize cho Telegram trước; webhook vẫn giữ
  payload canonical trừ khi có spec mở rộng riêng cho downstream consumer.
- Giá trị ngôn ngữ đích dùng dạng language tag chuẩn hóa như `vi-VN`.
- Fallback mặc định khi không tạo được bản dịch là tiếp tục gửi nội dung
  canonical để người vận hành vẫn nhận được tín hiệu xử lý xong.
- Translation dùng cùng provider/model/runtime config với phần LLM hiện có của
  project; chỉ prompt và dữ liệu đầu vào là khác theo use case dịch.
