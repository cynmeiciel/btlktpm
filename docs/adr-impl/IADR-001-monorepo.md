# IADR-001 — Monorepo

Trạng thái: Proposed

## Bối cảnh
M2 code một service (S3), có thể thêm S1. Nhóm 5 người, một học kỳ. Báo cáo cần một GitHub URL.

## Quyết định
Một repo, mỗi service một thư mục `services/<tên>/` với `pyproject.toml` và `uv.lock` riêng. `infra/` và `.github/` dùng chung.

## Phương án đã cân nhắc
- **Mỗi service một repo** — đúng tinh thần triển khai độc lập, nhưng nhân đôi CI, ruleset, template; nộp nhiều URL; đổi hợp đồng giữa S1 và S3 phải phối hợp hai PR.
- **uv workspace** (một `uv.lock` chung) — gọn hơn nhưng ép mọi service cùng phiên bản thư viện, làm mờ ranh giới triển khai độc lập mà ADR01 chọn.

## Hệ quả
- (+) Một pipeline, một chỗ review, một URL.
- (+) Mỗi service vẫn build image và khoá dependency riêng → vẫn là deployment unit độc lập (ADR01).
- (−) Không có rào cản kỹ thuật ngăn S1 import code S3. Bù bằng: không có package dùng chung ngoài `packages/` (nếu có), và review.

## Liên quan
ADR01.
