# Kế hoạch 15.6 - Admin Backup & Restore Console

Ngày lập: 2026-07-13

## 1. Mục tiêu

Phát triển tính năng cho phép Admin quản trị việc sao lưu và khôi phục:

- Database PostgreSQL.
- File upload đang lưu trên object storage tương thích S3/MinIO.
- Lịch chạy backup, thời gian giữ backup, người nhận thông báo.
- Trạng thái job backup/restore, artifact đã tạo, lỗi gần nhất và lịch sử thao tác.

Tính năng này phải dựa trên cơ chế backup hiện có trong source, nhưng cần bổ sung lớp cấu hình, API, UI, RBAC, audit log và quy trình restore an toàn. Không được biến UI thành nút "ghi đè production" trực tiếp trong phiên bản đầu.

## 2. Bằng chứng hiện trạng

Kết luận dưới đây đã được đối chiếu trực tiếp từ source và docs hiện tại.

### 2.1. Backup hiện đang là vận hành bằng Docker/env/script

- `.env.example:75-92` có các biến `BACKUP_STORAGE_*`, `BACKUP_RETENTION_DAYS`, `DB_BACKUP_CRON`, `MINIO_BACKUP_CRON`, `SOURCE_STORAGE_*`, `BACKUP_NOTIFY_EMAILS`.
- `docker-compose.prod.yml:122-170` khai báo service `backup_scheduler`.
- `docker-compose.lan.yml:142-196` khai báo service `backup_scheduler` trong profile `backup`.
- `scripts/backup-entrypoint.sh:59-70` tạo crontab tĩnh cho `supercronic` từ env rồi chạy `backup_db.sh` và `backup_minio.sh`.
- `scripts/backup_db.sh:61-85` chạy `pg_dump | gzip`, sau đó có thể đẩy file backup lên bucket đích bằng `mc cp`.
- `scripts/backup_minio.sh:64-101` mirror object storage nguồn sang snapshot `files-YYYYMMDD`, cleanup retention và gửi notification.
- `scripts/verify_backup.sh` và docs deploy/runbook mô tả quy trình kiểm tra backup.

### 2.2. Chưa có API/UI cho Admin cấu hình backup/restore

- `backend/app/api/v1/router.py` chưa include router backup/restore.
- `backend/app/api/v1/endpoints/notifications.py` là mẫu gần nhất cho cấu hình vận hành qua UI, nhưng chỉ phục vụ notification và dùng `settings:view`/`settings:edit`.
- `backend/app/core/rbac_catalog.py` chưa có module `backups` hoặc permission riêng cho backup/restore.
- `backend/app/core/audit_catalog.py` chưa có entity/action riêng cho backup/restore.
- `frontend/src/views/settings/SettingsView.vue` hiện mới là placeholder.
- `frontend/src/router/index.ts` có route `settings` và các route admin/users/roles/audit-logs, nhưng chưa có route backup/restore.
- `frontend/src/composables/usePermissionGate.ts` mirror danh sách module RBAC hiện có, nên khi thêm module `backups` cần cập nhật cả frontend.
- `frontend/src/components/layout/AppMenu.vue` đang là điểm gắn menu admin/settings hiện có.

### 2.3. Restore hiện tại cần giữ tính chất có kiểm soát

- Backup DB và object storage là hai artifact/luồng khác nhau, có thể lệch thời điểm.
- `scripts/restore_procedure.md:17-142` mô tả restore hiện tại là quy trình thủ công: dừng service, restore vào DB mới, swap DB name, và mirror snapshot MinIO về bucket live.
- Restore trực tiếp vào production có rủi ro mất dữ liệu. Phiên bản đầu nên chỉ cho phép Admin tạo yêu cầu restore/verify, restore vào DB/bucket mới hoặc staging, sau đó để thao tác swap production thành bước vận hành có người kiểm soát.
- UI phải phân biệt rõ:
  - backup source: DB/object storage đang chạy.
  - backup target: bucket backup lưu artifact.
  - DB dump: file `.sql.gz`.
  - object snapshot: snapshot file upload trong object storage.
  - restore request: yêu cầu khôi phục có trạng thái, audit và xác nhận.

