"""Agent 可以调用的工具：判断相关性、生成日历文件、保存待办。

注意：生成的是 .ics 日历文件，由用户自己点击导入手机或电脑日历，
程序不会自动改动用户的日历（用户确认后才生效）。
"""
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TODO_PATH = Path("data/todos.json")

# 给大模型看的工具说明（OpenAI / DeepSeek 的 function calling 格式）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "report_relevance",
            "description": "根据用户画像，判断这条通知和该学生的相关程度，并给出一句理由。每条通知必须先调用一次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["高", "中", "低"], "description": "高：明确面向该学生或需要他行动；中：可以参加但不必须；低：明显无关"},
                    "reason": {"type": "string", "description": "一句话理由，引用画像或通知里的具体条件"},
                },
                "required": ["level", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "为通知里明确的时间创建一个日历日程（含提前提醒）。只在相关程度为高或中，且已提取信息里有明确日期时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "日程标题"},
                    "when": {"type": "string", "description": "时间，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM，可带结束时间如 2026-10-27 09:00-11:30"},
                    "kind": {"type": "string", "enum": ["event", "deadline"], "description": "event：活动开始时间；deadline：报名或提交的截止时间"},
                    "location": {"type": "string", "description": "地点，没有则留空"},
                    "description": {"type": "string", "description": "备注，如需要做什么"},
                },
                "required": ["title", "when", "kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "把学生需要做的事保存为待办。只在相关程度为高或中，且确实有需要学生做的事时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "待办标题"},
                    "due": {"type": "string", "description": "截止或活动时间，没有则留空"},
                    "action": {"type": "string", "description": "要做什么"},
                    "location": {"type": "string", "description": "地点，没有则留空"},
                },
                "required": ["title", "action"],
            },
        },
    },
]

_WHEN = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T]+(\d{1,2}):(\d{2}))?(?:\s*[-–~至到]\s*(\d{1,2}):(\d{2}))?")


def parse_when(text):
    """解析时间，返回 (start, end, all_day)。start/end 是 datetime（有具体时刻）或 date（只有日期）。
    “24:00” 按当天 23:59 处理。"""
    if not text:
        raise ValueError("时间为空")
    m = _WHEN.search(str(text))
    if not m:
        raise ValueError(f"无法解析时间：{text}")
    y, mo, d, h, mi, h2, mi2 = m.groups()
    day = date(int(y), int(mo), int(d))
    if h is None:
        return day, None, True
    hour, minute = int(h), int(mi)
    if (hour, minute) == (24, 0):
        hour, minute = 23, 59
    start = datetime(day.year, day.month, day.day, hour, minute)
    end = None
    if h2 is not None:
        eh, em = int(h2), int(mi2)
        if (eh, em) == (24, 0):
            eh, em = 23, 59
        end = datetime(day.year, day.month, day.day, eh, em)
        if end <= start:
            end = None
    return start, end, False


def _esc(text) -> str:
    return (str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def _fold(line: str) -> str:
    """ICS 规定每行不超过 75 字节，超出的部分换行并以空格开头（按 UTF-8 字节计算，不拆开汉字）。"""
    out, cur, size = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        limit = 75 if not out else 74
        if size + b > limit:
            out.append(cur)
            cur, size = ch, b
        else:
            cur += ch
            size += b
    out.append(cur)
    return "\r\n ".join(out)


def make_ics(title, when, kind="event", location="", description="", reminders=(1440, 30)) -> str:
    """生成一个日历文件（.ics）的文本。默认提前 1 天和提前 30 分钟各提醒一次。"""
    start, end, all_day = parse_when(when)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = ("【截止】" if kind == "deadline" else "") + str(title)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//campus-notice-agent//CN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "BEGIN:VEVENT", f"UID:{uuid.uuid4()}@campus-notice-agent", f"DTSTAMP:{stamp}"]
    if all_day:
        lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}"]
    else:
        if end is None:
            end = start + (timedelta(minutes=15) if kind == "deadline" else timedelta(hours=1))
        lines += [f"DTSTART:{start:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}"]
    lines.append("SUMMARY:" + _esc(summary))
    if location:
        lines.append("LOCATION:" + _esc(location))
    if description:
        lines.append("DESCRIPTION:" + _esc(description))
    for minutes in reminders:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + _esc(summary), f"TRIGGER:-PT{int(minutes)}M", "END:VALARM"]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


# ---------------- 待办存储 ----------------
def load_todos(path=TODO_PATH) -> list:
    path = Path(path)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_todos(todos, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")


def add_todo_item(title, action="", due="", location="", relevance="", path=TODO_PATH) -> dict:
    todos = load_todos(path)
    item = {"id": uuid.uuid4().hex[:8], "title": title, "action": action, "due": due,
            "location": location, "relevance": relevance, "done": False,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")}
    todos.append(item)
    _save_todos(todos, path)
    return item


def set_todo_done(todo_id, done=True, path=TODO_PATH) -> None:
    todos = load_todos(path)
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = done
    _save_todos(todos, path)


def delete_todo(todo_id, path=TODO_PATH) -> None:
    _save_todos([t for t in load_todos(path) if t["id"] != todo_id], path)


class ToolBox:
    """执行 Agent 发出的工具调用，并记录结果。save_todos=False 时不写本地文件（评测用）。"""

    def __init__(self, save_todos=True, todo_path=TODO_PATH):
        self.save_todos = save_todos
        self.todo_path = todo_path
        self.relevance = None      # {"level":..., "reason":...}
        self.events = []           # [{"title","when","kind","location","ics"}]
        self.todos = []
        self.errors = []

    def call(self, name: str, args: dict) -> str:
        try:
            if name == "report_relevance":
                level = args.get("level")
                if level not in ("高", "中", "低"):
                    raise ValueError("level 必须是 高、中、低 之一")
                self.relevance = {"level": level, "reason": args.get("reason", "")}
                return json.dumps({"ok": True}, ensure_ascii=False)
            if name == "create_calendar_event":
                kind = args.get("kind", "event")
                ics = make_ics(args["title"], args["when"], kind=kind,
                               location=args.get("location", ""), description=args.get("description", ""))
                self.events.append({"title": args["title"], "when": args["when"], "kind": kind,
                                    "location": args.get("location", ""), "ics": ics})
                return json.dumps({"ok": True, "message": "日程已生成，等待用户导入"}, ensure_ascii=False)
            if name == "add_todo":
                level = self.relevance["level"] if self.relevance else ""
                if self.save_todos:
                    item = add_todo_item(args["title"], args.get("action", ""), args.get("due", ""),
                                         args.get("location", ""), level, self.todo_path)
                else:
                    item = {"title": args["title"], "action": args.get("action", ""), "due": args.get("due", ""),
                            "location": args.get("location", "")}
                self.todos.append(item)
                return json.dumps({"ok": True}, ensure_ascii=False)
            raise ValueError(f"未知工具：{name}")
        except Exception as e:  # 把错误返回给模型，让它有机会修正
            self.errors.append(f"{name}: {e}")
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
