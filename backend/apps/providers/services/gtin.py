"""GTIN (EAN/UPC/JAN) helpers: normalize, validate – and the other codes found on boxes
(article numbers in Code 128/39)."""

from __future__ import annotations

import re


def check_digit_ok(code: str) -> bool:
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    # Weights 3,1,3,… from the right, excluding the check digit.
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def normalize(raw: str) -> str | None:
    """Digits only, UPC-A (12) padded to GTIN-13. None if it isn't a valid GTIN."""
    code = re.sub(r"\D", "", raw)
    if len(code) == 12:
        code = "0" + code
    if len(code) not in (8, 13, 14) or not check_digit_ok(code):
        return None
    return code


# An article or product number: letters, digits and a few separators, 4–32 characters.
ARTICLE = re.compile(r"^[A-Z0-9][A-Z0-9./-]{3,31}$")


def is_gtin(code: str) -> bool:
    """A normalized GTIN (see `normalize`: UPC-A is padded to 13); other all-digit
    codes are article numbers."""
    return code.isdigit() and len(code) in (8, 13, 14)


def normalize_code(raw: str) -> str | None:
    """A scanned or typed code: a GTIN if it looks like one (digits of a GTIN length; a
    wrong check digit is a misread then), else an article number such as "1836540T"
    (upper case, without spaces). None if it's neither."""
    compact = re.sub(r"\s+", "", raw).upper()
    digits = compact.replace("-", "")
    if digits.isdigit() and len(digits) in (8, 12, 13, 14):
        return normalize(digits)
    return compact if ARTICLE.match(compact) else None
