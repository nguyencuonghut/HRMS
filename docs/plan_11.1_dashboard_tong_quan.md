# Kế hoạch triển khai — 11.1. Dashboard tổng quan (People Analytics)

**Phạm vi:** Headcount · Biến động nhân sự · Turnover Rate · Cơ cấu nhân sự  
**Phụ thuộc:** Module 3 (nhân viên `employees`, `employee_job_records`) · Module 4 (hợp đồng) · Module 5 (nghỉ phép) · Module 8 (khen thưởng/kỷ luật) · Module 13 (tuyển dụng) · Module 14 (thử việc)  
**Căn cứ nghiệp vụ:** FEATURES.md §11.1  
**Lưu ý:** Module chỉ đọc — không tạo bảng mới, toàn bộ là aggregation queries trên dữ liệu hiện có

---

## Trạng thái hiện tại

> **✅ Hoàn thành toàn bộ** — Backend + Frontend đã triển khai đầy đủ.

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Dữ liệu nhân viên (Module 3) | ✅ Có dữ liệu | `employees` + `employee_job_records` |
| Dữ liệu phòng ban (Module 1) | ✅ Có dữ liệu | `departments` |
| Dữ liệu học vấn (Module 3.4) | ✅ Có dữ liệu | `employee_education_histories` + `education_levels` |
| `dashboard_service.py` | ✅ Hoàn thành | 4 hàm: `get_summary`, `get_headcount_by_dept`, `get_monthly_trend`, `get_structure` |
| `app/schemas/dashboard.py` | ✅ Hoàn thành | 7 Pydantic schemas |
| `app/api/v1/endpoints/dashboard.py` | ✅ Hoàn thành | 4 endpoints GET tại prefix `/reports/dashboard` |
| `dashboardService.ts` | ✅ Hoàn thành | 4 API calls + đầy đủ TypeScript interfaces |
| `views/reports/DashboardView.vue` | ✅ Hoàn thành | Custom SVG charts, 4 KPI cards, responsive grid |
| Route `/reports/dashboard` | ✅ Hoàn thành | Đã đăng ký trong `router/index.ts` |
| Menu item | ✅ Hoàn thành | "Dashboard nhân sự" trong submenu Báo cáo |
| Tests | ✅ Hoàn thành | `tests/test_dashboard.py` |

### Lưu ý triển khai

- **Custom SVG charts** thay vì Chart.js/PrimeVue Chart — nhẹ hơn, không phụ thuộc thư viện ngoài.
- **Stub cũ** `views/dashboard/DashboardView.vue` còn tồn tại nhưng không dùng (route `/dashboard` trỏ đến đây — placeholder).
- Dashboard chính tại route `/reports/dashboard` → `views/reports/DashboardView.vue`.

---

## Phạm vi

**Trong phạm vi:**
- **KPI cards**: Tổng nhân viên hiện tại, mới trong tháng, nghỉ việc trong tháng, tỷ lệ nghỉ việc (turnover rate)
- **Biểu đồ headcount theo phòng ban**: horizontal bar chart số nhân viên đang làm việc theo từng phòng ban
- **Biểu đồ biến động nhân sự 12 tháng**: line chart với 2 đường — tuyển mới (`start_date` trong tháng) vs nghỉ việc (`resigned_date` trong tháng)
- **Cơ cấu nhân sự theo 4 chiều**: giới tính (pie chart), độ tuổi (bar chart nhóm tuổi), trình độ học vấn (bar chart), thâm niên (bar chart nhóm năm)
- Lọc theo: phòng ban, năm
- Responsive: mobile-first (1 cột trên mobile, 2 cột trên tablet, 4 cột trên desktop)

**Ngoài phạm vi:**
- Dự báo nhu cầu nhân sự (ML/AI)
- Real-time streaming / WebSocket
- Benchmark so sánh với ngành (external data)

---

## Các chỉ số chính (KPI Definitions)

### Headcount hiện tại

