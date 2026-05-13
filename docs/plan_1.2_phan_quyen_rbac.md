# Kế hoạch thực hiện — 1.2. Phân quyền (RBAC)

**Phạm vi:** User · Role · Permission · Phạm vi tổ chức · Audit log · Quản lý tài khoản  
**Ràng buộc:** Auth hiện tại là JWT cứng (admin/admin, không có DB). Cần thay hoàn toàn. Không phá vỡ các endpoint đang hoạt động cho đến khi guard được bật.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| JWT access/refresh token (`security.py`) | ✅ Có sẵn |
| Login endpoint (`POST /auth/login`) | ⚠️ Hardcoded `admin/admin`, không dùng DB |
| User model trong DB | ❌ Chưa có |
| Role / Permission model | ❌ Chưa có |
| Dependency `get_current_user` | ❌ Chưa có |
| Permission guard trên endpoint | ❌ Chưa có |
| Audit log tổng quát | ⚠️ Chỉ có `OrgChangeLog` cho org, chưa có log chung |
| `OrgChangeLog.changed_by` | ⚠️ Nullable int, chưa có FK thực đến users |

---

## Schema DB

```sql
-- ── Xác thực & Phân quyền ────────────────────────────────────────────────────

users
  id              serial PK
  email           varchar(200) unique not null   -- dùng làm login identifier
  full_name       varchar(200) not null
  hashed_password text not null
  is_active       bool default true
  is_superuser    bool default false   -- bypass mọi permission check (chỉ admin hệ thống)
  employee_id     int FK → employees.id nullable   -- liên kết hồ sơ nhân viên (Phase 2+)
  last_login_at   timestamptz
  created_at      timestamptz default now()
  updated_at      timestamptz

roles
  id          serial PK
  code        varchar(50)  unique not null   -- 'admin' | 'hr_manager' | 'hr_officer' | 'line_manager' | 'finance'
  name        varchar(200) not null          -- 'Quản trị viên' | 'HR Manager' ...
  description text
  is_system   bool default false             -- role hệ thống mặc định, không xóa được
  created_at  timestamptz default now()

permissions
  id          serial PK
  code        varchar(100) unique not null   -- '{module}:{action}' — vd: 'employees:view'
  name        varchar(200) not null          -- 'Xem danh sách nhân viên'
  module      varchar(50)  not null          -- 'org' | 'employees' | 'contracts' | ...
  action      varchar(20)  not null          -- 'view' | 'create' | 'edit' | 'delete' | 'export'
  description text

role_permissions
  role_id       int FK → roles.id        ON DELETE CASCADE
  permission_id int FK → permissions.id  ON DELETE CASCADE
  PRIMARY KEY (role_id, permission_id)

user_roles
  user_id         int FK → users.id   ON DELETE CASCADE
  role_id         int FK → roles.id   ON DELETE CASCADE
  -- Phạm vi tổ chức: NULL scope_type = toàn công ty
  scope_type      varchar(20) nullable   -- 'company' | 'department'
  department_ids  int[]       nullable   -- danh sách phòng ban được phép (khi scope_type='department')
  PRIMARY KEY (user_id, role_id)

audit_logs
  id          bigserial PK
  user_id     int FK → users.id nullable   -- NULL nếu chưa đăng nhập hoặc system action
  action      varchar(50) not null         -- 'LOGIN' | 'CREATE' | 'UPDATE' | 'DELETE' | 'EXPORT' | 'VIEW_SENSITIVE'
  entity_type varchar(50) nullable         -- 'employee' | 'contract' | 'user' | 'role' | ...
  entity_id   int nullable
  entity_name varchar(200) nullable
  old_data    jsonb nullable
  new_data    jsonb nullable
  ip_address  varchar(45) nullable
  user_agent  text nullable
  created_at  timestamptz default now()
  -- Index: (user_id), (entity_type, entity_id), (created_at DESC)
```

### Roles & Permissions mặc định (seed)

