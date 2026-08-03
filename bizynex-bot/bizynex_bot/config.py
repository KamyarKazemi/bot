"""Runtime configuration. Everything comes from the environment or a local .env file.

No secrets ever live in the source tree. No external services are contacted except
the Telegram Bot API (optionally through a proxy).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MODE_POLLING = "polling"
MODE_WEBHOOK = "webhook"


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader. Avoids a python-dotenv dependency on purpose."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Real environment variables always win over the file.
        os.environ.setdefault(key, value)


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise ValueError(
                f"ADMIN_CHAT_IDS contains a non-numeric value: {part!r}. "
                "Use numeric Telegram IDs (send /id to the bot to find yours)."
            )
    return ids


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_chat_ids: list[int] = field(default_factory=list)
    proxy_url: str | None = None
    db_path: Path = BASE_DIR / "data" / "leads.db"
    persistence_path: Path = BASE_DIR / "data" / "state.pickle"
    log_level: str = "INFO"
    company_name: str = "Bizynex"
    support_handle: str = ""  # e.g. "@bizynex_support" — shown in the closing message
    # Delivery mode: long polling locally, webhook when hosted (Render, a VPS, …).
    mode: str = MODE_POLLING
    port: int = 10000
    webhook_base_url: str = ""
    webhook_secret: str = ""
    startup_ping: bool = True

    @property
    def has_admins(self) -> bool:
        return bool(self.admin_chat_ids)

    @property
    def webhook_path(self) -> str:
        """Secret-ish URL path derived from the token.

        The raw token never appears in the URL: URLs end up in proxy logs, browser
        history and screenshots, and a leaked token means a hijacked bot.
        """
        return hashlib.sha256(self.bot_token.encode()).hexdigest()[:32]

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url.rstrip('/')}/{self.webhook_path}"


def load_config(*, use_dotenv: bool = True) -> Config:
    # Tests pass use_dotenv=False so they never pick up the developer's real .env.
    if use_dotenv:
        _load_dotenv(BASE_DIR / ".env")

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "BOT_TOKEN is not set.\n"
            "Copy .env.example to .env and paste the token you got from @BotFather."
        )

    admin_raw = os.environ.get("ADMIN_CHAT_IDS", os.environ.get("ADMIN_CHAT_ID", "")).strip()
    admin_ids = _parse_admin_ids(admin_raw)

    proxy = os.environ.get("PROXY_URL", "").strip() or None

    db_path = Path(os.environ.get("DB_PATH", str(BASE_DIR / "data" / "leads.db")))
    state_path = Path(os.environ.get("STATE_PATH", str(BASE_DIR / "data" / "state.pickle")))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Render sets RENDER_EXTERNAL_URL automatically; any other host can set WEBHOOK_URL.
    base_url = (
        os.environ.get("WEBHOOK_URL", "").strip()
        or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    )
    mode = os.environ.get("MODE", "").strip().lower()
    if mode not in {MODE_POLLING, MODE_WEBHOOK}:
        # A public URL means the platform expects an HTTP server, so webhook it is.
        mode = MODE_WEBHOOK if base_url else MODE_POLLING
    if mode == MODE_WEBHOOK and not base_url:
        raise SystemExit(
            "MODE=webhook needs a public address. Set WEBHOOK_URL (for example "
            "https://bizynex-bot.onrender.com), or use MODE=polling."
        )

    secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    if not secret:
        # Deterministic so a restart does not invalidate the registered webhook.
        secret = hashlib.sha256(f"{token}:bizynex-webhook".encode()).hexdigest()[:48]

    return Config(
        bot_token=token,
        admin_chat_ids=admin_ids,
        proxy_url=proxy,
        db_path=db_path,
        persistence_path=state_path,
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        support_handle=os.environ.get("SUPPORT_HANDLE", "").strip(),
        mode=mode,
        port=int(os.environ.get("PORT", "10000")),
        webhook_base_url=base_url,
        webhook_secret=secret,
        # A free host restarts often; a "bot is up" DM on every wake-up is noise.
        startup_ping=_bool(os.environ.get("STARTUP_PING"), mode == MODE_POLLING),
    )
