# Kế hoạch sửa đổi BHXH — lương đóng, nhóm vị trí, bậc thâm niên

**Phạm vi chính:** cấu hình lương tối thiểu vùng · cấu hình vùng BHXH của công ty · cấu hình nhóm vị trí và hệ số 7 bậc · tính mức lương đóng BHXH theo 2 mode tại hợp đồng

**Tình trạng:** plan đã review lại theo yêu cầu nghiệp vụ thực tế. Slice 1, Slice 2, Slice 3 và Slice 4 đã được triển khai; Slice 5+ vẫn pending.

---

## Kết luận review

Sau khi đọc lại docs BHXH và source `insurance / employee / contract`, bản draft trước đã **over-design** ở 3 chỗ:

1. tách quá nhiều mode tính lương BHXH
2. đưa thêm nhiều bảng policy hơn mức cần thiết
3. làm master “nhóm chức danh BHXH” quá trừu tượng, trong khi nhu cầu thực tế của công ty đang bám theo **nhóm vị trí** sát hơn

Theo yêu cầu nghiệp vụ vừa chốt, phần này nên giữ đơn giản:

1. cho phép cấu hình `regional_minimum_wages`
2. cho phép cấu hình `company_bhxh_region`
3. cho phép cấu hình `nhóm vị trí BHXH + 7 bậc hệ số`
4. tại hợp đồng, `Mức lương đóng BH (VNĐ)` có đúng **2 khả năng**:
   - `computed_by_position_group`
   - `fixed_manual`

---

## Trạng thái hiện tại đã xác nhận

### 1. Lương tối thiểu vùng và vùng công ty đã có model + seeder, chưa có cấu hình vận hành đầy đủ

Đã xác nhận:

- model ở [backend/app/models/salary.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/salary.py)
- seeder ở [backend/app/seeds/required.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/required.py)

Seeder hiện tại đang đặt:

- `company_bhxh_region = 3`
- `effective_from = 2026-01-01`
- `regional_minimum_wages.region=3.amount = 4_140_000`

**Lưu ý quan trọng:** trong repo hiện tại, mức `4.140.000` đang gắn với **Vùng III**, không phải Vùng II.

### 2. Hệ số bậc lương đang dùng seed prototype theo `job_title`

Đã xác nhận:

- `salary_scales` và `salary_scale_entries` có ở [backend/app/models/salary.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/salary.py)
- dữ liệu seed ở [backend/app/seeds/bootstrap.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/bootstrap.py)
- `salary_scale_entries` hiện gắn với `job_title_id`

Theo review với bảng HR thực tế, cách đó không còn phù hợp, vì công ty đang dùng logic:

- “nhóm chức danh / vị trí tương đương”

và về nghiệp vụ, **nhóm vị trí** là khái niệm bám thực tế hơn.

### 3. Hợp đồng hiện chỉ lưu một số `insurance_salary`

Đã xác nhận:

- model hợp đồng ở [backend/app/models/employee_contract.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_contract.py)
- form nhập ở [frontend/src/views/employees/ContractFormDialog.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/ContractFormDialog.vue)
- service CRUD ở [backend/app/services/employee_contract_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_contract_service.py)

Hiện trạng:

- contract chỉ có `insurance_salary`
- chưa có metadata để biết số đó là:
  - tính theo nhóm vị trí + bậc
  - hay là số cố định thỏa thuận

### 4. Hồ sơ BHXH và override thành phần theo employee đã có foundation thật

Đã xác nhận:

- `EmployeeInsuranceProfile` và `EmployeeInsuranceComponentOverride` ở [backend/app/models/employee_insurance.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_insurance.py)
- service runtime ở [backend/app/services/employee_insurance_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_insurance_service.py)
- UI ở [frontend/src/views/insurance/InsuranceView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/insurance/InsuranceView.vue)

Kết luận:

- phần “không phải employee nào cũng tham gia mọi thành phần BHXH như nhau” **đã có foundation**
- plan này **không thiết kế lại** phần component overrides

---

## Phạm vi nghiệp vụ chốt lại

