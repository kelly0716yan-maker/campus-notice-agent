/**
 * track 云函数
 * 输入：{ type: "open" | "extract" | "copy" | "todo_click" }
 * 写入 events 集合：{ _openid, type, ts }。不存任何通知内容。
 */
const cloud = require('wx-server-sdk');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const TYPES = ['open', 'extract', 'copy', 'todo_click'];

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const type = event && event.type;
  if (!TYPES.includes(type)) {
    return { ok: false, code: 'BAD_TYPE', message: '无效的事件类型' };
  }
  await cloud.database().collection('events').add({ data: { _openid: OPENID, type, ts: Date.now() } });
  return { ok: true };
};
