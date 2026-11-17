# 01 — Kiến trúc bên trong S3 Attendance

Tài liệu này là hiện thực hoá Hình 7 của báo cáo M1 ("Cấu trúc nội bộ của S3 Attendance"). Tên thành phần trong Hình 7 được giữ nguyên. Những gì bổ sung được liệt kê ở mục 6 kèm lý do.

## 1. Bốn layer và quy tắc phụ thuộc

```
┌─────────────────────────────────────────────────────────────┐
│ bootstrap        composition root: config, tạo adapter,     │
│                  nối vào use case, tạo FastAPI app          │
├─────────────────────────────────────────────────────────────┤
│ adapters                                                     │
│   inbound/http   FastAPI routes, Pydantic DTO, auth header  │
│   outbound/      PostgreSQL, clock, id, station token       │
├─────────────────────────────────────────────────────────────┤
│ application      use case + port (interface do layer này    │
│                  định nghĩa)                                │
├─────────────────────────────────────────────────────────────┤
│ domain           entity, value object, luật nghiệp vụ thuần │
└─────────────────────────────────────────────────────────────┘
     import chỉ được đi xuống. Adapter outbound "hiện thực" port
     của application → mũi tên phụ thuộc mã nguồn trỏ lên port,
     luồng điều khiển đi xuống DB (đúng chú thích Hình 7).
```

Kiểm bằng import-linter (cấu hình ở `07-conventions.md`, mục 3):

1. Layers: `bootstrap` > `adapters` > `application` > `domain`.
2. `domain` cấm import mọi framework/thư viện bên ngoài.
3. `application` cấm `fastapi`, `starlette`, `pydantic`, `sqlalchemy`, `psycopg`, `alembic`, `httpx`, `httpx2`.
4. `adapters.inbound` và `adapters.outbound` độc lập với nhau.

## 2. Cây package đầy đủ

```
services/s3-attendance/
├── pyproject.toml
├── uv.lock
├── .python-version                 # 3.13
├── .env.example
├── alembic.ini
├── Dockerfile
├── .dockerignore
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_create_attendance_schema.py
├── scripts/
│   └── simulate_station.py         # gửi lô sự kiện giả lập, gửi lại, tạo xung đột
├── src/tmc_attendance/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── model.py                # AttendanceEvent, Direction, EvidenceLevel
│   │   ├── values.py               # StationId, PayloadHash, SUPPORTED_SCHEMA_VERSIONS
│   │   ├── dedup.py                # canonical_payload, compute_payload_hash, DeduplicationRule
│   │   ├── policy.py               # EventValidationPolicy, RejectionReason
│   │   ├── access.py               # Role, ActorContext, can_read_history
│   │   └── errors.py               # DomainError, InvalidEvent
│   ├── application/
│   │   ├── __init__.py
│   │   ├── ports.py                # mọi port (mục 3)
│   │   ├── dto.py                  # IngestEventCommand, InvalidItem, IngestResult, ...
│   │   ├── ingest_event.py         # IngestAttendanceEventUseCase
│   │   ├── ingest_batch.py         # IngestAttendanceBatchUseCase
│   │   └── history.py              # GetAttendanceHistoryUseCase
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── inbound/
│   │   │   ├── __init__.py
│   │   │   └── http/
│   │   │       ├── __init__.py
│   │   │       ├── app.py          # create_app(deps: ApiDependencies) -> FastAPI
│   │   │       ├── dependencies.py # ApiDependencies, get_api_dependencies (adapter tự khai báo thứ nó cần)
│   │   │       ├── ingest.py       # EventIngestController (router)
│   │   │       ├── history.py      # router đọc lịch sử
│   │   │       ├── health.py       # /health/live, /health/ready
│   │   │       ├── schemas.py      # Pydantic DTO, camelCase alias
│   │   │       ├── security.py     # đọc Bearer token, actor header
│   │   │       └── errors.py       # exception handler: 422 không lộ giá trị đầu vào, 503 khi DB lỗi
│   │   └── outbound/
│   │       ├── __init__.py
│   │       ├── persistence/
│   │       │   ├── __init__.py
│   │       │   ├── tables.py       # SQLAlchemy Core Table
│   │       │   ├── unit_of_work.py # SqlAlchemyUnitOfWork
│   │       │   ├── attendance_repository.py   # PostgresAttendanceRepository
│   │       │   ├── attendance_queries.py      # PostgresAttendanceQueries
│   │       │   ├── outbox.py       # PostgresOutbox
│   │       │   └── health.py       # PostgresHealthProbe
│   │       ├── clock.py            # SystemClock
│   │       ├── ids.py              # Uuid4Generator
│   │       └── station_auth.py     # StaticTokenStationAuthenticator
│   └── bootstrap/
│       ├── __init__.py
│       ├── config.py               # Settings, DatabaseAdminSettings (pydantic-settings)
│       ├── container.py            # build_api_dependencies(settings), wire_api_dependencies(engine, settings)
│       └── main.py                 # app = create_app(build_api_dependencies(Settings()))
└── tests/
    ├── conftest.py                 # gán marker theo thư mục, fixture DB
    ├── fakes.py                    # fake cho mọi port
    ├── factories.py                # tạo AttendanceEvent / command hợp lệ
    ├── contracts/                  # bộ test hợp đồng dùng chung cho fake và adapter thật (LSP)
    ├── unit/
    │   ├── domain/
    │   └── application/
    ├── api/                        # TestClient + ApiDependencies dựng từ fake
    ├── integration/                # adapter thật + PostgreSQL thật
    └── e2e/                        # TestClient + wire_api_dependencies thật + PostgreSQL
```

