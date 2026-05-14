# Kế hoạch thực hiện — 2.2. Danh mục học vấn

**Phạm vi:** Trình độ học vấn · Trường học · Chuyên ngành · API tra cứu dùng lại cho hồ sơ nhân sự  
**Ràng buộc:** Phải bám kiến trúc hiện có sau `2.1 Danh mục hành chính`; không tạo module catalog rời rạc ngoài khu vực `Danh mục`; ưu tiên thiết kế đủ sâu để `3.4 Học vấn & Kinh nghiệm` dùng lại trực tiếp.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| `docs/FEATURES.md` có yêu cầu `2.2` | ✅ Có |
| Khu vực `Danh mục` trên FE | ✅ Đã có landing page + route con từ phase `2.1` |
| Pattern backend cho CRUD + lookup + RBAC + audit | ✅ Đã có từ `2.1`, `users`, `roles`, `departments` |
| Model / schema / service / endpoint cho học vấn | ❌ Chưa có |
| Component dùng lại cho hồ sơ nhân sự | ❌ Chưa có |
| Dữ liệu seed cơ bản cho trình độ học vấn | ❌ Chưa có |

### Nhận định triển khai

- Sau `2.1`, codebase đã có nền `catalog` thật:
  `router/menu` + `RBAC catalog:*` + `audit log` + `pattern service/api/frontend`.
- `2.2` không khó ở mặt phân cấp như địa chỉ hành chính, nhưng dễ bị làm quá nông nếu chỉ lưu text tự do.
- Nếu không chốt tốt `2.2`, phase `3.4 Học vấn & Kinh nghiệm` sẽ bị buộc phải nhập tay tên trường, chuyên ngành, trình độ và rất khó làm báo cáo/chuẩn hóa về sau.

---

## Mục tiêu nghiệp vụ

1. Quản lý danh mục **Trình độ học vấn** theo thứ bậc học thuật:
   `Tiểu học → THCS → THPT → Trung cấp → Cao đẳng → Đại học → Thạc sĩ → Tiến sĩ`
2. Quản lý danh mục **Trường học / Cơ sở đào tạo** để liên kết với hồ sơ nhân sự.
3. Quản lý danh mục **Chuyên ngành** để chuẩn hóa quá trình học vấn của nhân viên.
4. Hỗ trợ lookup/search nhanh trong form nhân sự, không buộc nhập tay toàn bộ.
5. Giữ đủ metadata để sau này mở rộng:
   mã trường, loại trường, quốc gia, trạng thái hoạt động, alias tìm kiếm, merge dữ liệu trùng.

---

## Nguyên tắc thiết kế

1. **Tách danh mục nền khỏi hồ sơ nhân sự**
   Hồ sơ học vấn của nhân viên chỉ tham chiếu FK tới catalog.

2. **Phân biệt “catalog chuẩn hóa” và “giá trị hiển thị”**
   Ví dụ:
   - `education_level.code = "bachelor"`
   - `education_level.name = "Đại học"`

3. **Cho phép inactive thay vì hard delete**
   Danh mục đã từng được dùng trong hồ sơ nhân sự không nên xóa vật lý.

4. **Ưu tiên search thực dụng**
   Trường học và chuyên ngành phải hỗ trợ search theo tên không dấu, alias, mã viết tắt nếu có.

5. **Không ép import nguồn ngoài ngay ở phase đầu**
   Với `trình độ học vấn` có thể seed cứng;
   với `trường học` và `chuyên ngành`, giai đoạn đầu có thể CRUD + import CSV/Excel nội bộ sau.

---

## Thiết kế dữ liệu đề xuất

### Schema DB

```sql
education_levels
  id               serial PK
  code             varchar(50) unique not null       -- primary_school, bachelor, master, ...
  name             varchar(255) not null             -- Đại học, Thạc sĩ, ...
  normalized_name  varchar(255) not null
  rank_no          int not null                      -- phục vụ sort và so sánh cấp bậc
  is_active        bool default true
  created_at       timestamptz default now()
  updated_at       timestamptz

educational_institutions
  id               serial PK
  code             varchar(50) unique null          -- nếu có mã nội bộ / mã import
  name             varchar(255) not null
  normalized_name  varchar(255) not null
  short_name       varchar(100) null                -- VD: ĐH Bách Khoa HN
  institution_type varchar(50) null                 -- university | college | vocational | high_school | other
  country_code     varchar(10) null                 -- VN, JP, KR, ...
  province_code    varchar(20) null                 -- nếu muốn nối nhẹ với catalog hành chính
  is_active        bool default true
  created_at       timestamptz default now()
  updated_at       timestamptz

education_majors
  id               serial PK
  code             varchar(50) unique null
  name             varchar(255) not null
  normalized_name  varchar(255) not null
  major_group      varchar(100) null                -- engineering, finance, law, ...
  is_active        bool default true
  created_at       timestamptz default now()
  updated_at       timestamptz
```

