# Kế hoạch triển khai — 8.2. Kỷ luật

**Phạm vi:** Tạo/sửa/xóa quyết định kỷ luật theo hình thức quy định bởi BLLĐ · Lưu biên bản/quyết định · Lịch sử kỷ luật trong hồ sơ nhân viên  
**Phụ thuộc:** `8.1 Khen thưởng` ✅ (dùng chung view container RewardsView, CSS, router) · `3.1 Thông tin nhân viên` ✅ · MinIO ✅  
**Căn cứ pháp lý:** Bộ luật Lao động 2019 (Luật 45/2019/QH14) — Điều 124 về hình thức xử lý kỷ luật

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `RewardsView.vue` với tabs | ✅ Hoàn thành (8.1) | Tab Kỷ luật đang rỗng |
| `employee_disciplines` table | ❌ Chưa có | |
| Backend API | ❌ Chưa có | |
| `DisciplineListTab.vue` | ❌ Chưa có | |

---

## Phân tích nghiệp vụ

### Hình thức kỷ luật (theo BLLĐ — cố định, không cần catalog)

Điều 124 BLLĐ 2019 quy định 4 hình thức xử lý kỷ luật lao động:

| Code | Tên hiển thị | Ghi chú |
|---|---|---|
| `khien_trach` | Khiển trách | Nhẹ nhất |
| `keo_dai_nang_luong` | Kéo dài thời hạn nâng lương | Có `extended_months` (1–12 tháng) |
| `cach_chuc` | Cách chức | Đối với NV có chức vụ |
| `sa_thai` | Sa thải | Nặng nhất — theo Điều 125 BLLĐ |

> **Lý do không dùng catalog:** Hình thức kỷ luật là **cố định theo luật**, không thay đổi theo chính sách công ty. Dùng `ENUM`-like VARCHAR với validation ở service layer là đủ và rõ ràng hơn.

### Quy tắc nghiệp vụ

- Mỗi quyết định kỷ luật gắn với **1 nhân viên**
- `discipline_form` bắt buộc phải thuộc 4 giá trị hợp lệ
- `extended_months` (1–12): chỉ bắt buộc khi `discipline_form = 'keo_dai_nang_luong'`
- `effective_date`: ngày kỷ luật có hiệu lực
- `end_date`: ngày kết thúc hiệu lực — bắt buộc khi `discipline_form = 'keo_dai_nang_luong'` (auto-fill = `effective_date + extended_months`), nullable cho các hình thức khác
- File đính kèm: 1 file/record (biên bản/quyết định), lưu MinIO
- Không có quy trình phê duyệt — HR ghi nhận trực tiếp
- Nhân viên đã nghỉ việc: vẫn xem được lịch sử, không tạo mới

---

## Schema cơ sở dữ liệu

### Bảng `employee_disciplines`

```
id               PK SERIAL
employee_id      FK → employees(id) ON DELETE CASCADE   NOT NULL   INDEX

discipline_form  VARCHAR(50) NOT NULL
                 CHECK IN ('khien_trach','keo_dai_nang_luong','cach_chuc','sa_thai')

violation_date   DATE NOT NULL           -- ngày vi phạm xảy ra
effective_date   DATE NOT NULL           -- ngày quyết định kỷ luật có hiệu lực
end_date         DATE nullable           -- ngày hết hiệu lực (dành cho keo_dai_nang_luong)
extended_months  SMALLINT nullable       -- số tháng kéo dài (1-12), chỉ khi keo_dai_nang_luong

title            VARCHAR(500) NOT NULL   -- tiêu đề / nội dung vi phạm ngắn gọn
description      TEXT nullable           -- mô tả chi tiết hành vi vi phạm
decision_number  VARCHAR(100) nullable   -- số quyết định kỷ luật
issued_by        VARCHAR(200) nullable   -- tên người/hội đồng ký quyết định
note             TEXT nullable           -- ghi chú thêm

-- File đính kèm (biên bản / quyết định) — 1 file, MinIO
file_path        VARCHAR(500) nullable
file_name        VARCHAR(255) nullable
file_size        INT nullable
mime_type        VARCHAR(100) nullable

created_by_id    FK → users(id) ON DELETE SET NULL
created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at       TIMESTAMPTZ nullable

INDEX (employee_id, effective_date DESC)
INDEX (discipline_form, effective_date)
INDEX (decision_number) WHERE decision_number IS NOT NULL
CONSTRAINT chk_extended_months CHECK (
    (discipline_form = 'keo_dai_nang_luong' AND extended_months IS NOT NULL)
    OR (discipline_form != 'keo_dai_nang_luong' AND extended_months IS NULL)
)
```

