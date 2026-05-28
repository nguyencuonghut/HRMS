# Kế hoạch triển khai — 11.2. Báo cáo Nhân sự

**Phạm vi:** Danh sách nhân viên · Biến động nhân sự · Thâm niên · Cơ cấu tổ chức  
**Phụ thuộc:** Module 3 (nhân viên) ✅ · Module 1 (tổ chức) ✅ · Module 4 (hợp đồng) ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §11.2  
**Đặc điểm:** Module chỉ đọc — không ghi dữ liệu, không workflow phê duyệt

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employees` table | ✅ Hoàn thành (Module 3) | `status`, `start_date`, `resigned_date`, `gender`, `is_active` |
| `employee_job_records` table | ✅ Hoàn thành (Module 3) | `is_current`, `department_id`, `job_title_id`, `effective_from` |
| `departments` table | ✅ Hoàn thành (Module 1) | `parent_id` (cây phân cấp), `is_active` |
| `employee_contracts` table | ✅ Hoàn thành (Module 4) | `contract_category_id`, `document_kind`, `status`, `effective_from` |
| `contract_categories` table | ✅ Hoàn thành (Module 4) | `document_kind` (labor/probation/addendum) |
| API báo cáo nhân sự | ❌ Chưa có | Cần tạo mới |
| `HRReportView.vue` | ❌ Chưa có | `ReportView.vue` hiện chỉ là placeholder |
| Service `hr_report_service.py` | ❌ Chưa có | |
| Schema `hr_report.py` | ❌ Chưa có | |

---

## Phạm vi

Theo FEATURES.md §11.2:
> Danh sách nhân viên theo nhiều tiêu chí lọc  
> Báo cáo biến động nhân sự: tuyển dụng, thôi việc theo tháng/quý/năm  
> Báo cáo thâm niên nhân viên  
> Báo cáo cơ cấu tổ chức

**Trong phạm vi:**
- **Danh sách nhân viên** với bộ lọc đa tiêu chí: phòng ban, trạng thái (`probation`/`official`/`long_leave`/`resigned`), giới tính (`male`/`female`/`other`), loại hợp đồng (`document_kind`), khoảng ngày vào làm (`start_date`), thâm niên (năm làm việc tính từ `start_date`)
- **Báo cáo biến động nhân sự**: tuyển dụng (nhân viên mới theo `start_date`), thôi việc (theo `resigned_date`), chuyển bộ phận (EmployeeJobRecord tạo mới với `is_current=True`) theo tháng/quý/năm
- **Báo cáo thâm niên**: phân nhóm < 1 năm · 1–3 năm · 3–5 năm · 5–10 năm · > 10 năm, lọc theo phòng ban
- **Báo cáo cơ cấu tổ chức**: headcount theo phòng ban (cây) + chức danh (`job_title`)
- Xuất Excel (openpyxl) toàn bộ 4 loại báo cáo
- Responsive mobile: filter panel dạng drawer trên màn hình nhỏ

**Ngoài phạm vi:**
- Dự báo nghỉ việc / phân tích turnover dự báo
- Phân tích sentiment, satisfaction
- Chart / biểu đồ trực quan (thuộc 11.1 Dashboard)
- So sánh kỳ với kỳ (YoY)
- Lưu mẫu báo cáo tùy chỉnh (thuộc 11.6)

**Không tạo bảng mới** — tất cả tính từ:
- `employees` + `employee_job_records` + `departments` + `job_titles` + `employee_contracts` + `contract_categories`

---

## Các báo cáo và SQL Queries

### 1. Danh sách nhân viên (Employee List)

**Mục đích:** Xuất danh sách toàn bộ nhân viên với bộ lọc đa tiêu chí, phân trang server-side.

**Logic:**
```
SELECT
    e.id, e.full_name, e.gender, e.date_of_birth, e.status, e.start_date,
    e.resigned_date, e.is_active,
    d.name AS department_name,
    jt.name AS job_title_name,
    cc.name AS contract_category_name,
    ec.document_kind,
    -- Thâm niên tính đến ngày hôm nay (hoặc resigned_date nếu đã nghỉ)
    EXTRACT(YEAR FROM AGE(COALESCE(e.resigned_date, CURRENT_DATE), e.start_date)) AS tenure_years
FROM employees e
LEFT JOIN employee_job_records ejr
    ON ejr.employee_id = e.id AND ejr.is_current = TRUE
LEFT JOIN departments d ON d.id = ejr.department_id
LEFT JOIN job_titles jt ON jt.id = ejr.job_title_id
LEFT JOIN employee_contracts ec
    ON ec.employee_id = e.id
    AND ec.status = 'active'
    AND ec.parent_contract_id IS NULL           -- chỉ lấy HĐ gốc (không phải phụ lục)
