"""评测 Agent 的“相关性判断”：给定你的画像，这条通知该不该关注？
用法：
  1. 在网页里保存“我的画像”（会生成 data/profile.json）
  2. 在 data/relevance_labels_test2.csv 里，按你自己的情况填写每条通知的 expected：相关 / 不相关
  3. python src/run_agent_eval.py v0.5 test2
Agent 判断为“高”或“中”算相关，“低”算不相关。结果保存到 data/results_agent_<数据集>.csv。
评测时不写待办文件，也不保存日程。
"""
import csv
import sys

from agent import process_notice
from extractor import get_client
from user_profile import is_filled, load_profile


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "v0.5"
    dataset = sys.argv[2] if len(sys.argv) > 2 else "test2"
    profile = load_profile()
    if not is_filled(profile):
        sys.exit("还没有画像：请先在网页左侧保存“我的画像”（会生成 data/profile.json）。")
    notices = read_csv(f"data/{dataset}_notices.csv")
    labels = {r["id"]: r.get("expected", "").strip() for r in read_csv(f"data/relevance_labels_{dataset}.csv")}
    client = get_client()
    rows, judged, correct = [], 0, 0
    for n in notices:
        res = process_notice(n["text"], n.get("source", "未知"), profile, today=n.get("notice_date") or None,
                             client=client, save_todos=False)
        rel = res["relevance"] or {}
        level = rel.get("level", "未判断")
        predicted = "相关" if level in ("高", "中") else ("不相关" if level == "低" else "未判断")
        expected = labels.get(n["id"], "")
        ok = ""
        if expected in ("相关", "不相关"):
            judged += 1
            ok = "对" if predicted == expected else "错"
            correct += ok == "对"
        rows.append({
            "id": n["id"], "标题": res["info"].get("title", ""), "你的标注": expected, "Agent相关程度": level,
            "Agent判断": predicted, "是否一致": ok, "理由": rel.get("reason", ""),
            "创建日程数": len(res["events"]), "创建待办数": len(res["todos"]), "工具报错": "；".join(res["errors"]),
        })
        print("done", n["id"])
    out = f"data/results_agent_{dataset}_{tag}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"已生成 {out}；相关性判断与你的标注一致：{correct}/{judged} 条")


if __name__ == "__main__":
    main()
