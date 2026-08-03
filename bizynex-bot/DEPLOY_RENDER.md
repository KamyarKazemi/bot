# Deploying to Render — step by step

Target: **free web service, webhook mode, no keep-alive ping.** Cost: $0.

Follow the parts in order. Every command is PowerShell, run from
`C:\mydesk\Desktop\bot\bizynex-bot`.

---

## Part 0 — Read this before you start

Three things you should know going in. None of them are blockers, but finding them
out later is worse.

**1. Render and Iran.** Render's terms require compliance with U.S. export law, and
U.S. sanctions broadly prohibit providing services to Iran. In practice: signing up
from an Iranian IP usually fails, so you will need a VPN for both signup and the
dashboard, and an account can be suspended without notice. Treat Render as
convenient, not permanent. Nothing in this bot is Render-specific — the same code
runs on any VPS or on a laptop with `MODE=polling`, so if the account ever goes away
you move it in ten minutes. Keep a copy of your `.env` values somewhere safe.

**2. The free instance sleeps.** After 15 minutes with no incoming traffic Render
suspends it. The next Telegram message wakes it, which takes about a minute. So the
first customer to message after a quiet period waits ~60 seconds for the first
reply; everything after that is instant until it goes idle again. This is why we use
**webhook** mode and not polling: an incoming message is what wakes the service. In
polling mode nothing would ever wake it and the bot would simply stay dead.

If that minute starts bothering you, add a free pinger later (cron-job.org hitting
your Render URL every 10 minutes). 750 free instance-hours per month is enough to
stay awake all month. You do not need it to start.

**3. The disk is wiped on every deploy and restart.** `data/leads.db` and
`data/state.pickle` do not survive. That is fine and expected — the lead card in your
Telegram is the real record, and it stays there forever. What you lose is `/stats`
history and `/pending` recovery beyond the current uptime, plus any half-finished
wizard when a deploy happens mid-conversation.

---

## Part 1 — Put the code on GitHub

Render deploys from a Git repository, so the code has to live on GitHub first.

**1.1 — Install Git** (skip if `git --version` already works)

