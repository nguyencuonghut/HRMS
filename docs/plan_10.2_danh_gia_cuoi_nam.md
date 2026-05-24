# Kế hoạch triển khai — 10.2. Đánh giá Cuối năm

**Phạm vi:** Tổng hợp điểm KPI trung bình theo năm · Xếp loại tự động · Nhận xét đánh giá cuối năm  
**Phụ thuộc:** `10.1 KPI Tháng` ✅ (`employee_kpi_monthly`)  
**Căn cứ nghiệp vụ:** FEATURES.md §10.2

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_kpi_monthly` table | ✅ Hoàn thành (10.1) | Nguồn tính điểm trung bình |
| `employee_yearly_reviews` table | ❌ Chưa có | Lưu nhận xét + xếp loại cuối năm |
| API tổng hợp điểm cuối năm | ❌ Chưa có | |
| Tab "Đánh giá Cuối năm" trong `PerformanceView.vue` | ❌ Chưa có (placeholder) | |

---

## Phạm vi

Theo FEATURES.md §10.2:
> Điểm KPI trung bình tự động tính từ các tháng đã nhập trong năm  
> Xếp loại tự động theo điểm: Xuất sắc / Tốt / Đạt / Cần cải thiện  
> Nhận xét – đánh giá cuối năm do nhân sự bổ sung

**Trong phạm vi:**
- Tính `avg_score` theo năm từ bảng `employee_kpi_monthly` (on-the-fly hoặc lưu denorm khi chốt)
- Xếp loại tự động từ `avg_score` theo ngưỡng cấu hình
- Nhân sự có thể bổ sung nhận xét cho từng NV từng năm
- Danh sách đánh giá cuối năm: filter theo năm, phòng ban, xếp loại

**Ngưỡng xếp loại mặc định (có thể cấu hình):**
| Điểm avg | Xếp loại |
|---|---|
| ≥ 90 | Xuất sắc (`xuat_sac`) |
| ≥ 75 | Tốt (`tot`) |
| ≥ 60 | Đạt (`dat`) |
| < 60 | Cần cải thiện (`can_cai_thien`) |

**Ngoài phạm vi:**
- Quy trình phê duyệt đánh giá đa cấp
- Tự đánh giá bởi nhân viên
- Liên kết khen thưởng / đào tạo (thuộc 10.3)

---

## Thiết kế data model

### Bảng `employee_yearly_reviews`

Lưu nhận xét và xếp loại đã được nhân sự xác nhận cuối năm.  
Điểm `avg_score` được tính lại on-the-fly từ `employee_kpi_monthly`; bảng này chỉ lưu `review_note` và `rating`.

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `employee_id` | INTEGER | FK employees(id) CASCADE NOT NULL | |
| `year` | SMALLINT | NOT NULL | Năm đánh giá |
| `rating` | VARCHAR(20) | NOT NULL | `xuat_sac` / `tot` / `dat` / `can_cai_thien` |
| `review_note` | TEXT | nullable | Nhận xét đánh giá cuối năm |
| `created_by_id` | INTEGER | FK users(id) SET NULL, nullable | Người tạo / lưu |
| `created_at` | TIMESTAMP | NOT NULL, default now() | |
| `updated_at` | TIMESTAMP | NOT NULL, default now() | |

**Unique constraint:** `uq_employee_yearly_review_year` trên `(employee_id, year)`

**Indexes:**
- `ix_employee_yearly_reviews_employee_id` trên `(employee_id)`
- `ix_employee_yearly_reviews_year` trên `(year)`

**Migration file:** `alembic/versions/0031_create_employee_yearly_reviews.py`

> **Thiết kế lựa chọn:** `avg_score` KHÔNG lưu vào DB. Tính on-the-fly khi query để đảm bảo luôn phản ánh đúng dữ liệu KPI tháng (kể cả khi có sửa/xóa sau). `rating` lưu để ghi nhận quyết định của nhân sự (có thể khác với tính tự động nếu nhân sự override).

---

## Thiết kế API

### Endpoints

```
GET    /performance/yearly-reviews
       ?year=&department_id=&rating=&search=&page=1&page_size=20
       → YearlyReviewListPage

GET    /performance/yearly-reviews/{id}
       → YearlyReviewRead

POST   /performance/yearly-reviews
       body: YearlyReviewCreate (JSON)
       → YearlyReviewRead

PUT    /performance/yearly-reviews/{id}
       body: YearlyReviewUpdate (JSON)
       → YearlyReviewRead

DELETE /performance/yearly-reviews/{id}
       → 204 No Content

# Xem tổng hợp điểm KPI năm của một nhân viên (on-the-fly)
GET    /performance/yearly-summary/{employee_id}
       ?year=
       → YearlyKpiSummary
