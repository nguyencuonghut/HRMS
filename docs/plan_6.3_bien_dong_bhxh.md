# Kế hoạch triển khai — 6.3. Biến động tăng/giảm BHXH

**Phạm vi chính:** Ghi nhận sự kiện tăng/giảm nhân sự đóng bảo hiểm · Bảng tổng hợp biến động theo tháng · Tích hợp tự động với thay đổi trạng thái hồ sơ · Export D02-TS Excel và iBHXH XML  
**Phụ thuộc hoàn thành:** `6.1 Thông tin bảo hiểm nhân viên` ✅ · `6.2 Tỷ lệ đóng BHXH` ✅  
**Căn cứ pháp lý:**
- Luật BHXH 2024 (41/2024/QH15), hiệu lực 01/07/2025 — Điều 16, 17, 97 (trách nhiệm đơn vị báo cáo)
- Luật BHYT (25/2008/QH12 sửa đổi bổ sung)
- Luật Việc làm 2013 (38/2013/QH13) — BHTN
- Quyết định 595/QĐ-BHXH (2017) — Quy trình thu, mẫu D02-TS, C12-TS, bảng mã lý do
- Quyết định 896/QĐ-BHXH (2021) — Cập nhật biểu mẫu
- Nghị định 12/2022/NĐ-CP — Mức phạt chậm báo cáo biến động

---

## Nguyên tắc thiết kế cốt lõi

> **Event table phải là self-contained snapshot.** Khi export D02-TS cho tháng 01/2026, tất cả dữ liệu cần thiết phải lấy được từ chính event record mà không cần JOIN vào employee hay contract — vì những bảng đó có thể đã thay đổi sau khi biến động xảy ra.

Mọi thông tin nhân viên, hợp đồng, tỷ lệ đóng tại thời điểm biến động phải được **snapshot vào event** ngay lúc tạo.

### Phân biệt hai khái niệm "tháng"

| Trường | Ý nghĩa | Ai đặt |
|---|---|---|
| `period_year` / `period_month` | Tháng biến động **xảy ra** trong thực tế (derive từ `effective_date`) | Hệ thống tự tính |
| `suggested_declaration_year` / `suggested_declaration_month` | Tháng kê khai **gợi ý** — tháng nên đưa biến động vào D02-TS | Hệ thống tự tính, HR xem |
| `declared_year` / `declared_month` (trên **line item** của báo cáo 6.4) | Tháng kê khai **chính thức** — tháng thực sự được nộp lên cơ quan BHXH | HR điều chỉnh trong luồng duyệt 6.4 |

> **Thiết kế:** `period_*` và `suggested_declaration_*` sống trên event (6.3). `declared_*` sống trên line item của báo cáo (`insurance_report_line_items`) do 6.4 quản lý — vì một event có thể xuất hiện trong nhiều lần nộp bổ sung với tháng kê khai khác nhau.

### Quy tắc tính `suggested_declaration_month`

```
Mặc định: suggested = tháng của effective_date
Ngoại lệ: nếu effective_date ≤ 5 ngày đầu tháng VÀ created_at ở tháng trước
           → suggested = tháng của created_at  (biến động cuối tháng trước ghi muộn)
```

Ví dụ thực tế:
- Nghỉ việc ngày 28/01, ghi nhận ngày 02/02 → suggested = 02/2026 (không kịp nộp 01)
- Tuyển dụng ngày 15/01, ghi nhận ngày 20/01 → suggested = 01/2026
- HR nhập tay sự kiện từ 3 tháng trước → suggested = tháng effective_date; HR tự điều chỉnh trong bước duyệt

---

## Yêu cầu pháp lý

### Thời hạn báo cáo (Điều 97 Luật BHXH 2024)
Đơn vị phải báo cáo biến động tăng/giảm tới cơ quan BHXH **trong vòng 30 ngày** kể từ ngày phát sinh. Phạt vi phạm: 500.000–1.000.000 đồng/người (NĐ 12/2022/NĐ-CP).

### Loại biến động (QĐ 595/QĐ-BHXH, Phụ lục II — mẫu D02-TS)

| change_type | Ký hiệu mẫu | Trường hợp |
|---|---|---|
| `increase` | **T** | Mới tuyển; Quay lại sau nghỉ; Chuyển từ đơn vị khác |
| `decrease` | **G** | Nghỉ việc; Chuyển đi; Thai sản không đóng; Tạm dừng đóng |

