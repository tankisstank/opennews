<!--
Báo cáo đồng bộ
- Thay đổi phiên bản: template -> 1.0.0
- Các nguyên tắc đã cập nhật:
  - Vị trí nguyên tắc mẫu 1 -> I. Ưu tiên tính toàn vẹn dữ liệu tài chính
  - Vị trí nguyên tắc mẫu 2 -> II. Hợp đồng ổn định xuyên suốt pipeline
  - Vị trí nguyên tắc mẫu 3 -> III. Vận hành có thể quan sát và phát lại
  - Vị trí nguyên tắc mẫu 4 -> IV. Mọi thay đổi hành vi đều phải được kiểm chứng
  - Vị trí nguyên tắc mẫu 5 -> V. Khả năng vận hành là mặc định
- Các mục đã thêm:
  - Ràng buộc kỹ thuật
  - Quy trình triển khai
- Các mục đã bỏ:
  - Không có
- Template cần cập nhật:
  - .specify/templates/plan-template.md: đã cập nhật
  - .specify/templates/spec-template.md: đã cập nhật
  - .specify/templates/tasks-template.md: đã cập nhật
  - .specify/templates/agent-file-template.md: đã cập nhật
  - .specify/templates/checklist-template.md: đã cập nhật
  - .specify/templates/constitution-template.md: đã cập nhật
  - .specify/templates/commands/: chưa có trong repository này
- TODO theo dõi thêm:
  - Không có
-->
# Hiến pháp OpenNews

## Nguyên tắc cốt lõi

### I. Ưu tiên tính toàn vẹn dữ liệu tài chính
Mọi thay đổi tác động đến ingest, enrich, chấm điểm, ghi đồ thị hoặc phản hồi
API BẮT BUỘC phải mô tả rõ giả định nguồn dữ liệu, ngữ nghĩa trường dữ liệu và
hành vi khi lỗi trước khi triển khai. Bản ghi, điểm số, nhãn chủ đề và quan hệ
đồ thị PHẢI truy vết được về batch identifier, timestamp và source identifier từ
upstream. Lý do: OpenNews chỉ hữu ích khi người vận hành và người dùng có thể
giải thích đầu ra đến từ đâu và vì sao nó được tạo ra.

### II. Hợp đồng ổn định xuyên suốt pipeline
Mỗi ranh giới giữa các stage của pipeline, scheduler, storage layer, cache
layer và HTTP endpoint PHẢI có hợp đồng đầu vào và đầu ra rõ ràng. Mọi thay đổi
hợp đồng PHẢI cập nhật schema, config, fixture, tài liệu và downstream consumer
liên quan trong cùng một thay đổi. Thay đổi phá vỡ tương thích PHẢI có kế hoạch
migration, replay hoặc backfill trước khi merge. Lý do: OpenNews trải dài qua
workflow Python, tầng lưu trữ và giao diện web, nên contract drift dễ gây lỗi
âm thầm và làm sai lệch dữ liệu.

### III. Vận hành có thể quan sát và phát lại
Các batch xử lý, scheduled job và luồng render share PHẢI có thể debug qua
structured log và ngữ cảnh thực thi định danh được như batch ID, source, time
window hoặc request parameter. Mọi thay đổi PHẢI giữ được khả năng replay batch
hoặc request với cùng config và model metadata cần thiết để giải thích kết quả.
Lỗi PHẢI được bộc lộ thành thông báo hành động được, không được thất bại một
phần theo kiểu im lặng. Lý do: dự án xử lý dữ liệu tài chính nhạy thời gian, nên
khả năng debug và khôi phục phải được thiết kế sẵn.

### IV. Mọi thay đổi hành vi đều phải được kiểm chứng
Mọi thay đổi làm khác hành vi hệ thống PHẢI có xác minh tự động ở mức hẹp nhất
đủ để chứng minh tính đúng: unit test cho biến đổi thuần, integration test cho
workflow và persistence path, contract test cho API hoặc thay đổi đầu ra share.
Hành vi có dùng model PHẢI kiểm chứng bằng fixture ổn định, tolerance hoặc
golden input thay vì chỉ kiểm tra thủ công. Nếu chưa tự động hóa được, thay đổi
PHẢI nêu rõ lý do và mô tả quy trình kiểm tra thủ công có thể lặp lại. Lý do:
pipeline phân tích nhiều bước không thể dựa vào quan sát cảm tính.

