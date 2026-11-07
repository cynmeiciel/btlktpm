# 03 — Hợp đồng HTTP API của S3

Nguồn sự thật lúc chạy là OpenAPI do FastAPI sinh (`/openapi.json`, giao diện `/docs`). Tài liệu này là đặc tả để code theo.

## 1. Quy ước chung

| Mục | Quy ước |
|---|---|
| Base path | `/v1` cho API nghiệp vụ; `/health/*` không có version |
| Định dạng | JSON UTF-8; tên trường **camelCase** (khớp `eventId`, `localSequence` trong báo cáo M1) |
| Thời gian | ISO 8601 có offset bắt buộc. Thiếu offset → item bị REJECTED/INVALID_FORMAT. Response luôn trả UTC dạng `...Z` |
| ID | UUID dạng chuỗi |
| Lỗi | JSON `{"detail": ...}` như mặc định của FastAPI; riêng 422 bỏ giá trị đầu vào (mục 5) |
| Versioning | Thay đổi phá tương thích → `/v2`. Thêm trường tuỳ chọn vào response không phá tương thích |

## 2. `POST /v1/attendance-event-batches` — tiếp nhận lô sự kiện

Gọi bởi Sync Worker của Gate Agent (M2: test, script giả lập, curl).

### Xác thực

`Authorization: Bearer <station token>`. Token ánh xạ tới đúng một `stationId`. Thiếu/sai → 401.

### Request

```json
{
  "stationId": "BD-G01-IN",
  "events": [
    {
      "eventId": "0b9f6c1e-6a52-4b7e-9a51-2f1b8d0c3a11",
      "attemptId": "5a3c2e10-1d4f-4c8b-8f7e-0a9b1c2d3e4f",
      "employeeRef": "9e8d7c6b-5a49-4382-a1b0-c9d8e7f6a5b4",
      "stationId": "BD-G01-IN",
      "direction": "IN",
      "occurredAt": "2026-11-03T07:58:12.345+07:00",
      "localSequence": 1042,
      "evidenceLevel": "CONTROLLER_CONFIRMED",
      "schemaVersion": 1
    }
  ]
}
```

| Trường | Kiểu | Bắt buộc | Ràng buộc |
|---|---|---|---|
| `stationId` (envelope) | string | có | phải bằng trạm của token, sai → 403 |
| `events` | array | có | 1 ≤ số phần tử ≤ `TMC_S3_MAX_BATCH_SIZE` (500), sai → 422 |
| `events[].eventId` | uuid | có | do trạm sinh, ổn định qua mọi lần gửi lại |
| `events[].attemptId` | uuid | có | `AccessAttempt` gốc tại trạm |
| `events[].employeeRef` | uuid | có | |
| `events[].stationId` | string | có | 1–64 ký tự `[A-Za-z0-9_-]` |
| `events[].direction` | `IN` \| `OUT` | có | |
| `events[].occurredAt` | datetime có offset | có | ≤ thời điểm nhận + 300s |
| `events[].localSequence` | integer ≥ 0 | có | số thứ tự do trạm đánh; lưu để điều tra, M2 không kiểm trùng |
| `events[].evidenceLevel` | `CONTROLLER_CONFIRMED` \| `CONTROLLER_UNCONFIRMED` \| `GUARD_RECORDED` | có | |
| `events[].schemaVersion` | integer | có | hiện chỉ `1` |

**Trường lạ (tolerant reader, IADR-006)**: ở cả envelope lẫn item, trường không có trong bảng trên bị **bỏ qua**, không reject. Lý do: Gate Agent tại các trạm được nâng cấp không đồng thời; trạm phiên bản mới thêm trường không được làm kẹt store-and-forward của trạm đó. Trường lạ không vào `payload_hash` (hash chỉ tính trên 9 trường chuẩn, `02-domain-model.md` §4), nên bỏ qua chúng không ảnh hưởng dedupe. Thay đổi phá tương thích đi qua `schemaVersion` hoặc `/v2`, không qua trường lạ.

