# 11 — SOLID trong code S3

Bảng ánh xạ để (1) người code biết mỗi nguyên tắc phải hiện ra ở đâu, (2) người viết báo cáo Task 1.3 và Task 2 trích đúng chỗ. Mỗi dòng có **test chứng minh** — báo cáo nên dẫn test, không chỉ dẫn class, vì test cho thấy nguyên tắc có tác dụng thật.

Đối chiếu DP của báo cáo M1: DP05 = SRP, DP06 = OCP, DP07 = LSP, DP08 = ISP, DP09 = DIP.

## S — Single Responsibility (DP05)

| Ở đâu | Một lý do thay đổi duy nhất | Test chứng minh |
|---|---|---|
| `DeduplicationRule` | luật phân loại trùng/xung đột | test `DeduplicationRule` |
| `EventValidationPolicy` | ngưỡng chấp nhận thời gian | test `EventValidationPolicy` |
| `compute_payload_hash` | định nghĩa "cùng một sự kiện" | test payload hash |
| `IngestAttendanceEventUseCase` | trình tự nghiệp vụ tiếp nhận một event | test use case với fake |
| `IngestAttendanceBatchUseCase` | ngữ nghĩa lô (thứ tự, per-item) | test batch use case |
| `EventIngestController` | dịch HTTP ↔ command/result | test API ingest |
| `PostgresAttendanceRepository` | SQL ghi event | contract test chạy với Postgres |

Phản ví dụ đã tránh: một `AttendanceService` vừa parse JSON, vừa kiểm đồng hồ, vừa viết SQL, vừa quyết định status. Đổi định dạng API sẽ phải sửa cùng file với luật dedupe.

Đánh đổi (ghi vào báo cáo như M1 DP05 đã nói): nhiều file và class nhỏ hơn; người mới phải nhảy qua nhiều file để theo một luồng. Bù lại bằng sơ đồ luồng ở `01-kien-truc-s3.md` mục 8.

Trích code gợi ý cho báo cáo: constructor của `IngestAttendanceEventUseCase` — chỉ nhận abstraction, mỗi phụ thuộc là một trách nhiệm được uỷ thác.

## O — Open/Closed (DP06)

| Điểm mở rộng | Mở rộng bằng cách | Không phải sửa |
|---|---|---|
| `StationAuthenticator` | thêm `MtlsStationAuthenticator` khi có PKI | controller, use case |
| `DeduplicationRule` | lớp con coi khác biệt chỉ ở `evidenceLevel` là nâng cấp bằng chứng | use case |
| `AttendanceWriter` | adapter cho kho khác | use case |
| `OutboxPort` (+ `MessagePublisher` ở T7.2) | publish qua broker thay vì log | worker, use case |
| Phiên bản schema | thêm `2` vào `SUPPORTED_SCHEMA_VERSIONS` + nhánh hash mới | event v1 đã lưu |

Bằng chứng: `bootstrap/container.py` là nơi duy nhất đổi khi thay adapter. Trong báo cáo, trình diễn bằng diff giả định "thay `StaticTokenStationAuthenticator` bằng `MtlsStationAuthenticator`" chỉ chạm `container.py` + file adapter mới.

Đánh đổi (M1 DP06): chỉ tạo điểm mở rộng ở chỗ có lý do thay đổi thật. **Không** tạo interface cho `canonical_payload` hay `can_read_history` — chúng là hàm thuần, thay đổi thì sửa thẳng.

## L — Liskov Substitution (DP07)

Mọi hiện thực của một port phải giữ **hợp đồng hành vi**, không chỉ chữ ký hàm.

| Hợp đồng | Fake | Thật | Test chung |
|---|---|---|---|
| `insert_if_absent`: event mới → `Inserted`; trùng id → `EventIdExists(hash cũ)`; chưa commit thì không thấy | `InMemoryAttendanceWriter` | `PostgresAttendanceRepository` | `AttendanceWriterContract` (chạy cho cả hai) |
| `UnitOfWork`: không commit → không ai thấy thay đổi | `InMemoryUnitOfWork` | `SqlAlchemyUnitOfWork` | `test_nothing_visible_without_commit` |
| `AttendanceReader`: sắp xếp `(occurredAt, eventId)`, không trùng/sót giữa các trang | `InMemoryAttendanceReader` | `PostgresAttendanceQueries` | contract reader (T5.1) |
| `Clock.now()` luôn aware UTC | `FixedClock` | `SystemClock` | unit nhỏ cho cả hai |

Đây chính là ý của M1 DP07 ("mọi adapter phải tuân thủ đúng ý nghĩa của các kết quả"): unit test của use case chỉ có giá trị nếu fake cư xử như Postgres. Contract test là cách chứng minh điều đó thay vì tin.

