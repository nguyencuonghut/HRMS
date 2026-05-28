# Kế hoạch triển khai — 11.3. Báo cáo Nghỉ phép (People Analytics)

**Phạm vi:** Tổng hợp theo nhân viên/phòng ban · Tồn phép cuối kỳ · Thống kê theo loại phép · Xu hướng nghỉ phép  
**Phụ thuộc:** Plan 5.x (leave_records, leave_entitlements đã hoàn thành ✅)  
**Căn cứ:** FEATURES.md §11.3  
**Mở rộng trên nền:** Plan 5.4 — không duplicate, bổ sung analytics nâng cao

---

## Trạng thái hiện tại

### Đã có từ Plan 5.4 (KHÔNG làm lại)

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `GET /leave-reports/employee-summary` | ✅ Hoàn thành | Báo cáo A — chi tiết NV theo entitlement |
| `GET /leave-reports/department-summary` | ✅ Hoàn thành | Báo cáo B — tổng hợp theo phòng ban + tháng |
| `GET /leave-reports/year-end` | ✅ Hoàn thành | Báo cáo C — tồn phép cuối năm (carryover_allowed) |
| `GET /leave-reports/export` | ✅ Hoàn thành | Export xlsx 3 loại A/B/C |
| `leave_report_service.py` | ✅ Hoàn thành | 3 hàm get + 3 hàm export xlsx |
| `app/schemas/leave_report.py` | ✅ Hoàn thành | EmployeeSummaryReport, DepartmentSummaryReport, YearEndReport |
| `LeaveReportView.vue` | ✅ Hoàn thành | 3 tab + filter + DataTable + xuất Excel |
| Route `/leave-reports` | ✅ Hoàn thành | Đã đăng ký trong router.ts + AppMenu |

### Chưa có — mục tiêu của Plan 11.3

| Thành phần | Trạng thái | Mô tả |
|---|---|---|
| Analytics summary (KPI cards) | ❌ Chưa có | Tổng ngày nghỉ YTD, tỷ lệ sử dụng phép, NV chưa nghỉ |
| Thống kê theo loại phép (pie/bar) | ❌ Chưa có | Phân bổ ngày nghỉ theo từng loại phép |
| Monthly heatmap | ❌ Chưa có | Ma trận 12 tháng × phòng ban: tổng ngày nghỉ |
| Top 10 nhân viên nghỉ nhiều | ❌ Chưa có | Ranking với tổng ngày, phòng ban, % so với allocated |
| Cảnh báo sắp hết hạn carryover | ❌ Chưa có | Filter tồn phép hết hạn trong N ngày tới |
| So sánh phòng ban | ❌ Chưa có | Bar chart avg_days_per_employee theo phòng ban |
| Export analytics (xlsx nhiều sheet) | ❌ Chưa có | 1 file xlsx với 4 sheet: KPI, ByType, Heatmap, Top10 |
| `leave_analytics_service.py` | ❌ Chưa có | Service mới, tách với leave_report_service.py |
| `LeaveAnalyticsView.vue` | ❌ Chưa có | View riêng với charts + heatmap |

---

## Phạm vi Plan 11.3

### Không làm

- Không sửa `leave_report_service.py` — giữ nguyên các hàm Plan 5.4
- Không sửa `LeaveReportView.vue` — giữ nguyên 3 tab hiện tại
- Không tạo bảng DB mới — tất cả đọc từ dữ liệu đã có

### Làm mới

1. **Dashboard analytics tổng hợp** — 4 KPI cards + trend 12 tháng
2. **Thống kê theo loại phép** — tổng ngày, số lần, tỷ lệ phần trăm
3. **Monthly heatmap** — ma trận tháng × phòng ban
4. **Top 10 nhân viên nghỉ nhiều nhất**
5. **Cảnh báo carryover sắp hết hạn** (trong 30/60/90 ngày)
6. **So sánh tỷ lệ nghỉ giữa các phòng ban**
7. **Export analytics xlsx** — 1 file nhiều sheet
8. **Route `/reports/leave-analytics`** — view mới tách với `/leave-reports`

---

## Các chỉ số chính (KPIs) + SQL Logic

### KPI 1 — Tổng ngày nghỉ YTD (Year-to-date)

