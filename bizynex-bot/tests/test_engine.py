"""Headless verification of the whole wizard.

Runs without a network connection and without a bot token:

    python tests/test_engine.py        # plain run, prints a report
    pytest tests/test_engine.py        # also works if pytest is installed

Every service branch is walked end to end, every button's callback payload is
checked against Telegram's 64-byte limit, and the navigation invariants (back,
edit, prune, skip) are asserted.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bizynex_bot.engine import MODE_EDIT, MODE_REVIEW, MODE_WIZARD, Wizard, new_state
from bizynex_bot.flow import FLOW, SERVICE_OPTIONS, STEPS_BY_ID, visible_steps
from bizynex_bot.localization import (
    format_jalali,
    gregorian_to_jalali,
    jalali_to_gregorian,
    to_ascii_digits,
    to_persian_digits,
)
from bizynex_bot.validators import validate_email, validate_name, validate_phone

SAMPLE_TEXT = {
    "url": "bizynex.com",
    "name": "کامیار کاظمی",
    "phone": "۰۹۱۲۱۲۳۴۵۶۷",
    "email": "kamyar@example.com",
    "short_text": "نمونهٔ پاسخ کوتاه",
    "free_text": "می‌خواهیم تماس‌های ورودی از مشتریان صنعتی بیشتر شود.",
}


def answer_step(wizard: Wizard, step, *, pick_index: int = 0) -> None:
    if step.kind == "choice":
        result = wizard.answer_choice(step.id, step.options[pick_index].key)
    elif step.kind == "multi":
        wizard.toggle_multi(step.id, step.options[pick_index].key)
        result = wizard.confirm_multi(step.id)
    else:
        result = wizard.answer_text(step.id, SAMPLE_TEXT.get(step.validator, SAMPLE_TEXT["free_text"]))
    assert result.ok, f"step {step.id} rejected a valid answer: {result.error}"


def walk(service_key: str, *, pick_index: int = 0) -> Wizard:
    wizard = Wizard(new_state())
    guard = 0
    while wizard.mode == MODE_WIZARD:
        step = wizard.step
        assert step is not None, "wizard lost its cursor mid-run"
        if step.id == "service":
            wizard.answer_choice("service", service_key)
        else:
            answer_step(wizard, step, pick_index=min(pick_index, len(step.options) - 1) if step.options else 0)
        guard += 1
        assert guard < 60, f"the {service_key} branch does not terminate"
    return wizard


# --------------------------------------------------------------------- tests
def test_flow_integrity() -> None:
    ids = [step.id for step in FLOW]
    assert len(ids) == len(set(ids)), "duplicate step ids"
    for step in FLOW:
        assert step.kind in {"choice", "multi", "text"}, step.id
        if step.kind in {"choice", "multi"}:
            assert step.options, f"{step.id} has no options"
            keys = [option.key for option in step.options]
            assert len(keys) == len(set(keys)), f"duplicate option keys in {step.id}"
        else:
            assert not step.options, f"{step.id} is a text step but declares options"
        assert step.summary_label or step.title


def test_every_branch_completes() -> None:
    for option in SERVICE_OPTIONS:
        for pick in (0, 1, 99):  # first option, second option, last available option
            wizard = walk(option.key, pick_index=pick)
            assert wizard.mode == MODE_REVIEW, option.key
            assert wizard.is_complete(), f"{option.key} finished with gaps: {wizard.missing()}"
            path = wizard.path
            assert 8 <= len(path) <= 20, f"{option.key} path length looks wrong: {len(path)}"
            # Every answered key belongs to the visible path — no orphan data.
            assert set(wizard.answers) <= {step.id for step in path}


def test_callback_payloads_fit_telegram_limit() -> None:
    from bizynex_bot.keyboards import cb

    for step in FLOW:
        for option in step.options:
            for action in ("pk", "tg"):
                data = cb(action, step.id, option.key)
                assert len(data.encode()) <= 64, data
        for action in ("bk", "sk", "ok", "eg"):
            assert len(cb(action, step.id).encode()) <= 64


def test_branch_switch_prunes_answers() -> None:
    wizard = Wizard(new_state())
    wizard.answer_choice("service", "website")
    wizard.answer_choice("w_type", "shop")
    assert "w_type" in wizard.answers
    wizard.goto("service", mode=MODE_WIZARD)
    wizard.answer_choice("service", "graphic")
    assert "w_type" not in wizard.answers, "website answers survived a switch to graphic design"
    assert wizard.step is not None and wizard.step.id.startswith("g_")


def test_back_walks_the_whole_path() -> None:
    wizard = walk("automation")
    assert wizard.mode == MODE_REVIEW
    steps_back = 0
    while wizard.back():
        steps_back += 1
        assert steps_back < 60
    assert wizard.step is not None and wizard.step.id == "service"
    assert steps_back == len(wizard.path)


def test_edit_returns_to_review() -> None:
    wizard = walk("bot")
    assert wizard.goto("t_name", mode=MODE_EDIT)
    assert wizard.mode == MODE_EDIT
    result = wizard.answer_text("t_name", "سارا محمدی")
    assert result.ok and result.finished
    assert wizard.mode == MODE_REVIEW
    assert wizard.answers["t_name"] == "سارا محمدی"


def test_optional_step_can_be_skipped() -> None:
    wizard = Wizard(new_state())
    wizard.answer_choice("service", "consulting")
    while wizard.mode == MODE_WIZARD:
        step = wizard.step
        assert step is not None
        if step.optional:
            assert wizard.skip(step.id).ok
            continue
        answer_step(wizard, step)
    assert wizard.answers["t_notes"] == ""
    assert wizard.is_complete()


def test_multi_select_rules() -> None:
    wizard = Wizard(new_state())
    wizard.answer_choice("service", "website")
    wizard.goto("w_features", mode=MODE_WIZARD)
    assert not wizard.confirm_multi("w_features").ok, "empty multi-select was accepted"
    wizard.toggle_multi("w_features", "seo")
    wizard.toggle_multi("w_features", "payment")
    assert set(wizard.selection("w_features")) == {"seo", "payment"}
    wizard.toggle_multi("w_features", "none")  # mutually exclusive
    assert wizard.selection("w_features") == ["none"]
    wizard.toggle_multi("w_features", "seo")
    assert wizard.selection("w_features") == ["seo"]
    assert wizard.confirm_multi("w_features").ok
    assert wizard.answers["w_features"] == ["seo"]

    # Coming back to a multi-select prefills the previous answer instead of
    # making the user start over, and clicking a selected item removes it.
    wizard.goto("w_features", mode=MODE_WIZARD)
    assert wizard.selection("w_features") == ["seo"]
    wizard.toggle_multi("w_features", "blog")
    wizard.toggle_multi("w_features", "payment")
    wizard.toggle_multi("w_features", "seo")  # deselect
    wizard.confirm_multi("w_features")
    # Stored in declaration order regardless of click order.
    assert wizard.answers["w_features"] == ["payment", "blog"]


def test_conditional_steps() -> None:
    wizard = walk("website")
    # w_url only appears when the user says they already have a site.
    wizard.goto("w_status", mode=MODE_WIZARD)
    wizard.answer_choice("w_status", "none")
    assert "w_url" not in {step.id for step in wizard.path}
    wizard.goto("w_status", mode=MODE_WIZARD)
    wizard.answer_choice("w_status", "redesign")
    assert "w_url" in {step.id for step in wizard.path}

    # t_email only when the preferred channel is email.
    wizard2 = walk("consulting")
    wizard2.goto("t_channel", mode=MODE_WIZARD)
    wizard2.answer_choice("t_channel", "email")
    assert "t_email" in {step.id for step in wizard2.path}
    assert "t_time" not in {step.id for step in wizard2.path}
    wizard2.goto("t_channel", mode=MODE_WIZARD)
    wizard2.answer_choice("t_channel", "call")
    assert "t_email" not in wizard2.answers
    assert "t_time" in {step.id for step in wizard2.path}


def test_validators() -> None:
    for raw, expected in [
        ("۰۹۱۲۱۲۳۴۵۶۷", "09121234567"),
        ("0912 123 4567", "09121234567"),
        ("+989121234567", "09121234567"),
        ("00989121234567", "09121234567"),
        ("9121234567", "09121234567"),
        ("۰۲۱۲۲۳۳۴۴۵۵", "02122334455"),
        ("۰۹۱۲-۱۲۳-۴۵۶۷", "09121234567"),
    ]:
        ok, value = validate_phone(raw)
        assert ok and value == expected, (raw, value)

    for bad in ["123", "0912123456", "abcdefghijk", "۰۸۱۲۱۲۳۴۵۶۷۸۹۰"]:
        ok, _ = validate_phone(bad)
        assert not ok, bad

    assert validate_name("کامیار کاظمی")[0]
    assert not validate_name("ک")[0]
    assert not validate_name("کامیار ۱۲۳")[0]
    assert validate_email("a.b@example.co.ir")[0]
    assert not validate_email("a@b")[0]


def test_display_values_are_human_readable() -> None:
    wizard = walk("inventory")
    for step, _ in wizard.answered_steps():
        shown = wizard.display_value(step)
        assert shown and shown != "—", step.id
        if step.kind in {"choice", "multi"}:
            raw = wizard.answers[step.id]
            raw_keys = raw if isinstance(raw, list) else [raw]
            for key in raw_keys:
                assert key not in shown.split("، "), f"{step.id} shows a raw key"


def test_localization() -> None:
    assert to_persian_digits(1405) == "۱۴۰۵"
    assert to_ascii_digits("۰۹۱۲") == "0912"
    assert gregorian_to_jalali(2026, 8, 3) == (1405, 5, 12)
    assert jalali_to_gregorian(1405, 5, 12) == (2026, 8, 3)
    day = dt.date(1950, 1, 1)
    while day < dt.date(2060, 1, 1):
        jalali = gregorian_to_jalali(day.year, day.month, day.day)
        assert jalali_to_gregorian(*jalali) == (day.year, day.month, day.day), day
        day += dt.timedelta(days=1)
    assert "۱۴۰" in format_jalali()


def test_rendering_does_not_crash() -> None:
    from bizynex_bot import render

    for option in SERVICE_OPTIONS:
        wizard = walk(option.key)
        assert render.review(wizard)
        assert render.admin_card(
            wizard, ticket="BZX-14050512-TEST", user={"id": 1, "full_name": "تست", "username": "t"}
        )
    wizard = Wizard(new_state())
    assert render.question(wizard)
    assert render.welcome("کامیار") and render.about() and render.services() and render.help_text()


def test_storage_roundtrip() -> None:
    import tempfile

    from bizynex_bot.storage import LeadStore

    with tempfile.TemporaryDirectory() as tmp:
        store = LeadStore(Path(tmp) / "leads.db")
        wizard = walk("website")
        ticket = store.new_ticket()
        assert ticket.startswith("BZX-")
        user = {"id": 42, "full_name": "کامیار", "username": "kam"}
        store.save_lead(ticket=ticket, user=user, answers=wizard.answers, delivered=False)
        assert store.stats() == {"total": 1, "today": 1, "pending": 1}
        assert len(store.undelivered()) == 1
        store.mark_delivered(ticket)
        assert store.stats()["pending"] == 0
        store.save_lead(ticket=ticket, user=user, answers=wizard.answers, delivered=True)
        assert store.stats()["total"] == 1, "re-saving the same ticket duplicated the lead"
        store.save_followup(ticket=ticket, user_id=42, body="یک نکتهٔ تکمیلی")
        assert store.by_service()[0][0] == "website"
        assert store.new_ticket() != ticket


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report anything unexpected
            failures += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
