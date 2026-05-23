# Kế hoạch triển khai — 8.1. Khen thưởng

**Phạm vi:** Quản lý danh mục loại khen thưởng · Tạo/sửa/xóa quyết định khen thưởng · Lưu file quyết định · Lịch sử khen thưởng trong hồ sơ nhân viên  
**Phụ thuộc:** `3.1 Thông tin nhân viên` ✅ · `1.1 Cơ cấu tổ chức` ✅ · MinIO file storage ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §8.1

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Route `/rewards` | ✅ Đã có | Placeholder `RewardListView.vue` |
| AppMenu item | ✅ Đã có | Single item — cần đổi thành group (Khen thưởng / Kỷ luật / Báo cáo) |
| `reward_types` table | ❌ Chưa có | Danh mục loại khen thưởng |
| `employee_rewards` table | ❌ Chưa có | Bảng chính |
| Backend API | ❌ Chưa có | |
| Frontend view | ❌ Chưa có | Cần thay placeholder |

---

## Phân tích nghiệp vụ

### Loại khen thưởng (catalog)

HR tự quản lý danh mục — không cố định theo luật. Ví dụ điển hình:

| Tên | Loại giá trị | Ghi chú |
|---|---|---|
| Bằng khen | Phi tiền tệ | Giấy chứng nhận |
| Giấy khen | Phi tiền tệ | Nội bộ công ty |
| Thưởng tiền | Tiền tệ | Có trường `value` |
| Thưởng hiện vật | Phi tiền tệ | Ghi mô tả vào `description` |

### Quy tắc nghiệp vụ

- Mỗi quyết định khen thưởng gắn với **1 nhân viên** (không gộp nhiều người trong 1 record)
- `value` (giá trị tiền thưởng) chỉ bắt buộc khi `reward_type.is_monetary = true`
- File quyết định: 1 file/record, lưu MinIO, download proxy qua FastAPI
- Nhân viên đã nghỉ việc (`status = 'resigned'`) vẫn có thể xem lịch sử — không được tạo mới
- Không có quy trình phê duyệt — HR ghi nhận trực tiếp
- `decision_number` không bắt buộc nhưng nên điền để tra cứu

---

## Schema cơ sở dữ liệu

### Bảng `reward_types` (danh mục)

```
id              PK SERIAL
code            VARCHAR(50) NOT NULL UNIQUE     -- 'bang_khen' | 'giai_khen' | ...
name            VARCHAR(200) NOT NULL           -- Tên hiển thị: "Bằng khen"
is_monetary     BOOLEAN NOT NULL DEFAULT false  -- true → trường value bắt buộc
sort_order      INT NOT NULL DEFAULT 0          -- thứ tự hiển thị dropdown
is_active       BOOLEAN NOT NULL DEFAULT true
created_at      TIMESTAMPTZ
```

**Seed data ban đầu (migration):**

| code | name | is_monetary |
|---|---|---|
| bang_khen | Bằng khen | false |
| giai_khen | Giấy khen | false |
| thuong_tien | Thưởng tiền | true |
| thuong_hien_vat | Thưởng hiện vật | false |

### Bảng `employee_rewards`

```
id              PK SERIAL
employee_id     FK → employees(id) ON DELETE CASCADE   NOT NULL   INDEX
reward_type_id  FK → reward_types(id) ON DELETE RESTRICT  NOT NULL

title           VARCHAR(500) NOT NULL      -- tiêu đề quyết định (VD: "Thưởng tháng 05/2026")
description     TEXT nullable              -- nội dung / lý do khen thưởng
reward_date     DATE NOT NULL              -- ngày khen thưởng (ngày trong quyết định)
decision_number VARCHAR(100) nullable      -- số quyết định / công văn
issued_by       VARCHAR(200) nullable      -- tên đơn vị / người ký khen thưởng
value           NUMERIC(18,2) nullable     -- giá trị (VND), chỉ dùng khi is_monetary=true
note            TEXT nullable

-- File quyết định (1 file, MinIO)
file_path       VARCHAR(500) nullable      -- object key trong MinIO
file_name       VARCHAR(255) nullable      -- tên file gốc
file_size       INT nullable               -- bytes
mime_type       VARCHAR(100) nullable

created_by_id   FK → users(id) ON DELETE SET NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at      TIMESTAMPTZ nullable

INDEX (employee_id, reward_date DESC)
INDEX (reward_type_id, reward_date)
INDEX (decision_number) WHERE decision_number IS NOT NULL
```

