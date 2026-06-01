# Hướng dẫn Restore — HRMS (Plan 15.4)

> **Lưu ý:** Luôn restore sang DB/bucket MỚI trước khi swap sang production. Không overwrite trực tiếp.

---

## RTO / RPO

| Metric | Target |
|---|---|
| Recovery Point Objective (RPO) | ≤ 24 giờ (daily backup) |
| Recovery Time Objective (RTO) | ≤ 4 giờ (manual restore) |
| Test restore frequency | Mỗi tháng 1 lần lên staging |

---

## 1. Restore PostgreSQL

### 1.1 Xác định file backup cần restore

```bash
# Liệt kê các backup có sẵn
ls -lh /backups/postgres/hrms_*.sql.gz

# Hoặc từ MinIO backup bucket
mc ls backup/hrms-db-backups/ --recursive | tail -20
```

### 1.2 Restore vào DB mới (không overwrite production)

```bash
# Bước 1: Dừng backend để tránh write trong khi restore
docker compose stop backend celery_worker celery_beat

# Bước 2: Tạo DB restore (trên container PostgreSQL)
docker exec hrms-db-1 psql -U postgres -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'hrms_restore' AND pid <> pg_backend_pid();
  DROP DATABASE IF EXISTS hrms_restore;
  CREATE DATABASE hrms_restore OWNER postgres;
"

# Bước 3: Restore từ file backup
BACKUP_FILE="/backups/postgres/hrms_20260101_020000.sql.gz"
gunzip -c "$BACKUP_FILE" | docker exec -i hrms-db-1 psql -U postgres hrms_restore

# Bước 4: Verify — đếm số bảng
docker exec hrms-db-1 psql -U postgres hrms_restore -c "
  SELECT count(*) AS table_count FROM information_schema.tables
  WHERE table_schema = 'public';
"

# Bước 5: Verify dữ liệu chính
docker exec hrms-db-1 psql -U postgres hrms_restore -c "
  SELECT 'employees' AS tbl, count(*) FROM employees
  UNION ALL
  SELECT 'departments', count(*) FROM departments
  UNION ALL
  SELECT 'users', count(*) FROM users;
"

# Hoặc verify nhanh bằng script tự động:
DB_HOST=127.0.0.1 DB_PORT=5433 DB_PASSWORD=your_password \
  bash scripts/verify_backup.sh "$BACKUP_FILE"
```

### 1.3 Swap sang production (khi đã verify OK)

```bash
# Cập nhật DATABASE_URL trong .env trỏ sang hrms_restore
# (hoặc rename DB)
docker exec hrms-db-1 psql -U postgres -c "
  -- Đổi tên: production → production_old, restore → production
  ALTER DATABASE hrms RENAME TO hrms_old;
  ALTER DATABASE hrms_restore RENAME TO hrms;
"

# Restart services
docker compose start backend celery_worker celery_beat
docker compose exec backend alembic upgrade head   # chạy migration nếu cần
```

### 1.4 Rollback nếu có vấn đề

```bash
docker exec hrms-db-1 psql -U postgres -c "
  ALTER DATABASE hrms RENAME TO hrms_restore;
  ALTER DATABASE hrms_old RENAME TO hrms;
"
docker compose start backend celery_worker celery_beat
```

---

## 2. Restore MinIO

### 2.1 Xác định snapshot cần restore

```bash
# Liệt kê snapshots có sẵn
mc ls backup/hrms-backup/ | grep "^files-"

# Xem chi tiết snapshot
mc ls backup/hrms-backup/files-20260101/ --recursive | wc -l
```

### 2.2 Restore từ snapshot về production bucket

