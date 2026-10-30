# Kế hoạch 15.7 - Chuyển object storage từ MinIO sang Garage

Ngày lập: 2026-10-30

Trạng thái: **Đề xuất, chưa triển khai.** Mọi lệnh và cấu hình trong tài liệu này là phác thảo; chỉ được coi là đã kiểm chứng khi slice tương ứng ghi nhận bằng chứng.

## 1. Mục tiêu

Thay MinIO (kho tệp ứng dụng + đích sao lưu) bằng **Garage** chạy một node, với các ràng buộc:

- Không đổi hành vi nhìn thấy được của người dùng: tải lên, tải xuống, xóa tệp đính kèm; Backup Console tiếp tục chạy sao lưu DB và kho tệp.
- Không mất dữ liệu tệp: kiểm kê ngay trước cutover. Production hiện **không có tệp nào** (0 object, kiểm kê 2026-10-30), nên không có gì để chép; nếu lúc đó có object thì dừng và quyết định (mục 9.0 và 10).
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
- Chuyển production sang Garage. Production không có tệp nào cần chép nên **không** có công cụ chuyển dữ liệu (Slice 4 đã bỏ, xem 9.0).
- Đổi nhãn giao diện (Slice 3); gom chỗ khởi tạo client S3 hoãn sang Slice 10.
- Cập nhật compose production, loại bỏ phụ thuộc `mc` (Slice 6), tài liệu vận hành và CI (Slice 9).
- Runbook cutover production ngắn và quay lui (mục 10); không diễn tập riêng (xem 9.0).

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
- `metadata_auto_snapshot_interval = "6h"`: Garage chỉ giữ hai snapshot gần nhất. Theo mã nguồn v2.5.0 và lần chạy thật ở Slice 1, giá trị tối thiểu là **600 giây (10 phút)**; giá trị nhỏ hơn làm Garage không khởi động được (và có thể kèm thông báo panic gây hiểu nhầm, xem "Kết quả Slice 1"). Snapshot dùng `VACUUM INTO` và nằm trong `<metadata_dir>/snapshots`, tức **cùng volume** với cơ sở dữ liệu nên không chống được mất cả volume.
- Bí mật (`rpc_secret`, `admin_token`) truyền bằng biến môi trường `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`, **không ghi vào file cấu hình trong repo**.

### 5.3. Mạng

- Garage chỉ nằm trong mạng nội bộ của compose, **không publish cổng ra host**. Endpoint cho ứng dụng: `garage:3900`.
- `MINIO_SECURE=false` (S3 API của Garage không có TLS; lưu lượng chỉ đi trong mạng Docker nội bộ).

### 5.4. Bucket, khóa và quyền

Garage dùng mô hình quyền riêng (khóa x bucket), không có ACL/policy của S3.

| Khóa | Bucket | Quyền | Dùng cho |
|---|---|---|---|
| `hrms-app` | `hrms-attachments-<env>` (production: **`hrms-attachments-prod`**, xem 12.3) | đọc, ghi, owner, **tạo bucket** (xem U4 và Slice 2) | `MINIO_*` và `SOURCE_STORAGE_*` (tệp đính kèm, nguồn sao lưu kho tệp, **và bucket đích khi khôi phục kho tệp sang đích mới**) |
| `hrms-backup` | `hrms-backup` | đọc, ghi, owner, **tạo bucket** (xem U4) | `BACKUP_STORAGE_*` (đích sao lưu; đọc bản sao lưu khi khôi phục) |

Định dạng khóa của Garage: access key `GK` + 24 ký tự hex, secret 64 ký tự hex. Khóa **tự sinh bằng `garage key create`**; lệnh `import` chỉ dành cho di trú/khôi phục theo tài liệu Garage, không dùng để đặt khóa tùy ý.

Theo mã nguồn v2.5.0 (đã đọc, chưa chạy): bucket tạo qua S3 (`make_bucket`) chỉ có **alias cục bộ** của khóa tạo ra nó, khóa khác không thấy theo tên; bucket tạo bằng CLI có alias toàn cục, và `make_bucket` trên tên đó trả `BucketAlreadyExists`/`BucketAlreadyOwnedByYou`. Vì vậy mọi bucket của ứng dụng nên do bootstrap tạo bằng CLI. Khóa `hrms-backup` chỉ cần quyền tạo bucket cho chức năng "Khôi phục sang đích mới" khi bucket đích chưa có (`restore_runner_service.py:373`), và bucket tạo kiểu đó chỉ khóa này thấy được. Probe C của Slice 1 kiểm điều này. Lệnh `garage key import <id> <secret>` tồn tại (id từ 8 ký tự, secret từ 16 ký tự theo mã nguồn), nên có thể đặt khóa xác định thay vì để `key create` tự sinh.

Bucket được tạo bằng script bootstrap **trước khi** `backend` khởi động, vì `ensure_bucket()` (`main.py:81`) làm backend lỗi nếu bucket chưa có và khóa không có quyền tạo.

### 5.5. Giữ tên biến `MINIO_*` trong đợt này

Đổi tên biến chạm `config.py`, 3 file compose, CI, `.env` production và nhiều tài liệu; để riêng ở Slice 10. Đợt này chỉ đổi **giá trị**: `MINIO_ENDPOINT=garage:3900`, khóa mới.

### 5.6. Bootstrap bằng script, không bằng container khởi tạo

Image Garage dựng `FROM scratch`, **không có shell** (tài liệu chính thức), nên không chạy được script bên trong container. Dùng `scripts/garage_bootstrap.sh` chạy từ máy host qua `docker compose exec -T garage /garage ...`, **idempotent** (chạy lại không lỗi), in khóa ra terminal đúng một lần và không ghi ra file.

### 5.7. Chuẩn hóa client S3

(**Hoãn sang Slice 10**, xem 9.0; `region` đã được truyền ở 4 chỗ từ Slice 2.) Tạo một hàm duy nhất `build_s3_client(endpoint, access_key, secret_key, secure, region=None)` (ví dụ ở `backend/app/core/s3_client.py`) và thay 4 chỗ `Minio(...)` ở mục 3.2. Tham số `region` **bắt buộc, đã xác nhận bằng chạy thật ở Slice 1** (xem "Kết quả Slice 1"). Theo mã nguồn v2.5.0, Garage từ chối chữ ký có region khác `s3_region` (`AuthorizationHeaderMalformed`), còn `minio-py` khi không có `region` sẽ dò bằng yêu cầu `GetBucketLocation` ký cho `us-east-1`; trang hướng dẫn Python của Garage cũng dặn đặt `region="garage"` (U5). Hiện `core/storage.py:_client()` tạo một `Minio(...)` mới cho **mỗi lần gọi**, nên không truyền `region` còn làm thêm một yêu cầu dò region mỗi lần; truyền `region` loại bỏ cả hai vấn đề.

### 5.8. Healthcheck

Image không có `curl`/`wget`/shell. Đề xuất `["CMD", "/garage", "health", "-q"]` (U2: đã chạy được dưới compose ở Slice 1, container lên `Healthy`). Theo mã nguồn v2.5.0, `garage health` thoát 1 khi cụm "unavailable" hoặc RPC không nối được, còn `garage status` chỉ thoát khác 0 khi RPC hỏng nên **không** phản ánh sức khỏe. Không dùng `docker run --health-cmd` (luôn bọc `CMD-SHELL`, hỏng trên image không có shell). Giữ được `depends_on: condition: service_healthy` cho `backend` và `celery_*` như hiện nay với MinIO.

### 5.9. Dừng dùng `mc`

Bỏ `backup_scheduler` và image sao lưu cũ (quyết định D3). Thủ tục khôi phục và tải artifact viết lại bằng SDK Python trong image backend (cách đã dùng thành công để tải file dump production).

### 5.10. Chuỗi cung ứng image

Mirror `dxflrs/garage:v2.5.0` lên `ghcr.io/nguyencuonghut/hrms/` và ghim theo **digest**, vì bài học MinIO: một image công khai có thể biến mất. Không dùng tag `latest`. Compose mặc định kéo thẳng từ Docker Hub theo digest (image công khai, không cần đăng nhập); bản mirror ghcr chỉ là **dự phòng** nếu Docker Hub xóa image (khi đó đổi `GARAGE_IMAGE` và đăng nhập ghcr bằng token chỉ đọc).

## 6. Bản đồ luồng dữ liệu

### 6.1. Các luồng và thay đổi

| # | Luồng | Đường đi | Thay đổi |
|---|---|---|---|
| F1 | Tải lên tệp đính kèm | Trình duyệt, nginx, `backend` (đọc vào RAM, kiểm tra loại/kích thước), `put_object`, ghi `object_name` vào DB | Chỉ đổi endpoint/khóa |
| F2 | Tải xuống | Trình duyệt, `backend`, `get_object` (stream), trả `StreamingResponse` | Như trên |
| F3 | Xóa | `backend`, `remove_object` (nuốt `S3Error`) | Như trên |
| F4 | Khởi động | `lifespan`, `ensure_bucket()` (`bucket_exists`, `make_bucket`) | **Cần bucket + quyền có sẵn** (bootstrap trước) |
| F5 | Health | `/health`, `bucket_exists(bucket)` | Giữ khóa `checks["minio"]` |
| F6 | Sao lưu DB | `celery_worker`, `pg_dump` rồi nén gzip, `put_object` vào `BACKUP_STORAGE_*` | Đổi endpoint/khóa sao lưu |
| F7 | Sao lưu kho tệp | `celery_worker`, `list_objects` + `get_object` từ **nguồn** (`backup_configs.source_*` hoặc `SOURCE_STORAGE_*`/`MINIO_*`), `put_object` sang **đích** (`files/files-<ts>/`) kèm manifest | **Phải sửa `backup_configs.source_endpoint` trong DB** |
| F8 | Khôi phục | `restore_runner`, `get_object` từ bucket sao lưu, ghi sang đích (`make_bucket` nếu đích mới, bằng khóa **ứng dụng**) | Cả hai khóa cần quyền tạo bucket (Slice 2) |
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