## 3. Port (định nghĩa trong `application/ports.py`)

Ký hiệu dưới đây là đặc tả, không phải code hoàn chỉnh. Mọi port là `abc.ABC`.

```python
class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...          # luôn aware, UTC

class IdGenerator(ABC):
    @abstractmethod
    def new_id(self) -> UUID: ...           # dùng cho outbox message, conflict record

# --- kết quả của AttendanceWriter.insert_if_absent (tagged union) ---
@dataclass(frozen=True, slots=True)
class Inserted: ...

@dataclass(frozen=True, slots=True)
class EventIdExists:
    existing_hash: PayloadHash

InsertOutcome = Inserted | EventIdExists

class AttendanceWriter(ABC):                # tên từ Hình 7
    @abstractmethod
    def insert_if_absent(
        self, event: AttendanceEvent, payload_hash: PayloadHash, received_at: datetime
    ) -> InsertOutcome: ...
    @abstractmethod
    def record_conflict(self, conflict: EventConflict) -> None: ...

class OutboxPort(ABC):                      # tên từ Hình 7
    @abstractmethod
    def add(self, message: OutboxMessage) -> None: ...

class UnitOfWork(ABC):
    attendance: AttendanceWriter
    outbox: OutboxPort
    def __enter__(self) -> Self: ...        # mở transaction
    def __exit__(self, *exc: object) -> None: ...   # rollback nếu chưa commit
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...

UnitOfWorkFactory = Callable[[], UnitOfWork]

class AttendanceReader(ABC):                # tách khỏi Writer theo ISP
    @abstractmethod
    def list_by_employee(
        self,
        employee_ref: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        limit: int,
        offset: int,
    ) -> HistoryPage: ...

class StationAuthenticator(ABC):
    @abstractmethod
    def authenticate(self, bearer_token: str) -> AuthenticatedStation | None: ...

class HealthProbe(ABC):
    @abstractmethod
    def is_ready(self) -> bool: ...
```

`UnitOfWork.__enter__()` mặc định trả về chính đối tượng.
Adapter có thể override để mở connection và transaction.

`UnitOfWork.__exit__()` luôn gọi `rollback()` để dọn thay đổi
chưa commit và không suppress exception.

Hợp đồng `rollback()`:
- Bỏ các thay đổi đang chờ trong transaction.
- Nếu không còn thay đổi đang chờ, thao tác không làm gì.
- Không được xóa hoặc hoàn tác dữ liệu đã commit.

