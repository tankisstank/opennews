# Quickstart: Per-News Processing Notifications

## Mục tiêu

Xác minh notification theo từng tin hoạt động đúng mà không làm hỏng đường chạy
pipeline chính, đồng thời chuẩn bị đường kiểm thử cho increment chọn ngôn ngữ
gửi Telegram.

## Chuẩn bị

1. Chuẩn bị một nguồn dữ liệu thử để batch chắc chắn tạo ra nhiều hơn một record
   mới.
2. Chuẩn bị sink thử:
   - Telegram bot/chat thử nghiệm
   - Webhook receiver cục bộ hoặc staging endpoint nếu cần
3. Cấu hình runtime để bật feature và sink cần kiểm thử.

## Kịch bản 1: Telegram happy path

1. Bật per-news notification và cấu hình Telegram sink.
2. Chạy một vòng pipeline có ít nhất hai record mới.
3. Xác nhận Telegram nhận một tin nhắn cho mỗi record mới.
4. Đối chiếu `batch_id`, `news_id` và tiêu đề giữa tin nhắn, DB và log.

## Kịch bản 2: Webhook happy path

1. Bật webhook sink.
2. Chạy một vòng pipeline có record mới.
3. Xác nhận receiver nhận đúng một request cho mỗi record mới.
4. Đối chiếu `batch_id`, `news_id`, `title` giữa payload và DB/log.

## Kịch bản 3: Multi-sink path

1. Bật cả Telegram và webhook.
2. Chạy một vòng pipeline có record mới.
3. Xác nhận cùng một tin tạo ra một Telegram message và một webhook payload.

## Kịch bản 4: Sink failure isolation

1. Trỏ webhook tới endpoint cố ý trả lỗi hoặc timeout.
2. Giữ Telegram sink hợp lệ.
3. Chạy một vòng pipeline có nhiều record mới.
4. Xác nhận batch vẫn được ghi vào PostgreSQL và, nếu khả dụng, graph vẫn được
   cập nhật.
5. Xác nhận Telegram vẫn nhận message còn log nêu rõ webhook thất bại cho tin nào.
6. Nếu `NOTIFICATION_MAX_ATTEMPTS=2`, xác nhận mỗi tin lỗi có tối đa hai lần thử
   gửi cho sink hỏng trước khi dừng retry.

## Kịch bản 5: Feature flag off

1. Tắt per-news notification.
2. Chạy một vòng pipeline có dữ liệu mới.
3. Xác nhận không có outbound request hay Telegram message nào được gửi.
4. Xác nhận log có `notification dispatch skipped` với reason phù hợp.

## Kịch bản 6: Telegram với ngôn ngữ đích `vi-VN`

1. Bật Telegram sink và cấu hình ngôn ngữ đích là `vi-VN`.
   Ví dụ: `TELEGRAM_PREFERRED_LANGUAGE=vi-VN`.
2. Chạy một vòng pipeline với ít nhất một tin có nội dung nguồn không phải tiếng
   Việt.
3. Xác nhận Telegram nhận đúng một message cho mỗi record mới.
4. Xác nhận phần nội dung người đọc trong message hiển thị bằng tiếng Việt, còn
   `batch_id`, `news_id` và link vẫn đối chiếu được với dữ liệu gốc.

## Kịch bản 7: Fallback khi localize lỗi

1. Giữ Telegram sink hợp lệ nhưng mô phỏng localize timeout hoặc lỗi dịch.
   Ví dụ: unset `LLM_API_KEY` hoặc trỏ translator tới backend lỗi trong môi
   trường thử nghiệm.
2. Chạy một vòng pipeline có record mới.
3. Xác nhận batch vẫn hoàn tất.
4. Xác nhận Telegram vẫn áp dụng delivery theo fallback policy đã định hoặc log
   chỉ rõ vì sao không localize được.
5. Xác nhận log có requested language, delivered language và translation status
   cho từng attempt liên quan.

## Dấu hiệu pass

- Mỗi tin mới đã processed thành công tạo ra đúng một notification trên mỗi sink
  đang bật.
- Mỗi sink được cấu hình nhận hoặc fail độc lập.
- Khi chọn `vi-VN`, Telegram hiển thị nội dung human-readable bằng tiếng Việt ở
  các mẫu kiểm thử chấp nhận.
- Không có thay đổi bất ngờ ở DB schema, web API hay share API.
