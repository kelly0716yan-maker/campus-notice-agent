"""批量评测：读取 data/notices.csv（列：id, source, text），
输出 data/results.csv，你在后两列手动标注对错，用来计算准确率、整理 bad case。
运行：python src/run_eval.py
"""
import csv

from extractor import extract

rows = list(csv.DictReader(open("data/notices.csv", encoding="utf-8-sig")))
out = []
for row in rows:
    try:
        r = extract(row["text"], row.get("source", "未知"))
    except Exception as e:
        r = {"title": f"出错：{e}"}
    out.append({
        "id": row["id"], "source": row.get("source", ""), "text": row["text"],
        "title": r.get("title", ""), "deadline": r.get("deadline", ""),
        "audience": r.get("audience", ""), "action": r.get("action", ""),
        "是否正确(手填:对/错)": "", "错在哪(手填)": "",
    })
    print("done", row["id"])

with open("data/results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
print("已生成 data/results.csv")