---

## API Endpoints

### Catalog loại khen thưởng

```
GET    /reward-types                  Danh sách (filter: is_active)
POST   /reward-types                  Tạo mới
PUT    /reward-types/{id}             Sửa
DELETE /reward-types/{id}             Xóa (chỉ khi không có record nào dùng)
```

### Quyết định khen thưởng

```
GET    /rewards                       List (filter: employee_id, reward_type_id, department_id,
                                           from_date, to_date, search; page, page_size)
GET    /rewards/{id}                  Xem chi tiết
POST   /rewards                       Tạo mới (multipart: JSON body + file)
PUT    /rewards/{id}                  Sửa (multipart: JSON body + file tùy chọn)
DELETE /rewards/{id}                  Xóa (hard delete, xóa file MinIO luôn)
GET    /rewards/{id}/download         Tải file đính kèm (proxy MinIO)
GET    /employees/{id}/rewards        Lịch sử khen thưởng trong hồ sơ nhân viên (không phân trang)
```

**RBAC:**

| Action | Admin | HR Manager | HR Officer | Line Manager |
|---|---|---|---|---|
| list / get | ✅ | ✅ | ✅ | ✅ (phòng ban) |
| create / update | ✅ | ✅ | ✅ | ❌ |
| delete | ✅ | ✅ | ❌ | ❌ |
| manage catalog | ✅ | ✅ | ❌ | ❌ |

---

## Schemas Pydantic

### `RewardTypeRead`
```python
class RewardTypeRead(BaseModel):
    id: int
    code: str
    name: str
    is_monetary: bool
    sort_order: int
    is_active: bool
```

### `RewardRead`
```python
class RewardRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    reward_type_id: int
    reward_type_name: str
    reward_type_is_monetary: bool
    title: str
    description: str | None
    reward_date: date
    decision_number: str | None
    issued_by: str | None
    value: Decimal | None        # VND
    note: str | None
    has_file: bool               # True nếu file_path IS NOT NULL
    file_name: str | None
    file_size: int | None
    created_by_id: int | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime | None
```

### `RewardCreate` / `RewardUpdate`
```python
class RewardCreate(BaseModel):
    employee_id: int
    reward_type_id: int
    title: str = Field(max_length=500)
    description: str | None = None
    reward_date: date
    decision_number: str | None = None
    issued_by: str | None = None
    value: Decimal | None = None       # validate: required nếu is_monetary=true
    note: str | None = None

    @model_validator(mode='after')
    def check_value_for_monetary(self): ...
    # Gọi DB để lấy reward_type.is_monetary tại service layer
```

---

## Service logic

```python
async def create_reward(
    session,
    data: RewardCreate,
    file: UploadFile | None,
    created_by_id: int,
) -> RewardRead:
    # 1. Lấy reward_type → validate is_monetary vs value
    rt = await get_reward_type_or_404(session, data.reward_type_id)
    if rt.is_monetary and data.value is None:
        raise HTTPException(422, "Loại khen thưởng tiền mặt phải nhập giá trị")
    if not rt.is_monetary and data.value is not None:
        data.value = None  # bỏ qua value nếu không phải tiền tệ

    # 2. Kiểm tra nhân viên tồn tại
    emp = await get_employee_or_404(session, data.employee_id)

    # 3. Upload file nếu có
    file_path = file_name = file_size = mime_type = None
    if file and file.filename:
        obj_key = f"rewards/{data.employee_id}/{uuid4()}_{file.filename}"
        await storage.save(obj_key, file)
        file_path, file_name = obj_key, file.filename
        file_size = file.size
        mime_type = file.content_type

    # 4. Tạo record
    record = EmployeeReward(**data.dict(), file_path=file_path, ...)
    session.add(record)
    await session.flush()
    return await _joined_read(session, record.id)

async def delete_reward(session, reward_id: int) -> None:
    record = await get_reward_or_404(session, reward_id)
    if record.file_path:
        await storage.delete(record.file_path)  # xóa MinIO trước
    await session.delete(record)
```

---

## Thiết kế Frontend

### Cấu trúc view

Route `/rewards` sẽ được refactor thành view có tabs (thay thế placeholder):

