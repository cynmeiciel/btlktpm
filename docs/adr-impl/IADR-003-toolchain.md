# IADR-003 — Toolchain: uv, ruff, mypy strict, import-linter

Trạng thái: Proposed

## Bối cảnh
5 người, máy Windows và Arch Linux, CI GitHub Actions. Cần môi trường giống nhau ở mọi nơi, và cần **máy kiểm** các quy tắc kiến trúc thay vì chỉ ghi trong báo cáo.

## Quyết định
- `uv`: quản lý Python (ghim 3.13), venv, dependency, lock file. CI dùng `uv sync --locked`.
- `ruff`: lint + format (thay flake8, isort, black). Bật `DTZ` (cấm datetime không timezone), `S` (bảo mật).
- `mypy --strict` trên `src`; `tests` được nới (không bắt type hint ở hàm test) để người mới viết test nhanh hơn.
- `import-linter`: 4 contract biểu diễn dependency rule của Hình 7 / DP09.
- `scripts/dev.py` (Python thuần) thay `Makefile` để lệnh kiểm tra chạy giống nhau trên Windows và Linux.
- `pre-commit`: ruff + lint-imports trước mỗi commit.

## Phương án đã cân nhắc
- `pip` + `venv` + `requirements.txt` — không có lock thật, Arch chặn pip hệ thống (PEP 668), dễ lệch phiên bản giữa máy.
- `poetry` — được, nhưng chậm hơn và không tự quản lý phiên bản Python.
- `pyright` thay mypy — tương đương; chọn mypy vì có plugin pydantic chính thức.
- Kiểm dependency rule bằng review — không đáng tin qua thời gian (báo cáo M1 4.4, lý do 3: "ranh giới module trong một tiến trình chỉ tồn tại nhờ kỷ luật ... nó mòn dần").

## Hệ quả
- (+) `lint-imports` là fitness function cho DIP, chạy mỗi PR.
- (+) Python của Arch nâng cấp không ảnh hưởng dự án.
- (−) mypy strict tốn công lúc đầu. Giảm bằng cách chỉ áp đầy đủ cho `src`.

## Liên quan
ADR05, DP09.
