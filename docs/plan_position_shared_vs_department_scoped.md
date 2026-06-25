# Kế hoạch xử lý Position dùng riêng theo đơn vị và Position dùng chung nhiều đơn vị

## 1. Kết luận sau khi rà source code hiện tại

Kết luận đã được kiểm chứng từ source code hiện tại: hệ thống **chưa xử lý đủ** cho cả 2 kiểu position mà công ty đang có.

- Kiểu 1: `Position thuộc về đúng 1 phòng/ban`  
  Hệ thống hiện tại hỗ trợ tốt theo mô hình này.
- Kiểu 2: `Position không thuộc về 1 phòng/ban cụ thể, mà được dùng lặp lại ở nhiều đơn vị`  
  Hệ thống hiện tại **không hỗ trợ đúng về mặt mô hình dữ liệu và luồng nghiệp vụ**.

## 2. Bằng chứng đã kiểm tra

### 2.1. Model dữ liệu hiện tại đang khóa Position vào đúng 1 Department

Trong [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py), model `JobPosition` có:

- `department_id: int = Field(foreign_key="departments.id")`

Điều này xác nhận mỗi `job_positions` row bắt buộc thuộc đúng 1 đơn vị.

### 2.2. CRUD Position bắt buộc chọn phòng/ban

Trong [backend/app/schemas/job_position.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/schemas/job_position.py):

- `JobPositionCreate.department_id` là field bắt buộc.

Trong [frontend/src/views/org/PositionListView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/org/PositionListView.vue):

- form tạo/sửa có field `Phòng/Ban *`
- validate frontend bắt buộc `form.department_id`

Trong [backend/app/services/job_position_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/job_position_service.py):

- `create()` gọi `_require_department(session, data.department_id)`
- `get_list()` join trực tiếp `JobPosition.department_id == Department.id`

=> CRUD hiện tại chỉ phù hợp với kiểu 1.

### 2.3. Khi gán Position cho nhân sự, backend ép Position phải cùng Department

Trong [backend/app/services/employee_job_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_job_service.py):

- `_validate_job_assignment()` kiểm tra:
  - nếu `job_position.department_id != department_id` thì trả lỗi  
    `"Vị trí công việc không thuộc phòng ban đã chọn"`

Trong [backend/app/services/employee_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_service.py):

- `_resolve_initial_job_context()` cũng ép:
  - nếu `job_position.department_id != department.id` thì lỗi tương tự

=> Dù UI có cho chọn tự do, backend hiện vẫn không cho một position dùng chung nhiều đơn vị.

### 2.4. Import nhân viên cũng đang phụ thuộc Position theo Department

Trong [backend/app/services/employee_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_import_service.py):

- `_find_job_position(..., department_id=dept_id)` chỉ tìm position trong department đã chọn
- nếu không khớp thì trả lỗi:
  - `"Muốn gán vị trí công việc thì phải xác định được phòng ban"`
  - `"Vị trí công việc ... không thuộc phòng ban đã chọn"`

=> Import nhân viên đang bám chặt vào mô hình Position thuộc một đơn vị cụ thể.

### 2.5. Tuyển dụng cũng đang ép Position phải thuộc Department

Trong [backend/app/services/hiring_decision_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/hiring_decision_service.py):

- `_validate_dept_position()` kiểm tra `jp.department_id != department_id` thì báo lỗi.

Trong [frontend/src/views/recruitment/components/JRFormDialog.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/recruitment/components/JRFormDialog.vue):

- chọn `Vị trí công việc`
- sau đó tự fill `department_id = pos.department_id`

Trong [frontend/src/views/recruitment/components/OfferFormDialog.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/recruitment/components/OfferFormDialog.vue) và [frontend/src/views/recruitment/components/HiringDecisionDialog.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/recruitment/components/HiringDecisionDialog.vue):

- `department_id` và `job_position_id` vẫn được lưu song song

=> Tuyển dụng hiện tại coi Position là một thực thể gắn sẵn với 1 Department.

