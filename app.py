import streamlit as st
import requests
import pandas as pd

# =========================================================
# 設定
# =========================================================

API_BASE = "http://127.0.0.1:5000"

st.set_page_config(
    page_title="競馬予想システム",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 JRA-VAN 自動取得テスト")

st.caption("JRA-VAN → SQLite → Windows API → Streamlit")


# =========================================================
# JRA-VAN APIからレース一覧を取得
# =========================================================

st.header("📅 レース一覧")

try:
    response = requests.get(
        f"{API_BASE}/races/latest?days=7",
        timeout=10
    )

    response.raise_for_status()

    races = response.json()

except Exception as e:

    st.error("❌ Windows側のJRA-VAN APIに接続できません")

    st.write("確認すること：")
    st.write("1. Windows側で jv_api_server.py が起動しているか")
    st.write("2. http://127.0.0.1:5000/health が開けるか")
    st.write("3. APIの黒い画面を閉じていないか")

    st.code(str(e))

    st.stop()


# =========================================================
# レースがない場合
# =========================================================

if not races:

    st.warning("レースデータがありません。")

    st.stop()


# =========================================================
# レース一覧をDataFrame化
# =========================================================

df_races = pd.DataFrame(races)


# ---------------------------------------------------------
# 表示用ラベル作成
# ---------------------------------------------------------

def make_race_label(row):

    date = str(row.get("date", ""))
    venue = str(row.get("venue", ""))
    race_no = str(row.get("race_no", ""))

    post_time = str(row.get("post_time", ""))

    name = str(row.get("name", "")).strip()

    surface = str(row.get("surface", ""))
    distance = str(row.get("distance", ""))

    horses = str(row.get("horse_count", ""))

    label = (
        f"{date}  "
        f"{venue} "
        f"{race_no}R  "
        f"{post_time}  "
        f"{surface}{distance}m  "
        f"{horses}頭"
    )

    if name:
        label += f"  {name}"

    return label


df_races["label"] = df_races.apply(
    make_race_label,
    axis=1
)


# =========================================================
# レース選択
# =========================================================

st.subheader("レースを選択")

selected_index = st.selectbox(
    "レース",
    range(len(df_races)),
    format_func=lambda i: df_races.iloc[i]["label"]
)


selected_race = df_races.iloc[selected_index]

race_id = selected_race["race_id"]


# =========================================================
# 選択したレース情報
# =========================================================

st.divider()

st.subheader("🏇 選択中のレース")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "開催日",
        str(selected_race.get("date", ""))
    )

with col2:
    st.metric(
        "競馬場",
        str(selected_race.get("venue", ""))
    )

with col3:
    st.metric(
        "レース",
        f'{selected_race.get("race_no", "")}R'
    )

with col4:
    st.metric(
        "距離",
        f'{selected_race.get("surface", "")}{selected_race.get("distance", "")}m'
    )


if str(selected_race.get("name", "")).strip():

    st.write(
        f"**レース名：{str(selected_race.get('name', '')).strip()}**"
    )

st.write(f"Race ID：`{race_id}`")


# =========================================================
# 出馬表取得
# =========================================================

st.divider()

st.subheader("📋 出馬表")


try:

    race_response = requests.get(
        f"{API_BASE}/race/{race_id}",
        timeout=10
    )

    race_response.raise_for_status()

    race_data = race_response.json()

except Exception as e:

    st.error("❌ 出馬表の取得に失敗しました")

    st.code(str(e))

    st.stop()


# =========================================================
# 馬データ
# =========================================================

horses = race_data.get("horses", [])


if not horses:

    st.warning("このレースの出走馬データがありません。")

    st.stop()


df_horses = pd.DataFrame(horses)


# =========================================================
# 表示する列
# =========================================================

display_columns = [
    "枠番",
    "馬番",
    "馬名",
    "騎手",
    "斤量",
    "馬体重",
    "オッズ",
    "人気",
    "脚質"
]


available_columns = [
    col for col in display_columns
    if col in df_horses.columns
]


df_display = df_horses[available_columns].copy()


# =========================================================
# 馬名の表示を整える
# =========================================================

if "馬名" in df_display.columns:

    df_display["馬名"] = (
        df_display["馬名"]
        .astype(str)
        .str.replace("\u3000", "", regex=False)
        .str.strip()
    )


# =========================================================
# 出馬表表示
# =========================================================

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True
)


# =========================================================
# デバッグ情報
# =========================================================

with st.expander("🔧 APIから取得したデータを見る"):

    st.write("レース情報")

    st.json(race_data)


# =========================================================
# 接続成功
# =========================================================

st.success(
    f"✅ JRA-VANデータ取得成功！ "
    f"{len(df_horses)}頭の出馬表を取得しました。"
)
