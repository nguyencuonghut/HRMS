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

Source hiện tại đã có nhiều nền tảng production:

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

Nhưng **chưa đủ điều kiện deploy production ngay** nếu dùng cấu hình/runbook hiện tại. Review ngày **08/06/2026** đã xác nhận thêm các blocker production ở tầng cấu hình, bảo mật, CI/CD và vận hành.

Các blocker import/runtime đã ghi nhận trước đó:

1. importer `Hợp đồng`, `Nghỉ phép`, `Bảo hiểm` đang tra cứu nhân viên bằng `employee_seq` parse từ mã hiển thị, chưa an toàn nếu doanh nghiệp dùng nhiều `employee_code_sequence`
2. importer `Hợp đồng` và `Bảo hiểm` chưa đi theo đúng engine BHXH mới `computed_by_position_group / fixed_manual`, nên có thể làm lệch state BHXH runtime nếu áp dụng máy móc cho dữ liệu production

Các blocker production mới đã xác nhận:

1. production domain/CORS/CSRF chưa được cấu hình trong `docker-compose.prod.yml`
2. MinIO/object storage chưa được wiring vào production stack
3. refresh cookie chưa bật `Secure` trong production compose
4. refresh session chưa revoke được server-side sau logout/đổi mật khẩu
5. CI/CD build image nhưng production compose không dùng image đó
6. backup/restore mới ở mức script + hướng dẫn crontab, chưa xác nhận scheduler production chạy thật

Vì vậy:

- phần runbook production sạch: chỉ dùng làm checklist chuẩn bị, **chưa được coi là go-live-ready**
- phần runbook import dữ liệu thực tế: dùng được sau khi các blocker import/runtime tương ứng đã có build deploy và verify runtime
- trước khi chạy thật phải xử lý hoặc có quyết định chấp nhận rủi ro bằng văn bản cho từng blocker ở mục 2

---

## 2. Blocker & giới hạn kỹ thuật hiện tại

### 2.1. Blocker A — importer đang tra cứu nhân viên theo `employee_seq`, không theo `display_code` đầy đủ

**Trạng thái nghiệp vụ đã xác nhận:** công ty hiện đang chạy với **3 hệ mã số nhân viên khác nhau**.

**Trạng thái source hiện tại trên nhánh làm việc ngày 2026-06-04:** đã vá xong blocker này trong code, nhưng chỉ được coi là gỡ blocker trên production sau khi bản build chứa fix đã được deploy.

Đã xác nhận trong source:

- [backend/app/services/contract_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/contract_import_service.py:128)
- [backend/app/services/leave_record_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_import_service.py:111)
- [backend/app/services/insurance_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/insurance_import_service.py:116)

Trước khi sửa, các hàm này:

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

### Cách đã sửa trong source hiện tại

Importer `HĐ / Nghỉ phép / Bảo hiểm` giờ tra cứu nhân viên theo rule:

1. nếu file có cột `Hệ mã nhân viên`:
   - parse phần số từ `Mã nhân viên`
   - lookup theo cặp `(employee_code_sequence.code, employee_seq)`
2. nếu file không có cột `Hệ mã nhân viên`:
   - ưu tiên match đúng `display_code` hiện tại
   - nếu không có `display_code` duy nhất thì mới fallback theo `employee_seq`
   - nếu `employee_seq` đang tồn tại ở nhiều hệ mã thì reject rõ ràng và yêu cầu điền `Hệ mã nhân viên`

Template import cho 3 module cũng đã có thêm cột `Hệ mã nhân viên` để dùng cho môi trường multi-sequence.

### Quyết định vận hành hiện tại

Trước khi deploy bản fix này lên production, với xác nhận mới rằng doanh nghiệp đang dùng **3 hệ mã nhân viên**, đây vẫn là:

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

Trạng thái mới của source trên branch làm việc hiện tại:

- `blocker 2.2` đã được fix trong source tính đến ngày **04/06/2026**
- nhưng chỉ được coi là **gỡ blocker go-live** sau khi môi trường production deploy đúng build có chứa fix này
- trên môi trường dev hiện tại đã verify runtime thật qua HTTP multipart:
  - `POST /api/v1/imports/contracts`
  - `POST /api/v1/imports/insurance`
  - với case `computed_by_position_group`, state cuối đã khớp:
    - `insurance_salary_mode = computed_by_position_group`
    - `bhxh_position_group = OFFICE_STAFF`
    - `insurance_salary_grade_no = 3`
    - `bhxh_seniority_start_date = 2023-01-01`
    - `insurance_salary = 5.423.400`
    - `insurance_basis_source = computed`
    - `insurance_basis_amount = 5.423.400`

### Cách đã sửa trong source hiện tại

1. Import hợp đồng:
- đã hỗ trợ đủ 2 mode:
  - `fixed_manual`
  - `computed_by_position_group`
- template import hợp đồng có thêm các cột:
  - `Mode lương BHXH`
  - `Mã nhóm vị trí BHXH`
  - `Bậc hệ số BHXH`
  - `Ngày bắt đầu tính thâm niên BHXH`
- nếu dòng import khai báo metadata BHXH, importer sẽ đi qua engine hợp đồng mới thay vì `INSERT` thẳng model
- với mode `computed_by_position_group`, importer sẽ:
  - resolve hệ số theo `bhxh_position_group`
  - tính bậc áp dụng theo rule thâm niên
  - snapshot `bhxh_seniority_start_date`
  - sync `employee_insurance_profiles` sang source `computed`

2. Import hồ sơ BHXH:
- không còn ép mọi hồ sơ về `insurance_basis_source = manual_fixed`
- nếu profile/hợp đồng active hiện tại đang ở mode:
  - `computed`
  - hoặc `contract`
  thì importer sẽ giữ source đúng và lấy mức đóng từ hợp đồng active mới nhất
- nếu user nhập `Mức lương đóng` không khớp với hợp đồng active trong mode `computed/contract`, importer sẽ reject rõ ràng
- mode `manual_fixed` vẫn giữ behavior nhập tay như cũ

### Hệ quả

Với đa số nhân viên đáng ra phải chạy mode:

- `computed_by_position_group`

thì nếu import theo source hiện tại:

- hợp đồng import vào sẽ thiếu metadata BHXH
- insurance profile import vào sẽ bị coi là `manual_fixed`
- sync runtime về sau có thể không còn bám đúng rule BHXH theo nhóm vị trí + bậc

### Exit criteria để gỡ blocker B

Chỉ coi blocker B đã gỡ khi đủ cả 3 điều kiện:

1. môi trường go-live đã deploy build chứa fix này
2. đã verify runtime thật trên môi trường chạy:
- import hợp đồng `computed_by_position_group` tạo đúng:
  - `insurance_salary_mode`
  - `bhxh_position_group_id`
  - `insurance_salary_grade_no`
  - `bhxh_seniority_start_date`
  - `insurance_salary`
- import BHXH sau đó không làm profile bị tụt từ `computed/contract` về `manual_fixed`
3. đã chạy test regression cho cả hai mode:
- `fixed_manual`
- `computed_by_position_group`

---

### 2.3. Giới hạn nghỉ phép

Trạng thái hiện tại:

- blocker này đã được gỡ trong source

Đã xác nhận ở code:

- importer nghỉ phép giờ gọi helper tạo entitlement nếu thiếu, rồi gắn `entitlement_id` ngay lúc tạo `LeaveRecord`
  - [backend/app/services/leave_record_import_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_record_import_service.py:221)
- helper `ensure_entitlement_for_import(...)` tạo entitlement ngay cả khi nhân viên đã `resigned`
  - [backend/app/services/leave_entitlement_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_entitlement_service.py:79)
- `bulk_allocate` vẫn chỉ áp cho nhân viên active; đây không còn là blocker cho import vì importer đã không phụ thuộc `bulk_allocate`
  - [backend/app/services/leave_entitlement_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/leave_entitlement_service.py:289)

Đã xác minh runtime:

- test importer nghỉ phép pass ở seam backend:
  - `pytest tests/test_leave_record_import.py -q`
