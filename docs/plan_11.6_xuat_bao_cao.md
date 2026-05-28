# Kế hoạch triển khai — 11.6. Xuất báo cáo

## Header

| Mục | Chi tiết |
|-----|----------|
| Phạm vi | Xuất Excel/PDF · Lọc đa tiêu chí · Lưu mẫu báo cáo tùy chỉnh · Lịch sử xuất |
| Phụ thuộc | 11.1→11.5 (toàn bộ báo cáo), Celery + Redis (task nền) |
| Căn cứ | FEATURES.md §11.6 |
| Ghi chú | Module infrastructure cho toàn bộ hệ thống báo cáo |

---

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
|----------|-----------|
| Export inline (StreamingResponse) ở các module riêng lẻ (probation, leave, recruitment…) | Đã có |
| Unified export center — 1 nơi quản lý toàn bộ export | Chưa có |
| Background export qua Celery (cho file lớn) | Chưa có |
| Lưu mẫu báo cáo tùy chỉnh (filter preset) | Chưa có |
| Lịch sử xuất — download lại file cũ | Chưa có |
| Unified Excel style standard dùng chung | Chưa có |

---

## Phạm vi

### Trong phạm vi

- **Unified Export Center**: giao diện 1 nơi để xuất tất cả loại báo cáo (dashboard, danh sách nhân viên, biến động, nghỉ phép, bảo hiểm, hợp đồng…)
- **Excel export**: tất cả báo cáo 11.1→11.5, hỗ trợ multi-sheet, áp dụng style chuẩn (header màu, border, column width tự động)
- **PDF export**: snapshot qua html-to-pdf (WeasyPrint hoặc LibreOffice headless convert từ XLSX)
- **Background export** (Celery): báo cáo ước tính >1 000 rows không block UI — tạo job, polling trạng thái, download khi xong
- **Lưu mẫu báo cáo**: lưu bộ filter + config → đặt tên → dùng lại nhiều lần
- **Lịch sử xuất**: danh sách file đã xuất, trạng thái, download lại trong vòng 7 ngày
- Mobile responsive

### Ngoài phạm vi

- Scheduled auto-export gửi email định kỳ
- Custom formula / pivot trong Excel
- Digital signing PDF
- Lưu file dài hạn (>7 ngày) trên object storage

---

## Database Migration

```sql
-- migrations/versions/0047_add_export_tables.py
-- revision: 0047
-- down_revision: 0046

-- ============================================================
-- Bảng 1: export_jobs — theo dõi từng lần xuất file
-- ============================================================
CREATE TABLE export_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    report_type     VARCHAR(100) NOT NULL,          -- 'hr-employee-list' | 'leaves' | ...
    format          VARCHAR(10)  NOT NULL,           -- 'xlsx' | 'pdf'
    filters         JSONB        NOT NULL DEFAULT '{}',
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
                                                    -- pending | processing | done | failed
    filename        VARCHAR(255),                   -- tên file người dùng đặt
    file_path       VARCHAR(500),                   -- đường dẫn lưu tạm / MinIO key
    file_size_bytes BIGINT,
    row_count       INTEGER,
    error_message   TEXT,
    celery_task_id  VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ  GENERATED ALWAYS AS (created_at + INTERVAL '7 days') STORED
);

CREATE INDEX ix_export_jobs_user_id    ON export_jobs(user_id);
CREATE INDEX ix_export_jobs_status     ON export_jobs(status);
CREATE INDEX ix_export_jobs_created_at ON export_jobs(created_at DESC);

-- ============================================================
-- Bảng 2: report_templates — mẫu báo cáo tùy chỉnh
-- ============================================================
CREATE TABLE report_templates (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    report_type VARCHAR(100) NOT NULL,
    format      VARCHAR(10)  NOT NULL DEFAULT 'xlsx',
    filters     JSONB        NOT NULL DEFAULT '{}',
    is_default  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_report_templates_user_id ON report_templates(user_id);
CREATE UNIQUE INDEX uq_report_templates_user_name
    ON report_templates(user_id, name);
```

---

