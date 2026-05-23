# Kế hoạch triển khai — 7.3. Bảng tổng hợp lương BHXH

**Phạm vi chính:** Bảng tổng hợp mức lương BHXH toàn công ty theo tháng · Tính số tiền đóng BHXH/BHYT/BHTN của NLĐ và NSDLĐ · Xuất Excel đối chiếu với cơ quan BHXH  
**Phụ thuộc hoàn thành:** `7.1 Mức lương BHXH` ✅ · `7.2 Điều chỉnh lương BHXH` ✅ · `6.2 Tỷ lệ đóng BHXH` ✅ (bảng `insurance_policy_component_rates` với tỷ lệ theo thời gian) · `6.1 Thông tin bảo hiểm nhân viên` ✅  
**Căn cứ pháp lý:**
- Luật BHXH 2024 (41/2024/QH15) — tỷ lệ đóng NLĐ: BHXH 8%, BHYT 1.5%, BHTN 1%
- Luật BHXH 2024 — tỷ lệ đóng NSDLĐ: BHXH 17.5%, BHYT 3%, BHTN 1%
- Thông tư 59/2015/TT-BLĐTBXH — phương pháp tính mức đóng

---

## Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|---|---|
| **Không tạo model mới** | Tất cả tính toán từ dữ liệu đã có: `employee_insurance_profiles`, `insurance_policy_component_rates`, `departments` |
| **Tỷ lệ từ `InsuranceContributionComponent`** | Đọc tỷ lệ `employee_rate` và `employer_rate` theo `component_code` và thời điểm áp dụng — không hardcode |
| **Snapshot tại thời điểm tính** | Trả về `basis_amount` từ `insurance_basis_amount` của profile tại thời điểm gọi API (không lưu cache) |
| **Chỉ nhân viên đang đóng** | Chỉ tính nhân viên có `participation_status = 'active'` trong tháng được tra cứu |
| **Excel chuẩn đối chiếu BHXH** | Format đúng cột theo yêu cầu mẫu đối chiếu thực tế với cơ quan BHXH |
| **Không scoped CSS** | Style dùng global class trong `_salary.scss` |

---

## Phạm vi dữ liệu

### Nguồn dữ liệu tính toán

```
employee_insurance_profiles (eip)
  ├── insurance_basis_amount    ← mức lương BHXH hiện tại
  ├── participation_status      ← chỉ lấy 'active'
  └── employee_id

insurance_policy_component_rates (ipcr)
  JOIN insurance_contribution_components (icc)
    ├── component_code          ← 'BHXH' | 'BHYT' | 'BHTN'
    ├── employee_rate           ← tỷ lệ NLĐ đóng (%)
    ├── employer_rate           ← tỷ lệ NSDLĐ đóng (%)
    └── effective_from / effective_to  ← áp dụng theo kỳ

employees (e)
  └── full_name, employee_code, department_id

departments (d)
  └── name AS department_name
```

### Logic tính tỷ lệ theo tháng

```python
def get_rates_for_month(session, year: int, month: int) -> dict[str, dict]:
    """
    Lấy tỷ lệ đóng BHXH/BHYT/BHTN áp dụng cho tháng year/month.
    Query InsuranceContributionComponent có effective_from <= last_day_of_month
    và (effective_to IS NULL OR effective_to >= first_day_of_month).
    Trả về dict:
    {
        'BHXH': {'employee_rate': Decimal('8.00'), 'employer_rate': Decimal('17.50')},
        'BHYT': {'employee_rate': Decimal('1.50'), 'employer_rate': Decimal('3.00')},
        'BHTN': {'employee_rate': Decimal('1.00'), 'employer_rate': Decimal('1.00')},
    }
    Nếu không tìm thấy component nào → raise HTTP 422 với thông báo rõ ràng.
    """
```

### Logic tính số tiền đóng

```python
def compute_contributions(basis: Decimal, rates: dict) -> dict:
    """
    basis: mức lương BHXH (VND)
    rates: output của get_rates_for_month()

    Trả về:
    {
        # NLĐ
        'bhxh_employee': round(basis * rates['BHXH']['employee_rate'] / 100, 0),
        'bhyt_employee': round(basis * rates['BHYT']['employee_rate'] / 100, 0),
        'bhtn_employee': round(basis * rates['BHTN']['employee_rate'] / 100, 0),
        'total_employee': sum of above,

        # NSDLĐ
        'bhxh_employer': round(basis * rates['BHXH']['employer_rate'] / 100, 0),
        'bhyt_employer': round(basis * rates['BHYT']['employer_rate'] / 100, 0),
        'bhtn_employer': round(basis * rates['BHTN']['employer_rate'] / 100, 0),
        'total_employer': sum of above,

        # Tổng cộng
        'grand_total': total_employee + total_employer,
    }
    Làm tròn về số nguyên (đơn vị VND) — dùng ROUND_HALF_UP.
    """
```

