# Kế hoạch thực hiện — 2.3. Danh mục nghiệp vụ khác

**Phạm vi:** Loại hợp đồng lao động · Quốc tịch · Dân tộc · Tôn giáo · Ngân hàng · Kỹ năng · Chứng chỉ · Loại nghỉ phép · Mẫu hợp đồng/phụ lục hợp đồng  
**Ràng buộc:** Phải bám kiến trúc hiện có sau `2.1 Danh mục hành chính` và `2.2 Danh mục học vấn`; không tách thành một module rời ngoài khu vực `Danh mục`; phải chừa đúng nền dữ liệu để module `Hợp đồng lao động` và `Hồ sơ nhân sự` dùng lại trực tiếp.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| `docs/FEATURES.md` có yêu cầu `2.3` | ✅ Có |
| Khu vực `Danh mục` trên FE | ✅ Đã có landing page + route con cho `2.1`, `2.2` |
| RBAC `catalog:*` + audit log | ✅ Đã có và đang dùng thực tế |
| Module `Hợp đồng` trên FE | ⚠️ Mới là placeholder `ContractListView.vue` |
| Model / schema / service / endpoint cho `2.3` | ❌ Chưa có |
| Nền dữ liệu để sinh hợp đồng/phụ lục từ mẫu Word | ❌ Chưa có |

### Kiểm chứng codebase

- Route `Hợp đồng` đã tồn tại tại `frontend/src/router/index.ts`, nhưng màn `frontend/src/views/contracts/ContractListView.vue` hiện chỉ là placeholder.
- RBAC đã có module `contracts` và `catalog` trong `backend/app/seeds/rbac.py`.
- Sau `2.1` và `2.2`, codebase đã có pattern hoàn chỉnh cho:
  `models` → `schemas` → `services` → `api/v1/endpoints` → `frontend/services` → `frontend/views`.

### Nhận định triển khai

- `2.3` không chỉ là “một nhóm danh mục lẻ”. Nếu làm phẳng tất cả vào vài bảng text đơn giản, phase `3.1 Hồ sơ nhân sự`, `4. Hợp đồng lao động` và `5. Nghỉ phép` sẽ phải nhập tay và rất khó chuẩn hóa.
- Riêng phần hợp đồng/phụ lục có tính nền tảng cao hơn các catalog còn lại, vì nó cần:
  - chuẩn hóa loại hợp đồng theo pháp luật và quy ước nội bộ
  - lưu file mẫu `.doc` / `.docx`
  - quản lý biến placeholder
  - sinh hợp đồng/phụ lục thực tế từ dữ liệu `Employee`

---

## Cơ sở pháp lý đã kiểm chứng

Các điểm dưới đây đã được kiểm tra ngày **2026-05-14**:

1. **Bộ luật Lao động 2019** có hiệu lực từ **01-01-2021** theo Cổng TTĐT Chính phủ.  
   Nguồn: https://vanban.chinhphu.vn/?docid=198540&pageid=27160

2. Tài liệu PBGDPL của Bộ Tư pháp tóm lược **Điều 20** xác nhận loại hợp đồng lao động theo Bộ luật Lao động 2019. Kết luận dùng cho plan này:
   - pháp luật hiện hành phân biệt **hợp đồng lao động không xác định thời hạn**
   - và **hợp đồng lao động xác định thời hạn**
   Nguồn: https://pbgdpl.moj.gov.vn/qt/tintuc/Lists/ToGap/Attachments/345/To%20gap%2003%20-%20PL%20hopdong.pdf

3. Nguồn của Bộ Tư pháp về thử việc cho thấy nội dung thử việc được điều chỉnh ở **Điều 24 đến Điều 27** Bộ luật Lao động 2019. Kết luận dùng cho plan này:
   - “thử việc” không nên được hardcode như một `legal_contract_type` riêng
   - mà nên mô hình hóa như **mục đích/nhóm mẫu nghiệp vụ** hoặc trạng thái thỏa thuận thử việc gắn với hợp đồng
   Nguồn: https://tcdcpl.moj.gov.vn/qt/tintuc/Pages/phap-luat-kinh-te.aspx?ItemID=382