```sql
SELECT SUM(r.total_days)
FROM leave_records r
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
  [AND EXTRACT(month FROM r.start_date) <= :current_month]
  [AND ejr.department_id = :department_id]
```

### KPI 2 — Tỷ lệ sử dụng phép bình quân

```
avg_usage_rate = SUM(used_days) / SUM(allocated_days + carryover_days) * 100
```

Nguồn: `leave_entitlements` GROUP BY tất cả, filter year.

### KPI 3 — Số nhân viên chưa nghỉ phép năm nào

```sql
SELECT COUNT(DISTINCT ent.employee_id)
FROM leave_entitlements ent
WHERE ent.year = :year
  AND ent.used_days = 0
  AND ent.leave_type_id IN (
      SELECT id FROM leave_types WHERE carryover_allowed = true
  )
```

### KPI 4 — Số ngày tồn phép sắp hết hạn (trong 30 ngày tới)

```sql
SELECT SUM(ent.allocated_days + ent.carryover_days - ent.used_days)
FROM leave_entitlements ent
WHERE ent.carryover_expires BETWEEN CURRENT_DATE AND CURRENT_DATE + 30
  AND ent.year = :year
  AND (ent.allocated_days + ent.carryover_days - ent.used_days) > 0
```

### Xu hướng 12 tháng (trend line)

```sql
SELECT
    EXTRACT(month FROM r.start_date)::int AS month,
    SUM(r.total_days)                     AS total_days,
    COUNT(r.id)                           AS total_records,
    COUNT(DISTINCT r.employee_id)         AS employee_count
FROM leave_records r
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
  [AND ejr.department_id = :department_id]
GROUP BY 1
ORDER BY 1
```

Trả về mảng 12 phần tử (tháng không có dữ liệu → 0).

### Thống kê theo loại phép

```sql
SELECT
    lt.id,
    lt.name,
    lt.color_tag,
    COUNT(r.id)             AS record_count,
    SUM(r.total_days)       AS total_days,
    COUNT(DISTINCT r.employee_id) AS unique_employees
FROM leave_records r
JOIN leave_types lt ON lt.id = r.leave_type_id
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
  [AND ejr.department_id = :department_id]
GROUP BY lt.id, lt.name, lt.color_tag
ORDER BY total_days DESC
```

### Monthly heatmap (12 tháng × N phòng ban)

```sql
SELECT
    d.id          AS dept_id,
    d.name        AS dept_name,
    EXTRACT(month FROM r.start_date)::int AS month,
    SUM(r.total_days) AS total_days
FROM leave_records r
JOIN employees e ON e.id = r.employee_id
LEFT JOIN employee_job_records ejr
    ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
GROUP BY d.id, d.name, month
ORDER BY d.name NULLS LAST, month
```

Sau khi query, pivot thành dict `{dept_id: {1: days, 2: days, ..., 12: days}}`.

### Top 10 nhân viên nghỉ nhiều nhất

```sql
SELECT
    e.id,
    e.full_name,
    d.name   AS dept_name,
    SUM(r.total_days)       AS total_days_taken,
    COUNT(r.id)             AS record_count,
    MAX(ent.allocated_days + ent.carryover_days) AS total_entitled
FROM leave_records r
JOIN employees e ON e.id = r.employee_id
LEFT JOIN employee_job_records ejr
    ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
LEFT JOIN leave_entitlements ent
    ON ent.employee_id = e.id AND ent.year = :year
WHERE r.status = 'active'
  AND EXTRACT(year FROM r.start_date) = :year
  [AND ejr.department_id = :department_id]
GROUP BY e.id, e.full_name, d.name
ORDER BY total_days_taken DESC
LIMIT 10
```

### Carryover sắp hết hạn

