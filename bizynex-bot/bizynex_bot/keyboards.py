"""Inline keyboards and the callback-data protocol.

Callback data format:  bx|<action>|<step_id>|<payload>
The step id travels with every button so a click on an old message can be detected
and rejected instead of silently corrupting the answer set (Telegram keeps stale
keyboards alive forever).
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .engine import Wizard
from .flow import Step

PREFIX = "bx"
SEP = "|"

ACT_START = "st"
ACT_ABOUT = "ab"
ACT_SERVICES = "sv"
ACT_PICK = "pk"
ACT_TOGGLE = "tg"
ACT_CONFIRM = "ok"
ACT_BACK = "bk"
ACT_SKIP = "sk"
ACT_EDIT_MENU = "ed"
ACT_EDIT_GOTO = "eg"
ACT_SUBMIT = "sb"
ACT_CANCEL = "cn"
ACT_RESTART = "rs"
ACT_RESUME = "rc"
ACT_NOOP = "np"

CHECK = "✓"
EMPTY = "▫"

LABEL_BACK = "◂ بازگشت"
LABEL_CONFIRM = "تأیید و ادامه ◂"
LABEL_SKIP = "رد کردن"
LABEL_CANCEL = "لغو"
LABEL_SUBMIT = "ارسال درخواست"
LABEL_EDIT = "اصلاح پاسخ‌ها"
LABEL_START = "شروع گفت‌وگو"
LABEL_ABOUT = "دربارهٔ Bizynex"
LABEL_SERVICES = "خدمات ما"
LABEL_RESTART = "شروع دوباره"
LABEL_BACK_REVIEW = "◂ بازگشت به خلاصه"
LABEL_RESUME = "ادامهٔ گفت‌وگوی قبلی"
LABEL_START_OVER = "شروع از ابتدا"


def cb(action: str, step_id: str = "", payload: str = "") -> str:
    data = SEP.join((PREFIX, action, step_id, payload))
    # Telegram hard-limits callback data to 64 bytes.
    assert len(data.encode("utf-8")) <= 64, f"callback data too long: {data}"
    return data


def parse_cb(data: str) -> tuple[str, str, str]:
    parts = data.split(SEP)
    if len(parts) != 4 or parts[0] != PREFIX:
        return "", "", ""
    return parts[1], parts[2], parts[3]


def _chunk(buttons: list[InlineKeyboardButton], columns: int) -> list[list[InlineKeyboardButton]]:
    if columns <= 1:
        return [[button] for button in buttons]
    return [buttons[i:i + columns] for i in range(0, len(buttons), columns)]


def welcome_keyboard(*, resume: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if resume:
        rows.append([InlineKeyboardButton(LABEL_RESUME, callback_data=cb(ACT_RESUME))])
        rows.append([InlineKeyboardButton(LABEL_START_OVER, callback_data=cb(ACT_START))])
    else:
        rows.append([InlineKeyboardButton(LABEL_START, callback_data=cb(ACT_START))])
    rows.append([
        InlineKeyboardButton(LABEL_SERVICES, callback_data=cb(ACT_SERVICES)),
        InlineKeyboardButton(LABEL_ABOUT, callback_data=cb(ACT_ABOUT)),
    ])
    return InlineKeyboardMarkup(rows)


def info_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LABEL_START, callback_data=cb(ACT_START))],
        [InlineKeyboardButton(LABEL_BACK, callback_data=cb(ACT_RESTART))],
    ])


def _nav_row(wizard: Wizard, step: Step) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if wizard.mode == "edit":
        row.append(InlineKeyboardButton(LABEL_BACK_REVIEW, callback_data=cb(ACT_BACK, step.id)))
    else:
        row.append(InlineKeyboardButton(LABEL_BACK, callback_data=cb(ACT_BACK, step.id)))
    if step.optional:
        row.append(InlineKeyboardButton(LABEL_SKIP, callback_data=cb(ACT_SKIP, step.id)))
    return row


def question_keyboard(wizard: Wizard) -> InlineKeyboardMarkup:
    step = wizard.step
    assert step is not None
    rows: list[list[InlineKeyboardButton]] = []

    if step.kind == "choice":
        current = wizard.answers.get(step.id)
        buttons = [
            InlineKeyboardButton(
                f"{CHECK} {option.label}" if option.key == current else option.label,
                callback_data=cb(ACT_PICK, step.id, option.key),
            )
            for option in step.options
        ]
        rows.extend(_chunk(buttons, step.columns))

    elif step.kind == "multi":
        selected = set(wizard.selection(step.id))
        buttons = [
            InlineKeyboardButton(
                f"{CHECK} {option.label}" if option.key in selected else f"{EMPTY} {option.label}",
                callback_data=cb(ACT_TOGGLE, step.id, option.key),
            )
            for option in step.options
        ]
        rows.extend(_chunk(buttons, step.columns))
        rows.append([InlineKeyboardButton(LABEL_CONFIRM, callback_data=cb(ACT_CONFIRM, step.id))])

    rows.append(_nav_row(wizard, step))
    return InlineKeyboardMarkup(rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LABEL_SUBMIT, callback_data=cb(ACT_SUBMIT))],
        [InlineKeyboardButton(LABEL_EDIT, callback_data=cb(ACT_EDIT_MENU))],
        [
            InlineKeyboardButton(LABEL_BACK, callback_data=cb(ACT_BACK)),
            InlineKeyboardButton(LABEL_CANCEL, callback_data=cb(ACT_CANCEL)),
        ],
    ])


def edit_menu_keyboard(wizard: Wizard) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for step, _ in wizard.answered_steps():
        label = step.label()
        if len(label) > 38:
            label = label[:37] + "…"
        rows.append([InlineKeyboardButton(label, callback_data=cb(ACT_EDIT_GOTO, step.id))])
    rows.append([InlineKeyboardButton(LABEL_BACK_REVIEW, callback_data=cb(ACT_BACK))])
    return InlineKeyboardMarkup(rows)


def done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LABEL_RESTART, callback_data=cb(ACT_RESTART))],
    ])


def retry_submit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LABEL_SUBMIT, callback_data=cb(ACT_SUBMIT))],
        [InlineKeyboardButton(LABEL_BACK_REVIEW, callback_data=cb(ACT_BACK))],
    ])
