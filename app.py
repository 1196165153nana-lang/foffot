import streamlit as st

st.set_page_config(
    page_title="fofoot · 佛脚闪卡",
    page_icon="🦶",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 全局轻量样式优化（适配手机与电脑端）
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 720px;
    }
    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

home_page = st.Page("views/home.py", title="词本首页", icon="🏠", default=True)
select_page = st.Page("views/select_words.py", title="选词组池", icon="🎯")
study_page = st.Page("views/study.py", title="闪卡刷题", icon="📖")

pg = st.navigation([home_page, select_page, study_page])
pg.run()
