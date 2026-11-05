/**
 * extract 云函数的核心逻辑，与 wx-server-sdk 解耦，方便本地单元测试。
 * DeepSeek 调用通过 transport 注入，默认使用 Node 内置 https 模块（不引入第三方依赖）。
 */
const https = require('https');

const MAX_CHARS = 3000; // 与小程序输入框 maxlength 一致
const MAX_PER_DAY = 30; // 每位用户每天最多提取次数（控制费用）
const FIELDS = ['title', 'event_time', 'deadline', 'location', 'audience', 'action', 'evidence'];

function validate(text) {
  if (typeof text !== 'string' || text.trim() === '') {
    return { code: 'EMPTY', message: '请先粘贴通知原文' };
  }
  if (text.length > MAX_CHARS) {
    return { code: 'TOO_LONG', message: `通知太长，最多 ${MAX_CHARS} 字` };
  }
  return null;
}

// 今天日期：优先用小程序传入的 today（手机当天日期），格式不对则退回服务器本地日期
function normalizeDate(today) {
  if (typeof today === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(today)) return today;
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function buildMessages(today, text) {
  return [
    { role: 'system', content: require('./prompt') },
    { role: 'user', content: `今天日期：${today}\n通知来源：未知\n通知原文：\n${text}` },
  ];
}

function buildPayload(today, text) {
  return {
    model: 'deepseek-chat',
    temperature: 0,
    max_tokens: 800,
    response_format: { type: 'json_object' },
    messages: buildMessages(today, text),
  };
}

// 解析模型返回的 JSON；字段缺失或为空补“未提及”（不编造，也不让前端白屏）
function parseResult(content) {
  const data = JSON.parse(content);
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    throw new Error('响应不是 JSON 对象');
  }
  const out = {};
  for (const field of FIELDS) {
    const value = data[field];
    out[field] = typeof value === 'string' && value.trim() !== '' ? value.trim() : '未提及';
  }
  return out;
}

// 调用 DeepSeek，成功时 resolve(message.content 字符串)
function defaultTransport(apiKey, payload) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const req = https.request(
      {
        hostname: 'api.deepseek.com',
        path: '/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
          'Content-Length': Buffer.byteLength(body),
        },
        // 注意：云函数控制台里的超时时间需设置为 20–30 秒，否则请求会被平台提前掐断
        timeout: 20000,
      },
      (res) => {
        let raw = '';
        res.on('data', (chunk) => {
          raw += chunk;
        });
        res.on('end', () => {
          if (res.statusCode !== 200) {
            reject(
              Object.assign(new Error(`DeepSeek API 返回 ${res.statusCode}`), {
                isApiError: true,
                statusCode: res.statusCode,
              })
            );
            return;
          }
          let data;
          try {
            data = JSON.parse(raw);
          } catch (e) {
            reject(Object.assign(new Error('DeepSeek API 响应不是合法 JSON'), { isApiError: true }));
            return;
          }
          const content =
            data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
          if (typeof content !== 'string' || content === '') {
            reject(Object.assign(new Error('DeepSeek 响应缺少 content'), { isApiError: true }));
            return;
          }
          resolve(content);
        });
      }
    );
    req.on('timeout', () => req.destroy(Object.assign(new Error('DeepSeek 请求超时'), { isApiError: true })));
    req.on('error', (err) => reject(Object.assign(err, { isApiError: true })));
    req.write(body);
    req.end();
  });
}

// 解析失败（模型返回非 JSON）重试 1 次，仍失败抛出；
// 网络/API 错误（isApiError）不重试，直接抛出，由上层映射成友好提示
async function extractWithRetry(apiKey, payload, transport = defaultTransport) {
  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const content = await transport(apiKey, payload);
      return parseResult(content);
    } catch (err) {
      lastError = err;
      if (err && err.isApiError) throw err;
      // 解析失败 → 再试一次
    }
  }
  throw lastError;
}

module.exports = {
  MAX_CHARS,
  MAX_PER_DAY,
  FIELDS,
  validate,
  normalizeDate,
  buildMessages,
  buildPayload,
  parseResult,
  defaultTransport,
  extractWithRetry,
};
