# Kế hoạch triển khai — 8.3. Báo cáo Khen thưởng & Kỷ luật

**Phạm vi:** Báo cáo tổng hợp khen thưởng/kỷ luật theo kỳ · Thống kê theo phòng ban và loại · Xuất Excel  
**Phụ thuộc:** `8.1 Khen thưởng` ✅ · `8.2 Kỷ luật` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §8.3

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_rewards` table | ✅ Hoàn thành (8.1) | |
| `employee_disciplines` table | ✅ Hoàn thành (8.2) | |
| API báo cáo | ❌ Chưa có | |
| Tab Báo cáo trong `RewardsView.vue` | ❌ Chưa có (placeholder) | |

---

## Phạm vi báo cáo

Theo FEATURES.md §8.3:
> Báo cáo tổng hợp khen thưởng/kỷ luật theo kỳ  
> Thống kê theo phòng ban, loại khen thưởng/kỷ luật

---

## Thiết kế API

### Không tạo model mới — tất cả tính từ `employee_rewards` + `employee_disciplines`

### Endpoint báo cáo tổng hợp

```
GET /rewards/report/summary
    ?from_date=&to_date=&department_id=
    → RewardDisciplineReportPage

GET /rewards/report/export
    ?from_date=&to_date=&department_id=
    → StreamingResponse (.xlsx)
```

---

## Schemas

### Báo cáo tổng hợp (`RewardDisciplineReportPage`)

```python
class RewardTypeStat(BaseModel):
    reward_type_id: int
    reward_type_name: str
    count: int
    total_value: Decimal | None      # chỉ có với loại tiền tệ

class DisciplineFormStat(BaseModel):
    discipline_form: str             # 'khien_trach' | ...
    discipline_form_label: str
    count: int

class DepartmentRewardStat(BaseModel):
    department_id: int | None
    department_name: str | None      # None = chưa phân phòng ban
    reward_count: int
    discipline_count: int

class RewardDisciplineSummary(BaseModel):
    total_rewards: int
    total_disciplines: int
    total_reward_value: Decimal      # tổng giá trị thưởng tiền (VND)
    by_reward_type: list[RewardTypeStat]
    by_discipline_form: list[DisciplineFormStat]
    by_department: list[DepartmentRewardStat]

class RewardDisciplineReportPage(BaseModel):
    from_date: date
    to_date: date
    department_id: int | None
    department_name: str | None      # tên phòng ban nếu có filter
    summary: RewardDisciplineSummary
    reward_items: list[RewardRead]   # danh sách chi tiết khen thưởng
    discipline_items: list[DisciplineRead]  # danh sách chi tiết kỷ luật
    total_rewards: int               # pagination
    total_disciplines: int
```

---

## Service logic

```python
async def get_reward_discipline_report(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
) -> RewardDisciplineReportPage:
    """
    1. Query employee_rewards JOIN employees JOIN departments
       WHERE reward_date BETWEEN from_date AND to_date
       (+ filter department_id nếu có)
       → danh sách rewards + group by reward_type_id (count, sum value)
       → group by department_id (reward_count)

    2. Query employee_disciplines JOIN employees JOIN departments
       WHERE effective_date BETWEEN from_date AND to_date
       (+ filter department_id)
       → danh sách disciplines + group by discipline_form (count)
       → group by department_id (discipline_count)

    3. Merge department stats từ cả 2 query
    4. Trả RewardDisciplineReportPage
    """

async def export_reward_discipline_excel(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
    company_name: str = "CÔNG TY TNHH HỒNG HÀ",
) -> bytes:
    """
    Tạo file Excel 2 sheet:
    - Sheet 1: "Khen thưởng" — bảng chi tiết khen thưởng
    - Sheet 2: "Kỷ luật" — bảng chi tiết kỷ luật
    """
```

---

## Thiết kế Excel Export

### Tên file
`khen_thuong_ky_luat_{from_date}_{to_date}.xlsx`

### Sheet 1: "Khen thưởng"

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged, bold, font 14)
Hàng 2: [DANH SÁCH KHEN THƯỞNG {DD/MM/YYYY – DD/MM/YYYY}] (merged, bold, font 12)
Hàng 3: trống
Hàng 4: Header cột
  A: STT
  B: Mã NV
  C: Họ và tên
  D: Phòng ban
  E: Loại khen thưởng
  F: Tiêu đề / Nội dung
  G: Số quyết định
  H: Ngày khen thưởng
  I: Giá trị (VND)
  J: Đơn vị khen thưởng
Hàng 5+: Dữ liệu
Hàng cuối: TỔNG CỘNG (bold)
```

