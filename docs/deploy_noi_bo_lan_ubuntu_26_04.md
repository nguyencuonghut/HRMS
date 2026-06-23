# Hướng dẫn deploy HRMS trên server nội bộ LAN Ubuntu 26.04

Tài liệu này dành cho kịch bản:

- HRMS chạy trên **server nội bộ**
- user truy cập qua **mạng LAN**
- không public Internet cho người dùng cuối

Tài liệu này được đối chiếu trực tiếp với:

- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)
- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml)
- [nginx/conf.d/default.lan-http.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.lan-http.conf)
- [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf)
- [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example)
- [README.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/README.md)
- [Makefile](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/Makefile)
- [docs/production_deploy_ubuntu_26_04.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_deploy_ubuntu_26_04.md)

---

## 1. Kết luận ngắn

Source hiện tại **có thể dùng để deploy trên mạng LAN**, và với kịch bản đã chốt:

- server nội bộ có IP tĩnh `172.16.2.100`
- không public IP ra Internet
- user truy cập nội bộ qua LAN

thì tài liệu này **ưu tiên flow build Docker image local ngay trên server nội bộ**, sau đó chạy `docker compose` bằng image tag local.

Tài liệu này **không lấy GHCR làm flow chính**. GHCR chỉ là phương án phụ khi:

- server có outbound internet ổn định
- và bạn chủ động muốn quản lý image qua registry

Ngoài ra:

- GitHub-hosted runner **không thể mặc định SSH trực tiếp** vào server LAN không public
- nên tài liệu này được viết cho **deploy thủ công trên chính server nội bộ** hoặc **self-hosted runner trong LAN**

- cấu hình Nginx hiện tại trong source **mặc định redirect từ HTTP sang HTTPS**
- và block HTTPS hiện tại **bắt buộc có certificate**

Điều này đã được xác nhận từ [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf):

- `listen 80` trả `301 https://$host$request_uri`
- `listen 443 ssl`
- yêu cầu:
  - `/etc/nginx/ssl/fullchain.pem`
  - `/etc/nginx/ssl/privkey.pem`

Vì vậy, khi chạy nội bộ LAN có 2 lớp quyết định:

1. **Mô hình triển khai**
2. **Mô hình HTTP/HTTPS**

### 1.1. Mô hình triển khai

#### Mô hình A — Build local trên server nội bộ

Đây là mô hình **ưu tiên trong tài liệu này**.

Ưu điểm:

- không phụ thuộc GHCR để chạy bản deploy
- không cần inbound Internet vào server
- dễ kiểm soát trong mạng LAN kín

#### Mô hình B — Server tự pull image từ GHCR

Chỉ là mô hình phụ, dùng khi:

- server có outbound internet
- bạn muốn quản lý artifact qua registry

#### Mô hình C — GitHub-hosted runner SSH thẳng vào server LAN

Không phù hợp với kịch bản này, trừ khi có thêm:

- VPN / tunnel / bastion / reverse tunnel
- hoặc đổi sang self-hosted runner trong LAN

### 1.2. Mô hình HTTP/HTTPS

Về mặt web serving, khi chạy nội bộ LAN có 2 phương án:

1. **Phương án A: HTTPS nội bộ**
2. **Phương án B: HTTP-only nội bộ**

Nếu không muốn quản lý SSL nội bộ, phải dùng **Phương án B** và sửa Nginx.

---

## 2. Khi nào nên chọn từng phương án

### Phương án A — HTTPS nội bộ

Nên dùng khi:

- công ty có domain nội bộ hoặc DNS nội bộ
- có thể cấp certificate nội bộ
- muốn cookie auth chạy ở mode an toàn hơn
- muốn tránh cảnh báo bảo mật trên trình duyệt

Ví dụ user truy cập:

- `https://hrms.honghafeed.com.vn`
- `https://172.16.2.100`

### Phương án B — HTTP-only nội bộ

Nên dùng khi:

- chỉ chạy trong LAN kín
- chưa có CA nội bộ / certificate
- cần lên nhanh để pilot nội bộ

Ví dụ user truy cập:

- `http://172.16.2.100`
- `http://hrms.honghafeed.com.vn`

Đã xác nhận trực tiếp từ source hiện tại:

- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml) nay chạy `ENVIRONMENT=${ENVIRONMENT:-lan}`
- `docker-compose.lan.yml` đã có service `minio` nội bộ
- `backup_scheduler` trong LAN stack đã được chuyển sang `profile` tùy chọn, không khởi động mặc định

