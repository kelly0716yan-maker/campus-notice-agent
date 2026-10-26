"""批量评测：读取 data/notices.csv（id, source, text）和 data/gold_labels.csv（标准答案），
让模型跑一遍，生成 data/results.csv：模型答案和标准答案并排，日期自动判定，其余你手动标注。
运行：python src/run_eval.py v0.2   （v0.2 是这次评测的版本标签，结果会存成 data/results_v0.2.csv）
"""
import csv
import re
import sys

from extractor import extract

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def judge_date(model_deadline: str, gold_deadline: str) -> str:
    """只比较日期部分（YYYY-MM-DD）。标准答案为“未提及”时，模型也必须答“未提及”。"""
    model_deadline, gold_deadline = str(model_deadline), str(gold_deadline)
    if gold_deadline.startswith("未提及"):
        return "对" if "未提及" in model_deadline else "错"
    g = DATE_RE.search(gold_deadline)
    m = DATE_RE.search(model_deadline)
    if not g or not m:
        return "错"
    return "对" if g.group() == m.group() else "错"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "latest"
    out_path = f"data/results_{tag}.csv"
    notices = read_csv("data/notices.csv")
    gold = {g["id"]: g for g in read_csv("data/gold_labels.csv")}
    out = []
    for row in notices:
        try:
            r = extract(row["text"], row.get("source", "未知"))
        except Exception as e:
            r = {"title": f"出错：{e}"}
        g = gold.get(row["id"], {})
        out.append({
            "id": row["id"],
            "source": row.get("source", ""),
            "模型_事项": r.get("title", ""),
            "标准_事项": g.get("gold_title", ""),
            "模型_时间": r.get("deadline", ""),
            "标准_时间": g.get("gold_deadline", ""),
            "日期自动判定": judge_date(r.get("deadline", ""), g.get("gold_deadline", "")),
            "模型_对象": r.get("audience", ""),
            "标准_对象": g.get("gold_audience", ""),
            "模型_行动": r.get("action", ""),
            "标准_行动": g.get("gold_action", ""),
            "难点备注": g.get("难点备注", ""),
            "对象是否正确(手填:对/错)": "",
            "行动是否正确(手填:对/错)": "",
            "错在哪(手填)": "",
            "原文": row["text"],
        })
        print("done", row["id"])

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    ok = sum(1 for o in out if o["日期自动判定"] == "对")
    print(f"已生成 {out_path}；日期自动判定：{ok}/{len(out)} 条正确")


if __name__ == "__main__":
    main()