### Mã lý do biến động iBHXH (QĐ 595 Phụ lục II)

| `change_reason` (nội bộ) | `change_type` | Mã iBHXH | Tên theo quyết định |
|---|---|---|---|
| `new_hire` | increase | **T-01** | Mới tham gia lần đầu |
| `return_from_leave` | increase | **T-02** | Tham gia lại sau thời gian nghỉ |
| `transfer_in` | increase | **T-04** | Chuyển đến từ đơn vị khác |
| `contract_renewal` | increase | **T-05** | Lý do khác |
| `manual_correction` | increase | **T-05** | Lý do khác |
| `resignation` | decrease | **G-01** | Nghỉ việc |
| `contract_end` | decrease | **G-01** | Nghỉ việc (hết hợp đồng) |
| `dismissal` | decrease | **G-01** | Nghỉ việc (sa thải) |
| `unpaid_leave` | decrease | **G-03** | Tạm dừng đóng BHXH |
| `maternity_no_contribution` | decrease | **G-04** | Hưởng chế độ thai sản |
| `long_term_sick` | decrease | **G-03** | Tạm dừng đóng BHXH |
| `transfer_out` | decrease | **G-05** | Chuyển đi đơn vị khác |
| `manual_correction` | decrease | **G-07** | Lý do khác |

---

## Phân tích gap so với data model hiện tại

### Dữ liệu có sẵn

| Nguồn | Field có sẵn |
|---|---|
| `employees` | `date_of_birth`, `gender`, `nationality_id` |
| `employee_contracts` | `contract_number`, `document_kind`, `signed_date`, `effective_from`, `effective_to`, `insurance_salary` |
| `employee_insurance_profiles` | `bhxh_code`, `bhyt_initial_clinic_name`, `company_bhxh_joined_date`, `insurance_basis_amount` |

### Gap cần xử lý

| Field cần cho D02-TS / iBHXH XML | Trạng thái | Hướng xử lý |
|---|---|---|
| Mã KCB ban đầu (`bhyt_initial_clinic_code`) | ❌ **Thiếu** — hiện chỉ có `bhyt_initial_clinic_name` | Thêm field `bhyt_initial_clinic_code` vào `employee_insurance_profiles` trong migration 0020; snapshot vào event |
| Số CCCD/CMND (`identity_number`) | ❌ **Thiếu** trong model hiện tại | Lưu vào snapshot event khi có; nếu chưa có field thì để nullable |
| Mã quốc tịch (ISO 3166-1 alpha-2) | Có `nationality_id` → cần join | Snapshot `nationality_code` (VN/KR/...) vào event |
| Phụ cấp tính vào mức đóng BHXH | ❌ **Thiếu** — chưa có trong model | Snapshot `allowances_amount` (nullable, default 0) |
| Loại HĐ theo mã iBHXH (01/02/03) | Có `document_kind` + `effective_to` | Derive lúc tạo event, snapshot `contract_type_code` |

> **Lưu ý triển khai:** `bhyt_initial_clinic_code` cần được thêm vào `employee_insurance_profiles` (migration 0020) cùng lúc với bảng event. Hiện tại iBHXH XML sẽ để trống nếu không có mã này — không blocking nhưng cần điền trước khi nộp file chính thức.

---

## Thiết kế dữ liệu

### Bảng `insurance_change_events` (Sổ cái biến động — self-contained)

