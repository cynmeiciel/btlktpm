# 00 — Tổng quan M2

## 1. Đề bài M2 nói gì

Assignment M2 giữ nguyên bối cảnh M1 và yêu cầu:

- **Task 1** — hoàn thiện thiết kế. So với M1, Task 1.2 có thêm yêu cầu trình bày kiến trúc theo **module views, component-and-connector views và allocation views**; có thêm Task 1.3 (giải thích áp dụng SOLID) và Task 1.4 (Reflection Report).
- **Task 2** — hiện thực: "choose at least one main module to implement", code tuân SOLID.
- Nộp: một báo cáo chi tiết kèm GitHub URL trên LMS.

Đề không yêu cầu test hay CI/CD. Nhóm làm vì đó là cách chứng minh rõ nhất rằng code đúng thiết kế (ví dụ: dependency rule được máy kiểm, không chỉ được hứa trong báo cáo). Giữ ở mức vừa đủ, đừng để hạ tầng ăn mất thời gian code nghiệp vụ.

## 2. Phạm vi code đã chốt

| Hạng mục | Trạng thái |
|---|---|
| S3 Attendance — tiếp nhận lô sự kiện, chống trùng, xung đột, outbox | **Bắt buộc** |
| S3 — tra lịch sử cá nhân (UC09), view `v1` cho S4 | **Bắt buộc** |
| S3 — điều chỉnh công có phê duyệt (ADR08, UC11) | Stretch 1 |
| S3 — outbox relay (đẩy outbox ra ngoài) | Stretch 2 |
| S1 — xác thực chữ ký QR | Stretch 3, xem `14-s1-stretch.md` |
| S2, S4, Gate Agent, UI | Ngoài phạm vi code M2 |

## 3. Vì sao chọn S3

- Báo cáo M1, Hình 7, đã vẽ sẵn cấu trúc Ports & Adapters của S3 và ghi rõ nó là "khuôn chung cho cả bốn dịch vụ". Code S3 là hiện thực trực tiếp một hình đã có trong báo cáo.
- S3 có logic nghiệp vụ thật để thể hiện SOLID: luật chống trùng, phân biệt duplicate với conflict, ranh giới transaction event + outbox.
- S3 nằm ở giao điểm của hai ADR quan trọng nhất về độ tin cậy: ADR04 (store-and-forward + dedupe) và ADR08 (event gốc bất biến). NFR-2 "không mất bản ghi" được chứng minh một phần ở đây.
- Test được hoàn toàn bằng phần mềm: không cần máy quét, không cần turnstile.

## 4. S3 nằm ở đâu trong hệ thống

```
Trạm cổng (mỗi làn)                         Trung tâm
┌──────────────────────────┐   HTTPS lô    ┌───────────────────────┐
│ Gate Agent               │  sự kiện      │ Reverse proxy         │
│  └ Local journal + outbox│──────────────▶│  └ S3 Attendance  ◀── M2 code
│  └ Sync Worker           │◀── ACK ───────│      │                │
└──────────────────────────┘               │      ▼                │
                                           │ PostgreSQL            │
                                           │  schema attendance    │
                                           │  view v1_attendance_  │
                                           │       event ──▶ S4    │
                                           └───────────────────────┘
```

Trong M2, Sync Worker không tồn tại. Vai trò của nó được đóng bởi: test e2e, script `scripts/simulate_station.py` (backlog T4.6), và `curl`.

## 5. Ánh xạ tới yêu cầu và ADR của M1

