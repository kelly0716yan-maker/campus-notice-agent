"""V0.1 网页：粘贴通知 -> 待办卡片。运行：streamlit run src/app.py"""
import streamlit as st

from extractor import extract

st.set_page_config(page_title="校园通知助手", page_icon="📌")
st.title("📌 校园通知助手 V0.1")
st.caption("把群里的通知粘贴进来，自动提取要做的事。")

source = st.selectbox("通知来源", ["辅导员群", "学院通知", "社团通知", "教务通知", "竞赛通知", "其他"])
text = st.text_area("粘贴通知原文", height=220, placeholder="在这里粘贴通知……（请先去掉姓名、学号等个人信息）")

if st.button("提取待办", type="primary"):
    if not text.strip():
        st.warning("请先粘贴通知内容")
    else:
        with st.spinner("分析中……"):
            try:
                r = extract(text, source)
            except Exception as e:
                st.error(f"出错了：{e}")
                st.stop()
        st.subheader(r.get("title", "未提及"))
        st.markdown(f"**⏰ 时间：** {r.get('deadline', '未提及')}")
        st.markdown(f"**👥 对象：** {r.get('audience', '未提及')}")
        st.markdown(f"**✅ 要做什么：** {r.get('action', '未提及')}")
        with st.expander("模型依据的原文片段"):
            st.write(r.get("evidence", "未提及"))
        st.info("请核对关键信息，模型可能出错。")