```sql
CREATE TABLE insurance_change_events (
    id              SERIAL PRIMARY KEY,
    employee_id     INT NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,

    -- ── Thông tin biến động ──────────────────────────────────────────────
    change_type     VARCHAR(10)  NOT NULL,  -- 'increase' | 'decrease'
    change_reason   VARCHAR(50)  NOT NULL,  -- xem bảng mã lý do ở trên
    ibhxh_reason_code VARCHAR(5) NOT NULL,  -- 'T-01'..'T-05', 'G-01'..'G-07'
    effective_date  DATE         NOT NULL,  -- Ngày biến động có hiệu lực
    period_year     SMALLINT     NOT NULL,  -- Năm kỳ báo cáo D02-TS
    period_month    SMALLINT     NOT NULL,  -- Tháng kỳ báo cáo (1–12)

    -- ── Snapshot nhân viên tại thời điểm biến động ───────────────────────
    employee_name_snapshot      VARCHAR(255) NOT NULL,
    date_of_birth_snapshot      DATE         NOT NULL,
    gender_snapshot             VARCHAR(10)  NOT NULL,  -- 'male' | 'female'
    nationality_code_snapshot   VARCHAR(10)  NOT NULL DEFAULT 'VN',  -- ISO 3166-1 alpha-2
    identity_number_snapshot    VARCHAR(25),            -- CCCD/CMND (nullable)

    -- ── Snapshot hợp đồng tại thời điểm biến động ───────────────────────
    contract_number_snapshot    VARCHAR(100),
    contract_type_code_snapshot VARCHAR(5),   -- '01'=xác định, '02'=vô thời hạn, '03'=thử việc
    contract_signed_date_snapshot DATE,
    contract_from_snapshot      DATE,
    contract_to_snapshot        DATE,         -- NULL nếu vô thời hạn

    -- ── Snapshot bảo hiểm tại thời điểm biến động ───────────────────────
    bhxh_code_snapshot          VARCHAR(20),
    basis_amount                NUMERIC(18, 2) NOT NULL,  -- Mức lương đóng
    allowances_amount           NUMERIC(18, 2) NOT NULL DEFAULT 0,  -- Phụ cấp tính vào mức đóng
    bhyt_clinic_name_snapshot   VARCHAR(255),
    bhyt_clinic_code_snapshot   VARCHAR(20),  -- Mã KCB — dùng trong iBHXH XML
    policy_version_code_snapshot VARCHAR(50), -- Mã policy version (tỷ lệ đóng)
    employee_rate_total_snapshot NUMERIC(8, 4) NOT NULL DEFAULT 0,  -- Tổng % NLĐ
    employer_rate_total_snapshot NUMERIC(8, 4) NOT NULL DEFAULT 0,  -- Tổng % NSDLĐ

    -- ── Trạng thái cũ/mới ───────────────────────────────────────────────
    old_status      VARCHAR(20),             -- NULL nếu profile mới
    new_status      VARCHAR(20) NOT NULL,

    -- ── Tháng kê khai gợi ý (6.4 sẽ dùng làm giá trị mặc định cho declared_month) ──
    suggested_declaration_year  SMALLINT NOT NULL,  -- hệ thống tính theo quy tắc trên
    suggested_declaration_month SMALLINT NOT NULL,  -- CHECK (1..12)

    -- ── Metadata ────────────────────────────────────────────────────────
    is_manual       BOOLEAN      NOT NULL DEFAULT FALSE,
    note            TEXT,
    created_by_id   INT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),

    CONSTRAINT ck_ice_change_type   CHECK (change_type IN ('increase', 'decrease')),
    CONSTRAINT ck_ice_reason        CHECK (change_reason IN (
        'new_hire', 'return_from_leave', 'transfer_in', 'contract_renewal',
        'resignation', 'contract_end', 'dismissal',
        'unpaid_leave', 'maternity_no_contribution', 'long_term_sick', 'transfer_out',
        'manual_correction'
    )),
    CONSTRAINT ck_ice_period_month  CHECK (period_month BETWEEN 1 AND 12),
    CONSTRAINT ck_ice_basis_positive CHECK (basis_amount > 0)
);

CREATE INDEX ix_ice_employee_id    ON insurance_change_events(employee_id);
CREATE INDEX ix_ice_period         ON insurance_change_events(period_year, period_month);
CREATE INDEX ix_ice_effective_date ON insurance_change_events(effective_date);
CREATE INDEX ix_ice_change_type    ON insurance_change_events(change_type);
CREATE INDEX ix_ice_ibhxh_code     ON insurance_change_events(ibhxh_reason_code);
```

### Bổ sung vào `employee_insurance_profiles` (cùng migration 0020)

```sql
ALTER TABLE employee_insurance_profiles
    ADD COLUMN bhyt_initial_clinic_code VARCHAR(20);
```

> Nullable — không breaking. HR cần cập nhật mã KCB cho nhân viên hiện hữu trước khi export iBHXH XML.

### Bảng tổng hợp theo tháng (query on-the-fly)

