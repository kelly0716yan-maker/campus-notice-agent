# 校园通知助手 · 微信小程序（MVP）

把一条校园通知粘贴进来，提取成结构化信息：事项、活动时间、截止时间、地点、对象、要做什么。
需求见 `docs/miniprogram-spec.md`，提示词与评测见仓库根目录的 `src/extractor.py` 与 `data/`。

## 目录结构

```
wechat-miniprogram/
├── project.config.json            # 开发者工具项目配置（appid 为占位，导入时填真实 AppID）
├── miniprogram/                   # 小程序前端（原生框架，单页）
│   ├── app.js / app.json / app.wxss / sitemap.json
│   ├── utils/mask-links.js        # 发送前把 http(s) 链接替换成 [链接]
│   └── pages/index/               # 唯一页面：输入、提取、结果卡片、复制、反馈
├── cloudfunctions/                # 微信云开发云函数
│   ├── extract/                   # 提取：校验、每日限流、调 DeepSeek、解析重试
│   │   ├── index.js               # 云函数入口（限流、环境变量、错误映射）
│   │   ├── core.js                # 核心逻辑（可本地单测）
│   │   └── prompt.js              # PROMPT_V05，一字不改复制自 src/extractor.py
│   ├── feedback/                  # 反馈：只有勾选“允许用于改进”才保存原文
│   └── track/                     # 埋点：open / extract / copy，不存通知内容
└── tests/
    ├── extract-core.test.js       # 单元测试（mock DeepSeek，无需 Key 和云环境）
    ├── mask-links.test.js         # 单元测试（链接遮罩，无需微信环境）
    └── e2e-extract.js             # 真实验收测试（test2_notices.csv 第 3/8/10 条，需 API Key）
```

## 本地自测

```bash
cd wechat-miniprogram
node tests/extract-core.test.js                       # 单元测试
node tests/mask-links.test.js                         # 单元测试（链接遮罩）
node --env-file=../.env tests/e2e-extract.js       # 真实调用 DeepSeek 的验收测试（约 3~6 次调用）
```

## 部署步骤（都需要在微信开发者工具/控制台手动操作）

1. 微信开发者工具「导入项目」，目录选 `wechat-miniprogram/`，填真实 AppID（云开发能力需要非个人测试号）。
2. 工具栏「云开发」开通并创建环境；如用默认环境无需改代码，如用专用环境把环境 ID 填进 `miniprogram/app.js` 的 `CLOUD_ENV`。
3. 云开发控制台 → 数据库，创建三个集合：`events`、`feedback`、`usage_daily`（权限选「仅创建者可读写」）。
4. 对 `cloudfunctions/` 下三个函数分别右键「上传并部署：云端安装依赖」。
5. 云开发控制台 → 云函数 → `extract`：
   - 配置环境变量 `DEEPSEEK_API_KEY`（**密钥只放这里，不进代码、不进 git**）；
   - 超时时间改为 **20–30 秒**（默认太短，大模型还没返回就会被掐断）。
6. 小程序后台（mp.weixin.qq.com）补「用户隐私保护指引」：说明收集使用记录、用户主动提交的反馈。
7. 上传代码 → 设为**体验版**（开发版只有开发者自己能打开）；「成员管理」里给试用者加体验者权限。
8. DeepSeek 平台给 API Key 设用量上限，避免意外超支。

## 注意事项

- 通知原文不落库：`extract` 只做提取不存储；只有用户勾选「允许用于改进产品」并提交反馈时，`feedback` 云函数才保存原文和结果（服务端强制校验，不信任前端）。
- 发送给 `extract` 前，通知里的 http(s) 链接会先被替换成 `[链接]`（链接可能带编辑权限，提取用不到它）。
- 每位用户每天最多提取 30 次（`usage_daily` 集合计数），超限提示「今天的次数用完了，明天再来」。
- `project.private.config.json`、`node_modules/` 等已在仓库根 `.gitignore` 中忽略；API Key 只存在于云函数环境变量，代码中搜不到。
