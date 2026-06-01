# Hồng Hà HRMS

Hệ thống Quản lý Nhân sự — FastAPI + Vue 3 + PostgreSQL + Docker

---

## Yêu cầu hệ thống

| Công cụ | Phiên bản tối thiểu |
|---|---|
| Docker | 24+ |
| Docker Compose | v2.20+ (plugin, dùng `docker compose` không phải `docker-compose`) |
| Git | bất kỳ |

> Không cần cài Python hay Node.js trên máy — tất cả chạy trong container.

---

## Chạy môi trường Dev (lần đầu)

### Bước 1 — Clone và tạo file `.env`

```bash
git clone <repo-url>
cd HRMS
cp .env.example .env
```

File `.env` mặc định đã dùng được ngay cho dev. Không cần chỉnh gì thêm.

---

### Bước 2 — Build và khởi động toàn bộ stack

```bash
docker compose up --build
```

Lần đầu sẽ mất vài phút do Docker tải image và build. Các lần sau chỉ cần:

```bash
docker compose up
```

Khi thấy log tương tự bên dưới là tất cả đã sẵn sàng:

```
db        | database system is ready to accept connections
redis     | Ready to accept connections
backend   | Application startup complete.
frontend  | VITE v6.x  ready in xxx ms  ➜  Local: http://localhost:5173/
```

---

### Bước 3 — Truy cập ứng dụng

| Dịch vụ | URL |
|---|---|
| **Frontend (Vue 3)** | http://localhost:5173 |
| **Backend API Docs (Swagger)** | http://localhost:8000/api/docs |
| **Backend API Docs (ReDoc)** | http://localhost:8000/api/redoc |
| **Health check** | http://localhost:8000/health |
| **MinIO Web Console** | http://localhost:9001 |

**Kết nối DB từ DBeaver / TablePlus (máy host):**

| Trường | Giá trị |
|---|---|
| Host | `localhost` |
| Port | `5433` ← dùng 5433 để tránh xung đột Postgres local (5432) |
| Database | `hrms` |
| Username | `postgres` |
| Password | `postgres` (theo `.env`) |

**MinIO** (Object Storage cho file đính kèm):

| Trường | Giá trị |
|---|---|
| S3 API | `localhost:9000` |
| Web Console | http://localhost:9001 (user: `minioadmin` / pass: `minioadmin`) |
| Bucket mặc định | `hrms-attachments` |

**Redis** expose tại `localhost:6380` (local Redis mặc định vẫn ở 6379).

**Tài khoản test mặc định:**

| Trường | Giá trị |
|---|---|
| Tên đăng nhập | `admin` |
| Mật khẩu | `admin` |

---

## Chạy Migration và Seed

Sau khi stack đã chạy, dùng lệnh `make` (xem đầy đủ với `make help`):

```bash
make migrate          # Áp dụng tất cả migration còn pending
make seed-required    # Seed baseline production (required + RBAC core)
make seed-bootstrap   # Seed thêm bootstrap data vận hành
make seed-local-users # Seed 5 tài khoản local dev/test
make seed-sample      # Seed full dev/test
make seed             # Alias dev = seed-sample

make migrate-status   # Xem migration hiện tại đang ở revision nào
make migrate-down     # Rollback 1 migration gần nhất
make migrate-new m=tên_migration   # Tạo file migration mới
```

### Flow khuyến nghị theo môi trường

```bash
# Production sạch
make migrate
make seed-required
make seed-bootstrap

# Development / test local
make migrate
make seed
```

---

## Build lại từ đầu khi thay đổi `.env`

> **Lưu ý quan trọng:** PostgreSQL ghi password vào **data volume** ngay lần khởi động đầu tiên.
> Nếu sau đó bạn đổi `POSTGRES_PASSWORD` trong `.env` rồi chỉ restart container thì password
> trong DB **không thay đổi** — phải xóa volume và khởi tạo lại.

### Khi nào cần làm theo hướng dẫn này?

- Đổi `POSTGRES_PASSWORD`, `POSTGRES_USER`, hoặc `POSTGRES_DB` trong `.env`
- Muốn reset DB sạch hoàn toàn (xóa toàn bộ data)
- Lỗi kết nối DB do password không khớp

