# Kế hoạch nhập dữ liệu & go-live production cho HRMS

Mục đích của tài liệu này:

1. khởi tạo một môi trường production sạch có thể đăng nhập và vận hành
2. nhập các dữ liệu thực tế doanh nghiệp đang có theo đúng thứ tự
3. bật các schedule cần thiết để hệ thống chạy thật
4. chỉ rõ các blocker kỹ thuật hiện còn tồn tại trong source hiện tại

Tài liệu này được viết lại sau khi đối chiếu trực tiếp với:

- `README.md`
- các seeder production hiện hành
- source import nhân viên / hợp đồng / nghỉ phép / bảo hiểm
- source BHXH foundation / hợp đồng / insurance profile
- source Celery worker / beat

---

## 1. Kết luận ngắn

Có thể đưa hệ thống lên production sạch và chạy thật với các phần sau:

- migrate DB
- seed required
- seed bootstrap
- bootstrap admin đầu tiên
- cấu hình danh mục vận hành
- import nhân viên
- import nghỉ phép
- import hợp đồng
- import bảo hiểm
- chạy worker / beat

Nhưng trước khi coi đây là runbook go-live hoàn chỉnh, phải ghi rõ 2 blocker kỹ thuật hiện có trong source:

1. importer `Hợp đồng`, `Nghỉ phép`, `Bảo hiểm` đang tra cứu nhân viên bằng `employee_seq` parse từ mã hiển thị, chưa an toàn nếu doanh nghiệp dùng nhiều `employee_code_sequence`
2. importer `Hợp đồng` và `Bảo hiểm` chưa đi theo đúng engine BHXH mới `computed_by_position_group / fixed_manual`, nên có thể làm lệch state BHXH runtime nếu áp dụng máy móc cho dữ liệu production

Vì vậy:

- phần runbook production sạch: dùng được ngay
- phần runbook import dữ liệu thực tế: dùng được, nhưng phải tuân thủ các giới hạn hiện tại ghi ở mục 2

---

## 2. Blocker & giới hạn kỹ thuật hiện tại

### 2.1. Blocker A — importer đang tra cứu nhân viên theo `employee_seq`, không theo `display_code` đầy đủ

**Trạng thái nghiệp vụ đã xác nhận:** công ty hiện đang chạy với **3 hệ mã số nhân viên khác nhau**.

Đã xác nhận trong source:

- [backend/app/services/contract_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/contract_import_service.py:128)
- [backend/app/services/leave_record_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_import_service.py:111)
- [backend/app/services/insurance_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/insurance_import_service.py:116)

Các hàm này:

- bỏ toàn bộ ký tự chữ của mã nhân viên
- lấy phần số
- query `Employee.employee_seq == seq`

Trong khi model hiện tại cho phép trùng `employee_seq` giữa các hệ mã khác nhau, unique thật là:

- `(employee_code_sequence_id, employee_seq)`
- [backend/app/models/employee.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee.py:119)

### Hệ quả

Nếu doanh nghiệp dùng nhiều hệ mã nhân viên, ví dụ:

- `SYS1` có nhân viên số `0001`
- `SYS2` cũng có nhân viên số `0001`

thì import HĐ / nghỉ phép / bảo hiểm có thể:

- ném `MultipleResultsFound`
- hoặc liên kết sai nhân viên

### Quyết định vận hành hiện tại

Với xác nhận mới rằng doanh nghiệp đang dùng **3 hệ mã nhân viên**, đây không còn là “giới hạn có thể né”, mà là:

- **blocker go-live chính thức** cho import `HĐ / Nghỉ phép / Bảo hiểm`

Cho đến khi sửa source, không được dùng importer production cho 3 module này nếu:

- mã nhân viên ở các hệ có thể trùng phần số
- hoặc chưa chứng minh được `employee_seq` là duy nhất toàn công ty

### Exit criteria để gỡ blocker A

Chỉ coi blocker này là đã xử lý khi thỏa cả 3 điều kiện:

1. importer `HĐ / Nghỉ phép / Bảo hiểm` tra nhân viên bằng:
   - `display_code` đầy đủ
   - hoặc cặp khóa logic tương đương `(employee_code_sequence, employee_seq)`
2. có automated test cho case:
   - 3 hệ mã khác nhau
   - cùng tồn tại nhân viên `0001` ở nhiều hệ
   - import vẫn map đúng người
3. có verify runtime thật trên môi trường chạy:
   - import hợp đồng đúng nhân viên
   - import nghỉ phép đúng nhân viên
   - import bảo hiểm đúng nhân viên

---

### 2.2. Blocker B — import HĐ/BHXH chưa khớp hoàn toàn với engine BHXH mới

Đã xác nhận trong source:

