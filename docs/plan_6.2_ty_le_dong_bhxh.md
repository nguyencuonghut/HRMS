# Kế hoạch thực hiện — 6.2. Tỷ lệ đóng BHXH

**Phạm vi chính:** Seed dữ liệu pháp lý mặc định · Quy trình cập nhật tỷ lệ khi có thay đổi quy định · Hoàn thiện UI cấu hình  
**Phụ thuộc hoàn thành:** `6.1 Thông tin bảo hiểm nhân viên` ✅ (toàn bộ infrastructure: models, API, service, InsuranceFoundationView)  
**Phụ thuộc pháp lý:** `Luật BHXH 2024 (41/2024/QH15)` hiệu lực 01/07/2025 · `Luật Việc làm 2025` · `Nghị định 188/2025/NĐ-CP` (BHYT)

> **Cảnh báo seeder:** Theo quyết định thiết kế ở 6.1, *"từng tỷ lệ theo component phải được verify lại từ văn bản pháp lý/nguồn chính thức ngay trước khi code seeder"*. Plan này **không hardcode tỷ lệ cụ thể**; chỉ ghi khung. Người thực hiện phải đối chiếu văn bản hiện hành trước khi nhập số vào seeder.

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Models: `InsurancePolicyVersion`, `InsurancePolicyComponentRate`, `InsuranceContributionComponent` | ✅ Đã có | `backend/app/models/insurance.py` |
| Migration tạo bảng | ✅ Đã có | `0018_create_insurance_foundation.py` |
| Service: CRUD + activate + delete policy | ✅ Đã có | `backend/app/services/insurance_policy_service.py` |
| API endpoints: policy-versions + company-region + effective-config | ✅ Đã có | `backend/app/api/v1/endpoints/insurance.py` |
| Frontend `InsuranceFoundationView.vue` tại `/catalog/insurance` | ✅ Đã có | 562 dòng, đủ create/edit/activate/delete/view |
| Frontend `insuranceService.ts` — methods cho policy/region/components | ✅ Đã có | |
| Tests: policy API, effective config resolver | ✅ Đã có | `test_insurance_policy_api.py`, `test_insurance_effective_config.py` |
| **Seed: `insurance_contribution_components`** | ❌ Chưa có | Chưa có seed nào gọi vào bảng này |
| **Seed: `insurance_policy_versions` + `insurance_policy_component_rates`** | ❌ Chưa có | DB sạch sau deploy; user phải tạo thủ công hoàn toàn |
| UI: nhóm rates theo insurance_kind (BHXH/BHYT/BHTN) | ❌ Thiếu | Bảng rates hiện hiển thị flat, chưa group |
| UI: kiểm tra cấu hình cho ngày bất kỳ | ❌ Thiếu | GET `/insurance/effective-config` chưa được expose trên UI |
| UI: clone policy active → bản nháp mới | ❌ Thiếu | Khi thay đổi quy định phải nhập lại từ đầu |
| Tests: seeder idempotent | ❌ Thiếu | |

### Khoảng trống nghiêm trọng nhất

Sau khi deploy lên môi trường mới, `required seeder` hiện tại **không seed bất kỳ dữ liệu insurance nào**. Người dùng sẽ thấy:
- `GET /insurance/policy-versions` → `[]`
- `GET /insurance/components` → `[]`
- `InsuranceFoundationView` hiện "Chưa có policy đang active" và form tạo policy không có component nào để nhập tỷ lệ
- Toàn bộ màn `/insurance` không tính được contribution snapshot cho bất kỳ nhân viên nào

→ **Slice 1 (seed) phải làm trước tất cả các phần khác.**

---

## Phạm vi 6.2

Theo `docs/FEATURES.md §6.2`:

| Tính năng | Yêu cầu |
|---|---|
| Cấu hình tỷ lệ đóng theo quy định hiện hành | Seed component + policy version mặc định với tỷ lệ đúng pháp luật |
| BHXH: NLĐ 8%, NSDLĐ 17.5% | Verify từ văn bản trước khi seed |
| BHYT: NLĐ 1.5%, NSDLĐ 3% | Verify từ văn bản trước khi seed |
| BHTN: NLĐ 1%, NSDLĐ 1% | Verify từ văn bản trước khi seed |
| Tự động cập nhật khi có thay đổi quy định | Quy trình UI: tạo nháp → sửa tỷ lệ → activate |

### Không nằm trong 6.2

