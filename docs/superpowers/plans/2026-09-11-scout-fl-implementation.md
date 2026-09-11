# Scout-FL (RSS-мониторинг заказов FL.ru) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать и задеплоить первую часть Scout-агента — периодический мониторинг RSS-ленты заказов FL.ru с фильтрацией по 5 направлениям и уведомлением в Telegram.

**Architecture:** Один Node.js-проект `scout-agent` с независимыми модулями (сопоставление ключевых слов, дедупликация, счётчик ошибок, Telegram-нотификатор, RSS-фид FL.ru), собранными в один entrypoint-скрипт `runScoutFl.js`, который запускается по systemd timer на VPS. Второй компонент из дизайна — `scout-tg` (мониторинг Telegram-чатов) — сюда не входит, это отдельный план после того, как эти же общие модули (keywordMatcher, notifier) будут проверены в бою.

**Tech Stack:** Node.js 20 (LTS, совпадает с версией на VPS), встроенный `node:test` для тестов (без доп. тест-фреймворка), `fast-xml-parser` — единственная внешняя зависимость (парсинг RSS).

**Spec:** `docs/superpowers/specs/2026-09-11-scout-agent-design.md`

## Global Constraints

- Секреты (`BOT_TOKEN`, `NOTIFY_CHAT_ID`) — только в `.env`, никогда не в коде и не в git (см. спеку, раздел «Секреты и безопасность»).
- Любая запись файла на диск (дедуп-стор, счётчик ошибок) — атомарно: пишем во временный файл, затем `rename` (см. урок из инцидента с `.env` agent-bot).
- Уведомление в Telegram — только факты (источник, название, направление, бюджет если есть, ссылка), без AI-оценки.
- Предупреждение об отказе RSS-фида — не чаще раза в час (после 6 неудачных циклов подряд при интервале 10 минут), не на каждый сбой.
- На локальной машине нет Node.js и нет прав администратора/winget — установка только через портативный zip-дистрибутив (тот же подход, что и с `gh.exe`, см. память `github_cli_access`).
- Прямого SSH-доступа к VPS с этой машины нет (сетевая блокировка на уровне хостинга) — деплой оформляется как runbook-инструкция для Jarvis, а не как команды, которые я выполняю сам.

---

### Task 1: Портативный Node.js + скелет проекта

**Files:**
- Create: `D:\Projects\scout-agent\package.json`
- Create: `D:\Projects\scout-agent\.gitignore`
- Create: `D:\Projects\scout-agent\.env.example`

**Interfaces:**
- Produces: рабочий `node`/`npm` в `D:\Tools\node-v20.18.1-win-x64\`, доступный по полному пути во всех следующих задачах; git-репозиторий `D:\Projects\scout-agent` с первым коммитом.

- [ ] **Step 1: Скачать портативный Node.js (без прав администратора)**

```powershell
New-Item -ItemType Directory -Force -Path D:\Tools | Out-Null
Invoke-WebRequest -Uri "https://nodejs.org/dist/v20.18.1/node-v20.18.1-win-x64.zip" -OutFile "D:\Tools\node.zip"
Expand-Archive -Path "D:\Tools\node.zip" -DestinationPath "D:\Tools" -Force
Remove-Item "D:\Tools\node.zip"
```

Если версия 20.18.1 больше недоступна (404) — открыть `https://nodejs.org/dist/` и подставить актуальную версию из ветки 20.x (не 22/24 — на VPS стоит именно Node 20, версии должны совпадать).

- [ ] **Step 2: Проверить, что node и npm работают**

```powershell
& "D:\Tools\node-v20.18.1-win-x64\node.exe" --version
& "D:\Tools\node-v20.18.1-win-x64\npm.cmd" --version
```

Expected: первая команда печатает `v20.18.1`, вторая — версию npm (например `10.x.x`).

- [ ] **Step 3: Добавить Node в PATH пользователя (не системный — прав администратора не требует)**

```powershell
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";D:\Tools\node-v20.18.1-win-x64", "User")
```

