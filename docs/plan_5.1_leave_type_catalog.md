# Kế hoạch thực hiện — 5.1. Danh mục loại nghỉ phép

**Phạm vi:** Cấu hình danh mục loại nghỉ phép, quy tắc nghỉ theo pháp luật VN và quy định công ty  
**Phụ thuộc:** Module nhân viên ✅ · Module hợp đồng ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Model `LeaveType` | ✅ Cơ bản | 6 trường cốt lõi, thiếu quy tắc nâng cao |
| Service CRUD (`other_business_catalog_service`) | ✅ Đầy đủ | list, get, create, update, soft-delete, lookup |
| API endpoints (`/leave-types`) | ✅ Đầy đủ | RBAC đúng quyền, audit log |
| Seed data (6 loại) | ✅ Cơ bản | Thiếu ngày giới hạn, thiếu loại theo luật |
| Frontend (`OtherBusinessCatalogView`) | ✅ Tab "Nghỉ phép" | Thiếu các trường mới |
| **`count_public_holidays`** | ❌ Thiếu | Ngày lễ có tính vào quota phép không? |
| **`max_days_per_year`** | ❌ Thiếu | Giới hạn ngày/năm (tang: 3, cưới: 3,…) |
| **`max_consecutive_days`** | ❌ Thiếu | Giới hạn ngày liên tiếp/đơn |
| **`min_advance_days`** | ❌ Thiếu | Số ngày báo trước tối thiểu |
| **`carryover_allowed`** | ❌ Thiếu | Phép dư có được chuyển sang năm sau? |
| **`carryover_cutoff_month`** | ❌ Thiếu | Tháng hết hạn phép chuyển (công ty: 3 = Q1) |
| **Loại `paternity_leave`** | ❌ Thiếu | Nghỉ thai sản nam (BLĐ 2019) |
| **Loại `child_care_leave`** | ❌ Thiếu | Nghỉ chăm sóc con ốm (BHXH) |
| Tests đầy đủ | ⚠️ Thiếu | Chỉ có soft-delete + quyền |

---

## Phân tích kỹ thuật

### 1. Quy định pháp luật Việt Nam (Bộ luật Lao động 2019)

| Loại nghỉ | Số ngày | Luật / điều |
|---|---|---|
| Phép năm — cơ bản | 12 ngày/năm | Điều 113 |
| Phép năm — nặng nhọc | 14 ngày/năm | Điều 113 |
| Phép năm — đặc biệt nặng nhọc | 16 ngày/năm | Điều 113 |
| Thâm niên | +1 ngày / 5 năm (từ năm thứ 6) | Điều 114 |
| Nghỉ bệnh (có BHXH) | 30–75 ngày/năm (tùy thâm niên đóng) | Luật BHXH |
| Nghỉ thai sản nữ | 6 tháng | Điều 139 |
| Nghỉ thai sản nam | 5 ngày (vợ đẻ thường); 7 ngày (phẫu thuật/non tháng) | Điều 34 Luật BHXH |
| Nghỉ chăm sóc con ốm < 3 tuổi | 20 ngày/năm | Điều 27 Luật BHXH |
| Nghỉ chăm sóc con ốm 3–7 tuổi | 15 ngày/năm | Điều 27 Luật BHXH |
| Nghỉ tang (bố/mẹ/vợ/chồng/con) | 3 ngày | Điều 115 |
| Nghỉ tang (ông/bà/anh/chị/em) | 1 ngày | Điều 115 |
| Nghỉ cưới (bản thân) | 3 ngày | Điều 115 |
| Nghỉ cưới (con) | 1 ngày | Điều 115 |
| Nghỉ không lương | Theo thỏa thuận | Điều 115 |

> **Lưu ý ngày lễ:** Theo Điều 112 BLĐ 2019, ngày nghỉ lễ quốc gia **không tính** vào ngày phép năm.
> Nếu NV nghỉ phép trùng ngày lễ, ngày lễ đó không bị trừ vào quota phép.

### 2. Quy định riêng công ty — Chuyển phép năm

- Phép năm dư cuối năm → được sử dụng **đến hết Quý I năm sau** (31/03)
- Sau 31/03: số ngày dư của năm trước **bị hủy hoàn toàn**
- Phép năm hiện tại không bị ảnh hưởng bởi việc hủy dư năm trước

**Ví dụ:**

| Thời điểm | Số ngày phép của nhân viên A |
|---|---|
| 31/12/2025 | Phép 2025 còn dư 4 ngày |
| 01/01/2026 | Phép 2026: 12 ngày mới + 4 ngày dư 2025 = **16 ngày** |
| 01/04/2026 | Phép 2026: **12 ngày** (4 ngày dư 2025 bị hủy) |

> Quy tắc này chỉ áp dụng cho `annual_leave`. Các loại khác (sick, maternity, v.v.) không có carryover.

