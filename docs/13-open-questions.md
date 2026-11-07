# 13 — Câu hỏi mở và giả định

Bộ tài liệu này đã chọn sẵn một phương án cho mỗi điểm dưới đây để code không bị chặn. Nhóm xác nhận hoặc đổi; đổi thì cập nhật file đặc tả tương ứng **trước** khi code.

## A. Giả định cần nhóm xác nhận

| # | Câu hỏi | Đang giả định | Ảnh hưởng nếu đổi | File |
|---|---|---|---|---|
| Q1 | Giá trị của `EvidenceLevel`? Báo cáo M1 có tên trường nhưng không liệt kê giá trị | `CONTROLLER_CONFIRMED`, `CONTROLLER_UNCONFIRMED`, `GUARD_RECORDED` | CHECK constraint, enum, hash golden value | `02` §1, `04` §2 |
| Q2 | Định dạng `stationId`? | chuỗi 1–64 ký tự `[A-Za-z0-9_-]`, ví dụ `BD-G01-IN` | regex, cột `varchar(64)` | `02` §2 |
| Q3 | Ngưỡng lệch đồng hồ cho phép? M1 chỉ nói "giới hạn độ lệch đồng hồ được chốt cùng chính sách QR" | 300 giây, chỉ chặn tương lai | config | `02` §6 |
| Q4 | Giám sát sản xuất có đọc lịch sử nhân viên trong phân xưởng không? Cần dữ liệu tổ chức S3 không có | Không, trong M2 | thêm role + nguồn dữ liệu phân xưởng | `02` §7 |
| Q5 | Kích thước lô tối đa? | 500 event, 1 MiB | config | `03` §2 |
| Q6 | Xác thực trạm? M1 ADR07 nói "xác thực gate device độc lập" | token tĩnh, lưu sha256 trong config | thay adapter `StationAuthenticator` | `03` §2, `00` §6 |
| Q7 | Có làm outbox relay không? | Không bắt buộc (T7.2); outbox chỉ được ghi | — | `09` |
| Q8 | Hạn nộp M2 và mốc trung gian? | chưa biết | lịch backlog | `09` |
| Q9 | Tên GitHub org/repo? (thành viên gọi TV1–TV5, không dùng CODEOWNERS — đã chốt) | chưa biết | badge README, URL ghi vào báo cáo | `06` §4–5 |
| Q10 | Repo public hay private? Giảng viên cần truy cập thế nào? | private + mời giảng viên/đặt public lúc nộp | quyền xem repo của giảng viên | `06` §4 |

## B. Điểm lệch trong báo cáo M1 nên sửa khi "finalize" ở M2

Đề M2 ghi M2 là "finalizing the software design", nên đây là lúc sửa. Không ảnh hưởng code S3, nhưng giảng viên đọc cả hai.

| # | Chỗ | Vấn đề | Đề xuất |
|---|---|---|---|
| B1 | 8.2.3 (DP02) và 8.5.3 (DP05) | Ghi S2 Gate Management "đánh giá access policy và điều phối lệnh điều khiển cổng" / "xử lý quyết định truy cập và điều khiển cổng". Chương 5 (Bước 3, bảng FR) lại giao quyết định và điều khiển cổng cho **Gate Agent**; S2 chỉ quản lý trạm, thiết bị, policy | Sửa DP02/DP05: S2 "quản lý trạm, thiết bị và phát hành policy"; Gate Agent "áp policy và điều khiển cổng tại trạm" |
| B2 | 8.9.3 (DP09) | "Gate Management phụ thuộc vào TurnstilePort" — `TurnstilePort` nằm ở Gate Agent (ADR05 ghi đúng "Tại gate station, TurnstilePort…") | Đổi chủ ngữ thành Gate Agent |
| B3 | 4.1 | "bốn đặc tính P1 đã xác định ở mục 2.1" — đặc tính nằm ở chương 3 (3.2) | Sửa tham chiếu thành mục 3.2 |
| B4 | Mục lục chương 7 | `ADR8`, `ADR9` lệch định dạng với `ADR01`–`ADR07` | `ADR08`, `ADR09` |
| B5 | 3.2.1 | "Thời gian phản hồi … (Latency) 2 giây" thiếu "≤" | "≤ 2 giây" |
| B6 | Hình 7 | Thiếu `UnitOfWork`, `AttendanceReader`, `StationAuthenticator`, batch use case | Cập nhật theo `01-kien-truc-s3.md` §6 (T8.1) |
| B7 | ERD Hình 2 | `AttendanceEvent` chưa có `schema_version`, `payload_hash`; chưa có `event_conflict` | Bổ sung, hoặc ghi chú "chi tiết lưu trữ của S3 xem mục Task 2" |
| B8 | Chương 3 vs đề M2 | Đề M2 Task 1.2 yêu cầu ba loại view; báo cáo M1 chưa có mục này | Thêm mục, xem `12-report-mapping.md` §2 |

## C. Quyết định đã chốt trong bộ tài liệu này (không cần hỏi lại trừ khi có lý do)

| Quyết định | Ở đâu |
|---|---|
| Monorepo | IADR-001 |
| FastAPI endpoint đồng bộ + SQLAlchemy Core + psycopg 3 | IADR-002 |
| uv, ruff, mypy (strict cho `src/`, nới cho `tests/`), import-linter | IADR-003 |
| Alembic, role DB tách owner/app/reader, grant chặn UPDATE/DELETE | IADR-004 |
| Mỗi event một transaction trong lô; API luôn 200 kèm kết quả từng item | IADR-005 |
| Port là `abc.ABC`, test dùng fake + contract test, không mock | `07`, `05` |
| `text + CHECK` thay cho PostgreSQL ENUM; không FK chéo schema | `04` §2 |
| Request HTTP theo tolerant reader: trường lạ ở envelope và item đều bỏ qua; "envelope chặt" = thiếu trường/sai kiểu/sai kích thước lô → 422 | IADR-006, `03` §2, `07` §4 |
| Cấu hình đọc qua `Settings` và `DatabaseAdminSettings` (`bootstrap/config.py`); test dùng lại `DatabaseAdminSettings`; chỉ cờ `TMC_REQUIRE_DB` trong `conftest.py` đọc `os.environ` | `07` §4, `05` §1, `services/s3-attendance/README.md` |
| `.gitignore`, `.gitattributes` (LF), `.pre-commit-config.yaml` ở gốc repo; `.env.example`, `scripts/dev.py` (thay `Makefile`, chạy được trên Windows) trong `services/s3-attendance/` | `07` §9, `10` |
| Thành viên gọi TV1–TV5 (TV1 = tech lead); không dùng CODEOWNERS | `08` §1 |
| Nhóm dùng Windows và Arch Linux; Docker là cách chung để chạy Postgres và app; image Docker là bắt buộc (T6.2) | `10` |
| Phạm vi tinh gọn: task chia mức Bắt buộc/Tuỳ chọn; test không đánh mã; lỗi HTTP theo định dạng mặc định FastAPI (chỉ thay handler 422); log bằng `logging` stdlib; lịch sử phân trang `LIMIT`/`OFFSET`; không kiểm trùng `(stationId, localSequence)` | `09`, `05` §3, `03` §5, `07` §6, `04` §8, `02` §9 |
| CI chỉ chạy test tự động (một job `test`: lint-imports + pytest có Postgres); không build/publish image, không release tự động; ruff/mypy chạy local | `06` |
