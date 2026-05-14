# Kế hoạch thực hiện — 2.1. Danh mục hành chính

**Phạm vi:** Tỉnh/Thành phố · Quận/Huyện · Xã/Phường · Hệ hành chính cũ/mới · Import dữ liệu chính thức  
**Ràng buộc:** Phải hỗ trợ song song 2 cách nhập địa chỉ cho hồ sơ nhân sự; không phá cấu trúc router/menu hiện có; ưu tiên bám pattern CRUD đang dùng ở backend FastAPI + frontend Vue/PrimeVue.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| `docs/FEATURES.md` có yêu cầu 2.1 | ✅ Có |
| Module `Catalog` trên FE | ⚠️ Mới là placeholder `CatalogView.vue` |
| Model / schema / service / endpoint cho danh mục hành chính | ❌ Chưa có |
| Cơ chế import dữ liệu danh mục | ❌ Chưa có |
| API phục vụ chọn địa chỉ cho hồ sơ nhân sự | ❌ Chưa có |
| Pattern CRUD + test tích hợp ở backend | ✅ Đã có sẵn từ `departments`, `job_titles`, `roles` |

### Nhận định triển khai

- Codebase hiện đã có sẵn khuôn chuẩn để mở rộng thêm một module danh mục mới:
  `models` → `schemas` → `services` → `api/v1/endpoints` → `frontend/services` → `frontend/views`.
- Điểm khó chính của `2.1` không phải CRUD đơn thuần, mà là mô hình dữ liệu phải biểu diễn được **cùng một đơn vị hành chính trong nhiều hệ phân cấp khác nhau**.
- Vì `3.1 Hồ sơ nhân sự` sẽ dùng lại danh mục này, API cần thiết kế theo hướng **tra cứu/phân cấp/phục vụ dropdown**, không chỉ phục vụ màn quản trị.

---

## Mục tiêu nghiệp vụ

1. Quản lý dữ liệu hành chính Việt Nam theo **hệ cũ**:
   `Tỉnh/Thành phố → Quận/Huyện → Xã/Phường`
2. Quản lý dữ liệu theo **hệ mới**:
   `Tỉnh/Thành phố → Xã/Phường`
3. Cho phép hồ sơ nhân sự lưu **đồng thời** địa chỉ theo hệ cũ và hệ mới cho cùng một loại địa chỉ, nhưng vẫn truy vết được độc lập từng hệ về sau.
4. Có cơ chế import/cập nhật từ dữ liệu chính thức, tránh nhập tay số lượng lớn.
5. Có khả năng đánh dấu hiệu lực dữ liệu theo thời gian để không mất lịch sử khi thay đổi địa giới hành chính.

---

## Thiết kế dữ liệu đề xuất

### Nguyên tắc

- **Tách “đơn vị hành chính” khỏi “quan hệ phân cấp”**.
- Một xã/phường có thể tham gia nhiều cây phân cấp theo từng hệ hành chính hoặc từng đợt cập nhật.
- Không hardcode riêng 2 bộ bảng old/new, vì sẽ khó đồng bộ và khó dùng lại cho hồ sơ nhân sự.

### Schema DB

```sql
administrative_units
  id               serial PK
  code             varchar(20) unique not null   -- mã chính thức/nguồn import
  name             varchar(255) not null
  normalized_name  varchar(255) not null         -- tên bỏ dấu/phục vụ search
  unit_type        varchar(20) not null          -- 'province' | 'district' | 'ward'
  official_name    varchar(255)                  -- tên đầy đủ nếu cần
  province_code    varchar(20)                   -- denormalized để filter nhanh
  is_active        bool default true
  effective_from   date
  effective_to     date
  source_name      varchar(100)                  -- ví dụ: 'official_import'
  source_version   varchar(50)                   -- ví dụ: '2026-05'
  created_at       timestamptz default now()
  updated_at       timestamptz

administrative_hierarchies
  id               serial PK
  system_type      varchar(20) not null          -- 'old' | 'new'
  parent_unit_id   int FK → administrative_units.id
  child_unit_id    int FK → administrative_units.id
  level_depth      smallint not null             -- 1=tỉnh, 2=quận, 3=xã trong hệ cũ
  effective_from   date
  effective_to     date
  is_active        bool default true
  UNIQUE(system_type, parent_unit_id, child_unit_id, effective_from)

administrative_import_batches
  id               serial PK
  source_name      varchar(100) not null
  source_version   varchar(50) not null
  file_name        varchar(255)
  imported_by      int FK → users.id nullable
  imported_at      timestamptz default now()
  status           varchar(20) not null          -- 'draft' | 'success' | 'failed'
  total_rows       int default 0
  success_rows     int default 0
  failed_rows      int default 0
  error_summary    text

administrative_import_errors
  id               serial PK
  batch_id         int FK → administrative_import_batches.id on delete cascade
  row_no           int
  raw_payload      jsonb
  error_message    text
```