Hai định dạng lưu trữ **không tương thích**, nên nếu có dữ liệu cần giữ thì phải chép đối tượng qua S3, không phải sao chép volume (hiện production không có tệp nào, nên không cần).

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

Kiểm chứng ở mức trình duyệt (Slice 2, 8), đọc DOM và request mạng. Nếu hạ tầng e2e hiện chỉ giả lập API, dùng kiểm tra thủ công bằng trình duyệt thật và ghi lại kết quả; **không viết test giả**.

### 8.2. Quản trị viên: Backup Console

1. Mở màn hình Sao lưu; dòng "Kho tệp ứng dụng" hiện đúng nhãn mới.
2. Bấm bút chì: form hiện nguồn `garage:3900`, bucket `hrms-attachments-dev`, các công tắc bảo mật tắt.
3. Lưu, rồi bấm nút dấu tích "Kiểm tra đích sao lưu": trạng thái **Thành công** với thời gian mới.
4. Bấm ▶ trên cả hai dòng: job `success`, hiện `artifact_bucket = hrms-backup` và khóa `postgres/...`, `files/...`.

### 8.3. Vận hành: cutover (tóm tắt, chi tiết ở mục 10)

Kiểm kê (phải 0 tệp), sao lưu DB, dựng Garage song song và bootstrap, đổi cấu hình (`.env` và DB), khởi động lại `backend` và `celery_*`, kiểm chứng, dừng MinIO nhưng giữ lại để quay lui. Không có bước chép dữ liệu.

## 9. Kế hoạch triển khai theo slice

Mỗi slice có cổng kiểm chứng riêng. Quy tắc chung (theo `AGENTS.md`): kết luận phải có bằng chứng; thay đổi ảnh hưởng giao diện phải kiểm bằng trình duyệt; báo cáo cuối slice nêu rõ **đã kiểm chứng gì và chưa kiểm chứng gì**. **Không chạy `pytest` trên DB `hrms` đang là bản sao production**: chạy trên bản clone (`CREATE DATABASE x TEMPLATE hrms`) rồi xóa, vì `test_administrative_import.py` xóa danh mục hành chính thật.

### 9.0. Bản rút gọn (2026-10-30)

**Tiền đề do chủ hệ thống nêu:** DB production thực tế mới có Phòng/ban, Chức danh, Vị trí công việc và 4 nhân viên thử; DB đã sao lưu và các tệp dữ liệu import vẫn còn, nên import lại được bất kỳ lúc nào; nếu mất cũng chấp nhận được. Cùng với kiểm kê ngày 2026-10-30 (bucket tệp 0 object; `hrms-backup` có 3 object là bản sao lưu thử), **không có dữ liệu tệp nào cần bảo toàn**. Đây là điều kiện để rút gọn: nếu trước cutover người dùng đã tải tệp lên (kiểm kê lại), kế hoạch phải được xem lại.

| Slice | Trạng thái | Thay đổi so với bản đầu |
|---|---|---|
| 0, 1, 2 | **Đã làm** | Không đổi |
| 3 | Giữ, rút gọn | Chỉ đổi nhãn "Kho tệp ứng dụng" kèm test/e2e. Bỏ `build_s3_client` và `checks["storage"]`: 4 chỗ tạo client đã nhận `region` và có test từ Slice 2, gom lại chỉ là dọn mã, hoãn sang Slice 10 |
| 4 | **Bỏ** | Không có gì để chép (0 tệp). 3 bản sao lưu thử không cần chuyển; chạy sao lưu mới sau cutover |
| 5 | **Dời sang Slice 9, tùy chọn** | CI vẫn cần một S3 sống: chạy toàn bộ `pytest` khi S3 không tồn tại cho 231 test qua, 8 thất bại, 1.385 lỗi (mẫu đã xem: `MaxRetryError` ở `ensure_bucket()` trong `lifespan` của `TestClient`), nên không thể chỉ xóa service MinIO. Nhưng CI đang chạy tốt với MinIO, nên không chặn cutover. Production kéo image Garage từ Docker Hub theo digest (công khai) nên không còn cần token chỉ đọc cho ghcr (U16) |
| 6 | Giữ, mở rộng | **Compose production**: thêm `garage`, truyền `region`, đổi `depends_on`, đưa `minio` vào profile, gỡ `backup_scheduler` và `mc` (D3) |
| 7 | **Bỏ** | Không có bước chép dữ liệu để diễn tập; các thành phần đã chạy thật ở Slice 2. Thay bằng kiểm tra tĩnh (`docker compose config`) ở Slice 6 |
| 8 | Giữ, rút gọn | Runbook ngắn (mục 10): không snapshot MinIO, không chép dữ liệu, không cửa sổ bảo trì riêng (khởi động lại backend khoảng 1 phút) |
| 9 | Mở rộng | Dọn dẹp sau cutover: gỡ MinIO, viết lại `restore_procedure.md`, cập nhật tài liệu, CI (tùy chọn) |
| 10 | Tùy chọn | Không đổi; thêm việc gom `build_s3_client` |

**Quyết định bị tác động:** D1 (cửa sổ bảo trì) không còn cần riêng. D4 (giữ MinIO cũ): **chủ hệ thống đã xác nhận (2026-10-30) rút xuống "đến khi sao lưu theo lịch đêm đầu tiên thành công trên Garage"** thay cho 7 ngày, vì MinIO không còn dữ liệu cần giữ. D2 (bản sao lưu ngoài máy) vẫn nên làm.

**Không rút gọn được:** kiểm kê lại ngay trước cutover; sửa `backup_configs.source_endpoint` trong DB (R2, đã gặp thật ở Slice 2); thêm `MINIO_REGION`/`BACKUP_STORAGE_REGION` vào compose production (Slice 6; hiện hai file đó không truyền hai biến này); kiểm tra bằng trình duyệt thật sau cutover; không xóa MinIO cũ trước khi có sao lưu theo lịch thành công trên Garage (đường lui gần như miễn phí).

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
- Đưa bộ kiểm tra vào repo: `backend/app/scripts/s3_conformance_probe.py` (dùng chính SDK `minio` của ứng dụng; 12 kiểm tra: `bucket_exists` cho bucket có và không có, `make_bucket`, put/stat/get, multipart 12 MiB so `sha256`, tên có dấu tiếng Việt/khoảng trắng/`#`/`()`/`+`/`%`/`&`/`?`/`'` (ứng dụng đặt tên object bằng nguyên tên tệp người dùng tải lên), ghi đè, 1.050 object đồng thời + phân trang, liệt kê không đệ quy, xóa, mã lỗi, dọn dẹp). Test của chính bộ kiểm tra: `backend/tests/test_s3_conformance_probe.py` (31 test dùng S3 giả có lỗi cố ý, không cần Docker).
- Đưa script chạy vào repo: `scripts/garage_spike.sh`. Script dựng hai instance Garage `v2.5.0` trong một project compose tạm (mạng và volume riêng, tự dọn): `garage` đúng cấu hình Phụ lục A (fsync bật, snapshot `6h`), và `garage_nofsync` (như trên nhưng tắt fsync) để so độ trễ. Với mỗi instance, script chạy probe hai lần: **A** là kịch bản production (bucket tạo sẵn, khóa không có quyền tạo bucket) **B** sau khi cấp `key allow --create-bucket`, và **C** giữ lại bucket tạo qua S3 để xem alias. Healthcheck của compose tạm là `garage health -q`. Nếu lỗi có dấu hiệu liên quan region, script tự chạy lại với `--region garage`.
- Chủ hệ thống tự chạy (xem mục "Cách chạy" bên dưới) và gửi lại đầu ra; người lập kế hoạch phân tích và ghi kết quả vào mục "Kết quả Slice 1".

**Cách chạy** (trên máy dev, không phải production; cần image `hrms-backend:latest` có sẵn, vì chứa SDK `minio`):

```bash
cd /run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS
bash scripts/garage_spike.sh 2>&1 | tee /tmp/garage_spike.out
```

Mất khoảng 2 phút. Đầu ra không chứa bí mật (khóa chỉ nằm trong biến shell; mọi chuỗi hex 64 ký tự bị che), nên dán nguyên văn được. Dùng `KEEP=1` để giữ lại container xem thủ công, `GARAGE_IMAGE=<digest của bản mirror>` để thử đúng image sẽ dùng thật.

**Cách đọc kết quả (mỗi điểm chưa xác minh lấy bằng chứng ở đâu)** (U1-U17, mục 12.1)

