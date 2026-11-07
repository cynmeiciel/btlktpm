# 02 — Domain model của S3

Mọi thứ trong tài liệu này sống ở `tmc_attendance.domain` và chỉ dùng stdlib.

## 1. Enum

```python
class Direction(StrEnum):
    IN = "IN"
    OUT = "OUT"

class EvidenceLevel(StrEnum):            # tên từ Hình 7 M1
    CONTROLLER_CONFIRMED = "CONTROLLER_CONFIRMED"
    CONTROLLER_UNCONFIRMED = "CONTROLLER_UNCONFIRMED"
    GUARD_RECORDED = "GUARD_RECORDED"
```

Ý nghĩa `EvidenceLevel` (đề xuất — cần nhóm xác nhận, xem `13-open-questions.md` Q1):

| Giá trị | Khi nào trạm gán | Nguồn trong M1 |
|---|---|---|
| `CONTROLLER_CONFIRMED` | `GateCommand = succeeded` | Hình 3, bước [12] |
| `CONTROLLER_UNCONFIRMED` | `GateCommand = unknown` (controller không trả lời trong deadline) | Hình 5, tình huống 1: "AttendanceEvent chưa xác nhận → hàng đợi ngoại lệ" |
| `GUARD_RECORDED` | Bảo vệ ghi nhận ngoại lệ tại cổng | UC08 |

S3 không suy luận lại mức bằng chứng; nó lưu đúng giá trị trạm gửi. Việc S4 xử lý `CONTROLLER_UNCONFIRMED` thế nào khi làm báo cáo là chuyện của S4.

```python
class IngestStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"

class RejectionReason(StrEnum):
    INVALID_FORMAT = "INVALID_FORMAT"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    CLOCK_SKEW = "CLOCK_SKEW"
    STATION_MISMATCH = "STATION_MISMATCH"

class ConflictKind(StrEnum):
    PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"   # để là enum để sau này thêm loại xung đột khác dễ dàng
```

`IngestStatus`, `RejectionReason`, `ConflictKind` đặt ở `domain/policy.py` và `domain/dedup.py` (cùng file với luật sinh ra chúng).

## 2. Value object

| Tên | Kiểu | Bất biến |
|---|---|---|
| `StationId` | `NewType("StationId", str)` + hàm `parse_station_id(s) -> StationId` | 1–64 ký tự, regex `^[A-Za-z0-9_-]+$` |
| `PayloadHash` | `NewType("PayloadHash", str)` | 64 ký tự hex thường |
| `SUPPORTED_SCHEMA_VERSIONS` | `frozenset[int]` | `{1}` |

UUID dùng thẳng `uuid.UUID`, không bọc.

## 3. Entity `AttendanceEvent`

```python
@dataclass(frozen=True, slots=True)
class AttendanceEvent:
    event_id: UUID
    attempt_id: UUID
    employee_ref: UUID
    station_id: StationId
    direction: Direction
    occurred_at: datetime
    local_sequence: int
    evidence_level: EvidenceLevel
    schema_version: int = 1
```

Bất biến kiểm trong `__post_init__`, vi phạm → `InvalidEvent(field, message)`:

1. `occurred_at.tzinfo is not None` và `occurred_at.utcoffset() is not None`.
2. `local_sequence >= 0`.
3. `station_id` đúng định dạng `StationId`.
4. `schema_version in SUPPORTED_SCHEMA_VERSIONS` — vi phạm ném `InvalidEvent` với `field="schemaVersion"`; use case đổi lý do thành `UNSUPPORTED_SCHEMA_VERSION` thay vì `INVALID_FORMAT`.

Không chuẩn hoá `occurred_at` về UTC trong entity (frozen + slots làm việc gán lại vụng về và không cần): chuẩn hoá xảy ra khi tính hash và khi adapter ghi DB (`timestamptz` tự lưu UTC).

`received_at` **không** thuộc entity: đó là dữ kiện của S3 về lúc nhận, không phải dữ kiện của sự kiện. Nó đi kèm khi ghi (`insert_if_absent(event, hash, received_at)`).

Khớp ERD Hình 2 M1 (`AttendanceEvent`: event_id, attempt_id, employee_ref, station_id, direction, occurred_at, received_at, local_sequence, evidence_level). Thêm `schema_version` và `payload_hash` ở mức lưu trữ — xem `04-database.md`.

## 4. Payload hash chuẩn hoá

Dùng để phân biệt "gửi lại đúng sự kiện cũ" (duplicate) với "dùng lại eventId cho nội dung khác" (conflict).

`canonical_payload(event) -> bytes`:

1. Dựng dict với đúng các khoá sau (tên camelCase để khớp với dữ liệu trạm gửi):
   `eventId, attemptId, employeeRef, stationId, direction, occurredAt, localSequence, evidenceLevel, schemaVersion`
2. Giá trị:
   - UUID → `str(uuid)` (chữ thường, có gạch nối).
   - `occurredAt` → `event.occurred_at.astimezone(UTC).isoformat(timespec="microseconds")`, ví dụ `2026-11-03T00:58:12.345000+00:00`.
   - enum → `.value`; số nguyên → int.
3. `json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.

`compute_payload_hash(event) -> PayloadHash` = `hashlib.sha256(canonical_payload(event)).hexdigest()`.

Hệ quả cần có test:

- `07:58:12.345+07:00` và `00:58:12.345Z` cùng một thời điểm → cùng hash.
- Đổi bất kỳ trường nào trong 9 trường → hash khác.
- `received_at` khác nhau → hash giống nhau.

**Đổi công thức này sau khi đã có dữ liệu là breaking change**: mọi lần gửi lại event cũ sẽ bị coi là conflict. Muốn đổi phải tăng `schemaVersion`.

## 5. `DeduplicationRule`

```python
class DedupDecision(StrEnum):
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"