LEFT JOIN contract_categories cc ON cc.id = ec.contract_category_id
WHERE
    (:department_id IS NULL OR ejr.department_id = :department_id)
    AND (:status IS NULL OR e.status = :status)
    AND (:gender IS NULL OR e.gender = :gender)
    AND (:document_kind IS NULL OR ec.document_kind = :document_kind)
    AND (:start_date_from IS NULL OR e.start_date >= :start_date_from)
    AND (:start_date_to IS NULL OR e.start_date <= :start_date_to)
    AND (:tenure_min IS NULL OR
         EXTRACT(YEAR FROM AGE(COALESCE(e.resigned_date, CURRENT_DATE), e.start_date)) >= :tenure_min)
    AND (:tenure_max IS NULL OR
         EXTRACT(YEAR FROM AGE(COALESCE(e.resigned_date, CURRENT_DATE), e.start_date)) < :tenure_max)
ORDER BY e.full_name
LIMIT :limit OFFSET :offset
```

**Ghi chú triển khai:** SQLAlchemy async — dùng `select()` kết hợp `outerjoin()`. Phân trang bằng `limit/offset`. Đếm tổng bằng `func.count()` trên subquery.

---

### 2. Biến động nhân sự (Movement Report)

**Mục đích:** Theo dõi tuyển dụng, thôi việc, chuyển bộ phận theo kỳ (tháng/quý/năm).

**Logic tuyển dụng mới:**
```
SELECT
    DATE_TRUNC(:group_by, e.start_date) AS period,
    COUNT(e.id) AS hired_count,
    d.name AS department_name
FROM employees e
LEFT JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
LEFT JOIN departments d ON d.id = ejr.department_id
WHERE e.start_date BETWEEN :start_date AND :end_date
GROUP BY period, d.name
ORDER BY period
```

**Logic thôi việc:**
```
SELECT
    DATE_TRUNC(:group_by, e.resigned_date) AS period,
    COUNT(e.id) AS resigned_count
FROM employees e
WHERE e.resigned_date BETWEEN :start_date AND :end_date
GROUP BY period
ORDER BY period
```

**Logic chuyển bộ phận** (đếm số bản ghi EmployeeJobRecord mới trong kỳ, không phải bản ghi đầu tiên):
```
SELECT
    DATE_TRUNC(:group_by, ejr.effective_from) AS period,
    COUNT(ejr.id) AS transfer_count
FROM employee_job_records ejr
JOIN employees e ON e.id = ejr.employee_id
WHERE ejr.effective_from BETWEEN :start_date AND :end_date
  -- Loại bỏ bản ghi đầu tiên (tức là bản ghi vào làm):
  AND ejr.effective_from != e.start_date
  AND e.is_active = TRUE
GROUP BY period
ORDER BY period
```

**group_by mapping:**
| Param | `DATE_TRUNC` |
|---|---|
| `month` | `'month'` |
| `quarter` | `'quarter'` |
| `year` | `'year'` |

**Triển khai:** Vì SQLAlchemy cần raw-SQL cho `DATE_TRUNC`, dùng `sa.func.date_trunc(:group_by, column)`.

---

### 3. Thâm niên (Tenure Analysis)

**Mục đích:** Phân loại nhân viên theo nhóm thâm niên, lọc theo phòng ban.

**Nhóm thâm niên:**
| Nhóm | Điều kiện |
|---|---|
| `< 1 năm` | tenure_years < 1 |
| `1–3 năm` | 1 <= tenure_years < 3 |
| `3–5 năm` | 3 <= tenure_years < 5 |
| `5–10 năm` | 5 <= tenure_years < 10 |
| `> 10 năm` | tenure_years >= 10 |

**Logic:**
```
WITH tenure_calc AS (
    SELECT
        e.id, e.full_name, e.start_date,
        ejr.department_id,
        d.name AS department_name,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.start_date))::int AS tenure_years
    FROM employees e
    LEFT JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
    LEFT JOIN departments d ON d.id = ejr.department_id
    WHERE e.is_active = TRUE
      AND (:department_id IS NULL OR ejr.department_id = :department_id)
)
SELECT
    CASE
        WHEN tenure_years < 1  THEN 'lt_1'
        WHEN tenure_years < 3  THEN '1_3'
        WHEN tenure_years < 5  THEN '3_5'
        WHEN tenure_years < 10 THEN '5_10'
        ELSE 'gt_10'
    END AS tenure_group,
    COUNT(id) AS headcount,
    ROUND(AVG(tenure_years), 1) AS avg_tenure_years
FROM tenure_calc
GROUP BY tenure_group
ORDER BY MIN(tenure_years)
```

**Chi tiết danh sách nhân viên từng nhóm** sẽ được trả kèm (array per group).

---

### 4. Cơ cấu tổ chức (Org Structure)

**Mục đích:** Headcount theo phòng ban (cây phân cấp) + chức danh. Hỗ trợ `department_id` để drill-down.

**Logic:**
```
SELECT
    d.id AS department_id,
    d.name AS department_name,
    d.parent_id,
    jt.id AS job_title_id,
    jt.name AS job_title_name,
    jt.level AS job_level,
    COUNT(ejr.employee_id) AS headcount
