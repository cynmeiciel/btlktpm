# 02 — Kiến trúc code, giải thích từ đầu

## 1. Ví dụ quán ăn

Hãy tưởng tượng S3 là một quán ăn:

| Trong quán | Trong code | Thư mục |
|---|---|---|
| **Công thức món ăn**: luật không đổi, không quan tâm bếp ga hay bếp điện | **domain**: luật nghiệp vụ thuần (sự kiện hợp lệ là gì, khi nào là trùng) | `domain/` |
| **Bếp trưởng**: điều phối các bước nấu một món, gọi "lấy nguyên liệu", "cất vào tủ" mà không quan tâm tủ hãng nào | **application**: use case, các bước xử lý một yêu cầu | `application/` |
| **Phục vụ** (nhận order từ khách) và **nhà cung cấp, tủ lạnh** (đồ thật bên ngoài) | **adapters**: HTTP (nhận request), PostgreSQL (lưu trữ), đồng hồ hệ thống | `adapters/inbound/`, `adapters/outbound/` |
| **Quản lý**: sáng mở cửa, xếp ai đứng đâu, nối mọi thứ lại | **bootstrap**: đọc cấu hình, tạo adapter, gắn vào use case, khởi động app | `bootstrap/` |

Điểm mấu chốt: **công thức không phụ thuộc vào bếp**. Đổi bếp ga sang bếp điện thì công thức không đổi. Tương tự, đổi PostgreSQL sang DB khác hay đổi FastAPI sang framework khác thì `domain/` và `application/` không phải sửa một dòng nào.

## 2. Quy tắc import: chỉ được nhìn xuống

```
bootstrap   ──▶ được import mọi thứ bên dưới
adapters    ──▶ được import application, domain
application ──▶ chỉ được import domain (và thư viện chuẩn Python)
domain      ──▶ chỉ thư viện chuẩn Python
```

```python
# ✅ trong application/ingest_event.py
from tmc_attendance.domain.model import AttendanceEvent

# ❌ trong application/ingest_event.py: application không được biết DB là gì
from sqlalchemy import insert

# ❌ trong domain/model.py: domain không được biết web framework
from pydantic import BaseModel
```

Bạn không cần tự nhớ. Lệnh `uv run lint-imports` (có trong `uv run scripts/dev.py check` và CI) sẽ báo lỗi nếu import sai. Đây là **Luật 1**.

> Câu hỏi tự nhiên: *"application cần lưu vào DB, mà không được import thư viện DB, vậy lưu kiểu gì?"* Câu trả lời là **port**, xem mục tiếp theo.

## 3. Port và adapter: ổ cắm và phích cắm

- **Port** là một *ổ cắm*: một lớp trừu tượng (`abc.ABC`) chỉ khai báo "cần làm được gì", không viết cách làm. Port nằm ở `application/ports.py`.
- **Adapter** là *phích cắm*: lớp cụ thể kế thừa port và làm việc thật (gọi PostgreSQL, đọc đồng hồ máy…). Adapter nằm ở `adapters/`.

Ví dụ nhỏ nhất là đồng hồ:

```python
# application/ports.py: ổ cắm
from abc import ABC, abstractmethod
from datetime import datetime

class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...
```

```python
# adapters/outbound/clock.py: phích cắm thật, dùng khi chạy app
from datetime import UTC, datetime
from tmc_attendance.application.ports import Clock

class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)
```

```python
# tests/fakes.py: phích cắm giả, dùng khi test
class FixedClock(Clock):
    def __init__(self, at: datetime) -> None:
        self._at = at
    def now(self) -> datetime:
        return self._at
```

Use case chỉ biết `Clock`, không biết đang cắm phích nào:

```python
class IngestAttendanceEventUseCase:
    def __init__(self, clock: Clock, ...) -> None:   # nhận "ổ cắm" qua constructor
        self._clock = clock

    def execute(self, ...):
        received_at = self._clock.now()
```

**Lợi ích thấy ngay:** khi test, ta cắm `FixedClock(07:58)` thì kết quả luôn giống nhau, không phụ thuộc giờ chạy test. Đó là lý do có **Luật 7: chỉ lấy thời gian qua `Clock`**. Nếu use case gọi thẳng `datetime.now()` thì không cách nào test được trường hợp "sự kiện đến từ tương lai 10 phút".

Việc *truyền* phích cắm vào qua constructor (thay vì để class tự tạo) gọi là **dependency injection**. Việc *chọn* phích nào cắm vào đâu chỉ xảy ra ở một chỗ duy nhất: `bootstrap/container.py`, gọi là **composition root**.

### Các port của S3

| Port | Làm gì | Adapter thật | Fake khi test |
|---|---|---|---|
| `Clock` | Cho biết bây giờ là mấy giờ | `SystemClock` | `FixedClock` |
| `IdGenerator` | Sinh UUID mới (cho outbox, conflict) | `Uuid4Generator` | `SequentialIdGenerator` |
| `AttendanceWriter` | Lưu sự kiện, ghi xung đột | `PostgresAttendanceRepository` | `InMemoryAttendanceStore` |
| `OutboxPort` | Ghi tin báo vào outbox | `PostgresOutbox` | `InMemoryOutbox` |
| `UnitOfWork` | Gói nhiều việc ghi vào **một transaction** | `SqlAlchemyUnitOfWork` | `InMemoryUnitOfWork` |
| `AttendanceReader` | Đọc lịch sử | `PostgresAttendanceQueries` | `InMemoryAttendanceReader` |
| `StationAuthenticator` | Kiểm token của trạm | `StaticTokenStationAuthenticator` | `FakeStationAuthenticator` |
| `HealthProbe` | DB còn sống không | `PostgresHealthProbe` | `FakeHealthProbe` |