## API Design

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/v1/reports/export` | Tạo export job (sync hoặc async tuỳ estimated_rows) |
| `GET`  | `/api/v1/reports/export/{job_id}/status` | Lấy trạng thái job |
| `GET`  | `/api/v1/reports/export/{job_id}/download` | Download file đã hoàn thành |
| `GET`  | `/api/v1/reports/export/history` | Lịch sử xuất (phân trang) |
| `DELETE` | `/api/v1/reports/export/{job_id}` | Xoá job / file |
| `POST` | `/api/v1/reports/templates` | Lưu mẫu mới |
| `GET`  | `/api/v1/reports/templates` | Danh sách mẫu của user hiện tại |
| `PUT`  | `/api/v1/reports/templates/{id}` | Cập nhật mẫu (đổi tên, sửa filter) |
| `DELETE` | `/api/v1/reports/templates/{id}` | Xoá mẫu |

---

## Pydantic Schemas (`app/schemas/export.py`)

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ── Enums ────────────────────────────────────────────────────────────────────

ReportType = Literal[
    "dashboard",
    "hr-employee-list",
    "hr-movement",
    "leaves",
    "insurance",
    "contracts",
    "recruitment",
    "probation",
    "payroll",
]

ExportFormat = Literal["xlsx", "pdf"]

ExportStatus = Literal["pending", "processing", "done", "failed"]


# ── Export Job ────────────────────────────────────────────────────────────────

class ExportJobRequest(BaseModel):
    report_type: ReportType
    format: ExportFormat = "xlsx"
    filters: dict[str, Any] = Field(default_factory=dict)
    filename: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def sanitize_filename(self) -> "ExportJobRequest":
        if self.filename:
            # Loại bỏ ký tự không hợp lệ trong tên file
            import re
            self.filename = re.sub(r'[\\/:*?"<>|]', "_", self.filename)
        return self


class ExportJobResponse(BaseModel):
    id: uuid.UUID
    report_type: str
    format: str
    status: ExportStatus
    filename: Optional[str]
    file_size_bytes: Optional[int]
    row_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    download_url: Optional[str] = None  # computed

    model_config = {"from_attributes": True}


class ExportJobStatusResponse(BaseModel):
    id: uuid.UUID
    status: ExportStatus
    progress_pct: Optional[int] = None   # 0-100, nếu có
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class ExportHistoryResponse(BaseModel):
    items: list[ExportJobResponse]
    total: int
    page: int
    page_size: int


# ── Report Templates ──────────────────────────────────────────────────────────

class ReportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    report_type: ReportType
    format: ExportFormat = "xlsx"
    filters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ReportTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    filters: Optional[dict[str, Any]] = None
    format: Optional[ExportFormat] = None
    is_default: Optional[bool] = None


class ReportTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    report_type: str
    format: str
    filters: dict[str, Any]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

---

## SQLAlchemy Models (`app/models/export.py`)

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Index, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_export_jobs_user_id", "user_id"),
        Index("ix_export_jobs_status", "status"),
        Index("ix_export_jobs_created_at", "created_at"),
    )


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="xlsx")
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_report_templates_user_id", "user_id"),
    )
```

---

## Export Service (`app/services/export_service.py`)