```sql
SELECT
    period_year,
    period_month,
    COUNT(*)                                FILTER (WHERE change_type = 'increase') AS total_increase,
    COUNT(*)                                FILTER (WHERE change_type = 'decrease') AS total_decrease,
    COUNT(*) FILTER (WHERE change_type = 'increase') -
    COUNT(*) FILTER (WHERE change_type = 'decrease')                               AS net_change,
    COUNT(*)                                FILTER (WHERE is_manual = TRUE)         AS manual_entries,
    BOOL_OR(bhyt_clinic_code_snapshot IS NULL
        AND change_type = 'increase')                                               AS has_missing_clinic_code
FROM insurance_change_events
GROUP BY period_year, period_month
ORDER BY period_year DESC, period_month DESC;
```

`has_missing_clinic_code`: cảnh báo nếu có TĂNG mà chưa có mã KCB → iBHXH XML sẽ thiếu trường này.

---

## Mapping D02-TS ↔ Event fields

| Cột D02-TS (QĐ 595) | Field event tương ứng | Ghi chú |
|---|---|---|
| STT | (tự tăng lúc export) | |
| Họ và tên | `employee_name_snapshot` | |
| Mã số BHXH | `bhxh_code_snapshot` | |
| Ngày tháng năm sinh | `date_of_birth_snapshot` | Format dd/MM/yyyy |
| Giới tính | `gender_snapshot` → Nam/Nữ | Map 'male'→'Nam', 'female'→'Nữ' |
| Quốc tịch | `nationality_code_snapshot` | VN → Việt Nam |
| Loại hợp đồng | `contract_type_code_snapshot` → tên | 01→Xác định, 02→Vô thời hạn, 03→Thử việc |
| Số hợp đồng | `contract_number_snapshot` | |
| Ngày ký hợp đồng | `contract_signed_date_snapshot` | |
| Ngày kết thúc hợp đồng | `contract_to_snapshot` | Để trống nếu vô thời hạn |
| Mức tiền lương đóng BHXH | `basis_amount` | |
| Phụ cấp tính vào mức đóng | `allowances_amount` | |
| Nơi đăng ký KCB ban đầu | `bhyt_clinic_name_snapshot` | Trên D02-TS dùng tên |
| Ngày tham gia / nghỉ | `effective_date` | |
| Loại biến động | `change_type` → T/G | |
| Lý do | `ibhxh_reason_code` | |
| Ghi chú | `note` | |

### Mapping iBHXH XML ↔ Event fields

```xml
<laoDong>
  <hoTen>         employee_name_snapshot       </hoTen>
  <maSoBHXH>      bhxh_code_snapshot           </maSoBHXH>
  <ngaySinh>      date_of_birth_snapshot       </ngaySinh>  <!-- YYYY-MM-DD -->
  <gioiTinh>      gender_snapshot → 1/2        </gioiTinh>  <!-- 1=Nam, 2=Nữ -->
  <quocTich>      nationality_code_snapshot    </quocTich>  <!-- VN -->
  <loaiBienDong>  change_type → T/G            </loaiBienDong>
  <maLyDo>        ibhxh_reason_code (01..07)   </maLyDo>    <!-- phần số sau dấu - -->
  <ngayBienDong>  effective_date               </ngayBienDong>
  <mucLuong>      basis_amount                 </mucLuong>
  <phuCapLuong>   allowances_amount            </phuCapLuong>
  <loaiHD>        contract_type_code_snapshot  </loaiHD>    <!-- 01/02/03 -->
  <soHopDong>     contract_number_snapshot     </soHopDong>
  <ngayKyHD>      contract_signed_date_snapshot</ngayKyHD>
  <ngayKetThucHD> contract_to_snapshot         </ngayKetThucHD>
  <noiDangKyKCB>  bhyt_clinic_code_snapshot    </noiDangKyKCB>  <!-- ⚠️ cần có mã -->
</laoDong>
```

> **⚠️ Version iBHXH:** Format XML trên là cấu trúc tham chiếu từ iBHXH 3.0.x. Cần verify lại schema XML chính xác từ phần mềm iBHXH đang triển khai tại công ty trước khi code Slice 5.

---

## Thiết kế API

### Endpoints `insurance/change-events`