Это подействует на новые процессы. Во всех следующих задачах команды всё равно вызывают `node`/`npm` по полному пути `D:\Tools\node-v20.18.1-win-x64\`, чтобы не зависеть от того, подхватилась ли переменная в конкретной сессии инструмента.

- [ ] **Step 4: Создать package.json**

```json
{
  "name": "scout-agent",
  "version": "0.1.0",
  "private": true,
  "description": "Мониторинг заказов фриланса (FL.ru RSS) с уведомлением в Telegram",
  "type": "commonjs",
  "engines": { "node": ">=20" },
  "scripts": {
    "test": "node --test test/",
    "scout-fl": "node src/runScoutFl.js"
  },
  "dependencies": {
    "fast-xml-parser": "^4.5.0"
  }
}
```

- [ ] **Step 5: Создать .gitignore**

```
node_modules/
.env
*.session
data/
```

- [ ] **Step 6: Создать .env.example**

```
BOT_TOKEN=
NOTIFY_CHAT_ID=
```

- [ ] **Step 7: Установить зависимости**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/npm.cmd" install
```

Expected: появляется `node_modules/` и `package-lock.json`, без ошибок.

- [ ] **Step 8: git init и первый коммит**

```bash
cd /d/Projects/scout-agent
git init
git add package.json package-lock.json .gitignore .env.example
git commit -m "chore: scaffold scout-agent project"
```

---

### Task 2: Загрузчик .env (без внешней зависимости)

**Files:**
- Create: `D:\Projects\scout-agent\src\env.js`
- Test: `D:\Projects\scout-agent\test\env.test.js`

**Interfaces:**
- Produces: `loadEnv(filePath: string): void` — читает `KEY=VALUE` построчно из файла и кладёт в `process.env`, не перезаписывая уже установленные переменные. Используется в Task 8 (`runScoutFl.js`).

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/env.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadEnv } = require('../src/env');

test('loads simple KEY=VALUE lines into process.env', () => {
  const filePath = path.join(os.tmpdir(), `env-test-${Date.now()}.env`);
  fs.writeFileSync(filePath, 'FOO_TEST_KEY=bar\n# comment\nBAZ_TEST_KEY="quoted value"\n');
  loadEnv(filePath);
  assert.strictEqual(process.env.FOO_TEST_KEY, 'bar');
  assert.strictEqual(process.env.BAZ_TEST_KEY, 'quoted value');
  delete process.env.FOO_TEST_KEY;
  delete process.env.BAZ_TEST_KEY;
  fs.unlinkSync(filePath);
});

test('does not overwrite already-set env vars', () => {
  const filePath = path.join(os.tmpdir(), `env-test-${Date.now()}.env`);
  process.env.EXISTING_TEST_KEY = 'original';
  fs.writeFileSync(filePath, 'EXISTING_TEST_KEY=overwritten\n');
  loadEnv(filePath);
  assert.strictEqual(process.env.EXISTING_TEST_KEY, 'original');
  delete process.env.EXISTING_TEST_KEY;
  fs.unlinkSync(filePath);
});

test('silently does nothing if file does not exist', () => {
  assert.doesNotThrow(() => loadEnv(path.join(os.tmpdir(), 'does-not-exist.env')));
});
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/env.test.js
```

Expected: FAIL — `Cannot find module '../src/env'`.

- [ ] **Step 3: Реализовать env.js**

```javascript
// src/env.js
const fs = require('node:fs');

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) return;
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;
    const key = trimmed.slice(0, eqIndex).trim();
    let value = trimmed.slice(eqIndex + 1).trim();
    const isQuoted =
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"));
    if (isQuoted) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

module.exports = { loadEnv };
```

- [ ] **Step 4: Запустить тест и убедиться, что он проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/env.test.js
```

