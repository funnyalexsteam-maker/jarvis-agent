# Scout-TG (мониторинг личных Telegram-чатов) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Task 7 is the exception — it requires the user's live participation (a Telegram verification code delivered in real time) and must be executed directly by whoever is running this plan, never dispatched to an autonomous subagent.**

**Goal:** Добавить в существующий проект `scout-agent` второй источник заказов — мониторинг личных Telegram-чатов Александра через MTProto (GramJS), с уведомлением в тот же выделенный бот, что и scout-fl.

**Architecture:** Новые модули (`tgConfig.js`, `tgListener.js`, `listMyChats.js`) в том же репозитории `D:\Projects\scout-agent`, переиспользующие без изменений `keywordMatcher.js`, `notifier.js`, `dedupStore.js`. Тестируемое ядро (`handleIncomingMessage`) отделено от GramJS-обвязки (`start()`) через инъекцию зависимостей — тот же паттерн, что и в `runScoutFl.js`. Деплой — постоянный systemd-сервис (`Restart=always`), а не таймер.

**Tech Stack:** Node.js 20 (та же версия, что уже используется), `telegram` (GramJS, `^2.26.22`) — MTProto-клиент, `input` (`^1.0.1`) — интерактивные промпты для первого входа. Тесты — встроенный `node:test`, как и весь остальной проект.

**Spec:** `docs/superpowers/specs/2026-09-11-scout-tg-design.md`

## Global Constraints

- `keywordMatcher.js`, `notifier.js`, `dedupStore.js` — используются как есть, без изменений интерфейса.
- Секреты `TG_API_ID`/`TG_API_HASH` — только в `.env` (уже гитигнорен), никогда в коде.
- Файл сессии MTProto — `data/tg.session`; `data/` уже полностью гитигнорена (плюс отдельно `*.session` в `.gitignore` — двойная защита).
- `data/tg-chats.json` — список чатов, не в git, по умолчанию отсутствует/пуст (`loadTgChats` возвращает `[]`).
- Уведомления — только факты, в того же бота, что и scout-fl (`BOT_TOKEN`/`NOTIFY_CHAT_ID` — общие с scout-fl, не отдельные).
- Любая запись файла на диск — атомарно (temp + rename), как и во всём остальном проекте.
- Деплой — постоянный `systemd --user` сервис с `Restart=always` (НЕ таймер, в отличие от scout-fl).
- **Task 7 (интерактивный вход) не выполняется автономным субагентом** — требует живого участия пользователя (код из Telegram в реальном времени). Управляющая сессия (controller) выполняет этот шаг сама, напрямую.

---

### Task 1: Вынести sanitizeText в общий модуль

**Files:**
- Create: `D:\Projects\scout-agent\src\textUtils.js`
- Test: `D:\Projects\scout-agent\test\textUtils.test.js`
- Modify: `D:\Projects\scout-agent\src\runScoutFl.js` (убрать локальную `sanitizeDescription`/`MAX_DESCRIPTION_CHARS`, использовать `sanitizeText` из нового модуля)

**Interfaces:**
- Produces: `sanitizeText(text: string, maxChars?: number): string` (по умолчанию `maxChars = 500`) — обрезает HTML-теги, схлопывает пробелы, режет по длине. Используется в Task 3 (`tgListener.js`) и здесь же в обновлённом `runScoutFl.js`.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/textUtils.test.js
const test = require('node:test');
const assert = require('node:assert');
const { sanitizeText } = require('../src/textUtils');

test('strips HTML tags and collapses whitespace', () => {
  const result = sanitizeText('<p>Нужен  лендинг</p><br>срочно');
  assert.strictEqual(result, 'Нужен лендинг срочно');
});

test('truncates to the given max length', () => {
  const long = 'а'.repeat(600);
  const result = sanitizeText(long, 500);
  assert.strictEqual(result.length, 500);
});

test('defaults max length to 500 when not given', () => {
  const long = 'б'.repeat(600);
  const result = sanitizeText(long);
  assert.strictEqual(result.length, 500);
});

test('returns empty string for empty/falsy input', () => {
  assert.strictEqual(sanitizeText(''), '');
  assert.strictEqual(sanitizeText(null), '');
  assert.strictEqual(sanitizeText(undefined), '');
});
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/textUtils.test.js
```

Expected: FAIL — `Cannot find module '../src/textUtils'`.

- [ ] **Step 3: Реализовать textUtils.js**

```javascript
// src/textUtils.js
const DEFAULT_MAX_CHARS = 500;