### 2.4. Các seam hiện có có thể tái sử dụng

- Uploaded files đang đi qua `backend/app/core/storage.py` và bucket/object-prefix được cấu hình trong `backend/app/core/config.py`; do đó backup UI nên dùng thuật ngữ "object storage/file upload", không đóng cứng chỉ riêng MinIO.
- Startup hiện có kiểm tra/tạo bucket trong `backend/app/main.py`, nên validation backup target nên theo cùng triết lý: lỗi cấu hình storage phải được báo rõ.
- Notification settings có pattern API/UI tại `backend/app/api/v1/endpoints/notifications.py`, `frontend/src/services/notificationService.ts`, `frontend/src/views/settings/NotificationSettingsView.vue`.
- Audit logs có pattern API/UI tại `backend/app/api/v1/endpoints/audit_logs.py`, `frontend/src/services/auditLogService.ts`, `frontend/src/views/admin/AuditLogView.vue`.
- Backend tests hiện có cho notifications/audit logs là mẫu tốt cho permission, metadata và audit behavior.

## 3. Phạm vi

### 3.1. Trong phạm vi

- Trang Admin xem tổng quan sức khỏe backup.
- Admin xem/cập nhật cấu hình backup DB và object storage:
  - Bật/tắt backup từng loại.
  - Cron schedule.
  - Retention days.
  - Bucket/path đích.
  - Danh sách email thông báo.
  - Trạng thái kết nối tới backup storage.
- Admin chạy backup thủ công.
- Admin xem lịch sử job backup/restore.
- Admin xem danh sách artifact backup.
- Admin tạo restore request theo chế độ an toàn:
  - Verify only.
  - Restore vào DB/bucket mới.
  - Đánh dấu "production swap cần thao tác vận hành" nếu cần.
- RBAC, audit log và notification cho thao tác backup/restore.
- Cập nhật docs vận hành sau khi có tính năng.

### 3.2. Ngoài phạm vi cho bản đầu

- Một nút restore ghi đè trực tiếp production.
- Hiển thị secret đầy đủ trên UI.
- Thay thế toàn bộ object storage hiện tại.
- Cross-region replication, versioning nâng cao, immutable backup/WORM.
- Quản lý credential cloud phức tạp từ UI nếu chưa có cơ chế mã hóa secret.

## 4. Quyết định thiết kế đề xuất

### 4.1. Dùng module quyền riêng `backups`

Không nên dùng chung `settings:view`/`settings:edit` vì backup/restore có mức rủi ro cao hơn cấu hình ứng dụng thông thường.

Đề xuất thêm module:

- `backups:view`: xem tổng quan, lịch sử job, artifact.
- `backups:edit`: cập nhật cấu hình backup.
- `backups:create`: tạo manual backup job và restore request.
- `backups:export`: tải/xuất metadata backup nếu cần.

Lý do không thêm action `restore` ngay: `ACTION_DEFS` hiện là tập action chung cho tất cả module. Nếu thêm `restore`, permission matrix sẽ mở rộng cho mọi module. Ban đầu có thể map thao tác restore request vào `backups:create`, sau này nếu permission engine hỗ trợ action theo module thì tách `backups:restore`.

### 4.2. UI nằm trong khu vực Admin

Route đề xuất:

- `frontend/src/views/admin/BackupRestoreView.vue`
- route: `/admin/backups`
- permission meta: `backups:view`
- menu group: Quản trị hệ thống

Không đặt là trang con của `/settings` nếu yêu cầu là Admin quản trị backup/restore. Trang `/settings` có thể thêm link nhanh nếu cần, nhưng route chính nên nằm trong Admin.

