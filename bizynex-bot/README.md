# Bizynex — ربات ویزارد دریافت درخواست

A Persian, RTL-native Telegram intake wizard for Bizynex. It asks a prospect what
they need, branches by service, validates every answer, shows a reviewable summary,
and sends the finished request straight to your Telegram as a formatted card.

Built on **python-telegram-bot 21.9** (no aiogram). No database server, no hosting
requirement, no external service — long polling from a laptop is a valid deployment.

---

## Setup (Windows, 5 minutes)

**1 — Create the bot**

Open Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, follow the
prompts, copy the token it gives you.

**2 — Install**

```powershell
cd C:\mydesk\Desktop\bot\bizynex-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**3 — Configure**

```powershell
copy .env.example .env
notepad .env
```

Paste your token into `BOT_TOKEN`.

**4 — Find your Telegram ID**

Run the bot once (`python main.py`), open your bot in Telegram, press **Start**, then
send `/id`. Put the number it replies with into `ADMIN_CHAT_IDS` in `.env`, then restart.

> Each founder listed in `ADMIN_CHAT_IDS` must press **Start** in the bot at least once.
> Telegram refuses to deliver messages to users who never started a conversation with it.

**5 — Run**

```powershell
python main.py
```

### Running from inside Iran

Telegram's API is filtered. Set `PROXY_URL` in `.env` and both the API calls and the
update polling go through it:

```
PROXY_URL=socks5://127.0.0.1:1080
```

HTTP proxies (`http://…`) and authenticated proxies (`socks5://user:pass@host:port`) work too.
If the server hosting the bot has unrestricted access, leave `PROXY_URL` empty.

---

## Preview without running the bot

```powershell
python simulate.py --auto website   # auto-play a branch, print every card
python simulate.py                  # answer the questions yourself in the terminal
```

Useful for reviewing copy before it ever reaches a customer.

## Deploying

See **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** for a step-by-step deploy to Render's free
tier (GitHub → web service → webhook mode → verification → troubleshooting).

The bot picks its own delivery mode:

| Where | Mode | How |
|---|---|---|
| Your laptop, a VPS | polling | default; no public address needed |
| Render, or any host with a domain | webhook | automatic when `RENDER_EXTERNAL_URL` or `WEBHOOK_URL` is set |

Pending updates are never dropped, so a request sent while the bot was restarting or
asleep is still answered — Telegram holds updates for 24 hours.

## Tests

```powershell
python tests\test_engine.py
python tests\test_config.py
```

Walks all six service branches with three different answer sets each, checks that
every path terminates, that branch switching prunes stale answers, that back/edit/skip
behave, that no callback payload exceeds Telegram's 64-byte limit, and round-trips
40,177 days through the Jalali converter.

---

## Commands

| Command | Who | What |
|---|---|---|
| `/start` | everyone | Welcome card; starts or resumes the wizard |
| `/help` | everyone | How the wizard works |
| `/cancel` | everyone | Discards the in-progress request |
| `/id` | everyone | Shows the numeric chat id (for `ADMIN_CHAT_IDS`) |
| `/stats` | admins | Requests today / total / undelivered, broken down by service |
| `/pending` | admins | Re-sends any lead that failed to deliver |

Non-admins get no response to `/stats` and `/pending` — the commands simply do not
exist for them.

---

## How it behaves

- **One live card.** The wizard edits a single message instead of flooding the chat.
  Text answers the customer types are deleted after being recorded, so the conversation
  stays clean.
- **Stale buttons are rejected.** Every button carries its step id; a click on an old
  keyboard raises an alert instead of corrupting the answer set.
- **Nothing is lost.** In-progress wizards survive a restart (`data/state.pickle`), and
  every submitted lead is written to SQLite (`data/leads.db`) even if the Telegram
  delivery fails — `/pending` re-sends those.
- **Branch switching is clean.** Change your mind about the service and the answers from
  the abandoned branch are pruned, not silently carried along.
- **Review before send.** The customer sees every answer and can edit any of them before
  submitting. After submitting, anything else they type is attached to the same ticket.
- **Persian throughout.** Persian numerals, Jalali dates, ZWNJ half-spaces, RTL-safe
  formatting. Phone numbers are stored canonically (`09121234567`) but shown to the
  customer in Persian digits.

Ticket format: `BZX-14050512-K7QF` — Jalali date plus a 4-character code with no
look-alike characters.

---

## Editing the questions

Everything the bot asks lives in **`bizynex_bot/flow.py`**. Add, remove or reorder a
`Step` and the keyboards, progress counter, review card, admin card and storage all
follow automatically. Nothing else needs to change.

```python
Step(
    id="w_hosting",                    # unique, short (it travels in callback data)
    kind="choice",                     # "choice" | "multi" | "text"
    section="وب‌سایت",                  # groups the answer in the summary
    title="میزبانی سایت را خودتان تأمین می‌کنید؟",
    help="اگر نمی‌دانید، گزینهٔ آخر را بزنید.",
    options=(Option("yes", "بله"), Option("no", "خیر"), Option("unknown", "نمی‌دانم")),
    summary_label="میزبانی",
    show_if=service_is("website"),     # omit to ask everyone
)
```

For text steps set `validator` to one of `free_text`, `short_text`, `name`, `phone`,
`email`, `url` (defined in `validators.py`), and `optional=True` to allow skipping.

**Review `BUDGET_OPTIONS` in `flow.py` every quarter.** Fixed Toman ranges age fast, and
stale numbers make us look out of touch — which is the opposite of what this bot is for.

---

## File map

```
main.py                  entry point, polling/webhook + proxy + persistence wiring
simulate.py              offline preview of the conversation
render.yaml              Render blueprint (optional one-click service creation)
DEPLOY_RENDER.md         step-by-step deployment guide
CONTEXT.md               the Bizynex context this bot was designed against
bizynex_bot/
  flow.py                every question — the only file you normally edit
  engine.py              navigation, branching, pruning (no Telegram imports)
  handlers.py            Telegram glue: callbacks, text input, submit, errors
  keyboards.py           inline keyboards + callback-data protocol
  render.py              every Persian string the user sees
  validators.py          phone / email / name / text validation
  storage.py             SQLite leads + follow-ups + tickets
  localization.py        Persian digits, Jalali calendar, Iran time
  config.py              .env loading
tests/test_engine.py     headless verification of all branches
data/                    leads.db + state.pickle (created on first run, git-ignored)
```

---

## Keeping it running

**Windows** — Task Scheduler, "run whether user is logged on or not", action
`C:\mydesk\Desktop\bot\bizynex-bot\.venv\Scripts\python.exe main.py` with the folder as
the working directory.

**Linux server** — a systemd unit with `Restart=always`.

Back up `data/leads.db`; it is the only irreplaceable file. `data/state.pickle` holds
only half-finished conversations and can be deleted safely.

## Privacy

The bot collects name, phone, business name and the answers above — nothing more. It
never asks for national ID, bank details or payment. Data stays in `data/leads.db` on
your machine and in your Telegram chat. Nothing is sent anywhere else.
