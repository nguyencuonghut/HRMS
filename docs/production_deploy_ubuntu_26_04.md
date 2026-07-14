# Hướng dẫn deploy production HRMS trên Ubuntu 26.04

Tài liệu này mô tả cách dựng môi trường production cho HRMS trên **Ubuntu 26.04** dựa trên source hiện tại của repo.

Phạm vi của tài liệu:

1. chuẩn bị máy chủ Ubuntu 26.04
2. cài Docker + Docker Compose plugin
3. chuẩn bị `.env`, Nginx SSL và image production
4. khởi động stack bằng `docker-compose.prod.yml`
5. migrate DB, bootstrap admin đầu tiên, kiểm tra health sau deploy
6. nêu rõ các giới hạn production đã được ghi nhận trong runbook hiện tại

Tài liệu này được đối chiếu trực tiếp với:

- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml)
- [README.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/README.md)
- [Makefile](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/Makefile)
- [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf)
- [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example)
- [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml)
- [docs/production_go_live_runbook.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_go_live_runbook.md)

---

## 1. Kết luận ngắn

Source hiện tại **đã có đủ artifact để deploy một production stack chạy được**:

- PostgreSQL
- Redis
- FastAPI backend qua Gunicorn/Uvicorn worker
- Celery worker
- Celery beat
- Vue frontend
- Nginx reverse proxy
- backup scheduler
- certbot profile cho SSL

Nhưng cần phân biệt rõ:

1. **deploy production stack chạy được**
2. **go-live production an toàn cho nghiệp vụ**

Theo [docs/production_go_live_runbook.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_go_live_runbook.md), source vẫn còn một số **blocker/go-live gap** ở tầng production hardening và vận hành. Vì vậy tài liệu này chỉ là hướng dẫn **dựng và chạy stack production**, không thay thế checklist go-live.

---

## 2. Kiến trúc production hiện tại

Theo [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml), stack production gồm:

- `db`: `postgres:16-alpine`
- `redis`: `redis:7-alpine`
- `backend`: image production của backend
- `celery_worker`: dùng cùng image backend
- `celery_beat`: dùng cùng image backend
- `frontend`: image production của frontend
- `backup_scheduler`: image riêng để chạy backup DB + object storage
- `nginx`: reverse proxy public 80/443
- `certbot`: profile chạy lấy chứng chỉ

Luồng truy cập public:

1. User truy cập `https://<domain>`
2. Nginx nhận traffic tại `443`
3. `/api/*` forward vào `backend:8000`
4. route còn lại forward vào `frontend:80`

Lưu ý đã xác nhận từ source:

- `docker-compose.prod.yml` **không build image tại chỗ**
- production compose **chỉ pull image** từ registry qua:
  - `BACKEND_IMAGE`
  - `FRONTEND_IMAGE`
  - `BACKUP_IMAGE`
  - `IMAGE_TAG`

Nghĩa là trước khi deploy, image phải được build/push sẵn.

---

## 3. Yêu cầu đầu vào

Máy chủ production Ubuntu 26.04 cần có:

- 1 VM hoặc bare metal có public IP
- user có quyền `sudo`
- domain trỏ về server, ví dụ `hrms.company.vn`
- outbound internet để pull Docker images và lấy SSL cert
- registry credentials nếu image để private trên GHCR

Khuyến nghị tối thiểu để chạy stack này:

- 4 vCPU
- 8 GB RAM
- 80 GB SSD

Đây là khuyến nghị vận hành, không phải giá trị hard-coded trong source.

---

## 4. Chuẩn bị hệ điều hành Ubuntu 26.04

### 4.1. Cập nhật hệ thống

```bash
sudo apt update
sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
```

### 4.2. Cài gói nền tảng

```bash
sudo apt install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  jq \
  unzip
```

### 4.3. Mở firewall

Nếu dùng `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Từ source hiện tại, chỉ `nginx` cần expose public:

- `80`
- `443`

Các service nội bộ như Postgres, Redis, backend không cần public port trong production compose.

---

## 5. Cài Docker Engine và Compose plugin

### 5.1. Thêm Docker apt repository

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
```

