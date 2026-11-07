# 06 — Hỏi đáp và sự cố thường gặp

## A. "Sao không làm kiểu X cho đơn giản?"

**Sao không SELECT kiểm tra rồi mới INSERT?**
Hai request đến cùng lúc đều SELECT thấy "chưa có", rồi cả hai cùng INSERT, sinh ra hai dòng. Chỉ ràng buộc `PRIMARY KEY` của DB mới chặn được tuyệt đối. Xem [01-bai-toan.md](01-bai-toan.md) §2 và `../04-database.md` §4.

**Sao chia nhiều layer, nhiều file thế, viết hết trong một file route có nhanh hơn không?**
Nhanh hơn lúc đầu, nhưng sau đó không test được nếu thiếu DB, và đổi một thứ là phải sửa khắp nơi. Đề M2 chấm SOLID, nên cấu trúc layer chính là thứ được chấm. Xem [02-kien-truc.md](02-kien-truc.md).

**Sao không dùng ORM (class model của SQLAlchemy)?**
Ta cần kiểm soát chính xác câu SQL (`INSERT ... ON CONFLICT DO NOTHING RETURNING`), và không muốn object DB lẫn vào domain. SQLAlchemy Core đủ dùng và rõ ràng hơn (IADR-002).

**Sao endpoint viết `def` mà không `async def`?**
Driver DB dùng ở chế độ đồng bộ. Viết `async def` mà gọi DB đồng bộ bên trong sẽ chặn cả server. Với `def`, FastAPI tự chạy hàm trong thread pool (IADR-002).

**Sao không dùng `Mock`?**
`Mock` chấp nhận mọi lời gọi nên không bắt được lỗi gọi sai. Xem [05-viet-code-va-test.md](05-viet-code-va-test.md) §5.

**Sao request có trường lạ vẫn được nhận?**
Đó là "tolerant reader": trạm phiên bản mới có thể gửi thêm trường, S3 bản cũ bỏ qua thay vì từ chối, nhờ vậy nâng cấp từng phần không làm hỏng hệ thống. Thiếu trường hoặc sai kiểu thì vẫn bị từ chối (IADR-006).

**Sao cả lô luôn trả 200, kể cả khi vài sự kiện bị từ chối?**
Mỗi sự kiện có kết quả riêng trong `results`. Một sự kiện hỏng không nên làm cả 500 sự kiện bị gửi lại (IADR-005).

**Sao event lưu UTC mà Việt Nam là UTC+7?**
Lưu một chuẩn duy nhất thì không bao giờ nhầm. Đổi sang giờ Việt Nam là việc của phần hiển thị (S4/UI), không phải S3.

## B. Sự cố môi trường

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `uv: command not found` / `uv` không nhận lệnh | Chưa cài uv, hoặc chưa mở lại terminal sau khi cài | Windows: `winget install --id astral-sh.uv -e`; Arch: `sudo pacman -S uv` (`../10-local-setup.md` §2–3) |
| Cảnh báo `VIRTUAL_ENV=... does not match` | pyenv hoặc venv khác đang bật | Vô hại. Muốn tắt thì `unset VIRTUAL_ENV` |
| `ModuleNotFoundError: No module named 'tmc_attendance'` | Chạy sai thư mục hoặc chưa `uv sync` | `cd services/s3-attendance && uv sync`, và luôn chạy bằng `uv run ...` |
| `docker: permission denied` | User chưa thuộc nhóm docker | `sudo usermod -aG docker $USER`, đăng xuất rồi đăng nhập lại |
| `port 5432 already in use` | PostgreSQL của máy đang chạy | `TMC_PG_HOST_PORT=55432 docker compose -f infra/compose.yaml up -d postgres` và đổi `5432` thành `55432` trong `.env` |
| Test integration toàn `SKIPPED` | Thiếu `.env` hoặc DB chưa chạy | `cp .env.example .env`, bật Postgres, kiểm `docker ps` |
| `password authentication failed` | Volume DB cũ được tạo trước khi có script role | `docker compose -f infra/compose.yaml down -v` rồi `up -d postgres` (xoá dữ liệu DB local) |
| `relation "attendance.attendance_event" does not exist` | Chưa chạy migration, hoặc T3.1 (migration 0001) chưa merge | `uv run alembic upgrade head` |
| `the --mount option requires BuildKit` khi build Docker | Thiếu gói `docker-buildx` | `sudo pacman -S docker-buildx` |
| `/health/ready` trả 503 `not_ready` | App không kết nối được DB | Kiểm `docker ps`, cổng trong `.env` |

## C. Sự cố với CI và PR

| Hiện tượng | Cách xử lý |
|---|---|
| CI đỏ ở bước `lint-imports` | Import sai layer. Đọc log để biết file nào, xem [05-viet-code-va-test.md](05-viet-code-va-test.md) §4 |
| CI đỏ ở `pytest` nhưng local xanh | Local có thể đã skip test DB. Chạy `uv run scripts/dev.py test-db`. Kiểm cả múi giờ: test phải dùng `FixedClock`, không phụ thuộc giờ máy |
| CI xanh nhưng reviewer vẫn yêu cầu sửa | CI không chạy ruff/mypy. Bạn cần tự chạy `uv run scripts/dev.py check` ở local |
| PR báo "This branch has conflicts" | Rebase lên `main`, xem [04-git-tung-buoc.md](04-git-tung-buoc.md) §3 |

## D. Khi nào hỏi TV1

- Đặc tả mâu thuẫn hoặc không đủ để code.
- Task có vẻ phải phá một trong 9 luật.
- Cần thêm thư viện mới (`uv add`). Hỏi trước, ghi lý do trong PR.
- Cần đổi port đã chốt ở `../01-kien-truc-s3.md` §3, vì việc này ảnh hưởng tới người khác.
- Kẹt quá nửa ngày.