```

### Query parameters — danh sách

| Param | Kiểu | Mô tả |
|---|---|---|
| `year` | int, optional | Lọc theo năm |
| `department_id` | int, optional | Lọc theo phòng ban |
| `rating` | str, optional | `xuat_sac` / `tot` / `dat` / `can_cai_thien` |
| `search` | str, optional | Tìm theo tên NV, mã NV |
| `page` | int, default=1 | |
| `page_size` | int, default=20 | |

### Permissions

| Endpoint | Permission |
|---|---|
| GET list / GET by id / GET yearly-summary | `performance:view` |
| POST / PUT / DELETE | `performance:manage_kpi` |

---

## Schemas

### `YearlyKpiSummary` (on-the-fly, không lưu DB)

```python
class MonthlyScore(BaseModel):
    month: int
    score: Decimal

class YearlyKpiSummary(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    year: int
    monthly_scores: list[MonthlyScore]   # các tháng đã có KPI
    months_count: int                    # số tháng đã nhập
    avg_score: Decimal | None            # None nếu chưa có tháng nào
    suggested_rating: str | None         # xếp loại gợi ý từ avg_score
    has_review: bool                     # đã lưu đánh giá cuối năm chưa
    review_id: int | None
```

### `YearlyReviewRead`

```python
class YearlyReviewRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    year: int
    # Computed from employee_kpi_monthly (on-the-fly)
    months_count: int
    avg_score: Decimal | None
    # Stored
    rating: str
    rating_label: str       # "Xuất sắc" / "Tốt" / "Đạt" / "Cần cải thiện"
    review_note: str | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime
```

### `YearlyReviewCreate`

```python
class YearlyReviewCreate(BaseModel):
    employee_id: int
    year: int               = Field(ge=2000, le=2100)
    rating: RatingValue     # Literal["xuat_sac","tot","dat","can_cai_thien"]
    review_note: str | None = None
```

### `YearlyReviewUpdate`

```python
class YearlyReviewUpdate(BaseModel):
    rating: RatingValue | None = None
    review_note: str | None = None
```

### `YearlyReviewListPage`

```python
class YearlyReviewListPage(BaseModel):
    items: list[YearlyReviewRead]
    total: int
    page: int
    page_size: int
```

### Logic xếp loại tự động

```python
RATING_THRESHOLDS = [
    (90, "xuat_sac"),
    (75, "tot"),
    (60, "dat"),
    (0,  "can_cai_thien"),
]

RATING_LABELS = {
    "xuat_sac":       "Xuất sắc",
    "tot":            "Tốt",
    "dat":            "Đạt",
    "can_cai_thien":  "Cần cải thiện",
}

def compute_rating(avg_score: Decimal | None) -> str | None:
    if avg_score is None:
        return None
    for threshold, rating in RATING_THRESHOLDS:
        if avg_score >= threshold:
            return rating
    return "can_cai_thien"
```

---

## Service logic

### `yearly_review_service.py`

**`get_avg_score(session, employee_id, year) → Decimal | None`:**
```sql
SELECT AVG(score) FROM employee_kpi_monthly
WHERE employee_id = :eid AND year = :year
```
Trả `None` nếu không có tháng nào.

**`get_yearly_kpi_summary(session, employee_id, year) → YearlyKpiSummary`:**
1. Query tất cả rows `employee_kpi_monthly WHERE employee_id=:eid AND year=:year`
2. Tính `avg_score = sum(scores) / count`
3. Gọi `compute_rating(avg_score)` → `suggested_rating`
4. Kiểm tra `employee_yearly_reviews` có bản ghi `(employee_id, year)` không
5. Trả `YearlyKpiSummary`

**`get_yearly_reviews(session, *, year, department_id, rating, search, page, page_size)`:**
1. JOIN `employee_yearly_reviews` + `employees` + `departments`
2. Apply filters
3. Với mỗi row: tính thêm `avg_score` và `months_count` từ `employee_kpi_monthly` (subquery hoặc after fetch)
4. Trả `YearlyReviewListPage`

**`create_review(session, data, created_by_id)`:**
1. Kiểm tra `employee_id` tồn tại
2. Kiểm tra unique `(employee_id, year)` — HTTP 409 nếu trùng
3. INSERT, trả `YearlyReviewRead` (kèm avg_score tính on-the-fly)

**`update_review(session, id, data)`:**
1. `_get_or_404(id)`
2. Apply `rating`, `review_note` nếu có
3. UPDATE, trả `YearlyReviewRead`

**`delete_review(session, id)`:**
1. `_get_or_404(id)`, DELETE (xóa nhận xét, không ảnh hưởng KPI tháng)

---

## Thiết kế Frontend

### `YearlyReviewTab.vue`

**Toolbar:**
- Select (filter): Năm
- Select (filter): Phòng ban
- Select (filter): Xếp loại — "Tất cả" / Xuất sắc / Tốt / Đạt / Cần cải thiện
- InputText: Tìm kiếm
- Button: "Lưu đánh giá" (icon: plus) → mở dialog

**DataTable:**

| Cột | Nội dung |
|---|---|
| Mã NV | `employee_code` |
| Họ và tên | `employee_name` |
| Phòng ban | `department_name` |
| Năm | `year` |
| Số tháng có KPI | `months_count` / 12 |
| Điểm TB | `avg_score` (1 chữ số thập phân, "—" nếu null) |
| Xếp loại | Tag màu theo `rating` |
| Nhận xét | `review_note` (truncate 60 ký tự) |
| Thao tác | Button edit, Button delete |

**Màu Tag `rating`:**

| Giá trị | Severity PrimeVue | Label |
|---|---|---|
| `xuat_sac` | `success` | Xuất sắc |
| `tot` | `info` | Tốt |
| `dat` | `secondary` | Đạt |
| `can_cai_thien` | `warn` | Cần cải thiện |

**Dialog "Lưu đánh giá cuối năm":**
- Select (filter): Nhân viên — `{employee_code} - {employee_name}` (disabled khi sửa)
- InputNumber: Năm (disabled khi sửa)
- Hiển thị read-only: Điểm TB — tự động load khi chọn NV + năm (gọi `GET /performance/yearly-summary/{employee_id}?year=`)
- Hiển thị read-only: Xếp loại gợi ý — tính từ `suggested_rating`
- Select: Xếp loại (required) — pre-fill từ `suggested_rating`, nhân sự có thể thay đổi
- Textarea: Nhận xét (optional)

**UX lưu ý:**
- Khi chọn NV + năm trong dialog: auto-fetch summary để hiển thị điểm TB và xếp loại gợi ý
- Nếu chưa có KPI tháng nào: hiển thị "Chưa có dữ liệu KPI tháng cho năm này"

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0031_create_employee_yearly_reviews.py   (NEW)
  app/models/performance.py                                  (EDIT: thêm EmployeeYearlyReview)
  app/schemas/performance.py                                 (EDIT: thêm Yearly schemas)
  app/services/yearly_review_service.py                      (NEW)
  app/api/v1/endpoints/performance.py                        (EDIT: thêm yearly-review endpoints)
  tests/test_yearly_reviews.py                               (NEW)

frontend/
  src/services/performanceService.ts                         (EDIT: thêm yearly review types + API)
  src/views/performance/components/YearlyReviewTab.vue       (NEW)
  src/views/performance/PerformanceView.vue                  (EDIT: activate tab 10.2)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: API Đánh giá cuối năm

**Tasks:**
1. Migration `0031_create_employee_yearly_reviews.py`
2. Model `EmployeeYearlyReview` trong `performance.py`
3. Schemas: `YearlyKpiSummary`, `MonthlyScore`, `YearlyReviewRead/Create/Update`, `YearlyReviewListPage`
4. Constants `RATING_THRESHOLDS`, `RATING_LABELS`, hàm `compute_rating()`
5. Service `yearly_review_service.py`
6. Endpoints trong `performance.py`

**Exit criteria:**
- `GET /performance/yearly-summary/{emp_id}?year=2026` trả đúng avg_score và suggested_rating
- avg_score = AVG của các tháng có dữ liệu (không phải chia 12)
- `POST /performance/yearly-reviews` lưu thành công, kèm avg_score on-the-fly
- Duplicate `(employee_id, year)` → HTTP 409
- `GET list` filter rating, department, year đúng

---

### Slice 2 — Frontend

**Tasks:**
1. Thêm types + API calls vào `performanceService.ts`
2. Tạo `YearlyReviewTab.vue`
3. Activate tab trong `PerformanceView.vue`

**Exit criteria:**
- DataTable hiển thị đúng cột, filter hoạt động
- Dialog: chọn NV + năm → auto-load điểm TB và xếp loại gợi ý
- Lưu / sửa / xóa đánh giá hoạt động

---

### Slice 3 — Tests

Tạo `tests/test_yearly_reviews.py`:

```
TestYearlySummary:
  - test_avg_score_calculated_from_monthly_kpi
  - test_avg_score_none_when_no_kpi
  - test_suggested_rating_xuat_sac          (avg >= 90)
  - test_suggested_rating_tot               (avg 75–89)
  - test_suggested_rating_dat               (avg 60–74)
  - test_suggested_rating_can_cai_thien     (avg < 60)
  - test_months_count_correct

TestYearlyReviewCRUD:
  - test_create_review_success
  - test_create_review_duplicate_returns_409
  - test_update_review_rating_and_note
  - test_delete_review
  - test_review_read_includes_avg_score     (avg tính on-the-fly)

TestYearlyReviewList:
  - test_filter_by_year
  - test_filter_by_rating
  - test_filter_by_department
  - test_search_by_employee_name
```

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| avg_score tính on-the-fly → N+1 khi load danh sách nhiều NV | Trung bình | Dùng subquery `AVG(score)` trong cùng 1 query JOIN thay vì fetch riêng từng NV |
| Nhân sự xóa KPI tháng sau khi đã lưu đánh giá → avg_score thay đổi | Thấp | avg_score luôn tính on-the-fly; hiển thị cảnh báo "Điểm TB đã thay đổi" nếu avg != rating ngưỡng |
| Ngưỡng xếp loại thay đổi theo chính sách công ty | Trung bình | Đặt hằng số `RATING_THRESHOLDS` ở 1 nơi duy nhất trong service, dễ sửa |
| `rating` do nhân sự override khác `suggested_rating` | Thấp | Cho phép override — lưu `rating` riêng, hiển thị cả `suggested_rating` để tham khảo |