### Bảng mở rộng tùy chọn nên cân nhắc sớm

```sql
institution_aliases
  id               serial PK
  institution_id   int FK → educational_institutions.id on delete cascade
  alias_name       varchar(255) not null
  normalized_name  varchar(255) not null

major_aliases
  id               serial PK
  major_id         int FK → education_majors.id on delete cascade
  alias_name       varchar(255) not null
  normalized_name  varchar(255) not null
```

> Nếu cần đi nhanh, alias có thể chưa làm ở migration đầu tiên.  
> Nhưng plan nên chừa chỗ vì đây là nhu cầu gần như chắc chắn có khi nhập dữ liệu nhân sự lịch sử.

---

## Tích hợp với Hồ sơ nhân sự

Phase `3.4 Học vấn & Kinh nghiệm` nên đi theo hướng:

```sql
employee_educations
  id                  serial PK
  employee_id         int FK → employees.id
  education_level_id  int FK → education_levels.id
  institution_id      int FK → educational_institutions.id nullable
  major_id            int FK → education_majors.id nullable
  degree_name         varchar(255) null            -- tên văn bằng thực tế nếu cần
  graduation_year     int null
  from_year           int null
  to_year             int null
  is_graduated        bool default true
  note                text null
  attachment_file_id  int nullable
  created_at          timestamptz default now()
  updated_at          timestamptz
```

### Quy tắc tích hợp

- `education_level_id` là bắt buộc.
- `institution_id` và `major_id` cho phép `NULL` để không chặn import hồ sơ lịch sử.
- Nếu người dùng nhập trường/chuyên ngành chưa có trong catalog:
  - giai đoạn đầu: cho phép nhập text tạm vào field riêng hoặc tạo nhanh qua dialog
  - dài hạn: có quy trình “thêm vào danh mục”

---

## API mục tiêu

### Admin CRUD

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/education-levels` | Danh sách trình độ học vấn |
| POST | `/api/v1/education-levels` | Tạo trình độ mới |
| PUT | `/api/v1/education-levels/{id}` | Cập nhật trình độ |
| DELETE | `/api/v1/education-levels/{id}` | Soft delete / khóa |
| GET | `/api/v1/educational-institutions` | Danh sách trường học |
| POST | `/api/v1/educational-institutions` | Tạo trường học |
| PUT | `/api/v1/educational-institutions/{id}` | Cập nhật trường học |
| DELETE | `/api/v1/educational-institutions/{id}` | Soft delete / khóa |
| GET | `/api/v1/education-majors` | Danh sách chuyên ngành |
| POST | `/api/v1/education-majors` | Tạo chuyên ngành |
| PUT | `/api/v1/education-majors/{id}` | Cập nhật chuyên ngành |
| DELETE | `/api/v1/education-majors/{id}` | Soft delete / khóa |

### Lookup dùng lại cho form nhân sự

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/lookups/education-levels` | Dropdown trình độ |
| GET | `/api/v1/lookups/educational-institutions` | Search trường học |
| GET | `/api/v1/lookups/education-majors` | Search chuyên ngành |

### Query params chính

- `is_active`
- `keyword`
- `page`
- `page_size`
- `institution_type`
- `country_code`
- `major_group`

---

## Bước 1 — Models & Migration

