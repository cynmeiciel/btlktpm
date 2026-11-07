# 03 — Từ điển thuật ngữ

Xếp theo nhóm. Mỗi mục: nghĩa ngắn, rồi chỗ nó xuất hiện trong dự án.

## Nghiệp vụ

| Thuật ngữ | Nghĩa |
|---|---|
| **Gate Agent** | Máy tính đặt tại cổng: đọc QR, mở cửa, ghi sự kiện. Không code trong M2 |
| **Sync Worker** | Tiến trình trong Gate Agent, gửi lô sự kiện lên S3 và gửi lại khi lỗi. M2 giả lập bằng test, `curl`, `scripts/simulate_station.py` |
| **Attendance event** (sự kiện chấm công) | Một lần đi qua cổng: ai, vào/ra, lúc nào, cổng nào. Entity `AttendanceEvent` |
| **`eventId`** | Mã duy nhất của sự kiện, do trạm sinh, giữ nguyên khi gửi lại |
| **`attemptId`** | Mã của lần quét QR (một lần quét có thể sinh nhiều lần thử) |
| **`employeeRef`** | UUID đại diện nhân viên, không chứa tên hay thông tin cá nhân (giả danh, pseudonymous) |
| **`stationId`** | Mã cổng, ví dụ `BD-G01-IN` (Bình Dương, cổng 01, chiều vào) |
| **`localSequence`** | Số thứ tự tăng dần do trạm đánh. S3 lưu lại để điều tra, M2 không kiểm trùng |
| **`evidenceLevel`** | Mức bằng chứng: cửa xác nhận mở (`CONTROLLER_CONFIRMED`), không rõ (`CONTROLLER_UNCONFIRMED`), bảo vệ ghi tay (`GUARD_RECORDED`) |
| **Lô** (batch) | Nhiều sự kiện gửi trong một request, tối đa 500 |
| **ACCEPTED / DUPLICATE / CONFLICT / REJECTED** | Bốn kết quả của mỗi sự kiện: lưu mới / đã có y hệt / trùng mã nhưng khác nội dung / không hợp lệ |
| **Clock skew** (lệch giờ) | Đồng hồ trạm chạy sai. Sự kiện "ở tương lai" quá 300 giây thì bị từ chối |

## Kiến trúc

| Thuật ngữ | Nghĩa |
|---|---|
| **Service-Based Architecture** | Kiểu kiến trúc chọn ở M1: vài service lớn (S1–S4) dùng chung một DB, chia schema theo service |
| **S1, S2, S3, S4** | Identity & QR / Gate Management / **Attendance (nhóm code)** / Reporting & HR Sync |
| **Ports & Adapters** (Hexagonal) | Cách tổ chức code bên trong S3: lõi nghiệp vụ ở giữa, giao tiếp với bên ngoài qua port |
| **Layer** | Một tầng code: domain, application, adapters, bootstrap |
| **Domain** | Luật nghiệp vụ thuần, không phụ thuộc framework |
| **Entity** | Đối tượng có danh tính riêng (`AttendanceEvent`, danh tính là `eventId`) |
| **Value object** | Đối tượng chỉ được xác định bằng giá trị (`StationId`, `PayloadHash`) |
| **Use case** | Một hành động người dùng/hệ thống muốn làm, ví dụ "nhận một sự kiện". Class trong `application/` |
| **Port** | Lớp trừu tượng khai báo "cần làm được gì" (`Clock`, `AttendanceWriter`) |
| **Adapter** | Lớp cụ thể hiện thực port, hoặc nhận request từ ngoài vào (HTTP) |
| **Inbound / outbound adapter** | Adapter nhận yêu cầu *vào* hệ thống (HTTP) / adapter để hệ thống gọi *ra* ngoài (DB, đồng hồ) |
| **DTO** | Data Transfer Object, gói dữ liệu để truyền giữa các layer (`IngestEventCommand`, `IngestResult`) |
| **Dependency injection** | Truyền thứ class cần dùng vào qua constructor, thay vì để class tự tạo |
| **Composition root** | Nơi duy nhất tạo adapter thật và nối vào use case: `bootstrap/container.py` |
| **`ApiDependencies`** | Dataclass do adapter HTTP khai báo, chứa các use case/port route cần; `bootstrap` tạo nó từ adapter thật, test tạo nó từ fake |
| **ADR** | Architecture Decision Record, quyết định kiến trúc trong báo cáo M1 (ADR01–ADR09) |
| **DP** | Design Principle, nguyên tắc thiết kế trong báo cáo M1 (DP01–DP09) |
| **IADR** | Implementation ADR, quyết định hiện thực của M2 (`docs/adr-impl/`) |

## Dữ liệu và độ tin cậy

