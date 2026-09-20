# Kwork Gig Evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Jarvis skill, `evaluate-gig`, that reads a pasted Kwork job posting and returns a structured verdict (take/skip/clarify, red flags, price, draft response), usable both locally in Claude Code and through the Jarvis Telegram bot on the VPS.

**Architecture:** A single plain-markdown skill file, no code, no service, no persistence. Follows the existing `reminder` skill's format exactly (title, natural-language trigger phrases, criteria tables, no YAML frontmatter, no slash-command registration) rather than a formal `/evaluate-gig` command — Jarvis skills are conversationally triggered, not slash-invoked, and this project must match that convention to work through the bot.

**Tech Stack:** Markdown only. Deployment via `git` (GitHub fork) + manual `scp`/`ssh` to the VPS, mirroring how `reminder` was deployed (the bot's own `/update` does not pull from Александр's fork).

**Spec:** `docs/superpowers/specs/2026-09-18-kwork-gig-evaluator-design.md`

## Global Constraints

- File lives at `Jarvis/.claude/skills/evaluate-gig/SKILL.md` — no other files, no `plugin.json`, no code.
- v1 scope is Kwork only — do not generalize criteria to FL.ru/Workzilla economics.
- Hard stop-factors (security-detection evasion without legitimate remediation purpose, non-consensual personal-data collection, malicious-site reputation laundering) override every other rule, including the "take it for reviews" logic — a stop-factor always means skip.
- The bot has no shared context with local Claude Code sessions (see jarvis-no-shared-context memory) — all criteria must be fully self-contained in SKILL.md, no reliance on anything from this conversation.
- Repo documentation convention is Russian — SKILL.md content must be written in Russian, matching `reminder/SKILL.md` and `GOALS.md`.
- Deleting `Personal\scout-agent\` is explicitly gated on user confirmation after VPS verification succeeds (Task 4) — it must never be executed automatically as a normal plan step.

---

### Task 1: Write the `evaluate-gig` skill file

**Files:**
- Create: `Jarvis/.claude/skills/evaluate-gig/SKILL.md`

**Interfaces:**
- Produces: a markdown file with these exact section headings, consumed by Task 2's verification: `## Триггеры`, `## Экономика Kwork`, `## Критерии`, `## Цена`, `## Формат ответа`.

- [ ] **Step 1: Write the skill file**

Create `Jarvis/.claude/skills/evaluate-gig/SKILL.md` with this content:

```markdown
# Оценка заказов с Kwork

Когда пользователь скидывает текст объявления с Kwork и спрашивает, стоит ли брать заказ, откликаться ли, что думаешь про такой заказ, оцени этот заказ, посмотри на такое ТЗ.

## Триггеры

Активируй этот скилл когда слышишь: "оцени заказ", "стоит ли брать", "как тебе такой заказ",
"посмотри такое ТЗ", "заказ с kwork", "откликнуться на это", "какая тут цена", "стоит ли откликаться".

## Контекст

Александр использует Kwork для поиска заказов по автоматизации, ботам и веб-разработке.
Лимит — 30 откликов в месяц. Текущая цель — не максимальный доход и не идеальное портфолио,
а наработка отзывов и репутации на площадке. Это меняет то, какие заказы стоит брать: заказ
не по профилю всё равно может быть достойным откликом, если он быстрый и надёжный.

## Экономика Kwork

- Отклики ограничены (30/мес) — их стоит тратить осмысленно, но не только на "идеальные" по нише заказы.
- Не по нише, но короткий и понятный заказ с высокой вероятностью хорошего отзыва — БРАТЬ.
- Заведомо проигрышная конкуренция (заказ, на который за минуты откликнутся десятки фрилансеров
  дешевле) — ПРОПУСКАТЬ, отклик потрачен впустую.
- Расплывчатый бриф без возможности быстро уточнить объём — ПРОПУСКАТЬ или сначала уточнить,
  не тратить отклик на заказ, который потом растянется в бесконечную переписку.

## Критерии

### Соответствие нише

По профилю: автоматизация, Telegram/Discord-боты, лендинги и сайты, интеграции API, простая
веб-разработка (авторизация, БД, формы).

Не по профилю: дизайн, копирайтинг, видеомонтаж, маркетинг-аналитика. Несоответствие нише — это
НЕ автоматический отказ, см. "Экономика Kwork" выше.

### Стоп-факторы (отказ всегда, независимо от ниши и экономики)

Отказывать безусловно, если заказ подразумевает:
- обход систем безопасности или антивирусного детектирования без легитимной цели устранения
  проблемы (например, "снять флаги VirusTotal" без реальной чистки вредоносного кода);
- сбор персональных данных третьих лиц без правовых оснований;
- что-либо похожее на отбеливание репутации заведомо вредоносного сайта.

Эти пункты перекрывают всё остальное — даже если заказ по нише и хорошо оплачивается.

## Цена

Ориентировочные вилки для заказов по профилю:

| Тип работы | Цена |
|---|---|
| Простая форма/интеграция (форма обратной связи, вебхук, уведомления в Telegram) | 2000–5000₽ |
| Telegram/Discord-бот (базовый функционал) | 5000–15000₽ |
| Лендинг/визитка под ключ | 5000–12000₽ |
| Автоматизация/скрипт под конкретную задачу | 3000–10000₽ |
| Мелкая правка/консультация | 500–2000₽ |

Для заказов не по профилю, взятых ради отзыва (см. "Экономика Kwork") — цена минимальная,
разумная для объёма работы, не выше, чем берут типичные исполнители в этой узкой категории.

## Формат ответа

Всегда отвечай в этом порядке:

1. **Вердикт** — брать / не брать / сначала уточнить (одна строка с коротким обоснованием).
2. **Red flags** — если есть; если нет, не писать раздел вообще.
3. **Цена** — только если вердикт "брать".
4. **Черновик отклика** — только если вердикт "брать". От первого лица, без двойных тире
   (обычные точки и запятые вместо "—"), в естественном разговорном тоне, без канцелярита.
```

