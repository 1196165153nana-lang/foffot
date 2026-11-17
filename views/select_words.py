import random
import pandas as pd
import streamlit as st
from feishu_api import load_all_words, load_wordbooks

st.title("🎯 选词组池")

try:
    wordbooks = load_wordbooks()
    all_words = load_all_words()
except Exception as e:
    st.error(f"读取词库失败：{e}")
    st.stop()

if not wordbooks:
    st.warning("当前没有任何词本，请先返回首页创建。")
    if st.button("🏠 返回首页"):
        st.switch_page("views/home.py")
    st.stop()

book_names = [b["name"] for b in wordbooks]
current_book = st.session_state.get("selected_wordbook")
if current_book not in book_names:
    current_book = book_names[0]

col_book, col_home = st.columns([3, 1])
with col_book:
    chosen_book = st.selectbox("当前词本", book_names, index=book_names.index(current_book))
    st.session_state["selected_wordbook"] = chosen_book
with col_home:
    st.write("")
    st.write("")
    if st.button("🏠 首页", use_container_width=True):
        st.switch_page("views/home.py")

book_words = [w for w in all_words if w["wordbook"] == chosen_book]

if not book_words:
    st.info(f"词本「{chosen_book}」里还没有单词，请回首页导入单词。")
    st.stop()

st.caption(f"当前词本共有 **{len(book_words)}** 个单词可选")

mode = st.radio(
    "选词方式",
    ["🎲 指定数量随机抽取", "☑️ 手动勾选单词"],
    horizontal=True,
)

shuffle_on = st.toggle("🔀 乱序排列本轮刷题顺序", value=True)

selected_pool = []

if mode == "🎲 指定数量随机抽取":
    default_n = min(20, len(book_words))
    draw_n = st.number_input(
        "抽取数量",
        min_value=1,
        max_value=len(book_words),
        value=default_n,
        step=1,
    )
    st.caption("点击开始后，将从当前词本随机抽取指定数量进入本轮卡片队列。")

    if st.button("🚀 生成刷题队列并开始", type="primary", use_container_width=True):
        indices = random.sample(range(len(book_words)), int(draw_n))
        if not shuffle_on:
            indices.sort()
        selected_pool = [dict(book_words[i]) for i in indices]

else:
    keyword = st.text_input("🔍 关键词过滤（按单词或释义筛选，不清空下方已勾选状态可留空）", "")
    select_all = st.checkbox("全选当前列表", value=False)

    df = pd.DataFrame([
        {
            "选择": select_all,
            "单词": w["word"],
            "音标": w["phonetic"],
            "释义": w["meaning"],
            "_idx": idx,
        }
        for idx, w in enumerate(book_words)
        if not keyword.strip()
        or keyword.strip().lower() in w["word"].lower()
        or keyword.strip().lower() in w["meaning"].lower()
    ])

    if df.empty:
        st.info("没有匹配的单词。")
    else:
        edited_df = st.data_editor(
            df.drop(columns=["_idx"]),
            use_container_width=True,
            hide_index=True,
            height=360,
            column_config={
                "选择": st.column_config.CheckboxColumn("选择", default=False),
                "单词": st.column_config.TextColumn("单词", disabled=True),
                "音标": st.column_config.TextColumn("音标", disabled=True),
                "释义": st.column_config.TextColumn("释义", disabled=True),
            },
        )
        chosen_rows = df[edited_df["选择"].values]
        st.caption(f"已勾选 **{len(chosen_rows)}** 个单词")

        if st.button("🚀 用勾选单词开始刷题", type="primary", use_container_width=True, disabled=chosen_rows.empty):
            chosen_indices = chosen_rows["_idx"].tolist()
            selected_pool = [dict(book_words[i]) for i in chosen_indices]
            if shuffle_on:
                random.shuffle(selected_pool)

if selected_pool:
    # 初始化纯内存的本轮刷题状态（不写回飞书）
    st.session_state["study_queue"] = selected_pool
    st.session_state["initial_pool"] = [dict(w) for w in selected_pool]
    st.session_state["total_count"] = len(selected_pool)
    st.session_state["mastered_count"] = 0
    st.session_state["is_flipped"] = False
    st.session_state["session_stats"] = {"forgot": 0, "vague": 0, "know": 0}
    st.switch_page("views/study.py")
