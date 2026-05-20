# Kế hoạch triển khai — 6.4. Báo cáo BHXH

**Phạm vi chính:** Tổng hợp biến động thành báo cáo tháng · Workflow duyệt báo cáo trước khi xuất file chính thức · Điều chỉnh tháng kê khai chính thức từng dòng · Export D02-TS Excel + iBHXH XML từ báo cáo đã duyệt  
**Phụ thuộc hoàn thành:** `6.3 Biến động tăng/giảm BHXH` ✅ (có bảng `insurance_change_events` với `suggested_declaration_year/month`)  
**Căn cứ pháp lý:**
- Quyết định 595/QĐ-BHXH (2017) — Mẫu D02-TS, quy trình nộp hồ sơ tăng/giảm
- Quyết định 896/QĐ-BHXH (2021) — Cập nhật biểu mẫu
- Luật BHXH 2024 (41/2024/QH15) Điều 97 — Thời hạn 30 ngày, trách nhiệm đơn vị
- Nghị định 12/2022/NĐ-CP — Mức phạt vi phạm hành chính

---

## Vấn đề cần giải quyết

### Tại sao cần approval workflow?

Trong thực tế vận hành HR, có nhiều trường hợp **ngày biến động thực tế** khác với **tháng kê khai nộp lên BHXH**:

| Tình huống | effective_date | Tháng kê khai thực tế |
|---|---|---|
| Nghỉ việc cuối tháng, ghi muộn | 31/01/2026 | 02/2026 (không kịp nộp tháng 1) |
| Nghỉ phép thai sản nhưng hệ thống nhập chậm | 15/01/2026 | 02/2026 |
| Tuyển mới nhưng thử việc chưa đủ điều kiện đóng | 01/01/2026 | 03/2026 (sau 2 tháng thử việc) |
| Sửa sai từ tháng trước | 15/11/2025 | 01/2026 (khai bổ sung) |

Nếu export D02-TS trực tiếp từ event (6.3) mà không có bước duyệt, HR không có cơ chế kiểm soát "dòng này thực sự được kê khai vào tháng nào". Báo cáo xuất ra có thể **không khớp với hồ sơ đã nộp cơ quan BHXH**.

### Giải pháp: báo cáo phải được duyệt trước khi xuất file chính thức

```
Biến động (6.3)                    Báo cáo (6.4)
─────────────────────────────────────────────────────────
event A  suggested=01/2026 ─┐
event B  suggested=01/2026 ─┤→  Báo cáo tháng 01/2026 [draft]
event C  suggested=02/2026  │       ↓ HR xem, điều chỉnh declared_month
event D  suggested=01/2026 ─┘       ↓ Duyệt → [approved]
                                    ↓ Export D02-TS / XML (chỉ từ approved)
```

---

## Thiết kế dữ liệu

### Bảng `insurance_period_reports` (Báo cáo biến động theo kỳ)

```sql
CREATE TABLE insurance_period_reports (
    id              SERIAL PRIMARY KEY,

    -- Kỳ báo cáo (thường = tháng kê khai đa số dòng)
    period_year     SMALLINT NOT NULL,
    period_month    SMALLINT NOT NULL,  -- 1–12
    submission_type VARCHAR(20) NOT NULL DEFAULT 'initial',
    -- 'initial'     : lần nộp đầu tiên trong kỳ
    -- 'supplement'  : bổ sung (D02-TS bổ sung — kê khai thiếu từ kỳ trước)
    -- 'correction'  : đính chính (sai thông tin đã nộp, nộp lại)

    -- Trạng thái workflow
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- 'draft'          : đang soạn, chưa nộp duyệt
    -- 'pending_review' : đã nộp cho người duyệt
    -- 'approved'       : đã duyệt — có thể export file chính thức
    -- 'rejected'       : bị trả lại — quay về draft để chỉnh sửa

    -- Người chuẩn bị
    prepared_by_id  INT REFERENCES users(id) ON DELETE SET NULL,
    prepared_at     TIMESTAMP,

    -- Người duyệt
    reviewed_by_id  INT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at     TIMESTAMP,
    review_note     TEXT,  -- lý do từ chối (nếu rejected) hoặc ghi chú khi duyệt

    note            TEXT,
    created_by_id   INT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP,

    CONSTRAINT ck_ipr_period_month CHECK (period_month BETWEEN 1 AND 12),
    CONSTRAINT ck_ipr_status CHECK (status IN ('draft','pending_review','approved','rejected')),
    CONSTRAINT ck_ipr_submission_type CHECK (submission_type IN ('initial','supplement','correction')),
    CONSTRAINT uq_ipr_period_type UNIQUE (period_year, period_month, submission_type)
);

CREATE INDEX ix_ipr_period ON insurance_period_reports(period_year, period_month);
CREATE INDEX ix_ipr_status ON insurance_period_reports(status);
```