### 2.6. Một số tính năng khác đang gắn theo Position row cụ thể

Các phần sau đang neo trực tiếp vào `job_position_id`, tức là nếu phải nhân bản position cho nhiều đơn vị thì cấu hình cũng bị nhân bản:

- Nhóm vị trí BHXH  
  [backend/app/models/salary.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/salary.py)  
  `BhxhPositionGroupMember.job_position_id` còn đặt `unique=True`
- Rule hệ mã nhân viên theo position  
  [backend/app/models/employee_code.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_code.py)
- Phỏng vấn / scorecard template theo position  
  [backend/app/models/recruitment.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/recruitment.py)
- File đính kèm position, JD, probation legal group, phụ cấp BHXH/non-BHXH  
  [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py)

=> Nếu workaround bằng cách tạo nhiều position bản sao cho từng trại, hệ thống vẫn chạy được ở mức kỹ thuật, nhưng dữ liệu cấu hình sẽ bị lặp, dễ lệch, khó vận hành.

## 3. Đánh giá theo 2 kiểu position thực tế của công ty

### 3.1. Kiểu 1: Position thuộc về 1 phòng/ban cụ thể

Ví dụ: `Bộ phận IT` có các position riêng như:

- Nhân viên IT tổng hợp
- Chuyên viên IT

Source code hiện tại xử lý tốt cho kiểu này.

### 3.2. Kiểu 2: Position dùng lặp lại ở nhiều đơn vị cùng loại

Ví dụ trong `Phòng Trại` có nhiều trại con:

- Trại 1
- Trại 2
- Trại 3
- ...

Mỗi trại đều có cùng bộ position:

- Trưởng trại
- Công nhân kỹ thuật
- Công nhân
- Kỹ thuật trại
- Admin trại
- Bảo vệ trại

Source code hiện tại **không hỗ trợ đúng** cho nhu cầu này, vì:

- một position row chỉ gắn được 1 `department_id`
- mọi validate backend hiện tại đều ép `position.department_id == department_id đang chọn`
- import, employee job record, tuyển dụng đều dựa trên giả định đó

## 4. Workaround hiện tại có thể làm được nhưng không nên dùng làm mô hình chính

Có thể vận hành bằng cách:

- tạo `Trưởng trại - Trại 1`
- tạo `Trưởng trại - Trại 2`
- tạo `Trưởng trại - Trại 3`
- ...

hoặc cùng tên nhưng khác mã position.

Về kỹ thuật, cách này tương thích với source hiện tại. Tuy nhiên đây chỉ là workaround, vì sẽ gây:

- lặp cấu hình probation legal group
- lặp cấu hình phụ cấp BHXH / không BHXH
- lặp cấu hình nhóm vị trí BHXH
- lặp rule hệ mã nhân viên theo position
- lặp tài liệu JD / attachment
- khó đồng bộ khi một loại position thay đổi chính sách

## 5. Phương án đề xuất

### 5.1. Hướng đề xuất

Nên chuyển sang mô hình 2 lớp:

- `Position master/template`
  - đại diện cho loại vị trí dùng chung toàn công ty hoặc dùng chung trong một nhóm đơn vị
  - ví dụ: `Trưởng trại`, `Công nhân kỹ thuật`, `Admin trại`
- `Department-Position assignment`
  - khai báo một position master được phép dùng ở những đơn vị nào
  - ví dụ:
    - `Trưởng trại` áp dụng cho `Trại 1`
    - `Trưởng trại` áp dụng cho `Trại 2`
    - `Trưởng trại` áp dụng cho `Trại 3`

### 5.2. Vì sao hướng này phù hợp hơn

Hướng này giữ được cả 2 kiểu cùng lúc:

- position riêng của một đơn vị  
  => chỉ gán master đó cho 1 đơn vị
- position dùng chung nhiều đơn vị  
  => gán cùng 1 master cho nhiều đơn vị

Ngoài ra, các cấu hình cấp position chỉ cần khai báo 1 lần:

- chức danh mặc định
- bậc mặc định
- phụ cấp BHXH
- phụ cấp không BHXH
- probation legal group
- file JD/attachment
- nhóm vị trí BHXH
- rule hệ mã nhân viên theo position

## 6. Thiết kế dữ liệu đề xuất

### 6.1. Tách `job_positions` thành thực thể master

Đề xuất đổi ý nghĩa `job_positions` thành position master, không còn bắt buộc `department_id`.

Trường hợp muốn giảm phá vỡ schema, có 2 lựa chọn:

- Lựa chọn A: giữ bảng `job_positions`, cho `department_id` nullable và thêm bảng mapping
- Lựa chọn B: tạo bảng mới `department_job_positions`, còn `job_positions` trở thành master hoàn toàn

Khuyến nghị: **Lựa chọn B** sạch hơn về domain, nhưng thay đổi lớn hơn.  
Nếu cần triển khai an toàn theo từng bước, nên đi theo **Lựa chọn A trước**, rồi mới refactor tiếp.

### 6.2. Bảng mapping mới

Đề xuất bảng:

- `department_job_positions`

Các cột chính:

- `id`
- `department_id`
- `job_position_id`
- `is_active`
- `created_at`
- `updated_at`

Ràng buộc:

- unique `(department_id, job_position_id)`

Ý nghĩa:

- một position có thể áp dụng cho nhiều department
- một department có thể có nhiều position

## 7. Thay đổi nghiệp vụ cần có

### 7.1. CRUD Position

Tách thành 2 phần:

- CRUD `Position master`
  - mã position
  - tên position
  - chức danh mặc định
  - bậc mặc định
  - phụ cấp
  - probation legal group
  - attachment
- màn `Gán position cho đơn vị`
  - chọn một position master
  - chọn các đơn vị áp dụng

### 7.2. Khi chọn Position ở các module khác

Các module như:

- Nhân viên
- Import nhân viên
- Job record
- JR
- Offer
- Hiring decision

không nên chỉ lấy danh sách position toàn cục, mà phải lấy:

- danh sách position hợp lệ theo department đang chọn

Nguồn dữ liệu lúc đó phải là:

- `department_job_positions`

### 7.3. Backend validation

Các rule hiện tại dạng:

- `job_position.department_id == department_id`

cần đổi thành:

- tồn tại mapping active trong `department_job_positions`

Áp dụng cho:

- `employee_service`
- `employee_job_service`
- `employee_import_service`
- `hiring_decision_service`
- các service tuyển dụng khác có validate tương tự

## 8. Ảnh hưởng tới dữ liệu hiện hữu

### 8.1. Dữ liệu hiện tại có thể migrate được

Vì hiện tại mỗi `job_position` đã có sẵn `department_id`, nên có thể migrate theo nguyên tắc:

- với mỗi `job_positions` row hiện có
  - tạo 1 mapping tương ứng trong `department_job_positions`

Nếu vẫn giữ `job_positions.department_id` tạm thời trong giai đoạn chuyển tiếp:

- coi đó là `legacy source`
- sinh mapping trước
- sau khi toàn bộ code chuyển sang dùng mapping thì mới bỏ phụ thuộc trực tiếp vào `job_positions.department_id`

### 8.2. Các cấu hình đang bám vào `job_position_id`

Ưu điểm của phương án master + mapping:

- `job_position_id` hiện tại vẫn giữ được
- các module như BHXH group, interview template, employee code rule không cần nhân bản dữ liệu theo từng department

## 9. Đề xuất lộ trình triển khai

### Slice 1 — Chuẩn bị dữ liệu

- thêm bảng `department_job_positions`
- backfill mapping từ `job_positions.department_id`
- thêm service/query lấy position theo department qua mapping

Trạng thái triển khai:

- Hoàn thành backend migration `department_job_positions`
- Đã backfill mapping từ `job_positions.department_id`
- Đã thêm service/query backend để resolve position hợp lệ theo department qua mapping
- Đã kiểm chứng bằng test backend và runtime check DB ngày `2026-06-24`

