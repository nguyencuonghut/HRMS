# TECH STACK — HRMS

**Phiên bản:** 1.0  
**Ngày:** 2026-05-12

---

## Backend

| Thành phần | Công nghệ | Phiên bản | Ghi chú |
|---|---|---|---|
| Web framework | **FastAPI** | 0.136.x (latest) | Async, tự động sinh OpenAPI docs |
| ORM / Schema | **SQLModel** | 0.0.38 (latest) | Kết hợp Pydantic v2 + SQLAlchemy |
| Database | **PostgreSQL** | 16+ | Primary database |
| Async DB driver | **asyncpg** | latest | Driver async cho PostgreSQL |
| DB Migration | **Alembic** | latest | Quản lý schema migration |
| ASGI Server | **Uvicorn** | latest | Chạy production với Gunicorn |
| Authentication | **python-jose** + **passlib** | latest | JWT token, bcrypt hash password |
| Validation | **Pydantic v2** | (kèm SQLModel) | Validate request/response |
| Task nền | **Celery** + **Redis** | latest | Gửi email, export file lớn, nhắc việc |
| API Docs | **Swagger UI / ReDoc** | (kèm FastAPI) | Tự động từ OpenAPI spec |
| Testing | **pytest** + **httpx** | latest | Unit test & integration test |
| Code quality | **Ruff** | latest | Linter + formatter thay thế Black/Flake8 |

---

## Frontend

| Thành phần | Công nghệ | Phiên bản | Ghi chú |
|---|---|---|---|
| Framework | **Vue 3** (Composition API) | 3.x (latest) | `<script setup>` syntax |
| Ngôn ngữ | **TypeScript** | 5.x | Strict mode |
| Build tool | **Vite** | latest | HMR nhanh, bundle tối ưu |
| UI Component | **PrimeVue** | v4 (latest) | DataTable, Form, Dialog, Chart,... |
| Icons | **PrimeIcons** | v4 (kèm PrimeVue) | |
| State management | **Pinia** | latest | Thay thế Vuex cho Vue 3 |
| Routing | **Vue Router** | v4 (latest) | |
| HTTP client | **Axios** | latest | Interceptors cho auth token |
| Form validation | **VeeValidate** + **Zod** | latest | Schema-based validation |
| Code quality | **ESLint** + **Prettier** | latest | Vue/TS rules |

---

## Hạ tầng & DevOps

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| Container | **Docker** + **Docker Compose** | Môi trường dev, staging, production |
| Reverse proxy | **Nginx** | Serve FE static, proxy API |
| Cache / Broker | **Redis** | Session cache, Celery message broker |
| Object Storage | **Garage** | Lưu trữ file đính kèm và bản sao lưu (S3-compatible) |
| Secrets | **`.env` file** | Tách biệt per environment (dev/staging/prod) |
| CI/CD | **GitHub Actions** | Build, test, deploy tự động |
| Log / Monitor | **Sentry** | Error tracking backend + frontend |

---

## Lưu trữ File (Object Storage)

### Garage

Dùng [Garage](https://garagehq.deuxfleurs.fr/) (v2.5.0, một nút, `sqlite` với `fsync` bật) — object storage S3-compatible, tự host. Thay MinIO từ kế hoạch 15.7 (`docs/plan_15.7_chuyen_minio_sang_garage.md`). Backend vẫn dùng SDK Python `minio` làm client S3, **phải truyền `region="garage"`** (Garage ký theo `s3_region` trong `docker/garage/garage.toml`).

| Thành phần | Giá trị (dev) |
|---|---|
| S3 API endpoint | `garage:3900`, chỉ trong mạng compose (không publish cổng ra host) |
| Web Console | Không có. Dùng CLI `docker compose exec garage /garage ...` |
| Bucket | `hrms-attachments-dev` (tệp ứng dụng), `hrms-backup` (sao lưu); production: `hrms-attachments-prod`, `hrms-backup` |
| Khóa truy cập | Hai khóa `hrms-app` và `hrms-backup`, sinh bằng `scripts/garage_bootstrap.sh`; không có mặc định |

Biến môi trường cấu hình trong `docker-compose.yml` → service `backend` (tên biến là `S3_*`; tên cũ `MINIO_*` đã được gỡ ở kế hoạch 15.7 Slice 10):

```
S3_ENDPOINT    = garage:3900       # đặt cứng trong docker-compose.yml
S3_ACCESS_KEY  = (khóa hrms-app, do scripts/garage_bootstrap.sh sinh)
S3_SECRET_KEY  = (như trên)
S3_REGION      = garage
S3_BUCKET      = hrms-attachments-dev   # production: hrms-attachments-prod
S3_SECURE      = false                  # lưu lượng chỉ đi trong mạng compose
BACKUP_STORAGE_*  = khóa hrms-backup, bucket hrms-backup (cùng Garage)
```

### Kiến trúc upload / download

```
Browser ──upload──▶ FastAPI ──put_object──▶ Garage
                                               │
Browser ◀──stream── FastAPI ◀──get_object──────┘
```

- **Upload**: `POST /api/v1/job-positions/{id}/attachments` — FastAPI nhận file, gọi `put_object()` (SDK `minio`), lưu `object_name` vào DB.
- **Download**: `GET /api/v1/job-positions/{id}/attachments/{att_id}/download` — FastAPI lấy stream từ Garage, proxy về browser bằng `StreamingResponse`.
- Object name trong DB theo dạng: `attachments/{position_id}/{uuid}_{filename}`.

> **Tại sao proxy qua FastAPI thay vì presigned URL?**  
> Trong Docker Compose, hostname `garage` chỉ resolve được bên trong mạng Docker (và cổng S3 không được publish).  
> Browser bên ngoài không truy cập được `garage:3900`.  
> Proxy qua FastAPI tránh được vấn đề này, đồng thời dễ thêm kiểm tra phân quyền sau này.

### Python package

```
minio>=7.2.0   # SDK client S3, khai báo trong backend/requirements.in (bản khóa ở requirements.txt: 7.2.20); dùng cho Garage
```

---

## Cấu trúc môi trường

```
├── backend/        # FastAPI app
│   └── app/core/storage.py   # S3 helper (ensure_bucket, save, stream, delete)
├── frontend/       # Vue 3 app
│   └── src/components/FileAttachmentList.vue
├── nginx/          # Nginx config
├── docker-compose.yml          # Dev (bao gồm Garage service)
├── docker-compose.prod.yml     # Production
└── .env.example
```

---

## Luồng xác thực

- **JWT Bearer Token** — Access token (15 phút) + Refresh token (7 ngày)
- Token lưu ở `httpOnly cookie` hoặc `localStorage` (cấu hình theo yêu cầu bảo mật)
- RBAC kiểm tra ở tầng FastAPI dependency injection

---

## Ghi chú phiên bản

- Ưu tiên dùng **phiên bản mới nhất ổn định** tại thời điểm bắt đầu phát triển
- Ghim phiên bản cụ thể trong `requirements.txt` (BE) và `package.json` (FE) trước khi vào production

    