```
GET    /insurance/change-events
       ?period_year=&period_month=&employee_id=&change_type=&keyword=&page=&page_size=
       → InsuranceChangeEventListPage

GET    /insurance/change-events/monthly-summary?year=2026
       → list[InsuranceMonthlyChangeSummary]

POST   /insurance/change-events
       body: InsuranceChangeEventCreate  (is_manual bắt buộc True)
       → InsuranceChangeEventRead

DELETE /insurance/change-events/{id}
       Chỉ xóa được nếu is_manual=True → 204
       Event auto → 409

GET    /insurance/change-events/export/d02-ts
       ?period_year=&period_month=
       → StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
       Filename: D02-TS_{YYYY}_{MM}.xlsx

GET    /insurance/change-events/export/ibhxh-xml
       ?period_year=&period_month=
       → StreamingResponse (application/xml)
       Filename: IBHXH_{YYYY}_{MM}.xml
```

### Schemas

```python
class InsuranceChangeEventRead(BaseModel):
    id: int
    employee_id: int
    employee_code: str           # JOIN employees tại query time (không snapshot)
    change_type: Literal['increase', 'decrease']
    change_reason: str
    ibhxh_reason_code: str
    effective_date: date
    period_year: int
    period_month: int

    # Snapshot fields
    employee_name_snapshot: str
    date_of_birth_snapshot: date
    gender_snapshot: str
    nationality_code_snapshot: str
    identity_number_snapshot: str | None
    contract_number_snapshot: str | None
    contract_type_code_snapshot: str | None
    bhxh_code_snapshot: str | None
    basis_amount: Decimal
    allowances_amount: Decimal
    bhyt_clinic_name_snapshot: str | None
    bhyt_clinic_code_snapshot: str | None
    policy_version_code_snapshot: str | None
    employee_rate_total_snapshot: Decimal
    employer_rate_total_snapshot: Decimal

    old_status: str | None
    new_status: str
    is_manual: bool
    note: str | None
    created_at: datetime

class InsuranceMonthlyChangeSummary(BaseModel):
    period_year: int
    period_month: int
    total_increase: int
    total_decrease: int
    net_change: int
    manual_entries: int
    has_missing_clinic_code: bool   # cảnh báo export iBHXH sẽ thiếu trường

class InsuranceChangeEventCreate(BaseModel):
    employee_id: int
    change_type: Literal['increase', 'decrease']
    change_reason: str
    effective_date: date
    period_year: int
    period_month: int = Field(ge=1, le=12)
    # Snapshot fields (service sẽ auto-populate từ DB, cho phép override)
    basis_amount: Decimal = Field(gt=0)
    allowances_amount: Decimal = Field(default=0, ge=0)
    note: str | None = None
```

---

## Quy tắc tự động ghi biến động

### Mapping trạng thái → loại biến động

| Chuyển trạng thái | change_type | change_reason mặc định | ibhxh_reason_code |
|---|---|---|---|
| `None` → `active` | increase | `new_hire` | T-01 |
| `active` → `paused` | decrease | `unpaid_leave` | G-03 |
| `paused` → `active` | increase | `return_from_leave` | T-02 |
| `active` → `stopped` | decrease | `resignation` | G-01 |
| `paused` → `stopped` | decrease | `contract_end` | G-01 |
| `stopped` → `active` | increase | `return_from_leave` | T-02 |

### Snapshot population (service logic)

Khi `record_status_change()` được gọi, service phải load và snapshot:

```python
# 1. Employee info
employee = await session.get(Employee, employee_id)
nationality = await get_nationality_code(session, employee.nationality_id)

# 2. Active contract
active_contract = await get_active_contract(session, employee_id)

# 3. Insurance profile
profile = await get_profile(session, employee_id)

# 4. Active policy (tỷ lệ đóng)
active_policy = await get_active_policy(session)
total_emp_rate = sum(r.employee_rate_percent for r in active_policy.rates)
total_er_rate  = sum(r.employer_rate_percent for r in active_policy.rates)

# 5. Contract type code (01/02/03)
contract_type_code = derive_contract_type_code(active_contract)
#   effective_to IS NULL → '02' (vô thời hạn)
#   document_kind == 'probation' → '03'
#   else → '01'

# 6. ibhxh_reason_code
ibhxh_code = _STATUS_TRANSITION_MAP[(old_status, new_status)].ibhxh_reason_code

# 7. basis_amount: resolve từ profile (contract salary / computed / manual)
basis = await resolve_basis_amount(session, profile, active_contract)
```

---

## Kế hoạch triển khai theo slice

### Slice 1 — Migration + Model

**Files:**