```bash
# Bước 1: Dừng frontend để user không upload mới trong khi restore
docker compose stop frontend

# Bước 2: Mirror từ backup về production bucket
SNAPSHOT_DATE="20260101"
mc mirror \
    "backup/hrms-backup/files-${SNAPSHOT_DATE}/" \
    "local/hrms-attachments-prod/" \
    --overwrite

# Bước 3: Verify số objects
RESTORED=$(mc ls "local/hrms-attachments-prod/" --recursive | wc -l)
SNAPSHOT=$(mc ls "backup/hrms-backup/files-${SNAPSHOT_DATE}/" --recursive | wc -l)
echo "Restored: $RESTORED objects (snapshot had: $SNAPSHOT objects)"

# Bước 4: Restart frontend
docker compose start frontend
```

### 2.3 Partial restore (chỉ restore một subfolder)

```bash
# Ví dụ: chỉ restore hồ sơ nhân viên
mc mirror \
    "backup/hrms-backup/files-20260101/employees/" \
    "local/hrms-attachments-prod/employees/" \
    --overwrite
```

---

## 3. Full Disaster Recovery (cả DB lẫn MinIO)

```bash
# Thứ tự thực hiện:
# 1. Restore DB trước (theo mục 1)
# 2. Restore MinIO sau (theo mục 2)
# 3. Đảm bảo file_path trong DB khớp với objects trong MinIO

# Verify cross-reference (optional sanity check):
docker exec hrms-db-1 psql -U postgres hrms -c "
  SELECT count(*) AS attachments_with_path
  FROM employee_attachments
  WHERE file_path IS NOT NULL;
"
# So sánh với tổng objects trong MinIO:
mc ls local/hrms-attachments-prod/employees/ --recursive | wc -l
```

---

## 4. Crontab setup

```bash
# Thêm vào crontab của backup container hoặc host:
# DB backup lúc 02:00 hàng ngày
0 2 * * * DB_HOST=db DB_PASSWORD=your_password \
BACKUP_NOTIFY_COMMAND='docker compose exec -T backend python -m app.scripts.send_backup_notification' \
bash /scripts/backup_db.sh >> /logs/backup_db.log 2>&1

# MinIO backup lúc 03:00 hàng ngày
0 3 * * * BACKUP_NOTIFY_COMMAND='docker compose exec -T backend python -m app.scripts.send_backup_notification' \
bash /scripts/backup_minio.sh >> /logs/backup_minio.log 2>&1
```

`send_backup_notification` sẽ:
- lấy recipient từ `BACKUP_NOTIFY_EMAILS` nếu có
- nếu không có thì lấy email admin / HR manager trong DB
- gửi mail cả khi `success` lẫn `failed`

---

## 4.1 Seed flow cho production mới

Khi dựng môi trường production mới từ DB sạch, dùng đúng thứ tự:

```bash
# 1. Apply schema
docker compose exec backend alembic upgrade head

# 2. Seed baseline hệ thống (required + RBAC core)
docker compose exec backend python -m app.seeds

# 3. Seed bootstrap vận hành của doanh nghiệp
docker compose exec backend python -m app.seeds --bootstrap
```

Không chạy trên production:

```bash
docker compose exec backend python -m app.seeds --local-users
docker compose exec backend python -m app.seeds --sample
```

Lý do đã được xác nhận trong code:
- `--local-users` tạo 5 tài khoản local `*@hrms.local` chỉ dùng cho dev/test
- `--sample` nạp dữ liệu demo/test

---

## 5. Test Restore Monthly Checklist

Thực hiện mỗi tháng trên môi trường **staging**:

- [ ] Chạy `backup_db.sh` thủ công → verify file tạo ra đúng
- [ ] Restore DB backup mới nhất lên staging DB
- [ ] Verify: số bảng đúng, dữ liệu sample đúng
- [ ] Chạy `backup_minio.sh` thủ công → verify mirror thành công
- [ ] Restore MinIO snapshot lên staging bucket
- [ ] Verify: file download qua API hoạt động
- [ ] Ghi lại: thời gian restore từ đầu đến xong (so với RTO 4h target)