// Telegram sendMessage ограничивает text 4096 символами. Источники вроде
// FL.ru RSS приходят с раскодированными HTML-сущностями (сырые <p>/<br>
// внутри текста); обычные сообщения из Telegram-чатов таких тегов не
// содержат, но функция общая для обоих источников — чистим на всякий
// случай, схлопываем пробелы и режем по длине.
function sanitizeText(text, maxChars = DEFAULT_MAX_CHARS) {
  if (!text) return '';
  return String(text)
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxChars);
}

module.exports = { sanitizeText, DEFAULT_MAX_CHARS };
```

- [ ] **Step 4: Запустить тест и убедиться, что он проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/textUtils.test.js
```

Expected: PASS, 4 теста зелёные.

- [ ] **Step 5: Обновить runScoutFl.js — использовать sanitizeText**

Открыть `src/runScoutFl.js`. Удалить строки 11 (`const MAX_DESCRIPTION_CHARS = 500;`) и функцию `sanitizeDescription` (строки 16-23), заменить на:

```javascript
const { sanitizeText } = require('./textUtils');
```

(добавить этот `require` в блок импортов вверху файла, рядом с остальными). Заменить единственный вызов `sanitizeDescription(item.description)` (было на строке 72) на `sanitizeText(item.description)`. В `module.exports` (было `module.exports = { run, sanitizeDescription };`) убрать `sanitizeDescription` — снаружи он нигде не используется (проверено: только `{ run }` импортируется в `test/runScoutFl.test.js`):

```javascript
module.exports = { run };
```

- [ ] **Step 6: Прогнать весь существующий набор тестов проекта — регрессий быть не должно**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/
```

Expected: все существующие тесты (36) плюс новые 4 — все зелёные, без регрессий в `runScoutFl.test.js`.

- [ ] **Step 7: Commit**

```bash
git add src/textUtils.js test/textUtils.test.js src/runScoutFl.js
git commit -m "refactor: extract sanitizeText into a shared module"
```

---

### Task 2: Конфиг списка чатов (tgConfig.js)

**Files:**
- Create: `D:\Projects\scout-agent\src\tgConfig.js`
- Test: `D:\Projects\scout-agent\test\tgConfig.test.js`

**Interfaces:**
- Produces: `loadTgChats(filePath: string): Array<string|number>` — возвращает `[]`, если файла нет или он пустой; бросает `Error`, если содержимое не JSON-массив. Используется в Task 4 (`tgListener.js`).

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/tgConfig.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadTgChats } = require('../src/tgConfig');

test('returns empty array when file does not exist', () => {
  const filePath = path.join(os.tmpdir(), `tg-chats-test-${Date.now()}-missing.json`);
  assert.deepStrictEqual(loadTgChats(filePath), []);
});

test('returns empty array when file is empty', () => {
  const filePath = path.join(os.tmpdir(), `tg-chats-test-${Date.now()}-empty.json`);
  fs.writeFileSync(filePath, '');
  assert.deepStrictEqual(loadTgChats(filePath), []);
  fs.unlinkSync(filePath);
});

test('parses a JSON array of chat identifiers', () => {
  const filePath = path.join(os.tmpdir(), `tg-chats-test-${Date.now()}.json`);
  fs.writeFileSync(filePath, JSON.stringify(['@freelance_orders_chat', -1001234567890]));
  const result = loadTgChats(filePath);
  assert.deepStrictEqual(result, ['@freelance_orders_chat', -1001234567890]);
  fs.unlinkSync(filePath);
});

test('throws a clear error when the file is not a JSON array', () => {
  const filePath = path.join(os.tmpdir(), `tg-chats-test-${Date.now()}-bad.json`);
  fs.writeFileSync(filePath, JSON.stringify({ not: 'an array' }));
  assert.throws(() => loadTgChats(filePath), /must contain a JSON array/);
  fs.unlinkSync(filePath);
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgConfig.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать tgConfig.js**

```javascript
// src/tgConfig.js
const fs = require('node:fs');

// Список чатов для мониторинга — не в git (папка data/ гитигнорена
// целиком). По умолчанию пустой: сервис стартует и ничего не слушает,
// пока чаты не добавят вручную.
function loadTgChats(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, 'utf8').trim();
  if (!raw) return [];
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`${filePath} must contain a JSON array of chat identifiers`);
  }
  return parsed;
}

