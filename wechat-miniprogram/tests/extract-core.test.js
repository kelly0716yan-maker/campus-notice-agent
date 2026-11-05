/**
 * extract 云函数核心逻辑的单元测试：不需要微信云环境和 API Key（mock transport）。
 * 运行（在 wechat-miniprogram/ 目录下）：node tests/extract-core.test.js
 */
const assert = require('node:assert');
const path = require('node:path');
const core = require(path.join(__dirname, '..', 'cloudfunctions', 'extract', 'core.js'));

let passed = 0;

async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`✓ ${name}`);
  } catch (e) {
    console.error(`✗ ${name}`);
    throw e;
  }
}

async function main() {
  await test('validate：空文本返回 EMPTY', () => {
    assert.strictEqual(core.validate('').code, 'EMPTY');
    assert.strictEqual(core.validate('   ').code, 'EMPTY');
    assert.strictEqual(core.validate(undefined).code, 'EMPTY');
  });

  await test('validate：超过 3000 字返回 TOO_LONG', () => {
    assert.strictEqual(core.validate('a'.repeat(3001)).code, 'TOO_LONG');
    assert.strictEqual(core.validate('a'.repeat(3000)), null);
  });

  await test('normalizeDate：合法格式原样返回，非法格式退回本地日期', () => {
    assert.strictEqual(core.normalizeDate('2026-11-05'), '2026-11-05');
    assert.match(core.normalizeDate('2026/11/05'), /^\d{4}-\d{2}-\d{2}$/);
    assert.match(core.normalizeDate(undefined), /^\d{4}-\d{2}-\d{2}$/);
  });

  await test('buildPayload：参数与 user 消息格式和 spec 一致', () => {
    const p = core.buildPayload('2026-11-05', '开班会');
    assert.strictEqual(p.messages[1].content, '今天日期：2026-11-05\n通知来源：未知\n通知原文：\n开班会');
    assert.strictEqual(p.model, 'deepseek-chat');
    assert.strictEqual(p.temperature, 0);
    assert.strictEqual(p.max_tokens, 800);
    assert.deepStrictEqual(p.response_format, { type: 'json_object' });
  });

  await test('parseResult：完整 JSON 原样解析', () => {
    const r = core.parseResult(
      JSON.stringify({ title: 't', event_time: 'e', deadline: 'd', location: 'l', audience: 'a', action: 'x', evidence: 'v' })
    );
    assert.deepStrictEqual(r, { title: 't', event_time: 'e', deadline: 'd', location: 'l', audience: 'a', action: 'x', evidence: 'v' });
  });

  await test('parseResult：缺失/空字段补“未提及”', () => {
    const r = core.parseResult(JSON.stringify({ title: 't' }));
    assert.strictEqual(r.title, 't');
    for (const f of core.FIELDS.slice(1)) assert.strictEqual(r[f], '未提及');
    assert.strictEqual(core.parseResult('{"title": ""}').title, '未提及');
  });

  await test('parseResult：非 JSON 或非对象抛错', () => {
    assert.throws(() => core.parseResult('不是 JSON'));
    assert.throws(() => core.parseResult('[1,2]'));
    assert.throws(() => core.parseResult('"字符串"'));
  });

  await test('extractWithRetry：第一次解析失败、第二次成功（共 2 次调用）', async () => {
    let calls = 0;
    const transport = async () => {
      calls++;
      if (calls === 1) return '不是 JSON';
      return JSON.stringify({ title: 'ok' });
    };
    const r = await core.extractWithRetry('k', {}, transport);
    assert.strictEqual(r.title, 'ok');
    assert.strictEqual(calls, 2);
  });

  await test('extractWithRetry：两次都解析失败则抛错', async () => {
    const transport = async () => '不是 JSON';
    await assert.rejects(() => core.extractWithRetry('k', {}, transport));
  });

  await test('extractWithRetry：API 错误不重试、直接抛出（只调 1 次）', async () => {
    let calls = 0;
    const err = Object.assign(new Error('api down'), { isApiError: true });
    const transport = async () => {
      calls++;
      throw err;
    };
    await assert.rejects(() => core.extractWithRetry('k', {}, transport), (e) => e === err);
    assert.strictEqual(calls, 1);
  });

  await test('prompt.js：加载成功且包含 7 个字段说明', () => {
    const prompt = require(path.join(__dirname, '..', 'cloudfunctions', 'extract', 'prompt.js'));
    assert.strictEqual(typeof prompt, 'string');
    for (const f of core.FIELDS) {
      assert.ok(prompt.includes(`- ${f}:`), `prompt 缺少字段 ${f}`);
    }
  });

  console.log(`\n全部通过：${passed} 个测试`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
