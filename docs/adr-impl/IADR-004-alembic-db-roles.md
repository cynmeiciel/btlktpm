# IADR-004 — Alembic và tách role PostgreSQL

Trạng thái: Proposed

## Bối cảnh
ADR02: một PostgreSQL, mỗi service một schema, "mỗi service là thành phần duy nhất được cấp quyền ghi vào schema của chính nó". ADR07: least privilege. ADR08: event gốc bất biến. Báo cáo M1 4.4 lý do 4: "đặc quyền tối thiểu được cơ sở dữ liệu thực thi ... là ràng buộc kỹ thuật, không phải quy ước".

## Quyết định
- Ba role: `s3_attendance_owner` (DDL, migration), `s3_attendance_app` (runtime), `s4_reporting_reader` (chỉ view).
- Role và schema tạo bằng script hạ tầng (`infra/postgres/init/01-roles.sql`); bảng, view, GRANT tạo bằng Alembic dưới role owner.
- Role app chỉ có `SELECT, INSERT` trên `attendance_event` — không `UPDATE`, không `DELETE`.
- Migration viết tay; autogenerate chỉ dùng cho `alembic check`.
- `alembic_version` nằm trong schema `attendance`.

## Phương án đã cân nhắc
- Một role cho mọi thứ — đơn giản, nhưng bất biến ADR08 khi đó chỉ dựa vào code.
- Trigger chặn UPDATE/DELETE — được, nhưng owner vẫn tắt được trigger; grant rõ ràng và dễ test hơn. Có thể thêm sau.
- Tạo role trong migration — role là đối tượng cấp cluster, nhiều service dùng chung cluster; migration của một service không nên tạo/xoá role.

## Hệ quả
- (+) Test quyền DB chứng minh ADR07/ADR08 ở mức DB.
- (+) S4 tương lai chỉ thấy view `v1` (ADR02).
- (−) Cần hai URL kết nối (app, migration) và ba trong test.
- (−) Môi trường mới phải chạy script role trước migration (CI có bước riêng).

## Liên quan
ADR02, ADR07, ADR08.