| Phần | Lý do |
|---|---|
| `6.3 Biến động tăng/giảm BHXH` | Cần event ledger / lịch sử hiệu lực riêng |
| `6.4 Báo cáo BHXH` | Cần report/export biểu mẫu |
| `7.x Lương BHXH` | Module riêng về workflow điều chỉnh lương |

---

## Phân tích thiết kế seed

### Component codes đã định nghĩa

Theo model và plan 6.1, 5 components chuẩn:

| Code | Tên tiếng Việt | insurance_kind | sort_order |
|---|---|---|---|
| `RETIREMENT_SURVIVOR` | Hưu trí - Tử tuất | BHXH | 1 |
| `SICKNESS_MATERNITY` | Ốm đau - Thai sản | BHXH | 2 |
| `OCC_ACCIDENT_DISEASE` | Tai nạn lao động - Bệnh nghề nghiệp | BHXH | 3 |
| `HEALTH` | Bảo hiểm y tế | BHYT | 4 |
| `UNEMPLOYMENT` | Bảo hiểm thất nghiệp | BHTN | 5 |

> Cần verify lại tên tiếng Việt chuẩn từ văn bản pháp lý trước khi seed.

### Tỷ lệ cần verify và seed

Theo FEATURES.md §6.2 (aggregate) và cách phân bổ thông thường VN:

| Component | NLĐ (%) | NSDLĐ (%) | Ghi chú |
|---|---|---|---|
| `RETIREMENT_SURVIVOR` | 8 | 14 | Verify Luật BHXH 2024 điều 85, 86 |
| `SICKNESS_MATERNITY` | 0 | 3 | Verify Luật BHXH 2024 |
| `OCC_ACCIDENT_DISEASE` | 0 | 0.5 | Verify NĐ hướng dẫn |
| `HEALTH` | 1.5 | 3 | Verify Luật BHYT, NĐ 188/2025/NĐ-CP |
| `UNEMPLOYMENT` | 1 | 1 | Verify Luật Việc làm 2025 |
| **Tổng** | **10.5** | **21.5** | Đối chiếu với tổng FEATURES.md: NLĐ 10.5%, NSDLĐ 21.5% |

> **QUAN TRỌNG:** Các tỷ lệ trên là tham chiếu từ FEATURES.md. Người thực hiện PHẢI đọc lại văn bản pháp lý đang hiệu lực tại thời điểm deploy, đặc biệt là `Luật BHXH 2024 (41/2024/QH15)` (hiệu lực 01/07/2025), `Luật Việc làm 2025`, `Nghị định 188/2025/NĐ-CP` trước khi nhập số vào seeder.

### Quy tắc seeder

```
seed_insurance_components()    → INSERT ON CONFLICT DO NOTHING
seed_insurance_policy_version_baseline()  → chỉ INSERT nếu chưa có version nào is_active
```

Seeder phải idempotent và an toàn khi chạy nhiều lần.

---

## Thiết kế quy trình "cập nhật khi có thay đổi quy định"

Luồng người dùng khi Nhà nước ban hành văn bản mới:

```
1. HR Manager → /catalog/insurance
2. [Tạo nháp từ policy hiện hành] → dialog, pre-fill tỷ lệ từ active version
3. Sửa tỷ lệ component nào thay đổi → nhập số mới
4. Nhập Mã policy, Ngày hiệu lực mới, Căn cứ pháp lý
5. [Tạo policy] → is_active = false (nháp)
6. Kiểm tra lại trong bảng policy list
7. [Kích hoạt] → activate: version cũ bị đóng effective_to tự động
```

UI phải dẫn dắt rõ ràng qua các bước này. Hiện tại `InsuranceFoundationView` đã có bước 2 (dialog create/edit), bước 7 (activate button), nhưng **thiếu bước "tạo nháp từ policy hiện hành"** và **thiếu preview "tỷ lệ sẽ thay đổi như thế nào"**.

---

## Kế hoạch triển khai theo slice

### Slice 1 — Seed dữ liệu pháp lý (Critical path)

**Mục tiêu:** Sau khi chạy seeder, hệ thống có đủ dữ liệu để hoạt động mà không cần người dùng tạo thủ công.

**Files cần sửa/tạo:**

```
backend/app/seeds/required.py         (EDIT: thêm 2 hàm seed)
backend/app/seeds/__main__.py         (EDIT: gọi 2 hàm mới)
backend/tests/test_insurance_seed.py  (NEW: verify idempotent)
```