| Role | Permissions |
|---|---|
| `admin` | `*` — toàn bộ (via `is_superuser=true` trên user admin) |
| `hr_manager` | Toàn bộ org, employees, contracts, leaves, insurance, salary, rewards, training, performance, reports, audit_logs:view |
| `hr_officer` | `*:view` + `*:create` + `*:edit` trừ users/roles/audit. Export: có |
| `line_manager` | `employees:view`, `leaves:view`, `leaves:create`, `performance:*` — giới hạn phòng ban |
| `finance` | `insurance:*`, `salary:*`, `reports:view`, `reports:export` |

### Danh sách permissions (seeded, không sửa qua API)

Modules: `org` · `employees` · `contracts` · `leaves` · `insurance` · `salary` · `rewards` · `training` · `performance` · `reports` · `users` · `roles` · `audit_logs`  
Actions: `view` · `create` · `edit` · `delete` · `export`

---

## Bước 1 — DB Models & Migration

**Mục tiêu:** Tạo 6 bảng mới, seed dữ liệu roles/permissions mặc định.

**Files tạo mới:**
- `backend/app/models/auth.py` — User, Role, Permission, RolePermission, UserRole, AuditLog
- `backend/app/seeds/rbac.py` — seed roles, permissions, user admin mặc định

**Thay đổi:**
- `backend/app/models/__init__.py` — import models mới để Alembic detect
- `backend/app/core/database.py` — chạy `create_all` hoặc tạo Alembic migration mới
- `backend/app/main.py` — gọi seed trong lifespan (chỉ nếu chưa có dữ liệu)

**Seed admin mặc định:**
```
email: admin@hrms.local
password: Admin@123  (đổi ngay sau khi deploy)
is_superuser: true
role: admin
```

**Tests:** `backend/tests/test_auth_models.py`
- Tạo user, role, permission — kiểm tra lưu/đọc đúng
- Gán role cho user, kiểm tra user_roles
- is_superuser bypass permission check (unit test trên service)

---

## Bước 2 — Auth Foundation (thay login cứng)

**Mục tiêu:** Login thật từ DB. JWT chứa `user_id` + `roles`. Dependency `get_current_user`.

**Files tạo mới:**
- `backend/app/services/auth_service.py`
  - `get_user_by_email(session, email) → User | None`
  - `authenticate_user(session, email, password) → User | None`
  - `get_user_permissions(session, user_id) → set[str]`
  - `log_audit(session, user_id, action, entity_type, entity_id, ...)` — helper ghi audit

**Files sửa:**
- `backend/app/core/security.py`
  - `create_access_token(subject: str, extra_claims: dict)` — thêm `user_id`, `roles` vào payload
  - `decode_token(token: str) → dict` — giải mã JWT

- `backend/app/api/v1/endpoints/auth.py`
  - `POST /auth/login` — xác thực từ DB, trả token có claims
  - `POST /auth/refresh` — dùng refresh token, cấp access token mới
  - `GET /auth/me` — trả thông tin user hiện tại (từ JWT)
  - `POST /auth/change-password` — đổi mật khẩu (cần old_password)

**Files tạo mới:**
- `backend/app/api/v1/deps.py` — FastAPI dependencies
  ```python
  async def get_current_user(token: str = Depends(oauth2_scheme), session = Depends(get_session)) -> User
  async def get_current_active_user(user = Depends(get_current_user)) -> User
  def require_permission(*perms: str):  # returns Depends
      """Trả dependency kiểm tra user có ít nhất 1 trong các permission được liệt kê."""
  ```

**Tích hợp `changed_by` vào OrgChangeLog:**
- Sửa `department_service.py`, `job_title_service.py`, `job_position_service.py`
- Truyền `current_user.id` vào `_log()` thay vì `None`

**Tests:** `backend/tests/test_auth.py`
- Login đúng → 200 + token
- Login sai → 401
- GET /auth/me với token hợp lệ → 200 + user info
- GET /auth/me không token → 401
- Refresh token hợp lệ → token mới
- Refresh token hết hạn → 401
- Đổi mật khẩu đúng → 200; sai mật khẩu cũ → 400