### 3. Các trường mới cần thêm vào `LeaveType`

```python
# Mới thêm vào model
count_public_holidays: bool = True       # Ngày lễ có tính vào thời gian nghỉ không?
                                          # False = ngày lễ trùng phép → không trừ quota
max_days_per_year: Optional[int] = None  # Giới hạn ngày/năm (null = không giới hạn)
max_consecutive_days: Optional[int] = None  # Giới hạn ngày liên tiếp/đơn (null = không)
min_advance_days: int = 0                # Số ngày báo trước tối thiểu
carryover_allowed: bool = False          # Phép dư được chuyển sang năm sau?
carryover_cutoff_month: int = 3          # Tháng hết hạn phép chuyển (3 = hết tháng 3 / Q1)
```

**Lý do `carryover_cutoff_month` ở catalog, không phải setting chung:**
- Tương lai có thể có loại phép khác với chu kỳ riêng (VD: phép đặc biệt hết hạn Q2)
- Mỗi loại phép quản lý quy tắc chuyển của chính nó — tránh coupling với company settings

---

## Seed data đầy đủ

### Loại nghỉ sau khi cập nhật

| Code | Tên | `is_paid` | `affects_annual` | `count_public_hol` | `max_days/yr` | `max_consec` | `carryover` | `cutoff_month` |
|---|---|---|---|---|---|---|---|---|
| `annual_leave` | Phép năm | ✅ | ✅ | ❌ | null | null | ✅ | 3 |
| `sick_leave` | Nghỉ bệnh | ❌ | ❌ | ✅ | null | null | ❌ | — |
| `maternity_leave` | Nghỉ thai sản nữ | ❌ | ❌ | ✅ | null | 180 | ❌ | — |
| `paternity_leave` | Nghỉ thai sản nam | ❌ | ❌ | ✅ | 14 | 14 | ❌ | — |
| `child_care_leave` | Nghỉ chăm sóc con ốm | ❌ | ❌ | ✅ | 20 | null | ❌ | — |
| `bereavement_leave` | Nghỉ tang | ✅ | ❌ | ✅ | 3 | 3 | ❌ | — |
| `marriage_leave` | Nghỉ cưới | ✅ | ❌ | ✅ | 3 | 3 | ❌ | — |
| `unpaid_leave` | Nghỉ không lương | ❌ | ❌ | ✅ | null | null | ❌ | — |

> `count_public_holidays = False` cho `annual_leave`: ngày lễ trùng phép không bị trừ quota (theo Điều 112 BLĐ).
>
> `carryover_cutoff_month` chỉ có ý nghĩa khi `carryover_allowed = True`. Các loại khác bỏ qua trường này (lưu giá trị mặc định `3`).

---

## Cấu trúc file mới / thay đổi

```
backend/
  alembic/versions/0013_add_leave_type_rules.py   (NEW — migration thêm 6 cột)
  app/models/catalog.py                            (UPDATE — 6 trường mới trong LeaveType)
  app/schemas/catalog.py                           (UPDATE — LeaveTypeCreate/Update/Read)
  app/seeds/other_business_catalog.py              (UPDATE — seed data đầy đủ + 2 loại mới)
  tests/test_leave_type_catalog.py                 (NEW — 12 test cases)

frontend/
  src/views/catalog/OtherBusinessCatalogView.vue   (UPDATE — hiển thị trường mới)
```

---

## Thiết kế Backend

### Bước 1 — Migration `0013_add_leave_type_rules.py`

```python
def upgrade():
    op.add_column("leave_types", sa.Column("count_public_holidays",  sa.Boolean(),  nullable=False, server_default="true"))
    op.add_column("leave_types", sa.Column("max_days_per_year",       sa.Integer(),  nullable=True))
    op.add_column("leave_types", sa.Column("max_consecutive_days",    sa.Integer(),  nullable=True))
    op.add_column("leave_types", sa.Column("min_advance_days",        sa.Integer(),  nullable=False, server_default="0"))
    op.add_column("leave_types", sa.Column("carryover_allowed",       sa.Boolean(),  nullable=False, server_default="false"))
    op.add_column("leave_types", sa.Column("carryover_cutoff_month",  sa.Integer(),  nullable=False, server_default="3"))

def downgrade():
    op.drop_column("leave_types", "carryover_cutoff_month")
    op.drop_column("leave_types", "carryover_allowed")
    op.drop_column("leave_types", "min_advance_days")
    op.drop_column("leave_types", "max_consecutive_days")
    op.drop_column("leave_types", "max_days_per_year")
    op.drop_column("leave_types", "count_public_holidays")
```

### Bước 2 — Model `app/models/catalog.py`

Thêm vào class `LeaveType` (sau `requires_attachment`):

