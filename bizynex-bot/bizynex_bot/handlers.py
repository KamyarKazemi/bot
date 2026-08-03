"""Telegram handlers — the thin layer between the engine and the Bot API.

UI model: the wizard lives in ONE message that is edited in place. The chat never
fills up with dead question cards, and there is exactly one live keyboard at any
moment. Clicks on older keyboards are detected and rejected.
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import BotCommand, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import keyboards as kb
from . import render
from .config import Config
from .engine import MODE_EDIT, MODE_REVIEW, MODE_WIZARD, Wizard, new_state
from .localization import format_jalali, to_persian_digits
from .storage import LeadStore

log = logging.getLogger(__name__)

KEY_STATE = "wizard_state"
KEY_MSG = "wizard_message_id"
KEY_TICKET = "last_ticket"
KEY_BUSY = "submitting"


# ---------------------------------------------------------------- utilities
def _config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["config"]


def _store(context: ContextTypes.DEFAULT_TYPE) -> LeadStore:
    return context.application.bot_data["store"]


def _user_dict(update: Update) -> dict[str, Any]:
    user = update.effective_user
    if user is None:
        return {"id": 0, "full_name": "—", "username": None}
    return {"id": user.id, "full_name": user.full_name, "username": user.username}


def _wizard(context: ContextTypes.DEFAULT_TYPE) -> Wizard | None:
    state = context.user_data.get(KEY_STATE)
    return Wizard(state) if state else None


async def _show(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    force_new: bool = False,
) -> None:
    """Edit the live card if we can, otherwise send a fresh one."""
    chat = update.effective_chat
    if chat is None:
        return
    message_id = context.user_data.get(KEY_MSG)

    if message_id and not force_new:
        try:
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=message_id,
                text=text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        except BadRequest as exc:
            # Identical content is not an error worth surfacing.
            if "not modified" in str(exc).lower():
                return
            log.debug("edit failed, sending a new card: %s", exc)

    sent = await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    context.user_data[KEY_MSG] = sent.message_id


async def _render_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Draw whatever the wizard currently is: a question, the review, or the edit menu."""
    wizard = _wizard(context)
    if wizard is None:
        await _show(update, context, render.no_session(), kb.welcome_keyboard())
        return

    if wizard.mode == MODE_REVIEW:
        await _show(update, context, render.review(wizard), kb.review_keyboard())
        return

    if wizard.step is None:
        wizard.mode = MODE_REVIEW
        await _show(update, context, render.review(wizard), kb.review_keyboard())
        return

    await _show(update, context, render.question(wizard), kb.question_keyboard(wizard))