---

## Bước 3 — User Management APIs

**Mục tiêu:** CRUD người dùng hệ thống. Chỉ admin/hr_manager được quản lý.

**File tạo mới:**
- `backend/app/services/user_service.py`
- `backend/app/schemas/user.py` — UserCreate, UserUpdate, UserRead, UserListItem
- `backend/app/api/v1/endpoints/users.py`

**Endpoints:**

| Method | URL | Permission | Mô tả |
|---|---|---|---|
| GET | `/users` | `users:view` | Danh sách users (phân trang, lọc) |
| POST | `/users` | `users:create` | Tạo user mới |
| GET | `/users/{id}` | `users:view` | Xem chi tiết user |
| PUT | `/users/{id}` | `users:edit` | Sửa thông tin user |
| DELETE | `/users/{id}` | `users:delete` | Vô hiệu hóa user (soft delete: `is_active=false`) |
| POST | `/users/{id}/reset-password` | `users:edit` | Admin đặt lại mật khẩu |
| GET | `/users/{id}/roles` | `users:view` | Xem roles của user |
| POST | `/users/{id}/roles` | `users:edit` | Gán role cho user (kèm scope) |
| DELETE | `/users/{id}/roles/{role_id}` | `users:edit` | Bỏ role khỏi user |

**Validation:**
- `email`: unique, format email hợp lệ — dùng làm login identifier
- `password`: min 8 ký tự, có chữ + số (khi tạo mới)
- Không được xóa/vô hiệu hóa chính mình
- Không được xóa user là `is_superuser=true` trừ chính superuser khác

**Tests:** `backend/tests/test_users.py` — CRUD đầy đủ, validation, permission check

---

## Bước 4 — Role & Permission Management APIs

**Mục tiêu:** Quản lý roles và gán permissions. Chỉ admin.

**File tạo mới:**
- `backend/app/services/role_service.py`
- `backend/app/schemas/role.py` — RoleCreate, RoleUpdate, RoleRead, PermissionRead
- `backend/app/api/v1/endpoints/roles.py`

**Endpoints:**

| Method | URL | Permission | Mô tả |
|---|---|---|---|
| GET | `/roles` | `roles:view` | Danh sách roles |
| POST | `/roles` | `roles:create` | Tạo role mới |
| GET | `/roles/{id}` | `roles:view` | Chi tiết role + permissions |
| PUT | `/roles/{id}` | `roles:edit` | Sửa tên/mô tả role |
| DELETE | `/roles/{id}` | `roles:delete` | Xóa role (không xóa được `is_system=true`) |
| GET | `/roles/{id}/permissions` | `roles:view` | Danh sách permissions của role |
| PUT | `/roles/{id}/permissions` | `roles:edit` | Cập nhật toàn bộ permissions của role (replace) |
| GET | `/permissions` | `roles:view` | Danh sách tất cả permissions (để render permission matrix) |

**Tests:** `backend/tests/test_roles.py`

---

## Bước 5 — Audit Log API

**Mục tiêu:** Xem lịch sử thao tác toàn hệ thống.

**File tạo mới:**
- `backend/app/api/v1/endpoints/audit_logs.py`

**Endpoints:**

| Method | URL | Permission | Mô tả |
|---|---|---|---|
| GET | `/audit-logs` | `audit_logs:view` | Danh sách audit log (lọc theo user, action, entity, ngày) |

**Params lọc:** `user_id`, `action`, `entity_type`, `entity_id`, `date_from`, `date_to`, `limit` (max 500)

**Tích hợp ghi audit vào endpoints hiện có:**
- Login / Logout → `LOGIN` / `LOGOUT`
- Create/Update/Delete trên org, employees, contracts,... → `CREATE` / `UPDATE` / `DELETE`
- Export → `EXPORT`
- Đặt lại mật khẩu → `RESET_PASSWORD`

