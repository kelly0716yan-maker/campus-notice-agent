/**
 * feedback 云函数
 * 输入：{ rating: "up" | "down", reason?, consent, text?, result?, prompt_version? }
 * 写入 feedback 集合：{ _openid, rating, reason, consent, text?, result?, prompt_version, ts }
 * 服务端强制：只有 consent === true 才保存原文 text 和提取结果 result（不信任前端）。
 */
const cloud = require('wx-server-sdk');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const rating = event && event.rating;
  if (rating !== 'up' && rating !== 'down') {
    return { ok: false, code: 'BAD_RATING', message: '无效的反馈类型' };
  }

  const consent = event.consent === true;
  const record = {
    _openid: OPENID,
    rating,
    reason: typeof event.reason === 'string' ? event.reason.trim().slice(0, 500) : '',
    consent,
    prompt_version: typeof event.prompt_version === 'string' ? event.prompt_version : '',
    ts: Date.now(),
  };

  // 只有用户明确勾选“允许用于改进产品”才保存原文和结果
  if (consent) {
    if (typeof event.text === 'string' && event.text.trim() !== '') {
      record.text = event.text.slice(0, 3000);
    }
    if (event.result && typeof event.result === 'object') {
      record.result = event.result;
    }
  }

  await cloud.database().collection('feedback').add({ data: record });
  return { ok: true };
};
