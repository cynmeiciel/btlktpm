# 04 — Cơ sở dữ liệu của S3

PostgreSQL 16. S3 sở hữu duy nhất schema `attendance` (ADR02). Truy cập bằng SQLAlchemy 2.0 **Core** + driver `psycopg` 3 (URL dạng `postgresql+psycopg://`).

## 1. Role và quyền (ADR02, ADR07)

| Role | Dùng bởi | Quyền |
|---|---|---|
| `s3_attendance_owner` | Alembic, fixture test | sở hữu schema `attendance`, tạo/sửa bảng |
| `s3_attendance_app` | app lúc chạy | `SELECT, INSERT` trên `attendance_event`, `event_conflict`; `SELECT, INSERT, UPDATE` trên `outbox`. **Không** `UPDATE`/`DELETE` trên `attendance_event` |
| `s4_reporting_reader` | S4 (giả lập trong test) | chỉ `SELECT` trên view `attendance.v1_attendance_event` |

Quyền DB là lớp bảo vệ thứ hai cho ADR08: kể cả có bug trong code, role app không sửa/xoá được event gốc. Có test kiểm điều này (`05-testing-strategy.md` §3, mục "quyền DB").

Role là đối tượng cấp cluster, không thuộc migration của service. Tạo bằng script hạ tầng:

`infra/postgres/init/01-roles.sql` (chạy tự động bởi image postgres khi volume trống; CI chạy bằng `psql`):

```sql
-- DEV/CI ONLY. Mật khẩu thật không bao giờ nằm trong repo.
CREATE ROLE s3_attendance_owner LOGIN PASSWORD 'owner-dev-pw';
CREATE ROLE s3_attendance_app   LOGIN PASSWORD 'app-dev-pw';
CREATE ROLE s4_reporting_reader LOGIN PASSWORD 'reader-dev-pw';

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA attendance AUTHORIZATION s3_attendance_owner;
GRANT USAGE ON SCHEMA attendance TO s3_attendance_app, s4_reporting_reader;
```

Grant trên từng bảng nằm trong migration (vì bảng được tạo ở đó).

## 2. Bảng

Migration `0001_create_attendance_schema` (chạy bằng role owner):

```sql
CREATE TABLE attendance.attendance_event (
    event_id        uuid         PRIMARY KEY,
    attempt_id      uuid         NOT NULL,
    employee_ref    uuid         NOT NULL,
    station_id      varchar(64)  NOT NULL,
    direction       text         NOT NULL CHECK (direction IN ('IN', 'OUT')),
    occurred_at     timestamptz  NOT NULL,
    received_at     timestamptz  NOT NULL,
    local_sequence  bigint       NOT NULL CHECK (local_sequence >= 0),
    evidence_level  text         NOT NULL CHECK (evidence_level IN
                        ('CONTROLLER_CONFIRMED', 'CONTROLLER_UNCONFIRMED', 'GUARD_RECORDED')),
    schema_version  smallint     NOT NULL,
    payload_hash    char(64)     NOT NULL
);

CREATE INDEX ix_attendance_event_employee_time
    ON attendance.attendance_event (employee_ref, occurred_at, event_id);
CREATE INDEX ix_attendance_event_station_time
    ON attendance.attendance_event (station_id, occurred_at);

CREATE TABLE attendance.event_conflict (
    conflict_id        uuid         PRIMARY KEY,
    event_id           uuid         NOT NULL,
    station_id         varchar(64)  NOT NULL,
    kind               text         NOT NULL CHECK (kind IN ('PAYLOAD_MISMATCH')),
    incoming_payload   jsonb        NOT NULL,
    incoming_hash      char(64)     NOT NULL,
    detected_at        timestamptz  NOT NULL,
    CONSTRAINT uq_event_conflict_once UNIQUE (event_id, kind, incoming_hash)
);
CREATE INDEX ix_event_conflict_station_time
    ON attendance.event_conflict (station_id, detected_at);

CREATE TABLE attendance.outbox (
    message_id    uuid         PRIMARY KEY,
    aggregate_id  uuid         NOT NULL,
    message_type  text         NOT NULL,
    payload       jsonb        NOT NULL,
    occurred_at   timestamptz  NOT NULL,
    state         text         NOT NULL DEFAULT 'PENDING'
                      CHECK (state IN ('PENDING', 'PUBLISHED', 'FAILED')),
    attempts      integer      NOT NULL DEFAULT 0,
    published_at  timestamptz
);
CREATE INDEX ix_outbox_pending
    ON attendance.outbox (occurred_at) WHERE state = 'PENDING';

CREATE VIEW attendance.v1_attendance_event AS
SELECT event_id, employee_ref, station_id, direction,
       occurred_at, received_at, evidence_level
FROM attendance.attendance_event;

GRANT SELECT, INSERT         ON attendance.attendance_event TO s3_attendance_app;
GRANT SELECT, INSERT         ON attendance.event_conflict   TO s3_attendance_app;
GRANT SELECT, INSERT, UPDATE ON attendance.outbox           TO s3_attendance_app;
GRANT SELECT                 ON attendance.v1_attendance_event TO s4_reporting_reader;
```