module.exports = { loadTgChats };
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgConfig.test.js
```

Expected: PASS, 4 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/tgConfig.js test/tgConfig.test.js
git commit -m "feat: add tg-chats.json loader"
```

---

### Task 3: Ядро обработки сообщения (handleIncomingMessage)

**Files:**
- Create: `D:\Projects\scout-agent\src\tgListener.js` (только `handleIncomingMessage` в этой задаче — `start()` добавляется в Task 4)
- Test: `D:\Projects\scout-agent\test\tgListener.test.js` (только тесты `handleIncomingMessage` в этой задаче)

**Interfaces:**
- Consumes: `matchDirection` (`./keywordMatcher`), `sanitizeText` (`./textUtils`, Task 1).
- Produces: `async handleIncomingMessage(info: {chatId, messageId, chatTitle, text}, deps: {store, botToken, notifyChatId, sendTelegramMessage}): Promise<{notified: boolean}>`. Дедуп-ключ — `` `${chatId}:${messageId}` ``. Используется в Task 4 (`start()`) и переиспользует интерфейс `DedupStore` (`.has(key)`/`.add(key)`) без изменений.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/tgListener.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { handleIncomingMessage } = require('../src/tgListener');
const { DedupStore } = require('../src/dedupStore');

test('notifies on a new matching message and marks it seen', async () => {
  const dedupFile = path.join(os.tmpdir(), `tg-handle-${Date.now()}-1.json`);
  const store = new DedupStore(dedupFile);
  const sent = [];

  const result = await handleIncomingMessage(
    { chatId: '111', messageId: 5, chatTitle: 'Заказы', text: 'Нужен телеграм-бот для магазина' },
    {
      store,
      botToken: 'TOKEN',
      notifyChatId: '999',
      sendTelegramMessage: async (t, c, txt) => sent.push({ t, c, txt }),
    }
  );

  assert.strictEqual(result.notified, true);
  assert.strictEqual(sent.length, 1);
  assert.match(sent[0].txt, /bots/);
  assert.match(sent[0].txt, /Заказы/);
  assert.strictEqual(store.has('111:5'), true);

  fs.unlinkSync(dedupFile);
});

test('does not notify for text matching no direction', async () => {
  const dedupFile = path.join(os.tmpdir(), `tg-handle-${Date.now()}-2.json`);
  const store = new DedupStore(dedupFile);
  const sent = [];

  const result = await handleIncomingMessage(
    { chatId: '111', messageId: 6, chatTitle: 'Заказы', text: 'Продам б/у ноутбук' },
    { store, botToken: 'TOKEN', notifyChatId: '999', sendTelegramMessage: async (t, c, txt) => sent.push({ t, c, txt }) }
  );

  assert.strictEqual(result.notified, false);
  assert.strictEqual(sent.length, 0);

  fs.unlinkSync(dedupFile);
});

test('does not re-notify an already-seen (chatId, messageId) pair', async () => {
  const dedupFile = path.join(os.tmpdir(), `tg-handle-${Date.now()}-3.json`);
  const store = new DedupStore(dedupFile);
  store.add('111:7');
  const sent = [];

  const result = await handleIncomingMessage(
    { chatId: '111', messageId: 7, chatTitle: 'Заказы', text: 'Нужен лендинг' },
    { store, botToken: 'TOKEN', notifyChatId: '999', sendTelegramMessage: async (t, c, txt) => sent.push({ t, c, txt }) }
  );

  assert.strictEqual(result.notified, false);
  assert.strictEqual(sent.length, 0);

  fs.unlinkSync(dedupFile);
});