> Ghi chú thiết kế: phần plan bên dưới phân biệt rõ `loại hợp đồng theo pháp luật` và `nhóm/mẫu hợp đồng theo nghiệp vụ nội bộ`, để không khóa hệ thống vào một giả định sai về pháp lý.

---

## Mục tiêu nghiệp vụ

1. Chuẩn hóa các danh mục nền dùng chung cho nhiều module:
   - quốc tịch
   - dân tộc
   - tôn giáo
   - ngân hàng
   - kỹ năng
   - chứng chỉ
   - loại nghỉ phép
2. Chuẩn hóa **loại hợp đồng lao động** theo hai lớp:
   - lớp pháp lý
   - lớp nghiệp vụ nội bộ / nhóm mẫu
3. Quản lý **mẫu hợp đồng lao động** và **mẫu phụ lục hợp đồng** dưới dạng file `.doc` hoặc `.docx`.
4. Thiết kế để sau này có thể:
   - chọn `1 Employee`
   - chọn `1 mẫu hợp đồng` hoặc `1 mẫu phụ lục`
   - tự động điền dữ liệu của nhân viên vào mẫu
   - sinh ra văn bản hợp đồng/phụ lục để HR rà soát và phát hành
5. Chừa đủ metadata để mở rộng về sau:
   - version mẫu
   - hiệu lực áp dụng
   - khóa mẫu cũ nhưng giữ lịch sử
   - bộ placeholder và mapping dữ liệu

---

## Phạm vi chi tiết của 2.3

### Nhóm A — Catalog nền dùng lại

- `contract categories`
- `nationalities`
- `ethnicities`
- `religions`
- `banks`
- `skills`
- `certificates`
- `leave types`

### Nhóm B — Catalog template cho hợp đồng

- `contract templates`
- `contract template fields / placeholders`
- `contract template versions`
- `contract document categories`
  - hợp đồng lao động
  - phụ lục hợp đồng lao động

> Phase `2.3` chỉ chuẩn bị catalog và nền template.  
> Phase `4. Hợp đồng lao động` mới là nơi quản lý hợp đồng thực tế đã phát hành cho từng nhân viên.

---

## Nguyên tắc thiết kế

1. **Tách catalog nền khỏi nghiệp vụ phát sinh**
   Ví dụ:
   - `contract_template` là danh mục/mẫu
   - `employee_contract` về sau mới là chứng từ phát sinh

2. **Tách “loại pháp lý” khỏi “mẫu nội bộ”**
   Ví dụ:
   - `legal_type = indefinite_term | definite_term`
   - `business_template_code = probation_offer_60d | definite_term_12m | appendix_salary_change`

3. **Không hard delete khi dữ liệu đã từng được dùng**
   Mọi catalog trong `2.3` nên soft delete / inactive.

4. **Upload file mẫu là metadata + file storage, không nhét binary vào bảng chính**
   Bảng template chỉ giữ thông tin file, version, checksum, MIME type, path/id trên storage.

5. **Placeholder phải có contract rõ ràng**
   Không parse Word “ngầm”.  
   Hệ thống phải biết:
   - biến nào được phép dùng
   - biến lấy từ đâu
   - kiểu dữ liệu gì
   - bắt buộc hay không

6. **Sinh văn bản theo cơ chế “render có kiểm soát”**
   Hệ thống sinh file từ mẫu và payload chuẩn hóa, không ghi đè file mẫu gốc.

---

## Thiết kế dữ liệu đề xuất

### 1. Danh mục loại hợp đồng