```python
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export import ExportJob
from app.schemas.export import ExportJobRequest
from app.utils.excel_style import ExcelStyler

# Ngưỡng để quyết định sync vs async
ASYNC_THRESHOLD_ROWS = 1_000


class ExportService:
    """Unified export service — phân loại sync/async và dispatch đúng handler."""

    # Registry ánh xạ report_type → hàm lấy dữ liệu
    _HANDLERS: dict[str, str] = {
        "hr-employee-list": "app.services.employee_report_service.get_employee_list_data",
        "hr-movement":      "app.services.movement_report_service.get_movement_data",
        "leaves":           "app.services.leave_report_service.get_leave_data",
        "insurance":        "app.services.insurance_report_service.get_insurance_data",
        "contracts":        "app.services.contract_report_service.get_contract_data",
        "recruitment":      "app.services.recruitment_report_service.get_recruitment_data",
        "probation":        "app.services.probation_report_service.get_probation_data",
        "payroll":          "app.services.payroll_report_service.get_payroll_data",
        "dashboard":        "app.services.dashboard_report_service.get_dashboard_data",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_export_job(
        self,
        request: ExportJobRequest,
        user_id: int,
    ) -> ExportJob:
        """Tạo job, ước lượng số dòng, quyết định sync/async."""
        job = ExportJob(
            user_id=user_id,
            report_type=request.report_type,
            format=request.format,
            filters=request.filters,
            filename=request.filename or self._default_filename(request),
            status="pending",
        )
        self.db.add(job)
        await self.db.flush()  # lấy id trước khi commit

        estimated = await self._estimate_rows(request)
        job.row_count = estimated  # tạm — sẽ cập nhật sau khi xuất thực

        if estimated <= ASYNC_THRESHOLD_ROWS:
            # Synchronous: xuất ngay, trả về job đã done
            await self._run_sync(job, request)
        else:
            # Asynchronous: đẩy sang Celery
            from app.tasks.export_tasks import run_export_task
            task = run_export_task.delay(str(job.id), request.model_dump())
            job.celery_task_id = task.id
            job.status = "pending"

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _estimate_rows(self, request: ExportJobRequest) -> int:
        """COUNT nhanh — không JOIN nặng, chỉ WHERE cơ bản."""
        # Mỗi service báo cáo cần cung cấp hàm count_rows(filters, db)
        try:
            module_path = self._HANDLERS[request.report_type]
            count_func_path = module_path.replace(
                "get_", "count_"
            ).replace("_data", "_rows")
            module_name, func_name = count_func_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_name)
            count_fn = getattr(module, func_name, None)
            if count_fn:
                return await count_fn(request.filters, self.db)
        except Exception:
            pass
        return 0

    async def _run_sync(self, job: ExportJob, request: ExportJobRequest) -> None:
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        try:
            data = await self._fetch_data(request)
            file_bytes, row_count = self._build_file(data, request)
            file_path = self._save_temp(job.id, request.format, file_bytes)
            job.status = "done"
            job.file_path = file_path
            job.file_size_bytes = len(file_bytes)
            job.row_count = row_count
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
        finally:
            job.completed_at = datetime.now(timezone.utc)

    async def _fetch_data(self, request: ExportJobRequest) -> list[dict]:
        module_path = self._HANDLERS[request.report_type]
        module_name, func_name = module_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_name)
        fn = getattr(module, func_name)
        return await fn(request.filters, self.db)

    def _build_file(
        self, data: list[dict], request: ExportJobRequest
    ) -> tuple[bytes, int]:
        if request.format == "xlsx":
            return ExcelStyler.build(data, request.report_type), len(data)
        else:
            # PDF: convert XLSX → PDF qua LibreOffice headless
            xlsx_bytes, count = self._build_file(
                data, request.model_copy(update={"format": "xlsx"})
            )
            pdf_bytes = _libreoffice_convert(xlsx_bytes)
            return pdf_bytes, count

    @staticmethod
    def _default_filename(request: ExportJobRequest) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = request.format
        return f"{request.report_type}_{ts}.{ext}"

    @staticmethod
    def _save_temp(job_id: uuid.UUID, fmt: str, data: bytes) -> str:
        tmp_dir = Path("/tmp/hrms_exports")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        path = tmp_dir / f"{job_id}.{fmt}"
        path.write_bytes(data)
        return str(path)


def _libreoffice_convert(xlsx_bytes: bytes) -> bytes:
    """Chuyển XLSX → PDF qua LibreOffice headless."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "input.xlsx"
        in_path.write_bytes(xlsx_bytes)
        subprocess.run(
            [
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", tmpdir, str(in_path),
            ],
            check=True,
            timeout=60,
        )
        out_path = Path(tmpdir) / "input.pdf"
        return out_path.read_bytes()
```

---