---

## Thiết kế API

### Endpoints

```
GET  /salary/summary
     ?year=&month=&department_id=&page=&page_size=
     → SalarySummaryPage

GET  /salary/summary/export
     ?year=&month=&department_id=
     → StreamingResponse (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
     Content-Disposition: attachment; filename="luong_bhxh_{year}_{month:02d}.xlsx"
```

### Schemas

```python
class SalarySummaryRow(BaseModel):
    stt: int                            # số thứ tự trong bảng
    employee_id: int
    employee_code: str
    full_name: str
    department_name: str | None
    basis_amount: Decimal               # mức lương BHXH

    # NLĐ đóng
    bhxh_employee: Decimal              # basis * 8%
    bhyt_employee: Decimal              # basis * 1.5%
    bhtn_employee: Decimal              # basis * 1%
    total_employee: Decimal             # tổng NLĐ

    # NSDLĐ đóng
    bhxh_employer: Decimal              # basis * 17.5%
    bhyt_employer: Decimal              # basis * 3%
    bhtn_employer: Decimal              # basis * 1%
    total_employer: Decimal             # tổng NSDLĐ

    grand_total: Decimal                # NLĐ + NSDLĐ

class SalarySummaryTotals(BaseModel):
    total_employees: int                # tổng số nhân viên đang đóng
    sum_basis: Decimal                  # tổng mức lương BHXH
    sum_bhxh_employee: Decimal
    sum_bhyt_employee: Decimal
    sum_bhtn_employee: Decimal
    sum_total_employee: Decimal
    sum_bhxh_employer: Decimal
    sum_bhyt_employer: Decimal
    sum_bhtn_employer: Decimal
    sum_total_employer: Decimal
    sum_grand_total: Decimal

class SalarySummaryRates(BaseModel):
    """Tỷ lệ áp dụng trong tháng được tính — để hiển thị trên UI"""
    bhxh_employee_rate: Decimal         # 8.00
    bhyt_employee_rate: Decimal         # 1.50
    bhtn_employee_rate: Decimal         # 1.00
    bhxh_employer_rate: Decimal         # 17.50
    bhyt_employer_rate: Decimal         # 3.00
    bhtn_employer_rate: Decimal         # 1.00

class SalarySummaryPage(BaseModel):
    year: int
    month: int
    rates: SalarySummaryRates           # tỷ lệ đang dùng để tính
    items: list[SalarySummaryRow]
    totals: SalarySummaryTotals         # dòng tổng cộng
    total: int                          # tổng số records (pagination)
    page: int
    page_size: int
```

---

## Thiết kế Excel Export

### Cấu trúc file `.xlsx`

**Tên file:** `luong_bhxh_{year}_{month:02d}.xlsx` (vd: `luong_bhxh_2026_06.xlsx`)

**Sheet 1: "Tổng hợp lương BHXH"**

```
Hàng 1: [CÔNG TY TNHH HỒNG HÀ] (merged A1:N1, bold, font 14)
Hàng 2: [BẢNG TỔNG HỢP LƯƠNG BHXH THÁNG {MM}/{YYYY}] (merged A2:N2, bold, font 12)
Hàng 3: [Tỷ lệ: NLĐ: BHXH 8% + BHYT 1.5% + BHTN 1% | NSDLĐ: BHXH 17.5% + BHYT 3% + BHTN 1%]
Hàng 4: [trống]
Hàng 5: Header nhóm (merged cells)
   A5: STT
   B5: Mã NV
   C5: Họ và tên
   D5: Phòng ban
   E5: Mức lương BHXH
   F5-I5: [NGƯỜI LAO ĐỘNG ĐÓNG] (merged F5:I5)
     F6: BHXH (8%)
     G6: BHYT (1.5%)
     H6: BHTN (1%)
     I6: Tổng NLĐ
   J5-M5: [NGƯỜI SỬ DỤNG LAO ĐỘNG ĐÓNG] (merged J5:M5)
     J6: BHXH (17.5%)
     K6: BHYT (3%)
     L6: BHTN (1%)
     M6: Tổng NSDLĐ
   N5-N6: Tổng cộng (merged N5:N6)
Hàng 7+: Dữ liệu từng nhân viên
Hàng cuối: [TỔNG CỘNG] — bold, tô nền xám nhạt
Hàng cuối+2: [Người lập bảng: ___________]  [Kế toán trưởng: ___________]  [Giám đốc: ___________]
```