Expected: PASS, 3 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/env.js test/env.test.js
git commit -m "feat: add minimal .env loader"
```

---

### Task 3: Модуль сопоставления ключевых слов (общий с будущим scout-tg)

**Files:**
- Create: `D:\Projects\scout-agent\src\keywordMatcher.js`
- Test: `D:\Projects\scout-agent\test\keywordMatcher.test.js`

**Interfaces:**
- Produces: `matchDirection(text: string): string | null` — возвращает одно из `'landing' | 'bots' | 'ai' | 'automation' | 'devops'` или `null`. Используется в Task 8 (`runScoutFl.js`) и будет переиспользован в будущем плане `scout-tg`.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/keywordMatcher.test.js
const test = require('node:test');
const assert = require('node:assert');
const { matchDirection } = require('../src/keywordMatcher');

test('matches landing/visitka orders', () => {
  assert.strictEqual(matchDirection('Нужен лендинг для стоматологии'), 'landing');
  assert.strictEqual(matchDirection('Сделать визитку для мастера маникюра'), 'landing');
});

test('matches telegram bot orders', () => {
  assert.strictEqual(matchDirection('Ищу разработчика телеграм бота для магазина'), 'bots');
});

test('matches AI assistant orders', () => {
  assert.strictEqual(matchDirection('Нужен ии-ассистент на сайт для консультаций'), 'ai');
});

test('matches parsing/automation orders', () => {
  assert.strictEqual(matchDirection('Нужен парсер цен конкурентов в Excel'), 'automation');
});

test('matches server deployment orders', () => {
  assert.strictEqual(matchDirection('Помочь развернуть бота на VPS, настроить деплой'), 'devops');
});

test('returns null for unrelated text', () => {
  assert.strictEqual(matchDirection('Нужен дизайн упаковки для конфет'), null);
});

test('is case-insensitive', () => {
  assert.strictEqual(matchDirection('ЛЕНДИНГ для юриста'), 'landing');
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/keywordMatcher.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать keywordMatcher.js**

```javascript
// src/keywordMatcher.js
const DIRECTIONS = {
  landing: ['лендинг', 'landing', 'одностраничник', 'визитк'],
  bots: ['телеграм бот', 'telegram бот', 'tg бот', 'чат-бот', 'бота для телеграм', 'телеграм-бота'],
  ai: ['нейросет', 'chatgpt', 'gpt', 'ии-ассистент', 'ai-ассистент', 'ассистент на базе', 'ии ассистент'],
  automation: ['парсинг', 'парсер', 'автоматизац', 'скрипт для сбора', 'интеграция api', 'интеграцию api'],
  devops: ['настроить сервер', 'деплой', 'vps', 'развернуть на сервере', 'docker', 'разверн'],
};

function matchDirection(text) {
  const lower = text.toLowerCase();
  for (const [direction, keywords] of Object.entries(DIRECTIONS)) {
    if (keywords.some((kw) => lower.includes(kw))) {
      return direction;
    }
  }
  return null;
}

module.exports = { matchDirection, DIRECTIONS };
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/keywordMatcher.test.js
```

Expected: PASS, 7 тестов зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/keywordMatcher.js test/keywordMatcher.test.js
git commit -m "feat: add keyword matcher for 5 service directions"
```

---

### Task 4: Дедуп-стор (JSON, атомарная запись)

**Files:**
- Create: `D:\Projects\scout-agent\src\dedupStore.js`
- Test: `D:\Projects\scout-agent\test\dedupStore.test.js`

**Interfaces:**
- Produces: класс `DedupStore` с методами `has(id: string): boolean`, `add(id: string): void`, `prune(maxAgeDays: number): void`. Конструктор `new DedupStore(filePath: string)`. Используется в Task 8.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/dedupStore.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DedupStore } = require('../src/dedupStore');

test('has() returns false for unseen id, true after add()', () => {
  const filePath = path.join(os.tmpdir(), `dedup-test-${Date.now()}-1.json`);
  const store = new DedupStore(filePath);
  assert.strictEqual(store.has('order-1'), false);
  store.add('order-1');
  assert.strictEqual(store.has('order-1'), true);
  fs.unlinkSync(filePath);
});

test('persists entries across reloads', () => {
  const filePath = path.join(os.tmpdir(), `dedup-test-${Date.now()}-2.json`);
  const store1 = new DedupStore(filePath);
  store1.add('order-2');
  const store2 = new DedupStore(filePath);
  assert.strictEqual(store2.has('order-2'), true);
  fs.unlinkSync(filePath);
});

test('prune removes entries older than maxAgeDays', () => {
  const filePath = path.join(os.tmpdir(), `dedup-test-${Date.now()}-3.json`);
  const store = new DedupStore(filePath);
  store.add('old-order');
  store.entries['old-order'] = Date.now() - 20 * 24 * 60 * 60 * 1000;
  store._save();
  store.prune(14);
  assert.strictEqual(store.has('old-order'), false);
  fs.unlinkSync(filePath);
});