```sql
contract_categories
  id                    serial PK
  code                  varchar(50) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  document_kind         varchar(30) not null      -- 'labor_contract' | 'contract_appendix'
  legal_contract_type   varchar(30) null          -- 'indefinite_term' | 'definite_term' | null
  business_group        varchar(50) null          -- probation, salary_change, title_change, renewal, termination_note...
  default_term_months   int null
  sort_order            int default 0
  is_active             bool default true
  description           text null
  created_at            timestamptz default now()
  updated_at            timestamptz
```

### 2. Quốc tịch, dân tộc, tôn giáo

```sql
nationalities
  id                    serial PK
  code                  varchar(20) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  iso2_code             varchar(2) null
  iso3_code             varchar(3) null
  is_active             bool default true

ethnicities
  id                    serial PK
  code                  varchar(20) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  is_active             bool default true

religions
  id                    serial PK
  code                  varchar(20) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  is_active             bool default true
```

### 3. Ngân hàng

```sql
banks
  id                    serial PK
  code                  varchar(30) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  short_name            varchar(100) null
  bin_code              varchar(20) null
  swift_code            varchar(20) null
  is_active             bool default true
```

### 4. Kỹ năng và chứng chỉ

```sql
skills
  id                    serial PK
  code                  varchar(50) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  skill_group           varchar(100) null        -- production, qa, veterinary, sales, import_export, office_it...
  is_active             bool default true

certificates
  id                    serial PK
  code                  varchar(50) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  certificate_group     varchar(100) null
  issuer_name           varchar(255) null
  expiry_policy         varchar(30) null         -- none | fixed_date | months_after_issue
  default_valid_months  int null
  is_active             bool default true
```

### 5. Loại nghỉ phép

```sql
leave_types
  id                    serial PK
  code                  varchar(50) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  is_paid_leave         bool default false
  affects_annual_leave  bool default false
  allow_half_day        bool default false
  requires_attachment   bool default false
  color_tag             varchar(20) null
  is_active             bool default true
  description           text null
```

### 6. Mẫu hợp đồng / phụ lục

```sql
contract_templates
  id                    serial PK
  code                  varchar(50) unique not null
  name                  varchar(255) not null
  normalized_name       varchar(255) not null
  contract_category_id  int FK -> contract_categories.id
  document_kind         varchar(30) not null      -- 'labor_contract' | 'contract_appendix'
  template_engine       varchar(30) not null      -- 'docx_placeholders'
  file_storage_id       int null                  -- tham chiếu bảng file storage hiện có / sẽ có
  file_name             varchar(255) not null
  mime_type             varchar(100) not null
  file_checksum         varchar(128) null
  version_no            int not null default 1
  effective_from        date null
  effective_to          date null
  is_active             bool default true
  note                  text null
  created_at            timestamptz default now()
  updated_at            timestamptz

  unique(code, version_no)
```

### 7. Placeholder catalog cho mẫu hợp đồng

```sql
contract_template_placeholders
  id                    serial PK
  template_id           int FK -> contract_templates.id on delete cascade
  placeholder_key       varchar(100) not null      -- employee.full_name
  label                 varchar(255) not null
  source_scope          varchar(50) not null       -- employee | organization | contract_draft | signer | system
  source_path           varchar(255) not null      -- employee.full_name, employee.department.name, ...
  data_type             varchar(30) not null       -- text | date | number | currency | boolean
  formatter             varchar(50) null           -- vn_date, currency_vnd, uppercase...
  is_required           bool default false
  default_value         varchar(255) null
  sort_order            int default 0

  unique(template_id, placeholder_key)
```

### 8. Bảng preview/generation draft cho phase sau

> Chưa bắt buộc ở migration đầu tiên, nhưng nên chừa chỗ trong plan:

```sql
contract_generation_drafts
  id                    serial PK
  employee_id           int FK -> employees.id
  template_id           int FK -> contract_templates.id
  rendered_payload      jsonb not null
  output_file_storage_id int null
  status                varchar(20) not null      -- draft | rendered | approved | failed
  rendered_at           timestamptz null
  rendered_by           int FK -> users.id null
```

