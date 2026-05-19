# Kế hoạch implementation — Refactor mã nhân viên 3 hệ theo lát cắt

**Phạm vi:** Triển khai refactor cơ chế cấp mã nhân viên từ 1 hệ toàn cục sang nhiều hệ số độc lập  
**Tài liệu gốc:** [docs/plan_refactor_ma_nhan_vien_3_he.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_refactor_ma_nhan_vien_3_he.md:1)  
**Mục tiêu rollout:** Chia implementation thành các lát cắt dọc có checkpoint rõ ràng, để mỗi bước đều kiểm soát được rủi ro migration, tương thích ngược, và verify được trên seam đúng

---

## Nguyên tắc chia lát cắt

1. **Không bật multi-sequence writes** cho đến khi tất cả writer và consumer nội bộ thôi giả định `employee_seq` là unique toàn cục
2. **Ưu tiên additive schema trước**, behavior switch sau
3. **Create flow và import flow phải migrate xong** trước khi siết validation mới
4. **Chuẩn hóa read-path `employee_code`** trước hoặc đồng thời với mọi thay đổi format hiển thị
5. **`job_position override` không phải lát cắt đầu tiên an toàn**; rollout mặc định nên ưu tiên department-first, rồi mới mở rộng nếu business vẫn cần

---

## Điều kiện chặn trước khi code

Các câu hỏi dưới đây phải được chốt trước khi đi tới lát cắt cutover:

1. Có giữ format hiển thị `{prefix}{seq}` hay không nếu một prefix có thể chứa nhiều hệ số?
2. Có tiếp tục support “draft employee chưa có job context” sau go-live hay không?
3. Rule `department/job_position` chỉ áp dụng lúc cấp mã lần đầu, hay có yêu cầu đổi mã khi chuyển công tác?
4. Đợt rollout đầu có hồi tố nhân viên cũ sang `SYS2/SYS3` hay không?

Khuyến nghị của plan này:

- rollout đầu **không hồi tố**
- rollout đầu **không đổi mã cũ**
- rollout đầu chỉ bật cutover khi `display_code` uniqueness đã được chốt bằng văn bản

---

## Tổng quan lát cắt

| Lát cắt | Mục tiêu | Có đổi hành vi runtime không? | Phụ thuộc |
|---|---|---|---|
| `Slice 0` | Chốt precondition nghiệp vụ và freeze point | Không | Không |
| `Slice 1` | Dựng schema + backfill an toàn | Không | `Slice 0` |
| `Slice 2` | Tách seam chung cho `employee_code` và rule resolution | Có, nhưng chỉ ở read-path | `Slice 1` |
| `Slice 3` | Migrate writer: create flow + import + compatibility | Có | `Slice 2` |
| `Slice 4` | Cutover allocator và invariant enforcement | Có, mạnh | `Slice 3` |
| `Slice 5` | Chuẩn hóa downstream module và UI hiển thị mã | Có | `Slice 4` |
| `Slice 6` | Mở `job_position override` nếu business vẫn cần | Có | `Slice 5` |

Checkpoint nguy hiểm nhất nằm giữa `Slice 3` và `Slice 4`.

---

## Slice 0 — Business Precondition và Freeze Point

### Mục tiêu

Chốt các quyết định nghiệp vụ nếu chưa chốt thì **không code cutover**:

- format và tính duy nhất của `display_code`
- có còn support employee tạo nháp khi chưa có current job hay không
- rule hệ số có đổi theo transfer hay chỉ áp dụng ở lần cấp mã đầu tiên

### Phạm vi

- Backend: không đổi
- Frontend: không đổi
- Data: không đổi

### Deliverable

- 1 biên bản chốt nghiệp vụ hoặc issue/ADR nội bộ
- update lại [docs/plan_refactor_ma_nhan_vien_3_he.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_refactor_ma_nhan_vien_3_he.md:1) nếu có thay đổi quyết định

### Verify bắt buộc

- Có văn bản chốt 4 câu hỏi ở trên
- Team thống nhất rõ `go/no-go` cho `{prefix}{seq}`

### Exit criteria

- Không còn câu hỏi business nào có thể làm đổi schema hoặc API create

---

## Slice 1 — Schema Scaffold và Backfill An Toàn

### Mục tiêu

Thêm đầy đủ hạ tầng DB cho 3 hệ số nhưng **chưa đổi cách ghi dữ liệu runtime**.

### Thay đổi chính