- DB/runtime probe thật:
  - import 2 dòng nghỉ phép cho 1 nhân viên `official` và 1 nhân viên `resigned`
  - kết quả:
    - `Leave Probe RTLEAVE23A` → `entitlement_id=24`, `used_days=3.0`
    - `Leave Probe RTLEAVE23R` → `entitlement_id=25`, `used_days=1.0`

### Kết luận vận hành

- không cần chạy script link `leave_records -> leave_entitlements` sau import nghỉ phép nữa
- importer hiện đã support cả dữ liệu nghỉ phép của nhân viên đã nghỉ việc, miễn bản thân mã nhân viên được resolve đúng

---

### 2.4. Blocker C — production domain/CORS/CSRF chưa được cấu hình

**Mức độ:** Critical.

Đã xác nhận trong source:

- `CORS_ORIGINS` mặc định chỉ có localhost:
  - [backend/app/core/config.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/config.py:131)
- `CSRFMiddleware` reject các request ghi (`POST`, `PUT`, `PATCH`, `DELETE`) nếu `Origin` không nằm trong `settings.CORS_ORIGINS`:
  - [backend/app/middleware/csrf.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/middleware/csrf.py:63)
- `FastAPI CORSMiddleware` cũng dùng cùng `settings.CORS_ORIGINS`:
  - [backend/app/main.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/main.py:102)
- `docker-compose.prod.yml` hiện chưa truyền `CORS_ORIGINS` vào backend / worker / beat:
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:46)

### Hệ quả

Khi chạy domain thật, trình duyệt sẽ gửi `Origin: https://<domain-production>`. Nếu domain này không nằm trong `CORS_ORIGINS`, các thao tác ghi như đăng nhập, import, CRUD, lưu cấu hình có thể bị 403.

### Exit criteria để gỡ blocker C

1. `docker-compose.prod.yml` truyền `CORS_ORIGINS` production cho backend, worker, beat nếu các process đó load settings.
2. `.env.example` ghi rõ format domain production.
3. Browser-level smoke test trên domain thật pass các thao tác:
   - login
   - tạo/sửa một record đơn giản
   - upload/import một file nhỏ

---

### 2.5. Blocker D — MinIO/object storage chưa được wiring vào production stack

**Mức độ:** Critical.

Đã xác nhận trong source:

- app gọi `ensure_bucket()` khi startup:
  - [backend/app/main.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/main.py:78)
- readiness check phụ thuộc MinIO:
  - [backend/app/main.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/main.py:141)
- config mặc định đang là `MINIO_ENDPOINT=minio:9000`, `MINIO_ACCESS_KEY=minioadmin`, `MINIO_SECRET_KEY=minioadmin`:
  - [backend/app/core/config.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/config.py:104)
- production config reject default MinIO credentials:
  - [backend/app/core/config.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/config.py:111)
- `docker-compose.prod.yml` không có service MinIO và không truyền `MINIO_*` vào backend / worker / beat:
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:34)

### Hệ quả

Production có thể fail startup hoặc fail readiness nếu không có object storage hợp lệ. Các tính năng upload/view/download file phụ thuộc trực tiếp vào storage này.

### Exit criteria để gỡ blocker D

1. Chốt mô hình storage production:
   - MinIO container trong compose; hoặc
   - MinIO/S3 external managed.
2. `docker-compose.prod.yml` truyền đủ `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`.
3. Runtime check pass:
   - backend startup không lỗi `ensure_bucket`
   - `/health/ready` báo MinIO `ok`
   - upload và preview/download file PDF hoặc ảnh hoạt động qua UI.

---

### 2.6. Blocker E — refresh cookie chưa bật `Secure` trong production

**Mức độ:** High.

Đã xác nhận trong source:

- default `REFRESH_TOKEN_COOKIE_SECURE = False`:
  - [backend/app/core/config.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/config.py:95)
- login/refresh set cookie theo setting này:
  - [backend/app/api/v1/endpoints/auth.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/auth.py:135)
  - [backend/app/api/v1/endpoints/auth.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/auth.py:190)
- `docker-compose.prod.yml` hiện chưa override setting này:
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:46)

### Hệ quả

