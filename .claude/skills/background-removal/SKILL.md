---
name: background-removal
description: Remove the background from a photo/product image for free, fully local, no account needed. Use when the user asks to cut out a background, make a transparent PNG, isolate a product/subject from a photo, or clean up a photo for e-commerce/design use.
---

# background-removal (rembg)

Open-source, runs 100% locally, no account, no API cost. Install (once per machine) if `rembg --help` fails:

```bash
python3 -m pip install --user "rembg[cli,cpu]"
# On Debian/Ubuntu servers with an externally-managed environment, if that errors:
python3 -m pip install --user --break-system-packages "rembg[cli,cpu]"
```

`rembg` has no `python -m rembg` module form — it only works as the installed console script. Pip installs it under the user's script dir, which often isn't on PATH:
- Linux/macOS: `$(python3 -m site --user-base)/bin/rembg`
- Windows: `%APPDATA%\Python\Python3XX\Scripts\rembg.exe`

If plain `rembg` doesn't resolve, use the full path from above.

## How to use

```bash
rembg i -m u2net input.jpg output.png
```

**Always pass `-m u2net`.** The library's default model (`bria-rmbg`, ~1GB) crashed with an ONNX "bad allocation" error on a low-RAM machine (insufficient RAM for that model's decoder) — confirmed on Windows during testing. `u2net` (~176MB) is the classic, well-tested, lighter model and works reliably on modest hardware, including small VPS instances.

- First run per model downloads the model file to `~/.rembg/models/` (one-time, ~176MB for u2net) — expect it to take a minute or two.
- Output is a PNG with a transparent background (alpha channel).
- For a folder of images: `rembg p -m u2net input_dir/ output_dir/`
- Other lightweight alternatives if u2net quality is insufficient for a specific subject: `u2netp` (smaller/faster, lower quality), `silueta` (people), `isnet-general-use`.

## Pipeline tip

Pair with the `pollinations-image` skill: generate a product/subject image, then run background removal on it to get a clean transparent-background asset for banners, product photos, or composites.