| Mục M1 | S3 thể hiện bằng |
|---|---|
| FR-3 Ghi nhận điểm danh, chống trùng | Ingest API, `DeduplicationRule`, PK `event_id` |
| FR-4 Tra cứu lịch sử (UC09) | `GET /v1/employees/{employeeRef}/attendance-events` |
| NFR-2 Không mất bản ghi | ACK sau commit, outbox cùng transaction |
| NFR-3 RBAC + audit | Station token, actor/role cho read API; quyền DB tối thiểu |
| NFR-4 Dữ liệu cá nhân | S3 chỉ giữ `employeeRef` (UUID), không giữ tên; không log payload |
| ADR02 Schema ownership | Role DB riêng, không FK chéo schema, view `v1` cho S4 |
| ADR04 Store-and-forward + dedupe | Toàn bộ luồng ingest |
| ADR05 Ports and Adapters | Cấu trúc package, import-linter |
| ADR07 Least privilege | Role app không có UPDATE/DELETE trên event |
| ADR08 Event bất biến | Không có đường code sửa event; grant DB chặn |
| DP01–DP09 | Xem `11-solid-mapping.md` |

## 6. Giới hạn cần công bố trong báo cáo

- Môi trường M2 là một host, một PostgreSQL: có SPOF, không gọi là high availability (đúng như báo cáo M1 chương 6, bước 4 đã ghi).
- Xác thực trạm bằng token tĩnh băm sha256 là cơ chế thay thế cho xác thực thiết bị thật (mTLS) — đủ để chứng minh port `StationAuthenticator` và OCP, không đủ cho production.
- Actor của read API lấy từ header do reverse proxy chèn vào; M2 không có S1 để phát JWT thật. Ghi rõ là stub.

## 7. Bất biến kiến trúc — không được phá

Vi phạm bất kỳ điều nào dưới đây là lỗi, kể cả khi test vẫn xanh. Nếu một task có vẻ đòi phá bất biến, dừng lại và hỏi TV1. Reviewer kiểm mục này đầu tiên (`08-team-workflow.md` §3; checklist trong template PR).

1. **Dependency rule (DP09, ADR05)**: `bootstrap → adapters → application → domain`. Mũi tên chỉ hướng được import. `domain` không import framework nào; `application` chỉ import `domain` và stdlib. Kiểm bằng `import-linter` trong CI (`06-ci-cd.md`).
2. **ACK sau commit (ADR04, DP04)**: API chỉ trả `ACCEPTED`/`DUPLICATE` cho một event sau khi transaction chứa event đó đã commit.
3. **Chống trùng lặp bằng ràng buộc DB (ADR04)**: tính duy nhất của `eventId` do `PRIMARY KEY` của PostgreSQL bảo đảm, không do kiểm tra trong code. Không bao giờ viết kiểu "SELECT rồi mới INSERT" để chống trùng.
4. **Event gốc bất biến (ADR08)**: không có code nào `UPDATE` hoặc `DELETE` bảng `attendance.attendance_event`. Role runtime của app không có quyền đó ở mức DB.
5. **Event + outbox cùng một transaction (ADR03 áp dụng phía trung tâm)**: bản ghi event và bản ghi outbox tương ứng được ghi trong cùng một Unit of Work.
6. **Schema ownership (ADR02)**: S3 chỉ ghi schema `attendance`. Không tạo foreign key sang schema của service khác. S4 chỉ đọc qua view có phiên bản `attendance.v1_attendance_event`.
7. **Thời gian chỉ lấy qua port `Clock`**: không gọi `datetime.now()`/`datetime.utcnow()` trong `domain` hay `application`. Mọi `datetime` là timezone-aware, lưu UTC.
8. **S3 không sinh `eventId`**: `eventId` do trạm sinh và giữ nguyên qua mọi lần gửi lại.
9. **Không log dữ liệu cá nhân hay bí mật (NFR-4)**: không log token, không log payload đầy đủ. `employeeRef` (UUID giả danh) được phép log.

## 8. Khi tài liệu mâu thuẫn

Thứ tự ưu tiên: mục 7 ở trên > `02`–`04` (đặc tả) > `01` > các file còn lại. Phát hiện mâu thuẫn thì báo TV1 và sửa tài liệu trước khi code, không tự chọn một bên.
