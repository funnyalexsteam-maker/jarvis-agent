---
name: pollinations-image
description: Generate an image from a text prompt for free, no API key or account needed. Use when the user asks to generate/create an image, illustration, banner, sticker, or infographic from a prompt for a client order (e.g. Kwork "Изображения по промту", "Статичная графика").
---

# Pollinations image generation

Free, keyless text-to-image via the Pollinations API. No signup, no billing, no rate-limit key required.

## How to use

Fetch (or curl-download) this URL, with the prompt URL-encoded:

```
https://image.pollinations.ai/prompt/<URL-ENCODED-PROMPT>?width=<W>&height=<H>&nologo=true&seed=<optional-int>
```

Example:

```bash
curl -s "https://image.pollinations.ai/prompt/a%20cozy%20coffee%20shop%20logo%2C%20flat%20vector%2C%20minimal?width=1024&height=1024&nologo=true" -o out.jpg
```

- `width`/`height`: pick sizes matching the deliverable (e.g. 1080x1080 for a social post, 1200x628 for an OG banner).
- `nologo=true`: removes the small Pollinations watermark when supported by the served model.
- `seed=<int>`: pass the same seed to get a reproducible variant, or omit for a fresh random result each call.
- Response is the raw image bytes (jpeg/png) — save directly to a file.

## When NOT to use

- For paid/commercial client deliverables where guaranteed no-watermark, high-res, or a specific style/brand consistency is required, verify output quality first — this is a free best-effort service, not an SLA-backed product. If quality is insufficient, fall back to Canva (already configured) for on-brand graphics.
- For product photography needing a transparent/clean background, generate here then run the `background-removal` skill on the result.