Đã verify runtime trên máy dev:

- boot stack tối thiểu `db + redis + minio + backend` với `HTTP-only`
- `backend` lên trạng thái `healthy`

Kết luận:

- artifact hiện tại **đã hỗ trợ HTTP-only nội bộ**
- không cần HTTPS để chỉ đạt mục tiêu boot và chạy trong LAN kín

---

## 3. Kiến trúc LAN hiện tại

Theo [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml), stack LAN hiện gồm:

- `db`
- `redis`
- `minio`
- `backend`
- `celery_worker`
- `celery_beat`
- `frontend`
- `nginx`

Ngoài ra:

- `backup_scheduler` là service tùy chọn, chỉ chạy khi bật profile `backup`

User trong LAN sẽ truy cập qua:

- port `80`
- hoặc `443`

Tùy theo phương án HTTP hay HTTPS.

Đã xác nhận từ source:

- `frontend` không expose `5173`
- `backend` không expose `8000`
- public entrypoint vẫn là `nginx`

Nghĩa là sau deploy nội bộ:

- user không vào `:5173`
- user vào qua địa chỉ website nội bộ bình thường

---

## 4. Yêu cầu đầu vào

Máy chủ Ubuntu 26.04 nội bộ cần có:

- IP LAN tĩnh, ví dụ `172.16.2.100`
- user có quyền `sudo`
- truy cập được source code của repo để build local

Tùy cách lấy source, máy chủ có thể:

- có outbound internet để `git clone` trực tiếp từ GitHub
- hoặc nhận source bằng cách copy file `.zip` / `git bundle` / thư mục source từ máy dev vào LAN

Khuyến nghị tối thiểu:

- 4 vCPU
- 8 GB RAM
- 80 GB SSD

---

## 5. Chuẩn bị Ubuntu 26.04

```bash
sudo apt update
sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
sudo apt install -y ca-certificates curl gnupg lsb-release git jq unzip
```

Nếu dùng `ufw`, chỉ mở port LAN cần dùng:

### Nếu chạy HTTP-only

```bash
sudo ufw allow OpenSSH
sudo ufw allow from 172.16.2.0/24 to any port 80 proto tcp
sudo ufw enable
sudo ufw status
```

### Nếu chạy HTTPS nội bộ

```bash
sudo ufw allow OpenSSH
sudo ufw allow from 172.16.2.0/24 to any port 80 proto tcp
sudo ufw allow from 172.16.2.0/24 to any port 443 proto tcp
sudo ufw enable
sudo ufw status
```

CIDR `172.16.2.0/24` ở trên chỉ là ví dụ theo IP bạn đã cung cấp. Nếu subnet LAN thực tế khác, cần thay lại cho đúng.

---

## 6. Cài Docker và Docker Compose plugin

### 6.1. Add Docker repo

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

### 6.2. Install Docker

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo docker version
sudo docker compose version
```

### 6.3. Add user vào group docker

```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps
```

---

## 7. Chuẩn bị source

```bash
sudo mkdir -p /opt/hrms
sudo chown -R $USER:$USER /opt/hrms
git clone <repo-url> /opt/hrms
cd /opt/hrms
cp .env.example .env
chmod 600 .env
```

---

## 8. Cấu hình `.env` cho LAN

### 8.1. Biến bắt buộc

Lưu ý:

- `.env.example` hiện đã để mặc định image local:
  - `BACKEND_IMAGE=hrms-backend`
  - `FRONTEND_IMAGE=hrms-frontend`
  - `BACKUP_IMAGE=hrms-backup`
  - `IMAGE_TAG=local`
- với kịch bản LAN nội bộ, nên giữ tư duy này: **build local trước, rồi compose chạy bằng tag local**
- không đổi sang `ghcr.io/...` trừ khi bạn chủ động chọn flow registry-based

```env
ENVIRONMENT=lan
DEBUG=false

POSTGRES_USER=postgres
POSTGRES_PASSWORD=<mat-khau-manh>
POSTGRES_DB=hrms

SECRET_KEY=<random-64-hex>
ENCRYPTION_KEY=<fernet-key>
REDIS_PASSWORD=<random-strong-password>