**Chi tiết `seed_insurance_components()`:**

```python
async def seed_insurance_components(session: AsyncSession) -> int:
    """Seed danh mục component đóng BHXH/BHYT/BHTN.

    Returns số dòng được thêm mới (0 nếu đã tồn tại).
    idempotent: INSERT ... ON CONFLICT (code) DO NOTHING
    """
    components = [
        {"code": "RETIREMENT_SURVIVOR",   "name_vi": "...", "insurance_kind": "BHXH", "sort_order": 1},
        {"code": "SICKNESS_MATERNITY",    "name_vi": "...", "insurance_kind": "BHXH", "sort_order": 2},
        {"code": "OCC_ACCIDENT_DISEASE",  "name_vi": "...", "insurance_kind": "BHXH", "sort_order": 3},
        {"code": "HEALTH",                "name_vi": "...", "insurance_kind": "BHYT", "sort_order": 4},
        {"code": "UNEMPLOYMENT",          "name_vi": "...", "insurance_kind": "BHTN", "sort_order": 5},
    ]
    # INSERT ON CONFLICT DO NOTHING, return rowcount
```

**Chi tiết `seed_insurance_policy_version_baseline()`:**

```python
async def seed_insurance_policy_version_baseline(session: AsyncSession) -> bool:
    """Seed policy version mặc định theo luật hiện hành.

    Chỉ insert nếu chưa có policy nào is_active = true.
    Returns True nếu đã seed, False nếu bỏ qua (đã có policy active).

    QUAN TRỌNG: Tỷ lệ % phải được verify từ văn bản trước khi deploy.
    Căn cứ pháp lý: Luật BHXH 2024 (41/2024/QH15), Luật Việc làm 2025,
                    Nghị định 188/2025/NĐ-CP
    """
    # 1. Kiểm tra đã có active policy chưa
    # 2. Nếu chưa: INSERT policy version + 5 component rates + set is_active=True
    # 3. effective_from = ngày hiệu lực của văn bản pháp lý đang áp dụng
    # Tỷ lệ: xem bảng "Tỷ lệ cần verify" ở phần thiết kế seed trên
```

**Tích hợp vào `__main__.py`:**

```python
# Thứ tự gọi trong seed_required():
await seed_minimum_wages(session)
await seed_company_region(session)
await seed_insurance_components(session)      # NEW
await seed_insurance_policy_version_baseline(session)  # NEW
await ...các seeder hiện có khác...
```

**Exit criteria Slice 1:**
- Chạy `python -m app.seeds` trên DB sạch → không lỗi
- `GET /insurance/components` → trả về 5 components
- `GET /insurance/policy-versions` → trả về 1 version `is_active=true`
- `GET /insurance/effective-config?as_of_date=<ngày_hiện_tại>` → trả về config đầy đủ
- Chạy lại seeder lần 2 → không tạo thêm dữ liệu (idempotent)
- `InsuranceFoundationView` hiện đúng policy active và bảng tỷ lệ đóng

---

### Slice 2 — UI cải tiến InsuranceFoundationView

**Mục tiêu:** Người dùng thấy tỷ lệ đóng rõ ràng theo nhóm, có công cụ kiểm tra và có nút tạo nháp từ policy hiện hành.

**File cần sửa:**

```
frontend/src/views/catalog/InsuranceFoundationView.vue  (EDIT)
```

#### 2a. Nhóm rates theo insurance_kind

Thay bảng flat hiện tại bằng bảng có group header:

```
┌─────────────────────────────────────────────────────────────┐
│ BHXH                                                        │
│   Hưu trí - Tử tuất       NLĐ: 8%   NSDLĐ: 14%  Tổng: 22%│
│   Ốm đau - Thai sản        NLĐ: 0%   NSDLĐ: 3%   Tổng: 3% │
│   TNLĐ - BNN               NLĐ: 0%   NSDLĐ: 0.5% Tổng: 0.5│
│   Subtotal BHXH            NLĐ: 8%   NSDLĐ: 17.5%          │
├─────────────────────────────────────────────────────────────┤
│ BHYT                                                        │
│   Bảo hiểm y tế            NLĐ: 1.5% NSDLĐ: 3%            │
├─────────────────────────────────────────────────────────────┤
│ BHTN                                                        │
│   Bảo hiểm thất nghiệp    NLĐ: 1%   NSDLĐ: 1%             │
├─────────────────────────────────────────────────────────────┤
│ TỔNG                       NLĐ: 10.5% NSDLĐ: 21.5%         │
└─────────────────────────────────────────────────────────────┘
```

