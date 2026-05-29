# Kế hoạch triển khai — 15.4. Lưu trữ file

**Phạm vi:** File backup SOP · File size limit · Retention policy · MinIO TLS  
**Phụ thuộc:** MinIO ✅ · `app/core/storage.py` ✅ · Docker Compose ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §15.4  
**Đặc điểm:** Hạ tầng MinIO và upload/download proxy đã hoàn chỉnh; plan tập trung vào operational gaps

---

## Trạng thái hiện tại

### Đã có (✅)

| Thành phần | Chi tiết |
|---|---|
| MinIO S3-compatible | Docker service, volume persist `minio_data` |
| Env-aware bucket naming | `hrms-attachments-{dev\|stg\|prod}` qua `minio_bucket_name` property |
| Download proxy | `StreamingResponse` qua FastAPI — không expose MinIO URL |
| Upload functions | 6 hàm riêng: employee, contract, template, reward, discipline, certificate |
| Object naming | UUID prefix ngăn path traversal |
| Permission trước download | `require_permission()` trên tất cả download endpoints |
| Health check | MinIO `curl -f .../minio/health/live` trong Docker Compose |
| Bucket auto-create | `ensure_bucket()` khi startup |

### Chưa có (❌)

| Thành phần | Ưu tiên |
|---|---|
| **Backup script PostgreSQL** | 🔴 Critical |
| **Backup script MinIO** | 🔴 Critical |
| **File size limit enforcement** | 🟠 High |
| **File retention / cleanup policy** | 🟡 Medium |
| **MinIO TLS cho production** | 🟡 Medium |
| **Restore procedure document** | 🟠 High |
| **File type whitelist** | 🟡 Medium |

---

## Phạm vi Plan 15.4

### Trong phạm vi

1. **Database backup** — `pg_dump` daily, 90-day retention, upload to S3/MinIO
2. **MinIO backup** — `mc mirror` daily, 90-day retention
3. **Restore procedure** — step-by-step SOP
4. **File size limit** — enforce 50MB max trong upload endpoints
5. **File type whitelist** — chỉ cho phép PDF, XLSX, DOCX, JPG, PNG
6. **Retention policy** — tài liệu hóa, chuẩn bị cleanup script

### Ngoài phạm vi

- Virus scanning (ClamAV) — phase sau khi có yêu cầu compliance
- CDN cho static files
- File versioning (keep multiple versions)
- Cross-region replication

---

## Chi tiết kỹ thuật

### 1. Database Backup (Slice 1 — Critical)

**Script `scripts/backup_db.sh`:**
```bash
#!/bin/bash
set -euo pipefail

# Config
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-hrms}"
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="hrms_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup: $FILENAME"

# Dump + compress
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" "$DB_NAME" \
    | gzip -9 > "$BACKUP_DIR/$FILENAME"

echo "[$(date)] Backup created: $BACKUP_DIR/$FILENAME ($(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1))"

# Upload to MinIO backup bucket (optional)
if command -v mc &>/dev/null; then
    mc cp "$BACKUP_DIR/$FILENAME" "backup/db-backups/$FILENAME"
    echo "[$(date)] Uploaded to backup bucket"
fi

# Delete old backups
find "$BACKUP_DIR" -name "hrms_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Cleaned up backups older than ${RETENTION_DAYS} days"

echo "[$(date)] Backup complete"
```

**Cron job (crontab hoặc Docker scheduled task):**
```bash
# Chạy 02:00 hàng ngày
0 2 * * * /scripts/backup_db.sh >> /logs/backup_db.log 2>&1
```

**Thêm vào `docker-compose.yml` (service backup):**
```yaml
backup:
  image: postgres:16-alpine
  volumes:
    - ./scripts:/scripts:ro
    - backups:/backups
  environment:
    DB_HOST: db
    DB_PASSWORD: ${POSTGRES_PASSWORD}
  depends_on:
    db:
      condition: service_healthy
  command: ["sh", "-c", "crond -f"]
  profiles: ["backup"]    # chạy riêng: docker compose --profile backup up backup
```

---

### 2. MinIO Backup (Slice 1 — Critical)

**Dùng `mc` (MinIO Client):**

