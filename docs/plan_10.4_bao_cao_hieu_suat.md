# Kế hoạch triển khai — 10.4. Báo cáo Hiệu suất

**Phạm vi:** Phân phối xếp loại toàn công ty theo năm · Điểm KPI trung bình theo phòng ban · Xuất Excel  
**Phụ thuộc:** `10.1 KPI Tháng` ✅ · `10.2 Đánh giá Cuối năm` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §10.4

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_kpi_monthly` table | ✅ Hoàn thành (10.1) | Điểm KPI tháng |
| `employee_yearly_reviews` table | ✅ Hoàn thành (10.2) | Xếp loại cuối năm |
| API báo cáo hiệu suất | ❌ Chưa có | |
| Tab "Báo cáo" trong `PerformanceView.vue` | ❌ Chưa có (placeholder) | |

---

## Phạm vi

Theo FEATURES.md §10.4:
> Phân phối xếp loại toàn công ty theo năm  
> Báo cáo điểm KPI trung bình theo phòng ban

**Trong phạm vi:**
- Tổng hợp phân phối xếp loại (Xuất sắc / Tốt / Đạt / Cần cải thiện) toàn công ty theo năm
- Điểm KPI trung bình theo phòng ban (tính từ `employee_kpi_monthly`)
- Trending điểm TB theo tháng trong năm (tổng công ty hoặc từng phòng ban)
- Xuất Excel 2 sheet: "Phân phối xếp loại" + "KPI theo phòng ban"

**Ngoài phạm vi:**
- Biểu đồ (Chart) — thuộc module 11 Dashboard
- So sánh liên năm (year-over-year)
- Báo cáo KPI cá nhân chi tiết (đã có trong hồ sơ NV — 10.3)

**Không tạo bảng mới** — tất cả tính từ:
- `employee_kpi_monthly` + `employee_yearly_reviews` + `employees` + `departments`

---

## Thiết kế API

### Endpoints

```
GET /performance/report/rating-distribution
    ?year=
    → RatingDistributionReport

GET /performance/report/department-kpi
    ?year=&month=&department_id=
    → list[DepartmentKpiStat]

GET /performance/report/monthly-trend
    ?year=&department_id=
    → MonthlyKpiTrend

GET /performance/report/export
    ?year=
    → StreamingResponse (.xlsx)
    Content-Disposition: attachment; filename="bao_cao_hieu_suat_{year}.xlsx"
```

### Query parameters chi tiết

| Param | Áp dụng | Kiểu | Mô tả |
|---|---|---|---|
| `year` | tất cả | int, required | Năm báo cáo |
| `month` | department-kpi | int (1–12), optional | Lọc tháng cụ thể; null = cả năm |
| `department_id` | department-kpi, trend | int, optional | Lọc phòng ban |

### Permissions

| Endpoint | Permission |
|---|---|
| Tất cả | `performance:view` |

---

## Schemas

### `RatingDistributionReport`

```python
class RatingCount(BaseModel):
    rating: str                 # "xuat_sac" / "tot" / "dat" / "can_cai_thien"
    rating_label: str
    count: int
    percentage: float           # làm tròn 1 chữ số thập phân

class RatingDistributionReport(BaseModel):
    year: int
    total_reviewed: int         # tổng NV có đánh giá cuối năm cho năm này
    total_employees: int        # tổng NV active (tham chiếu)
    coverage_rate: float        # total_reviewed / total_employees * 100
    distribution: list[RatingCount]
```

### `DepartmentKpiStat`

```python
class DepartmentKpiStat(BaseModel):
    department_id: int | None
    department_name: str | None
    employee_count: int             # số NV có KPI trong kỳ
    avg_score: Decimal | None       # điểm TB của phòng ban
    min_score: Decimal | None
    max_score: Decimal | None
    months_data_count: int          # tổng lượt (NV × tháng) có dữ liệu
```

### `MonthlyKpiTrend`

```python
class MonthlyPoint(BaseModel):
    month: int
    avg_score: Decimal | None   # None nếu tháng đó không có dữ liệu
    employee_count: int         # số NV có KPI tháng đó

class MonthlyKpiTrend(BaseModel):
    year: int
    department_id: int | None
    department_name: str | None
    points: list[MonthlyPoint]  # 12 điểm, tháng 1–12
