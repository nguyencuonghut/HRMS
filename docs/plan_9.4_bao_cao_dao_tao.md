# Kế hoạch triển khai — 9.4. Báo cáo Đào tạo

**Phạm vi:** Báo cáo tỷ lệ hoàn thành theo khóa học và phòng ban · Chi phí đào tạo · Danh sách NV chưa hoàn thành khóa bắt buộc · Xuất Excel 3 sheet  
**Phụ thuộc:** `9.1 Khóa đào tạo` ✅ · `9.2 Hồ sơ đào tạo` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §9.4

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `training_courses` table | ✅ Hoàn thành (9.1) | Có `is_mandatory`, `cost_per_person` |
| `employee_training_records` table | ✅ Hoàn thành (9.2) | Có `status`, `start_date`, `end_date`, `score` |
| `employee_certificates` table | ✅ Hoàn thành (9.3) | |
| API báo cáo đào tạo | ❌ Chưa có | |
| Tab Báo cáo trong `TrainingView.vue` | ❌ Chưa có (placeholder) | |

---

## Phạm vi

Theo FEATURES.md §9.4:
> Báo cáo tỷ lệ hoàn thành theo khóa học, phòng ban  
> Chi phí đào tạo theo kỳ  
> Danh sách nhân viên chưa hoàn thành đào tạo bắt buộc

**Trong phạm vi:**
- API tổng hợp: thống kê `by_course` và `by_department` trong khoảng thời gian
- Tính chi phí ước tính: `SUM(course.cost_per_person)` cho các lượt hoàn thành
- Danh sách NV chưa hoàn thành ít nhất một khóa bắt buộc (`is_mandatory=true`)
- Xuất Excel 3 sheet (tổng hợp theo khóa, chi tiết, NV chưa HT bắt buộc)

**Ngoài phạm vi:**
- Biểu đồ (Chart) — thuộc module 11 Dashboard
- Báo cáo chi tiết ngân sách thực chi (chỉ ước tính theo cost_per_person)
- Phê duyệt, workflow báo cáo

**Không tạo bảng mới** — tất cả tính từ:
- `employee_training_records` + `training_courses` + `employees` + `departments`

---

## Thiết kế API

### Endpoints

```
GET /training/report/summary
    ?from_date=&to_date=&department_id=&course_id=
    → TrainingReportSummary

GET /training/report/incomplete-mandatory
    ?department_id=
    → list[IncompleteMandatoryEmployee]

GET /training/report/export
    ?from_date=&to_date=&department_id=&course_id=
    → StreamingResponse (.xlsx)
    Content-Disposition: attachment; filename="bao_cao_dao_tao_{from}_{to}.xlsx"
```

### Query parameters chi tiết

| Param | Áp dụng | Kiểu | Mô tả |
|---|---|---|---|
| `from_date` | summary, export | date, required | Lọc `end_date >= from_date` (hoàn thành) hoặc `start_date >= from_date` (đang học) |
| `to_date` | summary, export | date, required | Lọc `end_date <= to_date` hoặc `start_date <= to_date` |
| `department_id` | tất cả | int, optional | Lọc theo phòng ban nhân viên |
| `course_id` | summary, export | int, optional | Lọc theo khóa học cụ thể |

### Permissions

| Endpoint | Permission |
|---|---|
| Tất cả báo cáo | `training:view` |
| Export Excel | `training:view` |

---

## Schemas

### Các schema thống kê

