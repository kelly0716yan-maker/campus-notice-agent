/**
 * extract 云函数
 * 输入：{ text, today }（today 由小程序传入，格式 YYYY-MM-DD）
 * 成功：{ ok: true, data: {...7 字段}, prompt_version: "v0.5" }
 * 失败：{ ok: false, code, message }
 *
 * 注意：
 * - API Key 在云开发控制台的环境变量 DEEPSEEK_API_KEY 里，代码中不含任何密钥；
 * - 本函数的超时时间需在控制台改为 20–30 秒；
 * - 不保存通知原文：原文只在用户勾选“允许用于改进”并提交反馈后由 feedback 云函数保存。
 */
const cloud = require('wx-server-sdk');
const core = require('./core');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const text = event && event.text;
  const today = core.normalizeDate(event && event.today);

  const err = core.validate(text);
  if (err) return { ok: false, ...err };

  const db = cloud.database();
  const usageId = `${OPENID}_${today}`;

  // 限流：每位用户每天最多 30 次（集合不存在时不拦截，先保证可用，费用由 DeepSeek 平台用量上限兜底）
  let count = 0;
  try {
    const doc = await db.collection('usage_daily').doc(usageId).get();
    count = (doc && doc.data && doc.data.count) || 0;
  } catch (e) {
    // 集合未创建等情况放行
  }
  if (count >= core.MAX_PER_DAY) {
    return { ok: false, code: 'LIMIT', message: '今天的次数用完了，明天再来' };
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    return { ok: false, code: 'NO_KEY', message: '服务尚未配置完成，请稍后再试' };
  }

  // 计数 +1：无论成功失败都算一次（每次调用都可能产生费用）。
  // 读-改-写之间有并发窗口，两人同时点恰好都通过限流检查时可能多一两次，MVP 可接受。
  try {
    const _ = db.command;
    if (count > 0) {
      await db.collection('usage_daily').doc(usageId).update({ data: { count: _.inc(1) } });
    } else {
      await db.collection('usage_daily').doc(usageId).set({ data: { _openid: OPENID, date: today, count: 1 } });
    }
  } catch (e) {
    // 计数失败不阻塞提取
  }

  try {
    const data = await core.extractWithRetry(apiKey, core.buildPayload(today, text));
    return { ok: true, data, prompt_version: 'v0.5' };
  } catch (e) {
    if (e && e.isApiError) {
      return { ok: false, code: 'API_ERROR', message: '提取服务暂时不可用，请稍后重试' };
    }
    return { ok: false, code: 'BAD_RESPONSE', message: 'AI 返回格式异常，请重试' };
  }
};
