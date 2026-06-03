"""Tạo bảng cơ cấu tổ chức và lương BHXH

Revision ID: 0001
Revises:
Create Date: 2026-05-12

Bảng được tạo (9 bảng):
  Cơ cấu tổ chức:
    - departments              Phòng/Ban/Bộ phận/Nhóm/Tổ (cây phân cấp)
    - job_titles               Chức danh
    - job_positions            Vị trí công việc
    - job_position_attachments File đính kèm tiêu chuẩn tuyển dụng
    - org_change_logs          Lịch sử thay đổi cơ cấu
  Lương BHXH (dữ liệu nguồn tính toán động):
    - regional_minimum_wages   Lịch sử mức lương tối thiểu vùng theo nghị định
    - company_bhxh_region      Vùng BHXH của công ty theo từng thời kỳ
    - salary_scales            Phiên bản thang bảng lương (theo năm)
    - salary_scale_entries     Hệ số bậc lương theo chức danh
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ──────────────────────────────────────────────────────────────────────
    # 1. departments — Phòng / Ban / Bộ phận / Nhóm / Tổ
    #    Cây phân cấp tùy độ sâu qua parent_id tự tham chiếu.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "departments",
        # Khóa chính tự tăng
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Mã phòng/ban, duy nhất toàn hệ thống — VD: "PHONG_KT", "BAN_GD"
        sa.Column("code", sa.String(20), nullable=False),
        # Tên đầy đủ — VD: "Phòng Kế toán", "Ban Giám đốc"
        sa.Column("name", sa.String(200), nullable=False),
        # Tên viết tắt — VD: "KT", "GD"
        sa.Column("short_name", sa.String(50), nullable=True),
        # ID của đơn vị cha trong cây; NULL = cấp gốc (không có cha)
        sa.Column("parent_id", sa.Integer(), nullable=True),
        # Loại đơn vị: PHONG | BAN | BO_PHAN | NHOM | TO
        # Dùng để hiển thị nhãn đúng và lọc theo cấp tổ chức
        sa.Column("dept_type", sa.String(20), nullable=False, server_default="PHONG"),
        # Thứ tự hiển thị trong cùng một cấp (số nhỏ hơn hiện trước)
        sa.Column("order_no", sa.Integer(), nullable=False, server_default="0"),
        # TRUE = đang hoạt động; FALSE = đã giải thể/không dùng
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Thời điểm tạo bản ghi
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Thời điểm cập nhật cuối — NULL nếu chưa từng sửa
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        # FK tự tham chiếu: parent_id → departments.id
        sa.ForeignKeyConstraint(["parent_id"], ["departments.id"], name="fk_departments_parent"),
        sa.UniqueConstraint("code", name="uq_departments_code"),
    )
    op.create_index("ix_departments_code", "departments", ["code"], unique=True)
    # Index parent_id để query cây con nhanh
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])

    # ──────────────────────────────────────────────────────────────────────
    # 2. job_titles — Chức danh
    #    VD: Giám đốc, Phó Giám đốc, Trưởng phòng, Nhân viên...
    #    Liên kết với salary_scale_entries để tra hệ số bậc lương.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "job_titles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Mã chức danh — VD: "GD", "PDG", "TP", "NV"
        sa.Column("code", sa.String(20), nullable=False),
        # Tên chức danh — VD: "Giám đốc", "Trưởng phòng"
        sa.Column("name", sa.String(200), nullable=False),
        # Cấp bậc quản lý: 1 = cao nhất (CEO), càng lớn càng thấp trong hệ thống
        # Dùng để sắp xếp danh sách dropdown theo thứ bậc
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_job_titles_code"),
    )
    op.create_index("ix_job_titles_code", "job_titles", ["code"], unique=True)

    # ──────────────────────────────────────────────────────────────────────
    # 3. job_positions — Vị trí công việc
    #    Kết hợp phòng/ban + chức danh + thông tin tuyển dụng.
    #    Lương BHXH KHÔNG lưu số tiền cứng — tính động từ LTTV × hệ_số_bậc.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "job_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Mã vị trí — VD: "KT_TRUONG", "KD_NV_1"
        sa.Column("code", sa.String(20), nullable=False),
        # Tên vị trí — VD: "Kế toán trưởng", "Nhân viên kinh doanh khu vực 1"
        sa.Column("name", sa.String(200), nullable=False),
        # Phòng/ban trực thuộc — bắt buộc
        sa.Column("department_id", sa.Integer(), nullable=False),
        # Chức danh tương ứng — nullable: vị trí chưa xếp chức danh
        sa.Column("job_title_id", sa.Integer(), nullable=True),
        # Bậc lương mặc định gợi ý khi tuyển nhân viên mới vào vị trí này
        # HR có thể override tại hợp đồng lao động
        sa.Column("default_grade", sa.SmallInteger(), nullable=False, server_default="1"),
        # Phụ cấp cố định TÍNH VÀO lương đóng BHXH (ghi trong HĐLĐ)
        # Ví dụ: phụ cấp chức vụ, phụ cấp trách nhiệm, phụ cấp nặng nhọc/độc hại
        sa.Column("bhxh_allowance", sa.Numeric(15, 0), nullable=False, server_default="0"),
        # Phụ cấp KHÔNG tính BHXH — phải tách dòng riêng trong HĐLĐ (quy định Luật BHXH 2024)
        # Ví dụ: tiền ăn ca, xăng xe, điện thoại, nhà ở
        sa.Column("non_bhxh_allowance", sa.Numeric(15, 0), nullable=False, server_default="0"),
        # Mô tả công việc chi tiết (dùng cho JD tuyển dụng)
        sa.Column("description", sa.Text(), nullable=True),
        # Yêu cầu tuyển dụng (kinh nghiệm, bằng cấp, kỹ năng...)
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name="fk_job_positions_department"
        ),
        sa.ForeignKeyConstraint(
            ["job_title_id"], ["job_titles.id"], name="fk_job_positions_job_title"
        ),
        sa.UniqueConstraint("code", name="uq_job_positions_code"),
    )
    op.create_index("ix_job_positions_code", "job_positions", ["code"], unique=True)
    op.create_index("ix_job_positions_department_id", "job_positions", ["department_id"])

    # ──────────────────────────────────────────────────────────────────────
    # 4. job_position_attachments — File đính kèm tiêu chuẩn tuyển dụng
    #    Xóa cascade khi vị trí bị xóa.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "job_position_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Vị trí công việc sở hữu file này
        sa.Column("job_position_id", sa.Integer(), nullable=False),
        # Tên file hiển thị cho người dùng — VD: "Mo_ta_cong_viec_KT_truong.pdf"
        sa.Column("file_name", sa.String(255), nullable=False),
        # Đường dẫn tương đối từ thư mục storage — VD: "positions/42/jd.pdf"
        sa.Column("file_path", sa.String(500), nullable=False),
        # Kích thước file tính bằng byte
        sa.Column("file_size", sa.Integer(), nullable=True),
        # Thời điểm upload
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["job_position_id"],
            ["job_positions.id"],
            name="fk_job_position_attachments_position",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_job_position_attachments_position_id",
        "job_position_attachments",
        ["job_position_id"],
    )

    # ──────────────────────────────────────────────────────────────────────
    # 5. org_change_logs — Lịch sử thay đổi cơ cấu tổ chức
    #    Ghi tự động khi create/update/delete phòng ban, chức danh, vị trí.
    #    changed_by sẽ có FK → users.id sau khi Auth Foundation được implement.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "org_change_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Loại đối tượng bị thay đổi: 'department' | 'job_title' | 'job_position'
        sa.Column("entity_type", sa.String(30), nullable=False),
        # ID của bản ghi bị thay đổi trong bảng tương ứng
        sa.Column("entity_id", sa.Integer(), nullable=False),
        # Tên snapshot tại thời điểm thay đổi (để tra cứu kể cả khi bản ghi đã xóa)
        sa.Column("entity_name", sa.String(200), nullable=False),
        # Hành động: 'create' | 'update' | 'delete'
        sa.Column("action", sa.String(10), nullable=False),
        # ID người thực hiện — TODO: thêm FK → users.id sau khi implement Auth Foundation
        sa.Column("changed_by", sa.Integer(), nullable=True),
        # Thời điểm thay đổi
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Toàn bộ dữ liệu trước khi thay đổi dạng JSON; NULL khi action='create'
        sa.Column("old_data", JSONB, nullable=True),
        # Toàn bộ dữ liệu sau khi thay đổi dạng JSON; NULL khi action='delete'
        sa.Column("new_data", JSONB, nullable=True),
    )
    # Index để lọc lịch sử theo đối tượng
    op.create_index("ix_org_change_logs_entity", "org_change_logs", ["entity_type", "entity_id"])
    # Index để lọc theo khoảng thời gian
    op.create_index("ix_org_change_logs_changed_at", "org_change_logs", ["changed_at"])

    # ──────────────────────────────────────────────────────────────────────
    # 6. regional_minimum_wages — Lịch sử mức lương tối thiểu vùng
    #    Không bao giờ sửa/xóa dòng cũ — chỉ thêm dòng mới khi có nghị định mới.
    #    effective_to = NULL nghĩa là nghị định đang có hiệu lực.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "regional_minimum_wages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Số hiệu nghị định — VD: "293/2025/NĐ-CP", "74/2024/NĐ-CP"
        sa.Column("decree_number", sa.String(50), nullable=False),
        # Vùng lương (1–4):
        #   1 = Vùng I   — HN nội thành, TP.HCM, Đồng Nai, Bình Dương...
        #   2 = Vùng II  — các tỉnh/TP loại II
        #   3 = Vùng III — các tỉnh còn lại
        #   4 = Vùng IV  — vùng sâu, vùng xa, miền núi
        sa.Column("region", sa.SmallInteger(), nullable=False),
        # Mức lương tối thiểu tháng (VNĐ)
        sa.Column("amount", sa.Numeric(15, 0), nullable=False),
        # Ngày bắt đầu có hiệu lực
        sa.Column("effective_from", sa.Date(), nullable=False),
        # Ngày hết hiệu lực; NULL = đang có hiệu lực
        sa.Column("effective_to", sa.Date(), nullable=True),
        # Ghi chú bổ sung
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_regional_minimum_wages_lookup",
        "regional_minimum_wages",
        ["region", "effective_from"],
        unique=True,
    )

    # ──────────────────────────────────────────────────────────────────────
    # 7. company_bhxh_region — Vùng BHXH đang áp dụng của công ty
    #    Khi công ty chuyển địa điểm, thêm dòng mới + cập nhật effective_to cũ.
    #    effective_to = NULL = dòng đang áp dụng.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "company_bhxh_region",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Vùng lương: 1 | 2 | 3 | 4
        sa.Column("region", sa.SmallInteger(), nullable=False),
        # Ngày bắt đầu áp dụng vùng này
        sa.Column("effective_from", sa.Date(), nullable=False),
        # NULL = đang áp dụng; phải điền khi chuyển sang vùng mới
        sa.Column("effective_to", sa.Date(), nullable=True),
        # Ghi chú — VD: "Trụ sở tại Đắk Lắk, thuộc Vùng III"
        sa.Column("note", sa.Text(), nullable=True),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 8. salary_scales — Phiên bản thang bảng lương
    #    Mỗi năm thường tạo một phiên bản mới khi Nghị định LTTV thay đổi.
    #    Nhiều phiên bản có thể cùng tồn tại (lịch sử), chỉ 1 đang hiệu lực.
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "salary_scales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Tên phiên bản — VD: "Thang bảng lương 2026"
        sa.Column("name", sa.String(200), nullable=False),
        # Ngày bắt đầu áp dụng thang lương này
        sa.Column("effective_from", sa.Date(), nullable=False),
        # NULL = đang áp dụng
        sa.Column("effective_to", sa.Date(), nullable=True),
        # Ghi chú — VD: "Cập nhật theo NĐ 293/2025, tăng 7.2% so với 2025"
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 9. salary_scale_entries — Hệ số bậc lương theo chức danh
    #    Công thức: Lương_bậc_N = LTTV_vùng × coefficient
    #    Ràng buộc: Lương_bậc_N >= LTTV_vùng (hệ số >= 1.0 với chức danh thấp nhất)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "salary_scale_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Phiên bản thang bảng lương chứa dòng này
        sa.Column("salary_scale_id", sa.Integer(), nullable=False),
        # Chức danh tương ứng
        sa.Column("job_title_id", sa.Integer(), nullable=False),
        # Số thứ tự bậc lương, bắt đầu từ 1
        # Bậc 1 = mức khởi điểm khi mới nhận chức danh
        sa.Column("grade_no", sa.SmallInteger(), nullable=False),
        # Hệ số nhân với LTTV vùng để ra mức lương bậc này
        # VD: coefficient=2.68 → Vùng III: 4.140.000 × 2.68 = 11.095.200 ₫
        sa.Column("coefficient", sa.Numeric(6, 4), nullable=False),
        # Số tháng công tác tối thiểu trong bậc hiện tại trước khi được xét nâng bậc
        # Doanh nghiệp tự quy định; phổ biến là 12 tháng
        sa.Column("promotion_months", sa.SmallInteger(), nullable=False, server_default="12"),
        # Tiêu chí/điều kiện để đạt bậc này — bắt buộc ghi theo quy định thang bảng lương
        # VD: "Hoàn thành tốt nhiệm vụ, không vi phạm kỷ luật trong 12 tháng"
        sa.Column("criteria", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["salary_scale_id"],
            ["salary_scales.id"],
            name="fk_salary_scale_entries_scale",
        ),
        sa.ForeignKeyConstraint(
            ["job_title_id"],
            ["job_titles.id"],
            name="fk_salary_scale_entries_job_title",
        ),
        # Mỗi chức danh chỉ có một hệ số cho mỗi bậc trong một phiên bản thang lương
        sa.UniqueConstraint(
            "salary_scale_id", "job_title_id", "grade_no",
            name="uq_salary_scale_entries",
        ),
    )
    op.create_index(
        "ix_salary_scale_entries_lookup",
        "salary_scale_entries",
        ["salary_scale_id", "job_title_id", "grade_no"],
    )


def downgrade() -> None:
    # Xóa theo thứ tự ngược để tránh lỗi vi phạm FK
    op.drop_table("salary_scale_entries")
    op.drop_table("salary_scales")
    op.drop_table("company_bhxh_region")
    op.drop_table("regional_minimum_wages")
    op.drop_table("org_change_logs")
    op.drop_table("job_position_attachments")
    op.drop_table("job_positions")
    op.drop_table("job_titles")
    op.drop_table("departments")
