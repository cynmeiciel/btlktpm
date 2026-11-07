# IADR-002 — FastAPI endpoint đồng bộ, SQLAlchemy Core, psycopg 3

Trạng thái: Proposed

## Bối cảnh
Nhóm chọn FastAPI. Tải của S3 rất nhỏ (~0,45 event/giây trung bình; đỉnh vài chục event/giây khi trạm xả hàng đợi sau mất mạng). Điều quan trọng nhất là **đúng giao dịch**: event + outbox cùng transaction, ACK sau commit, dedupe dưới truy cập đồng thời (ADR03, ADR04).

## Quyết định
1. Endpoint khai báo bằng `def`. FastAPI chạy chúng trong threadpool.
2. Truy cập DB bằng SQLAlchemy 2.0 **Core** (`Table`, `insert()`, `select()`), không dùng ORM `Session`/mapped class.
3. Driver `psycopg` 3, bản sync, `create_engine("postgresql+psycopg://...")`.
4. Unit of Work tự viết, bọc `Connection.begin()`.

## Phương án đã cân nhắc
- **`async def` + SQLAlchemy async + asyncpg** — idiomatic hơn với FastAPI, nhưng: phải đảm bảo không có lời gọi chặn nào trong luồng async; lỗi quản lý session/transaction khó thấy hơn; test async thêm `pytest-asyncio`. Không có lợi ích hiệu năng ở tải này.
- **ORM** — tiện cho CRUD, nhưng ở đây cần SQL chính xác (`INSERT ... ON CONFLICT DO NOTHING RETURNING`), không cần identity map hay lazy load. ORM còn khuyến khích dùng mapped class làm entity, phá ranh giới domain.

## Hệ quả
- (+) Transaction tường minh, dễ đọc, dễ chứng minh trong báo cáo.
- (+) Domain entity độc lập hoàn toàn với SQLAlchemy.
- (−) Threadpool mặc định của Starlette giới hạn số request đồng thời (~40). Thừa đủ cho tải này; ghi lại để biết nếu tải đổi.
- (−) Ánh xạ hàng ↔ entity viết tay trong repository.

## Liên quan
ADR03, ADR04, ADR05.