Adapter persistence phải bảo đảm đóng connection khi thoát context,
kể cả khi có exception. Fake và adapter PostgreSQL phải tuân thủ
cùng hợp đồng về commit và rollback.

## 4. Use case

### 4.1 `IngestAttendanceEventUseCase`

Phụ thuộc (qua constructor): `UnitOfWorkFactory`, `Clock`, `IdGenerator`, `EventValidationPolicy`, `DeduplicationRule`.

```
execute(cmd: IngestEventCommand, station: AuthenticatedStation) -> IngestResult

 1. received_at = clock.now()
 2. Dựng AttendanceEvent từ cmd.
   InvalidEvent với field="schemaVersion"
     → REJECTED(UNSUPPORTED_SCHEMA_VERSION)
   InvalidEvent khác
     → REJECTED(INVALID_FORMAT)
 3. event.station_id != station.station_id → REJECTED(STATION_MISMATCH)
 4. reason = policy.check(event, received_at); có reason → REJECTED(reason)
 5. h = compute_payload_hash(event)
 6. with uow_factory() as uow:
      outcome = uow.attendance.insert_if_absent(event, h, received_at)
      Inserted        → uow.outbox.add(AttendanceEventAccepted v1)
                        uow.commit()                → ACCEPTED
      EventIdExists   → rule.decide(h, existing_hash)
                          DUPLICATE → không thêm event/outbox
                                    → uow.commit()
                                    → trả DUPLICATE
                          CONFLICT  → uow.attendance.record_conflict(PAYLOAD_MISMATCH)
                                      uow.commit()  → CONFLICT(PAYLOAD_MISMATCH)
 7. Lỗi hạ tầng (DB mất kết nối...) không bị nuốt: exception đi lên adapter → HTTP 503.
```

Bước 2–4 không mở transaction: event bị từ chối không chạm DB. Bước 6: return chỉ xảy ra **sau** `commit()` → đúng bất biến "ACK sau commit".

### 4.2 `IngestAttendanceBatchUseCase`

Phụ thuộc: `IngestAttendanceEventUseCase` (composition, không kế thừa).

```
execute(items: Sequence[IngestEventCommand | InvalidItem], station) -> BatchResult
  với mỗi item theo thứ tự:
    InvalidItem          → IngestResult(REJECTED, INVALID_FORMAT, index, event_id thô nếu đọc được)
    IngestEventCommand   → single.execute(item, station)
  trả BatchResult(results theo đúng thứ tự, summary đếm theo status)
```

Mỗi event một transaction riêng: một event lỗi không kéo cả lô thất bại; nếu DB chết giữa lô, các event trước đã commit, Sync Worker gửi lại cả lô và các event đó trở thành `DUPLICATE`. Lý do chọn: `docs/adr-impl/IADR-005-per-item-batch-semantics.md`.

### 4.3 `GetAttendanceHistoryUseCase`

Phụ thuộc: `AttendanceReader`, `Clock`.

```
execute(query: HistoryQuery, actor: ActorContext) -> HistoryPage
  1. can_read_history(actor, query.employee_ref) sai → raise AccessDenied
  2. khoảng [from, to): to - from ≤ 62 ngày, from < to → sai thì raise InvalidQuery
  3. limit trong [1, 200], mặc định 50; offset ≥ 0, mặc định 0
  4. reader.list_by_employee(...)
```

`AccessDenied` và `InvalidQuery` là exception của application (khác kết quả ingest), vì với một truy vấn đơn lẻ chúng thật sự là trường hợp "không thể phục vụ".

## 5. Adapter

| Adapter | Hiện thực port | Ghi chú |
|---|---|---|
| `EventIngestController` (`adapters/inbound/http/ingest.py`) | — (inbound) | Parse envelope chặt, parse từng item mềm → `IngestEventCommand` hoặc `InvalidItem` |
| router history, health | — (inbound) | |
| `PostgresAttendanceRepository` | `AttendanceWriter` | `INSERT ... ON CONFLICT DO NOTHING RETURNING`, xem `04-database.md` mục 4 |
| `PostgresAttendanceQueries` | `AttendanceReader` | `LIMIT`/`OFFSET` (`04-database.md` §8) |
| `PostgresOutbox` | `OutboxPort` | |
| `SqlAlchemyUnitOfWork` | `UnitOfWork` | một `Connection` + một transaction; tạo repository/outbox dùng chung connection |
| `SystemClock` | `Clock` | `datetime.now(UTC)` — nơi duy nhất trong `src/` gọi hàm này |
| `Uuid4Generator` | `IdGenerator` | |
| `StaticTokenStationAuthenticator` | `StationAuthenticator` | so sha256 bằng `hmac.compare_digest` |
| `PostgresHealthProbe` | `HealthProbe` | `SELECT 1`, timeout ngắn |

