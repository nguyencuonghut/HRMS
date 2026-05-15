# Kế hoạch thực hiện — 3.4. Học vấn & Kinh nghiệm

**Phạm vi:** Quá trình học vấn · Kinh nghiệm làm việc trước · Kỹ năng · Chứng chỉ · Ngoại ngữ  
**Phụ thuộc:** `1.2 RBAC` ✅ · `2.2 Danh mục học vấn` ✅ · `2.3 Danh mục nghiệp vụ khác` ✅ · `3.1 Thông tin cá nhân` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Danh mục `education_levels` | ✅ Đã có (2.2) — tiểu học → tiến sĩ |
| Danh mục `educational_institutions` | ✅ Đã có (2.2) — trường học |
| Danh mục `education_majors` | ✅ Đã có (2.2) — chuyên ngành |
| Danh mục `skills` | ✅ Đã có (2.3) — kỹ năng |
| Danh mục `certificates` | ✅ Đã có (2.3) — chứng chỉ |
| Bảng `employee_education_histories` | ❌ Chưa có |
| Bảng `employee_work_experiences` | ❌ Chưa có |
| Bảng `employee_skills` | ❌ Chưa có |
| Bảng `employee_certificates` | ❌ Chưa có |
| Bảng `employee_languages` | ❌ Chưa có |
| Service / Schema / Endpoint cho các bảng trên | ❌ Chưa có |
| Frontend tab "Học vấn & KN" | ❌ Chưa có |

---

## Phạm vi 3.4

Theo `docs/FEATURES.md §3.4`:

| Nhóm | Trường thông tin |
|---|---|
| Học vấn | Trường, chuyên ngành, trình độ, năm tốt nghiệp, loại bằng, là bằng chính? |
| Kinh nghiệm làm việc | Công ty, vị trí, từ tháng/năm, đến tháng/năm, mô tả |
| Kỹ năng | Kỹ năng (FK danh mục), mức độ thành thạo, ghi chú |
| Chứng chỉ | Chứng chỉ (FK danh mục), số văn bằng, ngày cấp, ngày hết hạn, nơi cấp |
| Ngoại ngữ | Tên ngoại ngữ, mức độ thành thạo (theo khung CEFR) |

---

## Thiết kế cơ sở dữ liệu

### 1. Bảng `employee_education_histories`

```sql
CREATE TABLE employee_education_histories (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Liên kết danh mục (nullable cho phép nhập tự do nếu không có trong danh mục)
    institution_id      INTEGER REFERENCES educational_institutions(id) ON DELETE SET NULL,
    institution_name    VARCHAR(255),           -- tên trường nhập tự do nếu không có FK
    major_id            INTEGER REFERENCES education_majors(id) ON DELETE SET NULL,
    major_name          VARCHAR(255),           -- chuyên ngành nhập tự do
    education_level_id  INTEGER NOT NULL REFERENCES education_levels(id) ON DELETE RESTRICT,

    graduation_year     SMALLINT,               -- năm tốt nghiệp (có thể null nếu chưa tốt nghiệp)
    diploma_type        VARCHAR(100),           -- loại bằng: chính quy / liên thông / từ xa / vb2
    is_main_education   BOOLEAN NOT NULL DEFAULT FALSE,  -- bằng cấp chính dùng cho hồ sơ
    note                TEXT,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);

CREATE INDEX ix_emp_edu_histories_employee_id ON employee_education_histories (employee_id);
```

> **Thiết kế dual-field (FK + free text)**: `institution_id` FK danh mục khi trường đã có trong hệ thống; `institution_name` cho phép nhập trường nước ngoài hoặc trường chưa có trong danh mục. Service ưu tiên FK, fallback sang free text khi FK null.

### 2. Bảng `employee_work_experiences`

