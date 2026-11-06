const app = getApp();
const { maskSensitive, summarizeHidden } = require('../../utils/mask-sensitive');

// 云函数错误码 → 友好文案（找不到对应码时用兜底文案）
const ERROR_MESSAGES = {
  EMPTY: '请先粘贴通知原文',
  TOO_LONG: '通知太长，最多 3000 字',
  LIMIT: '今天的次数用完了，明天再来',
  BAD_RESPONSE: 'AI 返回格式异常，请重试',
  API_ERROR: '提取服务暂时不可用，请稍后重试',
  NO_KEY: '服务尚未配置完成，请稍后再试',
};

Page({
  data: {
    text: '',
    loading: false,
    error: '',
    result: null,
    promptVersion: '',
    showEvidence: false,
    consent: false,
    feedbackSent: false,
    maxLength: 3000,
    hiddenSummary: '', // “链接 2 个、电话 1 个”式提示文案（仅存页面内存）
    resultHidden: [], // 提取时被隐藏内容 [{type, value}] 的快照，用于结果卡片展示
  },

  onInput(e) {
    const text = e.detail.value;
    // textarea 的 maxlength 会自动截断超长内容；达到上限时提示一次
    if (text.length >= this.data.maxLength && this.data.text.length < this.data.maxLength) {
      wx.showToast({ title: '最多 3000 字，超出部分已截断', icon: 'none' });
    }
    // 实时检测会被自动隐藏的内容，原值仅存页面内存，不发往云函数、不落库
    this.setData({ text, hiddenSummary: summarizeHidden(maskSensitive(text).hidden) });
  },

  // 手机当天的日期，格式 YYYY-MM-DD
  today() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  },

  async onExtract() {
    if (this.data.loading) return;
    const text = this.data.text.trim();
    if (!text) {
      wx.showToast({ title: '请先粘贴通知原文', icon: 'none' });
      return;
    }
    this.setData({
      loading: true,
      error: '',
      result: null,
      showEvidence: false,
      consent: false,
      feedbackSent: false,
      resultHidden: [],
    });
    try {
      // 发送前把联系方式、链接、学号等替换成占位符，只把替换后的文本发给云函数；
      // 原值仅存页面内存，不落库、不进 feedback、不写日志
      const { masked, hidden } = maskSensitive(this.data.text);
      const res = await wx.cloud.callFunction({
        name: 'extract',
        data: { text: masked, today: this.today() },
      });
      const r = res && res.result;
      if (r && r.ok) {
        this.setData({
          result: r.data,
          promptVersion: r.prompt_version || '',
          resultHidden: hidden,
        });
        app.track('extract');
      } else {
        const code = r && r.code;
        this.setData({ error: ERROR_MESSAGES[code] || '提取失败，请稍后重试' });
      }
    } catch (err) {
      // 断网、未开通云开发、云函数未部署等
      console.error('extract failed', err);
      this.setData({ error: '调用失败，请检查网络后重试' });
    } finally {
      this.setData({ loading: false });
    }
  },

  // 点按结果卡片里被隐藏的原值：复制该值（原值只在前端内存，不落库、不上传）
  onCopyHidden(e) {
    const value = e.currentTarget.dataset.value;
    if (!value) return;
    wx.setClipboardData({
      data: value,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      },
    });
  },

  toggleEvidence() {
    this.setData({ showEvidence: !this.data.showEvidence });
  },

  onCopy() {
    const r = this.data.result;
    if (!r) return;
    const lines = [`【${r.title}】`];
    // 顺序按 spec：截止时间在活动时间前；跳过值为“未提及”的行
    const order = [
      ['deadline', '截止时间'],
      ['event_time', '活动时间'],
      ['location', '地点'],
      ['audience', '对象'],
      ['action', '要做什么'],
    ];
    order.forEach(([key, label]) => {
      const value = r[key];
      if (value && value !== '未提及') lines.push(`${label}：${value}`);
    });
    wx.setClipboardData({
      data: lines.join('\n'),
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
        app.track('copy');
      },
    });
  },

  // “加入待办”功能开发中：先提示并埋点（只记录点击，不记录任何通知内容）
  onAddTodo() {
    wx.showToast({ title: '待办功能正在开发中，你的需求我们记下了', icon: 'none' });
    app.track('todo_click');
  },

  onConsent(e) {
    this.setData({ consent: e.detail.value.length > 0 });
  },

  async sendFeedback(rating, reason = '') {
    if (this.data.feedbackSent) return;
    this.setData({ feedbackSent: true });
    const payload = {
      rating,
      reason,
      consent: this.data.consent,
      prompt_version: this.data.promptVersion,
    };
    // 只有勾选“允许用于改进产品”才随反馈提交原文和结果（云函数侧也会强制校验）
    // 保存的原文同样是隐私信息替换成占位符的版本，原值不上传
    if (this.data.consent) {
      payload.text = maskSensitive(this.data.text).masked;
      payload.result = this.data.result;
    }
    try {
      await wx.cloud.callFunction({ name: 'feedback', data: payload });
      wx.showToast({ title: '感谢反馈！', icon: 'none' });
    } catch (err) {
      console.error('feedback failed', err);
      this.setData({ feedbackSent: false });
      wx.showToast({ title: '反馈提交失败，请重试', icon: 'none' });
    }
  },

  onUp() {
    this.sendFeedback('up');
  },

  onDown() {
    wx.showModal({
      title: '哪里不对？',
      editable: true,
      placeholderText: '哪里不对？（可不填）',
      confirmText: '提交',
      success: (res) => {
        if (res.confirm) {
          this.sendFeedback('down', (res.content || '').trim());
        }
      },
    });
  },
});