```sql
-- Tổng nhân viên đang làm việc (is_active=TRUE, status != 'resigned')
SELECT COUNT(DISTINCT e.id) AS total_headcount
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE e.is_active = TRUE
  AND e.status != 'resigned'
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
```

### Headcount theo phòng ban

```sql
SELECT
    d.id AS department_id,
    d.name AS department_name,
    COUNT(e.id) AS headcount
FROM departments d
LEFT JOIN employee_job_records ejr ON ejr.department_id = d.id AND ejr.is_current = TRUE
LEFT JOIN employees e ON e.id = ejr.employee_id
    AND e.is_active = TRUE
    AND e.status != 'resigned'
WHERE d.is_active = TRUE
GROUP BY d.id, d.name
ORDER BY headcount DESC
```

### Nhân viên mới trong tháng

```sql
-- Nhân viên có start_date trong tháng/năm được chọn
SELECT COUNT(*) AS new_hires
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE EXTRACT(YEAR FROM e.start_date) = :year
  AND EXTRACT(MONTH FROM e.start_date) = :month
  AND e.is_active = TRUE
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
```

### Nhân viên nghỉ việc trong tháng

```sql
SELECT COUNT(*) AS resigned_count
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE e.status = 'resigned'
  AND e.resigned_date IS NOT NULL
  AND EXTRACT(YEAR FROM e.resigned_date) = :year
  AND EXTRACT(MONTH FROM e.resigned_date) = :month
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
```

### Turnover Rate

```
Turnover Rate (%) = (Số nhân viên nghỉ trong kỳ / Headcount đầu kỳ) × 100%
```

```sql
-- Headcount đầu kỳ (đầu tháng :month/:year)
SELECT COUNT(*) AS headcount_start
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE e.start_date < DATE_TRUNC('month', MAKE_DATE(:year, :month, 1))
  AND (e.resigned_date IS NULL
       OR e.resigned_date >= DATE_TRUNC('month', MAKE_DATE(:year, :month, 1)))
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
```

### Biến động 12 tháng (line chart)

```sql
-- Tuyển mới theo tháng
SELECT
    EXTRACT(MONTH FROM e.start_date)::int AS month,
    COUNT(*) AS new_hires
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE EXTRACT(YEAR FROM e.start_date) = :year
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
GROUP BY month
ORDER BY month

-- Nghỉ việc theo tháng
SELECT
    EXTRACT(MONTH FROM e.resigned_date)::int AS month,
    COUNT(*) AS resigned_count
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE e.status = 'resigned'
  AND e.resigned_date IS NOT NULL
  AND EXTRACT(YEAR FROM e.resigned_date) = :year
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
GROUP BY month
ORDER BY month
```

### Cơ cấu giới tính

```sql
SELECT
    e.gender,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
WHERE e.is_active = TRUE
  AND e.status != 'resigned'
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
GROUP BY e.gender
```

### Cơ cấu độ tuổi (nhóm tuổi)

```sql
SELECT
    CASE
        WHEN age_years < 25 THEN 'Dưới 25'
        WHEN age_years BETWEEN 25 AND 34 THEN '25-34'
        WHEN age_years BETWEEN 35 AND 44 THEN '35-44'
        WHEN age_years BETWEEN 45 AND 54 THEN '45-54'
        ELSE '55 trở lên'
    END AS age_group,
    COUNT(*) AS count
FROM (
    SELECT
        e.id,
        DATE_PART('year', AGE(CURRENT_DATE, e.date_of_birth))::int AS age_years
    FROM employees e
    JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
    WHERE e.is_active = TRUE
      AND e.status != 'resigned'
      AND (:department_id IS NULL OR ejr.department_id = :department_id)
) sub
GROUP BY age_group
ORDER BY MIN(age_years)
```

### Cơ cấu trình độ học vấn

