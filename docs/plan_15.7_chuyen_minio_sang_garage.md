# Kế hoạch 15.7 - Chuyển object storage từ MinIO sang Garage

Ngày lập: 2026-10-30

Trạng thái: **Đề xuất, chưa triển khai.** Mọi lệnh và cấu hình trong tài liệu này là phác thảo; chỉ được coi là đã kiểm chứng khi slice tương ứng ghi nhận bằng chứng.

## 1. Mục tiêu

Thay MinIO (kho tệp ứng dụng + đích sao lưu) bằng **Garage** chạy một node, với các ràng buộc:

- Không đổi hành vi nhìn thấy được của người dùng: tải lên, tải xuống, xóa tệp đính kèm; Backup Console tiếp tục chạy sao lưu DB và kho tệp.
- Không mất dữ liệu: mọi object hiện có được chép sang Garage với **cùng tên object**, đối chiếu bằng kích thước và `sha256`.
- Có đường lui rõ ràng trong suốt giai đoạn cutover.
- Loại bỏ mọi phụ thuộc vào thứ không còn kéo được từ internet (image `minio/minio`, `minio/mc`, `dl.min.io`).

## 2. Lý do thay đổi (bằng chứng ngày 2026-10-30)

Kiểm tra trực tiếp từ máy dev, không đăng nhập:

| Mục | Kết quả |
|---|---|
| `docker manifest inspect minio/minio:latest` và đúng tag đang dùng `RELEASE.2025-09-07T16-13-09Z` | `denied` |
| `docker manifest inspect minio/mc:latest` | `denied` |
| Docker Hub API `minio/minio`, `minio/mc` | HTTP 404 |
| `quay.io/minio/minio:latest` | no such manifest |
| `https://dl.min.io/client/mc/release/linux-amd64/mc` | HTTP 410 (Gone) |
| GitHub `minio/minio` | Đã archived (25/04/2026); README: không còn phát hành binary/image cho bản community |
| GitHub `minio/mc` | Đã archived (14/07/2026) |

Hệ quả cho dự án:

- Container đang chạy không sao (image đã nằm trong máy), nhưng **máy mới, khôi phục sau sự cố, `docker compose pull` và CI đều không kéo lại được image**.
- Không còn bản vá bảo mật cho MinIO community.
- Image sao lưu cũ (`docker/backup/Dockerfile:37`) không build được vì `mc` trả 410.

## 3. Bằng chứng hiện trạng trong repo

### 3.1. Ứng dụng chỉ dùng 7 thao tác S3 cơ bản

Đếm các lời gọi SDK trong `backend/app`:

| Thao tác | Số lần gọi |
|---|---|
| `put_object` | 9 |
| `bucket_exists` | 6 |
| `get_object` | 5 |
| `make_bucket` | 3 |
| `list_objects` | 3 |
| `stat_object` | 1 |
| `remove_object` | 1 |

Không có: presigned URL, `copy_object`, versioning, bucket policy, lifecycle, tagging. File được phát qua API (`get_object_stream`) nên kho **không cần truy cập được từ trình duyệt**, chỉ cần từ `backend` và `celery_*`.

### 3.2. Điểm chạm trong code

| Vị trí | Vai trò | Ghi chú |
|---|---|---|
| `backend/app/core/storage.py:91-97` | `_client()` dựng client cho tệp đính kèm | Đọc `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/SECURE` |
| `backend/app/core/storage.py:118-126` | `bucket_name()`, `ensure_bucket()` | `ensure_bucket()` gọi `make_bucket` nếu bucket chưa có |
| `backend/app/main.py:81` | `ensure_bucket()` trong `lifespan` | **Nếu lỗi thì backend không khởi động** |
| `backend/app/main.py:143-149` | Health check, khóa `checks["minio"]` | Gọi `bucket_exists` |
| `backend/app/core/storage.py:163-186` | `get_object_stream`, `get_object_bytes` | Phát file qua API |
| `backend/app/core/storage.py:254-259` | `delete_attachment` | Chỉ nuốt `S3Error` chung |
| `backend/app/core/circuit_breaker.py:141` | `minio_circuit` | Tên "minio" |
| `backend/app/services/backup_runner_service.py:86-96, 99-111` | Client đích sao lưu; tạo bucket đích nếu thiếu (`:108`) | Dùng `BACKUP_STORAGE_*` |
| `backend/app/services/restore_runner_service.py:44-47, 66, 373` | Client khôi phục; `make_bucket` bucket đích (`:373`) | Khôi phục "sang đích mới" cần quyền tạo bucket |
| `backend/app/services/backup_service.py:539-552` | `_probe_target_bucket` (nút "Kiểm tra đích sao lưu") | `bucket_exists` |
| `backend/app/services/backup_service.py:40-43` | Nhãn `"Kho tệp ứng dụng trên MinIO"` | Chuỗi hiển thị trên UI |
| `backend/app/core/config.py:132-136, 139-164` | `MINIO_*` và bộ kiểm tra giá trị không an toàn | Chỉ ép buộc khi `ENVIRONMENT=production` |
| `backend/app/core/config.py:222-235` | `BACKUP_STORAGE_*`, `SOURCE_STORAGE_*` | |
| `backend/app/core/config.py:278-286` | Tên bucket mặc định `hrms-attachments-<env>` | `ENVIRONMENT=lan` ra hậu tố `dev` |

Có **4 chỗ khởi tạo `Minio(...)`** rời nhau: `storage.py:92`, `restore_runner_service.py:45`, `backup_service.py:544`, `backup_runner_service.py:87`.

### 3.3. Hạ tầng

| Vị trí | Hiện trạng |
|---|---|
| `docker-compose.yml:28` | Service `minio` (dev); `backend` phụ thuộc ở dòng 100 |
| `docker-compose.lan.yml:34-47` | Service `minio`, healthcheck bằng `curl .../minio/health/live`; `MINIO_ROOT_USER/PASSWORD` lấy từ chính `MINIO_ACCESS_KEY/SECRET_KEY` |
| `docker-compose.lan.yml:102, 150, 182, 243` | `backend`, `celery_worker`, `celery_beat`, `backup_scheduler` đều `depends_on` `minio` |
| `docker-compose.prod.yml` | **Không có service `minio`**; `.env.example:68-74` yêu cầu trỏ endpoint object storage ngoài |
| `.github/workflows/ci.yml:45-58` | Service `minio/minio:latest` kèm khóa `command: server /data` (xem U12) |
| `.github/workflows/ci.yml:81, 93, 105` | `MINIO_ENDPOINT: localhost:9000` |
| `.github/workflows/ci.yml:164` | Bước build image backup (hiện hỏng, xem mục 2) |

### 3.4. Cấu hình sao lưu **nằm trong DB**, không chỉ trong `.env`

Bản sao DB production (nạp 2026-10-30), bảng `backup_configs`:

| `kind` | `source_endpoint` | `source_bucket` | `target_endpoint` | `target_bucket` | `target_prefix` |
|---|---|---|---|---|---|
| `db` | (null) | (null) | (null) | `hrms-backup` | `postgres` |
| `object_storage` | **`minio:9000`** | `hrms-attachments-dev` | (null) | `hrms-backup` | `files` |

`source_endpoint = minio:9000` được lưu cứng ở dòng `object_storage`. **Chỉ đổi `.env` khi cutover thì sao lưu kho tệp vẫn trỏ vào MinIO cũ.** Dòng này chỉ được tạo từ `.env` một lần lúc chưa tồn tại (`ensure_backup_configs`), nên không tự cập nhật.

`backup_jobs.artifact_bucket/artifact_key` tham chiếu object theo tên: **tên object phải giữ nguyên** khi chép sang Garage.

### 3.5. Kịch bản và tài liệu còn dùng `mc`

`scripts/backup_minio.sh`, `scripts/backup-entrypoint.sh`, `scripts/backup_db.sh:80-81`, `scripts/restore_procedure.md`, `docker/backup/Dockerfile:37`. Đây là cơ chế cũ (`backup_scheduler`, profile `backup`, mặc định tắt); cơ chế đang dùng là Backup Console (Celery + SDK Python) và **không dùng `mc`**.

### 3.6. Test

