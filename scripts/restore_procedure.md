# Hướng dẫn Khôi phục — HRMS

> Viết lại ở kế hoạch 15.7 (Slice 9) sau khi chuyển kho tệp từ MinIO sang Garage. Sao lưu do **Backup Console** (menu "Sao lưu & khôi phục", `/admin/backups`) chạy qua `celery_worker` và `celery_beat`; các script `backup_db.sh`, `backup_minio.sh`, image `hrms-backup` và `mc` **không còn**. Mọi lệnh dưới đây đã được chạy thật trên dev (Garage v2.5.0); chỗ nào chưa kiểm thì nói rõ ở mục 8.

**Nguyên tắc:** luôn khôi phục sang DB và kho MỚI, kiểm tra xong mới chuyển hệ thống sang. Không bao giờ ghi đè lên DB hay kho đang chạy.

**Giới hạn cần biết:** bản sao lưu nằm trong bucket `hrms-backup` của **chính Garage** của hệ thống, cùng máy và cùng ổ đĩa với dữ liệu thật. Hỏng hoặc mất ổ đĩa là mất cả hai. Hiện **chưa có** bản sao lưu ngoài máy (rủi ro R5 và việc D2 trong `docs/plan_15.7_chuyen_minio_sang_garage.md`, chủ hệ thống đã chấp nhận khi cutover). Tài liệu này chỉ giúp khôi phục khi kho `hrms-backup` còn đọc được.

---

## RTO / RPO

| Metric | Target |
|---|---|
| Recovery Point Objective (RPO) | ≤ 24 giờ (sao lưu theo lịch hằng ngày) |
| Recovery Time Objective (RTO) | ≤ 4 giờ (khôi phục thủ công) |
| Test restore frequency | Mỗi tháng 1 lần lên staging (mục 6) |

---

## 0. Bản sao lưu gồm những gì

Một lần "Sao lưu đầy đủ" (hoặc lịch `scheduled_full`) tạo một **bộ sao lưu** gồm hai artifact trong bucket `hrms-backup`:

| Artifact | Khóa trong `hrms-backup` | Nội dung |
|---|---|---|
| Cơ sở dữ liệu | `postgres/hrms_YYYYMMDD_HHMMSS.sql.gz` | `pg_dump` dạng SQL thuần, nén gzip. Thời gian trong tên là UTC |
| Kho tệp ứng dụng | `files/files-YYYYMMDD_HHMMSS/<đường dẫn tệp>` và `files/files-YYYYMMDD_HHMMSS/manifest.json` | Bản chép nguyên cấu trúc bucket tệp đính kèm, kèm manifest (số tệp, tổng dung lượng) |

Cả hai chạy **cùng lúc** trong một bộ, theo giờ đặt ở dòng **cơ sở dữ liệu** của Backup Console (mặc định 02:00 giờ Việt Nam; `created_at` trong bảng `backup_jobs` hiển thị UTC). Giờ đặt ở dòng kho tệp ứng dụng được lưu nhưng **lịch tự động không đọc** (đã kiểm: đặt DB 10:30 và kho tệp 10:35 trên production thì chỉ có một bộ lúc 10:30, không có lần chạy lúc 10:35).

---

## 1. Đường A: dùng Backup Console (ưu tiên)

Quyền: xem cần `backups:view`, tạo yêu cầu cần `backups:create`, duyệt cần `backups:edit`.

**Kiểm tra một bản sao lưu (không động vào dữ liệu thật).** Ở bảng "Bộ sao lưu đầy đủ" hoặc "Bản sao có thể khôi phục", bấm "Kiểm tra", nhập "Nội dung xác nhận" (tối thiểu 5 ký tự), bấm "Tạo yêu cầu chờ duyệt". Ở bảng "Yêu cầu khôi phục gần nhất", người có quyền duyệt bấm "Duyệt và kiểm tra" rồi **bấm OK ở hộp xác nhận của trình duyệt** (không bấm OK thì không có gì xảy ra). Hệ thống khôi phục dump vào một DB tạm rồi xóa DB tạm đó; với bộ sao lưu đầy đủ, nó cũng kiểm tra snapshot kho tệp. Trạng thái cuối là "Đã kiểm tra".

**Khôi phục sang đích mới.** Bấm "Khôi phục", chọn "Loại khôi phục", điền "Cơ sở dữ liệu đích mới" (chữ thường, số, dấu gạch dưới) và/hoặc "Kho tệp đích mới", nhập xác nhận, tạo yêu cầu, rồi bấm "Duyệt và khôi phục" và OK ở hộp xác nhận của trình duyệt. Trạng thái cuối là "Đã khôi phục" kèm dòng kết quả ghi tên DB và kho mới. Console từ chối nếu đích trùng DB đang chạy, kho tệp đang dùng hoặc kho sao lưu, và từ chối nếu kho tệp đích đã tồn tại.

