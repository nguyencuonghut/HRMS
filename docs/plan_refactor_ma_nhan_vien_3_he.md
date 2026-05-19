# Đề xuất refactor — Mã nhân viên theo 3 hệ số

**Ngày:** 2026-05-19  
**Phạm vi:** Refactor cơ chế cấp `employee_seq` / `display_code` cho toàn hệ thống HRMS  
**Mục tiêu:** Cho phép công ty vận hành **3 hệ auto tăng số nguyên mã nhân viên** thay vì 1 hệ toàn cục như hiện nay

---

## 1. Yêu cầu nghiệp vụ

Hiện tại công ty đang vận hành thực tế theo 3 hệ số nguyên để cấp mã nhân viên:

- **Hệ 1**: phần lớn các phòng/ban
- **Hệ 2**: công nhân bốc xếp, công nhân ra cám, tạp vụ
- **Hệ 3**: công nhân và bảo vệ thuộc **Phòng trại**

Nhu cầu mới:

- Không còn 1 bộ đếm toàn cục cho toàn công ty
- Phải cấu hình được **đơn vị nào / vị trí nào** chạy theo hệ nào
- Khi tương lai thêm **phòng/ban/bộ phận/nhóm/tổ** hoặc **vị trí công việc** mới, HR/Admin phải cấu hình được ngay mà không sửa code

---

## 2. Hiện trạng đã verify từ source code

### 2.1. Cơ chế hiện tại

Đã kiểm tra các file sau:

- [backend/app/models/employee.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee.py:16)
- [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py:20)
- [backend/app/services/employee_job_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_job_service.py:20)
- [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py:14)
- [backend/alembic/versions/0007_create_employee_tables.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/alembic/versions/0007_create_employee_tables.py:20)
- [backend/alembic/versions/0008_create_employee_job_records.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/alembic/versions/0008_create_employee_job_records.py:17)

Hiện trạng thật của hệ thống:

- `employees.employee_seq` là **số nguyên toàn cục, unique trên toàn bảng**
- Khi tạo nhân viên, backend lấy số tiếp theo bằng cách đọc `employee_seq` lớn nhất hiện tại rồi `+1`
- Mã hiển thị không lưu DB; backend tính bằng `compute_display_code(employee_seq, dept_prefix)`
- `dept_prefix` hiện lấy từ `departments.display_prefix` của **bản ghi công việc hiện tại**
- Nếu chưa có job record hoặc phòng ban không có `display_prefix`, UI sẽ chỉ thấy phần số

### 2.2. Công thức hiện tại

Trong [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py:20):

```python
def compute_display_code(employee_seq: int, dept_display_prefix: Optional[str] = None) -> str:
    seq_str = f"{employee_seq:04d}"
    return f"{dept_display_prefix}{seq_str}" if dept_display_prefix else seq_str
```

Tức là:

- Phần số là `employee_seq`
- Phần prefix là prefix phòng ban hiện tại
- Dạng hiển thị thực tế trong code đang là zero-pad tối thiểu 4 chữ số

### 2.3. Flow tạo nhân viên hiện tại

Đã kiểm tra:

- [frontend/src/views/employees/EmployeeDetailView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/EmployeeDetailView.vue:1)
- [backend/app/api/v1/endpoints/employees.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/employees.py:128)

Flow hiện nay là:

1. Tạo `Employee` trước
2. Gán `EmployeeJobRecord` sau

Điểm quan trọng:

- Ở mode tạo mới, tab `Công việc` đang bị disable trên frontend
- Nghĩa là **lúc tạo employee hiện tại chưa có department/job_position hiện hành**
- Vì vậy hệ thống **không đủ dữ liệu để tự suy ra “hệ mã” theo phòng ban / vị trí** ngay tại thời điểm cấp số

Đây là blocker kiến trúc quan trọng nhất của refactor này.

---

## 3. Bất nhất hiện tại giữa các module

Đã kiểm tra các service đang trả `employee_code`:

- [backend/app/services/leave_entitlement_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_entitlement_service.py:27)
- [backend/app/services/leave_record_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_service.py:30)
- [backend/app/services/leave_report_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_report_service.py:95)
- [backend/app/services/employee_contract_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_contract_service.py:338)
- [backend/app/services/reminder_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/reminder_service.py:80)

Hiện đang có 3 kiểu khác nhau:

- Leave modules dùng `compute_display_code(emp.employee_seq)` nhưng **không truyền prefix hiện tại**
- Contract global list đang trả `str(emp.employee_seq)`
- Reminder đang trả `emp.id_number`

Kết luận:

- Ngay cả trước khi thêm “3 hệ số”, việc chuẩn hóa `employee_code` toàn hệ thống đã là việc bắt buộc
- Refactor mới nên đồng thời chuẩn hóa mọi nơi về **một nguồn sự thật duy nhất**

---

## 4. Hạn chế của thiết kế hiện tại đối với yêu cầu mới

Thiết kế hiện tại chỉ hỗ trợ:

- 1 bộ đếm toàn cục
- Prefix hiển thị phụ thuộc phòng ban hiện tại

Thiết kế này không giải được:

1. **Nhiều bộ đếm song song**

- Vì `employees.employee_seq` đang `UNIQUE` toàn cục
- Không có khái niệm “employee thuộc hệ nào”

2. **Cấu hình theo vị trí công việc**

- Hiện không có bảng rule/mapping để nói rằng vị trí A dùng Hệ 2, vị trí B dùng Hệ 3

3. **Kế thừa theo cây tổ chức**

- `departments` đã là cây phân cấp, nhưng chưa có rule kế thừa bộ đếm theo node cha/con

4. **Cấp số đúng lúc tạo**

- Do `Employee` đang được tạo trước `EmployeeJobRecord`, backend không có đủ thông tin để resolve system tự động

---

## 5. Quyết định thiết kế được đề xuất

## 5.1. Không cấu hình thuần theo phòng ban

Nếu chỉ cấu hình theo `department`:

- Giải được phần lớn trường hợp “một đơn vị chạy theo một hệ”
- Nhưng không giải tốt trường hợp cùng một phòng có nhiều nhóm nhân sự khác nhau chạy các hệ khác nhau

Ví dụ nghiệp vụ:

- `Phòng trại` có thể có cả nhân sự văn phòng và công nhân/bảo vệ
- Nếu cùng một node tổ chức mà có 2 cách đánh số, cấu hình thuần theo department sẽ không đủ

## 5.2. Không cấu hình thuần theo vị trí công việc

Nếu chỉ cấu hình theo `job_position`:

- Giải được trường hợp ngoại lệ theo vai trò
- Nhưng lại không thuận tiện cho nhu cầu “cả một phòng/ban/tổ/nhóm mới sẽ dùng Hệ 2/Hệ 3”

## 5.3. Khuyến nghị: rule engine hybrid

Khuyến nghị dùng **cấu hình hybrid**:

- Rule có thể gắn vào **department**
- Rule có thể gắn vào **job_position**
- Khi resolve hệ số, áp dụng thứ tự ưu tiên:

1. `job_position` exact match
2. `department` exact match
3. `department` cha gần nhất có rule kế thừa
4. fallback về **Hệ 1** mặc định toàn công ty

Lý do:

- `departments` hiện đã mô hình hóa cả `PHONG | BAN | BO_PHAN | NHOM | TO`
- `job_positions` đã tồn tại trong schema và gắn với `department`
- Hybrid rule đáp ứng được cả 2 nhu cầu:
  - “Cả đơn vị này dùng hệ nào”
  - “Một vị trí đặc thù trong đơn vị dùng hệ khác”

Nhưng để `job_position` được phép override `department`, tài liệu này chốt thêm 2 bất biến bắt buộc:

1. Nếu có `job_position_id` thì vị trí đó **phải thuộc đúng `department_id` của job record**
2. Nếu `job_position` đã có `job_title_id` mặc định thì payload không được phép mâu thuẫn với `job_title_id` đó

Lý do phải chốt sớm:

- source hiện tại đang cho phép `department_id`, `job_title_id`, `job_position_id` đi độc lập, chưa có validation chéo
- nếu không khóa bất biến này, hệ thống có thể cấp số theo `job_position` của đơn vị A nhưng lại hiển thị prefix theo `department` của đơn vị B

Ngoài ra, vì `job_position` hiện là dữ liệu mutable và có thể bị đổi `department` hoặc bị xóa, rule gắn theo `job_position` chỉ an toàn nếu bổ sung thêm ràng buộc vận hành:

- không cho chuyển `job_position` sang `department` khác khi còn rule active hoặc còn nhân viên current đang giữ vị trí đó
- không cho xóa `job_position` khi còn rule active hoặc còn nhân viên current đang tham chiếu

Nếu business không chấp nhận các ràng buộc vận hành này, nên thu hẹp phase đầu về rule theo `department` là chính, còn `job_position` chỉ mở sau khi chuẩn hóa lifecycle của vị trí công việc.

---

## 6. Mô hình dữ liệu đề xuất

## 6.1. Bảng master các hệ số

### `employee_code_sequences`

