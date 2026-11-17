import re
from collections import Counter
from typing import Dict, List
import pandas as pd
import streamlit as st
from feishu_api import (
    batch_create_words,
    clear_data_cache,
    create_wordbook,
    load_all_words,
    load_wordbooks,
)


def parse_bulk_text(raw_text: str) -> List[Dict[str, str]]:
    """
    支持多格式批量解析，每行一个单词，字段支持 Tab、| 或中文/英文逗号分隔（建议用 | 或 Tab，防止释义里包含逗号）：
    格式：单词 | 音标 | 释义 | 例句 | 助记
    最少只需：单词 | 释义
    """
    parsed = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        elif "|" in line:
            parts = [p.strip() for p in line.split("|")]
        else:
            parts = [p.strip() for p in re.split(r"[,，]", line, maxsplit=4)]

        word = parts[0] if len(parts) > 0 else ""
        if not word:
            continue

        # 兼容只有2列（单词 | 释义）的情况
        if len(parts) == 2:
            phonetic, meaning, example, mnemonic = "", parts[1], "", ""
        else:
            phonetic = parts[1] if len(parts) > 1 else ""
            meaning = parts[2] if len(parts) > 2 else ""
            example = parts[3] if len(parts) > 3 else ""
            mnemonic = parts[4] if len(parts) > 4 else ""

        parsed.append({
            "word": word,
            "phonetic": phonetic,
            "meaning": meaning,
            "example": example,
            "mnemonic": mnemonic,
        })
    return parsed


col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("🦶 fofoot · 佛脚")
    st.caption("临时抱佛脚专用闪卡工具 · 词库云端同步飞书，本轮自评阅后即焚")
with col_refresh:
    st.write("")
    if st.button("🔄 刷新", use_container_width=True, help="从飞书多维表格重新拉取最新词库"):
        clear_data_cache()
        st.rerun()

try:
    with st.spinner("正在连接飞书词库..."):
        wordbooks = load_wordbooks()
        all_words = load_all_words()
except Exception as e:
    st.error(f"连接飞书失败，请检查配置与表格权限：\n\n`{e}`")
    st.stop()

word_counts = Counter(w["wordbook"] for w in all_words)

tab_books, tab_import, tab_create = st.tabs(["📚 选择词本", "📥 批量导入单词", "➕ 新建词本"])

with tab_books:
    if not wordbooks:
        st.info("飞书里还没有词本，请先切换到「➕ 新建词本」创建一个吧。")
    else:
        for idx, book in enumerate(wordbooks):
            count = word_counts.get(book["name"], 0)
            with st.container(border=True):
                c1, c2 = st.columns([3, 1.3])
                with c1:
                    st.subheader(book["name"])
                    desc_text = book["desc"] if book["desc"] else "暂无简介"
                    st.caption(f"{desc_text} · 共 **{count}** 词")
                with c2:
                    st.write("")
                    if st.button(
                        "去选词 👉",
                        key=f"pick_{idx}_{book['record_id']}",
                        type="primary",
                        use_container_width=True,
                        disabled=(count == 0),
                    ):
                        st.session_state["selected_wordbook"] = book["name"]
                        st.switch_page("views/select_words.py")

with tab_import:
    if not wordbooks:
        st.warning("请先创建一个词本后再导入单词。")
    else:
        book_names = [b["name"] for b in wordbooks]
        default_idx = 0
        if st.session_state.get("selected_wordbook") in book_names:
            default_idx = book_names.index(st.session_state["selected_wordbook"])

        target_book = st.selectbox("导入到哪个词本？", book_names, index=default_idx)
        st.markdown(
            "每行一个单词，推荐用 **`|`** 或 **Tab** 分隔：\n"
            "`单词 | 音标 | 释义 | 例句 | 助记`（后几项可省略，最少填 `单词 | 释义`）"
        )
        raw_text = st.text_area(
            "粘贴单词文本",
            height=180,
            placeholder=(
                "ephemeral | /ɪˈfemərəl/ | adj. 短暂的 | Fame is ephemeral. | e(出)+phemer(一天)→只活一天的\n"
                "ubiquitous | /juːˈbɪkwɪtəs/ | adj. 无所不在的 | Smartphones are ubiquitous. | ubi(哪里)+quit→到处都在"
            ),
        )

        uploaded = st.file_uploader("或者上传 CSV 文件（列名含 word, phonetic, meaning, example, mnemonic）", type=["csv"])

        preview_words: List[Dict[str, str]] = []
        if uploaded is not None:
            try:
                df_up = pd.read_csv(uploaded).fillna("")
                col_map = {c.lower().strip(): c for c in df_up.columns}
                w_col = col_map.get("word") or col_map.get("单词")
                if not w_col:
                    st.error("CSV 中未找到 `word` 或 `单词` 列。")
                else:
                    for _, row in df_up.iterrows():
                        w_val = str(row[w_col]).strip()
                        if not w_val:
                            continue
                        preview_words.append({
                            "word": w_val,
                            "phonetic": str(row[col_map["phonetic"]]) if "phonetic" in col_map else str(row.get("音标", "")),
                            "meaning": str(row[col_map["meaning"]]) if "meaning" in col_map else str(row.get("释义", "")),
                            "example": str(row[col_map["example"]]) if "example" in col_map else str(row.get("例句", "")),
                            "mnemonic": str(row[col_map["mnemonic"]]) if "mnemonic" in col_map else str(row.get("助记", "")),
                        })
            except Exception as e:
                st.error(f"解析 CSV 失败：{e}")
        elif raw_text.strip():
            preview_words = parse_bulk_text(raw_text)

        if preview_words:
            st.caption(f"已解析 **{len(preview_words)}** 个单词预览：")
            st.dataframe(pd.DataFrame(preview_words), use_container_width=True, hide_index=True)

            if st.button(f"确认写入飞书「{target_book}」", type="primary", use_container_width=True):
                try:
                    with st.spinner("正在批量写入飞书多维表格..."):
                        n = batch_create_words(target_book, preview_words)
                    st.success(f"成功导入 {n} 个单词到「{target_book}」！")
                    st.session_state["selected_wordbook"] = target_book
                except Exception as e:
                    st.error(f"导入出错：{e}")

with tab_create:
    with st.form("create_book_form", clear_on_submit=True):
        new_name = st.text_input("词本名称 *", placeholder="例如：六级考前急救高频词")
        new_desc = st.text_input("词本描述（可选）", placeholder="例如：历年真题生词汇总")
        submitted = st.form_submit_button("创建词本", type="primary", use_container_width=True)
        if submitted:
            if not new_name.strip():
                st.warning("词本名称不能为空。")
            elif any(b["name"] == new_name.strip() for b in wordbooks):
                st.warning("已存在同名词本，换个名字吧。")
            else:
                try:
                    create_wordbook(new_name, new_desc)
                    st.success(f"词本「{new_name.strip()}」创建成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败：{e}")
