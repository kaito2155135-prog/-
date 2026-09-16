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
    return unicodedata.normalize("NFKC", name).strip()


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
    "本格競馬展開シミュレーター（JRA-VAN完全連携版）"
    "</h2>",
    unsafe_allow_html=True,
)


# =========================================================
# 基準タイムExcel
# =========================================================

@st.cache_data
def load_base_data_excel():
    excel_filename = "JRA_基準上がり3F_実データ集計_修正版.xlsx"

    if not os.path.exists(excel_filename):
        return None, None

    try:
        xls = pd.ExcelFile(excel_filename)

        df_baba = (
            pd.read_excel(
                excel_filename,
                sheet_name="馬場別基準タイム"
            )
            if "馬場別基準タイム" in xls.sheet_names
            else None
        )

        df_f3 = (
            pd.read_excel(
                excel_filename,
                sheet_name="基準上がり3F"
            )
            if "基準上がり3F" in xls.sheet_names
            else None
        )

        return df_baba, df_f3

    except Exception as e:
        st.error(f"基準タイムExcelの読み込みに失敗しました: {e}")
        return None, None


df_base_master, df_f3_master = load_base_data_excel()


if df_base_master is not None and "距離" in df_base_master.columns:
    df_base_master["距離_num"] = pd.to_numeric(
        df_base_master["距離"]
        .astype(str)
        .str.extract(r"(\d+)")[0],
        errors="coerce",
    )


if df_f3_master is not None and "距離" in df_f3_master.columns:
    df_f3_master["距離_num"] = pd.to_numeric(
        df_f3_master["距離"]
        .astype(str)
        .str.extract(r"(\d+)")[0],
        errors="coerce",
    )


# =========================================================
# JRA-VAN用変換
# =========================================================

def format_time_seconds(value):
    """
    JRA-VANの走破タイムを秒に変換。
    """

    if value is None:
        return np.nan

    try:
        if isinstance(value, str):
            value = value.strip()

            if not value:
                return np.nan

            # 1:34.5 のような形式
            if ":" in value:
                parts = value.split(":")
                if len(parts) == 2:
                    return (
                        float(parts[0]) * 60.0
                        + float(parts[1])
                    )

        num = float(value)

        # 通常の秒表記
        # 例：132.5 → 132.5秒
        if num < 300:
            return num

        # JRA-VAN側で10倍された走破タイム
        # 例：1325 → 132.5秒
        if num < 10000:
            return num / 10.0

        # 念のため100倍形式にも対応
        # 例：13250 → 132.5秒
        return num / 100.0

    except Exception:
        return np.nan


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
    mapping = {
        1: "逃げ",
        2: "先行",
        3: "差し",
        4: "追込",
    }

    try:
        ivalue = int(value)
        return mapping.get(ivalue, "差し")
    except Exception:
        text = str(value)

        if "逃" in text:
            return "逃げ"
        if "先" in text:
            return "先行"
        if "追" in text:
            return "追込"

        return "差し"


def condition_from_code(value):
    mapping = {
        1: "良",
        2: "稍重",
        3: "重",
        4: "不良",
    }

    try:
        return mapping.get(int(value), "良")
    except Exception:
        text = str(value)

        for x in ["不良", "重", "稍重", "良"]:
            if x in text:
                return x

        return "良"


def surface_from_race(race):
    """
    API側のsurfaceを最優先。
    なければ従来の項目やtrack_codeから判定。
    """

    surface_name = str(
        race.get(
            "surface",
            race.get(
                "surface_name",
                race.get("芝・ダ", "")
            )
        )
    ).strip()

    if "ダ" in surface_name:
        return "ダート"

    if "芝" in surface_name:
        return "芝"

    if "障" in surface_name:
        return "障害"

    track_code = str(
        race.get("track_code", "")
    )

    if track_code.startswith("2"):
        return "ダート"

    if track_code.startswith("1"):
        return "芝"

    if track_code.startswith("3"):
        return "障害"

    return "芝"


# =========================================================
# クラス判定
# =========================================================

def detect_class(race_name="", grade_code="", condition_code=""):
    """
    JRA-VANのgrade_code・競走条件コード・レース名からクラスを判定
    """

    race_name = str(race_name or "")
    grade_code = str(grade_code or "").strip().upper()

    condition_code = str(condition_code or "").strip()

    condition_map = {
    "701": "新馬",
    "703": "未勝利",
    "005": "1勝",
    "010": "2勝",
    "016": "3勝",
    "999": "OP",
}

    # JRA-VAN grade_code
    grade_map = {
        "A": "G1",
        "B": "G2",
        "C": "G3",
    }

    if grade_code in grade_map:
        return grade_map[grade_code]

    if condition_code in condition_map:
        return condition_map[condition_code]
        
    # レース名から判定
    if "G1" in race_name:
        return "G1"

    if "G2" in race_name:
        return "G2"

    if "G3" in race_name:
        return "G3"

    if "L" in race_name:
        return "L"

    if "新馬" in race_name:
        return "新馬"

    if "未勝利" in race_name:
        return "未勝利"

    if "1勝" in race_name:
        return "1勝"

    if "2勝" in race_name:
        return "2勝"

    if "3勝" in race_name:
        return "3勝"

    if "OP" in race_name:
        return "OP"

    return "OP"


# =========================================================
# JRA-VAN レース一覧
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
    st.error(
        "JRA-VANからレースデータを取得できませんでした。\n"
        "Windows側のFlask APIとCloudflare Tunnelが起動しているか確認してください。"
    )
    st.stop()


