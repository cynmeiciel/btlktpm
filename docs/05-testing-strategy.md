# 05 — Chiến lược kiểm thử

Mục tiêu của test trong bài này không chỉ là bắt lỗi. Mỗi nhóm test là **bằng chứng** cho một khẳng định trong báo cáo: dependency rule được giữ (DIP), adapter thay được cho nhau (LSP), gửi lại không tạo bản ghi trùng (ADR04), event gốc không sửa được (ADR08).

## 1. Các tầng test

| Marker | Thư mục | Chạy gì | Cần DB | Chạy khi |
|---|---|---|---|---|
| `unit` | `tests/unit/` | domain + application với fake port | Không | Mọi lúc, pre-push, mọi PR |
| `api` | `tests/api/` | FastAPI `TestClient` + `ApiDependencies` dựng từ fake | Không | Mọi PR |
| `integration` | `tests/integration/` | adapter outbound thật với PostgreSQL thật | Có | Mọi PR (job `test`) |
| `e2e` | `tests/e2e/` | `TestClient` + `build_api_dependencies` thật + PostgreSQL | Có | Mọi PR (job `test`) |
| (kiến trúc) | — | `lint-imports` (bước riêng trong job `test`) | Không | Mọi PR |

Tỷ lệ mong muốn: nhiều unit, vừa phải api/integration, ít e2e (5–8 test luồng chính).

Marker được gán tự động trong `tests/conftest.py` theo đường dẫn:

```python
def pytest_collection_modifyitems(config, items):
    for item in items:
        part = Path(item.fspath).relative_to(TESTS_DIR).parts[0]
        if part in {"unit", "api", "integration", "e2e"}:
            item.add_marker(getattr(pytest.mark, part))
```

Cấu hình DB của test dùng lại `DatabaseAdminSettings` (`bootstrap/config.py`) — cùng lớp Alembic dùng, nên tên biến môi trường chỉ khai báo một nơi (bảng biến môi trường ở `services/s3-attendance/README.md`):

```python
class DatabaseAdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TMC_S3_", env_file=".env", extra="ignore")

    migration_database_url: str | None = None   # TMC_S3_MIGRATION_DATABASE_URL (role owner) — Alembic, fixture
    database_url: str | None = None             # TMC_S3_DATABASE_URL           (role app)   — fixture
    reader_database_url: str | None = None      # TMC_S3_READER_DATABASE_URL    (role s4)    — fixture
```

- Mọi trường là tuỳ chọn để import/khởi tạo không bao giờ lỗi; `migrations/env.py` tự báo lỗi rõ ràng nếu `migration_database_url` là `None`.
- `env_file=".env"` tính từ thư mục chạy lệnh (`services/s3-attendance/`). Local chỉ cần `cp .env.example .env` là test DB chạy; CI không có `.env` mà đặt biến môi trường trực tiếp.
- Fixture `database_urls` (scope session) dựng `DatabaseAdminSettings()` một lần: thiếu bất kỳ URL nào trong ba URL → `pytest.skip`, **trừ khi** `TMC_REQUIRE_DB=1` → `pytest.fail`. CI đặt biến này để không bao giờ "xanh vì đã skip hết".
- `TMC_REQUIRE_DB` là cờ riêng của test nên không đưa vào `src/`; `conftest.py` đọc nó bằng `os.environ.get("TMC_REQUIRE_DB") == "1"` — chỗ **duy nhất** trong repo đọc `os.environ` (`07-conventions.md` §4).
- Test unit/api không chạm `database_urls`, nên chạy được trên máy không có DB lẫn không có `.env`.

## 2. Fake thay vì mock

`tests/fakes.py` chứa cài đặt trong bộ nhớ cho mọi port. Chúng là adapter thật sự (kế thừa port) — chính điều đó minh hoạ LSP.

