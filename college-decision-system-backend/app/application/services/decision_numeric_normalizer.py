from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class NormalizedDecisionNumeric:
    unit_value: float | None
    ten_point_value: float | None
    warnings: tuple[str, ...] = ()


class DecisionNumericNormalizer:
    """Normalize decision-scoring numerics to both 0-1 and 0-10 scales."""

    def normalize(self, value: Any, *, field_path: str) -> NormalizedDecisionNumeric:
        if value is None:
            return NormalizedDecisionNumeric(unit_value=None, ten_point_value=None)
        if isinstance(value, str) and not value.strip():
            return NormalizedDecisionNumeric(
                unit_value=None,
                ten_point_value=None,
                warnings=(f"{field_path} was blank and was ignored.",),
            )

        try:
            decimal_value = Decimal(str(value).strip())
        except (InvalidOperation, AttributeError, TypeError, ValueError):
            return NormalizedDecisionNumeric(
                unit_value=None,
                ten_point_value=None,
                warnings=(f"{field_path} carried malformed numeric value {value!r} and was ignored.",),
            )

        warnings: list[str] = []
        if decimal_value < Decimal("0"):
            warnings.append(f"{field_path} was below 0 and was clamped to 0.")
            decimal_value = Decimal("0")
        elif decimal_value > Decimal("10"):
            warnings.append(f"{field_path} exceeded 10 and was clamped to 10.")
            decimal_value = Decimal("10")

        if decimal_value <= Decimal("1"):
            decimal_value *= Decimal("10")

        unit_value = float(decimal_value / Decimal("10"))
        ten_point_value = float(decimal_value)
        return NormalizedDecisionNumeric(
            unit_value=unit_value,
            ten_point_value=ten_point_value,
            warnings=tuple(warnings),
        )