```sql
SELECT
    e.id, e.full_name,
    d.name AS dept_name,
    lt.name AS leave_type_name,
    ent.carryover_days,
    ent.carryover_expires,
    (ent.allocated_days + ent.carryover_days - ent.used_days) AS remaining_days,
    (ent.carryover_expires - CURRENT_DATE)::int AS days_until_expire
FROM leave_entitlements ent
JOIN employees e ON e.id = ent.employee_id
JOIN leave_types lt ON lt.id = ent.leave_type_id
LEFT JOIN employee_job_records ejr
    ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
WHERE ent.year = :year
  AND ent.carryover_expires IS NOT NULL
  AND ent.carryover_expires > CURRENT_DATE
  AND ent.carryover_expires <= CURRENT_DATE + :expire_days
  AND (ent.allocated_days + ent.carryover_days - ent.used_days) > 0
  [AND ejr.department_id = :department_id]
ORDER BY ent.carryover_expires ASC
```

---

## API Design — Endpoints mới (prefix `/api/v1/reports/leaves`)

> Đây là prefix **mới**, tách biệt với `/api/v1/leave-reports` của Plan 5.4.

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/reports/leaves/analytics-summary` | KPI cards + trend 12 tháng |
| GET | `/api/v1/reports/leaves/by-type` | Thống kê theo loại phép |
| GET | `/api/v1/reports/leaves/monthly-heatmap` | Ma trận 12 tháng × phòng ban |
| GET | `/api/v1/reports/leaves/top-employees` | Top 10 NV nghỉ nhiều nhất |
| GET | `/api/v1/reports/leaves/expiring-balance` | Carryover sắp hết hạn |
| GET | `/api/v1/reports/leaves/department-comparison` | So sánh avg ngày nghỉ theo phòng ban |
| GET | `/api/v1/reports/leaves/export-analytics` | Export xlsx nhiều sheet |

### Query parameters

| Param | Type | Dùng ở | Ghi chú |
|---|---|---|---|
| `year` | int | Tất cả | Bắt buộc, 2020–2100 |
| `department_id` | int? | Tất cả | Lọc theo phòng ban |
| `leave_type_id` | int? | analytics-summary, by-type, top-employees | Lọc theo loại phép |
| `expire_days` | int default 30 | expiring-balance | 30/60/90 ngày tới |
| `limit` | int default 10 | top-employees | Tối đa 50 |

**RBAC:** Tất cả cần permission `leaves:read`. Không có thao tác ghi.

---

## Schemas Pydantic — `app/schemas/leave_analytics.py` (file mới)

```python
from __future__ import annotations
from datetime import date
from pydantic import BaseModel


# ── KPI + Trend ────────────────────────────────────────────────────────────────

class MonthlyTrendPoint(BaseModel):
    month: int                   # 1–12
    total_days: float
    total_records: int
    employee_count: int


class LeaveAnalyticsSummary(BaseModel):
    year: int
    department_id: int | None

    # KPI cards
    total_days_ytd: float        # Tổng ngày nghỉ YTD
    avg_usage_rate: float        # % sử dụng phép bình quân (0–100)
    employees_not_taken: int     # Số NV chưa dùng phép năm nào
    days_expiring_30d: float     # Ngày tồn sắp hết hạn trong 30 ngày

    # Trend
    monthly_trend: list[MonthlyTrendPoint]  # Luôn 12 phần tử


# ── Thống kê theo loại phép ───────────────────────────────────────────────────

class LeaveTypeStatRow(BaseModel):
    leave_type_id: int
    leave_type_name: str
    color_tag: str | None
    record_count: int
    total_days: float
    unique_employees: int
    percentage: float            # % tổng ngày (tính trong tập kết quả)


class LeaveByTypeReport(BaseModel):
    year: int
    department_id: int | None
    items: list[LeaveTypeStatRow]
    grand_total_days: float


# ── Monthly Heatmap ───────────────────────────────────────────────────────────

class HeatmapDeptRow(BaseModel):
    dept_id: int | None
    dept_name: str | None
    monthly_days: dict[int, float]   # key: 1–12, value: tổng ngày nghỉ
    annual_total: float


class MonthlyHeatmapReport(BaseModel):
    year: int
    departments: list[HeatmapDeptRow]
    # Thống kê tổng hàng ngang (tổng toàn công ty theo tháng)
    company_monthly: dict[int, float]  # key: 1–12


# ── Top Employees ─────────────────────────────────────────────────────────────

class TopEmployeeRow(BaseModel):
    rank: int
    employee_id: int
    employee_code: str
    employee_name: str
    dept_name: str | None
    total_days_taken: float
    record_count: int
    total_entitled: float        # allocated + carryover
    usage_rate: float            # total_days_taken / total_entitled * 100


