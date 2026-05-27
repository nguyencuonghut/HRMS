# Kế hoạch triển khai — 14.2. Quản lý thử việc

**Phạm vi:** Hợp đồng thử việc · Đánh giá thử việc · Quy trình kết thúc (Pass/Fail/Extend)  
**Phụ thuộc:** `13.5` ✅ · `Employee.status=probation` ✅ · `EmployeeJobRecord.probation_*` ✅ · `contract_generate_service` ✅ · `reminder_service` ✅ · `offer_service.PROBATION_LIMITS` ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §14.2 · Điều 24–27 Bộ luật Lao động 2019  
**Lưu ý:** Module này có ràng buộc pháp lý nghiêm ngặt — sai giới hạn thử việc hoặc lương thử việc có thể dẫn đến tranh chấp lao động

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `Employee.status` (probation\|official\|long_leave\|resigned) | ✅ Hoàn thành | Trường này là output của workflow 14.2 |
| `EmployeeJobRecord.probation_start_date`, `probation_end_date`, `official_date` | ✅ Hoàn thành | Được set bởi `convert_to_employee` |
| `EmployeeContract` + `document_kind='probation_agreement'` | ✅ Hoàn thành | Bảng contract có sẵn, chỉ cần trigger tạo |
| `contract_generate_service` + DOCX template | ✅ Hoàn thành | Hỗ trợ `probation_contract` document kind |
| `PROBATION_LIMITS` + `_LEVEL_TO_GROUP` trong `offer_service.py` | ✅ Hoàn thành | Level 1→director(180d), 2-3→manager(60d), 4-5→specialist(30d), 6+→worker(6d) |
| `reminder_service._get_probation_ends` | ✅ Hoàn thành | Đã track probation_end trong window [today, +N days] |
| `ProbationEvaluation` model | ❌ Chưa có | |
| `probation_service.py` | ❌ Chưa có | |
| API endpoints probation | ❌ Chưa có | |
| Tab "Thử việc" trong EmployeeDetailView | ❌ Chưa có | |

---

## Phạm vi

**Trong phạm vi:**
- Tạo và tải hợp đồng thử việc (reuse contract_generate_service, document_kind=probation_agreement)
- Form đánh giá thử việc (4 tiêu chí, điểm 0–10, kết quả tổng hợp)
- Quy trình phê duyệt đánh giá: trưởng bộ phận soạn → HR review → HR approve
- 3 kết quả kết thúc thử việc: Passed, Failed, Extended
- Workflow tự động sau khi approve: cập nhật Employee.status, EmployeeJobRecord, tạo hợp đồng chính thức hoặc terminate
- Validation pháp lý: giới hạn ngày thử việc, lương tối thiểu 85%, không thử việc 2 lần cùng vị trí
- Reminder T-15, T-7 trước ngày kết thúc thử việc
- Thông báo kết quả (generate document từ template)

**Ngoài phạm vi:**
- Self-service: nhân viên tự điền phiếu đánh giá
- Multi-step approval (>2 bước)
- Thử việc cho nhân viên internal transfer (chỉ cho nhân viên mới tuyển)
- Báo cáo tổng hợp (→ 14.3)

---

## Thiết kế dữ liệu

### Bảng `probation_evaluations`