def race_display_name(r):
    race_id = r.get("race_id", r.get("id", r.get("race_code", "")))
    date = r.get("date", r.get("kaisai_date", ""))
    place = r.get("place", r.get("場所", ""))
    race_no = r.get("race_no", r.get("race_bango", ""))

    name = r.get(
        "name",
        r.get("kyosomei_hondai", "")
    )

    return (
        f"{date} {place} "
        f"{race_no}R {name} "
        f"[{race_id}]"
    )


race_options = [
    race_display_name(r)
    for r in race_list
]

selected_race_label = st.sidebar.selectbox(
    "🎯 レース",
    race_options,
)


selected_index = race_options.index(selected_race_label)
selected_race_summary = race_list[selected_index]


race_id = selected_race_summary.get(
    "race_id",
    selected_race_summary.get(
        "id",
        selected_race_summary.get("race_code")
    )
)


# =========================================================
# 選択レース詳細
# =========================================================

race_detail = api_get(f"/race/{race_id}")


if not race_detail:
    st.error("選択したレースの詳細データを取得できませんでした。")
    st.stop()


# APIによっては race 情報がraceキーの中にある場合にも対応
if isinstance(race_detail, dict) and isinstance(
    race_detail.get("race"), dict
):
    race_meta = race_detail["race"]
else:
    race_meta = race_detail

horses = race_detail.get("horses", [])


if not horses:
    st.error("出走馬データが取得できませんでした。")
    st.stop()


# =========================================================
# 現在レースのdf_race作成
# =========================================================

race_name = race_meta.get(
    "name",
    race_meta.get(
        "kyosomei_hondai",
        selected_race_summary.get("name", "")
    )
)


race_place = str(
    race_meta.get(
        "venue",
        race_meta.get(
            "place",
            race_meta.get(
                "場所",
                selected_race_summary.get(
                    "venue",
                    selected_race_summary.get(
                        "place",
                        "不明"
                    )
                )
            )
        )
    )
).strip()


try:
    race_distance = int(
        float(
            race_meta.get(
                "distance",
                race_meta.get(
                    "kyori",
                    selected_race_summary.get("distance", 1600)
                )
            )
        )
    )
except Exception:
    race_distance = 1600


race_surface = surface_from_race(race_meta)


grade_code = str(race_meta.get("grade_code", "")).strip()

race_class = detect_class(
    race_name,
    grade_code,
    condition_code=race_meta.get("condition_code", "")
)

st.write(
    "クラス判定確認:",
    race_name,
    "grade_code=",
    repr(grade_code),
    "condition_code=",
    repr(race_meta.get("condition_code", ""))
)

# 馬場状態
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
        "馬名": h.get("馬名", h.get("bamei", "")),
        "オッズ": format_odds(
            h.get("オッズ", h.get("odds"))
        ),
        "人気": h.get(
            "人気",
            h.get("ninki")
        ),
        "脚質": style_from_value(
            h.get("脚質", h.get("kyakushitsu", 3))
        ),
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


df_race["馬名"] = df_race["馬名"].apply(normalize_horse_name)
df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)


# =========================================================
# 直線・コース補正
# =========================================================

straight_lengths_dict = {
    "芝": {
        "新潟": 659.9,
        "東京": 525.9,
        "阪神": 473.6,
        "中京": 412.5,
        "京都": 403.9,
        "中山": 310.0,
        "小倉": 293.0,
        "函館": 262.1,
        "福島": 292.0,
        "札幌": 266.1,
    },
    "ダ": {
        "新潟": 353.9,
        "東京": 501.6,
        "阪神": 352.7,
        "中京": 410.7,
        "京都": 329.1,
        "中山": 308.0,
        "小倉": 291.0,
        "函館": 260.1,
        "福島": 295.7,
        "札幌": 264.3,
    },
}


toughness_dict = {
    "中山": 1.10,
    "札幌": 1.15,
    "函館": 1.20,
    "阪神": 1.00,
    "福島": 1.10,
    "京都": 1.00,
    "中京": 1.05,
    "小倉": 1.05,
    "東京": 0.95,
    "新潟": 0.90,
}


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


# =========================================================
# 表示
# =========================================================

st.sidebar.markdown("---")

st.sidebar.info(
    f"**{race_place} {race_class}**\n\n"
    f"{race_distance}m {race_surface}\n\n"
    f"馬場: {default_baba}\n\n"
    f"頭数: {len(df_race)}頭"
)