**Migration số:** `0026_create_employee_disciplines.py`

---

## API Endpoints

```
GET    /disciplines                       List (filter: employee_id, discipline_form,
                                               department_id, from_date, to_date, search;
                                               page, page_size)
GET    /disciplines/{id}                  Xem chi tiết
POST   /disciplines                       Tạo mới (multipart: JSON body + file)
PUT    /disciplines/{id}                  Sửa (multipart: JSON body + file tùy chọn)
DELETE /disciplines/{id}                  Xóa + xóa file MinIO
GET    /disciplines/{id}/download         Tải file đính kèm
GET    /employees/{id}/disciplines        Lịch sử kỷ luật trong hồ sơ NV (không phân trang)
```

**RBAC:**

| Action | Admin | HR Manager | HR Officer | Line Manager |
|---|---|---|---|---|
| list / get | ✅ | ✅ | ✅ | ✅ (phòng ban) |
| create / update | ✅ | ✅ | ✅ | ❌ |
| delete | ✅ | ✅ | ❌ | ❌ |

---

## Schemas Pydantic

### Constants (không cần model DB)

```python
DISCIPLINE_FORMS = {
    "khien_trach":        "Khiển trách",
    "keo_dai_nang_luong": "Kéo dài thời hạn nâng lương",
    "cach_chuc":          "Cách chức",
    "sa_thai":            "Sa thải",
}

DisciplineFormType = Literal[
    "khien_trach",
    "keo_dai_nang_luong",
    "cach_chuc",
    "sa_thai",
]
```

### `DisciplineRead`
```python
class DisciplineRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    discipline_form: str              # 'khien_trach' | ...
    discipline_form_label: str        # "Khiển trách" | ...
    violation_date: date
    effective_date: date
    end_date: date | None
    extended_months: int | None
    title: str
    description: str | None
    decision_number: str | None
    issued_by: str | None
    note: str | None
    has_file: bool
    file_name: str | None
    file_size: int | None
    created_by_id: int | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime | None
```

### `DisciplineCreate`
```python
class DisciplineCreate(BaseModel):
    employee_id: int
    discipline_form: DisciplineFormType
    violation_date: date
    effective_date: date
    extended_months: int | None = Field(default=None, ge=1, le=12)
    title: str = Field(max_length=500)
    description: str | None = None
    decision_number: str | None = None
    issued_by: str | None = None
    note: str | None = None

    @model_validator(mode='after')
    def validate_extended_months(self):
        if self.discipline_form == 'keo_dai_nang_luong':
            if self.extended_months is None:
                raise ValueError("Phải nhập số tháng kéo dài khi hình thức là 'Kéo dài nâng lương'")
        else:
            self.extended_months = None  # bỏ qua nếu không phải hình thức này
        return self

    @model_validator(mode='after')
    def validate_dates(self):
        if self.violation_date > self.effective_date:
            raise ValueError("Ngày vi phạm không được sau ngày hiệu lực")
        return self
```

---

## Service logic

