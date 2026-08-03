"""Entry point.

    python main.py

Two delivery modes, chosen automatically:

  polling  — the default. Works from a laptop or a VPS, no public address needed.
  webhook  — used when WEBHOOK_URL or RENDER_EXTERNAL_URL is set (i.e. on Render).
             Telegram pushes updates to us, which also means an incoming message
             wakes a sleeping free instance.

Pending updates are never dropped: Telegram keeps them for 24 hours, so a request
sent while the bot was asleep or redeploying still gets answered.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, PersistenceInput, PicklePersistence

from bizynex_bot import handlers
from bizynex_bot.config import MODE_WEBHOOK, Config, load_config
from bizynex_bot.storage import LeadStore

log = logging.getLogger(__name__)


def build_application(config: Config) -> Application:
    store = LeadStore(config.db_path)

    builder = ApplicationBuilder().token(config.bot_token)
    builder.persistence(
        PicklePersistence(
            filepath=config.persistence_path,
            # Only half-finished wizards are worth restoring. bot_data must stay OFF:
            # persistence replaces bot_data during startup, which would wipe the config
            # and storage handles the handlers depend on.
            store_data=PersistenceInput(
                bot_data=False, chat_data=False, user_data=True, callback_data=False
            ),
        )
    )
    builder.post_init(handlers.build_post_init(config, store))

    if config.proxy_url:
        # Telegram is filtered in Iran; both the API calls and getUpdates need the proxy.
        builder.proxy(config.proxy_url).get_updates_proxy(config.proxy_url)
        log.info("using proxy %s", config.proxy_url)

    # Generous timeouts: unstable connections are the norm, not the exception.
    builder.connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)

    application = builder.build()
    handlers.inject_context(application, config, store)
    handlers.register(application)
    return application


def run(application: Application, config: Config) -> None:
    if config.mode == MODE_WEBHOOK:
        log.info("webhook mode on port %s -> %s", config.port, config.webhook_url)
        application.run_webhook(
            listen="0.0.0.0",          # required by Render's port detection
            port=config.port,
            url_path=config.webhook_path,
            webhook_url=config.webhook_url,
            secret_token=config.webhook_secret,
            drop_pending_updates=False,
            allowed_updates=Update.ALL_TYPES,
        )
        return

    log.info("polling mode")
    application.run_polling(
        drop_pending_updates=False,
        allowed_updates=Update.ALL_TYPES,
    )


def main() -> None:
    config = load_config()
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
        level=getattr(logging, config.log_level, logging.INFO),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run(build_application(config), config)


if __name__ == "__main__":
    main()