**Console không tự chuyển hệ thống sang đích mới.** Sau khi trạng thái yêu cầu là "Đã khôi phục", vẫn phải làm bước chuyển bằng tay: DB ở mục 2.5, kho tệp ở mục 2.8. Kho tệp mới do Console tạo có thêm tệp đánh dấu `.hrms-restore/request-<id>.json` (vô hại, có thể bỏ qua).

Nếu Console không dùng được (backend hỏng, hoặc cần tách khỏi ứng dụng), dùng đường B.

---

## 2. Đường B: thủ công, chỉ cần Docker và SDK Python

### 2.0 Chuẩn bị biến

```bash
cd /opt/hrms/HRMS
DC="docker compose -f docker-compose.lan.yml"   # production LAN. Dev: DC="docker compose"
LIVE=hrms                                        # tên DB đang chạy (POSTGRES_DB trong .env, mặc định hrms)
```

Các lệnh về kho đi qua `scripts/backup_fetch.py` chạy **trong container backend** (đã có SDK `minio` và biến môi trường `BACKUP_STORAGE_*`, `S3_*`, kể cả `region`). Script không in bí mật.

### 2.1 Tìm artifact cần khôi phục

```bash
$DC exec -T backend python - list < scripts/backup_fetch.py              # tất cả
$DC exec -T backend python - list postgres/ < scripts/backup_fetch.py    # chỉ dump DB
$DC exec -T backend python - list files/ < scripts/backup_fetch.py       # chỉ snapshot kho tệp
```

Mỗi dòng là: kích thước (byte), thời điểm sửa (UTC), khóa. Chọn dump và snapshot **cùng một bộ** (thời điểm gần nhau).

### 2.2 Tải dump DB và kiểm tra tệp

```bash
KEY=postgres/hrms_20261031_022606.sql.gz        # lấy từ bước 2.1
$DC exec -T backend python - get "$KEY" < scripts/backup_fetch.py > ~/hrms_restore.sql.gz
gzip -t ~/hrms_restore.sql.gz && echo "gzip OK"
```

Kích thước script báo (`đã ghi N byte`) phải bằng cột kích thước ở bước 2.1. Nếu `get` lỗi (sai khóa, kho không đọc được), tệp rỗng và `gzip -t` báo lỗi.

### 2.3 Khôi phục vào DB MỚI

```bash
NEW=${LIVE}_restore
$DC exec -T -e NEW="$NEW" db sh -c 'createdb -U "$POSTGRES_USER" "$NEW"'

set -o pipefail
gunzip -c ~/hrms_restore.sql.gz | LC_ALL=C sed '/^SET transaction_timeout /d' \
  | $DC exec -T -e NEW="$NEW" db sh -c 'psql -q -o /dev/null -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$NEW"'
echo "exit=$?"      # phải là 0 và không in dòng ERROR nào
```

Vì sao có `sed`: dump do `pg_dump` 17 tạo ra có dòng `SET transaction_timeout = 0;` mà PostgreSQL 16 không nhận (`unrecognized configuration parameter`), nên `psql` dừng ngay. Backup Console cũng lọc đúng dòng này. Nếu bước này lỗi giữa chừng: xóa DB mới rồi làm lại, không dùng nửa vời:

```bash
$DC exec -T -e NEW="$NEW" db sh -c 'dropdb -U "$POSTGRES_USER" "$NEW"'
```

### 2.4 So số liệu giữa DB đang chạy và DB mới

```bash
COUNTS=$(mktemp)
cat > "$COUNTS" <<'SQL'
SELECT 'tables', count(*) FROM information_schema.tables WHERE table_schema = 'public'
UNION ALL SELECT 'employees', count(*) FROM employees
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'departments', count(*) FROM departments
UNION ALL SELECT 'employee_attachments', count(*) FROM employee_attachments;
SQL
for d in "$LIVE" "$NEW"; do
  echo "== $d"
  $DC exec -T -e D="$d" db sh -c 'psql -U "$POSTGRES_USER" -d "$D" -At -F"|"' < "$COUNTS"
done
rm -f "$COUNTS"
```

Dump được lấy tại thời điểm sao lưu, nên nếu dữ liệu đã đổi sau đó thì số liệu lệch là bình thường. Khi khôi phục sau sự cố, so với số bạn kỳ vọng thay vì với DB hỏng.

