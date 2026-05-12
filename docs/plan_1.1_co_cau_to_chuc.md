# Kế hoạch thực hiện — 1.1. Cơ cấu Tổ chức

**Phạm vi:** Phòng/Ban (cây phân cấp) · Chức danh · Vị trí công việc · Lịch sử thay đổi  
**Ràng buộc:** Không có Chi nhánh · UI tiếng Việt có dấu · Toast/error do BE định nghĩa · Required field có dấu `*` đỏ

---

## Điều chỉnh Router & Menu so với stub hiện tại

| Route cũ | Thay đổi |
|---|---|
| `org/branches` → `BranchListView` | Đổi thành `org/job-titles` → `JobTitleListView` (Chức danh) |
| `org/departments` → `DepartmentListView` | Giữ, thay nội dung stub |
| `org/positions` → `PositionListView` | Giữ, thay nội dung stub |
| _(chưa có)_ | Thêm `org/history` → `OrgHistoryView` (Lịch sử) |

Menu section "Cơ cấu tổ chức" cập nhật: bỏ **Chi nhánh**, thêm **Chức danh** và **Lịch sử thay đổi**.

---

## Schema DB

> **Lưu ý thiết kế lương BHXH:** Không lưu số tiền cứng (`default_bhxh_salary`). Thay bằng
> `default_grade` + bảng hệ số động. Lương BHXH tính = `LTTV_vùng × hệ_số_bậc + phụ_cấp_BHXH`.
> Khi Nghị định mới ra, chỉ cần thêm dòng `regional_minimum_wages` — tất cả tự cập nhật.

```
-- ── Cơ cấu tổ chức ────────────────────────────────────────────────────

departments
  id            serial PK
  code          varchar(20) unique not null   -- VD: "PHONG_KT"
  name          varchar(200) not null
  short_name    varchar(50)
  parent_id     int FK → departments.id       -- NULL = phòng gốc
  order_no      int default 0
  is_active     bool default true
  created_at    timestamptz default now()
  updated_at    timestamptz

job_titles
  id            serial PK
  code          varchar(20) unique not null   -- VD: "GD", "TP", "NV"
  name          varchar(200) not null         -- VD: "Giám đốc"
  level         smallint default 1            -- 1 = cấp cao nhất
  is_active     bool default true
  created_at    timestamptz default now()
  updated_at    timestamptz

job_positions
  id                    serial PK
  code                  varchar(20) unique not null
  name                  varchar(200) not null
  department_id         int FK → departments.id not null
  job_title_id          int FK → job_titles.id
  default_grade         smallint default 1    -- bậc mặc định khi nhận vị trí
  bhxh_allowance        numeric(15,0) default 0   -- phụ cấp CÓ tính BHXH (chức vụ, trách nhiệm...)
  non_bhxh_allowance    numeric(15,0) default 0   -- phụ cấp KHÔNG tính BHXH (ăn ca, xăng xe...)
  description           text                 -- mô tả công việc
  requirements          text                 -- yêu cầu tuyển dụng
  is_active             bool default true
  created_at            timestamptz default now()
  updated_at            timestamptz

job_position_attachments
  id                serial PK
  job_position_id   int FK → job_positions.id on delete cascade
  file_name         varchar(255)
  file_path         varchar(500)
  file_size         int
  uploaded_at       timestamptz default now()

org_change_logs
  id            serial PK
  entity_type   varchar(30)                  -- 'department' | 'job_title' | 'job_position'
  entity_id     int
  entity_name   varchar(200)
  action        varchar(10)                  -- 'create' | 'update' | 'delete'
  changed_by    int FK → users.id
  changed_at    timestamptz default now()
  old_data      jsonb
  new_data      jsonb

-- ── Lương BHXH — Dữ liệu nguồn tính toán động ────────────────────────

regional_minimum_wages           -- Lịch sử mức lương tối thiểu vùng theo nghị định
  id               serial PK
  decree_number    varchar(50)   -- VD: "293/2025/NĐ-CP"
  region           smallint      -- 1 | 2 | 3 | 4
  amount           numeric(15,0) -- VD: 4.140.000 (Vùng III)
  effective_from   date NOT NULL
  effective_to     date          -- NULL = đang hiệu lực
  note             text

company_bhxh_region              -- Vùng BHXH hiện tại của công ty (lịch sử thay đổi)
  id               serial PK
  region           smallint NOT NULL
  effective_from   date NOT NULL
  effective_to     date          -- NULL = đang áp dụng
  note             text          -- VD: "Đang áp dụng"

salary_scales                    -- Phiên bản thang bảng lương (thường theo năm)
  id               serial PK
  name             varchar(200)  -- VD: "Thang bảng lương 2026"
  effective_from   date NOT NULL
  effective_to     date
  note             text

salary_scale_entries             -- Hệ số bậc lương theo từng chức danh
  id               serial PK
  salary_scale_id  int FK → salary_scales.id
  job_title_id     int FK → job_titles.id
  grade_no         smallint      -- Bậc 1, 2, 3...
  coefficient      numeric(6,4)  -- VD: 2.68 (Chủ tịch Bậc 1)
  promotion_months smallint      -- Tháng tối thiểu trước khi nâng lên bậc tiếp theo
  criteria         text          -- Điều kiện đạt bậc này (yêu cầu pháp lý)
```