Ghi chú thiết kế:

- **Không có foreign key** sang `identity.employee` hay `gate.station`: đó là schema của S1/S2. FK chéo schema sẽ buộc thứ tự triển khai và migration giữa các service — trái ADR02. Tính hợp lệ của `employee_ref`/`station_id` được trạm bảo đảm lúc quét (policy do S2 phát) và đối soát ở S4.
- `text + CHECK` thay cho `ENUM` của PostgreSQL: thêm giá trị mới bằng một migration thay CHECK, hợp với quy trình expand–migrate–contract (M1 chương 6) hơn `ALTER TYPE`.
- `local_sequence` được lưu nhưng **không** có ràng buộc UNIQUE trong M2 (`02-domain-model.md` §9). Khi cần phát hiện trạm dùng lại số thứ tự (M1 chương 6, bước 6), thêm bằng migration mới.
- `kind` vẫn là `text + CHECK` dù hiện chỉ có một giá trị, để thêm loại xung đột sau chỉ cần sửa CHECK.
- `uq_event_conflict_once`: Sync Worker gửi lại cùng payload xung đột nhiều lần chỉ tạo một bản ghi.
- View `v1_attendance_event` là API có phiên bản cho S4 (Bước 6 M1, điều chỉnh 3). Đổi cột phá tương thích → tạo `v2_...`, giữ `v1` tới khi S4 chuyển xong.
- `payload_hash`, `attempt_id`, `local_sequence`, `schema_version` không lộ ra view: chi tiết nội bộ.
- `AttendanceAdjustment` (ADR08) chưa có ở 0001 — thuộc stretch, migration riêng.

## 3. Định nghĩa SQLAlchemy Core

`adapters/outbound/persistence/tables.py` khai báo `metadata = MetaData(schema="attendance")` và ba `Table` khớp DDL ở trên. Migration Alembic viết tay bằng `op.create_table` / `op.execute` (không dùng autogenerate để sinh migration chính thức; autogenerate chỉ để so lệch, xem mục 6). View và GRANT viết bằng `op.execute(...)`.

## 4. `insert_if_absent` — chống trùng an toàn khi đồng thời

```sql
INSERT INTO attendance.attendance_event (event_id, ..., payload_hash)
VALUES (:event_id, ..., :payload_hash)
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id;
```

- Có dòng trả về → `Inserted()`.
- Không có dòng trả về → `SELECT payload_hash FROM attendance.attendance_event WHERE event_id = :event_id` → `EventIdExists(existing_hash)`. Không thấy dòng nào là lỗi nghiêm trọng (không có DELETE nên không thể xảy ra): `raise RuntimeError`.

Vì sao đúng khi hai request cùng event tới đồng thời (isolation mặc định READ COMMITTED):

