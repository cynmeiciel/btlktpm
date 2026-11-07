# S3 Attendance

Service tiếp nhận, chống trùng lặp và lưu giữ sự kiện chấm công ở trung tâm. Thiết kế: `docs/01-kien-truc-s3.md` ở gốc repo.

Trạng thái: walking skeleton (backlog T0.7). Route ingest ở mục "Thử nhanh" chạy được từ T4.3.

Cài đặt trên Windows hoặc Arch Linux: `docs/10-local-setup.md`. Mọi lệnh dưới đây chạy trong thư mục này và giống nhau trên PowerShell và bash, trừ chỗ có ghi chú.

## Cách 1: chạy bằng Docker (không cần Python)

Từ gốc repo:

```bash
docker compose -f infra/compose.yaml --profile app up --build
```

## Cách 2: chạy bằng uv (để phát triển)

```bash
docker compose -f ../../infra/compose.yaml up -d postgres
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn tmc_attendance.bootstrap.main:app --reload
```

`pydantic-settings` tự đọc `.env` (đã có trong `.gitignore`, không commit). Biến môi trường thật đè lên giá trị trong `.env`.

## Thử nhanh

PowerShell dùng `curl.exe` thay cho `curl`.

```bash
curl localhost:8000/health/ready
# {"status":"ready"}; 503 {"status":"not_ready"} nếu mất DB

curl -X POST localhost:8000/v1/attendance-event-batches -H "Authorization: Bearer dev-token-bd-g01-in" -H "Content-Type: application/json" --data "@scripts/sample-batch.json"
```

Lần đầu kết quả là `ACCEPTED`. Gửi lại đúng lệnh đó: kết quả phải là `DUPLICATE`, và bảng `attendance.attendance_event` vẫn chỉ có một dòng. Giao diện thử API: http://localhost:8000/docs.

Token dev `dev-token-bd-g01-in` đã được khai báo sẵn (dạng sha256) trong `.env.example` và `infra/compose.yaml`. Thêm trạm mới thì tính sha256 của token bằng:

```bash
uv run python -c "import hashlib; print(hashlib.sha256(b'<token>').hexdigest())"
```

## Biến môi trường

| Biến | Dùng bởi | Ví dụ dev |
|---|---|---|
| `TMC_S3_DATABASE_URL` | app (role `s3_attendance_app`, **bắt buộc**), fixture test | `postgresql+psycopg://s3_attendance_app:app-dev-pw@localhost:5432/tmc` |
| `TMC_S3_MIGRATION_DATABASE_URL` | Alembic, fixture test (role `s3_attendance_owner`) | `postgresql+psycopg://s3_attendance_owner:owner-dev-pw@localhost:5432/tmc` |
| `TMC_S3_READER_DATABASE_URL` | fixture test giả lập S4 (role `s4_reporting_reader`) | `postgresql+psycopg://s4_reporting_reader:reader-dev-pw@localhost:5432/tmc` |
| `TMC_S3_STATION_TOKENS` | `StaticTokenStationAuthenticator` | JSON `{"BD-G01-IN": "<sha256 của token>"}` |
| `TMC_S3_MAX_FUTURE_SKEW_SECONDS` | `EventValidationPolicy` | `300` |
| `TMC_S3_MAX_BATCH_SIZE` | route ingest | `500` |
| `TMC_S3_LOG_LEVEL` | logging | `INFO` |
| `TMC_S3_DB_CONNECT_TIMEOUT_SECONDS` | engine của app, để `/health/ready` không treo khi mất DB | `3` (mặc định) |
| `TMC_REQUIRE_DB` | `tests/conftest.py` | `1` trong CI: thiếu DB là fail, không skip |

Cách đọc: app dùng `Settings`; Alembic và `tests/conftest.py` dùng `DatabaseAdminSettings`. Cả hai lớp ở `bootstrap/config.py`, `env_prefix="TMC_S3_"`, `env_file=".env"`, nên file `.env` local có tác dụng ở mọi nơi. Chỉ cờ `TMC_REQUIRE_DB` được đọc thẳng từ `os.environ`.

Cổng 5432 bận (do PostgreSQL cài sẵn trên máy, Windows hoặc Arch): chạy compose với `TMC_PG_HOST_PORT=55432` và đổi cổng trong `.env` (`docs/10-local-setup.md` §8).

Mật khẩu và token ở trên chỉ dùng cho dev/CI. Không commit `.env`.

## Lệnh kiểm tra

```bash
uv run scripts/dev.py check     # ruff + mypy + lint-imports
uv run scripts/dev.py test      # unit + api, không cần DB
uv run scripts/dev.py test-db   # integration + e2e, cần Postgres đang chạy
uv run scripts/dev.py all       # tất cả
```
