---
name: edge-tts
description: Generate speech/voiceover audio from text for free, no API key or account needed. Use when the user asks for narration, озвучка, voiceover, TTS, or audio for a Reels/video script, in Russian or other languages.
---

# edge-tts — free text-to-speech

Uses Microsoft Edge's online neural voices. Completely free, no API key, no account, no per-character cost.

Install (once per machine) if `python3 -m edge_tts --help` fails:

```bash
python3 -m pip install --user edge-tts
# On Debian/Ubuntu servers with an externally-managed environment, if that errors:
python3 -m pip install --user --break-system-packages edge-tts
```

Always invoke via the module form — it works the same on Windows, Linux, and macOS regardless of where pip put the console script:

## How to use

```bash
python3 -m edge_tts --voice ru-RU-DmitryNeural --text "Текст для озвучки" --write-media out.mp3
```

- `--voice`: pick a voice. Known-good Russian voices: `ru-RU-DmitryNeural` (male), `ru-RU-SvetlanaNeural` (female).
- `--rate=+10%` / `--rate=-10%`: adjust speaking speed.
- `--pitch=+5Hz`: adjust pitch.
- `--file script.txt` instead of `--text` for longer scripts.
- List all voices: `python -m edge_tts --list-voices` (200+ voices, 50+ languages).

## Notes

- Output is mp3. For Reels/Shorts, feed the mp3 into the `video-editing` or `remotion-video-creation` skill (already installed) for the final render with captions/timing.
- No rate limit has been documented publicly, but this rides on Microsoft's consumer Edge TTS service, not an official paid product — for a single freelance order's voiceover this is a non-issue; don't script mass/bulk abuse.
