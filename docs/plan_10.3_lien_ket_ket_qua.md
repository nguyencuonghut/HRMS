# Kế hoạch triển khai — 10.3. Liên kết Kết quả Đánh giá

**Phạm vi:** Kết nối kết quả KPI với quyết định khen thưởng · Đề xuất kế hoạch đào tạo · Lịch sử đánh giá trong hồ sơ nhân viên  
**Phụ thuộc:** `10.2 Đánh giá Cuối năm` ✅ (`employee_yearly_reviews`) · `8.1 Khen thưởng` ✅ · `9.1–9.2 Đào tạo` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §10.3

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `employee_yearly_reviews` table | ✅ Hoàn thành (10.2) | Nguồn xếp loại |
| `employee_rewards` table | ✅ Hoàn thành (8.1) | Bảng khen thưởng |
| `training_plans` table | ✅ Hoàn thành (9.1) | Kế hoạch đào tạo |
| `employee_training_records` table | ✅ Hoàn thành (9.2) | Hồ sơ đào tạo |
| Tab "Đánh giá" trong hồ sơ nhân viên | ❌ Chưa có | |
| Liên kết khen thưởng từ đánh giá | ❌ Chưa có | |
| Đề xuất đào tạo từ đánh giá | ❌ Chưa có | |

---

## Phạm vi

Theo FEATURES.md §10.3:
> Kết nối kết quả đánh giá với quyết định khen thưởng  
> Kết nối với kế hoạch đào tạo (cải thiện điểm yếu)  
> Lịch sử kết quả đánh giá trong hồ sơ nhân viên

**Trong phạm vi:**

**A. Liên kết khen thưởng:**
- Từ màn hình đánh giá cuối năm: nút "Tạo khen thưởng" → prefill form khen thưởng với thông tin NV + lý do từ kết quả đánh giá
- Thêm cột `source_review_id` vào bảng `employee_rewards` để truy vết nguồn gốc

**B. Liên kết đào tạo:**
- Từ màn hình đánh giá: nút "Đề xuất đào tạo" → gán NV vào training record với note liên kết đánh giá
- Thêm cột `source_review_id` vào bảng `employee_training_records` để truy vết

**C. Lịch sử trong hồ sơ NV:**
- Tab "Đánh giá KPI" trong `EmployeeDetailView.vue` hiển thị toàn bộ lịch sử KPI tháng + đánh giá cuối năm của NV đó
- API: `GET /employees/{id}/performance/kpi` và `GET /employees/{id}/performance/reviews`

**Ngoài phạm vi:**
- Tự động tạo khen thưởng theo rule (thuộc module automation)
- Workflow phê duyệt đề xuất đào tạo
- So sánh đánh giá giữa các nhân viên

---

## Thay đổi data model

### Bổ sung cột vào bảng hiện có

**`employee_rewards` (migration 0032):**

| Cột bổ sung | Kiểu | Mô tả |
|---|---|---|
| `source_review_id` | INTEGER, FK `employee_yearly_reviews(id)` SET NULL | Review nguồn gốc khen thưởng (nullable) |

**`employee_training_records` (migration 0032 chung):**

| Cột bổ sung | Kiểu | Mô tả |
|---|---|---|
| `source_review_id` | INTEGER, FK `employee_yearly_reviews(id)` SET NULL | Review dẫn đến đào tạo (nullable) |

**Migration file:** `alembic/versions/0032_add_source_review_id_to_rewards_training.py`

> Không tạo bảng liên kết riêng — dùng FK trực tiếp trên bảng hiện có để đơn giản, đủ cho nhu cầu truy vết.

---

## Thiết kế API

### Endpoints mới

```
# Lịch sử KPI tháng của một nhân viên
GET  /employees/{employee_id}/performance/kpi
     ?year=
     → list[KpiMonthlyRead]

# Lịch sử đánh giá cuối năm của một nhân viên
GET  /employees/{employee_id}/performance/reviews
     → list[YearlyReviewRead]

# Tạo khen thưởng từ kết quả đánh giá
POST /performance/yearly-reviews/{review_id}/create-reward
     body: RewardFromReviewRequest
     → EmployeeRewardRead   (redirect tới module 8.1)

# Đề xuất đào tạo từ kết quả đánh giá
POST /performance/yearly-reviews/{review_id}/create-training
     body: TrainingFromReviewRequest
     → TrainingRecordRead   (tạo record trong module 9.2)
```

