# Kế hoạch thực hiện — 3.6. Sự kiện & Nhắc nhở

**Phạm vi:** Dashboard cảnh báo các sự kiện nhân sự sắp đến  
**Phụ thuộc:** `1.2 RBAC` ✅ · `3.1 Thông tin cá nhân` ✅ · `3.3 Hồ sơ công việc` ✅

---

## Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| Bảng `employees` — `date_of_birth`, `start_date`, `status` | ✅ Đã có |
| Bảng `employee_job_records` — `probation_end_date`, `is_current` | ✅ Đã có |
| Bảng `contracts` (hết hạn hợp đồng) | ❌ Chưa có — thuộc 4.1, defer |
| Endpoint reminders | ❌ Chưa có |
| View nhắc nhở | ❌ Chưa có |

---

## Phạm vi 3.6

| Loại sự kiện | Nguồn dữ liệu | Ghi chú |
|---|---|---|
| Sinh nhật nhân viên | `employees.date_of_birth` | So sánh (tháng, ngày), bỏ qua năm |
| Thâm niên (1, 3, 5, 10 năm) | `employees.start_date` | `start_date + N năm` rơi vào cửa sổ |
| Sắp hết thời gian thử việc | `employee_job_records.probation_end_date` (is_current) | |
| Sắp hết hạn hợp đồng | defer → 4.1 | Chưa có bảng contracts |

**Cửa sổ thời gian:** mặc định 30 ngày tới, cấu hình qua query param `days` (tối đa 90).

---

## Thiết kế kỹ thuật

### Không tạo bảng mới

Tất cả sự kiện được **tính toán on-demand** từ dữ liệu hiện có — không cần bảng `reminders` hay scheduler. Đây là lựa chọn phù hợp vì:
- Dữ liệu nguồn đã có đầy đủ
- Volume nhỏ (vài trăm nhân viên)
- Không có yêu cầu gửi email/notification

### Schema phản hồi

```python
class ReminderItem(BaseModel):
    employee_id:   int
    employee_code: str          # mã nhân viên (id_number)
    employee_name: str
    department:    Optional[str]
    event_type:    str          # "birthday" | "anniversary" | "probation_end"
    event_date:    date         # ngày sự kiện trong năm hiện tại / năm tới
    days_until:    int          # 0 = hôm nay, âm = đã qua (không trả về)
    extra:         dict         # {"years": 5} cho anniversary; {} cho birthday/probation_end

class RemindersResponse(BaseModel):
    birthday:      list[ReminderItem]
    anniversary:   list[ReminderItem]
    probation_end: list[ReminderItem]
    total:         int
```

### Logic tính toán

**Birthday:**
```python
# Lấy nhân viên đang hoạt động có birthday trong [today, today+days]
# Xử lý edge case 29/2 (năm nhuận → dùng 28/2)
target_year = today.year  # hoặc +1 nếu (month, day) < today
event_date = date(target_year, emp.date_of_birth.month, emp.date_of_birth.day)
```

**Anniversary:**
```python
# Với mỗi mốc N in [1, 3, 5, 10]:
anniversary_date = start_date + relativedelta(years=N)
# Nếu anniversary_date trong cửa sổ → thêm vào kết quả với extra={"years": N}
```

**Probation end:**
```python
# JOIN employee_job_records WHERE is_current=TRUE AND probation_end_date BETWEEN today AND today+days
# Chỉ nhân viên status='probation'
```

---

## API Endpoint

```
GET /api/v1/reminders
    Query params:
      days: int = 30  (1..90)
      types: str = "birthday,anniversary,probation_end"  (csv, lọc loại)

    Response: RemindersResponse
    Quyền: employees:view
```

---

## Frontend

### Route mới

```
/reminders  →  RemindersView.vue
```

### Layout RemindersView

```
┌─────────────────────────────────────────────────────────────┐
│ Nhắc nhở sự kiện nhân sự                    [Trong: 30 ngày▼]│
├──────────────┬──────────────────┬────────────────────────────┤
│ 🎂 Sinh nhật │ ⭐ Thâm niên     │ 📋 Hết thử việc             │
│     5        │      2           │      3                     │
├──────────────┴──────────────────┴────────────────────────────┤
│ DataTable: Nhân viên | Phòng ban | Sự kiện | Ngày | Còn N ngày│
│ Có thể lọc theo loại + xuất Excel                           │
└─────────────────────────────────────────────────────────────┘
```

**Cards tóm tắt:** 3 thẻ số liệu cho mỗi loại sự kiện.

**DataTable hợp nhất:** tất cả sự kiện trong 1 bảng, có cột "Loại" và sort theo `days_until` ASC.

**Filter:** `Select` lọc theo loại sự kiện (có `filter` prop).

**Màu sắc `days_until`:**
- 0 = hôm nay → badge đỏ "Hôm nay"
- 1–7 → badge cam "N ngày nữa"
- 8–30 → badge xanh "N ngày nữa"

### Sidebar badge

Thêm badge số vào mục "Nhắc nhở" trên sidebar, hiển thị tổng sự kiện trong **7 ngày tới**. Fetch 1 lần khi load layout, cache trong store.

### Không có route detail riêng

Click vào dòng trong bảng → navigate đến `employees/:id` (tab tương ứng).

---

## Global CSS cần thêm vào `main.scss`