### Bảng `insurance_report_line_items` (Dòng báo cáo — tháng kê khai có thể điều chỉnh)

```sql
CREATE TABLE insurance_report_line_items (
    id              SERIAL PRIMARY KEY,
    report_id       INT NOT NULL REFERENCES insurance_period_reports(id) ON DELETE CASCADE,
    event_id        INT NOT NULL REFERENCES insurance_change_events(id) ON DELETE RESTRICT,

    -- Gợi ý (copy từ event.suggested_declaration_* lúc thêm vào báo cáo)
    suggested_year  SMALLINT NOT NULL,
    suggested_month SMALLINT NOT NULL,

    -- Kê khai chính thức (HR điều chỉnh khi cần, default = suggested)
    declared_year   SMALLINT NOT NULL,
    declared_month  SMALLINT NOT NULL,

    -- Audit điều chỉnh
    is_adjusted     BOOLEAN  NOT NULL DEFAULT FALSE,  -- TRUE nếu declared != suggested
    adjustment_note TEXT,
    adjusted_by_id  INT REFERENCES users(id) ON DELETE SET NULL,
    adjusted_at     TIMESTAMP,

    sort_order      INT NOT NULL DEFAULT 0,  -- thứ tự trong báo cáo (HR có thể sắp xếp lại)

    CONSTRAINT ck_irli_suggested_month CHECK (suggested_month BETWEEN 1 AND 12),
    CONSTRAINT ck_irli_declared_month  CHECK (declared_month  BETWEEN 1 AND 12),
    CONSTRAINT uq_irli_report_event    UNIQUE (report_id, event_id)
);

CREATE INDEX ix_irli_report_id ON insurance_report_line_items(report_id);
CREATE INDEX ix_irli_event_id  ON insurance_report_line_items(event_id);
CREATE INDEX ix_irli_declared  ON insurance_report_line_items(declared_year, declared_month);
```

### Quan hệ giữa các bảng

```
insurance_change_events
  │  period_year/month          = tháng biến động xảy ra
  │  suggested_declaration_*    = tháng kê khai gợi ý (6.3)
  │
  └──▶ insurance_report_line_items
         │  suggested_*         = copy từ event
         │  declared_*          = HR điều chỉnh (default = suggested)
         │  is_adjusted         = cờ đánh dấu đã chỉnh
         │
         └──▶ insurance_period_reports
                  status         = draft → pending → approved
                  (export file chỉ từ approved)
```

---

## Workflow duyệt báo cáo

### Các bước

```
1. [HR tạo báo cáo tháng X]
   POST /insurance/reports
   body: { period_year, period_month, submission_type: 'initial' }
   → Hệ thống tự nạp tất cả events có suggested_declaration = X
     làm line items (declared = suggested mặc định)

2. [HR xem xét và điều chỉnh]
   PATCH /insurance/reports/{id}/line-items/{line_id}
   body: { declared_year, declared_month, adjustment_note }
   → is_adjusted = TRUE, ghi audit trail
   → Báo cáo vẫn ở trạng thái 'draft'

3. [HR thêm/bớt dòng]
   POST   /insurance/reports/{id}/line-items   { event_id }  (thêm event bất kỳ)
   DELETE /insurance/reports/{id}/line-items/{line_id}       (bỏ khỏi báo cáo này)

4. [HR nộp duyệt]
   POST /insurance/reports/{id}/submit
   → status: 'draft' → 'pending_review'
   → Không thể sửa line items khi đang pending

5. [Người duyệt xem xét]
   POST /insurance/reports/{id}/approve  { note? }
   → status: 'pending_review' → 'approved'
   → Chốt báo cáo, không thể sửa thêm

   POST /insurance/reports/{id}/reject   { review_note }
   → status: 'pending_review' → 'rejected' → 'draft' (HR sửa lại)

6. [HR xuất file chính thức — chỉ từ approved]
   GET /insurance/reports/{id}/export/d02-ts   → Excel D02-TS
   GET /insurance/reports/{id}/export/ibhxh-xml → XML iBHXH
```

