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
- deadline: 截止时间或活动时间。若是相对时间（如“本周五”），结合今天的日期换算成具体日期，格式 YYYY-MM-DD HH:MM，没有具体时刻就只写日期。原文没写年份时，按今天日期推断最合理的年份
- audience: 这件事本身面向谁（见下方对象规则）
- action: 需要对方做什么（提交什么、去哪里、找谁），只写读者需要采取的行动
- evidence: 你判断以上信息时依据的原文片段（简短）

基本规则：
1. 通知里没写的信息，对应字段填“未提及”，绝对不要猜测或编造。
2. 原文有多个时间点时，deadline 填与“需要采取行动”最相关的那个（如报名截止优先于活动开始），并在 action 里说明其他时间。
3. 不要根据通知来源推断原文没写的人物或地点。例如原文写“私发给我”，就写“发给发通知的人”，不要写成具体身份。

对象规则（audience）：
1. 只写“这件事本身面向谁”。背景介绍里出现的年级、人群，如果不是通知要求的对象，不要写进去。例如“2023级推免工作已结束，现举办经验交流会”，2023级是已经结束的人，不是听众。
2. 如果不同环节或不同人群的要求不同，要分开写并标明：必须参加、可选参加、仅限某个环节。不要把仅限某环节的条件当成整个事项的对象。
3. 如果有限定条件（如粉丝量、年级、人数名额），必须写进对象里，不要只写“全体师生”这样的宽泛说法。
4. @所有人、@全体成员只是群里的提醒方式，不是适用对象。
5. 如果通知是发给中间人转达的（如“请各位书记通知各班团支书”），audience 写最终需要行动的人，并在 action 里写明转达要求。

只输出 JSON，不要任何额外文字。"""


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