## Celery Tasks (`app/tasks/export_tasks.py`)

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="reports.run_export",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def run_export_task(self, job_id: str, request_dict: dict[str, Any]) -> dict:
    """
    Celery task xử lý export nền.

    Flow:
      1. Mở DB session (sync)
      2. Cập nhật job status → processing
      3. Gọi ExportService._fetch_data (async → chạy trong event loop mới)
      4. Build file
      5. Lưu file, cập nhật job → done
      6. Nếu lỗi → retry hoặc → failed
    """
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.schemas.export import ExportJobRequest
    from app.services.export_service import ExportService

    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            # Lấy job từ DB
            from sqlalchemy import select
            from app.models.export import ExportJob

            result = await db.execute(
                select(ExportJob).where(ExportJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("ExportJob %s not found", job_id)
                return

            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                request = ExportJobRequest(**request_dict)
                svc = ExportService(db)
                data = await svc._fetch_data(request)
                file_bytes, row_count = svc._build_file(data, request)
                file_path = ExportService._save_temp(
                    uuid.UUID(job_id), request.format, file_bytes
                )

                job.status = "done"
                job.file_path = file_path
                job.file_size_bytes = len(file_bytes)
                job.row_count = row_count
                job.completed_at = datetime.now(timezone.utc)

            except Exception as exc:
                logger.exception("Export task failed for job %s", job_id)
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                # Retry nếu chưa hết lần
                raise self.retry(exc=exc)

            await db.commit()

    asyncio.run(_run())
    return {"job_id": job_id, "status": "done"}
```

---

## Unified Excel Style (`app/utils/excel_style.py`)

```python
from __future__ import annotations

import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HEADER_FILL  = PatternFill("solid", fgColor="1E6091")   # xanh đậm
HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
BODY_FONT    = Font(size=10)
BORDER_SIDE  = Side(style="thin", color="CCCCCC")
CELL_BORDER  = Border(
    left=BORDER_SIDE, right=BORDER_SIDE,
    top=BORDER_SIDE,  bottom=BORDER_SIDE,
)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN   = Alignment(horizontal="left",   vertical="center", wrap_text=True)


class ExcelStyler:
    """Chuẩn hoá style Excel toàn hệ thống báo cáo."""

    @staticmethod
    def build(data: list[dict[str, Any]], sheet_title: str = "Báo cáo") -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:31]  # Excel giới hạn 31 ký tự

        if not data:
            buf = io.BytesIO()
            wb.save(buf)
            return buf.getvalue()

        headers = list(data[0].keys())
        ExcelStyler._write_header(ws, headers)
        ExcelStyler._write_rows(ws, data, headers)
        ExcelStyler._auto_width(ws)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def _write_header(ws, headers: list[str]) -> None:
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill      = HEADER_FILL
            cell.font      = HEADER_FONT
            cell.border    = CELL_BORDER
            cell.alignment = CENTER_ALIGN
        ws.row_dimensions[1].height = 22

    @staticmethod
    def _write_rows(ws, data: list[dict], headers: list[str]) -> None:
        for row_idx, record in enumerate(data, start=2):
            fill = PatternFill("solid", fgColor="F0F4F8") if row_idx % 2 == 0 else None
            for col_idx, key in enumerate(headers, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=record.get(key))
                cell.font      = BODY_FONT
                cell.border    = CELL_BORDER
                cell.alignment = LEFT_ALIGN
                if fill:
                    cell.fill = fill

    @staticmethod
    def _auto_width(ws) -> None:
        for col_cells in ws.columns:
            max_len = max(
                (len(str(c.value)) if c.value is not None else 0 for c in col_cells),
                default=10,
            )
            ws.column_dimensions[get_column_letter(col_cells[0].column)].width = (
                min(max_len + 4, 50)
            )
```

---

## API Endpoint (`app/api/v1/endpoints/export.py`)

```python
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.export import ExportJob, ReportTemplate
from app.schemas.export import (
    ExportHistoryResponse,
    ExportJobRequest,
    ExportJobResponse,
    ExportJobStatusResponse,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportTemplateUpdate,
)
from app.services.export_service import ExportService

router = APIRouter(prefix="/reports", tags=["reports-export"])


# ── Export Jobs ───────────────────────────────────────────────────────────────

@router.post("/export", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    body: ExportJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = ExportService(db)
    job = await svc.create_export_job(body, current_user.id)
    return _job_to_response(job)


@router.get("/export/history", response_model=ExportHistoryResponse)
async def get_export_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    offset = (page - 1) * page_size
    total_q = await db.execute(
        select(func.count()).select_from(ExportJob)
        .where(ExportJob.user_id == current_user.id)
    )
    total = total_q.scalar_one()

    jobs_q = await db.execute(
        select(ExportJob)
        .where(ExportJob.user_id == current_user.id)
        .order_by(ExportJob.created_at.desc())
        .offset(offset).limit(page_size)
    )
    jobs = jobs_q.scalars().all()
    return ExportHistoryResponse(
        items=[_job_to_response(j) for j in jobs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/export/{job_id}/status", response_model=ExportJobStatusResponse)
async def get_export_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_or_404(db, job_id, current_user.id)
    download_url = f"/api/v1/reports/export/{job_id}/download" if job.status == "done" else None
    return ExportJobStatusResponse(
        id=job.id,
        status=job.status,
        error_message=job.error_message,
        download_url=download_url,
    )


@router.get("/export/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_or_404(db, job_id, current_user.id)
    if job.status != "done":
        raise HTTPException(status_code=400, detail="File chưa sẵn sàng")
    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(status_code=404, detail="File không còn tồn tại")

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if job.format == "xlsx"
        else "application/pdf"
    )
    return FileResponse(
        path=job.file_path,
        filename=job.filename or f"export.{job.format}",
        media_type=media_type,
    )


@router.delete("/export/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_or_404(db, job_id, current_user.id)
    if job.file_path:
        Path(job.file_path).unlink(missing_ok=True)
    await db.delete(job)
    await db.commit()


# ── Report Templates ──────────────────────────────────────────────────────────

@router.post("/templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = ReportTemplate(**body.model_dump(), user_id=current_user.id)
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(ReportTemplate)
        .where(ReportTemplate.user_id == current_user.id)
        .order_by(ReportTemplate.updated_at.desc())
    )
    return result.scalars().all()


@router.put("/templates/{tpl_id}", response_model=ReportTemplateResponse)
async def update_template(
    tpl_id: int,
    body: ReportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await _get_template_or_404(db, tpl_id, current_user.id)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(tpl, field, val)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/templates/{tpl_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    tpl_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await _get_template_or_404(db, tpl_id, current_user.id)
    await db.delete(tpl)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_job_or_404(db: AsyncSession, job_id: uuid.UUID, user_id: int) -> ExportJob:
    result = await db.execute(
        select(ExportJob).where(ExportJob.id == job_id, ExportJob.user_id == user_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job không tồn tại")
    return job


async def _get_template_or_404(db: AsyncSession, tpl_id: int, user_id: int) -> ReportTemplate:
    result = await db.execute(
        select(ReportTemplate).where(
            ReportTemplate.id == tpl_id, ReportTemplate.user_id == user_id
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template không tồn tại")
    return tpl


def _job_to_response(job: ExportJob) -> ExportJobResponse:
    download_url = (
        f"/api/v1/reports/export/{job.id}/download" if job.status == "done" else None
    )
    return ExportJobResponse(
        **{c.key: getattr(job, c.key) for c in job.__table__.columns},
        download_url=download_url,
    )
```

---

## Frontend Design

### Cấu trúc component

```
src/views/reports/ExportCenterView.vue     (NEW — container chính)
src/services/exportService.ts              (NEW — API client)
src/composables/useExportPolling.ts        (NEW — polling logic)
src/router/index.ts                        (EDIT — thêm route /reports/export)
src/components/layout/AppMenu.vue         (EDIT — thêm menu item)
```

### `exportService.ts`

```typescript
import apiClient from '@/services/api'

export type ReportType =
  | 'dashboard' | 'hr-employee-list' | 'hr-movement'
  | 'leaves' | 'insurance' | 'contracts' | 'recruitment'
  | 'probation' | 'payroll'

export type ExportFormat = 'xlsx' | 'pdf'
export type ExportStatus = 'pending' | 'processing' | 'done' | 'failed'

export interface ExportJobRequest {
  report_type: ReportType
  format: ExportFormat
  filters: Record<string, unknown>
  filename?: string
}

export interface ExportJobResponse {
  id: string
  report_type: string
  format: string
  status: ExportStatus
  filename?: string
  file_size_bytes?: number
  row_count?: number
  error_message?: string
  created_at: string
  completed_at?: string
  download_url?: string
}

export interface ExportHistoryResponse {
  items: ExportJobResponse[]
  total: number
  page: number
  page_size: number
}

export interface ReportTemplateResponse {
  id: number
  name: string
  description?: string
  report_type: ReportType
  format: ExportFormat
  filters: Record<string, unknown>
  is_default: boolean
  created_at: string
  updated_at: string
}

const BASE = '/api/v1/reports'

export const exportService = {
  // Export Jobs
  createExport: (body: ExportJobRequest) =>
    apiClient.post<ExportJobResponse>(`${BASE}/export`, body),

  getStatus: (jobId: string) =>
    apiClient.get<{ id: string; status: ExportStatus; download_url?: string; error_message?: string }>(
      `${BASE}/export/${jobId}/status`
    ),

  getHistory: (page = 1, pageSize = 20) =>
    apiClient.get<ExportHistoryResponse>(`${BASE}/export/history`, {
      params: { page, page_size: pageSize },
    }),

  deleteJob: (jobId: string) =>
    apiClient.delete(`${BASE}/export/${jobId}`),

  downloadUrl: (jobId: string) => `${BASE}/export/${jobId}/download`,

  // Templates
  createTemplate: (body: Omit<ReportTemplateResponse, 'id' | 'created_at' | 'updated_at'>) =>
    apiClient.post<ReportTemplateResponse>(`${BASE}/templates`, body),

  listTemplates: () =>
    apiClient.get<ReportTemplateResponse[]>(`${BASE}/templates`),

  updateTemplate: (id: number, body: Partial<ReportTemplateResponse>) =>
    apiClient.put<ReportTemplateResponse>(`${BASE}/templates/${id}`, body),

  deleteTemplate: (id: number) =>
    apiClient.delete(`${BASE}/templates/${id}`),
}
```

### `useExportPolling.ts`

```typescript
import { ref, onUnmounted } from 'vue'
import { exportService, type ExportStatus } from '@/services/exportService'
import { useToast } from 'primevue/usetoast'

export function useExportPolling() {
  const toast = useToast()
  const pollingJobs = ref<Map<string, ReturnType<typeof setInterval>>>(new Map())

  function startPolling(jobId: string, filename: string) {
    const interval = setInterval(async () => {
      try {
        const { data } = await exportService.getStatus(jobId)
        if (data.status === 'done') {
          stopPolling(jobId)
          toast.add({
            severity: 'success',
            summary: 'Xuất file thành công',
            detail: `${filename} đã sẵn sàng để tải về`,
            life: 5000,
          })
          // Trigger download tự động
          window.open(exportService.downloadUrl(jobId), '_blank')
        } else if (data.status === 'failed') {
          stopPolling(jobId)
          toast.add({
            severity: 'error',
            summary: 'Xuất file thất bại',
            detail: data.error_message ?? 'Lỗi không xác định',
            life: 8000,
          })
        }
      } catch {
        stopPolling(jobId)
      }
    }, 2_000)

    pollingJobs.value.set(jobId, interval)
  }

  function stopPolling(jobId: string) {
    const timer = pollingJobs.value.get(jobId)
    if (timer) {
      clearInterval(timer)
      pollingJobs.value.delete(jobId)
    }
  }

  onUnmounted(() => {
    pollingJobs.value.forEach((timer) => clearInterval(timer))
  })

  return { startPolling, stopPolling }
}
```

### `ExportCenterView.vue` — Khung giao diện

```vue
<template>
  <div class="p-4">
    <div class="text-2xl font-bold mb-4">Trung tâm xuất báo cáo</div>

    <TabView>
      <!-- Tab 1: Xuất nhanh -->
      <TabPanel header="Xuất nhanh">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-3">
            <label class="font-semibold">Loại báo cáo</label>
            <Select
              v-model="form.report_type"
              :options="reportTypeOptions"
              option-label="label"
              option-value="value"
              placeholder="Chọn loại báo cáo"
            />

            <label class="font-semibold">Định dạng</label>
            <SelectButton v-model="form.format" :options="formatOptions" />

            <!-- Filter động theo report_type -->
            <ExportFilterPanel
              v-if="form.report_type"
              :report-type="form.report_type"
              v-model:filters="form.filters"
            />

            <InputText
              v-model="form.filename"
              placeholder="Tên file (không bắt buộc)"
            />

            <div class="flex gap-2">
              <Button
                label="Xuất file"
                icon="pi pi-download"
                :loading="exporting"
                @click="handleExport"
              />
              <Button
                label="Lưu mẫu"
                icon="pi pi-bookmark"
                severity="secondary"
                outlined
                @click="showSaveTemplate = true"
              />
            </div>
          </div>

          <!-- Danh sách job đang xử lý -->
          <div v-if="activeJobs.length > 0">
            <div class="font-semibold mb-2">Đang xử lý</div>
            <div
              v-for="job in activeJobs"
              :key="job.id"
              class="p-3 border rounded mb-2"
            >
              <div class="flex justify-between items-center">
                <span>{{ job.filename }}</span>
                <Tag :severity="statusSeverity(job.status)" :value="statusLabel(job.status)" />
              </div>
              <ProgressBar v-if="job.status === 'processing'" mode="indeterminate" class="mt-2" style="height: 4px" />
            </div>
          </div>
        </div>
      </TabPanel>

      <!-- Tab 2: Lịch sử xuất -->
      <TabPanel header="Lịch sử xuất">
        <DataTable
          :value="history.items"
          :loading="loadingHistory"
          lazy
          :rows="20"
          :total-records="history.total"
          @page="onHistoryPage"
        >
          <Column field="filename"    header="Tên file" />
          <Column field="report_type" header="Loại báo cáo" />
          <Column field="format"      header="Định dạng" />
          <Column field="row_count"   header="Số dòng" />
          <Column field="status"      header="Trạng thái">
            <template #body="{ data }">
              <Tag :severity="statusSeverity(data.status)" :value="statusLabel(data.status)" />
            </template>
          </Column>
          <Column field="created_at"  header="Thời gian" />
          <Column header="Thao tác">
            <template #body="{ data }">
              <Button
                v-if="data.status === 'done'"
                icon="pi pi-download"
                size="small"
                text
                @click="window.open(exportService.downloadUrl(data.id), '_blank')"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                severity="danger"
                text
                @click="deleteJob(data.id)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Tab 3: Mẫu đã lưu -->
      <TabPanel header="Mẫu báo cáo">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card v-for="tpl in templates" :key="tpl.id">
            <template #title>{{ tpl.name }}</template>
            <template #subtitle>{{ reportTypeLabel(tpl.report_type) }} · {{ tpl.format.toUpperCase() }}</template>
            <template #content>
              <p class="text-sm text-gray-500">{{ tpl.description }}</p>
            </template>
            <template #footer>
              <div class="flex gap-2">
                <Button label="Dùng mẫu" size="small" @click="loadTemplate(tpl)" />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  severity="danger"
                  outlined
                  @click="deleteTemplate(tpl.id)"
                />
              </div>
            </template>
          </Card>
        </div>
      </TabPanel>
    </TabView>

    <!-- Dialog lưu mẫu -->
    <Dialog v-model:visible="showSaveTemplate" header="Lưu mẫu báo cáo" modal>
      <div class="flex flex-col gap-3">
        <InputText v-model="templateName" placeholder="Tên mẫu" />
        <Textarea v-model="templateDesc" placeholder="Mô tả (không bắt buộc)" rows="2" />
      </div>
      <template #footer>
        <Button label="Huỷ" severity="secondary" @click="showSaveTemplate = false" />
        <Button label="Lưu" @click="saveTemplate" />
      </template>
    </Dialog>
  </div>
</template>
```

---

## Cấu trúc file

```
backend/
  app/
    models/
      export.py                           (NEW — ExportJob, ReportTemplate)
    schemas/
      export.py                           (NEW — Pydantic v2 schemas)
    services/
      export_service.py                   (NEW — Unified export logic)
    tasks/
      export_tasks.py                     (NEW — Celery tasks)
    api/v1/endpoints/
      export.py                           (NEW — API routes)
    utils/
      excel_style.py                      (NEW — Unified openpyxl style)
  migrations/versions/
    0047_add_export_tables.py             (NEW)
  tests/
    test_export.py                        (NEW)

frontend/src/
  services/
    exportService.ts                      (NEW)
  composables/
    useExportPolling.ts                   (NEW)
  views/reports/
    ExportCenterView.vue                  (NEW)
  components/reports/
    ExportFilterPanel.vue                 (NEW — filter động theo report_type)
  router/
    index.ts                              (EDIT — thêm route /reports/export)
  components/layout/
    AppMenu.vue                           (EDIT — thêm menu item Xuất báo cáo)
```

---

## Kế hoạch theo Slice

### Slice 1 — Backend: Migration + Models + Sync Export

**Mục tiêu:** Xuất được file XLSX/PDF đồng bộ cho báo cáo nhỏ (<1 000 rows)

**Tasks:**
1. Tạo migration `0047_add_export_tables.py` (bảng `export_jobs`, `report_templates`)
2. Tạo `app/models/export.py` (SQLAlchemy models)
3. Tạo `app/schemas/export.py` (Pydantic schemas)
4. Tạo `app/utils/excel_style.py` (ExcelStyler — chuẩn style chung)
5. Tạo `app/services/export_service.py` — chỉ phần sync (`_run_sync`, `_fetch_data`, `_build_file`)
6. Tạo `app/api/v1/endpoints/export.py` — endpoint `POST /export`, `GET /export/{id}/download`
7. Đăng ký router vào `app/api/v1/api.py`
8. Test: `tests/test_export.py` — test sync export XLSX

**Verify:**
```bash
pytest tests/test_export.py -v
```

---

### Slice 2 — Backend: Celery Async Export + Status Polling

**Mục tiêu:** Xuất file lớn không block API — polling trạng thái đến khi xong

**Tasks:**
1. Tạo `app/tasks/export_tasks.py` (`run_export_task` Celery task)
2. Cập nhật `export_service.py`: thêm `_estimate_rows`, phân nhánh sync/async
3. Thêm endpoint `GET /export/{id}/status`
4. Thêm endpoint `GET /export/history` + `DELETE /export/{id}`
5. Cấu hình Celery worker nhận queue `exports`
6. Test: mock Celery task, kiểm tra status transition `pending → processing → done`

**Verify:**
```bash
pytest tests/test_export.py::test_async_export -v
celery -A app.celery_app worker -Q exports --loglevel=info  # kiểm thủ công
```

---

### Slice 3 — Backend: Template Save/Load + Lịch sử

**Mục tiêu:** User lưu được bộ filter thành mẫu, xem lịch sử file đã xuất

**Tasks:**
1. Thêm endpoints CRUD templates (`POST`, `GET`, `PUT`, `DELETE /templates`)
2. Thêm endpoint `GET /export/history` phân trang
3. Cleanup job: xoá file quá 7 ngày (Celery beat task `cleanup_expired_exports`)
4. Test: CRUD template, lịch sử phân trang

**Verify:**
```bash
pytest tests/test_export.py -v -k "template or history"
```

---

### Slice 4 — Frontend: Export Center UI hoàn chỉnh

**Mục tiêu:** Giao diện đầy đủ — xuất nhanh, polling, lịch sử, mẫu

**Tasks:**
1. Tạo `exportService.ts` (API client)
2. Tạo `useExportPolling.ts` (polling composable)
3. Tạo `ExportFilterPanel.vue` — filter động theo `report_type`
4. Tạo `ExportCenterView.vue` — 3 tab (Xuất nhanh / Lịch sử / Mẫu)
5. EDIT `router/index.ts` — thêm route `/reports/export`
6. EDIT `AppMenu.vue` — thêm "Xuất báo cáo" vào menu Báo cáo
7. Chạy `vue-tsc --noEmit` verify TypeScript

**Verify:**
```bash
npx vue-tsc --noEmit
```

---

## Rủi ro và cách xử lý

| # | Rủi ro | Khả năng | Tác động | Cách xử lý |
|---|--------|----------|----------|------------|
| 1 | LibreOffice headless không có trên server | Trung bình | Cao — PDF không xuất được | Cài LibreOffice khi deploy; fallback: trả về XLSX kèm thông báo; hoặc dùng WeasyPrint cho PDF từ HTML |
| 2 | Celery worker chết giữa chừng | Thấp | Cao — job bị treo ở `processing` | Dùng `acks_late=True` + retry; có Celery beat task kiểm tra job `processing` quá 10 phút → mark `failed` |
| 3 | File tạm `/tmp` đầy ổ đĩa | Trung bình | Trung bình — export mới thất bại | Cleanup task xoá file >7 ngày; giám sát disk usage; tương lai dùng MinIO |
| 4 | Số dòng ước tính sai → job sync nhưng thực tế rất lớn | Thấp | Trung bình — timeout API | Giới hạn timeout 30s cho sync; nếu vượt → tự động chuyển sang job background |
| 5 | Concurrent export cùng lúc nhiều user | Trung bình | Trung bình — Celery queue tắc nghẽn | Tách queue `exports` riêng với concurrency đủ; ưu tiên job nhỏ (short-job first) |
| 6 | Polling FE liên tục gây tải server | Thấp | Thấp | Chỉ poll khi có job đang `pending/processing`; tự động dừng khi tab ẩn (`visibilitychange`) |
| 7 | User xoá mẫu đang được dùng | Thấp | Thấp | Xoá mẫu chỉ xoá metadata — không ảnh hưởng job đã chạy (job lưu `filters` riêng) |
| 8 | Tên file trùng lặp | Thấp | Thấp | Tên file lưu FS theo `{job_id}.{format}` — UUID đảm bảo unique; tên hiển thị là `filename` field |
| 9 | Mất kết nối Redis | Thấp | Cao — Celery không nhận task | Health check Redis trong startup; fallback sync cho mọi request khi Redis down |
| 10 | `report_type` mới thêm vào nhưng chưa có handler | Cao — khi mở rộng | Thấp | Registry `_HANDLERS` rõ ràng; raise `NotImplementedError` sớm tại `create_export_job`; test cover |

---

## Notes triển khai

- **Celery queue**: dùng queue riêng `exports` để không tranh chấp với queue mặc định
- **File storage**: giai đoạn 1 lưu `/tmp/hrms_exports/`; giai đoạn 2 migrate sang MinIO với signed URL
- **Cleanup**: Celery beat chạy mỗi đêm 2:00 AM xoá `ExportJob` hết hạn và file tương ứng
- **Permissions**: chỉ user tạo job mới được download/xoá job của mình; HR Manager có thể xem lịch sử toàn bộ
- **excel_style.py** là single source of truth — mọi module báo cáo dùng chung, không tự định nghĩa style riêng