Refresh token cookie có thể không được browser giới hạn HTTPS-only nếu production không set `Secure`.

### Exit criteria để gỡ blocker E

1. Production compose set `REFRESH_TOKEN_COOKIE_SECURE=true`.
2. Runtime browser check xác nhận cookie `refresh_token` có `HttpOnly`, `Secure`, `SameSite=Strict`, path `/api/v1/auth`.

---

### 2.7. Blocker F — refresh session chưa revoke được server-side

**Mức độ:** High.

Đã xác nhận trong source:

- refresh token là JWT tự chứa, có `jti` nhưng không được lưu session server-side:
  - [backend/app/core/security.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/security.py:28)
  - [backend/app/core/security.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/security.py:36)
- `logout` blacklist access token hiện tại:
  - [backend/app/api/v1/endpoints/auth.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/auth.py:225)
- access-token blacklist có được kiểm khi gọi API:
  - [backend/app/api/v1/deps.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/deps.py:34)
- `change-password` đổi mật khẩu nhưng không invalidate refresh sessions đang tồn tại:
  - [backend/app/api/v1/endpoints/auth.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/api/v1/endpoints/auth.py:294)

### Hệ quả

Nếu refresh token bị lộ, token vẫn có thể dùng đến khi hết hạn tự nhiên, kể cả sau logout hoặc đổi mật khẩu, trừ khi bổ sung cơ chế revoke refresh token/session version.

### Exit criteria để gỡ blocker F

1. Có bảng/session store hoặc version field để revoke refresh tokens.
2. Logout revoke refresh token hiện tại.
3. Đổi mật khẩu revoke toàn bộ refresh sessions cũ của user.
4. Test regression:
   - refresh sau logout bị từ chối
   - refresh sau đổi mật khẩu bị từ chối

---

### 2.8. Blocker G — CI/CD build image nhưng production compose không dùng image đó

**Mức độ:** High.

Đã xác nhận trong source:

- CI build và push backend/frontend image lên registry:
  - [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml:123)
  - [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml:134)
- deploy step chạy `docker compose pull backend frontend` rồi restart backend/frontend:
  - [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml:162)
- production compose lại dùng `build:` cho backend/frontend/worker/beat, không dùng `image:` tag từ registry:
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:35)
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:65)
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:82)
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:98)

### Hệ quả

Không có bằng chứng deploy đang chạy đúng artifact vừa build/push. Worker/beat cũng có thể không được restart cùng backend khi có thay đổi code.

### Exit criteria để gỡ blocker G

1. Chốt strategy deploy:
   - compose production dùng `image:` từ registry; hoặc
   - server deploy bằng `git pull` + `docker compose build` có kiểm soát.
2. Backend, celery worker, celery beat dùng cùng image/version.
3. Deploy step restart đủ service cần restart:
   - `backend`
   - `celery_worker`
   - `celery_beat`
   - `frontend`
4. Smoke test sau deploy xác nhận version/build đang chạy đúng.

---

### 2.9. Blocker H — backup/restore chưa được xác nhận là schedule production thật

**Mức độ:** Medium.

Đã xác nhận trong repo:

- có script backup DB:
  - [scripts/backup_db.sh](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/scripts/backup_db.sh:1)
- có hướng dẫn crontab:
  - [scripts/restore_procedure.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/scripts/restore_procedure.md:162)
- docs hiện ghi rõ chưa xác nhận cron/scheduler production chạy định kỳ thực tế:
  - [docs/production_improvements.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_improvements.md:957)
- `docker-compose.prod.yml` hiện không có backup service/scheduler riêng:
  - [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml:1)

### Hệ quả

Nếu host production chưa tự cấu hình cron/systemd timer/container backup riêng thì chưa có backup tự động, dù script đã tồn tại.

### Exit criteria để gỡ blocker H

1. Có cơ chế schedule production thật cho DB backup và object storage backup.
2. Backup job gửi notification success/failure.
3. Restore drill staging pass theo checklist:
   - [scripts/restore_procedure.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/scripts/restore_procedure.md:216)
