"""add application_on_hold email template

Revision ID: 0044
Revises: 0043
Create Date: 2026-05-26
"""
from alembic import op
from datetime import datetime, timezone

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None

_NOW = datetime.now(timezone.utc).replace(tzinfo=None)

_SUBJECT = "Thông báo về hồ sơ ứng tuyển — {{vi_tri}}"

_BODY = """<p>Kính gửi {{ten_ung_vien}},</p>
<p>Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí <strong>{{vi_tri}}</strong> tại <strong>{{ten_cong_ty}}</strong>.</p>
<p>Chúng tôi đã nhận được hồ sơ của bạn và hiện đang trong quá trình xem xét. Chúng tôi sẽ liên hệ với bạn sớm nhất có thể để thông báo kết quả.</p>
<p>Nếu có bất kỳ thắc mắc nào, vui lòng liên hệ {{ten_hr}} qua email {{email_hr}}.</p>
<p>Trân trọng,<br/>{{ten_hr}}<br/>{{ten_cong_ty}}</p>"""


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO recruitment_email_templates
            (code, name, trigger_event, subject, body_html, is_active, is_system, created_at, updated_at)
        VALUES
            ('application_on_hold', 'Hồ sơ đang được xem xét', 'hold',
             {op.inline_literal(_SUBJECT)}, {op.inline_literal(_BODY)},
             true, false, '{_NOW}', '{_NOW}')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM recruitment_email_templates WHERE code = 'application_on_hold'")