### Unit of Work là gì

`UnitOfWork` (UoW) là "một phiên làm việc với DB". Mọi thứ ghi trong một UoW chỉ thực sự được lưu khi gọi `commit()`. Thoát ra mà chưa commit thì tất cả bị huỷ.

```python
with uow_factory() as uow:                      # mở transaction
    outcome = uow.attendance.insert_if_absent(event, h, received_at)
    if isinstance(outcome, Inserted):
        uow.outbox.add(message)                 # cùng transaction với dòng trên
        uow.commit()                            # cả hai cùng được lưu
        return accepted                         # chỉ trả lời SAU commit (Luật 2)
# thoát khối with mà chưa commit → rollback tự động
```

Đoạn này thể hiện cùng lúc **Luật 2** (ACK sau commit) và **Luật 5** (event và outbox cùng transaction).

## 4. Theo chân một request

Khi trạm gửi `POST /v1/attendance-event-batches`, request đi qua các file sau (tên file theo `../01-kien-truc-s3.md` §2):

| # | File | Làm gì | Ai viết |
|---|---|---|---|
| 1 | `adapters/inbound/http/security.py` | Đọc header `Authorization: Bearer ...`, hỏi `StationAuthenticator` đây là trạm nào. Sai thì trả 401 | TV4 |
| 2 | `adapters/inbound/http/schemas.py` | Pydantic kiểm JSON đúng dạng chưa (thiếu trường, sai kiểu thì trả 422) | TV4 |
| 3 | `adapters/inbound/http/ingest.py` | `EventIngestController`: đổi JSON thành `IngestEventCommand` (dataclass thuần, không phải Pydantic), gọi use case | TV4 |
| 4 | `application/ingest_batch.py` | Duyệt từng sự kiện trong lô, gọi use case đơn | TV2 |
| 5 | `application/ingest_event.py` | Dựng `AttendanceEvent`, kiểm luật, tính hash, mở UoW, lưu, quyết định kết quả | TV2 |
| 6 | `domain/model.py`, `dedup.py`, `policy.py` | Luật thuần: sự kiện hợp lệ? trùng hay xung đột? lệch giờ? | TV2 |
| 7 | `adapters/outbound/persistence/*.py` | Câu SQL thật: `INSERT ... ON CONFLICT DO NOTHING` | TV3 |
| 8 | quay ngược về 3 | Đổi kết quả thành JSON, trả `200 {results, summary}` | TV4 |

Chú ý bước 3: **model Pydantic dừng lại ở layer adapter.** Use case nhận dataclass thuần, nên đổi framework web thì use case không phải sửa.

## 5. SOLID nằm ở đâu

Đề M2 yêu cầu code tuân SOLID. Dưới đây là cách nhận ra từng nguyên lý trong code của mình. Chi tiết và bằng chứng ở `../11-solid-mapping.md`.

| Nguyên lý | Ý nghĩa ngắn | Trong S3 |
|---|---|---|
| **S**: Single Responsibility | Mỗi class chỉ có một lý do để sửa | `DeduplicationRule` chỉ quyết định trùng hay xung đột; `EventValidationPolicy` chỉ kiểm lệch giờ. Đổi luật nào thì sửa đúng một chỗ |
| **O**: Open/Closed | Thêm tính năng bằng cách thêm class, không sửa class cũ | Muốn xác thực trạm bằng mTLS: viết adapter mới cho `StationAuthenticator`, use case không đổi |
| **L**: Liskov Substitution | Thay adapter này bằng adapter khác cùng port mà chương trình vẫn đúng | Fake và adapter Postgres chạy **cùng một bộ test** (contract test). Cả hai qua là chứng minh thay thế được |
| **I**: Interface Segregation | Không bắt ai phụ thuộc vào thứ họ không dùng | `AttendanceReader` tách khỏi `AttendanceWriter`: use case đọc lịch sử không thấy hàm ghi |
| **D**: Dependency Inversion | Code cấp cao phụ thuộc vào trừu tượng, không vào chi tiết | Use case phụ thuộc `Clock`, `UnitOfWork` (port), không phụ thuộc PostgreSQL. import-linter kiểm điều này |

## 6. Ba kiểu kết quả và lỗi

Phân biệt rõ để không dùng exception lung tung:

| Tình huống | Cách biểu diễn | Ví dụ |
|---|---|---|
| Kết quả nghiệp vụ *bình thường* (kể cả bị từ chối) | **Giá trị trả về** | `IngestResult(status=DUPLICATE)` |
| Dữ liệu vi phạm luật domain | Exception `InvalidEvent` | `occurred_at` không có múi giờ |
| Hạ tầng hỏng | Để exception gốc bay lên, HTTP đổi thành 503 | Mất kết nối DB |

Không bao giờ viết `except Exception: pass`, vì làm vậy là giấu lỗi.

Tiếp theo: cài môi trường (`../10-local-setup.md`), rồi [04-git-tung-buoc.md](04-git-tung-buoc.md) và [05-viet-code-va-test.md](05-viet-code-va-test.md).