Ví dụ vi phạm mà contract test bắt được: fake ghi thẳng vào store mà không chờ `commit()` → unit test của use case xanh dù quên commit, nhưng trên Postgres dữ liệu biến mất. Test "chưa commit thì không thấy" bắt lỗi này ở cả hai.

## I — Interface Segregation (DP08)

| Client | Phụ thuộc | Không bị buộc phụ thuộc |
|---|---|---|
| `IngestAttendanceEventUseCase` | `AttendanceWriter`, `OutboxPort` (qua `UnitOfWork`), `Clock`, `IdGenerator` | `AttendanceReader` |
| `GetAttendanceHistoryUseCase` | `AttendanceReader`, `Clock` | `AttendanceWriter`, `OutboxPort` |
| Route health | `HealthProbe` | mọi port nghiệp vụ |
| S4 (bên ngoài) | view `v1_attendance_event` | bảng gốc, `payload_hash`, `local_sequence` |

Bằng chứng: `PostgresAttendanceRepository` và `PostgresAttendanceQueries` là hai class riêng dù cùng bảng. Fake cho test history không cần cài `insert_if_absent`.

Ở mức dữ liệu, ISP thể hiện ở grant: `s4_reporting_reader` chỉ thấy view (test quyền DB).

## D — Dependency Inversion (DP09, ADR05)

| Module cấp cao | Phụ thuộc abstraction | Chi tiết cấp thấp hiện thực abstraction |
|---|---|---|
| `IngestAttendanceEventUseCase` | `UnitOfWork`, `Clock`, `IdGenerator` | `SqlAlchemyUnitOfWork`, `SystemClock`, `Uuid4Generator` |
| controller | use case (qua `ApiDependencies`) | — |

- Port **do application định nghĩa** (`application/ports.py`), không do adapter. Hướng phụ thuộc mã nguồn: `adapters → application`, đúng chú thích Hình 7 M1.
- Bằng chứng tự động: 4 contract của import-linter (`07-conventions.md` mục 3) chạy trong job CI `test`. Báo cáo chụp output `lint-imports` (mọi contract "KEPT").
- Bằng chứng thực nghiệm: toàn bộ test `unit` và `api` chạy không có PostgreSQL, không có FastAPI server thật.

Thử nghiệm nên đưa vào báo cáo: tạm thêm `import sqlalchemy` vào `application/ingest_event.py` → `lint-imports` báo "BROKEN" → CI đỏ. Chụp lại, rồi bỏ dòng đó.

## Tóm tắt một bảng (cho báo cáo)

| Nguyên tắc | Class tiêu biểu | Cơ chế kiểm | Test |
|---|---|---|---|
| SRP | `DeduplicationRule`, `EventValidationPolicy` | review + kích thước | test `DeduplicationRule`, `EventValidationPolicy` |
| OCP | `StationAuthenticator` | thay adapter chỉ sửa `container.py` | test API xác thực trạm |
| LSP | `AttendanceWriter` + 2 hiện thực | contract test | `AttendanceWriterContract` |
| ISP | `AttendanceWriter` / `AttendanceReader` tách | grant DB + test fake nhỏ | test quyền DB, test history use case |
| DIP | `application/ports.py` | import-linter | job CI `test` |

## Bằng chứng đã xác nhận từ phần TV2

| Nguyên tắc | Hiện thực | Bằng chứng |
|---|---|---|
| SRP | Tách hash, deduplication, timestamp policy và các use case | test_payload_hash.py, test_dedup.py, test_policy.py |
| OCP | Use case nhận các dependency qua constructor; adapter thực hiện port | Use case chạy với in-memory adapters mà không chứa SQL |
| LSP | Fake writer tuân theo hợp đồng AttendanceWriter | Ba test kế thừa AttendanceWriterContract chạy với fake |
| ISP | AttendanceReader và AttendanceWriter là hai port riêng | Reader fake không phải hiện thực các thao tác ghi |
| DIP | Application định nghĩa port, use case không import adapter | Cả bốn import-linter contracts được giữ |

Kết quả tại commit d4497f2:

- Toàn bộ kiểm tra: 130 test pass, gồm 5 integration test PostgreSQL.
- Đo coverage bằng unit/API: 125 test pass.
- Coverage Domain/Application: 99%; 24/24 nhánh được đo đã được chạy.
- Hai use case ingest_event và ingest_batch đạt 100% coverage.

Giới hạn:

- Test nghiệp vụ ingest hiện chạy với fake.
- Năm integration test hiện có kiểm tra hạ tầng DB,
  chưa kiểm chứng luồng ingest bằng adapter PostgreSQL thật.
- TV3 cần chạy AttendanceWriterContract với PostgreSQL adapter.
- Các ví dụ adapter production hoặc chức năng của TV4/TV5
  trong tài liệu là thiết kế dự kiến, chưa mặc nhiên là phần đã hoàn thành.