### V. Khả năng vận hành là mặc định
Nhóm phát triển PHẢI ưu tiên stack và luồng hiện có gồm Python, LangGraph, Vue,
PostgreSQL, Neo4j, Redis cùng các cách chạy Docker/local đã được tài liệu hóa
trước khi thêm framework, service hoặc model mới. Bất kỳ dependency hay thành
phần hạ tầng mới nào PHẢI giải thích được chi phí vận hành, tác động tới local
setup và phương án rollback. Luồng phát triển cục bộ và các bước khởi động đã
ghi trong tài liệu PHẢI tiếp tục dùng được sau mỗi thay đổi. Lý do: hệ thống đã
có độ rộng vận hành lớn, nên độ phức tạp không cần thiết sẽ làm chậm tiến độ và
làm sự cố khó xử lý hơn.

## Ràng buộc kỹ thuật

- Stack mặc định là Python 3.10+ cho backend và pipeline, Vue/Vite cho web
  client, PostgreSQL và Neo4j cho dữ liệu lưu trữ, Redis cho bộ nhớ thời gian và
  điều phối cache.
- Cấu hình PHẢI đi qua file config đã commit và biến môi trường. Secret KHÔNG
  được commit. Giá trị mẫu cục bộ chỉ được phép xuất hiện trong tài liệu setup
  không phục vụ môi trường production.
- Mọi thay đổi với persisted schema, graph structure, cache key hoặc batch
  payload PHẢI có xử lý migration, cleanup hoặc tương thích trong cùng phạm vi
  công việc.
- Tính năng phụ thuộc model inference, translation hoặc nguồn tin bên ngoài
  PHẢI định nghĩa rõ timeout, retry và fallback behavior.
- Artifact sinh ra và cache PHẢI dùng vị trí thư mục đã được tài liệu hóa để
  thao tác cleanup, replay và deploy luôn dự đoán được.

## Quy trình triển khai

1. Mỗi feature spec PHẢI nêu rõ giá trị người dùng, pipeline stage hoặc API bị
   ảnh hưởng, thực thể dữ liệu liên quan và kế hoạch observability cùng
   verification.
2. Mỗi implementation plan PHẢI vượt qua constitution check gồm data lineage,
   contract update, chiến lược replay hoặc backfill và tính đơn giản trong vận
   hành trước khi đi vào thiết kế.
3. Danh sách task PHẢI bao gồm phần việc về tài liệu, schema, config,
   observability và kiểm chứng tự động phù hợp với bề mặt thay đổi.
4. Việc triển khai NÊN đi theo từng lát cắt độc lập và kiểm chứng được theo user
   story để pipeline và web app luôn ở trạng thái có thể phát hành.
5. Review PHẢI xác nhận quickstart, runbook hoặc tài liệu cho người vận hành đã
   được cập nhật bất cứ khi nào luồng khởi động, cấu hình hoặc hành vi runtime
   thay đổi.

## Quản trị

Hiến pháp này có hiệu lực cao hơn các thói quen cục bộ hoặc shortcut riêng của
từng tính năng. Mọi sửa đổi hiến pháp cần đi kèm pull request cập nhật chính tài
liệu này cùng các template, tài liệu hoặc file hướng dẫn liên quan trong cùng
một thay đổi.

Chính sách phiên bản của hiến pháp dùng semantic versioning:

- MAJOR: xóa, định nghĩa lại nguyên tắc hoặc thay đổi quản trị làm đổi kỳ vọng
  tuân thủ trước đó.
- MINOR: thêm nguyên tắc mới hoặc mở rộng đáng kể hướng dẫn làm phát sinh nghĩa
  vụ mới.
- PATCH: làm rõ câu chữ, cải thiện diễn đạt hoặc chỉnh sửa không đổi nghĩa.

Việc rà soát tuân thủ là bắt buộc khi lập plan và lặp lại trong quá trình review
triển khai. Mỗi feature plan và pull request PHẢI nêu được cách nó đáp ứng năm
nguyên tắc cốt lõi, hoặc nếu cần ngoại lệ tạm thời thì phải nêu owner, phạm vi
và kế hoạch gỡ bỏ ngoại lệ đó.

**Version**: 1.0.0 | **Ratified**: 2026-04-02 | **Last Amended**: 2026-04-02