```python
DISCIPLINE_FORMS_VALID = frozenset(DISCIPLINE_FORMS.keys())

async def create_discipline(
    session,
    data: DisciplineCreate,
    file: UploadFile | None,
    created_by_id: int,
) -> DisciplineRead:
    # 1. Validate employee tồn tại
    emp = await get_employee_or_404(session, data.employee_id)

    # 2. Tính end_date nếu keo_dai_nang_luong
    end_date = None
    if data.discipline_form == 'keo_dai_nang_luong' and data.extended_months:
        end_date = data.effective_date + relativedelta(months=data.extended_months)

    # 3. Upload file nếu có
    file_path = file_name = file_size = mime_type = None
    if file and file.filename:
        obj_key = f"disciplines/{data.employee_id}/{uuid4()}_{file.filename}"
        await storage.save(obj_key, file)
        file_path, file_name = obj_key, file.filename
        file_size, mime_type = file.size, file.content_type

    # 4. Tạo record
    record = EmployeeDiscipline(
        **data.dict(exclude={'extended_months': False}),
        end_date=end_date,
        file_path=file_path, file_name=file_name,
        file_size=file_size, mime_type=mime_type,
        created_by_id=created_by_id,
    )
    session.add(record)
    await session.flush()
    return await _joined_read(session, record.id)
```

---

## Thiết kế Frontend

### Tab Kỷ luật trong `RewardsView.vue`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Kỷ luật nhân viên                             [+ Thêm quyết định]  │
├─────────────────────────────────────────────────────────────────────┤
│ Phòng ban: [Tất cả ▼]  Hình thức: [Tất cả ▼]  Từ: [__] Đến: [__]  │
│ Tìm kiếm: [Mã NV / Họ tên / Số QĐ____________]                     │
├───────────────────────────────────────────────────────────────────── │
│ Nhân viên │ Hình thức kỷ luật │ Tiêu đề  │ Ngày HLực│ File │ …     │
│ NV001 · A │ Khiển trách       │ Đi muộn  │ 10/05/26 │  📎  │ ⋮     │
│ NV002 · B │ Cách chức         │ Vi phạm  │ 01/04/26 │  —   │ ⋮     │
└─────────────────────────────────────────────────────────────────────┘
```

**Badge hình thức kỷ luật:**
- `khien_trach`: xanh lá (`success`) — nhẹ
- `keo_dai_nang_luong`: cam (`warn`)
- `cach_chuc`: đỏ cam (`danger` nhạt)
- `sa_thai`: đỏ đậm (`danger`)

### Dialog tạo/sửa quyết định kỷ luật

```
Thêm quyết định kỷ luật
────────────────────────────────────────────────
Nhân viên:  *  [Chọn nhân viên... ▼]
Hình thức:  *  [Khiển trách ▼]
Ngày vi phạm:* [10/05/2026]
Ngày hiệu lực:*[15/05/2026]
Số tháng KD:   [__]  ← chỉ hiện khi "Kéo dài nâng lương" (bắt buộc)
               → Hết hiệu lực: 15/11/2026 (auto-calculate)
Tiêu đề:    *  [___________________________________]
Số QĐ:         [___________________________________]  (tùy chọn)
Đơn vị ký:     [___________________________________]  (tùy chọn)
Mô tả:         [___________________________________]
               [___________________________________]
Ghi chú:       [___________________________________]
File BB/QĐ:    [Chọn file...]
────────────────────────────────────────────────
        [Hủy]          [Lưu]