Download from [git-scm.com](https://git-scm.com/download/win), accept the defaults.

**1.2 — Create an empty repo on GitHub**

Go to [github.com/new](https://github.com/new):

- Repository name: `bizynex-bot`
- Visibility: **Private** (this is business intake logic; there is no reason for it to be public)
- Do **not** tick "Add a README", "Add .gitignore" or "Choose a license" — the folder already has what it needs

Click **Create repository**. Leave the page open, you need the URL from it.

**1.3 — Initialise the repo locally**

```powershell
cd C:\mydesk\Desktop\bot\bizynex-bot
git init
git add .
git status
```

**Stop and read the `git status` output.** You should see `README.md`, `main.py`,
`bizynex_bot/`, `render.yaml` and friends. You must **not** see `.env` or anything
under `data/`. If you do, `.gitignore` is not being picked up — fix that before
committing, because a token pushed to GitHub is a compromised bot. (If it ever does
happen: `/revoke` in @BotFather, get a new token, update Render.)

```powershell
git commit -m "Bizynex intake wizard bot"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/bizynex-bot.git
git push -u origin main
```

Replace `YOUR-USERNAME`. GitHub will ask you to sign in — use the browser popup, or a
[personal access token](https://github.com/settings/tokens) as the password if it asks
for one at the command line.

Refresh the GitHub page. Your files should be there, and `.env` should not.

---

## Part 2 — Create the Render service

**2.1** Sign up at [render.com](https://render.com) with your GitHub account (VPN on,
see Part 0).

**2.2** In the dashboard: **New +** → **Web Service**.

**2.3** Connect your GitHub account when prompted, then pick the `bizynex-bot` repo.
If you made it private, grant Render access to that repository specifically.

**2.4** Fill in the form:

| Field | Value |
|---|---|
| Name | `bizynex-bot` (this becomes `bizynex-bot.onrender.com`) |
| Region | **Frankfurt** — the closest one to Iran |
| Branch | `main` |
| Root Directory | *leave empty* |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python main.py` |
| Instance Type | **Free** |

Leave **Health Check Path** empty. In webhook mode the only HTTP route belongs to
Telegram, so an HTTP health check would 404 and fail your deploys. With it empty
Render just checks that the port is bound, which is exactly right.

> Shortcut: the repo contains `render.yaml`, so you can instead use **New +** →
> **Blueprint**, point it at the repo, and Render fills all of the above in for you.
> It will still ask for the two secrets below.

---

## Part 3 — Environment variables

Still on the creation page, open **Advanced** → **Add Environment Variable**, and add:

| Key | Value |
|---|---|
| `BOT_TOKEN` | the token from @BotFather |
| `ADMIN_CHAT_IDS` | leave as `0` for now — Part 4 replaces it |
| `MODE` | `webhook` |
| `PYTHON_VERSION` | `3.12.7` |

Do **not** set `PROXY_URL`. Render reaches Telegram directly; a proxy there would only
break things. `PORT` and `RENDER_EXTERNAL_URL` are provided by Render automatically —
the bot reads them itself, so you never set them by hand.

Click **Create Web Service**. The first build takes 2–4 minutes.

Watch the log stream. You are looking for:

```
connected as @your_bot_name (123456789) in webhook mode
Your service is live 🎉
```

If instead you see `ADMIN_CHAT_IDS is empty` — that is expected right now, Part 4
fixes it.

---

## Part 4 — Point the leads at your Telegram

**4.1** Open your bot in Telegram (`t.me/your_bot_name`) and press **Start**.

If the service was asleep this first message takes about a minute. Be patient — that
is the cold start, not a bug.

**4.2** Send `/id`. The bot replies with a number. That is your Telegram ID.

**4.3** In Render: your service → **Environment** → edit `ADMIN_CHAT_IDS` → paste the
number → **Save Changes**. Render redeploys automatically (about a minute).

For more than one founder, comma-separate: `11111111,22222222`. **Each of them must
press Start in the bot at least once** — Telegram refuses to deliver messages to
people who have never opened a chat with it, and the log will say so if it happens.

**4.4** Send `/start` to the bot and complete one request end to end with fake
answers. The lead card should land in your Telegram within a second of pressing
«ارسال درخواست».

That is deployment done.

---

## Part 5 — Day to day

**Shipping a change.** Edit locally, then:

```powershell
git add .
git commit -m "what changed"
git push
```

Render redeploys on every push to `main`. Question changes in `flow.py` go live in
about two minutes.

**Logs.** Render dashboard → your service → **Logs**. Everything the bot does is
logged, including failed lead deliveries.

**Testing locally while the live bot runs.** Don't point both at the same token. A
webhook and local polling fight each other and Telegram returns errors. Make a second
bot with @BotFather (`bizynex_test_bot`), put that token in your local `.env`, and
leave the real one only on Render.

**Rolling back.** Render dashboard → **Events** → find the previous successful deploy
→ **Rollback**.

---

## Part 6 — When something is wrong

| Symptom | Cause | Fix |
|---|---|---|
| `RuntimeError: There is no current event loop` at startup | Python 3.14 with an old python-telegram-bot | `pip install -r requirements.txt` — 22.8 supports 3.14 |
| Deploy fails: "no open ports detected" | Started in polling mode, so nothing binds a port | Set `MODE=webhook` in Environment |
| Deploy fails on health check | A Health Check Path was configured | Clear it — Settings → Health Check Path → empty |
| Bot silent, logs show `Conflict: terminated by other getUpdates` | Another copy of the bot is running with the same token | Stop the local one, or use a separate test token |
| Bot silent, no logs at all | Service is asleep | Send it a message and wait ~60s; check Events for a crash |
| Requests complete but nothing reaches you | `ADMIN_CHAT_IDS` wrong, or that person never pressed Start | Re-check with `/id`; press Start; log says `admin … has not started the bot` |
| `Unauthorized` in logs at startup | Token wrong or revoked | Re-copy from @BotFather into Environment |
| Everything worked, now 500s after a deploy | Old Python cache or a bad commit | Manual Deploy → **Clear build cache & deploy**, or roll back |
| First reply takes a minute, every time | Free instance cold start | Expected. Add a cron-job.org ping every 10 min if it bothers you |

To see what Telegram thinks of your webhook, open this in a browser (it shows the
registered URL, pending update count and the last error — never share the result, it
contains your token):

```
https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

---

## Part 7 — If Render doesn't work out

The bot has no platform lock-in. Anywhere you can run Python, it runs:

- **Any VPS** (Hetzner ~€4/mo, Contabo, or an Iranian provider): `MODE=polling`, plus
  `PROXY_URL` if the server is inside Iran. Persistent disk, no sleeping, `/stats` and
  `/pending` actually work over time.
- **A machine in the office**: same as local development — `python main.py` with a
  proxy. Free, and the lead database lives on hardware you control.

In both cases you copy the folder, set `.env`, and start it. Nothing else changes.