- `backend/tests/test_auth.py:373-375`, `backend/tests/test_security.py:247-262`: kiểm tra bộ validator `MINIO_*` (không cần MinIO thật).
- `frontend/tests/e2e/backup-center.spec.ts` (dòng 220, 243-267, 387-411): fixture chứa `minio:9000` và nhãn `"Kho tệp ứng dụng trên MinIO"`.
- Khi test backend chạy với `TestClient`, `lifespan` gọi `ensure_bucket()` nên CI **cần một S3 thật** ở `MINIO_ENDPOINT`.

## 4. Phạm vi

### 4.1. Trong phạm vi

- Dựng Garage một node cho dev, LAN, và (nếu cần) compose HTTPS.
- Chuyển dữ liệu từ MinIO sang Garage, giữ nguyên tên object, có kiểm chứng.
- Chuẩn hóa chỗ khởi tạo client S3 và nhãn giao diện.
- Cập nhật CI, tài liệu vận hành, và loại bỏ phụ thuộc `mc`.
- Runbook cutover production, diễn tập và quay lui.

### 4.2. Ngoài phạm vi

- Cụm Garage nhiều node, nhân bản dữ liệu.
- Thay đổi định dạng tên object hoặc logic nghiệp vụ.
- Mở Garage ra ngoài mạng nội bộ; TLS cho S3 API (Garage không hỗ trợ TLS trực tiếp, cần reverse proxy nếu muốn).
- Đổi tên biến `MINIO_*` (làm ở Slice 10, tùy chọn).
- Đích sao lưu ngoài máy (offsite): chỉ nêu rủi ro và câu hỏi cần chốt (mục 12).

## 5. Quyết định thiết kế đề xuất

### 5.1. Các phương án đã xét

| Phương án | Kết luận | Lý do |
|---|---|---|
| **Garage** | **Chọn** | Trang tương thích chính thức liệt kê đủ 7 thao tác cần dùng. Bản `v2.5.0` (24/10/2026), Docker Hub cập nhật 30/10/2026. Nhẹ, thiết kế cho tự lưu trữ quy mô nhỏ. |
| PGSTY Silo (fork MinIO) | Dự phòng | Gần như thả vào thay thế, nhưng phụ thuộc cam kết của một công ty; chính trang của họ khuyên ghim phiên bản và giữ đường lui. Dùng nếu Slice 1 thất bại. |
| RustFS | Không chọn lúc này | README không khẳng định sẵn sàng production, nhiều tính năng ghi "Preview", chế độ một ổ đĩa không mở rộng được. (Tin đồn về chất lượng mã nguồn chưa được kiểm chứng và không dùng làm căn cứ.) |
| SeaweedFS, Ceph RGW | Không chọn | Quá lớn so với nhu cầu một node và dữ liệu nhỏ. |

Vì ứng dụng chỉ dùng S3 cơ bản, việc đổi sang kho khác về sau rẻ; quyết định này không khóa dự án.

### 5.2. Garage một node, cấu hình bền dữ liệu

Theo tài liệu cấu hình của Garage:

- `db_engine = "sqlite"`. `lmdb` (mặc định) dễ hỏng sau khi mất điện và không chuyển được giữa kiến trúc CPU; lợi thế của nó dựa vào việc có bản sao trên node khác. Một node duy nhất không có bản sao nên chọn `sqlite` (chậm hơn nhưng an toàn hơn). `sqlite` cũng không bị giới hạn độ dài khóa 511 byte của `lmdb`.
- `metadata_fsync = true`, `data_fsync = true`: giảm rủi ro hỏng dữ liệu khi mất điện, đổi lấy tốc độ ghi. Với quy mô tệp đính kèm hồ sơ, chi phí này chấp nhận được (đo ở Slice 1, xem U10).
- `metadata_auto_snapshot_interval = "6h"`: Garage chỉ giữ hai snapshot gần nhất (xem U11 về việc có áp dụng cho `sqlite` không).
- Bí mật (`rpc_secret`, `admin_token`) truyền bằng biến môi trường `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`, **không ghi vào file cấu hình trong repo**.

### 5.3. Mạng

- Garage chỉ nằm trong mạng nội bộ của compose, **không publish cổng ra host**. Endpoint cho ứng dụng: `garage:3900`.
- `MINIO_SECURE=false` (S3 API của Garage không có TLS; lưu lượng chỉ đi trong mạng Docker nội bộ).

### 5.4. Bucket, khóa và quyền

Garage dùng mô hình quyền riêng (khóa x bucket), không có ACL/policy của S3.

| Khóa | Bucket | Quyền | Dùng cho |
|---|---|---|---|
| `hrms-app` | `hrms-attachments-<env>` (production: **`hrms-attachments-prod`**, xem 12.3) | đọc, ghi, owner | `MINIO_*` và `SOURCE_STORAGE_*` (tệp đính kèm, nguồn sao lưu kho tệp) |
| `hrms-backup` | `hrms-backup` | đọc, ghi, owner, **tạo bucket** (xem U4) | `BACKUP_STORAGE_*` (đích sao lưu, khôi phục sang đích mới) |

Định dạng khóa của Garage: access key `GK` + 24 ký tự hex, secret 64 ký tự hex. Khóa **tự sinh bằng `garage key create`**; lệnh `import` chỉ dành cho di trú/khôi phục theo tài liệu Garage, không dùng để đặt khóa tùy ý.

Bucket được tạo bằng script bootstrap **trước khi** `backend` khởi động, vì `ensure_bucket()` (`main.py:81`) làm backend lỗi nếu bucket chưa có và khóa không có quyền tạo.

### 5.5. Giữ tên biến `MINIO_*` trong đợt này

Đổi tên biến chạm `config.py`, 3 file compose, CI, `.env` production và nhiều tài liệu; để riêng ở Slice 10. Đợt này chỉ đổi **giá trị**: `MINIO_ENDPOINT=garage:3900`, khóa mới.

### 5.6. Bootstrap bằng script, không bằng container khởi tạo

Image Garage dựng `FROM scratch`, **không có shell** (tài liệu chính thức), nên không chạy được script bên trong container. Dùng `scripts/garage_bootstrap.sh` chạy từ máy host qua `docker compose exec -T garage /garage ...`, **idempotent** (chạy lại không lỗi), in khóa ra terminal đúng một lần và không ghi ra file.

### 5.7. Chuẩn hóa client S3

Tạo một hàm duy nhất `build_s3_client(endpoint, access_key, secret_key, secure, region=None)` (ví dụ ở `backend/app/core/s3_client.py`) và thay 4 chỗ `Minio(...)` ở mục 3.2. Tham số `region` mặc định rỗng; chỉ bật nếu Slice 1 cho thấy việc tự dò region qua `GetBucketLocation` không hoạt động với `s3_region = "garage"` (U5).

### 5.8. Healthcheck

Image không có `curl`/`wget`/shell. Đề xuất `["CMD", "/garage", "status"]` (U2 phải kiểm chứng). Giữ được `depends_on: condition: service_healthy` cho `backend` và `celery_*` như hiện nay với MinIO.

### 5.9. Dừng dùng `mc`

Bỏ `backup_scheduler` và image sao lưu cũ (quyết định D3). Thủ tục khôi phục và tải artifact viết lại bằng SDK Python trong image backend (cách đã dùng thành công để tải file dump production).

### 5.10. Chuỗi cung ứng image

Mirror `dxflrs/garage:v2.5.0` lên `ghcr.io/nguyencuonghut/hrms/` và ghim theo **digest**, vì bài học MinIO: một image công khai có thể biến mất. Không dùng tag `latest`.

## 6. Bản đồ luồng dữ liệu

### 6.1. Các luồng và thay đổi