```sql
CREATE TABLE employee_work_experiences (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    company_name        VARCHAR(255) NOT NULL,
    position_name       VARCHAR(255),           -- chức vụ / vị trí
    start_date          DATE NOT NULL,          -- từ ngày (bắt buộc)
    end_date            DATE,                   -- đến ngày (NULL = hiện tại)
    description         TEXT,                   -- mô tả công việc / thành tích

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);

CREATE INDEX ix_emp_work_exp_employee_id ON employee_work_experiences (employee_id);
```

> **Không FK công ty**: kinh nghiệm làm việc trước đây là tên công ty ngoài, không có danh mục trong hệ thống. Nhập tự do hoàn toàn.

### 3. Bảng `employee_skills`

```sql
CREATE TABLE employee_skills (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    skill_id            INTEGER NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,

    proficiency_level   VARCHAR(20) NOT NULL,   -- beginner | intermediate | advanced | expert
    note                TEXT,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP,

    UNIQUE (employee_id, skill_id)              -- mỗi kỹ năng chỉ xuất hiện 1 lần per nhân viên
);

CREATE INDEX ix_emp_skills_employee_id ON employee_skills (employee_id);
```

### 4. Bảng `employee_certificates`

```sql
CREATE TABLE employee_certificates (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    certificate_id      INTEGER NOT NULL REFERENCES certificates(id) ON DELETE RESTRICT,

    certificate_number  VARCHAR(100),           -- số văn bằng / mã chứng chỉ
    issued_date         DATE,
    expires_on          DATE,                   -- NULL nếu không có hạn
    issued_by           VARCHAR(255),           -- nơi cấp (override nếu khác issuer_name trong danh mục)
    note                TEXT,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);

CREATE INDEX ix_emp_certificates_employee_id ON employee_certificates (employee_id);
```

> Không đặt UNIQUE (employee_id, certificate_id) vì nhân viên có thể có nhiều lần tái cấp cùng chứng chỉ với ngày cấp khác nhau.

### 5. Bảng `employee_languages`

```sql
CREATE TABLE employee_languages (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    language_name       VARCHAR(100) NOT NULL,  -- Tiếng Anh / Tiếng Trung / Tiếng Nhật...
    proficiency_level   VARCHAR(10) NOT NULL,   -- native | A1 | A2 | B1 | B2 | C1 | C2
    note                TEXT,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP,

    UNIQUE (employee_id, language_name)         -- mỗi ngoại ngữ chỉ 1 lần per nhân viên
);

CREATE INDEX ix_emp_languages_employee_id ON employee_languages (employee_id);
```

---

## Giá trị enum / hằng số

### `proficiency_level` (kỹ năng)

| Giá trị | Hiển thị |
|---|---|
| `beginner` | Cơ bản |
| `intermediate` | Trung bình |
| `advanced` | Khá |
| `expert` | Thành thạo |

### `proficiency_level` (ngoại ngữ — theo CEFR + native)

| Giá trị | Hiển thị |
|---|---|
| `native` | Bản ngữ |
| `A1` | A1 — Sơ cấp |
| `A2` | A2 — Sơ cấp |
| `B1` | B1 — Trung cấp |
| `B2` | B2 — Trung cấp |
| `C1` | C1 — Cao cấp |
| `C2` | C2 — Thành thạo |

### `diploma_type` (loại bằng — free text, gợi ý trong UI)

`chính quy` · `liên thông` · `vừa học vừa làm` · `từ xa` · `văn bằng 2`

---

## Schema thiết kế (Pydantic)

### Education history

```python
class EducationHistoryCreate(BaseModel):
    institution_id:     Optional[int] = None
    institution_name:   Optional[str] = None    # bắt buộc nếu institution_id null
    major_id:           Optional[int] = None
    major_name:         Optional[str] = None
    education_level_id: int
    graduation_year:    Optional[int] = None
    diploma_type:       Optional[str] = None
    is_main_education:  bool = False
    note:               Optional[str] = None

    @model_validator(mode='after')
    def require_institution_name_if_no_id(self):
        if not self.institution_id and not self.institution_name:
            raise ValueError('Cần nhập tên trường hoặc chọn từ danh mục')
        return self

class EducationHistoryRead(BaseModel):
    id: int
    employee_id: int
    institution_id: Optional[int]
    institution_name: Optional[str]
    major_id: Optional[int]
    major_name: Optional[str]
    education_level_id: int
    education_level_name: str           # denormalized từ join
    graduation_year: Optional[int]
    diploma_type: Optional[str]
    is_main_education: bool
    note: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
```

