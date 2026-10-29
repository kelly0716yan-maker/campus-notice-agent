"""V0.5 网页：粘贴通知 -> 待办卡片 -> 结合你的画像判断相关性 -> 生成日程和待办。
运行：streamlit run src/app.py"""
import streamlit as st

from agent import process_notice
from agent_tools import delete_todo, load_todos, set_todo_done
from extractor import extract
from user_profile import ROLE_OPTIONS, is_filled, load_profile, save_profile

st.set_page_config(page_title="校园通知助手", page_icon="📌")
st.title("📌 校园通知助手 V0.5")

# ---------------- 侧边栏：我的画像（记忆） ----------------
profile = load_profile()
with st.sidebar:
    st.header("我的画像")
    st.caption("用来判断通知和你有没有关系。只保存在这台电脑上，不会上传。")
    grade = st.text_input("年级", value=profile["grade"], placeholder="例如 2024级")
    major = st.text_input("学院 / 专业", value=profile["major"], placeholder="例如 经济管理学院 信息管理")
    roles = st.multiselect("身份", ROLE_OPTIONS, default=[r for r in profile["roles"] if r in ROLE_OPTIONS])
    interests = st.text_area("关注的方向（选填）", value=profile["interests"], placeholder="例如 保研、实习、政务实习")
    if st.button("保存画像"):
        save_profile({"grade": grade, "major": major, "roles": roles, "interests": interests})
        st.success("已保存")
        profile = load_profile()

tab_extract, tab_todo = st.tabs(["提取通知", "我的待办"])

# ---------------- 提取通知 ----------------
with tab_extract:
    st.caption("把群里的通知粘贴进来，自动提取要做的事。")
    source = st.selectbox("通知来源", ["辅导员群", "学院通知", "社团通知", "教务通知", "竞赛通知", "其他"])
    text = st.text_area("粘贴通知原文", height=220, placeholder="在这里粘贴通知……（请先去掉姓名、学号等个人信息）")

    if st.button("提取待办", type="primary"):
        if not text.strip():
            st.warning("请先粘贴通知内容")
        else:
            with st.spinner("分析中……"):
                try:
                    if is_filled(profile):
                        result = process_notice(text, source, profile)
                        info = result["info"]
                    else:
                        info, result = extract(text, source), None
                except Exception as e:
                    st.error(f"出错了：{e}")
                    st.stop()
            st.session_state["last"] = {"info": info, "result": result}

    last = st.session_state.get("last")
    if last:
        info, result = last["info"], last["result"]
        st.subheader(info.get("title", "未提及"))
        st.markdown(f"**🕒 活动时间：** {info.get('event_time', '未提及')}")
        st.markdown(f"**⏰ 截止时间：** {info.get('deadline', '未提及')}")
        st.markdown(f"**📍 地点：** {info.get('location', '未提及')}")
        st.markdown(f"**👥 对象：** {info.get('audience', '未提及')}")
        st.markdown(f"**✅ 要做什么：** {info.get('action', '未提及')}")
        with st.expander("模型依据的原文片段"):
            st.write(info.get("evidence", "未提及"))
        st.info("请核对关键信息，模型可能出错。")

        st.divider()
        if result is None:
            st.caption("在左侧填写并保存“我的画像”后，可以判断这条通知和你有没有关系，并自动生成日程和待办。")
        else:
            rel = result["relevance"] or {}
            icon = {"高": "🔴", "中": "🟡", "低": "⚪"}.get(rel.get("level"), "❔")
            st.markdown(f"**{icon} 和我的相关程度：{rel.get('level', '未判断')}**　{rel.get('reason', '')}")
            if result["events"]:
                st.markdown("**📅 日程（点击下载后，用手机或电脑日历打开即可导入，含提前 1 天和 30 分钟提醒）**")
                for i, ev in enumerate(result["events"]):
                    label = ("【截止】" if ev["kind"] == "deadline" else "") + ev["title"] + f"　{ev['when']}"
                    st.download_button(f"⬇ {label}", ev["ics"], file_name=f"notice_{i + 1}.ics",
                                       mime="text/calendar", key=f"ics_{i}_{ev['when']}")
            if result["todos"]:
                st.success(f"已加入 {len(result['todos'])} 条待办，可在“我的待办”里查看。")
            if result["errors"]:
                st.caption("部分工具调用失败：" + "；".join(result["errors"]))
            if result["summary"]:
                st.caption(result["summary"])

# ---------------- 我的待办 ----------------
with tab_todo:
    todos = load_todos()
    if not todos:
        st.caption("还没有待办。提取通知并保存画像后，相关的通知会自动加到这里。")
    for t in sorted(todos, key=lambda x: (x["done"], x.get("due") or "9999")):
        col1, col2 = st.columns([6, 1])
        with col1:
            done = st.checkbox(f"{t['title']}　{t.get('due', '')}", value=t["done"], key=f"done_{t['id']}")
            if done != t["done"]:
                set_todo_done(t["id"], done)
                st.rerun()
            if t.get("action"):
                st.caption(t["action"] + (f"　📍{t['location']}" if t.get("location") else ""))
        with col2:
            if st.button("删除", key=f"del_{t['id']}"):
                delete_todo(t["id"])
                st.rerun()
