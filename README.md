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

**Kết nối DB từ DBeaver / TablePlus (máy host):**

| Trường | Giá trị |
|---|---|
| Host | `localhost` |
| Port | `5433` ← dùng 5433 để tránh xung đột Postgres local (5432) |
| Database | `hrms` |
| Username | `postgres` |
| Password | `password` (hoặc theo `.env`) |

**Redis** expose tại `localhost:6380` (local Redis mặc định vẫn ở 6379).

**Tài khoản test mặc định:**

| Trường | Giá trị |
|---|---|
| Tên đăng nhập | `admin` |
| Mật khẩu | `admin` |

---

## Chạy Migration Database

Sau khi stack đã chạy, mở terminal khác và chạy:

```bash
# Tạo migration mới (khi thêm model mới)
docker compose exec backend alembic revision --autogenerate -m "tên migration"

# Áp dụng migration
docker compose exec backend alembic upgrade head

# Xem lịch sử migration
docker compose exec backend alembic history
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
sudo ss -tlnp | grep -E '5173|8000|5432|6379'

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
├── docker-compose.yml          Dev
├── docker-compose.prod.yml     Production
└── .env.example
```

Chi tiết tech stack: [docs/TECHSTACK.md](docs/TECHSTACK.md)  
Danh sách tính năng: [docs/FEATURES.md](docs/FEATURES.md)
