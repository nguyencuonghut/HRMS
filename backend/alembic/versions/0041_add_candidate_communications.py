"""add candidate communications

Revision ID: 0041
Revises: 0040
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

_TEMPLATES = [
    ("invite_screening",           "Mời tham gia sàng lọc",              "stage_moved:screening",  True),
    ("invite_interview",           "Mời phỏng vấn",                      "stage_moved:interview",  True),
    ("offer_sent",                 "Thông báo gửi Offer",                 "offer_sent",             True),
    ("offer_accepted_confirm",     "Xác nhận chấp nhận offer",           "offer_accepted",         True),
    ("rejection_early",            "Thông báo không phù hợp (sớm)",      "stage_moved:rejected",   True),
    ("rejection_after_interview",  "Cảm ơn sau phỏng vấn",               "rejected",               True),
    ("hired_welcome",              "Chào mừng nhân viên mới",            "hired",                  True),
]

_DEFAULT_SUBJECT = {
    "invite_screening":           "Thư mời tham gia sàng lọc — {{vi_tri}}",
    "invite_interview":           "Thư mời phỏng vấn — {{vi_tri}} tại {{ten_cong_ty}}",
    "offer_sent":                 "Thư mời nhận việc — {{vi_tri}}",
    "offer_accepted_confirm":     "Xác nhận chấp nhận Offer — {{vi_tri}}",
    "rejection_early":            "Thông báo kết quả ứng tuyển — {{vi_tri}}",
    "rejection_after_interview":  "Cảm ơn bạn đã tham gia phỏng vấn — {{vi_tri}}",
    "hired_welcome":              "Chào mừng bạn gia nhập {{ten_cong_ty}}!",
}

_DEFAULT_BODY = {
    "invite_screening": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Chúng tôi xin trân trọng mời bạn tham gia vòng sàng lọc cho vị trí <strong>{{vi_tri}}</strong> tại <strong>{{phong_ban}}</strong>.</p>
<p>Vui lòng liên hệ {{ten_hr}} qua email {{email_hr}} hoặc SĐT {{sdt_hr}} để biết thêm chi tiết.</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "invite_interview": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Chúng tôi xin mời bạn tham dự phỏng vấn cho vị trí <strong>{{vi_tri}}</strong> tại {{phong_ban}}.</p>
<ul>
  <li><strong>Thời gian:</strong> {{ngay_phong_van}} lúc {{gio_phong_van}}</li>
  <li><strong>Địa điểm:</strong> {{dia_diem_phong_van}}</li>
</ul>
<p>Mọi thắc mắc vui lòng liên hệ {{ten_hr}} — {{email_hr}}.</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "offer_sent": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Chúng tôi vui mừng gửi đến bạn thư mời nhận việc cho vị trí <strong>{{vi_tri}}</strong>.</p>
<ul>
  <li><strong>Ngày bắt đầu:</strong> {{ngay_bat_dau}}</li>
  <li><strong>Lương thử việc:</strong> {{luong_thu_viec}}</li>
  <li><strong>Thời gian thử việc:</strong> {{thoi_gian_thu_viec}}</li>
  <li><strong>Hạn phản hồi:</strong> {{han_phan_hoi_offer}}</li>
</ul>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "offer_accepted_confirm": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Chúng tôi xác nhận đã nhận được sự chấp thuận của bạn cho vị trí <strong>{{vi_tri}}</strong>.</p>
<p>Ngày bắt đầu làm việc dự kiến: <strong>{{ngay_bat_dau}}</strong>.</p>
<p>Chúng tôi sẽ liên hệ để hướng dẫn thủ tục onboarding.</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "rejection_early": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí <strong>{{vi_tri}}</strong> tại {{ten_cong_ty}}.</p>
<p>Sau khi xem xét hồ sơ, chúng tôi nhận thấy hồ sơ của bạn chưa phù hợp với yêu cầu hiện tại. Chúng tôi sẽ lưu thông tin của bạn và liên hệ khi có cơ hội phù hợp hơn.</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "rejection_after_interview": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Cảm ơn bạn đã dành thời gian tham gia phỏng vấn cho vị trí <strong>{{vi_tri}}</strong> tại {{ten_cong_ty}}.</p>
<p>Sau khi cân nhắc kỹ lưỡng, chúng tôi tiếc phải thông báo rằng chúng tôi sẽ tiếp tục với ứng viên khác phù hợp hơn với yêu cầu hiện tại. Chúng tôi đánh giá cao sự quan tâm và nỗ lực của bạn.</p>
<p>Chúc bạn thành công trong hành trình sự nghiệp!</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",

    "hired_welcome": """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Thay mặt toàn thể {{ten_cong_ty}}, chúng tôi xin chào mừng bạn chính thức gia nhập đội ngũ tại vị trí <strong>{{vi_tri}}</strong>, phòng <strong>{{phong_ban}}</strong>!</p>
<p>Ngày bắt đầu: <strong>{{ngay_bat_dau}}</strong>.</p>
<p>Chúng tôi sẽ liên hệ để hướng dẫn các thủ tục cần thiết trước ngày đi làm.</p>
<p>Hẹn gặp bạn sớm!<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>""",
}


def upgrade() -> None:
    op.create_table(
        "recruitment_email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("merge_fields", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_email_template_code"),
    )

    op.create_table(
        "candidate_communications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trigger_event", sa.String(100), nullable=True),
        sa.Column("merge_context", sa.Text(), nullable=True),
        sa.Column("sent_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["candidate_applications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["recruitment_email_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_candidate", "candidate_communications", ["candidate_id"])
    op.create_index("ix_comm_application", "candidate_communications", ["application_id"])
    op.create_index("ix_comm_status", "candidate_communications", ["status"])

    # Seed default templates
    from datetime import datetime
    import json
    import re
    now_dt = datetime.utcnow()
    rows = []
    for code, name, trigger_event, is_system in _TEMPLATES:
        body = _DEFAULT_BODY[code]
        subject = _DEFAULT_SUBJECT[code]
        fields = list(dict.fromkeys(re.findall(r"\{\{(\w+)\}\}", subject + body)))
        rows.append({
            "code": code,
            "name": name,
            "trigger_event": trigger_event,
            "subject": subject,
            "body_html": body,
            "merge_fields": json.dumps(fields),
            "is_active": True,
            "is_system": is_system,
            "created_at": now_dt,
            "updated_at": now_dt,
        })
    op.bulk_insert(
        sa.table(
            "recruitment_email_templates",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("trigger_event", sa.String),
            sa.column("subject", sa.Text),
            sa.column("body_html", sa.Text),
            sa.column("merge_fields", sa.Text),
            sa.column("is_active", sa.Boolean),
            sa.column("is_system", sa.Boolean),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        rows,
    )


def downgrade() -> None:
    op.drop_table("candidate_communications")
    op.drop_table("recruitment_email_templates")
