/**
 * 真实验收测试（对应 spec 验收标准第 1 条）：用 data/test2_notices.csv 的第 3、8、10 条。
 * 会真实调用 DeepSeek API（最多 6 次，费用极少）。
 *
 * 运行（在 wechat-miniprogram/ 目录下）：
 *   node --env-file=../.env tests/e2e-extract.js
 * API Key 只从环境变量或仓库根目录 .env 读取，不打印、不写入任何文件。
 */
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const core = require(path.join(__dirname, '..', 'cloudfunctions', 'extract', 'core.js'));

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CSV_PATH = path.join(REPO_ROOT, 'data', 'test2_notices.csv');

// 极简 CSV 解析：处理带引号、含逗号和换行的 text 字段
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      field = '';
      if (row.length > 1) rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }
  if (field !== '' || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function loadApiKey() {
  if (process.env.DEEPSEEK_API_KEY) return process.env.DEEPSEEK_API_KEY;
  const envPath = path.join(REPO_ROOT, '.env');
  if (fs.existsSync(envPath)) {
    for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
      const m = line.match(/^\s*DEEPSEEK_API_KEY\s*=\s*(.+?)\s*$/);
      if (m) return m[1].replace(/^["']|["']$/g, '');
    }
  }
  throw new Error('未找到 DEEPSEEK_API_KEY：请用 node --env-file=../.env tests/e2e-extract.js 运行');
}

async function main() {
  const apiKey = loadApiKey();
  // 去掉可能的 UTF-8 BOM，否则首列表头匹配不上
  const csvText = fs.readFileSync(CSV_PATH, 'utf8').replace(/^﻿/, '');
  const rows = parseCsv(csvText);
  const header = rows[0];
  const idIdx = header.indexOf('id');
  const noticeDateIdx = header.indexOf('notice_date');
  const textIdx = header.indexOf('text');
  assert.ok(idIdx >= 0 && noticeDateIdx >= 0 && textIdx >= 0, 'CSV 缺少 id/notice_date/text 列');

  const byId = {};
  for (const r of rows.slice(1)) byId[r[idIdx]] = r;
  for (const id of ['3', '8', '10']) assert.ok(byId[id], `test2_notices.csv 缺少第 ${id} 条`);

  for (const id of ['3', '8', '10']) {
    const row = byId[id];
    const text = row[textIdx];
    // 历史通知：today 用通知发出日期（与评测口径一致，相对时间按发出日期换算）
    const today = row[noticeDateIdx];
    console.log(`\n===== 第 ${id} 条（notice_date=${today}，原文 ${text.length} 字）=====`);
    const result = await core.extractWithRetry(apiKey, core.buildPayload(today, text));
    for (const f of core.FIELDS) {
      assert.ok(Object.prototype.hasOwnProperty.call(result, f), `第 ${id} 条缺少字段 ${f}`);
    }
    console.log(JSON.stringify(result, null, 2));

    if (id === '3') {
      assert.strictEqual(result.event_time, '未提及', '第 3 条 event_time 应为“未提及”');
      assert.strictEqual(result.deadline, '未提及', '第 3 条 deadline 应为“未提及”');
      // “没有编造报名方式”：action 里不应出现“报名”“提交”“回复”之外的杜撰方式，人工核对上方打印结果
    } else if (id === '8') {
      assert.strictEqual(result.event_time, '2026-01-16 15:00', `第 8 条 event_time 应为 2026-01-16 15:00，实际 ${result.event_time}`);
      assert.strictEqual(result.deadline, '未提及', '第 8 条 deadline 应为“未提及”');
      assert.ok(result.location.includes('腾讯会议'), `第 8 条 location 应含“腾讯会议”，实际 ${result.location}`);
    } else if (id === '10') {
      assert.strictEqual(result.deadline, '2026-03-09 17:00', `第 10 条 deadline 应为 2026-03-09 17:00，实际 ${result.deadline}`);
      assert.strictEqual(result.event_time, '未提及', '第 10 条 event_time 应为“未提及”');
    }
    console.log(`✓ 第 ${id} 条断言通过`);
  }
  console.log('\n验收测试全部通过');
}

main().catch((e) => {
  console.error('\n验收测试失败：', e.message);
  process.exit(1);
});