FROM departments d
LEFT JOIN employee_job_records ejr ON ejr.department_id = d.id AND ejr.is_current = TRUE
LEFT JOIN employees e ON e.id = ejr.employee_id AND e.is_active = TRUE
LEFT JOIN job_titles jt ON jt.id = ejr.job_title_id
WHERE d.is_active = TRUE
  AND (:department_id IS NULL OR d.id = :department_id OR d.parent_id = :department_id)
GROUP BY d.id, d.name, d.parent_id, jt.id, jt.name, jt.level
ORDER BY d.parent_id NULLS FIRST, d.name, jt.level
```

**Service sẽ xây dựng cây trong Python:** Nhóm theo `department_id`, tính `total_headcount` bao gồm cả phòng con (đệ quy).

---

## API Design

### Endpoints

```
GET /api/v1/reports/hr/employee-list
    ?page=1&page_size=20
    &department_id=<int>
    &status=probation|official|long_leave|resigned
    &gender=male|female|other
    &document_kind=labor|probation|addendum
    &start_date_from=YYYY-MM-DD
    &start_date_to=YYYY-MM-DD
    &tenure_min=<int>    (năm, inclusive)
    &tenure_max=<int>    (năm, exclusive)
    → EmployeeListResponse (paginated)

GET /api/v1/reports/hr/movement
    ?start_date=YYYY-MM-DD  (required)
    &end_date=YYYY-MM-DD    (required)
    &group_by=month|quarter|year  (default: month)
    &department_id=<int>
    → MovementReportResponse

GET /api/v1/reports/hr/tenure
    ?department_id=<int>
    → TenureReportResponse

GET /api/v1/reports/hr/org-structure
    ?department_id=<int>    (optional — nếu không có: toàn bộ)
    → OrgStructureResponse

GET /api/v1/reports/hr/export
    ?type=employee-list|movement|tenure|org-structure
    &<tham số lọc tương ứng với từng type>
    → StreamingResponse (.xlsx)
    Content-Disposition: attachment; filename="bao_cao_nhan_su_{type}_{date}.xlsx"
```

### Permissions

| Endpoint | Permission |
|---|---|
| Tất cả GET báo cáo | `hr_report:view` |
| Export Excel | `hr_report:view` |

### Prefix router

Router đăng ký tại: `app/api/v1/endpoints/hr_reports.py`  
Prefix: `/reports/hr`  
Tag: `HR Reports`

---

## Schemas (Pydantic v2) — `app/schemas/hr_report.py`

```python
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, computed_field


# ─── Employee List ────────────────────────────────────────────────────────────

class EmployeeListItem(BaseModel):
    id: int
    employee_code: Optional[str] = None
    full_name: str
    gender: str
    date_of_birth: Optional[date] = None
    status: str                          # probation | official | long_leave | resigned
    start_date: date
    resigned_date: Optional[date] = None
    is_active: bool
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    job_title_name: Optional[str] = None
    contract_category_name: Optional[str] = None
    document_kind: Optional[str] = None  # labor | probation | addendum
    tenure_years: int                    # số năm thâm niên làm tròn xuống

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Movement Report ─────────────────────────────────────────────────────────

class MovementPeriodRow(BaseModel):
    period_label: str                    # "2024-01", "Q1/2024", "2024"
    period_start: date
    period_end: date
    hired_count: int
    resigned_count: int
    transfer_count: int
    net_change: int                      # hired - resigned


class MovementReportResponse(BaseModel):
    group_by: str                        # month | quarter | year
    start_date: date
    end_date: date
    rows: list[MovementPeriodRow]
    total_hired: int
    total_resigned: int
    total_transfers: int


# ─── Tenure Report ───────────────────────────────────────────────────────────

class TenureGroupDetail(BaseModel):
    id: int
    full_name: str
    department_name: Optional[str] = None
    start_date: date
    tenure_years: int


class TenureGroup(BaseModel):
    group_key: str                       # lt_1 | 1_3 | 3_5 | 5_10 | gt_10
    group_label: str                     # "< 1 năm" | "1–3 năm" | ...
    headcount: int
    percentage: float                    # % trên tổng nhân viên is_active
    avg_tenure_years: float
    employees: list[TenureGroupDetail]


class TenureReportResponse(BaseModel):
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    total_active: int
    avg_tenure_years: float
    groups: list[TenureGroup]


# ─── Org Structure ───────────────────────────────────────────────────────────

class JobTitleHeadcount(BaseModel):
    job_title_id: Optional[int] = None
    job_title_name: Optional[str] = None
    job_level: Optional[int] = None
    headcount: int


class DepartmentNode(BaseModel):
    department_id: int
    department_name: str
    parent_id: Optional[int] = None
    total_headcount: int                 # bao gồm phòng con
    direct_headcount: int                # chỉ nhân viên trực tiếp (không tính phòng con)
    by_job_title: list[JobTitleHeadcount]
    children: list["DepartmentNode"] = Field(default_factory=list)