---

## Tích hợp với Hồ sơ nhân sự và module Hợp đồng

### Với `3. Hồ sơ nhân sự`

Các catalog sau phải được dùng lại trực tiếp:

- `nationalities`
- `ethnicities`
- `religions`
- `banks`
- `skills`
- `certificates`

Về sau nên có các bảng phát sinh:

```sql
employee_skills
employee_certificates
employee_bank_accounts
```

### Với `4. Hợp đồng lao động`

Thiết kế `2.3` phải làm nền cho:

```sql
employee_contracts
employee_contract_appendices
```

Flow mục tiêu về sau:

1. HR chọn `Employee`
2. HR chọn `Contract Template`
3. Hệ thống dựng `rendered_payload` từ dữ liệu chuẩn hóa:
   - hồ sơ cá nhân
   - thông tin công việc
   - địa chỉ cũ/mới
   - mức lương BHXH
   - người ký / đơn vị / công ty
4. Render file `.docx` kết quả
5. HR rà soát, chỉnh thủ công nếu cần, rồi phát hành

### Điểm quan trọng cần chốt ngay từ bây giờ

- Không buộc mọi dữ liệu phải lấy hết từ `Employee`.
- Một số trường phải cho phép override ở lúc sinh hợp đồng:
  - số hợp đồng
  - ngày ký
  - ngày hiệu lực
  - ngày hết hạn
  - mức lương, phụ cấp, nơi làm việc
  - nội dung thay đổi của phụ lục

Vì vậy phase sau nên có khái niệm:
- `base data from employee`
- `draft contract data override`

---

## API mục tiêu

### Admin CRUD cho catalog nền

| Method | URL | Mô tả |
|---|---|---|
| GET/POST/PUT/DELETE | `/api/v1/contract-categories` | Loại hợp đồng / nhóm phụ lục |
| GET/POST/PUT/DELETE | `/api/v1/nationalities` | Quốc tịch |
| GET/POST/PUT/DELETE | `/api/v1/ethnicities` | Dân tộc |
| GET/POST/PUT/DELETE | `/api/v1/religions` | Tôn giáo |
| GET/POST/PUT/DELETE | `/api/v1/banks` | Ngân hàng |
| GET/POST/PUT/DELETE | `/api/v1/skills` | Kỹ năng |
| GET/POST/PUT/DELETE | `/api/v1/certificates` | Chứng chỉ |
| GET/POST/PUT/DELETE | `/api/v1/leave-types` | Loại nghỉ phép |

### Admin CRUD cho mẫu hợp đồng

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/contract-templates` | Danh sách mẫu |
| POST | `/api/v1/contract-templates` | Tạo mẫu + metadata |
| PUT | `/api/v1/contract-templates/{id}` | Cập nhật metadata / inactive |
| POST | `/api/v1/contract-templates/{id}/upload` | Upload file `.doc` / `.docx` |
| GET | `/api/v1/contract-templates/{id}/placeholders` | Danh sách biến |
| PUT | `/api/v1/contract-templates/{id}/placeholders` | Cấu hình bộ biến cho mẫu |
| POST | `/api/v1/contract-templates/{id}/validate` | Validate file mẫu và placeholder |

### Lookup dùng lại cho form khác

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/lookups/contract-categories` | Dropdown loại hợp đồng |
| GET | `/api/v1/lookups/nationalities` | Dropdown quốc tịch |
| GET | `/api/v1/lookups/ethnicities` | Dropdown dân tộc |
| GET | `/api/v1/lookups/religions` | Dropdown tôn giáo |
| GET | `/api/v1/lookups/banks` | Search ngân hàng |
| GET | `/api/v1/lookups/skills` | Search kỹ năng |
| GET | `/api/v1/lookups/certificates` | Search chứng chỉ |
| GET | `/api/v1/lookups/leave-types` | Dropdown loại nghỉ |