```
backend/alembic/versions/0020_create_insurance_change_events.py  (NEW)
backend/app/models/insurance.py                                   (EDIT: thêm InsuranceChangeEvent)
backend/app/models/employee_insurance.py                          (EDIT: thêm bhyt_initial_clinic_code)
```

**Nội dung:**
- Tạo bảng `insurance_change_events` với đầy đủ snapshot columns
- Thêm cột `bhyt_initial_clinic_code VARCHAR(20) NULLABLE` vào `employee_insurance_profiles`

**Exit criteria:**
- `alembic upgrade head` + `alembic downgrade -1` không lỗi
- Schema đúng với thiết kế, đủ constraints và indexes

---

### Slice 2 — Backend Service + API (CRUD + auto-record)

**Files:**

```
backend/app/services/insurance_change_service.py         (NEW)
backend/app/schemas/insurance_change.py                  (NEW)
backend/app/api/v1/endpoints/insurance.py                (EDIT: thêm endpoints CRUD)
backend/app/services/employee_insurance_service.py       (EDIT: gọi auto-record)
backend/app/schemas/employee_insurance.py                (EDIT: thêm bhyt_initial_clinic_code)
```

**`insurance_change_service.py`:**

```python
async def record_status_change(session, employee_id, old_status, new_status,
                                effective_date, note, created_by_id) -> InsuranceChangeEvent:
    """Auto-snapshot toàn bộ thông tin nhân viên/hợp đồng/tỷ lệ vào event."""

async def list_change_events(session, *, period_year, period_month, ...) -> Page: ...
async def get_monthly_summary(session, *, year) -> list[Summary]: ...
async def create_manual_event(session, payload, created_by_id) -> InsuranceChangeEvent: ...
async def delete_manual_event(session, event_id) -> None: ...
```

**Tích hợp vào `upsert_insurance_profile`:**

```python
if old_status != new_status:
    await insurance_change_service.record_status_change(
        session,
        employee_id=employee_id,
        old_status=old_status,
        new_status=new_status,
        effective_date=payload.status_effective_from or date.today(),
        note=payload.status_note,
        created_by_id=current_user.id,
    )
```

**Exit criteria:**
- `PUT /insurance/employees/{id}` thay đổi status → auto tạo event với đầy đủ snapshot
- `GET /insurance/change-events/monthly-summary?year=2026` → đúng aggregate
- `POST` tạo thủ công → 201 với snapshot đầy đủ
- `DELETE` event auto → 409; event manual → 204

---

### Slice 3 — Frontend (Tab Biến động)

**Files:**

```
frontend/src/services/insuranceService.ts                 (EDIT: thêm types + methods)
frontend/src/views/insurance/InsuranceView.vue            (EDIT: thêm tab)
frontend/src/views/insurance/InsuranceChangesTab.vue      (NEW)
frontend/src/assets/styles/views/_insurance.scss          (EDIT: thêm CSS)
```

**Layout `InsuranceChangesTab.vue`:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  BẢNG TỔNG HỢP THÁNG          Năm: [2026 ▼]  [Xuất D02-TS] [Xuất XML] │
│  ┌─────────┬──────┬───────┬────────┬──────────┬─────────────────────┐  │
│  │ Tháng   │ Tăng │ Giảm  │ Số dư  │ Thủ công │ Cảnh báo           │  │
│  ├─────────┼──────┼───────┼────────┼──────────┼─────────────────────┤  │
│  │ T5/2026 │  3   │   1   │  +2    │    0     │                     │  │
│  │ T4/2026 │  5   │   2   │  +3    │    1     │ ⚠ Thiếu mã KCB (2) │  │
│  └─────────┴──────┴───────┴────────┴──────────┴─────────────────────┘  │
│                                                                         │
│  BIẾN ĐỘNG CHI TIẾT  [+ Thêm thủ công]  Tháng:[05/2026▼] Loại:[Tất cả▼]│
│  ┌──────────┬─────────────┬──────────┬───────┬────────────┬──────────┐ │
│  │ Ngày h/l │ Nhân viên   │ Mã BHXH  │ Loại  │ Lý do      │ Mức đóng│ │
│  ├──────────┼─────────────┼──────────┼───────┼────────────┼──────────┤ │
│  │01/05/26  │ NV001 - A   │ 0100xxx  │ TĂNG  │ Mới vào    │ 5.31tr  │ │
│  │15/05/26  │ NV042 - B   │ 0201xxx  │ GIẢM  │ Nghỉ việc  │ 5.31tr  │ │
│  └──────────┴─────────────┴──────────┴───────┴────────────┴──────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**UX rules:**
- Click hàng tháng → filter bảng chi tiết xuống tháng đó
- TĂNG: badge severity="success", GIẢM: badge severity="danger"
- Số dư dương: text xanh; âm: text đỏ
- `⚠ Thiếu mã KCB`: tooltip "X nhân viên tăng tháng này chưa có mã KCB — export iBHXH XML sẽ thiếu trường noiDangKyKCB"
- Chỉ `is_manual=True` có nút xóa [×]
- [Xuất D02-TS]: trigger download file Excel theo tháng đang chọn trong bảng tổng hợp
- [Xuất XML]: trigger download file iBHXH XML