| # | Luồng | Đường đi | Thay đổi |
|---|---|---|---|
| F1 | Tải lên tệp đính kèm | Trình duyệt, nginx, `backend` (đọc vào RAM, kiểm tra loại/kích thước), `put_object`, ghi `object_name` vào DB | Chỉ đổi endpoint/khóa |
| F2 | Tải xuống | Trình duyệt, `backend`, `get_object` (stream), trả `StreamingResponse` | Như trên |
| F3 | Xóa | `backend`, `remove_object` (nuốt `S3Error`) | Như trên |
| F4 | Khởi động | `lifespan`, `ensure_bucket()` (`bucket_exists`, `make_bucket`) | **Cần bucket + quyền có sẵn** (bootstrap trước) |
| F5 | Health | `/health`, `bucket_exists(bucket)` | Giữ khóa `checks["minio"]` (có thể thêm `checks["storage"]`, Slice 3) |
| F6 | Sao lưu DB | `celery_worker`, `pg_dump` rồi nén gzip, `put_object` vào `BACKUP_STORAGE_*` | Đổi endpoint/khóa sao lưu |
| F7 | Sao lưu kho tệp | `celery_worker`, `list_objects` + `get_object` từ **nguồn** (`backup_configs.source_*` hoặc `SOURCE_STORAGE_*`/`MINIO_*`), `put_object` sang **đích** (`files/files-<ts>/`) kèm manifest | **Phải sửa `backup_configs.source_endpoint` trong DB** |
| F8 | Khôi phục | `restore_runner`, `get_object` từ bucket sao lưu, ghi sang đích (`make_bucket` nếu đích mới) | Khóa `hrms-backup` cần quyền tạo bucket |
| F9 | Kiểm tra đích | Nút dấu tích trong Backup Console, `bucket_exists` | Kết quả cũ lưu trong DB, **phải bấm kiểm tra lại sau cutover** |
| F10 | CI | `pytest`, `TestClient`, `lifespan`, `ensure_bucket()` | Cần Garage thật trong job |

### 6.2. Sơ đồ trước và sau

```
TRƯỚC                                         SAU
backend / celery  --MINIO_ENDPOINT-->  minio:9000        backend / celery  --MINIO_ENDPOINT-->  garage:3900
celery (F7 nguồn) --backup_configs.source_endpoint-->    celery (F7 nguồn) --backup_configs.source_endpoint-->
                                       minio:9000                                                garage:3900
celery (F6/F7 đích) --BACKUP_STORAGE_*-> minio:9000      celery (F6/F7 đích) --BACKUP_STORAGE_*-> garage:3900
volume minio_data (định dạng MinIO)                      volumes garage_meta + garage_data (định dạng Garage)
```

Hai định dạng lưu trữ **không tương thích**, nên dữ liệu được chuyển bằng sao chép đối tượng qua S3 (Slice 4), không phải sao chép volume.

## 7. Ánh xạ cấu hình

### 7.1. Biến môi trường (`.env`, compose, CI)

| Biến | Hiện tại (LAN) | Sau cutover |
|---|---|---|
| `MINIO_ENDPOINT` | `minio:9000` | `garage:3900` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | tài khoản gốc MinIO (cũng là `MINIO_ROOT_*`) | khóa `hrms-app` của Garage |
| `MINIO_SECURE` | `false` | `false` |
| `MINIO_BUCKET` | (trống, tự suy ra `hrms-attachments-dev`) | **`hrms-attachments-prod`**, đặt tường minh (quyết định 12.3) |
| `BACKUP_STORAGE_ENDPOINT` | `minio:9000` | `garage:3900` |
| `BACKUP_STORAGE_ACCESS_KEY` / `_SECRET_KEY` | tài khoản gốc MinIO | khóa `hrms-backup` |
| `BACKUP_STORAGE_SECURE` | `false` | `false` |
| `BACKUP_STORAGE_BUCKET` | `hrms-backup` | giữ nguyên |
| `SOURCE_STORAGE_*` | trống (rơi về `MINIO_*`, `docker-compose.lan.yml:82-85`) | trống (rơi về `MINIO_*`) |
| (mới) `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN` | không có | sinh ngẫu nhiên, lưu trong `.env` quyền `600` |
| (mới) `GARAGE_IMAGE` / `GARAGE_TAG` | không có | ghim theo digest của bản mirror |

### 7.2. Form "Sửa cấu hình sao lưu" (Backup Console)

Dòng **Kho tệp ứng dụng** (`object_storage`), các trường và giá trị cần có sau cutover:

| Trường trên form | Hiện tại | Sau cutover | Cách đổi |
|---|---|---|---|
| Địa chỉ kết nối nguồn | `minio:9000` | `garage:3900` | Sửa trong form hoặc SQL (mục 10) |
| Kho lưu trữ nguồn | `hrms-attachments-dev` | `hrms-attachments-prod` | Sửa trong form hoặc SQL (mục 10) |
| Kết nối bảo mật nguồn | tắt | tắt | |
| Địa chỉ kết nối đích | (trống, dùng `.env`) | (trống, dùng `.env`) | |
| Kho lưu trữ đích / Thư mục đích | `hrms-backup` / `files` | giữ nguyên | |
| Kết nối bảo mật đích | tắt | tắt | |

Dòng **PostgreSQL** (`db`): chỉ phụ thuộc `.env`, không có endpoint lưu cứng.

Nhãn hiển thị `"Kho tệp ứng dụng trên MinIO"` đổi thành `"Kho tệp ứng dụng"` (Slice 3).

## 8. Hành trình người dùng và vận hành

### 8.1. Nhân sự (người dùng cuối): không thay đổi nhìn thấy

1. Mở hồ sơ nhân viên, tab tệp đính kèm hoặc hợp đồng.
2. Tải lên một PDF; danh sách hiện tệp mới.
3. Bấm tải xuống; nhận đúng tệp (so `sha256`).
4. Xóa; tệp biến mất khỏi danh sách.

Kiểm chứng ở mức trình duyệt (Slice 2, 7, 8), đọc DOM và request mạng. Nếu hạ tầng e2e hiện chỉ giả lập API, dùng kiểm tra thủ công bằng trình duyệt thật và ghi lại kết quả; **không viết test giả**.

### 8.2. Quản trị viên: Backup Console

1. Mở màn hình Sao lưu; dòng "Kho tệp ứng dụng" hiện đúng nhãn mới.
2. Bấm bút chì: form hiện nguồn `garage:3900`, bucket `hrms-attachments-dev`, các công tắc bảo mật tắt.
3. Lưu, rồi bấm nút dấu tích "Kiểm tra đích sao lưu": trạng thái **Thành công** với thời gian mới.
4. Bấm ▶ trên cả hai dòng: job `success`, hiện `artifact_bucket = hrms-backup` và khóa `postgres/...`, `files/...`.

### 8.3. Vận hành: cutover (tóm tắt, chi tiết ở mục 10)

Sao lưu trước, dựng Garage, chép dữ liệu lần 1 khi hệ thống còn chạy, dừng ứng dụng, chép bù lần cuối và đối chiếu, đổi cấu hình (`.env` và DB), khởi động, kiểm chứng, giữ MinIO cũ ở trạng thái dừng để quay lui.

## 9. Kế hoạch triển khai theo slice

Mỗi slice có cổng kiểm chứng riêng. Quy tắc chung (theo `AGENTS.md`): kết luận phải có bằng chứng; thay đổi ảnh hưởng giao diện phải kiểm bằng trình duyệt; báo cáo cuối slice nêu rõ **đã kiểm chứng gì và chưa kiểm chứng gì**. **Không chạy `pytest` trên DB `hrms` đang là bản sao production**: chạy trên bản clone (`CREATE DATABASE x TEMPLATE hrms`) rồi xóa, vì `test_administrative_import.py` xóa danh mục hành chính thật.

### Slice 0 - Kiểm kê và bảo toàn (không đổi code)

**Việc làm**
- Ghi lại định danh image MinIO production đang chạy: `docker inspect <container_minio> --format '{{.Image}} {{.Config.Image}}'`, `docker image inspect minio/minio:latest --format '{{.Id}} {{json .RepoDigests}} {{.Created}}'`, và loại kho ảnh `docker info --format '{{json .DriverStatus}}'` (kho `containerd` cho `Id` trùng digest của manifest; kho `overlay2` thì `Id` là digest của cấu hình, khác nhau).
- Chứng minh tệp lưu image dùng được: `sha256sum` và `gzip -t` trên `~/minio-image-20261030.tar.gz` ở production. Chỉ chứng minh được việc khôi phục vào kho ảnh **trống** khi tải sang một máy khác (xem "Kết quả diễn tập").
- Kiểm kê dữ liệu MinIO production bằng script chỉ đọc ở Phụ lục D: số object, dung lượng, số object trên 5 MiB, số tên chứa ký tự không phải ASCII, từng bucket.
- Snapshot volume MinIO thành tệp nén. **Nơi cất là chính máy production** (quyết định ngày 2026-10-30, mục 12.3): thư mục riêng ngoài repo, quyền `600`. Dùng lệnh đã chạy được ở mục "Gói lệnh production".
- Lưu kết quả `select kind, source_endpoint, source_bucket, target_endpoint, target_bucket, target_prefix from backup_configs` vào biên bản.
- Mirror `dxflrs/garage:v2.5.0` lên `ghcr.io/nguyencuonghut/hrms/garage` bằng cách **sao chép nguyên manifest** (ví dụ `docker buildx imagetools create` hoặc `crane copy`) để digest không đổi, rồi ghi digest.
- Chốt các quyết định D1-D6 theo mục 12.3.

