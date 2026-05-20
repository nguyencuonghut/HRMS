# Kế hoạch thực hiện — 6.1. Thông tin bảo hiểm nhân viên

**Phạm vi chính:** Hồ sơ bảo hiểm hiện hành của nhân viên · Danh sách tra cứu bảo hiểm · Cập nhật trạng thái tham gia  
**Phụ thuộc trực tiếp:** `1.1 Cơ cấu tổ chức` ✅ · `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅ · `3.7 Import/Export` ✅ · `4.1 Hợp đồng lao động` ✅  
**Phụ thuộc kiến trúc bắt buộc:** shared insurance foundation dùng chung với `6.2 Tỷ lệ đóng BHXH` và phần tính toán của `7.x Lương BHXH`

> **Lưu ý pháp lý đã verify ngày 20/05/2026:** nguồn mình kiểm tra cho thấy `Luật BHXH 2024 (41/2024/QH15)` có hiệu lực từ `01/07/2025`, không phải chính luật này bắt đầu từ `01/01/2026` ([MOJ PBGDPL](https://pbgdpl.moj.gov.vn/qt/tintuc/Pages/Hoat-Dong-PGBDPLTW.aspx?ItemID=2315)). `Luật Việc làm 2025` và các văn bản hướng dẫn tiếp tục chi phối phần BHTN, còn BHYT có nghị định hướng dẫn riêng ([Chinhphu.vn về Luật Việc làm 2025](https://xaydungchinhsach.chinhphu.vn/toan-van-luat-viec-lam-119250711173403835.htm), [Chinhphu.vn về Nghị định 188/2025/NĐ-CP](https://baochinhphu.vn/quy-dinh-moi-ve-doi-tuong-muc-dong-bao-hiem-y-te-102250711120524105.htm)). Vì vậy plan này **không hardcode một “phiên bản 2026” duy nhất**, mà thiết kế `versioned policy` theo ngày hiệu lực.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Route `/insurance` | ⚠️ Có route nhưng chưa có nghiệp vụ | `frontend/src/views/insurance/InsuranceView.vue` vẫn là placeholder |
| Menu “Bảo hiểm BHXH” | ✅ Đã có | Đã nằm trong `AppMenu.vue` |
| RBAC module `insurance` | ✅ Đã seed | `backend/app/seeds/rbac.py` đã có quyền view/create/edit |
| `employees.bhxh_code` | ✅ Đã có | Hiện đang nằm trong hồ sơ nhân viên (`Employee`, schema, form, import/export) |
| Import/Export cột `Số BHXH` | ✅ Đã có | `employee_import_service.py`, `employee_export_service.py` |
| `employee_contracts.insurance_salary` | ✅ Đã có | Hiện là nguồn runtime rõ nhất cho nền lương BHXH |
| `job_positions.bhxh_allowance` | ✅ Đã có | Chỉ là thành phần phụ cấp, chưa đủ để suy ra toàn bộ mức đóng |
| `regional_minimum_wages`, `company_bhxh_region`, `salary_scales` | ✅ Đã có | Là nền cho tính toán mức lương BHXH |
| `company_bhxh_region` seed mặc định | ✅ Đã có | Seed hiện tại đặt công ty ở `Vùng III`, `effective_from = 2026-01-01` |
| `FEATURES.md` đánh dấu Insurance/Salary là ✅ | ⚠️ Lệch với code hiện tại | Insurance view và Salary view vẫn đang là placeholder |
| Bảng/Model hồ sơ bảo hiểm riêng | ❌ Chưa có | Chưa có `employee_insurance_profiles` hay tương đương |
| API danh sách / chi tiết bảo hiểm | ❌ Chưa có | `router.py` chưa mount insurance endpoints |
| Resolver cấu hình đóng hiệu lực theo ngày | ❌ Chưa có | Chưa có seam resolve `policy version + company region + component rates` theo ngày áp dụng |
| Cấu hình tỷ lệ đóng versioned | ❌ Chưa có | Chưa có policy version / component rates |
| Cấu hình “công ty nộp hộ” | ❌ Chưa có | Chưa có field hay UI cho employer advance |
| Override fixed amount theo từng thành phần | ❌ Chưa có | Chưa có model hay read model |
| Danh mục nơi KCB ban đầu | ❌ Chưa có | Chưa có catalog hay field runtime |
| Trạng thái tham gia BHXH/BHYT/BHTN | ❌ Chưa có | Chưa có field hay workflow riêng |
| Ngày tham gia BHXH tại công ty | ❌ Chưa có | Chưa có field hay migration |

---

## Phạm vi 6.1

Theo `docs/FEATURES.md §6.1`, module này phải quản lý:

| Tính năng | Mục tiêu |
|---|---|
| `Mã số BHXH` | Theo dõi mã số BHXH của từng nhân viên |
| `Nơi đăng ký khám chữa bệnh ban đầu (BHYT)` | Lưu nơi KCB ban đầu hiện hành |
| `Mức lương đóng BHXH` | Lưu/hiển thị nền tính BHXH hiện hành của nhân viên |
| `Ngày tham gia BHXH tại công ty` | Lưu ngày bắt đầu tham gia tại công ty hiện tại |
| `Trạng thái` | `active` / `paused` / `stopped` tương ứng Đang đóng / Tạm dừng / Đã nghỉ |

### Điều chỉnh phạm vi theo yêu cầu mới

Các yêu cầu mới làm rõ rằng `6.1` không thể triển khai an toàn nếu thiếu nền dùng chung:

- Cần **version hóa văn bản/quy định**; version mới `active` thì version cũ phải `inactive`.
- Cần **cấu hình vùng BHXH công ty** theo thời gian; hiện repo đang seed `Vùng III`.
- Cần **cấu hình tỷ lệ đóng theo từng thành phần** cho `người lao động` và `người sử dụng lao động`.
- Cần đánh dấu component nào là **công ty nộp hộ phần NLĐ** rồi khấu trừ lại vào lương.
- Cần cho phép **ngoại lệ theo từng nhân viên, từng component**: dùng đúng chính sách công ty hoặc nhập **mức cố định**.

Vì vậy plan này chốt lại:

1. `6.1` vẫn là màn hồ sơ bảo hiểm nhân viên.
2. Nhưng phải có **shared insurance foundation** dùng chung với `6.2` và phần tính toán của `7.x`.
3. Các phần “policy version”, “company region”, “company pays on behalf”, “fixed amount override” là **dependency bắt buộc** của `6.1`, không để tách rời sang sau.

### Không nằm trong 6.1

| Phần | Lý do |
|---|---|
| `6.2 Tỷ lệ đóng BHXH` | Sở hữu `versioned legal regulations`, `effective_from/effective_to`, `active/inactive by date`, `company_bhxh_region`, `company default contribution rates by component/payer side`, và default-vs-override contribution rules. `6.1` chỉ tiêu thụ snapshot đã resolve |
| `6.3 Biến động tăng/giảm BHXH` | Cần event ledger / lịch sử hiệu lực riêng |
| `6.4 Báo cáo BHXH` | Cần report/export biểu mẫu |
| `7.2 Điều chỉnh lương BHXH` | Cần workflow quyết định điều chỉnh, không phải current-state profile |

> **Kết luận kiến trúc:** `6.1` quản lý current-state của hồ sơ bảo hiểm nhân viên, nhưng phải có lớp nền versioned để không làm sai pháp lý và không khóa đường phát triển của `6.2`, `6.3`, `7.x`.

---

## Phân tích hiện trạng kỹ thuật

### 1. Dữ liệu đã có và có thể tái sử dụng

| Dữ liệu hiện có | Nguồn | Ghi chú |
|---|---|---|
| `bhxh_code` | `employees` | Đã được nhập/sửa từ hồ sơ nhân viên và import Excel |
| `insurance_salary` | `employee_contracts` | Là nguồn runtime rõ nhất cho “nền tính BHXH” hiện tại |
| `bhxh_allowance`, `non_bhxh_allowance` | `job_positions` | Là thành phần tham chiếu cho tính toán |
| `regional_minimum_wages`, `company_bhxh_region`, `salary_scales` | `salary.py` | Là nền cho công thức/lịch sử 7.x |

### 2. Khoảng trống hiện tại

- Chưa có nơi lưu `nơi KCB ban đầu`.
- Chưa có nơi lưu `ngày tham gia BHXH tại công ty`.
- Chưa có `trạng thái tham gia BHXH`.
- Chưa có list/filter/API riêng cho module bảo hiểm.
- Chưa có quy ước versioned cho tỷ lệ đóng.
- Chưa có policy `company pays on behalf`.
- Chưa có per-employee fixed override theo từng component.

### 3. Ràng buộc phải tôn trọng

- `bhxh_code` hiện đang được dùng trong `EmployeeDetailView`, import và export; không thể cắt bỏ đột ngột.
- `insurance_salary` đã tồn tại ở hợp đồng; nếu 6.1 tạo thêm một nguồn ghi độc lập cho cùng khái niệm sẽ gây dual-write.
- `employee.status` hiện là vòng đời nhân sự (`probation` / `official` / `long_leave` / `resigned`), không được tái dùng làm `participation_status` của bảo hiểm.
- `docs/FEATURES.md` đang đánh dấu module bảo hiểm/lương BHXH là “đã có”, nhưng source thực tế chưa có màn hình nghiệp vụ tương ứng.
- Thay đổi quy định/tỷ lệ chỉ được áp dụng cho dữ liệu hiệu lực mới; không được làm sai lịch sử hợp đồng, hồ sơ bảo hiểm hay báo cáo đã chốt.
- `employee_insurance_profiles` không được trở thành write-source cho `company_bhxh_region`, `policy version`, hay `default contribution rates`; các giá trị đó phải nằm ở bảng cấu hình versioned và được resolve theo ngày.

---

## Quyết định thiết kế

### 1. Tách 3 lớp: `pháp lý` → `công ty` → `nhân viên`

Plan mới dùng 3 lớp rõ ràng:

| Lớp | Vai trò |
|---|---|
| `Policy version` | Phiên bản quy định/tỷ lệ đóng theo ngày hiệu lực |
| `Company default` | Chính sách công ty đang áp dụng trên nền policy, gồm vùng công ty và rule nộp hộ |
| `Employee override` | Ngoại lệ cho từng nhân viên hoặc từng component |

Điều này tránh trộn lẫn:
- thay đổi của pháp luật
- cấu hình nội bộ của công ty
- ngoại lệ cá nhân

### 2. Tạo bảng hồ sơ bảo hiểm hiện hành riêng

Không nhét thêm cột vào `employees`. Tạo bảng:

```sql
employee_insurance_profiles
```

Lý do:
- `6.1` có lifecycle riêng với `status`, `joined_date`, `clinic`.
- `6.3` sau này cần lịch sử biến động tăng/giảm.
- `bhxh_code` về domain thuộc hồ sơ bảo hiểm hơn là “liên lạc & thuế”.

### 3. `insurance_salary` và `component contribution` là hai seam khác nhau

Hai khái niệm phải tách riêng:

| Khái niệm | Ý nghĩa |
|---|---|
| `insurance_salary` / `insurance_basis_amount` | Nền lương/căn cứ để tính đóng, ưu tiên đọc từ hợp đồng hiện hành |
| `component contribution` | Số phải đóng theo từng component: BHYT, BHTN, hưu trí-tử tuất... |

Thứ tự resolve `insurance_basis_amount`:

1. Ưu tiên `employee_contracts.insurance_salary` của hợp đồng hiện hành.
2. Nếu hợp đồng không có thì mới dùng computed basis từ `regional_minimum_wages + company_bhxh_region + salary_scale + job_position.bhxh_allowance`.
3. Chỉ dùng `manual_fixed` ở cấp hồ sơ nếu nghiệp vụ thật sự yêu cầu override nền tính.

> Điểm cần giữ chặt: `insurance_salary` một mình **không đủ** cho yêu cầu mới về mức đóng. Nếu `6.1` hiển thị tỷ lệ/số tiền phải đóng thì chúng phải được resolve từ `effective legal rule + company region + company default rate set + employee override`, không được suy luận chỉ từ `insurance_salary`.

### 4. `Nơi KCB ban đầu` giai đoạn đầu lưu dạng text

Hiện repo không có catalog hay mã chuẩn cơ sở KCB. Giai đoạn đầu lưu:

```sql
bhyt_initial_clinic_name VARCHAR(255)
```

Nếu `6.4` sau này cần mã chuẩn biểu mẫu thì nâng cấp thành catalog riêng.

### 5. Giữ tương thích ngược với `employees.bhxh_code`

Trong rollout đầu:
- tạo bảng mới
- backfill `employees.bhxh_code` sang hồ sơ bảo hiểm
- write mới mirror sang cả `employee_insurance_profiles.bhxh_code` và `employees.bhxh_code`

Sau khi UI/API module bảo hiểm ổn định mới cân nhắc bỏ field khỏi form liên lạc của hồ sơ nhân viên.

### 6. Policy version phải versioned, không ghi đè lịch sử

Khi có văn bản mới:

- thêm `policy_version` mới với `effective_from`
- version đang `active` phải được đóng `effective_to`
- lịch sử áp dụng cũ phải còn truy vết được

> Đây là yêu cầu bắt buộc vì người dùng đã nêu rõ “văn bản mới active thì văn bản cũ inactive”.

---

## Thiết kế cơ sở dữ liệu

### Bảng `employee_insurance_profiles`

```sql
CREATE TABLE employee_insurance_profiles (
    id                          SERIAL PRIMARY KEY,
    employee_id                 INTEGER NOT NULL UNIQUE
                                REFERENCES employees(id) ON DELETE CASCADE,

    bhxh_code                   VARCHAR(20),
    bhyt_initial_clinic_name    VARCHAR(255),
    company_bhxh_joined_date    DATE,

    participation_status        VARCHAR(20) NOT NULL DEFAULT 'active'
                                CHECK (participation_status IN ('active', 'paused', 'stopped')),
    status_effective_from       DATE,
    status_note                 TEXT,

    insurance_basis_source      VARCHAR(20) NOT NULL DEFAULT 'contract'
                                CHECK (insurance_basis_source IN ('contract', 'computed', 'manual_fixed')),
    insurance_basis_amount      NUMERIC(18,2),
    insurance_policy_version_id INTEGER
                                REFERENCES insurance_policy_versions(id),

    created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP
);

