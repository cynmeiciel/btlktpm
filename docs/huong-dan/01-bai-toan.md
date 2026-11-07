# 01 — Bài toán, kể bằng lời thường

## 1. Chuyện gì xảy ra khi một công nhân đi qua cổng

1. Công nhân mở app trên điện thoại, app hiện mã QR.
2. Đưa QR vào máy quét ở cổng. Máy tính nhỏ đặt tại cổng (gọi là **Gate Agent**) kiểm tra QR có hợp lệ không.
3. Hợp lệ thì Gate Agent ra lệnh mở cửa xoay (turnstile). Công nhân đi qua.
4. Gate Agent ghi lại một dòng: *"nhân viên X, đi VÀO, lúc 07:58:12, tại cổng BD-G01-IN"*. Dòng này gọi là một **sự kiện chấm công** (`AttendanceEvent`).
5. Sự kiện được ghi vào ổ cứng của chính Gate Agent trước. Sau đó một tiến trình chạy nền (**Sync Worker**) gom nhiều sự kiện thành một **lô** và gửi lên máy chủ trung tâm.
6. Ở trung tâm, **S3 Attendance** nhận lô, lưu vào PostgreSQL, rồi trả lời cho Gate Agent biết sự kiện nào đã lưu xong.
7. Cuối tháng, S4 (dịch vụ báo cáo) đọc dữ liệu S3 đã lưu để tính công và gửi sang hệ thống lương.

**Nhóm mình code bước 6, tức là S3.** Các phần khác (app QR, Gate Agent, S4) chỉ có trong thiết kế M1, không code. Trong M2, vai trò của Gate Agent được đóng bằng test, bằng `curl` và bằng script giả lập.

## 2. Vì sao việc "chỉ lưu vào DB" lại khó

Đề M2 nêu sự cố: **mất kết nối trong lúc xử lý giao dịch**. Xem điều gì có thể xảy ra:

```
Gate Agent                      S3
   │── gửi lô [A, B, C] ─────────▶│  lưu A, B, C xong
   │                              │
   │◀──── trả lời "OK" ──── ✗     │  mạng rớt đúng lúc này
   │
   │  (không nhận được trả lời → không biết S3 đã lưu chưa)
   │── gửi lại lô [A, B, C] ─────▶│  ???
```

Gate Agent không biết S3 đã lưu hay chưa. Lựa chọn an toàn duy nhất là **gửi lại**. Nếu nó không gửi lại, sự kiện có thể mất, tức là công nhân bị mất công.

Vì thế S3 phải chịu được việc **nhận cùng một sự kiện nhiều lần** mà không lưu thành nhiều dòng. Đây là trái tim của bài toán, gọi là **chống trùng lặp** (deduplication).

### Cách nhận ra "cùng một sự kiện"

Mỗi sự kiện có một mã duy nhất `eventId` do Gate Agent sinh ra **một lần**, và giữ nguyên qua mọi lần gửi lại. Giống như số hiệu thư bảo đảm: bưu điện nhận hai lá cùng số hiệu thì biết đó là một lá gửi hai lần.

> Luật 8: **S3 không tự sinh `eventId`.** Nếu S3 sinh mã mới mỗi lần nhận, hai lần gửi sẽ thành hai mã khác nhau và chống trùng thất bại.

### Trùng lặp (duplicate) và xung đột (conflict)

Khi nhận một `eventId` đã có trong DB, S3 so sánh **nội dung**:

| Tình huống | Ví dụ | Kết luận |
|---|---|---|
| Cùng `eventId`, nội dung y hệt | Gửi lại do mạng rớt | `DUPLICATE`: bình thường, bỏ qua, báo "đã có rồi" |
| Cùng `eventId`, nội dung khác | Lỗi phần mềm trạm hoặc dữ liệu bị sửa | `CONFLICT`: bất thường, ghi vào bảng xung đột để người kiểm tra |

Để so nội dung nhanh, S3 tính **payload hash**: biến 9 trường của sự kiện thành một chuỗi 64 ký tự (sha256). Nội dung giống thì hash giống, khác một chữ thì hash khác hẳn.