BACKEND_IMAGE=hrms-backend
FRONTEND_IMAGE=hrms-frontend
BACKUP_IMAGE=hrms-backup
IMAGE_TAG=local

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<minio-access-key-noi-bo>
MINIO_SECRET_KEY=<minio-secret-key-noi-bo>
MINIO_SECURE=false
MINIO_BUCKET=hrms-attachments-lan

BOOTSTRAP_ADMIN_EMAIL=admin@company.local
BOOTSTRAP_ADMIN_FULL_NAME=System Administrator
BOOTSTRAP_ADMIN_PASSWORD=<mat-khau-admin-dau-tien>
```

Lệnh sinh `MINIO_ACCESS_KEY` và `MINIO_SECRET_KEY` trên Ubuntu:

```bash
python3 - <<'PY'
import secrets
print("MINIO_ACCESS_KEY=" + secrets.token_hex(12))
print("MINIO_SECRET_KEY=" + secrets.token_hex(24))
PY
```

Ghi chú:

- `MINIO_ACCESS_KEY` ở đây sinh ra 24 ký tự hex
- `MINIO_SECRET_KEY` ở đây sinh ra 48 ký tự hex
- có thể copy trực tiếp 2 dòng output vào file `.env`

Giải thích:

- `docker-compose.lan.yml` và `docker-compose.prod.yml` hiện dùng `image: ${...}:${IMAGE_TAG}`
- vì vậy khi build local, chỉ cần build image với đúng tag:
  - `hrms-backend:local`
  - `hrms-frontend:local`
  - `hrms-backup:local`

### 8.2. `CORS_ORIGINS` và `REFRESH_TOKEN_COOKIE_SECURE`

#### Nếu chạy HTTPS nội bộ

```env
CORS_ORIGINS=["https://hrms.honghafeed.com.vn"]
REFRESH_TOKEN_COOKIE_SECURE=true
```

#### Nếu muốn chạy HTTP-only nội bộ

```env
ENVIRONMENT=lan
CORS_ORIGINS=["http://hrms.honghafeed.com.vn","http://172.16.2.100"]
REFRESH_TOKEN_COOKIE_SECURE=false
```

Nếu user truy cập bằng nhiều hostname/IP khác nhau, phải khai báo đủ tất cả origin hợp lệ trong `CORS_ORIGINS`.

---

## 9. Phương án A — HTTPS nội bộ

### 9.1. Giữ nguyên `nginx/conf.d/default.conf`

Với phương án này, có thể giữ nguyên logic Nginx hiện tại vì source đã hỗ trợ sẵn:

- HTTP redirect sang HTTPS
- reverse proxy frontend/backend

### 9.2. Chuẩn bị certificate nội bộ

Source hiện tại yêu cầu:

```text
nginx/ssl/fullchain.pem
nginx/ssl/privkey.pem
```

Tạo thư mục:

```bash
mkdir -p nginx/ssl
chmod 700 nginx/ssl
```

Có 2 cách:

1. dùng certificate do CA nội bộ doanh nghiệp cấp
2. dùng self-signed certificate

Ví dụ self-signed cho LAN:

```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=hrms.honghafeed.com.vn"
```

Lưu ý:

- self-signed sẽ tạo cảnh báo trên browser nếu máy user chưa trust cert

### 9.3. Cấu hình `hosts` trên máy user khi không có DNS nội bộ

Vì công ty bạn không có domain nội bộ hoặc DNS nội bộ, có thể dùng file `hosts` trên từng máy user để map hostname về IP tĩnh của server.

Windows:

```text
C:\Windows\System32\drivers\etc\hosts
```

Linux/macOS:

```text
/etc/hosts
```

Thêm dòng:

```text
172.16.2.100 hrms.honghafeed.com.vn
```

Sau đó user truy cập bằng:

- `http://hrms.honghafeed.com.vn`
- hoặc `https://hrms.honghafeed.com.vn`

tùy theo mode HTTP/HTTPS bạn chọn.

### 9.4. Sửa `server_name`

Trong [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf), đổi:

```nginx
server_name _;
```

thành:

```nginx
server_name hrms.honghafeed.com.vn 172.16.2.100;
```

---

## 10. Phương án B — HTTP-only nội bộ

Phương án này giờ đã có sẵn artifact riêng trong repo:

- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)
- [nginx/conf.d/default.lan-http.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.lan-http.conf)

Không cần sửa tay `docker-compose.prod.yml`.

### 10.1. Tạo file cấu hình Nginx riêng cho LAN

File này đã tồn tại sẵn:

- [nginx/conf.d/default.lan-http.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.lan-http.conf)

