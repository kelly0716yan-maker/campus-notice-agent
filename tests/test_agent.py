"""离线测试：不需要 API Key。运行：python -m unittest discover -s tests -v
（在项目根目录运行；依赖 src 里的模块，openai 和 dotenv 用假的替身代替）"""
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import date, datetime
from types import SimpleNamespace as NS

# 用替身代替需要联网/安装的库，保证测试可以离线运行
sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None))
sys.modules.setdefault("openai", types.SimpleNamespace(OpenAI=lambda **k: None))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import agent_tools as T  # noqa: E402
from agent import run_agent  # noqa: E402
from extractor import PROMPTS  # noqa: E402
from user_profile import load_profile, save_profile, profile_text  # noqa: E402


def tool_call(i, name, args):
    return NS(id=str(i), function=NS(name=name, arguments=json.dumps(args, ensure_ascii=False)))


class FakeClient:
    """按顺序返回预设的模型回复，模拟大模型的工具调用。"""
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        msg = self.replies.pop(0)
        return NS(choices=[NS(message=msg)])


class ParseTests(unittest.TestCase):
    def test_date_only(self):
        s, e, allday = T.parse_when("2026-10-18")
        self.assertEqual((s, e, allday), (date(2026, 10, 18), None, True))

    def test_datetime(self):
        s, e, allday = T.parse_when("2026-10-18 15:00")
        self.assertEqual(s, datetime(2026, 10, 18, 15, 0)); self.assertFalse(allday)

    def test_range(self):
        s, e, _ = T.parse_when("2026-10-27 09:00-11:30")
        self.assertEqual((s.hour, e.hour, e.minute), (9, 11, 30))

    def test_2400_becomes_2359(self):
        s, _, _ = T.parse_when("2026-02-10 24:00")
        self.assertEqual((s.day, s.hour, s.minute), (10, 23, 59))

    def test_bad_inputs(self):
        for bad in ["", "未提及", "下周三"]:
            with self.assertRaises(ValueError):
                T.parse_when(bad)

    def test_impossible_date(self):
        with self.assertRaises(ValueError):
            T.parse_when("2026-02-30")


class IcsTests(unittest.TestCase):
    def test_structure_and_crlf(self):
        ics = T.make_ics("党史知识竞赛", "2026-06-07 09:00", location="线下", description="提前10分钟到场")
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n")); self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        self.assertIn("DTSTART:20260607T090000", ics); self.assertIn("DTEND:20260607T100000", ics)
        self.assertEqual(ics.count("BEGIN:VALARM"), 2)
        self.assertIn("TRIGGER:-PT1440M", ics); self.assertIn("TRIGGER:-PT30M", ics)

    def test_deadline_prefix(self):
        ics = T.make_ics("报名", "2026-01-16 11:00", kind="deadline")
        self.assertIn("SUMMARY:【截止】报名", ics.replace("\r\n ", ""))

    def test_all_day(self):
        ics = T.make_ics("戏曲进校园", "2026-10-18")
        self.assertIn("DTSTART;VALUE=DATE:20261018", ics); self.assertIn("DTEND;VALUE=DATE:20261019", ics)

    def test_line_folding_by_bytes(self):
        ics = T.make_ics("很长的标题" * 30, "2026-10-18 15:00", description="a,b;c\n换行")
        for line in ics.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        unfolded = ics.replace("\r\n ", "")
        self.assertIn("\\,", unfolded); self.assertIn("\\;", unfolded); self.assertIn("\\n", unfolded)


class TodoTests(unittest.TestCase):
    def test_add_done_delete(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "todos.json")
            item = T.add_todo_item("报名", action="填表", due="2026-01-16 11:00", path=p)
            self.assertEqual(len(T.load_todos(p)), 1)
            T.set_todo_done(item["id"], True, path=p)
            self.assertTrue(T.load_todos(p)[0]["done"])
            T.delete_todo(item["id"], path=p)
            self.assertEqual(T.load_todos(p), [])


class ProfileTests(unittest.TestCase):
    def test_roundtrip_and_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "profile.json")
            self.assertEqual(load_profile(p)["grade"], "")
            save_profile({"grade": "2024级", "major": "信息管理", "roles": ["班委"], "interests": "保研"}, p)
            prof = load_profile(p)
            self.assertEqual(prof["grade"], "2024级")
            self.assertIn("2024级", profile_text(prof))