**Kết quả diễn tập phía dev (2026-10-30, do agent thực hiện, đã được đối chiếu lại)**
- Image MinIO dev: `Id` `sha256:14cea493d9a3...`, `minio --version` = `RELEASE.2025-09-07T16-13-09Z`, kho ảnh `containerd`.
- `docker save | gzip` rồi `docker load` trên máy dev: tải lại được, `Id` trùng bản gốc, chạy `minio --version` cho cùng kết quả; các blob trong tệp tar đều khớp `sha256` của tên tệp. **Giới hạn:** vì phải giữ tag gốc nên kho ảnh vẫn còn các lớp, chưa chứng minh được việc khôi phục vào kho trống.
- Script kiểm kê (Phụ lục D) chạy được: dev có 2 bucket, 42 object, 6,65 MiB (`hrms-attachments-dev`: 26 object, 36.939 byte; `hrms-backup`: 16 object, 6.934.231 byte). Chạy lại độc lập cho cùng số liệu. Dữ liệu dev không có object trên 5 MiB hay tên có dấu, nên hai bộ đếm đó mới chỉ được kiểm bằng SDK giả.
- Snapshot volume dev: nén được 6.624.666 byte, `gzip -t` OK; giải nén vào volume tạm cho cùng số tệp và cùng tổng byte; khởi động MinIO trên volume khôi phục thấy đúng 42 object. **Hai phát hiện:** (1) lệnh `tar` đơn thuần tạo tệp `root:root` quyền `644`, người vận hành thường không `chmod 600` được, phải đặt `umask` và `chown` bên trong container; (2) snapshot của volume MinIO **đang chạy** chỉ nhất quán ở mức crash-consistent, và số mục thô của volume đang chạy có thể trôi trong vài phút (do thư mục tạm của MinIO), nên cần so sánh bằng script kiểm kê qua API, và chụp thêm một snapshot sau khi đã dừng ứng dụng (mục 10.2).
- Image Garage `v2.5.0` (truy vấn registry, không kéo, không chạy): manifest list `sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5`; `linux/amd64` `sha256:23b16d34e034...`, `linux/arm64` `sha256:32b5de84cf9e...`. Cấu hình image: `Cmd ["/garage","server"]`, không có `Entrypoint`, **không có `User` (chạy bằng root)**. **Không có nhãn OCI nào** và không có attestation, nên nguồn gốc phải do người vận hành ghi lại (digest cộng ngày tạo `2026-10-24T15:26:38Z`). Tag `v2.5.0` có thể bị đổi, vì vậy ghim theo digest. Chế độ `--dry-run` của `docker buildx imagetools create` cho thấy việc sao chép sang ghcr sẽ đẩy manifest giống hệt từng byte (digest giữ nguyên); chưa đẩy thật.

**Kết quả kiểm kê production (2026-10-30, chi tiết trong `plan_15.7_slice0_bien_ban.md`)**
- Image MinIO production có `Id` trùng hoàn toàn với image trên dev (`sha256:14cea493…`, `RELEASE.2025-09-07T16-13-09Z`); kho ảnh `containerd`.
- **Kho tệp ứng dụng production trống: `hrms-attachments-dev` có 0 object.** `hrms-backup` có 3 object, 1,18 MiB (hai bản sao lưu DB và một `manifest.json`). Dữ liệu thật cần chuyển chỉ còn 3 object.
- Dòng `object_storage` trong `backup_configs` trên production đúng như giả định ở mục 3.4 (`source_endpoint = minio:9000`, `source_bucket = hrms-attachments-dev`).
- **Hệ quả:** rủi ro mất dữ liệu khi chép thấp; việc đổi tên bucket không tốn gì về dữ liệu. Nhưng production không thể hiện các trường hợp biên (object lớn, tên có dấu, nhiều object), nên Slice 1 và Slice 4 là nơi duy nhất kiểm các trường hợp đó. **Kiểm kê lại ngay trước cutover.**

**Gói lệnh production (đã chạy được trên dev, cần chạy lại trên production)**

```bash
# 1) Tên volume và image thật đang dùng
docker volume ls | grep minio_data
docker inspect <container_minio> --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{"\n"}}{{end}}'

# 2) Snapshot volume (quyền 600, chủ là người chạy lệnh; MinIO vẫn chạy, mount chỉ đọc)
mkdir -p ~/minio-snapshots && chmod 700 ~/minio-snapshots
docker run --rm -e UIDGID="$(id -u):$(id -g)" -v <tên_volume>:/d:ro -v ~/minio-snapshots:/out alpine@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a \
  sh -c 'umask 077 && tar czf /out/minio_data_$(date +%F).tgz -C /d . && chown "$UIDGID" /out/minio_data_*.tgz'
f=$(ls -1t ~/minio-snapshots/minio_data_*.tgz | head -1)
stat -c '%a %U %s' "$f"; gzip -t "$f" && echo "gzip OK"; sha256sum "$f"; tar -tzf "$f" | wc -l

# 3) Kiểm kê qua API (script ở Phụ lục D), chạy trong image backend đang có sẵn
docker compose -f docker-compose.lan.yml run --rm --no-deps -T backend python - <<'PY'
...  # nội dung Phụ lục D
PY
```

**Kiểm chứng**: biên bản có số liệu thực của production (image, kiểm kê, cấu hình sao lưu); snapshot có quyền `600`, `gzip -t` OK, `tar -tzf` đọc được; số object trong snapshot khớp số object từ API; digest Garage đã ghi; `docker pull` từ ghcr theo digest thành công.

**Rollback**: không cần.

### Slice 1 - Spike tương thích (cổng quyết định go/no-go)

**Việc làm**
- Đưa bộ kiểm tra vào repo: `backend/app/scripts/s3_conformance_probe.py` (dùng chính SDK của ứng dụng; kiểm 7 thao tác, multipart 12 MiB, phân trang trên 1.000 object, tên có dấu tiếng Việt/khoảng trắng/`#`/`()`, ghi đè, mã lỗi).
- Chạy với Garage `v2.5.0` trong mạng Docker riêng, cấu hình đề xuất ở Phụ lục A.
- Trả lời toàn bộ mục "Điểm chưa xác minh" U1-U15 (mục 12) bằng bằng chứng; ghi kết quả vào mục "Kết quả Slice 1" của tài liệu này.

**Kiểm chứng (cổng)**: mọi bài kiểm tra PASS, hoặc mọi FAIL đều khắc phục được bằng cấu hình/tham số SDK. Nếu không: dừng và đánh giá phương án dự phòng (Silo) trước khi sang slice sau.

**Lưu ý**: bước này chạy image bên thứ ba và cần phê duyệt của người vận hành.

**Rollback**: xóa container/volume thử nghiệm.

### Slice 2 - Garage trong môi trường dev

**Việc làm**
- `docker/garage/garage.toml` (Phụ lục A) và service `garage` trong `docker-compose.yml`; `backend`/`celery_*` đổi `depends_on` từ `minio` sang `garage`.
- Giữ service `minio` dưới profile `legacy-minio` để diễn tập chép dữ liệu (Slice 4, 7).
- `scripts/garage_bootstrap.sh` (Phụ lục B), `.env.example` có mục Garage.
- Healthcheck theo mục 5.8.

**Kiểm chứng (cổng)**
1. `docker compose up -d`: `garage` healthy; chạy bootstrap **hai lần** không lỗi.
2. `backend` khởi động; `GET /health` có `checks.minio = ok`.
3. **Trình duyệt thật**: luồng 8.1 (tải lên, tải xuống đúng nội dung, xóa).
4. **Trình duyệt thật**: luồng 8.2 (kiểm tra đích Thành công; ▶ sao lưu DB và kho tệp thành công; dùng script SDK xác nhận artifact tồn tại trong Garage).
5. Khởi động lại container Garage: dữ liệu vẫn còn.

