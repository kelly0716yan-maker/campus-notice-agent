"""核心能力：把一条校园通知抽取成结构化待办信息。"""
import json
import os
from datetime import date

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 读取项目根目录 .env 文件里的密钥

SYSTEM_PROMPT = """你是校园通知信息抽取助手。用户会给你一条校园通知原文，请抽取关键信息，只返回 JSON。

字段（都必须出现）：
- title: 事项名称（一句话概括）
- deadline: 截止时间或活动时间。若是相对时间（如“本周五”），结合今天的日期换算成具体日期，格式 YYYY-MM-DD HH:MM，没有具体时刻就只写日期
- audience: 适用对象（如“2023级全体本科生”“学生党员”）
- action: 需要对方做什么（提交什么、去哪里、找谁）
- evidence: 你判断以上信息时依据的原文片段（简短）

严格规则：
1. 通知里没写的信息，对应字段填“未提及”，绝对不要猜测或编造。
2. 原文有多个时间点时，deadline 填与“需要采取行动”最相关的那个，并在 action 里说明其他时间。
3. 只输出 JSON，不要任何额外文字。"""


def extract(notice_text: str, source: str = "未知") -> dict:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    model = os.getenv("MODEL", "deepseek-chat")
    user_msg = f"今天日期：{date.today().isoformat()}\n通知来源：{source}\n通知原文：\n{notice_text}"
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=800,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return json.loads(resp.choices[0].message.content)