```

**Quy tắc UI:**
- `extended_months` field: chỉ show khi `discipline_form === 'keo_dai_nang_luong'`
- `end_date` auto-calculate và hiển thị preview (không cho nhập tay)
- Badge severity mapping: `khien_trach → success`, `keo_dai_nang_luong → warn`, `cach_chuc → danger` (với opacity 60%), `sa_thai → danger`

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0026_create_employee_disciplines.py   (NEW)
  app/models/discipline.py                               (NEW: EmployeeDiscipline)
  app/models/__init__.py                                 (EDIT)
  app/schemas/discipline.py                              (NEW)
  app/services/discipline_service.py                     (NEW)
  app/api/v1/endpoints/disciplines.py                    (NEW)
  app/api/v1/router.py                                   (EDIT: đăng ký /disciplines)
  tests/test_disciplines.py                              (NEW)

frontend/
  src/services/disciplineService.ts                      (NEW)
  src/views/rewards/components/DisciplineListTab.vue     (NEW)
  src/views/rewards/RewardsView.vue                      (EDIT: thêm tab Kỷ luật)
  src/assets/styles/views/_rewards.scss                  (EDIT: thêm discipline styles)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Migration + Model + API CRUD

**Tasks:**
1. Migration `0026`: tạo bảng `employee_disciplines` + constraint
2. Model `EmployeeDiscipline` trong `app/models/discipline.py` + đăng ký `__init__.py`
3. Service + endpoint đầy đủ (CRUD + file + employee history)
4. Đăng ký router

**Exit criteria:**
- `POST /disciplines` (multipart) tạo record với file
- Validation: `extended_months` required khi `keo_dai_nang_luong`, 422 nếu thiếu
- Validation: `discipline_form` không thuộc 4 giá trị hợp lệ → 422
- `GET /employees/{id}/disciplines` trả đúng history
- `DELETE /disciplines/{id}` xóa MinIO

---

### Slice 2 — Frontend: Tab Kỷ luật

**Tasks:**
1. `disciplineService.ts`: interfaces + API calls
2. `DisciplineListTab.vue`: bảng + dialog tạo/sửa
3. Thêm tab Kỷ luật vào `RewardsView.vue`
4. Thêm CSS vào `_rewards.scss`

**Exit criteria:**
- Tab Kỷ luật hiển thị bảng, filter, search
- Dialog: field `Số tháng` hiện/ẩn đúng, `end_date` tự tính
- Badge severity đúng theo hình thức
- Không scoped style

---

### Slice 3 — Tests

**File:** `backend/tests/test_disciplines.py`

```python
class TestCreateDiscipline:
    test_create_khien_trach_without_file
    test_create_keo_dai_requires_extended_months       # không có → 422
    test_create_keo_dai_auto_calculates_end_date       # end_date = effective + months
    test_create_sa_thai_with_file
    test_invalid_discipline_form_rejected              # form không hợp lệ → 422
    test_violation_date_after_effective_date_rejected  # → 422
    test_resigned_employee_rejected                    # NV đã nghỉ → 422

class TestListDisciplines:
    test_filter_by_employee_id
    test_filter_by_discipline_form
    test_filter_by_department_id
    test_filter_by_date_range
    test_search_by_employee_name
    test_search_by_decision_number

class TestUpdateDeleteDiscipline:
    test_update_changes_title_and_form
    test_update_keo_dai_recalculates_end_date
    test_delete_removes_file_from_minio

class TestEmployeeHistory:
    test_employee_discipline_history_returns_correct_records
    test_unauthenticated_returns_401
```

---

## Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Upload file thành công, DB lỗi | Upload TRƯỚC — nếu DB fail thì xóa file MinIO trong except |
| `end_date` tính sai tháng biên (31/01 + 1 tháng = ?) | Dùng `dateutil.relativedelta` — không cộng thô 30 ngày |
| NV bị kỷ luật `sa_thai` nhưng vẫn `status = 'active'` trong DB | 8.2 chỉ ghi nhận sự kiện — không tự đổi trạng thái NV; HR tự cập nhật status NV riêng |
| Trùng số quyết định | `decision_number` không unique (cùng số QĐ có thể cho nhiều NV trong 1 đợt) — không enforce unique constraint |

---

## Thứ tự thực hiện

```
Slice 1 (Migration + Backend API)
  ↓
Slice 2 (Frontend Tab)
  ↓
Slice 3 (Tests)
```

---

## Không nằm trong 8.2

| Phần | Thuộc về |
|---|---|
| Khen thưởng | 8.1 |
| Báo cáo tổng hợp | 8.3 |
| Tự động đổi trạng thái NV khi sa thải | 3.2 Thông tin công việc |
| Quy trình phê duyệt kỷ luật (hội đồng) | Ngoài phạm vi |
| Khiếu nại kỷ luật | Ngoài phạm vi |