**Định dạng số:** VND, không có thập phân, có phân cách nghìn (vd: `10,000,000`)

**Màu sắc:**
- Header (hàng 5-6): nền xanh đậm `#1F4E79`, chữ trắng, bold
- Dòng xen kẽ: nền `#F2F2F2` / trắng
- Dòng tổng cộng: nền `#D9E1F2`, bold
- Cột "Mức lương BHXH" và "Tổng cộng": nền vàng nhạt `#FFF2CC`

**Độ rộng cột:**
- A (STT): 6
- B (Mã NV): 10
- C (Họ tên): 25
- D (Phòng ban): 18
- E (Mức lương): 15
- F-N (Số tiền): 14 mỗi cột

### Thư viện sử dụng

```python
# openpyxl (đã có trong project từ 6.4 export)
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
```

---

## Thiết kế Backend

### Files cần tạo / sửa

```
backend/app/services/salary_service.py          (EDIT: thêm summary + export functions)
backend/app/schemas/salary.py                   (EDIT: thêm summary schemas)
backend/app/services/salary_export_service.py   (NEW: export Excel)
backend/app/api/v1/endpoints/salary.py          (EDIT: thêm /summary endpoints)
```

### `salary_service.py` — hàm summary

```python
async def get_salary_summary(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    department_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> SalarySummaryPage:
    """
    1. Lấy rates cho tháng year/month từ InsuranceContributionComponent
    2. Query employees JOIN insurance_profiles (status='active') JOIN departments
       - Filter department_id nếu có
       - Filter: participation_status = 'active'
    3. Với mỗi nhân viên: compute_contributions(basis_amount, rates)
    4. Tính totals (sum các cột)
    5. Trả SalarySummaryPage với stt đánh từ 1
    """

async def get_salary_summary_all(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    department_id: int | None = None,
) -> list[SalarySummaryRow]:
    """
    Không phân trang — trả tất cả records cho export Excel.
    Dùng chung logic với get_salary_summary nhưng không giới hạn page.
    Sort: department_name ASC, employee_code ASC
    """
```

### `salary_export_service.py` — hàm export

```python
async def export_salary_summary_excel(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    department_id: int | None = None,
    company_name: str = "CÔNG TY TNHH HỒNG HÀ",
) -> bytes:
    """
    Tạo file Excel từ dữ liệu summary.
    1. Gọi get_salary_summary_all() lấy dữ liệu
    2. Tạo Workbook + worksheet với format như thiết kế
    3. Ghi header, dữ liệu, dòng tổng
    4. Trả về bytes (để API trả StreamingResponse)
    """
```

---

## Kế hoạch triển khai theo slice

### Slice 1 — Backend: API Summary (không export)

**Mục tiêu:** Cung cấp dữ liệu tổng hợp cho FE hiển thị bảng + tổng cộng.

**Files:**

```
backend/app/services/salary_service.py          (EDIT: thêm get_salary_summary)
backend/app/schemas/salary.py                   (EDIT: thêm summary schemas)
backend/app/api/v1/endpoints/salary.py          (EDIT: thêm GET /salary/summary)
```

**Chi tiết:**

1. Thêm `get_rates_for_month()` helper trong service
2. Thêm `compute_contributions()` helper thuần (không cần session, viết test đơn giản)
3. Thêm `get_salary_summary()` với phân trang
4. Thêm endpoint `GET /salary/summary?year=&month=`

**Exit criteria:**
- `GET /salary/summary?year=2026&month=6` trả đúng danh sách nhân viên active
- Tỷ lệ đọc từ DB, không hardcode
- Số tiền tính đúng (VD: basis=10,000,000, BHXH NLĐ = 800,000)
- `totals` tính đúng sum của tất cả rows
- Nhân viên `participation_status != 'active'` không xuất hiện

---

### Slice 2 — Backend: Export Excel

**Files:**

```
backend/app/services/salary_export_service.py   (NEW)
backend/app/api/v1/endpoints/salary.py          (EDIT: thêm GET /salary/summary/export)
```

**Chi tiết `export_salary_summary_excel()`:**

