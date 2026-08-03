"""Configuration and deployment-mode tests.

Verifies the polling/webhook decision, the derived webhook URL, and the guards that
turn a misconfiguration into a clear message instead of a silent dead bot.

    python tests/test_config.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bizynex_bot.config import MODE_POLLING, MODE_WEBHOOK, load_config

TOKEN = "123456:AAHfakefakefakefakefakefakefakefake"

MANAGED_KEYS = (
    "BOT_TOKEN", "ADMIN_CHAT_IDS", "ADMIN_CHAT_ID", "PROXY_URL", "MODE", "PORT",
    "WEBHOOK_URL", "RENDER_EXTERNAL_URL", "WEBHOOK_SECRET", "STARTUP_PING",
    "DB_PATH", "STATE_PATH", "LOG_LEVEL", "SUPPORT_HANDLE",
)


@contextmanager
def env(**overrides: str):
    """Run with a clean, controlled environment and a throwaway data directory."""
    saved = {key: os.environ.pop(key, None) for key in MANAGED_KEYS}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DB_PATH"] = str(Path(tmp) / "leads.db")
        os.environ["STATE_PATH"] = str(Path(tmp) / "state.pickle")
        os.environ.update({k: v for k, v in overrides.items() if v is not None})
        try:
            yield
        finally:
            for key in MANAGED_KEYS:
                os.environ.pop(key, None)
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value


def test_defaults_to_polling() -> None:
    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS="42"):
        config = load_config(use_dotenv=False)
    assert config.mode == MODE_POLLING
    assert config.admin_chat_ids == [42]
    assert config.startup_ping is True, "a local run should announce itself"
    assert config.proxy_url is None


def test_render_url_switches_to_webhook() -> None:
    with env(
        BOT_TOKEN=TOKEN,
        ADMIN_CHAT_IDS="42",
        RENDER_EXTERNAL_URL="https://bizynex-bot.onrender.com",
        PORT="10000",
    ):
        config = load_config(use_dotenv=False)
    assert config.mode == MODE_WEBHOOK
    assert config.port == 10000
    assert config.webhook_url.startswith("https://bizynex-bot.onrender.com/")
    assert TOKEN not in config.webhook_url, "the token must never appear in the URL"
    assert len(config.webhook_path) == 32
    assert config.startup_ping is False, "a free host restarts often; no DM per restart"


def test_webhook_values_are_stable_across_restarts() -> None:
    with env(BOT_TOKEN=TOKEN, WEBHOOK_URL="https://example.com/"):
        first = load_config(use_dotenv=False)
    with env(BOT_TOKEN=TOKEN, WEBHOOK_URL="https://example.com"):
        second = load_config(use_dotenv=False)
    assert first.webhook_url == second.webhook_url
    assert first.webhook_secret == second.webhook_secret
    assert 1 <= len(first.webhook_secret) <= 256


def test_explicit_mode_wins() -> None:
    with env(BOT_TOKEN=TOKEN, MODE="polling", RENDER_EXTERNAL_URL="https://x.onrender.com"):
        assert load_config(use_dotenv=False).mode == MODE_POLLING
    with env(BOT_TOKEN=TOKEN, MODE="webhook", WEBHOOK_URL="https://x.onrender.com"):
        assert load_config(use_dotenv=False).mode == MODE_WEBHOOK


def test_webhook_without_url_fails_loudly() -> None:
    with env(BOT_TOKEN=TOKEN, MODE="webhook"):
        try:
            load_config(use_dotenv=False)
        except SystemExit as exc:
            assert "WEBHOOK_URL" in str(exc)
        else:
            raise AssertionError("MODE=webhook with no address should stop the bot")


def test_missing_token_fails_loudly() -> None:
    with env():
        try:
            load_config(use_dotenv=False)
        except SystemExit as exc:
            assert "BOT_TOKEN" in str(exc)
        else:
            raise AssertionError("a missing token should stop the bot")


def test_admin_ids_parsing() -> None:
    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS=" 11, 22 ;33 "):
        assert load_config(use_dotenv=False).admin_chat_ids == [11, 22, 33]
    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_ID="99"):  # singular spelling also works
        assert load_config(use_dotenv=False).admin_chat_ids == [99]
    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS="@kamyar"):
        try:
            load_config(use_dotenv=False)
        except ValueError as exc:
            assert "numeric" in str(exc)
        else:
            raise AssertionError("a @username in ADMIN_CHAT_IDS should be rejected")


def test_startup_ping_override() -> None:
    with env(BOT_TOKEN=TOKEN, WEBHOOK_URL="https://x.onrender.com", STARTUP_PING="true"):
        assert load_config(use_dotenv=False).startup_ping is True


def test_application_builds_in_webhook_mode() -> None:
    import main

    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS="42", RENDER_EXTERNAL_URL="https://x.onrender.com"):
        config = load_config(use_dotenv=False)
        application = main.build_application(config)
    assert application.bot_data["config"].mode == MODE_WEBHOOK
    assert application.handlers, "handlers were not registered"


def test_persistence_never_stores_bot_data() -> None:
    """Regression: persistence replaces bot_data at startup and wiped config + store."""
    import main

    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS="42"):
        application = main.build_application(load_config(use_dotenv=False))
    store_data = application.persistence.store_data
    assert store_data.bot_data is False, "bot_data persistence would wipe config at startup"
    assert store_data.user_data is True, "half-finished wizards must survive a restart"


def test_context_is_reinjected_after_a_wipe() -> None:
    import main
    from bizynex_bot import handlers

    with env(BOT_TOKEN=TOKEN, ADMIN_CHAT_IDS="42"):
        config = load_config(use_dotenv=False)
        application = main.build_application(config)
        assert application.bot_data["config"] is config

        # Exactly what PTB does to bot_data while initialising with persistence.
        application.bot_data.clear()
        handlers.inject_context(application, config, application.bot_data.get("store") or
                                main.LeadStore(config.db_path))

    assert application.bot_data["config"] is config
    assert application.bot_data["store"] is not None


def main_() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main_())