**Rollback**: `git checkout` các file compose/`.env.example`; dùng lại profile `legacy-minio`.

### Slice 3 - Chuẩn hóa client S3, nhãn UI và test

**Việc làm (TDD)**
- Viết test cho `build_s3_client` trước (truyền `secure`, `region`, chuẩn hóa endpoint), rồi cài đặt; thay 4 chỗ `Minio(...)`.
- Nếu Slice 1 cần: thêm biến `MINIO_REGION` (mặc định rỗng), truyền vào factory.
- Đổi nhãn `"Kho tệp ứng dụng trên MinIO"` thành **`"Kho tệp ứng dụng"`** (thuật ngữ đã chốt trong `CONTEXT.md`, không nêu tên công nghệ): `backup_service.py:42`, `BackupCenterView.vue:6, 827, 1061, 1066` (dòng 6 và 1066 còn câu chữ "trên MinIO"/"kết nối MinIO" cần viết lại không nêu công nghệ), và các fixture/assert tương ứng trong `backup-center.spec.ts`.
- Health: giữ `checks["minio"]` để không phá giám sát; thêm `checks["storage"]` cùng giá trị.

**Kiểm chứng (cổng)**
- `pytest` đầy đủ trên **bản clone DB**, với Garage thật.
- `npm run build` và `vue-tsc`; chạy `backup-center.spec.ts`.
- Trình duyệt thật: nhãn mới hiển thị ở danh sách, form và dropdown.
- Backend + UI là thay đổi full-stack: nêu rõ cả hai mức đã kiểm.

**Rollback**: revert commit; không đổi dữ liệu.

### Slice 4 - Công cụ chuyển dữ liệu

**Việc làm (TDD)**: `backend/app/scripts/s3_migrate.py` (chạy bằng `python -m app.scripts.s3_migrate`, có trong image backend).
- Tham số: endpoint và bucket nguồn/đích **tách riêng** (`--src-bucket`, `--dst-bucket`, vì production đổi tên bucket khi cutover), `--prefix`, `--dry-run`, `--verify`. **Khóa truy cập đọc từ biến môi trường, không đưa lên dòng lệnh.**
- Thuật toán: liệt kê nguồn; với mỗi object, bỏ qua nếu đích đã có cùng kích thước; nếu không thì đọc streaming từ nguồn, ghi sang đích với cùng tên và `content_type`; sau đó (nếu `--verify`) đọc lại hai phía, so kích thước và `sha256`.
- Idempotent, **không bao giờ xóa**, in báo cáo (số đã chép/bỏ qua/lỗi), thoát khác 0 nếu có sai lệch.

**Kiểm chứng (cổng)**
- Test đơn vị với client giả (đủ nhánh: bỏ qua, chép, lệch hash, lỗi giữa chừng).
- Tích hợp thật trên dev: MinIO (profile legacy) sang Garage cho cả hai bucket; số object, kích thước và `sha256` trùng khớp.
- Chạy lần hai: 0 object phải chép.
- Có ít nhất một object lớn hơn 5 MiB và một tên có dấu tiếng Việt trong bộ dữ liệu thử.

**Rollback**: xóa bucket đích rồi chạy lại (nguồn không bị thay đổi).

### Slice 5 - CI và chuỗi cung ứng image

**Việc làm**
- Thay service `minio` (`ci.yml:45-58`) bằng bước khởi động Garage bằng `docker run` từ image mirror (khóa `command` trong `services` có thể không có tác dụng, xem U12), kèm bước chờ sẵn sàng và bootstrap. Có thể dùng chế độ `--single-node --default-bucket` với `GARAGE_DEFAULT_*` cho CI nếu Slice 1 xác nhận.
- Đổi `MINIO_ENDPOINT` (`ci.yml:81, 93, 105`) và thêm khóa tương ứng.
- Xử lý bước build image backup (`ci.yml:164`) theo D3.

**Kiểm chứng (cổng)**: chạy workflow trên một nhánh (cần GitHub Actions): `test-backend` xanh; `build-and-push` xanh. Máy dev hiện không có `gh`, nên bước này cần người vận hành xác nhận kết quả.

**Rollback**: revert workflow.

### Slice 6 - Gỡ phụ thuộc `mc` và cập nhật tài liệu

**Việc làm (theo D3, khuyến nghị gỡ)**
- Gỡ `backup_scheduler` khỏi 3 file compose; xóa `docker/backup/Dockerfile`, `scripts/backup_minio.sh`, `scripts/backup-entrypoint.sh`, `scripts/backup_db.sh`.
- Viết lại `scripts/restore_procedure.md` bằng SDK Python (và `s3_migrate`).
- Cập nhật tài liệu vận hành: `docs/deploy_noi_bo_lan_ubuntu_26_04.md`, `docs/production_deploy_ubuntu_26_04.md`, `docs/production_go_live_runbook.md`, `docs/TECHSTACK.md`, `docs/FEATURES.md`, `README.md`, `.env.example`.
- Với các `plan_*.md` lịch sử: thêm một dòng ghi chú trỏ sang tài liệu này, không viết lại nội dung.

**Kiểm chứng (cổng)**
- `grep` không còn `mc `, `dl.min.io`, `minio/mc` ngoài tài liệu lịch sử.
- `docker compose -f <từng file> config` hợp lệ.
- **Làm theo đúng `restore_procedure.md` mới từ đầu đến cuối** trên dev (khôi phục dump DB từ Garage và tải tệp): chứng minh tài liệu chạy được.

**Rollback**: revert commit.

### Slice 7 - Diễn tập cutover trên dev với bản sao production

**Việc làm**: dựng lại hiện trạng "MinIO + dữ liệu" (profile `legacy-minio`), DB là bản sao production; chạy **đúng runbook mục 10, bằng đúng lệnh** sẽ dùng ở production; đo thời gian từng bước; diễn tập quay lui.

**Kiểm chứng (cổng)**: checklist sau cutover (mục 10.4) toàn PASS; sau quay lui, hệ thống về đúng trạng thái cũ, xác nhận bằng giao diện; thời gian gián đoạn thực đo được ghi lại để chốt cửa sổ bảo trì (D1).

**Rollback**: bỏ container/volume của buổi diễn tập.

### Slice 8 - Cutover production

**Điều kiện tiên quyết**: Slice 0-7 đạt cổng; bản sao lưu DB tạo **trong vòng 1 giờ** trước khi bắt đầu; snapshot volume MinIO mới; đã chốt cửa sổ bảo trì. Theo quyết định ngày 2026-10-30 (mục 12.3), **không bắt buộc** có bản sao lưu ngoài máy production.

**Việc làm**: thực hiện runbook mục 10.

**Kiểm chứng (cổng)**: checklist 10.4 PASS; theo dõi 24 giờ đầu (đăng nhập, tải tệp, lần sao lưu theo lịch 02:00 kế tiếp thành công cho cả `db` và `object_storage`).

**Rollback**: quy trình 10.5.

### Slice 9 - Hậu kiểm và dọn dẹp (7 ngày sau cutover, theo D4)

**Việc làm**
- Xác nhận sao lưu theo lịch chạy thành công nhiều ngày liền; chạy thử một lần khôi phục thật sang đích mới (kiểm tra quyền tạo bucket, U4).
- Gỡ service, volume và image MinIO khỏi compose và khỏi máy chủ (sau khi lưu bản nén cuối cùng theo D4).
- Cập nhật tài liệu thành trạng thái cuối; chốt giải pháp đích sao lưu ngoài máy (D2).
- Thêm giám sát cơ bản: dung lượng đĩa của `garage_data`, `garage status`.

**Kiểm chứng**: `docker ps -a` và `docker volume ls` không còn tài nguyên MinIO; một lần khôi phục thử thành công.

### Slice 10 (tùy chọn) - Đổi tên biến `MINIO_*` thành `S3_*`

Làm riêng sau khi hệ thống ổn định: thêm biến mới với dự phòng đọc biến cũ, đổi dần compose/CI/tài liệu, rồi gỡ biến cũ ở một đợt sau. Không thuộc phạm vi cutover.

