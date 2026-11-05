// 云开发环境 ID：留空使用账号的默认环境；
// 如专门为小程序创建了云环境，把环境 ID 填到引号里（形如 cloud1-xxxxxxxx）
const CLOUD_ENV = '';

App({
  onLaunch() {
    if (!wx.cloud) {
      // 基础库版本过低（需 2.2.3+），只打日志，不影响页面展示
      console.error('当前微信基础库版本过低，无法使用云能力');
      return;
    }
    wx.cloud.init({ env: CLOUD_ENV, traceUser: true });
    this.track('open');
  },

  // 埋点：打点失败（未开通云开发、未部署云函数等）不影响使用，静默忽略
  track(type) {
    wx.cloud.callFunction({ name: 'track', data: { type } }).catch(() => {});
  },
});
