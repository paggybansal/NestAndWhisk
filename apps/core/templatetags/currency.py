from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

INR_SYMBOL = "₹"


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _format_indian_integer(number: int) -> str:
    number_str = str(abs(number))
    if len(number_str) <= 3:
        return number_str

    last_three = number_str[-3:]
    remaining = number_str[:-3]
    parts: list[str] = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        parts.insert(0, remaining)
    return f"{','.join(parts)},{last_three}"


@register.filter(name="inr")
def inr(value) -> str:
    amount = _to_decimal(value).quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    integer_part = int(abs(amount))
    decimal_part = int((abs(amount) - integer_part) * 100)
    grouped_integer = _format_indian_integer(integer_part)
    return f"{sign}{INR_SYMBOL}{grouped_integer}.{decimal_part:02d}"


@register.simple_tag
def currency_code() -> str:
    return "INR"


@register.simple_tag
def currency_symbol() -> str:
    return INR_SYMBOL