### 4.3. Cấu hình runtime không chỉ dựa vào env

Hiện tại `backup_scheduler` đọc env một lần, tạo crontab tĩnh và chạy `supercronic`. Nếu Admin cập nhật UI, thay đổi sẽ không có tác dụng thật nếu scheduler vẫn chỉ đọc env khi container start.

Đề xuất:

- Env hiện tại tiếp tục là bootstrap/fallback.
- Khi hệ thống khởi động lần đầu, seed cấu hình backup từ env vào DB nếu chưa có bản ghi.
- Tạo runner đọc cấu hình từ DB và ghi trạng thái job vào DB.
- Runner chạy trong image/service có đủ tool `pg_dump`, `mc`, `gzip`.
- UI cập nhật DB config; runner đọc config mới mà không cần sửa compose mỗi lần.

### 4.4. Secret handling cho production nội bộ LAN

Bối cảnh đã chốt: hệ thống production chỉ chạy trong mạng LAN local, không public Internet. Điều này giảm bề mặt tấn công từ bên ngoài, nhưng không biến secret thành dữ liệu thường. Rủi ro còn lại vẫn gồm: user nội bộ tò mò/sai quyền, máy trạm nhiễm mã độc, log/screenshot bị chia sẻ, file `.env` bị copy nhầm, hoặc backup bucket bị dùng sai quyền.

Đề xuất v1 cho LAN local:

- Không cho Admin nhập/sửa secret trực tiếp trên UI.
- Không lưu raw secret trong DB.
- Giữ các secret vận hành trong `.env` trên server nội bộ:
  - `POSTGRES_PASSWORD`
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `BACKUP_STORAGE_ACCESS_KEY`
  - `BACKUP_STORAGE_SECRET_KEY`
  - `SOURCE_STORAGE_ACCESS_KEY`
  - `SOURCE_STORAGE_SECRET_KEY`
- UI chỉ quản lý các cấu hình không phải secret:
  - bật/tắt backup.
  - cron schedule.
  - retention days.
  - bucket/prefix.
  - danh sách email thông báo.
  - endpoint nội bộ nếu cần cho Admin xem/sửa.
  - trạng thái `configured/missing`, `last_validated_at`, `last_validation_error` đã rút gọn.
- UI không trả về access key/secret key, kể cả dạng mask đầy đủ. Nếu cần hiển thị dấu hiệu nhận diện, chỉ hiển thị `secret_source=env` và trạng thái đã cấu hình.
- Audit log không ghi giá trị secret cũ/mới. Chỉ ghi tên field thay đổi và metadata an toàn, ví dụ `backup credential source changed`, `backup target validation requested`.

Lý do chọn hướng này:

- Phù hợp với `docker-compose.lan.yml`, nơi các service hiện vẫn nhận secret qua environment.
- Đơn giản hơn so với việc thêm Vault/KMS hoặc cơ chế mã hóa field trong DB.
- Dễ vận hành trong LAN: người quản trị server cập nhật `.env`, sau đó restart đúng service cần thiết.
- Giảm rủi ro secret bị lộ qua frontend, API response, audit log hoặc database dump.

Yêu cầu vận hành kèm theo:

- File `.env` trên server production LAN phải thuộc quyền user deploy/admin và nên đặt permission chặt, ví dụ `chmod 600 .env`.
- Không commit `.env` vào git; chỉ commit `.env.example`.
- Backup offline của `.env` nên được lưu cùng tài liệu bàn giao vận hành, nhưng không đặt chung bucket public/chia sẻ rộng.
- Không dùng credential root MinIO cho backup nếu có thể. Nên tạo credential riêng:
  - source credential chỉ cần quyền đọc bucket upload.
  - backup target credential cần quyền ghi/xóa theo retention trên bucket backup.