### Work experience

```python
class WorkExperienceCreate(BaseModel):
    company_name:  str
    position_name: Optional[str] = None
    start_date:    date
    end_date:      Optional[date] = None
    description:   Optional[str] = None

class WorkExperienceRead(BaseModel):
    id: int; employee_id: int
    company_name: str; position_name: Optional[str]
    start_date: date; end_date: Optional[date]
    description: Optional[str]
    created_at: datetime; updated_at: Optional[datetime]
```

### Skills

```python
SkillProficiencyLevel = Literal["beginner", "intermediate", "advanced", "expert"]

class EmployeeSkillCreate(BaseModel):
    skill_id:          int
    proficiency_level: SkillProficiencyLevel
    note:              Optional[str] = None

class EmployeeSkillRead(BaseModel):
    id: int; employee_id: int
    skill_id: int; skill_name: str; skill_group: Optional[str]   # denormalized
    proficiency_level: str; note: Optional[str]
    created_at: datetime; updated_at: Optional[datetime]
```

### Certificates

```python
class EmployeeCertificateCreate(BaseModel):
    certificate_id:     int
    certificate_number: Optional[str] = None
    issued_date:        Optional[date] = None
    expires_on:         Optional[date] = None
    issued_by:          Optional[str] = None
    note:               Optional[str] = None

class EmployeeCertificateRead(BaseModel):
    id: int; employee_id: int
    certificate_id: int; certificate_name: str   # denormalized
    certificate_number: Optional[str]
    issued_date: Optional[date]; expires_on: Optional[date]
    issued_by: Optional[str]; note: Optional[str]
    created_at: datetime; updated_at: Optional[datetime]
```

### Languages

```python
LanguageProficiencyLevel = Literal["native", "A1", "A2", "B1", "B2", "C1", "C2"]

class EmployeeLanguageCreate(BaseModel):
    language_name:     str
    proficiency_level: LanguageProficiencyLevel
    note:              Optional[str] = None

class EmployeeLanguageRead(BaseModel):
    id: int; employee_id: int
    language_name: str; proficiency_level: str; note: Optional[str]
    created_at: datetime; updated_at: Optional[datetime]
```

### Bổ sung vào `EmployeeRead`

```python
class EmployeeRead(BaseModel):
    ...
    education_histories: list[EducationHistoryRead] = []
    work_experiences:    list[WorkExperienceRead] = []
    skills:              list[EmployeeSkillRead] = []
    certificates:        list[EmployeeCertificateRead] = []
    languages:           list[EmployeeLanguageRead] = []
```

---

## API Endpoints

```
# Học vấn
GET    /api/v1/employees/{id}/education-histories
POST   /api/v1/employees/{id}/education-histories
PUT    /api/v1/employees/{id}/education-histories/{edu_id}
DELETE /api/v1/employees/{id}/education-histories/{edu_id}

# Kinh nghiệm làm việc
GET    /api/v1/employees/{id}/work-experiences
POST   /api/v1/employees/{id}/work-experiences
PUT    /api/v1/employees/{id}/work-experiences/{exp_id}
DELETE /api/v1/employees/{id}/work-experiences/{exp_id}

# Kỹ năng
GET    /api/v1/employees/{id}/skills
POST   /api/v1/employees/{id}/skills
PUT    /api/v1/employees/{id}/skills/{skill_id}
DELETE /api/v1/employees/{id}/skills/{skill_id}

# Chứng chỉ
GET    /api/v1/employees/{id}/certificates
POST   /api/v1/employees/{id}/certificates
PUT    /api/v1/employees/{id}/certificates/{cert_id}
DELETE /api/v1/employees/{id}/certificates/{cert_id}

# Ngoại ngữ
GET    /api/v1/employees/{id}/languages
POST   /api/v1/employees/{id}/languages
PUT    /api/v1/employees/{id}/languages/{lang_id}
DELETE /api/v1/employees/{id}/languages/{lang_id}
```