| Mục | Bằng chứng trong đầu ra |
|---|---|
| U1 | bước "U1": `garage status`, `layout show` (dung lượng, zone do `--single-node` tạo) |
| U2, U13 | bước "U13/U2": `up gate` thành công, log `gate` có dòng "đã chạy", và trạng thái healthcheck `healthy` của cả hai instance |
| U3 | mã thoát của `bucket info`/`key info` với đối tượng có và không có |
| U4 | probe A: `make_bucket` FAIL (mong đợi), sau `key allow --create-bucket` probe B: `make_bucket` PASS |
| U5 | probe không có `--region` vượt qua kiểm tra đầu tiên; nếu không thì xem lần chạy lại với `--region garage` |
| U6, U7, U14 | các dòng PASS/FAIL tương ứng của probe, kèm mã lỗi trong cột chi tiết |
| U8 | probe kết nối được qua mạng bridge khi Garage bind `0.0.0.0` (chưa so với `[::]`) |
| U9, U17 | log khởi động của từng instance và nội dung volume metadata; Garage khởi động được dù `garage.toml` không có `rpc_secret` (secret lấy từ biến môi trường) |
| U10 | so thời gian dòng "1050 objects" và "12 MiB" giữa `garage` và `garage_nofsync` |
| U11 | bộ `snapshot` của `scripts/garage_spike_crash.sh` (đã chạy; kết quả ở "Kết quả Slice 1") |
| U15 | các dòng "tài nguyên" khi rảnh và sau probe |
| U12, U16 | **không kiểm được cục bộ**: U12 chỉ liên quan CI (tùy chọn, Slice 9, cần GitHub Actions thật); U16 không còn chặn (xem 9.0) |

Script chẩn đoán đi kèm: `scripts/garage_spike_crash.sh` (hai bộ `crash` và `snapshot` đều đã chạy; xem "Kết quả Slice 1").

**Kiểm chứng (cổng)**: mọi bài kiểm tra PASS, hoặc mọi FAIL đều khắc phục được bằng cấu hình/tham số SDK. Riêng probe A có đúng một FAIL được chấp nhận trước: `make_bucket`, vì khóa của ứng dụng không có quyền tạo bucket. Nếu không đạt: dừng và đánh giá phương án dự phòng (Silo) trước khi sang slice sau.

**Đã xác minh trước khi chạy**
- Probe đạt 12/12 trên MinIO dev thật và dọn sạch bucket thử (đối chứng dương); sai khóa cho `SignatureDoesNotMatch` thoát mã 1 (đối chứng âm).
- `scripts/garage_spike.sh`: chạy trọn luồng với `docker` giả (không có Garage thật): đọc đúng khóa, bí mật 0 lần trong đầu ra và 0 lần trên dòng lệnh, dọn sạch thư mục tạm; file compose sinh ra qua `docker compose config` thật. **Chưa xác minh**: định dạng đầu ra thật của `garage key create` (script lấy khóa bằng mẫu `GK` + 24 hex và chuỗi 64 hex nên không phụ thuộc nhãn, nhưng chưa thấy đầu ra thật), và mọi hành vi của Garage.

**Lưu ý**: bước này chạy image bên thứ ba và cần phê duyệt của người vận hành, nên do người vận hành tự chạy.

**Rollback**: script tự dọn (`down -v`); nếu dùng `KEEP=1` thì chạy lệnh dọn mà script in ra.

### Kết quả Slice 1 (lần chạy 1, 2026-10-30 15:15 +07)

Chạy `scripts/garage_spike.sh` trên máy dev (Docker 29.8.2, Compose 5.6.0) với `dxflrs/garage:v2.5.0`. Lần chạy này không ghi được digest vì bộ che bí mật của script che luôn mọi chuỗi 64 hex (đã sửa); lần chạy chẩn đoán sau đó in digest của image đã kéo là `dxflrs/garage@sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5`, **trùng từng ký tự** với manifest list đã ghim ở Slice 0 và đã mirror lên ghcr.

**Kết luận: tương thích S3 ĐẠT; GO có điều kiện (chủ hệ thống đã chấp thuận ngày 2026-10-30, xem 12.3).** Mọi FAIL đều khắc phục được bằng cấu hình hoặc tham số SDK, đúng tiêu chí cổng:
- truyền `region="garage"` cho SDK `minio` (U5);
- bucket của ứng dụng do bootstrap tạo bằng CLI; quyền tạo bucket chỉ cần cho "Khôi phục sang đích mới" vào bucket chưa có (U4), và theo kết quả Slice 2 phải cấp cho **cả hai khóa** vì khóa ứng dụng mới là khóa tạo bucket đích;
- `metadata_auto_snapshot_interval` phải từ 10 phút trở lên (U11); crash ở lần chạy 1 là do đặt `1min`, không phải do fsync hay lỗi dữ liệu.

Còn mở (không chặn cổng, xử lý ở slice sau): `health -q` có thoát 1 khi cụm chưa sẵn sàng không (U2), độ trễ khi tắt fsync (U10; ta dùng fsync bật nên không cần), token Admin API có được áp dụng không (U17), và U12 chỉ liên quan CI (tùy chọn, Slice 9) và U16 không còn chặn (9.0).

| Mục | Kết quả quan sát được | Trạng thái |
|---|---|---|
| U1 | `--single-node` tự tạo layout: phiên bản 1, zone `dc1`, dung lượng 465,5 GiB (bằng tổng đĩa); không cần `--default-bucket` | Đạt |
| U2 | Healthcheck `["CMD","/garage","health","-q"]` dưới compose: container lên `Healthy`; `health -q` và `status` đều thoát 0 khi cụm khỏe. **Chưa kiểm** `health -q` có thoát 1 khi chưa sẵn sàng | Đạt một phần |
| U3 | `bucket info`/`key info` với đối tượng không có: thoát 1 (`NoSuchBucket (404)`, `NoSuchAccessKey (404)`); có: thoát 0. Khóa tự sinh dạng `GK` + 24 hex, secret 64 ký tự. `key info` không có `--show-secret` in `(redacted)`. Đầu ra CLI kèm dòng `INFO garage_net::netapp` (script gộp stdout và stderr nên chưa biết dòng đó ở luồng nào) | Đạt |
| U4 | Probe A: khóa không có quyền tạo bucket thì `make_bucket` bị `AccessDenied` ("is not allowed to create buckets"), đúng một FAIL dự kiến, mọi kiểm tra còn lại đạt. Sau `key allow --create-bucket`, probe B đạt 12/12 và dọn được bucket. Bucket tạo qua S3 (`probe-c`) chỉ có **alias cục bộ** `GK...:probe-c`; `bucket info probe-c` theo tên trả `NoSuchBucket` | Đạt; có hệ quả thiết kế (5.4) |
| U5 | Không truyền `region`: mọi kiểm tra cần bucket lỗi `AuthorizationHeaderMalformed` (ký cho `us-east-1`, server mong `garage`). Truyền `region="garage"`: đạt hết | Đạt: **cần `region="garage"`** |
| U6, U7 | 1.050 object đồng thời + phân trang: `1050/1050`; 3 tên có dấu tiếng Việt, khoảng trắng, `# ( ) + % & ? '` đọc lại nguyên vẹn; multipart 12 MiB `sha256` khớp | Đạt |
| U8 | Garage bind `0.0.0.0` (log: `Listening on 0.0.0.0:3901`, S3 `:3900`, admin `:3903`) và probe nối được qua mạng bridge. Chưa so với `[::]` | Đạt cho `0.0.0.0` |
| U9 | Ghi được vào volume có tên; file trong volume thuộc `root:root`. Cấu hình image không có khóa `User` | Đạt (chạy root) |
| U10 | Với fsync **bật** (cấu hình ta dùng): put + get 12 MiB mất 0,12 giây; 1.050 put đồng thời + liệt kê mất 1,20 giây (MinIO dev: 0,09 và 1,21 giây). **Chưa có** số liệu fsync tắt để so (instance đó crash) | Đạt một phần |
| U11 | Snapshot hoạt động với `sqlite`: lệnh thủ công `garage meta snapshot` tạo `snapshots/<UTC>/db.sqlite` (573.440 byte); chu kỳ tự động `10min` chụp đúng sau nửa chu kỳ (5 phút) và node vẫn khỏe. Chu kỳ dưới 600 giây bị từ chối. Lần chụp đầu của `6h` (khoảng 3 giờ sau khởi động) chưa quan sát, nhưng cơ chế đã chạy ở `10min` | Đạt (xem chẩn đoán bên dưới) |
| U12, U16 | Không kiểm được cục bộ | U12: CI tùy chọn ở Slice 9; U16: không còn chặn (9.0) |
| U13 | `up gate` chờ dòng `garage ... Healthy` rồi mới khởi động `gate`; log `gate` có dòng "đã chạy" | Đạt |
| U14 | Thiếu khóa: `NoSuchKey`. `stat` trên bucket không tồn tại: **`NoSuchKey`** (không phải `NoSuchBucket` như MinIO; `minio-py` suy mã từ HEAD không có thân). Ứng dụng chỉ bắt `S3Error` chung (`core/storage.py:258`) nên không ảnh hưởng | Đạt |
| U15 | Rảnh: RAM 7,6 MiB, CPU 0,01%. Sau probe: RAM 15 MiB, CPU 0,02% | Đạt |
| U17 | Garage khởi động và lắng nghe dù `garage.toml` không có `rpc_secret`/`admin_token` (lấy từ biến môi trường); CLI gọi `GetClusterHealth` qua Admin API được. **Chưa kiểm** token có được áp dụng | Đạt một phần |