```python
def _write_header(ws, year: int, month: int, company_name: str, rates: SalarySummaryRates):
    """Viết hàng 1-6: tiêu đề công ty, tiêu đề bảng, thông tin tỷ lệ, header cột"""

def _write_data_rows(ws, rows: list[SalarySummaryRow], start_row: int = 7):
    """Viết từng dòng nhân viên, xen kẽ màu nền"""

def _write_totals_row(ws, totals: SalarySummaryTotals, row_idx: int):
    """Viết dòng TỔNG CỘNG với định dạng bold + nền màu"""

def _write_signature_row(ws, row_idx: int):
    """Viết hàng ký tên ở cuối"""

def _apply_number_format(ws, start_row: int, end_row: int):
    """Áp dụng format số VND cho các cột E-N"""
```

**Endpoint export:**

```python
@router.get("/summary/export")
async def export_salary_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
) -> StreamingResponse:
    excel_bytes = await export_salary_summary_excel(
        session, year=year, month=month, department_id=department_id
    )
    filename = f"luong_bhxh_{year}_{month:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Exit criteria:**
- `GET /salary/summary/export?year=2026&month=6` trả file .xlsx
- File mở được trong LibreOffice/Excel không lỗi
- Header hàng 1-6 đúng format
- Dữ liệu nhân viên đúng, số tiền tính đúng
- Dòng tổng cộng đúng
- Khi không có nhân viên active: trả file với chỉ header + dòng trống tổng = 0

---

### Slice 3 — Frontend

**Files:**

```
frontend/src/services/salaryService.ts                              (EDIT: thêm summary API calls)
frontend/src/views/salary/SalaryView.vue                            (EDIT: thêm tab Tổng hợp BHXH)
frontend/src/views/salary/components/BhxhSummaryTable.vue           (NEW)
frontend/src/assets/styles/views/_salary.scss                       (EDIT)
```

#### Giao diện Tab "Tổng hợp BHXH" (`BhxhSummaryTable.vue`)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Bảng tổng hợp lương BHXH                                                      │
├────────────────────────────────────────────────────────────────────────────────┤
│ Năm: [2026 ▼]  Tháng: [06 ▼]  Phòng ban: [Tất cả ▼]  [Xem]  [Xuất Excel ↓] │
├────────────────────────────────────────────────────────────────────────────────┤
│ Tỷ lệ áp dụng: NLĐ: BHXH 8% + BHYT 1.5% + BHTN 1%                          │
│                NSDLĐ: BHXH 17.5% + BHYT 3% + BHTN 1%                         │
├─────┬───────┬──────────────┬───────────┬──────────────┬────────────────────────┤
│     │       │              │           │              │ NGƯỜI LAO ĐỘNG ĐÓNG   │
│ STT │ Mã NV │ Họ và tên    │ Phòng ban │ Lương BHXH   ├───────┬───────┬───────┤
│     │       │              │           │              │ BHXH  │ BHYT  │ BHTN  │
├─────┼───────┼──────────────┼───────────┼──────────────┼───────┼───────┼───────┤
│   1 │ NV001 │ Nguyễn Văn A │ Kỹ thuật  │ 10,000,000   │800,000│150,000│100,000│
│   2 │ NV002 │ Trần Thị B   │ Kế toán   │  8,500,000   │680,000│127,500│ 85,000│
│   3 │ NV003 │ Lê Văn C     │ Nhân sự   │  7,000,000   │560,000│105,000│ 70,000│
├─────┴───────┴──────────────┴───────────┼──────────────┼───────┼───────┼───────┤
│ TỔNG CỘNG (3 nhân viên)               │ 25,500,000   │   ...  │ ...   │ ...   │
└────────────────────────────────────────┴──────────────┴───────┴───────┴───────┘

[Tiếp: cột Tổng NLĐ | BHXH NSDLĐ | BHYT NSDLĐ | BHTN NSDLĐ | Tổng NSDLĐ | Tổng cộng]
```

**Lưu ý về bảng:** DataTable PrimeVue có horizontal scroll khi màn hình nhỏ (nhiều cột).

**Chi tiết các phần UI:**

**1. Bộ lọc (FilterBar):**
- Dropdown `Năm`: 2020 → current year + 1
- Dropdown `Tháng`: 01-12 (hiển thị "Tháng 01" → "Tháng 12")
- Dropdown `Phòng ban`: danh sách từ API catalog
- Nút `[Xem]`: trigger fetch data
- Nút `[Xuất Excel ↓]`: gọi export API, download file