- import hợp đồng đang tạo `EmployeeContract` trực tiếp:
  - [backend/app/services/contract_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/contract_import_service.py:268)
- model hợp đồng hiện có default:
  - `insurance_salary_mode = 'fixed_manual'`
  - [backend/app/models/employee_contract.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_contract.py:74)
- import hợp đồng hiện chưa set:
  - `insurance_salary_mode`
  - `bhxh_position_group_id`
  - `insurance_salary_grade_no`
  - `bhxh_seniority_start_date`
- import bảo hiểm hiện luôn ép:
  - `insurance_basis_source = 'manual_fixed'`
  - [backend/app/services/insurance_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/insurance_import_service.py:240)
- sync contract -> insurance profile sẽ bỏ qua profile đang là `manual_fixed`:
  - [backend/app/services/employee_contract_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_contract_service.py:583)

### Hệ quả

Với đa số nhân viên đáng ra phải chạy mode:

- `computed_by_position_group`

thì nếu import theo source hiện tại:

- hợp đồng import vào sẽ thiếu metadata BHXH
- insurance profile import vào sẽ bị coi là `manual_fixed`
- sync runtime về sau có thể không còn bám đúng rule BHXH theo nhóm vị trí + bậc

### Quyết định vận hành hiện tại

Trước khi fix importer cho BHXH slices 3–5, runbook production phải tách 2 nhóm:

1. Nhóm `fixed_manual`
- có thể import hồ sơ BHXH với mức đóng cố định

2. Nhóm `computed_by_position_group`
- **không nên** rely vào importer HĐ/BHXH hiện tại để chốt state cuối
- nên nhập/xử lý qua UI hợp đồng hoặc một script/importer riêng đã đi qua engine mới

Nếu mục tiêu go-live là đưa toàn bộ công ty vào mode BHXH mới ngay từ đầu, đây là blocker cần fix trước.

---

### 2.3. Giới hạn nghỉ phép

Đã xác nhận:

- import nghỉ phép tạo `LeaveRecord` nhưng không gắn `entitlement_id`
  - [backend/app/services/leave_record_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_import_service.py:231)
- `bulk_allocate` chỉ tạo entitlement cho nhân viên:
  - `is_active = true`
  - `status != 'resigned'`
  - [backend/app/services/leave_entitlement_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_entitlement_service.py:283)

### Hệ quả

- sau import nghỉ phép phải chạy script link `leave_records -> leave_entitlements`
- nếu import lịch sử nghỉ phép của nhân sự đã nghỉ việc, có thể không tồn tại entitlement để link

### Quyết định vận hành hiện tại

Runbook này mặc định áp dụng cho:

- dữ liệu phép năm đang vận hành
- nhân viên đang active

Nếu cần import lịch sử nghỉ phép sâu cho nhân sự đã nghỉ việc, phải làm script riêng.

---

## 3. Runbook production sạch

### 3.1. Preconditions

Máy production phải có:

- Docker
- Docker Compose plugin
- file `.env` production đầy đủ
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_FULL_NAME`

### 3.2. Khởi tạo DB sạch

Theo README hiện hành, flow đúng là:

```bash
make migrate
make seed-required
make seed-bootstrap
make seed-bootstrap-admin
```

Đã xác nhận ở:

- [README.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/README.md:76)
- [Makefile](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/Makefile:67)
- [backend/app/seeds/__main__.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/__main__.py:55)

### 3.3. Kết quả mong đợi sau seed

#### `seed-required`

Tạo baseline bắt buộc:

- `regional_minimum_wages`
- `company_bhxh_region`
- `bhxh_seniority_settings`
- `insurance_contribution_components`
- `insurance_policy_version`
- danh mục hành chính
- danh mục học vấn
- danh mục loại hợp đồng
- leave types
- bệnh viện KCB
- checklist hồ sơ pháp lý
- notification templates

Nguồn:

- [backend/app/seeds/required.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/required.py:273)

#### `seed-bootstrap`

Tạo bootstrap vận hành:

- `job_titles`
- `salary_scales`
- `bhxh_position_groups`
- `salary_scale_entries`
- `departments`

Nguồn:

- [backend/app/seeds/bootstrap.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/bootstrap.py:1)

#### `seed-bootstrap-admin`

Tạo admin đăng nhập đầu tiên.

Nguồn:

- [backend/app/seeds/__main__.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/__main__.py:85)

---

## 4. Cấu hình production sau seed, trước khi import dữ liệu

### 4.1. Rà lại `Cấu hình BHXH dùng chung`

Màn hình:

- [frontend/src/router/index.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:398)
- [frontend/src/views/catalog/InsuranceFoundationView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/catalog/InsuranceFoundationView.vue:204)

Phải kiểm tra và cập nhật nếu cần:

1. `Rule thâm niên BHXH`
2. `Lịch sử vùng BHXH công ty`
3. `Lương tối thiểu vùng`
4. `Thang bảng lương`
5. `Nhóm vị trí BHXH + hệ số 7 bậc`

### 4.2. Rà lại các bootstrap catalog vận hành

Phải rà thực tế và chỉnh nếu cần:

1. `Phòng ban`
2. `Chức danh`
3. `Vị trí công việc`
4. `Leave types`
5. `Loại hợp đồng`
6. `Bệnh viện KCB`

Lý do:

- `seed-bootstrap` và `seed-required` chỉ tạo baseline / bootstrap mặc định
- dữ liệu thực tế doanh nghiệp có thể khác

---

## 5. Thứ tự nhập dữ liệu thực tế

Thứ tự này là thứ tự vận hành an toàn nhất theo source hiện tại.

### Bước 1 — Danh mục tổ chức

Tạo hoặc chỉnh:

1. phòng ban
2. chức danh
3. vị trí công việc

Lý do:

- import nhân viên phụ thuộc trực tiếp vào các danh mục này
- lookup phòng ban / chức danh / vị trí đã có hỗ trợ normalize, nhưng vẫn phải tồn tại trước

Nguồn:

- [backend/app/services/employee_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_import_service.py:157)

### Bước 2 — Import nhân viên

Thực tế UI:

- tab `Nhân viên` trong `Nhập dữ liệu` chỉ redirect sang trang nhân viên
  - [frontend/src/views/data/DataImportView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/data/DataImportView.vue:49)

Flow đúng:

- import nhân viên từ màn danh sách nhân viên / dialog import nhân viên

Lưu ý:

1. Nếu doanh nghiệp chỉ dùng một hệ mã, có thể để trống `Hệ mã nhân viên` để dùng default
2. Vì doanh nghiệp đang dùng 3 hệ mã, bước này phải ghi nhận rõ:
   - có hay không trùng phần số giữa các hệ
   - nếu có khả năng trùng, dừng runbook import `HĐ / Nghỉ phép / Bảo hiểm` tại đây cho đến khi gỡ blocker A

### Bước 3 — Rà lại employee code sau import nhân viên

Phải check:

1. mã hiển thị thực tế
2. hệ mã nhân viên
3. có bị trùng suffix giữa các hệ mã không

Lý do:

- các importer HĐ / nghỉ phép / BHXH sau đó đang tra theo phần số `employee_seq`
- vì công ty đang dùng 3 hệ mã, đây là gate quyết định có được phép đi tiếp sang các bước import sau hay không

### Bước 4 — Import hợp đồng

Chỉ import theo flow hiện tại nếu:

- dữ liệu HĐ chỉ cần lưu record hợp đồng cơ bản
- chưa dùng importer này để chốt mode BHXH `computed_by_position_group`
- và blocker A đã được chứng minh không ảnh hưởng dữ liệu thực tế của công ty

Không nên dùng importer HĐ hiện tại cho nhóm nhân viên cần setup:

- `bhxh_position_group_id`
- `insurance_salary_grade_no`
- `computed_by_position_group`

Nhóm đó nên xử lý qua UI hợp đồng hoặc một script/importer riêng đã đi qua engine hợp đồng mới.

### Bước 5 — Cấp entitlement phép năm

Chạy:

- UI `Cấp phép năm`
- hoặc `POST /api/v1/leave-entitlements/bulk-allocate`

Nguồn:

- [backend/app/api/v1/endpoints/leave_entitlements.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/leave_entitlements.py:40)

### Bước 6 — Import nghỉ phép

Chỉ nên dùng cho:

- dữ liệu phép năm đang active
- nhân viên còn active
- và blocker A đã được chứng minh không ảnh hưởng dữ liệu thực tế của công ty

Sau khi import xong, **bắt buộc** chạy script link ở mục 6.1.

### Bước 7 — Import hồ sơ BHXH

Chỉ nên dùng importer hiện tại cho nhóm:

- `fixed_manual`
- và chỉ sau khi blocker A đã được gỡ hoặc được chứng minh không ảnh hưởng dataset thực tế

Không nên dùng importer này như state cuối cho nhóm:

- `computed_by_position_group`

vì importer đang ép:

- `insurance_basis_source = manual_fixed`

### Bước 8 — Rà lại BHXH runtime sau import

Bắt buộc kiểm tra ngẫu nhiên một số nhân viên đại diện:

1. nhân viên mode `fixed_manual`
2. nhân viên mode `computed_by_position_group`
3. nhân viên có hợp đồng active mới nhất
4. nhân viên có component override riêng

Phải đối chiếu:

- hồ sơ hợp đồng
- hồ sơ BHXH
- màn lương BHXH

Nếu chưa có importer mới cho computed mode, bước này sẽ là nơi phát hiện lệch state.

---

## 6. Script / lệnh bắt buộc sau import

### 6.1. Link `leave_records` với `leave_entitlements`

```sql
UPDATE leave_records lr
SET entitlement_id = le.id
FROM leave_entitlements le
WHERE lr.entitlement_id IS NULL
  AND lr.status = 'active'
  AND le.employee_id = lr.employee_id
  AND le.leave_type_id = lr.leave_type_id
  AND le.year = EXTRACT(YEAR FROM lr.start_date);