### 2.5 Chuyển sang DB mới (dừng dịch vụ, đổi tên trong một giao dịch)

```bash
OLD=${LIVE}_old
$DC stop backend celery_worker celery_beat

$DC exec -T -e LIVE="$LIVE" -e NEW="$NEW" -e OLD="$OLD" db sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -v live="$LIVE" -v new="$NEW" -v old="$OLD"' <<'SQL'
SELECT count(pg_terminate_backend(pid)) AS terminated FROM pg_stat_activity
 WHERE datname IN (:'live', :'new') AND pid <> pg_backend_pid();
BEGIN;
ALTER DATABASE :"live" RENAME TO :"old";
ALTER DATABASE :"new" RENAME TO :"live";
COMMIT;
SQL
```

Phải dừng backend, worker và beat trước: `ALTER DATABASE ... RENAME` không chạy được khi còn kết nối. Hai lệnh đổi tên nằm trong một giao dịch nên hoặc cả hai thành công hoặc không đổi gì (nếu `$OLD` đã tồn tại từ lần trước thì lệnh dừng, hệ thống vẫn nguyên).

### 2.6 Khởi động lại và kiểm tra

```bash
$DC start backend celery_worker celery_beat
$DC exec -T backend alembic current
$DC exec -T backend alembic heads
```

Nếu `alembic current` không có `(head)` (khôi phục từ bản sao lưu cũ hơn mã hiện tại), chạy `$DC exec -T backend alembic upgrade head`. Sau đó:

```bash
# backend cần vài giây để lên; thử lại tối đa 60 giây
for i in $(seq 1 30); do
  $DC exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())" 2>/dev/null && break
  sleep 2
done
```

Kết quả phải có `"status":"ok"` và `database`, `redis`, `storage` đều `ok`. Cuối cùng đăng nhập bằng trình duyệt, mở một hồ sơ nhân viên và tải một tệp đính kèm (xem lưu ý ở mục 7 về tệp thiếu).

### 2.7 Quay lui (khi bản mới có vấn đề)

```bash
$DC stop backend celery_worker celery_beat
$DC exec -T -e LIVE="$LIVE" -e NEW="$NEW" -e OLD="$OLD" db sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -v live="$LIVE" -v new="$NEW" -v old="$OLD"' <<'SQL'
SELECT count(pg_terminate_backend(pid)) AS terminated FROM pg_stat_activity
 WHERE datname IN (:'live', :'old') AND pid <> pg_backend_pid();
BEGIN;
ALTER DATABASE :"live" RENAME TO :"new";
ALTER DATABASE :"old" RENAME TO :"live";
COMMIT;
SQL
$DC start backend celery_worker celery_beat
```

Sau vài ngày chạy ổn, xóa DB cũ để giải phóng chỗ: `$DC exec -T -e OLD="$OLD" db sh -c 'dropdb -U "$POSTGRES_USER" "$OLD"'`.

### 2.8 Khôi phục kho tệp

Chép snapshot sang một kho **mới** (script từ chối nếu kho đã tồn tại, và không bao giờ ghi vào kho đang chạy):

```bash
SNAPSHOT=files/files-20261031_022608            # lấy từ bước 2.1, bỏ phần /manifest.json
NEWBUCKET=hrms-attachments-restore-20261101     # tên mới, chưa tồn tại
$DC exec -T backend python - restore-files "$SNAPSHOT" "$NEWBUCKET" < scripts/backup_fetch.py
```

Số tệp script báo phải bằng `object_count` trong `manifest.json` của snapshot (`get "$SNAPSHOT/manifest.json"`).

**Chuyển ứng dụng sang kho mới:**

1. Sửa `S3_BUCKET=<NEWBUCKET>` trong `.env`.
2. Ở Backup Console, mục "Cấu hình sao lưu", dòng kho tệp ứng dụng: nếu cột "Nguồn" hiện một tên kho cụ thể (trường "Kho lưu trữ nguồn" có giá trị), đổi sang kho mới hoặc để trống để dùng `S3_BUCKET`. Giá trị này **ghi đè** `S3_BUCKET` (xem mục 7); quên bước này thì lần sao lưu sau vẫn đọc kho cũ.
3. Tạo lại dịch vụ để nhận `.env` mới: `$DC up -d --no-deps backend celery_worker celery_beat`.
4. Kiểm tra: tải một tệp đính kèm (hoặc `GET /api/v1/employees/<id>/attachments/<att>/download` có token) và so `sha256` với bản gốc nếu có.