#### Backend / DB

- tạo bảng `employee_code_sequences`
- tạo bảng `employee_code_sequence_rules`
- thêm cột nullable `employees.employee_code_sequence_id`
- thêm unique constraint/index cho `employees.id_number`
- seed `SYS1`, `SYS2`, `SYS3`
- backfill toàn bộ employee hiện có vào `SYS1`
- set `SYS1.next_value = MAX(employee_seq) + 1`

#### Frontend

- không đổi

#### Data / seed

- chưa bỏ unique toàn cục trên `employee_seq`
- chưa cho phép trùng `employee_seq` giữa các hệ

### File/Seam dự kiến

- [backend/app/models/employee.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee.py:1)
- [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py:1)
- `backend/alembic/versions/0016_*.py`

### Rủi ro

- seed/tooling hiện còn dùng `employee_seq` như global key
- nếu vội drop unique toàn cục ở lát cắt này sẽ làm seed/import/tooling mơ hồ ngay

### Verify bắt buộc

- migration chạy được trên dữ liệu hiện có
- tất cả employee cũ có `employee_code_sequence_id = SYS1`
- `SYS1.next_value` đúng bằng `MAX(employee_seq)+1`
- create/list/get employee hiện tại không đổi hành vi

### Exit criteria

- DB có đủ schema mới nhưng runtime hiện tại vẫn hoạt động như cũ

---

## Slice 2 — Centralize `employee_code` và Rule Resolution

### Mục tiêu

Tạo một seam duy nhất cho:

- `resolve_employee_code_sequence(...)`
- `allocate_employee_sequence(...)`
- `compute_employee_display_code(...)`

Lát cắt này chủ yếu chuẩn hóa read-path trước khi đổi write-path.

### Thay đổi chính

#### Backend

- tạo service mới, ví dụ `employee_code_service.py`
- di chuyển logic tính `display_code` về service chung
- chuyển các read-path chính dùng helper/service mới:
  - employee list
  - employee lookup
  - employee detail
  - export list

#### Frontend

- không đổi contract hiển thị, chỉ hưởng lợi từ API nhất quán hơn

#### Data

- không đổi dữ liệu

### File/Seam dự kiến

- [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py:1)
- [backend/app/services/employee_job_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_job_service.py:1)
- [backend/app/api/v1/endpoints/employees.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/employees.py:1)
- [backend/app/services/employee_export_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_export_service.py:1)

### Rủi ro

- hidden caller vẫn dùng raw `employee_seq`
- có thể chuẩn hóa chưa hết, khiến các module khác vẫn trả `id_number` hoặc seq thuần

### Verify bắt buộc

- backend tests cho:
  - format `display_code`
  - fallback khi chưa có prefix
  - rule precedence cơ bản trên dữ liệu giả lập
- verify API:
  - `/employees`
  - `/employees/{id}`
  - `/employees/lookup`
  - export list
  cùng dùng một helper chuẩn

### Exit criteria

- Có đúng 1 seam backend chịu trách nhiệm tính `employee_code` cho:
  - employee list
  - employee detail
  - employee lookup
  - employee export list

Các module downstream như leave / contract / reminder có thể vẫn còn đang ở lát cắt sau, nhưng không được tạo thêm seam mới ngoài service chung này.

---

## Slice 3 — Writer Compatibility: Create Flow, Import, và Caller Migration

### Mục tiêu

Migrate tất cả writer chính để chúng **có thể** gửi đủ context cho allocator mới, nhưng chưa bật cutover cứng.

### Thay đổi chính

#### Backend

- mở rộng `EmployeeCreate`:
  - `initial_department_id`
  - `initial_job_title_id`
  - `initial_job_position_id`
  - `initial_job_effective_from`
  - fallback `employee_code_sequence_id`
- thêm validation:
  - nếu có `job_position_id` thì vị trí phải thuộc đúng `department_id`
  - nếu `job_position` đã có `job_title_id` thì payload không được mâu thuẫn
- với caller mới, create path phải có khả năng:
  - resolve sequence
  - tạo `Employee`
  - tạo current `EmployeeJobRecord` đầu tiên
  trong **cùng một transaction**
- tạm thời vẫn accept payload cũ trong giai đoạn tương thích

#### Frontend

- redesign create flow ở [EmployeeDetailView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/EmployeeDetailView.vue:1) để user nhập current job context trước khi submit
- không còn dựa hoàn toàn vào việc tạo employee trước rồi mới qua tab `Công việc`