| Fake | Hành vi bắt buộc |
|---|---|
| `FixedClock(at)` | `now()` trả `at`; có `advance(delta)` |
| `SequentialIdGenerator` | trả UUID tất định `00000000-0000-0000-0000-000000000001`, `...0002`, … |
| `InMemoryAttendanceStore` | giữ dict theo `event_id`; `insert_if_absent` trả `Inserted` hoặc `EventIdExists` giống adapter Postgres |
| `InMemoryUnitOfWork(store)` | ghi vào bộ đệm, chỉ áp vào `store` khi `commit()`; `rollback` bỏ bộ đệm; đếm `commits`, `rollbacks` |
| `InMemoryUnitOfWorkFactory(store)` | callable trả `InMemoryUnitOfWork`; đếm `opened` (để kiểm "bị từ chối thì không mở UoW"); có thể cấu hình để `commit` hoặc `outbox.add` ném lỗi |
| `InMemoryOutbox` | danh sách message; gắn với UoW |
| `FakeStationAuthenticator(mapping)` | token → station |
| `FakeHealthProbe(ready=True)` | |
| `InMemoryAttendanceReader(store)` | lọc/sắp xếp/phân trang giống adapter thật |

Không dùng `unittest.mock.Mock` để giả port của chính dự án. `Mock` chấp nhận mọi lời gọi nên không phát hiện được khi use case gọi sai hợp đồng. `monkeypatch` chỉ dùng cho biến môi trường.

**Contract test cho port** (chứng minh LSP): viết một bộ test dùng chung, chạy với cả fake lẫn adapter thật:

```python
# tests/contracts/attendance_writer_contract.py
class AttendanceWriterContract:
    @pytest.fixture
    def uow_factory(self) -> UnitOfWorkFactory: raise NotImplementedError
    def test_first_insert_returns_inserted(self, uow_factory): ...
    def test_same_event_id_returns_event_id_exists_with_hash(self, uow_factory): ...
    def test_nothing_visible_without_commit(self, uow_factory): ...

# tests/unit/application/test_in_memory_writer_contract.py
class TestInMemoryWriter(AttendanceWriterContract): ...   # fixture trả fake

# tests/integration/persistence/test_postgres_writer_contract.py
class TestPostgresWriter(AttendanceWriterContract): ...   # fixture trả SqlAlchemyUnitOfWork
```

`tests/contracts/` không có marker riêng; marker đến từ lớp con nằm ở `unit/` hay `integration/`. Đặt tên file contract không bắt đầu bằng `test_` để pytest không thu thập trực tiếp.

## 3. Nên test những gì

Chia hai mức. **Bắt buộc** là những test chứng minh điều báo cáo khẳng định; thiếu thì PR chưa xong. **Tuỳ chọn** là làm thêm nếu còn thời gian. Không cần đánh số test, chỉ cần tên test nói rõ hành vi.

### Domain (unit) — TV2

| Mức | Hành vi cần test |
|---|---|
| Bắt buộc | `AttendanceEvent` hợp lệ tạo được; thiếu múi giờ, `local_sequence < 0`, `station_id` sai định dạng, `schema_version` không hỗ trợ → `InvalidEvent` |
| Bắt buộc | Payload hash: cùng thời điểm khác offset (`+07:00` và `Z`) → hash bằng nhau; đổi một trường → hash khác |
| Bắt buộc | `DeduplicationRule`: hash bằng → DUPLICATE; khác → CONFLICT |
| Bắt buộc | `EventValidationPolicy`: +299 giây ok, +301 giây → CLOCK_SKEW, sự kiện cũ 30 ngày vẫn ok |
| Bắt buộc | `can_read_history`: tự đọc ok, HR ok, ADMIN và người khác không |
| Tuỳ chọn | Hash có giá trị cố định cho một event mẫu (phát hiện ai đó vô tình đổi công thức) |

### Application (unit, dùng fake) — TV2

| Mức | Hành vi cần test |
|---|---|
| Bắt buộc | Event mới → ACCEPTED; store có 1 event, outbox có 1 message, đã commit |
| Bắt buộc | Gửi lại y hệt → DUPLICATE; store và outbox vẫn 1 |
| Bắt buộc | Cùng `eventId`, khác nội dung → CONFLICT; event cũ không đổi; có 1 bản ghi conflict |
| Bắt buộc | Station mismatch hoặc clock skew → REJECTED và **không mở UoW** |
| Bắt buộc | `commit` ném lỗi → exception lan ra, không trả ACCEPTED (ACK sau commit) |
| Bắt buộc | Batch: kết quả đúng thứ tự, item hỏng → REJECTED/INVALID_FORMAT, summary đúng |
| Bắt buộc | History: không đủ quyền → `AccessDenied`; khoảng > 62 ngày → `InvalidQuery` |
| Tuỳ chọn | `outbox.add` ném lỗi → store không có event (rollback) |
| Tuỳ chọn | Batch: item 2 lỗi hạ tầng → item 1 vẫn đã commit |