Cách implement: nhóm `activePolicy.components` bằng `insurance_kind`, render từng nhóm với row subtotal. Thêm row "TỔNG" cuối bảng.

**CSS cần thêm vào `_insurance.scss`:**

```scss
.ins-rates-group-header  { font-weight: 700; padding: 0.5rem 0.875rem; background: var(--p-surface-100); }
.ins-rates-subtotal      { font-weight: 600; background: color-mix(...); }
.ins-rates-total         { font-weight: 700; border-top: 2px solid var(--p-content-border-color); }
html.dark-mode .ins-rates-group-header { background: var(--p-surface-800); }
```

Không dùng scoped style.

#### 2b. Nút "Tạo nháp từ policy hiện hành"

Thêm button bên cạnh "Tạo policy mới":

```vue
<Button
  v-if="activePolicy"
  label="Tạo nháp từ policy hiện hành"
  icon="pi pi-copy"
  severity="secondary"
  @click="openCloneDialog(activePolicy)"
/>
```

`openCloneDialog(policy)`: mở dialog tạo mới với form pre-fill từ `policy`, nhưng `code` và `effective_from` để trống, `name` = `"[NHÁP] " + policy.name`.

#### 2c. Công cụ "Kiểm tra cấu hình ngày"

Thêm một card nhỏ dưới phần lịch sử vùng:

```
┌──────────────────────────────────────────┐
│ Kiểm tra cấu hình tại thời điểm          │
│ [date picker] [Kiểm tra]                 │
│                                          │
│ → Policy: BHXH_2025_V1                   │
│ → Vùng: Vùng III                         │
│ → NLĐ tổng: 10.5% | NSDLĐ tổng: 21.5%  │
└──────────────────────────────────────────┘
```

Gọi `GET /insurance/effective-config?as_of_date={date}` từ `insuranceService`.

Thêm method vào `insuranceService.ts`:

```typescript
getEffectiveConfig: (asOfDate: string) =>
  api.get<InsuranceEffectiveContributionConfigRead>('/insurance/effective-config', {
    params: { as_of_date: asOfDate },
  }),
```

Thêm interface:

```typescript
export interface InsuranceEffectiveContributionConfigRead {
  as_of_date: string
  company_region: CompanyRegionHistoryItem
  policy_version: InsurancePolicyVersionRead
}
```

**Exit criteria Slice 2:**
- Bảng tỷ lệ hiển thị đúng nhóm BHXH/BHYT/BHTN với subtotal
- Click "Tạo nháp từ policy hiện hành" → dialog mở với tỷ lệ được pre-fill từ active policy
- Nhập ngày trong tool "Kiểm tra" → hiện đúng policy và vùng tương ứng
- `vue-tsc --noEmit` không lỗi

---

### Slice 3 — Tests seeder + regression

**Mục tiêu:** Verify seeder hoạt động đúng và không làm vỡ tests cũ.

**File cần tạo:**

```
backend/tests/test_insurance_seed.py  (NEW)
```

**Test cases:**

```python
# test_insurance_seed.py

async def test_seed_components_creates_five_active_components()
async def test_seed_components_is_idempotent()
async def test_seed_policy_version_creates_one_active_policy()
async def test_seed_policy_version_skips_if_active_policy_exists()
async def test_seed_policy_version_has_all_five_component_rates()
async def test_seeded_policy_rate_totals_match_features_spec()
    # Verify NLĐ total = 10.5% (hoặc tổng từ FEATURES.md)
    # Verify NSDLĐ total = 21.5%

async def test_effective_config_works_after_seed()
    # GET /insurance/effective-config?as_of_date=today → 200, policy and region returned
```

**Chạy lại tests hiện có để verify không regress:**

```bash
docker compose exec backend pytest tests/test_insurance_policy_api.py tests/test_insurance_effective_config.py tests/test_insurance_seed.py -v
```

**Exit criteria Slice 3:**
- Tất cả test trong file mới pass
- `test_insurance_policy_api.py` và `test_insurance_effective_config.py` không regress

---

## Không cần làm trong 6.2

| Phần | Lý do |
|---|---|
| Thay đổi models hoặc migration | Toàn bộ infrastructure đã đúng từ 6.1 |
| Thay đổi API backend | Các endpoint đã đủ |
| Thay đổi `employee_insurance_service.py` | Service đã đọc từ policy active đúng cách |
| `InsuranceView.vue` (module nhân viên) | Đã done trong 6.1 Slice 3 |
| `InsuranceTab.vue` trong EmployeeDetailView | Đã done trong 6.1 Slice 4 |
| Export biểu mẫu BHXH | Thuộc 6.4 |