CREATE INDEX ix_employee_insurance_profiles_status
    ON employee_insurance_profiles (participation_status);
CREATE INDEX ix_employee_insurance_profiles_joined_date
    ON employee_insurance_profiles (company_bhxh_joined_date);
```

### Bảng `insurance_contribution_components`

```sql
CREATE TABLE insurance_contribution_components (
    code            VARCHAR(50) PRIMARY KEY,
    name_vi         VARCHAR(255) NOT NULL,
    insurance_kind  VARCHAR(30) NOT NULL,
    sort_order      INTEGER NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
```

Seed mặc định:
- `RETIREMENT_SURVIVOR`
- `SICKNESS_MATERNITY`
- `OCC_ACCIDENT_DISEASE`
- `HEALTH`
- `UNEMPLOYMENT`

### Bảng `insurance_policy_versions`

```sql
CREATE TABLE insurance_policy_versions (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(50) NOT NULL UNIQUE,
    name                VARCHAR(255) NOT NULL,
    legal_basis_summary TEXT,
    effective_from      DATE NOT NULL,
    effective_to        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT FALSE,
    company_region      SMALLINT NOT NULL,
    note                TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP
);
```

Quy tắc:
- chỉ có tối đa 1 version `is_active = true`
- activate version mới phải auto-close version cũ
- `company_region` khởi tạo từ vùng công ty đang hiệu lực

### Bảng `insurance_policy_component_rates`

```sql
CREATE TABLE insurance_policy_component_rates (
    id                              SERIAL PRIMARY KEY,
    policy_version_id               INTEGER NOT NULL
                                    REFERENCES insurance_policy_versions(id) ON DELETE CASCADE,
    component_code                  VARCHAR(50) NOT NULL
                                    REFERENCES insurance_contribution_components(code),
    employee_rate_percent           NUMERIC(8,4) NOT NULL DEFAULT 0,
    employer_rate_percent           NUMERIC(8,4) NOT NULL DEFAULT 0,
    employer_advances_employee_part BOOLEAN NOT NULL DEFAULT FALSE,
    is_active                       BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (policy_version_id, component_code)
);
```

`employer_advances_employee_part` dùng cho case công ty nộp hộ trước rồi khấu trừ lại vào lương.

### Bảng `employee_insurance_component_overrides`

```sql
CREATE TABLE employee_insurance_component_overrides (
    id                              SERIAL PRIMARY KEY,
    employee_insurance_profile_id   INTEGER NOT NULL
                                    REFERENCES employee_insurance_profiles(id) ON DELETE CASCADE,
    component_code                  VARCHAR(50) NOT NULL
                                    REFERENCES insurance_contribution_components(code),
    use_company_default             BOOLEAN NOT NULL DEFAULT TRUE,
    fixed_employee_amount           NUMERIC(18,2),
    fixed_employer_amount           NUMERIC(18,2),
    employer_advances_employee_part BOOLEAN,
    note                            TEXT,
    created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMP,
    UNIQUE (employee_insurance_profile_id, component_code)
);
```

Ý nghĩa:
- mặc định nhân viên dùng `company default`
- nếu có ngoại lệ, từng component có thể nhập fixed amounts
- có thể override cả việc `công ty nộp hộ` ở cấp nhân viên nếu nghiệp vụ cần
- bảng này là **current-state only** trong `6.1`; lịch sử hiệu lực để module khác xử lý

### Vùng công ty

Tiếp tục dùng `company_bhxh_region` đã có trong `salary.py`.  
Plan này chỉ bổ sung:

- UI/API quản lý lịch sử vùng công ty
- ràng buộc khi activate `policy_version` mới phải đọc vùng đang hiệu lực
- seed mặc định giữ `Vùng III`, `effective_from = 2026-01-01` như source hiện tại

---

## Read model cho module 6.1

### Danh sách bảo hiểm nhân viên

```python
class InsuranceContributionComponentSnapshot(BaseModel):
    component_code: str
    component_name: str
    calc_mode: str                      # company_policy | fixed_amount
    employee_rate_percent: Decimal | None
    employer_rate_percent: Decimal | None
    fixed_employee_amount: Decimal | None
    fixed_employer_amount: Decimal | None
    employer_advances_employee_part: bool
    employee_amount: Decimal | None
    employer_amount: Decimal | None

class EmployeeInsuranceListItem(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    job_title_name: str | None

    bhxh_code: str | None
    bhyt_initial_clinic_name: str | None
    company_bhxh_joined_date: date | None
    participation_status: str

    insurance_basis_amount: Decimal | None
    insurance_basis_source: str | None   # contract | computed | manual_fixed
    policy_version_id: int | None
    policy_version_name: str | None
    effective_regulation_code: str | None
    company_region: int | None
    has_component_overrides: bool
    employer_pays_on_behalf: bool

    contract_id: int | None
    contract_number: str | None
    contributions: list[InsuranceContributionComponentSnapshot]
```

### Cách resolve `insurance_basis_amount`

1. Tìm hợp đồng lao động hiện hành.
2. Nếu hợp đồng có `insurance_salary` thì dùng giá trị đó và đánh dấu `basis_source = contract`.
3. Nếu không có, tính từ nền `regional_minimum_wages + company_bhxh_region + salary_scale + job_position`.
4. Nếu hồ sơ dùng `manual_fixed`, trả `basis_source = manual_fixed`.

### Cách resolve component contribution

1. Lấy `policy_version` active theo ngày hiệu lực.
2. Nạp `insurance_policy_component_rates`.
3. Với từng component:
   - nếu employee không có override → dùng company default
   - nếu có override → dùng fixed amounts / employer pays on behalf của override
4. Cờ `employer_advances_employee_part` lấy từ override nếu có, ngược lại lấy từ policy.

---

## Schemas & API

### Schemas

```python
class EmployeeInsuranceComponentOverrideInput(BaseModel):
    component_code: str
    use_company_default: bool = True
    fixed_employee_amount: Optional[Decimal] = None
    fixed_employer_amount: Optional[Decimal] = None
    employer_advances_employee_part: Optional[bool] = None

class EmployeeInsuranceProfileBase(BaseModel):
    bhxh_code: Optional[str] = Field(None, max_length=20)
    bhyt_initial_clinic_name: Optional[str] = Field(None, max_length=255)
    company_bhxh_joined_date: Optional[date] = None
    participation_status: Literal["active", "paused", "stopped"] = "active"
    status_effective_from: Optional[date] = None
    status_note: Optional[str] = Field(None, max_length=2000)
    insurance_basis_source: Literal["contract", "computed", "manual_fixed"] = "contract"
    insurance_basis_amount: Optional[Decimal] = None

class EmployeeInsuranceProfileUpdate(EmployeeInsuranceProfileBase):
    component_overrides: list[EmployeeInsuranceComponentOverrideInput] = []

class InsurancePolicyComponentRateRead(BaseModel):
    component_code: str
    component_name: str
    employee_rate_percent: Decimal
    employer_rate_percent: Decimal
    employer_advances_employee_part: bool

class InsurancePolicyVersionRead(BaseModel):
    id: int
    code: str
    name: str
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    company_region: int
    legal_basis_summary: Optional[str]
    components: list[InsurancePolicyComponentRateRead]

class EmployeeInsuranceProfileRead(EmployeeInsuranceProfileBase):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str]
    job_title_name: Optional[str]
    policy_version_id: Optional[int]
    policy_version_name: Optional[str]
    effective_regulation_code: Optional[str]
    company_region: Optional[int]
    has_component_overrides: bool
    employer_pays_on_behalf: bool
    contract_id: Optional[int]
    contract_number: Optional[str]
    contributions: list[InsuranceContributionComponentSnapshot] = []
    created_at: datetime
    updated_at: Optional[datetime]
```

### API endpoints

| Method | Path | Permission | Mô tả |
|---|---|---|---|
| `GET` | `/insurance/employees` | `insurance:view` | Danh sách hồ sơ bảo hiểm nhân viên |
| `GET` | `/insurance/employees/{employee_id}` | `insurance:view` | Chi tiết hồ sơ bảo hiểm của 1 nhân viên |
| `PUT` | `/insurance/employees/{employee_id}` | `insurance:edit` | Cập nhật hồ sơ bảo hiểm + overrides |
| `GET` | `/insurance/policy-versions` | `insurance:view` | Danh sách policy versions |
| `POST` | `/insurance/policy-versions` | `insurance:create` | Tạo policy version mới |
| `PUT` | `/insurance/policy-versions/{id}` | `insurance:edit` | Sửa policy version chưa khóa |
| `POST` | `/insurance/policy-versions/{id}/activate` | `insurance:edit` | Activate version mới, auto-inactivate version cũ |
| `GET` | `/insurance/company-region` | `insurance:view` | Xem vùng BHXH công ty hiện hành + lịch sử |
| `PUT` | `/insurance/company-region` | `insurance:edit` | Đổi vùng công ty theo ngày hiệu lực |

### Tương thích với hồ sơ nhân viên

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/employees/{id}` | Tiếp tục trả `bhxh_code` trong giai đoạn compatibility |
| `PUT` | `/employees/{id}` | Nếu client cũ cập nhật `bhxh_code`, service phải mirror sang hồ sơ bảo hiểm |

### Filters cho `GET /insurance/employees`

| Param | Ý nghĩa |
|---|---|
| `keyword` | Tìm theo mã NV, tên nhân viên, mã BHXH |
| `department_id` | Phòng ban hiện tại |
| `participation_status` | `active` / `paused` / `stopped` |
| `has_bhxh_code` | `true/false` |
| `joined_from`, `joined_to` | Lọc theo ngày tham gia BHXH tại công ty |
| `policy_version_id` | Lọc theo policy đang áp dụng |
| `has_component_overrides` | Có/không có override theo component |
| `employer_pays_on_behalf` | Có/không có cờ công ty nộp hộ ở snapshot hiện hành |
| `page`, `page_size` | Phân trang |

---

## Backend implementation

### File đề xuất

```text
backend/app/models/employee_insurance.py           (NEW)
backend/app/schemas/employee_insurance.py          (NEW)
backend/app/services/employee_insurance_service.py (NEW)
backend/app/services/insurance_policy_service.py   (NEW)
backend/app/api/v1/endpoints/insurance.py          (NEW)
backend/alembic/versions/00xx_employee_insurance_profiles.py (NEW)
```

### Service responsibilities

```python
get_insurance_profile(session, employee_id) -> EmployeeInsuranceProfileRead
list_insurance_profiles(session, filters, page, page_size) -> EmployeeInsuranceListPage
upsert_insurance_profile(session, employee_id, payload, actor_id) -> EmployeeInsuranceProfileRead
sync_legacy_bhxh_code(session, employee_id, bhxh_code) -> None

resolve_insurance_basis_snapshot(session, employee_id, on_date) -> InsuranceBasisSnapshot
compute_component_contributions(session, employee_id, on_date) -> list[InsuranceContributionComponentSnapshot]

list_policy_versions(session) -> list[InsurancePolicyVersionRead]
create_policy_version(session, payload, actor_id) -> InsurancePolicyVersionRead
activate_policy_version(session, version_id, actor_id) -> InsurancePolicyVersionRead

get_company_region(session, on_date) -> CompanyRegionRead
upsert_company_region(session, region, effective_from, actor_id) -> CompanyRegionRead
```

### Validation rules

- `employee_id` phải tồn tại.
- `participation_status = stopped` thì `status_effective_from` không được null.
- `company_bhxh_joined_date` nếu có thì không lớn hơn ngày hiện tại.
- Nếu `company_bhxh_joined_date < employees.start_date` thì chỉ cho phép lưu khi `status_note` có nội dung giải thích.
- `bhxh_code` strip whitespace; chuỗi rỗng normalize về `null`.
- chỉ có 1 `insurance_policy_version` được `active` tại một thời điểm.
- khi activate version mới, version cũ bắt buộc có `effective_to`.
- `employee_rate_percent`, `employer_rate_percent` không âm.
- `fixed_employee_amount`, `fixed_employer_amount` phải không âm nếu có giá trị.
- `use_company_default = true` thì không cho phép nhập fixed amounts.
- snapshot hợp lệ chỉ khi có đúng 1 `company_bhxh_region` hiệu lực và đúng 1 `policy version` active cho ngày đang resolve.
- `company_region` chỉ cho phép `1..4`.

### Query strategy cho danh sách

JOIN tối thiểu:
- `employees`
- `employee_insurance_profiles`
- `employee_job_records` (`is_current = true`)
- `departments`
- `job_titles`
- subquery hoặc lateral join để lấy hợp đồng hiện hành và `insurance_basis_amount`
- policy version + component rates đang hiệu lực
- employee component overrides đang hiệu lực

> Danh sách này là read-heavy. Không nên N+1 qua từng employee để lấy contract/policy/override snapshots.

---

## Frontend implementation

### Màn hình `/insurance`

Thay placeholder hiện tại bằng `InsuranceView.vue` thật:

| Khu vực | Nội dung |
|---|---|
| Header | Tên màn + tổng số nhân viên tham gia + policy đang active |
| Filter bar | keyword, phòng ban, trạng thái, policy version, có/không có mã BHXH |
| DataTable | Mã NV, Họ tên, Phòng ban, Mã BHXH, Nơi KCB ban đầu, Ngày tham gia, Trạng thái, Nền tính BHXH |
| Detail/Edit dialog | Sửa `bhxh_code`, `clinic`, `joined_date`, `status`, `note`, override theo từng component |
| Admin config dialog/page | Quản lý policy version, component rates, vùng công ty |

### Vị trí hiển thị trong hồ sơ nhân viên

- Giai đoạn đầu vẫn giữ `Mã số BHXH` trong `EmployeeDetailView`.
- Thêm tab hoặc section “Bảo hiểm” trong hồ sơ nhân viên để deep-link sang module bảo hiểm.
- Sau khi `/insurance` ổn định, có thể bỏ field `bhxh_code` khỏi tab “Liên lạc & Thuế” hoặc chuyển sang readonly.
- Với người có quyền admin/finance, hồ sơ bảo hiểm phải hiển thị rõ nhân viên đang dùng `theo quy định công ty` hay `mức cố định`.

### Frontend services

```text
frontend/src/services/insuranceService.ts          (NEW)
frontend/src/views/insurance/InsuranceView.vue     (REPLACE placeholder)
```

### UI conventions

- Dùng PrimeVue: `DataTable`, `Dialog`, `Select`, `DatePicker`, `Tag`, `InputNumber`, `Checkbox`.
- Không thêm `scoped style` mới nếu có thể dùng global/PrimeVue utility.
- Phần tỷ lệ đóng nên hiển thị rõ:
  - phần NLĐ
  - phần NSDLĐ
  - tổng
  - trạng thái active
  - cờ `công ty nộp hộ`

---

## Migration & compatibility

### Migration dữ liệu

1. Tạo `employee_insurance_profiles`.
2. Tạo `insurance_contribution_components`, `insurance_policy_versions`, `insurance_policy_component_rates`, `employee_insurance_component_overrides`.
3. Seed component codes chuẩn.
4. Seed policy version mặc định theo bộ quy định đang áp dụng tại thời điểm rollout.
5. Backfill toàn bộ nhân viên hiện có:

```sql
INSERT INTO employee_insurance_profiles (
    employee_id, bhxh_code, participation_status, insurance_basis_source
)
SELECT id, bhxh_code, 'active', 'contract'
FROM employees
WHERE is_active = true;
```

6. Với nhân viên `status = resigned`, có thể backfill `participation_status = stopped`.
7. Không tự suy luận `company_bhxh_joined_date` từ `start_date`; để `null` nếu chưa có dữ liệu chắc chắn.
8. Không fabricate `component overrides`, `employer_pays_on_behalf`, hay policy links ở cấp nhân viên khi backfill; để mặc định null / company-default cho tới khi được cấu hình rõ.

### Seeder pháp lý/cấu hình

Seeder phải tách làm 2 tầng:

1. `seed_insurance_components()`
2. `seed_insurance_policy_versions()`

`seed_insurance_policy_versions()` phải:
- seed đúng policy đang active tại thời điểm triển khai
- đóng policy cũ khi seed policy mới trong future migration
- không sửa ngược lịch sử những version đã khóa
- không lấy phần trăm seed chỉ từ ảnh tham chiếu hoặc memory; từng tỷ lệ theo component phải được verify lại từ văn bản pháp lý/nguồn chính thức ngay trước khi code seeder

> **Lưu ý:** source nội bộ đang seed `company_bhxh_region` là `Vùng III`, `effective_from = 2026-01-01`. Plan giữ nguyên giả định này cho dữ liệu công ty.

### Compatibility contract

Trong phase đầu:
- `employees.bhxh_code` vẫn tồn tại trong schema và API cũ.
- `employee_service.create/update` khi nhận `bhxh_code` phải sync sang `employee_insurance_profiles`.
- `employee_import_service` tiếp tục nhận cột `Số BHXH`, nhưng write vào cả hai nơi.
- `employee_export_service` có thể vẫn đọc từ `employees.bhxh_code` trong phase đầu, hoặc chuyển sang hồ sơ bảo hiểm sau khi backfill xong.

---

## Kế hoạch triển khai theo lát cắt

### Slice 0 — Shared Insurance Foundation

**Mục tiêu:** Có nền pháp lý/cấu hình dùng chung cho `6.1`, `6.2` và phần tính toán của `7.x`.

- Tạo tables policy version + component rates
- Tạo CRUD/API activate/deactivate policy
- Tạo API/UI cấu hình vùng công ty
- Seed `Vùng III` và policy version đang active

**Exit criteria:**
- Chỉ có 1 policy version active
- Vùng công ty đang hiệu lực truy vấn được
- Thay policy version mới không làm mất lịch sử version cũ

### Slice 1 — Employee Insurance Schema + Backfill Compatibility

**Mục tiêu:** Có bảng hồ sơ bảo hiểm và compatibility với source cũ.

- Thêm `employee_insurance_profiles`
- Thêm `employee_insurance_component_overrides`
- Backfill `bhxh_code`
- Sync write từ `employee_service`
- Test migration + compatibility import/export

**Exit criteria:**
- Không vỡ `EmployeeDetailView`
- Import/Export cột `Số BHXH` vẫn chạy
- DB có 1 hồ sơ bảo hiểm cho mọi nhân viên hiện có

### Slice 1.5 — Effective Contribution Config Resolver

**Mục tiêu:** Có seam resolve `policy version + company region + component rates` theo ngày trước khi `6.1` hiển thị snapshot đóng.

- Tạo resolver backend dùng cho `6.1`
- Chặn UI hiển thị contribution snapshot nếu chưa có config hợp lệ

**Exit criteria:**
- Với một ngày bất kỳ, resolver tìm được đúng 1 company region và đúng 1 policy active
- `6.1` không phải tự sở hữu hay tự sửa company config

### Slice 2 — Backend Insurance API + Computation Snapshot

**Mục tiêu:** Có read/write seam riêng cho bảo hiểm.

- Tạo schemas, service, endpoints `insurance`
- List/filter/detail/update
- Resolve `insurance_basis_amount`
- Resolve component snapshots theo `company_policy` hoặc `fixed_amount`

**Exit criteria:**
- API `/insurance/employees` usable
- Snapshot contribution đọc đúng policy active + employee override

### Slice 3 — Frontend Insurance View + Admin Config

**Mục tiêu:** Thay placeholder bằng màn thật.

- Tạo `insuranceService.ts`
- Thay `InsuranceView.vue` bằng DataTable + dialog chỉnh sửa
- Thêm filter phòng ban/trạng thái/policy
- Tạo UI cấu hình policy version, component rates, company region
- Tạo UI override `company_policy` / `fixed_amount` theo component

**Exit criteria:**
- Người dùng xem và sửa được hồ sơ bảo hiểm hiện hành trên UI
- Admin cấu hình được policy active và vùng công ty
- Browser verification pass cho list/filter/edit

### Slice 4 — Employee Profile Integration Cleanup

**Mục tiêu:** Chuyển dần BHXH từ tab liên lạc sang domain đúng.

- Thêm tab/section “Bảo hiểm” ở hồ sơ nhân viên
- Giảm vai trò edit trực tiếp của `bhxh_code` trong tab Liên lạc & Thuế
- Chuẩn hóa export/read path sang hồ sơ bảo hiểm

**Exit criteria:**
- Một nguồn đọc chính cho dữ liệu bảo hiểm
- Không còn logic rời rạc giữa `employees` và `insurance`

---

## Verification plan

### Backend

- Migration test:
  - bảng mới được tạo
  - backfill đúng số lượng nhân viên
  - `resigned -> stopped` nếu rollout áp dụng rule này
  - chỉ có 1 policy version active
- Service/API tests:
  - list theo `keyword`, `department_id`, `status`
  - update `bhxh_code`, `clinic`, `joined_date`, `status`
  - activate version mới thì version cũ bị inactivate
  - resolve basis theo `contract` / `computed` / `manual_fixed`
  - resolve từng component theo `company_policy` / `fixed_amount`
  - flag `employer_advances_employee_part` được trả đúng
- Compatibility tests:
  - update employee cũ với `bhxh_code` vẫn sync đúng
  - import/export cột `Số BHXH` không regress

### Frontend

- `npm run build`
- Browser-level verification:
  - vào `/insurance`
  - filter theo trạng thái/phòng ban/policy
  - mở dialog sửa
  - save xong table cập nhật đúng
  - đổi active policy version
  - cấu hình 1 component fixed override cho 1 nhân viên
  - kiểm tra network request/response

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Dual-write `bhxh_code` giữa `employees` và bảng mới | Chấp nhận tạm thời trong compatibility phase, có test sync rõ ràng |
| Hiểu sai “nền lương BHXH” và “mức đóng từng thành phần” là một | Tách `insurance_basis_amount` khỏi `component contribution` ngay trong schema/read model |
| Trộn `6.1` với `6.3` | Chưa tạo event ledger trong plan này |
| Trộn `6.1` với `7.x` | Chỉ dựng shared foundation + snapshot; chưa dựng workflow lịch sử điều chỉnh |
| Dữ liệu KCB ban đầu bị trùng tên | Chấp nhận text ở 6.1; nếu báo cáo chuẩn biểu mẫu yêu cầu mã cơ sở, nâng cấp catalog ở phase sau |
| Activate policy mới làm sai dữ liệu cũ | Version hóa bằng `effective_from/effective_to`, không overwrite lịch sử |

---

## Câu hỏi nghiệp vụ cần chốt trước khi code

1. Khi nhân viên `status = resigned`, có mặc định map `participation_status = stopped` không?
2. `Ngày tham gia BHXH tại công ty` có cho phép nhỏ hơn `start_date` trong case chuyển đơn vị / nhận lại lao động cũ không?
3. Có cần bắt buộc nhập `nơi KCB ban đầu` khi `participation_status = active` không?
4. Khi policy version mới active, có cần tự động áp cho toàn bộ nhân viên đang dùng `company_policy` hay chỉ áp từ kỳ tính tiếp theo?
5. `fixed_amount` có cho phép nhập riêng cả `phần NLĐ` và `phần NSDLĐ` cho từng component không, hay chỉ override tổng?
6. Flag `công ty nộp hộ` có được override ở cấp nhân viên, hay chỉ cấu hình ở policy version?
7. Flag `công ty nộp hộ` được áp dụng một lần cho toàn bộ nhân viên, một lần cho toàn bộ profile, hay theo từng component?
8. “Mức cố định” ở yêu cầu nghiệp vụ là override `mức đóng từng component` hay override `nền lương/căn cứ BHXH`? Nếu là vế sau thì seam này phải chuyển về module `7.x`.

> Theo source hiện tại và yêu cầu mới, hướng an toàn nhất là:
> - `insurance_basis_amount` vẫn ưu tiên từ hợp đồng hiện hành
> - còn **mức đóng từng thành phần** được tính từ policy active hoặc fixed override của nhân viên
> - không overwrite lịch sử khi thay policy version.