### Công thức tính lương BHXH (tính tại thời điểm t)

Có **2 loại** mức lương BHXH theo nhân viên — được lưu ở cấp **hợp đồng lao động** (section 4), không phải cấp vị trí:

| Loại | Trường hợp | Cách tính |
|---|---|---|
| `computed` | Nhân viên tuyển mới theo thang bảng lương | `LTTV × hệ_số_bậc + bhxh_allowance` |
| `fixed` | FDI transfer, thỏa thuận riêng, mức cũ giữ nguyên | Dùng `bhxh_salary_fixed` ghi trong hợp đồng |

```
-- Loại 'computed':
LTTV      = regional_minimum_wages.amount   (lọc theo vùng công ty + ngày t)
HeSo      = salary_scale_entries.coefficient (lọc theo job_title + grade + scale ngày t)
LuongBHXH = MIN(46_800_000,  LTTV × HeSo + contracts.bhxh_allowance)

-- Loại 'fixed' (FDI transfer, thỏa thuận đặc biệt):
LuongBHXH = MIN(46_800_000,  contracts.bhxh_salary_fixed)
            -- Ràng buộc: bhxh_salary_fixed >= LTTV_vung (validate khi nhập)
```

**Trường override lưu ở `contracts` (section 4 — Hợp đồng lao động):**
```
contracts
  ...
  bhxh_salary_type    varchar(10)   -- 'computed' | 'fixed'
  bhxh_salary_fixed   numeric(15,0) -- chỉ dùng khi type = 'fixed'
  bhxh_grade          smallint      -- bậc của nhân viên này (có thể khác default_grade của vị trí)
  bhxh_allowance      numeric(15,0) -- phụ cấp BHXH thực tế ghi trong HĐ (có thể khác vị trí)
  ...
```

> **Tại sao đặt ở contract, không phải employee?**  
> Khi tái ký hợp đồng, loại/mức có thể thay đổi (FDI transfer có thể sau 1 năm chuyển sang computed).  
> Lịch sử mức lương BHXH = lịch sử hợp đồng → không cần bảng riêng.

> **Trần BHXH:** 20 × mức_tham_chiếu = 20 × 2.340.000 = **46.800.000 VND/tháng** (Luật BHXH 2024)

---

## Bước 1 — Models & Migration

**Mục tiêu:** Tạo đầy đủ bảng DB, không có UI.