### RBAC

| Hành động | Quyền |
|---|---|
| Xem tất cả | `employees:view` |
| Thêm / Sửa / Xóa | `employees:edit` |

### Audit log actions

| Thao tác | Action |
|---|---|
| Thêm học vấn | `CREATE_EDUCATION_HISTORY` |
| Sửa học vấn | `UPDATE_EDUCATION_HISTORY` |
| Xóa học vấn | `DELETE_EDUCATION_HISTORY` |
| Thêm kinh nghiệm | `CREATE_WORK_EXPERIENCE` |
| Sửa kinh nghiệm | `UPDATE_WORK_EXPERIENCE` |
| Xóa kinh nghiệm | `DELETE_WORK_EXPERIENCE` |
| Thêm kỹ năng | `CREATE_SKILL` |
| Sửa kỹ năng | `UPDATE_SKILL` |
| Xóa kỹ năng | `DELETE_SKILL` |
| Thêm chứng chỉ | `CREATE_CERTIFICATE` |
| Sửa chứng chỉ | `UPDATE_CERTIFICATE` |
| Xóa chứng chỉ | `DELETE_CERTIFICATE` |
| Thêm ngoại ngữ | `CREATE_LANGUAGE` |
| Sửa ngoại ngữ | `UPDATE_LANGUAGE` |
| Xóa ngoại ngữ | `DELETE_LANGUAGE` |

---

## Frontend

### Tab "Học vấn & KN" trong `EmployeeDetailView.vue`

```
<Tab value="education" :disabled="isNew">Học vấn & KN</Tab>
```

### Component `EducationTab.vue`

Tab được chia thành 5 section-card, mỗi section có header + nút "Thêm" + DataTable/list:

```
┌─────────────────────────────────────────────────────────┐
│ Quá trình học vấn                       [+ Thêm]        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Đại học · ĐH Nông nghiệp VN · Thú y · 2012 ✓  │   │
│  │ THPT · THPT Nguyễn Du                            │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│ Kinh nghiệm làm việc                    [+ Thêm]        │
│  Cty ABC · Kỹ sư · 06/2010 → 12/2011                   │
├─────────────────────────────────────────────────────────┤
│ Kỹ năng                                 [+ Thêm]        │
│  QA/QC [Thành thạo]  Thú y [Khá]                       │
├─────────────────────────────────────────────────────────┤
│ Chứng chỉ                               [+ Thêm]        │
│  HACCP · 01/2024 → 01/2027                              │
├─────────────────────────────────────────────────────────┤
│ Ngoại ngữ                               [+ Thêm]        │
│  Tiếng Anh [B2]  Tiếng Trung [A2]                      │
└─────────────────────────────────────────────────────────┘
```

**Chiến lược dialog**: Mỗi section dùng dialog riêng (5 dialog), hoặc 1 dialog dynamic thay đổi header/form theo context. Chọn **5 dialog riêng** — rõ ràng hơn, không cần quản lý state phức tạp.

**Kỹ năng và Ngoại ngữ**: Hiển thị dạng chip/tag thay vì DataTable (ngắn gọn hơn).

**Học vấn**: Hightlight `is_main_education = TRUE` bằng icon ✓ hoặc Tag "Bằng chính".

### Service bổ sung trong `employeeService.ts`

