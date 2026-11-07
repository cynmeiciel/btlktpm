# 10 — Môi trường local (Windows và Arch Linux)

Nhóm dùng cả Windows và Arch Linux. Docker giúp mọi máy chạy **cùng một** PostgreSQL và cùng một image app, không phụ thuộc hệ điều hành.

## 1. Hai cách làm việc

| Cách | Cần cài | Dùng khi |
|---|---|---|
| **A. Chỉ Docker** | Docker, Git | Muốn chạy app để xem, demo, thử `curl`. Không cần Python |
| **B. Phát triển** | Docker, Git, uv | Viết code và chạy test. Postgres vẫn chạy trong Docker, còn code chạy bằng Python do uv quản lý |

Ai viết code thì cài theo cách B (cài B là có luôn A).

## 2. Cài đặt trên Windows

Dùng **PowerShell** (không cần quyền admin, trừ khi ghi chú).

1. **Docker Desktop**: tải ở docker.com, khi cài chọn backend **WSL 2**. Nếu được hỏi cài WSL thì chạy `wsl --install` (PowerShell admin) rồi khởi động lại máy. Mở Docker Desktop và đợi trạng thái "Engine running".
2. **Git**, **uv**, (tuỳ chọn) **GitHub CLI**:
   ```powershell
   winget install --id Git.Git -e
   winget install --id astral-sh.uv -e
   winget install --id GitHub.cli -e
   ```
   Đóng và mở lại PowerShell để nhận lệnh mới.
3. Kiểm tra:
   ```powershell
   docker run --rm hello-world
   docker compose version
   uv --version
   git --version
   ```

Không cần cài Python: uv tự tải đúng Python 3.13 cho dự án. Không cần `make`: lệnh kiểm tra chạy bằng `uv run scripts/dev.py ...`.

## 3. Cài đặt trên Arch Linux

```bash
sudo pacman -Syu --needed git github-cli docker docker-compose docker-buildx uv jq
sudo systemctl enable --now docker.socket
sudo usermod -aG docker "$USER"     # đăng xuất rồi đăng nhập lại
docker run --rm hello-world
```

- `docker-buildx` là bắt buộc: Dockerfile dùng tính năng BuildKit (`--mount=type=cache`). Docker Desktop trên Windows đã có sẵn.
- Không dùng `pip` hệ thống, không `sudo pip`. Mọi thứ đi qua `uv`.
- Thêm user vào nhóm `docker` tương đương quyền root. Muốn tránh thì dùng Docker rootless; các lệnh trong tài liệu không đổi.

## 4. Git (mọi máy)

```bash
gh auth login                       # hoặc dùng HTTPS + token / SSH key
git config --global user.name  "Tên"
git config --global user.email "email@..."
git config --global pull.rebase true
```

File `.gitattributes` ở gốc repo giữ mọi file ở dạng xuống dòng LF, nên Windows và Linux không tạo diff "sửa toàn bộ file" vì CRLF. Không cần chỉnh `core.autocrlf`.

## 5. Lần đầu clone (cách B)

**Windows (PowerShell):**

```powershell
gh repo clone <owner>/<repo> tmc-m2; cd tmc-m2
docker compose -f infra/compose.yaml up -d postgres
cd services/s3-attendance
Copy-Item .env.example .env
uv sync
uv run alembic upgrade head
uv run scripts/dev.py all          # check + toàn bộ test
```

**Arch (bash/zsh):**

```bash
gh repo clone <owner>/<repo> tmc-m2 && cd tmc-m2
docker compose -f infra/compose.yaml up -d postgres
cd services/s3-attendance
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run scripts/dev.py all
```

Chạy app: `uv run uvicorn tmc_attendance.bootstrap.main:app --reload`, rồi mở http://localhost:8000/docs.

(Tuỳ chọn) Tự chạy ruff trước mỗi commit: `uv tool install pre-commit`, rồi `pre-commit install` ở gốc repo.

### Lệnh hằng ngày

| Lệnh (trong `services/s3-attendance/`) | Làm gì |
|---|---|
| `uv run scripts/dev.py check` | ruff + mypy + lint-imports |
| `uv run scripts/dev.py fmt` | tự sửa format và lỗi ruff sửa được |
| `uv run scripts/dev.py test` | unit + api test, không cần DB |
| `uv run scripts/dev.py test-db` | integration + e2e test, cần Postgres đang chạy |
| `uv run scripts/dev.py all` | check rồi chạy mọi test |

## 6. Chạy bằng Docker (cách A)

Từ gốc repo, trên mọi máy:

```bash
docker compose -f infra/compose.yaml --profile app up --build
```

Lệnh này dựng ba container theo thứ tự trong `infra/compose.yaml`:

1. `postgres`: PostgreSQL 16. Lần đầu (volume trống) tự chạy `infra/postgres/init/01-roles.sql` để tạo 3 role và schema `attendance`.
2. `s3-migrate`: chạy `alembic upgrade head` bằng role owner rồi thoát.
3. `s3-attendance`: chạy app ở cổng 8000 bằng role app, chỉ khởi động sau khi migrate thành công.

