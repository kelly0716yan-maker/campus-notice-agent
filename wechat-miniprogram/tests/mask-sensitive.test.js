/**
 * 前端发送前隐私信息隐藏（maskSensitive）的单元测试：不需要微信环境和 API Key。
 * 运行（在 wechat-miniprogram/ 目录下）：node tests/mask-sensitive.test.js
 */
const assert = require('node:assert');
const path = require('node:path');
const { maskSensitive, summarizeHidden } = require(path.join(__dirname, '..', 'miniprogram', 'utils', 'mask-sensitive.js'));

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
  await test('链接替换成 [链接]，原值进 hidden', () => {
    const r = maskSensitive('报名 https://docs.qq.com/form/abc 填写');
    assert.strictEqual(r.masked, '报名 [链接] 填写');
    assert.deepStrictEqual(r.hidden, [{ type: '链接', value: 'https://docs.qq.com/form/abc' }]);
  });

  await test('链接末尾紧跟的句号/中文括号不算进链接', () => {
    const r = maskSensitive('见 https://a.com. 谢谢（https://b.com）');
    assert.strictEqual(r.masked, '见 [链接]. 谢谢（[链接]）');
    assert.deepStrictEqual(r.hidden.map((h) => h.value), ['https://a.com', 'https://b.com']);
  });

  await test('手机号替换成 [电话]', () => {
    const r = maskSensitive('联系 13812345678');
    assert.strictEqual(r.masked, '联系 [电话]');
    assert.deepStrictEqual(r.hidden, [{ type: '电话', value: '13812345678' }]);
  });

  await test('座机号替换成 [电话]', () => {
    const r = maskSensitive('办公室 0631-5673834 转 801');
    assert.strictEqual(r.masked, '办公室 [电话] 转 801');
    assert.deepStrictEqual(r.hidden, [{ type: '电话', value: '0631-5673834' }]);
  });

  await test('邮箱替换成 [邮箱]', () => {
    const r = maskSensitive('发到 zhangsan@qq.com 即可');
    assert.strictEqual(r.masked, '发到 [邮箱] 即可');
    assert.deepStrictEqual(r.hidden, [{ type: '邮箱', value: 'zhangsan@qq.com' }]);
  });

  await test('会议号（连字符/空格两种写法）替换成 [会议号]', () => {
    let r = maskSensitive('会议号 324-314-635 入会');
    assert.strictEqual(r.masked, '会议号 [会议号] 入会');
    assert.deepStrictEqual(r.hidden, [{ type: '会议号', value: '324-314-635' }]);
    r = maskSensitive('会议号 324 314 635 入会');
    assert.deepStrictEqual(r.hidden, [{ type: '会议号', value: '324 314 635' }]);
  });

  await test('18 位证件号替换成 [证件号]', () => {
    const r = maskSensitive('证件号 11010119900307775X');
    assert.strictEqual(r.masked, '证件号 [证件号]');
    assert.deepStrictEqual(r.hidden, [{ type: '证件号', value: '11010119900307775X' }]);
  });

  await test('7 位及以上连续数字（学号/群号）替换成 [号码]', () => {
    const r = maskSensitive('学号 2024123456，群号 1234567');
    assert.strictEqual(r.masked, '学号 [号码]，群号 [号码]');
    assert.deepStrictEqual(r.hidden.map((h) => h.value), ['2024123456', '1234567']);
  });

  await test('日期、时间、数量不被误伤', () => {
    const texts = [
      '2026-10-27 09:00',
      '2026年10月',
      '1月16日（周五）11:00',
      '09:00-11:30',
      '100题',
      '20万元',
    ];
    for (const t of texts) {
      const r = maskSensitive(t);
      assert.strictEqual(r.masked, t, `不应改动：${t}`);
      assert.deepStrictEqual(r.hidden, [], `不应有隐藏项：${t}`);
    }
  });

  await test('发给云函数的文本里不含任何原值', () => {
    const text = '报名 https://docs.qq.com/abc 邮箱 zhangsan@qq.com 电话 13812345678 会议号 324-314-635 学号 2024123456';
    const r = maskSensitive(text);
    for (const h of r.hidden) {
      assert.ok(!r.masked.includes(h.value), `${h.type} 原值不应出现在发送文本里`);
    }
    assert.ok(!r.masked.includes('docs.qq.com'));
    assert.ok(r.masked.includes('[链接]'));
  });

  await test('summarizeHidden：按类型统计数量', () => {
    assert.strictEqual(
      summarizeHidden([
        { type: '链接', value: 'a' },
        { type: '链接', value: 'b' },
        { type: '电话', value: 'c' },
      ]),
      '链接 2 个、电话 1 个'
    );
    assert.strictEqual(summarizeHidden([]), '');
  });

  await test('没有敏感内容的文本原样返回', () => {
    const t = '明天下午三点在图书馆开会，请准时参加。';
    const r = maskSensitive(t);
    assert.strictEqual(r.masked, t);
    assert.deepStrictEqual(r.hidden, []);
  });

  await test('混合文本：各类敏感内容同时隐藏且类型正确', () => {
    const r = maskSensitive(
      '报名https://a.com/x 邮箱 zhangsan@qq.com 电话 13812345678 座机 0631-5673834 证件号 11010119900307775X 会议号 324-314-635 学号 2024123456'
    );
    assert.deepStrictEqual(r.hidden.map((h) => h.type), ['链接', '邮箱', '证件号', '电话', '电话', '会议号', '号码']);
    for (const p of ['[链接]', '[邮箱]', '[证件号]', '[电话]', '[会议号]', '[号码]']) {
      assert.ok(r.masked.includes(p), `缺少占位符 ${p}`);
    }
  });

  await test('电话号码紧跟中文标点时不把标点算进原值', () => {
    const r = maskSensitive('电话13812345678。请查收');
    assert.strictEqual(r.masked, '电话[电话]。请查收');
    assert.deepStrictEqual(r.hidden, [{ type: '电话', value: '13812345678' }]);
  });

  console.log(`\n全部通过：${passed} 个测试`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