```python
count_public_holidays:  bool           = Field(default=True)
max_days_per_year:      Optional[int]  = Field(default=None)
max_consecutive_days:   Optional[int]  = Field(default=None)
min_advance_days:       int            = Field(default=0)
carryover_allowed:      bool           = Field(default=False)
carryover_cutoff_month: int            = Field(default=3, ge=1, le=12)
```

### Bước 3 — Schemas `app/schemas/catalog.py`

**`LeaveTypeCreate`** thêm:
```python
count_public_holidays:  bool          = True
max_days_per_year:      Optional[int] = None
max_consecutive_days:   Optional[int] = None
min_advance_days:       int           = 0
carryover_allowed:      bool          = False
carryover_cutoff_month: int           = Field(default=3, ge=1, le=12)
```

**`LeaveTypeUpdate`** thêm (tất cả Optional):
```python
count_public_holidays:  Optional[bool] = None
max_days_per_year:      Optional[int]  = None
max_consecutive_days:   Optional[int]  = None
min_advance_days:       Optional[int]  = None
carryover_allowed:      Optional[bool] = None
carryover_cutoff_month: Optional[int]  = Field(default=None, ge=1, le=12)
```

**`LeaveTypeRead`** thêm (trả về đầy đủ):
```python
count_public_holidays:  bool
max_days_per_year:      Optional[int]
max_consecutive_days:   Optional[int]
min_advance_days:       int
carryover_allowed:      bool
carryover_cutoff_month: int
```

### Bước 4 — Seed data `app/seeds/other_business_catalog.py`

Cập nhật `LEAVE_TYPES` list:
- Thêm trường mới vào 6 loại hiện có
- Thêm 2 loại mới: `paternity_leave`, `child_care_leave`
- Cập nhật `annual_leave`: `count_public_holidays=False`, `carryover_allowed=True`, `carryover_cutoff_month=3`
- Seed chạy `INSERT ... ON CONFLICT (code) DO UPDATE` — backward-compatible

---

## Thiết kế Frontend

### Bước 5 — `OtherBusinessCatalogView.vue`

**Trong form dialog loại nghỉ phép, thêm section "Quy tắc":**

```
┌────────────────────────────────────────────────────────┐
│ Mã*            │ Tên*                                  │
│ ──────────────────────────────────────────────────────│
│ [x] Hưởng lương   [ ] Ảnh hưởng phép năm             │
│ [x] Cho nghỉ nửa ngày   [ ] Yêu cầu đính kèm         │
│ ──────────────────────────────────────────────────────│
│ Quy tắc nghỉ                                          │
│ Ngày/năm tối đa    [____]  (trống = không giới hạn)  │
│ Ngày LT tối đa/đơn [____]  (trống = không giới hạn)  │
│ Báo trước (ngày)   [____]                             │
│ ──────────────────────────────────────────────────────│
│ [x] Không tính ngày lễ vào quota phép                 │
│ [ ] Cho phép chuyển phép dư sang năm sau              │
│     Hết hạn tháng  [ 3 ]  (3 = Quý I)                │
│ ──────────────────────────────────────────────────────│
│ Màu tag   [____]   Ghi chú [____________________]     │
│ [x] Đang hoạt động                                    │
└────────────────────────────────────────────────────────┘
```

**Trong DataTable, thêm cột "Quy tắc" tóm tắt:**
```html
<Column header="Quy tắc" style="min-width:200px">
  <template #body="{ data }">
    <div class="leave-rule-chips">
      <Tag v-if="data.is_paid_leave"           value="Có lương"       severity="success" />
      <Tag v-if="data.allow_half_day"          value="½ ngày"         severity="info" />
      <Tag v-if="data.carryover_allowed"       value="Chuyển phép"    severity="warning" />
      <Tag v-if="!data.count_public_holidays"  value="Trừ ngày lễ"    severity="secondary" />
      <span v-if="data.max_days_per_year" class="muted-text">
        Max {{ data.max_days_per_year }} ngày/năm
      </span>
    </div>
  </template>
</Column>
```

> Không dùng `<style scoped>` — CSS thêm vào `main.scss`.

---

## Tests — `test_leave_type_catalog.py`

```
test_create_leave_type_with_all_rule_fields
  → POST với đầy đủ 6 trường mới → 201, read-back khớp

test_create_annual_leave_default_carryover
  → annual_leave seed: carryover_allowed=True, carryover_cutoff_month=3

test_create_leave_type_count_public_holidays_false
  → count_public_holidays=False → lưu và trả về đúng

test_update_leave_type_max_days_per_year
  → PATCH max_days_per_year=3 cho bereavement_leave → 200

test_update_leave_type_carryover_toggle
  → Bật carryover_allowed=True, đặt carryover_cutoff_month=6 → 200

test_carryover_cutoff_month_validation
  → carryover_cutoff_month=0 → 422
  → carryover_cutoff_month=13 → 422
  → carryover_cutoff_month=12 → 201

test_seed_annual_leave_has_correct_rules
  → GET annual_leave từ DB → count_public_holidays=False, carryover_allowed=True

test_seed_paternity_leave_exists
  → GET paternity_leave từ DB → 200, max_days_per_year=14

test_seed_child_care_leave_exists
  → GET child_care_leave từ DB → 200, max_days_per_year=20

test_lookup_leave_types_returns_new_fields
  → GET /lookups/leave-types → mỗi item có carryover_allowed

test_admin_can_create_custom_leave_type
  → Tạo loại phép tùy chỉnh (VD: "Nghỉ thể thao") → 201

test_officer_cannot_create_leave_type
  → POST với token officer → 403
```