### Slice 2 — Chuyển validation backend

- `employee_service`
- `employee_job_service`
- `employee_import_service`
- `hiring_decision_service`
- các service tuyển dụng liên quan

Thay toàn bộ check:

- `position.department_id == department_id`

thành:

- `position được gán active cho department`

Trạng thái triển khai:

- Đã chuyển validation ở `employee_service`
- Đã chuyển validation ở `employee_job_service`
- Đã chuyển lookup/import ở `employee_import_service`
- Đã chuyển validation ở `hiring_decision_service`
- Đã kiểm chứng bằng regression tests backend ngày `2026-06-24`
- Chưa bao gồm UI/FE picker, vẫn thuộc các slice sau

### Slice 3 — FE danh mục Position

- tách UI `Position master`
- thêm UI `Gán position cho đơn vị`
- sửa filter/list để hiển thị rõ:
  - position dùng riêng
  - position dùng ở nhiều đơn vị

Trạng thái triển khai:

- Đã bổ sung UI `Đơn vị áp dụng` trong màn `Vị trí công việc`
- Đã hiển thị rõ `Đơn vị quản lý` và `Phạm vi áp dụng`
- Đã trả dữ liệu `assigned_department_ids`, `assigned_departments`, `is_shared` từ backend để FE render
- Đã kiểm chứng bằng `npm run build` và browser loop ngày `2026-06-24`

### Slice 4 — FE các module chọn Position

- Nhân sự
- Import dữ liệu
- Tuyển dụng
- BHXH nếu có picker position

Các dropdown position phải load theo department đang chọn.

Trạng thái triển khai:

- Đã chuyển màn tạo nhân viên mới sang load position theo `department_id`
- Đã chuyển `Job record` / điều chuyển công việc sang load position theo `department_id`
- Đã chuyển các dialog tuyển dụng:
  - `JRFormDialog`
  - `OfferFormDialog`
  - `HiringDecisionDialog`
  - `HeadcountPlanTab`
- Đã bổ sung backend validation cho `Headcount Plan` và `JR` để không thể bypass bằng API call sai mapping
- Đã kiểm chứng bằng regression tests backend và browser loop ngày `2026-06-24` cho:
  - `PositionListView`
  - `EmployeeDetailView` (route tạo mới)
  - `HeadcountPlanTab`
  - `JRFormDialog`
- Chưa có browser loop riêng cho `OfferFormDialog` và `HiringDecisionDialog`; hai màn này đã được build pass và cùng dùng pattern load theo `department_id` đã áp dụng ở các dialog trên

### Slice 5 — Dọn legacy

- sau khi mọi module đã dùng mapping
- mới xem xét bỏ phụ thuộc trực tiếp vào `job_positions.department_id`

Trạng thái triển khai:

- Đã dọn legacy ở lớp validate/picker nghiệp vụ: không còn dùng rule `position.department_id == department_id` cho các luồng nhân sự và tuyển dụng đã nêu ở trên
- `job_positions.department_id` hiện vẫn được giữ như `đơn vị quản lý/owner department` cho màn danh mục Position và một số báo cáo/cấu hình liên quan
- Việc giữ cột này là chủ đích của giai đoạn chuyển tiếp, không còn là nguồn validate gán position vào department
- `JRListTab` vẫn load danh sách position toàn cục cho **bộ lọc danh sách**; đây không phải picker phụ thuộc department nên không xem là bug của slice này

## 10. Khuyến nghị cuối cùng

Khuyến nghị triển khai theo hướng:

- **Position là master dùng chung**
- **Department chỉ là nơi được phép sử dụng position đó**

Đây là mô hình phù hợp nhất với thực tế công ty đang có cả:

- position riêng theo đơn vị
- position lặp lại ở nhiều đơn vị cùng loại

Nếu không làm theo hướng này, hệ thống vẫn có thể chạy bằng cách nhân bản position theo từng đơn vị, nhưng sẽ phát sinh nợ dữ liệu và chi phí vận hành cao.
