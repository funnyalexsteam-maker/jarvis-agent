# Kwork gig evaluator — design

## Purpose

Александр works Kwork as a freelance channel for automation/bot/web-dev work, currently to build up reviews/reputation, with only 30 responses per month. Evaluating each incoming job posting (fit, red flags, price, whether to respond) has so far happened manually in a Claude Code chat, one posting at a time. This project turns that manual reasoning into a reusable Claude Code skill: paste a Kwork job posting, get a structured verdict back, invokable both from a local Claude Code session and from the Jarvis Telegram bot on the VPS.

## Scope

**v1 (this spec):** a single skill, `/evaluate-gig`, that takes pasted job-posting text and returns a verdict. No code, no service, no persistence — pure prompt/criteria logic in a SKILL.md.

**Explicitly out of scope (deferred to v2):** an automated parser that pulls new Kwork postings without the user pasting them (mirroring what `scout-agent` does for FL.ru's RSS feed). Kwork has no known public feed/API for this, so v2 will need its own feasibility spike before design. Not addressed here.

## Location

```
Jarvis/.claude/skills/evaluate-gig/
  SKILL.md
```

Follows the same pattern as the existing `reminder` skill (single `SKILL.md`, no wrapper files). This is a project-authored custom skill under `.claude/skills/`, distinct from the marketplace plugins listed in `enabledPlugins` in `.claude/settings.json` (claude-code-setup, superdesign, carbone-skill, etc.) and distinct from the public course skill library at `Jarvis/skills/` (`global/`, `custom/`), which is student-facing template content for the "Архитектор нейросотрудников" course, not runtime tooling for Александр's own use.

Works two ways once deployed:
- Locally in Claude Code, whenever the Jarvis repo (or this skill specifically) is available to the session.
- Through the Jarvis Telegram bot on the VPS, after the skill is deployed there the same way `reminder` was (see jarvis-bot-deployment memory) — the bot has no shared context with local Claude Code sessions, so the skill's criteria must be fully self-contained in SKILL.md, not dependent on anything from this conversation.

## Skill behavior

### Input
Free-text job posting pasted by the user (Kwork listing: title + ТЗ + any stated price).

### Criteria (encoded in SKILL.md)

**Niche fit** — in-profile: automation, Telegram/Discord bots, landing pages/websites, API integrations, simple web dev (auth, DB, forms). Out-of-profile: design, copywriting, video editing, marketing analytics. Out-of-profile is *not* an automatic skip (see below).

**Kwork's 30-response/month economics** — current goal is building reviews/reputation, not maximizing income or portfolio fit. So an out-of-profile posting is still worth taking if: it's short and well-defined, low risk of missing the deadline, and the client is likely to leave a review (typical small, low-ambiguity job). Skip: postings that are effectively unwinnable (heavy underbidding competition, dozens of freelancers will respond in minutes), postings with a brief too vague to scope without back-and-forth that eats the response budget, and postings with red-flag/stop-factor content.

**Hard stop-factors (skip regardless of platform economics)** — anything requesting evasion of security/antivirus detection without a legitimate remediation purpose, collecting others' personal data without legal basis, or anything that amounts to laundering a malicious site's reputation. These override the "take it for reviews" logic entirely.

**Price** — rough ranges per work type (bots, landing pages, integrations, small fixes/forms), reusing the figures established in this conversation, so the skill doesn't re-derive pricing from scratch each time.

### Output format
1. **Verdict** — take / skip / ask for clarification first
2. **Red flags** (if any)
3. **Price** (if verdict is "take")
4. **Draft response** (only if verdict is "take") — first person, Александр's own voice, no em-dashes, matching the style used in this conversation's drafts

## Rollout

1. Build the skill in the Jarvis repo, `Jarvis/.claude/skills/evaluate-gig/SKILL.md`.
2. Test `/evaluate-gig` locally against a few real Kwork postings, including ones already manually evaluated in this conversation, and compare verdicts for consistency.
3. Deploy to the VPS the same way `reminder` was deployed (see jarvis-bot-deployment memory), and verify `/evaluate-gig` works through the Jarvis Telegram bot.
4. **Only after step 3 is verified**, and with explicit user confirmation at that point, retire `Personal\scout-agent\` (repo + GitHub remote) — its FL.ru-monitoring purpose is being superseded by this new evaluator for the platform Александр is actually focusing on (Kwork). This is a separate, explicitly-confirmed step, not automatic once the skill ships.

## v2 (not designed here)

- A Kwork posting parser/poller feeding postings into the same evaluator automatically, mirroring `scout-agent`'s FL.ru RSS monitor. Needs its own feasibility spike first (Kwork has no known public feed/API — likely needs scraping or an unofficial approach, TOS considerations apply).
- If posting volume grows enough that the free-text criteria in SKILL.md become inconsistent between runs, consider extracting weighted rules into a structured config file (criteria.json) — deferred per the "Approach A first, B if needed" decision made during design.