**Script `scripts/backup_minio.sh`:**
```bash
#!/bin/bash
set -euo pipefail

SOURCE_ALIAS="${MC_SOURCE_ALIAS:-local}"
SOURCE_BUCKET="${SOURCE_BUCKET:-hrms-attachments-prod}"
DEST_ALIAS="${MC_DEST_ALIAS:-backup}"
DEST_BUCKET="${DEST_BUCKET:-hrms-backup}"
DATE=$(date +%Y%m%d)
LOG_DIR="/logs"

mkdir -p "$LOG_DIR"

echo "[$(date)] Starting MinIO mirror: ${SOURCE_ALIAS}/${SOURCE_BUCKET} → ${DEST_ALIAS}/${DEST_BUCKET}/files-${DATE}/"

# Mirror (copy new/changed objects)
mc mirror \
    --overwrite \
    --preserve \
    "${SOURCE_ALIAS}/${SOURCE_BUCKET}" \
    "${DEST_ALIAS}/${DEST_BUCKET}/files-${DATE}/" \
    2>&1 | tee -a "$LOG_DIR/backup_minio_${DATE}.log"

echo "[$(date)] Mirror complete"

# Cleanup: giữ 90 ngày backup
mc ls "${DEST_ALIAS}/${DEST_BUCKET}/" | awk '{print $NF}' | while read -r dir; do
    dir_date=$(echo "$dir" | grep -oP '\d{8}' | head -1)
    if [ -n "$dir_date" ]; then
        age=$(( ($(date +%s) - $(date -d "$dir_date" +%s)) / 86400 ))
        if [ "$age" -gt 90 ]; then
            mc rm --recursive --force "${DEST_ALIAS}/${DEST_BUCKET}/${dir}"
            echo "[$(date)] Removed old backup: ${dir} (${age} days old)"
        fi
    fi
done

echo "[$(date)] Cleanup complete"
```

**Config `mc` aliases (chạy một lần khi setup):**
```bash
mc alias set local http://minio:9000 minioadmin minioadmin
mc alias set backup https://backup-s3.example.com ACCESS_KEY SECRET_KEY
mc mb backup/hrms-backup  # tạo bucket backup
```

---

### 3. Restore Procedure (SOP) — Slice 1

#### Restore Database từ backup

```bash
# 1. Dừng backend để tránh conflict
docker compose stop backend celery_worker celery_beat

# 2. Tạo DB mới (nếu restore sang DB trống)
docker exec hrms-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS hrms_restore;"
docker exec hrms-db-1 psql -U postgres -c "CREATE DATABASE hrms_restore;"

# 3. Restore từ backup file
gunzip -c /backups/postgres/hrms_20260101_020000.sql.gz | \
    docker exec -i hrms-db-1 psql -U postgres hrms_restore

# 4. Verify: đếm số bảng
docker exec hrms-db-1 psql -U postgres hrms_restore -c "\dt" | wc -l

# 5. Swap DB (nếu OK)
# Cập nhật DATABASE_URL trong .env, restart backend

# 6. Restart services
docker compose start backend celery_worker celery_beat
```

#### Restore MinIO từ backup

```bash
# 1. Stop frontend để user không upload mới trong khi restore
docker compose stop frontend

# 2. Mirror từ backup về production bucket
mc mirror \
    "backup/hrms-backup/files-20260101/" \
    "local/hrms-attachments-prod/" \
    --overwrite

# 3. Verify: đếm objects
mc ls "local/hrms-attachments-prod/" --recursive | wc -l

# 4. Restart frontend
docker compose start frontend
```

**RTO/RPO:**
- RPO (Recovery Point Objective): ≤ 24 giờ (daily backup)
- RTO (Recovery Time Objective): ≤ 4 giờ (manual restore)
- Test restore: mỗi tháng 1 lần vào staging

---

### 4. File Size Limit (Slice 2)

**Cập nhật `app/core/storage.py`:**
```python
MAX_UPLOAD_SIZE_MB = 50
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

async def validate_upload(upload: UploadFile) -> bytes:
    """Đọc và validate file upload. Raise HTTPException nếu quá giới hạn."""
    content = await upload.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File quá lớn. Tối đa {MAX_UPLOAD_SIZE_MB}MB."
        )
    return content
```

**Cập nhật `app/core/config.py`:**
```python
MAX_UPLOAD_SIZE_MB: int = 50
```

**Áp dụng trong tất cả upload endpoints:**
```python
# Thay vì:
content = await upload.read()

# Dùng:
content = await validate_upload(upload)
```

---

### 5. File Type Whitelist (Slice 2)

```python
# app/core/storage.py
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",   # xlsx
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/msword",           # doc
    "application/vnd.ms-excel",     # xls
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".webp"}

def validate_file_type(upload: UploadFile) -> None:
    """Kiểm tra content-type và extension."""
    ext = Path(upload.filename or "").suffix.lower()
    ct = upload.content_type or ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail=f"Định dạng file không được phép: {ext}")
    if ct and ct not in ALLOWED_CONTENT_TYPES and not ct.startswith("image/"):
        raise HTTPException(400, detail=f"Content-type không hợp lệ: {ct}")
```

