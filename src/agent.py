"""Agent：结合用户画像（记忆）判断通知是否相关，并通过工具调用生成日程和待办。

流程：通知原文 --extract--> 结构化信息 --Agent（带画像，可调用工具）--> 相关性 + 日程 + 待办
"""
import json
from datetime import date

from agent_tools import TOOLS, ToolBox
from extractor import extract, get_client, get_model
from user_profile import profile_text

AGENT_PROMPT = """你是校园通知助手，替一位学生处理一条已经提取好的通知。你可以调用工具。

规则：
1. 第一步必须调用 report_relevance：根据用户画像判断这条通知和该学生的相关程度，并给出一句理由。
   - 高：通知明确面向该学生（年级、学院、身份符合），或需要该学生采取行动；
   - 中：该学生可以参加或可能感兴趣，但不是必须；
   - 低：明显无关（年级、学院、身份、资格条件不符），或没有对该学生的任何要求。
   判断依据只能是用户画像和通知里写明的条件，画像里没填的信息不要猜。
2. 相关程度为高或中时：
   - 已提取信息里有明确日期，就调用 create_calendar_event：只有截止时间时 kind=deadline，活动时间用 kind=event；两种时间都有就分别创建。
   - 有需要学生做的事，就调用 add_todo。
3. 相关程度为低时，不要调用其他工具。
4. 工具参数只能使用已提取信息里的内容，不要编造。没有具体日期（“未提及”）就不要创建日程。
5. 所有工具调用完成后，用一句话总结你做了什么。"""


def run_agent(info: dict, profile: dict, today: str = None, client=None, toolbox: ToolBox = None, max_steps: int = 5) -> dict:
    """对已提取的通知信息运行 Agent。返回相关性、生成的日程和待办、调用记录。"""
    client = client or get_client()
    toolbox = toolbox or ToolBox()
    today = today or date.today().isoformat()
    user_msg = (f"今天日期：{today}\n用户画像：{profile_text(profile)}\n"
                f"已提取的通知信息：\n{json.dumps(info, ensure_ascii=False, indent=2)}")
    messages = [{"role": "system", "content": AGENT_PROMPT}, {"role": "user", "content": user_msg}]
    log, final = [], ""

    for _ in range(max_steps):
        resp = client.chat.completions.create(model=get_model(), temperature=0, messages=messages,
                                              tools=TOOLS, tool_choice="auto", max_tokens=800)
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            final = msg.content or ""
            break
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": c.id, "type": "function",
                                         "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                        for c in calls]})
        for c in calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = toolbox.call(c.function.name, args)
            log.append({"tool": c.function.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})

    return {"relevance": toolbox.relevance, "events": toolbox.events, "todos": toolbox.todos,
            "errors": toolbox.errors, "log": log, "summary": final}


def process_notice(text: str, source: str, profile: dict, today: str = None, client=None, save_todos=True) -> dict:
    """完整流程：提取 + Agent。"""
    client = client or get_client()
    info = extract(text, source, today=today, client=client)
    result = run_agent(info, profile, today=today, client=client, toolbox=ToolBox(save_todos=save_todos))
    result["info"] = info
    return result