```sql
CREATE TABLE employee_code_sequences (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,   -- SYS1, SYS2, SYS3
    name            VARCHAR(200) NOT NULL,         -- Hệ 1 / Hệ 2 / Hệ 3
    description     TEXT,
    next_value      INTEGER NOT NULL DEFAULT 1,
    min_digits      SMALLINT NOT NULL DEFAULT 4,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);
```

Ràng buộc bắt buộc bổ sung ở migration:

- đúng **1 sequence active** có `is_default = true`
- `code` là bất biến kỹ thuật, không sửa sau khi go-live

Seed tối thiểu:

- `SYS1` — Hệ 1 — mặc định công ty
- `SYS2` — Hệ 2 — công nhân bốc xếp / ra cám / tạp vụ
- `SYS3` — Hệ 3 — công nhân / bảo vệ thuộc Phòng trại

### Tại sao cần `next_value`

Thiết kế hiện tại dùng `MAX(employee_seq)+1`.  
Với nhiều hệ song song, cách đó không còn hợp lý.  

`employee_code_sequences.next_value` cho phép:

- lock đúng 1 row của hệ đang cấp số
- cấp số an toàn khi concurrent create/import
- không phải quét toàn bộ bảng `employees`

## 6.2. Bảng rule cấu hình hệ số

### `employee_code_sequence_rules`

```sql
CREATE TABLE employee_code_sequence_rules (
    id                          SERIAL PRIMARY KEY,
    scope_type                  VARCHAR(20) NOT NULL
                                    CHECK (scope_type IN ('department', 'job_position')),
    department_id               INTEGER REFERENCES departments(id) ON DELETE CASCADE,
    job_position_id             INTEGER REFERENCES job_positions(id) ON DELETE CASCADE,
    employee_code_sequence_id   INTEGER NOT NULL REFERENCES employee_code_sequences(id),
    apply_to_descendants        BOOLEAN NOT NULL DEFAULT FALSE,
    note                        TEXT,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP,

    CHECK (
        (scope_type = 'department'   AND department_id IS NOT NULL AND job_position_id IS NULL) OR
        (scope_type = 'job_position' AND job_position_id IS NOT NULL AND department_id IS NULL)
    )
);
```

### Ý nghĩa

- `department` rule: áp dụng cho cả một node tổ chức
- `apply_to_descendants = true`: cho phép một phòng/ban cha kéo theo bộ phận/nhóm/tổ con
- `job_position` rule: dùng cho ngoại lệ nghiệp vụ đặc thù

Ràng buộc bắt buộc bổ sung ở migration:

- tối đa **1 rule active exact-match** cho mỗi `department_id`
- tối đa **1 rule active exact-match** cho mỗi `job_position_id`
- không dùng `priority` ở phase đầu; nếu sau này cần nhiều rule cạnh tranh trên cùng một scope thì phải thiết kế lại thuật toán resolve thay vì để mơ hồ

## 6.3. Thay đổi trên bảng `employees`

Giữ lại `employee_seq` nhưng đổi nghĩa kỹ thuật:

- **trước đây**: số nguyên toàn cục toàn công ty
- **sau refactor**: số nguyên trong **hệ đã gán cho nhân viên**

Đề xuất thêm:

```sql
ALTER TABLE employees
    ADD COLUMN employee_code_sequence_id INTEGER
        REFERENCES employee_code_sequences(id);
```

Sau backfill xong:

```sql
ALTER TABLE employees
    ALTER COLUMN employee_code_sequence_id SET NOT NULL;
```

Đồng thời đổi unique index:

- **bỏ** unique toàn cục trên `employee_seq`
- **thêm** unique theo cặp:

```sql
CREATE UNIQUE INDEX uq_employees_sequence_value
ON employees (employee_code_sequence_id, employee_seq);
```

### Vì sao không đổi tên cột ngay

Không nên rename `employee_seq` ở đợt đầu vì:

- đang được dùng rất rộng ở backend, frontend, tests, seeds
- mục tiêu refactor trước hết là thay semantics và ràng buộc

Nếu sau này muốn làm sạch tên cột, có thể làm phase 2:

- `employee_seq` → `sequence_value`

### Tương thích ngược bắt buộc trước khi bỏ unique toàn cục

Đây là điểm phải xử lý rõ trong implementation plan:

- nhiều seed/tool nội bộ hiện vẫn đang dùng `employee_seq` như một khóa tra cứu toàn cục
- ví dụ seed employee dùng `ON CONFLICT (employee_seq)`, seed job record join bằng `WHERE e.employee_seq = :employee_seq`

Vì vậy trước khi drop unique toàn cục trên `employee_seq`, phải chốt một chiến lược tương thích:

1. hoặc chuyển toàn bộ consumer nội bộ sang `employee_id`
2. hoặc chuyển sang cặp `(employee_code_sequence_id, employee_seq)`
3. hoặc giữ một legacy key toàn cục riêng cho tooling nội bộ