### Schema `RewardFromReviewRequest`

```python
class RewardFromReviewRequest(BaseModel):
    reward_type_id: int         # loại khen thưởng từ catalog 8.1
    amount: Decimal | None = None
    decision_date: date
    note: str | None = None
    # employee_id và lý do được prefill từ review
```

### Schema `TrainingFromReviewRequest`

```python
class TrainingFromReviewRequest(BaseModel):
    course_id: int              # khóa đào tạo từ catalog 9.1
    plan_id: int | None = None  # gắn vào kế hoạch đào tạo nếu có
    note: str | None = None     # prefill: "Cải thiện điểm yếu từ đánh giá năm {year}"
```

### Permissions

| Endpoint | Permission |
|---|---|
| GET employee KPI history / review history | `performance:view` |
| POST create-reward | `performance:manage_kpi` + `rewards:manage` |
| POST create-training | `performance:manage_kpi` + `training:manage_records` |

---

## Service logic

### `link_service.py`

**`get_employee_kpi_history(session, employee_id, year?) → list[KpiMonthlyRead]`:**
- Query `employee_kpi_monthly WHERE employee_id = :eid` (+ filter year nếu có)
- Sort `year DESC, month DESC`

**`get_employee_review_history(session, employee_id) → list[YearlyReviewRead]`:**
- Query `employee_yearly_reviews WHERE employee_id = :eid`
- Sort `year DESC`
- Kèm `avg_score` tính on-the-fly từ `employee_kpi_monthly`

**`create_reward_from_review(session, review_id, data, created_by_id) → EmployeeRewardRead`:**
1. `_get_review_or_404(review_id)`
2. Prefill `employee_id`, `note` từ review
3. Gọi `reward_service.create_reward(...)` với `source_review_id=review_id`
4. Trả `EmployeeRewardRead`

**`create_training_from_review(session, review_id, data, created_by_id) → TrainingRecordRead`:**
1. `_get_review_or_404(review_id)`
2. Prefill `employee_id` từ review
3. Gọi `training_record_service.create_record(...)` với `source_review_id=review_id`
4. Trả `TrainingRecordRead`

---

## Thiết kế Frontend

### Tab "Đánh giá KPI" trong `EmployeeDetailView.vue`

Thêm tab "Đánh giá KPI" vào trang hồ sơ nhân viên (`/employees/{id}`).

**Layout tab:**

**Phần 1 — KPI Tháng:**
- Select năm (filter)
- DataTable: Tháng / Điểm KPI / Ghi chú / Người nhập

**Phần 2 — Đánh giá Cuối năm:**
- DataTable: Năm / Điểm TB / Xếp loại (Tag màu) / Nhận xét / Nguồn khen thưởng / Nguồn đào tạo

### Nút liên kết trong `YearlyReviewTab.vue`

Bổ sung thêm cột "Hành động liên kết" vào DataTable đánh giá:
- Button "Tạo khen thưởng" (icon: trophy) → mở dialog `RewardFromReviewDialog`
- Button "Đề xuất đào tạo" (icon: graduation-cap) → mở dialog `TrainingFromReviewDialog`

**`RewardFromReviewDialog`:**
- Hiển thị read-only: tên NV, năm, xếp loại
- Select (filter): Loại khen thưởng (từ catalog 8.1)
- DatePicker: Ngày quyết định (required)
- InputNumber: Giá trị (optional)
- Textarea: Ghi chú (prefill: "Khen thưởng theo kết quả đánh giá năm {year} — {rating_label}")

**`TrainingFromReviewDialog`:**
- Hiển thị read-only: tên NV, năm, xếp loại
- Select (filter): Khóa đào tạo (từ catalog 9.1)
- Select (filter): Kế hoạch đào tạo (optional, từ 9.1)
- Textarea: Ghi chú (prefill: "Cải thiện điểm yếu từ đánh giá năm {year}")

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0032_add_source_review_id_to_rewards_training.py   (NEW)
  app/models/reward.py                    (EDIT: thêm source_review_id)
  app/models/training.py                  (EDIT: thêm source_review_id vào EmployeeTrainingRecord)
  app/services/link_service.py            (NEW)
  app/api/v1/endpoints/performance.py     (EDIT: thêm link endpoints)
  app/api/v1/router.py                    (EDIT: thêm employee performance sub-routes)
  tests/test_performance_links.py         (NEW)