**2. Banner tỷ lệ:** Hiển thị tỷ lệ từ `response.rates` — tự động cập nhật theo tháng được chọn.

**3. DataTable:**

| Cột | Align | Format |
|---|---|---|
| STT | Center | Số nguyên |
| Mã NV | Left | String |
| Họ và tên | Left | String |
| Phòng ban | Left | String |
| Lương BHXH | Right | `{n:,.0f} đ` |
| BHXH NLĐ (8%) | Right | `{n:,.0f}` |
| BHYT NLĐ (1.5%) | Right | `{n:,.0f}` |
| BHTN NLĐ (1%) | Right | `{n:,.0f}` |
| Tổng NLĐ | Right | Bold |
| BHXH NSDLĐ (17.5%) | Right | `{n:,.0f}` |
| BHYT NSDLĐ (3%) | Right | `{n:,.0f}` |
| BHTN NSDLĐ (1%) | Right | `{n:,.0f}` |
| Tổng NSDLĐ | Right | Bold |
| Tổng cộng | Right | Bold, highlight |

**4. Dòng TỔNG CỘNG:** Ghim ở cuối bảng, tô nền khác, bold. Hiển thị `total_employees` dạng "X nhân viên".

**5. Nút Xuất Excel:**
- Loading spinner khi đang tải
- Sau khi có blob: `window.URL.createObjectURL()` + `<a>.click()` để trigger download
- Toast thành công sau khi tải xong

**salaryService.ts — các hàm cần thêm:**

```typescript
interface SalarySummaryParams {
  year: number
  month: number
  department_id?: number
  page?: number
  page_size?: number
}

export async function getSalarySummary(
  params: SalarySummaryParams
): Promise<SalarySummaryPage>

export async function exportSalarySummary(params: {
  year: number
  month: number
  department_id?: number
}): Promise<Blob>
// Gọi GET /salary/summary/export với responseType: 'blob'
```

**Exit criteria Slice 3:**
- Dropdown năm/tháng/phòng ban hoạt động
- Bảng hiển thị đúng dữ liệu, số tiền format VND đúng
- Dòng tổng cộng đúng
- Banner tỷ lệ hiển thị đúng theo tháng
- Nút Xuất Excel tải được file, tên file đúng format
- Khi tháng không có dữ liệu: hiển thị "Không có nhân viên nào đang đóng BHXH trong tháng này"
- `vue-tsc --noEmit` không lỗi
- Không có `<style scoped>` hay inline style

---

### Slice 4 — Tests

**Files:**

```
backend/tests/test_salary_summary.py    (NEW)
```

**Test cases:**

```python
class TestGetRatesForMonth:
    async def test_returns_correct_rates_for_given_month()
    async def test_raises_when_no_rates_configured_for_month()
    async def test_uses_latest_effective_rate_when_multiple_exist()

class TestComputeContributions:
    def test_bhxh_employee_is_8_percent_of_basis()
    def test_bhyt_employee_is_1_5_percent_of_basis()
    def test_bhtn_employee_is_1_percent_of_basis()
    def test_bhxh_employer_is_17_5_percent_of_basis()
    def test_bhyt_employer_is_3_percent_of_basis()
    def test_bhtn_employer_is_1_percent_of_basis()
    def test_total_employee_is_sum_of_nlđ_components()
    def test_total_employer_is_sum_of_nsdlđ_components()
    def test_grand_total_is_nlđ_plus_nsdlđ()
    def test_rounds_to_integer_using_half_up()

class TestGetSalarySummary:
    async def test_only_includes_active_participation_employees()
    async def test_excludes_paused_employees()
    async def test_excludes_stopped_employees()
    async def test_filter_by_department_id()
    async def test_pagination_works()
    async def test_totals_match_sum_of_rows()
    async def test_stt_starts_from_1_and_increments()
    async def test_returns_rates_used_for_calculation()
    async def test_empty_result_when_no_active_employees()

class TestExportSalarySummaryExcel:
    async def test_returns_bytes()
    async def test_excel_is_valid_xlsx()
    async def test_correct_number_of_data_rows()
    async def test_totals_row_exists_and_correct()
    async def test_header_contains_year_month()
    async def test_basis_amount_column_correct()
    async def test_bhxh_employee_column_is_8_percent()
```

**Exit criteria:**
- Tất cả tests mới pass
- `compute_contributions` là pure function — test không cần DB
- Regression: `pytest tests/test_insurance*.py tests/test_contracts.py` không fail thêm