```

---

## Service logic

### `performance_report_service.py`

**`get_rating_distribution(session, year) → RatingDistributionReport`:**
```sql
SELECT rating, COUNT(*) AS cnt
FROM employee_yearly_reviews
WHERE year = :year
GROUP BY rating
```
- Tính `total_reviewed = SUM(cnt)`
- Tính `total_employees` từ `SELECT COUNT(*) FROM employees WHERE is_active = true`
- Tính `coverage_rate = round(total_reviewed / total_employees * 100, 1)` nếu `total_employees > 0`
- Với mỗi rating: `percentage = round(cnt / total_reviewed * 100, 1)` nếu `total_reviewed > 0`
- Đảm bảo trả đủ 4 rating (count=0 cho rating không có dữ liệu)

**`get_department_kpi_stats(session, year, month?, department_id?) → list[DepartmentKpiStat]`:**
```sql
SELECT ejr.department_id, d.name,
       COUNT(DISTINCT ekm.employee_id) AS employee_count,
       AVG(ekm.score) AS avg_score,
       MIN(ekm.score) AS min_score,
       MAX(ekm.score) AS max_score,
       COUNT(*) AS months_data_count
FROM employee_kpi_monthly ekm
JOIN employees e ON ekm.employee_id = e.id
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = true
LEFT JOIN departments d ON d.id = ejr.department_id
WHERE ekm.year = :year
  [AND ekm.month = :month]           -- nếu month có giá trị
  [AND ejr.department_id = :dept_id] -- nếu department_id có giá trị
GROUP BY ejr.department_id, d.name
ORDER BY avg_score DESC NULLS LAST
```

**`get_monthly_trend(session, year, department_id?) → MonthlyKpiTrend`:**
```sql
SELECT ekm.month,
       AVG(ekm.score) AS avg_score,
       COUNT(DISTINCT ekm.employee_id) AS employee_count
FROM employee_kpi_monthly ekm
JOIN employees e ON ekm.employee_id = e.id
JOIN employee_job_records ejr ON ejr.employee_id = e.id AND ejr.is_current = true
WHERE ekm.year = :year
  [AND ejr.department_id = :dept_id]
GROUP BY ekm.month
ORDER BY ekm.month
```
- Build đủ 12 tháng (tháng không có dữ liệu → `avg_score=None, employee_count=0`)

---

### `performance_export_service.py`

**`export_performance_excel(session, year) → bytes`**

**Tên file:** `bao_cao_hieu_suat_{year}.xlsx`

**Sheet 1: "Phân phối xếp loại"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged A1:E1, bold, font 14)
Hàng 2: [PHÂN PHỐI XẾP LOẠI HIỆU SUẤT NĂM {year}] (merged A2:E2, bold, font 12)
Hàng 3: trống
Hàng 4: Header
  A: Xếp loại
  B: Số nhân viên
  C: Tỷ lệ (%)
Hàng 5–8: 4 xếp loại (Xuất sắc / Tốt / Đạt / Cần cải thiện)
Hàng 9: TỔNG CỘNG (bold, cột B = total_reviewed, cột C = 100%)
Hàng 11: [Tổng NV active: {total_employees}   Tỷ lệ có đánh giá: {coverage_rate}%]
```

**Sheet 2: "KPI theo phòng ban"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged, bold, font 14)
Hàng 2: [ĐIỂM KPI TRUNG BÌNH THEO PHÒNG BAN NĂM {year}] (merged, bold, font 12)
Hàng 3: trống
Hàng 4: Header
  A: STT
  B: Phòng ban
  C: Số NV có KPI
  D: Điểm TB
  E: Điểm thấp nhất
  F: Điểm cao nhất
  G: Tổng lượt nhập
Hàng 5+: Dữ liệu từng phòng ban (sắp xếp avg_score DESC)
Hàng cuối: TỔNG CỘNG (bold)
```

**Định dạng chung:**
- Header hàng 4: nền `#1F4E79`, chữ trắng, bold
- Dòng xen kẽ: `#F2F2F2` / trắng
- Dòng tổng: `#D9E1F2`, bold
- Cột điểm và tỷ lệ: format `0.0`
- Freeze pane tại hàng 5

---

## Thiết kế Frontend

### `PerformanceReportTab.vue`

**Bộ lọc:**
- Select: Năm (required, default: năm hiện tại)
- Button: "Xem báo cáo" (primary) → gọi các API report
- Button: "Xuất Excel" (secondary, icon: download) → gọi export

**Cards tổng hợp (sau khi fetch):**

| Card | Nội dung |
|---|---|
| Card 1 | Tổng NV có đánh giá: `total_reviewed` / `total_employees` |
| Card 2 | Tỷ lệ bao phủ: `coverage_rate`% |
| Card 3 | Xuất sắc + Tốt: tổng count 2 loại trên |
| Card 4 | Cần cải thiện: count |

**Bảng "Phân phối xếp loại":**

DataTable với cột: Xếp loại (Tag màu) / Số NV / Tỷ lệ (%)

**Bảng "KPI theo phòng ban":**

DataTable với cột: Phòng ban / Số NV có KPI / Điểm TB / Điểm thấp nhất / Điểm cao nhất
- Sắp xếp mặc định: `avg_score DESC`
- Cột điểm: 1 chữ số thập phân, "—" nếu null

