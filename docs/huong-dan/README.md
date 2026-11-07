# Hướng dẫn cho người mới — bắt đầu từ đây

Các file `docs/00`–`docs/14` là **đặc tả**: chúng nói chính xác hệ thống phải làm *cái gì*, viết gọn để tra cứu. Đọc ngay từ đầu sẽ thấy nhiều thuật ngữ lạ.

Thư mục này viết cho người chưa quen. Nó giải thích **tại sao** thiết kế như vậy và **làm thế nào** để bắt tay vào code, bằng ví dụ đời thường. Đọc xong phần này rồi mới quay lại đặc tả.

## Lộ trình đọc

| Bước | Đọc | Thời gian | Sau bước này bạn sẽ… |
|---|---|---|---|
| 1 | [01-bai-toan.md](01-bai-toan.md) | 20 phút | Kể lại được S3 làm gì, vì sao phải chống trùng |
| 2 | [02-kien-truc.md](02-kien-truc.md) | 40 phút | Hiểu 4 layer, port/adapter, và một request đi qua những file nào |
| 3 | `../10-local-setup.md` §1–5 (Windows hoặc Arch) | 30 phút (cài đặt) | Có môi trường chạy được `uv run scripts/dev.py test` |
| 4 | [04-git-tung-buoc.md](04-git-tung-buoc.md) | 20 phút | Mở được PR đầu tiên mà không sợ hỏng repo |
| 5 | [05-viet-code-va-test.md](05-viet-code-va-test.md) | 40 phút | Viết được một hàm kèm test, qua được `uv run scripts/dev.py check` |
| — | [03-tu-dien.md](03-tu-dien.md) | tra khi cần | Gặp từ lạ thì tra ở đây |
| — | [06-hoi-dap.md](06-hoi-dap.md) | tra khi cần | Gặp lỗi hoặc thắc mắc "sao không làm kiểu X" |

Nên đọc theo thứ tự 1 → 2 → 5. Bước 3 và 4 có thể làm song song.

## Theo vai trò: đọc thêm gì, bắt đầu từ đâu

| Ai | Đặc tả cần đọc kỹ | Task đầu tiên | Bạn sẽ viết code ở |
|---|---|---|---|
| TV2 — Domain + Application | `02-domain-model.md`, `01-kien-truc-s3.md` §3–4 | T1.1 | `src/tmc_attendance/domain/`, `application/` |
| TV3 — Persistence | `04-database.md`, `01-kien-truc-s3.md` §3, §5 | T3.1 (migration) | `migrations/`, `adapters/outbound/persistence/` |
| TV4 — HTTP API | `03-api-contract.md`, `01-kien-truc-s3.md` §5, §7 | T4.1 (xử lý lỗi), T4.2 (xác thực trạm) | `adapters/inbound/http/` |
| TV5 — Read side | `03-api-contract.md` §3, `04-database.md` §8 | T5.1 | `adapters/outbound/persistence/`, `application/history.py` |

TV3, TV4 và TV5 không phải chờ TV2 làm xong toàn bộ domain. Mọi người chỉ cần chờ **T2.1 (port)** được merge, vì port là "hợp đồng" để code hai phía khớp nhau. Trước khi T2.1 được merge, bạn có thể code trước dựa trên đặc tả port ở `01-kien-truc-s3.md` §3.

## Code mẫu để nhìn theo

Repo đã có một **walking skeleton** (T0.7): đường `/health/ready` đi đủ 4 layer. Đọc nó trước khi viết code của bạn, vì mọi tính năng sau đều theo đúng khuôn này:

| Layer | File | Vai trò |
|---|---|---|
| application | `src/tmc_attendance/application/ports.py` | port `HealthProbe` (ổ cắm) |
| adapters outbound | `src/tmc_attendance/adapters/outbound/persistence/health.py` | `PostgresHealthProbe` (phích cắm thật) |
| adapters inbound | `src/tmc_attendance/adapters/inbound/http/health.py`, `dependencies.py`, `app.py` | route, khai báo dependency, app factory |
| bootstrap | `src/tmc_attendance/bootstrap/container.py`, `main.py` | nối phích thật vào ổ |
| test | `tests/fakes.py`, `tests/api/test_health.py`, `tests/integration/test_health_probe.py` | phích giả, test API, test với DB thật |

## Ba điều quan trọng nhất

1. **Không hiểu thì hỏi sớm.** Mở issue hoặc comment trong PR nháp. Kẹt nửa ngày mới hỏi là quá lâu.
2. **Có 9 luật không được phá** (`../00-tong-quan.md` §7). Bạn chưa cần thuộc ngay. Đọc xong [01-bai-toan.md](01-bai-toan.md) bạn sẽ hiểu vì sao có từng luật.
3. **Máy sẽ kiểm giúp bạn.** `uv run scripts/dev.py check` và CI báo lỗi trước khi người review phải đọc code. Thấy lỗi đỏ là bình thường, cứ đọc thông báo và sửa.