### 1. Chỉ có 2 mode lương đóng BHXH

#### Mode A — `computed_by_position_group`

Áp dụng cho đa số nhân viên.

Mức lương đóng BHXH được tính:

```text
insurance_salary =
    lương tối thiểu vùng theo ngày hiệu lực
  × hệ số bậc theo nhóm vị trí
```

Nhóm nhân viên này:

- có `nhóm vị trí BHXH`
- có `bậc hiện tại`
- được xét nâng bậc 3 năm/lần theo rule công ty

#### Mode B — `fixed_manual`

Áp dụng cho một số nhân viên đặc thù.

Mức lương đóng BHXH:

```text
insurance_salary = một khoản cố định theo thỏa thuận
```

Nhóm này:

- không tăng theo lương tối thiểu vùng
- không tăng bậc theo năm
- chỉ đổi khi có quyết định mới

### 2. Rule nâng bậc thâm niên của công ty

Phase 1 chốt đúng rule hiện tại, **nhưng phải có UI cấu hình** để vận hành:

- ngày nâng bậc mặc định hiện tại là `01/01` hàng năm
- đủ `3 năm` thì tăng `1 bậc`
- nếu ngày chính thức từ `01/01` đến `30/04` thì tính tròn `1 năm` cho năm đó
- nếu từ `01/05` trở đi thì bắt đầu tính từ năm sau

**Kết luận thiết kế:** rule này không nên hardcode hoàn toàn trong code. Phase 1 cần có một cấu hình công ty đơn giản cho:

- `ngày nâng bậc hàng năm`
- `số năm cho mỗi lần tăng 1 bậc`
- `cutoff tính tròn năm đầu`

nhưng chưa cần mở rộng thành hệ policy nhiều biến thể theo từng nhóm nhân sự.

---

## Quyết định kiến trúc sau review

### 1. Dùng `nhóm vị trí BHXH`, không dùng `nhóm chức danh BHXH`

Plan mới chốt:

- không gắn hệ số BHXH trực tiếp với `job_title`
- thay vào đó tạo khái niệm:
  - `bhxh_position_groups`

Lý do:

- bám đúng thực tế công ty hơn
- tránh nhập nhằng giữa `chức danh` và `vị trí`
- phù hợp với nhận định của user rằng “lấy theo nhóm vị trí thì chính xác hơn”

### 2. Giữ contract là nơi HR nhập rule gốc

Về mặt UX/nghiệp vụ, thông tin này vẫn bắt đầu từ hợp đồng:

- tại hợp đồng có mục `Mức lương đóng BH (VNĐ)`
- nhưng source hiện tại chưa đủ metadata để phân biệt 2 mode

Plan mới chốt:

- hợp đồng phải lưu thêm metadata của mode BHXH
- `insurance_salary` vẫn được giữ lại như giá trị số đang áp dụng / snapshot

### 3. Giữ `employee_insurance_profiles.insurance_basis_amount` làm seam runtime cho report và insurance module

Vì source hiện tại đã xoay quanh seam này:

- salary module đọc `insurance_basis_amount`
- insurance module đọc `insurance_basis_amount`
- analytics/report BHXH đọc `insurance_basis_amount`

Plan mới không đập bỏ seam đó.

Thay vào đó:

- contract là nơi nhập rule
- insurance profile là nơi giữ current applied basis cho runtime/report

### 4. Cần cấu hình công ty cho progression, nhưng chưa cần policy engine phức tạp

Lý do:

- user đã chốt là cần UI cấu hình rule thâm niên và ngày nâng bậc
- nhưng yêu cầu hiện tại vẫn chỉ là một rule công ty dùng chung

Plan phase 1:

- có cấu hình vận hành cho rule thâm niên
- chưa làm hệ versioned policy nhiều lớp / nhiều rule song song

Nếu sau này công ty có nhiều rule khác nhau theo khối nhân sự, mới tách thành policy engine riêng.

---

## Thiết kế dữ liệu đề xuất

## 1. Cấu hình pháp lý và vùng công ty

