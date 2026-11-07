# 09 — Backlog

Mỗi task có **mức**:

- **Bắt buộc**: cần cho bản nộp. Làm xong hết mức này là đủ một module chạy được, chứng minh được SOLID và khớp thiết kế M1.
- **Tuỳ chọn**: làm nếu còn thời gian, hoặc nếu bạn muốn học thêm. Không làm cũng không sao.

Test cần có cho từng task: xem bảng theo layer ở `05-testing-strategy.md` §3 (cột "Mức"). Hạn chót chưa chốt (`13-open-questions.md` Q8).

```
Phase 0 (TV1, xong) ──▶ T2.1 ports (TV2) ──┬──▶ Phase 1–2 (TV2)
                                          ├──▶ Phase 3 (TV3)
                                          └──▶ Phase 4 (TV4)
Phase 2 + 3 + 4 ──▶ Phase 5 (TV5) ──▶ Phase 6 (TV1) ──▶ Phase 8 (báo cáo)
```

Đường găng: T2.1 → T2.3 → T3.3 → T4.3 → E2E. T2.1 cần merge sớm nhất có thể.

---

## Phase 0 — Dựng repo (TV1)

| Task | Trạng thái |
|---|---|
| T0.1 Repo GitHub, mời 5 thành viên; (tuỳ chọn) ruleset cho `main` theo `06-ci-cd.md` §3 | chờ tạo repo |
| T0.2 Khung project Python (`pyproject.toml`, `uv.lock`, cây package, `scripts/dev.py`, `.env.example`) | xong |
| T0.3 PostgreSQL local (`infra/compose.yaml`, script tạo 3 role) | xong |
| T0.4 CI một job `test` (`06-ci-cd.md`) | xong, chờ lần chạy đầu trên GitHub |
| T0.5 Hạ tầng test (`conftest.py`, fixture DB, `factories.py`, khung contract test) | xong |
| T0.6 Template PR/issue; tạo issue cho các task bên dưới và gán người | template xong, issue chờ repo |
| T0.7 Walking skeleton: `/health/*` đi đủ 4 layer, Alembic, Dockerfile | xong |

T0.7 là **code mẫu** cho cả nhóm: port `HealthProbe` → adapter `PostgresHealthProbe` → route → nối dây ở `bootstrap` → test với fake và với DB thật. Danh sách file ở `huong-dan/README.md` mục "Code mẫu để nhìn theo".

---

## Phase 1 — Domain (TV2)

### T1.1 Enum, value object, `AttendanceEvent` — Bắt buộc
- AC: theo `02-domain-model.md` mục 1–3; `InvalidEvent` mang `field` và `message`; thêm `make_event(**overrides)` vào `tests/factories.py` (bọc `event_fields`).

### T1.2 Payload hash chuẩn hoá — Bắt buộc
- Phụ thuộc: T1.1
- AC: `canonical_payload`, `compute_payload_hash` theo `02-domain-model.md` mục 4.

### T1.3 `DeduplicationRule`, `EventValidationPolicy`, quyền đọc — Bắt buộc
- Phụ thuộc: T1.1
- AC: theo `02-domain-model.md` mục 5–7.

---

## Phase 2 — Application (TV2)

### T2.1 Port và DTO — Bắt buộc, **làm đầu tiên, merge sớm**
- Phụ thuộc: T1.1 (chỉ cần kiểu `AttendanceEvent`)
- AC:
  - Thêm vào `application/ports.py` (đã có `HealthProbe`) các port ở `01-kien-truc-s3.md` mục 3, mỗi port có docstring mô tả hợp đồng.
  - `application/dto.py`: `IngestEventCommand`, `InvalidItem`, `IngestResult`, `BatchResult`, `BatchSummary`, `EventConflict`, `OutboxMessage`, `AuthenticatedStation`, `HistoryQuery`, `HistoryPage`, `AttendanceEventView`.
  - Exception `AccessDenied`, `InvalidQuery`.
  - `tests/factories.py`: thêm `make_command(**overrides)`, `make_station(...)`.
- Sau khi merge, TV3, TV4, TV5 code dựa trên các port này.

### T2.2 Fake — Bắt buộc
- Phụ thuộc: T2.1
- AC: thêm các fake vào `tests/fakes.py` (đã có `FakeHealthProbe`) theo `05-testing-strategy.md` mục 2; contract test chạy với fake.

### T2.3 `IngestAttendanceEventUseCase` — Bắt buộc
- Phụ thuộc: T1.2, T1.3, T2.2
- AC: theo `01-kien-truc-s3.md` mục 4.1; đúng ma trận ở `02-domain-model.md` mục 9.

### T2.4 `IngestAttendanceBatchUseCase` — Bắt buộc
- Phụ thuộc: T2.3

---

## Phase 3 — Persistence (TV3)

### T3.1 Migration 0001 — Bắt buộc
- Đã có (T0.7): `alembic.ini`, `migrations/env.py`, template. Tạo file: `uv run alembic revision --rev-id 0001 -m "create attendance schema"`.
- AC: đúng DDL `04-database.md` mục 2, kể cả view và GRANT; `downgrade()` gỡ sạch (giữ schema).

### T3.2 `tables.py` + `SqlAlchemyUnitOfWork` — Bắt buộc
- Phụ thuộc: T2.1, T3.1
- AC: theo `04-database.md` mục 3, 5; gán `target_metadata` trong `migrations/env.py` bằng `MetaData` của `tables.py`.