## 10. Runbook cutover production (phác thảo, chưa chạy)

Chạy trong `/opt/hrms/HRMS` với `docker-compose.lan.yml`. **Mọi lệnh phải được kiểm chứng ở Slice 7 trước khi dùng thật.**

### 10.1. Chuẩn bị (trước cửa sổ bảo trì, hệ thống còn chạy)

1. `git pull origin master` (nhớ: nhánh là `master`, không phải `main`).
2. Đảm bảo `.env` có `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN` (sinh bằng `openssl rand -hex 32`), `GARAGE_IMAGE`/`GARAGE_TAG` ghim theo digest; `chmod 600 .env`.
3. Backup Console: ▶ sao lưu PostgreSQL và xác nhận `success` (truy vấn `backup_jobs`).
4. Snapshot volume MinIO:
   ```bash
   docker volume ls | grep minio_data      # xác nhận tên volume, ví dụ hrms_minio_data
   docker run --rm -e UIDGID="$(id -u):$(id -g)" -v <tên_volume>:/d:ro -v "$PWD":/out alpine@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a \
     sh -c 'umask 077 && tar czf /out/minio_data_$(date +%F).tgz -C /d . && chown "$UIDGID" /out/minio_data_*.tgz'
   ```
5. Bật Garage song song với MinIO: `docker compose -f docker-compose.lan.yml up -d garage`, rồi `scripts/garage_bootstrap.sh`. Ghi hai cặp khóa vào nơi tạm an toàn (chưa đưa vào `.env`).
6. **Chép dữ liệu lần 1 khi hệ thống còn chạy** (khóa nguồn/đích truyền bằng biến môi trường cho lệnh). Kiểm kê ngày 2026-10-30: bucket tệp có 0 object và `hrms-backup` có 3 object; bước chép bucket tệp có thể không chép gì, vẫn chạy để xác nhận. **Chạy lại kiểm kê (Phụ lục D) ngay trước khi bắt đầu**, vì người dùng có thể đã tải tệp lên:
   ```bash
   docker compose -f docker-compose.lan.yml run --rm --no-deps \
     -e SRC_ENDPOINT=minio:9000 -e DST_ENDPOINT=garage:3900 ... \
     backend python -m app.scripts.s3_migrate --src-bucket hrms-attachments-dev --dst-bucket hrms-attachments-prod --verify
   docker compose -f docker-compose.lan.yml run --rm --no-deps ... \
     backend python -m app.scripts.s3_migrate --src-bucket hrms-backup --dst-bucket hrms-backup --verify
   ```

### 10.2. Cắt chuyển (trong cửa sổ bảo trì)

1. Dừng ứng dụng: `docker compose -f docker-compose.lan.yml stop backend celery_worker celery_beat`. Sau đó chụp **snapshot volume MinIO lần cuối** bằng lệnh ở 10.1 bước 4 (tên tệp khác): lúc này MinIO không còn ghi nên snapshot nhất quán.
2. **Chép bù lần cuối** cả hai bucket (như 10.1 bước 6); báo cáo phải là 0 lỗi, số object/kích thước/hash trùng.
3. Sửa `.env`: `MINIO_ENDPOINT`, `MINIO_BUCKET=hrms-attachments-prod`, `MINIO_ACCESS_KEY/SECRET_KEY` (khóa `hrms-app`), `BACKUP_STORAGE_ENDPOINT`, `BACKUP_STORAGE_ACCESS_KEY/SECRET_KEY` (khóa `hrms-backup`) theo bảng 7.1. Sao lưu `.env` cũ ra ngoài thư mục repo với quyền `600`.
4. Sửa cấu hình sao lưu **trong DB** (hoặc bằng form ở mục 7.2):
   ```sql
   update backup_configs
      set source_endpoint = 'garage:3900',
          source_bucket   = 'hrms-attachments-prod'
    where kind = 'object_storage'
      and source_endpoint = 'minio:9000'
      and source_bucket   = 'hrms-attachments-dev';
   select kind, source_endpoint, source_bucket, target_endpoint, target_bucket from backup_configs order by kind;
   ```
5. Khởi động lại: `docker compose -f docker-compose.lan.yml up -d --force-recreate --no-deps backend celery_worker celery_beat`.
6. Ngăn MinIO tự bật lại sau khởi động máy: `docker compose -f docker-compose.lan.yml stop minio` và `docker update --restart=no <container_minio>`; **chưa xóa** container và volume.

### 10.3. Kiểm chứng

Chạy checklist 10.4.

### 10.4. Checklist sau cutover

1. `docker compose ... ps`: `garage`, `backend`, `celery_*` healthy.
2. `GET /health`: `database`, `redis`, `minio` đều `ok`.
3. Trình duyệt thật: luồng 8.1; mở lại một tệp đính kèm **cũ** (đã có trước cutover) và so `sha256` với bản gốc.
4. Backup Console: nút "Kiểm tra đích sao lưu" Thành công cho cả hai dòng; ▶ sao lưu DB và kho tệp `success`; `backup_jobs` có `artifact_bucket = hrms-backup`.
5. `select` từ `backup_configs` đúng như 10.2 bước 4 (**cả `source_endpoint` lẫn `source_bucket`**); `GET /health` cũng kiểm tra bucket `hrms-attachments-prod`, nên `ok` là bằng chứng `MINIO_BUCKET` đã nạp đúng.
6. Log `backend` không có `S3Error`/`Traceback` bất thường trong 15 phút đầu.

### 10.5. Quay lui

Điều kiện kích hoạt: bất kỳ mục nào của 10.4 FAIL mà không sửa được trong thời hạn đã định trước.

1. Dừng `backend`, `celery_worker`, `celery_beat`.
2. **Nếu đã có ghi mới vào Garage** sau cutover: chép ngược các object mới từ Garage về MinIO bằng `s3_migrate` (hướng ngược); nếu không sẽ mất các tệp đó.
3. Trả `.env` về bản cũ (gồm bỏ `MINIO_BUCKET`); trả `backup_configs.source_endpoint` về `minio:9000` và `source_bucket` về `hrms-attachments-dev`.
4. `docker compose ... start minio`; khởi động lại ba dịch vụ; chạy lại 10.4 mục 1-4 với MinIO.

Việc quay lui chỉ dùng được khi container và volume MinIO còn nguyên, nên không xóa chúng trước Slice 9.

## 11. Rủi ro và đường lui

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | Garage không tương thích một hành vi ứng dụng cần | Cao | Slice 1 là cổng go/no-go; dự phòng Silo |
| R2 | Quên cập nhật `backup_configs.source_endpoint` trong DB | Cao | Bước SQL cụ thể trong 10.2; checklist 10.4 mục 5; nhãn lỗi rõ ở Backup Console |
| R3 | Backend không khởi động vì `ensure_bucket()` (bucket chưa có/thiếu quyền) | Cao | Bootstrap trước khi khởi động dịch vụ; kiểm trong diễn tập (Slice 7) |
| R4 | Hỏng/mất dữ liệu Garage khi mất điện | Trung bình | `sqlite` + `fsync` + snapshot; vẫn chỉ một node nên cần sao lưu ngoài máy (D2) |
| R5 | Sao lưu và dữ liệu thật nằm cùng một kho, cùng một ổ đĩa, và **hiện chưa có nơi nào ngoài máy production** (xác nhận 2026-10-30) | Cao | **Chủ hệ thống đã chấp nhận rủi ro khi cutover** (mục 12.3). Vẫn nên có ít nhất một bản ngoài máy (D2); không giải quyết trong đợt này |
| R6 | Mất dữ liệu khi chép | Thấp hiện tại (production có 0 tệp và 3 object sao lưu, kiểm kê 2026-10-30); có thể tăng nếu người dùng tải tệp lên trước cutover | `--verify` theo `sha256`, chép hai lần, không xóa nguồn, giữ snapshot và container MinIO cũ; kiểm kê lại ngay trước cutover |
| R7 | Image Garage biến mất khỏi registry công khai | Trung bình | Mirror lên ghcr, ghim digest (5.10) |
| R8 | Lộ khóa truy cập | Trung bình | Khóa chỉ in một lần ra terminal; `.env` quyền `600`; không đưa khóa lên dòng lệnh script |
| R9 | CI không khởi động được Garage | Trung bình | Dùng `docker run` trong bước riêng (U12); chạy thử trên nhánh trước khi gộp |
| R10 | Gián đoạn dịch vụ lâu hơn dự kiến | Trung bình | Chép lần 1 khi chạy; chỉ chép bù lần cuối trong cửa sổ; đo thời gian ở Slice 7 |
| R11 | AGPLv3 của Garage | Thấp | Dùng nội bộ, không sửa mã; (không phải tư vấn pháp lý, cần chốt nếu có phân phối lại) |
| R12 | Test hạ tầng làm hỏng DB bản sao production | Trung bình | Luôn chạy test trên bản clone DB (mục 9) |
| R13 | Đổi tên bucket cùng lúc cutover làm tăng số điểm phải đúng (`MINIO_BUCKET`, `backup_configs.source_bucket`, bucket mới trong Garage, quyền của khóa `hrms-app`) | Trung bình | Một SQL duy nhất cập nhật cả endpoint lẫn bucket; checklist 10.4 mục 5; diễn tập đúng tên bucket ở Slice 7. Manifest của các bản sao lưu cũ vẫn ghi `source_bucket = hrms-attachments-dev` nhưng khôi phục đọc từ bucket sao lưu, không dùng giá trị này (đã đọc `restore_runner_service.py:336-355`, chưa chạy thử; **kiểm chứng ở Slice 7 bằng một lần khôi phục thật**) |