class DeduplicationRule:
    def decide(self, incoming: PayloadHash, existing: PayloadHash) -> DedupDecision:
        return DUPLICATE if hmac.compare_digest(incoming, existing) else CONFLICT
```

Luật nhỏ nhưng là luật nghiệp vụ có tên trong Hình 7 và ADR04 (quy tắc 5 và 6): "Nếu sự kiện đã tồn tại và payload giống nhau, trả về duplicate. Nếu eventId đã được sử dụng nhưng payload khác, xem đây là conflict và chuyển đi điều tra; không ghi đè bản ghi cũ." Để nó thành class (không phải `if` trong use case) cho phép đổi luật (ví dụ coi khác biệt chỉ ở `evidenceLevel` là nâng cấp bằng chứng) mà không sửa use case — OCP.

Phần **bảo đảm** tính duy nhất nằm ở DB (PK), không ở class này. Class này chỉ phân loại khi DB đã báo trùng.

## 6. `EventValidationPolicy`

```python
class EventValidationPolicy:
    def __init__(self, max_future_skew: timedelta) -> None: ...
    def check(self, event: AttendanceEvent, received_at: datetime) -> RejectionReason | None:
        if event.occurred_at > received_at + self._max_future_skew:
            return RejectionReason.CLOCK_SKEW
        return None
```

- Chỉ chặn sự kiện **ở tương lai** quá ngưỡng (mặc định 300 giây): dấu hiệu đồng hồ trạm sai hoặc dữ liệu giả.
- **Không** chặn sự kiện cũ. Trạm có thể mất WAN 4 giờ (giả định A2 M1) hoặc lâu hơn khi sự cố; từ chối sự kiện cũ là làm mất dữ liệu, trái NFR-2. Sự kiện tới muộn sau khi kỳ đã chốt là việc của S4 (ADR06: supplemental batch).

## 7. Quyền đọc lịch sử (`domain/access.py`)

```python
class Role(StrEnum):
    EMPLOYEE = "EMPLOYEE"; SUPERVISOR = "SUPERVISOR"; HR = "HR"
    SECURITY = "SECURITY"; ADMIN = "ADMIN"; EXECUTIVE = "EXECUTIVE"

@dataclass(frozen=True, slots=True)
class ActorContext:
    actor_id: UUID
    employee_ref: UUID | None
    roles: frozenset[Role]

def can_read_history(actor: ActorContext, target: UUID) -> bool:
    return actor.employee_ref == target or Role.HR in actor.roles
```

- Nhân viên chỉ đọc của chính mình (UC09, "phạm vi dữ liệu giới hạn ở bản thân").
- HR đọc được của mọi người (cần cho UC11 đối soát).
- `ADMIN` **không** đọc được: báo cáo M1 ghi quản trị viên "không mặc nhiên có quyền sửa dữ liệu chấm công", ADR07 least privilege.
- `SUPERVISOR` chưa được phép trong M2: phạm vi "phân xưởng được giao" cần dữ liệu tổ chức mà S3 không có. Xem `13-open-questions.md` Q4.

## 8. Các bản ghi khác

```python
@dataclass(frozen=True, slots=True)
class EventConflict:          # application/dto.py
    conflict_id: UUID
    event_id: UUID
    station_id: StationId
    kind: ConflictKind
    incoming_payload: Mapping[str, object]   # dict từ canonical_payload, để điều tra
    incoming_hash: PayloadHash
    detected_at: datetime

@dataclass(frozen=True, slots=True)
class OutboxMessage:          # application/dto.py
    message_id: UUID
    aggregate_id: UUID                       # = event_id
    message_type: str                        # "AttendanceEventAccepted.v1"
    payload: Mapping[str, object]
    occurred_at: datetime                    # = received_at
```

Payload của `AttendanceEventAccepted.v1`:
`eventId, employeeRef, stationId, direction, occurredAt (ISO UTC), evidenceLevel, receivedAt (ISO UTC)`.
Không chứa `attemptId`, `localSequence`, `payloadHash` — đó là chi tiết nội bộ của S3.

## 9. Ma trận quyết định ingest

| Điều kiện | Status | Reason | Ghi DB |
|---|---|---|---|
| Item không parse được (thiếu trường, sai kiểu, UUID hỏng) | REJECTED | INVALID_FORMAT | Không |
| Bất biến entity sai | REJECTED | INVALID_FORMAT | Không |
| `schemaVersion` không hỗ trợ | REJECTED | UNSUPPORTED_SCHEMA_VERSION | Không |
| `stationId` của item ≠ trạm đã xác thực | REJECTED | STATION_MISMATCH | Không |
| `occurredAt` > nhận + 300s | REJECTED | CLOCK_SKEW | Không |
| `eventId` mới | ACCEPTED | — | event + outbox |
| `eventId` đã có, hash bằng | DUPLICATE | — | Không |
| `eventId` đã có, hash khác | CONFLICT | PAYLOAD_MISMATCH | event_conflict |

Không kiểm trùng `(stationId, localSequence)` trong M2: đó là ca hiếm (lỗi phần mềm trạm) và làm logic ghi phức tạp gấp đôi. `localSequence` vẫn được lưu để điều tra sau. Nếu cần, thêm ràng buộc UNIQUE và loại xung đột mới ở một migration sau.

Hành vi Sync Worker tương ứng (ghi vào hợp đồng API): ACCEPTED/DUPLICATE → đánh dấu đã đồng bộ; CONFLICT/REJECTED → giữ lại tại trạm, cách ly, cảnh báo; không gửi lại nguyên trạng.