**Mục tiêu:** Có schema DB chuẩn cho 3 nhóm catalog học vấn.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/models/catalog.py` | Thêm `EducationLevel`, `EducationalInstitution`, `EducationMajor` |
| `backend/app/models/__init__.py` | Export model mới cho Alembic |
| `backend/alembic/versions/xxxx_create_education_catalog_tables.py` | Tạo bảng + index |

### Index nên có

- `education_levels(code)` unique
- `education_levels(rank_no)` unique hoặc index thường tùy rule
- `educational_institutions(normalized_name)`
- `educational_institutions(institution_type, is_active)`
- `education_majors(normalized_name)`
- `education_majors(major_group, is_active)`

**Verify:** `alembic upgrade head` chạy sạch; DB có đủ bảng và index.

---

## Bước 2 — Seed dữ liệu nền ban đầu

**Mục tiêu:** Có baseline tối thiểu để form nhân sự dùng được ngay.

### Seed bắt buộc

#### Trình độ học vấn

```text
Tiểu học
THCS
THPT
Trung cấp
Cao đẳng
Đại học
Thạc sĩ
Tiến sĩ
```

### Seed khuyến nghị

- Một tập mẫu nhỏ cho `trường học`:
  - Đại học Bách khoa Hà Nội
  - Đại học Kinh tế Quốc dân
  - Đại học Quốc gia Hà Nội
  - Đại học Cần Thơ
  - ...
- Một tập mẫu nhỏ cho `chuyên ngành`:
  - Công nghệ thông tin
  - Kế toán
  - Tài chính - Ngân hàng
  - Quản trị kinh doanh
  - Luật
  - Cơ khí
  - Điện - Điện tử

### Backend

| File | Nội dung |
|---|---|
| `backend/app/seeds/education_catalog.py` | Seed levels + sample institutions/majors |
| `backend/app/seeds/required.py` | Nối seed mới vào flow `make seed` |

### Quy tắc seed

1. `education_levels` phải idempotent theo `code`.
2. `institution` và `major` có thể idempotent theo `normalized_name`.
3. Không xóa dữ liệu đã có khi chạy `make seed`; chỉ upsert/insert thiếu.

**Verify:** chạy `make seed` hoặc `python -m app.seeds --sample` trong container và kiểm tra API list trả dữ liệu.

---

## Bước 3 — Schemas, Services, API

**Mục tiêu:** Mở đủ CRUD admin và lookup cho frontend.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/schemas/catalog.py` | Thêm schema create/update/read/page cho `education_levels`, `educational_institutions`, `education_majors` |
| `backend/app/services/education_catalog_service.py` | CRUD, search, soft delete |
| `backend/app/api/v1/endpoints/education_catalog.py` | Router cho admin + lookup |
| `backend/app/api/v1/router.py` | Include router mới |

### Validation quan trọng

- `rank_no` không trùng giữa các `education_levels`
- `code` nếu có phải unique
- `name` không được rỗng sau normalize/trim
- `institution_type` nếu dùng enum phải validate nhất quán
- Không soft delete một bản ghi đang được tham chiếu bởi `employee_educations` trong phase sau

### Test

| File | Nội dung |
|---|---|
| `backend/tests/test_education_catalog.py` | CRUD + filter + pagination |
| `backend/tests/test_education_lookup.py` | Lookup/search cho form nhân sự |

**Verify:** Swagger `/api/docs` test được flow create → list → update → search.

---

## Bước 4 — Frontend quản trị trong khu vực Danh mục

**Mục tiêu:** Bổ sung nhóm `Học vấn` vào khu vực `Danh mục` hiện có.

### Router/Menu

| Thành phần | Thay đổi |
|---|---|
| `frontend/src/router/index.ts` | Thêm route `catalog/education` |
| `frontend/src/components/layout/AppMenu.vue` | Thêm mục con `Danh mục học vấn` |
| `frontend/src/views/catalog/CatalogView.vue` | Thêm entry card tới khu học vấn |

### Frontend files

| File | Nội dung |
|---|---|
| `frontend/src/services/educationCatalogService.ts` | Axios wrapper |
| `frontend/src/views/catalog/EducationCatalogView.vue` | Landing page/tab page cho 3 danh mục |
| `frontend/src/views/catalog/EducationLevelListView.vue` | CRUD trình độ |
| `frontend/src/views/catalog/EducationalInstitutionListView.vue` | CRUD trường học |
| `frontend/src/views/catalog/EducationMajorListView.vue` | CRUD chuyên ngành |

### UI đề xuất

- Có thể đi theo 2 hướng:
  1. Một page duy nhất với `Tabs`:
     - Trình độ học vấn
     - Trường học
     - Chuyên ngành
  2. Một page landing + 3 route con riêng

### Khuyến nghị

- Chọn `1 page + Tabs` cho nhanh và nhất quán với quy mô `2.2`
- Chỉ tách route con riêng nếu danh sách trường/chuyên ngành trở nên quá lớn hoặc cần filter phức tạp