Khuyến nghị của tài liệu này: **nội bộ hệ thống phải chuyển sang `employee_id`**; `employee_seq` không nên tiếp tục được dùng như khóa kỹ thuật toàn cục.

---

## 7. Thuật toán resolve hệ số

Đầu vào:

- `department_id`
- `job_position_id`

Thuật toán:

```text
0. Nếu có `job_position_id`, validate vị trí đó thuộc đúng `department_id`; nếu sai → reject 422
1. Nếu có rule active cho job_position_id hiện tại → dùng rule đó
2. Nếu không có:
   2.1. tìm rule active cho department_id hiện tại
   2.2. nếu không có, leo parent_id lên node cha gần nhất có rule + apply_to_descendants = true
3. Nếu vẫn không có → dùng sequence mặc định (SYS1)
```

Đây là thuật toán cần đóng gói thành 1 service duy nhất, ví dụ:

```python
resolve_employee_code_sequence(
    session,
    department_id: int | None,
    job_position_id: int | None,
) -> EmployeeCodeSequence
```

Mọi nơi cấp số mới chỉ được đi qua service này.

Service này cũng phải là nơi duy nhất quyết định:

- có chấp nhận `job_title_id` lệch với `job_position.job_title_id` hay không
- rule theo `job_position` còn hợp lệ hay đã bị vô hiệu vì vị trí bị move/delete

---

## 8. Thuật toán cấp số mới

Thay cho `MAX(employee_seq)+1`, dùng row lock trên `employee_code_sequences`.

Pseudo-code:

```python
async def allocate_employee_seq(session, sequence_id: int) -> tuple[int, int]:
    seq_row = (
        await session.execute(
            select(EmployeeCodeSequence)
            .where(EmployeeCodeSequence.id == sequence_id)
            .with_for_update()
        )
    ).scalar_one()

    value = seq_row.next_value
    seq_row.next_value = value + 1
    session.add(seq_row)

    return seq_row.id, value
```

Khi tạo employee:

1. resolve sequence
2. lock row sequence
3. lấy `next_value`
4. tăng `next_value`
5. ghi `employees.employee_code_sequence_id`
6. ghi `employees.employee_seq`

Lưu ý: concurrency của sequence allocator **không giải quyết** race condition trên `employees.id_number`.

Source hiện tại chỉ check trùng `id_number` ở application layer; migration của feature này cần đồng thời thêm unique constraint/index ở DB cho `employees.id_number`, rồi chuẩn hóa handling `409`/`IntegrityError` riêng cho trùng giấy tờ định danh.

---

## 9. Quy tắc bất biến của employee sau refactor

Khuyến nghị chốt 2 nguyên tắc:

1. **`employee_code_sequence_id` là bất biến sau khi cấp**
2. **`employee_seq` là bất biến sau khi cấp**

Điều này bám với logic hiện tại:

- nhân viên chuyển phòng thì prefix hiển thị đổi
- nhưng số gốc không đổi

Sau refactor:

- nhân viên chuyển sang đơn vị khác vẫn **không đổi hệ số** và **không đổi số**
- chỉ `display_code` đổi theo prefix hiển thị hiện hành nếu công ty vẫn giữ rule prefix động theo tổ chức

Ý nghĩa của rule `department/job_position` vì vậy phải được chốt rất rõ:

- rule chỉ áp dụng tại **thời điểm cấp mã lần đầu**
- sau khi đã cấp mã, transfer sang đơn vị thuộc hệ khác **không kích hoạt cấp lại mã**
- nếu business muốn “vào đơn vị nào thì phải mang mã của đơn vị đó”, đây là bài toán khác và tài liệu này không cover

Luồng `PUT /job-records/current` hiện có cũng phải được chốt rõ trong implementation:

- hoặc cấm sửa `department_id` / `job_position_id` bằng update-in-place sau khi đã cấp mã, chỉ cho sửa qua transfer
- hoặc vẫn cho sửa nhưng khẳng định rõ là **không cấp lại mã**

Nếu nghiệp vụ muốn “chuyển vị trí thì đổi luôn hệ số/mã số”, đó là một bài toán khác và không nên gộp vào refactor này.

---

## 10. Vấn đề lớn cần quyết định: cấp số lúc nào

Đây là chỗ source hiện tại chưa khớp với yêu cầu mới.

## 10.1. Vấn đề

Hiện tại:

- tạo `Employee` trước
- tạo `EmployeeJobRecord` sau

Nhưng hệ số mới lại phụ thuộc:

- `department`
- hoặc `job_position`

