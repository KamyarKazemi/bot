"""Offline preview of the conversation — no token, no network, no Telegram.

    python simulate.py                # interactive: you answer, it prints the cards
    python simulate.py --auto website # auto-play one branch and print every card

Use it to review the Persian copy and the question order before touching production.
"""

from __future__ import annotations

import argparse
import re
import sys

from bizynex_bot import keyboards as kb
from bizynex_bot import render
from bizynex_bot.engine import MODE_REVIEW, MODE_WIZARD, Wizard, new_state
from bizynex_bot.flow import SERVICE_OPTIONS

TAG_RE = re.compile(r"<[^>]+>")


def plain(html_text: str) -> str:
    text = html_text.replace("<br>", "\n")
    return TAG_RE.sub("", text)


def show_card(wizard: Wizard) -> None:
    print("\n" + "─" * 62)
    if wizard.mode == MODE_REVIEW:
        print(plain(render.review(wizard)))
        markup = kb.review_keyboard()
    else:
        print(plain(render.question(wizard)))
        markup = kb.question_keyboard(wizard)
    print("─" * 62)
    for row in markup.inline_keyboard:
        print("   [ " + " ]  [ ".join(button.text for button in row) + " ]")


def auto(service_key: str) -> None:
    wizard = Wizard(new_state())
    guard = 0
    while wizard.mode == MODE_WIZARD and guard < 60:
        show_card(wizard)
        step = wizard.step
        assert step is not None
        if step.id == "service":
            wizard.answer_choice("service", service_key)
        elif step.kind == "choice":
            wizard.answer_choice(step.id, step.options[0].key)
        elif step.kind == "multi":
            wizard.toggle_multi(step.id, step.options[0].key)
            wizard.confirm_multi(step.id)
        else:
            samples = {
                "phone": "۰۹۱۲۱۲۳۴۵۶۷",
                "email": "info@example.com",
                "name": "نام نمونه",
                "url": "example.com",
            }
            wizard.answer_text(step.id, samples.get(step.validator, "نمونهٔ پاسخ متنی برای پیش‌نمایش."))
        guard += 1
    show_card(wizard)
    print("\n" + plain(render.submitted("BZX-14050512-DEMO")))
    print("\n" + "═" * 62)
    print("کارت ارسالی به ادمین:")
    print("═" * 62)
    print(plain(render.admin_card(
        wizard,
        ticket="BZX-14050512-DEMO",
        user={"id": 123456789, "full_name": "نام نمونه", "username": "example"},
    )))


def interactive() -> None:
    wizard = Wizard(new_state())
    print(plain(render.welcome("مهمان")))
    while wizard.mode == MODE_WIZARD:
        show_card(wizard)
        step = wizard.step
        assert step is not None
        raw = input("\n> ").strip()
        if raw in {"q", "quit", "exit"}:
            return
        if raw in {"b", "back"}:
            wizard.back()
            continue
        if step.kind == "text":
            result = wizard.answer_text(step.id, raw)
        else:
            try:
                index = int(raw) - 1
                key = step.options[index].key
            except (ValueError, IndexError):
                print("شمارهٔ گزینه را وارد کنید (یا b برای بازگشت، q برای خروج).")
                continue
            if step.kind == "choice":
                result = wizard.answer_choice(step.id, key)
            else:
                wizard.toggle_multi(step.id, key)
                confirm = input("گزینهٔ دیگری هست؟ Enter برای ادامه، شماره برای انتخاب بیشتر: ").strip()
                while confirm:
                    try:
                        wizard.toggle_multi(step.id, step.options[int(confirm) - 1].key)
                    except (ValueError, IndexError):
                        pass
                    confirm = input("...: ").strip()
                result = wizard.confirm_multi(step.id)
        if not result.ok:
            print(f"\n!! {result.error}")
    show_card(wizard)
    print("\n" + plain(render.submitted("BZX-14050512-DEMO")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview the Bizynex intake wizard offline.")
    parser.add_argument(
        "--auto",
        nargs="?",
        const="website",
        choices=[option.key for option in SERVICE_OPTIONS],
        help="auto-play a single branch",
    )
    args = parser.parse_args()
    if args.auto:
        auto(args.auto)
    else:
        interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