#### Import

- thêm cột `Vị trí công việc`
- thêm cột `Hệ mã nhân viên` cho override ngoại lệ / legacy
- đổi processor để có thể gửi initial job context hoặc explicit sequence
- unresolved department/rule phải được định nghĩa rõ:
  - trong giai đoạn tương thích có thể còn support caller cũ
  - nhưng phải có cờ để biết path nào chưa migrate

#### Seed / tooling

- bắt đầu dọn các điểm đang lookup/upsert theo `employee_seq`

### File/Seam dự kiến

- [backend/app/schemas/employee.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/schemas/employee.py:1)
- [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py:1)
- [backend/app/services/employee_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_import_service.py:1)
- [frontend/src/services/employeeService.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/services/employeeService.ts:1)
- [frontend/src/views/employees/EmployeeDetailView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/EmployeeDetailView.vue:1)

### Rủi ro

- create UI và import migrate lệch nhịp
- payload cũ vẫn tồn tại nhưng không được quan sát/đếm để biết đã loại bỏ hết hay chưa

### Verify bắt buộc

- browser-level verify create flow mới:
  - chọn department/job hợp lệ
  - save thành công
  - hiển thị mã đúng sau save
- API tests:
  - payload hợp lệ với department-only
  - payload hợp lệ với department + job_position
  - reject mismatch `job_position` / `department`
- import tests:
  - có department-only
  - có position override
  - có explicit system override
  - unresolved department/rule theo đúng policy đã chốt

### Exit criteria

- Tất cả writer chính đã có đường gửi đủ context cho allocator mới
- Caller mới đã có path tạo `Employee` + current `EmployeeJobRecord` đầu tiên trong cùng transaction
- Team biết chính xác caller nào còn đang ở mode tương thích

---

## Slice 4 — Allocator Cutover và Invariant Enforcement

### Mục tiêu

Đây là lát cắt đổi behavior chính thức:

- chuyển từ global counter sang allocator theo từng hệ
- bỏ giả định `employee_seq` unique toàn cục
- siết invariant dữ liệu

### Thay đổi chính

#### Backend

- create/import dùng allocator theo `employee_code_sequence_id`
- row lock trên `employee_code_sequences.next_value`
- `employee_code_sequence_id` và `employee_seq` trở thành bất biến sau khi cấp
- bật reject `422` với create/import thiếu context bắt buộc

#### DB

- drop unique toàn cục trên `employees.employee_seq`
- tạo unique mới trên `(employee_code_sequence_id, employee_seq)`
- set `employees.employee_code_sequence_id NOT NULL`

#### Seed / tooling / test infra

- toàn bộ seed/tooling phải chuyển khỏi lookup/upsert bằng `employee_seq` toàn cục
- ưu tiên dùng `employee_id`

#### Frontend

- hiển thị rõ validation errors từ contract mới

### File/Seam dự kiến

- [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py:1)
- [backend/app/services/employee_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_import_service.py:1)
- [backend/app/seeds/employees.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/employees.py:1)
- [backend/app/seeds/employee_job_records.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/employee_job_records.py:1)

### No-go trước khi merge

- chưa migrate xong create flow và import flow
- seed/tooling còn dùng `ON CONFLICT (employee_seq)` hoặc `WHERE e.employee_seq = ...`
- `display_code` uniqueness còn chưa chốt

### Verify bắt buộc

- concurrent tests:
  - 2 create cùng hệ không cấp trùng
  - 2 create khác hệ tăng độc lập
  - duplicate `id_number` bị DB chặn đúng
- migration tests:
  - backfill đúng
  - seed rerun vẫn idempotent
  - `NOT NULL` và composite unique hoạt động đúng
- runtime checks:
  - create employee mới đi đúng system
  - import đi đúng system

### Exit criteria

- Hệ thống đã thực sự ghi theo multi-sequence
- Không còn phụ thuộc kỹ thuật nào vào global unique `employee_seq`

---

## Slice 5 — Downstream Module Normalization

### Mục tiêu

Chuẩn hóa toàn bộ module đang hiển thị hoặc trả `employee_code`, để user nhìn cùng một mã ở mọi nơi.

### Thay đổi chính

#### Backend

- thay toàn bộ logic ad hoc ở:
  - leave
  - contract
  - reminder
  - export
  - lookup
- tất cả đều đọc từ seam `compute_employee_display_code(...)`

#### Frontend

