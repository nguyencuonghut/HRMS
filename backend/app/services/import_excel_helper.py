"""Helpers dùng chung cho import Excel."""
from __future__ import annotations

from collections.abc import Iterable

from openpyxl.worksheet.worksheet import Worksheet


def is_blank_row(row_vals: Iterable[object]) -> bool:
    return all(value is None or str(value).strip() == "" for value in row_vals)


def extract_header_and_non_blank_rows(ws: Worksheet) -> tuple[list[str], list[tuple[int, tuple[object, ...]]]]:
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_source = next(rows_iter)
    except StopIteration:
        return [], []

    header_row = [str(cell).strip() if cell else "" for cell in header_source]
    data_rows: list[tuple[int, tuple[object, ...]]] = []

    for excel_row, row_vals in enumerate(rows_iter, start=2):
        if is_blank_row(row_vals):
            continue
        data_rows.append((excel_row, row_vals))

    return header_row, data_rows