```typescript
// Education histories
getEducationHistories: (id) => api.get(`${BASE}/${id}/education-histories`)
createEducationHistory: (id, data) => api.post(`${BASE}/${id}/education-histories`, data)
updateEducationHistory: (id, eduId, data) => api.put(`${BASE}/${id}/education-histories/${eduId}`, data)
deleteEducationHistory: (id, eduId) => api.delete(`${BASE}/${id}/education-histories/${eduId}`)

// Work experiences
getWorkExperiences: (id) => api.get(`${BASE}/${id}/work-experiences`)
createWorkExperience: (id, data) => api.post(`${BASE}/${id}/work-experiences`, data)
updateWorkExperience: (id, expId, data) => api.put(`${BASE}/${id}/work-experiences/${expId}`, data)
deleteWorkExperience: (id, expId) => api.delete(`${BASE}/${id}/work-experiences/${expId}`)

// Skills
getEmployeeSkills: (id) => api.get(`${BASE}/${id}/skills`)
createEmployeeSkill: (id, data) => api.post(`${BASE}/${id}/skills`, data)
updateEmployeeSkill: (id, skillId, data) => api.put(`${BASE}/${id}/skills/${skillId}`, data)
deleteEmployeeSkill: (id, skillId) => api.delete(`${BASE}/${id}/skills/${skillId}`)

// Certificates
getEmployeeCertificates: (id) => api.get(`${BASE}/${id}/certificates`)
createEmployeeCertificate: (id, data) => api.post(`${BASE}/${id}/certificates`, data)
updateEmployeeCertificate: (id, certId, data) => api.put(`${BASE}/${id}/certificates/${certId}`, data)
deleteEmployeeCertificate: (id, certId) => api.delete(`${BASE}/${id}/certificates/${certId}`)

// Languages
getEmployeeLanguages: (id) => api.get(`${BASE}/${id}/languages`)
createEmployeeLanguage: (id, data) => api.post(`${BASE}/${id}/languages`, data)
updateEmployeeLanguage: (id, langId, data) => api.put(`${BASE}/${id}/languages/${langId}`, data)
deleteEmployeeLanguage: (id, langId) => api.delete(`${BASE}/${id}/languages/${langId}`)
```

---

## Seed dữ liệu

File: `backend/app/seeds/employee_education.py`

Seed cho nhân viên mẫu seq=1 và seq=3 (đủ để demo tất cả 5 sections):

| Seq | Học vấn | KN làm việc | Kỹ năng | Chứng chỉ | Ngoại ngữ |
|---|---|---|---|---|---|
| 1 | ĐH Nông nghiệp VN · Thú y · 2012 (chính) | Cty ABC 2010-2011 | QA/QC (thành thạo) | HACCP 2024-2027 | Tiếng Anh B2 |
| 3 | ĐH Nông Lâm · KD Nông nghiệp · 2015 | Cty XYZ 2015-2018 | Nhập khẩu (khá) | An toàn LĐ 2023 | Tiếng Anh B1, Tiếng Trung A2 |

---

## Tests

File: `backend/tests/test_employee_education.py`

```
# Education histories
test_list_education_empty
test_create_education_with_institution_fk
test_create_education_free_text_institution
test_create_education_no_institution_422        → thiếu cả FK lẫn free text → 422
test_create_education_sets_main_flag
test_update_education_success
test_delete_education_success
test_delete_education_wrong_employee_404        → IDOR protection

# Work experiences
test_create_work_experience_success
test_create_work_experience_no_end_date         → end_date null = hiện tại
test_update_work_experience_success
test_delete_work_experience_success

# Skills
test_create_skill_success
test_create_skill_invalid_proficiency_422
test_create_skill_duplicate_409                 → unique(employee_id, skill_id)
test_update_skill_proficiency

# Certificates
test_create_certificate_success
test_create_certificate_with_expiry
test_update_certificate_success

# Languages
test_create_language_success
test_create_language_invalid_level_422
test_create_language_duplicate_409              → unique(employee_id, language_name)
test_update_language_level

# Permissions
test_all_creates_require_edit_perm              → viewer → 403

# GET /employees/{id}
test_employee_detail_includes_all_education_fields
```