### Sheet 2: "Kỷ luật"

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ]
Hàng 2: [DANH SÁCH KỶ LUẬT {DD/MM/YYYY – DD/MM/YYYY}]
Hàng 3: trống
Hàng 4: Header cột
  A: STT
  B: Mã NV
  C: Họ và tên
  D: Phòng ban
  E: Hình thức kỷ luật
  F: Tiêu đề / Vi phạm
  G: Số quyết định
  H: Ngày vi phạm
  I: Ngày hiệu lực
  J: Ngày hết hiệu lực
  K: Đơn vị ký
Hàng 5+: Dữ liệu
Hàng cuối: TỔNG CỘNG (bold)
```

**Định dạng:**
- Header (hàng 4): nền `#1F4E79`, chữ trắng, bold
- Xen kẽ: `#F2F2F2` / trắng
- Dòng tổng: `#D9E1F2`, bold
- Cột giá trị (VND): format `#,##0`
- Cột ngày: format `DD/MM/YYYY`

---

## Thiết kế Frontend

### Tab "Báo cáo" trong `RewardsView.vue`

```
┌────────────────────────────────────────────────────────────────────┐
│  Báo cáo Khen thưởng & Kỷ luật                                     │
├────────────────────────────────────────────────────────────────────┤
│ Từ ngày: [01/01/2026]  Đến ngày: [31/12/2026]                      │
│ Phòng ban: [Tất cả ▼]                                              │
│                                     [Xem báo cáo] [Xuất Excel ↓]   │
├────────────────────────────────────────────────────────────────────┤
│                    ┌──────────────┬──────────────┐                  │
│  TỔNG KHEN THƯỞNG  │     12       │  Tổng KL: 3  │                  │
│  Tổng giá trị: 50M │              │              │                  │
│                    └──────────────┴──────────────┘                  │
├───────────────────────────────────────────────────────────────────┤
│  [Theo loại khen thưởng]              [Theo phòng ban]             │
│  ┌─────────────────────────────┐      ┌──────────────────────────┐ │
│  │ Thưởng tiền     ████ 6      │      │ Phòng ban A    KT:4  KL:2│ │
│  │ Bằng khen       ██   3      │      │ Phòng ban B    KT:5  KL:1│ │
│  │ Giấy khen       ███  3      │      │ Phòng ban C    KT:3  KL:0│ │
│  └─────────────────────────────┘      └──────────────────────────┘ │
├───────────────────────────────────────────────────────────────────┤
│  [Tab: Chi tiết Khen thưởng] [Tab: Chi tiết Kỷ luật]              │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ DataTable chi tiết (paginated)                             │   │
│  └────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

### Component `RewardDisciplineReport.vue`

**Phần tóm tắt (Summary Cards):**
- Card 1: Tổng khen thưởng (số lượng + tổng giá trị tiền)
- Card 2: Tổng kỷ luật (số lượng)

**Phần thống kê:**
- Bảng "Theo loại khen thưởng": cột `Loại`, `Số lượng`, `Tổng giá trị`
- Bảng "Theo hình thức kỷ luật": cột `Hình thức`, `Số lượng`
- Bảng "Theo phòng ban": cột `Phòng ban`, `Số KT`, `Số KL`

**Phần chi tiết (Tabs bên dưới):**
- Sub-tab "Khen thưởng": DataTable paginated giống `RewardListTab` (read-only, không có nút tạo/sửa/xóa)
- Sub-tab "Kỷ luật": DataTable paginated giống `DisciplineListTab` (read-only)

> **Không dùng biểu đồ (Chart)** ở phase này — chỉ bảng thống kê text để đơn giản. Chart thuộc về module 11 (Dashboard).

---

## Cấu trúc file mới / thay đổi

```
backend/
  app/schemas/reward_report.py                              (NEW)
  app/services/reward_report_service.py                     (NEW)
  app/services/reward_export_service.py                     (NEW: export Excel)
  app/api/v1/endpoints/rewards.py                           (EDIT: thêm /report endpoints)
  tests/test_reward_report.py                               (NEW)

