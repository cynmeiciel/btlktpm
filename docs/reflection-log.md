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