Giữ nguyên 2 bảng hiện có:

- `regional_minimum_wages`
- `company_bhxh_region`

Việc cần làm:

- mở CRUD/UI vận hành
- không chỉ seed rồi để đó

Không đổi semantics của 2 bảng này.

## 2. Master nhóm vị trí BHXH

Đề xuất thêm:

```sql
bhxh_position_groups
  id
  code
  name
  description
  is_active
  created_at
  updated_at

bhxh_position_group_members
  id
  bhxh_position_group_id
  job_position_id
  note
```

Mục đích:

- một nhóm vị trí BHXH có thể chứa nhiều `job_position`
- bám đúng logic “vị trí tương đương”

## 3. Hệ số 7 bậc

Khuyến nghị tận dụng lại `salary_scales` hiện có, nhưng đổi semantic của entry:

```sql
salary_scales
  id
  name
  effective_from
  effective_to
  note

salary_scale_entries
  id
  salary_scale_id
  bhxh_position_group_id
  grade_no
  coefficient
  promotion_months
  criteria
```

Nghĩa là:

- vẫn giữ versioning của scale
- nhưng entry không còn gắn `job_title_id`
- mà gắn `bhxh_position_group_id`

### 4. Metadata BHXH tại hợp đồng

Hiện contract chỉ có:

- `insurance_salary`

Plan mới đề xuất bổ sung vào `employee_contracts`:

```sql
insurance_salary_mode         -- 'computed_by_position_group' | 'fixed_manual'
bhxh_position_group_id        -- nullable, bắt buộc nếu mode = computed
bhxh_grade_no                 -- nullable, bắt buộc nếu mode = computed
bhxh_seniority_start_date     -- nullable, bắt buộc nếu mode = computed
insurance_salary_fixed_amount -- nullable, bắt buộc nếu mode = fixed_manual
```

Giữ lại:

- `insurance_salary`

với vai trò:

- snapshot số tiền đang áp dụng tại thời điểm tạo/cập nhật hợp đồng

### 5. Insurance profile

Không cần thêm quá nhiều field mới ở phase 1.

Giữ:

- `insurance_basis_amount`
- `insurance_basis_source`

Phase 1 chỉ cần bảo đảm:

- khi hợp đồng active được tạo/cập nhật theo mode BHXH
- profile basis hiện hành được sync đúng

### 6. Cấu hình rule thâm niên công ty

Đề xuất thêm một bảng cấu hình đơn giản:

```sql
bhxh_seniority_settings
  id
  raise_month                  -- hiện tại = 1
  raise_day                    -- hiện tại = 1
  years_per_grade              -- hiện tại = 3
  first_year_cutoff_month      -- hiện tại = 4
  first_year_cutoff_day        -- hiện tại = 30
  is_active
  note
  created_at
  updated_at
```

Mục đích:

- cho phép UI cấu hình rule thâm niên và ngày nâng bậc
- vẫn giữ thiết kế đơn giản
- không cần version hóa phức tạp trong phase 1 nếu công ty hiện chỉ dùng một rule active

---

## Thuật toán nghiệp vụ phase 1

### 1. Resolve bậc hiện tại cho mode `computed_by_position_group`

Input:

- `bhxh_seniority_start_date`
- `as_of_date`
- `bhxh_grade_no` tại thời điểm bắt đầu
- `bhxh_seniority_settings` đang active
- max grade = `7`

Quy tắc:

```text
if seniority_start_date in [01/01 .. cutoff]:
    counted_start_year = year(seniority_start_date)
else:
    counted_start_year = year(seniority_start_date) + 1

completed_years = year(as_of_date) - counted_start_year
step_count = floor(completed_years / years_per_grade)
resolved_grade = min(initial_grade + step_count, 7)
```

### 2. Resolve lương đóng BHXH

#### Với `computed_by_position_group`

```text
insurance_salary =
    regional_minimum_wage(company_region, as_of_date)
  × coefficient(bhxh_position_group, resolved_grade, active_scale)
```

#### Với `fixed_manual`