## 12. Điểm chưa xác minh và quyết định cần chốt

### 12.1. Phải xác minh trong Slice 1 (chưa có bằng chứng)

| # | Nội dung |
|---|---|
| U1 | `garage server --single-node` có tự tạo layout mà không cần `--default-bucket`; dung lượng layout mặc định |
| U2 | Healthcheck `["CMD", "/garage", "status"]` chạy được trong image `FROM scratch` dưới compose |
| U3 | Lệnh `garage bucket info`, `garage key info` tồn tại và có mã thoát phân biệt "có/không" (để bootstrap idempotent) |
| U4 | `garage key allow --create-bucket` tồn tại và đủ để `make_bucket` qua S3 (`backup_runner_service.py:108`, `restore_runner_service.py:373`); tài liệu hướng dẫn nhanh không nói rõ |
| U5 | SDK `minio` tự dò region qua `GetBucketLocation` với `s3_region = "garage"`; nếu không thì cần tham số `region` |
| U6 | Liệt kê trên 1.000 object và tên có dấu tiếng Việt (tài liệu Garage ghi có trường hợp đặc biệt với `encoding-type=url`) |
| U7 | Multipart 12 MiB và `sha256` khớp |
| U8 | Bind `0.0.0.0` (phác thảo ở Phụ lục A) so với `[::]` trong mạng bridge của Docker |
| U9 | Quyền ghi lên volume. Cấu hình image cho thấy tiến trình chạy bằng root (không có `User`), nên nhiều khả năng không vướng; vẫn cần xác nhận khi chạy thật |
| U10 | Độ trễ khi bật `metadata_fsync` và `data_fsync` |
| U11 | `metadata_auto_snapshot_interval` có áp dụng cho `sqlite` |
| U12 | GitHub Actions có hỗ trợ khóa `command` trong `services` (`ci.yml` đang dùng nhưng tôi tin là không có tác dụng) |
| U13 | `depends_on: condition: service_healthy` hoạt động với healthcheck của Garage |
| U14 | Mã/ngữ nghĩa lỗi khi object hoặc bucket không tồn tại (ứng dụng chỉ bắt `S3Error` chung nên rủi ro thấp) |
| U15 | Mức dùng RAM và CPU khi rảnh và khi sao lưu |
| U16 | Gói mirror trên ghcr là **riêng tư** (xác nhận: không đăng nhập thì `401`) và do token cá nhân đẩy lên, image không có nhãn `org.opencontainers.image.source` nên có thể **chưa được liên kết với repo**. Kiểm tra `GITHUB_TOKEN` trong Actions có kéo được không; nếu không thì kết nối gói với repo (Manage Actions access). Production cần token chỉ đọc để kéo (Slice 5, 8) |

### 12.2. Quyết định cần chốt trước Slice 0

| # | Câu hỏi | Đề xuất |
|---|---|---|
| D1 | Cửa sổ bảo trì cho cutover (đo thực tế ở Slice 7) | Ngoài giờ làm việc; chốt sau Slice 7 |
| D2 | Đích sao lưu ngoài máy (offsite) | Cần quyết định riêng; ít nhất sao chép định kỳ bucket `hrms-backup` sang máy khác |
| D3 | Gỡ image/script sao lưu cũ dùng `mc` | **Gỡ** (Backup Console đã thay thế) |
| D4 | Thời gian giữ MinIO cũ ở trạng thái dừng sau cutover | 14 ngày |
| D5 | Đổi tên `MINIO_*` thành `S3_*` | Để sau, Slice 10 |
| D6 | `docker-compose.prod.yml` (HTTPS) hiện không có service MinIO, trỏ endpoint ngoài | Thêm service `garage` tương tự LAN nếu compose này còn được dùng |

### 12.3. Nhật ký quyết định

| Ngày | Quyết định | Hệ quả cho kế hoạch |
|---|---|---|
| 2026-10-30 | **Chưa có nơi nào ngoài máy production** để cất snapshot, image, hay bản sao lưu | Slice 0 lưu trên chính máy production (thư mục riêng ngoài repo, quyền `600`). Nơi lưu ngoài máy trở thành việc nên làm (D2), nhưng không chặn Slice 8 theo quyết định dưới đây |
| 2026-10-30 | **Cho phép cutover dù chưa có bản ngoài máy; chấp nhận rủi ro** (lý do: dữ liệu production hiện còn ít, 4 nhân viên) | R5 chuyển từ "cần giải quyết" sang "đã chấp nhận". Bắt buộc giữ nguyên MinIO cũ (container và volume) và snapshot trên cùng máy suốt thời gian D4, vì đó là lưới an toàn duy nhất |
| 2026-10-30 | **Đổi tên bucket tệp production thành `hrms-attachments-prod` ngay khi cutover** (tôi đề xuất giữ nguyên `hrms-attachments-dev`; chủ hệ thống chọn đổi) | Thêm `MINIO_BUCKET=hrms-attachments-prod` vào `.env` production; chép từ bucket `hrms-attachments-dev` (MinIO) sang `hrms-attachments-prod` (Garage), nên `s3_migrate` nhận `--src-bucket`/`--dst-bucket` riêng; cập nhật `backup_configs.source_bucket` trong cùng SQL với `source_endpoint`; thêm R13. Dev và CI giữ `hrms-attachments-dev` |
| 2026-10-30 | **D4: giữ MinIO cũ (container dừng + volume) 7 ngày** sau cutover rồi gỡ (tôi đề xuất 30 ngày; chủ hệ thống chọn 7) | Slice 9 diễn ra ở ngày thứ 7: cần đủ 7 lần sao lưu theo lịch 02:00 thành công và một lần khôi phục thử trong khoảng này. Sau ngày 7, việc quay về MinIO nghĩa là chép ngược các tệp mới. **Ghi chú của người lập kế hoạch, chưa chốt:** nên giữ riêng tệp snapshot nén trước cutover lâu hơn container (ví dụ tới 30 ngày) vì tốn rất ít chỗ và là bản dữ liệu tiền-cutover duy nhất |
| 2026-10-30 | **D3: gỡ hẳn** `backup_scheduler`, `docker/backup/Dockerfile`, `scripts/backup_*.sh`, `scripts/backup-entrypoint.sh` (bằng chứng: không chạy trên production, không build được vì `dl.min.io` trả 410, Backup Console đã thay thế) | Slice 6 thực hiện việc gỡ; viết lại `scripts/restore_procedure.md` bằng SDK Python |
| 2026-10-30 | **Cách chạy Slice 1: chủ hệ thống tự chạy script kiểm tra tương thích và gửi kết quả** (không đổi quyền; image Garage của bên thứ ba do người vận hành tự chạy) | Slice 1 gồm việc viết script vào repo và hướng dẫn từng lệnh; người lập kế hoạch chỉ phân tích kết quả được gửi lại, không tự chạy image Garage |
| 2026-10-30 | **Thuật ngữ và nhãn giao diện: "Kho tệp ứng dụng"**, gọi theo vai trò, không nêu tên công nghệ (đã loại "Kho tệp ứng dụng (S3)" và "... trên Garage"). Đã tạo `CONTEXT.md` ở thư mục gốc repo | Slice 3 đổi nhãn theo thuật ngữ này; các tài liệu mới dùng cùng thuật ngữ; lần đổi công nghệ sau không phải sửa giao diện, test và dữ liệu hiển thị |
| 2026-10-30 | *(Phát hiện, không phải quyết định)* **Kho tệp ứng dụng production trống (0 object)**; `hrms-backup` có 3 object (1,18 MiB) | Việc chuyển dữ liệu thực tế chỉ còn 3 object; đổi tên bucket không tốn về dữ liệu; Slice 1 và Slice 4 là nơi duy nhất kiểm các trường hợp biên; kiểm kê lại trước cutover |
| 2026-10-30 | **D5: để sau.** Cutover chỉ đổi giá trị biến `MINIO_*`, không đổi tên | Slice 10 vẫn là tùy chọn, làm riêng sau khi Garage ổn định |
| 2026-10-30 | **D6: thêm service `garage` vào `docker-compose.prod.yml`** theo cùng mẫu với file LAN (workflow deploy mặc định dùng file này; server thật chạy `docker-compose.lan.yml`) | Slice 2 và Slice 6 sửa cả ba file compose; hai file không được lệch nhau |

