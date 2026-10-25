# 校园通知助手（campus-notice-agent）

> 一个用 AI 帮同学从群通知中提取待办的小工具。产品经理 + AI 开发协作项目。

## 背景与痛点
【补充：3–5 句话，来自 docs/problem-definition.md】

## 方案
粘贴通知 → AI 抽取（事项 / 时间 / 对象 / 要做什么）→ 生成待办卡片。

## 版本规划
- V0.1：粘贴通知，抽取关键信息，展示卡片 ← 当前
- V0.2：【根据评测和访谈结果决定】
- 之后：个人画像（判断与我是否相关）、提醒、日历同步

## 如何运行
```bash
pip install -r requirements.txt
# 复制 .env.example 为 .env，并填入你的 DeepSeek API Key
streamlit run src/app.py
```
模型接口使用 DeepSeek（兼容 OpenAI 调用方式），默认模型 deepseek-chat，可在 .env 中用 MODEL 修改。

## 评测
把脱敏后的通知放进 `data/notices.csv`，运行 `python src/run_eval.py`，在生成的 `data/results.csv` 里手动标注对错。

## 评测结果与迭代记录
【补充：每次评测的准确率、典型 bad case、对应的改动】
