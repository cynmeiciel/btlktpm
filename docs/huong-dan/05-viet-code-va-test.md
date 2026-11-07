# 05 — Viết code và test: một ví dụ trọn vẹn

Ví dụ dùng `DeduplicationRule` (một phần của T1.3, đặc tả ở `../02-domain-model.md` §5). Nó nhỏ, nhưng đi đủ các bước bạn sẽ làm với mọi task.

Mọi lệnh chạy trong `services/s3-attendance/`.

## 1. Đọc đặc tả và tiêu chí nghiệm thu

Trước khi gõ, mở task trong `../09-backlog.md` và đặc tả liên quan. Trả lời được ba câu:

1. Class/hàm tên gì, nằm ở file nào? (`../01-kien-truc-s3.md` §2) → `domain/dedup.py`
2. Đầu vào, đầu ra là gì? → `decide(incoming: PayloadHash, existing: PayloadHash) -> DedupDecision`
3. Test nào bắt buộc? (bảng theo layer, cột "Mức", ở `../05-testing-strategy.md` §3)

Nếu đặc tả mơ hồ hoặc mâu thuẫn, hỏi TV1 **trước** khi code.

## 2. Viết test trước

Test cho `domain/dedup.py` đặt ở `tests/unit/domain/test_dedup.py`. Đường dẫn test phản chiếu đường dẫn code.

```python
from tmc_attendance.domain.dedup import DedupDecision, DeduplicationRule
from tmc_attendance.domain.values import PayloadHash

HASH_A = PayloadHash("a" * 64)
HASH_B = PayloadHash("b" * 64)


def test_same_hash_is_duplicate() -> None:
    assert DeduplicationRule().decide(HASH_A, HASH_A) is DedupDecision.DUPLICATE


def test_different_hash_is_conflict() -> None:
    assert DeduplicationRule().decide(HASH_A, HASH_B) is DedupDecision.CONFLICT
```

Quy ước đặt tên: `test_<điều kiện>_<kết quả mong đợi>`. Đọc tên test là biết hành vi.

Chạy và thấy test **đỏ** (vì chưa có code):

```bash
uv run pytest tests/unit/domain/test_dedup.py
# ModuleNotFoundError: No module named 'tmc_attendance.domain.dedup'
```

Thấy đỏ trước rồi mới viết code. Làm vậy để chắc test thật sự kiểm tra gì đó: một test chưa bao giờ đỏ có thể là test không kiểm gì cả.

## 3. Viết code vừa đủ để test xanh

```python
# src/tmc_attendance/domain/dedup.py
import hmac
from enum import StrEnum

from tmc_attendance.domain.values import PayloadHash


class DedupDecision(StrEnum):
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"


class DeduplicationRule:
    """Decide whether a resent event is a harmless duplicate or a conflict."""

    def decide(self, incoming: PayloadHash, existing: PayloadHash) -> DedupDecision:
        if hmac.compare_digest(incoming, existing):
            return DedupDecision.DUPLICATE
        return DedupDecision.CONFLICT
```

Chú ý:
- **Có type hint đầy đủ** trong `src/` (`-> DedupDecision`): mypy strict bắt buộc ở đây. Trong test, ghi `-> None` là nên làm nhưng không bắt buộc.
- **Docstring và tên bằng tiếng Anh.** Tài liệu `docs/` thì tiếng Việt.
- Domain chỉ import thư viện chuẩn (`hmac`, `enum`) và chính domain.

```bash
uv run pytest tests/unit/domain/test_dedup.py     # xanh
```

## 4. Chạy kiểm tra đầy đủ trước khi commit

```bash
uv run scripts/dev.py fmt      # tự sửa format và lỗi ruff sửa được
uv run scripts/dev.py check    # ruff + mypy + lint-imports
uv run scripts/dev.py test     # toàn bộ unit + api
```

### Đọc thông báo lỗi thường gặp

