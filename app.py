import os
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st
import requests


# =========================================================
# 基本設定
# =========================================================

API_BASE = "https://symantec-clark-albany-ski.trycloudflare.com"


def normalize_horse_name(name):
    if not isinstance(name, str):
        return ""
    # 全角・半角スペースをすべて削除して綺麗にする
    n = unicodedata.normalize("NFKC", name)
    return "".join(n.split())


def api_get(path, timeout=20):
    try:
        url = API_BASE.rstrip("/") + path
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"JRA-VAN APIとの通信に失敗しました。\n{e}")
        return None


st.set_page_config(
    page_title="本格競馬展開シミュレーター（JRA-VAN版）",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .main { background-color: #0b0b0b; color: #ffffff; }

    h1, h2, h3 {
        color: #f1c40f !important;
        font-family: sans-serif;
    }

    .stButton>button {
        background: linear-gradient(to bottom, #d4af37, #aa820a);
        color: #ffffff;
        font-weight: bold;
        border: 1px solid #ffd700;
        border-radius: 6px;
        width: 100%;
        padding: 10px;
        font-size: 16px;
    }

    .stButton>button:hover {
        background: linear-gradient(to bottom, #e6c547, #c1960d);
        border-color: #ffffff;
    }

    .race-info-box {
        background-color: #1a1a1a;
        border: 1px solid #d4af37;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #ffffff;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    "<h2 style='text-align: center; color: #f1c40f;'>"
    "本格競馬展開シミュレーター（JRA-VAN完全連携版・修正完了）"
    "</h2>",
    unsafe_allow_html=True,
)


# =========================================================
# 基準タイムExcel
# =========================================================

@st.cache_data
def load_base_data_excel():
    xlsx_files = [
        f for f in os.listdir(".")
        if f.lower().endswith(".xlsx")
        and "馬場別基準タイム" in f
    ]

    if not xlsx_files:
        return None, None

    excel_filename = xlsx_files[0]

    try:
        xls = pd.ExcelFile(excel_filename)
        df_baba = (
            pd.read_excel(excel_filename, sheet_name="馬場別基準タイム")
            if "馬場別基準タイム" in xls.sheet_names else None
        )
        df_f3 = (
            pd.read_excel(excel_filename, sheet_name="基準上がり3F")
            if "基準上がり3F" in xls.sheet_names else None
        )
        return df_baba, df_f3
    except Exception:
        return None, None


df_base_master, df_f3_master = load_base_data_excel()

if df_base_master is not None and "距離" in df_base_master.columns:
    df_base_master["距離_num"] = pd.to_numeric(
        df_base_master["距離"].astype(str).str.extract(r"(\d+)")[0],
        errors="coerce",
    )

if df_f3_master is not None and "距離" in df_f3_master.columns:
    df_f3_master["距離_num"] = pd.to_numeric(
        df_f3_master["距離"].astype(str).str.extract(r"(\d+)")[0],
        errors="coerce",
    )


# =========================================================
# 変換関数群
# =========================================================

def format_weight(value):
    if value is None:
        return np.nan
    try:
        return float(value) / 10.0
    except Exception:
        return np.nan


def format_odds(value):
    if value is None:
        return np.nan
    try:
        s = str(value).strip()
        if not s:
            return np.nan
        if s.isdigit():
            return int(s) / 10.0
        return float(s)
    except Exception:
        return np.nan


def style_from_value(value):
    mapping = {1: "逃げ", 2: "先行", 3: "差し", 4: "追込"}
    try:
        return mapping.get(int(value), "差し")
    except Exception:
        text = str(value)
        if "逃" in text: return "逃げ"
        if "先" in text: return "先行"
        if "追" in text: return "追込"
        return "差し"


def condition_from_code(value):
    mapping = {1: "良", 2: "稍重", 3: "重", 4: "不良"}
    try:
        return mapping.get(int(value), "良")
    except Exception:
        text = str(value)
        for x in ["不良", "重", "稍重", "良"]:
            if x in text:
                return x
        return "良"


def surface_from_race(race):
    surface_name = str(
        race.get("surface", race.get("surface_name", race.get("芝・ダ", "")))
    ).strip()
    if "ダ" in surface_name: return "ダート"
    if "芝" in surface_name: return "芝"
    if "障" in surface_name: return "障害"

    track_code = str(race.get("track_code", ""))
    if track_code.startswith("2"): return "ダート"
    if track_code.startswith("1"): return "芝"
    if track_code.startswith("3"): return "障害"
    return "芝"


def detect_class(race_name="", grade_code="", condition_code=""):
    race_name = str(race_name or "")
    grade_code = str(grade_code or "").strip().upper()
    condition_code = str(condition_code or "").strip()

    condition_map = {
        "701": "新馬", "703": "未勝利", "005": "1勝",
        "010": "2勝", "016": "3勝", "999": "OP",
    }
    grade_map = {"A": "G1", "B": "G2", "C": "G3"}

    if grade_code in grade_map: return grade_map[grade_code]
    if condition_code in condition_map: return condition_map[condition_code]
    if "G1" in race_name: return "G1"
    if "G2" in race_name: return "G2"
    if "G3" in race_name: return "G3"
    if "L" in race_name: return "L"
    if "新馬" in race_name: return "新馬"
    if "未勝利" in race_name: return "未勝利"
    if "1勝" in race_name: return "1勝"
    if "2勝" in race_name: return "2勝"
    if "3勝" in race_name: return "3勝"
    if "OP" in race_name: return "OP"
    return "OP"


# =========================================================
# レース一覧取得
# =========================================================

@st.cache_data(ttl=60)
def load_race_list():
    data = api_get("/races/latest?days=7")
    if isinstance(data, dict):
        return data.get("races", [])
    if isinstance(data, list):
        return data
    return []


race_list = load_race_list()


# =========================================================
# サイドバー
# =========================================================

st.sidebar.markdown("### 🏇 JRA-VANからレースを選択")

if not race_list:
    st.error("JRA-VANからレースデータを取得できませんでした。")
    st.stop()


def race_display_name(r):
    race_id = r.get("race_id", r.get("id", r.get("race_code", "")))
    date = r.get("date", r.get("kaisai_date", ""))
    place = r.get("place", r.get("場所", ""))
    race_no = r.get("race_no", r.get("race_bango", ""))
    name = r.get("name", r.get("kyosomei_hondai", ""))
    return f"{date} {place} {race_no}R {name} [{race_id}]"


race_options = [race_display_name(r) for r in race_list]
selected_race_label = st.sidebar.selectbox("🎯 レース", race_options)

selected_index = race_options.index(selected_race_label)
selected_race_summary = race_list[selected_index]
race_id = selected_race_summary.get(
    "race_id", selected_race_summary.get("id", selected_race_summary.get("race_code"))
)

race_detail = api_get(f"/race/{race_id}")
if not race_detail:
    st.error("選択したレースの詳細データを取得できませんでした。")
    st.stop()

if isinstance(race_detail, dict) and isinstance(race_detail.get("race"), dict):
    race_meta = race_detail["race"]
else:
    race_meta = race_detail

horses = race_detail.get("horses", [])
if not horses:
    st.error("出走馬データが取得できませんでした。")
    st.stop()

race_name = race_meta.get(
    "name", race_meta.get("kyosomei_hondai", selected_race_summary.get("name", ""))
)
race_place = str(
    race_meta.get("venue", race_meta.get("place", race_meta.get("場所", "不明")))
).strip()

try:
    race_distance = int(
        float(race_meta.get("distance", race_meta.get("kyori", 1600)))
    )
except Exception:
    race_distance = 1600

race_surface = surface_from_race(race_meta)
grade_code = str(race_meta.get("grade_code", "")).strip()
race_class = detect_class(race_name, grade_code, condition_code=race_meta.get("condition_code", ""))

surface_condition_code = (
    race_meta.get("shiba_babajotai_code")
    if race_surface == "芝"
    else race_meta.get("dirt_babajotai_code")
)
default_baba = condition_from_code(surface_condition_code)

race_rows = []
for h in horses:
    row = {
        "枠番": h.get("枠番", h.get("wakuban", 1)),
        "馬番": h.get("馬番", h.get("umaban", 1)),
        "馬名": normalize_horse_name(h.get("馬名", h.get("bamei", ""))),
        "オッズ": format_odds(h.get("オッズ", h.get("odds"))),
        "人気": h.get("人気", h.get("ninki")),
        "脚質": style_from_value(h.get("脚質", h.get("kyakushitsu", 3))),
        "得意馬場": "指定なし",
        "場所": race_place,
        "距離": race_distance,
        "芝・ダ": race_surface,
        "クラス": race_class,
        "馬場状態": default_baba,
        "当日の馬場": default_baba,
    }
    race_rows.append(row)

df_race = pd.DataFrame(race_rows)
df_race["馬名_clean"] = df_race["馬名"]

straight_lengths_dict = {
    "芝": {"新潟": 659.9, "東京": 525.9, "阪神": 473.6, "中京": 412.5, "京都": 403.9, "中山": 310.0, "小倉": 293.0, "函館": 262.1, "福島": 292.0, "札幌": 266.1},
    "ダ": {"新潟": 353.9, "東京": 501.6, "阪神": 352.7, "中京": 410.7, "京都": 329.1, "中山": 308.0, "小倉": 291.0, "函館": 260.1, "福島": 295.7, "札幌": 264.3},
}
toughness_dict = {"中山": 1.10, "札幌": 1.15, "函館": 1.20, "阪神": 1.00, "福島": 1.10, "京都": 1.00, "中京": 1.05, "小倉": 1.05, "東京": 0.95, "新潟": 0.90}

surface_key = "ダ" if "ダ" in race_surface else "芝"
straight_len = 400.0
for k, v in straight_lengths_dict[surface_key].items():
    if k in race_place:
        straight_len = v
        break

course_toughness = 1.10
for k, v in toughness_dict.items():
    if k in race_place:
        course_toughness = v
        break

# 出馬表エディタ
edit_columns = ["枠番", "馬番", "馬名", "オッズ", "脚質", "得意馬場"]
edited_df = st.data_editor(
    df_race[edit_columns],
    column_config={
        "脚質": st.column_config.SelectboxColumn("脚質", options=["逃げ", "先行", "差し", "追込"], required=True),
        "得意馬場": st.column_config.SelectboxColumn("得意馬場", options=["指定なし", "良", "稍重", "重", "不良"], required=True),
        "オッズ": st.column_config.NumberColumn("オッズ", format="%.1f"),
    },
    use_container_width=True,
    hide_index=True,
    key="race_data_editor",
)

for col in edit_columns:
    df_race[col] = edited_df[col]

df_race["馬名"] = df_race["馬名"].apply(normalize_horse_name)
df_race["馬名_clean"] = df_race["馬名"]

selected_pace = st.sidebar.radio("ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1)
selected_bias = st.sidebar.radio("トラックバイアス", ["フラット", "内有利", "外有利"], index=0)
selected_condition = st.sidebar.selectbox("当日の馬場状態", ["良", "稍重", "重", "不良"], index=0)

if race_distance <= 1400: race_category = "短距離"
elif race_distance <= 1800: race_category = "マイル"
elif race_distance <= 2200: race_category = "中距離"
else: race_category = "長距離"


def format_time(seconds):
    m = int(seconds // 60)
    s = seconds % 60
    if m > 0: return f"{m}分{s:04.1f}秒"
    return f"{s:.1f}秒"


@st.cache_data(ttl=300)
def load_horse_history(horse_name):
    encoded_name = requests.utils.quote(horse_name, safe="")
    data = api_get(f"/horse/{encoded_name}/history", timeout=30)
    if isinstance(data, dict):
        return data.get("history", data.get("races", []))
    elif isinstance(data, list):
        return data
    return []


def build_master_data_from_jv(df_current):
    all_history = []
    for horse_name in df_current["馬名"].tolist():
        history = load_horse_history(normalize_horse_name(horse_name))
        for h in history:
            h["_target_horse_name"] = horse_name
            all_history.append(h)

    if not all_history:
        return pd.DataFrame()

    rows = []
    for h in all_history:
        horse_name = normalize_horse_name(h.get("馬名", h.get("bamei", h.get("_target_horse_name", ""))))
        
        raw_finish = h.get("kakutei_chakujun", h.get("着順", np.nan))
        finish = np.nan
        try:
            if raw_finish is not None:
                f_str = str(raw_finish).strip()
                # "00" や "0" は未確定・出走前データなので除外する
                if f_str and f_str != "00" and f_str != "0":
                    import re
                    match_f = re.search(r'\d+', f_str)
                    if match_f:
                        val = int(match_f.group(0))
                        if val > 0:
                            finish = float(val)
        except Exception:
            pass

        rows.append({
            "馬名": horse_name,
            "馬名_clean": horse_name,
            "場所": str(h.get("場所", h.get("place", ""))),
            "距離": float(h.get("距離", h.get("kyori", 0)) or 0),
            "着順": finish,
            "年": h.get("年", h.get("kaisai_nen", np.nan)),
            "月": h.get("月", np.nan),
            "日": h.get("日", np.nan),
        })

    return pd.DataFrame(rows)


# =========================================================
# シミュレーション実行ボタン
# =========================================================

if st.button("🚀 シミュレーション実行"):
    master_data = build_master_data_from_jv(df_race)

    if master_data.empty:
        st.error("有効な過去走データが構築できませんでした。")
    else:
        st.success(f"過去走データの読み込みに成功しました！（総レコード数: {len(master_data)}件）")
        
        # サンプルとしてロブチェン等の着順データを確認表示
        st.write("### 📊 読み込んだ過去走の着順サンプル確認", master_data[["馬名", "場所", "距離", "着順", "年"]].head(10))
        
        # 簡易的な能力計算や表示のシミュレーション処理をここに繋げられます
        st.info("ここに本来の展開・能力シミュレーション結果を表示します。")
