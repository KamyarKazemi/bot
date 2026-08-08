"""Message text. Every Persian string the user sees lives here.

Voice (from CONTEXT.md): professional, warm, plain. We explain why we ask, we never
pressure, we never promise a price, and we never use jargon the customer would have
to look up. Emphasis markers are used sparingly — at most one per message.
"""

from __future__ import annotations

import html
from typing import Any

from .engine import Wizard
from .flow import Step
from .localization import format_jalali, to_persian_digits

BRAND = "Bizynex"
BULLET = "•"
CHECK = "✓"
DOT = "·"

# The one promise the bot makes. Keep it conservative — a kept promise is the product.
RESPONSE_PROMISE = "معمولاً در کمتر از یک روز کاری پاسخ می‌دهیم."


def esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


# --------------------------------------------------------------------- start
def welcome(first_name: str | None = None) -> str:
    greeting = f"سلام {esc(first_name)} عزیز" if first_name else "سلام"
    return (
        f"<b>{greeting}؛ به {BRAND} خوش آمدید.</b>\n\n"
        "ما سامانه‌های دیجیتالی می‌سازیم که کار کسب‌وکار شما را ساده‌تر و قابل‌اتکاتر می‌کند: "
        "وب‌سایت، اتوماسیون فرایندها، ربات پیام‌رسان، سیستم انبارداری و طراحی پوستر و بنر تبلیغاتی.\n\n"
        "برای اینکه دقیق بفهمیم به چه چیزی نیاز دارید، چند پرسش کوتاه می‌پرسیم.\n\n"
        f"{BULLET} حدود دو دقیقه وقت می‌گیرد\n"
        f"{BULLET} در هر مرحله می‌توانید به عقب برگردید\n"
        f"{BULLET} پیش از ارسال، همهٔ پاسخ‌ها را می‌بینید و می‌توانید اصلاح کنید\n"
        f"{BULLET} هیچ پرداختی و هیچ تعهدی در کار نیست\n\n"
        "<i>اطلاعات شما فقط برای همین درخواست استفاده می‌شود.</i>"
    )


def about() -> str:
    return (
        f"<b>دربارهٔ {BRAND}</b>\n\n"
        "ما یک تیم فنی هستیم؛ از طراحی رابط کاربری تا معماری و زیرساخت و راهبرد کسب‌وکار، همه در داخل تیم انجام می‌شود.\n\n"
        "طرز کارمان ساده است:\n"
        f"{BULLET} اول مسئلهٔ کسب‌وکار را می‌فهمیم، بعد دربارهٔ راه‌حل فنی حرف می‌زنیم\n"
        f"{BULLET} پیش از شروع، دامنهٔ کار، زمان‌بندی و هزینه شفاف نوشته می‌شود\n"
        f"{BULLET} چیزی که تحویل می‌دهیم مستند دارد؛ برای تغییرات بعدی به ما وابسته نمی‌مانید\n"
        f"{BULLET} بعد از تحویل هم در دسترسیم؛ پروژه پایان رابطه نیست\n\n"
        "ارزان‌ترین گزینهٔ بازار نیستیم و ادعایش را هم نداریم. "
        "چیزی که می‌فروشیم نتیجهٔ قابل‌اتکاست، نه کمترین قیمت."
    )


def services() -> str:
    return (
        "<b>خدمات ما</b>\n\n"
        f"<b>{BULLET} وب‌سایت</b>\n"
        "سایت شرکتی، فروشگاه اینترنتی، وب‌اپلیکیشن و پنل کاربری — با تمرکز بر سرعت، دسترس‌پذیری و اعتبار حرفه‌ای.\n\n"
        f"<b>{BULLET} اتوماسیون و یکپارچه‌سازی</b>\n"
        "حذف کارهای دستی تکراری، اتصال ابزارهای جدا از هم، و گزارش‌گیری خودکار.\n\n"
        f"<b>{BULLET} ربات پیام‌رسان</b>\n"
        "پاسخ خودکار، ثبت سفارش، جذب سرنخ و اطلاع‌رسانی روی تلگرام و سایر بسترها.\n\n"
        f"<b>{BULLET} سیستم انبارداری</b>\n"
        "کنترل موجودی، بارکد، فاکتور و گزارش مدیریتی متناسب با اندازهٔ واقعی کسب‌وکار شما.\n\n"
        f"<b>{BULLET} طراحی پوستر، بنر، کاور و تامبنیل</b>\n"
        "پوستر و بنر تبلیغاتی، کاور اینستاگرام و تامبنیل یوتیوب — طراحی‌شده برای دیده‌شدن، نه فقط زیبا بودن.\n"
        "زمان تحویل مشخص است: به ازای هر ۳ طرح، یک روز کاری.\n\n"
        "برای شروع، «شروع گفت‌وگو» را بزنید."
    )