### Các bước

```bash
# 1. Dừng tất cả container VÀ xóa volume data (mất toàn bộ data DB)
docker compose down -v

# 2. Chỉnh .env theo ý muốn (nếu chưa chỉnh)
#    Ví dụ: POSTGRES_PASSWORD=postgres

# 3. Build lại image và khởi động
docker compose up --build -d

# 4. Chờ DB healthy rồi chạy migration
make migrate

# 5. Seed dữ liệu
make seed
```

> Nếu chỉ đổi biến không liên quan đến DB (như `SECRET_KEY`, `DEBUG`):
> chỉ cần `docker compose restart backend` — **không cần** `down -v`.

### Sửa nhanh nếu không muốn mất data

Trường hợp volume đã có data và chỉ muốn đồng bộ lại password (không xóa data):

```bash
# Thay 'matkhaumoi' bằng POSTGRES_PASSWORD trong .env của bạn
docker compose exec db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'matkhaumoi';"
```

---

## Các lệnh thường dùng

### Khởi động / Dừng

```bash
# Khởi động (chạy nền)
docker compose up -d

# Xem log realtime
docker compose logs -f

# Xem log của một service cụ thể
docker compose logs -f backend
docker compose logs -f frontend

# Dừng tất cả (giữ data)
docker compose stop

# Dừng và xóa container (giữ volume data)
docker compose down

# Dừng, xóa container VÀ xóa toàn bộ data DB
docker compose down -v
```

### Vào shell container

```bash
# Shell backend (Python)
docker compose exec backend bash

# Shell database (psql)
docker compose exec db psql -U postgres -d hrms

# Shell Redis
docker compose exec redis redis-cli

# MinIO — kiểm tra bucket và object
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc ls local/hrms-attachments
```

### Cài thêm package

```bash
# Backend — thêm vào requirements.txt rồi rebuild
docker compose build backend
docker compose up -d backend

# Frontend — chạy npm install trong container
docker compose exec frontend npm install <package-name>
```

---

## Hot Reload

Cả backend lẫn frontend đều hỗ trợ hot reload trong dev:

- **Backend**: Uvicorn chạy với `--reload`, tự restart khi thay đổi file `.py`
- **Frontend**: Vite HMR, thay đổi file `.vue`/`.ts` cập nhật ngay trên trình duyệt

Không cần restart container sau khi sửa code.

---

## Xử lý sự cố thường gặp

### Port bị chiếm

```bash
# Kiểm tra process đang dùng port
sudo ss -tlnp | grep -E '5173|8000|5432|5433|6379|6380|9000|9001'

# Đổi port trong docker-compose.yml nếu cần, ví dụ:
# ports: - "8001:8000"
```

### Frontend báo lỗi kết nối API

Kiểm tra backend đã chạy chưa:

```bash
docker compose ps
curl http://localhost:8000/health
```

### Database lỗi kết nối

```bash
# Xem log DB
docker compose logs db

# Kiểm tra container đang chạy
docker compose ps db
```

### MinIO lỗi kết nối / không upload được

```bash
# Kiểm tra MinIO đang chạy và healthy
docker compose ps minio
docker compose logs minio

# Kiểm tra bucket đã được tạo chưa (backend tự tạo khi khởi động)
docker compose exec backend python -c "from app.core.storage import ensure_bucket; ensure_bucket(); print('OK')"

# Nếu backend khởi động trước khi MinIO healthy, restart backend
docker compose restart backend
```

### Reset hoàn toàn để bắt đầu lại

```bash
docker compose down -v --remove-orphans
docker compose up --build
```

---

## Cấu trúc dự án

```
HRMS/
├── backend/            FastAPI + SQLModel + Alembic
├── frontend/           Vue 3 + PrimeVue v4 + TypeScript
├── nginx/              Cấu hình reverse proxy (production)
├── docs/               Tài liệu dự án
├── docker-compose.yml          Dev (PostgreSQL · Redis · MinIO · Backend · Frontend)
├── docker-compose.prod.yml     Production
└── .env.example
```

Chi tiết tech stack: [docs/TECHSTACK.md](docs/TECHSTACK.md)  
Danh sách tính năng: [docs/FEATURES.md](docs/FEATURES.md)