```sql
CREATE TABLE probation_evaluations (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    job_record_id       INTEGER NOT NULL REFERENCES employee_job_records(id) ON DELETE RESTRICT,
    -- Ngày đánh giá (thường = evaluation_date gần probation_end_date)
    evaluation_date     DATE NOT NULL,
    -- Người đánh giá (trưởng bộ phận hoặc quản lý trực tiếp)
    evaluator_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    -- HR review (nullable: không bắt buộc nếu HR trực tiếp approve)
    hr_reviewer_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,

    -- Điểm tiêu chí (0.0–10.0, nullable: không bắt buộc nhập đủ)
    attitude_score      NUMERIC(4,1),    -- Thái độ làm việc, tác phong
    competence_score    NUMERIC(4,1),    -- Năng lực chuyên môn
    culture_score       NUMERIC(4,1),    -- Phù hợp văn hóa công ty
    kpi_score           NUMERIC(4,1),    -- Kết quả công việc / KPI thử việc

    -- Điểm tổng hợp (tính bình quân các tiêu chí đã nhập; nullable nếu chưa có tiêu chí nào)
    overall_score       NUMERIC(5,2),

    -- Nhận xét
    manager_comment     TEXT,
    hr_comment          TEXT,

    -- Kết quả: pending=chờ quyết định | passed=đạt | failed=không đạt | extended=gia hạn
    result              VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Số ngày gia hạn (chỉ khi result=extended; tổng thời gian thử việc không được vượt giới hạn pháp lý)
    extension_days      SMALLINT,

    -- Workflow: draft=đang soạn | submitted=đã nộp lên HR | approved=HR đã phê duyệt
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    approved_by_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMP,

    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ràng buộc: mỗi đợt thử việc (employee + job_record) chỉ có 1 phiếu đánh giá
    UNIQUE (employee_id, job_record_id)
);

CREATE INDEX ix_probation_eval_employee ON probation_evaluations(employee_id);
CREATE INDEX ix_probation_eval_status ON probation_evaluations(status);
CREATE INDEX ix_probation_eval_result ON probation_evaluations(result);
```

**Validation DB-level:**
- `CHECK (attitude_score IS NULL OR (attitude_score >= 0 AND attitude_score <= 10))`
- `CHECK (competence_score IS NULL OR (competence_score >= 0 AND competence_score <= 10))`
- `CHECK (culture_score IS NULL OR (culture_score >= 0 AND culture_score <= 10))`
- `CHECK (kpi_score IS NULL OR (kpi_score >= 0 AND kpi_score <= 10))`
- `CHECK (extension_days IS NULL OR extension_days > 0)`
- `CHECK (result IN ('pending', 'passed', 'failed', 'extended'))`
- `CHECK (status IN ('draft', 'submitted', 'approved'))`

### Alembic migration

File: `0046_add_probation_evaluations.py`

```python
# Tạo: probation_evaluations
# Depends on: 0045_add_onboarding_checklist.py
```

---

## Giới hạn thử việc pháp lý

Tái sử dụng từ `offer_service.py` — import `PROBATION_LIMITS` và `_LEVEL_TO_GROUP` vào `probation_service.py`:

```python
from app.services.offer_service import PROBATION_LIMITS, _LEVEL_TO_GROUP, _probation_limit_for_level

# Giới hạn theo Điều 24 BLLĐ 2019:
# Level 1 (director/CEO): 180 ngày
# Level 2-3 (manager/quản lý, yêu cầu trình độ CĐ+): 60 ngày
# Level 4-5 (specialist/nhân viên chuyên môn, TC/CNKT): 30 ngày
# Level 6+ (worker/lao động thông thường): 6 ngày
```

---

## Logic validation pháp lý — `probation_service.py`

### `validate_probation_legal(session, employee_id, job_record_id) → ProbationLegalCheck`

1. **Giới hạn ngày thử việc:**
   - Tính `total_days = probation_end_date - probation_start_date`
   - Lấy `job_title.level` từ EmployeeJobRecord → `_probation_limit_for_level(level)`
   - Nếu `total_days > limit`: `violations.append("Thời gian thử việc ({total_days} ngày) vượt quá giới hạn pháp lý ({limit} ngày) cho cấp bậc này")`

2. **Lương thử việc tối thiểu 85% lương chính thức (Điều 24 khoản 2):**
   - Lấy từ `HiringDecision.probation_salary` và `HiringDecision.official_salary` (thông qua employee → hiring_decision)
   - Nếu `probation_salary < official_salary * 0.85`: cảnh báo
   - Lưu ý: đây là cảnh báo (warning), không phải block — HR có thể override

3. **Không thử việc quá 1 lần cùng vị trí (Điều 24 khoản 1):**
   - Query: `COUNT(probation_evaluations WHERE employee_id = X AND job_record.job_position_id = current_position_id)`
   - Nếu > 0: `violations.append("Nhân viên đã thử việc vị trí này trước đó")`