DepartmentNode.model_rebuild()


class OrgStructureResponse(BaseModel):
    total_headcount: int
    department_count: int
    tree: list[DepartmentNode]
```

---

## Service Logic — `app/services/hr_report_service.py`

### Cấu trúc module

```python
"""Service báo cáo nhân sự (11.2)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from math import ceil

import sqlalchemy as sa
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ContractCategory
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobTitle
from app.schemas.hr_report import (
    DepartmentNode,
    EmployeeListItem,
    EmployeeListResponse,
    JobTitleHeadcount,
    MovementPeriodRow,
    MovementReportResponse,
    OrgStructureResponse,
    TenureGroup,
    TenureGroupDetail,
    TenureReportResponse,
)
```

### Hàm `get_employee_list()`

```python
async def get_employee_list(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    gender: Optional[str] = None,
    document_kind: Optional[str] = None,
    start_date_from: Optional[date] = None,
    start_date_to: Optional[date] = None,
    tenure_min: Optional[int] = None,
    tenure_max: Optional[int] = None,
) -> EmployeeListResponse:
```

**Các bước xử lý:**
1. Build `stmt` với `select(Employee, EmployeeJobRecord, Department, JobTitle, EmployeeContract, ContractCategory)` + `outerjoin` lần lượt từng bảng
2. Điều kiện `EmployeeJobRecord.is_current == True`
3. Điều kiện `EmployeeContract.status == 'active'` và `EmployeeContract.parent_contract_id.is_(None)`
4. Áp dụng các filter tùy chọn
5. Tính `tenure_years` trong Python: `(today - employee.start_date).days // 365`
6. Filter `tenure_min/tenure_max` sau khi tính (hoặc dùng subquery với `AGE`)
7. Đếm tổng bằng `count_stmt` riêng
8. Phân trang: `limit(page_size).offset((page - 1) * page_size)`

### Hàm `get_movement_report()`

```python
async def get_movement_report(
    session: AsyncSession,
    *,
    start_date: date,
    end_date: date,
    group_by: str = "month",   # month | quarter | year
    department_id: Optional[int] = None,
) -> MovementReportResponse:
```

**Các bước xử lý:**
1. Xác định các kỳ (period) trong khoảng `start_date`–`end_date` theo `group_by`
2. Query tuyển dụng: `Employee.start_date BETWEEN start_date AND end_date`, group theo kỳ
3. Query thôi việc: `Employee.resigned_date BETWEEN start_date AND end_date`, group theo kỳ
4. Query chuyển bộ phận: `EmployeeJobRecord.effective_from BETWEEN ...` AND `effective_from != employee.start_date`
5. Merge kết quả theo kỳ (dict lookup)
6. Tính nhãn `period_label`: `"2024-01"` cho month, `"Q1/2024"` cho quarter, `"2024"` cho year
7. Tính `net_change = hired - resigned`

**Helper `_period_label(period_start, group_by)`:**
```python
def _period_label(d: date, group_by: str) -> str:
    if group_by == "month":
        return d.strftime("%Y-%m")
    elif group_by == "quarter":
        q = (d.month - 1) // 3 + 1
        return f"Q{q}/{d.year}"
    else:
        return str(d.year)
```

### Hàm `get_tenure_report()`

```python
async def get_tenure_report(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
) -> TenureReportResponse:
```

**Các bước xử lý:**
1. Query tất cả nhân viên `is_active=True` (+ lọc `department_id`)
2. Tính `tenure_years` cho từng nhân viên trong Python
3. Phân nhóm vào 5 bucket theo thâm niên
4. Tính `percentage` = `group.headcount / total_active * 100`
5. Tính `avg_tenure_years` toàn cục

**TENURE_GROUPS constant:**
```python
TENURE_GROUPS = [
    ("lt_1",  "< 1 năm",   0,  1),
    ("1_3",   "1–3 năm",   1,  3),
    ("3_5",   "3–5 năm",   3,  5),
    ("5_10",  "5–10 năm",  5, 10),
    ("gt_10", "> 10 năm", 10, 999),
]
```

### Hàm `get_org_structure()`

```python
async def get_org_structure(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
) -> OrgStructureResponse:
```

**Các bước xử lý:**
1. Load tất cả departments (hoặc cây con từ `department_id`)
2. Load headcount theo `(department_id, job_title_id)` từ `employee_job_records` + `employees.is_active=True`
3. Build dict `dept_nodes: dict[int, DepartmentNode]`
4. Đệ quy tính `total_headcount` bao gồm cả children
5. Ghép cây: gán `children` theo `parent_id`
6. Root nodes = nodes không có `parent_id` (hoặc `parent_id` không có trong dataset)

### Hàm `export_to_excel()`

```python
async def export_employee_list_excel(session, **filters) -> bytes:
async def export_movement_excel(session, **filters) -> bytes:
async def export_tenure_excel(session, **filters) -> bytes:
async def export_org_structure_excel(session, **filters) -> bytes:
```

**Mỗi hàm:**
1. Gọi hàm service tương ứng (không phân trang — lấy tất cả)
2. Tạo `openpyxl.Workbook()`
3. Ghi header (font bold, background color header row)
4. Ghi data rows
5. Auto-fit column width (tính max length per column)
6. `return workbook_to_bytes(wb)` → `io.BytesIO`

**`workbook_to_bytes(wb)`:**
```python
def workbook_to_bytes(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
```

**Cấu trúc sheet Excel từng loại:**

| Báo cáo | Sheet name | Columns chính |
|---|---|---|
| employee-list | Danh sách nhân viên | Mã NV, Họ tên, Giới tính, Ngày vào, Phòng ban, Chức danh, Loại HĐ, Thâm niên (năm), Trạng thái |
| movement | Biến động nhân sự | Kỳ, Tuyển dụng, Thôi việc, Chuyển bộ phận, Biến động ròng |
| tenure | Thâm niên | Nhóm, Số NV, Tỷ lệ (%), Thâm niên TB (năm) + Sheet chi tiết từng nhóm |
| org-structure | Cơ cấu tổ chức | Phòng ban, Phòng cha, Chức danh, Headcount |

---

## Frontend Design

### Route

```
/reports/hr  →  HRReportView.vue
```

Cập nhật `frontend/src/router/index.ts`:
```typescript
{
  path: "reports/hr",
  name: "reports-hr",
  component: () => import("@/views/reports/HRReportView.vue"),
}
```

### Cấu trúc component

```
views/reports/
├── HRReportView.vue              ← View chính, Tab container
└── components/
    ├── EmployeeListTab.vue       ← Tab 1: Danh sách nhân viên
    ├── MovementTab.vue           ← Tab 2: Biến động nhân sự
    ├── TenureTab.vue             ← Tab 3: Thâm niên
    └── OrgStructureTab.vue       ← Tab 4: Cơ cấu tổ chức
```

### `HRReportView.vue` — Tab container

```html
<template>
  <div>
    <div class="page-header">
      <h2>Báo cáo Nhân sự</h2>
    </div>
    <TabView v-model:activeIndex="activeTab" lazy>
      <TabPanel header="Danh sách nhân viên">
        <EmployeeListTab />
      </TabPanel>
      <TabPanel header="Biến động nhân sự">
        <MovementTab />
      </TabPanel>
      <TabPanel header="Thâm niên">
        <TenureTab />
      </TabPanel>
      <TabPanel header="Cơ cấu tổ chức">
        <OrgStructureTab />
      </TabPanel>
    </TabView>
  </div>
</template>
```

Dùng `lazy` trên `TabView` để tránh load tất cả tabs cùng lúc.

### Tab 1 — `EmployeeListTab.vue`

**Layout desktop:**
```
┌─ Filter Panel (Card, collapsible) ──────────────────────────────────┐
│ [Phòng ban ▼] [Trạng thái ▼] [Giới tính ▼] [Loại HĐ ▼]           │
│ Ngày vào: [từ ngày] → [đến ngày]  Thâm niên: [min] - [max] năm    │
│                                         [Xóa lọc] [Tìm kiếm]       │
└─────────────────────────────────────────────────────────────────────┘
┌─ DataTable ─────────────────────────────────────────────────────────┐
│ Mã NV | Họ tên | Giới tính | Ngày vào | Phòng ban | Chức danh |    │
│ Loại HĐ | Thâm niên | Trạng thái                                    │
│ [← 1 2 3 ... →] (server-side pagination)                           │
└─────────────────────────────────────────────────────────────────────┘
[Xuất Excel]
```

**Mobile:** Filter panel collapse thành Drawer (sidebar từ trái). Button `Bộ lọc` mở drawer.

**PrimeVue components:** `DataTable`, `Column`, `Paginator`, `Select` (dropdown), `DatePicker`, `InputNumber`, `Button`, `Card`, `Drawer`

**Composable `useEmployeeListReport.ts`:**
```typescript
const filters = reactive({
  department_id: null as number | null,
  status: null as string | null,
  gender: null as string | null,
  document_kind: null as string | null,
  start_date_from: null as string | null,
  start_date_to: null as string | null,
  tenure_min: null as number | null,
  tenure_max: null as number | null,
})
const page = ref(1)
const pageSize = ref(20)

const { data, isLoading, refetch } = useQuery(...)

async function exportExcel() {
  const url = buildExportUrl('employee-list', filters)
  window.open(url, '_blank')
}
```

### Tab 2 — `MovementTab.vue`

**Layout:**
```
┌─ Controls ──────────────────────────────────────────────────────────┐
│ Kỳ: [Năm ▼] [2024 ▼]    Nhóm theo: [Tháng] [Quý] [Năm]          │
│                                               [Xuất Excel]          │
└─────────────────────────────────────────────────────────────────────┘
┌─ DataTable ─────────────────────────────────────────────────────────┐
│ Kỳ | Tuyển dụng | Thôi việc | Chuyển bộ phận | Biến động ròng     │
└─────────────────────────────────────────────────────────────────────┘
```

**Toggle group_by:** `SelectButton` PrimeVue với options `[{ label: 'Tháng', value: 'month' }, ...]`

**Columns:** Biến động ròng hiển thị màu xanh nếu dương, đỏ nếu âm (dùng PrimeVue `Tag` hoặc class binding).

### Tab 3 — `TenureTab.vue`

**Layout:**
```
┌─ Filter ────────────────────────────────────────────────────────────┐
│ [Phòng ban ▼]                           [Xuất Excel]                │
└─────────────────────────────────────────────────────────────────────┘
┌─ Summary cards (5 cards) ────────────────────────────────────────────┐
│ [< 1 năm: 12 NV (8%)] [1-3 năm: 45 NV (30%)] ...                  │
└─────────────────────────────────────────────────────────────────────┘
┌─ DataTable (grouped by tenure_group) ───────────────────────────────┐
│ Nhóm thâm niên | Số nhân viên | Tỷ lệ | Thâm niên TB              │
│ ▶ Danh sách (expandable row per group)                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Row expansion:** Mỗi row nhóm thâm niên expand ra DataTable con liệt kê nhân viên.

### Tab 4 — `OrgStructureTab.vue`

**Layout:**
```
┌─ Filter ────────────────────────────────────────────────────────────┐
│ [Phòng ban gốc ▼]                       [Xuất Excel]               │
└─────────────────────────────────────────────────────────────────────┘
┌─ TreeTable ─────────────────────────────────────────────────────────┐
│ ▼ Ban Giám đốc                      5 NV                            │
│   ▼ Phòng Kế toán                   12 NV                           │
│       Kế toán trưởng                 1                              │
│       Kế toán viên                   8                              │
│       Thủ quỹ                        3                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Component:** `TreeTable` PrimeVue với `Column` cho `department_name`, `headcount`.  
Dữ liệu truyền vào `TreeTable` cần chuyển đổi `DepartmentNode[]` → `TreeNode[]` (PrimeVue TreeTable format).

**Hàm chuyển đổi `convertToTreeNodes(nodes: DepartmentNode[]): TreeNode[]`:**
```typescript
function convertToTreeNodes(nodes: DepartmentNode[]): TreeNode[] {
  return nodes.map(node => ({
    key: String(node.department_id),
    data: {
      name: node.department_name,
      total_headcount: node.total_headcount,
      direct_headcount: node.direct_headcount,
    },
    children: convertToTreeNodes(node.children),
  }))
}
```

### Service API `hrReportService.ts`

```typescript
// frontend/src/services/hrReportService.ts

const BASE = '/api/v1/reports/hr'

export const hrReportService = {
  getEmployeeList: (params: EmployeeListParams) =>
    api.get<EmployeeListResponse>(`${BASE}/employee-list`, { params }),

  getMovement: (params: MovementParams) =>
    api.get<MovementReportResponse>(`${BASE}/movement`, { params }),

  getTenure: (params: TenureParams) =>
    api.get<TenureReportResponse>(`${BASE}/tenure`, { params }),

  getOrgStructure: (params: OrgStructureParams) =>
    api.get<OrgStructureResponse>(`${BASE}/org-structure`, { params }),

  getExportUrl: (type: ExportType, params: Record<string, unknown>) => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString()
    return `${BASE}/export?type=${type}&${qs}`
  },
}
```

### Types `hr_report.types.ts`

```typescript
// frontend/src/types/hr_report.types.ts

export type EmployeeStatus = 'probation' | 'official' | 'long_leave' | 'resigned'
export type Gender = 'male' | 'female' | 'other'
export type DocumentKind = 'labor' | 'probation' | 'addendum'
export type GroupBy = 'month' | 'quarter' | 'year'
export type ExportType = 'employee-list' | 'movement' | 'tenure' | 'org-structure'

export interface EmployeeListItem {
  id: number
  employee_code: string | null
  full_name: string
  gender: Gender
  date_of_birth: string | null
  status: EmployeeStatus
  start_date: string
  resigned_date: string | null
  is_active: boolean
  department_id: number | null
  department_name: string | null
  job_title_name: string | null
  contract_category_name: string | null
  document_kind: DocumentKind | null
  tenure_years: number
}

export interface EmployeeListResponse {
  items: EmployeeListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MovementPeriodRow {
  period_label: string
  period_start: string
  period_end: string
  hired_count: number
  resigned_count: number
  transfer_count: number
  net_change: number
}

export interface MovementReportResponse {
  group_by: GroupBy
  start_date: string
  end_date: string
  rows: MovementPeriodRow[]
  total_hired: number
  total_resigned: number
  total_transfers: number
}

export interface TenureGroupDetail {
  id: number
  full_name: string
  department_name: string | null
  start_date: string
  tenure_years: number
}

export interface TenureGroup {
  group_key: string
  group_label: string
  headcount: number
  percentage: number
  avg_tenure_years: number
  employees: TenureGroupDetail[]
}

export interface TenureReportResponse {
  department_id: number | null
  department_name: string | null
  total_active: number
  avg_tenure_years: number
  groups: TenureGroup[]
}

export interface JobTitleHeadcount {
  job_title_id: number | null
  job_title_name: string | null
  job_level: number | null
  headcount: number
}

export interface DepartmentNode {
  department_id: number
  department_name: string
  parent_id: number | null
  total_headcount: number
  direct_headcount: number
  by_job_title: JobTitleHeadcount[]
  children: DepartmentNode[]
}

export interface OrgStructureResponse {
  total_headcount: number
  department_count: number
  tree: DepartmentNode[]
}
```

---

## Cấu trúc file

```
backend/
└── app/
    ├── schemas/
    │   └── hr_report.py                   ← Pydantic schemas (slice 1)
    ├── services/
    │   └── hr_report_service.py           ← Business logic (slice 1 + 2)
    ├── api/v1/endpoints/
    │   └── hr_reports.py                  ← FastAPI router (slice 2)
    └── api/v1/router.py                   ← Đăng ký router (slice 2)

frontend/
└── src/
    ├── types/
    │   └── hr_report.types.ts             ← TypeScript types (slice 3)
    ├── services/
    │   └── hrReportService.ts             ← API service (slice 3)
    └── views/reports/
        ├── HRReportView.vue               ← Tab container (slice 3)
        └── components/
            ├── EmployeeListTab.vue        ← Slice 3
            ├── MovementTab.vue            ← Slice 3
            ├── TenureTab.vue              ← Slice 4
            └── OrgStructureTab.vue        ← Slice 4

backend/tests/
└── test_hr_reports.py                     ← Tests (cuối mỗi slice)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend schemas + service logic (không Excel)

**Mục tiêu:** Hoàn thành `hr_report.py` schemas + 4 hàm service cốt lõi.

**Việc cần làm:**
1. Tạo `app/schemas/hr_report.py` — tất cả Pydantic schemas như đã thiết kế ở trên
2. Tạo `app/services/hr_report_service.py`:
   - `get_employee_list()` — query + phân trang
   - `get_movement_report()` — query 3 loại biến động + merge theo kỳ
   - `get_tenure_report()` — phân nhóm thâm niên
   - `get_org_structure()` — build cây phòng ban
3. Viết test `test_hr_reports.py`:
   - Seed: 3 departments (1 parent + 2 con), 10 employees (mix status, start_date, gender)
   - Test `get_employee_list` với filter `department_id`, `status`, `gender`
   - Test `get_movement_report` với `group_by=month`
   - Test `get_tenure_report` — verify 5 groups
   - Test `get_org_structure` — verify tree structure

**Định nghĩa "hoàn thành":** Tất cả tests pass, `mypy` không báo lỗi type.

---

### Slice 2 — Backend API endpoints + Excel export

**Mục tiêu:** 5 endpoints hoạt động, trả về JSON + xlsx.

**Việc cần làm:**
1. Tạo `app/api/v1/endpoints/hr_reports.py`:
   ```python
   router = APIRouter(prefix="/reports/hr", tags=["HR Reports"])

   @router.get("/employee-list", response_model=EmployeeListResponse)
   async def employee_list(...)

   @router.get("/movement", response_model=MovementReportResponse)
   async def movement_report(...)

   @router.get("/tenure", response_model=TenureReportResponse)
   async def tenure_report(...)

   @router.get("/org-structure", response_model=OrgStructureResponse)
   async def org_structure(...)

   @router.get("/export")
   async def export_report(type: ExportType, ...)
       # dispatch theo type → gọi hàm export tương ứng
       # return StreamingResponse(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
   ```
2. Thêm 4 hàm Excel vào `hr_report_service.py`:
   - `export_employee_list_excel()`
   - `export_movement_excel()`
   - `export_tenure_excel()`
   - `export_org_structure_excel()`
3. Đăng ký router trong `app/api/v1/router.py`
4. Kiểm tra permission `hr_report:view` qua `Depends(require_permission(...))`
5. Bổ sung test:
   - Test HTTP endpoints với `AsyncClient` (mock session)
   - Test export trả về bytes có header `Content-Disposition`

**Định nghĩa "hoàn thành":** `pytest tests/test_hr_reports.py` pass toàn bộ.

---

### Slice 3 — Frontend Tab 1 (Danh sách) + Tab 2 (Biến động)

**Mục tiêu:** 2 tabs đầu hoạt động hoàn chỉnh trên cả desktop và mobile.

**Việc cần làm:**
1. Tạo `frontend/src/types/hr_report.types.ts`
2. Tạo `frontend/src/services/hrReportService.ts`
3. Tạo `frontend/src/views/reports/HRReportView.vue` — TabView skeleton 4 tabs
4. Tạo `EmployeeListTab.vue`:
   - Filter panel với Collapse/Drawer (breakpoint `lg`)
   - DataTable server-side pagination
   - Button Export Excel
   - Verify `vue-tsc` không báo lỗi
5. Tạo `MovementTab.vue`:
   - Year/group_by selector
   - DataTable với cột net_change có màu
   - Button Export Excel
6. Cập nhật router `index.ts` thêm route `reports/hr`
7. Cập nhật `AppMenu.vue` nếu cần thêm menu item

**Quy trình verify (theo feedback_frontend_verify_before_code.md):**
- Grep `hrReportService` để confirm tên method trước khi dùng trong component
- Chạy `vue-tsc --noEmit` sau khi hoàn thành
- Kiểm tra trên màn hình 375px (mobile)

**Định nghĩa "hoàn thành":** Tab 1 + 2 load data, phân trang, filter, export Excel hoạt động; `vue-tsc` clean.

---

### Slice 4 — Frontend Tab 3 (Thâm niên) + Tab 4 (Cơ cấu tổ chức)

**Mục tiêu:** Hoàn thiện 2 tabs còn lại.

**Việc cần làm:**
1. Tạo `TenureTab.vue`:
   - 5 Summary cards (dùng PrimeVue `Card` hoặc custom stat cards)
   - DataTable với row expansion (expandedRows ref)
   - Row expansion content: DataTable con liệt kê nhân viên trong nhóm
   - Button Export Excel
2. Tạo `OrgStructureTab.vue`:
   - `TreeTable` PrimeVue với 3 columns: Tên phòng ban, Headcount trực tiếp, Tổng headcount
   - Hàm `convertToTreeNodes()` chuyển đổi từ API response
   - Button Export Excel
3. Đảm bảo `vue-tsc --noEmit` clean toàn bộ

**Định nghĩa "hoàn thành":** Tất cả 4 tabs hoạt động, export Excel hoạt động, `vue-tsc` clean, responsive mobile.

---

## Rủi ro và cách xử lý

| Rủi ro | Khả năng | Mức độ ảnh hưởng | Cách xử lý |
|---|---|---|---|
| **Nhân viên không có `employee_job_records` is_current** | Trung bình | Cao — dữ liệu thiếu phòng ban | `outerjoin` thay vì `join`; hiển thị `(Chưa phân công)` |
| **Nhân viên có nhiều contract active** | Thấp | Trung bình — join nhân đôi row | Lọc `parent_contract_id IS NULL` + chỉ lấy contract mới nhất (`ORDER BY effective_from DESC LIMIT 1`) |
| **Cây phòng ban quá sâu (circular reference)** | Rất thấp | Cao — vòng lặp vô hạn khi build tree | Giới hạn depth max=10; detect cycle khi build tree |
| **DATE_TRUNC không có trong SQLite (test env)** | Cao nếu dùng SQLite cho test | Trung bình | Dùng PostgreSQL cho test (docker-compose test db); hoặc tính trong Python thay vì SQL |
| **Export Excel file lớn (> 10,000 nhân viên)** | Thấp | Trung bình — timeout | Giới hạn export max 5,000 rows; hiển thị warning nếu vượt |
| **`TreeTable` PrimeVue cần format `TreeNode[]` đặc biệt** | Chắc chắn | Thấp | Viết helper `convertToTreeNodes()` rõ ràng, test riêng |
| **Filter thâm niên kết hợp với `department_id`** | Trung bình | Thấp | Xử lý trong Python sau khi fetch (không cần complex SQL) |
| **Performance khi load toàn bộ nhân viên cho tenure** | Trung bình | Thấp | `is_active=True` giảm dataset; index trên `employees.is_active` |

---

## Checklist trước khi đánh dấu hoàn thành

### Backend
- [ ] `pytest tests/test_hr_reports.py` — tất cả tests pass
- [ ] `mypy app/schemas/hr_report.py app/services/hr_report_service.py app/api/v1/endpoints/hr_reports.py` — không lỗi
- [ ] Router đăng ký trong `app/api/v1/router.py`
- [ ] Permission `hr_report:view` được seed vào DB
- [ ] Export Excel hoạt động với openpyxl (BytesIO response)

### Frontend
- [ ] `vue-tsc --noEmit` — không lỗi TypeScript
- [ ] Tab 1: filter + phân trang server-side hoạt động
- [ ] Tab 2: toggle month/quarter/year hoạt động
- [ ] Tab 3: row expansion nhóm thâm niên hoạt động
- [ ] Tab 4: TreeTable expand/collapse hoạt động
- [ ] Export Excel mỗi tab → tải file đúng
- [ ] Responsive: filter drawer hiện trên mobile (≤ 768px)
- [ ] Không có `<style scoped>` CSS custom — dùng PrimeVue utilities
