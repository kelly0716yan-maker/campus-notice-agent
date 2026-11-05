# HANDOFF — 微信小程序 MVP 开发交接（2026-11-05）

## 做了什么

- 在 `wechat-miniprogram/` 下新建原生小程序 + 微信云开发项目（单页），功能范围严格按 `docs/miniprogram-spec.md`：
  - 顶部隐私提示、3000 字上限输入框（超长提示并截断）、提取按钮（loading / 友好错误 + 重试，不白屏）；
  - 结果卡片 6 字段（“未提及”灰色显示）、AI 生成提醒、“原文依据”默认折叠可展开、“复制成文字”（截止时间在前、跳过“未提及”行，已接入剪贴板）；
  - 反馈：👍 准确 / 👎 有误（弹可选的“哪里不对”输入框）+“允许把这条通知（已去掉个人信息）用于改进产品”勾选框（默认不勾，勾选且提交反馈才保存原文）；
  - 埋点：启动 open、提取成功 extract、点复制 copy。
- 云函数 3 个：
  - `extract`：PROMPT_V05（一字不改复制自 `src/extractor.py`，HEAD 5b9fd16）→ `cloudfunctions/extract/prompt.js`；校验空/超长、每日 30 次限流（usage_daily）、调 DeepSeek（temperature 0 / max_tokens 800 / json_object）、解析失败重试 1 次、字段缺失补“未提及”；API Key 只读环境变量 `DEEPSEEK_API_KEY`。
  - `feedback`：服务端强制只有 consent===true 才保存 text/result。
  - `track`：open/extract/copy 白名单，不存任何通知内容。
- 测试（本地已跑通）：
  - `tests/extract-core.test.js`：11 项单元测试全过（mock DeepSeek，不需 Key/云环境）；
  - `tests/e2e-extract.js`：真实调用 DeepSeek，用 `data/test2_notices.csv` 第 3/8/10 条验收，断言全过（第 3 条双“未提及”；第 8 条 event_time=2026-01-16 15:00、地点含腾讯会议；第 10 条 deadline=2026-03-09 17:00）。
- git：5 个本地提交（21cf476 → 最新），**未 push**（由你在 GitHub Desktop 里推送）。`.gitignore` 增加了 `node_modules/`、`project.private.config.json`；密钥不进代码、不进提交。

## 没做什么（按 spec 明确排除或留待后续）

- 用户画像、相关性判断、日历文件、待办列表、登录注册、分享、历史记录。
- 前端 UI 尚未在微信开发者工具/真机上验证（本机无法运行 GUI）；云函数未部署，限流与集合写入只在逻辑层面测试，未在云环境实测。
- 限流的读-改-写存在小并发窗口（两人同时点可能多一两次调用），MVP 可接受。

## 需要手动操作（下一步按顺序做）

1. 微信开发者工具「导入项目」→ `wechat-miniprogram/`，填真实 AppID。
2. 开通云开发；若用专用环境，把环境 ID 填进 `miniprogram/app.js` 的 `CLOUD_ENV`。
3. 控制台创建集合 `events` / `feedback` / `usage_daily`（权限“仅创建者可读写”）。
4. 三个云函数右键「上传并部署：云端安装依赖」。
5. `extract` 云函数：配置环境变量 `DEEPSEEK_API_KEY`；**超时时间改 20–30 秒**。
6. 小程序后台补「用户隐私保护指引」（使用记录、用户主动提交的反馈）。
7. 开发者工具里真机预览自测一遍（提取、错误场景、复制到备忘录、反馈），再上传为**体验版**；「成员管理」加体验者。
8. DeepSeek 平台给 Key 设用量上限。

## 下次从哪里继续

- 部署跑通后，回来看 `data/feedback` 的点赞/点踩数据（点踩率）和 `data/events` 的复用率（一周内有 2 天以上使用的用户数）。
- 提示词迭代仍走 `src/extractor.py` + `src/run_eval.py`；改完 PROMPT_V05 后要重新生成 `cloudfunctions/extract/prompt.js`（用同一段提取逻辑，见该文件头部注释）。