**Parse hai tầng**: envelope parse chặt theo nghĩa *thiếu trường bắt buộc, sai kiểu, hoặc `events` ngoài khoảng 1…`TMC_S3_MAX_BATCH_SIZE`* → 422 cho cả request (trường lạ vẫn bỏ qua như trên). Từng item parse riêng: item hỏng chỉ làm item đó `REJECTED/INVALID_FORMAT`, các item khác vẫn được xử lý. Vì vậy trong schema Pydantic, `events` là `list[dict[str, Any]]` ở tầng envelope, mỗi phần tử được validate bằng model `EventIn` trong controller.

### Response 200

Luôn là 200 khi request được xử lý, kể cả khi mọi item bị từ chối. Thứ tự `results` = thứ tự `events`.

```json
{
  "results": [
    { "index": 0, "eventId": "0b9f…3a11", "status": "ACCEPTED" },
    { "index": 1, "eventId": "1c2d…4b22", "status": "DUPLICATE" },
    { "index": 2, "eventId": "2d3e…5c33", "status": "CONFLICT", "reason": "PAYLOAD_MISMATCH" },
    { "index": 3, "eventId": null, "status": "REJECTED", "reason": "INVALID_FORMAT",
      "errors": [ { "field": "eventId", "message": "Field required" } ] }
  ],
  "summary": { "accepted": 1, "duplicate": 1, "conflict": 1, "rejected": 1 }
}
```

| Trường | Ghi chú |
|---|---|
| `index` | vị trí trong `events`, luôn có |
| `eventId` | `null` nếu không đọc được UUID hợp lệ |
| `status` | `ACCEPTED` \| `DUPLICATE` \| `CONFLICT` \| `REJECTED` |
| `reason` | có khi `CONFLICT` hoặc `REJECTED` |
| `errors` | chỉ khi `INVALID_FORMAT`; danh sách `{field, message}`; **không** chứa giá trị gốc (tránh lộ dữ liệu vào log phía trạm) |

### Hợp đồng với Sync Worker

| Status | Trạm phải làm |
|---|---|
| `ACCEPTED`, `DUPLICATE` | Đánh dấu đã đồng bộ (Hình 4 M1, bước [07]) |
| `CONFLICT` | Không gửi lại; cách ly, cảnh báo vận hành |
| `REJECTED` | Không gửi lại nguyên trạng; cách ly, cảnh báo |
| HTTP 5xx, timeout, mất kết nối | Gửi lại **cả lô**, cùng `eventId`, backoff có jitter (Hình 5 M1, tình huống 2–3) |
| HTTP 401/403 | Dừng đồng bộ, cảnh báo cấu hình |
| HTTP 422 | Lỗi phía trạm; cảnh báo, không lặp vô hạn |

Gửi lại cả lô sau 5xx là an toàn: item đã commit trở thành `DUPLICATE`.

### Mã lỗi

| HTTP | Khi nào |
|---|---|
| 401 | thiếu/sai token |
| 403 | `stationId` envelope ≠ trạm của token |
| 422 | envelope sai (thiếu `events`, quá 500 item, JSON hỏng) |
| 503 | DB không sẵn sàng / lỗi hạ tầng |

## 3. `GET /v1/employees/{employeeRef}/attendance-events` — lịch sử (UC09)

### Xác thực actor (stub M2)

M2 chưa có S1 phát token người dùng. Reverse proxy (hoặc test) chèn header:

| Header | Ví dụ |
|---|---|
| `X-Actor-Id` | `3f1e…` (uuid) |
| `X-Actor-Employee-Ref` | uuid, tuỳ chọn (tài khoản không gắn nhân viên thì không có) |
| `X-Actor-Roles` | `EMPLOYEE` hoặc `HR,EMPLOYEE` |

