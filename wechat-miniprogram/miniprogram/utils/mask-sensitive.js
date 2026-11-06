/**
 * 发送通知原文给云函数前的隐私信息隐藏，与 wx API 解耦，方便本地单元测试。
 * 只把替换后的文本发给云函数；原值仅存前端页面内存，不落库、不进 feedback、不写日志。
 */

// 链接末尾紧跟的 ASCII 句末标点：从匹配里剥掉，不算进隐藏原值
const TRAILING_PUNCT_RE = /[.,;:!?)\]}>"'…]+$/;
// 链接以 http:// 或 https:// 开头，匹配到空白、中文字符或中文标点为止
const URL_RE = /https?:\/\/[^\s一-鿿，。；：！？、“”‘’（）【】《》〈〉]+/g;

// 隐藏规则：按顺序应用，更具体、更长的在前（先替换的不再参与后续规则）。
// 数字类规则都用 \b 边界，保证不匹配更长数字串的中间片段，也不会把紧跟的
// 句号、中文括号等标点算进原值。
const RULES = [
  { type: '链接', placeholder: '[链接]', re: URL_RE },
  { type: '邮箱', placeholder: '[邮箱]', re: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g },
  { type: '证件号', placeholder: '[证件号]', re: /\b\d{17}[\dXx]\b/g }, // 18 位身份证
  // 11 位手机号（1[3-9] 开头）或座机号（如 0631-5673834）
  { type: '电话', placeholder: '[电话]', re: /\b(?:1[3-9]\d{9}|0\d{2,3}-\d{7,8})\b/g },
  // 会议号：如 324-314-635 或 324 314 635
  { type: '会议号', placeholder: '[会议号]', re: /\b\d{3}[- ]\d{3}[- ]\d{3}\b/g },
  // 7 位及以上连续数字（学号、群号等）；放过 19xx/20xx 开头的 8 位日期
  { type: '号码', placeholder: '[号码]', re: /\b(?!(?:19|20)\d{6}\b)\d{7,}\b/g },
];

/**
 * 把文本里的隐私信息替换成占位符，返回：
 * - masked：替换后的文本（发给云函数的版本）
 * - hidden：[{ type, value }]，所有被隐藏的原值，按规则顺序分组
 */
function maskSensitive(text) {
  const hidden = [];
  let masked = String(text);
  for (const rule of RULES) {
    masked = masked.replace(rule.re, (match) => {
      const punct = match.match(TRAILING_PUNCT_RE);
      const value = punct ? match.slice(0, match.length - punct[0].length) : match;
      const suffix = punct ? punct[0] : '';
      hidden.push({ type: rule.type, value });
      return rule.placeholder + suffix;
    });
  }
  return { masked, hidden };
}

// 把 hidden 列表汇总成“链接 2 个、电话 1 个”形式的提示文案（为空返回 ''）
function summarizeHidden(hidden) {
  const counts = [];
  for (const h of hidden) {
    const last = counts[counts.length - 1];
    if (last && last.type === h.type) last.count += 1;
    else counts.push({ type: h.type, count: 1 });
  }
  return counts.map((c) => `${c.type} ${c.count} 个`).join('、');
}

module.exports = { maskSensitive, summarizeHidden };