### Quy tắc business

| Hành động | Điều kiện |
|---|---|
| Sửa line item (declared_month) | Chỉ khi báo cáo ở `draft` hoặc `rejected` |
| Thêm/xóa line item | Chỉ khi báo cáo ở `draft` hoặc `rejected` |
| Submit duyệt | Báo cáo ở `draft`; phải có ít nhất 1 line item |
| Approve | Chỉ role `insurance:approve` (khác với người tạo) |
| Export file | Chỉ báo cáo ở `approved` |
| Tạo báo cáo `supplement` | Đã tồn tại báo cáo `initial` cho cùng kỳ (không bắt buộc approved) |

---

## Thiết kế API

```
GET    /insurance/reports
       ?year=&status=&page=&page_size=
       → InsurancePeriodReportListPage

POST   /insurance/reports
       body: { period_year, period_month, submission_type? }
       → InsurancePeriodReportRead (auto-populate line items từ suggested_declaration)

GET    /insurance/reports/{id}
       → InsurancePeriodReportDetail (bao gồm line_items đầy đủ)

PATCH  /insurance/reports/{id}
       body: { note? }
       → InsurancePeriodReportRead

DELETE /insurance/reports/{id}
       Chỉ xóa được khi status='draft'; không có line item nào đã adjusted

POST   /insurance/reports/{id}/submit
       → 200, status → 'pending_review'

POST   /insurance/reports/{id}/approve  body: { note? }
       → 200, status → 'approved'

POST   /insurance/reports/{id}/reject   body: { review_note }
       → 200, status → 'rejected' (→ draft)

-- Line items
GET    /insurance/reports/{id}/line-items
       → list[InsuranceReportLineItemRead]

POST   /insurance/reports/{id}/line-items
       body: { event_id, declared_year?, declared_month? }
       → InsuranceReportLineItemRead

PATCH  /insurance/reports/{id}/line-items/{line_id}
       body: { declared_year, declared_month, adjustment_note }
       → InsuranceReportLineItemRead

DELETE /insurance/reports/{id}/line-items/{line_id}
       → 204

-- Export (chỉ approved)
GET    /insurance/reports/{id}/export/d02-ts
       → StreamingResponse .xlsx

GET    /insurance/reports/{id}/export/ibhxh-xml
       → StreamingResponse .xml
```

### Schemas chính

```python
class InsurancePeriodReportRead(BaseModel):
    id: int
    period_year: int
    period_month: int
    submission_type: Literal['initial', 'supplement', 'correction']
    status: Literal['draft', 'pending_review', 'approved', 'rejected']
    prepared_by_id: int | None
    prepared_at: datetime | None
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    review_note: str | None
    note: str | None
    line_item_count: int         # total dòng
    adjusted_count: int          # số dòng đã điều chỉnh declared
    missing_clinic_code_count: int  # cảnh báo cho export XML
    created_at: datetime

class InsuranceReportLineItemRead(BaseModel):
    id: int
    report_id: int
    event_id: int

    # Thông tin event (join)
    employee_name: str
    employee_code: str
    bhxh_code: str | None
    change_type: Literal['increase', 'decrease']
    change_reason: str
    effective_date: date
    basis_amount: Decimal
    bhyt_clinic_code: str | None

    # Declared period
    suggested_year: int
    suggested_month: int
    declared_year: int
    declared_month: int
    is_adjusted: bool
    adjustment_note: str | None
```

---

## Thiết kế Frontend