=> backend hiện tại **không thể tự resolve sequence đúng tại thời điểm tạo employee**.

## 10.2. Phương án khả thi

### Phương án A — Khuyến nghị

Mở rộng flow tạo nhân viên để có luôn **job hiện tại ban đầu**:

- `department_id`
- `job_position_id` (nullable)
- `job_title_id` (nullable)
- `effective_from`

Khi đó create flow chạy trong **một transaction**:

1. resolve sequence theo job/department
2. allocate số
3. insert `Employee`
4. insert `EmployeeJobRecord` đầu tiên

Đây là **breaking change** đối với API create hiện tại, frontend create hiện tại, và file import hiện tại.

### Phương án B — Tạm chấp nhận nhưng kém đẹp hơn

Cho phép create employee khi chưa có job, nhưng UI phải cho chọn thủ công:

- `employee_code_sequence_id`

Phương án này giải được kỹ thuật, nhưng kém hơn nghiệp vụ vì:

- HR phải hiểu “hệ mã” là gì
- dễ chọn sai nếu không đối chiếu job/department

### Phương án C — Cấp số khi tạo job record đầu tiên

Giữ employee chưa có số cho đến khi có job record.

Không khuyến nghị cho đợt refactor đầu vì:

- nhiều chỗ đang kỳ vọng employee có `display_code` ngay sau create
- kéo theo thay đổi lớn ở list/detail/import/export/reminders/contracts

## 10.3. Khuyến nghị chốt

**Khuyến nghị chọn Phương án A**:

- đúng nghiệp vụ nhất
- ít phát sinh “manual override”
- giữ tính nhất quán cao giữa hồ sơ nhân sự và công việc hiện hành

Nhưng rollout phải đi theo **2 phase tương thích**:

- **Phase tương thích**:
  - thêm schema/table mới
  - mở rộng API/UI/import để nhận initial job context hoặc explicit sequence
  - chưa bật reject cứng với caller cũ ngay
- **Phase enforce**:
  - sau khi UI create, import template và các caller liên quan đã chuyển xong
  - mới bật `422` khi thiếu job context / explicit sequence
  - mới siết `employee_code_sequence_id NOT NULL` cho toàn bộ luồng create mới

---

## 11. Tính duy nhất của mã hiển thị là precondition bắt buộc

Hiện tại mã hiển thị đang là:

```text
{department.display_prefix}{employee_seq}
```

Khi có nhiều hệ số, sẽ phát sinh rủi ro:

- nếu **cùng một prefix hiển thị** có thể chứa nhân viên thuộc nhiều hệ
- và các hệ có thể có cùng số `employee_seq`
- thì `display_code` có thể bị trùng

Ví dụ:

- nhân viên A thuộc prefix `PT`, Hệ 1, `employee_seq = 15` → `PT0015`
- nhân viên B cũng thuộc prefix `PT`, Hệ 3, `employee_seq = 15` → `PT0015`

=> **trùng mã hiển thị**

## 11.1. Hệ thống hiện tại chưa có cơ chế chống case này

Source hiện tại chỉ dựa vào:

- prefix phòng ban hiện tại
- số nguyên

Không có thêm marker hệ số.

## 11.2. Quyết định nghiệp vụ cần chốt trước khi code

Tài liệu này nâng điểm này từ “câu hỏi mở” thành **precondition bắt buộc**:

- chưa được code feature này khi business chưa chốt format và mức độ duy nhất của `display_code`
- vì employee list, export và nhiều màn hình khác đã hiển thị trực tiếp `display_code`

Business phải chốt 1 trong 3 hướng:

### Hướng 1 — Giữ format hiện tại

```text
{prefix phòng ban}{số}
```

Chỉ khả thi nếu công ty đảm bảo:

- một prefix hiển thị chỉ map về một hệ số duy nhất

### Hướng 2 — Thêm marker hệ số vào mã hiển thị

Ví dụ:

- `PK-1-1342`
- `PK-2-015`
- `PT-3-015`

Ưu điểm:

- loại bỏ trùng hiển thị

Nhược điểm:

- thay đổi format mã đang dùng thực tế

### Hướng 3 — Prefix hiển thị không lấy thuần từ phòng ban cha

Dùng prefix của:

- node tổ chức thấp hơn (`Tổ`, `Nhóm`, `Bộ phận`)
- hoặc prefix riêng của vị trí/nhóm nhân sự

Hướng này chỉ hợp lý nếu dữ liệu tổ chức thực tế đủ chi tiết để tách prefix.

## 11.3. Khuyến nghị

Nếu business xác nhận trong tương lai **cùng một phòng hiển thị vẫn có thể chứa nhiều hệ số**, thì:

- **không nên** giữ format `{department prefix}{number}` thuần
- phải thêm marker hệ số hoặc tách prefix hiển thị chi tiết hơn

Nếu business xác nhận mỗi prefix hiển thị luôn chỉ thuộc một hệ, có thể giữ format cũ.

Nếu business vẫn chấp nhận `display_code` trùng ở mức hiển thị, phải có tài liệu UX/API riêng mô tả:

- dropdown/search phân biệt nhân viên bằng gì
- export/list sắp xếp và hiển thị thế nào khi `display_code` trùng
- operator nội bộ dùng trường nào để tránh chọn nhầm người

---

## 12. Tương thích với dữ liệu hiện có

## 12.1. Backfill tối thiểu

Khuyến nghị backfill như sau:

1. Tạo 3 dòng trong `employee_code_sequences`
2. Gán **toàn bộ nhân viên hiện có** vào `SYS1`
3. Giữ nguyên `employee_seq` hiện tại
4. Set `SYS1.next_value = MAX(employees.employee_seq) + 1`
5. `SYS2.next_value = 1`
6. `SYS3.next_value = 1`

Ưu điểm:

- không đổi mã cũ
- ít rủi ro nhất
- không ảnh hưởng hợp đồng, nghỉ phép, audit log, export cũ

Điều kiện để phương án backfill này khả thi:

- format `display_code` sau go-live đã được chốt
- các consumer nội bộ đang dùng `employee_seq` toàn cục đã được refactor khỏi giả định đó

## 12.2. Không khuyến nghị renumber dữ liệu cũ trong đợt đầu

Nếu cố chuyển nhân viên cũ sang SYS2/SYS3 ngay trong migration:

- sẽ phải thay lại `employee_seq`
- kéo theo thay đổi `display_code`
- tăng rủi ro đối soát giấy tờ, hợp đồng, file export đã dùng

Khuyến nghị:

- dữ liệu cũ giữ nguyên trong `SYS1`
- chỉ nhân viên tạo mới sau mốc go-live mới đi theo rule 3 hệ

Nếu chưa xử lý xong 2 điều kiện trên, không nên go-live dù migration schema đã sẵn sàng.

Nếu business bắt buộc hồi tố, cần một tài liệu migration/backfill riêng và sign-off rõ ràng.

---

## 13. Ảnh hưởng tới import/export

Đã kiểm tra:

- [backend/app/services/employee_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_import_service.py:1)
- [backend/app/services/employee_export_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_export_service.py:1)

## 13.1. Import

Import hiện tại:

- tạo employee trước
- nếu có department thì tạo job record sau

Import hiện tại còn có 2 đặc điểm phải đổi nếu áp dụng rule mới:

- file mẫu chưa có `Vị trí công việc`
- import vẫn cho phép thiếu hoặc không resolve được `Phòng ban` mà vẫn tạo employee thành công

Sau refactor, import phải đổi contract theo hướng rõ ràng hơn:

- bổ sung `Vị trí công việc` nếu muốn rule `job_position` thắng `department`
- bổ sung cột override `Hệ mã nhân viên` cho dữ liệu ngoại lệ / legacy
- trước khi bật allocator mới, case không resolve được department/rule phải thành **hard validation failure**, không còn là warning rồi vẫn tạo employee

Khuyến nghị thêm 1 cột tùy chọn trong template:

- `Hệ mã nhân viên`

Chỉ dùng cho:

- dữ liệu legacy
- trường hợp import không đủ thông tin job để suy ra tự động

Khuyến nghị thêm 1 cột nữa:

- `Vị trí công việc`

## 13.2. Export danh sách

Export danh sách hiện đã tự ghép `display_code` từ prefix hiện tại.

Sau refactor:

- vẫn phải chuẩn hóa về helper chung `compute_employee_display_code(...)`
- mọi list export chỉ gọi helper này

## 13.3. Export hồ sơ chi tiết

Export hồ sơ chi tiết hiện chưa có dòng `Mã NV` trong sheet thông tin cá nhân.

Business cần chốt rõ:

- có bổ sung `Mã NV` chuẩn vào hồ sơ chi tiết hay không

Khuyến nghị:

- nên bổ sung để tất cả output đối ngoại dùng cùng một mã hiển thị chuẩn

---

## 14. Ảnh hưởng tới API / service / frontend

## 14.1. Backend cần tác động

### Bảng / model / migration

- `backend/app/models/employee.py`
- `backend/app/models/employee_job.py`
- `backend/app/models/org.py`
- migration mới sau `0015`

### Service