UPDATE leave_entitlements le
SET used_days = COALESCE(
    (SELECT SUM(lr.total_days)
     FROM leave_records lr
     WHERE lr.entitlement_id = le.id
       AND lr.status = 'active'),
    0
);
```

Lý do:

- import nghỉ phép hiện chưa set `entitlement_id`

### 6.2. Chạy task expire hợp đồng quá hạn

```bash
docker compose exec backend python -c "from app.workers.tasks import expire_overdue_contracts; expire_overdue_contracts()"
```

Nguồn:

- [backend/app/workers/tasks.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/workers/tasks.py:37)

### 6.3. Chạy task gửi notification hằng ngày thử nghiệm

```bash
docker compose exec backend python -c "from app.workers.tasks import send_daily_notifications; send_daily_notifications()"
```

### 6.4. Chạy task reset carryover thử nghiệm

```bash
docker compose exec backend python -c "from app.workers.tasks import reset_expired_carryover; reset_expired_carryover()"
```

---

## 7. Scheduler production thật

### 7.1. Service phải chạy

Production phải giữ:

- `backend`
- `celery_worker`
- `celery_beat`

Nguồn:

- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:64)

### 7.2. Beat schedule hiện tại

Đã xác nhận ở:

- [backend/app/core/celery_app.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/celery_app.py:42)

Lịch hiện tại:

- `expire_overdue_contracts` → `00:05` hằng ngày
- `reset_expired_carryover` → `00:05` ngày `01/04`
- `expire_stale_postings` → `00:10` hằng ngày
- `cleanup_expired_exports` → `01:00` hằng ngày
- `send_daily_notifications` → `08:00` hằng ngày
- `ping_healthcheck` → mỗi `60` giây

### 7.3. Lưu ý production compose

Trong production:

- `celery_beat` dùng `redbeat.RedBeatScheduler`
- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:84)

Vì vậy runbook production phải bám `docker-compose.prod.yml`, không bám file dev compose mặc định.

---

## 8. Checklist go-live

### 8.1. Bắt buộc trước go-live

1. `make migrate`
2. `make seed-required`
3. `make seed-bootstrap`
4. `make seed-bootstrap-admin`
5. đăng nhập được bằng admin bootstrap
6. rà lại `Cấu hình BHXH dùng chung`
7. rà lại phòng ban / chức danh / vị trí / loại hợp đồng / leave types / bệnh viện KCB
8. import nhân viên
9. kiểm tra employee code / sequence thực tế
10. import phần dữ liệu còn lại theo đúng giới hạn ở mục 5
11. chạy script link nghỉ phép
12. chạy thử các task Celery thủ công
13. bật `celery_worker` + `celery_beat` production

### 8.2. Không được bỏ qua

1. không bỏ qua bước `migrate`
2. không giả định importer BHXH hiện tại đã support đầy đủ mode `computed_by_position_group`
3. vì công ty đang dùng 3 hệ mã, không import `HĐ / Nghỉ phép / BHXH` nếu blocker A chưa được gỡ hoặc chưa có bằng chứng runtime rằng dataset thực tế không trùng `employee_seq`
4. không bỏ qua step link `leave_records -> leave_entitlements`

---

## 9. Việc nên làm tiếp trước khi coi runbook này là production-ready hoàn toàn

### Ưu tiên 1

Fix importer HĐ / nghỉ phép / BHXH để tra nhân viên bằng:

- `display_code` đầy đủ
- hoặc `(employee_code_sequence + employee_seq)`

Đây là ưu tiên bắt buộc trước go-live import production vì công ty đang chạy 3 hệ mã nhân viên.

thay vì chỉ dùng `employee_seq`.

### Ưu tiên 2

Làm importer / script import mới cho hợp đồng và BHXH để hỗ trợ đúng 2 mode:

1. `computed_by_position_group`
2. `fixed_manual`

### Ưu tiên 3

Tách runbook import dữ liệu production thành 2 nhánh rõ:

1. `import dữ liệu nền`
2. `import dữ liệu vận hành có effect runtime`

để tránh người vận hành dùng sai importer cho dữ liệu BHXH computed.