### Trang `/insurance/reports` — Danh sách báo cáo

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Báo cáo biến động BHXH                    [+ Tạo báo cáo tháng mới]   │
├─────────────────────────────────────────────────────────────────────────┤
│ Năm: [2026 ▼]                                                           │
│                                                                         │
│ ┌──────────┬──────────┬────────────┬──────────┬───────────────────────┐ │
│ │ Kỳ      │ Loại     │ Trạng thái │ Dòng     │ Hành động             │ │
│ ├──────────┼──────────┼────────────┼──────────┼───────────────────────┤ │
│ │ 05/2026 │ Lần đầu  │ ● Đã duyệt │ 4 dòng   │ [Xem] [Xuất D02-TS]  │ │
│ │ 04/2026 │ Lần đầu  │ ◌ Chờ duyệt│ 3 dòng   │ [Xem]                │ │
│ │ 03/2026 │ Lần đầu  │ ✎ Nháp    │ 2 dòng   │ [Xem] [Xóa]          │ │
│ │ 02/2026 │ Bổ sung  │ ● Đã duyệt │ 1 dòng   │ [Xem] [Xuất D02-TS]  │ │
│ └──────────┴──────────┴────────────┴──────────┴───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Trang `/insurance/reports/{id}` — Chi tiết báo cáo + duyệt

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Báo cáo T05/2026 — Lần đầu                        [Nộp duyệt] [Xóa]   │
│ Trạng thái: ✎ Nháp                                                     │
├────────────────────────────────────────────────────────────────────────┤
│ ⚠ 1 dòng thiếu mã KCB — export iBHXH XML sẽ thiếu <noiDangKyKCB>      │
│ ℹ 1 dòng đã được điều chỉnh tháng kê khai                              │
├─────────────────────────────────────────────────────────────────────────┤
│ [+ Thêm biến động]  Lọc: [Tất cả ▼] [Tăng/Giảm ▼]  Sắp xếp: [Ngày ▼]│
│                                                                         │
│ ┌────┬──────────────┬──────────┬───────┬──────────┬────────────────┐   │
│ │ #  │ Nhân viên    │ Mã BHXH  │ Loại  │ Ngày h/l │ Tháng kê khai │   │
│ ├────┼──────────────┼──────────┼───────┼──────────┼────────────────┤   │
│ │ 1  │ NV001 - A    │ 0100xxx  │ TĂNG  │ 01/05/26 │ 05/2026       │   │
│ │ 2  │ NV042 - B    │ —        │ GIẢM  │ 28/04/26 │ 05/2026 ✎(!)  │   │
│ │    │              │          │       │          │ gợi ý: 04/2026 │   │
│ │ 3  │ NV015 - C ⚠  │ 0301xxx  │ TĂNG  │ 20/05/26 │ 05/2026       │   │
│ └────┴──────────────┴──────────┴───────┴──────────┴────────────────┘   │
│ ⚠ = thiếu mã KCB   ✎ = đã chỉnh tháng kê khai (!)= khác gợi ý         │
├─────────────────────────────────────────────────────────────────────────┤
│ Tổng: 3 dòng (2 TĂNG, 1 GIẢM)         Người lập: Trần Thị B — hôm nay│
└─────────────────────────────────────────────────────────────────────────┘
```

**Khi click vào ô "Tháng kê khai" của 1 dòng (chỉ khi báo cáo ở draft):**

```
┌──────────────────────────────────────┐
│ Điều chỉnh tháng kê khai             │
│                                      │
│ Biến động: NV042 - Nghỉ việc 28/04  │
│ Gợi ý hệ thống: 05/2026             │
│ (ghi nhận sau 5 ngày đầu tháng 5)   │
│                                      │
│ Tháng kê khai chính thức:            │
│ [05 ▼] / [2026 ▼]                   │
│                                      │
│ Lý do điều chỉnh (bắt buộc):         │
│ ┌──────────────────────────────┐     │
│ │                              │     │
│ └──────────────────────────────┘     │
│                                      │
│          [Hủy]  [Lưu điều chỉnh]    │
└──────────────────────────────────────┘
```

**Khi báo cáo ở `pending_review` — giao diện duyệt:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Báo cáo T04/2026 — Lần đầu                                             │
│ Trạng thái: ◌ Chờ duyệt — Nộp bởi Trần Thị B lúc 10:30 17/05/2026   │
├─────────────────────────────────────────────────────────────────────────┤
│ [... bảng dòng báo cáo, chỉ xem, không sửa ...]                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Ghi chú duyệt:                                                          │
│ ┌────────────────────────────────────────────┐                          │
│ │                                            │                          │
│ └────────────────────────────────────────────┘                          │
│                          [Trả lại] [✓ Phê duyệt]                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Kế hoạch triển khai theo slice

### Slice 1 — Migration + Models

**Files:**

```
backend/alembic/versions/0021_create_insurance_period_reports.py  (NEW)
backend/app/models/insurance.py                                    (EDIT: thêm 2 model mới)
```

**Models:**
- `InsurancePeriodReport` — bảng `insurance_period_reports`
- `InsuranceReportLineItem` — bảng `insurance_report_line_items`

**Exit criteria:** `alembic upgrade head` / `downgrade -1` không lỗi.

---

### Slice 2 — Backend Service + API

**Files:**

```
backend/app/services/insurance_report_service.py    (NEW)
backend/app/schemas/insurance_report.py             (NEW)
backend/app/api/v1/endpoints/insurance.py           (EDIT: thêm /reports endpoints)
```

**`insurance_report_service.py`:**

```python
async def create_report(session, period_year, period_month,
                        submission_type, created_by_id) -> InsurancePeriodReport:
    """
    Tạo báo cáo draft + auto-populate line items từ events có
    suggested_declaration_year/month = period_year/month và
    chưa xuất hiện trong bất kỳ approved report nào cùng kỳ.
    """