| Thông báo | Nghĩa | Sửa |
|---|---|---|
| `error: Function is missing a return type annotation` (mypy) | Thiếu `-> ...` | Thêm kiểu trả về; hàm không trả gì thì `-> None` |
| `error: Function is missing a type annotation for one or more arguments` | Tham số thiếu kiểu | `def f(x: int)` |
| `Incompatible return value type (got "str", expected "PayloadHash")` | Sai kiểu | Bọc đúng kiểu: `PayloadHash(s)` |
| `DTZ005 datetime.datetime.now() called without a tz argument` (ruff) | Gọi giờ không có múi giờ | Trong domain/application: dùng `Clock`. Ở chỗ khác: `datetime.now(UTC)` |
| `E501 Line too long` | Dòng quá dài | `uv run scripts/dev.py fmt` thường tự sửa; còn lại thì tự xuống dòng |
| `Contract "..." BROKEN` (lint-imports) | Import sai layer | Đọc dòng `tmc_attendance.x -> y` để biết file nào import gì; chuyển code về đúng layer hoặc dùng port |
| `SKIPPED ... database not configured: TMC_S3_... not set` (pytest) | Test DB bị bỏ qua vì thiếu `.env` | `cp .env.example .env`, bật Postgres |

## 5. Test use case: dùng fake, không dùng mock

Use case phụ thuộc port (DB, đồng hồ…). Khi test unit, ta truyền **fake** từ `tests/fakes.py`:

```python
def test_resend_same_event_is_duplicate() -> None:
    store = InMemoryAttendanceStore()
    uow_factory = InMemoryUnitOfWorkFactory(store)
    use_case = IngestAttendanceEventUseCase(
        uow_factory, FixedClock(NOW), SequentialIdGenerator(),
        EventValidationPolicy(timedelta(seconds=300)), DeduplicationRule(),
    )
    cmd = make_command()                           # factory tạo dữ liệu hợp lệ

    first = use_case.execute(cmd, STATION)
    second = use_case.execute(cmd, STATION)

    assert first.status is IngestStatus.ACCEPTED
    assert second.status is IngestStatus.DUPLICATE
    assert store.count() == 1                      # vẫn chỉ một dòng
```

Đây là phác thảo. Tên chính xác của fake, factory và các thuộc tính (như `count()`) sẽ được chốt ở T2.1/T2.2, nên khi viết thật hãy mở `tests/fakes.py` để xem.

**Vì sao không dùng `unittest.mock.Mock`?** `Mock()` chấp nhận *mọi* lời gọi: gõ sai tên hàm, truyền sai tham số, nó vẫn vui vẻ chạy. Test xanh nhưng code sai. Fake kế thừa port thật nên gọi sai là lỗi ngay, và mypy cũng kiểm được. Ngoài ra fake và adapter Postgres chạy chung một bộ contract test, đó là bằng chứng LSP cho báo cáo.

Ba phần của một test (Arrange, Act, Assert): **chuẩn bị** dữ liệu, **gọi** hàm cần test, **kiểm** kết quả. Để một dòng trống giữa ba phần cho dễ đọc.

## 6. Test nào đặt ở đâu

| Bạn viết | Test ở | Cần DB? |
|---|---|---|
| Code trong `domain/` | `tests/unit/domain/` | Không |
| Use case trong `application/` | `tests/unit/application/` (dùng fake) | Không |
| Route HTTP | `tests/api/` (`TestClient` + `ApiDependencies` dựng từ fake, xem `tests/api/test_health.py`) | Không |
| Adapter Postgres | `tests/integration/` (DB thật, tự dọn sạch giữa các test) | Có: `uv run scripts/dev.py test-db` |
| Luồng đầy đủ | `tests/e2e/` | Có |

Không tự gắn `@pytest.mark.unit`: marker được gán tự động theo thư mục.

## 7. Checklist trước khi mở PR

- [ ] Test viết cùng code, đã thấy đỏ rồi xanh.
- [ ] `uv run scripts/dev.py check` và `uv run scripts/dev.py test` sạch. Sửa adapter DB thì chạy thêm `uv run scripts/dev.py test-db`.
- [ ] Tên class/file khớp `../01-kien-truc-s3.md`. Thêm class mới thì cập nhật luôn tài liệu đó.
- [ ] Không phá luật nào trong `../00-tong-quan.md` §7.
- [ ] Hiểu từng dòng mình viết, kể cả dòng do công cụ AI gợi ý. Giảng viên có thể hỏi.
