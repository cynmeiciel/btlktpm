# IADR-005 — Ngữ nghĩa lô: mỗi event một transaction, API trả kết quả từng item

Trạng thái: Proposed

## Bối cảnh
Sync Worker gửi lô (Hình 4 M1). Trong một lô có thể lẫn event hợp lệ, event gửi lại, event xung đột, event hỏng định dạng. ADR04: ACK chỉ sau commit; gửi lại phải an toàn.

## Quyết định
1. Mỗi event xử lý trong **một transaction riêng**.
2. Envelope sai → lỗi cho cả request (4xx). Item sai → chỉ item đó `REJECTED`.
3. Request được xử lý → luôn HTTP 200 với `results[]` cùng thứ tự input và `summary`.
4. Lỗi hạ tầng giữa lô → 503; các event trước đó vẫn đã commit; trạm gửi lại cả lô, chúng thành `DUPLICATE`.

## Phương án đã cân nhắc
- **Cả lô một transaction** — "tất cả hoặc không"; một event hỏng chặn cả lô; trạm phải tự tách lô để tìm thủ phạm. Không có lợi ích nghiệp vụ vì các event độc lập nhau.
- **207 Multi-Status** — đúng ngữ nghĩa WebDAV hơn nhưng nhiều client HTTP xử lý kém; 200 + kết quả từng item phổ biến và rõ ràng hơn.
- **Savepoint trong một transaction** — giữ được per-item nhưng lô dài giữ khoá lâu; không cần.

## Hệ quả
- (+) Một event hỏng không chặn dữ liệu khác (NFR-2).
- (+) Gửi lại sau lỗi luôn an toàn nhờ dedupe.
- (−) Lô 500 event = 500 transaction. Ở tải này không đáng kể; ghi lại để biết.
- (−) Client phải đọc `results`, không chỉ đọc HTTP status. Ghi rõ trong hợp đồng (`03-api-contract.md` §2).

## Liên quan
ADR04, NFR-2.
