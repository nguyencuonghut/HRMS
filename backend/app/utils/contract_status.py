from __future__ import annotations

from datetime import date
from typing import Optional

import sqlalchemy as sa


def effective_contract_status(status: str, effective_to: Optional[date]) -> str:
    if status in {"terminated", "draft"}:
        return status
    today = date.today()
    if effective_to is not None and effective_to < today:
        return "expired"
    return "active"


def contract_effective_status_expr(
    *,
    status_col,
    effective_to_col,
    today: Optional[date] = None,
):
    today = today or date.today()
    return sa.case(
        (status_col == "terminated", "terminated"),
        (status_col == "draft", "draft"),
        ((effective_to_col.is_not(None)) & (effective_to_col < today), "expired"),
        else_="active",
    )
