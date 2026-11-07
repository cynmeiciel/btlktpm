# 07 — Quy ước code và cấu hình công cụ

## 1. Ngôn ngữ và phiên bản

- Python **3.13**, ghim bằng `services/s3-attendance/.python-version`; `uv` tự tải bản Python này trên cả Windows lẫn Linux, độc lập với Python của máy.
- `src/`: type hint ở mọi hàm, `mypy --strict` phải sạch. `tests/`: được bỏ type hint ở hàm test (đã nới trong `pyproject.toml`), mypy vẫn kiểm phần còn lại.
- Identifier, docstring, comment, commit message: tiếng Anh. Tài liệu `docs/`: tiếng Việt.

## 2. Dependency

Thêm bằng `uv add` để lấy bản mới nhất tương thích rồi khoá trong `uv.lock`. Cận dưới tham khảo:

| Nhóm | Gói | Dùng cho |
|---|---|---|
| runtime | `fastapi>=0.115` | HTTP |
| runtime | `uvicorn[standard]>=0.30` | ASGI server |
| runtime | `pydantic>=2.8`, `pydantic-settings>=2.4` | DTO, config |
| runtime | `sqlalchemy>=2.0.30` | Core |
| runtime | `psycopg[binary]>=3.2` | driver PostgreSQL (wheel có sẵn libpq, không cần cài gì trên Arch) |
| runtime | `alembic>=1.13` | migration |
| dev | `pytest>=8.2`, `pytest-cov>=5`, `pytest-timeout>=2.3` | test |
| dev | `httpx2>=2.16` | cần cho `fastapi.testclient` (Starlette ≥ 1.10 dùng `httpx2`; `httpx` cũ chỉ còn là fallback có cảnh báo, mà pytest đặt `filterwarnings = error`) |
| dev | `mypy>=1.11`, `ruff>=0.6`, `import-linter>=2.0` | chất lượng |

Không thêm gói khác nếu task không đòi. Đặc biệt **không** thêm: ORM khác, DI framework (`dependency-injector`…), thư viện mock, `testcontainers` (CI dùng service container, local dùng compose).

## 3. `pyproject.toml`

File thật: `services/s3-attendance/pyproject.toml`. Những điểm cần biết:

| Mục | Cấu hình | Ý nghĩa |
|---|---|---|
| `[tool.ruff]` | `line-length = 100`; bộ luật gồm `DTZ` (cấm datetime không múi giờ), `S` (bảo mật), `T20` (cấm `print` trong `src/`) | `uv run scripts/dev.py fmt` tự sửa phần lớn |
| `[tool.mypy]` | `strict = true` cho `src/`; override nới cho `tests.*` | |
| `[tool.pytest.ini_options]` | marker `unit`/`api`/`integration`/`e2e` (gán tự động theo thư mục), `filterwarnings = ["error"]`, `timeout = 30` | cảnh báo deprecation làm test fail để sửa sớm |
| `[tool.importlinter]` | 4 contract: layers; domain không framework; application không framework; inbound và outbound độc lập | đây là bằng chứng máy kiểm cho dependency rule |

Sửa mục `[tool.importlinter]` là thay đổi kiến trúc: cần TV1 duyệt.

Nếu `filterwarnings = ["error"]` vướng cảnh báo từ thư viện bên thứ ba ngoài tầm kiểm soát, thêm một dòng `ignore` cụ thể (kèm comment lý do), không gỡ `error`.

## 4. Cấu trúc code

| Chủ đề | Quy ước |
|---|---|
| Port | `abc.ABC` + `@abstractmethod`. Adapter kế thừa tường minh: `class PostgresOutbox(OutboxPort)` |
| Entity / value object | `@dataclass(frozen=True, slots=True)` |
| DTO giữa adapter và application | `@dataclass(frozen=True, slots=True)` trong `application/dto.py` |
| DTO HTTP | Pydantic `BaseModel` trong `adapters/inbound/http/schemas.py`, `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")` cho **mọi** model request, kể cả envelope (tolerant reader, IADR-006). Không dùng `extra="forbid"` |
| Enum | `StrEnum`, giá trị chữ hoa trùng tên |
| Dependency injection | Constructor injection thuần; nối dây duy nhất ở `bootstrap/container.py`. Không dùng global, không singleton module-level (trừ `app` trong `bootstrap/main.py`) |
| Hằng cấu hình | Biến môi trường đọc qua đúng hai lớp `pydantic-settings` ở `bootstrap/config.py` (đọc cả `.env`, biến thật đè `.env`): `Settings` (app) và `DatabaseAdminSettings` (ba URL DB, dùng bởi Alembic và fixture test, xem `05-testing-strategy.md` §1). Giá trị truyền vào constructor. Không gọi `os.environ`/`os.getenv` ở nơi khác; ngoại lệ duy nhất: cờ `TMC_REQUIRE_DB` trong `tests/conftest.py`. `monkeypatch.setenv` trong test được phép |
| Kích thước | Hàm > 40 dòng hoặc class > 200 dòng là tín hiệu nên tách — xem lại SRP |