### 5.2. Cài Docker

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo docker version
sudo docker compose version
```

### 5.3. Cho phép user hiện tại chạy Docker

```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps
```

---

## 6. Chuẩn bị source và thư mục deploy

### 6.1. Clone repo

```bash
sudo mkdir -p /opt/hrms
sudo chown -R $USER:$USER /opt/hrms
git clone <repo-url> /opt/hrms
cd /opt/hrms
```

### 6.2. Cấu trúc thư mục production

Repo hiện tại kỳ vọng:

```text
/opt/hrms
├── docker-compose.prod.yml
├── .env
├── nginx/
│   ├── conf.d/default.conf
│   └── ssl/
│       ├── fullchain.pem
│       └── privkey.pem
└── ...
```

---

## 7. Chuẩn bị file `.env`

### 7.1. Tạo file `.env`

```bash
cp .env.example .env
chmod 600 .env
```

### 7.2. Các biến bắt buộc phải sửa cho production

Dựa trên [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example) và `docker-compose.prod.yml`, tối thiểu phải cấu hình:

```env
ENVIRONMENT=production
DEBUG=false

POSTGRES_USER=postgres
POSTGRES_PASSWORD=<mat-khau-rat-manh>
POSTGRES_DB=hrms

SECRET_KEY=<random-64-hex>
ENCRYPTION_KEY=<fernet-key>
REDIS_PASSWORD=<random-strong-password>

BACKEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backend
FRONTEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-frontend
BACKUP_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backup
IMAGE_TAG=<commit-sha-hoac-tag>

REFRESH_TOKEN_COOKIE_SECURE=true
CORS_ORIGINS=["https://hrms.company.vn"]

MINIO_ENDPOINT=<object-storage-endpoint>
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_SECURE=true
MINIO_BUCKET=hrms-attachments-prod

BOOTSTRAP_ADMIN_EMAIL=admin@company.vn
BOOTSTRAP_ADMIN_FULL_NAME=System Administrator
BOOTSTRAP_ADMIN_PASSWORD=<mat-khau-admin-dau-tien>
```

### 7.3. Các biến nên cấu hình thêm

```env
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-pass>
SMTP_USE_STARTTLS=true
SMTP_FROM_EMAIL=no-reply@company.vn
SMTP_FROM_NAME=HRMS

SENTRY_DSN=<dsn-neu-co>
HEALTHCHECK_PING_URL=<url-neu-co>

BACKUP_STORAGE_ENDPOINT=<backup-object-storage-endpoint>
BACKUP_STORAGE_ACCESS_KEY=<backup-key>
BACKUP_STORAGE_SECRET_KEY=<backup-secret>
BACKUP_STORAGE_SECURE=true
BACKUP_STORAGE_BUCKET=hrms-backup
BACKUP_RETENTION_DAYS=90
DB_BACKUP_CRON=0 2 * * *
MINIO_BACKUP_CRON=0 3 * * *
BACKUP_NOTIFY_EMAILS=it@company.vn,hr@company.vn
```

### 7.4. Cách sinh secret

`SECRET_KEY`:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

`ENCRYPTION_KEY`:

```bash
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Nếu server chưa có Python package `cryptography`, có thể generate key ở máy khác rồi copy vào `.env`.

---

## 8. Chuẩn bị SSL và Nginx

### 8.1. Sửa `server_name`

Trong [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf), source hiện để:

```nginx
server_name _;
```

Trước production thật, phải đổi thành domain thực, ví dụ:

```nginx
server_name hrms.company.vn;
```

Cần sửa ở cả block:

- HTTP `listen 80`
- HTTPS `listen 443 ssl`

### 8.2. Chuẩn bị certificate

Source hiện mount cert từ:

```text
./nginx/ssl/fullchain.pem
./nginx/ssl/privkey.pem
```

Tạo thư mục:

```bash
mkdir -p nginx/ssl
chmod 700 nginx/ssl
```

### 8.3. Lấy cert bằng certbot profile của compose

Theo `docker-compose.prod.yml`, đã có service `certbot`.

Chạy:

```bash
export CERTBOT_EMAIL=admin@company.vn
export DOMAIN=hrms.company.vn
docker compose -f docker-compose.prod.yml run --rm --profile certbot certbot
```

Sau đó kiểm tra:

```bash
ls -l nginx/ssl/
```