### T3.3 `PostgresAttendanceRepository` — Bắt buộc
- Phụ thuộc: T3.2
- AC: `insert_if_absent` theo `04-database.md` mục 4; contract test chạy với Postgres.

### T3.4 `PostgresOutbox` — Bắt buộc
- Phụ thuộc: T3.2

### T3.5 Test quyền DB — Bắt buộc
- Phụ thuộc: T3.1
- AC: test "quyền DB" ở `05-testing-strategy.md` §3. Đây là bằng chứng cho ADR07, ADR08 trong báo cáo.

---

## Phase 4 — HTTP API (TV4)

### T4.1 Xử lý lỗi và logging — Bắt buộc
- Phụ thuộc: T2.1
- Đã có (T0.7): `create_app(deps)` tối thiểu.
- AC: `adapters/inbound/http/errors.py` theo `03-api-contract.md` mục 5 (422 không lộ giá trị đầu vào, 503 khi DB lỗi); `logging.basicConfig` theo `TMC_S3_LOG_LEVEL` trong `bootstrap/main.py`.

### T4.2 `StaticTokenStationAuthenticator` + đọc Bearer token — Bắt buộc
- Phụ thuộc: T2.1
- AC: so sánh `hmac.compare_digest` trên sha256; token không bao giờ xuất hiện trong log.

### T4.3 `EventIngestController` — Bắt buộc
- Phụ thuộc: T2.4 (có thể code trước với fake use case), T4.1, T4.2
- AC: parse hai tầng theo `03-api-contract.md` mục 2; giới hạn `TMC_S3_MAX_BATCH_SIZE`; thêm use case và authenticator vào `ApiDependencies`.

### T4.6 `scripts/simulate_station.py` — Tuỳ chọn
- Phụ thuộc: T4.3
- AC: gửi lô giả lập, gửi lại, tạo xung đột (tham số ở `05-testing-strategy.md` mục 6); chỉ dùng stdlib + `httpx2`. Tiện để quay demo.

---

## Phase 5 — Read side (TV5)

### T5.1 `PostgresAttendanceQueries` + `InMemoryAttendanceReader` — Bắt buộc
- Phụ thuộc: T3.2
- AC: truy vấn `04-database.md` mục 8 (`LIMIT`/`OFFSET`).

### T5.2 `GetAttendanceHistoryUseCase` + route — Bắt buộc
- Phụ thuộc: T5.1, T4.1
- AC: theo `01-kien-truc-s3.md` mục 4.3 và `03-api-contract.md` mục 3.

### T5.3 View `v1` cho S4 — Bắt buộc
- Phụ thuộc: T3.1 (view nằm trong migration 0001)
- AC: test role `s4_reporting_reader` đọc được view, không đọc được bảng (chung với T3.5).

---

## Phase 6 — Đóng gói và E2E (TV1)

### T6.2 Docker — Bắt buộc
- Đã có (T0.7): `Dockerfile`, `.dockerignore`; image chạy non-root, healthcheck, migrate trong container chạy được.
- AC còn lại: trên cả Arch và Windows (Docker Desktop), `docker compose -f infra/compose.yaml --profile app up --build` cho `/health/ready` 200; sau T4.3, lệnh `curl` trong `services/s3-attendance/README.md` trả `ACCEPTED`. Hướng dẫn ở `10-local-setup.md`.

### T6.5 E2E — Bắt buộc
- Phụ thuộc: T4.3, T5.2
- AC: các kịch bản mức bắt buộc ở `05-testing-strategy.md` §3 (E2E).

---

## Phase 7 — Mở rộng (Tuỳ chọn, theo thứ tự ưu tiên)

### T7.1 Điều chỉnh công (ADR08, UC11) — TV5
- Bảng `attendance.attendance_adjustment` (migration 0002), use case tạo/duyệt điều chỉnh. Viết thiết kế ngắn trong `docs/15-adjustments.md` trước khi code (TV1 duyệt).

### T7.2 Outbox relay — TV3
- Worker đọc `outbox` `PENDING`, "publish" qua port `MessagePublisher` (adapter M2: ghi log), đánh dấu `PUBLISHED`. Minh hoạ OCP.

### T7.3 S1 — xác thực chữ ký QR
- Xem `14-s1-stretch.md`. Chỉ bắt đầu khi mọi task bắt buộc đã xong.

### T7.4 Test nâng cao
- Các test mức "Tuỳ chọn" ở `05-testing-strategy.md` §3 (ví dụ hai thread ghi đồng thời, migration round-trip).

---

## Phase 8 — Báo cáo (tất cả, TV1 điều phối)

Báo cáo chiếm phần lớn điểm. Bắt đầu song song với code, đừng để tới cuối.

| Task | Ai | Nội dung |
|---|---|---|
| T8.1 | TV1 | Cập nhật Hình 7 và vẽ các view (module, C&C, allocation), xem `12-report-mapping.md` |
| T8.2 | TV2 + TV4 | Bảng SOLID có trích code, theo `11-solid-mapping.md` |
| T8.3 | TV1 | Ảnh chụp: CI xanh, `curl`/demo, kết quả test quyền DB |
| T8.4 | Mọi người | Mỗi người viết 1 đoạn Reflection từ `reflection-log.md` |
| T8.5 | TV1 | Tag `s3-v1.0.0`, ghi URL repo + tag vào báo cáo |