## 5. Lỗi

| Loại | Biểu diễn | Ví dụ |
|---|---|---|
| Kết quả nghiệp vụ dự kiến | giá trị trả về | `IngestResult(status=DUPLICATE)` |
| Bất biến domain bị phá | `InvalidEvent(DomainError)` | thiếu timezone |
| Truy vấn không phục vụ được | `AccessDenied`, `InvalidQuery` (application) | đọc lịch sử người khác |
| Lỗi hạ tầng | để exception gốc (`sqlalchemy.exc.OperationalError`…) bay lên; adapter HTTP đổi thành 503 | DB mất kết nối |

- Không `except Exception: pass`. Không bắt rộng trong domain/application.
- Exception handler của FastAPI là nơi **duy nhất** đổi exception thành HTTP status.

## 6. Log

- Dùng `logging` của thư viện chuẩn: `logger = logging.getLogger(__name__)`. Cấu hình một lần trong `bootstrap/main.py` bằng `logging.basicConfig(level=settings.log_level)`.
- Log ở adapter và bootstrap; **không** log trong domain.
- Nên có: một dòng mỗi lô (`station_id`, số accepted/duplicate/conflict/rejected) ở mức INFO; mỗi conflict ở mức WARNING kèm `event_id`.
- **Cấm log**: token, header `Authorization`, payload đầy đủ, giá trị đầu vào của lỗi validation. `employee_ref` được phép (UUID giả danh).

## 7. Thời gian

- `domain`, `application`: chỉ nhận `datetime` qua tham số hoặc `Clock`.
- Chỉ `SystemClock` được gọi `datetime.now(UTC)`. Ruff `DTZ` bắt `datetime.now()` không tz ở mọi nơi.
- Lưu `timestamptz`. Trả API dạng UTC `Z`. Chuyển sang `Asia/Ho_Chi_Minh` để hiển thị không phải việc của S3.

## 8. Git

- Nhánh: `feat/T2.3-ingest-use-case`, `fix/T3.3-sequence-conflict`, `test/...`, `ci/...`, `docs/...`, `chore/...`.
- Commit: Conventional Commits, tiếng Anh, thể mệnh lệnh.
  ```
  feat(s3): classify resent events as duplicate or conflict
  test(s3): prove resent batch yields duplicates only
  ci: add postgres service and migration round-trip
  ```
- PR squash-merge; tiêu đề PR = commit message cuối cùng trên `main`, nên viết theo cùng quy ước.

## 9. File phụ trợ ở `services/s3-attendance/`

`.env.example`:

```dotenv
TMC_S3_DATABASE_URL=postgresql+psycopg://s3_attendance_app:app-dev-pw@localhost:5432/tmc
TMC_S3_MIGRATION_DATABASE_URL=postgresql+psycopg://s3_attendance_owner:owner-dev-pw@localhost:5432/tmc
TMC_S3_READER_DATABASE_URL=postgresql+psycopg://s4_reporting_reader:reader-dev-pw@localhost:5432/tmc
# sha256("dev-token-bd-g01-in"); tính lại: uv run python -c "import hashlib; print(hashlib.sha256(b'dev-token-bd-g01-in').hexdigest())"
TMC_S3_STATION_TOKENS={"BD-G01-IN":"11611500e1dbbc5e6fa01a067eed7400afedc57391138b51a8bfeaade654011f"}
TMC_S3_MAX_FUTURE_SKEW_SECONDS=300
TMC_S3_MAX_BATCH_SIZE=500
TMC_S3_LOG_LEVEL=INFO
```

`.gitignore` (gốc repo) tối thiểu: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.import_linter_cache/`, `.coverage`, `coverage*.xml`, `reports/`, `.env`, `*.egg-info/`, `dist/`, `.idea/`, `.vscode/` (trừ `.vscode/extensions.json` nếu nhóm muốn).

`.pre-commit-config.yaml` (gốc repo, tuỳ chọn): chạy ruff và lint-imports trước mỗi commit. Cài bằng `uv tool install pre-commit` rồi `pre-commit install`. mypy và pytest không chạy trong pre-commit vì chậm.

CI chỉ chạy `lint-imports` + pytest (`06-ci-cd.md`); `uv run scripts/dev.py check` (ruff + mypy + lint-imports) là trách nhiệm của người mở PR, chạy ở local trước khi push.

`scripts/dev.py`: lệnh tiện dụng chạy giống nhau trên Windows và Linux (thay cho `Makefile`, vì Windows không có `make`):

| Lệnh | Chạy |
|---|---|
| `uv run scripts/dev.py check` | `ruff check .`, `ruff format --check .`, `mypy`, `lint-imports` |
| `uv run scripts/dev.py fmt` | `ruff check --fix .`, `ruff format .` |
| `uv run scripts/dev.py test` | `pytest -m "unit or api"` |
| `uv run scripts/dev.py test-db` | `pytest -m "integration or e2e"` |
| `uv run scripts/dev.py all` | `check` rồi `pytest` |