4. **Thông báo kết quả ít nhất 3 ngày trước end_date (Điều 27):**
   - Áp dụng khi `result = 'failed'`: kiểm tra `evaluation_date <= probation_end_date - 3 ngày`
   - Nếu vi phạm: warning (không block, HR tự quyết định)

```python
class ProbationLegalCheck(BaseModel):
    is_valid: bool
    violations: List[str]      # lỗi cứng — phải fix trước khi proceed
    warnings: List[str]        # cảnh báo — HR có thể override
    probation_days: int
    probation_limit: int
    job_level: Optional[int]
    job_level_group: str       # director | manager | specialist | worker
```

---

## Hợp đồng thử việc

### Tạo hợp đồng — `probation_service.generate_probation_contract(session, employee_id, created_by_id)`

Gọi `contract_generate_service` với:
- `document_kind = 'probation_agreement'`
- Template: lấy `ContractTemplate` có `document_kind='probation_agreement'` và `is_active=True` mới nhất
- Merge fields: full_name, id_number, start_date, probation_start_date, probation_end_date, probation_salary, job_title, department, ...
- Tạo `EmployeeContract` mới với status='draft'

**Auto-trigger:** Sau `convert_to_employee` thành công, gọi `generate_probation_contract`. Nếu không có template → log warning, không fail.

**Manual trigger:** HR có thể gọi `POST /employees/{id}/probation/contract/generate` để tạo lại.

---

## Quy trình đánh giá thử việc

### Luồng trạng thái

```
[draft] → (evaluator submit) → [submitted] → (HR approve) → [approved]
                                                   ↓
                                          Trigger workflow theo result:
                                          - passed → update Employee.status
                                          - failed → mark resigned
                                          - extended → update probation_end_date
```

### `create_evaluation(session, employee_id, data, created_by_id) → ProbationEvaluationRead`

1. Kiểm tra employee tồn tại và `status = 'probation'`; raise 409 nếu không.
2. Lấy current job_record (`is_current=True`).
3. Kiểm tra UNIQUE `(employee_id, job_record_id)` — raise 409 nếu đã có evaluation cho đợt thử việc này.
4. Compute `overall_score`:
   - Tính trung bình các trường score không NULL
   - `scores = [x for x in [attitude, competence, culture, kpi] if x is not None]`
   - `overall_score = sum(scores) / len(scores)` nếu `len > 0` else `None`
5. Tạo `ProbationEvaluation` với `status='draft'`, `result='pending'`.

### `submit_evaluation(session, eval_id, user_id) → ProbationEvaluationRead`

1. Chỉ được submit nếu `status='draft'`.
2. Validate: phải có ít nhất 2 trong 4 score, hoặc có `manager_comment`.
3. Set `status='submitted'`.

### `approve_evaluation(session, eval_id, data: ProbationApproveRequest, user_id) → ProbationEvaluationRead`

1. Chỉ được approve nếu `status='submitted'`.
2. Kiểm tra permission `employees:manage`.
3. Validate pháp lý qua `validate_probation_legal()` — nếu có `violations` → raise 422.
4. Validate `result` hợp lệ (không còn `pending`).
5. Nếu `result='extended'`: kiểm tra `extension_days > 0`.
6. Set `status='approved'`, `approved_by_id`, `approved_at`.
7. Set `hr_comment` nếu cung cấp.
8. **Trigger workflow** theo result.

---

## Workflow kết thúc thử việc

### `_execute_passed_workflow(session, eval, employee_id)`

1. `Employee.status = 'official'`
2. `EmployeeJobRecord.official_date = eval.evaluation_date` (job record is_current=True)
3. Tạo hợp đồng lao động chính thức: gọi `contract_generate_service` với `document_kind='labor_contract'`
4. Ghi `AuditLog`: entity_type='employee', entity_id=employee_id, old_data={status:'probation'}, new_data={status:'official', official_date:...}
5. (Phase sau) Gửi email "Thông báo kết quả thử việc đạt"

### `_execute_failed_workflow(session, eval, employee_id)`