class AgentLoopTests(unittest.TestCase):
    info = {"title": "党史知识竞赛", "event_time": "2026-06-07 09:00", "deadline": "未提及",
            "location": "未提及", "audience": "全院学生自愿参加", "action": "提前10分钟到场答题"}
    profile = {"grade": "2025级", "major": "信息管理", "roles": [], "interests": ""}

    def test_relevant_notice_creates_event_and_todo(self):
        client = FakeClient([
            NS(content=None, tool_calls=[
                tool_call(1, "report_relevance", {"level": "高", "reason": "2025级必须参加"}),
                tool_call(2, "create_calendar_event", {"title": "党史知识竞赛", "when": "2026-06-07 09:00", "kind": "event"}),
                tool_call(3, "add_todo", {"title": "党史知识竞赛", "action": "提前10分钟到场答题", "due": "2026-06-07 09:00"}),
            ]),
            NS(content="已创建日程和待办。", tool_calls=None),
        ])
        box = T.ToolBox(save_todos=False)
        res = run_agent(self.info, self.profile, today="2026-06-01", client=client, toolbox=box)
        self.assertEqual(res["relevance"]["level"], "高")
        self.assertEqual(len(res["events"]), 1); self.assertIn("BEGIN:VEVENT", res["events"][0]["ics"])
        self.assertEqual(len(res["todos"]), 1); self.assertEqual(res["summary"], "已创建日程和待办。")
        self.assertEqual(len(client.requests), 2)
        # 第二次请求必须带上工具执行结果
        roles = [m["role"] for m in client.requests[1]["messages"]]
        self.assertEqual(roles.count("tool"), 3)
        # 画像要出现在发给模型的内容里
        self.assertIn("2025级", client.requests[0]["messages"][1]["content"])

    def test_irrelevant_notice_creates_nothing(self):
        client = FakeClient([
            NS(content=None, tool_calls=[tool_call(1, "report_relevance", {"level": "低", "reason": "仅限2023级"})]),
            NS(content="与你无关，未创建日程。", tool_calls=None),
        ])
        res = run_agent(self.info, self.profile, client=client, toolbox=T.ToolBox(save_todos=False))
        self.assertEqual(res["relevance"]["level"], "低"); self.assertEqual(res["events"], []); self.assertEqual(res["todos"], [])

    def test_bad_tool_args_are_reported_back_to_model(self):
        client = FakeClient([
            NS(content=None, tool_calls=[
                tool_call(1, "report_relevance", {"level": "高", "reason": "x"}),
                tool_call(2, "create_calendar_event", {"title": "t", "when": "未提及", "kind": "event"}),
            ]),
            NS(content="没有具体日期，未创建日程。", tool_calls=None),
        ])
        box = T.ToolBox(save_todos=False)
        res = run_agent(self.info, self.profile, client=client, toolbox=box)
        self.assertEqual(res["events"], []); self.assertEqual(len(res["errors"]), 1)
        tool_msgs = [m for m in client.requests[1]["messages"] if m["role"] == "tool"]
        self.assertIn('"ok": false', tool_msgs[1]["content"])

    def test_max_steps_stops_endless_loop(self):
        endless = [NS(content=None, tool_calls=[tool_call(i, "report_relevance", {"level": "中", "reason": "x"})]) for i in range(10)]
        client = FakeClient(endless)
        res = run_agent(self.info, self.profile, client=client, toolbox=T.ToolBox(save_todos=False), max_steps=3)
        self.assertEqual(len(client.requests), 3)

    def test_invalid_level_rejected(self):
        box = T.ToolBox(save_todos=False)
        out = json.loads(box.call("report_relevance", {"level": "很高", "reason": ""}))
        self.assertFalse(out["ok"]); self.assertIsNone(box.relevance)


class PromptTests(unittest.TestCase):
    def test_versions_exist_and_v05_has_new_rules(self):
        self.assertEqual(set(PROMPTS), {"v0.3", "v0.4", "v0.5"})
        p5 = PROMPTS["v0.5"]
        for key in ["event_time", "location", "较为友好", "不是对象限定", "不要写“辅导员”"]:
            self.assertIn(key, p5)
        self.assertNotIn("event_time", PROMPTS["v0.4"])


if __name__ == "__main__":
    unittest.main()
