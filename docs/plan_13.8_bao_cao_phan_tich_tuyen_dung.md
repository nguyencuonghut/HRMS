# Kế hoạch triển khai — 13.8. Báo cáo & Phân tích tuyển dụng

**Phạm vi:** Funnel report · Time to Hire/Fill · Cost per Hire · Channel effectiveness · Probation Pass Rate  
**Phụ thuộc:** `13.1→13.6` (toàn bộ dữ liệu tuyển dụng) · `14.x Thử việc` (Probation Pass Rate)  
**Căn cứ nghiệp vụ:** FEATURES.md §13.8  
**Lưu ý:** Module này chỉ đọc — không tạo bảng mới (trừ bảng cache tùy chọn), toàn bộ là aggregation queries trên dữ liệu hiện có

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Dữ liệu tuyển dụng 13.1→13.6 | Phụ thuộc | Phải hoàn thành trước |
| API báo cáo | ❌ Chưa có | |
| Frontend | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- **Funnel report**: số ứng viên qua từng stage, tỷ lệ chuyển đổi giữa các bước
- **Time to Hire**: từ ngày tạo JR → ngày `hiring_decision.status = converted`
- **Time to Fill**: từ ngày `job_posting.opened_at` → ngày tuyển được
- **Cost per Hire**: tổng chi phí tuyển dụng (`recruitment_budget_items`) / số người tuyển được
- **Offer Acceptance Rate**: offers_accepted / offers_sent × 100%
- **Channel effectiveness**: số ứng viên, tỷ lệ hired, chi phí theo kênh tuyển dụng
- **Probation Pass Rate**: tỷ lệ vượt thử việc (từ Module 14 khi có dữ liệu)
- Lọc theo: phòng ban, vị trí, khoảng thời gian, kênh tuyển dụng
- Xuất Excel toàn bộ báo cáo

**Ngoài phạm vi:**
- Dự báo nhu cầu tuyển dụng (ML/AI)
- Benchmark so sánh với ngành (external data)
- Real-time dashboard streaming

---

## Các chỉ số chính (KPI Definitions)

### Time to Hire (ngày)

```sql
-- Tính từ ngày ứng viên apply → ngày convert thành nhân viên
SELECT AVG(
    EXTRACT(DAY FROM (hd.created_at - ca.applied_date::timestamp))
) AS avg_time_to_hire
FROM hiring_decisions hd
JOIN offers o ON o.id = hd.offer_id
JOIN candidate_applications ca ON ca.id = o.application_id
WHERE hd.status = 'converted'
  AND hd.created_at BETWEEN :start_date AND :end_date
```

### Time to Fill (ngày)

```sql
-- Tính từ ngày job_posting active → ngày JR completed
SELECT AVG(
    EXTRACT(DAY FROM (jr.updated_at - jp.opened_at))
) AS avg_time_to_fill
FROM job_requisitions jr
JOIN job_postings jp ON jp.job_requisition_id = jr.id
WHERE jr.status = 'completed'
  AND jp.opened_at BETWEEN :start_date AND :end_date
```

### Funnel Conversion

```sql
-- Đếm ứng viên tại mỗi stage trong kỳ
SELECT current_stage, COUNT(*) AS count
FROM candidate_applications
WHERE job_requisition_id IN (
    SELECT id FROM job_requisitions WHERE department_id = :dept_id
)
GROUP BY current_stage
```

Tỷ lệ chuyển đổi: `stage_n / stage_{n-1} * 100%`

### Offer Acceptance Rate

```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'accepted') AS accepted,
    COUNT(*) FILTER (WHERE status IN ('sent','waiting','accepted','rejected','expired')) AS total_sent,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'accepted') * 100.0
        / NULLIF(COUNT(*) FILTER (WHERE status IN ('sent','waiting','accepted','rejected','expired')), 0),
        1
    ) AS acceptance_rate
FROM offers
WHERE sent_at BETWEEN :start_date AND :end_date
```

### Cost per Hire

```sql
SELECT
    SUM(rbi.actual_amount) / NULLIF(COUNT(DISTINCT hd.id), 0) AS cost_per_hire
FROM recruitment_budget_items rbi
JOIN job_requisitions jr ON jr.id = rbi.job_requisition_id
JOIN hiring_decisions hd ON hd.job_requisition_id = jr.id
WHERE hd.status = 'converted'
  AND rbi.expense_date BETWEEN :start_date AND :end_date
```

### Channel Effectiveness