### Backend
| File | Nội dung |
|---|---|
| `app/models/org.py` | SQLModel table classes: `Department`, `JobTitle`, `JobPosition`, `JobPositionAttachment`, `OrgChangeLog` |
| `app/models/salary.py` | `RegionalMinimumWage`, `CompanyBhxhRegion`, `SalaryScale`, `SalaryScaleEntry` |
| `app/models/__init__.py` | Export tất cả models (để Alembic detect) |
| `alembic/versions/0001_create_org_tables.py` | Migration tạo 9 bảng trên |
| `alembic/versions/0002_seed_minimum_wages.py` | Seed dữ liệu Nghị định 293/2025/NĐ-CP (4 vùng) + vùng công ty |

**Verify:** `alembic upgrade head` → không lỗi; `regional_minimum_wages` có 4 dòng trong DBeaver.

---

## Bước 2 — Phòng/Ban: Backend CRUD

**Mục tiêu:** API Phòng/Ban hoạt động, test được qua Swagger `/api/docs`.

### Backend
| File | Nội dung |
|---|---|
| `app/schemas/department.py` | `DepartmentCreate`, `DepartmentUpdate`, `DepartmentRead`, `DepartmentTreeNode` |
| `app/services/department_service.py` | `get_list()`, `get_tree()`, `create()`, `update()`, `delete()` |
| `app/api/v1/endpoints/departments.py` | Router: 5 endpoints bên dưới |
| `app/api/v1/router.py` | `include_router(departments.router, ...)` |

**Endpoints:**
```
GET    /api/v1/departments        list phẳng, query: is_active
GET    /api/v1/departments/tree   cây phân cấp đệ quy
POST   /api/v1/departments        tạo mới
PUT    /api/v1/departments/{id}   cập nhật
DELETE /api/v1/departments/{id}   xóa (chặn nếu còn con hoặc có nhân viên)
```

**Verify:** Gọi `POST` → `GET /tree` → thấy node đúng.

---

## Bước 3 — Phòng/Ban: Frontend UI

**Mục tiêu:** Trang `/org/departments` hoạt động hoàn chỉnh end-to-end.

### Frontend
| File | Nội dung |
|---|---|
| `src/services/departmentService.ts` | Wrap axios: `getTree()`, `create()`, `update()`, `remove()` |
| `src/views/org/DepartmentListView.vue` | Thay toàn bộ stub — xem chi tiết bên dưới |

**UI layout:**
```
┌─ Phòng / Ban ────────────────────────────── [+ Thêm phòng/ban] ─┐
│ TreeTable                                                         │
│  ▾ Khối Quản lý              [Sửa] [Xóa]                        │
│    ▾ Phòng Kế toán           [Sửa] [Xóa]                        │
│      Bộ phận Thanh toán      [Sửa] [Xóa]                        │
└──────────────────────────────────────────────────────────────────┘
```

**Dialog thêm/sửa — các trường (required đánh `*`):**
- Mã phòng/ban `*`
- Tên phòng/ban `*`
- Tên viết tắt
- Phòng/ban cha _(dropdown tree, bỏ trống = cấp gốc)_
- Thứ tự hiển thị
- Trạng thái (toggle)

**Quy tắc xóa:** Nếu BE trả lỗi "còn phòng con" hoặc "đang có nhân viên" → hiện toast lỗi từ BE, không xóa.

**Verify:** Thêm → cây cập nhật; Sửa tên → hiển thị ngay; Xóa → biến mất.

---

## Bước 4 — Chức danh: Backend + Frontend

**Mục tiêu:** Trang `/org/job-titles` hoạt động, menu "Chi nhánh" → "Chức danh".

### Backend
| File | Nội dung |
|---|---|
| `app/schemas/job_title.py` | `JobTitleCreate`, `JobTitleUpdate`, `JobTitleRead` |
| `app/services/job_title_service.py` | `get_list()`, `create()`, `update()`, `delete()` |
| `app/api/v1/endpoints/job_titles.py` | CRUD 4 endpoints |
| `app/api/v1/router.py` | include router |

**Endpoints:**
```
GET    /api/v1/job-titles
POST   /api/v1/job-titles
PUT    /api/v1/job-titles/{id}
DELETE /api/v1/job-titles/{id}   chặn nếu đang dùng ở job_positions
```