```sql
-- Lấy trình độ cao nhất (is_main_education = TRUE) của mỗi nhân viên
SELECT
    el.name AS education_level,
    COUNT(DISTINCT e.id) AS count
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
LEFT JOIN employee_education_histories eeh
    ON eeh.employee_id = e.id AND eeh.is_main_education = TRUE
LEFT JOIN education_levels el ON el.id = eeh.education_level_id
WHERE e.is_active = TRUE
  AND e.status != 'resigned'
  AND (:department_id IS NULL OR ejr.department_id = :department_id)
GROUP BY el.name
ORDER BY count DESC
```

### Cơ cấu thâm niên (nhóm năm)

```sql
SELECT
    CASE
        WHEN tenure_years < 1 THEN 'Dưới 1 năm'
        WHEN tenure_years BETWEEN 1 AND 2 THEN '1-2 năm'
        WHEN tenure_years BETWEEN 3 AND 5 THEN '3-5 năm'
        WHEN tenure_years BETWEEN 6 AND 10 THEN '6-10 năm'
        ELSE 'Trên 10 năm'
    END AS tenure_group,
    COUNT(*) AS count
FROM (
    SELECT
        e.id,
        DATE_PART('year', AGE(CURRENT_DATE, e.start_date))::int AS tenure_years
    FROM employees e
    JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
    WHERE e.is_active = TRUE
      AND e.status != 'resigned'
      AND (:department_id IS NULL OR ejr.department_id = :department_id)
) sub
GROUP BY tenure_group
ORDER BY MIN(tenure_years)
```

---

## API Design

### KPI Summary Cards

```
GET /api/v1/reports/dashboard/summary?year=&month=&department_id=
    → {
        total_headcount: int,           -- Tổng nhân viên hiện tại
        new_hires_this_month: int,      -- Mới trong tháng
        resigned_this_month: int,       -- Nghỉ việc trong tháng
        turnover_rate: float,           -- % nghỉ việc / headcount đầu tháng
        headcount_start_of_month: int,  -- Headcount đầu tháng (mẫu số turnover)
        as_of_date: date                -- Ngày tính (today)
      }
```

### Headcount theo phòng ban

```
GET /api/v1/reports/dashboard/headcount-by-dept?year=&month=&department_id=
    → List[{
        department_id: int,
        department_name: str,
        headcount: int
      }]
```

### Biến động 12 tháng

```
GET /api/v1/reports/dashboard/monthly-trend?year=&department_id=
    → {
        year: int,
        monthly: List[{
            month: int,                 -- 1-12
            new_hires: int,
            resigned_count: int,
            net_change: int             -- new_hires - resigned_count
        }]
      }
```

### Cơ cấu nhân sự (4 chiều)

```
GET /api/v1/reports/dashboard/structure?year=&department_id=
    → {
        gender: List[{ label: str, count: int, percentage: float }],
        age_group: List[{ label: str, count: int }],
        education_level: List[{ label: str, count: int }],
        tenure_group: List[{ label: str, count: int }]
      }
```

### Permissions

| Action | Permission |
|---|---|
| Xem dashboard | `employees:read` |

---

## Schemas (Pydantic)

```python
# app/schemas/dashboard.py

class DashboardSummary(BaseModel):
    total_headcount: int
    new_hires_this_month: int
    resigned_this_month: int
    headcount_start_of_month: int
    turnover_rate: float              # %, làm tròn 1 chữ số thập phân
    as_of_date: date

class HeadcountByDeptItem(BaseModel):
    department_id: int
    department_name: str
    headcount: int

class MonthlyTrendItem(BaseModel):
    month: int                        # 1-12
    new_hires: int
    resigned_count: int
    net_change: int                   # new_hires - resigned_count

class MonthlyTrendReport(BaseModel):
    year: int
    department_id: Optional[int]
    monthly: List[MonthlyTrendItem]   # luôn đủ 12 phần tử (tháng chưa có data = 0)

class GenderItem(BaseModel):
    label: str                        # "Nam" | "Nữ" | "Khác"
    count: int
    percentage: float                 # %

class StructureGroupItem(BaseModel):
    label: str
    count: int

class StructureReport(BaseModel):
    gender: List[GenderItem]
    age_group: List[StructureGroupItem]
    education_level: List[StructureGroupItem]
    tenure_group: List[StructureGroupItem]
```