4. Ghi lại thời gian restore thực tế để đối chiếu RTO.

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

UI hiện tại:

- màn `Nhập dữ liệu` đã có 3 tab riêng theo đúng thứ tự phụ thuộc:
  1. `Phòng ban`
  2. `Chức danh`
  3. `Vị trí công việc`
- sau 3 tab này mới đến:
  - `Nhân viên`
  - `Nghỉ phép`
  - `Hợp đồng`
  - `Bảo hiểm`
- nguồn:
  - [frontend/src/views/data/DataImportView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/data/DataImportView.vue)

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

### 6.1. Chạy task expire hợp đồng quá hạn

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

1. gỡ hoặc có quyết định chấp nhận rủi ro cho toàn bộ blocker ở mục 2
2. cấu hình domain production trong `CORS_ORIGINS`
3. cấu hình object storage production và verify `/health/ready`
4. bật `REFRESH_TOKEN_COOKIE_SECURE=true`
5. chốt deploy strategy để production chạy đúng artifact đã build
6. cấu hình backup scheduler production thật
7. `make migrate`
8. `make seed-required`
9. `make seed-bootstrap`
10. `make seed-bootstrap-admin`
11. đăng nhập được bằng admin bootstrap
12. rà lại `Cấu hình BHXH dùng chung`
13. rà lại phòng ban / chức danh / vị trí / loại hợp đồng / leave types / bệnh viện KCB
14. import nhân viên
15. kiểm tra employee code / sequence thực tế
16. import phần dữ liệu còn lại theo đúng giới hạn ở mục 5
17. chạy thử các task Celery thủ công
18. bật `celery_worker` + `celery_beat` production

### 8.2. Không được bỏ qua

1. không bỏ qua bước `migrate`
2. không deploy nếu `CORS_ORIGINS` vẫn chỉ là localhost
3. không deploy nếu MinIO/object storage chưa có runtime check pass
4. không deploy HTTPS production nếu refresh cookie chưa có `Secure`
5. không giả định CI/CD đã deploy đúng image nếu compose vẫn dùng `build:`
6. không giả định backup đang chạy nếu chưa thấy log/notification của schedule production
7. không giả định importer BHXH hiện tại đã support đầy đủ mode `computed_by_position_group`
8. vì công ty đang dùng 3 hệ mã, không import `HĐ / Nghỉ phép / BHXH` nếu blocker A chưa được gỡ hoặc chưa có bằng chứng runtime rằng dataset thực tế không trùng `employee_seq`
9. không giả định dữ liệu nghỉ phép đã đúng nếu chưa kiểm tra ngẫu nhiên `entitlement_id` và `used_days` sau import

---

## 9. Việc nên làm tiếp trước khi coi runbook này là production-ready hoàn toàn

### Ưu tiên 1

Fix các blocker production infrastructure/security:

1. truyền `CORS_ORIGINS` production vào compose
2. wiring MinIO/object storage production
3. bật `REFRESH_TOKEN_COOKIE_SECURE=true`
4. sửa CI/CD để production chạy đúng image/build artifact
5. cấu hình backup scheduler production thật

Fix importer HĐ / nghỉ phép / BHXH để tra nhân viên bằng:

- `display_code` đầy đủ
- hoặc `(employee_code_sequence + employee_seq)`

Đây là ưu tiên bắt buộc trước go-live import production vì công ty đang chạy 3 hệ mã nhân viên.

thay vì chỉ dùng `employee_seq`.

### Ưu tiên 2

Thiết kế refresh session revocation:

1. revoke refresh token khi logout
2. revoke toàn bộ refresh sessions cũ khi đổi mật khẩu
3. thêm regression test cho refresh sau logout/đổi mật khẩu

Làm importer / script import mới cho hợp đồng và BHXH để hỗ trợ đúng 2 mode:

1. `computed_by_position_group`
2. `fixed_manual`

### Ưu tiên 3

Tách runbook import dữ liệu production thành 2 nhánh rõ:

1. `import dữ liệu nền`
2. `import dữ liệu vận hành có effect runtime`

để tránh người vận hành dùng sai importer cho dữ liệu BHXH computed.