### Frontend
| File | Nội dung |
|---|---|
| `src/services/jobTitleService.ts` | API calls |
| `src/views/org/JobTitleListView.vue` | Trang mới (thay BranchListView) |
| `src/router/index.ts` | Đổi `org/branches` → `org/job-titles`, component → `JobTitleListView` |
| `src/components/layout/AppMenu.vue` | Đổi label + route "Chi nhánh" → "Chức danh" |

**UI layout:**
```
┌─ Chức danh ─────────────────────────── [+ Thêm chức danh] ──────┐
│ DataTable: Mã | Tên chức danh | Cấp bậc | Trạng thái | Thao tác │
│ VD: GD  | Giám đốc         | 1      | ● Hoạt động | Sửa Xóa  │
└──────────────────────────────────────────────────────────────────┘
```

**Dialog — các trường:**
- Mã chức danh `*`
- Tên chức danh `*`
- Cấp bậc `*` _(số, 1 = cao nhất)_
- Trạng thái

---

## Bước 5 — Vị trí công việc: Backend + Frontend

**Mục tiêu:** Trang `/org/positions` hoạt động với đầy đủ fields cơ bản.

### Backend
| File | Nội dung |
|---|---|
| `app/schemas/job_position.py` | `JobPositionCreate`, `JobPositionUpdate`, `JobPositionRead`, `JobPositionListItem` |
| `app/services/job_position_service.py` | `get_list()`, `get_by_id()`, `create()`, `update()`, `delete()` |
| `app/api/v1/endpoints/job_positions.py` | 5 endpoints |
| `app/api/v1/router.py` | include router |

**Endpoints:**
```
GET    /api/v1/job-positions              query: department_id, is_active, search
GET    /api/v1/job-positions/{id}
POST   /api/v1/job-positions
PUT    /api/v1/job-positions/{id}
DELETE /api/v1/job-positions/{id}         chặn nếu đang có nhân viên giữ vị trí này
```

### Frontend
| File | Nội dung |
|---|---|
| `src/services/jobPositionService.ts` | API calls |
| `src/views/org/PositionListView.vue` | Thay stub |

**UI layout:**
```
┌─ Vị trí công việc ──────────── [Phòng ban ▼] [+ Thêm vị trí] ───┐
│ DataTable:                                                         │
│ Mã | Tên vị trí | Phòng ban | Chức danh | Lương BHXH | Trạng thái│
│ Thao tác: [Chi tiết] [Sửa] [Xóa]                                  │
└────────────────────────────────────────────────────────────────────┘
```

**Dialog thêm/sửa — các trường:**
- Mã vị trí `*`
- Tên vị trí `*`
- Phòng/Ban `*` _(dropdown)_
- Chức danh _(dropdown, optional)_
- Bậc mặc định `*` _(số nguyên, 1–N; N = số bậc của chức danh được chọn)_
- Phụ cấp tính BHXH _(số VND — phụ cấp chức vụ, trách nhiệm... ghi trong HĐLĐ)_
- Phụ cấp không tính BHXH _(số VND — ăn ca, xăng xe... tách dòng riêng trong HĐLĐ)_
- Mô tả công việc _(textarea)_
- Yêu cầu tuyển dụng _(textarea)_
- Trạng thái

**Hiển thị tính toán (read-only, cập nhật realtime khi chọn chức danh + bậc):**
```
Lương BHXH dự kiến = [LTTV Vùng III] × [Hệ số bậc N] + [Phụ cấp BHXH]
                   = 4.140.000 × 2.68 + 0 = 11.095.200 ₫/tháng
```
_(Dòng này chỉ hiển thị khi đã chọn Chức danh và có thang bảng lương đang hiệu lực)_

---

## Bước 6 — Vị trí công việc: File đính kèm

**Mục tiêu:** Upload/download file tiêu chuẩn tuyển dụng cho từng vị trí.