**Chẩn đoán crash (lần chạy 2 và 3, 2026-10-30 15:26 và 15:33 +07; máy dev Intel i7-1355U, kernel 6.6.156, Docker dùng containerd snapshotter).** Ở lần chạy 1, instance `garage_nofsync` (fsync tắt + snapshot mỗi 1 phút) thoát mã 139. `scripts/garage_spike_crash.sh` chạy từng cấu hình riêng (mỗi cấu hình một container và volume mới):

| Biến thể | fsync | Chu kỳ snapshot | Kết quả quan sát được |
|---|---|---|---|
| A | bật | `6h` | chạy ổn 30 giây, `health -q` thoát 0 |
| B | tắt | không đặt | chạy ổn 30 giây, `health -q` thoát 0 |
| C | bật | `1min` | **crash**, mã 139, sau chưa tới 1 giây |
| D1, D2 | tắt | `1min` | **crash**, mã 139, sau chưa tới 1 giây (cả hai lần) |
| M | bật | không đặt, gọi `garage meta snapshot` | chạy ổn; "Snapshot created"; có `snapshots/2026-10-30T08:33:13Z/db.sqlite` (573.440 byte) |
| I60 | bật | `60s` | **thoát mã 1 sạch**: `Error: metadata_auto_snapshot_interval too small or negative` |
| I2 | bật | `2min` | **crash**, mã 139, giống C |
| I10 | bật | `10min` | chạy ổn 330 giây; snapshot tự động lúc 08:38:42, đúng 5 phút sau khi khởi động (08:33:41); log có `Metadata db snapshot finished`; `health -q` thoát 0 |
| I1H | bật | `1h` | chạy ổn 20 giây |

Thông báo panic ở C, D1, D2, I2 giống hệt: `panicked at src/table/merkle.rs:326:4: called Result::unwrap() on an Err value: JoinError::Cancelled(Id(19))`.

Kết luận:
- **Nguyên nhân: chu kỳ snapshot nhỏ hơn 600 giây.** Quan sát: mọi giá trị dưới 600 giây (`60s`, `1min`, `2min`) thất bại, mọi giá trị từ 600 giây trở lên (`10min`, `1h`, `6h`) chạy được. Mã nguồn v2.5.0 (đọc qua công cụ tóm tắt, `Garage::spawn_workers`) có đúng điều kiện `if interval < Duration::from_secs(600)` trả lỗi trên. Chỉ `60s` cho thấy thông báo lỗi sạch trong dữ liệu ta có.
- **Panic ở `1min` và `2min` là biểu hiện phụ (suy luận, chưa thấy trực tiếp)**: lỗi trả về khi dựng worker làm tiến trình thoát trong lúc `MerkleWorker` đang chờ một tác vụ `spawn_blocking`, nên tác vụ bị hủy (`JoinError::Cancelled`) rồi `.unwrap()` gây panic. Ta chưa thấy dòng "too small" trong log của `1min`/`2min` vì script đã cắt log.
- **fsync không liên quan**: C (fsync bật) crash như D (fsync tắt); B (fsync tắt, không snapshot) chạy ổn.
- **`6h` trong Phụ lục A hợp lệ.** Lần chụp đầu của nó (khoảng 3 giờ sau) chưa quan sát, nhưng cơ chế đã chạy đúng ở `10min`; snapshot đầu luôn được lên lịch sau nửa chu kỳ.
- **Hệ quả vận hành**: cấu hình sai chu kỳ không cho thông báo dễ hiểu và với `restart: always` sẽ lặp crash. Slice 2 cần một bước khởi động thử cấu hình (hoặc đọc log) trước khi coi là xong.

**Lỗi của script ở lần chạy này (đã sửa)**: lệnh `docker image inspect` lỗi template; che nhầm digest và ID bucket; không lấy được trạng thái container đã chết; `--tail 40` cắt mất thông báo panic; kiểm tra "thiếu khóa/bucket" của probe chấp nhận mọi `S3Error` nên PASS sai lý do trong lần chạy không có `region` (nay đòi đúng mã `NoSuchKey`/`NoSuchBucket`).

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

### Kết quả Slice 2 (2026-10-30)

**Thay đổi đã làm (chưa commit):** `docker/garage/garage.toml`; service `garage` trong `docker-compose.yml` (ghim digest, không publish cổng, healthcheck `garage health -q`); `minio` chuyển vào profile `legacy-minio`; `backend`, `celery_worker`, `celery_beat` trỏ sang `garage:3900`; `scripts/garage_bootstrap.sh`; `.env.example`; và, **ngoài phạm vi ban đầu của slice**, tham số `region` (`MINIO_REGION`, `BACKUP_STORAGE_REGION`) ở 4 chỗ tạo client, làm theo TDD (7 test, `backend/tests/test_s3_client_region.py`). Lý do kéo `region` lên Slice 2: Slice 1 cho thấy mọi lệnh cần bucket lỗi `AuthorizationHeaderMalformed` nếu thiếu `region`, và `ensure_bucket()` chạy ngay trong `lifespan`, nên backend không khởi động được với Garage; cổng 2 đến 4 không thể đạt nếu thiếu.

**Cách kiểm chứng:** Garage chạy thật từ `docker-compose.yml`. Phần trình duyệt chạy trên **bản clone DB** (`CREATE DATABASE ... TEMPLATE hrms`, thêm user thử chỉ vào clone), không chạm DB `hrms`; clone đã xóa sau khi xong.

| Cổng (mục Slice 2) | Kết quả | Bằng chứng |
|---|---|---|
| 1. `up -d`: `garage` healthy; bootstrap hai lần không lỗi | Đạt | healthy sau ~2 giây; lần 1 tạo 2 bucket + 2 khóa và in 4 dòng; lần 2 báo "đã có" cho tất cả, stdout rỗng |
| 2. `backend` khởi động; `/health` có `checks.minio = ok` | Đạt | `{"database":"ok","redis":"ok","minio":"ok"}`. Đối chứng âm trên Garage thật: bỏ trống `MINIO_REGION` thì `S3Error: AuthorizationHeaderMalformed` |
| 3. Trình duyệt: luồng 8.1 (tải lên, tải xuống đúng nội dung, xóa) | Đạt một phần | Tải lên qua giao diện (tệp 20 KB tên `Hợp đồng lao động (bản 1) #2+A&B 100% [..].pdf` và tệp 6 MiB đi đường multipart): object có trong Garage với `sha256` khớp từng byte; API tải xuống (có token) trả đúng nội dung và tên tệp; xóa qua giao diện làm mất dòng và mất object trong Garage. **Nút "Tải xuống" trên giao diện không tải được** (xem phát hiện 4) |
| 4. Trình duyệt: luồng 8.2 (Backup Console) | Đạt | Sửa nguồn `minio:9000` thành `garage:3900` qua form (PUT 200); kiểm tra đích Thành công cho cả hai dòng; ▶ sao lưu DB (617 KB) và kho tệp `success` vào `hrms-backup`. Với 13 object nguồn (31,6 MB, gồm tệp 6 MiB), mọi object có trong bản sao lưu với size và `sha256` giống hệt (thêm 1 tệp manifest). Nhãn vẫn là "Kho tệp ứng dụng trên MinIO" (đổi ở Slice 3) |
| 5. Khởi động lại Garage: dữ liệu còn | Đạt | danh sách tên và kích thước của cả hai bucket giống hệt trước và sau (mã băm danh sách trùng); healthy sau ~8 giây; `/health` vẫn ok |

Kiểm tra ngoài cổng: khôi phục kho tệp (`_restore_object_snapshot_sync`) sang bucket mới: **trước** khi cấp quyền tạo bucket cho khóa ứng dụng thì `AccessDenied`; **sau** khi cấp thì chép đủ 13 object (31.600.877 byte), không thiếu và không khác (thêm 1 tệp đánh dấu `.hrms-restore/request-N.json`), bucket thử đã dọn được bằng khóa ứng dụng. Test: 65 test (7 mới + 58 có sẵn của `test_backups`, `test_backup_runner_service`, `test_security`) qua trên clone DB; lint không phát sinh cảnh báo mới. E2E `backup-center.spec.ts` trên stack dùng Garage: 13/15 qua.