test('prune keeps entries newer than maxAgeDays', () => {
  const filePath = path.join(os.tmpdir(), `dedup-test-${Date.now()}-4.json`);
  const store = new DedupStore(filePath);
  store.add('recent-order');
  store.prune(14);
  assert.strictEqual(store.has('recent-order'), true);
  fs.unlinkSync(filePath);
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/dedupStore.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать dedupStore.js**

```javascript
// src/dedupStore.js
const fs = require('node:fs');
const path = require('node:path');

class DedupStore {
  constructor(filePath) {
    this.filePath = filePath;
    this.entries = this._load();
  }

  _load() {
    if (!fs.existsSync(this.filePath)) return {};
    const raw = fs.readFileSync(this.filePath, 'utf8').trim();
    if (!raw) return {};
    return JSON.parse(raw);
  }

  has(id) {
    return Object.prototype.hasOwnProperty.call(this.entries, id);
  }

  add(id) {
    this.entries[id] = Date.now();
    this._save();
  }

  prune(maxAgeDays) {
    const cutoff = Date.now() - maxAgeDays * 24 * 60 * 60 * 1000;
    for (const [id, ts] of Object.entries(this.entries)) {
      if (ts < cutoff) delete this.entries[id];
    }
    this._save();
  }

  _save() {
    const dir = path.dirname(this.filePath);
    fs.mkdirSync(dir, { recursive: true });
    const tmpPath = `${this.filePath}.tmp`;
    fs.writeFileSync(tmpPath, JSON.stringify(this.entries, null, 2));
    fs.renameSync(tmpPath, this.filePath);
  }
}

module.exports = { DedupStore };
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/dedupStore.test.js
```

Expected: PASS, 4 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/dedupStore.js test/dedupStore.test.js
git commit -m "feat: add dedup store with atomic writes"
```

---

### Task 5: Счётчик подряд идущих сбоев (для правила «не спамить»)

**Files:**
- Create: `D:\Projects\scout-agent\src\failureTracker.js`
- Test: `D:\Projects\scout-agent\test\failureTracker.test.js`

**Interfaces:**
- Produces: `recordFailure(filePath: string, threshold: number): boolean` (true, когда счётчик достиг threshold), `recordSuccess(filePath: string): void` (сбрасывает счётчик в 0). Используется в Task 8.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/failureTracker.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { recordFailure, recordSuccess } = require('../src/failureTracker');

test('recordFailure returns true only once threshold reached', () => {
  const filePath = path.join(os.tmpdir(), `fail-test-${Date.now()}-1.txt`);
  assert.strictEqual(recordFailure(filePath, 3), false);
  assert.strictEqual(recordFailure(filePath, 3), false);
  assert.strictEqual(recordFailure(filePath, 3), true);
  fs.unlinkSync(filePath);
});

test('recordSuccess resets counter', () => {
  const filePath = path.join(os.tmpdir(), `fail-test-${Date.now()}-2.txt`);
  recordFailure(filePath, 3);
  recordFailure(filePath, 3);
  recordSuccess(filePath);
  assert.strictEqual(recordFailure(filePath, 3), false);
  fs.unlinkSync(filePath);
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/failureTracker.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать failureTracker.js**

```javascript
// src/failureTracker.js
const fs = require('node:fs');
const path = require('node:path');

function readCount(filePath) {
  if (!fs.existsSync(filePath)) return 0;
  const raw = fs.readFileSync(filePath, 'utf8').trim();
  return raw ? Number(raw) : 0;
}

function writeCount(filePath, count) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.tmp`;
  fs.writeFileSync(tmpPath, String(count));
  fs.renameSync(tmpPath, filePath);
}

function recordFailure(filePath, threshold) {
  const count = readCount(filePath) + 1;
  writeCount(filePath, count);
  return count >= threshold;
}

function recordSuccess(filePath) {
  writeCount(filePath, 0);
}

module.exports = { recordFailure, recordSuccess };
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/failureTracker.test.js
```

Expected: PASS, 2 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/failureTracker.js test/failureTracker.test.js
git commit -m "feat: add consecutive-failure tracker"
```

---

### Task 6: Telegram-нотификатор (общий с будущим scout-tg)

**Files:**
- Create: `D:\Projects\scout-agent\src\notifier.js`
- Test: `D:\Projects\scout-agent\test\notifier.test.js`

**Interfaces:**
- Produces: `async sendTelegramMessage(botToken: string, chatId: string, text: string): Promise<object>` — POST на `https://api.telegram.org/bot<token>/sendMessage`, бросает `Error` при не-2xx ответе. Используется в Task 8.
- Consumes: глобальный `fetch` (встроен в Node 20).

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/notifier.test.js
const test = require('node:test');
const assert = require('node:assert');
const { sendTelegramMessage } = require('../src/notifier');

test('sends POST to Telegram API with correct body', async () => {
  const calls = [];
  const originalFetch = global.fetch;
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ ok: true }) };
  };
  await sendTelegramMessage('TOKEN', '12345', 'Новый заказ');
  global.fetch = originalFetch;

  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].url, 'https://api.telegram.org/botTOKEN/sendMessage');
  const body = JSON.parse(calls[0].options.body);
  assert.strictEqual(body.chat_id, '12345');
  assert.strictEqual(body.text, 'Новый заказ');
});

