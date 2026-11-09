"""Financial schemas and precision-enforced currency types.

Non-negotiable invariant: Zero binary float math.
All monetary amounts are strictly represented as Python Decimal objects with
exact 2-decimal-place quantization (NUMERIC(12, 2)).
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Annotated, Any
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def validate_strict_money(v: Any) -> Decimal:
    """Validate that input is a valid monetary value and reject standard floats.

    Binary floating-point types (float) lose precision (e.g. 0.1 + 0.2 != 0.3)
    and are strictly forbidden in financial calculation engines.
    """
    if isinstance(v, float):
        raise ValueError(
            "Float types are forbidden for monetary values to prevent precision loss. "
            "Pass amounts as a Decimal, integer cents, or string (e.g. '123.45')."
        )

    try:
        if isinstance(v, Decimal):
            d = v
        elif isinstance(v, (str, int)):
            d = Decimal(str(v))
        else:
            raise ValueError(f"Unsupported money type: {type(v).__name__}")
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid monetary decimal format: {v}") from exc

    if not d.is_finite():
        raise ValueError("Monetary amount must be a finite number (NaN or Infinity rejected).")

    # Quantize to 2 decimal places using Banker's Rounding (ROUND_HALF_EVEN)
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def serialize_money(d: Decimal) -> str:
    """Serialize Decimal to a standard 2-decimal string format for JSON."""
    return f"{d:.2f}"


# Reusable Pydantic Type for financial amounts
Money = Annotated[
    Decimal,
    BeforeValidator(validate_strict_money),
    PlainSerializer(serialize_money, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^-?\d+\.\d{2}$", "example": "42.50"}),
]


def validate_positive_money(v: Any) -> Decimal:
    """Validate that money amount is strictly positive (> 0.00)."""
    d = validate_strict_money(v)
    if d <= Decimal("0.00"):
        raise ValueError("Monetary amount must be strictly greater than 0.00")
    return d


PositiveMoney = Annotated[
    Decimal,
    BeforeValidator(validate_positive_money),
    PlainSerializer(serialize_money, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^\d+\.\d{2}$", "example": "42.50"}),
]