test('does not mark as seen when sendTelegramMessage fails', async () => {
  const dedupFile = path.join(os.tmpdir(), `tg-handle-${Date.now()}-4.json`);
  const store = new DedupStore(dedupFile);

  const result = await handleIncomingMessage(
    { chatId: '111', messageId: 8, chatTitle: 'Заказы', text: 'Нужен лендинг' },
    {
      store,
      botToken: 'TOKEN',
      notifyChatId: '999',
      sendTelegramMessage: async () => {
        throw new Error('network down');
      },
    }
  );

  assert.strictEqual(result.notified, false);
  assert.strictEqual(store.has('111:8'), false);

  fs.unlinkSync(dedupFile);
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgListener.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать handleIncomingMessage в src/tgListener.js**

```javascript
// src/tgListener.js
const { matchDirection } = require('./keywordMatcher');
const { sendTelegramMessage: defaultSendTelegramMessage } = require('./notifier');
const { sanitizeText } = require('./textUtils');

// Тестируемое ядро: получает уже извлечённые данные о сообщении, решает,
// нужно ли уведомлять. Ничего не знает про GramJS — этим занимается
// start() (Task 4).
async function handleIncomingMessage(info, deps) {
  const { chatId, messageId, chatTitle, text } = info;
  const { store, botToken, notifyChatId, sendTelegramMessage } = deps;

  const direction = matchDirection(text || '');
  if (!direction) return { notified: false };

  const dedupKey = `${chatId}:${messageId}`;
  if (store.has(dedupKey)) return { notified: false };

  const lines = [`Новый заказ (${direction})`, `Чат: ${chatTitle}`];
  const body = sanitizeText(text);
  if (body) lines.push(body);

  try {
    await sendTelegramMessage(botToken, notifyChatId, lines.join('\n'));
  } catch (err) {
    // Не помечаем как seen — сообщение будет рассмотрено заново, если
    // GramJS повторно доставит событие после переподключения.
    console.error(`[scout-tg] Failed to notify about ${dedupKey}: ${err.message}`);
    return { notified: false };
  }
  store.add(dedupKey);
  return { notified: true };
}

module.exports = { handleIncomingMessage };
```

(`defaultSendTelegramMessage` пока не используется — он понадобится в Task 4 и уже импортирован здесь заранее, чтобы Task 4 не переписывал этот блок импортов. Если линтер/тест ругается на неиспользуемый импорт — это ожидаемо и временно, Task 4 его использует.)

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgListener.test.js
```

Expected: PASS, 4 теста зелёные.

- [ ] **Step 5: Commit**

```bash
git add src/tgListener.js test/tgListener.test.js
git commit -m "feat: add handleIncomingMessage core logic for scout-tg"
```

---

### Task 4: GramJS-обвязка (start + createClient)

**Files:**
- Modify: `D:\Projects\scout-agent\src\tgListener.js` (добавить `start()`, `defaultCreateClient`, экспорт `createClient`, блок `require.main === module`)
- Modify: `D:\Projects\scout-agent\test\tgListener.test.js` (добавить тесты `start()`)
- Modify: `D:\Projects\scout-agent\package.json` (добавить зависимости `telegram`, `input`)

**Interfaces:**
- Consumes: `loadTgChats` (`./tgConfig`, Task 2), `loadEnv` (`./env`), `DedupStore` (`./dedupStore`), `handleIncomingMessage` (эта же задача, Task 3).
- Produces: `async start(deps): Promise<Client>` — `deps` включает `botToken, notifyChatId, sessionFilePath, tgChatsFilePath, apiId, apiHash, store, createClient?, sendTelegramMessage?`; бросает `Error`, если `botToken`/`notifyChatId` или `apiId`/`apiHash` не заданы. `createClient(opts: {apiId, apiHash, sessionFilePath}): Promise<Client>` — экспортируется отдельно, переиспользуется в Task 5 (`listMyChats.js`).

- [ ] **Step 1: Добавить зависимости в package.json**

Открыть `package.json`, добавить в `dependencies` (рядом с `fast-xml-parser`):

```json
    "input": "^1.0.1",
    "telegram": "^2.26.22"
```

И добавить в `scripts`:

```json
    "scout-tg": "node src/tgListener.js"
```

Установить:

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/npm.cmd" install
```

Expected: `node_modules/telegram` и `node_modules/input` появились, `package-lock.json` обновился, без ошибок. Если версии `^2.26.22`/`^1.0.1` больше недоступны — взять актуальные из `npm view telegram version` / `npm view input version` и использовать их вместо этих.

- [ ] **Step 2: Написать падающие тесты для start()**

Добавить в конец `test/tgListener.test.js` (после существующих тестов `handleIncomingMessage`, не удаляя их):

```javascript
const { start } = require('../src/tgListener');

test('start() throws when required config is missing', async () => {
  await assert.rejects(() => start({}), /botToken and notifyChatId are required/);
  await assert.rejects(
    () => start({ botToken: 'x', notifyChatId: 'y' }),
    /apiId and apiHash are required/
  );
});

test('start() registers a handler that notifies on a matching new message', async () => {
  const tgChatsFile = path.join(os.tmpdir(), `tg-chats-start-${Date.now()}.json`);
  fs.writeFileSync(tgChatsFile, JSON.stringify(['@test_chat']));

  let registeredCallback;
  const fakeClient = {
    addEventHandler: (callback) => {
      registeredCallback = callback;
    },
  };

  const sent = [];
  const dedupFile = path.join(os.tmpdir(), `tg-dedup-start-${Date.now()}.json`);
  const store = new DedupStore(dedupFile);

  const returnedClient = await start({
    botToken: 'TOKEN',
    notifyChatId: '999',
    apiId: '123',
    apiHash: 'hash',
    sessionFilePath: path.join(os.tmpdir(), 'unused.session'),
    tgChatsFilePath: tgChatsFile,
    store,
    createClient: async () => fakeClient,
    sendTelegramMessage: async (t, c, txt) => sent.push({ t, c, txt }),
  });

  assert.strictEqual(returnedClient, fakeClient);
  assert.strictEqual(typeof registeredCallback, 'function');

  await registeredCallback({
    message: {
      chatId: 'abc',
      id: 42,
      chat: { title: 'Заказы Фриланс' },
      message: 'Нужен лендинг срочно',
    },
  });

  assert.strictEqual(sent.length, 1);
  assert.match(sent[0].txt, /landing/);
  assert.match(sent[0].txt, /Заказы Фриланс/);

  fs.unlinkSync(tgChatsFile);
  fs.unlinkSync(dedupFile);
});

test('start() works with zero configured chats (no file)', async () => {
  const tgChatsFile = path.join(os.tmpdir(), `tg-chats-empty-${Date.now()}.json`);
  // Файл намеренно не создаём — loadTgChats должен вернуть [].
  const fakeClient = { addEventHandler: () => {} };
  const dedupFile = path.join(os.tmpdir(), `tg-dedup-empty-${Date.now()}.json`);

  const client = await start({
    botToken: 'TOKEN',
    notifyChatId: '999',
    apiId: '123',
    apiHash: 'hash',
    sessionFilePath: path.join(os.tmpdir(), 'unused2.session'),
    tgChatsFilePath: tgChatsFile,
    store: new DedupStore(dedupFile),
    createClient: async () => fakeClient,
    sendTelegramMessage: async () => {},
  });

  assert.strictEqual(client, fakeClient);

  if (fs.existsSync(dedupFile)) fs.unlinkSync(dedupFile);
});
```

- [ ] **Step 3: Запустить и убедиться, что новые тесты падают**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgListener.test.js
```

Expected: FAIL — `start` не экспортируется / не определена.

- [ ] **Step 4: Дописать start(), defaultCreateClient и блок main в src/tgListener.js**

Добавить в конец `src/tgListener.js` (после `handleIncomingMessage`, перед `module.exports`):

```javascript
const path = require('node:path');
const fs = require('node:fs');
const { loadEnv } = require('./env');
const { DedupStore } = require('./dedupStore');
const { loadTgChats } = require('./tgConfig');

// Вынесено отдельно, чтобы не тянуть класс NewMessage при тестировании
// с фейковым client — require происходит только внутри функции.
function buildNewMessageFilter(chats) {
  const { NewMessage } = require('telegram/events');
  return chats.length > 0 ? new NewMessage({ chats }) : new NewMessage({});
}

async function defaultCreateClient({ apiId, apiHash, sessionFilePath }) {
  const { TelegramClient } = require('telegram');
  const { StringSession } = require('telegram/sessions');
  const input = require('input');

  const savedSession = fs.existsSync(sessionFilePath)
    ? fs.readFileSync(sessionFilePath, 'utf8').trim()
    : '';

  const client = new TelegramClient(new StringSession(savedSession), Number(apiId), apiHash, {
    connectionRetries: 5,
  });

  await client.start({
    phoneNumber: async () => input.text('Номер телефона (с кодом страны, например +7...): '),
    password: async () => input.text('Пароль 2FA (если не включён — просто Enter): '),
    phoneCode: async () => input.text('Код из Telegram: '),
    onError: (err) => console.error(`[scout-tg] Ошибка авторизации: ${err.message}`),
  });

  const sessionString = client.session.save();
  fs.mkdirSync(path.dirname(sessionFilePath), { recursive: true });
  const tmpPath = `${sessionFilePath}.tmp`;
  fs.writeFileSync(tmpPath, sessionString);
  fs.renameSync(tmpPath, sessionFilePath);

  return client;
}

// Реальная точка входа: поднимает MTProto-клиент, слушает чаты из
// data/tg-chats.json. createClient/sendTelegramMessage инъецируются для
// тестируемости.
async function start(deps = {}) {
  const {
    botToken,
    notifyChatId,
    sessionFilePath,
    tgChatsFilePath,
    apiId,
    apiHash,
    store,
    createClient = defaultCreateClient,
    sendTelegramMessage = defaultSendTelegramMessage,
  } = deps;

  if (!botToken || !notifyChatId) {
    throw new Error('botToken and notifyChatId are required');
  }
  if (!apiId || !apiHash) {
    throw new Error('apiId and apiHash are required (TG_API_ID/TG_API_HASH in .env)');
  }

  const chats = loadTgChats(tgChatsFilePath);
  if (chats.length === 0) {
    console.log('[scout-tg] data/tg-chats.json пуст — сервис запущен, но не слушает ни одного чата.');
  } else {
    console.log(`[scout-tg] Слушаю ${chats.length} чат(ов).`);
  }

  const client = await createClient({ apiId, apiHash, sessionFilePath });

  client.addEventHandler(async (event) => {
    const message = event.message;
    if (!message) return;
    const chatId = String(message.chatId ?? message.peerId ?? '');
    const info = {
      chatId,
      messageId: message.id,
      chatTitle: (message.chat && (message.chat.title || message.chat.username)) || chatId,
      text: message.message || '',
    };
    await handleIncomingMessage(info, { store, botToken, notifyChatId, sendTelegramMessage });
  }, buildNewMessageFilter(chats));

  return client;
}
```

Заменить `module.exports = { handleIncomingMessage };` на:

```javascript
module.exports = { handleIncomingMessage, start, createClient: defaultCreateClient };

if (require.main === module) {
  const envPath = path.join(__dirname, '..', '.env');
  loadEnv(envPath);

  start({
    botToken: process.env.BOT_TOKEN,
    notifyChatId: process.env.NOTIFY_CHAT_ID,
    apiId: process.env.TG_API_ID,
    apiHash: process.env.TG_API_HASH,
    sessionFilePath: path.join(__dirname, '..', 'data', 'tg.session'),
    tgChatsFilePath: path.join(__dirname, '..', 'data', 'tg-chats.json'),
    store: new DedupStore(path.join(__dirname, '..', 'data', 'seen-tg.json')),
  }).catch((err) => {
    console.error(`[scout-tg] Fatal error: ${err.message}`);
    process.exitCode = 1;
  });
}
```

- [ ] **Step 5: Запустить и убедиться, что все тесты tgListener проходят**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/tgListener.test.js
```

Expected: PASS, все 7 тестов (4 из Task 3 + 3 новых) зелёные.

- [ ] **Step 6: Прогнать весь набор тестов проекта**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/
```

Expected: все тесты всех файлов зелёные, без регрессий.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json src/tgListener.js test/tgListener.test.js
git commit -m "feat: add GramJS wiring (start/createClient) for scout-tg"
```

---

### Task 5: Вспомогательный скрипт listMyChats.js

**Files:**
- Create: `D:\Projects\scout-agent\src\listMyChats.js`
- Test: `D:\Projects\scout-agent\test\listMyChats.test.js`

**Interfaces:**
- Consumes: `createClient` (экспортировано из `./tgListener`, Task 4).
- Produces: `async listChats(deps: {createClient?, apiId, apiHash, sessionFilePath}): Promise<Array<{id: string, title: string, isGroup: boolean, isChannel: boolean}>>`.

- [ ] **Step 1: Написать падающий тест**

```javascript
// test/listMyChats.test.js
const test = require('node:test');
const assert = require('node:assert');
const { listChats } = require('../src/listMyChats');

test('maps dialogs into id/title/type entries', async () => {
  const fakeClient = {
    getDialogs: async () => [
      { id: { toString: () => '-1001234567890' }, title: 'Заказы Фриланс', isGroup: true, isChannel: false },
      { id: 123456, name: 'Личный чат', isGroup: false, isChannel: false },
    ],
  };

  const result = await listChats({
    createClient: async () => fakeClient,
    apiId: '1',
    apiHash: 'h',
    sessionFilePath: '/tmp/unused.session',
  });

  assert.deepStrictEqual(result, [
    { id: '-1001234567890', title: 'Заказы Фриланс', isGroup: true, isChannel: false },
    { id: '123456', title: 'Личный чат', isGroup: false, isChannel: false },
  ]);
});

test('falls back to "(без названия)" when title and name are both missing', async () => {
  const fakeClient = {
    getDialogs: async () => [{ id: 1, isGroup: false, isChannel: true }],
  };

  const result = await listChats({
    createClient: async () => fakeClient,
    apiId: '1',
    apiHash: 'h',
    sessionFilePath: '/tmp/unused.session',
  });

  assert.strictEqual(result[0].title, '(без названия)');
});
```

- [ ] **Step 2: Запустить и убедиться, что падает**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/listMyChats.test.js
```

Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать listMyChats.js**

```javascript
// src/listMyChats.js
// Разовый вспомогательный скрипт: выводит все чаты, где состоит аккаунт,
// с их ID и названием/юзернеймом — нужен, чтобы найти chat ID приватной
// группы без публичного юзернейма для data/tg-chats.json.
const path = require('node:path');
const { loadEnv } = require('./env');

async function listChats(deps = {}) {
  const { createClient = defaultCreateClient, apiId, apiHash, sessionFilePath } = deps;
  const client = await createClient({ apiId, apiHash, sessionFilePath });
  const dialogs = await client.getDialogs();
  return dialogs.map((d) => ({
    id: d.id && typeof d.id.toString === 'function' ? d.id.toString() : String(d.id),
    title: d.title || d.name || '(без названия)',
    isGroup: !!d.isGroup,
    isChannel: !!d.isChannel,
  }));
}

// Переиспользует ту же логику подключения/сессии, что и tgListener.js —
// сессия должна быть уже создана первым (интерактивным) запуском
// tgListener.js, здесь только чтение.
async function defaultCreateClient(opts) {
  const { createClient } = require('./tgListener');
  return createClient(opts);
}

module.exports = { listChats };

if (require.main === module) {
  loadEnv(path.join(__dirname, '..', '.env'));
  listChats({
    apiId: process.env.TG_API_ID,
    apiHash: process.env.TG_API_HASH,
    sessionFilePath: path.join(__dirname, '..', 'data', 'tg.session'),
  })
    .then((chats) => {
      for (const c of chats) {
        const type = c.isGroup ? 'group' : c.isChannel ? 'channel' : 'chat';
        console.log(`${c.id}\t${type}\t${c.title}`);
      }
      process.exitCode = 0;
    })
    .catch((err) => {
      console.error(`[list-my-chats] Fatal error: ${err.message}`);
      process.exitCode = 1;
    });
}
```

- [ ] **Step 4: Запустить и убедиться, что проходит**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/listMyChats.test.js
```

Expected: PASS, 2 теста зелёные.

- [ ] **Step 5: Прогнать весь набор тестов проекта**

```bash
cd /d/Projects/scout-agent
"/d/Tools/node-v20.18.1-win-x64/node.exe" --test test/
```

Expected: все тесты всех файлов зелёные, без единого регресса относительно предыдущих задач (точное количество не фиксируем — важно, что ни один существующий тест не сломался и все новые проходят).

- [ ] **Step 6: Commit**

```bash
git add src/listMyChats.js test/listMyChats.test.js
git commit -m "feat: add listMyChats helper for finding chat IDs"
```

---

### Task 6: Deploy-артефакты и .env.example

**Files:**
- Create: `D:\Projects\scout-agent\deploy\scout-tg.service`
- Create: `D:\Projects\scout-agent\deploy\RUNBOOK-tg.md`
- Modify: `D:\Projects\scout-agent\.env.example`

**Interfaces:**
- Produces: готовый к установке systemd-юнит и runbook для Task 7.

- [ ] **Step 1: Создать systemd-юнит (постоянный сервис, не таймер)**

```ini
# deploy/scout-tg.service
[Unit]
Description=Scout-TG: мониторинг личных Telegram-чатов на заказы

[Service]
Type=simple
Restart=always
RestartSec=10
WorkingDirectory=%h/projects/scout-agent
ExecStart=/usr/bin/node %h/projects/scout-agent/src/tgListener.js

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Обновить .env.example**

Текущее содержимое (`BOT_TOKEN=`, `NOTIFY_CHAT_ID=`) дополнить:

```
BOT_TOKEN=
NOTIFY_CHAT_ID=
TG_API_ID=
TG_API_HASH=
```

- [ ] **Step 3: Написать RUNBOOK-tg.md**

```markdown
# deploy/RUNBOOK-tg.md

Второй компонент Scout — мониторинг личных Telegram-чатов. В отличие от
scout-fl, требует один интерактивный шаг (авторизация MTProto) и
выполняется в связке: Александр (номер телефона, код, my.telegram.org)
+ тот, кто выполняет этот runbook (Claude Code через SSH+tmux, или
Jarvis).

## 1. Получить TG_API_ID / TG_API_HASH

Только Александр может это сделать (нужен вход под своим номером):
1. Открыть https://my.telegram.org, войти по номеру телефона.
2. API development tools → создать приложение (любое название/платформа).
3. Скопировать `api_id` и `api_hash`.

## 2. Обновить репозиторий и .env

    cd ~/projects/scout-agent
    git pull
    npm install

Дописать в существующий `.env` (права уже 600, файл не пересоздавать):

    TG_API_ID=<значение из шага 1>
    TG_API_HASH=<значение из шага 1>

## 3. Интерактивный вход (разовый, через tmux)

Выполняется вместе с Александром — Telegram пришлёт код подтверждения
в приложение, его нужно ввести сразу же:

    tmux new -s scout-tg-login
    node src/tgListener.js

Скрипт спросит номер телефона, код из Telegram (и пароль 2FA, если
включён). После успешного входа сессия сохранится в `data/tg.session`
— этот шаг больше не повторится, пока файл сессии существует и валиден.
Остановить скрипт (Ctrl+C) — на этом этапе он больше не нужен, дальше
он будет жить как systemd-сервис.

## 4. Установить systemd-сервис

    mkdir -p ~/.config/systemd/user
    cp deploy/scout-tg.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now scout-tg.service
    systemctl --user status scout-tg.service --no-pager

Ожидается: `Active: active (running)`, в логе строка вида
`[scout-tg] data/tg-chats.json пуст — сервис запущен, но не слушает ни
одного чата.` (или `Слушаю N чат(ов).`, если чаты уже добавлены).

## 5. Добавить чат для мониторинга

    node src/listMyChats.js

Выведет список всех чатов аккаунта с ID. Выбрать нужный (юзернейм
`@some_chat`, если публичный, иначе числовой ID из списка), дописать в
`data/tg-chats.json`:

    ["@freelance_orders_chat"]

Перезапустить, чтобы список подхватился:

    systemctl --user restart scout-tg.service
    journalctl --user -u scout-tg.service -n 20 --no-pager
```

- [ ] **Step 4: Commit и push**

```bash
cd /d/Projects/scout-agent
git add deploy/scout-tg.service deploy/RUNBOOK-tg.md .env.example
git commit -m "chore: add scout-tg systemd unit and deployment runbook"
git push origin master
```

---

### Task 7 (ручная, НЕ для автономного субагента): Деплой на VPS

Эта задача требует живого участия Александра (код из Telegram приходит
в реальном времени) и выполняется управляющей сессией (controller)
напрямую по шагам `deploy/RUNBOOK-tg.md`, через SSH-алиас `scout-vps` —
не как обычная TDD-задача с падающим/проходящим тестом.

- [ ] Выполнить шаги 1-2 RUNBOOK-tg.md (Александр добывает `TG_API_ID`/`TG_API_HASH`, controller обновляет `.env` на сервере).
- [ ] Выполнить шаг 3 — интерактивный вход через `tmux` на VPS вместе с Александром (номер телефона, код, пароль 2FA при наличии).
- [ ] Выполнить шаг 4 — установить и включить `scout-tg.service`, убедиться, что `systemctl --user status` показывает `active (running)`.
- [ ] Проверить журнал (`journalctl --user -u scout-tg.service -n 20`) — сервис стартовал без ошибок, залогировал, что чатов пока 0.
- [ ] Список чатов (шаг 5) оставить пустым до отдельного запроса Александра — это его ручная задача (найти и вступить в чаты), не часть этого плана.

---

## После этого плана

- Наполнение `data/tg-chats.json` реальными чатами — отдельная задача по запросу Александра, когда он найдёт и вступит в подходящие чаты.
- Если объём совпадений из чатов окажется большим — рассмотреть отдельный дедуп-файл на чат вместо одного общего `seen-tg.json` (сейчас не требуется, YAGNI).