test('throws on non-ok response', async () => {
  const originalFetch = global.fetch;
  global.fetch = async () => ({ ok: false, status: 400, text: async () => 'Bad Request' });
  await assert.rejects(() => sendTelegramMessage('TOKEN', '12345', 'text'));
  global.fetch = originalFetch;
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/notifier.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать notifier.js**

```javascript
// src/notifier.js
async function sendTelegramMessage(botToken, chatId, text) {
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Telegram sendMessage failed: ${response.status} ${body}`);
  }
  return response.json();
}

module.exports = { sendTelegramMessage };
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/notifier.test.js
```

Expected: PASS, 2 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/notifier.js test/notifier.test.js
git commit -m "feat: add Telegram notifier"
```

---

### Task 7: RSS-фид FL.ru — получение и парсинг

**Files:**
- Create: `D:\Projects\scout-agent\src\flFeed.js`
- Test: `D:\Projects\scout-agent\test\flFeed.test.js`
- Create: `D:\Projects\scout-agent\fixtures\fl-rss-sample.xml`

**Interfaces:**
- Produces: `parseFlRssItems(xml: string): Array<{id, title, link, description}>`, `async fetchFlRssItems(feedUrl: string): Promise<Array<{id, title, link, description}>>`, константа `FL_RSS_FEEDS: string[]`. Используется в Task 8.
- Consumes: `fast-xml-parser` (`XMLParser`), глобальный `fetch`.

- [ ] **Step 1: Создать тестовую фикстуру**

```xml
<!-- fixtures/fl-rss-sample.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FL.ru — новые проекты</title>
    <item>
      <title>Нужен лендинг для стоматологии</title>
      <link>https://www.fl.ru/projects/1000001/nuzhen-lending.html</link>
      <guid>https://www.fl.ru/projects/1000001/nuzhen-lending.html</guid>
      <description>Бюджет: 15000 руб. Требуется лендинг под рекламу.</description>
    </item>
    <item>
      <title>Дизайн упаковки для конфет</title>
      <link>https://www.fl.ru/projects/1000002/dizayn-upakovki.html</link>
      <guid>https://www.fl.ru/projects/1000002/dizayn-upakovki.html</guid>
      <description>Бюджет по договорённости.</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Написать падающий тест**

```javascript
// test/flFeed.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { parseFlRssItems } = require('../src/flFeed');

test('parses items from sample RSS feed', () => {
  const xml = fs.readFileSync(path.join(__dirname, '../fixtures/fl-rss-sample.xml'), 'utf8');
  const items = parseFlRssItems(xml);
  assert.strictEqual(items.length, 2);
  assert.strictEqual(items[0].title, 'Нужен лендинг для стоматологии');
  assert.strictEqual(items[0].link, 'https://www.fl.ru/projects/1000001/nuzhen-lending.html');
  assert.strictEqual(items[0].id, 'https://www.fl.ru/projects/1000001/nuzhen-lending.html');
});

test('returns empty array when feed has no items', () => {
  const xml = '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>';
  const items = parseFlRssItems(xml);
  assert.deepStrictEqual(items, []);
});

test('handles a single item (not wrapped in array by the XML parser)', () => {
  const xml = `<?xml version="1.0"?><rss version="2.0"><channel><item>
    <title>Единственный заказ</title>
    <link>https://www.fl.ru/projects/1/x.html</link>
    <guid>https://www.fl.ru/projects/1/x.html</guid>
    <description>Текст</description>
  </item></channel></rss>`;
  const items = parseFlRssItems(xml);
  assert.strictEqual(items.length, 1);
  assert.strictEqual(items[0].title, 'Единственный заказ');
});
```

- [ ] **Step 3: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/flFeed.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 4: Реализовать flFeed.js**

```javascript
// src/flFeed.js
const { XMLParser } = require('fast-xml-parser');

// Категории FL.ru для отслеживания. Точные id категорий/подкатегорий
// нужно свериться с текущей структурой fl.ru/projects/ при первом реальном
// запуске (схема "category=X&subcategory=Y" описана в источнике 2019 года,
// см. спеку) — начинаем с широкой категории "Веб-программирование" и
// сужаем при необходимости.
const FL_RSS_FEEDS = ['https://www.fl.ru/rss/all.xml?category=5'];

