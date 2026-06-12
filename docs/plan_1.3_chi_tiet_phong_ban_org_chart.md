# Kế hoạch trang chi tiết Phòng ban và sơ đồ nhân sự

**Phạm vi chính:** trang chi tiết 1 phòng/ban · headcount trực tiếp và toàn cây · org chart bằng PrimeVue `OrganizationChart` · cơ chế xác định người đứng đầu đơn vị · ảnh thẻ tại node

**Tình trạng:** draft thiết kế, chưa triển khai.

---

## 1. Kết luận review source hiện tại

### 1.1. Cây phòng ban đã có

Đã xác nhận:

- `departments.parent_id` đang biểu diễn quan hệ cha/con ở [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py:17)
- API cây phòng ban đã có ở [backend/app/api/v1/endpoints/departments.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/departments.py:18)
- service build tree đã có ở [backend/app/services/department_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/department_service.py:91)

Kết luận:

- nền tảng để hiển thị subtree của một phòng ban đã có
- chưa có trang chi tiết phòng ban riêng

### 1.2. Quan hệ nhân viên với phòng ban đang nằm ở `employee_job_records`

Đã xác nhận:

- `employee_job_records.department_id`
- `employee_job_records.job_title_id`
- `employee_job_records.job_position_id`
- `employee_job_records.is_current`

ở [backend/app/models/employee_job.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_job.py:20)

Kết luận:

- headcount hiện hành phải lấy từ `employee_job_records` với `is_current = TRUE`
- không nên lấy từ bảng `employees`

### 1.3. Chưa có cơ chế xác định người đứng đầu đơn vị

Đã xác nhận:

- model `Department` không có `head_employee_id`
- model `EmployeeJobRecord` không có cờ kiểu `is_department_head`

ở:

- [backend/app/models/org.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/org.py:17)
- [backend/app/models/employee_job.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_job.py:20)

Kết luận:

- source hiện tại **chưa đủ dữ liệu** để render org chart đúng theo yêu cầu “người đứng đầu phòng/ban/tổ/nhóm”
- không được suy luận người đứng đầu từ `job_title.level`

### 1.4. Hệ thống đã có foundation headcount theo cây phòng ban

Đã xác nhận:

- service báo cáo cơ cấu tổ chức đã tính:
  - `direct_headcount`
  - `total_headcount`
  - `children`
  - `by_job_title`

ở [backend/app/services/hr_report_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/hr_report_service.py:482)

Kết luận:

- có thể reuse logic subtree/headcount thay vì viết lại từ đầu

### 1.5. Ảnh thẻ hiện đang có 2 bề mặt dữ liệu

Đã xác nhận:

- `employees.avatar_path` tồn tại ở [backend/app/models/employee.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee.py:93)
- attachment loại `avatar` tồn tại ở [backend/app/models/employee_attachment.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_attachment.py:14)
- upload attachment hiện chỉ ghi vào `employee_attachments`, chưa thấy source xác nhận tự đồng bộ sang `employees.avatar_path`

Kết luận:

- trước khi dựng org chart, phải chốt nguồn ảnh chuẩn

---

## 2. Yêu cầu nghiệp vụ chốt

Trang chi tiết Phòng ban cần có:

1. hiển thị số lượng nhân viên đang có của phòng
2. hiển thị số lượng nhân viên toàn cây gồm cả đơn vị con
3. hiển thị sơ đồ nhân sự dạng org chart
4. tôn trọng quan hệ cha/con giữa các phòng/ban/bộ phận/nhóm/tổ
5. có cơ chế xác định người đứng đầu mỗi đơn vị
6. tại mỗi node, hiển thị:
   - ảnh
   - họ tên
   - vị trí

**Lưu ý nghiệp vụ bổ sung đã chốt:** thực tế có trường hợp **1 Employee quản lý 1 hoặc nhiều đơn vị khác nhau**.

Kết luận từ yêu cầu này:

- mô hình dữ liệu không được ép `1 employee -> chỉ đứng đầu 1 đơn vị`
- quan hệ đúng phải là:
  - `1 department -> tối đa 1 head hiện hành`
  - `1 employee -> có thể head nhiều department`

---

## 3. Phạm vi UX đề xuất

### 3.1. Route mới

Tạo route mới:

- `/org/departments/:id`

Từ màn [DepartmentListView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/org/DepartmentListView.vue:1):

- tên phòng/ban bấm vào để vào trang chi tiết

### 3.2. Bố cục trang

Trang chi tiết nên có 3 khối:

1. `Header tổng quan`
   - tên đơn vị
   - mã
   - loại đơn vị
   - đơn vị cha
   - trạng thái

2. `Summary cards`
   - số nhân viên trực tiếp
   - số nhân viên toàn subtree
   - số đơn vị con trực tiếp
   - số vị trí công việc của đơn vị
   - người đứng đầu hiện tại

3. `Sơ đồ nhân sự`
   - PrimeVue `OrganizationChart`
   - node gốc là đơn vị đang xem
   - các node con là các đơn vị thuộc subtree

4. `Danh sách nhân sự trực tiếp`
   - bảng đối soát
   - hiển thị các nhân viên hiện đang thuộc đúng đơn vị đó

### 3.3. Phạm vi node trên org chart

Không nên nhét toàn bộ nhân viên của mỗi phòng vào org chart.

Node nên biểu diễn:

- `đơn vị`
- `người đứng đầu đơn vị`

Lý do:

1. đúng với nhu cầu sơ đồ quản lý
2. nhẹ hơn nhiều
3. dễ đọc hơn với cây nhiều cấp

Danh sách toàn bộ nhân sự trực tiếp sẽ hiển thị ở bảng bên dưới.

---

## 4. Thiết kế dữ liệu cho người đứng đầu đơn vị

## 4.1. Không khuyến nghị dùng `departments.head_employee_id`

Không khuyến nghị thêm thẳng:

- `departments.head_employee_id`

Lý do:

1. lịch sử bổ nhiệm sẽ tách rời lịch sử công việc
2. khó audit khi đổi trưởng đơn vị
3. không bám lifecycle của `employee_job_records`

## 4.2. Phương án khuyến nghị

Phương án khuyến nghị cuối cùng là tạo bảng quan hệ riêng:

- `department_heads`

Không nhét metadata head vào `employee_job_records` ngay ở phase đầu.

Ví dụ các cột nghiệp vụ:

- `department_id`
- `employee_id`
- `job_position_id` nullable
- `head_role_label`
- `effective_from`
- `effective_to`
- `is_current`

Ví dụ `head_role_label`:

- `Trưởng phòng`
- `Trưởng bộ phận`
- `Tổ trưởng`
- `Phụ trách`

### 4.3. Rule dữ liệu

Rule chốt:

1. một `department` tại một thời điểm chỉ có tối đa `1` người đứng đầu hiện hành
2. một `employee` có thể đứng đầu `nhiều` department khác nhau
3. người đứng đầu phải là một employee hợp lệ, đang active trong hệ thống
4. nếu có bản ghi công việc current ở chính `department_id` đó thì phải ưu tiên dùng để hiển thị `job_position_name`
5. trường hợp một người quản lý chéo nhiều đơn vị, vẫn chỉ được có tối đa 1 head current trên mỗi đơn vị

### 4.4. Constraint DB đề xuất

Tạo partial unique index trên bảng `department_heads`:

```sql
UNIQUE (department_id)
WHERE is_current = TRUE
```

Index này đảm bảo:

- một đơn vị không có 2 head hiện hành
- không chặn case 1 employee làm head của nhiều đơn vị

### 4.5. Trường hợp một người quản lý nhiều đơn vị

Case này phải được hỗ trợ chính thức.

Thiết kế vận hành:

1. cùng một `employee_id` có thể xuất hiện ở nhiều dòng `department_heads`
2. mỗi dòng tương ứng một đơn vị khác nhau
3. các dòng đó đều có thể `is_current = TRUE` nếu employee đang đồng thời phụ trách nhiều đơn vị

