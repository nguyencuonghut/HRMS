# Kế hoạch triển khai — 14.3. Báo cáo Onboarding & Thử việc

**Phạm vi:** 6 báo cáo tổng hợp về onboarding checklist và thử việc  
**Phụ thuộc:** `14.1` (OnboardingChecklist data — PHẢI hoàn thành trước) · `14.2` (ProbationEvaluation data — PHẢI hoàn thành trước) · `employees` ✅ · `employee_job_records` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §14.3  
**Lưu ý:** Module này chỉ đọc — không tạo bảng mới, toàn bộ là aggregation queries trên dữ liệu từ 14.1 và 14.2

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `OnboardingChecklist` + `OnboardingChecklistItem` | ❌ Phụ thuộc 14.1 | Phải hoàn thành 14.1 trước |
| `ProbationEvaluation` | ❌ Phụ thuộc 14.2 | Phải hoàn thành 14.2 trước |
| `Employee`, `EmployeeJobRecord`, `Department` | ✅ Hoàn thành | Data source chính |
| API báo cáo 14.3 | ❌ Chưa có | |
| `probation_report_service.py` | ❌ Chưa có | |
| Frontend `ProbationReportView.vue` | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi (6 báo cáo):**

1. **Danh sách nhân viên đang thử việc** — với số ngày còn lại, trạng thái onboarding
2. **Tỷ lệ hoàn thành checklist onboarding theo phòng ban** — completion rate phân theo bộ phận và kỳ
3. **Tỷ lệ vượt thử việc** — theo phòng ban, vị trí, kỳ (quý/năm)
4. **Thống kê lý do không qua thử việc** — phân nhóm từ manager_comment (manual category hoặc keyword count)
5. **Thời gian trung bình hoàn thành checklist** — tính theo phòng ban và kỳ
6. **Xuất Excel** — toàn bộ báo cáo ra file .xlsx (nhiều sheet)

**Ngoài phạm vi:**
- Real-time dashboard
- Dự báo tỷ lệ vượt thử việc (ML)
- So sánh benchmark ngành
- Phân tích NLP tự động từ `manager_comment`
- Báo cáo tuyển dụng (→ 13.8)

---

## Định nghĩa KPI

### Probation Pass Rate

```sql
-- Tỷ lệ vượt thử việc trong kỳ
SELECT
    COUNT(*) FILTER (WHERE pe.result = 'passed') AS passed,
    COUNT(*) FILTER (WHERE pe.result IN ('passed','failed','extended')) AS total_decided,
    ROUND(
        COUNT(*) FILTER (WHERE pe.result = 'passed') * 100.0
        / NULLIF(COUNT(*) FILTER (WHERE pe.result IN ('passed','failed','extended')), 0),
        1
    ) AS pass_rate
FROM probation_evaluations pe
WHERE pe.status = 'approved'
  AND pe.evaluation_date BETWEEN :start_date AND :end_date
```

Lưu ý: `extended` được tính vào `total_decided` vì đây là quyết định, không phải kết quả cuối cùng.

### Average Checklist Completion Time (ngày)

```sql
SELECT
    d.name AS department_name,
    AVG(
        EXTRACT(DAY FROM (oc.updated_at - e.start_date::timestamp))
    ) AS avg_completion_days
FROM onboarding_checklists oc
JOIN employees e ON e.id = oc.employee_id
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
JOIN departments d ON d.id = ejr.department_id
WHERE oc.status = 'completed'
  AND e.start_date BETWEEN :start_date AND :end_date
GROUP BY d.id, d.name
ORDER BY avg_completion_days ASC
```

### Active Probation Employees

```sql
SELECT
    e.id AS employee_id,
    e.full_name,
    ejr.department_id,
    d.name AS department_name,
    ejr.probation_start_date,
    ejr.probation_end_date,
    (ejr.probation_end_date - CURRENT_DATE) AS days_remaining,
    oc.status AS onboarding_status,
    oc.completion_pct,
    COALESCE(pe.result, 'not_started') AS evaluation_result
FROM employees e
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
JOIN departments d ON d.id = ejr.department_id
LEFT JOIN onboarding_checklists oc ON oc.employee_id = e.id
LEFT JOIN probation_evaluations pe ON pe.employee_id = e.id AND pe.job_record_id = ejr.id
WHERE e.status = 'probation'
ORDER BY ejr.probation_end_date ASC
```