## 13. Tiêu chí hoàn thành

- Không còn tham chiếu tới `minio/minio`, `minio/mc`, `dl.min.io` trong compose, CI, Dockerfile và kịch bản vận hành.
- Production chạy trên Garage: tải lên, tải xuống, xóa, sao lưu DB, sao lưu kho tệp, khôi phục đều hoạt động, kiểm chứng ở trình duyệt thật.
- Mọi object cũ có mặt trong Garage với đúng tên, kích thước và `sha256` (biên bản kiểm chứng đính kèm).
- Sao lưu theo lịch chạy thành công nhiều ngày liền sau cutover; đã khôi phục thử thật một lần.
- CI xanh, dùng Garage từ image đã mirror và ghim digest.
- Tài liệu vận hành cập nhật; thủ tục khôi phục đã được làm theo từ đầu đến cuối.
- MinIO cũ đã được gỡ (Slice 9) sau thời gian giữ lại đã chốt.

## Phụ lục A. Cấu hình Garage đề xuất (phác thảo)

`docker/garage/garage.toml` (không chứa bí mật; `rpc_secret` và `admin_token` lấy từ biến môi trường `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`):

```toml
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"

db_engine = "sqlite"
metadata_fsync = true
data_fsync = true
metadata_auto_snapshot_interval = "6h"

replication_factor = 1

rpc_bind_addr = "0.0.0.0:3901"
rpc_public_addr = "127.0.0.1:3901"

[s3_api]
s3_region = "garage"
api_bind_addr = "0.0.0.0:3900"

[admin]
api_bind_addr = "0.0.0.0:3903"
```

Service compose (phác thảo, lấy theo `docker-compose.lan.yml`):

```yaml
  garage:
    image: ${GARAGE_IMAGE}:${GARAGE_TAG}      # ghim theo digest của bản mirror
    restart: always
    command: ["/garage", "server", "--single-node"]
    environment:
      GARAGE_RPC_SECRET: ${GARAGE_RPC_SECRET}
      GARAGE_ADMIN_TOKEN: ${GARAGE_ADMIN_TOKEN}
    volumes:
      - ./docker/garage/garage.toml:/etc/garage.toml:ro
      - garage_meta:/var/lib/garage/meta
      - garage_data:/var/lib/garage/data
    healthcheck:
      test: ["CMD", "/garage", "status"]      # U2
      interval: 10s
      timeout: 5s
      retries: 5
```

## Phụ lục B. Script bootstrap (phác thảo)

`scripts/garage_bootstrap.sh`: chạy từ host, idempotent, không ghi khóa ra file.

```bash
#!/usr/bin/env bash
set -euo pipefail
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.lan.yml}"
# Production: export MINIO_BUCKET=hrms-attachments-prod BACKUP_STORAGE_BUCKET=hrms-backup trước khi chạy (mặc định bên dưới là của dev).
G() { docker compose -f "$COMPOSE_FILE" exec -T garage /garage "$@"; }

until G status >/dev/null 2>&1; do sleep 2; done      # chờ Garage sẵn sàng

ensure_bucket() { G bucket info "$1" >/dev/null 2>&1 || G bucket create "$1"; }       # U3
ensure_key()    { G key info "$1"    >/dev/null 2>&1 || G key create "$1"; }          # U3

ensure_bucket "${MINIO_BUCKET:-hrms-attachments-dev}"
ensure_bucket "${BACKUP_STORAGE_BUCKET:-hrms-backup}"
ensure_key hrms-app
ensure_key hrms-backup

G bucket allow --read --write --owner "${MINIO_BUCKET:-hrms-attachments-dev}" --key hrms-app
G bucket allow --read --write --owner "${BACKUP_STORAGE_BUCKET:-hrms-backup}"  --key hrms-backup
G key allow --create-bucket hrms-backup                                              # U4

echo "Khóa được in MỘT LẦN dưới đây; chép vào .env (quyền 600), không lưu nơi khác:"
G key info hrms-app    --show-secret
G key info hrms-backup --show-secret
```

## Phụ lục C. Tài liệu tham khảo

- Garage, trang tương thích S3: https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/
- Garage, tham chiếu cấu hình: https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/
- Garage, hướng dẫn nhanh: https://garagehq.deuxfleurs.fr/documentation/quick-start/
- Garage, triển khai thực tế (Docker): https://garagehq.deuxfleurs.fr/documentation/cookbook/real-world/
- PGSTY Silo (phương án dự phòng): https://github.com/pgsty/minio
- Trạng thái MinIO: https://github.com/minio/minio và https://github.com/minio/mc

## Phụ lục D. Script kiểm kê object storage (chỉ đọc)

Chạy được trên dev (đã kiểm chứng) và dự kiến trên production. Chỉ đọc cấu hình từ biến môi trường của container backend (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_SECURE`), không import gì từ repo, không in khóa. Chỉ in ba tên object (cắt ngắn) cho mỗi bucket vì tên có thể chứa dữ liệu cá nhân.

```python
import os
import sys
from collections import Counter

from minio import Minio

MIB5 = 5 * 1024 * 1024


def env(name, default=None):
    v = os.environ.get(name, default)
    if v is None or v == "":
        sys.exit(f"missing env var {name}")
    return v


endpoint = env("MINIO_ENDPOINT")
secure = os.environ.get("MINIO_SECURE", "false").strip().lower() in ("1", "true", "yes", "on")
client = Minio(endpoint, access_key=env("MINIO_ACCESS_KEY"), secret_key=env("MINIO_SECRET_KEY"), secure=secure)

print(f"endpoint={endpoint} secure={secure}")
buckets = client.list_buckets()
print(f"buckets={len(buckets)}")
g_count = g_bytes = 0
for b in sorted(buckets, key=lambda x: x.name):
    count = total = big = non_ascii = 0
    prefixes = Counter()
    top = []
    for o in client.list_objects(b.name, recursive=True):
        if o.is_dir:
            continue
        size = o.size or 0
        count += 1
        total += size
        if size > MIB5:
            big += 1
        if not o.object_name.isascii():
            non_ascii += 1
        prefixes[o.object_name.split("/", 1)[0] if "/" in o.object_name else "(root)"] += 1
        top.append((size, o.object_name))
    top.sort(reverse=True)
    g_count += count
    g_bytes += total
    print(f"\n[bucket] {b.name}")
    print(f"  objects={count} total_bytes={total} (~{total / 1048576:.2f} MiB)")
    print(f"  objects_gt_5MiB={big} non_ascii_names={non_ascii}")
    print("  top3_largest:")
    for size, name in top[:3]:
        print(f"    {size:>12}  {name[:60]!r}")
    print("  top_level_prefixes:")
    for p, c in prefixes.most_common():
        print(f"    {p[:60]!r}: {c}")
print(f"\nTOTAL objects={g_count} bytes={g_bytes} (~{g_bytes / 1048576:.2f} MiB)")
```