---

## Thứ tự thực hiện

```
Slice 1 (Backend: API Summary)
  ↓
Slice 2 (Backend: Export Excel)
  ↓
Slice 3 (Frontend)
  ↓
Slice 4 (Tests)
```

---

## Cấu trúc file Excel đầy đủ (spec cho developer)

### Mapping cột → field

| Cột Excel | Header hiển thị | Field Python | Ghi chú |
|---|---|---|---|
| A | STT | `stt` | 1, 2, 3... |
| B | Mã NV | `employee_code` | |
| C | Họ và tên | `full_name` | |
| D | Phòng ban | `department_name` | |
| E | Mức lương BHXH | `basis_amount` | Format: `#,##0` |
| F | BHXH NLĐ (8%) | `bhxh_employee` | Format: `#,##0` |
| G | BHYT NLĐ (1.5%) | `bhyt_employee` | Format: `#,##0` |
| H | BHTN NLĐ (1%) | `bhtn_employee` | Format: `#,##0` |
| I | Tổng NLĐ đóng | `total_employee` | Bold |
| J | BHXH NSDLĐ (17.5%) | `bhxh_employer` | Format: `#,##0` |
| K | BHYT NSDLĐ (3%) | `bhyt_employer` | Format: `#,##0` |
| L | BHTN NSDLĐ (1%) | `bhtn_employer` | Format: `#,##0` |
| M | Tổng NSDLĐ đóng | `total_employer` | Bold |
| N | Tổng cộng | `grand_total` | Bold + highlight |

### Merged cells trong header

```python
# Hàng 1: Tiêu đề công ty
ws.merge_cells("A1:N1")

# Hàng 2: Tiêu đề bảng
ws.merge_cells("A2:N2")

# Hàng 3: Thông tin tỷ lệ
ws.merge_cells("A3:N3")

# Hàng 5: Nhóm cột chính (row 5 = nhóm, row 6 = tên cột chi tiết)
ws.merge_cells("A5:A6")   # STT
ws.merge_cells("B5:B6")   # Mã NV
ws.merge_cells("C5:C6")   # Họ và tên
ws.merge_cells("D5:D6")   # Phòng ban
ws.merge_cells("E5:E6")   # Mức lương BHXH
ws.merge_cells("F5:I5")   # NGƯỜI LAO ĐỘNG ĐÓNG
ws.merge_cells("J5:M5")   # NGƯỜI SỬ DỤNG LAO ĐỘNG ĐÓNG
ws.merge_cells("N5:N6")   # Tổng cộng
```

---

## Không nằm trong 7.3

| Phần | Thuộc về |
|---|---|
| Tạo / sửa mức lương BHXH | 7.2 |
| Xem lịch sử thay đổi mức lương | 7.1 |
| Export D02-TS biến động tăng/giảm | 6.4 |
| Báo cáo quyết toán BHXH năm | Ngoài phạm vi |
| So sánh với số liệu đã nộp cơ quan BHXH | Ngoài phạm vi |
| Tính lương net (sau khi trừ BHXH) | Ngoài phạm vi — thuộc module tính lương riêng |

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Không có tỷ lệ đóng cho tháng được chọn | API trả 422 với message rõ: "Chưa cấu hình tỷ lệ đóng BHXH cho tháng {MM}/{YYYY}. Vào 6.2 để thêm."; FE hiển thị thông báo hướng dẫn |
| Nhân viên có `basis_amount = NULL` | Bỏ qua trong tính toán, không raise exception; hiển thị `—` trên UI với tooltip "Chưa có mức lương BHXH" |
| File Excel quá lớn khi công ty nhiều nhân viên | `get_salary_summary_all()` dùng streaming query (yield per row) thay vì load tất cả vào memory |
| Số tiền bị sai do floating point | Dùng `Decimal` + `ROUND_HALF_UP` suốt pipeline — không dùng `float` cho bất kỳ phép tính nào |
| Tỷ lệ thay đổi giữa các tháng → số liệu không nhất quán | Banner tỷ lệ trên UI hiển thị rõ tỷ lệ đang dùng cho tháng đó; trong Excel ghi rõ tỷ lệ trên hàng 3 |
| Export chậm khi nhiều nhân viên | Tính toán ở Python (không SQL), cache rates 1 lần cho cả batch; target < 3 giây cho 500 nhân viên |
| HR export nhầm tháng | Tên file và header trong Excel ghi rõ tháng/năm; không thể nhầm khi mở file |