---

## Thứ tự thực hiện

```
Slice 1 (seed)  →  Slice 3 (test seed)  →  Slice 2 (UI)
```

> Slice 1 phải làm trước vì không có seed thì không test được Slice 2 UI trên browser.
> Slice 3 (tests) nên làm song song hoặc ngay sau Slice 1 để lock down seeder behavior.

---

## Verification plan

### Backend

- Seed:
  - `python -m app.seeds` trên DB sạch → no error, no duplicate
  - `python -m app.seeds` lần 2 → no error, no new rows
  - `SELECT count(*) FROM insurance_contribution_components WHERE is_active` → 5
  - `SELECT count(*) FROM insurance_policy_versions WHERE is_active` → 1
  - `SELECT count(*) FROM insurance_policy_component_rates WHERE policy_version_id IN (SELECT id FROM insurance_policy_versions WHERE is_active)` → 5
  - Tổng `employee_rate_percent` của policy seeded = giá trị verify từ văn bản
  - Tổng `employer_rate_percent` của policy seeded = giá trị verify từ văn bản

- API (sau seed):
  - `GET /insurance/components` → 5 items
  - `GET /insurance/policy-versions` → 1 item `is_active=true`
  - `GET /insurance/effective-config?as_of_date=YYYY-MM-DD` → 200, policy + region đầy đủ

- Tests:
  - `pytest tests/test_insurance_seed.py -v` → all pass
  - Không regress `test_insurance_policy_api.py`, `test_insurance_effective_config.py`, `test_employee_insurance_slice2.py`

### Frontend

- Browser tại `/catalog/insurance`:
  - Card "Policy đang active" hiện tên policy seeded
  - Bảng tỷ lệ đóng hiển thị đúng nhóm BHXH/BHYT/BHTN
  - Subtotal và tổng đúng với số từ FEATURES.md
  - "Tạo nháp từ policy hiện hành" → form pre-filled đúng
  - Tool kiểm tra ngày → gọi API, hiện kết quả đúng
- `vue-tsc --noEmit` → 0 errors

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| Tỷ lệ seed sai do nhớ nhầm | Đọc trực tiếp văn bản pháp lý, ghi rõ số điều khoản trong comment seeder; reviewer cross-check |
| Seeder không idempotent → dup data | Dùng `ON CONFLICT DO NOTHING`; với policy version dùng guard `if not active_exists` |
| Policy seeded có `effective_from` sai (trước ngày luật hiệu lực) | Set `effective_from = 2025-07-01` (ngày Luật BHXH 2024 có hiệu lực); verify lại trước deploy |
| UI group rates bị sai thứ tự khi thêm component mới sau này | Sort theo `sort_order`, group theo `insurance_kind` (không hardcode tên group) |
| "Clone từ policy hiện hành" tạo ra version trùng code | Form validate `code` là unique; disable nút clone nếu chưa có active policy |
| Activate policy mới làm hỏng snapshot nhân viên | Backend đã xử lý: resolve dùng `effective_from/to`, không overwrite lịch sử |

---

## Câu hỏi cần chốt trước khi code Slice 1

1. **Tỷ lệ BHTN có áp dụng cho mọi nhân viên không?** Luật Việc làm giới hạn ở hợp đồng ≥ 3 tháng. Nếu có ngoại lệ, seeder cần comment rõ; UI component override ở 6.1 đã có cơ chế xử lý.
2. **Cờ `employer_advances_employee_part` seed mặc định là `false` hay `true`?** Nộp hộ là cấu hình riêng từng công ty, nên mặc định là `false`.
3. **Ngày `effective_from` của policy seeded:** phải là ngày luật có hiệu lực (01/07/2025 cho Luật BHXH 2024), hay ngày công ty bắt đầu triển khai hệ thống? Nếu triển khai sau 01/07/2025 thì dùng 01/07/2025 vẫn đúng.
4. **Tỷ lệ OCC_ACCIDENT_DISEASE (TNLĐ-BNN) có thể được giảm xuống 0.3% theo Nghị quyết thường niên của Chính phủ không?** Nếu công ty đang được hưởng mức giảm, phải dùng mức thực tế, không phải mức gốc trong luật.