### Checklist Completion Rate by Department

```sql
SELECT
    d.id AS department_id,
    d.name AS department_name,
    COUNT(oc.id) AS total_checklists,
    COUNT(oc.id) FILTER (WHERE oc.status = 'completed') AS completed_count,
    ROUND(
        COUNT(oc.id) FILTER (WHERE oc.status = 'completed') * 100.0
        / NULLIF(COUNT(oc.id), 0),
        1
    ) AS completion_rate,
    ROUND(AVG(oc.completion_pct), 1) AS avg_completion_pct
FROM onboarding_checklists oc
JOIN employees e ON e.id = oc.employee_id
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = TRUE
JOIN departments d ON d.id = ejr.department_id
WHERE e.start_date BETWEEN :start_date AND :end_date
GROUP BY d.id, d.name
ORDER BY completion_rate DESC
```

---

## API Design

### Danh sách nhân viên đang thử việc

```
GET /reports/probation/active?department_id=&sort_by=days_remaining&order=asc
    → List[ProbationActiveItem]
    -- Luôn chỉ hiện employee.status='probation'
    -- sort_by: days_remaining | employee_name | department_name
```

### Tỷ lệ hoàn thành checklist

```
GET /reports/probation/checklist-completion?year=&quarter=&department_id=
    → {
        period: { year, quarter? },
        department_breakdown: List[ChecklistCompletionRow],
        overall: { total, completed, completion_rate, avg_completion_pct }
      }
```

### Tỷ lệ vượt thử việc

```
GET /reports/probation/pass-rate?start_date=&end_date=&department_id=&position_id=
    → {
        period: { start_date, end_date },
        overall: { passed, failed, extended, total_decided, pass_rate },
        by_department: List[ProbationPassRateStat],
        by_position: List[ProbationPassRateStat],
        monthly_trend: List[{ month, year, passed, failed, total }]
      }
```

### Thống kê lý do không qua

```
GET /reports/probation/failure-reasons?start_date=&end_date=
    → {
        total_failed: int,
        reasons: List[{ keyword, count, pct }],
        raw_comments: List[{ employee_id, employee_name, evaluation_date, manager_comment }]
      }
    -- reasons: đếm keyword thủ công từ manager_comment (không dùng ML)
    -- Keyword categories: "năng lực", "thái độ", "văn hóa", "kpi", "sức khỏe", "nghỉ việc sớm"
```

### Thời gian trung bình hoàn thành checklist

```
GET /reports/probation/completion-time?year=&department_id=
    → {
        overall_avg_days: float,
        by_department: List[{ department_name, avg_days, completed_count }]
      }
```

### Xuất Excel

```
GET /reports/probation/export?start_date=&end_date=&department_id=
    → file .xlsx (5 sheets)
    -- Giới hạn: tối đa range 1 năm; trả 400 nếu end_date - start_date > 366 ngày
```

### Permissions

| Action | Permission |
|---|---|
| Xem báo cáo | `employees:view` |
| Xuất Excel | `employees:view` |

---

## Service Logic — `probation_report_service.py`

### `get_active_probation(session, department_id?) → List[ProbationActiveItem]`
- Query SQL như trên với LEFT JOIN onboarding_checklists và probation_evaluations
- Thêm computed field `urgency`: `days_remaining <= 7 → 'critical'`, `<= 15 → 'warning'`, else `'normal'`

### `get_checklist_completion(session, year, quarter?, department_id?) → ChecklistCompletionReport`
- Tính `start_date/end_date` từ `year` + `quarter` (nếu có)
- Query GROUP BY department
- Tổng overall = sum của tất cả departments

### `get_pass_rate(session, start_date, end_date, department_id?, position_id?) → ProbationPassRateReport`
- Query overall + GROUP BY department + GROUP BY position + GROUP BY month
- `monthly_trend`: trả đủ các tháng trong range, tháng nào = 0 vẫn trả (không bỏ qua)

### `get_failure_reasons(session, start_date, end_date) → FailureReasonReport`
- Query tất cả `manager_comment` WHERE `result='failed'`
- Đếm keyword đơn giản: `for kw in KEYWORDS: count += comment.lower().count(kw)`
- KEYWORDS = `['năng lực', 'thái độ', 'văn hóa', 'kpi', 'sức khỏe', 'nghỉ việc', 'không phù hợp']`
- Trả cả `raw_comments` để HR đọc trực tiếp