async def list_reports(session, *, year, status, page, page_size): ...

async def get_report_detail(session, report_id): ...

async def update_line_item(session, report_id, line_item_id,
                           declared_year, declared_month,
                           adjustment_note, adjusted_by_id): ...

async def add_line_item(session, report_id, event_id,
                        declared_year=None, declared_month=None): ...

async def remove_line_item(session, report_id, line_item_id): ...

async def submit_for_review(session, report_id, prepared_by_id): ...

async def approve_report(session, report_id, reviewed_by_id, note): ...

async def reject_report(session, report_id, reviewed_by_id, review_note): ...
```

**Exit criteria:**
- Tạo báo cáo tháng X → line items tự nạp từ events có `suggested_declaration = X`
- Điều chỉnh `declared_month` → `is_adjusted=True`, ghi `adjusted_by_id`
- Submit → `pending_review`; Approve → `approved`; Reject → trở về `draft`
- Approve bởi người khác với người tạo (enforce ở API layer)

---

### Slice 3 — Export từ báo cáo đã duyệt

**Files:**

```
backend/app/services/insurance_export_service.py    (EDIT: thêm export từ report)
backend/app/api/v1/endpoints/insurance.py           (EDIT: thêm export endpoints)
```

**Thay đổi so với export trong 6.3:**
- Export D02-TS và iBHXH XML trong 6.4 dùng `declared_year/month` từ line item (không phải `suggested` hay `period_year/month` của event)
- Chỉ báo cáo `approved` mới được export
- Thứ tự dòng theo `sort_order` trên line item
- Header ghi rõ: "Kỳ kê khai: {declared_year}/{declared_month}" của từng dòng

> **Ghi chú:** Một báo cáo có thể có các dòng với `declared_month` khác nhau (vd: báo cáo 05/2026 có dòng kê khai tháng 04). D02-TS xuất ra phải nhóm theo `declared_month` và xuất thành sheet riêng hoặc ghi rõ trên cột "Kỳ kê khai" của từng dòng.

**Exit criteria:**
- `GET /insurance/reports/{id}/export/d02-ts` với `status=approved` → .xlsx đúng
- Với `status=draft` hoặc `pending_review` → 422 "Báo cáo chưa được duyệt"
- Dòng có `is_adjusted=True` → tháng kê khai trên Excel là `declared_month`, không phải `suggested_month`

---

### Slice 4 — Frontend

**Files:**

```
frontend/src/services/insuranceService.ts                  (EDIT: thêm report methods)
frontend/src/router/index.ts                               (EDIT: thêm routes /insurance/reports)
frontend/src/views/insurance/InsuranceReportsView.vue      (NEW: danh sách báo cáo)
frontend/src/views/insurance/InsuranceReportDetailView.vue (NEW: chi tiết + duyệt)
frontend/src/assets/styles/views/_insurance.scss           (EDIT: thêm CSS)
```

**CSS mới (không scoped):**
```scss
.ins-report-status-draft        { color: var(--p-text-muted-color); }
.ins-report-status-pending      { color: var(--p-orange-600); font-weight: 600; }
.ins-report-status-approved     { color: var(--p-green-600); font-weight: 600; }
.ins-report-status-rejected     { color: var(--p-red-600); font-weight: 600; }
.ins-line-adjusted              { background: color-mix(...p-orange-50...); }
.ins-line-missing-clinic        { ... cảnh báo màu vàng ... }
html.dark-mode { ... }
```

**Exit criteria:**
- Danh sách báo cáo theo năm, lọc được theo trạng thái
- Tạo báo cáo → line items tự nạp, hiển thị ngay
- Click ô tháng kê khai → dialog điều chỉnh (chỉ khi draft)
- Nút "Nộp duyệt" → pending; Nút "Phê duyệt" / "Trả lại" → đúng vai trò
- Trạng thái approved → hiện nút xuất file, ẩn nút sửa
- `vue-tsc --noEmit` không lỗi

---

### Slice 5 — Tests

**Files:**

```
backend/tests/test_insurance_reports.py  (NEW)
```

**Test cases:**

```python
class TestReportCreation:
    async def test_create_report_auto_populates_line_items_from_suggested_period()
    async def test_create_report_does_not_include_events_already_in_approved_report()
    async def test_create_supplement_requires_initial_to_exist()