```
RewardsView.vue                      ← container với Tabs (Khen thưởng | Kỷ luật | Báo cáo)
  ├── components/
  │   ├── RewardListTab.vue          ← tab 1: Khen thưởng (8.1)
  │   ├── DisciplineListTab.vue      ← tab 2: Kỷ luật (8.2)
  │   └── RewardDisciplineReport.vue ← tab 3: Báo cáo (8.3)
```

AppMenu cần đổi từ single item thành group (như salary):

```javascript
{
  label: 'Khen thưởng & Kỷ luật',
  icon: 'pi-star',
  items: [
    { to: '/rewards', label: 'Khen thưởng & Kỷ luật', icon: 'pi-star' },
    // Khi 8.2 xong sẽ có sub-tab — không cần thêm route mới
  ],
}
```

> **Lưu ý:** Cả 3 tính năng (Khen thưởng / Kỷ luật / Báo cáo) dùng chung route `/rewards`, phân biệt bằng tab. Không cần thêm route mới.

### Layout `RewardListTab.vue`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Khen thưởng nhân viên                           [+ Thêm quyết định]│
├─────────────────────────────────────────────────────────────────────┤
│ Phòng ban: [Tất cả ▼]  Loại: [Tất cả ▼]  Từ: [__] Đến: [__]       │
│ Tìm kiếm: [Mã NV / Họ tên / Số QĐ____________]                     │
├──────────────────────────────────────────────────────────────────────┤
│ Nhân viên │ Loại khen thưởng │ Tiêu đề │ Ngày  │ Giá trị │ File │ … │
│ NV001 · A │ Thưởng tiền      │ Q2 2026 │05/06  │500,000  │  📎  │ ⋮ │
│ NV002 · B │ Bằng khen        │ Xuất sắc│01/05  │ —       │  —   │ ⋮ │
└──────────────────────────────────────────────────────────────────────┘
```

### Dialog tạo/sửa quyết định

```
Thêm quyết định khen thưởng
──────────────────────────────────────────────────
Nhân viên: *  [Chọn nhân viên... ▼ (có filter)]
Loại KT:   *  [Thưởng tiền ▼]
Tiêu đề:   *  [_________________________________]
Số QĐ:        [_________________________________]  (tùy chọn)
Ngày KT:   *  [23/05/2026]
Đơn vị KT:    [_________________________________]  (tùy chọn)
Giá trị:      [_______________] VND              ← chỉ hiện nếu is_monetary=true
Nội dung:     [_________________________________]
              [_________________________________]
Ghi chú:      [_________________________________]
File QĐ:      [Chọn file...]  (PDF/DOCX/JPEG, max 10MB)
──────────────────────────────────────────────────
        [Hủy]          [Lưu]