## 6. So với Hình 7 của báo cáo M1

| Thành phần | Có trong Hình 7 | Lý do bổ sung | Cần cập nhật báo cáo |
|---|---|---|---|
| `UnitOfWork` | Không | Hình 7 có `AttendanceWriter` và `OutboxPort` riêng nhưng ranh giới giao dịch ở Bước 4 (M1) đòi hai việc ghi đó chung một transaction. Cần một port biểu diễn ranh giới đó để use case không biết tới connection | Có — thêm vào Hình 7 |
| `AttendanceReader` | Không | UC09 cần đọc; tách khỏi Writer theo ISP (DP08) | Có |
| `StationAuthenticator` | Không | ADR07: xác thực thiết bị độc lập với logic nghiệp vụ | Có |
| `IdGenerator` | Không | Test tất định cho outbox/conflict id | Không bắt buộc (chi tiết hiện thực) |
| `IngestAttendanceBatchUseCase` | Không | Sync Worker gửi theo lô (Hình 4 M1, bước [03]) | Có |
| `GetAttendanceHistoryUseCase` | Không | UC09 | Có |
| `EventValidationPolicy` | Không | Kiểm độ lệch đồng hồ (M1 chương 6, bước 6: "tuổi policy và độ lệch đồng hồ") | Có |

Tech lead cập nhật lại Hình 7 (PlantUML) cho báo cáo M2 khi Phase 2 xong.

## 7. Composition root

Ai khai báo cái gì:

- **Adapter HTTP tự khai báo thứ nó cần** trong `adapters/inbound/http/dependencies.py`: dataclass `ApiDependencies` chỉ chứa port và use case (kiểu của `application`), cộng vài giá trị đơn giản như `max_batch_size`.
- **`bootstrap` đáp ứng nhu cầu đó**: `build_api_dependencies(settings)` tạo engine rồi gọi `wire_api_dependencies(engine, settings)` để nối mọi adapter thật. E2E gọi thẳng `wire_api_dependencies` với engine của fixture, nên test chạy đúng cách nối dây của production.

Lý do không đặt `Container` ở `bootstrap` rồi truyền vào `create_app`: khi đó `adapters` phải import `bootstrap` để biết kiểu, tức là import ngược layer, và contract layers của import-linter sẽ báo lỗi. Để adapter định nghĩa "hợp đồng" còn composition root hiện thực nó là DIP áp dụng cho chính việc nối dây.

```python
# adapters/inbound/http/dependencies.py
@dataclass(frozen=True, slots=True)
class ApiDependencies:
    health: HealthProbe
    station_authenticator: StationAuthenticator | None = None   # None → route trả 503
    ingest_batch: IngestAttendanceBatchUseCase | None = None
    max_batch_size: int = 500
    history: GetAttendanceHistoryUseCase | None = None

def get_api_dependencies(request: Request) -> ApiDependencies: ...   # đọc app.state

# bootstrap/container.py
def build_api_dependencies(settings: Settings) -> ApiDependencies:
    return wire_api_dependencies(create_app_engine(settings), settings)

def wire_api_dependencies(engine: Engine, settings: Settings) -> ApiDependencies:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(engine)
    ingest_event = IngestAttendanceEventUseCase(
        uow_factory, SystemClock(), Uuid4Generator(),
        EventValidationPolicy(timedelta(seconds=settings.max_future_skew_seconds)),
        DeduplicationRule(),
    )
    return ApiDependencies(
        health=PostgresHealthProbe(engine),
        station_authenticator=StaticTokenStationAuthenticator(settings.station_tokens),
        ingest_batch=IngestAttendanceBatchUseCase(ingest_event),
        max_batch_size=settings.max_batch_size,
        history=GetAttendanceHistoryUseCase(PostgresAttendanceQueries(engine)),
    )
```