```python
class CourseCompletionStat(BaseModel):
    course_id: int
    course_name: str
    course_type_label: str          # label tiếng Việt của course_type enum
    total_assigned: int             # tổng lượt NV được gán trong kỳ
    completed: int                  # status = "hoan_thanh"
    not_completed: int              # status = "khong_hoan_thanh" | "vang_mat"
    in_progress: int                # status = "chua_bat_dau" | "dang_hoc"
    completion_rate: float          # completed / total_assigned * 100, làm tròn 1 chữ số thập phân


class DepartmentTrainingStat(BaseModel):
    department_id: int | None
    department_name: str | None     # None = NV chưa phân phòng ban
    total_records: int
    completed: int
    completion_rate: float
    total_cost: Decimal | None      # SUM(course.cost_per_person) cho các record "hoan_thanh"


class TrainingReportSummary(BaseModel):
    from_date: date
    to_date: date
    department_id: int | None
    department_name: str | None
    course_id: int | None
    course_name: str | None
    total_records: int              # tổng lượt đào tạo trong kỳ
    total_completed: int
    total_not_completed: int
    total_in_progress: int
    total_cost: Decimal             # tổng chi phí ước tính (completed records)
    avg_completion_rate: float      # trung bình completion_rate của các khóa
    by_course: list[CourseCompletionStat]
    by_department: list[DepartmentTrainingStat]


class IncompleteMandatoryEmployee(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    incomplete_courses: list[str]   # tên các khóa bắt buộc chưa hoàn thành
    incomplete_count: int
```

---

## Service logic

### `training_report_service.py`

**`get_training_report_summary(session, *, from_date, to_date, department_id, course_id)`:**

1. **Base query** records trong kỳ:
   ```sql
   SELECT etr.*, tc.name AS course_name, tc.course_type, tc.cost_per_person, tc.is_mandatory,
          e.employee_code, e.full_name, d.id AS dept_id, d.name AS dept_name
   FROM employee_training_records etr
   JOIN training_courses tc ON etr.course_id = tc.id
   JOIN employees e ON etr.employee_id = e.id
   LEFT JOIN departments d ON e.department_id = d.id
   WHERE (etr.end_date BETWEEN :from_date AND :to_date
          OR (etr.end_date IS NULL AND etr.start_date BETWEEN :from_date AND :to_date))
   ```
   - Apply `department_id` filter nếu có: `AND e.department_id = :department_id`
   - Apply `course_id` filter nếu có: `AND etr.course_id = :course_id`

2. **Group by course** → `list[CourseCompletionStat]`:
   - Với mỗi `course_id` duy nhất: đếm `total_assigned`, `completed` (status="hoan_thanh"), `not_completed` (status IN ("khong_hoan_thanh","vang_mat")), `in_progress` (còn lại)
   - `completion_rate = round(completed / total_assigned * 100, 1)` nếu `total_assigned > 0` else `0.0`

3. **Group by department** → `list[DepartmentTrainingStat]`:
   - Với mỗi `department_id` duy nhất: đếm `total_records`, `completed`
   - `total_cost = SUM(cost_per_person)` chỉ cho các record `status="hoan_thanh"` và `cost_per_person IS NOT NULL`
   - `completion_rate = round(completed / total_records * 100, 1)` nếu `total_records > 0` else `0.0`

4. **Tổng hợp** `TrainingReportSummary`:
   - `total_records = len(all_records)`
   - `total_completed = sum(completed per course)`
   - `total_cost = sum(cost_per_person for completed records)`
   - `avg_completion_rate = round(mean([s.completion_rate for s in by_course]), 1)` nếu `by_course` không rỗng else `0.0`
   - Gắn `department_name` nếu filter `department_id` có giá trị (query departments)

5. **Kỳ không có dữ liệu**: trả `TrainingReportSummary` với tất cả count = 0, `total_cost = Decimal("0")`, `by_course = []`, `by_department = []`

---

**`get_incomplete_mandatory_employees(session, *, department_id)`:**

1. Lấy tất cả `training_courses WHERE is_mandatory = true` → `mandatory_courses: list[(id, name)]`
2. Nếu không có khóa bắt buộc nào: trả `[]`
3. Lấy tất cả nhân viên active (`status="active"`), filter `department_id` nếu có
4. Với mỗi nhân viên: tìm các `course_id` mà nhân viên đó CÓ record `status = "hoan_thanh"` → `completed_course_ids: set[int]`
   - Query: `SELECT DISTINCT course_id FROM employee_training_records WHERE employee_id = :eid AND status = 'hoan_thanh'`
