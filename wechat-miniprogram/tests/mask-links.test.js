/**
 * 前端发送前链接遮罩（maskLinks）的单元测试：不需要微信环境和 API Key。
 * 运行（在 wechat-miniprogram/ 目录下）：node tests/mask-links.test.js
 */
const assert = require('node:assert');
const path = require('node:path');
const { maskLinks } = require(path.join(__dirname, '..', 'miniprogram', 'utils', 'mask-links.js'));

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
  await test('https 链接替换成 [链接]', () => {
    assert.strictEqual(
      maskLinks('报名链接 https://docs.qq.com/form/page/abc 请尽快填写'),
      '报名链接 [链接] 请尽快填写'
    );
  });

  await test('http 链接同样替换', () => {
    assert.strictEqual(maskLinks('见 http://example.com 通知'), '见 [链接] 通知');
  });

  await test('带查询参数的链接整体替换（token 不残留）', () => {
    assert.strictEqual(
      maskLinks('链接https://a.com/form?token=abc123&edit=1报名'),
      '链接[链接]报名'
    );
  });

  await test('无空格紧邻中文的链接不吞掉后面的正文和标点', () => {
    assert.strictEqual(
      maskLinks('详情见https://docs.qq.com/x。请及时报名'),
      '详情见[链接]。请及时报名'
    );
  });

  await test('链接末尾紧跟的 ASCII 句末标点保留在 [链接] 之后', () => {
    assert.strictEqual(maskLinks('见 https://a.com. 谢谢'), '见 [链接]. 谢谢');
  });

  await test('括号里的链接：括号保留', () => {
    assert.strictEqual(maskLinks('（https://a.com）'), '（[链接]）');
    assert.strictEqual(maskLinks('(https://a.com)'), '([链接])');
  });

  await test('多条链接全部替换', () => {
    assert.strictEqual(maskLinks('A https://a.com B https://b.com'), 'A [链接] B [链接]');
  });

  await test('只有链接的文本返回 [链接]', () => {
    assert.strictEqual(maskLinks('https://a.com'), '[链接]');
  });

  await test('没有链接的文本原样返回', () => {
    const t = '明天下午三点在图书馆开会，请准时参加。';
    assert.strictEqual(maskLinks(t), t);
  });

  console.log(`\n全部通过：${passed} 个测试`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
