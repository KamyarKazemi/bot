# CONTEXT.md — Bizynex Telegram Wizard Bot

Consolidated from: project knowledge (`context.md`, 8 strategy docs, `memory.md`) + the graphify
semantic graph in `bot/graphify-out/` (313 nodes / 393 edges across 34 files, 94,983 words).

---

## 1. What graphify found in this directory

The `bot/` directory is **not** a codebase — it is a **design-taste rule library**. The graph
contains zero application code (only `package.json` → `headroom-ai`) and 21 skill documents
grouped into four clusters:

| Cluster | Skills | What it governs |
|---|---|---|
| Frontend taste | `design-taste-frontend` (v2, 31 nodes), `design-taste-frontend-v1`, `gpt-taste`, `high-end-visual-design` | Three Dials (VARIANCE / MOTION / DENSITY), anti-AI-slop rules, forbidden patterns, pre-flight checks |
| Visual style archetypes | `minimalist-ui`, `industrial-brutalist-ui`, `stitch-design-taste` (+ `DESIGN.md`) | Single-archetype commitment, palette roles, one-accent rule, banned colors |
| Image generation | `imagegen-frontend-web`, `imagegen-frontend-mobile`, `image-to-code`, `brandkit` | Image-first art direction, combinatorial variation, 21/27-point clarity checks |
| Process discipline | `full-output-enforcement`, `redesign-existing-projects` | No truncation, no placeholders, scan→diagnose→fix ordering |

**The recurring meta-principle across all 21 documents:** taste is encoded as *explicit negative
constraints* — banned elements, AI tells, anti-patterns, pre-flight checklists — not as open-ended
creative freedom. `memory.md` confirms this independently: *"Constraint-heavy prompts outperform
open-ended ones."*

This bot is built the same way: every question is closed-form where possible, every input is
validated, every state transition is explicit, and the copy is written to a fixed voice.

## 2. Business context the bot must express

**Bizynex** — software/digital services company, Iran, 3 founders (front-end, back-end,
business & strategy), pre-launch, no employees, limited capital, international-ready by design.

**We sell business outcomes, not deliverables.** Not websites → digital credibility. Not
automation → operational efficiency. Not software → measurable business improvement.

Ordered principles (higher wins on conflict): long-term sustainability > short-term growth ·
customer trust > immediate profit · quality > volume · systems > individual heroics ·
transparency > ambiguity · simplicity > unnecessary complexity.

**Never compete on price.** Customers cannot evaluate engineering — they evaluate
professionalism, communication, process, responsiveness. **Reducing uncertainty beats reducing price.**

### Fears the bot must neutralize at every step
wasted money · project failure · dishonest provider · hidden costs · delays · poor
communication · vendor lock-in · technical complexity.

### Drivers the bot must amplify
confidence · professionalism · transparency · predictability · competence · partnership.

## 3. Service catalog (from `memory.md` + strategy docs)

1. **وب‌سایت** — custom development and WordPress
2. **اتوماسیون و یکپارچه‌سازی** — process automation, integrations, internal tooling
3. **ربات پیام‌رسان** — Telegram/messaging bots
4. **طراحی گرافیک** — logo, banner, poster, social assets
5. **سیستم انبارداری / مدیریت موجودی** — inventory management systems
6. **مشاوره** — consulting, unsure-what-I-need path

## 4. Brand constraints applied to bot copy and UI

| Constraint | Source | How the bot honours it |
|---|---|---|
| Farsi-first, RTL-native | memory.md | All copy written natively in Persian, never translated; RLM/RTL-safe formatting |
| Latin-script brand name | memory.md | "Bizynex" always Latin, never بیزینکس |
| Navy `#122A3E` / Teal `#17A096` | memory.md (canonical, from master logo) | Documented for any future web-view or generated assets |
| Teal used sparingly — one accent per viewport | memory.md | One emphasis marker per bot message maximum |
| No emoji spam | design-taste anti-emoji policy | Restrained markers only (`•`, `✓`, `◂`), never decorative emoji |
| Self-hosted / no external CDN | memory.md | Zero third-party services at runtime; SQLite file + Telegram API only |
| Persian orthography precision (ZWNJ) | memory.md | Half-spaces (`‌`) used correctly in compound words |
| Persian digits | user decision | All numbers rendered ۰-۹ |
| Jalali calendar | user decision | All dates shown in the Persian calendar |
| Iran connectivity reality | context.md §3 | Optional HTTP/SOCKS5 proxy, pure-python deps only, offline-capable storage |

## 5. Decision filter applied to this bot

- **Genuine customer value?** Yes — a prospect gets a structured, transparent intake at 2am without waiting for a founder.
- **Strengthens trust?** Yes — the wizard shows exactly what will happen next, and never asks for payment or commitment.
- **Communicates business value, not technical complexity?** Yes — questions are phrased in business outcomes, never in stack terms.
- **Runnable by 3 people?** Yes — one file per concern, no infrastructure, leads arrive as a Telegram DM.
- **Survives worse economic conditions?** Yes — no paid services, no hosting requirement, runs on a laptop behind a proxy.
- **Reduces a known failure mode (§9)?** Yes — attacks "projects without defined scope" and "poor communication" by capturing scope before the first call.