Kiểm tra: `curl localhost:8000/health/ready` (PowerShell: `curl.exe localhost:8000/health/ready`) trả `{"status":"ready"}`. Dừng bằng `Ctrl+C`, hoặc `docker compose -f infra/compose.yaml --profile app down`.

Chỉ cần Postgres cho cách B: `docker compose -f infra/compose.yaml up -d postgres` (không có `--profile app`).

Xoá sạch dữ liệu DB local (ví dụ sau khi sửa `01-roles.sql`, vì script init chỉ chạy khi volume trống): thêm `-v` vào lệnh `down`.

Ghi chú báo cáo: đây là cấu hình một host, có SPOF (M1 chương 6, bước 4).

## 7. Image Docker của S3 hoạt động thế nào

File: `services/s3-attendance/Dockerfile`. Đáng đọc kỹ vì đây là kỹ năng dùng lại được ở dự án khác.

| Kỹ thuật | Trong file | Vì sao |
|---|---|---|
| **Multi-stage build** | Stage `build` cài thư viện bằng uv; stage cuối chỉ copy `/app` sang | Image cuối không chứa uv, cache, công cụ build: nhỏ và ít bề mặt tấn công |
| **Cài dependency trước, code sau** | `COPY pyproject.toml uv.lock` → `uv sync --no-install-project` → mới `COPY src` | Sửa code không làm cài lại thư viện: Docker dùng lại layer cache, build lại chỉ vài giây |
| **Cache mount** | `RUN --mount=type=cache,target=/root/.cache/uv` | Lần build sau không tải lại gói (cần BuildKit) |
| **Ghim phiên bản** | `ghcr.io/astral-sh/uv:0.12.19`, `uv sync --locked` | Build hôm nay và tuần sau ra cùng kết quả |
| **`--no-editable`** | Cài package `tmc_attendance` thật vào venv | Stage cuối không phụ thuộc thư mục mã nguồn |
| **Không chạy bằng root** | `useradd ... app`, `USER app` | Lỗi trong app không có quyền root trong container |
| **Healthcheck** | gọi `/health/ready` mỗi 10 giây | Docker (và `docker ps`) biết app thật sự sẵn sàng, không chỉ "process còn sống" |
| **`.dockerignore`** | bỏ `.venv`, `.env`, `tests`, cache | Không đưa mật khẩu trong `.env` hay file rác vào image |

Cấu hình (URL DB, token trạm) **không** nằm trong image mà truyền bằng biến môi trường lúc chạy (`environment:` trong compose). Cùng một image chạy được ở dev, CI hay máy khác.

## 8. Sự cố thường gặp

### Windows

| Triệu chứng | Cách sửa |
|---|---|
| `error during connect ... dockerDesktopLinuxEngine` | Docker Desktop chưa chạy. Mở nó và đợi "Engine running" |
| `WSL 2 installation is incomplete` | `wsl --install` (PowerShell admin), khởi động lại máy |
| `uv` hoặc `git` không nhận lệnh sau khi cài | Đóng và mở lại terminal |
| Cổng 5432 bận (đã cài PostgreSQL cho Windows) | `$env:TMC_PG_HOST_PORT = "55432"; docker compose -f infra/compose.yaml up -d postgres`, rồi đổi `localhost:5432` thành `localhost:55432` trong ba URL của `.env` |
| `curl` trong PowerShell báo lỗi tham số | PowerShell có alias `curl` khác. Dùng `curl.exe`, hoặc `Invoke-RestMethod localhost:8000/health/ready` |
| Test hoặc `uv sync` rất chậm | Antivirus quét thư mục `.venv`. Thêm thư mục repo vào danh sách loại trừ của Windows Defender |

### Arch Linux

| Triệu chứng | Cách sửa |
|---|---|
| `the --mount option requires BuildKit` | Thiếu `docker-buildx`: `sudo pacman -S docker-buildx` |
| `permission denied ... docker.sock` | Chưa đăng nhập lại sau `usermod -aG docker` |
| Cổng 5432 bận | `postgresql.service` của Arch đang chạy. Tắt nó (`sudo systemctl disable --now postgresql`), hoặc `TMC_PG_HOST_PORT=55432 docker compose -f infra/compose.yaml up -d postgres` và đổi cổng trong `.env` |
| `error: externally-managed-environment` | Đang dùng pip hệ thống. Dùng `uv sync` / `uv run` |
| Cảnh báo `VIRTUAL_ENV=... does not match` | pyenv/venv khác đang bật. Vô hại; `unset VIRTUAL_ENV` để tắt |

### Mọi máy

| Triệu chứng | Cách sửa |
|---|---|
| Test integration bị skip hết | Thiếu `.env` hoặc Postgres chưa chạy (`docker ps`) |
| `password authentication failed` | Volume DB tạo trước khi có script role: `docker compose -f infra/compose.yaml down -v` rồi `up -d postgres` |
| `/health/ready` trả 503 | App không kết nối được DB: kiểm `docker ps` và cổng trong `.env` |