1. Kiểm tra 3-ngày-notice: `eval.evaluation_date <= job_record.probation_end_date - 3 ngày`
   - Nếu vi phạm: log warning (không block — HR đã xác nhận ở approve step)
2. `Employee.status = 'resigned'`
3. `Employee.resigned_date = eval.evaluation_date`
4. Ghi `AuditLog`: entity_type='employee', entity_id=employee_id, old_data={status:'probation'}, new_data={status:'resigned', resigned_date:...}
5. (Phase sau) Gửi "Thông báo chấm dứt thử việc" (tham chiếu Điều 27 BLLĐ)

### `_execute_extended_workflow(session, eval, employee_id)`

1. Lấy current job_record.
2. Tính `new_probation_end = job_record.probation_end_date + timedelta(days=eval.extension_days)`
3. Validate: `new_probation_end - job_record.probation_start_date <= probation_limit` — raise 422 nếu vượt.
4. `EmployeeJobRecord.probation_end_date = new_probation_end`
5. `EmployeeJobRecord.updated_at = utcnow()`
6. Ghi `AuditLog`.
7. (Reminder service sẽ tự pick up ngày mới trong lần chạy tiếp theo)

---

## Tích hợp Reminder — Cảnh báo T-15 và T-7

### Mở rộng `reminder_service._get_probation_ends`

Hiện tại hàm này nhận `days` parameter và trả tất cả `probation_end` trong window `[today, today+days]`. HR cần alert cụ thể ở T-15 và T-7.

**Cách mở rộng:** Thêm logic tag `days_until` trong `RemindersResponse`, frontend hiển thị badge màu:
- `days_until <= 7`: badge đỏ "Cấp thiết"
- `days_until <= 15`: badge cam "Sắp đến"

**Không cần thêm code** vào reminder_service — `days_until` đã có trong `ReminderItem`. Chỉ cần frontend `/reminders` hiển thị phân biệt màu theo ngưỡng.

**Bổ sung:** Thêm endpoint dashboard `/reminders?types=probation_end&days=15` → HR dashboard có thể hiện widget "Sắp hết thử việc (15 ngày tới)".

---

## API Design

```
GET    /employees/{id}/probation
       → ProbationDetailRead (kèm evaluation nếu có, legal_check, contract status)
       Permission: employees:view

POST   /employees/{id}/probation/evaluate
       body: ProbationEvaluationCreate
       → ProbationEvaluationRead
       -- Tạo evaluation draft (evaluator = trưởng bộ phận hoặc HR)
       Permission: employees:edit

PATCH  /employees/{id}/probation/evaluate/{eval_id}
       body: ProbationEvaluationUpdate
       → ProbationEvaluationRead
       -- Cập nhật draft (điểm, nhận xét, result, extension_days)
       -- Chỉ khi status=draft
       Permission: employees:edit

POST   /employees/{id}/probation/submit
       → ProbationEvaluationRead
       -- draft → submitted
       Permission: employees:edit

POST   /employees/{id}/probation/approve
       body: ProbationApproveRequest { result, hr_comment?, extension_days? }
       → ProbationEvaluationRead
       -- submitted → approved; trigger workflow
       Permission: employees:manage

GET    /employees/{id}/probation/contract
       → List[EmployeeContractRead] (chỉ probation_agreement)
       Permission: employees:view

POST   /employees/{id}/probation/contract/generate
       → EmployeeContractRead (tạo từ template)
       Permission: employees:edit

GET    /employees/{id}/probation/legal-check
       → ProbationLegalCheck
       -- Kiểm tra nhanh các điều kiện pháp lý
       Permission: employees:view
```

### Schemas