- [ ] **Step 2: Verify all required section headings are present**

Run: `grep -E "^## (Триггеры|Экономика Kwork|Критерии|Цена|Формат ответа)" "Jarvis/.claude/skills/evaluate-gig/SKILL.md"`
Expected: 5 matching lines, one per heading listed above.

- [ ] **Step 3: Commit**

```bash
cd Jarvis
git add .claude/skills/evaluate-gig/SKILL.md
git commit -m "$(cat <<'EOF'
Add evaluate-gig skill for Kwork job postings

Encodes the manual evaluation criteria (niche fit, Kwork's 30-response/month reputation-building economics, hard stop-factors, price ranges, response format) worked out in chat as a reusable skill, following the reminder skill's plain-markdown, conversationally-triggered format.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Verify locally against real Kwork-style postings

**Files:** none created or modified unless Step 4 finds a wording problem, in which case: Modify `Jarvis/.claude/skills/evaluate-gig/SKILL.md`.

**Interfaces:**
- Consumes: the skill file produced in Task 1, loaded into a Claude Code session with `Jarvis/.claude` on the skill search path (open the session with the `Jarvis` folder as the working directory).

- [ ] **Step 1: Test posting A — in-niche, expect "брать"**

In a Claude Code session opened at `Jarvis/`, paste this posting and ask "оцени этот заказ с kwork":

```
Подключить форму обратной связи на сайт клиники.
- Отправка заявок на почту и в Telegram
- Валидация обязательных полей
- Уведомление пользователю после успешной отправки
- Работает на десктопе и на мобильном
Дизайн сайта менять не нужно, встроить в существующую страницу.
```

Expected: вердикт "брать", цена в диапазоне 2000–5000₽ (простая форма/интеграция), черновик отклика присутствует, без двойных тире.

- [ ] **Step 2: Test posting B — off-niche but low-risk, expect "брать" (reputation logic)**

Paste this posting:

```
Вычитать предоставленный текст объёмом до 1000 знаков.
- Исправить орфографические ошибки
- Исправить пунктуационные ошибки
```

Expected: вердикт "брать" (обоснование через логику наработки отзывов — короткий, низкий риск, не по нише), минимальная цена, черновик отклика присутствует.

- [ ] **Step 3: Test posting C — stop-factor, expect "не брать"**

Paste this posting:

```
Нужен человек который удалит все вирусы у VirusTotal о моем сайте.
По цене: 5 вирусов = 3000 рублей и т.д.
```

Expected: вердикт "не брать", red flags объясняют, что это похоже на обход детекта, а не легитимную чистку; цены и черновика отклика в ответе быть не должно.

- [ ] **Step 4: Fix and re-test if any verdict is wrong**

If any of A/B/C didn't match its expected verdict, edit the relevant section of `Jarvis/.claude/skills/evaluate-gig/SKILL.md` to sharpen the wording, then repeat the mismatched test. If a fix was needed, commit it:

```bash
cd Jarvis
git add .claude/skills/evaluate-gig/SKILL.md
git commit -m "fix: sharpen evaluate-gig criteria after local test mismatch"
```

---

### Task 3: Deploy to the VPS and verify through the Jarvis Telegram bot

**Files:** none in this repo; this task operates on the live VPS filesystem via SSH (alias `scout-vps`, see jarvis-bot-deployment memory).

**Interfaces:**
- Consumes: the committed `Jarvis/.claude/skills/evaluate-gig/SKILL.md` from Task 1.

- [ ] **Step 1: Push the commits to GitHub**

```bash
cd Jarvis
git push
```

- [ ] **Step 2: Locate the live path of the `reminder` skill on the VPS**

```bash
ssh scout-vps "find / -maxdepth 6 -type d -iname reminder 2>/dev/null"
```

Expected: a path like `/home/agent/.claude/skills/reminder` (or wherever it actually is — the jarvis-bot-deployment memory warns hostnames/paths can drift; trust this command's output over any assumption).

- [ ] **Step 3: Create the matching directory for evaluate-gig and copy the file**

Using the parent directory found in Step 2 (substitute `<skills-dir>` with it):

```bash
ssh scout-vps "mkdir -p <skills-dir>/evaluate-gig"
scp "Jarvis/.claude/skills/evaluate-gig/SKILL.md" "scout-vps:<skills-dir>/evaluate-gig/SKILL.md"
```

- [ ] **Step 4: Confirm the file landed correctly**

```bash
ssh scout-vps "cat <skills-dir>/evaluate-gig/SKILL.md" | head -5
```

Expected: shows the `# Оценка заказов с Kwork` heading — confirms the copy succeeded and wasn't truncated.