**Tests:** `backend/tests/test_audit_logs.py`

---

## Bước 6 — Frontend: User Management

**Mục tiêu:** Trang quản lý tài khoản người dùng.

**Files tạo mới:**
- `frontend/src/views/admin/UserListView.vue`
  - DataTable: full_name, email, roles (Tags), is_active, last_login_at
  - Toolbar: tìm kiếm, nút Thêm, nút Làm mới
  - Actions: Sửa, Đặt lại MK, Vô hiệu hóa
- `frontend/src/views/admin/UserFormDialog.vue`
  - Tạo mới: email, full_name, password, confirm_password
  - Sửa: email, full_name, is_active (không đổi password tại đây)
- `frontend/src/views/admin/UserRoleDialog.vue`
  - Gán/bỏ roles cho user
  - Chọn scope: Toàn công ty / Phòng ban cụ thể (MultiSelect departments)
- `frontend/src/services/userService.ts`

**Router:** `admin/users` → `UserListView`  
**Menu:** Thêm section "Quản trị hệ thống" → item "Tài khoản người dùng"

---

## Bước 7 — Frontend: Role Management

**Mục tiêu:** Trang quản lý vai trò và phân quyền.

**Files tạo mới:**
- `frontend/src/views/admin/RoleListView.vue`
  - DataTable: code, name, số permissions, is_system, actions
  - Nút Thêm role mới
- `frontend/src/views/admin/RoleFormDialog.vue`
  - Tạo/sửa role: code, name, description
- `frontend/src/views/admin/PermissionMatrixDialog.vue`
  - Bảng Ma trận quyền:
    - Hàng: modules (Cơ cấu tổ chức, Nhân sự, Hợp đồng,...)
    - Cột: actions (Xem, Thêm, Sửa, Xóa, Xuất)
    - Cell: Checkbox
  - Nút Lưu → `PUT /roles/{id}/permissions`
- `frontend/src/services/roleService.ts`

**Router:** `admin/roles` → `RoleListView`  
**Menu:** Section "Quản trị hệ thống" → item "Vai trò & Quyền"

---

## Bước 8 — Frontend: Audit Log

**Mục tiêu:** Trang xem lịch sử audit toàn hệ thống.

**Files tạo mới:**
- `frontend/src/views/admin/AuditLogView.vue`
  - DataTable: Thời gian, Người thực hiện, Hành động (Tag severity), Đối tượng, Chi tiết (eye icon)
  - Toolbar lọc: user, action, entity_type, date range
  - Dialog chi tiết: hiển thị diff old_data/new_data (tái dùng logic từ OrgHistoryView)
- `frontend/src/services/auditLogService.ts`

**Router:** `admin/audit-logs` → `AuditLogView`  
**Menu:** Section "Quản trị hệ thống" → item "Nhật ký hệ thống"

---

## Bước 9 — Gắn Permission Guard vào endpoints hiện có

**Mục tiêu:** Bật kiểm tra quyền trên toàn bộ endpoints đã có (org, sau đó mở rộng).

**Thứ tự ưu tiên:**
1. Org endpoints (`departments`, `job_titles`, `job_positions`, `org_history`) → `org:*`
2. Sau đó áp dụng cho các module còn lại khi triển khai từng module

**Pattern áp dụng:**
```python
@router.get("")
async def list_departments(
    _: User = Depends(require_permission("org:view")),
    session: AsyncSession = Depends(get_session),
):
```

**Frontend — hiển thị/ẩn theo quyền:**
- `frontend/src/composables/usePermission.ts`
  - `hasPermission(perm: string): boolean`
  - `canView(module: string): boolean`
- Ẩn nút Thêm/Sửa/Xóa nếu không có quyền
- Ẩn menu item nếu không có quyền xem module

---

## Thứ tự thực hiện & Dependencies

