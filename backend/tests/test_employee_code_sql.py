from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.core.database import AsyncSessionLocal
from app.utils.employee_code_sql import sql_padded_employee_seq_expr


@pytest.mark.asyncio
async def test_sql_padded_employee_seq_expr_preserves_long_numbers_and_respects_min_digits():
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                sa.select(
                    sql_padded_employee_seq_expr(sa.literal(312), min_digits=4).label("short_code"),
                    sql_padded_employee_seq_expr(sa.literal(10000), min_digits=4).label("long_code"),
                    (sa.literal("KS") + sql_padded_employee_seq_expr(sa.literal(123456), min_digits=4)).label("prefixed_long_code"),
                    sql_padded_employee_seq_expr(sa.literal(312), min_digits=6).label("short_code_wide"),
                    sql_padded_employee_seq_expr(sa.literal(10000), min_digits=6).label("long_code_wide"),
                    (sa.literal("SYS2") + sql_padded_employee_seq_expr(sa.literal(1234567), min_digits=6)).label("prefixed_long_code_wide"),
                )
            )
        ).mappings().one()

    assert row["short_code"] == "0312"
    assert row["long_code"] == "10000"
    assert row["prefixed_long_code"] == "KS123456"
    assert row["short_code_wide"] == "000312"
    assert row["long_code_wide"] == "010000"
    assert row["prefixed_long_code_wide"] == "SYS21234567"