### 10.2. Đổi file Nginx được mount

Không cần sửa tay file nào nếu chạy bằng:

- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)

Vì file này đã mount trực tiếp:

- `./nginx/conf.d/default.lan-http.conf -> /etc/nginx/conf.d/default.conf`

### 10.3. Không cần thư mục SSL cho HTTP-only

Với phương án HTTP-only:

- không cần `nginx/ssl/fullchain.pem`
- không cần `nginx/ssl/privkey.pem`
- không dùng `certbot`

---

## 11. Build image local và khởi động stack

Phần này là flow **ưu tiên** cho server nội bộ IP tĩnh không public.

### 11.1. Build image local trên server

Từ thư mục source `/opt/hrms`:

```bash
docker build -t hrms-backend:local ./backend
docker build -t hrms-frontend:local ./frontend
docker build -t hrms-backup:local -f docker/backup/Dockerfile .
```

Lưu ý:

- backend image phải được build lại sau mỗi lần thay đổi dependency Python
- nếu trước đó đã build một image cũ thiếu `gunicorn`, cần rebuild lại backend image trước khi `docker compose up -d`

Kiểm tra image đã có:

```bash
docker images | grep hrms-
```

### 11.2. Start stack

#### Nếu chạy HTTPS nội bộ

```bash
docker compose -f docker-compose.prod.yml up -d
```

#### Nếu chạy HTTP-only nội bộ

```bash
docker compose -f docker-compose.lan.yml up -d
```

### 11.3. Migrate và seed

#### Nếu chạy HTTPS nội bộ

```bash
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds --bootstrap
docker compose -f docker-compose.prod.yml exec -T backend python -m app.seeds --bootstrap-admin
```

#### Nếu chạy HTTP-only nội bộ

```bash
docker compose -f docker-compose.lan.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.lan.yml exec -T backend python -m app.seeds
docker compose -f docker-compose.lan.yml exec -T backend python -m app.seeds --bootstrap
docker compose -f docker-compose.lan.yml exec -T backend python -m app.seeds --bootstrap-admin
```

### 11.4. Troubleshooting nhanh

Nếu `docker compose -f docker-compose.lan.yml up -d` báo lỗi:

```text
exec: "gunicorn": executable file not found in $PATH
```

thì nguyên nhân là backend image đang được build từ một state chưa có `gunicorn`.

Chạy lại:

```bash
docker build --no-cache -t hrms-backend:local ./backend
docker compose -f docker-compose.lan.yml up -d
```

### 11.5. Khi nào mới dùng GHCR

Chỉ dùng GHCR nếu bạn chủ động chọn flow registry-based.

Ví dụ:

```bash
echo '<registry-token>' | docker login ghcr.io -u <username> --password-stdin
docker pull ghcr.io/nguyencuonghut/hrms/hrms-backend:<tag>
docker pull ghcr.io/nguyencuonghut/hrms/hrms-frontend:<tag>
docker pull ghcr.io/nguyencuonghut/hrms/hrms-backup:<tag>
```

Sau đó sửa `.env`:

```env
BACKEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backend
FRONTEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-frontend
BACKUP_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backup
IMAGE_TAG=<tag-da-push>
```

---

## 12. User trong LAN sẽ truy cập bằng gì

Đã xác nhận từ source:

- FE production không public `5173`
- public entrypoint là `nginx`

Nên user trong LAN sẽ truy cập bằng:

### Nếu HTTPS nội bộ

- `https://hrms.honghafeed.com.vn`
- `https://172.16.2.100`

### Nếu HTTP-only nội bộ

- `http://hrms.honghafeed.com.vn`
- `http://172.16.2.100`

Không truy cập bằng:

- `http://172.16.2.100:5173`

trừ khi tự chạy dev server Vite, nhưng đó không phải flow deploy LAN theo `docker-compose.prod.yml` hoặc `docker-compose.lan.yml`.

---

## 13. Kiểm tra sau deploy

