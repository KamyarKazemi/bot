"""Persian numerals, Jalali (Shamsi) calendar, and Iran-local time.

Pure standard library — no jdatetime, no pytz, nothing to install and nothing that
needs network access at runtime.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Iran Standard Time. Iran abolished DST in 2022, so a fixed offset is correct.
IRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="IRST")

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"

_TO_PERSIAN = str.maketrans(ASCII_DIGITS, PERSIAN_DIGITS)
_TO_ASCII = str.maketrans(
    PERSIAN_DIGITS + ARABIC_INDIC_DIGITS,
    ASCII_DIGITS + ASCII_DIGITS,
)

JALALI_MONTHS = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)

JALALI_WEEKDAYS = (
    "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه",
)


def to_persian_digits(text: str | int) -> str:
    """۱۲۳ instead of 123. Applied to every number the user sees."""
    return str(text).translate(_TO_PERSIAN)


def to_ascii_digits(text: str) -> str:
    """Normalise anything the user typed (۰۹۱۲... or ٠٩١٢...) back to 0912..."""
    return str(text).translate(_TO_ASCII)


def group_digits(number: int) -> str:
    """1234567 -> ۱٬۲۳۴٬۵۶۷ using the Persian thousands separator."""
    return to_persian_digits(f"{number:,}").replace(",", "٬")


# --- Gregorian <-> Jalali -------------------------------------------------
# The standard 33-year-cycle arithmetic conversion (the same algorithm used by
# jdatetime and the common JS/PHP implementations), written out in full so the
# bot has no calendar dependency.

_G_CUMULATIVE_DAYS = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

_JALALI_LEAP_REMAINDERS = frozenset({1, 5, 9, 13, 17, 22, 26, 30})


def is_jalali_leap(year: int) -> bool:
    """Esfand has 30 days in a leap year instead of 29."""
    return year % 33 in _JALALI_LEAP_REMAINDERS


def jalali_days_in_month(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """(2026, 8, 3) -> (1405, 5, 12)"""
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621

    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + _G_CUMULATIVE_DAYS[gm - 1]
    )

    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """(1405, 5, 12) -> (2026, 8, 3)"""
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621

    days = (
        365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )

    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    month_lengths = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 0
    for gm, length in enumerate(month_lengths, start=1):
        if gd <= length:
            break
        gd -= length
    return gy, gm, gd


def jalali_date_parts(dt: datetime | None = None) -> tuple[int, int, int]:
    dt = dt or now_iran()
    return gregorian_to_jalali(dt.year, dt.month, dt.day)


def now_iran() -> datetime:
    return datetime.now(IRAN_TZ)


def format_jalali(dt: datetime | None = None, *, with_time: bool = True, with_weekday: bool = True) -> str:
    """'دوشنبه ۱۲ مرداد ۱۴۰۵ — ساعت ۱۸:۴۵'"""
    dt = dt or now_iran()
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    parts: list[str] = []
    if with_weekday:
        # Python: Monday=0 ... Sunday=6. Jalali week starts Saturday.
        parts.append(JALALI_WEEKDAYS[(dt.weekday() + 2) % 7])
    parts.append(f"{to_persian_digits(jd)} {JALALI_MONTHS[jm - 1]} {to_persian_digits(jy)}")
    text = " ".join(parts)
    if with_time:
        text += f" — ساعت {to_persian_digits(f'{dt.hour:02d}')}:{to_persian_digits(f'{dt.minute:02d}')}"
    return text


def jalali_stamp(dt: datetime | None = None) -> str:
    """Compact ASCII stamp for ticket codes: 14050512"""
    jy, jm, jd = jalali_date_parts(dt)
    return f"{jy:04d}{jm:02d}{jd:02d}"