```scss
// Reminder cards
.reminder-cards   { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.reminder-card    { background: var(--l-surface); border: 1px solid var(--l-border); border-radius: 12px; padding: 1.25rem; }
.reminder-card-count { font-size: 2rem; font-weight: 700; line-height: 1; }
.reminder-card-label { font-size: 0.85rem; color: var(--l-text-muted); margin-top: 0.25rem; }

// Days-until badges
.days-badge       { display: inline-block; padding: 0.2em 0.6em; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }
.days-badge.today { background: color-mix(in srgb, var(--p-red-500) 12%, transparent); color: var(--p-red-600); }
.days-badge.soon  { background: color-mix(in srgb, var(--p-orange-500) 12%, transparent); color: var(--p-orange-600); }
.days-badge.later { background: color-mix(in srgb, var(--p-green-500) 12%, transparent); color: var(--p-green-600); }
```

---

## `employeeService.ts` / service mới

Tạo `frontend/src/services/reminderService.ts`:

```typescript
export type EventType = 'birthday' | 'anniversary' | 'probation_end'

export interface ReminderItem {
  employee_id:   number
  employee_code: string
  employee_name: string
  department:    string | null
  event_type:    EventType
  event_date:    string   // ISO date
  days_until:    number
  extra:         Record<string, unknown>  // { years: 5 } cho anniversary
}

export interface RemindersResponse {
  birthday:      ReminderItem[]
  anniversary:   ReminderItem[]
  probation_end: ReminderItem[]
  total:         number
}

export default {
  getReminders: (days = 30, types?: EventType[]) =>
    api.get<RemindersResponse>('/reminders', {
      params: { days, types: types?.join(',') }
    }),
}
```

---

## Backend — cấu trúc file

```
backend/app/api/v1/endpoints/reminders.py   (NEW)
backend/app/services/reminder_service.py     (NEW)
backend/app/schemas/reminder.py              (NEW)
```

Đăng ký router vào `backend/app/api/v1/router.py`.

### `reminder_service.py` — skeleton

```python
async def get_reminders(
    session: AsyncSession,
    days: int = 30,
    types: set[str] | None = None,
) -> RemindersResponse:
    today = date.today()
    end   = today + timedelta(days=days)
    types = types or {"birthday", "anniversary", "probation_end"}

    results: dict[str, list[ReminderItem]] = {
        "birthday": [], "anniversary": [], "probation_end": []
    }

    if "birthday" in types:
        results["birthday"] = await _get_birthdays(session, today, end)

    if "anniversary" in types:
        results["anniversary"] = await _get_anniversaries(session, today, end)

    if "probation_end" in types:
        results["probation_end"] = await _get_probation_ends(session, today, end)

    total = sum(len(v) for v in results.values())
    return RemindersResponse(**results, total=total)
```

### Query birthday (raw SQL-style SQLAlchemy):

```python
# Tối ưu: dùng EXTRACT(month) = ? AND EXTRACT(day) = ? cho từng ngày trong window
# Hoặc: lấy tất cả nhân viên active rồi filter Python-side (đơn giản hơn, đủ dùng)
```

---

## Tests

File: `backend/tests/test_reminders.py`

```
test_birthday_within_window          → nhân viên sinh nhật trong 30 ngày → xuất hiện
test_birthday_outside_window         → sinh nhật > 30 ngày → không xuất hiện
test_birthday_today                  → days_until = 0
test_birthday_year_rollover          → sinh nhật qua năm mới (VD: test chạy tháng 12)
test_anniversary_1_year              → start_date tròn 1 năm trong window
test_anniversary_3_5_10_years        → 3 mốc cùng 1 employee khác nhau
test_anniversary_not_yet             → mốc chưa đến không xuất hiện
test_probation_end_within_window     → probation_end_date trong window
test_probation_end_outside_window    → ngoài window → không xuất hiện
test_filter_by_type_birthday_only    → ?types=birthday → chỉ trả birthday
test_days_param_7                    → days=7 → chỉ 7 ngày
test_viewer_can_access               → employees:view → 200
test_unauthenticated_401             → không có token → 401
```

---

## Thứ tự triển khai

### Bước 1 — Backend service & endpoint
1. Tạo `backend/app/schemas/reminder.py` — `ReminderItem`, `RemindersResponse`
2. Tạo `backend/app/services/reminder_service.py` — 3 hàm query
3. Tạo `backend/app/api/v1/endpoints/reminders.py` — 1 endpoint GET
4. Đăng ký router

### Bước 2 — Backend tests
1. Tạo `backend/tests/test_reminders.py`
2. Chạy pytest → tất cả pass

### Bước 3 — Frontend
1. Tạo `frontend/src/services/reminderService.ts`
2. Thêm CSS reminder classes vào `main.scss`
3. Tạo `frontend/src/views/RemindersView.vue`
4. Thêm route `/reminders` vào router
5. Thêm mục + badge vào sidebar

### Bước 4 — Verify
1. Kiểm tra quyền `employees:view` trên endpoint
2. Kiểm tra badge cập nhật đúng trên sidebar
3. Kiểm tra navigate đến `employees/:id` khi click dòng

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Edge case 29/2 (năm nhuận) | Fallback sang 28/2 nếu năm hiện tại không nhuận |
| Birthday qua năm (tháng 12 → tháng 1 năm sau) | So sánh theo `ordinal` hoặc xử lý `end_year = today.year + 1` khi cần |
| Anniversary: nhân viên nhiều mốc cùng 1 window | Trả về nhiều `ReminderItem` riêng, mỗi mốc 1 dòng |
| Nhân viên nghỉ việc không nên nhắc | Filter `employees.status != 'resigned'` |
| Timeout khi nhiều nhân viên | Query DB có LIMIT; on-demand, không cần cache |

---

## Kết quả mong đợi sau 3.6

- HR mở trang Nhắc nhở thấy ngay ai sinh nhật, ai tròn thâm niên, ai hết thử việc trong 30 ngày tới
- Sidebar hiện badge số khi có sự kiện trong 7 ngày gần
- Click vào nhân viên → mở hồ sơ tương ứng
- Không cần cấu hình scheduler hay gửi email