### `get_completion_time(session, year, department_id?) → CompletionTimeReport`
- AVG(updated_at - employee.start_date) WHERE onboarding_checklists.status='completed'
- GROUP BY department

### `export_excel(session, start_date, end_date, department_id?) → bytes`

File Excel với 5 sheets:
1. **Tổng quan**: KPI summary cards (số đang thử việc, tỷ lệ vượt, thời gian TB hoàn thành checklist)
2. **Đang thử việc**: DataTable active employees (có cột urgency)
3. **Hoàn thành checklist**: completion rate by department
4. **Tỷ lệ vượt thử việc**: pass rate by dept + by position + trend tháng
5. **Lý do không đạt**: failure reasons + raw comments

Style: header row fill `#1B4F72`, alternating row, % format cho rate, số ngày format integer.

---

## Schemas

```python
class ProbationActiveItem(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_id: int
    department_name: str
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    days_remaining: Optional[int]       # None nếu probation_end_date = None
    urgency: str                        # normal | warning | critical
    onboarding_status: Optional[str]   # in_progress | completed | cancelled | None (không có checklist)
    completion_pct: Optional[float]
    evaluation_result: str              # not_started | pending | passed | failed | extended

class ChecklistCompletionRow(BaseModel):
    department_id: int
    department_name: str
    total_checklists: int
    completed_count: int
    completion_rate: float              # %
    avg_completion_pct: float           # % tiến độ trung bình kể cả chưa xong

class ProbationPassRateStat(BaseModel):
    group_id: Optional[int]             # department_id hoặc position_id
    group_name: str
    passed: int
    failed: int
    extended: int
    total_decided: int
    pass_rate: Optional[float]          # None nếu total=0

class MonthlyProbationTrend(BaseModel):
    year: int
    month: int
    passed: int
    failed: int
    extended: int
    total: int

class ProbationPassRateReport(BaseModel):
    period_start: date
    period_end: date
    overall: ProbationPassRateStat
    by_department: List[ProbationPassRateStat]
    by_position: List[ProbationPassRateStat]
    monthly_trend: List[MonthlyProbationTrend]

class FailureReasonReport(BaseModel):
    total_failed: int
    reasons: List[FailureKeywordCount]  # sorted by count DESC
    raw_comments: List[FailureCommentItem]

class FailureKeywordCount(BaseModel):
    keyword: str
    count: int
    pct: float

class FailureCommentItem(BaseModel):
    employee_id: int
    employee_name: str
    evaluation_date: date
    manager_comment: Optional[str]
```

---

## Thiết kế Frontend

### `ProbationReportView.vue` (standalone — route `/employees/probation-reports`)

**Breadcrumb:** `Nhân viên > Báo cáo thử việc`

**Toolbar:**
- DatePicker range (start_date → end_date); default: 12 tháng gần nhất
- Select Phòng ban (optional)
- Button "Xem báo cáo"
- Button "Xuất Excel" → GET /reports/probation/export?... → tải file

**Section 1: Summary KPI Cards (4 cards)**

| Card | Giá trị | Màu |
|---|---|---|
| Đang thử việc | COUNT(active) | Primary |
| Ngày còn lại TB | AVG(days_remaining) | Info |
| Tỷ lệ vượt thử việc | `pass_rate`% | Success |
| Checklist hoàn thành TB | `avg_completion_pct`% | Warning |

**Section 2: DataTable — Nhân viên đang thử việc**

| Cột | Nội dung |
|---|---|
| Nhân viên | name + code badge |
| Phòng ban | |
| Ngày kết thúc TV | probation_end_date |
| Còn lại | days_remaining — Badge đỏ (<= 7), cam (<= 15), xanh (> 15) |
| Onboarding | completion_pct ProgressBar |
| Kết quả đánh giá | Tag: Chưa đánh giá / Đang chờ / Đạt / Không đạt / Gia hạn |
| Thao tác | Link "Xem hồ sơ" → /employees/{id}?tab=probation |

Sortable theo `days_remaining` ASC (mặc định).

**Section 3: Chart + DataTable — Tỷ lệ vượt thử việc theo phòng ban**

- Bar chart: pass_rate by department (PrimeVue Chart.js)
- DataTable: department_name, passed, failed, extended, pass_rate%

**Section 4: Line Chart — Xu hướng tháng**