def help_text() -> str:
    return (
        "<b>راهنما</b>\n\n"
        f"{BULLET} /start — شروع یا شروع دوبارهٔ گفت‌وگو\n"
        f"{BULLET} /cancel — لغو درخواست فعلی\n"
        f"{BULLET} /help — همین راهنما\n\n"
        "در طول پرسش‌ها:\n"
        f"{DOT} دکمهٔ «بازگشت» شما را به پرسش قبلی می‌برد\n"
        f"{DOT} در پرسش‌های چندگزینه‌ای، بعد از انتخاب‌ها «تأیید و ادامه» را بزنید\n"
        f"{DOT} در پرسش‌های متنی، پاسخ را همین‌جا تایپ و ارسال کنید\n\n"
        f"{RESPONSE_PROMISE}"
    )


# ---------------------------------------------------------------- questions
def progress_line(wizard: Wizard) -> str:
    index, total = wizard.position()
    section = wizard.step.section if wizard.step else ""
    # Before a service is chosen the remaining count is not knowable yet — showing a
    # total that then changes would look careless.
    if "service" not in wizard.answers:
        parts = [f"گام {to_persian_digits(index)}"]
    else:
        parts = [f"گام {to_persian_digits(index)} از {to_persian_digits(total)}"]
    if section:
        parts.append(section)
    return f"<i>{esc(f' {DOT} '.join(parts))}</i>"


def question(wizard: Wizard) -> str:
    step = wizard.step
    assert step is not None
    lines = []
    if wizard.mode == "edit":
        lines.append("<i>ویرایش پاسخ</i>")
    else:
        lines.append(progress_line(wizard))
    lines.append("")
    lines.append(f"<b>{esc(step.title)}</b>")
    if step.help:
        lines.append("")
        lines.append(f"<i>{esc(step.help)}</i>")

    if step.kind == "text":
        lines.append("")
        hint = "پاسخ را همین‌جا بنویسید و ارسال کنید."
        if step.placeholder:
            hint += f"\n{DOT} {step.placeholder}"
        lines.append(f"<i>{esc(hint)}</i>")
        existing = wizard.answers.get(step.id)
        if existing:
            lines.append("")
            lines.append(f"پاسخ فعلی: <code>{esc(existing)}</code>")
    elif step.kind == "multi":
        selected = wizard.selection(step.id)
        lines.append("")
        count = to_persian_digits(len(selected))
        lines.append(f"<i>{esc(f'{count} گزینه انتخاب شده است.')}</i>")
    return "\n".join(lines)


def validation_error(message: str) -> str:
    return f"<b>پاسخ ثبت نشد</b>\n{esc(message)}"


# ------------------------------------------------------------------- review
def review(wizard: Wizard) -> str:
    lines = ["<b>خلاصهٔ درخواست شما</b>", ""]
    lines.append("<i>لطفاً یک بار مرور کنید. هر مورد را می‌توانید اصلاح کنید.</i>")
    current_section = ""
    for step, _ in wizard.answered_steps():
        if step.section and step.section != current_section:
            current_section = step.section
            lines.append("")
            lines.append(f"<b>{esc(current_section)}</b>")
        value = wizard.display_value(step)
        if step.validator == "phone":
            value = to_persian_digits(value)  # customers read Persian numerals
        lines.append(f"{DOT} {esc(step.label())}: {esc(value)}")
    lines.append("")
    lines.append("<i>با ارسال، این اطلاعات برای تیم Bizynex فرستاده می‌شود.</i>")
    return "\n".join(lines)


def edit_menu() -> str:
    return (
        "<b>کدام پاسخ را می‌خواهید تغییر دهید؟</b>\n\n"
        "<i>پس از اصلاح، دوباره به همین خلاصه برمی‌گردید.</i>"
    )


