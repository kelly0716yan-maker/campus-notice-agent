/**
 * 发送通知原文给云函数前的文本清洗，与 wx API 解耦，方便本地单元测试。
 */

// 链接末尾紧跟的 ASCII 句末标点：从匹配里剥掉，保留在 [链接] 之后
const TRAILING_PUNCT_RE = /[.,;:!?)\]}>"'…]+$/;

/**
 * 把 http:// 或 https:// 开头的链接替换成 [链接]。
 * 链接可能带编辑权限，提取任务用不到它，发往云函数前先遮掉。
 * 匹配到空白、中文字符或中文标点为止，避免把链接后的正文吞掉。
 */
function maskLinks(text) {
  return String(text).replace(
    /https?:\/\/[^\s一-鿿，。；：！？、“”‘’（）【】《》〈〉]+/g,
    (url) => {
      const punct = url.match(TRAILING_PUNCT_RE);
      return punct ? `[链接]${punct[0]}` : '[链接]';
    }
  );
}

module.exports = { maskLinks };