function parseFlRssItems(xml) {
  const parser = new XMLParser();
  const data = parser.parse(xml);
  const items = data?.rss?.channel?.item;
  if (!items) return [];
  const list = Array.isArray(items) ? items : [items];
  return list.map((item) => {
    const guid = typeof item.guid === 'object' ? item.guid['#text'] : item.guid;
    return {
      id: String(guid ?? item.link ?? ''),
      title: String(item.title ?? ''),
      link: String(item.link ?? ''),
      description: String(item.description ?? ''),
    };
  });
}

async function fetchFlRssItems(feedUrl) {
  const response = await fetch(feedUrl);
  if (!response.ok) {
    throw new Error(`FL.ru RSS fetch failed: ${response.status}`);
  }
  const xml = await response.text();
  return parseFlRssItems(xml);
}

module.exports = { parseFlRssItems, fetchFlRssItems, FL_RSS_FEEDS };
```

- [ ] **Step 5: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/flFeed.test.js
```

Expected: PASS, 3 теста зелёные.

- [ ] **Step 6: Commit**

```bash
git add src/flFeed.js test/flFeed.test.js fixtures/fl-rss-sample.xml
git commit -m "feat: add FL.ru RSS fetch and parse"
```

---

### Task 8: Entrypoint runScoutFl.js — сборка всех модулей

**Files:**
- Create: `D:\Projects\scout-agent\src\runScoutFl.js`
- Test: `D:\Projects\scout-agent\test\runScoutFl.test.js`

**Interfaces:**
- Consumes: `loadEnv` (Task 2), `matchDirection` (Task 3), `DedupStore` (Task 4), `recordFailure`/`recordSuccess` (Task 5), `sendTelegramMessage` (Task 6), `fetchFlRssItems`/`FL_RSS_FEEDS` (Task 7).
- Produces: `async function run(deps): Promise<{ notified: number, anyFeedSucceeded: boolean }>` — принимает объект зависимостей для тестируемости (fetchFlRssItems, sendTelegramMessage, dedup store path, failure file path), плюс `if (require.main === module)` блок для реального запуска из systemd.

- [ ] **Step 1: Написать падающий интеграционный тест**

```javascript
// test/runScoutFl.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { run } = require('../src/runScoutFl');

test('notifies only new, matching items and marks them as seen', async () => {
  const dedupFile = path.join(os.tmpdir(), `scoutfl-dedup-${Date.now()}.json`);
  const failureFile = path.join(os.tmpdir(), `scoutfl-fail-${Date.now()}.txt`);
  const sentMessages = [];

  const result = await run({
    botToken: 'TOKEN',
    chatId: '999',
    dedupFilePath: dedupFile,
    failureFilePath: failureFile,
    feedUrls: ['https://example.invalid/feed1'],
    fetchFlRssItems: async () => [
      { id: 'a', title: 'Нужен лендинг для кафе', link: 'https://x/a', description: '' },
      { id: 'b', title: 'Дизайн упаковки', link: 'https://x/b', description: '' },
    ],
    sendTelegramMessage: async (token, chatId, text) => {
      sentMessages.push({ token, chatId, text });
    },
  });

  assert.strictEqual(result.notified, 1);
  assert.strictEqual(sentMessages.length, 1);
  assert.match(sentMessages[0].text, /Нужен лендинг для кафе/);
  assert.match(sentMessages[0].text, /landing/);

  fs.unlinkSync(dedupFile);
  if (fs.existsSync(failureFile)) fs.unlinkSync(failureFile);
});

test('does not re-notify an already-seen matching item on second run', async () => {
  const dedupFile = path.join(os.tmpdir(), `scoutfl-dedup-${Date.now()}-2.json`);
  const failureFile = path.join(os.tmpdir(), `scoutfl-fail-${Date.now()}-2.txt`);
  const sentMessages = [];
  const deps = {
    botToken: 'TOKEN',
    chatId: '999',
    dedupFilePath: dedupFile,
    failureFilePath: failureFile,
    feedUrls: ['https://example.invalid/feed1'],
    fetchFlRssItems: async () => [
      { id: 'a', title: 'Нужен лендинг для кафе', link: 'https://x/a', description: '' },
    ],
    sendTelegramMessage: async (token, chatId, text) => {
      sentMessages.push({ token, chatId, text });
    },
  };

  await run(deps);
  await run(deps);

  assert.strictEqual(sentMessages.length, 1);

  fs.unlinkSync(dedupFile);
  if (fs.existsSync(failureFile)) fs.unlinkSync(failureFile);
});

test('records failure without throwing when a feed fetch fails', async () => {
  const dedupFile = path.join(os.tmpdir(), `scoutfl-dedup-${Date.now()}-3.json`);
  const failureFile = path.join(os.tmpdir(), `scoutfl-fail-${Date.now()}-3.txt`);

  const result = await run({
    botToken: 'TOKEN',
    chatId: '999',
    dedupFilePath: dedupFile,
    failureFilePath: failureFile,
    feedUrls: ['https://example.invalid/broken'],
    fetchFlRssItems: async () => {
      throw new Error('network down');
    },
    sendTelegramMessage: async () => {},
  });

  assert.strictEqual(result.anyFeedSucceeded, false);

  if (fs.existsSync(dedupFile)) fs.unlinkSync(dedupFile);
  fs.unlinkSync(failureFile);
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/runScoutFl.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать runScoutFl.js**

```javascript
// src/runScoutFl.js
const path = require('node:path');
const { loadEnv } = require('./env');
const { matchDirection } = require('./keywordMatcher');
const { DedupStore } = require('./dedupStore');
const { recordFailure, recordSuccess } = require('./failureTracker');
const { fetchFlRssItems: defaultFetchFlRssItems, FL_RSS_FEEDS } = require('./flFeed');
const { sendTelegramMessage: defaultSendTelegramMessage } = require('./notifier');

