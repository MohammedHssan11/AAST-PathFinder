from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import DateTime, func
from sqlalchemy.sql.sqltypes import Numeric
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column


PROGRAM_TRAIT_TYPES = frozenset({"best_fit", "avoid_if", "close_alternative"})
ACCREDITATION_SCOPES = frozenset({"national", "international"})
MOBILITY_ITEM_TYPES = frozenset(
    {"mobility_type", "partner_body", "region", "evidence_note"}
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionTimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )


class SafeNumeric(TypeDecorator):
    """Numeric column wrapper that preserves malformed SQLite values for runtime validation."""

    impl = Numeric
    cache_ok = True

    def result_processor(self, dialect, coltype):
        processor = self.impl.result_processor(dialect, coltype)

        def process(value):
            if value is None or processor is None:
                return value
            try:
                return processor(value)
            except (TypeError, ValueError, InvalidOperation):
                try:
                    return Decimal(str(value).strip())
                except (InvalidOperation, ValueError, TypeError):
                    return value

        return process


def validate_allowed_value(
    field_name: str,
    value: str,
    allowed_values: frozenset[str],
) -> str:
    if value not in allowed_values:
        allowed_display = ", ".join(sorted(allowed_values))
        raise ValueError(f"{field_name} must be one of: {allowed_display}")
    return value