```sql
SELECT
    rc.name AS channel_name,
    COUNT(ca.id) AS total_candidates,
    COUNT(hd.id) AS hired_count,
    ROUND(COUNT(hd.id) * 100.0 / NULLIF(COUNT(ca.id), 0), 1) AS hire_rate,
    SUM(rbi.actual_amount) AS total_cost,
    SUM(rbi.actual_amount) / NULLIF(COUNT(hd.id), 0) AS cost_per_hire
FROM recruitment_channels rc
LEFT JOIN candidate_applications ca ON ca.source_channel_id = rc.id
LEFT JOIN offers o ON o.application_id = ca.id
LEFT JOIN hiring_decisions hd ON hd.offer_id = o.id AND hd.status = 'converted'
LEFT JOIN recruitment_budget_items rbi ON rbi.channel_id = rc.id
WHERE ca.created_at BETWEEN :start_date AND :end_date
GROUP BY rc.id, rc.name
ORDER BY hired_count DESC
```

---

## API Design

### Báo cáo tổng quan

```
GET /recruitment/reports/summary?start_date=&end_date=&department_id=&position_id=
    → {
        total_jr: int,                     -- JR mở trong kỳ
        total_applications: int,
        total_hired: int,
        avg_time_to_hire: float,           -- ngày
        avg_time_to_fill: float,           -- ngày
        offer_acceptance_rate: float,      -- %
        cost_per_hire: float,              -- VND
        probation_pass_rate: Optional[float]  -- % (nếu có dữ liệu Module 14)
      }
```

### Funnel report

```
GET /recruitment/reports/funnel?start_date=&end_date=&department_id=&job_requisition_id=
    → List[{ stage, count, conversion_rate_from_prev }]
```

### Time metrics

```
GET /recruitment/reports/time-metrics?year=&department_id=
    → {
        monthly: List[{
            month: int,
            avg_time_to_hire: float,
            avg_time_to_fill: float,
            hired_count: int
        }]
      }
```

### Channel effectiveness

```
GET /recruitment/reports/channel-effectiveness?start_date=&end_date=
    → List[{
        channel_id, channel_name,
        total_candidates, hired_count, hire_rate,
        total_cost, cost_per_hire
      }]
```

### Department breakdown

```
GET /recruitment/reports/by-department?start_date=&end_date=
    → List[{
        department_id, department_name,
        total_jr, hired_count,
        avg_time_to_hire, offer_acceptance_rate,
        budget_used, cost_per_hire
      }]
```

### Xuất Excel

```
GET /recruitment/reports/export?start_date=&end_date=&department_id=&format=xlsx
    → file .xlsx (nhiều sheet: Tổng quan, Funnel, Kênh tuyển dụng, Theo phòng ban, Chỉ tiêu tháng)
```

### Permissions

| Action | Permission |
|---|---|
| Xem báo cáo | `recruitment:view` |
| Xuất Excel | `recruitment:view` |

---

## Schemas

```python
class RecruitmentSummaryReport(BaseModel):
    period_start: date
    period_end: date
    total_jr: int
    total_applications: int
    total_screened: int
    total_interviewed: int
    total_offered: int
    total_hired: int
    avg_time_to_hire: Optional[float]       -- ngày, None nếu chưa có data
    avg_time_to_fill: Optional[float]
    offer_acceptance_rate: Optional[float]  -- %
    cost_per_hire: Optional[float]          -- VND
    probation_pass_rate: Optional[float]    -- %, None nếu module 14 chưa có data

class FunnelStage(BaseModel):
    stage: str                  -- new | screening | test | interview | offer | hired | rejected
    stage_label: str            -- "Mới" | "Sàng lọc" | "Kiểm tra" | ...
    count: int
    conversion_rate: Optional[float]  -- % so với stage trước

class ChannelEffectivenessItem(BaseModel):
    channel_id: int
    channel_name: str
    total_candidates: int
    hired_count: int
    hire_rate: float        -- %
    total_cost: Optional[float]   -- VND, None nếu không có budget data
    cost_per_hire: Optional[float]

class DepartmentRecruitmentStat(BaseModel):
    department_id: int
    department_name: str
    total_jr: int
    open_jr: int
    hired_count: int
    avg_time_to_hire: Optional[float]
    offer_acceptance_rate: Optional[float]
    budget_used: Optional[float]
    cost_per_hire: Optional[float]

class MonthlyTimeMetric(BaseModel):
    month: int
    year: int
    avg_time_to_hire: Optional[float]
    avg_time_to_fill: Optional[float]
    hired_count: int
    applications_count: int
```

---

## Service Logic

### `recruitment_report_service.py`

**`get_summary(session, start_date, end_date, department_id?) → RecruitmentSummaryReport`**
- Chạy 5 queries song song (asyncio.gather)
- `probation_pass_rate`: JOIN với `employee_job_records` — nếu bảng probation (Module 14) chưa có → trả `None`

**`get_funnel(session, start_date, end_date, department_id?, jr_id?) → List[FunnelStage]`**
- Snapshot theo stage cuối cùng của application trong kỳ
- Tính `conversion_rate` giữa các bước liền kề
- Stage order: new → screening → test → interview → offer → hired