### Tích hợp với hồ sơ nhân sự

`employees` hoặc bảng địa chỉ nhân sự ở phase sau nên lưu theo hướng:

```sql
employee_addresses
  ...
  address_kind          varchar(20)   -- 'permanent' | 'contact' | ...
  address_system_type   varchar(20)   -- 'old' | 'new'
  province_unit_id      int FK → administrative_units.id
  district_unit_id      int FK → administrative_units.id nullable
  ward_unit_id          int FK → administrative_units.id
  address_line          varchar(255)
  ...
```

> `district_unit_id` được phép `NULL` khi dùng hệ mới.  
> Để lưu đồng thời cả hai hệ cho một nhân sự, cần ràng buộc dạng:
> `UNIQUE(employee_id, address_kind, address_system_type)`.
> Cách lưu này giữ được đúng dữ liệu người dùng đã chọn, không ép quy đổi giả.

---

## API mục tiêu

### Admin CRUD / Import

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/admin-units` | Danh sách đơn vị hành chính, có filter |
| GET | `/api/v1/admin-units/{id}` | Chi tiết một đơn vị |
| POST | `/api/v1/admin-units` | Tạo thủ công một đơn vị |
| PUT | `/api/v1/admin-units/{id}` | Cập nhật đơn vị |
| DELETE | `/api/v1/admin-units/{id}` | Soft delete / khóa |
| GET | `/api/v1/admin-hierarchies/tree` | Cây phân cấp theo `system_type=old|new` |
| POST | `/api/v1/admin-units/import` | Import file dữ liệu |
| GET | `/api/v1/admin-units/import-batches` | Lịch sử import |

### API phục vụ dropdown tra cứu

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/address-systems` | Trả danh sách hệ hành chính hỗ trợ |
| GET | `/api/v1/locations/provinces` | Danh sách tỉnh/thành |
| GET | `/api/v1/locations/children` | Lấy cấp con theo `parent_id` + `system_type` |
| GET | `/api/v1/locations/search` | Search theo tên/mã, có filter loại đơn vị |
| POST | `/api/v1/locations/validate-path` | Validate tổ hợp tỉnh/quận/xã theo hệ đã chọn |

### Query params quan trọng

- `system_type=old|new`
- `unit_type=province|district|ward`
- `parent_id`
- `is_active`
- `keyword`
- `effective_at`

---

## Bước 1 — Models & Migration

**Mục tiêu:** Có cấu trúc DB đủ để lưu đơn vị hành chính, quan hệ phân cấp theo hệ cũ/mới và lịch sử import.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/models/catalog.py` | `AdministrativeUnit`, `AdministrativeHierarchy`, `AdministrativeImportBatch`, `AdministrativeImportError` |
| `backend/app/models/__init__.py` | Export model mới để Alembic detect |
| `backend/alembic/versions/xxxx_create_administrative_catalog_tables.py` | Tạo 4 bảng mới + index |

### Index nên có

- `administrative_units(code)` unique
- `administrative_units(unit_type, is_active)`
- `administrative_units(normalized_name)`
- `administrative_hierarchies(system_type, parent_unit_id, is_active)`
- `administrative_hierarchies(system_type, child_unit_id, is_active)`

**Verify:** `alembic upgrade head` chạy sạch; DB có đủ 4 bảng và index.

---

## Bước 2 — Import Service & Seed dữ liệu ban đầu

**Mục tiêu:** Nạp được dữ liệu hành chính từ file nguồn và tạo được cả cây `old/new`.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/services/administrative_import_service.py` | Parse file, upsert đơn vị, upsert hierarchy, log batch/error |
| `backend/app/seeds/administrative_units.py` | Seed dữ liệu mẫu hoặc bootstrap dữ liệu chính thức |
| `backend/app/core/config.py` | Thêm biến cấu hình đường dẫn dữ liệu import mặc định nếu cần |

### Quy tắc import