- [ ] **Step 5: Find how the bot invokes the `claude` CLI, to replicate it for a manual smoke test**

```bash
ssh scout-vps "grep -n 'claude' /home/agent/.agent/bot/index.js | head -20"
```

This shows the exact command/args pattern `bot/index.js` uses to spawn the CLI per message (see jarvis-agent-setup memory: the bot spawns the real `claude` CLI rather than calling an API directly).

- [ ] **Step 6: Smoke-test the skill on the VPS using that same invocation pattern**

Using the pattern found in Step 5, manually run the equivalent of a user message containing Test Posting A from Task 2 Step 1, either by:
- SSHing in and invoking the CLI the same way `bot/index.js` does, or
- sending the posting to the Jarvis bot for real via Telegram, if that's faster to confirm.

Expected: response follows the same format verified locally in Task 2 (вердикт → red flags if any → цена → черновик отклика), confirming the bot picks up the new skill without a restart (per jarvis-agent-setup, the bot spawns a fresh `claude` CLI process per message, so no `systemctl restart agent-bot` should be needed — but if the smoke test fails, try the restart and re-test before assuming something else is wrong).

- [ ] **Step 7: Report the smoke-test result to Александр**

Tell him explicitly whether Task 3 passed (bot replied correctly through Telegram) before moving to Task 4 — Task 4 must not start until he's seen this confirmation.

---

### Task 4: Retire scout-agent (gated — do not auto-execute)

**Files:**
- Delete (only after explicit confirmation): `Personal\scout-agent\` (local directory) and its GitHub remote repository.

**Interfaces:** none — this task has no code interface, it's a cleanup action.

- [ ] **Step 1: STOP and ask for explicit confirmation**

Do not proceed past this step automatically, regardless of execution mode (subagent-driven or inline). Message Александр directly:

> "evaluate-gig задеплоен и подтверждён рабочим через Jarvis-бота (Task 3 прошла). Как договаривались в спеке — удаляю `Personal\scout-agent\` (локально и GitHub-репозиторий), так как его функция для Kwork больше не нужна. Подтверди, что можно удалять."

Wait for an explicit yes. If he says no, wait, or asks to keep it, stop here — do not delete anything, and do not re-ask later without a new prompt from him.

- [ ] **Step 2: Delete the GitHub remote repository (only after Step 1's explicit yes)**

```bash
gh repo delete funnyalexsteam-maker/scout-agent --yes
```

(Confirm the exact remote name first with `cd Personal/scout-agent && git remote -v` if unsure — do not guess the repo slug.)

- [ ] **Step 3: Delete the local directory**

```bash
rm -rf Personal/scout-agent
```

- [ ] **Step 4: Report completion**

Tell Александр both deletions are done and that Kwork evaluation now runs entirely through `evaluate-gig`.