**Phát hiện và hệ quả**
1. **Khóa ứng dụng cũng cần quyền tạo bucket** (sửa lỗi của §5.4 và Phụ lục B): `restore_runner_service.py` tạo bucket đích bằng `_source_client()`, tức khóa `MINIO_*`, không phải khóa sao lưu. Bootstrap đã cấp cho cả hai khóa.
2. **Cấu hình sao lưu nằm trong DB (R2) đã gặp thật**: bản sao production có `object_storage.source_endpoint = minio:9000`; phải sửa bằng form (hoặc SQL) thì sao lưu kho tệp mới chạy trên Garage. Ở production, bước này nằm trong cutover (mục 10).
3. **`.env` dev đặt tường minh `BACKUP_STORAGE_ENDPOINT=minio:9000`** cùng khóa sao lưu của MinIO, nên đổi mặc định trong compose chưa đủ: người dùng phải sửa `.env` (xóa các dòng `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `BACKUP_STORAGE_ACCESS_KEY`, `BACKUP_STORAGE_SECRET_KEY` cũ rồi nối đầu ra bootstrap, đổi hoặc xóa `BACKUP_STORAGE_ENDPOINT`). Script không tự sửa `.env`.
4. **Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không hoạt động** (`AttachmentsTab.vue`, hàm `download`): tạo thẻ `<a>` tới `/api/v1/employees/{id}/attachments/{id}/download` không kèm token nên backend trả `401` (kiểm bằng `curl`: không token `401`, có token `200` đúng nội dung); trình duyệt hủy tải. Xảy ra ở lớp xác thực, trước khi chạm tới kho tệp, nên không do Garage; frontend không bị sửa trong slice này. **Chưa kiểm** trên MinIO, và **chưa sửa** (ngoài phạm vi).
5. **Hai test e2e có sẵn lỗi selector** (`backup-center.spec.ts:589` và `:742`): `getByRole('button', { name: 'Sao lưu đầy đủ' })` khớp hai nút (không `exact`); test 589 giả lập toàn bộ API. Không liên quan kho tệp; chưa sửa. Vì chế độ `serial`, một test lỗi làm 9 test sau bị bỏ qua khi chạy cả file, nên phải chạy từng test.
6. **Ghi chú hạ tầng kiểm thử**: Vite proxy `/api` tới host `backend:8000`, nên backend thay thế phải mang alias `backend` trên mạng compose; `@playwright/test` không có trong `frontend/node_modules` trên máy chủ (nằm trong volume của container `frontend`).
7. **Kế hoạch §5.8 chưa chính xác**: chỉ `backend` có `depends_on: minio`; `celery_worker` và `celery_beat` không có, nên không có gì để đổi cho hai service này.

**Chưa kiểm**: luồng 8.1 bằng nút "Tải xuống" thật trên giao diện (xem phát hiện 4); nhãn mới ở giao diện (Slice 3); bootstrap trên `docker-compose.lan.yml` và `docker-compose.prod.yml` (Slice 6); sao lưu theo lịch 02:00/03:00 của celery beat (chỉ chạy tay); khôi phục kho tệp qua giao diện thật (chỉ gọi hàm của ứng dụng); hành vi sau nhiều ngày chạy liên tục.

### Slice 3 - Nhãn giao diện "Kho tệp ứng dụng" (rút gọn)

**Việc làm**
- Đổi nhãn `"Kho tệp ứng dụng trên MinIO"` thành **`"Kho tệp ứng dụng"`** (thuật ngữ đã chốt trong `CONTEXT.md`, không nêu tên công nghệ): `backup_service.py:42`, `BackupCenterView.vue:6, 827, 1061, 1066` (dòng 6 và 1066 còn câu chữ "trên MinIO"/"kết nối MinIO" cần viết lại không nêu công nghệ), và các fixture/assert tương ứng trong `backup-center.spec.ts`.
- Không làm (hoãn sang Slice 10): hàm `build_s3_client`, `checks["storage"]`.

**Kiểm chứng (cổng)**
- `npm run build` và `vue-tsc`.
- `backup-center.spec.ts`: chạy **từng test** (chế độ `serial` bỏ qua các test sau khi một test lỗi). Hai test `:589` và `:742` đang lỗi selector có sẵn (`"Sao lưu đầy đủ"` khớp hai nút, xem kết quả Slice 2) nên không dùng làm bằng chứng cho slice này; sửa bằng `exact: true` nếu chủ hệ thống đồng ý.
- Trình duyệt thật: nhãn mới hiển thị ở danh sách, form và dropdown. Đây là thay đổi full-stack: nêu rõ cả hai mức đã kiểm.

**Rollback**: revert commit; không đổi dữ liệu.

### Kết quả Slice 3 (2026-10-30)

**Thay đổi (chưa commit):** nhãn `"Kho tệp ứng dụng trên MinIO"` thành `"Kho tệp ứng dụng"` ở `backup_service.py:42` (cũng là tên việc trong email thông báo sao lưu: `job_name`), `BackupCenterView.vue` (tiêu đề phụ, dropdown "Loại khôi phục", hai giá trị dự phòng; câu "Địa chỉ kết nối MinIO" thành "Địa chỉ kết nối nguồn"), và các kỳ vọng trong `backup-center.spec.ts`. **Ngoài danh sách ban đầu**: thông báo lỗi khi nhập sai tên kho (`schemas/backup.py`) từ "kho lưu trữ MinIO/S3 không hợp lệ" thành "kho lưu trữ không hợp lệ", vì quản trị viên nhìn thấy nó trong form.

**Đã kiểm chứng**
- Backend (TDD, trên clone DB): 2 test (nhãn trong email: `test_backups.py`, đã sửa kỳ vọng và thấy đỏ trước; thông báo lỗi: test mới, đỏ trước); 38 test của `test_backups.py` và `test_backup_runner_service.py` qua; lint không phát sinh cảnh báo mới.
- Frontend: `vue-tsc --noEmit` thoát 0; `vite build` thành công (build ra `/tmp` trong container, không đụng `frontend/dist`).
- Trình duyệt thật (clone DB sạch, backend thật chạy trên Garage): API trả `kind_label = "Kho tệp ứng dụng"`; danh sách có nhãn mới và nút "Chạy sao lưu Kho tệp ứng dụng"; form có tiêu đề "Sửa cấu hình sao lưu: Kho tệp ứng dụng"; dropdown "Loại khôi phục" gồm đúng 3 lựa chọn `Cơ sở dữ liệu PostgreSQL`, `Kho tệp ứng dụng`, `Bộ sao lưu đầy đủ`; toàn trang không còn chữ "minio" ở phần giao diện (đã loại trừ khóa artifact là dữ liệu).
- `backup-center.spec.ts` chạy từng test: 13/15 qua.

**Không liên quan nhãn, chưa sửa**
- Hai test `:589` và `:742` vẫn lỗi selector (`"Sao lưu đầy đủ"` khớp hai nút), như ở Slice 2.
- **Dữ liệu thử làm hỏng một phép kiểm có sẵn**: khi chạy `pytest` lên **cùng** một clone rồi chạy e2e, 3 test (`:209`, `:1091`, `:1111`) lỗi ở phép kiểm "giao diện không chứa từ tiếng Anh", vì bảng "Yêu cầu khôi phục" hiện thông báo của backend "Đã kiểm tra artifact DB." (có từ `artifact`). Trên clone sạch cả ba đều qua. Hệ quả: chạy e2e Backup Console phải dùng clone chưa chạy `pytest`. Thông báo này là chữ tiếng Anh thật do `restore_runner_service` sinh ra, nên khi quản trị viên chạy một yêu cầu kiểm tra khôi phục thật, phép kiểm đó sẽ lỗi; chưa sửa (ngoài phạm vi).

**Chưa kiểm**: hiển thị nhãn trong email thật (chỉ kiểm giá trị `job_name` ở test); các màn hình khác ngoài Backup Console (đã `grep`: không còn "trên MinIO"/"kết nối MinIO"/"MinIO/S3" ở `frontend/src`, `frontend/tests`, `backend/app/services/backup_service.py`, `backend/app/schemas`, `backend/tests`); chế độ tối và khổ hẹp của form sau khi đổi nhãn (hai test e2e có sẵn về việc này `:957`, `:994` đều qua).

### Slice 4 - Công cụ chuyển dữ liệu (ĐÃ BỎ, xem 9.0)

Production không có tệp nào (0 object tệp; `hrms-backup` chỉ có 3 bản sao lưu thử), nên không có gì để chép. Nếu kiểm kê ngay trước cutover thấy bucket tệp có object: **dừng và quyết định**. Với dữ liệu nhỏ, cách nhanh nhất là tải lại bằng giao diện hoặc import. Chỉ viết công cụ chép khi số lượng đủ lớn (thuật toán đã nghĩ sẵn: liệt kê nguồn; bỏ qua nếu đích đã có cùng kích thước; đọc streaming và ghi sang đích cùng tên và `content_type`; đối chiếu `sha256`; không bao giờ xóa).

### Slice 5 - CI và chuỗi cung ứng image (DỜI sang Slice 9, tùy chọn, xem 9.0)

CI **không** chặn cutover và vẫn chạy với MinIO. CI cần một S3 sống vì `TestClient` chạy `lifespan` và `ensure_bucket()` (đã kiểm ở bản rút gọn), nên khi làm thì phải thay bằng Garage chứ không thể chỉ xóa service. Nội dung công việc nằm ở Slice 9. Chuỗi cung ứng: production kéo trực tiếp từ Docker Hub theo digest; bản mirror ghcr (đã làm ở Slice 0) là dự phòng, không cần token chỉ đọc (U16).

### Slice 6 - Compose production và gỡ `mc`

**Việc làm** (cho `docker-compose.lan.yml` và `docker-compose.prod.yml`, theo D6)
- Thêm service `garage` và volume `garage_meta`, `garage_data` theo mẫu `docker-compose.yml`. Khác ở production: `restart: always`; `GARAGE_RPC_SECRET` và `GARAGE_ADMIN_TOKEN` dùng `${VAR:?...}` (bắt buộc đặt, không có giá trị mặc định); image ghim digest.
- **Truyền `MINIO_REGION` và `BACKUP_STORAGE_REGION`** cho `backend`, `celery_worker`, `celery_beat`. Hai file này liệt kê từng biến môi trường (không dùng `env_file`) và hiện **không có** hai biến này (đã `grep`); thiếu chúng thì backend không khởi động được với Garage (Slice 1, 2).
- Đổi `depends_on: minio` thành `garage` (ở LAN: `backend`, `celery_worker`, `celery_beat`).
- Đưa `minio` vào profile `legacy-minio` (còn dùng cho quay lui).
- Gỡ `backup_scheduler` khỏi cả hai file (nó cũng `depends_on: minio`), xóa `docker/backup/Dockerfile`, `scripts/backup_minio.sh`, `scripts/backup-entrypoint.sh`, `scripts/backup_db.sh`, và bước build image backup trong `ci.yml` (D3: không chạy trên production, không build được vì `dl.min.io` trả 410).
- Ghi chú trong `.env.example` (mục Garage đã có từ Slice 2): production phải đặt `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN` ngẫu nhiên riêng.

**Kiểm chứng (cổng)**
- `docker compose -f <từng file> config` hợp lệ với một `.env` mẫu đủ biến; so `config` của `backend` giữa LAN và dev để chắc `MINIO_REGION` và `BACKUP_STORAGE_REGION` đều có mặt.
- `grep` không còn `backup_scheduler`, `minio/mc`, `dl.min.io` trong compose, CI và Dockerfile.
- **Không khởi động trên production ở slice này.**

**Rollback**: `git revert`.

### Slice 7 - Diễn tập cutover trên dev với bản sao production (ĐÃ BỎ, xem 9.0)

Không có bước chép dữ liệu để diễn tập; Garage, bootstrap, backend, Backup Console, sao lưu, khôi phục và khởi động lại đã chạy thật ở Slice 2. Phần còn lại khác dev (tên file compose, tên bucket production) được kiểm tĩnh bằng `docker compose config` ở Slice 6.

### Slice 8 - Cutover production (rút gọn)

**Điều kiện tiên quyết**: Slice 3 và 6 đạt cổng và đã `git pull` trên production; kiểm kê lại cho **0 object tệp**; bản sao lưu DB gần nhất `success` (khuyến nghị, vì rất rẻ).

**Việc làm**: thực hiện runbook mục 10 (khoảng 15 phút, gián đoạn khoảng 1-2 phút).

**Kiểm chứng (cổng)**: checklist 10.3 PASS; đêm đầu: sao lưu theo lịch 02:00 (`db`) và 03:00 (`object_storage`) thành công.

**Rollback**: 10.4.

### Slice 9 - Dọn dẹp sau cutover

**Điều kiện**: sao lưu theo lịch đêm đầu tiên thành công cho cả `db` và `object_storage` trên Garage (D4 đã chốt, xem 9.0).

**Việc làm**
- Gỡ container, volume và image MinIO khỏi máy chủ và khỏi compose. Giữ bản nén ở Slice 0 ngoài thư mục repo cho đến khi chủ hệ thống cho phép xóa.
- Viết lại `scripts/restore_procedure.md` bằng SDK Python và **làm theo đúng từ đầu đến cuối** trên dev (khôi phục dump DB từ Garage và tải tệp), để chứng minh tài liệu chạy được.
- Cập nhật tài liệu vận hành: `docs/deploy_noi_bo_lan_ubuntu_26_04.md`, `docs/production_deploy_ubuntu_26_04.md`, `docs/production_go_live_runbook.md`, `docs/TECHSTACK.md`, `docs/FEATURES.md`, `README.md`. Với các `plan_*.md` lịch sử chỉ thêm một dòng ghi chú trỏ sang tài liệu này.
- Giám sát cơ bản: dung lượng đĩa của `garage_data`, `garage health`.
- **(Tùy chọn, làm sau được)** CI: thay service `minio` (`ci.yml:45-58`) bằng Garage khởi động bằng `docker run` **sau bước checkout** (service chạy trước checkout nên không gắn được `garage.toml` từ repo; `--health-cmd` làm job hỏng trên image không có shell; `command` phải bắt đầu bằng `/garage`; xem U12), kèm bước chờ sẵn sàng và bootstrap; đổi `MINIO_ENDPOINT` (`ci.yml:81, 93, 105`), thêm khóa và `MINIO_REGION=garage`.

**Kiểm chứng**: `docker ps -a` và `docker volume ls` không còn tài nguyên MinIO; `grep` không còn `mc `, `dl.min.io`, `minio/mc` ngoài tài liệu lịch sử; `restore_procedure.md` chạy được từ đầu đến cuối; nếu làm CI thì workflow xanh (người vận hành xác nhận, máy dev không có `gh`).

### Slice 10 (tùy chọn) - Đổi tên biến `MINIO_*` thành `S3_*`

Làm riêng sau khi hệ thống ổn định: thêm biến mới với dự phòng đọc biến cũ, đổi dần compose/CI/tài liệu, rồi gỡ biến cũ ở một đợt sau. Có thể gộp việc gom 4 chỗ tạo client vào một `build_s3_client` (hoãn từ Slice 3; hành vi đã có test ở `backend/tests/test_s3_client_region.py`) và thêm `checks["storage"]`. Không thuộc phạm vi cutover.

## 10. Runbook cutover production (bản rút gọn)

Chạy trong `/opt/hrms/HRMS` với `docker-compose.lan.yml`. Các lệnh về Garage, bootstrap, backend và Backup Console đã chạy thật ở dev (Slice 2); phần khác biệt production (tên file compose, tên bucket) được kiểm tĩnh bằng `docker compose config` ở Slice 6. Không có bước chép dữ liệu (production không có tệp nào, xem 9.0). Không cần cửa sổ bảo trì riêng: gián đoạn chỉ là lần khởi động lại `backend` và `celery_*` (khoảng 1-2 phút); nên làm ngoài giờ làm việc.

### 10.1. Chuẩn bị (hệ thống còn chạy, chưa ảnh hưởng người dùng)

1. `git pull origin master` (nhớ: nhánh là `master`, không phải `main`).
2. **Kiểm kê (Phụ lục D)** và ghi lại số object của bucket tệp. Phải là **0**. Nếu lớn hơn 0: dừng, quyết định (tải lại bằng giao diện hoặc import, hoặc chép tay); không tiếp tục theo runbook này.
3. Backup Console: ▶ sao lưu PostgreSQL và xác nhận `success`. (Khuyến nghị, vì rất rẻ.)
4. Sao lưu `.env` hiện tại ra ngoài thư mục repo với quyền `600`. Thêm vào `.env`: `GARAGE_RPC_SECRET` và `GARAGE_ADMIN_TOKEN` (sinh bằng `openssl rand -hex 32`); `chmod 600 .env`.
5. Bật Garage song song với MinIO: `docker compose -f docker-compose.lan.yml up -d garage`; chờ `healthy`.
6. Bootstrap, lấy khóa vào tệp tạm, **chưa động vào khóa cũ trong `.env`**:
   ```bash
   (umask 077; COMPOSE_FILE=docker-compose.lan.yml MINIO_BUCKET=hrms-attachments-prod bash scripts/garage_bootstrap.sh > /tmp/garage_keys.env)
   wc -l /tmp/garage_keys.env      # phải là 4 dòng
   ```

### 10.2. Cắt chuyển (gián đoạn khoảng 1-2 phút)

1. Sửa `.env` (không in giá trị bí mật ra màn hình): đặt `MINIO_ENDPOINT=garage:3900`, `MINIO_BUCKET=hrms-attachments-prod`, `MINIO_REGION=garage`, `MINIO_SECURE=false`, `BACKUP_STORAGE_ENDPOINT=garage:3900`, `BACKUP_STORAGE_REGION=garage`, `BACKUP_STORAGE_SECURE=false`; xóa 4 dòng khóa cũ (`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `BACKUP_STORAGE_ACCESS_KEY`, `BACKUP_STORAGE_SECRET_KEY`) rồi nối nội dung `/tmp/garage_keys.env`; sau đó `shred -u /tmp/garage_keys.env`. Lưu ý: ở compose LAN, MinIO đọc tài khoản gốc từ chính `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`, nên sau bước này `.env` không còn dùng được cho MinIO; quay lui (10.4) vì vậy phải trả `.env` bản cũ.
2. Sửa cấu hình sao lưu **trong DB** (hoặc bằng form ở mục 7.2):
   ```sql
   update backup_configs
      set source_endpoint = 'garage:3900',
          source_bucket   = 'hrms-attachments-prod'
    where kind = 'object_storage'
      and source_endpoint = 'minio:9000'
      and source_bucket   = 'hrms-attachments-dev';
   select kind, source_endpoint, source_bucket, target_endpoint, target_bucket from backup_configs order by kind;
   ```