Các trường của `ApiDependencies` để `| None` để test API chỉ cần dựng phần mình dùng. Production không bao giờ để trống: `tests/unit/test_bootstrap.py::test_build_api_dependencies_wires_every_dependency` kiểm mọi trường đều đã được nối.

`adapters/inbound/http/app.py`: `create_app(deps: ApiDependencies) -> FastAPI` gắn `deps` vào `app.state.api_dependencies`; route lấy qua `Depends(get_api_dependencies)`. Test API dựng `ApiDependencies` từ fake rồi gọi `create_app`, không cần monkeypatch.

`bootstrap/main.py` chỉ có: cấu hình logging stdlib (`logging.basicConfig`, T4.1), `Settings()`, `build_api_dependencies`, `create_app`. Không có logic.

## 8. Luồng một request ingest (component-and-connector)

```
Sync Worker ──HTTPS POST /v1/attendance-event-batches──▶ FastAPI
   ▶ security: Bearer → StationAuthenticator → AuthenticatedStation | 401
   ▶ EventIngestController: envelope.stationId == station? | 403
       parse item i → IngestEventCommand | InvalidItem
   ▶ IngestAttendanceBatchUseCase
       ▶ IngestAttendanceEventUseCase (mỗi item)
           ▶ UnitOfWork ─▶ PostgresAttendanceRepository ─▶ attendance.attendance_event
                        └▶ PostgresOutbox                ─▶ attendance.outbox
   ◀ BatchResult ◀ 200 {results, summary}
```

Đây là nguyên liệu cho component-and-connector view trong báo cáo M2 (xem `12-report-mapping.md`).

## 9. Hợp đồng DTO của Application

DTO nằm trong `application/dto.py`, dùng dataclass frozen và slots.
Tên field nội bộ là snake_case; adapter HTTP chuyển sang camelCase.

- `IngestEventCommand` chứa chín field chuẩn của sự kiện.
  Command không kiểm các bất biến nghiệp vụ; use case dựng
  `AttendanceEvent` để kiểm tra.
- `AuthenticatedStation` chứa `station_id` đã được xác thực,
  không chứa token thô.
- `FieldError` chứa `field` và `message`, không chứa giá trị
  đầu vào nhạy cảm.
- `InvalidItem` chứa các lỗi parse đã làm sạch và `event_id`
  hợp lệ nếu đọc được; nếu không thì `event_id=None`.
- `IngestResult` chứa `event_id`, `status`, `reason`, `errors`
  và `index`. Single-event use case để `index=None`;
  batch use case gán index theo thứ tự đầu vào.
- `reason` nhận `RejectionReason`, `ConflictKind` hoặc None.
- `BatchResult.results` giữ đúng thứ tự đầu vào.
  `BatchSummary` đếm accepted, duplicate, conflict và rejected.
- `EventConflict` giữ bằng chứng payload/hash xung đột;
  không thay thế hoặc sửa event gốc.
- `OutboxMessage` được ghi cùng transaction với event mới.
  `aggregate_id` là event_id; `occurred_at` là received_at.
- `HistoryQuery` dùng khoảng thời gian
  `[occurred_from, occurred_to)`, limit mặc định 50,
  offset mặc định 0.
- `HistoryPage` chứa items theo thứ tự ổn định và has_more.
- `AttendanceEventView` cung cấp các field cần cho API
  lịch sử, gồm occurred_at và received_at.

Các collection kết quả dùng tuple.
Mapping trong payload là hợp đồng chỉ đọc; frozen dataclass
không tự đóng băng dict bên trong, nên bên tạo không được
sửa payload sau khi bàn giao.

`AccessDenied` và `InvalidQuery` nằm trong
`application/errors.py`. Adapter HTTP chịu trách nhiệm
chuyển chúng thành HTTP response.