---

## Thứ tự triển khai

### Bước 1 — Models & Migration
1. Tạo 5 model classes trong `backend/app/models/employee_education.py`
2. Đăng ký vào `backend/app/models/__init__.py`
3. Tạo migration `0010_create_employee_education_tables.py` (1 migration, 5 bảng)

### Bước 2 — Seed dữ liệu
1. Tạo `backend/app/seeds/employee_education.py`
2. Đăng ký vào `backend/app/seeds/sample.py`

### Bước 3 — Backend CRUD
1. Bổ sung schemas vào `backend/app/schemas/employee.py`
2. Tạo `backend/app/services/employee_education_service.py` (CRUD cho cả 5 entity)
3. Cập nhật `employee_service.py`: bổ sung 5 list vào `build_employee_read_data()`
4. Thêm 20 endpoints vào `backend/app/api/v1/endpoints/employees.py`

### Bước 4 — Tests backend
1. Tạo `backend/tests/test_employee_education.py`
2. Chạy pytest → toàn bộ pass

### Bước 5 — Frontend
1. Bổ sung ~20 types + service methods vào `employeeService.ts`
2. Tạo `frontend/src/views/employees/EducationTab.vue` (5 sections, không scoped style)
3. Thêm tab "Học vấn & KN" vào `EmployeeDetailView.vue`

### Bước 6 — Phân quyền & Audit log
1. Verify quyền `employees:view` / `employees:edit` trên 20 endpoints
2. Verify 15 audit log actions

---

## Rủi ro thiết kế cần tránh

1. **N+1 khi load `EmployeeRead`**  
   `build_employee_read_data()` hiện đang gọi nhiều query tuần tự. Với 3.4, thêm 5 query nữa. Tổng cộng ~10 query mỗi lần load `/employees/{id}`. Vẫn chấp nhận được cho detail view (không phải list). Không cần optimize thêm ở bước này.

2. **IDOR trên tất cả PUT/DELETE**  
   Mỗi service function phải kiểm tra `record.employee_id == employee_id` từ path. Pattern đã thiết lập từ 3.3 — áp dụng nhất quán cho cả 5 entity.

3. **`is_main_education` — nhiều bản ghi TRUE**  
   Không đặt DB constraint unique vì một nhân viên có thể muốn thay đổi bằng chính. Service xử lý: khi set `is_main_education=TRUE` → không tự reset các bản ghi khác (để HR quyết định). UI chỉ warning nếu có nhiều hơn 1 bản ghi main.

4. **Unique constraint kỹ năng và ngoại ngữ**  
   `UNIQUE(employee_id, skill_id)` và `UNIQUE(employee_id, language_name)` trên DB — trả 409 khi vi phạm, không dùng ON CONFLICT DO UPDATE (không muốn silent upsert).

5. **Denormalized fields trong EmployeeRead**  
   `education_level_name`, `skill_name`, `certificate_name` phải được join khi build response — không lưu trong bảng employee. Join đơn giản với danh mục catalog đã có.

6. **`EducationTab.vue` sẽ lớn**  
   5 sections + 5 dialogs = component nặng. Cân nhắc tách thành sub-components nếu file > 600 dòng. Để quyết định khi bắt đầu Bước 5.

---

## Kết quả mong đợi sau 3.4

- Hồ sơ nhân viên có đầy đủ thông tin học vấn, kinh nghiệm, kỹ năng, chứng chỉ, ngoại ngữ.
- Dữ liệu học vấn liên kết với danh mục chuẩn hóa (trình độ, trường, chuyên ngành) — hỗ trợ lọc/báo cáo sau này.
- Kỹ năng và chứng chỉ liên kết với catalog để đảm bảo tính nhất quán.
- `GET /employees/{id}` trả về đầy đủ 5 nhóm thông tin học vấn & kinh nghiệm.
- Frontend có tab "Học vấn & KN" với UX rõ ràng cho từng nhóm.