### API chuẩn bị cho phase sinh hợp đồng

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/v1/contracts/template-preview` | Chọn employee + template, trả payload preview |
| POST | `/api/v1/contracts/render-preview` | Render thử nội dung trước khi phát hành |

> Hai API preview có thể làm ở cuối `2.3` hoặc đầu phase `4`, nhưng contract dữ liệu phải được thiết kế từ bây giờ.

---

## Bước 1 — Models & Migration

**Mục tiêu:** Có schema DB chuẩn cho toàn bộ catalog nền và nền template hợp đồng.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/models/catalog.py` | Thêm các model mới của `2.3` |
| `backend/app/models/__init__.py` | Export model mới |
| `backend/alembic/versions/xxxx_create_other_business_catalog_tables.py` | Tạo bảng + index |

### Index nên có

- mọi bảng catalog: `code` unique
- mọi bảng catalog: `normalized_name`
- `contract_templates(contract_category_id, is_active)`
- `contract_templates(document_kind, is_active)`
- `contract_template_placeholders(template_id, sort_order)`
- `banks(short_name)`
- `skills(skill_group, is_active)`
- `certificates(certificate_group, is_active)`

**Verify:** `alembic upgrade head` chạy sạch; DB có đủ bảng và index.

---

## Bước 2 — Seed dữ liệu nền ban đầu

**Mục tiêu:** Có baseline đủ tốt để form nhân sự và module hợp đồng dùng được ngay.

### Seed bắt buộc

- `contract_categories`
  - HĐLĐ không xác định thời hạn
  - HĐLĐ xác định thời hạn
  - Phụ lục thay đổi lương
  - Phụ lục thay đổi chức danh / công việc
  - Phụ lục gia hạn / điều chỉnh thời hạn nếu nghiệp vụ nội bộ cần
- `nationalities`
  - tối thiểu seed đầy đủ quốc tịch phổ biến, ưu tiên chuẩn hóa theo danh sách quốc gia
- `ethnicities`
  - seed theo danh mục dân tộc Việt Nam doanh nghiệp cần dùng
- `religions`
  - seed các tôn giáo phổ biến + `không`
- `banks`
  - seed ngân hàng nội địa phổ biến
- `leave_types`
  - phép năm, nghỉ bệnh, thai sản, tang, cưới, không lương...

### Seed khuyến nghị cho doanh nghiệp nông nghiệp

- `skills`
  - vận hành sản xuất
  - QA/QC
  - kiểm nghiệm nguyên liệu
  - công thức thức ăn chăn nuôi
  - quản lý trại
  - thú y
  - an toàn sinh học
  - xuất nhập khẩu
  - logistics
  - khai báo hải quan
- `certificates`
  - an toàn vệ sinh lao động
  - ISO/HACCP liên quan sản xuất
  - chứng chỉ thú y/chăn nuôi nếu doanh nghiệp cần
  - nghiệp vụ xuất nhập khẩu / hải quan

### Mẫu hợp đồng ban đầu

- có thể chưa upload file Word thật ngay ở bước seed
- nhưng nên seed ít nhất metadata mẫu:
  - `ld_indefinite_v1`
  - `ld_definite_12m_v1`
  - `appendix_salary_change_v1`

**Verify:** `make seed` nạp đủ catalog; lookup API trả dữ liệu thật.

---

## Bước 3 — Schemas, Services, API

**Mục tiêu:** Mở API quản trị và lookup cho toàn bộ `2.3`.

### Backend

| File | Nội dung |
|---|---|
| `backend/app/schemas/catalog.py` | Schema cho 8 nhóm catalog + template |
| `backend/app/services/other_catalog_service.py` | CRUD + lookup + validate template metadata |
| `backend/app/api/v1/endpoints/other_catalog.py` | Router quản trị cho `2.3` |
| `backend/app/api/v1/router.py` | Include router mới |

### Validation quan trọng

- `contract_categories.legal_contract_type` chỉ nhận:
  - `indefinite_term`
  - `definite_term`
  - hoặc `NULL` cho phụ lục