5. `incomplete_courses = [name for (id, name) in mandatory_courses if id NOT IN completed_course_ids]`
6. Chỉ include nhân viên có `len(incomplete_courses) > 0`
7. Sắp xếp theo `incomplete_count DESC`, rồi `employee_code ASC`

> **Tối ưu:** Thay vì N+1 queries, dùng 1 query tổng hợp:
> ```sql
> SELECT etr.employee_id, etr.course_id
> FROM employee_training_records etr
> WHERE etr.course_id IN :mandatory_course_ids
>   AND etr.status = 'hoan_thanh'
> ```
> Sau đó build `completed_map: dict[employee_id, set[course_id]]` trong Python.

---

### `training_export_service.py`

**`export_training_excel(session, *, from_date, to_date, department_id, course_id)`:**

**Tên file:** `bao_cao_dao_tao_{from_date}_{to_date}.xlsx`

**Sheet 1: "Tổng hợp theo khóa học"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged A1:G1, bold, font 14)
Hàng 2: [BÁO CÁO ĐÀO TẠO {DD/MM/YYYY} – {DD/MM/YYYY}] (merged A2:G2, bold, font 12)
Hàng 3: trống
Hàng 4: Header cột
  A: STT
  B: Tên khóa học
  C: Loại
  D: Tổng NV
  E: Hoàn thành
  F: Chưa hoàn thành
  G: Tỷ lệ HT (%)
Hàng 5+: Dữ liệu từ by_course
Hàng cuối: TỔNG CỘNG (bold, cột D=total_assigned, E=completed, F=not_completed, G=avg_rate)
```

**Sheet 2: "Chi tiết đào tạo"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged, bold, font 14)
Hàng 2: [CHI TIẾT ĐÀO TẠO {DD/MM/YYYY} – {DD/MM/YYYY}] (merged, bold, font 12)
Hàng 3: trống
Hàng 4: Header cột
  A: STT
  B: Mã NV
  C: Họ và tên
  D: Phòng ban
  E: Khóa học
  F: Loại
  G: Trạng thái
  H: Kết quả
  I: Điểm
  J: Ngày bắt đầu
  K: Ngày kết thúc
Hàng 5+: Dữ liệu từng record chi tiết (JOIN như summary query)
Hàng cuối: TỔNG CỘNG (chỉ bold, không sum — vì có text)
```

**Sheet 3: "NV chưa HT bắt buộc"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged, bold, font 14)
Hàng 2: [DANH SÁCH NHÂN VIÊN CHƯA HOÀN THÀNH ĐÀO TẠO BẮT BUỘC] (merged, bold, font 12)
Hàng 3: trống
Hàng 4: Header cột
  A: STT
  B: Mã NV
  C: Họ và tên
  D: Phòng ban
  E: Số khóa chưa HT
  F: Danh sách khóa chưa HT
Hàng 5+: Dữ liệu từ get_incomplete_mandatory_employees() (không filter ngày)
Hàng cuối: TỔNG CỘNG (bold, ghi số NV)
```

**Định dạng chung (giống plan 8.3):**
- Header hàng 4: nền `#1F4E79`, chữ trắng, bold
- Dòng xen kẽ: `#F2F2F2` / trắng
- Dòng tổng cuối: `#D9E1F2`, bold
- Cột tỷ lệ (%): format `0.0"%"`
- Cột điểm (số thực): format `0.0`
- Cột ngày: format `DD/MM/YYYY`
- Auto column width: estimate từ max content length
- Freeze pane ở hàng 5 (sau header)

---

## Thiết kế Frontend

### Tab "Báo cáo" trong `TrainingView.vue`

Thêm tab "Báo cáo" vào `TabView` hiện có, render component `TrainingReportTab.vue`.

### `TrainingReportTab.vue`

**Bộ lọc (Filters section):**
- DatePicker: Từ ngày (required, default: đầu năm hiện tại)
- DatePicker: Đến ngày (required, default: hôm nay)
- Select (filter prop): Phòng ban — "Tất cả" + danh sách phòng ban
- Select (filter prop): Khóa học — "Tất cả" + danh sách courses
- Button: "Xem báo cáo" (severity: primary) → gọi `fetchReport()`
- Button: "Xuất Excel" (severity: secondary, icon: download) → gọi `exportExcel()`