**Quay lui kho tệp:** đặt lại `S3_BUCKET` và "Kho lưu trữ nguồn" về giá trị cũ rồi `up -d` như bước 3. Kho cũ không bị đụng tới nên còn nguyên.

**Lấy lại một tệp lẻ** (ví dụ ai đó lỡ xóa): lấy tệp ra rồi tải lên lại qua ứng dụng, không ghi trực tiếp vào kho đang chạy:

```bash
$DC exec -T backend python - get "files/files-20261031_022608/employees/1/<tên tệp>" < scripts/backup_fetch.py > ./tep_khoi_phuc
```

**Dọn kho thử** (sau khi kiểm tra khôi phục trên staging/dev, hoặc kho cũ sau khi đã chạy ổn trên kho mới). Script từ chối xóa kho đang dùng (`S3_BUCKET`, `BACKUP_STORAGE_BUCKET`) và **không hoàn tác được**:

```bash
$DC exec -T backend python - delete-bucket "$NEWBUCKET" < scripts/backup_fetch.py
```

---

## 3. Khôi phục toàn bộ (DB và kho tệp), thứ tự

1. Dựng hệ thống theo `docs/deploy_noi_bo_lan_ubuntu_26_04.md` (gồm Garage và `scripts/garage_bootstrap.sh`). Kho `hrms-backup` phải đọc được; nếu Garage là máy mới và dữ liệu cũ đã mất thì **không có gì để khôi phục** (xem "Giới hạn" đầu tài liệu).
2. Khôi phục DB: mục 2.1 đến 2.6.
3. Khôi phục kho tệp: mục 2.8.
4. Kiểm tra chéo thô: số tệp đính kèm hồ sơ trong DB so với số tệp của snapshot (không tính `manifest.json`):

```bash
$DC exec -T -e D="$LIVE" db sh -c 'psql -U "$POSTGRES_USER" -d "$D" -Atc "SELECT count(*) FROM employee_attachments WHERE file_path IS NOT NULL"'
$DC exec -T backend python - list "$SNAPSHOT/" < scripts/backup_fetch.py | tail -n 3
```

Đây chỉ là kiểm tra thô cho một bảng: các bảng khác (hợp đồng, khen thưởng, kỷ luật, đào tạo, biểu mẫu...) cũng trỏ tới tệp trong cùng kho.

---

## 4. Dựng mới hoàn toàn (seed flow)

Khi dựng môi trường production mới từ DB sạch, dùng đúng thứ tự (đặt `DC` như mục 2.0):

```bash
# 1. Apply schema
$DC exec backend alembic upgrade head

# 2. Seed baseline hệ thống (required + RBAC core)
$DC exec backend python -m app.seeds

# 3. Seed bootstrap vận hành của doanh nghiệp
$DC exec backend python -m app.seeds --bootstrap

# 4. Bootstrap tài khoản admin đầu tiên
$DC exec backend python -m app.seeds --bootstrap-admin
```

Không chạy trên production:

```bash
$DC exec backend python -m app.seeds --local-users
$DC exec backend python -m app.seeds --sample
```

Lý do đã được xác nhận trong code:
- `--local-users` tạo 5 tài khoản local `*@hrms.local` chỉ dùng cho dev/test
- `--sample` nạp dữ liệu demo/test
- `seed-required` và `--bootstrap` không tạo user đăng nhập; `--bootstrap-admin` là bước tạo first admin
- `--bootstrap-admin` đọc `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_FULL_NAME`, `BOOTSTRAP_ADMIN_PASSWORD` từ `.env`

---

## 5. Lịch sao lưu và thông báo

Không còn crontab hay script ngoài. Muốn đổi giờ sao lưu, đổi "Giờ chạy hằng ngày" của dòng **cơ sở dữ liệu** (dòng kho tệp không quyết định lịch, xem mục 0). Lịch, số ngày giữ và danh sách email nhận thông báo đặt ở Backup Console, mục "Cấu hình sao lưu" (các trường "Giờ chạy hằng ngày", "Số ngày giữ", "Thư điện tử nhận thông báo"). Lịch do `celery_beat` kích hoạt và `celery_worker` thực thi, nên cả hai phải đang chạy (`$DC ps`). Kiểm tra kết nối tới đích bằng biểu tượng "Kiểm tra đích sao lưu" ở cuối mỗi dòng cấu hình.

---

## 6. Checklist kiểm tra khôi phục hằng tháng

Làm trên **staging** (hoặc dev), không làm trên production:

