import streamlit as st
import requests
import pandas as pd

# =========================================================
# 設定
# =========================================================

API_BASE = "https://symantec-clark-albany-ski.trycloudflare.com"

st.set_page_config(
    page_title="JRA-VAN 自動取得テスト",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 JRA-VAN 自動取得テスト")


# =========================================================
# API接続確認
# =========================================================

try:

    health = requests.get(
        f"{API_BASE}/health",
        timeout=15
    )

    health.raise_for_status()

    health_data = health.json()

except Exception as e:

    st.error("❌ JRA-VAN APIに接続できません")

    st.code(str(e))

    st.stop()


if health_data.get("ok") is not True:

    st.error(
        "❌ APIは応答しましたが、"
        "SQLiteに接続できていません"
    )

    st.json(health_data)

    st.stop()


st.success("✅ JRA-VAN API接続成功")


# =========================================================
# レース一覧取得
# =========================================================

try:

    response = requests.get(
        f"{API_BASE}/races/latest?days=7",
        timeout=15
    )

    response.raise_for_status()

    races_response = response.json()

except Exception as e:

    st.error(
        "❌ レース一覧の取得に失敗しました"
    )

    st.code(str(e))

    st.stop()


# =========================================================
# APIの返り値から「races」だけ取り出す
# =========================================================

if isinstance(races_response, dict):

    race_list = races_response.get(
        "races",
        []
    )

else:

    race_list = races_response


if not race_list:

    st.warning(
        "レースデータがありません"
    )

    st.stop()


# =========================================================
# レース一覧をDataFrame化
# =========================================================

df_races = pd.DataFrame(
    race_list
)


# =========================================================
# APIから何が来ているか確認
# =========================================================

with st.expander(
    "🔧 APIから取得したレースデータを確認"
):

    st.write(
        "取得件数：",
        len(df_races)
    )

    st.write(
        "取得した項目："
    )

    st.write(
        list(df_races.columns)
    )

    st.dataframe(
        df_races,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# race_id確認
# =========================================================

if "race_id" not in df_races.columns:

    st.error(
        "❌ APIから race_id が取得できていません"
    )

    st.write(
        "現在取得している項目："
    )

    st.write(
        list(df_races.columns)
    )

    st.stop()


# =========================================================
# 表示用レース名
# =========================================================

def make_race_label(row):

    date = str(
        row.get(
            "date",
            ""
        )
    )

    venue = str(
        row.get(
            "venue",
            ""
        )
    )

    race_no = str(
        row.get(
            "race_no",
            ""
        )
    )

    post_time = str(
        row.get(
            "post_time",
            ""
        )
    )

    surface = str(
        row.get(
            "surface",
            ""
        )
    )

    distance = str(
        row.get(
            "distance",
            ""
        )
    )

    horse_count = str(
        row.get(
            "horse_count",
            ""
        )
    )

    name = str(
        row.get(
            "name",
            ""
        )
    ).strip()

    label = (
        f"{date} "
        f"{venue} "
        f"{race_no}R "
        f"{post_time} "
        f"{surface}{distance}m "
        f"{horse_count}頭"
    )

    if name:

        label += (
            f"  {name}"
        )

    return label


df_races["label"] = df_races.apply(
    make_race_label,
    axis=1
)


# =========================================================
# レース選択
# =========================================================

st.divider()

st.subheader(
    "📅 レースを選択"
)


selected_index = st.selectbox(

    "レース",

    range(
        len(df_races)
    ),

    format_func=lambda i:
        df_races.iloc[i]["label"]

)


# =========================================================
# 選択したレース
# =========================================================

selected_race = df_races.iloc[
    selected_index
]


# =========================================================
# Race ID取得
# =========================================================

race_id = str(
    selected_race["race_id"]
)


# =========================================================
# レース情報表示
# =========================================================

st.divider()

st.subheader(
    "🏇 選択中のレース"
)


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(

        "開催日",

        str(
            selected_race.get(
                "date",
                ""
            )
        )

    )


with col2:

    st.metric(

        "競馬場",

        str(
            selected_race.get(
                "venue",
                ""
            )
        )

    )


with col3:

    st.metric(

        "レース",

        f'{selected_race.get("race_no", "")}R'

    )


with col4:

    st.metric(

        "距離",

        f'{selected_race.get("surface", "")}'
        f'{selected_race.get("distance", "")}m'

    )


race_name = str(

    selected_race.get(
        "name",
        ""
    )

).strip()


if race_name:

    st.write(
        f"**レース名：{race_name}**"
    )


st.write(
    f"Race ID：`{race_id}`"
)


# =========================================================
# 出馬表取得
# =========================================================

st.divider()

st.subheader(
    "📋 出馬表"
)


try:

    race_response = requests.get(

        f"{API_BASE}/race/{race_id}",

        timeout=15

    )

    race_response.raise_for_status()

    race_data = race_response.json()


except Exception as e:

    st.error(
        "❌ 出馬表の取得に失敗しました"
    )

    st.code(
        str(e)
    )

    st.stop()


# =========================================================
# 馬データ
# =========================================================

horses = race_data.get(
    "horses",
    []
)


if not horses:

    st.warning(
        "このレースの出走馬データがありません"
    )

    st.stop()


df_horses = pd.DataFrame(
    horses
)


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

    col

    for col in display_columns

    if col in df_horses.columns

]


df_display = df_horses[
    available_columns
].copy()


# =========================================================
# 馬名の表示調整
# =========================================================

if "馬名" in df_display.columns:

    df_display["馬名"] = (

        df_display["馬名"]

        .astype(str)

        .str.replace(
            "\u3000",
            "",
            regex=False
        )

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
# 成功
# =========================================================

st.success(

    f"✅ JRA-VANから "
    f"{len(df_horses)}頭の出馬表を取得しました！"

)


# =========================================================
# 詳細データ
# =========================================================

with st.expander(
    "🔧 APIの詳細データ"
):

    st.json(
        race_data
    )