- Request B gặp xung đột với dòng request A vừa chèn nhưng chưa commit → B **chờ** A kết thúc.
- A commit → `ON CONFLICT DO NOTHING` của B không chèn; câu SELECT sau đó của B thấy dòng của A → `EventIdExists` → hash bằng → `DUPLICATE`.
- A rollback → B chèn được → `ACCEPTED`.

Không bao giờ có hai dòng cùng `event_id`, không cần `SERIALIZABLE` hay khoá tay. Lập luận này đưa vào báo cáo; test hai thread thật là tuỳ chọn (`05-testing-strategy.md` §3).

`record_conflict`: `INSERT ... ON CONFLICT (event_id, kind, incoming_hash) DO NOTHING`.

## 5. Unit of Work

`SqlAlchemyUnitOfWork(engine)`:

- `__enter__`: `self._conn = engine.connect()`; `self._tx = self._conn.begin()`; tạo `PostgresAttendanceRepository(self._conn)` và `PostgresOutbox(self._conn)` gán vào `attendance`, `outbox`.
- `commit()`: `self._tx.commit()`, đánh dấu đã commit.
- `rollback()`: `self._tx.rollback()` nếu còn active.
- `__exit__`: chưa commit → rollback; luôn `self._conn.close()`.

Không dùng `Session` ORM. Một UoW = một connection = một transaction.

## 6. Alembic

- `alembic.ini` không chứa URL; `migrations/env.py` lấy `TMC_S3_MIGRATION_DATABASE_URL` qua `DatabaseAdminSettings` (`bootstrap/config.py`, đọc cả `.env`); thiếu → báo lỗi rõ ràng.
- `version_table_schema="attendance"` để bảng `alembic_version` nằm trong schema của S3, không đụng `public`.
- `target_metadata = tables.metadata` chỉ để so lệch giữa `tables.py` và DB. Kiểm bằng tay với `uv run alembic check`; CI chưa chạy lệnh này.
- Mỗi migration phải có `downgrade()` chạy được. Kiểm bằng tay trên DB dev: `uv run alembic downgrade base`, rồi `uv run alembic upgrade head` (lệnh đầu xoá toàn bộ bảng của S3). Chưa có pytest tự động cho việc này; đây là test mức Tuỳ chọn ở `05-testing-strategy.md` §3.
- Tên file: `NNNN_<mô_tả_snake_case>.py`, `revision` = `"NNNN"` để thứ tự dễ đọc.
- Migration đã merge vào `main` không sửa. Thay đổi phá tương thích theo expand → migrate → contract (M1 chương 6, quy tắc 3): ba migration riêng ở ba PR.

## 7. Dữ liệu trong test

- Fixture `owner_engine` (role owner), `app_engine` (role app). Dependencies của test e2e dùng `app_engine` — đúng quyền như production.
- Trước mỗi test integration/e2e: `TRUNCATE` **mọi bảng trong schema `attendance` trừ `alembic_version`** bằng `owner_engine` (hàm `truncate_attendance_tables` trong `tests/conftest.py`, danh sách bảng đọc từ `pg_tables` nên không phải sửa khi migration thêm bảng; autouse qua `tests/integration/conftest.py`, e2e làm tương tự khi có). Không bọc test trong transaction rollback, vì code dưới test tự commit.
- Test DB chạy tuần tự (không `pytest-xdist` cho integration/e2e).

## 8. Truy vấn lịch sử

```sql
SELECT event_id, station_id, direction, occurred_at, received_at, evidence_level
FROM attendance.attendance_event
WHERE employee_ref = :employee_ref
  AND occurred_at >= :from AND occurred_at < :to
ORDER BY occurred_at, event_id
LIMIT :limit_plus_one OFFSET :offset;
```

Lấy `limit + 1` dòng: có dòng thứ `limit + 1` nghĩa là `hasMore = true` (dòng đó không trả về). Dùng được index `ix_attendance_event_employee_time`.

## 9. Dung lượng

Theo M1 chương 6 bước 5: ~1,04 triệu event/năm, ~5 GB/năm kể cả index. Một PostgreSQL đơn là đủ, không cần partition trong M2.
