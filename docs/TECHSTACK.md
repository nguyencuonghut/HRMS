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
| Object Storage | **MinIO** | Lưu trữ file đính kèm (S3-compatible) |
| Secrets | **`.env` file** | Tách biệt per environment (dev/staging/prod) |
| CI/CD | **GitHub Actions** | Build, test, deploy tự động |
| Log / Monitor | **Sentry** | Error tracking backend + frontend |

---

## Lưu trữ File (Object Storage)

### MinIO

Dùng [MinIO](https://min.io/) — object storage S3-compatible, tự host.

| Thành phần | Giá trị mặc định (dev) |
|---|---|
| S3 API endpoint | `http://localhost:9000` |
| Web Console | `http://localhost:9001` |
| Bucket | `hrms-attachments` |
| Access Key | `minioadmin` |
| Secret Key | `minioadmin` |

Biến môi trường cấu hình trong `docker-compose.yml` → service `backend`:

```
MINIO_ENDPOINT    = minio:9000        # internal Docker hostname
MINIO_ACCESS_KEY  = minioadmin
MINIO_SECRET_KEY  = minioadmin
MINIO_BUCKET      = hrms-attachments
MINIO_SECURE      = false
```

### Kiến trúc upload / download

```
Browser ──upload──▶ FastAPI ──put_object──▶ MinIO
                                               │
Browser ◀──stream── FastAPI ◀──get_object──────┘
```

- **Upload**: `POST /api/v1/job-positions/{id}/attachments` — FastAPI nhận file, gọi `minio.put_object()`, lưu `object_name` vào DB.
- **Download**: `GET /api/v1/job-positions/{id}/attachments/{att_id}/download` — FastAPI lấy stream từ MinIO, proxy về browser bằng `StreamingResponse`.
- Object name trong DB theo dạng: `attachments/{position_id}/{uuid}_{filename}`.

> **Tại sao proxy qua FastAPI thay vì presigned URL?**  
> Trong Docker Compose, hostname `minio` chỉ resolve được bên trong mạng Docker.  
> Browser bên ngoài không truy cập được `http://minio:9000/...`.  
> Proxy qua FastAPI tránh được vấn đề này, đồng thời dễ thêm kiểm tra phân quyền sau này.

### Python package

```
minio>=7.2.0   # thêm vào backend/requirements.txt
```

---

## Cấu trúc môi trường

```
├── backend/        # FastAPI app
│   └── app/core/storage.py   # MinIO helper (ensure_bucket, save, stream, delete)
├── frontend/       # Vue 3 app
│   └── src/components/FileAttachmentList.vue
├── nginx/          # Nginx config
├── docker-compose.yml          # Dev (bao gồm MinIO service)
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

    