1. Upsert theo `code`, không insert trùng.
2. Nếu cùng `code` nhưng tên thay đổi, lưu `updated_at` và cập nhật metadata nguồn.
3. Quan hệ phân cấp được xử lý riêng theo `system_type`.
4. Một batch import lỗi không được làm hỏng toàn bộ DB:
   phần thành công vẫn commit, phần lỗi ghi vào `administrative_import_errors`.
5. Cho phép import lặp lại cùng `source_version` theo mode:
   `replace` hoặc `merge`.

### Dữ liệu đầu vào đề xuất

- `CSV` hoặc `JSON` có cột tối thiểu:
  `system_type`, `province_code`, `district_code`, `ward_code`, `province_name`, `district_name`, `ward_name`
- Với hệ mới, `district_code` có thể rỗng.

**Verify:** Chạy import file mẫu, sau đó gọi API tree của cả `old` và `new` đều trả dữ liệu hợp lệ.

---

## Bước 3 — Schemas, Services, API

**Mục tiêu:** Mở API quản trị và API tra cứu để frontend và các module nghiệp vụ khác dùng lại.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/schemas/catalog.py` | `AdministrativeUnitCreate`, `AdministrativeUnitUpdate`, `AdministrativeUnitRead`, `AdministrativeTreeNode`, `ImportBatchRead` |
| `backend/app/services/administrative_unit_service.py` | CRUD, tree, search, validate-path |
| `backend/app/api/v1/endpoints/admin_units.py` | Router cho CRUD/import/query |
| `backend/app/api/v1/router.py` | Include router mới |

### Validation quan trọng

- `unit_type='province'` không có parent trong hierarchy.
- `unit_type='district'` chỉ được làm con của `province` ở hệ cũ.
- `unit_type='ward'`:
  ở hệ cũ là con của `district`, ở hệ mới có thể là con trực tiếp của `province`.
- Không tạo vòng lặp hierarchy.
- Không xóa một unit nếu còn hierarchy active hoặc đang được tham chiếu bởi hồ sơ địa chỉ.

### Test

| File | Nội dung |
|---|---|
| `backend/tests/test_administrative_units.py` | CRUD + filter + validate |
| `backend/tests/test_administrative_import.py` | Import success/fail/mixed |
| `backend/tests/test_location_lookup.py` | Tree lookup theo `old/new` |

**Verify:** Swagger `/api/docs` test được toàn bộ flow create → tree → search → validate-path.

---

## Bước 4 — Frontend quản trị trong khu vực Danh mục

**Mục tiêu:** Thay `CatalogView.vue` placeholder bằng màn thật cho danh mục hành chính.

### Điều chỉnh Router/Menu

| Thành phần | Thay đổi |
|---|---|
| `frontend/src/router/index.ts` | Tách `catalog` thành route con rõ nghĩa hoặc thêm route `catalog/administrative-units` |
| `frontend/src/components/layout/AppMenu.vue` | Đổi mục `Danh mục` từ 1 link đơn thành nhóm con nếu cần |
| `frontend/src/views/catalog/CatalogView.vue` | Không để placeholder; dùng làm trang điều hướng hoặc dashboard danh mục |

### Frontend files

| File | Nội dung |
|---|---|
| `frontend/src/services/administrativeUnitService.ts` | Axios wrapper cho list/tree/search/import |
| `frontend/src/views/catalog/AdministrativeUnitListView.vue` | Màn quản trị chính |
| `frontend/src/views/catalog/AdministrativeImportHistoryView.vue` | Lịch sử import |

### UI đề xuất

```text
┌─ Danh mục hành chính ─────────────────────────────────────── [Import dữ liệu] ┐
│ Hệ hành chính: [Cũ] [Mới]   Tìm kiếm: [.................]  [Chỉ hoạt động]   │
│                                                                              │
│ TreeTable                                                                    │
│  Tỉnh/Thành phố A                                                            │
│    Quận/Huyện B   (chỉ trong hệ cũ)                                          │
│      Xã/Phường C                                                             │
│    Xã/Phường D   (trực tiếp dưới tỉnh trong hệ mới)                          │
│                                                     [Sửa] [Khóa] [Xem lịch sử]│
└──────────────────────────────────────────────────────────────────────────────┘
```

### Chức năng UI

- Toggle giữa `Hệ cũ` và `Hệ mới`
- TreeTable xem phân cấp
- Search theo tên/mã
- Dialog thêm/sửa đơn vị hành chính
- Import file + hiển thị kết quả batch
- Cảnh báo khi tạo hierarchy không hợp lệ

**Verify:** FE thao tác được end-to-end với API thật, không còn màn placeholder.

---

## Bước 5 — Chuẩn bị tích hợp Hồ sơ nhân sự

**Mục tiêu:** Chốt contract để module `3.1 Thông tin cá nhân` dùng lại ngay khi triển khai, với yêu cầu lưu đồng thời cả `hệ cũ` và `hệ mới`.

### Yêu cầu tích hợp

- Form hồ sơ nhân sự phải hiển thị **đồng thời 2 cụm địa chỉ**:
  `Địa chỉ hệ cũ` và `Địa chỉ hệ mới`
- Cụm `Hệ cũ`: hiện 3 dropdown
  `Tỉnh/Thành` → `Quận/Huyện` → `Xã/Phường`
- Cụm `Hệ mới`: hiện 2 dropdown
  `Tỉnh/Thành` → `Xã/Phường`
- Khi mở hồ sơ đã lưu, hệ thống phải hydrate lại đúng cả hai hệ đã lưu, không tự chuyển đổi.
- Hai cụm địa chỉ được validate độc lập và có thể kiểm tra chung trước khi submit.

### Frontend dùng lại sau này

| File | Nội dung |
|---|---|
| `frontend/src/components/catalog/AdministrativeAddressPairSelector.vue` | Component chọn đồng thời địa chỉ hệ cũ + hệ mới |

### Backend dùng lại sau này

- `GET /locations/children`
- `GET /locations/search`
- `POST /locations/validate-path`
- `POST /locations/validate-dual-paths`

**Verify:** Có thể mock tích hợp vào form nhân sự mà không cần viết lại logic chọn địa chỉ; payload preview thể hiện đồng thời `old_address` và `new_address`.

---

## Bước 6 — Phân quyền, audit log, dữ liệu vận hành

**Mục tiêu:** Module này vận hành an toàn như các khu vực admin khác.

### RBAC đề xuất

| Permission | Ý nghĩa |
|---|---|
| `catalog:view` | Xem danh mục hành chính |
| `catalog:create` | Tạo mới |
| `catalog:edit` | Chỉnh sửa / khóa |
| `catalog:delete` | Xóa logic nếu cho phép |
| `catalog:import` | Import dữ liệu hành chính |

### Audit cần ghi

- Tạo/sửa/khóa đơn vị hành chính
- Import batch
- Import thất bại
- Thay đổi hierarchy giữa `old/new`

### Files liên quan

- `backend/app/api/v1/endpoints/admin_units.py`
- `backend/app/services/administrative_unit_service.py`
- `backend/app/services/administrative_import_service.py`
- `backend/app/services/auth_service.py` hoặc helper audit dùng chung

**Verify:** Có log thao tác trong `audit_logs` khi sửa danh mục hoặc import.

---

## Thứ tự triển khai khuyến nghị

1. Chốt schema `administrative_units` + `administrative_hierarchies`
2. Làm migration + test model
3. Làm import service + seed file mẫu
4. Mở API tree/search/validate-path
5. Xây màn quản trị FE trong `Danh mục`
6. Tạo component selector kép để tái sử dụng cho hồ sơ nhân sự
7. Bật RBAC + audit cho toàn bộ flow

---

## Rủi ro & lưu ý thiết kế

1. Nếu gộp luôn “đơn vị” và “quan hệ cha-con” vào một bảng duy nhất với `parent_id`, hệ mới và hệ cũ sẽ xung đột dữ liệu.
2. Import từ nguồn chính thức cần chuẩn hóa encoding, tên đơn vị, và mã đơn vị trước khi upsert.
3. Hồ sơ nhân sự không nên chỉ lưu text tên tỉnh/huyện/xã; phải lưu FK về danh mục để giữ tính nhất quán.
4. Nếu lưu đồng thời hệ cũ và hệ mới, không nên cố suy luận tự động từ hệ này sang hệ kia; hai cụm địa chỉ phải được nhập/lưu độc lập.
5. Nếu cần hỗ trợ lịch sử địa giới theo thời gian, `effective_from/effective_to` phải được đưa vào ngay từ migration đầu tiên.

---

## Kết quả mong muốn sau phase 2.1

- Hệ thống có module danh mục hành chính thật, không còn placeholder.
- Có thể quản trị và import dữ liệu theo cả hệ cũ và hệ mới.
- Các module nhân sự về sau có API/component dùng lại để nhập địa chỉ chuẩn hóa.
- Kiến trúc dữ liệu đủ linh hoạt cho thay đổi hành chính tiếp theo mà không phải tách thêm bộ bảng mới.