const FAILURE_THRESHOLD = 6; // ~1 час при интервале таймера в 10 минут

async function run(deps = {}) {
  const {
    botToken,
    chatId,
    dedupFilePath,
    failureFilePath,
    feedUrls = FL_RSS_FEEDS,
    fetchFlRssItems = defaultFetchFlRssItems,
    sendTelegramMessage = defaultSendTelegramMessage,
  } = deps;

  if (!botToken || !chatId) {
    throw new Error('botToken and chatId are required');
  }

  const store = new DedupStore(dedupFilePath);
  store.prune(14);

  let anyFeedSucceeded = false;
  let notified = 0;

  for (const feedUrl of feedUrls) {
    let items;
    try {
      items = await fetchFlRssItems(feedUrl);
      anyFeedSucceeded = true;
    } catch (err) {
      console.error(`[scout-fl] Failed to fetch ${feedUrl}: ${err.message}`);
      continue;
    }

    for (const item of items) {
      const direction = matchDirection(`${item.title} ${item.description}`);
      if (!direction) continue;
      if (store.has(item.id)) continue;

      const text = [
        `Новый заказ (${direction})`,
        `FL.ru: ${item.title}`,
        item.link,
      ].join('\n');

      await sendTelegramMessage(botToken, chatId, text);
      store.add(item.id);
      notified += 1;
    }
  }

  if (anyFeedSucceeded) {
    recordSuccess(failureFilePath);
  } else {
    const shouldAlert = recordFailure(failureFilePath, FAILURE_THRESHOLD);
    if (shouldAlert) {
      await sendTelegramMessage(
        botToken,
        chatId,
        'Scout: FL.ru недоступен уже больше часа (6 циклов подряд).'
      );
    }
  }

  return { notified, anyFeedSucceeded };
}

module.exports = { run };

if (require.main === module) {
  loadEnv(path.join(__dirname, '..', '.env'));
  run({
    botToken: process.env.BOT_TOKEN,
    chatId: process.env.NOTIFY_CHAT_ID,
    dedupFilePath: path.join(__dirname, '..', 'data', 'seen-fl.json'),
    failureFilePath: path.join(__dirname, '..', 'data', 'fl-failures.txt'),
  })
    .then(({ anyFeedSucceeded }) => process.exit(anyFeedSucceeded ? 0 : 1))
    .catch((err) => {
      console.error(`[scout-fl] Fatal error: ${err.message}`);
      process.exit(1);
    });
}
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/runScoutFl.test.js
```

Expected: PASS, 3 теста зелёные.

- [ ] **Step 5: Прогнать весь набор тестов проекта разом**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/
```

Expected: все тесты всех файлов зелёные (env, keywordMatcher, dedupStore, failureTracker, notifier, flFeed, runScoutFl).

- [ ] **Step 6: Commit**

```bash
git add src/runScoutFl.js test/runScoutFl.test.js
git commit -m "feat: wire modules together into scout-fl entrypoint"
```

---

### Task 9: systemd-юниты, GitHub-репозиторий, runbook для деплоя через Jarvis

