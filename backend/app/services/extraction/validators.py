"""
Post-extraction validation - check extracted fields for common errors.

Runs AFTER extraction, BEFORE returning results to the user.
Does NOT re-extract - just flags suspicious values as warnings.

Validators:
- Date format check (should be YYYY-MM-DD)
- Amount sanity check (should be numeric, reasonable range)
- Required field presence (template-defined required fields should not be null)
- Line items total check (line items should sum to total amount)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("validation")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AMOUNT_MAX = 1_000_000_000  # $1B - anything above this is likely an error


@dataclass
class ValidationWarning:
    """A warning about a potentially incorrect extracted value."""

    field: str
    message: str
    severity: str = "warning"  # "warning" | "error"


@dataclass
class ValidationResult:
    """Result of validating extracted fields."""

    warnings: list[ValidationWarning] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> list[dict[str, str]]:
        return [
            {"field": w.field, "message": w.message, "severity": w.severity}
            for w in self.warnings
        ]


def validate_extracted_fields(
    fields: dict[str, Any],
    *,
    date_fields: Optional[list[str]] = None,
    amount_fields: Optional[list[str]] = None,
    required_fields: Optional[list[str]] = None,
) -> ValidationResult:
    """
    Validate extracted field values and return warnings.

    Field type hints are inferred from field names if not explicitly provided:
    - Fields containing "date" -> date validation
    - Fields containing "amount", "total", "price", "cost", "tax" -> amount validation
    """
    result = ValidationResult()

    if date_fields is None:
        date_fields = [f for f in fields if _is_date_field(f)]
    if amount_fields is None:
        amount_fields = [f for f in fields if _is_amount_field(f)]

    for field_name in date_fields:
        value = fields.get(field_name)
        if value is None:
            continue
        if isinstance(value, str) and not DATE_PATTERN.match(value):
            result.warnings.append(
                ValidationWarning(
                    field=field_name,
                    message=f"Date not in YYYY-MM-DD format: '{value}'",
                    severity="warning",
                )
            )

    for field_name in amount_fields:
        value = fields.get(field_name)
        if value is None:
            continue
        try:
            num = float(value) if isinstance(value, str) else float(value)
            if num < 0:
                result.warnings.append(
                    ValidationWarning(
                        field=field_name,
                        message=f"Negative amount: {num}",
                        severity="warning",
                    )
                )
            if abs(num) > AMOUNT_MAX:
                result.warnings.append(
                    ValidationWarning(
                        field=field_name,
                        message=f"Unusually large amount: {num}",
                        severity="warning",
                    )
                )
        except (ValueError, TypeError):
            result.warnings.append(
                ValidationWarning(
                    field=field_name,
                    message=f"Amount is not numeric: '{value}'",
                    severity="error",
                )
            )

    if required_fields:
        for field_name in required_fields:
            value = fields.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                result.warnings.append(
                    ValidationWarning(
                        field=field_name,
                        message="Required field is empty",
                        severity="error",
                    )
                )

    _check_line_items_total(fields, result)

    if result.has_warnings:
        logger.info(
            "Validation found %d warnings: %s",
            len(result.warnings),
            ", ".join(w.field for w in result.warnings),
        )

    return result


def _is_date_field(name: str) -> bool:
    """Heuristic: field name contains 'date'."""
    return "date" in name.lower()


def _is_amount_field(name: str) -> bool:
    """Heuristic: field name suggests a monetary amount."""
    lower = name.lower()
    return any(
        kw in lower
        for kw in ["amount", "total", "price", "cost", "tax", "subtotal", "fee"]
    )


def _check_line_items_total(fields: dict[str, Any], result: ValidationResult) -> None:
    """Check if line items sum to the total amount (±2% tolerance)."""
    total_value = None
    total_field = None
    for key in ("total_amount", "grand_total", "total", "amount_due", "net_amount"):
        if key in fields and fields[key] is not None:
            try:
                total_value = float(fields[key])
                total_field = key
                break
            except (ValueError, TypeError):
                pass

    if total_value is None or total_field is None:
        return

    line_items = fields.get("line_items")
    if not isinstance(line_items, list) or not line_items:
        return

    line_total = 0.0
    amount_keys = ("amount", "total", "line_total", "extended_price", "net_amount")
    for item in line_items:
        if not isinstance(item, dict):
            continue
        for key in amount_keys:
            if key in item and item[key] is not None:
                try:
                    line_total += float(item[key])
                    break
                except (ValueError, TypeError):
                    pass

    if line_total == 0:
        return

    tolerance = max(abs(total_value) * 0.02, 0.01)  # 2% or $0.01
    diff = abs(total_value - line_total)
    if diff > tolerance:
        result.warnings.append(
            ValidationWarning(
                field=total_field,
                message=(
                    f"Line items sum ({line_total:.2f}) doesn't match "
                    f"total ({total_value:.2f})"
                ),
                severity="warning",
            )
        )