**Verify:** thao tác CRUD end-to-end với API thật, không còn placeholder.

---

## Bước 5 — Chuẩn bị tích hợp Hồ sơ nhân sự

**Mục tiêu:** Chốt contract để `3.4 Học vấn & Kinh nghiệm` cắm thẳng vào catalog.

### Frontend dùng lại sau này

| File | Nội dung |
|---|---|
| `frontend/src/components/catalog/EmployeeEducationEditor.vue` | Component nhập 1 dòng học vấn |
| `frontend/src/components/catalog/EducationalInstitutionSelect.vue` | Search trường học dùng lại |
| `frontend/src/components/catalog/EducationMajorSelect.vue` | Search chuyên ngành dùng lại |

### Hành vi form nhân sự

- Có thể thêm nhiều dòng quá trình học vấn
- Mỗi dòng gồm:
  - trình độ
  - trường học
  - chuyên ngành
  - năm bắt đầu / năm tốt nghiệp
  - ghi chú / văn bằng
- Cho phép lookup trường/chuyên ngành bằng search box
- Nếu chưa có catalog phù hợp:
  - phase đầu: cho nhập text dự phòng hoặc “tạo nhanh”
  - phase sau: workflow duyệt/chuẩn hóa

### Backend dùng lại sau này

- `GET /lookups/education-levels`
- `GET /lookups/educational-institutions`
- `GET /lookups/education-majors`

**Verify:** Có thể mock tích hợp vào form nhân sự mà không viết lại logic search/select.

---

## Bước 6 — Phân quyền, audit log, dữ liệu vận hành

**Mục tiêu:** Khu `Danh mục học vấn` vận hành an toàn và nhất quán với `2.1`.

### RBAC đề xuất

| Permission | Ý nghĩa |
|---|---|
| `catalog:view` | Xem toàn bộ khu danh mục, gồm học vấn |
| `catalog:create` | Tạo mới trình độ/trường/chuyên ngành |
| `catalog:edit` | Chỉnh sửa / khóa |
| `catalog:delete` | Xóa logic nếu cho phép |
| `catalog:import` | Nếu về sau mở import trường/chuyên ngành hàng loạt |

### Audit cần ghi

- Tạo/sửa/khóa `education_level`
- Tạo/sửa/khóa `educational_institution`
- Tạo/sửa/khóa `education_major`
- Import batch nếu có

### Dữ liệu vận hành cần theo dõi

- số lượng trường đang active
- số lượng chuyên ngành đang active
- top trường/chuyên ngành được dùng nhiều nhất trong hồ sơ nhân sự (phase sau)

**Verify:** Có audit log tương ứng khi CRUD qua admin UI/API.

---

## Thứ tự triển khai khuyến nghị

1. Chốt schema 3 bảng catalog học vấn
2. Làm migration + test model
3. Seed `education_levels` + sample data tối thiểu
4. Mở API CRUD + lookup
5. Bổ sung page quản trị FE trong `Danh mục`
6. Tạo component lookup dùng lại cho hồ sơ nhân sự
7. Bật audit / dùng chung `catalog:*`

---

## Rủi ro & lưu ý thiết kế

1. Nếu để trường học và chuyên ngành là text tự do ngay từ đầu, phase hồ sơ nhân sự sẽ nhanh nhưng báo cáo và chuẩn hóa sẽ hỏng về sau.
2. Nếu ép unique quá chặt theo `name`, dữ liệu lịch sử hoặc biến thể tên trường sẽ khó nhập. Cần chừa đường cho `alias` hoặc `merge`.
3. Nếu không có `rank_no` cho trình độ học vấn, việc sort và suy luận cấp độ cao nhất của nhân viên sẽ rối.
4. Nếu import trường/chuyên ngành từ nhiều nguồn khác nhau, cần chiến lược normalize tên trước khi upsert.
5. Nếu phase đầu chưa làm `country_code` và `institution_type`, vẫn nên chừa field nullable để khỏi migration đập lại sớm.

---

## Kết quả mong muốn sau phase 2.2

- Hệ thống có khu `Danh mục học vấn` thật trong `Danh mục`
- Trình độ học vấn, trường học, chuyên ngành được chuẩn hóa thành catalog riêng
- Hồ sơ nhân sự phase `3.4` có API/component dùng lại để nhập học vấn có cấu trúc
- Kiến trúc đủ linh hoạt để sau này mở rộng import hàng loạt, alias, merge dữ liệu trùng