**`get_channel_effectiveness(session, start_date, end_date) → List[ChannelEffectivenessItem]`**
- LEFT JOIN để giữ kênh có 0 ứng viên
- Sort theo `hired_count DESC`, sau đó `total_candidates DESC`

**`get_time_metrics_monthly(session, year, department_id?) → List[MonthlyTimeMetric]`**
- Tháng nào không có data → `avg_time_to_hire = None`, `hired_count = 0`
- Trả đủ 12 tháng của năm (kể cả tháng chưa có data)

**`export_excel(session, start_date, end_date, department_id?) → bytes`**

File Excel với 5 sheets:
1. **Tổng quan**: KPI summary + biểu đồ (bar chart funnel)
2. **Funnel tuyển dụng**: bảng chuyển đổi từng stage
3. **Theo kênh tuyển dụng**: channel effectiveness table
4. **Theo phòng ban**: department breakdown
5. **Xu hướng tháng**: 12 tháng time metrics

Style: header row fill `#1B4F72`, alternating row color, number format VND cho cost, % format cho rate.

---

## Thiết kế Frontend

### `RecruitmentReportTab.vue` (trong `RecruitmentView.vue`)

**Toolbar:**
- DatePicker range (start_date → end_date)
- Select Phòng ban (optional)
- Button "Xem báo cáo"
- Button "Xuất Excel" → tải file

**Section 1: Summary Cards (6 cards)**

| Card | Giá trị |
|---|---|
| Tổng JR | `total_jr` |
| Ứng viên tiếp nhận | `total_applications` |
| Đã tuyển | `total_hired` |
| Thời gian tuyển TB | `avg_time_to_hire` ngày |
| Tỷ lệ chấp nhận Offer | `offer_acceptance_rate`% |
| Chi phí mỗi tuyển dụng | `cost_per_hire` VND |

**Section 2: Funnel Chart**
- Horizontal bar chart (PrimeVue Chart / Chart.js)
- Hiển thị count và conversion rate
- Màu gradient từ xanh → vàng theo tỷ lệ chuyển đổi

**Section 3: DataTable — Hiệu quả kênh tuyển dụng**

| Cột | |
|---|---|
| Kênh | |
| Ứng viên | |
| Đã tuyển | Badge |
| Tỷ lệ tuyển | % |
| Chi phí tổng | VND |
| Chi phí/người | VND |

**Section 4: DataTable — Theo phòng ban**
- Dept name, JR count, hired count, avg time to hire, OAR, cost/hire

**Section 5: Line Chart — Xu hướng tháng**
- 2 lines: Time to Hire, Time to Fill (ngày)
- Bar chart overlay: hired_count
- Trục X: 12 tháng của năm

---

## Cấu trúc file

```
backend/
  app/services/recruitment_report_service.py             (NEW)
  app/schemas/recruitment.py                             (EDIT: thêm report schemas)
  app/api/v1/endpoints/recruitment.py                    (EDIT: thêm report endpoints)
  tests/test_recruitment_reports.py                      (NEW)

frontend/
  src/services/recruitmentService.ts                     (EDIT: thêm report API)
  src/views/recruitment/components/RecruitmentReportTab.vue (NEW)
  src/views/recruitment/RecruitmentView.vue              (EDIT: thêm tab Báo cáo)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Summary + Funnel
- `get_summary()`, `get_funnel()`
- Endpoints: `/reports/summary`, `/reports/funnel`

### Slice 2 — Backend: Channel + Department + Time metrics
- `get_channel_effectiveness()`, `get_time_metrics_monthly()`, `get_department_breakdown()`
- Endpoints tương ứng

### Slice 3 — Backend: Excel export + Tests
- `export_excel()` với 5 sheets
- `tests/test_recruitment_reports.py`: test từng query với data đã seed từ các module trước

### Slice 4 — Frontend
- Summary cards + Funnel chart
- DataTable kênh + phòng ban
- Line chart xu hướng tháng
- Export button

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Query tổng hợp chậm khi data lớn | Trung bình | Thêm index trên `created_at`, `status`, `department_id`; xem xét materialized view cho báo cáo năm |
| `probation_pass_rate` khi Module 14 chưa có | Trung bình | Trả `None`, frontend hiển thị "Chưa có dữ liệu" |
| `cost_per_hire = None` khi không nhập budget | Thấp | Hiển thị `—` khi `None`; không crash |
| Funnel count không khớp (1 ứng viên nhiều JR) | Trung bình | Tính theo `application_id` (không theo `candidate_id`), ghi rõ "số lượt ứng tuyển" |
| Export Excel quá lớn (nhiều năm) | Thấp | Giới hạn range tối đa 1 năm (365 ngày); trả 400 nếu vượt quá |
| Time to Fill không xác định được (JR không có posting) | Thấp | Tính `time_to_fill` chỉ cho JR có ít nhất 1 posting active; exclude JR không có posting |
