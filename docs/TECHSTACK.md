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
| Secrets | **`.env` file** | Tách biệt per environment (dev/staging/prod) |
| CI/CD | **GitHub Actions** | Build, test, deploy tự động |
| Log / Monitor | **Sentry** | Error tracking backend + frontend |

---

## Cấu trúc môi trường

```
├── backend/        # FastAPI app
├── frontend/       # Vue 3 app
├── nginx/          # Nginx config
├── docker-compose.yml          # Dev
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