- [ ] Ở Backup Console, bấm "Sao lưu đầy đủ" và đợi bộ mới có trạng thái thành công
- [ ] `list` (mục 2.1) thấy cả dump `postgres/…` và snapshot `files/…` mới, kích thước hợp lý
- [ ] "Kiểm tra" bản DB mới nhất (mục 1) cho kết quả đạt
- [ ] Khôi phục DB sang DB mới bằng đường B (mục 2.2 đến 2.4), số liệu khớp kỳ vọng
- [ ] Khôi phục snapshot kho tệp sang kho mới (mục 2.8), tải được một tệp và `sha256` khớp
- [ ] Giám sát: `garage health` báo `HEALTHY` và `garage status` còn đủ `DataAvail` (xem `docs/deploy_noi_bo_lan_ubuntu_26_04.md`, mục giám sát)
- [ ] Dọn: `dropdb` DB thử, `delete-bucket` kho thử
- [ ] Ghi lại thời gian từ đầu đến xong (so với RTO 4 giờ)

---

## 7. Những bẫy đã gặp (có bằng chứng ở dev)

- **Cấu hình trong DB ghi đè `.env`.** Dòng cấu hình "Kho tệp ứng dụng" trong `backup_configs` (cột `source_endpoint`, `source_bucket`) được ưu tiên hơn `S3_ENDPOINT` và `S3_BUCKET` (`backup_runner_service.py`, hàm `_source_values`). Khi dev còn `source_endpoint = minio:9000` trong DB, job kho tệp thất bại với `AccessDenied` dù `.env` đã trỏ sang Garage. Sửa qua Backup Console (hoặc `PUT /api/v1/backups/config/object_storage`), không sửa `.env`.
- **`region`.** Garage cần `region=garage`; thiếu thì lệnh đầu tiên báo `AuthorizationHeaderMalformed`. Script `backup_fetch.py` đọc `BACKUP_STORAGE_REGION` và `S3_REGION` từ môi trường nên không phải tự đặt.
- **Kho tạo qua S3 chỉ có bí danh cục bộ.** Kho do script hoặc Console tạo (không qua `garage bucket create`) không có tên toàn cục, nên `garage bucket info <tên>` báo `NoSuchBucket`; tra bằng ID lấy từ `garage bucket list`. Với kho kiểu này, `garage bucket delete` cũng báo còn bí danh cục bộ; dùng `delete-bucket` ở mục 2.8.
- **Tải tệp thiếu trong kho.** Image backend cũ (trước bản sửa LD-003 trong `docs/known_issues.md`) trả HTTP 200 với thân rỗng, và 3 lần tải tệp thiếu liên tiếp làm mọi thao tác kho trả 503 trong 30 giây. Bản sửa nay trả 404 và không làm mạch ngắt mở, nhưng chỉ có tác dụng sau khi **dựng lại image backend và tạo lại `backend`, `celery_worker`, `celery_beat`**. Khôi phục DB mà chưa khôi phục kho tệp tương ứng thì tệp thiếu; luôn kiểm tra tải một tệp thật sau khi khôi phục.
- **Dòng `SET transaction_timeout`** (mục 2.3).

---

## 8. Chưa kiểm

- Các lệnh trên chạy thật trên **dev** (`docker compose`, Garage v2.5.0, PostgreSQL 16.15, một DB là bản sao của DB dev). Với file `docker-compose.lan.yml` trên máy chủ production chỉ kiểm được rằng service `db` và `backend` có đủ biến môi trường mà các lệnh dùng (đọc file), chưa chạy các lệnh này trên production.
- Luồng giao diện ở mục 1 (tạo yêu cầu kiểm tra và khôi phục sang đích mới, duyệt, kết quả) đã chạy thật bằng trình duyệt (Playwright, không mock) trên dev và đối chiếu số liệu với DB và Garage. Chưa thử các nút "Thử lại" và "Hủy", và chưa thử loại yêu cầu `db` hoặc `object_storage` riêng lẻ qua giao diện (chỉ `db` qua API).
- Mục 4 (seed flow) giữ nguyên các lệnh của bản cũ, chỉ đổi `docker compose` thành `$DC`; các tùy chọn `--bootstrap`, `--bootstrap-admin`, `--local-users`, `--sample` có trong `backend/app/seeds/__main__.py` (đã đọc), nhưng các lệnh này chưa được chạy lại hôm nay.
- `garage_bootstrap.sh` và dựng máy mới ở mục 3 chưa được thử như một cuộc khôi phục thảm họa trọn vẹn trên máy trống.
- `delete-bucket` mới thử trên kho tạo qua S3; chưa thử trên kho tạo bằng `garage bucket create` (kho do bootstrap tạo).
