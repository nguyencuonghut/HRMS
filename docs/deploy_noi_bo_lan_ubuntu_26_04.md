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

Source hiện tại **có thể dùng để deploy trên mạng LAN**, nhưng có một khác biệt rất quan trọng:

- cấu hình Nginx hiện tại trong source **mặc định redirect từ HTTP sang HTTPS**
- và block HTTPS hiện tại **bắt buộc có certificate**

Điều này đã được xác nhận từ [nginx/conf.d/default.conf](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/nginx/conf.d/default.conf):

- `listen 80` trả `301 https://$host$request_uri`
- `listen 443 ssl`
- yêu cầu:
  - `/etc/nginx/ssl/fullchain.pem`
  - `/etc/nginx/ssl/privkey.pem`

Vì vậy, khi chạy nội bộ LAN có 2 phương án:

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

Lưu ý:

- với HTTP-only, `REFRESH_TOKEN_COOKIE_SECURE` **không được để `true`**
- nếu để `true`, browser sẽ không gửi secure cookie qua HTTP

Điểm này được xác nhận từ [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example):

- dev HTTP local dùng `REFRESH_TOKEN_COOKIE_SECURE=false`
- production HTTPS dùng `REFRESH_TOKEN_COOKIE_SECURE=true`

---

## 3. Kiến trúc LAN hiện tại

Theo [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml), stack LAN vẫn dùng cùng kiến trúc production:

- `db`
- `redis`
- `backend`
- `celery_worker`
- `celery_beat`
- `frontend`
- `backup_scheduler`
- `nginx`

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
- outbound internet nếu cần pull image từ registry

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

```env
ENVIRONMENT=production
DEBUG=false

POSTGRES_USER=postgres
POSTGRES_PASSWORD=<mat-khau-manh>
POSTGRES_DB=hrms

SECRET_KEY=<random-64-hex>
ENCRYPTION_KEY=<fernet-key>
REDIS_PASSWORD=<random-strong-password>

BACKEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backend
FRONTEND_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-frontend
BACKUP_IMAGE=ghcr.io/nguyencuonghut/hrms/hrms-backup
IMAGE_TAG=<commit-sha-hoac-tag>

MINIO_ENDPOINT=<object-storage-endpoint>
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_SECURE=<true-hoac-false>
MINIO_BUCKET=hrms-attachments-prod

BOOTSTRAP_ADMIN_EMAIL=admin@company.local
BOOTSTRAP_ADMIN_FULL_NAME=System Administrator
BOOTSTRAP_ADMIN_PASSWORD=<mat-khau-admin-dau-tien>
```

### 8.2. `CORS_ORIGINS` và `REFRESH_TOKEN_COOKIE_SECURE`

#### Nếu chạy HTTPS nội bộ

```env
CORS_ORIGINS=["https://hrms.honghafeed.com.vn"]
REFRESH_TOKEN_COOKIE_SECURE=true
```

#### Nếu chạy HTTP-only nội bộ

```env
CORS_ORIGINS=["http://hrms.honghafeed.com.vn","http://172.16.2.100"]
REFRESH_TOKEN_COOKIE_SECURE=false
```

Nếu user truy cập bằng nhiều hostname/IP khác nhau, phải khai báo đủ tất cả origin hợp lệ trong `CORS_ORIGINS`.

Ví dụ:

```env
CORS_ORIGINS=["http://hrms.honghafeed.com.vn","http://172.16.2.100"]
```

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

## 11. Pull image và khởi động stack

### 11.1. Login registry nếu image private

```bash
echo '<registry-token>' | docker login ghcr.io -u <username> --password-stdin
```

### 11.2. Pull image

```bash
docker pull ${BACKEND_IMAGE}:${IMAGE_TAG}
docker pull ${FRONTEND_IMAGE}:${IMAGE_TAG}
docker pull ${BACKUP_IMAGE}:${IMAGE_TAG}
```

### 11.3. Start stack

#### Nếu chạy HTTPS nội bộ

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

#### Nếu chạy HTTP-only nội bộ

```bash
docker compose -f docker-compose.lan.yml pull
docker compose -f docker-compose.lan.yml up -d
```

### 11.4. Migrate và seed

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

Source hiện tại vẫn có `backup_scheduler` trong LAN deployment.

Đã xác nhận từ:

- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml)
- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)

- `backup_scheduler` luôn có trong stack
- backup DB và object storage vẫn dùng các biến:
  - `BACKUP_STORAGE_ENDPOINT`
  - `BACKUP_STORAGE_ACCESS_KEY`
  - `BACKUP_STORAGE_SECRET_KEY`
  - `BACKUP_STORAGE_BUCKET`

Nếu hệ thống LAN không có object storage backup riêng, service này có thể không chạy đúng. Phần này không phải suy đoán logic nghiệp vụ, mà là yêu cầu cấu hình trực tiếp từ source hiện tại.

Cần kiểm tra log:

```bash
docker compose -f docker-compose.prod.yml logs backup_scheduler --tail=200
```

Nếu chạy HTTP-only nội bộ, thay `docker-compose.prod.yml` bằng `docker-compose.lan.yml`.

---

## 15. Known gaps cho kịch bản LAN

### Đã xác nhận

1. source hiện tại mặc định ưu tiên HTTPS
2. HTTP-only nội bộ đã có artifact riêng, không cần sửa tay file production
3. FE production không dùng port `5173`
4. `REFRESH_TOKEN_COOKIE_SECURE` phải khớp với HTTP/HTTPS thực tế

### Chưa xác nhận trong tài liệu này

1. chưa verify trực tiếp flow LAN trên một server Ubuntu 26.04 thật trong turn này
2. chưa verify certificate nội bộ cụ thể của doanh nghiệp
3. chưa verify backup target nội bộ của doanh nghiệp
4. chưa verify trực tiếp artifact `docker-compose.lan.yml` trên server Ubuntu 26.04 thật trong turn này

---

## 16. Khuyến nghị thực tế

Nếu cần lên nhanh trong LAN:

1. dùng **HTTP-only nội bộ**
2. set `REFRESH_TOKEN_COOKIE_SECURE=false`
3. khai báo `CORS_ORIGINS` đúng theo IP/hostname LAN
4. deploy bằng [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)

Nếu cần vận hành lâu dài:

1. dùng **HTTPS nội bộ**
2. cấp cert nội bộ
3. chuẩn hóa DNS nội bộ
4. sau đó giữ gần như nguyên flow của tài liệu production public