Lưu ý đã xác nhận từ source:

- `certbot` mount `./nginx/ssl:/etc/letsencrypt/live`
- `nginx` mount `./nginx/ssl:/etc/nginx/ssl:ro`

Nếu dùng cert đã phát hành từ nơi khác, chỉ cần copy đúng 2 file:

- `nginx/ssl/fullchain.pem`
- `nginx/ssl/privkey.pem`

---

## 9. Xác nhận image production đã tồn tại

Production compose không build tại chỗ. Phải chắc chắn image đã được push lên registry.

Theo [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml):

- branch `master` khi push sẽ build/push:
- `ghcr.io/nguyencuonghut/hrms/hrms-backend:latest`
- `ghcr.io/nguyencuonghut/hrms/hrms-backend:<github.sha>`
- `ghcr.io/nguyencuonghut/hrms/hrms-backup:latest`
- `ghcr.io/nguyencuonghut/hrms/hrms-backup:<github.sha>`
- `ghcr.io/nguyencuonghut/hrms/hrms-frontend:latest`
- `ghcr.io/nguyencuonghut/hrms/hrms-frontend:<github.sha>`

### 9.1. Login registry

Ví dụ GHCR:

```bash
echo '<ghcr-token>' | docker login ghcr.io -u <github-username> --password-stdin
```

### 9.2. Pull thử image

```bash
docker pull ${BACKEND_IMAGE}:${IMAGE_TAG}
docker pull ${FRONTEND_IMAGE}:${IMAGE_TAG}
docker pull ${BACKUP_IMAGE}:${IMAGE_TAG}
```

Nếu 3 lệnh này fail thì chưa nên deploy.

---

## 10. Khởi động production stack lần đầu

### 10.1. Pull toàn bộ image

```bash
docker compose -f docker-compose.prod.yml pull
```

### 10.2. Khởi động stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 10.3. Kiểm tra container

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=200
```

### 10.4. Chạy migration

```bash
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

### 10.5. Seed dữ liệu required

```bash
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds --bootstrap
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds --bootstrap-admin
```

Lưu ý:

- `--bootstrap-admin` phụ thuộc 3 biến:
  - `BOOTSTRAP_ADMIN_EMAIL`
  - `BOOTSTRAP_ADMIN_FULL_NAME`
  - `BOOTSTRAP_ADMIN_PASSWORD`

### 10.6. Kiểm tra health sau seed

```bash
curl -I http://127.0.0.1/health
curl -I http://127.0.0.1
curl -kI https://127.0.0.1
```

Nếu đã trỏ DNS:

```bash
curl -I https://hrms.company.vn/health
curl -I https://hrms.company.vn
```

---

## 11. Checklist verify sau deploy

### 11.1. Hạ tầng

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail=100
docker compose -f docker-compose.prod.yml logs celery_worker --tail=100
docker compose -f docker-compose.prod.yml logs celery_beat --tail=100
docker compose -f docker-compose.prod.yml logs nginx --tail=100
docker compose -f docker-compose.prod.yml logs backup_scheduler --tail=100
```

Xác nhận:

- `db` đang healthy
- `redis` đang healthy
- `backend` khởi động không lỗi
- `frontend` đang up
- `nginx` không lỗi SSL/config
- `backup_scheduler` không crash loop

### 11.2. Ứng dụng

Xác nhận thủ công tối thiểu:

1. mở trang login
2. đăng nhập bằng bootstrap admin
3. mở một API docs route nội bộ nếu policy cho phép
4. upload thử 1 file đính kèm
5. kiểm tra task định kỳ có xuất hiện log ở `celery_beat` / `celery_worker`

### 11.3. Database

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "\dt"
docker compose -f docker-compose.prod.yml exec -T backend alembic current
```

---

## 12. Cập nhật phiên bản production

Theo workflow hiện tại, deploy update nên đi theo flow:

1. push code lên `main`
2. CI build/push image mới
3. lấy `IMAGE_TAG` là commit SHA vừa build
4. cập nhật `.env` trên production
5. pull + restart service dùng image mới
6. chạy migration

### 12.1. Cập nhật `.env`

```env
IMAGE_TAG=<new-commit-sha>
```

### 12.2. Pull và restart toàn bộ app layer