```python
class ProbationEvaluationCreate(BaseModel):
    evaluation_date: date
    evaluator_id: int
    attitude_score: Optional[float] = None     # 0.0–10.0
    competence_score: Optional[float] = None
    culture_score: Optional[float] = None
    kpi_score: Optional[float] = None
    result: str = 'pending'                    # pending|passed|failed|extended
    extension_days: Optional[int] = None       # chỉ khi result=extended
    manager_comment: Optional[str] = None

class ProbationEvaluationRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    job_record_id: int
    evaluation_date: date
    evaluator_id: int
    evaluator_name: str
    hr_reviewer_id: Optional[int]
    attitude_score: Optional[float]
    competence_score: Optional[float]
    culture_score: Optional[float]
    kpi_score: Optional[float]
    overall_score: Optional[float]
    manager_comment: Optional[str]
    hr_comment: Optional[str]
    result: str
    extension_days: Optional[int]
    status: str                              # draft|submitted|approved
    approved_by_id: Optional[int]
    approved_by_name: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class ProbationApproveRequest(BaseModel):
    result: str                              # passed|failed|extended (không được là 'pending')
    hr_comment: Optional[str] = None
    extension_days: Optional[int] = None    # bắt buộc nếu result=extended

class ProbationDetailRead(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    department_name: Optional[str]
    job_title_name: Optional[str]
    job_title_level: Optional[int]
    status: str                             # Employee.status
    probation_start_date: Optional[date]
    probation_end_date: Optional[date]
    official_date: Optional[date]
    days_remaining: Optional[int]          # probation_end_date - today
    legal_check: ProbationLegalCheck
    evaluation: Optional[ProbationEvaluationRead]
    contracts: List[EmployeeContractRead]  # probation_agreement contracts
```

---

## Thiết kế Frontend

### Tab "Thử việc" trong `EmployeeDetailView.vue`

Thêm tab mới sau tab "Hồ sơ pháp lý":

```vue
<Tab value="probation" :disabled="isNew">Thử việc</Tab>
```

### `ProbationTab.vue` (component mới, import vào EmployeeDetailView)

**Section 1 — Thông tin thử việc:**
- Card: Ngày bắt đầu, Ngày kết thúc, Ngày còn lại (Badge màu theo ngưỡng)
- Legal check panel: hiển thị violations (đỏ) và warnings (cam)
- Hợp đồng thử việc: link tải + Button "Tạo hợp đồng" (nếu chưa có)

**Section 2 — Phiếu đánh giá:**

| Trường | Loại | Validation |
|---|---|---|
| Ngày đánh giá | DatePicker | Bắt buộc; không được sau probation_end_date + 30 ngày |
| Người đánh giá | Select User | Bắt buộc |
| Thái độ làm việc (0–10) | Slider + Input | Optional; 0 ≤ x ≤ 10 |
| Năng lực chuyên môn (0–10) | Slider + Input | Optional |
| Phù hợp văn hóa (0–10) | Slider + Input | Optional |
| KPI thử việc (0–10) | Slider + Input | Optional |
| Điểm tổng hợp | Computed, readonly | Hiện tự động |
| Kết quả | RadioGroup | pending/passed/failed/extended; bắt buộc khi submit |
| Số ngày gia hạn | InputNumber | Bắt buộc nếu result=extended; min=1 |
| Nhận xét trưởng bộ phận | Textarea | Optional |
| Nhận xét HR | Textarea | Optional; chỉ HR điền được |

**Action buttons theo workflow:**
- `status=draft`: Button "Lưu nháp" + Button "Nộp lên HR"
- `status=submitted`: (HR) Button "Phê duyệt" → mở `ProbationApproveDialog.vue`
- `status=approved`: Hiện nhãn "Đã hoàn thành" + ngày approve + người approve

### `ProbationApproveDialog.vue`

- Hiển thị tóm tắt điểm và kết quả
- Cảnh báo pháp lý (violations từ `/probation/legal-check`)
- Confirm action với result + hr_comment
- Extension days (nếu result=extended)

**Breadcrumb:** `Nhân viên > {employee_name} > Thử việc`

---

## Cấu trúc file