st.markdown(
    f"""
    <div class="race-info-box">
        <h3 style="margin: 0; color: #f1c40f;">
            📌 JRA-VAN読み込み済みレース
        </h3>

        <p style="font-size: 18px; margin: 5px 0 0 0;">
            <b>競馬場:</b> {race_place}
            (直線: {straight_len}m)
            &nbsp;|&nbsp;

            <b>馬場種別:</b> {race_surface}
            &nbsp;|&nbsp;

            <b>距離:</b> {race_distance}m
            &nbsp;|&nbsp;

            <b>クラス:</b> {race_class}
            &nbsp;|&nbsp;

            <b>馬場状態:</b> {default_baba}
            &nbsp;|&nbsp;

            <b>出走頭数:</b> {len(df_race)}頭
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 出馬表編集
# =========================================================

for c in [
    "枠番",
    "馬番",
    "馬名",
    "オッズ",
    "脚質",
    "得意馬場",
]:
    if c not in df_race.columns:

        if c == "脚質":
            df_race[c] = "差し"

        elif c == "得意馬場":
            df_race[c] = "指定なし"

        elif c == "オッズ":
            df_race[c] = 10.0

        else:
            df_race[c] = 1


edit_columns = [
    "枠番",
    "馬番",
    "馬名",
    "オッズ",
    "脚質",
    "得意馬場",
]


edited_df = st.data_editor(
    df_race[edit_columns],

    column_config={
        "脚質": st.column_config.SelectboxColumn(
            "脚質",
            options=["逃げ", "先行", "差し", "追込"],
            required=True,
        ),

        "得意馬場": st.column_config.SelectboxColumn(
            "得意馬場",
            options=[
                "指定なし",
                "良",
                "稍重",
                "重",
                "不良",
            ],
            required=True,
        ),

        "オッズ": st.column_config.NumberColumn(
            "オッズ",
            format="%.1f",
        ),
    },

    use_container_width=True,
    hide_index=True,
    key="race_data_editor",
)


for col in edit_columns:
    df_race[col] = edited_df[col]


df_race["馬名"] = df_race["馬名"].apply(normalize_horse_name)
df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)


# =========================================================
# ペース・バイアス・馬場
# =========================================================

st.markdown("---")


col_p1, col_p2, col_p3 = st.columns(3)


with col_p1:
    selected_pace = st.radio(
        "ペース想定",
        ["S（スロー）", "M（ミドル）", "H（ハイ）"],
        index=1,
    )


with col_p2:
    selected_bias = st.radio(
        "トラックバイアス",
        ["フラット", "内有利", "外有利"],
        index=0,
    )


with col_p3:

    baba_default_idx = 0

    if default_baba == "稍重":
        baba_default_idx = 1
    elif default_baba == "重":
        baba_default_idx = 2
    elif default_baba == "不良":
        baba_default_idx = 3

    selected_condition = st.selectbox(
        "当日の馬場状態",
        ["良", "稍重", "重", "不良"],
        index=baba_default_idx,
    )


# =========================================================
# 距離カテゴリー
# =========================================================

if race_distance <= 1400:
    race_category = "短距離"

elif race_distance <= 1800:
    race_category = "マイル"

elif race_distance <= 2200:
    race_category = "中距離"

else:
    race_category = "長距離"


st.markdown("---")


def format_time(seconds):
    m = int(seconds // 60)
    s = seconds % 60

    if m > 0:
        return f"{m}分{s:04.1f}秒"

    return f"{s:.1f}秒"


# =========================================================
# JRA-VAN → 既存master_data形式
# =========================================================

@st.cache_data(ttl=300)
def load_horse_history(horse_name):

    encoded_name = requests.utils.quote(
        horse_name,
        safe=""
    )

    data = api_get(
        f"/horse/{encoded_name}/history",
        timeout=30
    )

    if isinstance(data, dict):
        history = data.get(
            "history",
            data.get("races", [])
        )
    elif isinstance(data, list):
        history = data
    else:
        history = []

    return history


def build_master_data_from_jv(df_current):

    all_history = []

    progress = st.progress(
        0,
        text="JRA-VANから過去走データを取得中..."
    )

    total = len(df_current)

    for i, horse_name in enumerate(
        df_current["馬名"].tolist()
    ):

        history = load_horse_history(
            normalize_horse_name(horse_name)
        )

        for h in history:
            all_history.append(h)

        progress.progress(
            (i + 1) / max(total, 1),
            text=(
                f"過去走取得中 "
                f"{i + 1}/{total}頭: {horse_name}"
            )
        )

    progress.empty()

    if not all_history:
        return pd.DataFrame()

    rows = []

    for h in all_history:

        horse_name = normalize_horse_name(
            h.get(
                "馬名",
                h.get("bamei", "")
            )
        )

        if not horse_name:
            continue

        # 場所
        place = h.get(
            "場所",
            h.get(
                "place",
                h.get("keibajo_name", "")
            )
        )

        # 距離
        distance = h.get(
            "距離",
            h.get(
                "kyori",
                0
            )
        )

        try:
            distance = float(distance)
        except Exception:
            distance = np.nan

        # 芝ダート
        surface = h.get(
            "芝・ダ",
            h.get(
                "surface_name",
                ""
            )
        )

        surface = str(surface)

        if "ダ" in surface:
            surface = "ダート"
        elif "芝" in surface:
            surface = "芝"

        # レース名
        race_name = h.get(
            "kyosomei_hondai",
            h.get(
                "レース名",
                h.get(
                    "name",
                    ""
                )
            )
        )

        # クラス
        historical_class = detect_class(
    race_name,
    h.get("grade_code", ""),
    condition_code=h.get("condition_code", "")
)

        # 馬場状態
        baba = h.get(
            "馬場状態",
            h.get(
                "馬場",
                ""
            )
        )

        if not baba:

            track_code = str(
                h.get("track_code", "")
            )

            if track_code.startswith("1"):
                baba_code = h.get(
                    "shiba_babajotai_code"
                )
            else:
                baba_code = h.get(
                    "dirt_babajotai_code"
                )

            baba = condition_from_code(
                baba_code
            )

        # 走破タイム
        soha_time = h.get(
            "走破タイム",
            h.get(
                "soha_time",
                np.nan
            )
        )

        soha_time = format_time_seconds(
            soha_time
        )

        # 上がり3F
        f3 = h.get(
            "上がり3Fタイム",
            h.get(
                "kohan_3f",
                np.nan
            )
        )

        try:
            f3 = float(f3)
        except Exception:
            f3 = np.nan

        # 着順
        finish = h.get(
            "着順",
            h.get(
                "kakutei_chakujun",
                np.nan
            )
        )

        try:
            finish = float(finish)
        except Exception:
            finish = np.nan

        # 日付
        date_value = h.get(
            "date",
            h.get(
                "kaisai_date",
                ""
            )
        )

        year = h.get("年", np.nan)
        month = h.get("月", np.nan)
        day = h.get("日", np.nan)

        if (
            pd.isna(year)
            or pd.isna(month)
            or pd.isna(day)
        ):

            date_str = str(date_value)

            if len(date_str) >= 10:

                try:
                    dt = pd.to_datetime(
                        date_str,
                        errors="coerce"
                    )

                    if not pd.isna(dt):
                        year = dt.year
                        month = dt.month
                        day = dt.day

                except Exception:
                    pass

        rows.append(
            {
                "馬名": horse_name,
                "馬名_clean": horse_name,

                "場所": str(place),

                "距離": distance,

                "走破タイム": soha_time,

                "上がり3Fタイム": f3,

                "馬場状態": str(baba),

                "芝・ダ": surface,

                "略レース名": historical_class,

                "クラス": historical_class,

                "着順": finish,

                "年": year,
                "月": month,
                "日": day,

                "斤量": format_weight(
                    h.get("斤量", h.get("futan_juryo"))
                ),
            }
        )

    master_df = pd.DataFrame(rows)

    if master_df.empty:
        return master_df

    # JRA競馬場だけ
    jra_places = [
        "東京",
        "中山",
        "京都",
        "阪神",
        "中京",
        "札幌",
        "函館",
        "福島",
        "新潟",
        "小倉",
    ]

    if "場所" in master_df.columns:

        master_df = master_df[
            master_df["場所"]
            .astype(str)
            .str.contains(
                "|".join(jra_places),
                na=False
            )
        ].copy()

    # 日付で新しい順
    sort_cols = [
        c
        for c in ["年", "月", "日"]
        if c in master_df.columns
    ]

    if sort_cols:
        master_df = master_df.sort_values(
            sort_cols,
            ascending=False
        )

    return master_df


# =========================================================
# 既存の予想エンジン
# =========================================================

def run_integrated_simulation(
    df_r,
    pace,
    bias,
    condition,
    master_data,
    target_cat,
    straight_length,
    place_name,
    surface_type,
    toughness_val,
    target_cls,
    base_master_df,
    f3_master_df,
):

    res_df = df_r.copy()

    try:
        target_distance = float(
            res_df.iloc[0].get(
                "距離",
                1600.0
            )
        )
    except Exception:
        target_distance = 1600.0

    surface = str(surface_type).strip()

    surface_keyword = (
        "ダート"
        if "ダ" in surface
        else "芝"
    )



    # =====================================================
    # 現在レースの基準走破タイム
    # =====================================================

    target_base_seconds = 0.0

    if base_master_df is not None:

        match_target = base_master_df[
            (
                base_master_df["競馬場"]
                .astype(str)
                .str.contains(
                    place_name,
                    na=False
                )
            )
            &
            (
                base_master_df["芝/ダート"]
                ==
                (
                    "ダ"
                    if "ダ" in surface
                    else "芝"
                )
            )
            &
            (
                base_master_df["距離_num"]
                ==
                target_distance
            )
            &
            (
                base_master_df["クラス"]
                .astype(str)
                .str.contains(
                    class_keyword,
                    na=False
                )
            )
        ]

        if match_target.empty:

            match_target = base_master_df[
                (
                    base_master_df["競馬場"]
                    .astype(str)
                    .str.contains(
                        place_name,
                        na=False
                    )
                )
                &
                (
                    base_master_df["芝/ダート"]
                    ==
                    (
                        "ダ"
                        if "ダ" in surface
                        else "芝"
                    )
                )
                &
                (
                    base_master_df["距離_num"]
                    ==
                    target_distance
                )
            ]

        if not match_target.empty:

            baba_col = (
                condition
                if condition in [
                    "良",
                    "稍重",
                    "重",
                    "不良"
                ]
                else "良"
            )

            target_base_seconds = pd.to_numeric(
                match_target.iloc[0][baba_col],
                errors="coerce"
            )

    if (
        pd.isna(target_base_seconds)
        or target_base_seconds <= 0
    ):

        if "ダ" in surface:
            target_base_seconds = (
                target_distance
                / 1000.0
            ) * 62.5
        else:
            target_base_seconds = (
                target_distance
                / 1000.0
            ) * 59.0

    # =====================================================
    # 現在レースの基準上がり3F
    # =====================================================

    target_base_f3 = 0.0

    if f3_master_df is not None:

        match_f3 = f3_master_df[
            (
                f3_master_df["競馬場"]
                .astype(str)
                .str.contains(
                    place_name,
                    na=False
                )
            )
            &
            (
                f3_master_df["芝/ダート"]
                ==
                surface_keyword
            )
            &
            (
                f3_master_df["距離_num"]
                ==
                target_distance
            )
            &
            (
                f3_master_df["クラス"]
                .astype(str)
                .str.contains(
                    class_keyword,
                    na=False
                )
            )
        ]

        if match_f3.empty:

            match_f3 = f3_master_df[
                (
                    f3_master_df["競馬場"]
                    .astype(str)
                    .str.contains(
                        place_name,
                        na=False
                    )
                )
                &
                (
                    f3_master_df["芝/ダート"]
                    ==
                    surface_keyword
                )
                &
                (
                    f3_master_df["距離_num"]
                    ==
                    target_distance
                )
            ]

        if not match_f3.empty:

            baba_col = (
                condition
                if condition in [
                    "良",
                    "稍重",
                    "重",
                    "不良"
                ]
                else "良"
            )

            if baba_col in match_f3.columns:

                target_base_f3 = pd.to_numeric(
                    match_f3.iloc[0][baba_col],
                    errors="coerce"
                )

    if (
        pd.isna(target_base_f3)
        or target_base_f3 <= 0
    ):

        target_base_f3 = (
            34.5
            if "芝" in surface
            else 37.0
        )

    # =====================================================
    # 上がり3F重み
    # =====================================================

    if "ダ" in surface:

        f3_weight_factor = max(
            0.5,
            min(
                1.15,
                straight_length / 450.0
            )
        )

    else:

        f3_weight_factor = max(
            0.4,
            min(
                1.6,
                straight_length / 350.0
            )
        )

    horse_ability_map = {}
    horse_f3_theory_bonus_map = {}
    horse_course_fit_map = {}
    horse_soha_theory_map = {}
    horse_predicted_time_map = {}
    rising_star_map = {}

    # =====================================================
    # 過去走データ
    # =====================================================

    if (
        master_data is not None
        and not master_data.empty
        and "馬名_clean" in master_data.columns
    ):

        sort_cols = [
            c
            for c in ["年", "月", "日"]
            if c in master_data.columns
        ]

        if sort_cols:

            master_data = master_data.sort_values(
                by=sort_cols,
                ascending=False
            )

        # 現在の芝/ダートと同じ過去走だけを見る
        if "芝・ダ" in master_data.columns:

            if "ダ" in surface_keyword:

                filtered_master = master_data[
                    master_data["芝・ダ"]
                    .astype(str)
                    .str.contains(
                        "ダ",
                        na=False
                    )
                ].copy()

            else:

                filtered_master = master_data[
                    ~master_data["芝・ダ"]
                    .astype(str)
                    .str.contains(
                        "ダ",
                        na=False
                    )
                ].copy()

        else:

            filtered_master = master_data.copy()

        recent_master_data = (
            filtered_master
            .groupby("馬名_clean")
            .head(6)
            .copy()
        )

        class_rank_map = {
            "新馬": 1,
            "未勝利": 1,

            "1勝": 2,
            "1勝クラス": 2,

            "2勝": 3,
            "2勝クラス": 3,

            "3勝": 4,
            "3勝クラス": 4,

            "OP": 5,
            "オープン": 5,
            "リステッド": 5,

            "G3": 6,
            "G2": 7,
            "G1": 8,
        }

        # =================================================
        # ライジングスター
        # =================================================

        for hname, group in filtered_master.groupby(
            "馬名_clean"
        ):

            if (
                "着順" in group.columns
                and len(group) >= 2
            ):

                top2 = group.head(2)

                finishes = pd.to_numeric(
                    top2["着順"],
                    errors="coerce"
                ).tolist()

                if (
                    len(finishes) == 2
                    and finishes[0] == 1
                    and finishes[1] == 1
                ):

                    rising_star_map[hname] = True

                else:

                    rising_star_map[hname] = False

            else:

                rising_star_map[hname] = False

        # =================================================
        # 理論値計算
        # =================================================

        def calc_theories_score(group):

            if (
                "馬名_clean" in group.columns
                and not group["馬名_clean"].empty
            ):

                h_name = str(
                    group["馬名_clean"].iloc[0]
                )

            elif (
                "馬名" in group.columns
                and not group["馬名"].empty
            ):

                h_name = normalize_horse_name(
                    str(group["馬名"].iloc[0])
                )

            else:

                h_name = (
                    str(group.name)
                    if group.name
                    else "不明"
                )

            is_rising = rising_star_map.get(
                h_name,
                False
            )

            derived_times = []
            derived_f3s = []

            # ---------------------------------------------
            # 過去6走を1走ずつ処理
            # ---------------------------------------------

            for _, row in group.iterrows():

                r_course = str(
                    row.get(
                        "場所",
                        row.get(
                            "競馬場",
                            place_name
                        )
                    )
                ).strip()

                r_dist = pd.to_numeric(
                    row.get(
                        "距離",
                        0
                    ),
                    errors="coerce"
                )

                r_time = pd.to_numeric(
                    row.get(
                        "走破タイム",
                        0
                    ),
                    errors="coerce"
                )

                r_f3_time = pd.to_numeric(
                    row.get(
                        "上がり3Fタイム",
                        0
                    ),
                    errors="coerce"
                )

                r_baba = str(
                    row.get(
                        "馬場状態",
                        row.get(
                            "馬場",
                            "良"
                        )
                    )
                ).strip()

                r_surface = str(
                    row.get(
                        "芝・ダ",
                        surface
                    )
                ).strip()
                r_class = str(
                    row.get(
                        "略レース名",
                        row.get(
                            "クラス",
                            "OP"
                        )
                    )
                ).strip()

                r_class_keyword = (
                    str(r_class)
                    .strip()
                    .replace("クラス", "")
                )

                r_surface_keyword = (
                    "ダート"
                    if "ダ" in r_surface
                    else "芝"
                )

                r_surface_short = (
                    "ダ"
                    if "ダ" in r_surface
                    else "芝"
                )
                r_surface_short = (
                    "ダ"
                    if "ダ" in r_surface
                    else "芝"
                )

                if (
                    pd.isna(r_dist)
                    or r_dist <= 0
                ):
                    continue

                # -----------------------------------------
                # 過去コース補正
                # -----------------------------------------

                past_course_multiplier = 1.0

                if "小倉" in r_course:
                    past_course_multiplier = 1.11

                elif (
                    "函館" in r_course
                    or "札幌" in r_course
                ):
                    past_course_multiplier = 0.99

                past_c_rank = class_rank_map.get(
                    r_class.replace(
                        "クラス",
                        ""
                    ),
                    1
                )

                target_c_rank = class_rank_map.get(
                    target_cls.replace(
                        "クラス",
                        ""
                    ),
                    2
                )

                class_diff = (
                    target_c_rank
                    - past_c_rank
                )

                # =========================================
                # 走破タイム
                # =========================================

                if (
                    not pd.isna(r_time)
                    and r_time > 0
                ):

                    adjusted_r_time = (
                        r_time
                        * past_course_multiplier
                    )

                    past_base_time = 0.0

                    if base_master_df is not None:

                        m_match = base_master_df[
    (
        base_master_df["競馬場"]
        .astype(str)
        .str.contains(
            r_course,
            na=False
        )
    )
    &
    (
        base_master_df["芝/ダート"]
        ==
        r_surface_short
    )
    &
    (
        base_master_df["距離_num"]
        ==
        r_dist
    )
    &
    (
        base_master_df["クラス"]
        .astype(str)
        .str.contains(
            r_class_keyword,
            na=False
        )
    )
]

                        if m_match.empty:

                            m_match = base_master_df[
                                (
                                    base_master_df["競馬場"]
                                    .astype(str)
                                    .str.contains(
                                        r_course,
                                        na=False
                                    )
                                )
                                &
                                (
                                    base_master_df["芝/ダート"]
                                    ==
                                    r_surface_short
                                )
                                &
                                (
                                    base_master_df["距離_num"]
                                    ==
                                    r_dist
                                )
                            ]

                        if not m_match.empty:

                            b_col = (
                                r_baba
                                if r_baba in [
                                    "良",
                                    "稍重",
                                    "重",
                                    "不良"
                                ]
                                else "良"
                            )

                            if b_col in m_match.columns:

                                past_base_time = pd.to_numeric(
                                    m_match.iloc[0][b_col],
                                    errors="coerce"
                                )

                    if (
                        pd.isna(past_base_time)
                        or past_base_time <= 0
                    ):

                        past_base_time = (
                            r_dist
                            / 1000.0
                        ) * (
                            62.5
                            if r_surface_short == "ダ"
                            else 59.0
                        )

                    time_diff = (
                        past_base_time
                        - adjusted_r_time
                    )

                    furlong_diff = (
                        target_distance
                        - r_dist
                    ) / 200.0

                    if target_distance <= 1400:
                        furlong_weight = 1.15

                    elif target_distance <= 1800:
                        furlong_weight = 1.00

                    elif target_distance <= 2200:
                        furlong_weight = 0.85

                    else:
                        furlong_weight = 0.70

                    distance_penalty_or_bonus = (
                        furlong_diff
                        * furlong_weight
                    )

                    if is_rising:

                        class_level_penalty = 0.0

                    else:

                        class_level_penalty = (
                            (
                                class_diff
                                * 0.20
                            )
                            if class_diff > 0
                            else
                            (
                                class_diff
                                * 0.15
                            )
                        )

                    converted_time = (
                        target_base_seconds
                        - time_diff
                        + distance_penalty_or_bonus
                        + class_level_penalty
                    )

                    if is_rising:
                        converted_time -= 0.2

                    derived_times.append(
                        converted_time
                    )

                # =========================================
                # 上がり3F
                # =========================================

                if (
                    not pd.isna(r_f3_time)
                    and r_f3_time > 0
                ):

                    past_base_f3 = 0.0

                    if f3_master_df is not None:

                        f3_match = f3_master_df[
                            (
                                f3_master_df["競馬場"]
                                .astype(str)
                                .str.contains(
                                    r_course,
                                    na=False
                                )
                            )
                            &
                            (
                                f3_master_df["芝/ダート"]
                                ==
                                r_surface_keyword
                            )
                            &
                            (
                                f3_master_df["距離_num"]
                                ==
                                r_dist
                            )
                            &
(
    f3_master_df["クラス"]
    .astype(str)
    .str.contains(
        r_class_keyword,
        na=False
    )
)
                        ]

                        # ★ここが元コードのバグ修正箇所
                        if f3_match.empty:

                            f3_match = f3_master_df[
                                (
                                    f3_master_df["競馬場"]
                                    .astype(str)
                                    .str.contains(
                                        r_course,
                                        na=False
                                    )
                                )
                                &
                                (
                                    f3_master_df["芝/ダート"]
                                    ==
                                    r_surface_keyword
                                )
                                &
                                (
                                    f3_master_df["距離_num"]
                                    ==
                                    r_dist
                                )
                            ]

                        if not f3_match.empty:

                            b_col = (
                                r_baba
                                if r_baba in [
                                    "良",
                                    "稍重",
                                    "重",
                                    "不良"
                                ]
                                else "良"
                            )

                            if b_col in f3_match.columns:

                                past_base_f3 = pd.to_numeric(
                                    f3_match.iloc[0][b_col],
                                    errors="coerce"
                                )

                    if (
                        pd.isna(past_base_f3)
                        or past_base_f3 <= 0
                    ):

                        past_base_f3 = (
                            34.5
                            if r_surface_keyword == "芝"
                            else 37.0
                        )

                    f3_diff = (
                        r_f3_time
                        - past_base_f3
                    )

                    f3_class_adjustment = 0.0

                    if not is_rising:

                        if (
                            r_surface_keyword
                            == "ダート"
                        ):

                            if class_diff > 0:
                                f3_class_adjustment = (
                                    class_diff
                                    * 0.15
                                )

                            elif class_diff < 0:
                                f3_class_adjustment = (
                                    class_diff
                                    * 0.1
                                )

                    converted_f3 = (
                        target_base_f3
                        + f3_diff
                        + f3_class_adjustment
                    )

                    derived_f3s.append(
                        converted_f3
                    )

            # =============================================
            # 走破タイム指数
            # =============================================

            soha_score = 0.0

            if derived_times:

                sorted_times = sorted(
                    derived_times
                )

                val_to_use = float(
                    np.median(
                        sorted_times
                    )
                )

                st.write(
                    "予測タイム確認:",
                    h_name,
                    "換算値=",
                    [round(x, 1) for x in sorted_times],
                    "中央値=",
                    round(val_to_use, 1),
                    "今回基準=",
                    round(target_base_seconds, 1)
                )

                # 過去6走を今回条件へ換算した中央値を保存
                horse_predicted_time_map[h_name] = val_to_use

                time_advantage = (
                    target_base_seconds
                    - val_to_use
                )

                soha_score = max(
                    -5.0,
                    min(
                        12.0,
                        time_advantage * 3.0
                    )
                )

            # =============================================
            # 上がり3F指数
            # =============================================

            f3_score = 0.0

            if derived_f3s:

                sorted_f3s = sorted(
                    derived_f3s
                )

                f3_val_to_use = float(
                    np.median(
                        sorted_f3s
                    )
                )

                f3_advantage = (
                    target_base_f3
                    - f3_val_to_use
                )

                f3_score = max(
                    -3.0,
                    min(
                        10.0,
                        f3_advantage
                        * 2.5
                        * f3_weight_factor
                    )
                )

            # =============================================
            # 走破＋上がり統合
            # =============================================

            if straight_length < 320:

                combined_score = (
                    soha_score * 0.75
                    + f3_score * 0.25
                )

            elif 320 <= straight_length < 400:

                combined_score = (
                    soha_score * 0.7
                    + f3_score * 0.3
                )

            else:

                combined_score = (
                    soha_score * 0.6
                    + f3_score * 0.4
                )

            return pd.Series(
                {
                    "soha_score": soha_score,
                    "f3_score": f3_score,
                    "combined_score": combined_score,
                    "is_rising_star": is_rising,
                }
            )

        # =================================================
        # 全馬計算
        # =================================================

        theories_df = (
            recent_master_data
            .groupby("馬名_clean")
            .apply(
                calc_theories_score
            )
        )

        if not theories_df.empty:

            if "soha_score" in theories_df.columns:
                horse_soha_theory_map = (
                    theories_df[
                        "soha_score"
                    ].to_dict()
                )

            if "f3_score" in theories_df.columns:
                horse_f3_theory_bonus_map = (
                    theories_df[
                        "f3_score"
                    ].to_dict()
                )

            if "combined_score" in theories_df.columns:
                horse_course_fit_map = (
                    theories_df[
                        "combined_score"
                    ].to_dict()
                )

        # =================================================
        # 着順能力
        # =================================================

        if "着順" in recent_master_data.columns:

            recent_master_data[
                "着順_num"
            ] = pd.to_numeric(
                recent_master_data["着順"],
                errors="coerce"
            )

            avg_finishes = (
                recent_master_data
                .groupby("馬名_clean")[
                    "着順_num"
                ]
                .mean()
                .to_dict()
            )

            for hname, af in avg_finishes.items():

                if not pd.isna(af):

                    horse_ability_map[hname] = max(
                        0.0,
                        (
                            15.0
                            - (af - 1) * 1.2
                        ) * 0.5
                    )

    # =====================================================
    # 現在レースの統合指数
    # =====================================================

    scored_horses = []
    rising_star_flags = []

    for idx, r in res_df.iterrows():

        hname_clean = str(
            r.get(
                "馬名_clean",
                ""
            )
        )

        kyakushitsu = str(
            r.get(
                "脚質",
                "差し"
            )
        )

        tokui_baba = str(
            r.get(
                "得意馬場",
                "指定なし"
            )
        )

        try:
            wakuban = int(
                r.get(
                    "枠番",
                    1
                )
            )
        except Exception:
            wakuban = 1

        ability_bonus = horse_ability_map.get(
            hname_clean,
            2.5
        )

        soha_theory_bonus = (
            horse_soha_theory_map.get(
                hname_clean,
                0.0
            )
        )

        f3_theory_bonus = (
            horse_f3_theory_bonus_map.get(
                hname_clean,
                0.0
            )
        )

        combined_theory_bonus = (
            horse_course_fit_map.get(
                hname_clean,
                0.0
            )
        )

        is_rising = rising_star_map.get(
            hname_clean,
            False
        )

        rising_star_flags.append(
            "🌟 2連勝中"
            if is_rising
            else "-"
        )

        toughness_effect = (
            toughness_val - 1.0
        ) * 4.0

        raw_index = (
            70.0
            + ability_bonus
            + combined_theory_bonus
            + (
                soha_theory_bonus
                * 1.5
            )
            + (
                f3_theory_bonus
                * 1.0
            )
        )

        if is_rising:
            raw_index += 4.0

        if (
            toughness_val >= 1.2
            and kyakushitsu in [
                "逃げ",
                "先行"
            ]
        ):
            raw_index += (
                toughness_effect
                * 1.5
            )

        if straight_length < 320:

            if kyakushitsu in [
                "逃げ",
                "先行"
            ]:
                raw_index += 5.0

            elif kyakushitsu in [
                "差し",
                "追込"
            ]:
                raw_index -= 2.0

        if (
            pace == "S（スロー）"
            and kyakushitsu in [
                "逃げ",
                "先行"
            ]
        ):
            raw_index += 3.0

        elif (
            pace == "H（ハイ）"
            and kyakushitsu in [
                "差し",
                "追込"
            ]
        ):
            raw_index += (
                4.5
                + (
                    f3_theory_bonus
                    * 0.5
                )
            )

        if (
            bias == "内有利"
            and wakuban <= 3
        ):
            raw_index += 3.0

        elif (
            bias == "外有利"
            and wakuban >= 6
        ):
            raw_index += 3.0

        if tokui_baba == condition:
            raw_index += 5.0

        scored_horses.append(
            raw_index
        )

    res_df["統合指数"] = scored_horses

    res_df["ライジングスター"] = (
        rising_star_flags
    )

    res_df = res_df.sort_values(
        by="統合指数",
        ascending=False
    ).reset_index(
        drop=True
    )

    res_df["着順予測"] = range(
        1,
        len(res_df) + 1
    )

    # =====================================================
    # 予測走破タイム
    # =====================================================
    times = []

    for i in range(len(res_df)):

        hname_clean = str(
            res_df.iloc[i].get(
                "馬名_clean",
                ""
            )
        )

        predicted_time = horse_predicted_time_map.get(
            hname_clean,
            np.nan
        )

        if pd.isna(predicted_time):

            predicted_time = target_base_seconds

        times.append(
            round(
                float(predicted_time),
                1
            )
        )

    res_df["予測走破タイム"] = [
        format_time(t)
        for t in times
    ]

    return res_df


# =========================================================
# シミュレーション実行
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)


if st.button(
    "🚀 走破タイム×上がり3F完全統合シミュレーションを実行"
):

    with st.spinner(
        "JRA-VANから各馬の過去走を取得し、"
        "基準走破タイム・基準上がり3Fと照合しています..."
    ):

        # ---------------------------------------------
        # ① JRA-VANから過去走を取得
        # ---------------------------------------------

        master_data = build_master_data_from_jv(
            df_race
        )

        if master_data.empty:

            st.error(
                "JRA-VANから過去走データを取得できませんでした。"
            )

            st.stop()

        # ---------------------------------------------
        # ② 既存シミュレーション
        # ---------------------------------------------

        st.session_state[
            "df_simulated"
        ] = run_integrated_simulation(
            df_race,
            selected_pace,
            selected_bias,
            selected_condition,
            master_data,
            race_category,
            straight_len,
            race_place,
            race_surface,
            course_toughness,
            race_class,
            df_base_master,
            df_f3_master,
        )

        st.session_state[
            "sim_executed"
        ] = True

        st.session_state[
            "master_data_jv"
        ] = master_data

        st.success(
            f"JRA-VAN過去走 {len(master_data)}件を取得して計算しました。"
        )


# =========================================================
# 結果表示
# =========================================================

if (
    st.session_state.get(
        "sim_executed",
        False
    )
    and "df_simulated"
    in st.session_state
):

    st.markdown(
        f"""
        <br>
        <h3>
            🏆 総合指数ランキング
            （{race_place} {race_class} /
            JRA-VAN完全連携版）
        </h3>
        """,
        unsafe_allow_html=True,
    )

    df_simulated = (
        st.session_state[
            "df_simulated"
        ]
    )

    display_columns = [
        c
        for c in [
            "着順予測",
            "馬番",
            "馬名",
            "ライジングスター",
            "オッズ",
            "脚質",
            "得意馬場",
            "統合指数",
            "予測走破タイム",
        ]
        if c in df_simulated.columns
    ]

    display_df = (
        df_simulated[
            display_columns
        ].copy()
    )

    display_df[
        "統合指数"
    ] = display_df[
        "統合指数"
    ].apply(
        lambda x: f"{x:.1f}pt"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # ---------------------------------------------
    # 取得した過去走件数
    # ---------------------------------------------

    if "master_data_jv" in st.session_state:

        master_debug = (
            st.session_state[
                "master_data_jv"
            ]
        )

        st.caption(
            f"📊 JRA-VANから取得した過去走データ: "
            f"{len(master_debug)}件"
        )

else:

    st.info(
        "👆 ペース・バイアス等を設定して、"
        "上のボタンを押すとJRA-VANの過去走を取得して"
        "統合シミュレーションを実行します。"
    )