- Line chart: passed, failed (stacked) theo tháng
- Trục X: 12 tháng gần nhất

**Section 5: DataTable — Lý do không đạt**

- Chỉ hiển thị khi có data (total_failed > 0)
- Top keywords + count + %
- Accordion mở ra: raw comments (tên nhân viên, ngày, nhận xét)

### Route cần thêm (`router/index.ts`)

```typescript
{
  path: 'employees/probation-reports',
  name: 'probation-reports',
  component: () => import('@/views/employees/ProbationReportView.vue'),
  meta: { title: 'Báo cáo thử việc' },
}
```

### Menu item cần thêm (`AppMenu.vue` — submenu Nhân sự)

```typescript
{ to: '/employees/probation-reports', label: 'Báo cáo thử việc', icon: 'pi-chart-bar' }
```

---

## Cấu trúc file

```
backend/
  app/services/probation_report_service.py              (NEW)
  app/schemas/probation_report.py                       (NEW: report schemas tách riêng khỏi probation.py)
  app/api/v1/endpoints/probation_reports.py             (NEW: report endpoints)
  app/api/v1/router.py                                  (EDIT: include probation_reports router)
  tests/test_probation_reports.py                       (NEW)

frontend/
  src/services/probationReportService.ts                (NEW)
  src/views/employees/ProbationReportView.vue           (NEW — standalone view)
  src/router/index.ts                                   (EDIT: thêm route /employees/probation-reports)
  src/components/layout/AppMenu.vue                     (EDIT: thêm submenu item Báo cáo thử việc)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Core reports API + Service
- `probation_report_service.py`: `get_active_probation`, `get_checklist_completion`, `get_pass_rate`, `get_failure_reasons`, `get_completion_time`
- `probation_report.py` schemas
- `probation_reports.py` endpoints: 5 GET endpoints
- Tests: `test_probation_reports.py` với seed data từ 14.1 + 14.2
- **Deliverable:** Tất cả 5 API endpoints trả data đúng, coverage test từng query

### Slice 2 — Backend: Excel export
- `export_excel()` với 5 sheets
- Endpoint `GET /reports/probation/export`
- Validation: max 1 năm range; trả 400 nếu vượt
- **Deliverable:** Tải được file Excel với đủ 5 sheet, data đúng, format đẹp

### Slice 3 — Frontend
- `probationReportService.ts`: API calls
- `ProbationReportView.vue`: KPI cards + 2 DataTables + 2 Charts + failure reasons section + Export button
- Router + AppMenu update
- **Deliverable:** HR xem báo cáo trong UI, lọc theo phòng ban/kỳ, xuất Excel

---

## Phụ thuộc rõ ràng

**Module 14.1 PHẢI hoàn thành trước:**
- `onboarding_checklists` và `onboarding_checklist_items` phải có data thực tế
- Không có data → báo cáo checklist trả `null` hoặc `0%`; không crash

**Module 14.2 PHẢI hoàn thành trước:**
- `probation_evaluations` phải có data với `status='approved'`
- Không có data → pass_rate = `None`; frontend hiển thị "Chưa có dữ liệu"

**Xử lý graceful khi thiếu data:**
- Tất cả aggregate trả `Optional[float]`; nếu `None` → frontend hiển thị `—`
- `monthly_trend`: trả đủ tháng trong range; tháng không có data → count = 0 (không bỏ tháng)

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Query chậm khi JOIN nhiều bảng với data lớn | Trung bình | Thêm index `ix_probation_eval_status_date` trên `(status, evaluation_date)`; index `ix_onboarding_checklists_status` đã có trong 14.1 |
| `pass_rate` khi không có data 14.2 | Thấp | Return `None`; frontend hiển thị "Chưa có dữ liệu" |
| Export Excel quá lớn khi range > 1 năm | Thấp | Validate: `(end_date - start_date).days > 366 → raise 400` với message rõ ràng |
| `failure_reasons` keyword count không chính xác (tiếng Việt) | Thấp | Dùng keyword đơn giản + `lower()` + `count()`; không dùng NLP; ghi chú trong UI "Thống kê từ khóa (không phân tích tự động)" |
| Báo cáo 14.3 build trước khi 14.1/14.2 có data | Thấp | Tất cả aggregate có NULLIF và Optional; unit test với empty DB phải pass (trả 0/None, không crash) |