| Thuật ngữ | Nghĩa |
|---|---|
| **Transaction** | Nhóm thao tác DB "tất cả hoặc không gì cả" |
| **Commit / Rollback** | Chốt lưu transaction / huỷ toàn bộ |
| **Unit of Work** (UoW) | Port gói một transaction: ghi event và outbox chung, rồi `commit()` |
| **ACK** | Acknowledgement, lời xác nhận "đã nhận và lưu xong" gửi về trạm |
| **Idempotent** | Làm một lần hay mười lần thì kết quả như nhau. API ingest của S3 là idempotent nhờ dedupe |
| **Deduplication** (dedupe) | Chống lưu trùng khi nhận lại cùng sự kiện |
| **Payload hash** | sha256 của 9 trường sự kiện, dùng để so nội dung nhanh |
| **Store-and-forward** | Lưu tại chỗ trước, gửi đi sau (cách Gate Agent chịu được mất mạng, ADR04) |
| **Outbox** | Bảng ghi "tin cần báo cho hệ thống khác", ghi cùng transaction với dữ liệu chính |
| **Immutable** (bất biến) | Không sửa được sau khi tạo. Event gốc bất biến (ADR08); dataclass `frozen=True` |
| **Schema** (PostgreSQL) | "Thư mục" chứa bảng trong một DB. S3 sở hữu schema `attendance` |
| **Role** (PostgreSQL) | Tài khoản DB. S3 có 3: owner (tạo bảng), app (chạy app, không UPDATE/DELETE event), reader (S4 chỉ đọc view) |
| **Migration** | File Python mô tả thay đổi cấu trúc DB theo phiên bản; chạy bằng Alembic |
| **View `v1_attendance_event`** | "Bảng ảo" có phiên bản để S4 đọc, S3 đổi bảng thật mà không làm hỏng S4 |
| **`LIMIT`/`OFFSET`** | Phân trang trong SQL: lấy tối đa `LIMIT` dòng, bỏ qua `OFFSET` dòng đầu |

## Công cụ

| Thuật ngữ | Nghĩa |
|---|---|
| **uv** | Trình quản lý Python và thư viện. `uv sync` cài đủ, `uv run <lệnh>` chạy trong môi trường dự án, `uv add <gói>` thêm thư viện |
| **`uv.lock`** | File ghim chính xác phiên bản mọi thư viện. Không sửa tay |
| **ruff** | Kiểm lỗi style và tự format code |
| **mypy** | Kiểm kiểu dữ liệu (type hint). Code trong `src/` phải ghi kiểu ở mọi hàm; test thì được bỏ qua |
| **import-linter** | Kiểm quy tắc import giữa các layer (`uv run lint-imports`) |
| **pytest** | Chạy test |
| **Marker** (`unit`, `api`, `integration`, `e2e`) | Nhãn phân loại test, gán tự động theo thư mục |
| **Fixture** | Hàm pytest chuẩn bị sẵn thứ test cần (kết nối DB, dữ liệu mẫu) |
| **Fake** | Adapter giả chạy trong bộ nhớ, kế thừa port thật (`tests/fakes.py`) |
| **Mock** | Đối tượng giả "chấp nhận mọi lời gọi". **Không dùng** cho port của dự án |
| **Contract test** | Bộ test chạy cho cả fake lẫn adapter thật để chứng minh chúng cư xử giống nhau |
| **Factory** (test) | Hàm tạo dữ liệu mẫu hợp lệ (`tests/factories.py`: `event_fields()`, `event_payload()`) |
| **FastAPI** | Framework web Python. Endpoint viết bằng `def`, không `async def` (IADR-002) |
| **Pydantic** | Thư viện kiểm dữ liệu JSON. Chỉ dùng ở adapter HTTP và config |
| **SQLAlchemy Core** | Thư viện viết SQL bằng Python. Dùng phần Core (`Table`, `insert`), không dùng ORM |
| **Alembic** | Công cụ chạy migration |
| **Docker / compose** | Chạy PostgreSQL trong container: `docker compose -f infra/compose.yaml up -d postgres` |
| **`scripts/dev.py`** | Lệnh tiện dụng chạy được trên cả Windows và Linux: `uv run scripts/dev.py check` |
| **Docker image** | Gói app + Python + thư viện thành một khối chạy giống nhau trên mọi máy (`services/s3-attendance/Dockerfile`) |
| **CI** | GitHub Actions tự chạy test mỗi khi có PR (`.github/workflows/ci.yml`) |
| **PR** (Pull Request) | Yêu cầu gộp nhánh của bạn vào `main`, kèm review |
| **Conventional Commits** | Quy ước viết commit: `feat(s3): ...`, `fix(s3): ...`, `test(s3): ...` |