```
Bước 1 (DB) → Bước 2 (Auth) → Bước 3 (Users API)
                            ↓
                     Bước 4 (Roles API)
                            ↓
                     Bước 5 (Audit Log)
                            ↓
              Bước 6 → Bước 7 → Bước 8 (Frontend)
                            ↓
                     Bước 9 (Guards)
```

Bước 3 và 4 có thể làm song song sau khi Bước 2 xong.  
Bước 6, 7, 8 có thể làm song song sau khi Bước 3, 4, 5 xong.

---

## Quyết định thiết kế

| Vấn đề | Quyết định | Lý do |
|---|---|---|
| Token format | JWT với claims `user_id`, `roles: [code]` | Stateless, không cần DB lookup mỗi request |
| Permission check | Check từ DB mỗi request (cache trong scope request) | Đảm bảo cập nhật ngay khi thu hồi quyền |
| Soft delete user | `is_active=false`, không xóa vật lý | Giữ FK integrity với audit_logs |
| Scope phòng ban | `department_ids: int[]` trên user_roles | Đủ cho Line Manager, không over-engineer |
| Permissions | Seeded, không tạo qua UI | Permissions là code contract, không phải cấu hình |
| Audit log | Table riêng (`audit_logs`), không dùng `OrgChangeLog` | `OrgChangeLog` chỉ dùng cho org history view, audit_log dùng cho security |
| Password policy | Min 8 ký tự, có chữ + số | Đủ mạnh cho internal app, không quá phức tạp |
| Token blacklist | Không implement (dùng short-lived access token 15 phút) | Đơn giản hóa, refresh token đủ dài |

---

## Cấu trúc file sau khi hoàn thành

```
backend/app/
├── models/
│   ├── auth.py          ← MỚI: User, Role, Permission, RolePermission, UserRole, AuditLog
│   └── org.py           (cập nhật: OrgChangeLog.changed_by có FK thực)
├── schemas/
│   ├── user.py          ← MỚI
│   └── role.py          ← MỚI
├── services/
│   ├── auth_service.py  ← MỚI
│   ├── user_service.py  ← MỚI
│   └── role_service.py  ← MỚI
├── api/v1/
│   ├── deps.py          ← MỚI: get_current_user, require_permission
│   └── endpoints/
│       ├── auth.py      (sửa: login thật, thêm /me, /refresh, /change-password)
│       ├── users.py     ← MỚI
│       ├── roles.py     ← MỚI
│       └── audit_logs.py ← MỚI
└── seeds/
    └── rbac.py          ← MỚI: seed roles, permissions, admin user

frontend/src/
├── views/admin/
│   ├── UserListView.vue        ← MỚI
│   ├── UserFormDialog.vue      ← MỚI
│   ├── UserRoleDialog.vue      ← MỚI
│   ├── RoleListView.vue        ← MỚI
│   ├── RoleFormDialog.vue      ← MỚI
│   ├── PermissionMatrixDialog.vue ← MỚI
│   └── AuditLogView.vue        ← MỚI
├── services/
│   ├── userService.ts          ← MỚI
│   └── roleService.ts          ← MỚI
└── composables/
    └── usePermission.ts        ← MỚI
```

---

## Acceptance Criteria

- [ ] Login bằng tài khoản lưu trong DB, JWT có `user_id` + `roles`
- [ ] `GET /auth/me` trả đúng thông tin user + danh sách roles
- [ ] Admin tạo/sửa/vô hiệu hóa user được
- [ ] Gán/bỏ role cho user với scope phòng ban hoạt động đúng
- [ ] Permission matrix UI cho phép tick quyền từng module × action
- [ ] Endpoint org trả 403 nếu không có quyền tương ứng
- [ ] Line manager chỉ xem được dữ liệu phòng ban của mình
- [ ] Audit log ghi đầy đủ CREATE/UPDATE/DELETE/LOGIN
- [ ] Superuser bypass permission check
- [ ] Không thể xóa role `is_system=true`
- [ ] Không thể vô hiệu hóa chính mình
- [ ] Tất cả tests pass (target: >90% coverage trên auth/user/role services)