- `backend/app/services/employee_service.py`
- `backend/app/services/employee_job_service.py`
- `backend/app/services/employee_import_service.py`
- `backend/app/services/employee_export_service.py`
- `backend/app/services/leave_entitlement_service.py`
- `backend/app/services/leave_record_service.py`
- `backend/app/services/leave_report_service.py`
- `backend/app/services/employee_contract_service.py`
- `backend/app/services/reminder_service.py`

### Endpoint / schema

- `backend/app/api/v1/endpoints/employees.py`
- `backend/app/schemas/employee.py`
- các schema đang trả `employee_code`
- seed/tooling nội bộ đang còn dùng `employee_seq` toàn cục

## 14.2. Frontend cần tác động

- `frontend/src/services/employeeService.ts`
- `frontend/src/views/employees/EmployeeDetailView.vue`
- `frontend/src/views/employees/EmployeeListView.vue`
- `frontend/src/views/employees/ImportDialog.vue`
- `frontend/src/views/leaves/LeaveEntitlementView.vue`
- `frontend/src/views/leaves/LeaveListView.vue`
- `frontend/src/views/leaves/LeaveReportView.vue`
- `frontend/src/views/contracts/ContractListView.vue`
- `frontend/src/views/RemindersView.vue`

## 14.3. Chuẩn hóa nguồn `employee_code`

Khuyến nghị mọi API response chỉ dùng 1 rule:

- `employee_code` luôn là **mã hiển thị chuẩn**
- không trả lẫn `id_number`
- không trả raw `employee_seq` ở chỗ UI đang hiểu là mã

---

## 15. Đề xuất thay đổi schema/API

## 15.1. `EmployeeCreate`

Khuyến nghị mở rộng để hỗ trợ create đúng hệ:

```python
class EmployeeCreate(BaseModel):
    ...
    initial_department_id: int | None = None
    initial_job_title_id: int | None = None
    initial_job_position_id: int | None = None
    initial_job_effective_from: date | None = None

    # fallback cho import / dữ liệu ngoại lệ
    employee_code_sequence_id: int | None = None
```

Rule ở phase cuối:

- nếu có `initial_job_position_id` / `initial_department_id` → auto resolve
- nếu không có, cho phép dùng `employee_code_sequence_id` explicit
- nếu cả hai đều không có → reject `422`
- nếu `initial_job_position_id` không thuộc `initial_department_id` → reject `422`

Rule ở phase tương thích:

- có thể tạm accept payload cũ trong lúc UI/import chưa migrate xong
- nhưng chưa được bật allocator 3 hệ cho caller đó

## 15.2. `EmployeeRead`

Nên bổ sung:

```python
employee_code_sequence_id: int
```

Không nhất thiết phải show trên UI phổ thông, nhưng cần cho admin/debug/import đối soát.

---

## 16. Đề xuất migration / rollout

## Bước 1 — Schema scaffolding an toàn

Tạo migration mới, ví dụ `0016_refactor_employee_code_sequences.py`:

1. tạo `employee_code_sequences`
2. tạo `employee_code_sequence_rules`
3. thêm `employees.employee_code_sequence_id` nhưng **chưa set NOT NULL**
4. thêm unique constraint/index cho `employees.id_number`
5. seed `SYS1`, `SYS2`, `SYS3`
6. backfill toàn bộ employee cũ → `SYS1`
7. set `SYS1.next_value = MAX(employee_seq)+1`
8. tạo các partial unique index:
   - đúng 1 active default sequence
   - 1 active rule / department
   - 1 active rule / job_position

## Bước 2 — Refactor caller và seam cấp mã

1. tách `employee_code_service.py`
2. chuẩn hóa:
   - resolve rule
   - allocate value
   - compute display code chuẩn
3. cập nhật API create
4. cập nhật frontend create flow để lấy initial job context
5. cập nhật import template và import processor
6. cập nhật validation chéo `department_id` ↔ `job_position_id`
7. cập nhật seed/tooling nội bộ để không còn coi `employee_seq` là khóa toàn cục

## Bước 3 — Enforce allocator mới

Chỉ làm bước này khi toàn bộ caller chính đã migrate xong:

1. bật logic cấp mã theo `employee_code_sequence_id`
2. đổi unique từ global `employee_seq` sang `(employee_code_sequence_id, employee_seq)`
3. set `employees.employee_code_sequence_id NOT NULL`
4. reject `422` với create/import không có đủ context

## Bước 4 — Chuẩn hóa toàn hệ thống

Thay toàn bộ nơi đang trả `employee_code` về cùng helper chuẩn.

---

## 17. Test plan bắt buộc

## 17.1. Backend

### Rule resolution

- job position rule thắng department rule
- department exact thắng parent inherited rule
- không có rule thì fallback SYS1

### Allocation