Điểm cần làm rõ thêm khi implement:

- khi employee là head của đơn vị khác với đơn vị công tác chính, node sẽ hiển thị `job_position_name` nào

Theo model hiện tại, `employee_job_records` đang có unique:

- tối đa 1 record `is_current = TRUE` cho mỗi employee

ở [backend/app/models/employee_job.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_job.py:83)

**Kết luận kiến trúc:** vì requirement “1 employee quản lý nhiều đơn vị” là requirement thật, phương án bền hơn là **bảng `department_heads` riêng**, không cố nhồi vào `employee_job_records`.

---

## 5. Quyết định thiết kế khuyến nghị

Sau khi đối chiếu source hiện tại và yêu cầu mới, phương án khuyến nghị là:

1. **Trang chi tiết phòng ban** là route riêng
2. **Headcount** reuse logic từ `hr_report_service.get_org_structure()`
3. **Người đứng đầu đơn vị** dùng bảng riêng `department_heads`
4. **Org chart** hiển thị cây đơn vị + head hiện hành của từng node
5. **Danh sách nhân sự trực tiếp** vẫn lấy từ `employee_job_records.is_current = TRUE`

Lý do chọn bảng riêng `department_heads`:

1. đáp ứng được case 1 employee quản lý nhiều đơn vị
2. không đụng constraint current record của `employee_job_records`
3. dễ audit lịch sử bổ nhiệm
4. ít phá vỡ source hiện tại hơn

---

## 6. Nguồn ảnh cho node org chart

## 6.1. Nguồn ảnh chuẩn

Khuyến nghị chuẩn hóa nguồn ảnh node theo thứ tự:

1. attachment mới nhất có `document_type = 'avatar'`
2. fallback `employees.avatar_path` nếu có
3. fallback ảnh placeholder

### 6.2. Lý do

Attachment `avatar` hiện là nguồn nghiệp vụ rõ ràng hơn, vì:

- user upload qua tab hồ sơ đính kèm
- đã có preview flow riêng

### 6.3. Việc cần làm thêm

Nên có service helper:

- resolve avatar preview URL cho 1 employee

Đầu ra:

- `avatar_preview_url: Optional[str]`

để frontend không phải tự gọi thêm nhiều request.

---

## 7. API backend đề xuất

## 7.1. API chi tiết phòng ban

Tạo endpoint:

- `GET /api/v1/departments/{dept_id}/detail`

Response gợi ý:

```json
{
  "department": {
    "id": 12,
    "code": "HCNS",
    "name": "Phòng Hành chính nhân sự",
    "dept_type": "PHONG",
    "dept_type_label": "Phòng",
    "parent_id": 3,
    "parent_name": "Khối Văn phòng",
    "is_active": true
  },
  "summary": {
    "direct_headcount": 8,
    "total_headcount": 23,
    "direct_child_count": 2,
    "job_position_count": 5
  },
  "head": {
    "employee_id": 101,
    "full_name": "Nguyễn Văn A",
    "job_position_name": "Trưởng phòng Hành chính nhân sự",
    "avatar_preview_url": "/api/..."
  },
  "org_chart": {
    "department_id": 12,
    "department_name": "Phòng Hành chính nhân sự",
    "dept_type_label": "Phòng",
    "direct_headcount": 8,
    "total_headcount": 23,
    "head": {
      "employee_id": 101,
      "full_name": "Nguyễn Văn A",
      "job_position_name": "Trưởng phòng Hành chính nhân sự",
      "avatar_preview_url": "/api/..."
    },
    "children": []
  },
  "direct_employees": [
    {
      "employee_id": 101,
      "employee_code": "HC001",
      "full_name": "Nguyễn Văn A",
      "job_position_name": "Trưởng phòng Hành chính nhân sự",
      "is_department_head": true
    }
  ]
}
```

## 7.2. API quản lý người đứng đầu đơn vị

Nếu dùng bảng `department_heads`, cần thêm:

1. `GET /api/v1/departments/{dept_id}/head`
2. `PUT /api/v1/departments/{dept_id}/head`
3. `DELETE /api/v1/departments/{dept_id}/head`

Request `PUT`:

- `employee_id`
- `head_role_label`
- `effective_from`

---

## 8. Thiết kế frontend đề xuất

## 8.1. Route

Thêm route mới trong [frontend/src/router/index.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:1):

- `org/departments/:id`

Component mới:

- `frontend/src/views/org/DepartmentDetailView.vue`

## 8.2. Service

Mở rộng [frontend/src/services/departmentService.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/services/departmentService.ts:1):

- `getDetail(id: number)`
- `updateHead(id: number, payload)`
- `deleteHead(id: number)`

## 8.3. UI node org chart

Mỗi node hiển thị:

1. badge loại đơn vị
2. tên đơn vị
3. avatar head
4. họ tên head
5. vị trí / role label
6. `Trực tiếp: X`
7. `Toàn cây: Y`

Nếu chưa có head:

- hiện placeholder `Chưa gán người phụ trách`

## 8.4. Tương tác

1. click node con:
   - điều hướng sang chi tiết đơn vị con
2. click tên nhân sự:
   - mở hồ sơ nhân viên
3. action `Gán người đứng đầu`
   - mở dialog chọn employee

---

## 9. Kế hoạch triển khai theo slice

## Slice 1 — Detail page foundation

Bao gồm:

1. route chi tiết phòng ban
2. API `GET /departments/{id}/detail`
3. summary cards
4. bảng nhân sự trực tiếp

Chưa bao gồm:

- org chart
- CRUD người đứng đầu

## Slice 2 — Mô hình người đứng đầu đơn vị

Bao gồm:

1. migration tạo `department_heads`
2. service CRUD head
3. validation nghiệp vụ
4. audit log

## Slice 3 — Org chart

Bao gồm:

1. backend shape `org_chart`
2. frontend `OrganizationChart`
3. node template có avatar, họ tên, vị trí

## Slice 4 — Vận hành

Bao gồm:

1. dialog gán head
2. điều hướng giữa các node
3. loading / empty state / error state

---

## 10. Rủi ro và quyết định cần chốt trước khi code

### 10.1. Có giữ `employees.avatar_path` nữa hay không?

Chưa xác nhận source hiện tại có đang dùng trường này như nguồn chuẩn hay không.

Cần chốt:

1. tiếp tục giữ song song
2. hay chuẩn hóa hoàn toàn về `employee_attachments.avatar`

### 10.2. Có cho phép một đơn vị tạm thời không có head hay không?

Khuyến nghị:

- có

để không chặn vận hành khi dữ liệu chưa đủ.

### 10.3. Có hiển thị tất cả nhân viên trên org chart hay không?

Khuyến nghị:

- không

Chỉ hiển thị:

- đơn vị
- người đứng đầu đơn vị

Toàn bộ nhân sự hiển thị ở bảng riêng.

### 10.4. Có cần lịch sử bổ nhiệm head trên UI ngay phase đầu hay không?

Khuyến nghị:

- chưa cần UI lịch sử ở slice đầu
- nhưng schema backend nên giữ được lịch sử

---

## 11. Kết luận chốt

Phương án phù hợp nhất với source hiện tại và yêu cầu thực tế là:

1. làm `Department detail page` riêng
2. reuse logic headcount/subtree hiện có
3. thêm mô hình `department_heads` riêng
4. dùng `OrganizationChart` để hiển thị cây đơn vị + người đứng đầu từng node
5. chuẩn hóa nguồn ảnh node theo attachment `avatar` là ưu tiên số 1

Điểm quan trọng nhất của bản plan này:

- **phải support case 1 employee quản lý nhiều đơn vị**
- vì vậy không nên gắn head theo mô hình 1-1 đơn giản ở `departments`
- và cũng không nên phá unique current record của `employee_job_records` nếu chưa thật cần thiết
