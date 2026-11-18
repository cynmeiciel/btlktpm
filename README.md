# TMC QR Attendance & Access Control — M2

Bài tập lớn CO3017 Kiến trúc Phần mềm, HCMUT, HK261. Repo chứa phần hiện thực của Assignment M2: service **S3 Attendance** theo thiết kế Service-Based Architecture đã chốt ở M1.

> Trạng thái: đang phát triển. Phạm vi và tiến độ xem `docs/09-backlog.md`.

## S3 Attendance làm gì

S3 là nơi tiếp nhận và giữ sổ cái (ledger) sự kiện chấm công ở trung tâm:

- Nhận lô sự kiện từ Sync Worker của Local Gate Agent tại các trạm cổng (store-and-forward).
- Chống ghi trùng theo `eventId` bằng ràng buộc duy nhất của PostgreSQL; gửi lại bao nhiêu lần cũng chỉ có một bản ghi.
- Phát hiện xung đột (cùng `eventId` nhưng nội dung khác, hoặc một trạm dùng lại số thứ tự) và cách ly để điều tra, không ghi đè.
- Ghi bản ghi outbox cùng transaction với event để các bên sau (S4, audit) nhận được thay đổi một cách tin cậy.
- Cho nhân viên tra lịch sử ra/vào của chính mình (UC09); công bố view có phiên bản cho S4.

S3 **không** xác thực QR, không điều khiển cổng (việc của Gate Agent tại trạm), không làm báo cáo tháng (S4).

## Bắt đầu nhanh

Yêu cầu: Docker, `uv`, `git`. Cài đặt trên Windows hoặc Arch Linux: `docs/10-local-setup.md`. Lệnh dưới đây viết cho bash; trên PowerShell thay `cp` bằng `Copy-Item` và `curl` bằng `curl.exe`.

```bash
git clone <repo-url> tmc-m2 && cd tmc-m2
docker compose -f infra/compose.yaml up -d postgres
cd services/s3-attendance
uv sync
cp .env.example .env
uv run pytest
uv run alembic upgrade head
uv run uvicorn tmc_attendance.bootstrap.main:app --reload
curl localhost:8000/health/ready        # {"status":"ready"}
# mở http://localhost:8000/docs
```

App đã chạy đầy đủ trên PostgreSQL: tiếp nhận lô sự kiện, chống trùng, ghi xung đột, ghi outbox và tra lịch sử. Tiến độ xem `docs/09-backlog.md`.

Chạy toàn bộ bằng container (DB + migrate + app; cần gói `docker-buildx`):

```bash
docker compose -f infra/compose.yaml --profile app up --build
```

## Cấu trúc

```
infra/                    PostgreSQL local, script tạo role
services/s3-attendance/   mã nguồn, test, migration, Dockerfile của S3
docs/                     đặc tả, quy ước, backlog, tài liệu cho báo cáo
.github/                  CI/CD, template PR/issue
```

## Tài liệu chính

**Thành viên mới bắt đầu từ [`docs/huong-dan/`](docs/huong-dan/README.md)**: giải thích bài toán, kiến trúc, Git và cách viết test bằng lời dễ hiểu. Các file dưới đây là đặc tả để tra cứu.

| Cần biết | Đọc |
|---|---|
| Bối cảnh, phạm vi, **bất biến kiến trúc** | `docs/00-tong-quan.md` |
| Kiến trúc bên trong S3 | `docs/01-kien-truc-s3.md` |
| Luật nghiệp vụ, dedupe | `docs/02-domain-model.md` |
| API | `docs/03-api-contract.md` (OpenAPI sống tại `/docs` khi chạy app) |
| CSDL và quyền | `docs/04-database.md` |
| Cách test | `docs/05-testing-strategy.md` |
| CI/CD | `docs/06-ci-cd.md` |
| Quy trình nhóm | `docs/08-team-workflow.md` |

## Nhóm

| Mã | Vai trò |
|---|---|
| TV1 | Tech lead — repo, CI/CD, test infra, review |
| TV2 | Domain + Application |
| TV3 | Persistence |
| TV4 | HTTP API |
| TV5 | Read side + stretch |

Chi tiết phân công: `docs/08-team-workflow.md` mục 1.
