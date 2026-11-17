import os
from typing import Any, Dict, List
import requests
import streamlit as st

FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


def get_config(key: str) -> str:
    """优先从 Streamlit Secrets 读取配置，其次读取环境变量。"""
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(f"缺少配置项：{key}，请在 Streamlit Secrets 中填写。")
    return val


def extract_text(value: Any) -> str:
    """兼容飞书多维表格记录检索接口返回的文本格式（str 或 list[dict]）。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("text", "") or item.get("name", ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return str(value.get("text", "") or value.get("link", "")).strip()
    return str(value).strip()


@st.cache_data(ttl=5400, show_spinner=False)
def _fetch_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token（有效期 2 小时，缓存 1.5 小时）。"""
    url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(
        url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取飞书 Token 失败: {data}")
    return data["tenant_access_token"]


def _headers() -> Dict[str, str]:
    token = _fetch_tenant_token(
        get_config("FEISHU_APP_ID"),
        get_config("FEISHU_APP_SECRET"),
    )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _list_all_records(table_id: str) -> List[Dict[str, Any]]:
    """分页拉取指定数据表的全部记录。"""
    app_token = get_config("FEISHU_APP_TOKEN")
    url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"

    records: List[Dict[str, Any]] = []
    page_token = ""

    while True:
        params: Dict[str, Any] = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        resp = requests.post(url, headers=_headers(), params=params, json={}, timeout=20)
        data = resp.json()

        # 若 token 异常过期，清理缓存重试一次
        if data.get("code") in (99991663, 99991664):
            _fetch_tenant_token.clear()
            resp = requests.post(url, headers=_headers(), params=params, json={}, timeout=20)
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"读取飞书表格失败 (code={data.get('code')}): {data.get('msg')}")

        payload = data.get("data", {})
        records.extend(payload.get("items", []))
        if not payload.get("has_more"):
            break
        page_token = payload.get("page_token", "")

    return records


@st.cache_data(ttl=60, show_spinner=False)
def load_wordbooks() -> List[Dict[str, str]]:
    """加载词本表。"""
    table_id = get_config("FEISHU_WORDBOOK_TABLE_ID")
    items = _list_all_records(table_id)
    books = []
    for item in items:
        fields = item.get("fields", {})
        name = extract_text(fields.get("词本名称"))
        if name:
            books.append({
                "record_id": item.get("record_id", ""),
                "name": name,
                "desc": extract_text(fields.get("描述")),
            })
    return books


@st.cache_data(ttl=60, show_spinner=False)
def load_all_words() -> List[Dict[str, str]]:
    """加载单词表全部单词。"""
    table_id = get_config("FEISHU_WORD_TABLE_ID")
    items = _list_all_records(table_id)
    words = []
    for item in items:
        fields = item.get("fields", {})
        word = extract_text(fields.get("单词"))
        if not word:
            continue
        words.append({
            "record_id": item.get("record_id", ""),
            "wordbook": extract_text(fields.get("所属词本")),
            "word": word,
            "phonetic": extract_text(fields.get("音标")),
            "meaning": extract_text(fields.get("释义")),
            "example": extract_text(fields.get("例句")),
            "mnemonic": extract_text(fields.get("助记")),
        })
    return words


def clear_data_cache() -> None:
    """手动清理词库缓存，确保新增/修改后立即同步。"""
    load_wordbooks.clear()
    load_all_words.clear()


def create_wordbook(name: str, desc: str = "") -> None:
    """在飞书词本表中新建词本。"""
    app_token = get_config("FEISHU_APP_TOKEN")
    table_id = get_config("FEISHU_WORDBOOK_TABLE_ID")
    url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"fields": {"词本名称": name.strip(), "描述": desc.strip()}},
        timeout=15,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"创建词本失败: {data.get('msg')} ({data.get('code')})")
    clear_data_cache()


def batch_create_words(wordbook_name: str, words: List[Dict[str, str]]) -> int:
    """批量写入单词到飞书单词表（飞书单次上限 500 条，自动分批）。"""
    if not words:
        return 0

    app_token = get_config("FEISHU_APP_TOKEN")
    table_id = get_config("FEISHU_WORD_TABLE_ID")
    url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

    records_payload = []
    for w in words:
        records_payload.append({
            "fields": {
                "所属词本": wordbook_name,
                "单词": w.get("word", "").strip(),
                "音标": w.get("phonetic", "").strip(),
                "释义": w.get("meaning", "").strip(),
                "例句": w.get("example", "").strip(),
                "助记": w.get("mnemonic", "").strip(),
            }
        })

    total_created = 0
    for i in range(0, len(records_payload), 500):
        chunk = records_payload[i : i + 500]
        resp = requests.post(url, headers=_headers(), json={"records": chunk}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"批量导入失败: {data.get('msg')} ({data.get('code')})")
        total_created += len(chunk)

    clear_data_cache()
    return total_created