3. Khởi động lại: `docker compose -f docker-compose.lan.yml up -d --force-recreate --no-deps backend celery_worker celery_beat`.
4. Dừng MinIO và ngăn nó tự bật lại sau khởi động máy: `docker compose -f docker-compose.lan.yml stop minio` rồi `docker update --restart=no <container_minio>`. **Chưa xóa** container và volume.

### 10.3. Checklist sau cutover

1. `docker compose -f docker-compose.lan.yml ps`: `garage`, `backend`, `celery_*` chạy và healthy.
2. `GET /health`: `database`, `redis`, `minio` đều `ok` (kiểm cả bucket `hrms-attachments-prod`, nên `ok` là bằng chứng `MINIO_BUCKET` đã nạp đúng).
3. Trình duyệt thật (luồng 8.1): tải lên một tệp, mở bằng nút **Xem file**, xóa. Nút "Tải xuống" chỉ kiểm sau khi lỗi `401` của nó đã được sửa (xem kết quả Slice 2, phát hiện 4).
4. Backup Console: "Kiểm tra đích sao lưu" Thành công cho cả hai dòng; ▶ sao lưu DB và kho tệp đều `success`; `backup_jobs` có `artifact_bucket = hrms-backup`.
5. `select` từ `backup_configs` đúng như 10.2 bước 2 (**cả `source_endpoint` lẫn `source_bucket`**).
6. Log `backend` không có `S3Error`/`Traceback` bất thường trong 15 phút đầu.