---

### 6. File Retention Policy (Slice 2 — Document only)

**Policy (tài liệu hóa, chưa auto-delete):**

| Loại file | Thời gian giữ | Trigger xóa | Ghi chú |
|---|---|---|---|
| Hồ sơ nhân viên | Vĩnh viễn | Chỉ xóa thủ công | Yêu cầu pháp lý: 10 năm sau nghỉ việc |
| Hợp đồng lao động | Vĩnh viễn | Chỉ xóa thủ công | Yêu cầu pháp lý |
| File import tạm (xlsx upload) | Không lưu | Không lưu vào MinIO | Xử lý in-memory |
| Export jobs (xlsx) | 7 ngày | Auto (cleanup_expired_exports task) | Đã có ✅ |
| Ảnh đại diện | Khi xóa employee | Chưa implement | Future: thêm hook |

**Script cleanup (chạy thủ công khi cần):**
```python
# scripts/cleanup_orphan_files.py
# So sánh objects trong MinIO vs file_path trong DB
# Đánh dấu/xóa các file không có record trong DB
```

---

## Cấu trúc file thay đổi

```
backend/
├── app/core/
│   └── storage.py          ← UPDATE — validate_upload(), validate_file_type(), MAX_UPLOAD_SIZE
├── app/core/config.py      ← UPDATE — MAX_UPLOAD_SIZE_MB
scripts/
├── backup_db.sh            ← NEW — PostgreSQL backup script
├── backup_minio.sh         ← NEW — MinIO mirror script
└── restore_procedure.md    ← NEW — Step-by-step restore guide
```

---

## Kế hoạch theo Slice

### Slice 1 — Backup + Restore SOP (Critical)

**Việc cần làm:**
1. Viết `scripts/backup_db.sh` — pg_dump + compress + cleanup 90 ngày
2. Viết `scripts/backup_minio.sh` — mc mirror + cleanup 90 ngày
3. Viết `scripts/restore_procedure.md` — step-by-step cả DB lẫn MinIO
4. Test backup: chạy `backup_db.sh` thủ công → verify file tạo ra đúng
5. Test restore: restore sang DB test → verify data đúng
6. Setup cron job: 02:00 hàng ngày backup DB, 03:00 backup MinIO

**Verify:** Backup file được tạo, có thể restore thành công lên staging.

---

### Slice 2 — File Validation + Type Whitelist (High)

**Việc cần làm:**
1. Thêm `validate_upload()` vào `storage.py`
2. Thêm `validate_file_type()` vào `storage.py`
3. Áp dụng cho tất cả upload endpoints (employee attachments, contracts, templates, etc.)
4. Tests:
   - `test_upload_over_limit_returns_413`
   - `test_upload_invalid_extension_returns_400`
   - `test_upload_valid_pdf_succeeds`

**Verify:** `pytest tests/test_file_upload_validation.py -v` pass.

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Backup disk full | Monitor disk usage, cảnh báo tại 80%; rotate sang remote S3 |
| `mc mirror` chậm (file lớn) | Chạy incremental (`--newer-than 24h`); full mirror weekly |
| Restore sai version → mất data mới | Luôn restore sang DB/bucket mới, không overwrite trực tiếp |
| File type bypass (MIME spoofing) | Kiểm tra cả extension + content-type; tương lai: magic bytes check |
| 50MB limit chặn file hợp lệ | Config `MAX_UPLOAD_SIZE_MB` trong .env, HR có thể tăng nếu cần |

---

## Checklist

### Critical (phải có trước go-live)
- [ ] `scripts/backup_db.sh` viết và test thành công
- [ ] `scripts/backup_minio.sh` viết và test thành công
- [ ] `scripts/restore_procedure.md` có đủ bước, test được
- [ ] Cron job backup chạy hàng ngày (02:00 DB, 03:00 MinIO)
- [ ] Backup retention: tự động xóa sau 90 ngày

### High (nên có trước go-live)
- [ ] File size limit 50MB enforce trong tất cả upload endpoints
- [ ] File type whitelist — từ chối extension không hợp lệ
- [ ] Test restore: thực hiện restore staging 1 lần, verify thành công

### Medium (làm sau go-live)
- [ ] MinIO TLS certificate cho production (`MINIO_SECURE=true`)
- [ ] Retention policy document chính thức ký duyệt
- [ ] Cleanup orphan files script
