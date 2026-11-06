/**
 * track 云函数的单元测试：mock wx-server-sdk，不需要微信云环境。
 * 运行（在 wechat-miniprogram/ 目录下）：node tests/track.test.js
 */
const assert = require('node:assert');
const path = require('node:path');
const Module = require('node:module');

// 记录 add 写入的集合名与数据，用于断言只存 { _openid, type, ts }、不存通知内容
const writes = [];
const fakeSdk = {
  DYNAMIC_CURRENT_ENV: 'dynamic-env',
  init() {},
  getWXContext() {
    return { OPENID: 'test-openid' };
  },
  database() {
    return {
      collection(name) {
        return {
          add({ data }) {
            writes.push({ collection: name, data });
            return Promise.resolve({ _id: 'mock-id' });
          },
        };
      },
    };
  },
};

// 拦截 require('wx-server-sdk')，避免依赖真实 SDK 与云环境
const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === 'wx-server-sdk') return fakeSdk;
  return originalLoad.apply(this, arguments);
};

const track = require(path.join(__dirname, '..', 'cloudfunctions', 'track', 'index.js'));

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
  await test('todo_click 被接受，写入 events 集合', async () => {
    writes.length = 0;
    const r = await track.main({ type: 'todo_click' });
    assert.deepStrictEqual(r, { ok: true });
    assert.strictEqual(writes.length, 1);
    assert.strictEqual(writes[0].collection, 'events');
    assert.strictEqual(writes[0].data.type, 'todo_click');
  });

  await test('只存 { _openid, type, ts }，即使调用方传了通知内容也不落库', async () => {
    writes.length = 0;
    await track.main({
      type: 'todo_click',
      text: '明天 15:00 开班会',
      result: { title: '班会', location: '教一 101' },
    });
    const data = writes[0].data;
    assert.deepStrictEqual(Object.keys(data).sort(), ['_openid', 'ts', 'type']);
    assert.strictEqual(data._openid, 'test-openid');
    assert.ok(typeof data.ts === 'number');
  });

  await test('原有 open/extract/copy 类型仍被接受', async () => {
    for (const t of ['open', 'extract', 'copy']) {
      writes.length = 0;
      const r = await track.main({ type: t });
      assert.deepStrictEqual(r, { ok: true });
      assert.strictEqual(writes[0].data.type, t);
    }
  });

  await test('未知类型或缺 type 返回 BAD_TYPE 且不写库', async () => {
    for (const ev of [{ type: 'todo' }, { type: '' }, {}, null, undefined]) {
      writes.length = 0;
      const r = await track.main(ev);
      assert.deepStrictEqual(r, { ok: false, code: 'BAD_TYPE', message: '无效的事件类型' });
      assert.strictEqual(writes.length, 0);
    }
  });

  console.log(`\n全部通过：${passed} 个测试`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