### 10.4. Quay lui

Điều kiện kích hoạt: bất kỳ mục nào của 10.3 FAIL mà không sửa được nhanh.

1. Dừng `backend`, `celery_worker`, `celery_beat`.
2. Trả `.env` về bản đã sao lưu ở 10.1 bước 4; trả `backup_configs.source_endpoint` về `minio:9000` và `source_bucket` về `hrms-attachments-dev`.
3. `docker compose -f docker-compose.lan.yml --profile legacy-minio up -d minio`; khởi động lại ba dịch vụ; chạy lại 10.3 mục 1-4 với MinIO.
4. Tệp nào người dùng tải lên Garage sau cutover sẽ không có ở MinIO: theo tiền đề ở 9.0 thì tải lại hoặc chấp nhận mất (nếu cần giữ thì chép tay trước bước 1).

Quay lui chỉ dùng được khi container và volume MinIO còn nguyên, nên không xóa chúng trước Slice 9.

## 11. Rủi ro và đường lui

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | Garage không tương thích một hành vi ứng dụng cần | Cao | Slice 1 là cổng go/no-go; dự phòng Silo |
| R2 | Quên cập nhật `backup_configs.source_endpoint` trong DB | Cao | Bước SQL cụ thể trong 10.2; checklist 10.4 mục 5; nhãn lỗi rõ ở Backup Console |
| R3 | Backend không khởi động vì `ensure_bucket()` (bucket chưa có/thiếu quyền) hoặc vì thiếu `region` | Cao | Bootstrap trước khi khởi động dịch vụ; compose production truyền `region` (Slice 6); checklist 10.3 |
| R4 | Hỏng/mất dữ liệu Garage khi mất điện | Trung bình | `sqlite` + `fsync` + snapshot `6h` (chu kỳ tối thiểu 10 phút, U11); snapshot nằm cùng volume với DB nên vẫn cần sao lưu ngoài máy (D2) |
| R5 | Sao lưu và dữ liệu thật nằm cùng một kho, cùng một ổ đĩa, và **hiện chưa có nơi nào ngoài máy production** (xác nhận 2026-10-30) | Cao | **Chủ hệ thống đã chấp nhận rủi ro khi cutover** (mục 12.3). Vẫn nên có ít nhất một bản ngoài máy (D2); không giải quyết trong đợt này |
| R6 | Mất dữ liệu tệp khi cutover | Rất thấp (production có 0 tệp, kiểm kê 2026-10-30; dữ liệu còn lại khôi phục được bằng import) | Kiểm kê lại ngay trước cutover; nếu có tệp thì dừng và quyết định; container và volume MinIO cũ không bị xóa cho tới Slice 9 |
| R7 | Image Garage biến mất khỏi registry công khai | Trung bình | Mirror lên ghcr, ghim digest (5.10) |
| R8 | Lộ khóa truy cập | Trung bình | Khóa chỉ in một lần ra terminal; `.env` quyền `600`; không đưa khóa lên dòng lệnh script |
| R9 | CI không khởi động được Garage | Thấp (không chặn cutover) | CI vẫn dùng MinIO cho tới khi làm bước tùy chọn ở Slice 9; khi làm: `docker run` sau checkout (U12), chạy thử trên nhánh trước khi gộp |
| R10 | Gián đoạn dịch vụ lâu hơn dự kiến | Thấp | Garage và bootstrap chạy trước khi động vào ứng dụng; gián đoạn chỉ là lần khởi động lại `backend` và `celery_*`; có quay lui 10.4 |
| R11 | AGPLv3 của Garage | Thấp | Dùng nội bộ, không sửa mã; (không phải tư vấn pháp lý, cần chốt nếu có phân phối lại) |
| R12 | Test hạ tầng làm hỏng DB bản sao production | Trung bình | Luôn chạy test trên bản clone DB (mục 9) |
| R13 | Đổi tên bucket cùng lúc cutover làm tăng số điểm phải đúng (`MINIO_BUCKET`, `backup_configs.source_bucket`, bucket mới trong Garage, quyền của khóa `hrms-app`) | Thấp (bucket trống) | Một SQL cập nhật cả endpoint lẫn bucket; checklist 10.3 mục 5 |

## 12. Điểm chưa xác minh và quyết định cần chốt

### 12.1. Phải xác minh trong Slice 1 (chưa có bằng chứng)

| # | Nội dung |
|---|---|
| U1 | `garage server --single-node` có tự tạo layout mà không cần `--default-bucket`; dung lượng layout mặc định |
| U2 | Healthcheck `["CMD", "/garage", "health", "-q"]` chạy được trong image `FROM scratch` dưới compose (và thoát khác 0 khi chưa sẵn sàng); `status` đã bị loại, xem 5.8 |
| U3 | Lệnh `garage bucket info`, `garage key info` tồn tại và có mã thoát phân biệt "có/không" (để bootstrap idempotent) |
| U4 | `garage key allow --create-bucket` tồn tại và đủ để `make_bucket` qua S3 (`backup_runner_service.py:108`, `restore_runner_service.py:373`); tài liệu hướng dẫn nhanh không nói rõ |
| U5 | SDK `minio` tự dò region qua `GetBucketLocation` với `s3_region = "garage"`. Mã nguồn cho thấy **không** (cần `region="garage"`); chờ xác nhận chạy thật |
| U6 | Liệt kê trên 1.000 object và tên có dấu tiếng Việt (tài liệu Garage ghi có trường hợp đặc biệt với `encoding-type=url`) |
| U7 | Multipart 12 MiB và `sha256` khớp |
| U8 | Bind `0.0.0.0` (phác thảo ở Phụ lục A) so với `[::]` trong mạng bridge của Docker |
| U9 | Quyền ghi lên volume. Cấu hình image cho thấy tiến trình chạy bằng root (không có `User`), nên nhiều khả năng không vướng; vẫn cần xác nhận khi chạy thật |
| U10 | Độ trễ khi bật `metadata_fsync` và `data_fsync` |
| U11 | `metadata_auto_snapshot_interval` có áp dụng cho `sqlite` **(đã xác minh ở Slice 1: có; tối thiểu 600 giây)** |
| U12 | GitHub Actions có hỗ trợ khóa `command` trong `services` (`ci.yml` đang dùng nhưng tôi tin là không có tác dụng) **Chỉ liên quan CI (tùy chọn, Slice 9).** |
| U13 | `depends_on: condition: service_healthy` hoạt động với healthcheck của Garage |
| U14 | Mã/ngữ nghĩa lỗi khi object hoặc bucket không tồn tại (ứng dụng chỉ bắt `S3Error` chung nên rủi ro thấp) |
| U15 | Mức dùng RAM và CPU khi rảnh và khi sao lưu |
| U16 | Gói mirror trên ghcr là **riêng tư** (xác nhận: không đăng nhập thì `401`) và do token cá nhân đẩy lên, image không có nhãn `org.opencontainers.image.source` nên có thể **chưa được liên kết với repo**. Kiểm tra `GITHUB_TOKEN` trong Actions có kéo được không; nếu không thì kết nối gói với repo (Manage Actions access). Production cần token chỉ đọc để kéo (Slice 5, 8) **Không còn chặn** (bản rút gọn): production kéo thẳng từ Docker Hub theo digest; mirror ghcr chỉ là dự phòng. |
| U17 | `GARAGE_RPC_SECRET` và `GARAGE_ADMIN_TOKEN` có được Garage đọc từ biến môi trường khi `garage.toml` không có `rpc_secret`/`admin_token` (Phụ lục A và compose đang dựa vào điều này; trang cấu hình chỉ thấy liệt kê biến môi trường của log, chưa thấy hai biến này). Nếu không: dùng `rpc_secret_file` hoặc ghi vào file cấu hình quyền 600 |

### 12.1a. Bằng chứng đọc từ mã nguồn Garage v2.5.0 (trước khi chạy, chưa kiểm chứng)

Nguồn: agent nghiên cứu đọc tài liệu và mã nguồn (GitHub mirror, tag `v2.5.0`; một số tệp chỉ lấy được ở nhánh `main-v2`), qua công cụ tóm tắt nên chỉ là chỉ dẫn, **không phải bằng chứng chạy thật**. Trình theo dõi lỗi của Garage chặn truy cập nên không đọc được các issue.