class TestLineItemAdjustment:
    async def test_adjust_declared_month_sets_is_adjusted_flag()
    async def test_adjust_declared_month_records_adjusted_by()
    async def test_cannot_adjust_when_report_is_pending_review()
    async def test_declared_month_defaults_to_suggested_when_not_adjusted()

class TestApprovalWorkflow:
    async def test_submit_changes_status_to_pending_review()
    async def test_cannot_submit_empty_report()
    async def test_approve_changes_status_to_approved()
    async def test_reject_returns_report_to_draft()
    async def test_approver_cannot_be_same_as_preparer()   # business rule

class TestExport:
    async def test_export_d02_ts_only_from_approved_report()
    async def test_export_uses_declared_month_not_suggested()
    async def test_export_pending_report_returns_422()
    async def test_adjusted_rows_use_declared_month_in_excel()
```

**Exit criteria:**
- Tất cả tests mới pass
- Regression: test_insurance_changes.py, test_insurance_seed.py không fail thêm

---

## Thứ tự thực hiện

```
Slice 1 (Migration)
  ↓
Slice 2 (Service + API CRUD + workflow)
  ↓
Slice 3 (Export từ report đã duyệt)
  ↓
Slice 4 (Frontend)
  ↓
Slice 5 (Tests)
```

---

## Không nằm trong 6.4

| Phần | Thuộc về |
|---|---|
| Mẫu C12-TS (Bảng thanh toán chi tiết) | Làm sau trong 6.4 mở rộng hoặc 6.5 |
| Danh sách nhân viên đang tham gia + tổng quỹ lương | 6.4 mở rộng |
| Gửi file XML lên cổng dichvucong.gov.vn tự động | Ngoài phạm vi (cần API bên ngoài) |
| Lịch sử nộp hồ sơ (tracking đã nhận của BHXH chưa) | Ngoài phạm vi |
| Điều chỉnh lương BHXH tạo biến động | 7.2 |

---

## Rủi ro và cách né

| Rủi ro | Cách né |
|---|---|
| HR export file trước khi duyệt → file không chính thức | API chặn export nếu `status != 'approved'`; UI ẩn nút xuất |
| Một event bị kéo vào 2 báo cáo approved cùng lúc | Khi auto-populate: bỏ qua events đã có trong approved report cùng kỳ; khi thêm thủ công: cảnh báo |
| Người tạo tự duyệt báo cáo của mình | `approve_report` check `reviewed_by_id != prepared_by_id`; enforce qua permission role `insurance:approve` |
| Adjustment note bị bỏ qua → mất audit trail | Bắt buộc nhập `adjustment_note` khi `declared != suggested` (validate ở API) |
| Báo cáo approved nhưng cần sửa | Tạo báo cáo `correction` cho cùng kỳ → HR điều chỉnh → duyệt lại; không unlock approved report |
| Nhiều dòng khác `declared_month` trong 1 báo cáo → Excel khó đọc | Excel xuất 1 sheet nhưng có cột "Tháng kê khai" rõ ràng; nhóm và sort theo `declared_month` trước |