---

## Service Logic (`dashboard_service.py`)

**`get_summary(session, year, month, department_id?) → DashboardSummary`**
- Chạy 3 queries song song với `asyncio.gather`: `total_headcount`, `new_hires`, `resigned_count` + `headcount_start`
- `turnover_rate = resigned / headcount_start * 100` — trả `0.0` nếu `headcount_start = 0`
- `year` + `month` mặc định = tháng hiện tại nếu không truyền

**`get_headcount_by_dept(session, department_id?) → List[HeadcountByDeptItem]`**
- Luôn trả tất cả phòng ban `is_active=True`, kể cả phòng ban có `headcount = 0`
- Sort theo `headcount DESC`

**`get_monthly_trend(session, year, department_id?) → MonthlyTrendReport`**
- Chạy 2 queries song song: tuyển mới và nghỉ việc theo tháng
- Merge kết quả: đảm bảo đủ 12 tháng — tháng chưa có data trả `0`
- `net_change = new_hires - resigned_count` (có thể âm khi nghỉ nhiều hơn tuyển)

**`get_structure(session, department_id?) → StructureReport`**
- Chạy 4 queries song song: gender, age_group, education_level, tenure_group
- `gender` label mapping: `'male'` → `'Nam'`, `'female'` → `'Nữ'`, `'other'` → `'Khác'`
- `education_level`: nhân viên không có bản ghi `is_main_education=True` → gom vào `'Chưa cập nhật'`
- Nhóm tuổi và thâm niên: sort theo thứ tự tăng dần (không theo count)

---

## Thiết kế Frontend

> **Kiến trúc:** `DashboardView.vue` là standalone view tại route `/reports/dashboard`, không phải tab trong hub.

### `DashboardView.vue` (route `/reports/dashboard`)

**Filter toolbar (sticky top):**
- Select Năm (default: năm hiện tại)
- Select Tháng (default: tháng hiện tại) — dùng cho KPI cards
- Select Phòng ban (optional, default: Tất cả)
- Button "Xem báo cáo"

**Section 1: KPI Cards (responsive grid — 4 cards)**

| Card | Giá trị | Icon |
|---|---|---|
| Tổng nhân viên | `total_headcount` | `pi-users` |
| Mới trong tháng | `new_hires_this_month` | `pi-user-plus` |
| Nghỉ việc trong tháng | `resigned_this_month` | `pi-user-minus` |
| Turnover Rate | `turnover_rate`% | `pi-chart-line` |

Layout: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`  
Dùng PrimeVue `Card` component, không viết CSS scoped/inline.

**Section 2: Headcount theo phòng ban (horizontal bar chart)**
- PrimeVue `Chart` (Chart.js, type `bar`, `indexAxis: 'y'`)
- Trục Y: tên phòng ban; trục X: số nhân viên
- Màu: PrimeVue token `--p-primary-500`
- Hiển thị label số lượng trên bar

**Section 3: Biến động 12 tháng (line chart)**
- PrimeVue `Chart` (Chart.js, type `line`)
- Dataset 1: Tuyển mới — màu xanh lá `--p-green-500`
- Dataset 2: Nghỉ việc — màu đỏ `--p-red-500`
- Trục X: tháng 1→12; trục Y: số nhân viên
- Legend hiển thị ở dưới chart

**Section 4: Cơ cấu nhân sự (grid 2×2 → mobile 1 cột)**

| Vị trí | Chart |
|---|---|
| Trên trái | Giới tính — pie chart |
| Trên phải | Độ tuổi — horizontal bar chart |
| Dưới trái | Trình độ học vấn — horizontal bar chart |
| Dưới phải | Thâm niên — horizontal bar chart |

Layout: `grid grid-cols-1 md:grid-cols-2 gap-4`

**Loading state:** Skeleton placeholder cho mỗi section trong khi fetch.  
**Empty state:** Hiển thị `"Không có dữ liệu"` khi list rỗng.

---

## Cấu trúc file

```
backend/
  app/services/dashboard_service.py              (NEW)
  app/schemas/dashboard.py                       (NEW)
  app/api/v1/endpoints/dashboard.py              (NEW)
  tests/test_dashboard.py                        (NEW)