### Backend
| File | Nội dung |
|---|---|
| `app/core/storage.py` | Helper lưu file vào `storage/attachments/` trên server |
| Thêm vào `job_positions.py` | `POST /api/v1/job-positions/{id}/attachments` (upload) |
| | `DELETE /api/v1/job-positions/{id}/attachments/{att_id}` |
| `app/main.py` | Mount `StaticFiles` tại `/storage` |

### Frontend
| File | Nội dung |
|---|---|
| `src/components/FileAttachmentList.vue` | Component tái sử dụng: hiển thị danh sách file + upload + xóa |
| `src/views/org/PositionListView.vue` | Thêm tab/section "Tài liệu đính kèm" trong detail dialog |

---

## Bước 7 — Lịch sử thay đổi cơ cấu

**Mục tiêu:** Tự động ghi log mỗi khi Phòng/Ban hoặc Vị trí công việc bị tạo/sửa/xóa; xem được trên UI.

### Backend
| File | Nội dung |
|---|---|
| `app/services/org_log_service.py` | `log_change(entity_type, entity_id, entity_name, action, old, new, user_id)` |
| `app/services/department_service.py` | Gọi `log_change` trong create/update/delete |
| `app/services/job_position_service.py` | Gọi `log_change` trong create/update/delete |
| `app/api/v1/endpoints/org_history.py` | `GET /api/v1/org-history` — filter: entity_type, date_from, date_to |
| `app/api/v1/router.py` | include router |

### Frontend
| File | Nội dung |
|---|---|
| `src/services/orgHistoryService.ts` | API call |
| `src/views/org/OrgHistoryView.vue` | Trang mới |
| `src/router/index.ts` | Thêm route `org/history` → `OrgHistoryView` |
| `src/components/layout/AppMenu.vue` | Thêm mục "Lịch sử thay đổi" vào section Cơ cấu tổ chức |

**UI layout:**
```
┌─ Lịch sử thay đổi cơ cấu ── [Loại ▼] [Từ ngày] [Đến ngày] [Lọc] ─┐
│ DataTable:                                                            │
│ Thời gian | Đối tượng | Tên | Hành động | Người thực hiện | Chi tiết │
│ 12/05/2026 | Phòng/Ban | Phòng KT | Cập nhật | admin | [Xem] │
└──────────────────────────────────────────────────────────────────────┘
```
"Xem chi tiết" → Dialog hiển thị diff old_data / new_data dạng bảng so sánh.

---

## Tóm tắt file cần tạo/sửa

### Backend (mới tạo)
```
app/models/org.py
app/models/salary.py               -- RegionalMinimumWage, CompanyBhxhRegion, SalaryScale, SalaryScaleEntry
app/schemas/department.py
app/schemas/job_title.py
app/schemas/job_position.py
app/services/department_service.py
app/services/job_title_service.py
app/services/job_position_service.py
app/services/org_log_service.py
app/core/storage.py
app/api/v1/endpoints/departments.py
app/api/v1/endpoints/job_titles.py
app/api/v1/endpoints/job_positions.py
app/api/v1/endpoints/org_history.py
alembic/versions/0001_create_org_tables.py
```

### Backend (cập nhật)
```
app/models/__init__.py          -- export models
app/api/v1/router.py            -- include 4 routers mới
app/main.py                     -- mount StaticFiles (bước 6)
```

### Frontend (mới tạo)
```
src/services/departmentService.ts
src/services/jobTitleService.ts
src/services/jobPositionService.ts
src/services/orgHistoryService.ts
src/views/org/JobTitleListView.vue
src/views/org/OrgHistoryView.vue
src/components/FileAttachmentList.vue
```

### Frontend (cập nhật)
```
src/views/org/DepartmentListView.vue    -- thay stub
src/views/org/PositionListView.vue      -- thay stub
src/router/index.ts                     -- đổi branches→job-titles, thêm org/history
src/components/layout/AppMenu.vue       -- đổi menu
```
