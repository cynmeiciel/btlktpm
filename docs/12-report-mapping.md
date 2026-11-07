# 12 — Ánh xạ code ↔ báo cáo M2

Đề M2 chấm trên báo cáo + repo. Tài liệu này nói mỗi mục báo cáo lấy bằng chứng từ đâu trong repo, để code xong là có đủ nguyên liệu, không phải chạy lại lúc gần hạn.

## 1. Những gì M2 thêm so với M1

| Mục đề M2 | Có trong báo cáo M1? | Việc cần làm |
|---|---|---|
| Task 1.2 — module views, component-and-connector views, allocation views | Có sơ đồ rời rạc (Hình 6, 7, deployment, network) nhưng **chưa tổ chức theo ba loại view** | Viết mục mới, tái sử dụng hình cũ + hình từ code (mục 2) |
| Task 1.3 — giải thích áp dụng SOLID | Có DP05–DP09 ở mức nguyên tắc | Bổ sung bằng chứng từ code: `11-solid-mapping.md` |
| Task 1.4 — Reflection Report | Không | Tổng hợp `reflection-log.md` |
| Task 2 — code | Không | Repo này |
| "finalizing the software design" | — | Sửa các điểm lệch ở `13-open-questions.md` mục B |

## 2. Ba loại view và nguồn

### Module views (cấu trúc mã nguồn tĩnh)

| Kiểu view | Nội dung | Nguồn |
|---|---|---|
| Decomposition | 4 service + Gate Agent; trong S3: `domain`, `application`, `adapters.inbound`, `adapters.outbound`, `bootstrap` | `01-kien-truc-s3.md` mục 2 |
| Uses / Layered | quy tắc `bootstrap → adapters → application → domain` | Hình 7 (cập nhật) + `[tool.importlinter]` |
| Data model | 3 bảng + view của schema `attendance` | `04-database.md` mục 2; vẽ lại phần S3 của Hình 2 M1 |

Sinh sơ đồ package từ code (tuỳ chọn, làm ở T8.1): `uvx --from pylint pyreverse -o png -p s3 src/tmc_attendance` (chạy tạm, không thêm `pylint` vào dependency; xuất PNG cần `graphviz`: `sudo pacman -S graphviz`). Ảnh sinh tự động thường rối; dùng làm đối chiếu, sơ đồ chính vẽ tay bằng PlantUML.

### Component-and-connector views (cấu trúc lúc chạy)

| Kiểu view | Nội dung | Nguồn |
|---|---|---|
| Component | Gate Agent, Sync Worker, reverse proxy, S1–S4, PostgreSQL; connector HTTPS lô, SQL, view | Hình 6 M1 |
| Bên trong S3 | security → controller → use case → UoW → repository/outbox → PostgreSQL | `01-kien-truc-s3.md` mục 8 |
| Tuần tự | ingest bình thường, gửi lại sau mất ACK, xung đột | Hình 4–5 M1 + test E2E |

### Allocation views (ánh xạ phần mềm lên môi trường)

| Kiểu view | Nội dung | Nguồn |
|---|---|---|
| Deployment | container `s3-attendance`, `s3-migrate`, `postgres` trên một host (M2) vs cấu hình production đề xuất | `infra/compose.yaml` + deployment diagram M1 chương 6 |
| Install / implementation | artifact: image build từ `services/s3-attendance/Dockerfile` (local, không publish), migration Alembic, tag git `s3-v1.0.0` | `06-ci-cd.md` §4, `10-local-setup.md` §6–7 |
| Work assignment | thành viên ↔ module | `08-team-workflow.md` mục 1 |

Work assignment là allocation view hợp lệ (gán module cho đội) — có sẵn ở bảng vai trò TV1–TV5, chỉ cần trình bày.

## 3. Task 2 — nội dung tối thiểu trong báo cáo

1. URL repo + tag `s3-v1.0.0`.
2. Phạm vi đã hiện thực (bảng `00-tong-quan.md` mục 2, đánh dấu cái nào xong).
3. Cách chạy (chép từ README).
4. Cấu trúc code (cây package rút gọn) và ánh xạ tới Hình 7.
5. Luồng chính có trích code: use case ingest; `insert_if_absent` SQL.
6. Kết quả kiểm thử: số test theo marker, coverage domain+application, ảnh CI xanh.
7. Bằng chứng trọng tâm:
   - E2E gửi lại cùng lô → DUPLICATE, số dòng không đổi (NFR-2, ADR04). Lập luận đồng thời ở `04-database.md` §4.
   - Test quyền DB: role app không UPDATE/DELETE được event (ADR07, ADR08).
   - `lint-imports` KEPT, và thử nghiệm làm nó BROKEN (DIP).
   - `simulate_station.py --resend --conflict`: bảng kết quả.
8. Giới hạn đã biết (`00-tong-quan.md` mục 6).

## 4. Ảnh/kết quả cần thu thập trong lúc làm (đừng để cuối)

| Khi nào | Thu gì | Ai |
|---|---|---|
| Sau T0.4 | ảnh PR đầu tiên có check `test` xanh | TV1 |
| Sau T2.3 | output `pytest -m unit -v` | TV2 |
| Sau T3.5 | output test quyền DB | TV3 |
| Sau T4.3 | ảnh `/docs` (Swagger UI) và `docker ps` thấy container `healthy` | TV4, TV1 |
| Sau T6.5 | ảnh job `test` xanh với đủ integration + e2e | TV1 |
| Trước nộp | coverage report, output `simulate_station.py` | TV1 |

Lưu vào `docs/report-assets/` (ảnh nhỏ < 500 KB, PNG).