Thiếu `X-Actor-Id` hoặc `X-Actor-Roles` → 401. Role lạ → bỏ qua role đó. Việc đọc header gói trong một hàm của adapter, `read_actor(request) -> ActorContext` ở `security.py`; khi có S1 chỉ cần thay hàm này bằng bộ xác minh JWT — use case không đổi vì nó chỉ nhận `ActorContext`.

**Ghi rõ trong báo cáo**: header actor chỉ được tin vì giả định chỉ reverse proxy gọi được S3. Đây là stub, không phải cơ chế bảo mật.

### Query

| Tham số | Bắt buộc | Mặc định | Ràng buộc |
|---|---|---|---|
| `from` | có | — | datetime có offset |
| `to` | có | — | > `from`, `to - from` ≤ 62 ngày |
| `limit` | không | 50 | 1–200 |
| `offset` | không | 0 | ≥ 0; số bản ghi bỏ qua (trang sau = `offset + limit`) |

### Response 200

```json
{
  "items": [
    {
      "eventId": "0b9f…3a11",
      "stationId": "BD-G01-IN",
      "direction": "IN",
      "occurredAt": "2026-11-03T00:58:12.345000Z",
      "receivedAt": "2026-11-03T00:58:14.002000Z",
      "evidenceLevel": "CONTROLLER_CONFIRMED"
    }
  ],
  "hasMore": false
}
```

Sắp xếp `occurredAt` tăng dần, rồi `eventId` (để thứ tự ổn định giữa các trang). `hasMore` = còn bản ghi sau trang này. Phân trang bằng `LIMIT`/`OFFSET`: đơn giản, đủ nhanh với lượng dữ liệu một nhân viên trong ≤ 62 ngày.

### Mã lỗi

| HTTP | Khi nào |
|---|---|
| 401 | thiếu header actor |
| 403 | `can_read_history` sai |
| 422 | tham số sai, khoảng > 62 ngày |
| 503 | DB không sẵn sàng |

## 4. Health

| Endpoint | Trả về | Dùng cho |
|---|---|---|
| `GET /health/live` | 200 `{"status":"ok"}` nếu tiến trình chạy | liveness; không chạm DB |
| `GET /health/ready` | 200 `{"status":"ready"}` nếu `HealthProbe.is_ready()`; ngược lại 503 `{"status":"not_ready"}` | readiness, Docker healthcheck |

Báo cáo M1, chương 6 bước 6, quy tắc vận hành 1: "Mọi dịch vụ có health check và readiness check."

## 5. Định dạng lỗi

Dùng định dạng mặc định của FastAPI, chỉ thêm một chỗ: handler 422.

```json
{ "detail": "Envelope stationId does not match the authenticated station." }
```

- 401, 403: route `raise HTTPException(status_code=..., detail="...")`. 401 kèm header `WWW-Authenticate: Bearer`.
- 422: thay handler `RequestValidationError` mặc định để **không trả lại giá trị đầu vào** (mặc định FastAPI có trường `input`, có thể chứa dữ liệu cá nhân):
  ```json
  { "detail": "Validation failed", "errors": [ { "field": "events", "message": "List should have at most 500 items" } ] }
  ```
- 503: handler cho `sqlalchemy.exc.OperationalError` (DB mất kết nối) trả `{"detail": "Service unavailable"}`. Trạm gặp 503 sẽ gửi lại.
- Lỗi không lường trước: để FastAPI trả 500 mặc định; chi tiết chỉ nằm trong log server.

## 6. Hiệu năng (thông tin, không phải NFR)

NFR-1 (≤ 2 giây) đo tại kiosk và được bảo đảm bởi xử lý tại trạm (Hình 3 M1). S3 nằm ngoài đường mở cổng. Mục tiêu tham khảo cho S3 trên máy dev: lô 100 event mới xử lý xong < 1 giây. Tải thật: 800 lượt / 30 phút / nhà máy ≈ 0,45 event/giây — rất nhỏ.
