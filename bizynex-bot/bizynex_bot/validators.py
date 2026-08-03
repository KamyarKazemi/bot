"""Input validators for free-text wizard steps.

Every validator returns (ok, cleaned_value_or_error_message). Errors are Persian,
written to be helpful rather than scolding — an intake form is the first impression
of how Bizynex communicates.
"""

from __future__ import annotations

import re

from .localization import to_ascii_digits

ZWNJ = "‌"

_MOBILE_RE = re.compile(r"^09\d{9}$")
_LANDLINE_RE = re.compile(r"^0[1-8]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
_URL_RE = re.compile(r"^(https?://)?([\w-]+\.)+[a-zA-Z]{2,}(/\S*)?$")

# Characters that are invisible or purely decorative and only cause storage noise.
_CONTROL_RE = re.compile(r"[‪-‮⁦-⁩﻿]")


def clean_text(value: str) -> str:
    value = _CONTROL_RE.sub("", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def validate_free_text(value: str, *, min_len: int = 2, max_len: int = 800) -> tuple[bool, str]:
    value = clean_text(value)
    if len(value) < min_len:
        return False, "لطفاً کمی کامل‌تر بنویسید تا بتوانیم درست راهنمایی‌تان کنیم."
    if len(value) > max_len:
        return False, f"متن طولانی‌تر از حد مجاز است. لطفاً در حداکثر {max_len} نویسه خلاصه کنید."
    return True, value


def validate_short_text(value: str) -> tuple[bool, str]:
    return validate_free_text(value, min_len=2, max_len=120)


def validate_name(value: str) -> tuple[bool, str]:
    value = clean_text(value)
    if len(value) < 3:
        return False, "لطفاً نام و نام خانوادگی را کامل بنویسید."
    if len(value) > 80:
        return False, "نام واردشده بیش از حد طولانی است."
    if any(ch.isdigit() for ch in to_ascii_digits(value)):
        return False, "نام نباید شامل عدد باشد. لطفاً فقط نام و نام خانوادگی را بنویسید."
    return True, value


def validate_phone(value: str) -> tuple[bool, str]:
    """Accepts Persian digits, spaces, dashes, +98 / 0098 prefixes.

    Returns the canonical 09xxxxxxxxx (mobile) or 0xxxxxxxxxx (landline) form.
    """
    raw = to_ascii_digits(clean_text(value))
    raw = re.sub(r"[\s\-()._]", "", raw)
    raw = raw.replace("+98", "0", 1) if raw.startswith("+98") else raw
    if raw.startswith("0098"):
        raw = "0" + raw[4:]
    elif raw.startswith("98") and len(raw) == 12:
        raw = "0" + raw[2:]
    elif raw.startswith("9") and len(raw) == 10:
        raw = "0" + raw
    if _MOBILE_RE.match(raw) or _LANDLINE_RE.match(raw):
        return True, raw
    return False, (
        "شماره واردشده معتبر نیست.\n"
        "نمونهٔ درست: ۰۹۱۲۱۲۳۴۵۶۷ یا ۰۲۱۲۲۳۳۴۴۵۵"
    )


def validate_email(value: str) -> tuple[bool, str]:
    value = to_ascii_digits(clean_text(value)).strip().lower()
    if _EMAIL_RE.match(value) and len(value) <= 120:
        return True, value
    return False, "ایمیل واردشده معتبر نیست. نمونهٔ درست: name@example.com"


def validate_url_or_text(value: str) -> tuple[bool, str]:
    value = clean_text(value)
    if len(value) > 300:
        return False, "آدرس واردشده بیش از حد طولانی است."
    if len(value) < 3:
        return False, "لطفاً آدرس یا توضیح کوتاهی بنویسید."
    return True, value


VALIDATORS = {
    "free_text": validate_free_text,
    "short_text": validate_short_text,
    "name": validate_name,
    "phone": validate_phone,
    "email": validate_email,
    "url": validate_url_or_text,
}
