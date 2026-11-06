/**
 * 发送通知原文给云函数前的文本清洗，与 wx API 解耦，方便本地单元测试。
 */

// 链接末尾紧跟的 ASCII 句末标点：从链接里剥掉，不算进链接
const TRAILING_PUNCT_RE = /[.,;:!?)\]}>"'…]+$/;
// 链接以 http:// 或 https:// 开头，匹配到空白、中文字符或中文标点为止
const URL_RE = /https?:\/\/[^\s一-鿿，。；：！？、“”‘’（）【】《》〈〉]+/g;

// 找出文本里所有 http(s) 链接：去掉句末标点，按首次出现顺序去重。
// 链接只在前端页面内存里使用，不发给云函数、不落库。
function extractLinks(text) {
  const seen = new Set();
  const links = [];
  String(text).replace(URL_RE, (url) => {
    const link = url.replace(TRAILING_PUNCT_RE, '');
    if (!seen.has(link)) {
      seen.add(link);
      links.push(link);
    }
    return url; // 本函数只收集链接，不动原文
  });
  return links;
}

/**
 * 把 http:// 或 https:// 开头的链接替换成 [链接]。
 * 链接可能带编辑权限，提取任务用不到它，发往云函数前先遮掉。
 * 匹配到空白、中文字符或中文标点为止，避免把链接后的正文吞掉。
 */
function maskLinks(text) {
  return String(text).replace(URL_RE, (url) => {
    const punct = url.match(TRAILING_PUNCT_RE);
    return punct ? `[链接]${punct[0]}` : '[链接]';
  });
}

module.exports = { extractLinks, maskLinks };
