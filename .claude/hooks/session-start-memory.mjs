#!/usr/bin/env node
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function safeRead(p) {
  try { return readFileSync(p, "utf8"); } catch { return ""; }
}

let ctx = "";
for (const f of ["SOUL.md", "MEMORY.md", "GOALS.md"]) {
  const c = safeRead(join(root, f));
  if (c) ctx += `\n\n## ${f}\n\n${c}`;
}

try {
  const memDir = join(root, "memory");
  const cutoff = Date.now() - 3 * 24 * 60 * 60 * 1000;
  const files = readdirSync(memDir)
    .filter((f) => f.endsWith(".md"))
    .filter((f) => statSync(join(memDir, f)).mtimeMs >= cutoff)
    .sort();
  for (const f of files) {
    ctx += `\n\n## memory/${f}\n\n${safeRead(join(memDir, f))}`;
  }
} catch {}

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ctx,
  },
}));