**Files:**
- Create: `D:\Projects\scout-agent\deploy\scout-fl.service`
- Create: `D:\Projects\scout-agent\deploy\scout-fl.timer`
- Create: `D:\Projects\scout-agent\deploy\RUNBOOK.md`

**Interfaces:**
- Produces: готовый к деплою репозиторий на GitHub + текстовый runbook, который Александр пересылает Jarvis для выполнения на VPS (прямого SSH-доступа с этой машины к VPS нет — см. Global Constraints).

- [ ] **Step 1: Создать systemd-юнит сервиса (user-level, не системный — под пользователем agent без sudo)**

```ini
# deploy/scout-fl.service
[Unit]
Description=Scout-FL: разовый прогон мониторинга заказов FL.ru

[Service]
Type=oneshot
WorkingDirectory=%h/projects/scout-agent
ExecStart=/usr/bin/node %h/projects/scout-agent/src/runScoutFl.js
```

- [ ] **Step 2: Создать systemd-таймер**

```ini
# deploy/scout-fl.timer
[Unit]
Description=Запускать Scout-FL каждые 10 минут

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Unit=scout-fl.service

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Написать RUNBOOK.md — инструкция для Jarvis**

```markdown
# deploy/RUNBOOK.md

Выполнить на VPS от имени пользователя agent (без sudo — всё
user-level, по аналогии с уже работающим `code-tunnel.service`):

## 1. Клонировать репозиторий

    cd ~/projects
    git clone git@github.com:funnyalexsteam-maker/scout-agent.git
    cd scout-agent
    npm install

## 2. Создать .env с правами 600

    cp .env.example .env
    chmod 600 .env

Заполнить .env:
- BOT_TOKEN — то же значение, что в /home/agent/.agent/bot/.env (значение
  скопировать, файлы не объединять — см. спеку, раздел «Секреты»).
- NOTIFY_CHAT_ID — chat_id Александра в Telegram (тот же чат, в который
  agent-bot обычно отвечает).

## 3. Проверить один прогон вручную

    node src/runScoutFl.js

Ожидается: скрипт завершается без ошибок (exit code 0), при наличии
подходящих заказов в RSS — приходит сообщение в Telegram.

## 4. Установить systemd user-юниты

    mkdir -p ~/.config/systemd/user
    cp deploy/scout-fl.service deploy/scout-fl.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now scout-fl.timer

## 5. Проверить, что таймер держится и без активной SSH-сессии

    loginctl show-user agent | grep Linger

Если `Linger=no` — user-сервисы будут останавливаться при выходе из
сессии. В этом случае нужен `loginctl enable-linger agent` от root
(agent сам это выполнить не может — нет sudo). Скорее всего linger уже
включён, раз `code-tunnel.service` тоже работает как `--user` и переживает
переподключения.

## 6. Проверить логи

    systemctl --user list-timers scout-fl.timer
    journalctl --user -u scout-fl.service -n 50 --no-pager
```

- [ ] **Step 4: Commit**

```bash
cd /d/Projects/scout-agent
git add deploy/scout-fl.service deploy/scout-fl.timer deploy/RUNBOOK.md
git commit -m "chore: add systemd units and deployment runbook"
```

- [ ] **Step 5: Создать GitHub-репозиторий и запушить**

```bash
cd /d/Projects/scout-agent
gh repo create funnyalexsteam-maker/scout-agent --private --source=. --remote=origin
git push -u origin master
```

Expected: репозиторий создан и виден на github.com/funnyalexsteam-maker/scout-agent, все коммиты запушены.

- [ ] **Step 6: Передать RUNBOOK.md Александру для пересылки Jarvis**

Это не автоматизируемый шаг — вывести содержимое `deploy/RUNBOOK.md` в чат и попросить переслать его текстом (или пересказать своими словами) агенту Jarvis в Telegram, так как прямого SSH-доступа с этой машины к VPS нет.

---

## После этого плана

- `scout-tg` (мониторинг Telegram-чатов) — отдельный план, переиспользующий `keywordMatcher.js` и `notifier.js` из этого репозитория. Начинать после того, как этот план задеплоен и проверен в бою хотя бы несколько дней.
- Точные `category`/`subcategory` в `FL_RSS_FEEDS` (Task 7) нужно сверить с реальной структурой fl.ru/projects при первом ручном прогоне (Step 3 из Task 9) — не факт, что `category=5` покрывает все 5 направлений сразу.
