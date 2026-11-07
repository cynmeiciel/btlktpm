# 04 — Git và PR, từng bước

Quy trình đầy đủ ở `../08-team-workflow.md`. File này là phiên bản "gõ lệnh theo".

## 1. Làm một lần khi mới vào

Làm theo `../10-local-setup.md`: §2 (Windows) hoặc §3 (Arch), rồi §4 (cấu hình Git) và §5 (clone, chạy thử). Xong khi `uv run scripts/dev.py all` không báo lỗi. Nếu cổng 5432 bị chiếm, xem §8 của file đó.

Các lệnh Git dưới đây giống nhau trên PowerShell và bash.

## 2. Quy trình cho mỗi task

Ví dụ bạn nhận task **T1.1**, issue số **#12**.

### Bước 1: lấy code mới nhất và tạo nhánh

```bash
git switch main
git pull
git switch -c feat/T1.1-attendance-event
```

Tên nhánh: `<loại>/<mã task>-<mô tả ngắn>`. Loại: `feat`, `fix`, `test`, `docs`, `chore`.

### Bước 2: code và commit nhỏ

```bash
# ... sửa code, viết test ...
uv run scripts/dev.py check && uv run scripts/dev.py test                # phải sạch trước khi commit
git add src/tmc_attendance/domain/model.py tests/unit/domain/test_model.py
git commit -m "feat(s3): add AttendanceEvent entity with invariants"
```

- Commit message bằng **tiếng Anh**, dạng mệnh lệnh: `add`, `fix`, `reject`, không phải `added`, `fixes`.
- Mỗi commit là một bước hợp lý (ví dụ "thêm enum", "thêm entity"). Không gom cả task vào một commit khổng lồ, cũng không commit "wip" lung tung.
- `git add` từng file cụ thể. Tránh `git add .` nếu chưa xem `git status`, để không lỡ commit `.env`.

### Bước 3: đẩy lên và mở PR

```bash
git push -u origin feat/T1.1-attendance-event
gh pr create --fill                    # hoặc mở trên web GitHub
```

Trong mô tả PR (template tự hiện):
- Ghi `Closes #12` để issue tự đóng khi merge.
- Tick checklist, đặc biệt dòng về 9 luật ở `../00-tong-quan.md` §7.
- Chưa xong mà muốn hỏi ý kiến thì mở **Draft PR**. Việc này được khuyến khích.

### Bước 4: chờ CI và review

- CI (job `test`) chạy tự động. Đỏ thì bấm vào xem log, sửa, commit và push lại. PR tự cập nhật.
- TV1 review. Có góp ý thì sửa bằng commit mới rồi `git push`. **Không cần** tạo PR mới.
- Đã xanh và được duyệt thì TV1 bấm **Squash and merge**. Mọi commit của bạn gộp thành một commit trên `main`.

### Bước 5: dọn dẹp

```bash
git switch main
git pull
git branch -d feat/T1.1-attendance-event
```

## 3. Cập nhật nhánh khi `main` có code mới

Người khác merge trước bạn thì cần đưa code mới vào nhánh của mình:

```bash
git fetch origin
git rebase origin/main
# nếu có xung đột: mở file, sửa chỗ có <<<<<<< ======= >>>>>>>
git add <file đã sửa>
git rebase --continue
git push --force-with-lease            # bắt buộc sau rebase; KHÔNG dùng --force trần
```

Rebase hỏng, rối quá thì `git rebase --abort` để quay lại như cũ, rồi hỏi TV1.

**Xung đột ở `uv.lock`**: đừng sửa tay. Lấy bản của `main`, rồi để uv tính lại từ `pyproject.toml` (đã gộp xong):

```bash
git checkout origin/main -- uv.lock
uv lock
git add uv.lock
git rebase --continue
```

## 4. Những điều không làm

| Không làm | Vì sao |
|---|---|
| Push thẳng lên `main` | Bỏ qua CI và review |
| `git push --force` (không có `-with-lease`) | Có thể xoá mất commit của người khác |
| Commit file `.env` | Chứa mật khẩu. Đã có trong `.gitignore`, nhưng vẫn nên kiểm `git status` |
| Sửa migration đã merge | Máy người khác đã chạy bản cũ. Muốn đổi thì tạo migration mới |
| Một PR làm nhiều task | Khó review. Một task = một nhánh = một PR, dưới ~400 dòng |
| Để nhánh sống quá 3 ngày | Càng lâu càng nhiều xung đột |

## 5. Lệnh cứu hộ hay dùng

| Muốn | Lệnh |
|---|---|
| Xem đang ở nhánh nào, file nào đã sửa | `git status` |
| Xem mình đã sửa gì | `git diff` |
| Bỏ thay đổi chưa commit của một file | `git restore <file>` |
| Bỏ file khỏi staging (đã `git add` nhầm) | `git restore --staged <file>` |
| Sửa message của commit cuối (chưa push) | `git commit --amend` |
| Cất tạm thay đổi để chuyển nhánh | `git stash`, sau đó `git stash pop` |