### Vì sao không "kiểm tra trước rồi mới lưu"

Cách nghĩ tự nhiên là: *"SELECT xem eventId có chưa, chưa có thì INSERT"*. Cách này sai khi hai request đến cùng lúc:

```
Request 1: SELECT → chưa có     
Request 2: SELECT → chưa có      (request 1 chưa kịp INSERT)
Request 1: INSERT → OK
Request 2: INSERT → OK           → hai dòng cùng eventId!
```

Vì vậy chúng ta để **PostgreSQL** bảo đảm: cột `event_id` là `PRIMARY KEY`, DB từ chối dòng thứ hai bất kể code viết thế nào. → **Luật 3.**

## 3. "Chỉ báo OK khi đã cất vào két"

Nếu S3 trả lời "OK" *trước khi* dữ liệu thật sự được ghi xuống đĩa, rồi máy chủ sập, thì Gate Agent tưởng đã xong và xoá bản sao của mình. Sự kiện mất vĩnh viễn.

Giống như thủ quỹ chỉ ký biên nhận sau khi tiền đã vào két. Trong DB, "vào két" là **commit transaction**. → **Luật 2: ACK sau commit.**

## 4. Sổ ghi bằng mực, không tẩy xoá

Dữ liệu chấm công là căn cứ trả lương. Nếu ai đó (hoặc một bug) sửa được giờ vào cổng thì không còn tin được nữa.

Nên S3 **không bao giờ UPDATE hay DELETE** sự kiện gốc. Có sai thì ghi thêm một bản ghi điều chỉnh (giống kế toán ghi bút toán điều chỉnh, không tẩy sổ). Để chắc chắn, ngay ở mức DB, tài khoản mà app dùng **không có quyền** UPDATE/DELETE bảng này. Code có bug cũng không sửa được. → **Luật 4.**

## 5. Outbox: "nhớ báo cho người khác"

Khi lưu xong một sự kiện, S3 cần báo cho hệ thống khác (ví dụ S4). Nếu lưu sự kiện xong rồi mới gửi tin, mà máy sập ở giữa, thì sự kiện có nhưng tin báo không bao giờ được gửi.

Cách giải quyết: ghi tin báo vào một bảng **outbox** trong cùng một transaction với sự kiện. Hai việc cùng thành công hoặc cùng thất bại, không bao giờ lệch nhau. Một tiến trình khác sẽ đọc outbox và gửi đi sau. → **Luật 5.** Trong M2 mình chỉ cần *ghi* outbox, phần gửi đi là stretch.

## 6. Sự cố thứ hai của đề: QR bị lộ

Mã QR cố định có thể bị chụp lại và dùng để chấm công hộ. Thiết kế M1 xử lý bằng QR **động**: mỗi mã có chữ ký số và hết hạn sau vài chục giây, Gate Agent kiểm chữ ký ngay tại cổng. Việc này thuộc S1 và Gate Agent, không thuộc S3. Nhóm chỉ làm nếu còn thời gian (`../14-s1-stretch.md`).

Phần liên quan đến S3: S3 chỉ biết `employeeRef`, một mã UUID giả danh, không biết tên hay số điện thoại. Không log token hay toàn bộ dữ liệu. → **Luật 9**, bảo vệ dữ liệu cá nhân.

## 7. Tóm lại S3 làm đúng ba việc

1. **Nhận lô sự kiện** từ trạm (`POST /v1/attendance-event-batches`). Mỗi sự kiện trả về một trong bốn kết quả: `ACCEPTED`, `DUPLICATE`, `CONFLICT`, `REJECTED`.
2. **Lưu an toàn**: chống trùng bằng DB, ACK sau commit, không sửa xoá, ghi outbox cùng transaction.
3. **Cho xem lịch sử** chấm công của một nhân viên (`GET /v1/employees/{employeeRef}/attendance-events`), và cung cấp một view cho S4 đọc.

Tiếp theo: [02-kien-truc.md](02-kien-truc.md), giải thích code được sắp xếp thế nào để làm được những điều trên.