**Sub-section "Xu hướng KPI theo tháng":**
- Select (filter): Phòng ban (optional, "Toàn công ty" = null)
- Button: "Xem xu hướng" → gọi `GET /performance/report/monthly-trend`
- DataTable: Tháng 1–12 / Điểm TB / Số NV
- (Không vẽ chart — chỉ bảng số liệu)

**Empty states và loading:** tương tự `TrainingReportTab.vue`

---

## Cấu trúc file mới / thay đổi

```
backend/
  app/services/performance_report_service.py   (NEW)
  app/services/performance_export_service.py   (NEW)
  app/schemas/performance.py                   (EDIT: thêm report schemas)
  app/api/v1/endpoints/performance.py          (EDIT: thêm 4 report endpoints)
  tests/test_performance_report.py             (NEW)

frontend/
  src/services/performanceService.ts                          (EDIT: thêm report API calls)
  src/views/performance/components/PerformanceReportTab.vue   (NEW)
  src/views/performance/PerformanceView.vue                   (EDIT: activate tab báo cáo)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: API báo cáo

**Tasks:**
1. Schemas báo cáo vào `performance.py`: `RatingCount`, `RatingDistributionReport`, `DepartmentKpiStat`, `MonthlyPoint`, `MonthlyKpiTrend`
2. Service `performance_report_service.py`: 3 hàm get
3. Endpoints: `GET /performance/report/rating-distribution`, `GET /performance/report/department-kpi`, `GET /performance/report/monthly-trend`

**Exit criteria:**
- `rating-distribution`: tổng `count` = `total_reviewed`; đủ 4 rating (count=0 cho loại không có)
- `coverage_rate` = `total_reviewed / total_employees * 100` đúng
- `department-kpi`: `avg_score` đúng theo phòng ban, filter `month` đúng
- `monthly-trend`: đủ 12 tháng, tháng không có dữ liệu → avg_score=null, count=0

---

### Slice 2 — Backend: Export Excel

**Tasks:**
1. Service `performance_export_service.py`
2. Endpoint `GET /performance/report/export`

**Exit criteria:**
- Content-Type đúng: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- File Excel hợp lệ, có đúng 2 sheets
- Sheet 1: tổng count = total_reviewed
- Sheet 2: số dòng = số phòng ban có dữ liệu

---

### Slice 3 — Frontend

**Tasks:**
1. Thêm report types + API calls vào `performanceService.ts`
2. Tạo `PerformanceReportTab.vue`
3. Activate tab báo cáo trong `PerformanceView.vue`

**Exit criteria:**
- Tab "Báo cáo" hiển thị đúng
- Bấm "Xem báo cáo": cards + tables cập nhật
- Xuất Excel: file tải xuống thành công
- Bảng phòng ban sort `avg_score DESC`

---

### Slice 4 — Tests

Tạo `tests/test_performance_report.py`:

```
TestRatingDistribution:
  - test_distribution_counts_correct
  - test_distribution_includes_all_four_ratings   (count=0 cho rating không có)
  - test_coverage_rate_calculation
  - test_percentage_sum_to_100
  - test_empty_year_returns_zero_counts

TestDepartmentKpi:
  - test_avg_score_calculated_per_department
  - test_filter_by_month
  - test_filter_by_department_id
  - test_no_data_returns_empty_list

TestMonthlyTrend:
  - test_trend_has_12_months
  - test_months_without_data_return_null_avg
  - test_filter_by_department

TestPerformanceExport:
  - test_export_returns_xlsx_content_type
  - test_export_valid_xlsx_file
  - test_export_has_two_sheets
  - test_sheet1_rating_counts_match_distribution
  - test_sheet2_row_count_matches_departments
```

**Exit criteria:**
- Tất cả test pass: `docker exec hrms-backend-1 pytest tests/test_performance_report.py -v`

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| NV đổi phòng ban giữa năm → `department_id` không chính xác khi group | Trung bình | Dùng `employee_job_records WHERE is_current = true` — phòng ban hiện tại, đây là cách tiếp cận nhất quán với toàn hệ thống |
| `total_employees` (active) vs `total_reviewed` không cùng thời điểm | Thấp | `total_employees` = active hiện tại; ghi rõ footnote trên báo cáo "Tính theo nhân viên hiện tại" |
| Năm chưa có đánh giá cuối năm → distribution = [] | Thấp | Trả đủ 4 rating với count=0; UI hiển thị empty state rõ ràng |
| Query AVG KPI department với nhiều NV × tháng → chậm | Thấp | Index `ix_employee_kpi_monthly_year_month` + `ix_employee_kpi_monthly_employee_id` đã có từ 10.1 |
| Excel 2 sheet với ít dữ liệu → nhanh, không cần write_only | Thấp | Report này nhẹ hơn training export; dùng openpyxl thông thường là đủ |
