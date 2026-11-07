# Implementation ADR (IADR)

ADR01–ADR09 trong báo cáo M1 là quyết định **kiến trúc** (style, ranh giới, dữ liệu). IADR ghi quyết định **hiện thực** trong M2 (công cụ, thư viện, ngữ nghĩa API) — đủ quan trọng để không bị đổi tuỳ tiện, nhưng không thuộc tầm kiến trúc.

Mẫu: Bối cảnh · Quyết định · Phương án đã cân nhắc · Hệ quả · Liên quan. Trạng thái: `Proposed` → `Accepted` (khi TV1 merge) → `Superseded by IADR-xxx`.

| Mã | Tiêu đề | Trạng thái |
|---|---|---|
| IADR-001 | Monorepo | Proposed |
| IADR-002 | FastAPI đồng bộ + SQLAlchemy Core + psycopg 3 | Proposed |
| IADR-003 | Toolchain: uv, ruff, mypy strict, import-linter | Proposed |
| IADR-004 | Alembic và tách role DB | Proposed |
| IADR-005 | Ngữ nghĩa lô: mỗi event một transaction | Proposed |
| IADR-006 | Tolerant reader cho request HTTP | Proposed |