frontend/
  src/services/performanceService.ts      (EDIT: thêm link API calls)
  src/views/performance/components/YearlyReviewTab.vue   (EDIT: thêm nút liên kết + dialogs)
  src/views/employee/components/KpiHistoryTab.vue        (NEW — tab trong hồ sơ NV)
  src/views/employee/EmployeeDetailView.vue              (EDIT: thêm tab KPI History)
```

---

## Kế hoạch theo slice

### Slice 1 — Backend: Migration + Lịch sử NV

**Tasks:**
1. Migration `0032`: thêm `source_review_id` vào `employee_rewards` và `employee_training_records`
2. Cập nhật models `Reward` và `EmployeeTrainingRecord`
3. Service `link_service.py`: `get_employee_kpi_history`, `get_employee_review_history`
4. Endpoints `GET /employees/{id}/performance/kpi` và `GET /employees/{id}/performance/reviews`

**Exit criteria:**
- GET KPI history của NV trả đúng danh sách, filter year đúng
- GET review history trả đúng, kèm avg_score on-the-fly

---

### Slice 2 — Backend: Tạo khen thưởng + đào tạo từ review

**Tasks:**
1. Service: `create_reward_from_review`, `create_training_from_review`
2. Endpoint `POST /performance/yearly-reviews/{id}/create-reward`
3. Endpoint `POST /performance/yearly-reviews/{id}/create-training`

**Exit criteria:**
- Tạo khen thưởng từ review: record `employee_rewards` có `source_review_id` đúng
- Tạo đào tạo từ review: record `employee_training_records` có `source_review_id` đúng
- Review không tồn tại → HTTP 404

---

### Slice 3 — Frontend: Tab lịch sử trong hồ sơ NV

**Tasks:**
1. Tạo `KpiHistoryTab.vue` (KPI tháng + đánh giá cuối năm của 1 NV)
2. Thêm tab vào `EmployeeDetailView.vue`

**Exit criteria:**
- Tab "Đánh giá KPI" xuất hiện trong hồ sơ NV
- Dữ liệu KPI tháng và đánh giá cuối năm hiển thị đúng

---

### Slice 4 — Frontend: Nút liên kết + dialog

**Tasks:**
1. Thêm nút "Tạo khen thưởng" + "Đề xuất đào tạo" vào `YearlyReviewTab.vue`
2. Tạo `RewardFromReviewDialog` và `TrainingFromReviewDialog`

**Exit criteria:**
- Tạo khen thưởng từ dialog: record tạo thành công, có `source_review_id`
- Tạo training từ dialog: record tạo thành công, prefill note đúng

---

### Slice 5 — Tests

Tạo `tests/test_performance_links.py`:

```
TestEmployeeHistory:
  - test_get_kpi_history_returns_correct_employee
  - test_get_kpi_history_filter_by_year
  - test_get_review_history_includes_avg_score
  - test_nonexistent_employee_returns_404

TestCreateFromReview:
  - test_create_reward_from_review_sets_source_review_id
  - test_create_training_from_review_sets_source_review_id
  - test_create_from_nonexistent_review_returns_404
  - test_reward_prefills_employee_id_from_review
```

---

## Rủi ro và cách xử lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| `source_review_id` FK SET NULL khi xóa review → mất truy vết | Thấp | SET NULL là đúng — khen thưởng vẫn tồn tại, chỉ mất liên kết; acceptable |
| Tạo khen thưởng từ review đòi hỏi permission 2 module cùng lúc | Trung bình | Endpoint yêu cầu cả `performance:manage_kpi` AND `rewards:manage` |
| Thêm cột vào bảng lớn (`employee_rewards`) có dữ liệu hiện có | Thấp | Cột nullable, migration chỉ là `ALTER TABLE ... ADD COLUMN`, không ảnh hưởng dữ liệu cũ |
| `EmployeeDetailView.vue` đã có nhiều tab → UI quá tải | Trung bình | Tab "Đánh giá KPI" chỉ hiển thị khi NV có dữ liệu KPI; hoặc luôn hiển thị nhưng empty state rõ ràng |
