"""批量评测。
用法：
  python src/run_eval.py v0.4              # 开发集：data/notices.csv + data/gold_labels.csv
  python src/run_eval.py v0.4 test         # 测试集：data/test_notices.csv + data/test_gold_labels.csv
  python src/run_eval.py v0.4 test2        # 新测试集：data/test2_notices.csv + data/test2_gold_labels.csv
第一个参数是版本标签，同时决定使用哪一版提示词（v0.3、v0.4）。
结果保存到 data/results_<版本>[_数据集].csv，模型答案和标准答案并排，日期自动判定，其余你手动标注。
如果通知表里有 notice_date 列（通知发出日期），“今天/本周”这类相对时间会按那一天换算。
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
    """只比较日期部分（YYYY-MM-DD）。
    - 标准答案以“人工判定”开头：返回“人工”，不计入自动正确率。
    - 标准答案以“未提及”开头：模型答“未提及”算对；模型给出的日期若出现在标准答案的括号说明里也算对。
    """
    model_deadline, gold_deadline = str(model_deadline), str(gold_deadline)
    if gold_deadline.startswith("人工判定"):
        return "人工"
    m = DATE_RE.search(model_deadline)
    if gold_deadline.startswith("未提及"):
        if "未提及" in model_deadline:
            return "对"
        return "对" if m and m.group() in DATE_RE.findall(gold_deadline) else "错"
    g = DATE_RE.search(gold_deadline)
    if not g or not m:
        return "错"
    return "对" if g.group() == m.group() else "错"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "latest"
    dataset = sys.argv[2] if len(sys.argv) > 2 else "dev"
    if dataset == "dev":
        notices_path, gold_path = "data/notices.csv", "data/gold_labels.csv"
        out_path = f"data/results_{tag}.csv"
    else:
        notices_path, gold_path = f"data/{dataset}_notices.csv", f"data/{dataset}_gold_labels.csv"
        out_path = f"data/results_{tag}_{dataset}.csv"
    notices = read_csv(notices_path)
    gold = {g["id"]: g for g in read_csv(gold_path)}
    out = []
    for row in notices:
        try:
            r = extract(row["text"], row.get("source", "未知"), today=row.get("notice_date") or None, prompt_version=tag)
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
            "易混淆点": g.get("易混淆点", ""),
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
    manual = sum(1 for o in out if o["日期自动判定"] == "人工")
    judged = len(out) - manual
    print(f"已生成 {out_path}；日期自动判定：{ok}/{judged} 条正确（另有 {manual} 条需人工判断）")


if __name__ == "__main__":
    main()