**CSS mới (không scoped, trong `_insurance.scss`):**
```scss
.ins-changes-tab { ... }
.ins-changes-badge-increase { color: var(--p-green-600); font-weight: 700; }
.ins-changes-badge-decrease { color: var(--p-red-600); font-weight: 700; }
.ins-changes-net-positive { color: var(--p-green-600); font-weight: 700; }
.ins-changes-net-negative { color: var(--p-red-600); font-weight: 700; }
.ins-changes-warn { color: var(--p-orange-600); font-size: 0.85rem; }
html.dark-mode { /* adaptive colors */ }
```

**Exit criteria:**
- Tab hiển thị đúng bảng tổng hợp năm
- Click tháng → filter chi tiết
- TĂNG/GIẢM badge màu đúng
- Cảnh báo thiếu mã KCB hiện đúng
- Nút xuất file kích hoạt download đúng tên file
- `vue-tsc --noEmit` không lỗi

---

### Slice 4 — Export backend (D02-TS Excel + iBHXH XML)

**Files:**

```
backend/app/services/insurance_export_service.py         (NEW)
backend/app/api/v1/endpoints/insurance.py                (EDIT: thêm 2 export endpoints)
```

**Dependencies:** `openpyxl` (đã có nếu dùng cho module khác, nếu chưa thêm vào requirements.txt)

**`insurance_export_service.py`:**

```python
async def export_d02_ts_excel(session, period_year, period_month) -> BytesIO:
    """
    Sheet "TĂNG": tất cả event change_type='increase' trong kỳ
    Sheet "GIẢM": tất cả event change_type='decrease' trong kỳ
    Header row: theo mẫu D02-TS QĐ 595/QĐ-BHXH
    """

async def export_ibhxh_xml(session, period_year, period_month) -> str:
    """
    XML chuẩn iBHXH 3.0.x
    Cần verify schema XML từ phần mềm iBHXH đang dùng trước khi deploy.
    Field <noiDangKyKCB> để trống nếu bhyt_clinic_code_snapshot IS NULL.
    """
```

**Cấu trúc D02-TS Excel (theo QĐ 595):**

| Cột | Tên cột | Source field |
|---|---|---|
| A | STT | auto |
| B | Họ và tên | `employee_name_snapshot` |
| C | Mã số BHXH | `bhxh_code_snapshot` |
| D | Ngày sinh | `date_of_birth_snapshot` (dd/MM/yyyy) |
| E | Giới tính | `gender_snapshot` → Nam/Nữ |
| F | Quốc tịch | `nationality_code_snapshot` → tên |
| G | Loại hợp đồng | `contract_type_code_snapshot` → tên |
| H | Số hợp đồng | `contract_number_snapshot` |
| I | Ngày ký HĐ | `contract_signed_date_snapshot` |
| J | Ngày kết thúc HĐ | `contract_to_snapshot` |
| K | Mức lương đóng BHXH | `basis_amount` |
| L | Phụ cấp tính vào mức đóng | `allowances_amount` |
| M | Nơi đăng ký KCB | `bhyt_clinic_name_snapshot` |
| N | Ngày tham gia/nghỉ | `effective_date` |
| O | Lý do | `ibhxh_reason_code` → tên đầy đủ |
| P | Ghi chú | `note` |

**Exit criteria Slice 4:**
- `GET /insurance/change-events/export/d02-ts?period_year=2026&period_month=5` → file .xlsx đúng format
- File Excel có 2 sheet: TĂNG / GIẢM, đúng cột
- `GET /insurance/change-events/export/ibhxh-xml?period_year=2026&period_month=5` → file .xml parse được
- Event có `bhyt_clinic_code_snapshot IS NULL` → field `<noiDangKyKCB>` empty (không crash)