- Với LAN kín, `MINIO_SECURE=false` hoặc `BACKUP_STORAGE_SECURE=false` có thể chấp nhận nếu object storage nằm cùng Docker network hoặc cùng mạng nội bộ tin cậy. Nếu backup target nằm qua switch/VLAN khác hoặc có TLS nội bộ sẵn, vẫn ưu tiên `*_SECURE=true`.

Nếu sau này bắt buộc cho Admin sửa credential từ UI:

- Thêm encrypted secret fields trong DB, mã hóa bằng `ENCRYPTION_KEY` từ env.
- Không bao giờ trả raw secret về frontend.
- Khi update secret, chỉ cho phép ghi đè, không cho đọc lại.
- Audit chỉ ghi hành động và người thực hiện, không ghi giá trị.
- Cần test riêng để chứng minh API response, audit log và job log không chứa secret.

## 5. Mô hình dữ liệu đề xuất

### 5.1. `backup_configs`

Lưu cấu hình hiện hành theo từng loại backup.

Trường chính:

- `id`
- `kind`: `db` hoặc `object_storage`
- `enabled`
- `cron_expression`
- `retention_days`
- `target_bucket`
- `target_prefix`
- `source_bucket` cho object storage
- `notify_emails`
- `secret_source`: ví dụ `env`
- `last_validated_at`
- `last_validation_status`
- `last_validation_error`
- `created_at`, `updated_at`
- `created_by_id`, `updated_by_id`

### 5.2. `backup_jobs`

Lưu mỗi lần backup, validate, verify hoặc restore runner xử lý.

Trường chính:

- `id`
- `kind`: `db`, `object_storage`, `validate_target`, `restore_db`, `restore_object_storage`
- `trigger`: `schedule`, `manual`, `restore_request`, `system`
- `status`: `queued`, `running`, `success`, `failed`, `cancelled`
- `artifact_key`
- `artifact_bucket`
- `artifact_size_bytes`
- `object_count`
- `started_at`, `finished_at`
- `error_summary`
- `log_excerpt`
- `created_by_id`
- `created_at`, `updated_at`

### 5.3. `restore_requests`

Lưu yêu cầu khôi phục có audit và trạng thái riêng.

Trường chính:

- `id`
- `kind`: `db`, `object_storage`, `full`
- `db_artifact_key`
- `object_snapshot_key`
- `mode`: `verify_only`, `restore_to_new_target`, `production_swap_pending_operator`
- `target_db_name`
- `target_bucket`
- `status`: `draft`, `queued`, `running`, `verified`, `restored`, `failed`, `cancelled`
- `requested_by_id`
- `approved_by_id`
- `confirmation_text`
- `notes`
- `created_at`, `updated_at`

## 6. Backend API đề xuất

Thêm router mới:

- `backend/app/api/v1/endpoints/backups.py`
- include trong `backend/app/api/v1/router.py`

Endpoint đề xuất:

- `GET /api/v1/backups/meta`
  - Trả permission, enum, cấu hình giới hạn UI.
- `GET /api/v1/backups/overview`
  - Tổng quan last success, last failure, next run, storage validation status.
- `GET /api/v1/backups/config`
  - Xem cấu hình backup đã mask secret.
- `PUT /api/v1/backups/config/{kind}`
  - Cập nhật cấu hình DB/object storage.
- `POST /api/v1/backups/validate-target`
  - Tạo job validate kết nối backup storage.
- `POST /api/v1/backups/jobs`
  - Tạo manual backup job.
- `GET /api/v1/backups/jobs`
  - Lịch sử job, filter theo kind/status/date.
- `GET /api/v1/backups/snapshots`
  - Liệt kê DB dumps/object snapshots có thể restore.
- `POST /api/v1/backups/restore-requests`
  - Tạo yêu cầu restore.
- `GET /api/v1/backups/restore-requests`
  - Lịch sử restore request.
- `POST /api/v1/backups/restore-requests/{id}/approve`
  - Tùy chọn v1.5/v2 nếu muốn tách người tạo và người duyệt.