```bash
docker compose -f docker-compose.prod.yml pull backend celery_worker celery_beat frontend
docker compose -f docker-compose.prod.yml up -d --no-deps --remove-orphans backend celery_worker celery_beat frontend
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

Đây là đúng flow đã được xác nhận trong [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml).

### 12.3. Cập nhật riêng biệt (FE hoặc BE) để giảm downtime

Nếu chỉ có thay đổi ở Frontend hoặc Backend, bạn có thể pull và cập nhật riêng từng phần:

#### A. Chỉ cập nhật Frontend (FE)
```bash
docker compose -f docker-compose.prod.yml pull frontend
docker compose -f docker-compose.prod.yml up -d --no-deps frontend
```
> [!NOTE]
> Cấu hình Nginx reverse proxy đã được cập nhật để không cache file `index.html`. Tuy nhiên, nếu trình duyệt của người dùng vẫn còn cache phiên bản cũ trước đó, hãy hướng dẫn họ thực hiện **Hard Reload (Ctrl + F5)** hoặc mở ở chế độ ẩn danh (Incognito) để kiểm tra.

#### B. Chỉ cập nhật Backend (BE)
```bash
docker compose -f docker-compose.prod.yml pull backend celery_worker celery_beat
docker compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker celery_beat
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

---

## 13. Backup và restore

### 13.1. Backup

Lịch backup production mặc định chạy qua Admin Backup Console + Celery:

- `celery_beat` kiểm tra lịch mỗi phút.
- Khi đến giờ cấu hình, hệ thống tạo một `backup_set` loại `scheduled_full`.
- `celery_worker` queue `backups` chạy backup DB trước, sau đó backup kho tệp ứng dụng.

Service `backup_scheduler` script cũ vẫn còn trong compose nhưng chỉ để dự phòng legacy, nằm dưới profile `legacy-backup` và không khởi động mặc định.

Chỉ bật scheduler cũ khi đã chủ động quay về cơ chế script/env:

```bash
docker compose -f docker-compose.prod.yml --profile legacy-backup up -d backup_scheduler
docker compose -f docker-compose.prod.yml --profile legacy-backup logs backup_scheduler --tail=200
```

### 13.2. Restore

Quy trình restore chi tiết đã có ở:

- [scripts/restore_procedure.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/scripts/restore_procedure.md)

Nguyên tắc đã ghi rõ trong source:

- luôn restore sang DB/bucket mới trước
- không overwrite trực tiếp production đang chạy

### 13.3. Chạy production với dữ liệu vừa khôi phục

Admin Backup Console hiện có 2 chế độ khôi phục:

- `Chỉ kiểm tra`: hệ thống chỉ restore thử DB vào cơ sở dữ liệu tạm, kiểm tra snapshot MinIO, sau đó dọn tài nguyên tạm. Chế độ này **không** dùng để chạy production với dữ liệu khôi phục.
- `Khôi phục sang đích mới`: hệ thống tạo DB đích mới và bucket MinIO đích mới, restore dữ liệu vào đó, nhưng **không tự động chuyển production sang đích mới**.

Sau khi yêu cầu `Khôi phục sang đích mới` có trạng thái `Đã khôi phục`, thực hiện chuyển production sang dữ liệu vừa khôi phục như sau.

1. Ghi lại chính xác 2 giá trị trên màn **Yêu cầu khôi phục gần nhất**:

   - `Cơ sở dữ liệu đích mới`, ví dụ `hrms_restore_20260714`
   - `Kho tệp đích mới`, ví dụ `hrms-attachments-restore-20260714`

2. Trên server production, backup file `.env` hiện tại:

   ```bash
   cp .env ".env.before-restore-switch-$(date +%Y%m%d_%H%M%S)"
   ```

3. Sửa `.env` để app trỏ sang DB/bucket vừa khôi phục:

   ```env
   POSTGRES_DB=hrms_restore_20260714
   MINIO_BUCKET=hrms-attachments-restore-20260714
   ```

   Nếu production dùng `DATABASE_URL` tự khai báo thay vì biến `POSTGRES_DB`, phải đổi `DATABASE_URL` sang database vừa khôi phục tương ứng.

