# 08 — Quy trình làm việc nhóm

## 1. Vai trò

Nhóm 5 người, gọi theo mã TV1–TV5 (dùng thống nhất trong mọi tài liệu).

| Mã | Vai trò | Phụ trách thư mục | Task chính |
|---|---|---|---|
| TV1 | Tech lead — quản lý repo, CI/CD, review | `.github/`, `infra/`, `pyproject.toml`, `uv.lock`, cùng TV3 với `migrations/` | Phase 0, Phase 6, review mọi PR, cập nhật Hình 7 |
| TV2 | Domain + Application | `domain/`, `application/` | Phase 1, Phase 2 |
| TV3 | Persistence | `adapters/outbound/persistence/`, `migrations/` | Phase 3 |
| TV4 | HTTP API | `adapters/inbound/http/` | Phase 4 |
| TV5 | Read side + stretch | — | Phase 5, Phase 7 |

Mọi người đều viết test cho code của mình. TV1 viết hạ tầng test (conftest, fixture DB, contract base class) ở Phase 0 để người khác chỉ việc dùng.

Trong lúc TV2 làm Phase 1–2, TV3 và TV4 không phải chờ: họ code dựa trên **port đã chốt** ở `01-kien-truc-s3.md` (T2.1 làm sớm nhất có thể, xem `09-backlog.md`).

## 2. Vòng đời một task

```
Issue ──▶ nhánh feat/Tx.y-slug ──▶ code + test ──▶ PR ──▶ CI xanh ──▶ TV1 duyệt ──▶ squash merge
```

- Một task = một nhánh = một PR. Ghi `Closes #N` trong PR để issue tự đóng.
- Không push thẳng `main`.
- Nên mở PR nháp (`Draft`) sớm để hỏi ý kiến; đừng ôm nhánh quá lâu rồi mới đẩy lên.
- Hướng dẫn gõ lệnh từng bước: `huong-dan/04-git-tung-buoc.md`.

## 3. Review

TV1 review mọi PR, tập trung vào:

1. Có phá luật nào ở `00-tong-quan.md` §7 không.
2. Test có kiểm đúng hành vi không (đọc `assert`), có đủ các test mức "Bắt buộc" ở `05-testing-strategy.md` §3 không.
3. Tên class/file có khớp `01-kien-truc-s3.md` không.

Style để ruff lo, không bình luận chuyện format. Góp ý thì nói lý do, không phải sở thích.

## 4. Definition of Done

- [ ] PR đã merge, CI xanh.
- [ ] `uv run scripts/dev.py check` sạch ở local (CI không chạy ruff/mypy).
- [ ] Có các test mức "Bắt buộc" của phần mình (`05-testing-strategy.md` §3).
- [ ] Tài liệu bị ảnh hưởng đã cập nhật, nếu có.
- [ ] Gặp khó khăn đáng kể thì ghi 1–3 dòng vào `docs/reflection-log.md` (nguyên liệu cho bài Reflection).

## 5. Dùng công cụ AI

- Mỗi người được dùng công cụ AI ở máy mình. File cấu hình riêng của công cụ không đưa vào repo: mỗi người tự thêm chúng vào `.git/info/exclude` ở máy mình (file này không được push), không sửa `.gitignore` chung.
- Code do AI viết được review như code người viết. Người mở PR chịu trách nhiệm hiểu từng dòng, vì giảng viên có thể hỏi vấn đáp.
- Không dán token, mật khẩu thật hay dữ liệu nhân viên thật vào prompt.

## 6. Nhịp làm việc

- TV1 gán task theo `09-backlog.md` (issue trên GitHub). Bị chặn thì comment ngay trong issue.
- Xong mỗi phase, TV1 chụp màn hình CI và kết quả chạy thử để dùng cho báo cáo.

## 7. Xử lý sự cố thường gặp

| Tình huống | Làm gì |
|---|---|
| `uv.lock` xung đột khi rebase | Lấy bản của `main`, chạy lại `uv add`/`uv lock`, commit |
| Hai migration cùng số | Người merge sau đổi số và `down_revision` |
| CI đỏ nhưng local xanh | Local có thể đã skip test DB: chạy `uv run scripts/dev.py test-db` |
| Cần đổi port đã chốt | Mở issue, TV1 + TV2 quyết; cập nhật `01-kien-truc-s3.md` trước, code sau |
