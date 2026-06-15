"""Quy tắc pháp lý thử việc theo Điều 25 Bộ luật Lao động 2019.

Không suy diễn từ cấp bậc nội bộ (`job_titles.level`).
Nhóm pháp lý phải được cấu hình tường minh trên vị trí công việc.
"""
from __future__ import annotations

from typing import Optional

PROBATION_LEGAL_LIMITS: dict[str, int] = {
    "enterprise_manager": 180,
    "college_plus": 60,
    "intermediate_technical_clerical": 30,
    "other": 6,
}

PROBATION_LEGAL_GROUP_LABELS: dict[str, str] = {
    "enterprise_manager": "Người quản lý doanh nghiệp",
    "college_plus": "Công việc yêu cầu trình độ từ cao đẳng trở lên",
    "intermediate_technical_clerical": "Công việc yêu cầu trung cấp / công nhân kỹ thuật / nhân viên nghiệp vụ",
    "other": "Công việc khác",
}

PROBATION_LEGAL_GROUP_OPTIONS: tuple[str, ...] = tuple(PROBATION_LEGAL_LIMITS.keys())


def normalize_probation_legal_group(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized not in PROBATION_LEGAL_GROUP_OPTIONS:
        raise ValueError(f"Nhóm thử việc pháp lý không hợp lệ: '{value}'")
    return normalized


def get_probation_limit(probation_legal_group: Optional[str]) -> Optional[int]:
    normalized = normalize_probation_legal_group(probation_legal_group)
    if normalized is None:
        return None
    return PROBATION_LEGAL_LIMITS[normalized]


def get_probation_legal_group_label(probation_legal_group: Optional[str]) -> Optional[str]:
    normalized = normalize_probation_legal_group(probation_legal_group)
    if normalized is None:
        return None
    return PROBATION_LEGAL_GROUP_LABELS[normalized]