- `document_kind='contract_appendix'` thì `legal_contract_type` có thể `NULL`
- chỉ cho upload `.doc` / `.docx` đối với `contract_templates`
- không cho inactive một template đang là bản active duy nhất của một code nếu chưa có version thay thế, trừ khi người dùng xác nhận rõ
- placeholder key phải unique trong từng template

### Test

- CRUD + filter cho từng catalog
- upload metadata cho template
- validate placeholder contract
- lookup dùng lại cho nhân sự

**Verify:** test API pass; Swagger thử được toàn bộ flow create → list → lookup → template metadata.

---

## Bước 4 — Frontend quản trị trong khu vực Danh mục

**Mục tiêu:** Có màn quản trị thật cho `2.3` trong khu vực `Danh mục`.

### Đề xuất UI

- route mới: `/catalog/other-business`
- dùng `Tabs` hoặc `Section switcher`
- tách 2 khu chính:
  - `Danh mục nền`
  - `Mẫu hợp đồng & phụ lục`

### Các tab đề xuất

1. `Loại hợp đồng`
2. `Quốc tịch`
3. `Dân tộc`
4. `Tôn giáo`
5. `Ngân hàng`
6. `Kỹ năng`
7. `Chứng chỉ`
8. `Loại nghỉ phép`
9. `Mẫu hợp đồng`

### Với tab `Mẫu hợp đồng`

Phải có:
- list mẫu
- trạng thái active/version
- upload file `.doc` / `.docx`
- xem danh sách placeholder
- cấu hình placeholder
- validate mẫu trước khi đưa vào dùng

**Verify:** browser-level check bắt buộc cho upload, filter, tab switch, empty state, dialog.

---

## Bước 5 — Chuẩn bị tích hợp Hồ sơ nhân sự và Hợp đồng

**Mục tiêu:** Chốt contract để `3.1`, `3.4`, `4.1`, `4.2` dùng lại ngay.

**Trạng thái:** ✅ Hoàn thành — 2026-05-15

### Kiểm chứng từ 2 file mẫu tham khảo

Ngày **2026-05-15**, đã kiểm tra trực tiếp bằng ElementTree scan:

- `templates/fixed_term.docx`
- `templates/probation.docx`

Kết quả thực tế:

- `probation.docx`: 15 token `${...}`, không có `{{}}`, không có MERGEFIELD
- `fixed_term.docx`: 16 token `${...}` (2 token có typo khoảng trắng: `${employee _cccd _issued_by}`, `${employee _cccd _issued_on}`), 6 MERGEFIELD tiếng Việt (`Ngày`, `Tháng`, `Năm`, `SĐT`, `Loại_HĐLĐ__`, `Thời_hạn_trả_lương`)
- **Tất cả token `${...}` đều nằm trong single XML run** — không có token bị tách qua nhiều run (đã verify trực tiếp qua ElementTree)

> Kết luận đã điều chỉnh: token không bị tách run, nhưng không được parse bằng regex thô trên text thuần vì MERGEFIELD nằm trong `<w:instrText>`, không phải `<w:t>`.

### Quyết định chốt cho template Word — 2026-05-15

**Đã thảo luận và chốt** sau khi đánh giá đề xuất của user và Codex agent:

#### Quyết định 1: Cú pháp `{{}}` là chuẩn authoring mới

- **Chuẩn mới:** Template Word mới **chỉ dùng `{{snake_case}}`**
- **Tương thích ngược:** Scanner vẫn đọc được `${...}` và `MERGEFIELD` cho các file cũ
- **Warning:** Hệ thống cảnh báo khi phát hiện `${}` hoặc MERGEFIELD, khuyến nghị migrate về `{{}}`
- **2 file mẫu hiện tại** (`probation.docx`, `fixed_term.docx`) đã được convert sang `{{}}` trong bước này

