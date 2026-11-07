# IADR-006 — Tolerant reader cho request HTTP

Trạng thái: Proposed

## Bối cảnh
Tài liệu cũ vừa nói "envelope parse chặt" (`03-api-contract.md` §2) vừa quy định mọi model HTTP dùng `extra="ignore"` (`07-conventions.md` §4), khiến không rõ trường lạ ở envelope bị bỏ qua hay trả 422.

Gate Agent chạy tại nhiều trạm ở hai nhà máy và được nâng cấp lệch thời điểm. Sync Worker gửi lại cả lô khi gặp lỗi (Hình 5 M1). Nếu S3 trả 422 cho cả lô chỉ vì một trường lạ, hàng đợi store-and-forward của trạm đó sẽ kẹt đến khi S3 được nâng cấp. Kiểu lỗi này đúng là loại NFR-2 (không mất dữ liệu chấm công) muốn tránh.

## Quyết định
1. Mọi model request Pydantic dùng `extra="ignore"`, ở cả envelope (`BatchIn`) lẫn item (`EventIn`). Không dùng `extra="forbid"`.
2. "Parse chặt" ở envelope chỉ có nghĩa là: thiếu trường bắt buộc, sai kiểu, hoặc số phần tử `events` nằm ngoài khoảng 1…`TMC_S3_MAX_BATCH_SIZE` thì trả 422 cho cả request.
3. Item sai trường bắt buộc hoặc sai kiểu thì chỉ item đó bị `REJECTED/INVALID_FORMAT` (IADR-005).
4. Thay đổi phá tương thích đi qua `schemaVersion` (item) hoặc `/v2` (API), không bao giờ qua "trường lạ".

## Phương án đã cân nhắc
- **`extra="forbid"` ở envelope, `ignore` ở item**: bắt được lỗi gõ tên trường ở client. Đổi lại, nâng cấp trạm phải đồng bộ với S3, trái với việc triển khai độc lập (ADR02). Lỗi gõ tên trường bắt buộc vốn đã ra 422 vì "thiếu trường", nên lợi ích còn lại rất nhỏ.
- **`extra="forbid"` ở cả hai tầng**: kẹt nặng nhất khi trạm đi trước S3.

## Hệ quả
- (+) Trạm và S3 nâng cấp độc lập. Khả năng tiến hoá (evolvability) có thể trích vào báo cáo.
- (+) Không ảnh hưởng dedupe, vì `payload_hash` chỉ tính trên 9 trường chuẩn (`02-domain-model.md` §4).
- (−) Lỗi gõ tên một trường **tuỳ chọn** sẽ bị bỏ qua mà không báo. Hiện tại API không có trường tuỳ chọn nào nên chưa thành vấn đề. Khi thêm trường tuỳ chọn thì cân nhắc lại.
- Test (API): một item có trường lạ vẫn `ACCEPTED`; một envelope có trường lạ vẫn 200. Đã ghi trong `05-testing-strategy.md` §3.

## Liên quan
ADR02, ADR04, NFR-2, IADR-005, `03-api-contract.md` §2, `07-conventions.md` §4.