**Summary Cards (hiển thị sau khi fetch):**

| Card | Nội dung |
|---|---|
| Card 1 | Tổng lượt đào tạo: `total_records` |
| Card 2 | Hoàn thành: `total_completed` |
| Card 3 | Tổng chi phí ước tính: `total_cost` (format VND) |
| Card 4 | Tỷ lệ HT TB: `avg_completion_rate`% |

**Bảng "Theo khóa học":**

DataTable với cột: Tên khóa, Loại, Tổng NV, Hoàn thành, Chưa HT, Đang học, Tỷ lệ HT (%)
- Cột "Tỷ lệ HT": hiển thị kèm ProgressBar mini hoặc text `XX.X%`
- Sắp xếp mặc định: `completion_rate DESC`

**Bảng "Theo phòng ban":**

DataTable với cột: Phòng ban, Tổng lượt, Hoàn thành, Tỷ lệ HT (%), Chi phí ước tính
- Cột "Chi phí ước tính": format VND, hiển thị "—" nếu null

**Sub-tab "NV chưa HT bắt buộc":**
- Nút riêng "Xem danh sách" (không phụ thuộc date filter, chỉ dùng `department_id`)
- DataTable: Mã NV, Họ và tên, Phòng ban, Số khóa chưa HT, Danh sách khóa (text, xuống dòng)
- Select (filter): Phòng ban — lọc riêng cho sub-tab này
- Sắp xếp mặc định: `incomplete_count DESC`

**Loading states:**
- Skeleton cards khi đang fetch summary
- DataTable loading spinner
- Button "Xuất Excel" disabled + icon spinner khi đang export

**Empty states:**
- Khi chưa bấm "Xem báo cáo": hiển thị placeholder "Chọn khoảng thời gian và bấm Xem báo cáo"
- Khi không có dữ liệu trong kỳ: hiển thị "Không có dữ liệu đào tạo trong khoảng thời gian này"

---

## Cấu trúc file mới / thay đổi

```
backend/
  app/schemas/training_report.py                          (NEW)
  app/services/training_report_service.py                 (NEW)
  app/services/training_export_service.py                 (NEW)
  app/api/v1/endpoints/training.py                        (EDIT: thêm 3 report endpoints)
  tests/test_training_report.py                           (NEW)

frontend/
  src/services/trainingReportService.ts                   (NEW)
  src/views/training/components/TrainingReportTab.vue     (NEW)
  src/views/training/TrainingView.vue                     (EDIT: thêm tab "Báo cáo")
  src/assets/styles/views/_training.scss                  (EDIT: thêm report styles)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: API Báo cáo tổng hợp

**Tasks:**
1. Tạo `app/schemas/training_report.py`:
   - `CourseCompletionStat`
   - `DepartmentTrainingStat`
   - `TrainingReportSummary`
2. Tạo `app/services/training_report_service.py`:
   - `get_training_report_summary(session, *, from_date, to_date, department_id, course_id)`
   - Logic group by course, group by department, tính total_cost, avg_completion_rate
   - Xử lý empty period (trả zeros)
3. Thêm endpoint vào `training.py`:
   - `GET /training/report/summary` (require `training:view`)
   - Query params: `from_date`, `to_date`, `department_id`, `course_id`

**Exit criteria:**
- API trả đúng `total_records`, `total_completed`, `total_cost`
- `by_course` group đúng số lượng per course_id
- `by_department` group đúng per department
- `completion_rate` tính đúng: 5 completed / 10 total = 50.0
- `avg_completion_rate` là trung bình của các course rates
- `total_cost` chỉ tính cho `status = "hoan_thanh"`
- Filter `department_id` loại đúng NV ngoài phòng ban
- Filter `course_id` chỉ trả dữ liệu khóa đó
- Khoảng thời gian không có dữ liệu: trả summary với tất cả count = 0, list rỗng

---

### Slice 2 — Backend: Incomplete Mandatory + Export Excel

**Tasks:**
1. Thêm `IncompleteMandatoryEmployee` vào `training_report.py`
2. Thêm vào `training_report_service.py`:
   - `get_incomplete_mandatory_employees(session, *, department_id)` với tối ưu N+1
3. Thêm endpoint:
   - `GET /training/report/incomplete-mandatory` (require `training:view`)
4. Tạo `app/services/training_export_service.py`:
   - `export_training_excel(session, *, from_date, to_date, department_id, course_id) → bytes`
   - 3 sheets: "Tổng hợp theo khóa học", "Chi tiết đào tạo", "NV chưa HT bắt buộc"
   - Định dạng header `#1F4E79`, xen kẽ `#F2F2F2`, total row `#D9E1F2`