- verify các màn Employee / Leave / Contract / Reminder hiển thị cùng một mã

### File/Seam dự kiến

- [backend/app/services/leave_entitlement_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_entitlement_service.py:1)
- [backend/app/services/leave_record_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_service.py:1)
- [backend/app/services/leave_report_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_report_service.py:1)
- [backend/app/services/employee_contract_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_contract_service.py:1)
- [backend/app/services/reminder_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/reminder_service.py:1)

### Rủi ro

- nếu `display_code` không còn globally unique ở mức hiển thị, dropdown/search có thể gây chọn nhầm

### Verify bắt buộc

- browser-level verification:
  - employee list/detail
  - leave entitlement/list/report
  - contract list
  - reminders
- verify cùng một nhân viên có cùng mã ở mọi module

### Exit criteria

- Không còn module nào dùng `id_number` hoặc `employee_seq` raw như employee code hiển thị

---

## Slice 6 — Job Position Override Rollout

### Mục tiêu

Chỉ triển khai lát cắt này nếu business vẫn thực sự cần `job_position` override sau khi đã có rollout an toàn theo department/system.

### Vì sao tách riêng

- `job_position` hiện là dữ liệu mutable
- có thể bị move sang department khác
- có thể bị xóa
- source hiện tại chưa chặn đủ lifecycle này

### Thay đổi chính

#### Backend / DB

- enable rule resolution ưu tiên `job_position`
- chặn move/delete `job_position` khi:
  - còn rule active
  - hoặc còn current employee đang tham chiếu
- chốt policy với `PUT /job-records/current`:
  - hoặc cấm sửa `department_id` / `job_position_id` in-place
  - hoặc cho sửa nhưng không cấp lại mã

#### Frontend

- nếu cần, hiển thị cảnh báo rõ khi admin sửa current job theo cách có thể làm thay đổi rule áp dụng cho nhân viên mới về sau

### Verify bắt buộc

- reject mismatch `job_position.department_id != department_id`
- reject move/delete vị trí đang có rule hoặc current assignee
- verify transfer và update-current tuân thủ đúng policy đã chốt

### Exit criteria

- `job_position override` hoạt động mà không tạo mâu thuẫn giữa sequence allocation và display prefix

---

## No-Go Combinations

Không được merge các tổ hợp sau:

1. Drop global unique `employee_seq` khi seed/tooling vẫn dùng `employee_seq` làm khóa toàn cục
2. Bật multi-sequence allocator khi create/import chưa migrate xong
3. Bật `422 require job context` trước khi frontend create flow và import template đã đổi
4. Bật `job_position override` trước khi có validation `job_position belongs to department`
5. Merge `Slice 4` trước `Slice 5` nếu `Slice 4` đồng thời làm đổi format hoặc semantics duy nhất của `display_code`
6. Đổi format `display_code` khi leave/contracts/reminders/export còn mỗi nơi tính một kiểu
7. Hồi tố dữ liệu cũ sang `SYS2/SYS3` trong rollout đầu

---

## Thứ tự rollout khuyến nghị

1. `Slice 0`
2. `Slice 1`
3. `Slice 2`
4. `Slice 3`
5. checkpoint review: chỉ khi writer và tooling đã migrate xong mới đi tiếp
6. `Slice 4`
7. `Slice 5`
8. `Slice 6` nếu còn cần

---

## Verify Matrix

| Lát cắt | Verify bắt buộc |
|---|---|
| `Slice 0` | văn bản chốt nghiệp vụ |
| `Slice 1` | migration/backfill verification |
| `Slice 2` | backend tests cho helper/rule/display code |
| `Slice 3` | browser create flow + API/import tests |
| `Slice 4` | concurrent tests + DB constraint verification |
| `Slice 5` | browser-level cross-module verification |
| `Slice 6` | lifecycle tests cho `job_position` + transfer/update-current |

---

## Khuyến nghị chốt

Nếu muốn rollout rủi ro thấp nhất:

- đi theo `department/system` trước
- để `job_position override` thành lát cắt mở rộng sau
- không hồi tố nhân viên cũ
- không cắt global unique `employee_seq` cho tới khi seed/tooling và writer đã migrate sạch

Plan này phù hợp với current source vì nó tách rõ:

- lát cắt additive-only
- lát cắt migrate caller
- lát cắt cutover behavior
- lát cắt normalize toàn hệ thống

Thay vì gộp mọi thứ vào một migration lớn khó rollback.