4. Restart **app layer**, không xóa volume và không recreate `db` / `minio`:

   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate backend celery_worker celery_beat
   ```

   Nếu đang bật profile `legacy-backup` và `backup_scheduler` đang chạy, restart thêm service đó để nó nhận `POSTGRES_DB` / `MINIO_BUCKET` mới:

   ```bash
   docker compose -f docker-compose.prod.yml --profile legacy-backup up -d --no-deps --force-recreate backup_scheduler
   ```

5. Kiểm tra DB app đang trỏ tới:

   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend python - <<'PY'
   from app.core.config import settings
   print(settings.DATABASE_URL)
   print(settings.MINIO_BUCKET)
   PY
   ```

6. Kiểm tra migration của DB vừa khôi phục:

   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend alembic current
   ```

   Nếu source hiện tại mới hơn snapshot được restore, chạy migration trên DB đích mới:

   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
   ```

7. Smoke test sau chuyển đổi:

   - đăng nhập bằng tài khoản admin
   - mở danh sách nhân sự
   - mở một hồ sơ có file đính kèm
   - tải thử file từ MinIO
   - kiểm tra log backend/worker:

   ```bash
   docker compose -f docker-compose.prod.yml logs backend --tail=100
   docker compose -f docker-compose.prod.yml logs celery_worker --tail=100
   ```

Không chạy các lệnh sau khi chỉ muốn chuyển sang dữ liệu vừa khôi phục:

```bash
docker compose -f docker-compose.prod.yml down -v
docker volume rm ...
```

Các lệnh đó có thể xóa volume dữ liệu hiện tại.

---

## 14. Chạy production bằng systemd

Để stack tự lên sau reboot, tạo service:

`/etc/systemd/system/hrms.service`

```ini
[Unit]
Description=HRMS Production Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/hrms
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hrms
sudo systemctl start hrms
sudo systemctl status hrms
```

---

## 15. Các known gaps phải đọc trước khi go-live

Tài liệu này không phủ nhận các vấn đề đã ghi nhận trong runbook.

Trước khi go-live thật, phải đọc lại:

- [docs/production_go_live_runbook.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_go_live_runbook.md)

Các nhóm rủi ro đã được ghi nhận ở đó gồm:

1. domain/CORS/CSRF production hardening
2. object storage wiring và validate runtime
3. refresh cookie/session hardening
4. CI/CD và rollback discipline
5. backup/restore rehearsal
6. các blocker import/go-live nghiệp vụ

Nói ngắn gọn:

- tài liệu này giúp **deploy được**
- runbook go-live giúp quyết định **có nên chạy thật hay chưa**

---

## 16. Lệnh vận hành nhanh

```bash
# Xem trạng thái
docker compose -f docker-compose.prod.yml ps

# Xem log realtime
docker compose -f docker-compose.prod.yml logs -f

# Restart backend
docker compose -f docker-compose.prod.yml restart backend

# Restart toàn bộ app layer, không động vào db/redis
docker compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker celery_beat frontend nginx

# Vào shell backend
docker compose -f docker-compose.prod.yml exec backend bash

# Kiểm tra migration hiện tại
docker compose -f docker-compose.prod.yml exec -T backend alembic current
```

---

## 17. Điều đã xác nhận và chưa xác nhận

### Đã xác nhận từ source

1. production compose dùng image đã build/push sẵn, không build local
2. Nginx public qua `80/443`, frontend/backend ở internal network
3. có backup scheduler và certbot profile
4. CI hiện build/push 3 image production và có flow deploy staging qua SSH
5. bootstrap admin production dùng `python -m app.seeds --bootstrap-admin`

### Chưa xác nhận trong tài liệu này

1. chưa verify trực tiếp trên một máy Ubuntu 26.04 thật trong turn này
2. chưa verify end-to-end việc lấy cert thật qua certbot profile trên domain thật
3. chưa verify runtime object storage production cụ thể của doanh nghiệp
4. chưa xác nhận mọi blocker trong runbook go-live đã được xử lý xong

Nếu cần, bước tiếp theo hợp lý là mình rà lại tài liệu này cùng `production_go_live_runbook.md`, rồi tách ra:

1. `deploy infra`
2. `go-live checklist`
3. `rollback + disaster recovery`