**Lý do chọn `{{}}` thay vì `${}`:**
- `{{}}` là cú pháp phổ biến hơn trong template engines (Jinja2, Handlebars, Mustache)
- Dễ gõ hơn trong Word (không cần Shift+4)
- Ít bị Word autocorrect can thiệp hơn `$`

#### Quyết định 2: Token ASCII, label tiếng Việt ở UI

- **Không dùng** `{{nhân viên: họ và tên}}` — quá dễ typo, khó parse, Unicode fragile trong Word XML
- **Không dùng** `{{nhan_vien_ho_va_ten}}` — chi phí migrate cao, lợi ích thấp so với token English đã có
- **Giữ token ASCII** (`{{employee_full_name}}`) — industry standard, ổn định, dễ validate
- **Label tiếng Việt** hiển thị trong UI/DB (`label = "Họ và tên"`) — đã có sẵn trong registry

**Lý do:** Token trong file Word không phải thứ HR nhìn hàng ngày. HR nhìn `label` trong UI khi chọn placeholder. Registry đã có đủ label tiếng Việt.

### Phương án thiết kế chốt cho template Word

1. `placeholder_key` trong DB là **token thật xuất hiện trong file Word** (ASCII snake_case).
2. `source_scope + source_path` là contract dữ liệu nội bộ của hệ thống.
3. **Chuẩn authoring cho template mới: chỉ dùng `{{snake_case}}`.**
4. `${}` và `MERGEFIELD` vẫn được đọc để tương thích ngược, nhưng scanner phải warn và đề nghị migrate về `{{}}`.
5. Admin không nhập tay toàn bộ placeholder từ đầu. Flow đúng là:
   - khai báo metadata template
   - gắn `storage_path`
   - backend quét DOCX
   - backend trả token phát hiện được + token nào map được tự động từ registry field chuẩn
   - admin rà lại rồi mới lưu `contract_template_placeholders`

### Registry field chuẩn cho phase hợp đồng

Backend cần có một field registry công khai dùng chung cho:
- quản trị mẫu hợp đồng
- preview sinh hợp đồng
- render hợp đồng thật ở phase `4`

Ví dụ mapping chuẩn:
- `employee_full_name -> employee.full_name`
- `employee_birthday -> employee.date_of_birth`
- `employee_cccd -> employee.identity_number`
- `employee_address -> employee.permanent_address_full`
- `employee_temp_address -> employee.current_address_full`
- `contract_number -> contract.contract_number`
- `contract_start_date -> contract.start_date`
- `contract_end_date -> contract.end_date`
- `insurance_salary -> contract.insurance_salary`

### Với Hồ sơ nhân sự

Tạo component lookup dùng lại:
- `NationalitySelect`
- `EthnicitySelect`
- `ReligionSelect`
- `BankSelect`
- `SkillMultiSelect`
- `CertificateEditor`

### Với hợp đồng lao động

Tạo contract dữ liệu preview:

```json
{
  "employee_id": 123,
  "template_id": 5,
  "draft_data": {
    "contract_number": "HDLD/2026/001",
    "signed_at": "2026-05-14",
    "effective_date": "2026-05-20",
    "expired_at": "2027-05-19",
    "bhxh_salary": 12000000
  }
}
```

### Payload preview hệ thống phải trả được

```json
{
  "template": {
    "id": 5,
    "code": "ld_definite_12m_v1"
  },
  "placeholders": {
    "employee_full_name": "Nguyễn Văn A",
    "employee_birthday": "01/01/1995",
    "department_name": "Kinh doanh",
    "employee_address": "...",
    "employee_temp_address": "...",
    "contract_number": "HDLD/2026/001"
  },
  "missing_fields": []
}
```

> `placeholders` trả theo token thật của file Word.  
> Hệ thống dùng `source_path` nội bộ để dựng giá trị cho từng token này.

### Quy tắc render về sau