# ----------------------------------------------------------------- commands
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    wizard = _wizard(context)
    resume = wizard is not None and not (wizard.mode == MODE_REVIEW and wizard.is_complete()) \
        and bool(wizard.answers)
    context.user_data[KEY_MSG] = None  # start a fresh card for a fresh /start
    await _show(
        update,
        context,
        render.welcome(update.effective_user.first_name if update.effective_user else None),
        kb.welcome_keyboard(resume=resume),
        force_new=True,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(render.help_text())


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(KEY_STATE, None)
    context.user_data[KEY_MSG] = None
    await update.effective_message.reply_html(render.cancelled())


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lets the founders find the chat id to put in ADMIN_CHAT_IDS."""
    chat = update.effective_chat
    await update.effective_message.reply_html(
        "شناسهٔ عددی این گفت‌وگو:\n"
        f"<code>{chat.id}</code>\n\n"
        "<i>این عدد را در فایل .env مقابل ADMIN_CHAT_IDS قرار دهید.</i>"
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = _config(context)
    user = update.effective_user
    if user is None or user.id not in config.admin_chat_ids:
        return  # silent for non-admins: the command simply does not exist for them
    stats = _store(context).stats()
    lines = [
        "<b>آمار درخواست‌ها</b>",
        f"{render.DOT} امروز: {to_persian_digits(stats['today'])}",
        f"{render.DOT} مجموع: {to_persian_digits(stats['total'])}",
        f"{render.DOT} ارسال‌نشده: {to_persian_digits(stats['pending'])}",
        "",
        f"<i>{format_jalali()}</i>",
    ]
    breakdown = _store(context).by_service()
    if breakdown:
        lines.append("")
        lines.append("<b>به تفکیک خدمت</b>")
        from .flow import STEPS_BY_ID

        service_step = STEPS_BY_ID["service"]
        for key, count in breakdown:
            lines.append(f"{render.DOT} {service_step.option_label(key)}: {to_persian_digits(count)}")
    await update.effective_message.reply_html("\n".join(lines))


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-send leads that could not be delivered when they were submitted."""
    config = _config(context)
    user = update.effective_user
    if user is None or user.id not in config.admin_chat_ids:
        return
    store = _store(context)
    rows = store.undelivered()
    if not rows:
        await update.effective_message.reply_html("درخواست ارسال‌نشده‌ای وجود ندارد.")
        return
    sent = 0
    for row in rows:
        text = (
            f"<b>درخواست بازارسال‌شده {render.DOT} {row['ticket']}</b>\n"
            f"<i>{row['created_at']}</i>\n\n"
            f"<code>{render.esc(row['answers_json'])}</code>"
        )
        try:
            await context.bot.send_message(user.id, text, parse_mode=ParseMode.HTML)
            store.mark_delivered(row["ticket"])
            sent += 1
        except TelegramError as exc:
            log.warning("resend failed for %s: %s", row["ticket"], exc)
    await update.effective_message.reply_html(
        f"{to_persian_digits(sent)} درخواست بازارسال شد."
    )


# ------------------------------------------------------------ callback query
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    action, step_id, payload = kb.parse_cb(query.data)
    if not action:
        await query.answer()
        return

    # The card the button belongs to must be the live card.
    if query.message and context.user_data.get(KEY_MSG) not in (None, query.message.message_id):
        context.user_data[KEY_MSG] = query.message.message_id

    if action == kb.ACT_NOOP:
        await query.answer()
        return

    if action == kb.ACT_ABOUT:
        await query.answer()
        await _show(update, context, render.about(), kb.info_keyboard())
        return

    if action == kb.ACT_SERVICES:
        await query.answer()
        await _show(update, context, render.services(), kb.info_keyboard())
        return

    if action == kb.ACT_RESTART:
        await query.answer()
        wizard = _wizard(context)
        resume = wizard is not None and bool(wizard.answers) and wizard.mode != MODE_REVIEW
        await _show(
            update,
            context,
            render.welcome(update.effective_user.first_name if update.effective_user else None),
            kb.welcome_keyboard(resume=resume),
        )
        return

    if action == kb.ACT_START:
        await query.answer()
        context.user_data[KEY_STATE] = new_state()
        await _render_state(update, context)
        return

    if action == kb.ACT_RESUME:
        await query.answer()
        if _wizard(context) is None:
            context.user_data[KEY_STATE] = new_state()
        await _render_state(update, context)
        return

    if action == kb.ACT_CANCEL:
        await query.answer()
        context.user_data.pop(KEY_STATE, None)
        await _show(update, context, render.cancelled(), kb.done_keyboard())
        return

    wizard = _wizard(context)
    if wizard is None:
        await query.answer()
        await _show(update, context, render.no_session(), kb.welcome_keyboard())
        return

    # Answer actions must refer to the question actually on screen.
    if action in {kb.ACT_PICK, kb.ACT_TOGGLE, kb.ACT_CONFIRM, kb.ACT_SKIP}:
        current = wizard.step
        if current is None or current.id != step_id:
            await query.answer(render.stale_click(), show_alert=True)
            await _render_state(update, context)
            return

    if action == kb.ACT_PICK:
        result = wizard.answer_choice(step_id, payload)
        await query.answer("" if result.ok else result.error, show_alert=not result.ok)
        await _render_state(update, context)
        return

    if action == kb.ACT_TOGGLE:
        result = wizard.toggle_multi(step_id, payload)
        await query.answer("" if result.ok else result.error, show_alert=not result.ok)
        await _render_state(update, context)
        return

    if action == kb.ACT_CONFIRM:
        result = wizard.confirm_multi(step_id)
        if not result.ok:
            await query.answer(result.error, show_alert=True)
            return
        await query.answer()
        await _render_state(update, context)
        return

    if action == kb.ACT_SKIP:
        result = wizard.skip(step_id)
        await query.answer("" if result.ok else result.error, show_alert=not result.ok)
        await _render_state(update, context)
        return

    if action == kb.ACT_BACK:
        await query.answer()
        if not wizard.back():
            # Already at the first question — go back to the welcome card.
            await _show(
                update,
                context,
                render.welcome(update.effective_user.first_name if update.effective_user else None),
                kb.welcome_keyboard(resume=bool(wizard.answers)),
            )
            return
        await _render_state(update, context)
        return

    if action == kb.ACT_EDIT_MENU:
        await query.answer()
        await _show(update, context, render.edit_menu(), kb.edit_menu_keyboard(wizard))
        return

    if action == kb.ACT_EDIT_GOTO:
        await query.answer()
        if not wizard.goto(step_id, mode=MODE_EDIT):
            await _render_state(update, context)
            return
        await _render_state(update, context)
        return

    if action == kb.ACT_SUBMIT:
        await _submit(update, context, wizard)
        return

    await query.answer()


# ------------------------------------------------------------------- submit
async def _submit(update: Update, context: ContextTypes.DEFAULT_TYPE, wizard: Wizard) -> None:
    query = update.callback_query
    if context.user_data.get(KEY_BUSY):
        if query:
            await query.answer("در حال ارسال است؛ لطفاً چند لحظه صبر کنید.")
        return

    missing = wizard.missing()
    if missing:
        if query:
            await query.answer("چند پرسش بی‌پاسخ مانده است.", show_alert=True)
        wizard.goto(missing[0].id, mode=MODE_WIZARD)
        await _render_state(update, context)
        return

    context.user_data[KEY_BUSY] = True
    if query:
        await query.answer()
    try:
        config = _config(context)
        store = _store(context)
        user = _user_dict(update)
        ticket = store.new_ticket()
        card = render.admin_card(wizard, ticket=ticket, user=user)

        delivered = False
        for admin_id in config.admin_chat_ids:
            try:
                await context.bot.send_message(
                    admin_id, card, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
                delivered = True
            except Forbidden:
                log.error(
                    "admin %s has not started the bot — they must send /start to it once",
                    admin_id,
                )
            except TelegramError as exc:
                log.error("could not deliver lead %s to %s: %s", ticket, admin_id, exc)

        # Persist regardless: the lead is never lost because a message failed.
        store.save_lead(ticket=ticket, user=user, answers=wizard.answers, delivered=delivered)

        if not delivered and config.has_admins:
            await _show(update, context, render.submit_failed(), kb.retry_submit_keyboard())
            return

        context.user_data[KEY_TICKET] = ticket
        context.user_data.pop(KEY_STATE, None)
        await _show(update, context, render.submitted(ticket), kb.done_keyboard())
    finally:
        context.user_data[KEY_BUSY] = False


# --------------------------------------------------------------- text input
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    raw = message.text

    wizard = _wizard(context)

    # Not in a wizard, but they already submitted: treat it as a note on that ticket.
    if wizard is None:
        ticket = context.user_data.get(KEY_TICKET)
        if ticket:
            await _handle_followup(update, context, ticket, raw)
            return
        await message.reply_html(render.no_session(), reply_markup=kb.welcome_keyboard())
        return

    step = wizard.step
    if wizard.mode == MODE_REVIEW or step is None:
        await message.reply_html(render.unexpected_text())
        return

    if step.kind != "text":
        await message.reply_html(render.unexpected_text())
        return

    result = wizard.answer_text(step.id, raw)

    # Keep the chat to a single card: remove the user's raw input if we may.
    try:
        await message.delete()
    except TelegramError:
        pass

    if not result.ok:
        await _show(
            update,
            context,
            render.question(wizard) + "\n\n" + render.validation_error(result.error),
            kb.question_keyboard(wizard),
        )
        return

    await _render_state(update, context)


async def _handle_followup(
    update: Update, context: ContextTypes.DEFAULT_TYPE, ticket: str, text: str
) -> None:
    config = _config(context)
    store = _store(context)
    user = _user_dict(update)
    store.save_followup(ticket=ticket, user_id=user["id"], body=text)
    for admin_id in config.admin_chat_ids:
        try:
            await context.bot.send_message(
                admin_id,
                render.admin_followup(ticket, user, text),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except TelegramError as exc:
            log.warning("follow-up delivery failed: %s", exc)
    await update.effective_message.reply_html(render.followup_ack())


async def on_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Photos, files, voice notes — accepted politely, never silently swallowed."""
    message = update.effective_message
    if message is None:
        return
    ticket = context.user_data.get(KEY_TICKET)
    if ticket:
        config = _config(context)
        for admin_id in config.admin_chat_ids:
            try:
                await message.forward(admin_id)
                await context.bot.send_message(
                    admin_id,
                    f"<i>فایل بالا مربوط به درخواست {render.esc(ticket)} است.</i>",
                    parse_mode=ParseMode.HTML,
                )
            except TelegramError as exc:
                log.warning("attachment forward failed: %s", exc)
        await message.reply_html(render.followup_ack())
        return
    await message.reply_html(
        "فعلاً فقط پاسخ متنی لازم است.\n"
        "<i>فایل‌ها را بعد از ثبت درخواست می‌توانید بفرستید.</i>"
    )


# ------------------------------------------------------------ error handling
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("unhandled error while processing update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                render.error_notice(),
                parse_mode=ParseMode.HTML,
                reply_markup=kb.done_keyboard(),
            )
        except TelegramError:
            pass


# ------------------------------------------------------------------ wiring
def inject_context(application: Application, config: Config, store: LeadStore) -> None:
    """Put config and storage into bot_data.

    Called twice on purpose: once at build time, and again from post_init. Persistence
    REPLACES bot_data while the application initialises, so anything written before
    that point is gone by the time handlers run.
    """
    application.bot_data["config"] = config
    application.bot_data["store"] = store


def build_post_init(config: Config, store: LeadStore):
    """post_init needs config, but only receives the application — so close over it."""

    async def post_init(application: Application) -> None:
        inject_context(application, config, store)
        await _post_init(application)

    return post_init


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "شروع گفت‌وگو"),
        BotCommand("help", "راهنما"),
        BotCommand("cancel", "لغو درخواست فعلی"),
        BotCommand("id", "نمایش شناسهٔ عددی این گفت‌وگو"),
    ])
    config: Config = application.bot_data["config"]
    me = await application.bot.get_me()
    log.info("connected as @%s (%s) in %s mode", me.username, me.id, config.mode)
    if not config.has_admins:
        log.warning(
            "ADMIN_CHAT_IDS is empty — leads will only be stored in %s", config.db_path
        )
        return
    if not config.startup_ping:
        # On a free host the process restarts often; a DM per restart is just noise.
        return
    for admin_id in config.admin_chat_ids:
        try:
            await application.bot.send_message(
                admin_id,
                f"<b>ربات {render.BRAND} فعال شد.</b>\n<i>{format_jalali()}</i>",
                parse_mode=ParseMode.HTML,
            )
        except Forbidden:
            log.warning("admin %s must send /start to the bot once to receive leads", admin_id)
        except TelegramError as exc:
            log.warning("startup ping to %s failed: %s", admin_id, exc)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("cancel", cmd_cancel))
    application.add_handler(CommandHandler("id", cmd_id))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("pending", cmd_pending))
    application.add_handler(CallbackQueryHandler(on_callback, pattern=r"^bx\|"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL | filters.VOICE | filters.VIDEO,
            on_non_text,
        )
    )
    application.add_error_handler(on_error)