---

## Thứ tự triển khai

### Bước 1 — Migration
Tạo `0013_add_leave_type_rules.py` — 6 cột mới với `server_default` an toàn.

### Bước 2 — Model + Schema
- `app/models/catalog.py`: thêm 6 trường vào `LeaveType`
- `app/schemas/catalog.py`: cập nhật `LeaveTypeCreate`, `LeaveTypeUpdate`, `LeaveTypeRead`

### Bước 3 — Service
Hàm `_create_basic_row` và `_update_basic_row` đã dùng `model_dump(exclude_unset=True)` — **không cần sửa service**; trường mới tự động được xử lý.

### Bước 4 — Seed data
Cập nhật `LEAVE_TYPES` trong `other_business_catalog.py`:
- 6 loại cũ: thêm `count_public_holidays`, `max_days_per_year`, `min_advance_days`, `carryover_allowed`, `carryover_cutoff_month`
- Thêm 2 loại mới: `paternity_leave`, `child_care_leave`
- SQL seed dùng `ON CONFLICT (code) DO UPDATE SET ...` → chạy lại được

### Bước 5 — Tests
Tạo `tests/test_leave_type_catalog.py` — 12 test cases, chạy pytest pass.

### Bước 6 — Frontend
Cập nhật `OtherBusinessCatalogView.vue`:
- Form dialog: thêm section "Quy tắc" với 6 input mới
- DataTable: thêm cột tóm tắt quy tắc
- CSS: thêm `.leave-rule-chips` vào `main.scss`

### Bước 7 — Verify
1. Chạy Alembic migration — table `leave_types` có 6 cột mới
2. Chạy seed — `annual_leave` có `carryover_allowed=True`
3. Gọi API: `GET /leave-types/1` → response có đầy đủ trường mới
4. Mở `/catalog` tab "Nghỉ phép" → thấy cột Quy tắc + dialog đầy đủ

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Migration break data cũ | `server_default` cho tất cả cột mới — rows hiện có nhận giá trị hợp lệ |
| Service không pass trường mới | `_create_basic_row` dùng `model_dump()` — tự động nếu model có trường |
| Seed chạy lại tạo duplicate | `INSERT ... ON CONFLICT (code) DO UPDATE` — idempotent |
| `carryover_cutoff_month` out of range | `ge=1, le=12` validator trong schema → 422 tự động |
| Frontend dialog quá dài | Chia 2 column trong dialog, dùng `ToggleSwitch` cho bool |

---

## Kết quả mong đợi sau 5.1

- HR có thể cấu hình **từng loại nghỉ phép** với quy tắc riêng: giới hạn ngày/năm, báo trước, chuyển phép
- Seed data phản ánh **đúng pháp luật VN 2019**: phép năm không trừ ngày lễ, thai sản đúng số ngày
- **Phép năm** được đánh dấu `carryover_allowed=True`, `carryover_cutoff_month=3` — sẵn sàng cho 5.2 tính tự động hủy dư Q1
- `paternity_leave` và `child_care_leave` có mặt trong seed — đủ cho 5.3 ghi nhận nghỉ phép

---

## Liên kết với 5.2 (Quản lý số ngày phép)

5.1 thiết lập catalog. 5.2 sẽ dùng trường `carryover_allowed` và `carryover_cutoff_month` để:

```
leave_entitlements (bảng mới ở 5.2):
  employee_id  → FK Employee
  leave_type_id → FK LeaveType
  year         → int (2025, 2026, ...)
  allocated_days    → Decimal  (12 ngày cơ bản + thâm niên)
  carryover_days    → Decimal  (dư năm trước — null nếu !carryover_allowed)
  carryover_expires → Date     (cutoff date: năm+1, tháng=carryover_cutoff_month, ngày cuối tháng)
  used_days         → Decimal  (cập nhật khi ghi nhận nghỉ ở 5.3)
  remaining_days    → Computed (allocated + carryover - used, carryover hết hạn = 0 sau cutoff)
```

Celery task (5.2) chạy 01/04 hàng năm: hủy `carryover_days` còn dư của tất cả NV cho năm trước.
