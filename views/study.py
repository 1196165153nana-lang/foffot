import html
import streamlit as st

if "study_queue" not in st.session_state or "initial_pool" not in st.session_state:
    st.title("📖 闪卡刷题")
    st.info("当前还没有生成本轮刷题池，请先去选词。")
    if st.button("🎯 去选词", type="primary"):
        st.switch_page("views/select_words.py")
    st.stop()

queue = st.session_state["study_queue"]
total_count = st.session_state["total_count"]
mastered_count = st.session_state["mastered_count"]
stats = st.session_state["session_stats"]

# 顶部状态栏（仿墨墨简洁进度头）
top_l, top_r = st.columns([3.5, 1])
with top_l:
    progress = mastered_count / total_count if total_count > 0 else 1.0
    st.progress(progress)
    st.caption(
        f"本轮进度：**{mastered_count} / {total_count}** 已掌握 · "
        f"队列剩余 **{len(queue)}** 词 · *(临时记忆，关闭即清)*"
    )
with top_r:
    if st.button("结束本轮", use_container_width=True):
        for k in ("study_queue", "initial_pool", "total_count", "mastered_count", "is_flipped", "session_stats"):
            st.session_state.pop(k, None)
        st.switch_page("views/select_words.py")

# 队列已全部刷完 -> 结算页面
if not queue:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #ecfdf5 0%, #f0f9ff 100%);
            border: 1px solid #a7f3d0;
            border-radius: 18px;
            padding: 36px 24px;
            text-align: center;
            margin: 16px 0 24px 0;
        ">
            <div style="font-size: 44px; margin-bottom: 8px;">🎉</div>
            <h2 style="margin: 0; color: #065f46;">本轮佛脚抱完啦！</h2>
            <p style="color: #047857; margin-top: 8px;">所有单词均已标记「认识」，本轮记录不会写入飞书。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ 认识（移出）", stats["know"])
    c2.metric("🤔 模糊（队尾）", stats["vague"])
    c3.metric("😰 忘记（靠前）", stats["forgot"])

    st.write("")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("🔄 原词再来一轮", type="primary", use_container_width=True):
            st.session_state["study_queue"] = [dict(w) for w in st.session_state["initial_pool"]]
            st.session_state["mastered_count"] = 0
            st.session_state["is_flipped"] = False
            st.session_state["session_stats"] = {"forgot": 0, "vague": 0, "know": 0}
            st.rerun()
    with b2:
        if st.button("🎯 重新选词", use_container_width=True):
            st.switch_page("views/select_words.py")
    with b3:
        if st.button("🏠 返回首页", use_container_width=True):
            st.switch_page("views/home.py")
    st.stop()

# 当前队首单词
current = queue[0]
word_html = html.escape(current["word"])
phonetic_html = html.escape(current["phonetic"]) if current["phonetic"] else ""
meaning_html = html.escape(current["meaning"]).replace("\n", "<br>") if current["meaning"] else "（暂无释义）"
example_html = html.escape(current["example"]).replace("\n", "<br>")
mnemonic_html = html.escape(current["mnemonic"]).replace("\n", "<br>")

is_flipped = st.session_state.get("is_flipped", False)

if not is_flipped:
    # 卡片正面：仅展示单词 + 音标
    st.markdown(
        f"""
        <div style="
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            padding: 68px 24px 56px 24px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            margin: 10px 0 14px 0;
        ">
            <div style="font-size: 42px; font-weight: 800; color: #111827; letter-spacing: 0.5px;">
                {word_html}
            </div>
            <div style="font-size: 18px; color: #6b7280; margin-top: 12px; font-family: sans-serif;">
                {phonetic_html}
            </div>
            <div style="font-size: 13px; color: #9ca3af; margin-top: 40px;">
                先尝试在脑中回忆释义，再点击下方按钮翻面
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit 后端渲染下，用铺满卡片宽度的按钮模拟点击翻卡
    if st.button("👁️ 点击翻面查看释义", type="primary", use_container_width=True):
        st.session_state["is_flipped"] = True
        st.rerun()

else:
    # 卡片反面：释义 + 例句 + 助记
    extra_blocks = ""
    if example_html:
        extra_blocks += f"""
        <div style="margin-top: 18px; padding: 12px 14px; background: #f8fafc; border-radius: 12px; border-left: 4px solid #3b82f6;">
            <div style="font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 4px;">例句</div>
            <div style="font-size: 15px; color: #334155; line-height: 1.6;">{example_html}</div>
        </div>
        """
    if mnemonic_html:
        extra_blocks += f"""
        <div style="margin-top: 12px; padding: 12px 14px; background: #fffbeb; border-radius: 12px; border-left: 4px solid #f59e0b;">
            <div style="font-size: 12px; color: #b45309; font-weight: 700; margin-bottom: 4px;">助记</div>
            <div style="font-size: 15px; color: #78350f; line-height: 1.6;">{mnemonic_html}</div>
        </div>
        """

    st.markdown(
        f"""
        <div style="
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            padding: 28px 26px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            margin: 10px 0 18px 0;
        ">
            <div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px;">
                <span style="font-size: 32px; font-weight: 800; color: #111827;">{word_html}</span>
                <span style="font-size: 16px; color: #6b7280;">{phonetic_html}</span>
            </div>
            <div style="margin-top: 18px;">
                <div style="font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 6px;">释义</div>
                <div style="font-size: 19px; font-weight: 600; color: #1e293b; line-height: 1.6;">{meaning_html}</div>
            </div>
            {extra_blocks}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 三档自评按钮（仅控制当前内存队列）
    col_forgot, col_vague, col_know = st.columns(3)

    with col_forgot:
        if st.button("😰 忘记\n(靠前再刷)", use_container_width=True):
            item = queue.pop(0)
            # 插入到队列靠前位置（跳过后面 2 个词再出现，避免原地连续重复）
            insert_pos = min(2, len(queue))
            queue.insert(insert_pos, item)
            stats["forgot"] += 1
            st.session_state["is_flipped"] = False
            st.rerun()

    with col_vague:
        if st.button("🤔 认识模糊\n(队尾再刷)", use_container_width=True):
            item = queue.pop(0)
            queue.append(item)
            stats["vague"] += 1
            st.session_state["is_flipped"] = False
            st.rerun()

    with col_know:
        if st.button("✅ 认识\n(移出队列)", type="primary", use_container_width=True):
            queue.pop(0)
            st.session_state["mastered_count"] += 1
            stats["know"] += 1
            st.session_state["is_flipped"] = False
            st.rerun()