```

**Quy tắc UI:**
- Field `Giá trị` hiện/ẩn động theo `reward_type.is_monetary`
- File upload: hiển thị tên file hiện tại (nếu đang edit) + nút xóa file
- Format giá trị VND: `InputNumber` với `mode="decimal"`, `locale="vi-VN"`

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0025_create_reward_types_and_employee_rewards.py   (NEW)
  app/models/reward.py                  (NEW: RewardType, EmployeeReward)
  app/models/__init__.py                (EDIT: đăng ký models mới)
  app/schemas/reward.py                 (NEW: RewardTypeRead/Create/Update, RewardRead/Create/Update)
  app/services/reward_service.py        (NEW)
  app/api/v1/endpoints/rewards.py       (NEW)
  app/api/v1/router.py                  (EDIT: đăng ký /reward-types, /rewards)
  tests/test_rewards.py                 (NEW)

frontend/
  src/services/rewardService.ts                              (NEW)
  src/views/rewards/RewardsView.vue                          (NEW: thay RewardListView.vue)
  src/views/rewards/components/RewardListTab.vue             (NEW)
  src/router/index.ts                                        (EDIT: đổi component rewards route)
  src/assets/styles/views/_rewards.scss                      (NEW)
  src/assets/styles/main.scss                                (EDIT: @use _rewards)
  src/components/layout/AppMenu.vue                          (EDIT: cập nhật menu item)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Migration + Model + Danh mục loại khen thưởng

**Mục tiêu:** Bảng `reward_types` có sẵn dữ liệu mẫu + API CRUD catalog.

**Tasks:**
1. Migration `0025`: tạo `reward_types` + `employee_rewards` + seed 4 loại mặc định
2. Model `RewardType`, `EmployeeReward` trong `app/models/reward.py`
3. Đăng ký trong `app/models/__init__.py`
4. Schema + service + endpoint cho `/reward-types`

**Exit criteria:**
- `GET /reward-types` trả 4 loại seed mặc định
- `POST /reward-types` tạo được loại mới
- `DELETE /reward-types/{id}` bị chặn nếu đã có record dùng (409)

---

### Slice 2 — Backend: CRUD quyết định khen thưởng + file

**Tasks:**
1. Service `reward_service.py`: `create_reward`, `update_reward`, `delete_reward`, `list_rewards`, `get_employee_reward_history`
2. Endpoint `/rewards` + `/employees/{id}/rewards`
3. File upload/download (MinIO)

**Exit criteria:**
- `POST /rewards` (multipart) tạo record + upload file MinIO
- `GET /rewards/{id}/download` trả stream file đúng content-type
- `DELETE /rewards/{id}` xóa record + file MinIO
- Filter theo `department_id`, `reward_type_id`, `from_date/to_date`, `search` hoạt động

---

### Slice 3 — Frontend

**Tasks:**
1. `rewardService.ts`: interfaces + API calls
2. `RewardsView.vue`: container tabs (Khen thưởng / Kỷ luật / Báo cáo)
3. `RewardListTab.vue`: bảng danh sách + dialog tạo/sửa
4. `_rewards.scss`: global styles (không scoped)
5. Cập nhật router + AppMenu

**Exit criteria:**
- Bảng hiển thị danh sách, filter hoạt động
- Dialog tạo/sửa lưu được record có file
- Download file đúng
- Không có `<style scoped>` hay inline style
- All Select có prop `filter`
- `vue-tsc --noEmit` không lỗi

---

### Slice 4 — Tests

**File:** `backend/tests/test_rewards.py`

```python
class TestRewardTypeCatalog:
    test_list_default_seed_types        # GET → 4 types
    test_create_reward_type             # POST → 201
    test_delete_used_type_rejected      # DELETE type có record → 409
    test_delete_unused_type             # DELETE type không dùng → 204

class TestCreateReward:
    test_create_without_file            # tạo không có file
    test_create_with_monetary_type_requires_value  # is_monetary + value=None → 422
    test_create_monetary_with_value     # is_monetary + value → 201
    test_create_non_monetary_ignores_value  # !is_monetary + value bị bỏ qua
    test_create_with_file_upload        # multipart với file → has_file=True
    test_create_resigned_employee_rejected  # NV đã nghỉ → 422

class TestListRewards:
    test_filter_by_employee_id
    test_filter_by_department_id
    test_filter_by_reward_type_id
    test_filter_by_date_range
    test_search_by_employee_code
    test_search_by_employee_name
    test_search_by_decision_number

class TestUpdateDeleteReward:
    test_update_reward_metadata         # sửa title, date
    test_update_replaces_file           # upload file mới → file cũ bị xóa MinIO
    test_delete_removes_file            # xóa record + xóa MinIO

class TestEmployeeHistory:
    test_employee_rewards_history       # GET /employees/{id}/rewards → list đúng NV
    test_unauthenticated_returns_401
```

---

## Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Upload file thành công nhưng DB insert lỗi | Upload TRƯỚC, nếu DB lỗi thì xóa file MinIO trong except block |
| Xóa record xong nhưng MinIO delete lỗi | Log warning, không raise — record đã xóa, orphan file xử lý bằng cleanup job sau |
| `is_monetary` của reward_type bị sửa sau khi đã có records | Khi sửa type: nếu đổi `is_monetary` → validate không có records cũ bị vi phạm; hoặc đơn giản là chặn sửa `is_monetary` |
| File quá lớn | Validate file size <= 10MB ở service layer trước khi gọi MinIO |
| MIME type giả mạo | Chấp nhận rủi ro ở phase này — chỉ whitelist extension phổ biến |

---

## Thứ tự thực hiện

```
Slice 1 (Migration + Catalog API)
  ↓
Slice 2 (CRUD Rewards + file)
  ↓
Slice 3 (Frontend)
  ↓
Slice 4 (Tests)
```

---

## Không nằm trong 8.1

| Phần | Thuộc về |
|---|---|
| Kỷ luật nhân viên | 8.2 |
| Báo cáo tổng hợp | 8.3 |
| Liên kết kết quả KPI với khen thưởng | 10.4 |
| Import hàng loạt quyết định khen thưởng | Ngoài phạm vi |
| Quy trình phê duyệt khen thưởng | Ngoài phạm vi |