### 13.1. Kiểm tra container

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail=100
docker compose -f docker-compose.prod.yml logs nginx --tail=100
docker compose -f docker-compose.prod.yml logs celery_worker --tail=100
docker compose -f docker-compose.prod.yml logs celery_beat --tail=100
docker compose -f docker-compose.prod.yml logs backup_scheduler --tail=100
```

Nếu chạy HTTP-only nội bộ, thay `docker-compose.prod.yml` bằng `docker-compose.lan.yml`.

### 13.2. Kiểm tra HTTP/HTTPS từ chính server

#### Nếu HTTPS nội bộ

```bash
curl -kI https://127.0.0.1
curl -kI https://127.0.0.1/health
```

#### Nếu HTTP-only nội bộ

```bash
curl -I http://127.0.0.1
curl -I http://127.0.0.1/health
```

### 13.3. Kiểm tra từ máy user trong LAN

Ví dụ:

```bash
curl -I http://172.16.2.100
```

hoặc:

```bash
curl -kI https://172.16.2.100
```

### 13.4. Kiểm tra đăng nhập

1. mở URL LAN
2. đăng nhập bằng bootstrap admin
3. mở một vài màn chính
4. upload thử một file

---

## 14. Backup trên server nội bộ

Trong LAN deployment hiện tại:

- `backup_scheduler` không chạy mặc định
- muốn bật backup phải dùng profile `backup`

Ví dụ:

```bash
docker compose -f docker-compose.lan.yml --profile backup up -d
```

Khi bật profile này, vẫn cần cấu hình:

- `BACKUP_STORAGE_ENDPOINT`
- `BACKUP_STORAGE_ACCESS_KEY`
- `BACKUP_STORAGE_SECRET_KEY`
- `BACKUP_STORAGE_BUCKET`

Nếu hệ thống LAN chưa có object storage backup riêng, cứ để profile này tắt trong giai đoạn pilot/go-live ban đầu.

Cần kiểm tra log khi đã bật profile:

```bash
docker compose -f docker-compose.lan.yml --profile backup logs backup_scheduler --tail=200
```

---

## 15. Known gaps cho kịch bản LAN

### Đã xác nhận

1. source hiện tại mặc định ưu tiên HTTPS
2. `docker-compose.lan.yml` hiện hỗ trợ `ENVIRONMENT=lan` cho HTTP-only nội bộ
3. FE production không dùng port `5173`
4. `REFRESH_TOKEN_COOKIE_SECURE` phải khớp với HTTP/HTTPS thực tế
5. `docker-compose.lan.yml` có service `minio` nội bộ
6. `backup_scheduler` trong LAN hiện là optional profile, không chạy mặc định
7. runtime verify cục bộ cho `db + redis + minio + backend` đã cho `backend` trạng thái `healthy`

### Chưa xác nhận trong tài liệu này

1. chưa verify trực tiếp flow LAN trên một server Ubuntu 26.04 thật trong turn này
2. chưa verify certificate nội bộ cụ thể của doanh nghiệp
3. chưa verify backup target nội bộ của doanh nghiệp
4. chưa verify trực tiếp artifact `docker-compose.lan.yml` trên server Ubuntu 26.04 thật trong turn này

---

## 16. Khuyến nghị thực tế

Nếu cần lên nhanh trong LAN:

1. dùng **HTTP-only nội bộ**
2. set `ENVIRONMENT=lan`
3. set `REFRESH_TOKEN_COOKIE_SECURE=false`
4. khai báo `CORS_ORIGINS` đúng theo hostname/IP mà user thực sự dùng
5. build image local ngay trên server
6. deploy bằng [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)
7. chạy deploy **ngay trên server nội bộ** hoặc bằng **self-hosted runner trong LAN**
8. chỉ bật profile `backup` khi đã có cấu hình backup destination

Nếu cần vận hành lâu dài:

1. dùng **HTTPS nội bộ**
2. cấp cert nội bộ
3. chuẩn hóa DNS nội bộ
4. vẫn ưu tiên build local hoặc self-hosted runner
5. nếu vẫn muốn CD tự động từ GitHub, dùng **self-hosted runner**
6. chỉ dùng GHCR khi thật sự cần quản lý image qua registry

### 16.1. Checklist khi gặp lỗi `container hrms-backend-1 is unhealthy`

Chạy đúng 3 lệnh này trên server:

```bash
docker compose -f docker-compose.lan.yml ps
docker compose -f docker-compose.lan.yml logs backend --tail=200
docker inspect hrms-backend-1 --format '{{json .State.Health}}'
```

Với source hiện tại, 3 nguyên nhân phải kiểm tra đầu tiên là:

1. `ENVIRONMENT` trong `.env` không phải `lan` hoặc bị override ngoài ý muốn
2. `CORS_ORIGINS` không phải JSON array hợp lệ
3. image local đang cũ, chưa rebuild theo source mới