# --------------------------------------------------------------------- done
def submitted(ticket: str) -> str:
    return (
        f"<b>درخواست شما ثبت شد.</b>\n\n"
        f"شمارهٔ پیگیری: <code>{esc(ticket)}</code>\n"
        f"تاریخ ثبت: {esc(format_jalali())}\n\n"
        "<b>مرحلهٔ بعد چیست؟</b>\n"
        f"{DOT} پاسخ‌های شما را بررسی می‌کنیم\n"
        f"{DOT} اگر نکتهٔ مبهمی باشد، ابتدا همان را می‌پرسیم\n"
        f"{DOT} سپس پیشنهاد اولیه شامل دامنهٔ کار، زمان‌بندی و بازهٔ هزینه را می‌فرستیم\n\n"
        f"{RESPONSE_PROMISE}\n\n"
        "<i>اگر چیزی از قلم افتاد، همین‌جا بنویسید؛ به همین پرونده اضافه می‌شود.</i>"
    )


def submit_failed() -> str:
    return (
        "<b>ارسال کامل نشد.</b>\n\n"
        "پاسخ‌های شما ذخیره شده و از بین نرفته است. لطفاً چند لحظه بعد دوباره «ارسال درخواست» را بزنید.\n\n"
        "<i>اگر باز هم تکرار شد، همین پیام را برای پشتیبانی بفرستید.</i>"
    )


def cancelled() -> str:
    return (
        "<b>درخواست لغو شد.</b>\n\n"
        "هر وقت خواستید با /start دوباره شروع کنید. چیزی از طرف شما ارسال نشده است."
    )


def stale_click() -> str:
    return "این دکمه مربوط به پیام قبلی است. لطفاً از پیام پایین ادامه دهید."


def unexpected_text() -> str:
    return (
        "برای این پرسش لطفاً یکی از دکمه‌های بالا را انتخاب کنید.\n"
        "<i>اگر دکمه‌ها را نمی‌بینید، /start را بزنید.</i>"
    )


def no_session() -> str:
    return (
        "گفت‌وگوی فعالی در جریان نیست.\n"
        "برای شروع /start را بزنید."
    )


def error_notice() -> str:
    return (
        "<b>مشکلی پیش آمد.</b>\n\n"
        "پاسخ‌های شما حفظ شده است. لطفاً دوباره تلاش کنید یا /start را بزنید."
    )


def followup_ack() -> str:
    return "یادداشت شما ثبت شد و به پروندهٔ درخواستتان اضافه می‌شود."


# ---------------------------------------------------------------- admin card
def admin_card(wizard: Wizard, *, ticket: str, user: dict[str, Any]) -> str:
    lines = [
        f"<b>درخواست جدید {DOT} {esc(ticket)}</b>",
        f"<i>{esc(format_jalali())}</i>",
        "",
    ]
    current_section = ""
    for step, _ in wizard.answered_steps():
        if step.section and step.section != current_section:
            current_section = step.section
            lines.append("")
            lines.append(f"<b>{esc(current_section)}</b>")
        value = wizard.display_value(step)
        if step.validator == "phone":
            # Copyable and dialable — the founder acts on this, not reads it.
            lines.append(f"{DOT} {esc(step.label())}: <code>{esc(value)}</code>")
            continue
        lines.append(f"{DOT} {esc(step.label())}: {esc(value)}")
    lines.append("")
    lines.append("<b>کاربر تلگرام</b>")
    full_name = esc(user.get("full_name") or "—")
    username = user.get("username")
    lines.append(f"{DOT} نام پروفایل: {full_name}")
    if username:
        lines.append(f"{DOT} شناسه: @{esc(username)}")
    user_id = user.get("id")
    lines.append(f"{DOT} آی‌دی عددی: <code>{esc(user_id)}</code>")
    lines.append(f'{DOT} گفت‌وگوی مستقیم: <a href="tg://user?id={esc(user_id)}">باز کردن چت</a>')
    return "\n".join(lines)


def admin_followup(ticket: str, user: dict[str, Any], text: str) -> str:
    return (
        f"<b>پیام تکمیلی {DOT} {esc(ticket)}</b>\n"
        f"<i>{esc(format_jalali())}</i>\n\n"
        f"{esc(text)}\n\n"
        f'<a href="tg://user?id={esc(user.get("id"))}">باز کردن چت کاربر</a>'
    )


def admin_setup_warning() -> str:
    return (
        "<b>هشدار پیکربندی</b>\n\n"
        "متغیر <code>ADMIN_CHAT_IDS</code> تنظیم نشده است؛ درخواست‌ها فقط در پایگاه‌داده ذخیره می‌شوند "
        "و به تلگرام کسی ارسال نمی‌شوند.\n\n"
        "برای رفع: دستور /id را به ربات بفرستید و عدد نمایش‌داده‌شده را در فایل <code>.env</code> قرار دهید."
    )