### API (TestClient + fake) — TV4, TV5

| Mức | Hành vi cần test |
|---|---|
| Bắt buộc | Không có token → 401; envelope `stationId` khác trạm của token → 403 |
| Bắt buộc | 0 event hoặc 501 event → 422; envelope có trường lạ → vẫn 200 (tolerant reader) |
| Bắt buộc | Lô trộn item hợp lệ và item hỏng → 200, kết quả đúng thứ tự; item lỗi có `errors[].field`, không có giá trị đầu vào |
| Bắt buộc | History: thiếu header actor → 401; nhân viên đọc người khác → 403; HR → 200 |
| Bắt buộc | `/health/ready` trả 503 khi probe báo chưa sẵn sàng (đã có) |
| Tuỳ chọn | Use case ném `OperationalError` → 503 |

### Integration (PostgreSQL thật) — TV3, TV5

| Mức | Hành vi cần test |
|---|---|
| Bắt buộc | Contract test `AttendanceWriterContract` chạy với adapter Postgres (cùng bộ test với fake: bằng chứng LSP) |
| Bắt buộc | **Quyền DB**: role app `UPDATE`/`DELETE attendance_event` → `InsufficientPrivilege`; `s4_reporting_reader` đọc được view, không đọc được bảng |
| Bắt buộc | Reader: lọc đúng nhân viên và khoảng thời gian, phân trang không trùng không sót |
| Bắt buộc | `PostgresHealthProbe` true khi DB sống, false nhanh khi sai cổng (đã có) |
| Tuỳ chọn | Migration: upgrade → downgrade base → upgrade không lỗi |
| Tuỳ chọn | Hai thread cùng ghi một event (rào `threading.Barrier`) → đúng 1 ACCEPTED + 1 DUPLICATE |
| Tuỳ chọn | `record_conflict` gọi 2 lần cùng payload → 1 dòng |

### E2E — TV1

| Mức | Kịch bản |
|---|---|
| Bắt buộc | Gửi lô 10 event → 10 ACCEPTED; gửi lại → 10 DUPLICATE; số dòng không đổi |
| Bắt buộc | Gửi lô rồi đọc history bằng actor là nhân viên đó → thấy đúng event |
| Tuỳ chọn | Lô trộn hợp lệ + conflict + skew + hỏng định dạng → đúng 4 status |
| Tuỳ chọn | Role `s4_reporting_reader` đọc view thấy event vừa ACCEPTED |

## 4. Độ phủ

- CI không đo coverage (CI chỉ chạy test, `06-ci-cd.md`).
- Mục tiêu: domain + application ≥ 90% nhánh. Đo ở local khi cần số liệu cho báo cáo: `uv run pytest -m "unit or api" --cov=tmc_attendance.domain --cov=tmc_attendance.application --cov-branch --cov-report=term-missing`.
- Độ phủ là chỉ báo, không phải mục tiêu: một test không có `assert` có ý nghĩa vẫn tăng độ phủ. Reviewer kiểm assert, không kiểm con số.

## 5. Quy ước viết test

- Tên: `test_<hành_vi>_<khi_điều_kiện>`, ví dụ `test_returns_duplicate_when_same_payload_resent`.
- Mỗi test theo Arrange / Act / Assert, một hành vi.
- Dữ liệu tạo bằng `tests/factories.py` (`event_fields`, `event_payload`, sau này `make_event`, `make_command`), không chép JSON dài giữa các test.
- Không `time.sleep` trong unit test; dùng `FixedClock.advance`.
- Mọi test có timeout 30 giây (`pytest-timeout`, cấu hình trong `pyproject.toml`) để không treo CI.
- `filterwarnings = ["error"]`: cảnh báo deprecation làm test fail, ép sửa sớm.

## 6. Kiểm thử thủ công / demo

`scripts/simulate_station.py` (T4.6) — dùng để quay video demo và chụp màn hình cho báo cáo:

```
uv run python scripts/simulate_station.py --station BD-G01-IN --token dev-token-bd-g01-in \
    --count 50 --resend --conflict 2 --skew 1
```

In bảng kết quả theo status và kiểm tổng số dòng trong DB khớp số ACCEPTED.