5. Thêm endpoint:
   - `GET /training/report/export` (require `training:view`) → `StreamingResponse`

**Exit criteria:**
- `GET /training/report/incomplete-mandatory`: NV có record `hoan_thanh` cho khóa bắt buộc → không xuất hiện trong list
- NV không có record nào cho khóa bắt buộc → xuất hiện với đúng `incomplete_courses`
- NV có record nhưng `status != "hoan_thanh"` → vẫn bị tính là chưa HT
- Filter `department_id` cho incomplete-mandatory hoạt động
- Không có khóa bắt buộc nào trong hệ thống → trả `[]`
- `GET /training/report/export`: HTTP 200, `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- File Excel hợp lệ (openpyxl có thể mở), có đúng 3 sheets với tên đúng
- Sheet 1 có `completion_rate` đúng format
- Sheet 3 có đúng danh sách NV chưa HT

---

### Slice 3 — Frontend

**Tasks:**
1. Tạo `src/services/trainingReportService.ts`:
   - Types: `CourseCompletionStat`, `DepartmentTrainingStat`, `TrainingReportSummary`, `IncompleteMandatoryEmployee`
   - `getTrainingReportSummary(params)` → GET /training/report/summary
   - `getIncompleteMandatoryEmployees(params)` → GET /training/report/incomplete-mandatory
   - `exportTrainingExcel(params)` → GET /training/report/export, trigger browser download
2. Tạo `src/views/training/components/TrainingReportTab.vue`:
   - Filters section (from_date, to_date, dept, course, buttons)
   - Summary cards (4 cards)
   - DataTable "Theo khóa học"
   - DataTable "Theo phòng ban"
   - Sub-tab "NV chưa HT bắt buộc" với filter dept riêng
   - Loading + empty states
3. Edit `TrainingView.vue`: thêm TabPanel "Báo cáo" → `<TrainingReportTab />`
4. Edit `_training.scss`: thêm style summary cards, report section (dùng PrimeVue utilities, không viết scoped CSS)

**Exit criteria:**
- Tab "Báo cáo" xuất hiện trong TrainingView
- Bấm "Xem báo cáo": summary cards cập nhật đúng số liệu
- DataTable "Theo khóa học" render đúng cột, đúng dữ liệu
- DataTable "Theo phòng ban" render đúng, cột chi phí format VND
- Sub-tab "NV chưa HT bắt buộc" tải đúng danh sách
- Filter phòng ban của sub-tab hoạt động độc lập với filter chính
- Bấm "Xuất Excel": trình duyệt tải file `.xlsx`
- Empty state hiển thị đúng khi không có dữ liệu
- Loading state hiển thị khi đang fetch

---

### Slice 4 — Tests

**Tasks:**

Tạo `tests/test_training_report.py`:

```
TestTrainingReportSummary:
  - test_empty_period_returns_zeros
    → from_date = to_date = today, không có records → all counts = 0, lists empty
  - test_total_records_count_in_range
    → 3 records trong kỳ, 1 ngoài kỳ → total_records = 3
  - test_excludes_records_out_of_range
    → record có end_date trước from_date không được tính
  - test_by_course_groups_correctly
    → 2 courses, mỗi course 3 records → by_course có 2 entries, counts đúng
  - test_completion_rate_calculation
    → 4 hoan_thanh / 5 total → completion_rate = 80.0
  - test_by_department_groups_correctly
    → 2 phòng ban, records phân bố đều → by_department có 2 entries
  - test_total_cost_only_counts_completed
    → 3 hoan_thanh (cost=100) + 2 khong_hoan_thanh → total_cost = 300
  - test_cost_null_when_no_cost_per_person
    → course.cost_per_person = null → department_cost = null
  - test_avg_completion_rate_is_mean_of_courses
    → course A: 100%, course B: 0% → avg = 50.0
  - test_filter_by_department_id
    → 2 phòng ban, filter dept A → chỉ trả records của dept A
  - test_filter_by_course_id
    → 3 courses, filter course 2 → chỉ trả records của course 2