frontend/
  src/services/dashboardService.ts               (NEW)
  src/views/reports/DashboardView.vue            (NEW)
  src/router/index.ts                            (EDIT: thêm route /reports/dashboard)
  src/components/layout/AppMenu.vue             (EDIT: thêm menu item 'Dashboard nhân sự')
```

### Route cần thêm (`router/index.ts`)

```typescript
{
  path: 'reports/dashboard',
  name: 'dashboard-overview',
  component: () => import('@/views/reports/DashboardView.vue'),
  meta: { title: 'Dashboard tổng quan' },
}
```

### Menu item cần thêm (`AppMenu.vue` — submenu Báo cáo)

```typescript
{ to: '/reports/dashboard', label: 'Dashboard nhân sự', icon: 'pi-chart-pie' }
```

---

## Kế hoạch theo Slice

### ✅ Slice 1 — Backend: KPI Summary (Hoàn thành)
- `get_summary()` với 4 queries song song
- Endpoint `GET /api/v1/reports/dashboard/summary`
- Schema `DashboardSummary`
- Test: `test_dashboard_summary_no_filter`, `test_dashboard_summary_by_dept`

### ✅ Slice 2 — Backend: Headcount by Dept + Biến động 12 tháng (Hoàn thành)
- `get_headcount_by_dept()`, `get_monthly_trend()`
- Endpoints: `/headcount-by-dept`, `/monthly-trend`
- Schemas: `HeadcountByDeptItem`, `MonthlyTrendReport`
- Đảm bảo đủ 12 tháng kể cả tháng không có data

### ✅ Slice 3 — Backend: Cơ cấu nhân sự + Tests (Hoàn thành)
- `get_structure()` với 4 sub-queries song song
- Endpoint `/structure`
- Schema `StructureReport`
- Nhân viên không có `is_main_education=True` được gom vào `'Chưa cập nhật'`

### ✅ Slice 4 — Frontend full view (Hoàn thành)
- `dashboardService.ts`: 4 API calls + TypeScript interfaces đầy đủ
- `views/reports/DashboardView.vue`: filter toolbar + 4 sections
- KPI cards, custom SVG bar chart, SVG line chart, grid cơ cấu 2×2
- Router `/reports/dashboard` + menu item trong submenu Báo cáo

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Query aggregation chậm khi data lớn (>5.000 nhân viên) | Trung bình | Thêm index `(is_active, status)` trên `employees`; index `(employee_id, is_current)` trên `employee_job_records` đã có |
| Nhân viên không có `employee_job_records.is_current=TRUE` | Thấp | LEFT JOIN để không bỏ sót; ghi log warning khi phát hiện orphan employee |
| `education_level` null khi nhân viên chưa nhập học vấn | Trung bình | Gom vào nhóm `'Chưa cập nhật'`; hiển thị rõ trong chart legend |
| Turnover rate = `0 / 0` khi headcount đầu tháng = 0 | Thấp | Trả `0.0`, không crash; frontend hiển thị `"N/A"` thay vì `0%` |
| `resigned_date` NULL trên nhân viên `status='resigned'` | Thấp | Chỉ tính resigned khi `resigned_date IS NOT NULL`; bổ sung data validation ở service nhân viên |
| Phòng ban `is_active=FALSE` vẫn có nhân viên (sau cơ cấu lại) | Thấp | `get_headcount_by_dept` chỉ lấy dept `is_active=TRUE`; nhân viên orphan phòng ban cũ không bị đếm nhầm vì join qua `ejr.is_current=TRUE` |
| Chart.js render chậm khi nhiều phòng ban (>20) | Thấp | Headcount chart: hiển thị top 15 phòng ban, còn lại gom vào "Khác"; có thể scroll ngang |