---

### Slice 5 — Tests

**Files:**

```
backend/tests/test_insurance_changes.py  (NEW)
```

**Test cases:**

```python
class TestAutoRecordOnStatusChange:
    async def test_new_hire_creates_increase_event_with_full_snapshot()
        # Verify snapshot: employee_name, date_of_birth, gender, contract_number, basis_amount, policy_code
    async def test_active_to_stopped_creates_decrease_event()
    async def test_active_to_paused_creates_decrease_with_g03_code()
    async def test_paused_to_active_creates_increase_with_t02_code()
    async def test_no_event_when_status_unchanged()
    async def test_ibhxh_reason_code_matches_mapping_table()

class TestManualChangeEvents:
    async def test_create_manual_event_with_valid_payload()
    async def test_delete_manual_event()
    async def test_cannot_delete_auto_event_returns_409()

class TestMonthlyReport:
    async def test_monthly_summary_counts_correctly()
    async def test_has_missing_clinic_code_flag_when_clinic_code_null()
    async def test_filter_by_period_returns_correct_events()

class TestExport:
    async def test_d02_ts_excel_returns_xlsx_content_type()
    async def test_d02_ts_excel_has_increase_and_decrease_sheets()
    async def test_ibhxh_xml_is_valid_xml()
    async def test_export_empty_period_returns_empty_file_not_error()
    async def test_missing_clinic_code_does_not_crash_xml_export()
```

**Exit criteria:**
- Tất cả tests pass
- Regression: `test_insurance_seed.py`, `test_insurance_policy_api.py`, `test_insurance_effective_config.py` không fail thêm

---

## Thứ tự thực hiện

```
Slice 1 (Migration)
  ↓
Slice 2 (Service + API CRUD + auto-record)
  ↓
Slice 3 (Frontend tab)
  ↓
Slice 4 (Export backend)
  ↓
Slice 5 (Tests)
```

---

## Không nằm trong 6.3

| Phần | Thuộc về |
|---|---|
| Approval workflow: duyệt báo cáo trước khi xuất file chính thức | **6.4** |
| Điều chỉnh `declared_year/month` per-row (tháng kê khai chính thức) | **6.4** — qua `insurance_report_line_items` |
| Mẫu C12-TS (Bảng thanh toán thu BHXH) | 6.4 |
| Danh sách nhân viên đang tham gia BHXH + tổng quỹ | 6.4 |
| Nộp bổ sung D02-TS (supplemental filing) | 6.4 |
| Gửi file XML trực tiếp lên cổng dichvucong.gov.vn | Ngoài phạm vi |
| Điều chỉnh mức lương BHXH | 7.2 |

> **Liên kết 6.3 → 6.4:** `suggested_declaration_year/month` trên mỗi event là input cho 6.4. Khi HR tạo báo cáo tháng X trong 6.4, hệ thống tự nạp các event có `suggested_declaration = X` làm line items mặc định, mỗi line item có `declared = suggested` ban đầu và HR có thể điều chỉnh.

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Snapshot thiếu field → export bị lỗi | Service `record_status_change` phải validate đủ field trước khi INSERT; raise ValueError nếu thiếu |
| Double-record khi gọi upsert nhiều lần | Guard: chỉ tạo event nếu `old_status != new_status` |
| Format XML iBHXH thay đổi theo phiên bản phần mềm | Cấu hình `ibhxh_version` trong settings; export service chọn template theo version |
| `bhyt_clinic_code` thiếu → XML bị từ chối bởi iBHXH | Cảnh báo trong UI (cột `has_missing_clinic_code`); XML export vẫn chạy được, chỉ để trống field đó |
| Xóa nhân viên → mất event ledger | `ON DELETE RESTRICT` trên FK `employee_id` |
| Event auto bị sửa sai | Không cho sửa event auto — chỉ cho thêm thủ công hoặc xóa manual; mọi chỉnh sửa phải là event mới |
| Tỷ lệ đóng snapshot sai nếu policy thay đổi sau khi ghi event | Snapshot `policy_version_code_snapshot` + `employee_rate_total_snapshot` / `employer_rate_total_snapshot` → dùng số snapshot, không recalculate |
