from __future__ import annotations

import sqlalchemy as sa


def sql_padded_employee_seq_expr(
    employee_seq_col,
    *,
    min_digits,
):
    seq_str = sa.cast(employee_seq_col, sa.String())
    return sa.case(
        (sa.func.length(seq_str) >= min_digits, seq_str),
        else_=sa.func.lpad(seq_str, min_digits, "0"),
    )