- file mẫu gốc không bị sửa
- mọi lần render tạo một output mới
- output gắn với `employee_contract` hoặc `contract_generation_draft`
- nếu placeholder thiếu dữ liệu bắt buộc, hệ thống phải báo rõ biến nào đang thiếu
- nếu template còn token legacy như `MERGEFIELD`, hệ thống phải cảnh báo nhưng vẫn cho preview nếu mapping đã đầy đủ

---

## Bước 6 — Phân quyền, audit log, dữ liệu vận hành ✅

**Mục tiêu:** Mọi thay đổi trong `2.3` đều kiểm soát được và đủ log để vận hành.

### RBAC

Tiếp tục dùng `catalog:*` cho:
- tất cả catalog nền
- quản trị mẫu hợp đồng

Riêng phase tạo hợp đồng thực tế về sau nên dùng `contracts:*`, không lẫn với `catalog:*`.

### Audit log bắt buộc

- create / update / inactive mọi catalog nền ✅
- upload / replace file mẫu hợp đồng ✅
- thay đổi placeholder của template ✅ (action = `UPDATE`)
- activate / deactivate version mẫu ✅

### Dữ liệu vận hành nên có

- cảnh báo mẫu hợp đồng có vấn đề: ✅
  - đang inactive → `is_active=False`
  - hết hiệu lực → `effective_to < today`
  - chưa có file → `storage_path` trống
  - chưa có placeholder nào khai báo
- Endpoint: `GET /api/v1/contract-templates/health-summary` trả `ContractTemplateHealthRead[]`
- Frontend: panel cảnh báo hiển thị trong tab Templates của `OtherBusinessCatalogView.vue`
- Nút "Xem nhật ký hệ thống" trong hero panel → `/admin/audit-logs` ✅
- Nút "Xem audit log" trong health panel → `/admin/audit-logs?entity_type=contract_template` ✅

### Tests

- `test_catalog_create_writes_audit_log` ✅
- `test_contract_template_operations_write_audit_log` ✅ (CREATE + UPDATE trong audit)
- 228/228 tests pass ✅

**Verify:** test RBAC + audit log; frontend có đường đi tới nhật ký hệ thống.

---

## Thứ tự triển khai khuyến nghị

1. `Models & Migration`
2. `Seed baseline`
3. `CRUD/Lookup cho catalog nền`
4. `Contract template metadata + upload`
5. `Frontend quản trị`
6. `Preview payload cho sinh hợp đồng`
7. `RBAC + audit + vận hành`

---

## Rủi ro thiết kế cần tránh

1. **Gộp “thử việc” thành loại hợp đồng pháp lý thứ ba**
   Theo cơ sở pháp lý đã kiểm chứng cho plan này, đây là điểm rất dễ mô hình hóa sai.

2. **Lưu file Word nhưng không quản placeholder**
   Nếu chỉ upload file mà không có metadata biến, phase auto-fill sẽ rất khó kiểm soát.

3. **Cho phép chỉnh thẳng lên file mẫu đang active mà không version hóa**
   Sẽ phá khả năng truy vết hợp đồng đã sinh trước đó.

4. **Trộn catalog template với hợp đồng phát sinh**
   Dẫn đến khó audit và khó quản lý lịch sử tài liệu.

5. **Để toàn bộ dữ liệu hợp đồng chỉ lấy từ Employee**
   Thực tế cần lớp `draft override` khi sinh hợp đồng/phụ lục.

---

## Kết quả mong đợi sau phase 2.3

- Khu `Danh mục` có thêm nhóm catalog nền nghiệp vụ dùng được thật.
- Hệ thống có nền chuẩn để nhập hồ sơ nhân sự nhất quán hơn.
- Module `Hợp đồng lao động` có thể bước sang phase triển khai thật mà không phải thiết kế lại từ đầu.
- Việc chọn `Employee + mẫu hợp đồng/phụ lục` để auto-fill vào file Word đã có đủ nền dữ liệu và contract kỹ thuật để triển khai an toàn ở phase sau.
