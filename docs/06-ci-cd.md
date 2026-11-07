# 06 — CI

Phạm vi CI đã được tối giản: **chỉ chạy test tự động** trên mỗi PR và mỗi lần push lên `main`. Không build image, không publish GHCR, không release tự động, không smoke test container.

Lint/format/type check (`ruff`, `mypy`) **không** chạy trong CI. Mỗi người chạy `uv run scripts/dev.py check` ở máy mình trước khi mở PR (DoD, `08-team-workflow.md` §4), còn `ruff` chạy tự động qua pre-commit (`07-conventions.md` §9).

## 1. Pipeline

```
pull_request / push main / chạy tay
        │
        └── test   postgres service → tạo role (01-roles.sql) → alembic upgrade head (khi đã có migration)
                   → lint-imports → pytest (mọi marker, TMC_REQUIRE_DB=1)
```

Một job duy nhất tên `test`, mục tiêu dưới 3 phút.

`lint-imports` vẫn giữ trong job: bất biến 1 (`00-tong-quan.md` §7) quy định dependency rule được kiểm bằng import-linter trong CI. Đây cũng là test kiến trúc, bằng chứng cho DIP trong báo cáo (`11-solid-mapping.md`).

## 2. `.github/workflows/ci.yml`

File thật nằm ở `.github/workflows/ci.yml` (T0.4). Nội dung chính:

| Bước | Lệnh | Ghi chú |
|---|---|---|
| Checkout | `actions/checkout@v7.0.1` | `persist-credentials: false` |
| Cài uv | `astral-sh/setup-uv@v10.3.3` | cache theo `uv.lock`. Bản này không còn tag major "trượt" (`@v10`), nên ghim bản đầy đủ |
| Cài dependency | `uv sync --locked` | lock lệch so với `pyproject.toml` là fail |
| Tạo role | `psql ... -f infra/postgres/init/01-roles.sql` | service container chạy trước checkout nên không mount được script; chạy tay bằng `psql` có sẵn trên runner |
| Migrate | `uv run alembic upgrade head` | chỉ chạy khi `alembic.ini` tồn tại (`if: hashFiles(...)`). File này đã có từ T0.7 nên bước này luôn chạy; trước T3.1 nó chỉ tạo `attendance.alembic_version` |
| Dependency rule | `uv run lint-imports` | |
| Test | `uv run pytest` | chạy mọi marker; `TMC_REQUIRE_DB=1` để test DB không bao giờ "xanh vì skip" |

Biến môi trường của job: ba URL `TMC_S3_*_DATABASE_URL` trỏ tới `localhost:5432` của service container, giá trị dev giống `.env.example`.

### Điểm dễ sai — đã xử lý

| Vấn đề | Cách xử lý |
|---|---|
| Service container không mount được file repo | Bước `psql` riêng sau checkout |
| `defaults.run.working-directory` không áp cho bước `uses` | Đường dẫn trong `with:` viết từ gốc repo |
| Path filter + required check làm PR kẹt "Expected — waiting" | Không dùng path filter |
| Test DB "xanh" vì skip hết | `TMC_REQUIRE_DB=1` |

Kiểm tra cục bộ: các bước trên đã chạy thử trên một container `postgres:16-alpine` mới tinh, cho kết quả 14 passed, `lint-imports` 4/4 KEPT (trước T0.7). Sau T0.7: 22 passed.

## 3. Bảo vệ nhánh `main` (tuỳ chọn, Settings → Rules → Rulesets)

| Quy tắc | Giá trị |
|---|---|
| Require a pull request before merging | Bật, 1 approval |
| Require status checks to pass | `test` |
| Block force pushes, restrict deletions | Bật |
| Allowed merge methods | Squash |

## 4. Phiên bản nộp bài

Không có release tự động. Đến mốc nộp, TV1 tạo tag git `s3-v1.0.0` trên commit cuối (`git tag s3-v1.0.0 && git push origin s3-v1.0.0`) rồi ghi URL repo và tag vào báo cáo để giảng viên checkout đúng phiên bản.

Muốn chạy toàn bộ bằng container để demo thì dùng `docker compose -f infra/compose.yaml --profile app up --build` ở máy local (T6.2). Việc này không nằm trong CI.

## 5. Badge cho README (sau khi có repo)

```markdown
![ci](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg?branch=main)
```