TestIncompleteMandatory:
  - test_employee_with_no_record_is_incomplete
    → NV chưa có record cho khóa bắt buộc → xuất hiện trong list
  - test_employee_with_completed_record_is_excluded
    → NV có record status="hoan_thanh" → không xuất hiện
  - test_employee_with_non_completed_record_is_incomplete
    → NV có record status="dang_hoc" cho khóa bắt buộc → vẫn là incomplete
  - test_incomplete_courses_list_correct
    → NV chưa HT 2 khóa bắt buộc → incomplete_courses có đúng 2 tên khóa
  - test_filter_by_department_id
    → 2 phòng ban, filter dept A → chỉ trả NV của dept A
  - test_no_mandatory_courses_returns_empty
    → không có khóa is_mandatory=true → trả []
  - test_inactive_employees_excluded
    → NV có status!="active" không xuất hiện dù chưa HT

TestTrainingExport:
  - test_export_returns_xlsx_content_type
    → response Content-Type = application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  - test_export_valid_xlsx_file
    → openpyxl.load_workbook(BytesIO(content)) không raise exception
  - test_export_has_three_sheets
    → wb.sheetnames có đúng 3 tên: "Tổng hợp theo khóa học", "Chi tiết đào tạo", "NV chưa HT bắt buộc"
  - test_sheet1_row_count_matches_courses
    → 3 courses → sheet1 có 3 data rows (+ 4 header rows + 1 total row = 8 rows)
  - test_sheet2_row_count_matches_records
    → 5 records → sheet2 có 5 data rows
  - test_sheet3_row_count_matches_incomplete
    → 2 NV chưa HT bắt buộc → sheet3 có 2 data rows
```

**Exit criteria:**
- Tất cả test pass: `docker exec hrms-backend-1 pytest tests/test_training_report.py -v`
- Coverage: empty period, N+1 tối ưu verify qua query count, xlsx structure
- Không có regression trên `tests/test_training_records.py` và `tests/test_training_courses.py`

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| N+1 queries khi tính incomplete_mandatory với nhiều NV | Cao | Dùng 1 query tổng hợp + build dict trong Python (xem mục service logic) |
| `end_date IS NULL` cho records `dang_hoc` không lọc được theo `to_date` | Trung bình | Fallback dùng `start_date` khi `end_date IS NULL` trong WHERE clause |
| `cost_per_person` NULL cho một số khóa → `total_cost` không chính xác | Thấp | Dùng `COALESCE(cost_per_person, 0)` hoặc để NULL, ghi rõ "ước tính" trên UI |
| Excel 3 sheets với nhiều records (>1000) → chậm | Trung bình | Dùng openpyxl `write_only=True` mode cho sheet chi tiết |
| `avg_completion_rate` bị lệch khi có khóa 0 NV | Thấp | Chỉ tính average từ các course có `total_assigned > 0` |
| Khóa bắt buộc mới thêm → toàn bộ NV cũ thành incomplete | Trung bình | Đây là behavior đúng — document rõ trong UI: "Dựa trên trạng thái hiện tại của danh sách khóa bắt buộc" |
| `department_id` filter cho incomplete-mandatory độc lập với date filter | Thấp | Thiết kế API đúng từ đầu: `/incomplete-mandatory?department_id=` không nhận `from_date/to_date` |