```
backend/
  alembic/versions/0046_add_probation_evaluations.py    (NEW)
  app/models/probation.py                                (NEW: ProbationEvaluation)
  app/schemas/probation.py                               (NEW)
  app/services/probation_service.py                      (NEW)
  app/api/v1/endpoints/probation.py                      (NEW)
  app/api/v1/router.py                                   (EDIT: include probation router, mount under /employees)
  app/services/hiring_decision_service.py                (EDIT: thêm generate_probation_contract sau convert_to_employee)
  app/services/offer_service.py                          (KHÔNG edit: chỉ import PROBATION_LIMITS từ đây)
  tests/test_probation.py                                (NEW)

frontend/
  src/services/probationService.ts                       (NEW)
  src/views/employees/ProbationTab.vue                   (NEW: tab component)
  src/views/employees/ProbationApproveDialog.vue         (NEW)
  src/views/employees/EmployeeDetailView.vue             (EDIT: thêm Tab "Thử việc" + import ProbationTab)
```

---

## Kế hoạch theo Slice

### Slice 1 — DB migration + constants
- `0046_add_probation_evaluations.py`
- Model `app/models/probation.py`
- Import `PROBATION_LIMITS` từ `offer_service.py` vào `probation_service.py`
- Hàm `validate_probation_legal()`
- Endpoint `GET /employees/{id}/probation/legal-check`
- **Deliverable:** HR có thể query legal check cho bất kỳ nhân viên thử việc nào

### Slice 2 — Hợp đồng thử việc
- `generate_probation_contract()` trong `probation_service.py`
- Auto-trigger trong `hiring_decision_service.convert_to_employee`
- Endpoints: `GET /employees/{id}/probation/contract`, `POST /employees/{id}/probation/contract/generate`
- **Deliverable:** Convert ứng viên → tự sinh hợp đồng thử việc; HR tải được

### Slice 3 — Evaluation model + CRUD API
- `create_evaluation`, `submit_evaluation` trong service
- Endpoints: `GET /employees/{id}/probation`, `POST /employees/{id}/probation/evaluate`, `PATCH`, `POST .../submit`
- Schemas đầy đủ
- Tests: `test_probation.py` slice 1–3
- **Deliverable:** HR/Manager có thể tạo và nộp phiếu đánh giá

### Slice 4 — Workflow approve + status update
- `approve_evaluation()` + 3 workflow functions: `_execute_passed`, `_execute_failed`, `_execute_extended`
- AuditLog ghi nhận
- Endpoint `POST /employees/{id}/probation/approve`
- Tests: workflow tests (pass/fail/extend)
- **Deliverable:** HR approve → Employee.status tự động cập nhật; EmployeeJobRecord.official_date/probation_end_date thay đổi đúng

### Slice 5 — Frontend
- `probationService.ts`
- `ProbationTab.vue` với form đánh giá đầy đủ
- `ProbationApproveDialog.vue`
- Edit `EmployeeDetailView.vue`: thêm Tab value="probation"
- **Deliverable:** HR click tab Thử việc → thấy thông tin, tạo/submit/approve evaluation trong UI

---

## Rủi ro pháp lý

| Rủi ro | Mức độ | Cách xử lý |
|---|---|---|
| Thử việc vượt giới hạn pháp lý (Điều 24) | **Cao** | `validate_probation_legal()` block hard ở approve step — nếu `violations` không rỗng → raise 422; HR không thể override lỗi cứng này |
| Lương thử việc < 85% lương chính thức (Điều 24 khoản 2) | **Cao** | Warning ở approve step — HR phải tick checkbox "Xác nhận đã kiểm tra" để override (lưu vào `hr_comment`) |
| Thử việc 2 lần cùng vị trí | **Cao** | Block hard: query `probation_evaluations WHERE employee_id AND job_position_id` — nếu có → raise 422 |
| Không thông báo trước 3 ngày khi fail (Điều 27) | Trung bình | Warning (không block) — HR xác nhận bằng `hr_comment`; ghi vào AuditLog |
| `_execute_extended` vượt giới hạn tổng thời gian | Trung bình | Tính `total = (original_end + extension) - start`; nếu > limit → raise 422 trước khi update DB |
| AuditLog không ghi khi workflow fail giữa chừng | Thấp | Wrap toàn bộ `_execute_*_workflow` trong transaction; chỉ commit AuditLog sau khi tất cả update thành công |
| Race condition: 2 HR approve cùng lúc | Thấp | SELECT FOR UPDATE trên `probation_evaluations.id` trước khi check status=submitted |