| Mục | Điều mã nguồn cho thấy | Tác động |
|---|---|---|
| U1 | `--single-node` tự tạo layout (zone `dc1`, dung lượng lấy từ ổ đĩa, dự phòng 1 GiB) khi layout chưa có; yêu cầu `replication_factor = 1`. `--default-bucket` tạo khóa với quyền tạo bucket và bucket mặc định, idempotent khi khởi động lại | Không cần bước layout thủ công |
| U2 | `garage health -q` thoát 1 khi cụm không sẵn sàng; `garage status` thoát 0 khi RPC chạy được. Admin API `GET /health` không cần xác thực nhưng cần curl nên không chạy được trong image | Đổi healthcheck sang `health -q` |
| U3 | `bucket info`/`key info` với đối tượng không tồn tại thoát 1; `bucket create` và `key create` **không** idempotent (`key create` luôn sinh khóa mới); `key info` khớp theo tiền tố ID hoặc tên chính xác (không phân biệt hoa thường); `bucket allow`, `key allow` idempotent | Phụ lục B giữ nguyên mẫu `info \|\| create`; chỉ trùng khóa nếu đã có hai khóa cùng tên |
| U4 | `CreateBucket` cần cờ cấp khóa `allow_create_bucket` (`key allow --create-bucket`), nếu không trả 403; bucket tạo qua S3 chỉ có alias cục bộ; `DeleteBucket` cần owner và bucket rỗng | Xem 5.4 |
| U5 | Chữ ký sai region trả 400 `AuthorizationHeaderMalformed`; `minio-py` không truyền `region` sẽ ký dò cho `us-east-1` và không thử lại | Xem 5.7: truyền `region="garage"` |
| U8 | Tài liệu không nói gì về `[::]` so với `0.0.0.0` trong mạng bridge; ví dụ quick-start dùng `[::]`. Chỉ suy luận: nếu kernel tắt IPv6 thì `[::]` có thể lỗi | Phụ lục A giữ `0.0.0.0`; spike xác nhận |
| U9 | Dockerfile gốc `FROM scratch`, không có `USER`/`VOLUME`/`HEALTHCHECK`; image đã phát hành nhiều khả năng chạy root (suy luận, chưa kiểm image) | Spike xem quyền volume |
| U11 | Snapshot hoạt động với sqlite (`VACUUM INTO`), mặc định ở `<metadata_dir>/snapshots`, giữ 2 bản gần nhất, mỗi bản là bản sao đầy đủ | Snapshot nằm **cùng volume** với DB nên không chống được mất volume; volume metadata cần chỗ cho khoảng 3 bản. Đã xác nhận bằng chạy thật; chu kỳ tối thiểu 600 giây |
| U12 | `command` và `entrypoint` có trong `services`; service khởi động trước checkout; không gắn được tệp từ repo; `--health-cmd` làm job hỏng; `command` phải bắt đầu bằng `/garage` | CI (Slice 9, tùy chọn) dùng `docker run` sau checkout |
| U14 | Thiếu object: 404 `NoSuchKey`; thiếu bucket: 404 `NoSuchBucket`; bucket có sẵn nhưng khóa thiếu quyền: 403 `AccessDenied` (`bucket_exists` ném lại lỗi này thay vì trả False) | Khớp ứng dụng chỉ bắt `S3Error` chung |
| X1 | Garage không có giới hạn phần tối thiểu 5 MiB (khác MinIO); `ListObjectsV2` mã hóa `encoding-type=url`, tài liệu Garage tự cảnh báo "có thể có lỗi mã hóa"; `minio-py` qua HTTP gửi SHA-256 thật của nội dung (issue #1196 liên quan, chưa đọc được trạng thái) | Probe thử tên có `+ % & ? '`, multipart 12 MiB, 1.050 object |

**Đã xác minh phía ứng dụng**: ứng dụng chỉ gọi 7 hàm (`put_object`, `get_object`, `stat_object`, `list_objects`, `remove_object`, `bucket_exists`, `make_bucket`); không dùng `remove_objects`, presigned URL, tagging, policy hay versioning, nên các endpoint Garage trả 501 không ảnh hưởng.

### 12.2. Quyết định cần chốt trước Slice 0

| # | Câu hỏi | Đề xuất |
|---|---|---|
| D1 | Cửa sổ bảo trì cho cutover | **Không cần riêng** (bản rút gọn, 9.0): khởi động lại `backend` khoảng 1-2 phút, làm ngoài giờ làm việc |
| D2 | Đích sao lưu ngoài máy (offsite) | Cần quyết định riêng; ít nhất sao chép định kỳ bucket `hrms-backup` sang máy khác |
| D3 | Gỡ image/script sao lưu cũ dùng `mc` | **Gỡ** (Backup Console đã thay thế) |
| D4 | Thời gian giữ MinIO cũ ở trạng thái dừng sau cutover | **Đã chốt (2026-10-30): đến khi sao lưu theo lịch đêm đầu tiên thành công trên Garage** (thay cho 7 ngày đã chọn trước đó; bản rút gọn) |
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
| 2026-10-30 | **Cổng Slice 1: GO có điều kiện** (theo đề xuất; chủ hệ thống chấp thuận). Điều kiện: (1) SDK truyền `region="garage"`; (2) bucket do bootstrap tạo bằng CLI, khóa chỉ có quyền tạo bucket khi cần khôi phục vào bucket chưa có; (3) `metadata_auto_snapshot_interval` từ 10 phút trở lên (giữ `6h`) | Slice 2 làm theo ba điều kiện này; độ chín của Garage v2.5.0 (mới ra vài ngày) tiếp tục là rủi ro theo dõi ở Slice 2 và 7; U2, U10, U17 còn mở một phần, U12 và U16 để Slice 5 |
| 2026-10-30 | **Rút gọn kế hoạch theo tiền đề của chủ hệ thống**: dữ liệu production nhỏ và khôi phục được bằng import (chỉ có Phòng/ban, Chức danh, Vị trí, 4 nhân viên thử). Bỏ Slice 4 và 7; dời CI (Slice 5) sang Slice 9 và để tùy chọn; bỏ snapshot MinIO, bước chép dữ liệu và cửa sổ bảo trì ở cutover; rút D4 | Chi tiết ở 9.0. Điều kiện: kiểm kê lại ngay trước cutover phải cho 0 tệp. Tìm thấy thêm: compose production chưa truyền `region` (Slice 6 phải làm); CI vẫn cần S3 sống nên không thể chỉ xóa service MinIO |
| 2026-10-30 | **D4 chốt: giữ MinIO cũ ở trạng thái dừng cho đến khi sao lưu theo lịch đêm đầu tiên (02:00 `db`, 03:00 `object_storage`) thành công trên Garage, rồi gỡ** (thay cho 7 ngày đã chọn trước đó) | Slice 9 bắt đầu sau đêm đầu tiên thay vì ngày thứ 7; đường lui (10.4) vẫn còn nguyên cho tới lúc đó |
| 2026-10-30 | *(Điều chỉnh theo bằng chứng, không phải quyết định mới của chủ hệ thống)* Kéo tham số `region` từ Slice 3 sang Slice 2; cấp quyền tạo bucket cho **cả hai** khóa thay vì chỉ `hrms-backup` | Cả hai đều do bằng chứng chạy thật: backend không khởi động được với Garage nếu thiếu `region` (Slice 1, Slice 2); khôi phục kho tệp tạo bucket đích bằng khóa ứng dụng (`AccessDenied` khi thiếu quyền). Cần chủ hệ thống xem lại nếu muốn hạn chế quyền tạo bucket của khóa ứng dụng |

## 13. Tiêu chí hoàn thành

- Production chạy trên Garage: tải lên, xem, xóa, sao lưu DB, sao lưu kho tệp hoạt động, kiểm chứng ở trình duyệt thật (checklist 10.3); khôi phục kho tệp đã được kiểm ở dev (Slice 2) và `restore_procedure.md` mới được làm theo từ đầu đến cuối (Slice 9).
- Kiểm kê ngay trước cutover cho 0 tệp (hoặc đã xử lý theo 10.1 bước 2), biên bản ghi lại.
- Sao lưu theo lịch đêm đầu tiên thành công cho cả `db` và `object_storage` trên Garage.
- Không còn tham chiếu tới `minio/mc`, `dl.min.io`, `backup_scheduler` trong compose, CI, Dockerfile và kịch bản vận hành (Slice 6); MinIO cũ đã được gỡ (Slice 9).
- Tài liệu vận hành cập nhật.
- (Tùy chọn) CI dùng Garage từ image ghim digest, xanh.

## Phụ lục A. Cấu hình Garage đề xuất (phác thảo)

`docker/garage/garage.toml` (không chứa bí mật; `rpc_secret` và `admin_token` lấy từ biến môi trường `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`):

```toml
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"

db_engine = "sqlite"
metadata_fsync = true
data_fsync = true
metadata_auto_snapshot_interval = "6h"   # tối thiểu 10min; nhỏ hơn thì Garage không khởi động được (xem "Kết quả Slice 1")

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
      test: ["CMD", "/garage", "health", "-q"]      # U2 (không dùng `status`, xem 5.8)
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
G key allow --create-bucket hrms-app                                                 # U4: khôi phục kho tệp tạo bucket đích bằng khóa ứng dụng
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