- tạo 2 nhân viên cùng hệ → seq tăng đúng 1
- tạo 2 nhân viên khác hệ → mỗi hệ tăng độc lập
- import explicit seq/system → validate không conflict
- concurrent create cùng hệ → không cấp trùng
- concurrent create/import trùng `id_number` → DB chặn được, trả lỗi đúng
- explicit seq lớn hơn `next_value` → cơ chế cập nhật `next_value` sau import phải được define và test rõ

### Employee lifecycle

- create employee với initial department/job → cấp đúng system
- transfer job record → `employee_code_sequence_id` không đổi
- đổi prefix phòng ban → `display_code` đổi theo prefix nếu business giữ rule prefix động
- update current job record đổi `department_id` / `job_position_id` → không cấp lại mã, hoặc bị chặn; phải test đúng theo quyết định cuối
- create/transfer/import với `job_position_id` không thuộc `department_id` → reject `422`

### Module integration

- leave entitlement trả `employee_code` chuẩn
- leave record trả `employee_code` chuẩn
- leave report trả `employee_code` chuẩn
- contract global list trả `employee_code` chuẩn
- reminder trả `employee_code` chuẩn, không còn dùng `id_number`
- lookup employee trả `display_code` chuẩn có prefix nếu có
- export danh sách dùng cùng helper chuẩn
- nếu bổ sung `Mã NV` vào hồ sơ chi tiết thì export hồ sơ cũng phải dùng cùng helper chuẩn
- seed re-run vẫn idempotent sau khi bỏ unique toàn cục trên `employee_seq`
- migration backfill `SYS1` đúng và không làm lệch dữ liệu cũ

## 17.2. Frontend

- sau khi create flow được redesign để nhập initial job context, create employee mới chọn đúng job/department → mã hiển thị đúng sau save
- import có dòng thuộc Hệ 2 / Hệ 3 → kết quả hiển thị đúng
- các màn Employee / Leave / Contract / Reminder hiển thị cùng một mã
- browser-level verify cho lookup/dropdown nếu `display_code` không còn là khóa hiển thị duy nhất toàn cục

---

## 18. Thứ tự triển khai khuyến nghị

1. Chốt nghiệp vụ về format mã hiển thị nếu nhiều hệ có thể cùng một prefix
2. Chốt business có còn support “draft employee chưa có job context” hay không
3. Tạo bảng `employee_code_sequences` + `employee_code_sequence_rules`
4. Backfill toàn bộ nhân viên cũ vào `SYS1` + thêm unique DB cho `id_number`
5. Refactor allocator khỏi `employee_service.next_employee_seq()`
6. Migrate create flow, import template, import processor, seed/tooling nội bộ
7. Siết validation chéo `job_position` ↔ `department`
8. Chỉ sau đó mới drop unique toàn cục trên `employee_seq`
9. Chuẩn hóa toàn bộ nơi trả `employee_code`
10. Cập nhật tests + seed
11. Verify end-to-end Employee → Leave → Contract → Reminder

---

## 19. Kết luận / khuyến nghị cuối

### Khuyến nghị chính

- Dùng **3 bảng logic**:
  - `employee_code_sequences`
  - `employee_code_sequence_rules`
  - `employees.employee_code_sequence_id`
- Dùng **rule hybrid**:
  - `job_position` override
  - `department` + inheritance
  - fallback `SYS1`
- Dùng **row-lock allocator** theo từng hệ, không dùng `MAX+1` toàn bảng nữa
- Giữ `employee_seq` là số bất biến sau khi cấp

### Điểm cần business chốt trước khi code

1. Có giữ nguyên format hiển thị `{prefix phòng ban}{số}` hay không?
2. Nếu cùng một prefix có thể chứa nhiều hệ, công ty có chấp nhận trùng hiển thị không?
3. Có chấp nhận đổi flow tạo nhân viên để nhập luôn job hiện tại hay không?
4. Dữ liệu cũ có cần hồi tố sang SYS2/SYS3 không, hay chỉ áp dụng cho nhân viên mới?
5. Rule theo `department/job_position` có chỉ áp dụng tại lần cấp mã đầu tiên hay có yêu cầu đổi mã khi chuyển công tác?
6. Công ty có còn cần luồng “tạo nháp nhân viên chưa có job context” sau go-live hay không?

### Khuyến nghị triển khai thực tế

Nếu muốn rủi ro thấp nhất:

- **không hồi tố dữ liệu cũ**
- dữ liệu cũ giữ ở `SYS1`
- từ ngày go-live mới, nhân viên mới đi theo rule 3 hệ

Đây là phương án ít phá vỡ nhất đối với source code hiện tại và phù hợp nhất với hiện trạng đã verify.
