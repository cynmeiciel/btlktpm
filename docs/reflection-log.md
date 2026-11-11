# Nhật ký reflection

Nguyên liệu cho Task 1.4 (Reflection Report: SOLID giúp cải thiện thiết kế thế nào, khó khăn, vì sao hệ thống modular/maintainable/extensible hơn). Ghi trong lúc làm, ngắn, cụ thể. Một mục chỉ cần 2–4 dòng. Không ghi lại cho đẹp — giảng viên đánh giá được độ thật.

## Mẫu

```
### YYYY-MM-DD — <tên> — T?.?
Tình huống: <đang làm gì, gặp gì>
Nguyên tắc liên quan: <SRP / OCP / LSP / ISP / DIP / ADR..>
Cách xử lý: <quyết định gì>
Bài học: <một câu>
```

## Gợi ý những thứ đáng ghi

- Lần đầu import-linter chặn một import "tiện tay" — sửa thế nào.
- Fake và Postgres cư xử khác nhau, contract test bắt được (LSP).
- Phải thêm port `UnitOfWork` mà Hình 7 chưa có — vì sao.
- Viết test use case không cần DB nhờ DIP — tiết kiệm bao nhiêu thời gian.
- Chỗ áp SOLID quá tay (interface không cần thiết) và đã gỡ.
- Thay đổi yêu cầu giữa chừng (ví dụ Q1 `EvidenceLevel`) — bao nhiêu file phải sửa.

## Mục ghi

<!-- Thêm mục mới ở dưới cùng -->

### 2026-11-09 — TV2 — T2.2

Tình huống: Khi viết fake persistence, tôi cần bảo đảm event và outbox chưa commit không xuất hiện trong dữ liệu mà reader có thể đọc; lỗi outbox cũng không được để lại event riêng lẻ.

Nguyên tắc liên quan: LSP, DIP.

Cách xử lý: Tôi tách committed store khỏi buffer của từng UnitOfWork, chỉ chuyển dữ liệu khi commit thành công và bỏ buffer khi rollback. Tôi bổ sung test cho lỗi commit/outbox và chạy bộ AttendanceWriterContract với fake; phần chạy cùng contract trên PostgreSQL adapter cần TV3 hoàn thiện.

Bài học: Kế thừa đúng interface chưa đủ để bảo đảm khả năng thay thế. Fake cần giữ đúng ý nghĩa của commit và rollback thì kết quả unit test mới đáng tin cậy.

### 2026-11-09 — TV2 — T2.3 và T2.4

Tình huống: Khi hiện thực ingest, tôi cần kiểm tra lỗi giữa batch: event trước đã commit phải được giữ lại, event đang lỗi phải rollback và việc gửi lại cả lô không được tạo thêm bản ghi trùng.

Nguyên tắc liên quan: SRP, DIP.

Cách xử lý: Tôi tách use case một event khỏi use case batch, truyền Clock, IdGenerator và UnitOfWorkFactory qua constructor. Tôi dùng fake gây lỗi commit ở transaction thứ hai để kiểm tra exception truyền lên, dữ liệu đã commit còn nguyên và lần gửi lại trả DUPLICATE cho event đã nhận.

Bài học: Tách điều phối batch khỏi xử lý từng event giúp giữ rõ ranh giới transaction. Phụ thuộc vào port giúp kiểm thử tình huống lỗi bằng thời gian và ID tất định mà không cần thay đổi logic nghiệp vụ.