frontend/
  src/services/rewardReportService.ts                       (NEW)
  src/views/rewards/components/RewardDisciplineReport.vue   (NEW)
  src/views/rewards/RewardsView.vue                         (EDIT: thêm tab Báo cáo)
  src/assets/styles/views/_rewards.scss                     (EDIT: thêm report styles)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: API báo cáo tổng hợp

**Tasks:**
1. Schema `RewardDisciplineSummary`, `RewardDisciplineReportPage`
2. Service `reward_report_service.py`: `get_reward_discipline_report()`
3. Thêm endpoint `GET /rewards/report/summary` vào `rewards.py`

**Exit criteria:**
- API trả đúng `total_rewards`, `total_disciplines`
- `by_reward_type` group đúng số lượng
- `by_discipline_form` group đúng 4 hình thức
- `by_department` merge dữ liệu từ cả reward + discipline
- Filter `from_date`, `to_date`, `department_id` hoạt động
- Khoảng thời gian không có dữ liệu: trả summary với tất cả count = 0

---

### Slice 2 — Backend: Export Excel

**Tasks:**
1. `reward_export_service.py`: `export_reward_discipline_excel()`
2. Thêm endpoint `GET /rewards/report/export`

**Exit criteria:**
- File `.xlsx` hợp lệ, mở được
- Sheet "Khen thưởng" đúng cột, đúng dữ liệu
- Sheet "Kỷ luật" đúng cột, đúng dữ liệu
- Tên file format đúng
- Khi không có dữ liệu: trả file với chỉ header + 0 dòng

---

### Slice 3 — Frontend: Tab Báo cáo

**Tasks:**
1. `rewardReportService.ts`: types + API calls
2. `RewardDisciplineReport.vue`: summary cards + bảng thống kê + sub-tabs chi tiết
3. Thêm tab "Báo cáo" vào `RewardsView.vue`
4. CSS styles

**Exit criteria:**
- Chọn kỳ + nhấn Xem → hiển thị summary cards đúng số
- Bảng thống kê theo loại / phòng ban đúng
- Sub-tab chi tiết khen thưởng / kỷ luật hiển thị đúng
- Nút Xuất Excel tải file
- Không có scoped style

---

### Slice 4 — Tests

**File:** `backend/tests/test_reward_report.py`

```python
class TestRewardDisciplineReport:
    test_empty_period_returns_zero_counts
    test_counts_rewards_in_date_range
    test_excludes_rewards_outside_date_range
    test_counts_disciplines_in_date_range
    test_filter_by_department
    test_by_reward_type_groups_correctly
    test_by_discipline_form_groups_correctly
    test_by_department_merges_reward_and_discipline_stats
    test_monetary_reward_value_summed_correctly
    test_unauthenticated_returns_401

class TestRewardDisciplineExport:
    test_returns_xlsx_content_type
    test_file_is_valid_xlsx
    test_sheet_khen_thuong_exists
    test_sheet_ky_luat_exists
    test_reward_sheet_correct_row_count
    test_discipline_sheet_correct_row_count
    test_filename_contains_date_range
```

---

## Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Kỳ báo cáo rất dài (cả năm, nhiều NV) → API chậm | Không phân trang summary (chỉ COUNT/SUM), chỉ phân trang chi tiết items; target < 2s cho 500 records |
| `department_id = NULL` (NV chưa có phòng ban) | Group vào bucket "Chưa phân phòng ban" (`department_name = null`) |
| Chi tiết rewards/disciplines trong report page quá nhiều | `reward_items` + `discipline_items` phân trang riêng (page, page_size); summary aggregates không phân trang |
| Export file lớn | openpyxl streaming mode nếu > 5000 rows; bình thường load full |

---

## Thứ tự thực hiện

```
Slice 1 (Backend: API Summary)
  ↓
Slice 2 (Backend: Export Excel)
  ↓
Slice 3 (Frontend: Tab Báo cáo)
  ↓
Slice 4 (Tests)
```

---

## Không nằm trong 8.3

| Phần | Thuộc về |
|---|---|
| Dashboard headcount / biểu đồ KPI | 11.1 Dashboard |
| Báo cáo đào tạo | 9.4 |
| Export PDF | Ngoài phạm vi (chỉ Excel) |
| Báo cáo lịch sử khen thưởng từng cá nhân (dạng "transcript") | Có thể xuất từ hồ sơ NV (3.x) |