Tất cả endpoint phải:

- Dùng `require_permission`.
- Log audit cho thao tác thay đổi config, manual job, validate, restore request.
- Không trả secret raw về client.
- Validate cron expression, retention, bucket/path, notify email.

## 7. Backup runner đề xuất

### 7.1. Hướng triển khai khuyến nghị cho v1

Tạo DB-backed backup runner trên Celery queue `backups`, dùng `celery_beat` làm bộ kích hoạt lịch.

Runner mới:

- Đọc `backup_configs` từ DB.
- Mỗi phút, `celery_beat` gọi task dispatcher ngắn để kiểm tra lịch.
- Khi đến lịch, tạo một `backup_set` loại `scheduled_full` gồm job DB và job kho tệp ứng dụng.
- Chạy backup bằng backend runner hiện có:
  - DB: `pg_dump`, gzip, upload artifact lên backup target.
  - Object storage: copy snapshot kho tệp ứng dụng lên backup target.
- Cập nhật `backup_sets.status`, `backup_jobs.status`, artifact, size/object count, lỗi rút gọn.
- Gửi notification bằng service hiện có nếu cấu hình có email.
- `backup_scheduler` script/env cũ chỉ còn là profile legacy dự phòng, không khởi động mặc định trong production/LAN.

Không thêm dependency parse cron mới trong v1. Runner dùng matcher nhỏ cho biểu thức 5 trường đã được validate, hỗ trợ `*`, danh sách, khoảng và bước.

### 7.2. Lý do không chỉ sửa `supercronic`

`supercronic` phù hợp khi lịch nằm trong env/file tĩnh. Khi Admin cấu hình từ UI, cần có:

- Trạng thái job trong DB.
- Manual trigger.
- Validate/restore job.
- Thay đổi schedule không phụ thuộc restart container.

Những yêu cầu này cần runner có state/application logic hơn là crontab tĩnh.

## 8. Restore safety model

Phiên bản đầu không restore ghi đè production trực tiếp.

Quy trình UI đề xuất sau khi bổ sung bộ sao lưu đầy đủ:

1. Nếu khôi phục riêng lẻ, Admin chọn DB dump hoặc object snapshot tương ứng.
2. Nếu khôi phục đầy đủ, Admin chọn một bộ sao lưu đầy đủ đã thành công; bộ này đã liên kết sẵn DB dump và snapshot kho tệp ứng dụng.
3. Hệ thống hiển thị thời điểm, kích thước, source, checksum nếu có.
4. Admin chọn mode:
   - Verify only.
   - Restore to new DB/bucket.
5. Admin nhập confirmation text.
6. Runner tạo restore job và cập nhật `restore_requests`.
7. Khi thành công, UI hiển thị kết quả và hướng dẫn bước vận hành nếu cần swap production.

Cần thêm guardrails:

- Không cho target DB/bucket trùng production trong v1.
- Không log secret vào `log_excerpt`.
- Giới hạn quyền restore request bằng `backups:create`.
- Tất cả thao tác restore request phải có audit log.

## 9. Frontend đề xuất

### 9.1. File/chức năng

- `frontend/src/services/backupService.ts`
- `frontend/src/views/admin/BackupRestoreView.vue`
- Thêm route `/admin/backups` trong `frontend/src/router/index.ts`
- Thêm menu item nếu menu hiện được tạo từ route/meta.

### 9.2. Bố cục UI

Trang Admin Backup & Restore nên là giao diện vận hành gọn, dễ scan:

- Header:
  - Trạng thái tổng quan.
  - Nút "Chạy backup".
  - Nút "Kiểm tra kết nối".
- Tab "Tổng quan":
  - Last DB backup.
  - Last file backup.
  - Last failed job.
  - Next scheduled runs.
- Tab "Cấu hình":
  - Cấu hình DB backup.
  - Cấu hình object storage backup.
  - Retention và email thông báo.