```text
insurance_salary = insurance_salary_fixed_amount
```

### 3. Đồng bộ runtime

Khi resolve xong:

- ghi `employee_contracts.insurance_salary`
- đồng bộ `employee_insurance_profiles.insurance_basis_amount`

Ghi chú:

- phase 1 cần chốt rõ có cho job chạy tăng bậc hàng năm tự update contract hay không
- nếu không muốn sửa ngược bản ghi hợp đồng cũ, thì phải tạo workflow điều chỉnh/snapshot riêng vào `employee_insurance_profiles`

Đây là trade-off lớn nhất của phần thiết kế này.

---

## Điểm cần chốt thêm trước khi code

### 1. Có cho phép update `employee_contracts.insurance_salary` hàng năm không?

Hiện có 2 hướng:

#### Hướng A — update contract active

Ưu điểm:

- đơn giản
- hợp đồng active luôn phản ánh mức hiện tại

Nhược điểm:

- sửa ngược dữ liệu hợp đồng đã ký

#### Hướng B — contract giữ metadata rule, profile giữ current applied amount

Ưu điểm:

- không làm bẩn lịch sử hợp đồng
- hợp với seam runtime hiện tại của insurance/salary module

Nhược điểm:

- `insurance_salary` trên contract không còn là nơi duy nhất để đọc current amount

**Khuyến nghị:** chọn **Hướng B**.

Lý do:

- phù hợp hơn với source hiện tại đang đọc `employee_insurance_profiles.insurance_basis_amount`
- tránh phải mutate lịch sử hợp đồng mỗi kỳ `01/01`

### 2. Có cần UI cấu hình rule thâm niên không?

Khuyến nghị phase 1:

- **có**
- phải có UI cấu hình tối thiểu cho:
  - `ngày nâng bậc hàng năm`
  - `số năm cho mỗi lần tăng 1 bậc`
  - `cutoff tính tròn năm đầu`
- engine nghiệp vụ đọc từ cấu hình này
- chỉ giữ phạm vi đơn giản ở mức `một rule active của công ty`, chưa mở thành nhiều policy song song

Nếu sau này công ty cần nhiều rule khác nhau theo khối nhân sự hoặc theo thời kỳ, mới mở rộng thành policy engine/versioned rules.

---

## Tác động đến UI

### 1. `Cấu hình BHXH dùng chung`

Mở rộng `/catalog/insurance` hoặc màn cùng context với các tab:

1. `Tỷ lệ đóng`
2. `Lương tối thiểu vùng`
3. `Vùng BHXH công ty`
4. `Nhóm vị trí BHXH`
5. `Hệ số 7 bậc`
6. `Rule thâm niên`

### 2. `ContractFormDialog`

Bổ sung các field:

- `Mode lương BHXH`
  - `Theo nhóm vị trí + bậc`
  - `Mức cố định`

Nếu `Theo nhóm vị trí + bậc`:

- `Nhóm vị trí BHXH`
- `Bậc hiện tại`
- `Ngày bắt đầu tính thâm niên`
- preview `Mức lương đóng BH`

Nếu `Mức cố định`:

- `Mức lương BHXH cố định`

### 3. `InsuranceView` / `InsuranceTab`

Hiển thị rõ:

- nguồn basis
- mode BHXH
- nhóm vị trí BHXH
- bậc hiện tại
- kỳ xét tăng bậc tiếp theo

---

## Kế hoạch triển khai theo slice

### Slice 1 — Cấu hình LTTV vùng và vùng công ty

Mục tiêu:

- có CRUD/UI cho `regional_minimum_wages`
- tận dụng UI hiện có cho `company_bhxh_region`
- thêm CRUD/UI cho `bhxh_seniority_settings`

Exit criteria:

- không còn phụ thuộc seeder cho vận hành hàng ngày
- rule thâm niên và ngày nâng bậc sửa được qua UI

Trạng thái:

- đã xong

### Slice 2 — Master nhóm vị trí BHXH + hệ số 7 bậc

Mục tiêu:

- thêm `bhxh_position_groups`
- map `job_position` vào group
- đổi semantic `salary_scale_entries` sang group

Exit criteria:

- mỗi group có đủ 7 bậc
- có thể đối chiếu thẳng với bảng HR hiện tại

Trạng thái:

- đã xong

### Slice 3 — Hợp đồng hỗ trợ 2 mode BHXH

Mục tiêu:

- `ContractFormDialog` và backend contract hỗ trợ:
  - `computed_by_position_group`
  - `fixed_manual`

Exit criteria:

- tạo/sửa hợp đồng với 2 mode đều pass
- preview số tiền đúng theo rule

Trạng thái:

- đã xong

### Slice 4 — Engine thâm niên

Mục tiêu:

- implement engine đọc từ `bhxh_seniority_settings`

Exit criteria:

- có test cho:
  - ngày chính thức trong khoảng trước cutoff năm đầu
  - ngày chính thức sau cutoff năm đầu
  - capped ở bậc `7`
  - mode `fixed_manual` không tự tăng
  - đổi `raise_month/raise_day` trong config thì kết quả thay đổi đúng

Trạng thái:

- đã xong

### Slice 5 — Đồng bộ runtime/report

Mục tiêu:

- current applied basis trong `employee_insurance_profiles` luôn đúng
- salary/report/insurance module đọc số thống nhất

Exit criteria:

- không có chênh lệch không giải thích được giữa contract / profile / salary report

---

## Những gì plan này cố ý không làm ở phase 1

- không thiết kế lại `EmployeeInsuranceComponentOverride`
- không tạo hệ policy progression phức tạp nhiều biến thể
- không tiếp tục gắn hệ số BHXH với `job_title`
- không tách thêm nhiều mode lương BHXH ngoài 2 mode đã chốt

---

## Kết luận

Sau review, hướng đúng cho repo này là:

1. dùng **nhóm vị trí BHXH**
2. giữ đúng **2 mode**:
   - `computed_by_position_group`
   - `fixed_manual`
3. giữ contract là nơi HR nhập rule gốc
4. giữ insurance profile là seam runtime cho current applied basis
5. phase 1 có UI cấu hình rule tăng bậc của công ty, nhưng chưa tạo policy engine nhiều biến thể

Đây là thiết kế đơn giản hơn, bám sát nhu cầu vận hành hiện tại, và ít phá vỡ source đang chạy hơn bản draft trước.

---

## Đã xác minh cho tài liệu này

- đã đọc các docs liên quan:
  - [docs/plan_1.1_co_cau_to_chuc.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_1.1_co_cau_to_chuc.md)
  - [docs/plan_4.1_contract_management.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_4.1_contract_management.md)
  - [docs/plan_6.1_thong_tin_bao_hiem_nhan_vien.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_6.1_thong_tin_bao_hiem_nhan_vien.md)
  - [docs/plan_6.2_ty_le_dong_bhxh.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_6.2_ty_le_dong_bhxh.md)
  - [docs/plan_7.1_muc_luong_bhxh.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/plan_7.1_muc_luong_bhxh.md)
- đã đọc source liên quan:
  - [backend/app/models/salary.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/salary.py)
  - [backend/app/seeds/required.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/required.py)
  - [backend/app/seeds/bootstrap.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/seeds/bootstrap.py)
  - [backend/app/models/employee_contract.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_contract.py)
  - [backend/app/services/employee_contract_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_contract_service.py)
  - [backend/app/models/employee_insurance.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/models/employee_insurance.py)
  - [backend/app/services/employee_insurance_service.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/services/employee_insurance_service.py)
  - [frontend/src/views/employees/ContractFormDialog.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/ContractFormDialog.vue)
  - [frontend/src/views/insurance/InsuranceView.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/insurance/InsuranceView.vue)

## Chưa xác minh cho tài liệu này

- chưa sửa code runtime
- chưa chạy test hay browser verification
- chưa chốt cuối cùng giữa:
  - update current active contract hàng năm
  - hay chỉ update `employee_insurance_profiles.insurance_basis_amount`