class TopEmployeesReport(BaseModel):
    year: int
    department_id: int | None
    items: list[TopEmployeeRow]


# ── Expiring Balance ──────────────────────────────────────────────────────────

class ExpiringBalanceRow(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    dept_name: str | None
    leave_type_name: str
    carryover_days: float
    remaining_days: float
    carryover_expires: date
    days_until_expire: int       # số ngày còn lại trước khi hết hạn


class ExpiringBalanceReport(BaseModel):
    expire_days: int             # ngưỡng filter (30/60/90)
    year: int
    department_id: int | None
    items: list[ExpiringBalanceRow]
    total_expiring_days: float   # tổng ngày sắp bị mất


# ── Department Comparison ─────────────────────────────────────────────────────

class DeptComparisonRow(BaseModel):
    dept_id: int | None
    dept_name: str | None
    employee_count: int
    total_days_taken: float
    avg_days_per_employee: float
    allocated_total: float
    usage_rate: float            # total_days_taken / allocated_total * 100


class DeptComparisonReport(BaseModel):
    year: int
    items: list[DeptComparisonRow]
```

---

## Service Logic — `app/services/leave_analytics_service.py` (file mới)

File này **không import** từ `leave_report_service.py`. Tách hoàn toàn.

```python
# Cấu trúc hàm chính

async def get_analytics_summary(
    session: AsyncSession,
    *,
    year: int,
    department_id: int | None = None,
    leave_type_id: int | None = None,
) -> LeaveAnalyticsSummary:
    """
    4 KPI + trend 12 tháng.
    - KPI 1: SUM(leave_records.total_days) WHERE year=:year AND status='active'
    - KPI 2: SUM(used_days) / SUM(allocated+carryover) từ leave_entitlements
    - KPI 3: COUNT(DISTINCT employee_id) WHERE used_days=0
    - KPI 4: SUM(remaining) WHERE carryover_expires BETWEEN now AND now+30
    - Trend: GROUP BY month → fill 12 slots (0 nếu không có dữ liệu)
    """

async def get_by_type(
    session: AsyncSession,
    *,
    year: int,
    department_id: int | None = None,
) -> LeaveByTypeReport:
    """
    GROUP BY leave_type_id + tính percentage = row.total_days / grand_total * 100
    """

async def get_monthly_heatmap(
    session: AsyncSession,
    *,
    year: int,
) -> MonthlyHeatmapReport:
    """
    Query raw (dept, month, days) → pivot thành dict[dept_id][month] = days
    Tính company_monthly = SUM theo tháng toàn công ty
    """

async def get_top_employees(
    session: AsyncSession,
    *,
    year: int,
    department_id: int | None = None,
    leave_type_id: int | None = None,
    limit: int = 10,
) -> TopEmployeesReport:
    """
    ORDER BY total_days_taken DESC LIMIT :limit
    Tính rank bằng enumerate (tránh window function phức tạp)
    usage_rate = total_days_taken / total_entitled * 100 nếu total_entitled > 0
    """

async def get_expiring_balance(
    session: AsyncSession,
    *,
    year: int,
    department_id: int | None = None,
    expire_days: int = 30,
) -> ExpiringBalanceReport:
    """
    Filter carryover_expires BETWEEN today AND today + expire_days
    AND remaining > 0
    Tính total_expiring_days = SUM(remaining)
    """

async def get_department_comparison(
    session: AsyncSession,
    *,
    year: int,
) -> DeptComparisonReport:
    """
    JOIN leave_entitlements để lấy allocated_total
    usage_rate = total_days_taken / allocated_total * 100
    """

def build_analytics_xlsx(
    summary: LeaveAnalyticsSummary,
    by_type: LeaveByTypeReport,
    heatmap: MonthlyHeatmapReport,
    top: TopEmployeesReport,
) -> io.BytesIO:
    """
    4 sheets trong 1 file:
    - Sheet 1 "Tổng quan": KPI cards + trend table
    - Sheet 2 "Theo loại phép": bảng LeaveTypeStatRow
    - Sheet 3 "Heatmap tháng": ma trận dept × tháng
    - Sheet 4 "Top nhân viên": TopEmployeeRow
    Tái dùng helper _build_xlsx_sheet() nội bộ (không dùng _build_xlsx từ leave_report_service)
    """
```

### Lưu ý kỹ thuật quan trọng

- Tất cả query dùng `AsyncSession` + `await session.execute()`
- `func.extract("year"/"month", column)` cho date filtering (nhất quán với leave_report_service)
- `func.coalesce(value, 0)` cho các SUM có thể NULL
- `EmployeeJobRecord.is_current == True` cho JOIN phòng ban hiện tại
- Pivot heatmap thực hiện trong Python (không dùng SQL CROSSTAB — tránh dependency PostgreSQL-specific)
- `employee_code_service.batch_build_employee_display_codes()` cho top_employees để lấy mã NV đúng format

---

## Frontend Design

### Route mới

```
/reports/leave-analytics   →   LeaveAnalyticsView.vue
```

Route này tách với `/leave-reports` (Plan 5.4) — đặt trong nhóm "Báo cáo & Analytics" trên AppMenu.

### `LeaveAnalyticsView.vue` — Layout tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Toolbar] Năm: [2026 ▼]  Phòng ban: [Tất cả ▼]  [Tải lại]  [Xuất Excel]
├────────────────┬────────────────┬────────────────┬──────────────────┤
│ KPI: Tổng ngày │ KPI: Tỷ lệ dùng│ KPI: Chưa nghỉ │ KPI: Sắp hết hạn │
│    1,234 ngày  │     68.5%      │    12 NV       │     45 ngày      │
├────────────────┴────────────────┴────────────────┴──────────────────┤
│  [Section 2] Bar chart: Ngày nghỉ theo loại phép (horizontal bar)   │
│  ─────────────────────────────────────────────────────────────────  │
│  [Section 3] Heatmap: 12 tháng × Phòng ban (DataTable + cell color) │
│  ─────────────────────────────────────────────────────────────────  │
│  [Section 4] Top 10 NV nghỉ nhiều | [Section 5] So sánh phòng ban  │
│  ─────────────────────────────────────────────────────────────────  │
│  [Section 6] Cảnh báo carryover sắp hết hạn (DataTable highlight)  │
└─────────────────────────────────────────────────────────────────────┘
```

### Section 1 — KPI Cards

4 cards responsive grid (`grid grid-cols-2 lg:grid-cols-4 gap-4`):

| Card | Icon | Giá trị | Màu border |
|---|---|---|---|
| Tổng ngày nghỉ YTD | calendar | `total_days_ytd` | xanh dương |
| Tỷ lệ sử dụng phép | chart-pie | `avg_usage_rate`% | xanh lá |
| Nhân viên chưa nghỉ | user-x | `employees_not_taken` NV | cam |
| Ngày sắp hết hạn | alert-triangle | `days_expiring_30d` ngày | đỏ |

Dùng PrimeVue `Card` component. Không dùng inline style — dùng class utility.

### Section 2 — Bar Chart theo loại phép

Dùng PrimeVue `Chart` (type: `bar`, horizontal) với dataset từ `LeaveByTypeReport`:

```typescript
{
  labels: items.map(i => i.leave_type_name),
  datasets: [{
    label: 'Tổng ngày nghỉ',
    data: items.map(i => i.total_days),
    backgroundColor: items.map(i => i.color_tag ?? '#94a3b8'),
  }]
}
```

Tooltip hiển thị: `{leave_type_name}: {total_days} ngày ({percentage}%) — {record_count} lần`.

### Section 3 — Heatmap 12 tháng × Phòng ban

Dùng PrimeVue `DataTable` với 13 cột: `Phòng ban` + `T1`–`T12`.

Mỗi ô số ngày được tô màu theo giá trị (cell coloring bằng class động — không dùng style inline):

```
0 ngày     → class "heat-0"  (nền trắng)
1–5 ngày   → class "heat-1"  (xanh nhạt nhất)
6–10 ngày  → class "heat-2"
11–20 ngày → class "heat-3"
>20 ngày   → class "heat-4"  (xanh đậm nhất)
```

Định nghĩa các class `.heat-0` đến `.heat-4` trong `main.scss` (không viết scoped).

Dòng cuối: tổng toàn công ty theo tháng (bold, background phân biệt).

### Section 4 — Top 10 nhân viên nghỉ nhiều

PrimeVue `DataTable`, không phân trang (tối đa 10 dòng):

| # | Nhân viên | Phòng ban | Tổng ngày | Số lần | Tỷ lệ sử dụng |
|---|---|---|---|---|---|

Cột `Tỷ lệ sử dụng`: hiển thị `ProgressBar` PrimeVue (value = usage_rate).  
Rank 1 highlight bằng class `.rank-1` (nền vàng nhạt — định nghĩa trong `main.scss`).

### Section 5 — So sánh phòng ban

PrimeVue `DataTable` sort theo `avg_days_per_employee DESC`:

| Phòng ban | Số NV | Tổng ngày | TB/NV | Tỷ lệ sử dụng |
|---|---|---|---|---|

Cột `Tỷ lệ sử dụng`: `ProgressBar` + giá trị %.

### Section 6 — Cảnh báo carryover sắp hết hạn

Filter `Ngưỡng cảnh báo: [30 ▼ | 60 | 90] ngày`.

PrimeVue `DataTable` với row class theo `days_until_expire`:

```
≤ 7 ngày  → class "expiry-critical" (đỏ)
≤ 30 ngày → class "expiry-warning"  (cam)
> 30 ngày → class "expiry-ok"       (mặc định)
```

Định nghĩa trong `main.scss`. Hiển thị cột `Hết hạn sau` dạng badge màu.

### Mobile responsive

- KPI: 2 cột (`grid-cols-2`) thay vì 4
- Bar chart: full width, height giảm còn 250px
- Heatmap: `overflow-x-auto` + `min-width: 800px` cho bảng bên trong
- Top 10 + So sánh: ẩn cột ProgressBar, chỉ hiển thị số %
- Section 6: ẩn cột "Loại phép" trên mobile

### Frontend services — `src/services/leaveAnalyticsService.ts` (file mới)

```typescript
// Interface types (mirror Pydantic schemas)
export interface MonthlyTrendPoint { month: number; total_days: number; ... }
export interface LeaveAnalyticsSummary { ... }
export interface LeaveByTypeReport { ... }
export interface MonthlyHeatmapReport { ... }
export interface TopEmployeesReport { ... }
export interface ExpiringBalanceReport { ... }
export interface DeptComparisonReport { ... }

// Service functions
const leaveAnalyticsService = {
  getAnalyticsSummary(params: { year: number; department_id?: number }): Promise<LeaveAnalyticsSummary>
  getByType(params: { year: number; department_id?: number }): Promise<LeaveByTypeReport>
  getMonthlyHeatmap(params: { year: number }): Promise<MonthlyHeatmapReport>
  getTopEmployees(params: { year: number; department_id?: number; limit?: number }): Promise<TopEmployeesReport>
  getExpiringBalance(params: { year: number; department_id?: number; expire_days?: number }): Promise<ExpiringBalanceReport>
  getDeptComparison(params: { year: number }): Promise<DeptComparisonReport>
  exportAnalyticsUrl(params: { year: number; department_id?: number }): string
}
```

---

## Cấu trúc file

```
backend/
  app/schemas/
    leave_analytics.py              (NEW) — 7 response schemas analytics
  app/services/
    leave_analytics_service.py      (NEW) — 6 async functions + build_analytics_xlsx
    leave_report_service.py         (KHÔNG SỬA — Plan 5.4)
  app/api/v1/endpoints/
    leave_analytics.py              (NEW) — 7 endpoints GET
    leave_reports.py                (KHÔNG SỬA — Plan 5.4)
  app/api/v1/
    router.py                       (UPDATE — đăng ký /reports/leaves)
  tests/
    test_leave_analytics.py         (NEW) — test analytics endpoints

frontend/
  src/services/
    leaveAnalyticsService.ts        (NEW) — API calls + types
    leaveReportService.ts           (KHÔNG SỬA — Plan 5.4)
  src/views/reports/
    LeaveAnalyticsView.vue          (NEW) — analytics dashboard
  src/router/
    index.ts                        (UPDATE — thêm /reports/leave-analytics)
  src/components/layout/
    AppMenu.vue                     (UPDATE — thêm vào nhóm Báo cáo)
  src/assets/
    main.scss                       (UPDATE — thêm .heat-0..4, .rank-1, .expiry-*)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend Analytics Core (không có Frontend)

**Mục tiêu:** 4 endpoints analytics cơ bản hoạt động, có test.

**Backend:**

1. Tạo `app/schemas/leave_analytics.py`:
   - `MonthlyTrendPoint`, `LeaveAnalyticsSummary`
   - `LeaveTypeStatRow`, `LeaveByTypeReport`
   - `HeatmapDeptRow`, `MonthlyHeatmapReport`
   - `TopEmployeeRow`, `TopEmployeesReport`

2. Tạo `app/services/leave_analytics_service.py`:
   - `get_analytics_summary()` — 4 KPI + 12-point trend
   - `get_by_type()` — GROUP BY leave_type + percentage
   - `get_monthly_heatmap()` — pivot trong Python
   - `get_top_employees()` — ORDER BY + rank + usage_rate

3. Tạo `app/api/v1/endpoints/leave_analytics.py`:
   - `GET /reports/leaves/analytics-summary`
   - `GET /reports/leaves/by-type`
   - `GET /reports/leaves/monthly-heatmap`
   - `GET /reports/leaves/top-employees`

4. Đăng ký router trong `router.py`

5. Tạo `tests/test_leave_analytics.py`:
   - `test_analytics_summary_kpis_correct` — fixture 2 records, verify 4 KPIs
   - `test_trend_fills_12_months` — chỉ có tháng 3, kết quả vẫn 12 phần tử
   - `test_by_type_percentage_sums_100` — verify tổng percentage ≈ 100
   - `test_heatmap_pivot_correct` — verify dept × month đúng
   - `test_top_employees_ordering` — NV nghỉ nhiều nhất ở vị trí 1
   - `test_unauthenticated_rejected` — 401 trên tất cả endpoints

**Verify:** `pytest tests/test_leave_analytics.py -v` pass.

---

### Slice 2 — Backend Remaining + Export

**Mục tiêu:** 3 endpoints còn lại + export xlsx nhiều sheet.

**Backend:**

1. Bổ sung `app/schemas/leave_analytics.py`:
   - `ExpiringBalanceRow`, `ExpiringBalanceReport`
   - `DeptComparisonRow`, `DeptComparisonReport`

2. Bổ sung `app/services/leave_analytics_service.py`:
   - `get_expiring_balance()` — carryover_expires filter
   - `get_department_comparison()` — usage_rate theo phòng ban
   - `build_analytics_xlsx()` — 4 sheets trong 1 file

3. Bổ sung `app/api/v1/endpoints/leave_analytics.py`:
   - `GET /reports/leaves/expiring-balance`
   - `GET /reports/leaves/department-comparison`
   - `GET /reports/leaves/export-analytics`

4. Bổ sung tests:
   - `test_expiring_balance_threshold_30d` — fixture với expires = today+15 → xuất hiện
   - `test_expiring_balance_threshold_30d_miss` — expires = today+45 → không xuất hiện
   - `test_dept_comparison_usage_rate` — verify usage_rate đúng
   - `test_export_analytics_returns_xlsx` — verify Content-Type + 4 sheets trong file
   - `test_export_analytics_sheet_names` — verify tên sheet đúng

**Verify:** `pytest tests/test_leave_analytics.py -v` pass toàn bộ.

---

### Slice 3 — Frontend `LeaveAnalyticsView.vue`

**Mục tiêu:** Dashboard analytics đầy đủ, mobile responsive.

**Frontend:**

1. Tạo `src/services/leaveAnalyticsService.ts`:
   - Tất cả interface types
   - 7 functions gọi API
   - `exportAnalyticsUrl()` helper

2. Tạo `src/views/reports/LeaveAnalyticsView.vue`:
   - Toolbar: filter Năm + Phòng ban + Tải lại + Xuất Excel
   - Section 1: 4 KPI cards (`<Card>`)
   - Section 2: Bar chart loại phép (`<Chart type="bar">`)
   - Section 3: Heatmap (`<DataTable>` + cell class động)
   - Section 4: Top 10 NV (`<DataTable>` + `<ProgressBar>`)
   - Section 5: So sánh phòng ban (`<DataTable>` + `<ProgressBar>`)
   - Section 6: Expiring balance (`<DataTable>` + row class expiry)
   - Loading states: `<Skeleton>` cho mỗi section khi đang fetch
   - Error handling: `<Message severity="error">` nếu API lỗi

3. Cập nhật `src/router/index.ts`:
   ```typescript
   {
     path: '/reports/leave-analytics',
     name: 'leave-analytics',
     component: () => import('@/views/reports/LeaveAnalyticsView.vue'),
     meta: { requiresAuth: true }
   }
   ```

4. Cập nhật `src/components/layout/AppMenu.vue`:
   - Thêm item "Phân tích nghỉ phép" vào nhóm "Báo cáo" (icon: `pi pi-chart-bar`)

5. Cập nhật `src/assets/main.scss`:
   ```scss
   /* Heatmap cell colors */
   .heat-0 { background-color: #f8fafc; }
   .heat-1 { background-color: #dbeafe; }
   .heat-2 { background-color: #93c5fd; }
   .heat-3 { background-color: #3b82f6; color: white; }
   .heat-4 { background-color: #1d4ed8; color: white; font-weight: 600; }

   /* Top employee ranking */
   .rank-1 { background-color: #fef9c3 !important; }

   /* Expiry alert rows */
   .expiry-critical { background-color: #fee2e2 !important; }
   .expiry-warning  { background-color: #ffedd5 !important; }
   ```

6. Chạy `vue-tsc --noEmit` — không có lỗi TypeScript.

**Verify:**
- 4 KPI hiển thị đúng số liệu (cross-check với API response)
- Heatmap hiển thị đúng màu theo giá trị
- Export xlsx tải về, mở được, có 4 sheet
- Mobile: KPI 2 cột, heatmap scroll ngang

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| `avg_usage_rate` chia cho 0 (không có entitlement nào) | Kiểm tra denominator > 0 trước khi chia, trả về `0.0` |
| Heatmap quá nhiều phòng ban (>20) làm bảng khó đọc | Frontend: giới hạn hiển thị top 15 phòng ban (theo tổng ngày nghỉ nhiều nhất), thêm nút "Xem tất cả" |
| Nhân viên không có `employee_job_records.is_current` | LEFT JOIN → dept_name = null → nhóm vào "Không xác định" |
| `build_analytics_xlsx` chậm với dataset lớn (>500 NV × 4 sheets) | Limit export: mỗi sheet tối đa 1000 dòng; thêm chú thích trong file xlsx nếu bị cắt |
| `leave_records` thiếu `entitlement_id` ảnh hưởng KPI 2 | KPI 2 tính từ `leave_entitlements.used_days` (đã được service 5.3 cập nhật), không dùng COUNT từ leave_records |
| Prefix `/reports/leaves` conflict nếu sau này có báo cáo khác | Đặt prefix đủ cụ thể: `/reports/leaves` riêng cho leave analytics; các module khác dùng `/reports/employees`, `/reports/insurance` |
| PrimeVue `Chart` cần `chart.js` dependency | Verify `chart.js` đã có trong `package.json` trước khi dùng; nếu không có thì cài thêm |
| Carryover logic phức tạp (expires ảnh hưởng remaining) | Tái dùng helper `_remaining()` từ `leave_report_service.py` — copy vào `leave_analytics_service.py` dưới tên `_calc_remaining()` để tránh circular import |

---

## Liên kết

- **Plan 5.4 → 11.3:** Nguồn dữ liệu `leave_records` + `leave_entitlements` dùng chung. Service analytics KHÔNG sửa service 5.4.
- **11.3 → 11.1 (Dashboard tổng quan):** Khi làm Dashboard tổng quan, có thể tái dùng `get_analytics_summary()` từ `leave_analytics_service` để lấy KPI leave cho dashboard.
- **11.3 → 11.6 (Xuất báo cáo):** `build_analytics_xlsx()` là nền tảng cho module xuất báo cáo tổng hợp đa module sau này.