- Tab "Artifacts":
  - Danh sách DB dumps và object snapshots.
  - Filter theo loại, ngày, trạng thái.
- Tab "Jobs":
  - Job history, log excerpt, retry/inspect.
- Tab "Restore":
  - Restore request wizard an toàn.

UI không hiển thị "hướng dẫn sử dụng" dài dòng trong app. Các cảnh báo restore nên ngắn gọn, rõ rủi ro và đúng lúc.

## 10. Audit và notification

### 10.1. Audit

Thêm entity vào `backend/app/core/audit_catalog.py`:

- `backup_config`
- `backup_job`
- `restore_request`

Audit các hành động:

- Cập nhật config.
- Validate target.
- Tạo manual backup.
- Tạo/approve/cancel restore request.
- Restore job thành công/thất bại.

### 10.2. Notification

Hiện đã có `backend/app/services/backup_notification_service.py`, command `backend/app/scripts/send_backup_notification.py` và test `backend/tests/test_backup_notifications.py`. Đề xuất:

- Giữ cơ chế gửi email hiện có cho runner.
- Thêm mapping notification event nếu muốn quản trị template qua UI notification hiện có:
  - `backup_success`
  - `backup_failed`
  - `restore_success`
  - `restore_failed`
- Trong v1 có thể chỉ cấu hình danh sách email tại Backup config, chưa cần đưa vào Notification Template nếu muốn giảm phạm vi.

## 11. Kế hoạch triển khai theo slice TDD

Nguyên tắc: kiểm thử qua API/UI public seam trước, tránh test qua private helper nếu có thể. Các pattern hiện có nên tái sử dụng:

- `backend/tests/test_notifications.py`: permission, metadata, update settings.
- `backend/tests/test_audit_logs.py`: audit log list/filter và permission.
- `backend/tests/test_backup_notifications.py`: format/gửi notification backup.
- `frontend/tests/e2e/settings-permissions.spec.ts`: route/menu permission.
- `frontend/tests/e2e/backend-driven-metadata.spec.ts`: UI metadata-driven filter/select.

### Slice 1 - Nền tảng domain, RBAC, audit

Mục tiêu:

- Thêm module `backups` vào RBAC catalog/seed.
- Thêm audit entities.
- Thêm schemas enum dùng chung.

Kiểm thử:

- Test RBAC seed/catalog có permission `backups:view/edit/create/export`.
- Test endpoint protected mẫu trả 403 khi thiếu permission.
- Test audit catalog có entity mới.

### Slice 2 - Persistence và service cấu hình backup

Mục tiêu:

- Migration tạo `backup_configs`, `backup_jobs`, `restore_requests`.
- Service seed config từ env lần đầu.
- API read-only `GET /backups/config`, `GET /backups/overview`.

Kiểm thử:

- Backend tests qua API, không gọi trực tiếp private function.
- Direct DB check sau migration/seed.
- Test secret được mask và không trả raw secret.

### Slice 3 - UI read-only Backup Center

Mục tiêu:

- Route `/admin/backups`.
- Hiển thị overview/config/job history read-only.
- Permission gate theo `backups:view`.

Kiểm thử:

- `npm run build`.
- Browser-level test:
  - Admin có quyền vào được trang.
  - User không có quyền không thấy/không vào được.
  - Overview render đúng data backend.

### Slice 4 - Cập nhật cấu hình và validate target

Mục tiêu:

- `PUT /backups/config/{kind}`.
- `POST /backups/validate-target`.
- UI form save config, validation state, audit.

Kiểm thử:

- Backend tests validate cron, retention, email, bucket.
- Test audit row sau khi save config.
- Browser-level test save config rồi reload vẫn thấy giá trị mới.
- Runtime check validate target với MinIO dev/LAN nếu môi trường có sẵn.

### Slice 5 - Manual backup và job history

Mục tiêu:

- `POST /backups/jobs` tạo manual backup job.
- Runner xử lý job từ DB.
- Ghi artifact metadata, status, log excerpt.
- UI nút chạy backup và job history realtime/polling.

Kiểm thử:

- Backend/job test với command runner adapter test-safe.
- Runtime check với Docker Compose:
  - Chạy manual DB backup.
  - Xác nhận artifact có trong backup bucket.
  - Chạy manual object storage backup.
  - Xác nhận snapshot/object count.
- Browser-level test nút chạy backup tạo job và UI đổi trạng thái.

### Slice 6 - Restore request và verify/dry-run

Mục tiêu:

- `GET /backups/snapshots`.
- `POST /backups/restore-requests`.
- Runner verify DB dump/object snapshot.
- Restore vào DB/bucket mới, không ghi đè production.
- UI wizard restore.

Kiểm thử:

- Backend tests:
  - Không cho target trùng production.
  - Bắt buộc confirmation text.
  - Reject snapshot không tồn tại.
  - Tạo audit row.
- Runtime check:
  - Verify DB dump thành công.
  - Restore vào DB mới thành công.
  - Verify object snapshot/bucket mới thành công.
- Browser-level test wizard chặn thao tác unsafe và hiển thị kết quả restore request.

### Slice 7 - Tài liệu và hardening vận hành

Mục tiêu:

- Cập nhật docs deploy/runbook để phân biệt:
  - env bootstrap.
  - UI config.
  - restore safe flow.
  - production swap manual.
- Bổ sung runbook khi runner lỗi.
- Bổ sung checklist bảo mật secret/log.

Kiểm thử:

- Review docs với source mới.
- Chạy full backend tests liên quan.
- Chạy frontend build và e2e liên quan.
- Direct runtime check backup/restore trên môi trường dev/LAN nếu có sẵn.

## 12. Rủi ro và câu hỏi cần chốt trước khi code

- "Admin" có nghĩa là superuser/system admin hay mọi user có `settings:edit`? Đề xuất: chỉ user có permission `backups:*`.
- Với production nội bộ LAN, v1 không cho Admin nhập/sửa credential backup storage từ UI. Credential đặt trong `.env` trên server và UI chỉ hiển thị trạng thái đã cấu hình/chưa cấu hình.
- Có bắt buộc restore full DB + file cùng một thời điểm không? Đã chốt: restore full phải đi qua `backup_sets`, không ghép hai snapshot rời. Restore riêng DB hoặc riêng kho tệp vẫn được giữ cho tình huống vận hành đặc biệt.
- Có cần approval 2 người cho restore không? Đề xuất v1.5/v2 nếu hệ thống có yêu cầu kiểm soát nội bộ.
- Runner nên dùng DB polling riêng hay Celery queue `backups`? Đã chốt v1: dùng Celery queue `backups`; `backup_scheduler` cũ chỉ là đường legacy dự phòng.

## 13. Tiêu chí hoàn thành

Tính năng chỉ được coi là xong khi:

- Admin có quyền vào được `/admin/backups`.
- Admin xem được config không chứa secret, trạng thái backup gần nhất, job history và artifact.
- Admin sửa được schedule/retention/notify emails và thay đổi có tác dụng với runner.
- Admin trigger được manual DB backup và object storage backup.
- Admin trigger được bộ sao lưu đầy đủ; DB backup và snapshot kho tệp ứng dụng được chạy nối tiếp trong cùng hàng đợi và cùng `backup_set_id`.
- Artifact backup được ghi vào backup target và hiển thị trong UI.
- Admin tạo được restore request an toàn, tối thiểu verify-only hoặc restore vào target mới; restore full phải chọn một bộ sao lưu đầy đủ đã thành công.
- Tất cả thao tác thay đổi có audit log.
- Secret không bị trả về frontend hoặc ghi vào log excerpt.
- Backend tests, frontend build, browser-level tests và runtime backup/restore checks liên quan đều được chạy và ghi lại kết quả.
