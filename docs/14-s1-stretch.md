# 14 — Stretch: S1 Identity and QR (chỉ phần xác thực QR)

Chỉ bắt đầu khi Phase 0–6 xong. Mục tiêu: cho thấy khuôn Ports & Adapters của S3 áp lại được cho service thứ hai (đúng tinh thần "khuôn chung" của Hình 7 M1), và giải quyết vấn đề "QR tĩnh có thể bị lộ" ở mức mã nguồn.

## 1. Bám báo cáo M1

- Giả định A3: QR **cố định** cho mỗi nhân viên, trạm tự xác thực ngoại tuyến bằng **khoá công khai**.
- Bước 5 M1 (Security): khoá riêng chỉ nằm trong S1 (secret store); trạm chỉ giữ khoá công khai.
- Hình 3, bước [03]: trạm kiểm "định dạng, chữ ký, issuer, audience, key version".
- UC02: phát hành / thu hồi QR. Bảng `Credential`: `credential_version`, `revoked_at`, `status`.

Chữ ký **bất đối xứng** (Ed25519), không phải HMAC — HMAC buộc trạm giữ khoá bí mật, trái Bước 5.

## 2. Phạm vi

| Có | Không |
|---|---|
| Phát hành credential cho một `employeeRef` → chuỗi QR đã ký | Quản lý hồ sơ nhân viên đầy đủ (UC03) |
| Thu hồi credential (tăng `credentialVersion`) | Tài khoản, vai trò, đăng nhập (UC13) |
| Endpoint công bố khoá công khai (JWKS) | Ứng dụng di động hiển thị QR |
| Endpoint công bố danh sách credential còn hiệu lực theo phiên bản (để trạm tải) | Gate Agent |
| Thư viện `QrVerifier` dùng chung được (trạm sẽ dùng) | Xoay khoá tự động |

## 3. Định dạng QR

Compact JWS (`header.payload.signature`, base64url), thuật toán `EdDSA` (Ed25519).

Header: `{"alg":"EdDSA","kid":"s1-2026-01","typ":"tmc-qr+jwt"}`

Payload (giữ nhỏ để mã QR không quá dày):

| Claim | Ý nghĩa |
|---|---|
| `iss` | `tmc-s1` |
| `aud` | `tmc-gate` |
| `sub` | `employeeRef` (UUID) — **không** chứa tên, mã nhân viên HR (NFR-4) |
| `cv` | `credentialVersion` (int) |
| `iat` | thời điểm phát hành |

Không có `exp`: QR tĩnh theo A3. Hiệu lực do `cv` quyết định — trạm chỉ chấp nhận `cv` bằng phiên bản hiện hành của `sub` trong danh sách đã tải về. Thu hồi = tăng `cv`; QR cũ hết hiệu lực ngay khi trạm tải danh sách mới (trong cửa sổ offline vẫn có độ trễ — giới hạn đã ghi ở bảng pattern M1 4.5).

## 4. Cấu trúc (lặp khuôn S3)

```
services/s1-identity-qr/src/tmc_identity/
  domain/        Credential, CredentialStatus, QrClaims, luật thu hồi
  application/   ports: CredentialRepository, Signer, KeyProvider, Clock
                 use case: IssueCredential, RevokeCredential, ListActiveCredentials
  adapters/
    inbound/http/
    outbound/    Ed25519Signer (thư viện `cryptography`), FileKeyProvider (M2) / VaultKeyProvider (tương lai),
                 PostgresCredentialRepository (schema identity)
  bootstrap/
packages/qr-verifier/   QrVerifier thuần (chỉ phụ thuộc `cryptography`), có test vector
```

`QrVerifier.verify(token, public_keys, active_versions) -> VerifiedQr | QrRejection` — trả lý do: `MALFORMED`, `UNKNOWN_KID`, `BAD_SIGNATURE`, `WRONG_ISSUER`, `WRONG_AUDIENCE`, `REVOKED_VERSION`.

## 5. Test bắt buộc nếu làm

- Chữ ký hợp lệ / sửa 1 byte payload → `BAD_SIGNATURE`.
- `kid` lạ → `UNKNOWN_KID`.
- Thu hồi → QR cũ `REVOKED_VERSION`, QR mới hợp lệ.
- QR không chứa tên hay dữ liệu cá nhân ngoài UUID (test đọc payload).
- Test vector cố định (khoá test cố định trong `tests/`, **không** dùng ở đâu khác).
- Import-linter: cùng 4 contract như S3.

## 6. CI

Thêm `strategy.matrix.service: [s3-attendance, s1-identity-qr]` vào job `test` và đổi `working-directory` theo `matrix.service`. Vẫn chỉ chạy test (`06-ci-cd.md`).
