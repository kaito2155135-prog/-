import json
import os
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st


def normalize_horse_name(name):
  if not isinstance(name, str):
    return ""
  return unicodedata.normalize("NFKC", name).strip()


st.set_page_config(
    page_title="本格競馬展開シミュレーター（ライジングスター対応版）",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
   <style>
   .main { background-color: #0b0b0b; color: #ffffff; }
   h1, h2, h3 { color: #f1c40f !important; font-family: sans-serif; }
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
    "<h2 style='text-align: center; color: #f1c40f;'>本格競馬展開シミュレーター（ライジングスター対応版）</h2>",
    unsafe_allow_html=True,
)


@st.cache_data
def load_base_data_excel():
  excel_filename = "JRA_基準上がり3F_実データ集計_修正版.xlsx"
  if os.path.exists(excel_filename):
    try:
      xls = pd.ExcelFile(excel_filename)
      df_baba = (
          pd.read_excel(excel_filename, sheet_name="馬場別基準タイム")
          if "馬場別基準タイム" in xls.sheet_names
          else None
      )
      df_f3 = (
          pd.read_excel(excel_filename, sheet_name="基準上がり3F")
          if "基準上がり3F" in xls.sheet_names
          else None
      )
      return df_baba, df_f3
    except Exception:
      return None, None
  return None, None


df_base_master, df_f3_master = load_base_data_excel()

if df_base_master is not None and "距離" in df_base_master.columns:
  df_base_master["距離_num"] = pd.to_numeric(
      df_base_master["距離"].astype(str).str.extract(r"(\d+)")[0],
      errors="coerce",
  )

if df_f3_master is not None and "距離" in df_f3_master.columns:
  df_f3_master["距離_num"] = pd.to_numeric(
      df_f3_master["距離"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
  )

master_df = None
csv_filename = "keiba_master_data.csv"
if os.path.exists(csv_filename):
  try:
    master_df = pd.read_csv(csv_filename, encoding="utf-8")
  except:
    master_df = pd.read_csv(csv_filename, encoding="cp932")

if master_df is not None:
  if "馬名" in master_df.columns:
    master_df["馬名_clean"] = master_df["馬名"].apply(normalize_horse_name)
  if "場所" in master_df.columns:
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
    master_df = master_df[
        master_df["場所"].astype(str).str.contains("|".join(jra_places), na=False)
    ].copy()

master_data = master_df

st.sidebar.markdown("### 📥 出馬表スクショから読み込む")
uploaded_image = st.sidebar.file_uploader(
    "出馬表の画像をアップロード", type=["png", "jpg", "jpeg"]
)

df_race = None
parsed_race_meta = {}

if uploaded_image is not None:
  st.sidebar.image(
      uploaded_image, caption="アップロードされた出馬表", use_container_width=True
  )
  if st.sidebar.button("✨ 画像からAI解析を実行"):
    with st.spinner("AIがレース情報や出馬表を解析しています..."):
      try:
        from google import genai
        from google.genai import types

        image_bytes = uploaded_image.getvalue()
        mime_type = uploaded_image.type if uploaded_image.type else "image/jpeg"

        api_key = None
        try:
          api_key = st.secrets["GEMINI_API_KEY"]
        except:
          api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
          st.error(
              "⚠️ GEMINI_API_KEY"
              " が設定されていません。StreamlitのSecretsに設定してください。"
          )
        else:
          client = genai.Client(api_key=api_key)
          image_part = types.Part.from_bytes(
              data=image_bytes, mime_type=mime_type
          )

          response = client.models.generate_content(
              model="gemini-3.6-flash",
              contents=[
                  image_part,
                  (
                      "この画像は競馬の出馬表です。上部に記載されている以下のレース全体情報を必ず読み取ってください。\n1."
                      " 場所（競馬場名 例:東京、阪神、京都、中山、福島、新潟、中京、札幌、函館、小倉など）\n2."
                      " 距離（数値のみ 例: 1200）\n3. 芝・ダ（「芝」または「ダート」）\n4."
                      " クラス（例:「新馬」「未勝利」「1勝クラス」「2勝クラス」「3勝クラス」「OP」「G3」「G2」「G1」など）\n5."
                      " 当日の馬場状態（例:「良」「稍重」「重」「不良」）\n\nまた、各馬の「枠番」「馬番」「馬名」「オッズ（人気・倍率）」、そして右端にある「脚質」の傾向から「逃げ」「先行」「中団」「差し」「追込」のいずれかに分類してください。\n\n"
                      "【重要：馬名抽出のルール】\n"
                      "- 馬名は純粋な馬名のみを抽出してください（性齢（牡3、牝4など）、斤量、騎手名、調教師名、外国産馬記号などは含めないでください）。\n"
                      "- 前後の余分なスペースや特殊記号、カッコ書きは完全に排除してください。\n\n"
                      "出力は必ず以下のJSON形式のみで出力してください。他のテキストやバッククォートは含めないでください。\n{\n"
                      '  "race_info": {"場所": "阪神", "距離": 1200, '
                      '"芝・ダ": "ダート", "クラス": "1勝", "馬場状態": "良"},\n'
                      '  "horses": [\n'
                      '    {"枠番": 1, "馬番": 1, "馬名": "タイセイブロウ", '
                      '"オッズ": 55.7, "脚質": "差し"}\n'
                      "  ]\n"
                      "}"
                  ),
              ],
          )

          cleaned_text = (
              response.text.replace("```json", "").replace("```", "").strip()
          )
          parsed_json = json.loads(cleaned_text)

          meta = parsed_json.get("race_info", {})
          horses = parsed_json.get("horses", [])

          import re

          for h in horses:
            if "馬名" in h:
              h_name = str(h["馬名"])
              h_name = re.sub(r"[牡牝せんセ]\s*\d+", "", h_name)
              h_name = re.sub(r"[\(\[（［].*?[\)\]））]", "", h_name)
              h_name = normalize_horse_name(h_name)
              h["馬名"] = h_name

          df_race = pd.DataFrame(horses)
          df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)
          df_race["場所"] = meta.get("場所", "阪神")
          df_race["距離"] = float(meta.get("距離", 1200))
          df_race["芝・ダ"] = meta.get("芝・ダ", "ダート")
          df_race["クラス"] = meta.get("クラス", "1勝")
          df_race["当日の馬場"] = meta.get("馬場状態", "良")
          df_race["得意馬場"] = "指定なし"

          st.session_state["custom_df_race"] = df_race
          st.session_state["custom_race_meta"] = meta
          st.success("出馬表の解析に成功しました！")
      except Exception as e:
        st.error(f"解析に失敗しました: {e}")

if "custom_df_race" in st.session_state:
  df_race = st.session_state["custom_df_race"]
  if "馬名_clean" not in df_race.columns and "馬名" in df_race.columns:
    df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)
  selected_race = "アップロードされた出馬表レース"
  meta_info = st.session_state.get("custom_race_meta", {})
else:
  if master_data is not None and not master_data.empty:
    master_data["レースID"] = (
        master_data["年"].astype(str)
        + "年"
        + master_data["月"].astype(str)
        + "月"
        + master_data["日"].astype(str)
        + "日 "
        + master_data["場所"]
        + " "
        + master_data["レース番号"].astype(str)
        + "R "
        + master_data["略レース名"].astype(str)
    )
    race_list = master_data["レースID"].unique()
    selected_race = st.sidebar.selectbox("🎯 過去のレースを選択", race_list)
    df_race = master_data[master_data["レースID"] == selected_race].copy()
    if "馬名_clean" not in df_race.columns and "馬名" in df_race.columns:
      df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)
    if "得意馬場" not in df_race.columns:
      df_race["得意馬場"] = "指定なし"
    meta_info = {}
  else:
    df_race = None
    meta_info = {}

if df_race is not None and not df_race.empty:
  st.sidebar.markdown("---")
  st.sidebar.info(f"**{selected_race}**\n\n頭数: {len(df_race)}頭")

  sample_row = df_race.iloc[0]
  race_place = str(sample_row.get("場所", "東京")).strip()
  race_surface = str(sample_row.get("芝・ダ", "芝")).strip()
  race_class = str(
      sample_row.get(
          "クラス", sample_row.get("略レース名", "1勝クラス")
      )
  ).strip()
  default_baba = str(sample_row.get("馬場状態", "良")).strip()
  try:
    race_distance = int(float(sample_row.get("距離", 1600)))
  except:
    race_distance = 1600

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

  st.markdown(
      f"""
       <div class="race-info-box">
           <h3 style="margin: 0; color: #f1c40f;">📌 読み込み済みレース条件（ライジングスター対応版）</h3>
           <p style="font-size: 18px; margin: 5px 0 0 0;">
               <b>競馬場:</b> {race_place} (直線: {straight_len}m) &nbsp;|&nbsp;
               <b>馬場種別:</b> {race_surface} &nbsp;|&nbsp;
               <b>距離:</b> {race_distance}m &nbsp;|&nbsp;
               <b>クラス:</b> {race_class} &nbsp;|&nbsp;
               <b>出走頭数:</b> {len(df_race)}頭
           </p>
       </div>
   """,
      unsafe_allow_html=True,
  )

  edit_columns = [
      c
      for c in ["枠番", "馬番", "馬名", "オッズ", "脚質", "得意馬場"]
      if c in df_race.columns
  ]
  for c in ["枠番", "馬番", "馬名", "オッズ", "脚質", "得意馬場"]:
    if c not in df_race.columns:
      if c == "脚質":
        df_race["脚質"] = "差し"
      elif c == "得意馬場":
        df_race["得意馬場"] = "指定なし"
      elif c == "オッズ":
        df_race["オッズ"] = 10.0
      else:
        df_race[c] = 1

  if "馬名_clean" not in df_race.columns:
    df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)

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
              options=["指定なし", "良", "稍重", "重", "不良"],
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
  df_race["馬名_clean"] = df_race["馬名"].apply(normalize_horse_name)

  st.markdown("---")
  col_p1, col_p2, col_p3 = st.columns(3)
  with col_p1:
    selected_pace = st.radio(
        "ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1
    )
  with col_p2:
    selected_bias = st.radio(
        "トラックバイアス", ["フラット", "内有利", "外有利"], index=0
    )
  with col_p3:
    baba_default_idx = 0
    if default_baba in ["稍重"]:
      baba_default_idx = 1
    elif default_baba in ["重"]:
      baba_default_idx = 2
    elif default_baba in ["不良"]:
      baba_default_idx = 3
    selected_condition = st.selectbox(
        "当日の馬場状態", ["良", "稍重", "重", "不良"], index=baba_default_idx
    )

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
    else:
      return f"{s:.1f}秒"


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
      target_distance = float(res_df.iloc[0].get("距離", 1600.0))
    except:
      target_distance = 1600.0

    surface = str(surface_type).strip()
    surface_keyword = "ダート" if "ダ" in surface else "芝"
    class_keyword = str(target_cls).strip().replace("クラス", "")

    target_base_seconds = 0.0
    if base_master_df is not None:
      match_target = base_master_df[
          (base_master_df["競馬場"].str.contains(place_name, na=False))
          & (base_master_df["芝/ダート"] == ("ダ" if "ダ" in surface else "芝"))
          & (base_master_df["距離_num"] == target_distance)
          & (base_master_df["クラス"].str.contains(class_keyword, na=False))
      ]
      if match_target.empty:
        match_target = base_master_df[
            (base_master_df["競馬場"].str.contains(place_name, na=False))
            & (base_master_df["芝/ダート"] == ("ダ" if "ダ" in surface else "芝"))
            & (base_master_df["距離_num"] == target_distance)
        ]
      if not match_target.empty:
        baba_col = (
            condition if condition in ["良", "稍重", "重", "不良"] else "良"
        )
        target_base_seconds = pd.to_numeric(
            match_target.iloc[0][baba_col], errors="coerce"
        )

    if pd.isna(target_base_seconds) or target_base_seconds <= 0:
      if "ダ" in surface:
        target_base_seconds = (target_distance / 1000.0) * 62.5
      else:
        target_base_seconds = (target_distance / 1000.0) * 59.0

    target_base_f3 = 0.0
    if f3_master_df is not None:
      match_f3 = f3_master_df[
          (f3_master_df["競馬場"].str.contains(place_name, na=False))
          & (f3_master_df["芝/ダート"] == surface_keyword)
          & (f3_master_df["距離_num"] == target_distance)
          & (f3_master_df["クラス"].str.contains(class_keyword, na=False))
      ]
      if match_f3.empty:
        match_f3 = f3_master_df[
            (f3_master_df["競馬場"].str.contains(place_name, na=False))
            & (f3_master_df["芝/ダート"] == surface_keyword)
            & (f3_master_df["距離_num"] == target_distance)
        ]
      if not match_f3.empty:
        baba_col = (
            condition if condition in ["良", "稍重", "重", "不良"] else "良"
        )
        if baba_col in match_f3.columns:
          target_base_f3 = pd.to_numeric(
              match_f3.iloc[0][baba_col], errors="coerce"
          )

    if pd.isna(target_base_f3) or target_base_f3 <= 0:
      target_base_f3 = 34.5 if "芝" in surface else 37.0

    if "ダ" in surface:
      f3_weight_factor = max(0.5, min(1.15, straight_length / 450.0))
    else:
      f3_weight_factor = max(0.4, min(1.6, straight_length / 350.0))

    horse_ability_map = {}
    horse_f3_theory_bonus_map = {}
    horse_course_fit_map = {}
    horse_soha_theory_map = {}
    rising_star_map = {}

    if master_data is not None and "馬名_clean" in master_data.columns:
      sort_cols = [c for c in ["年", "月", "日"] if c in master_data.columns]
      if sort_cols:
        master_data = master_data.sort_values(by=sort_cols, ascending=False)

      if "芝・ダ" in master_data.columns:
        if "ダ" in surface_keyword:
          filtered_master = master_data[
              master_data["芝・ダ"].str.contains("ダ", na=False)
          ].copy()
        else:
          filtered_master = master_data[
              ~master_data["芝・ダ"].str.contains("ダ", na=False)
          ].copy()
      else:
        filtered_master = master_data.copy()

      recent_master_data = filtered_master.groupby("馬名_clean").head(6).copy()

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

      for hname, group in filtered_master.groupby("馬名_clean"):
        if "着順" in group.columns and len(group) >= 2:
          top2 = group.head(2)
          finishes = pd.to_numeric(top2["着順"], errors="coerce").tolist()
          if len(finishes) == 2 and finishes[0] == 1 and finishes[1] == 1:
            rising_star_map[hname] = True
          else:
            rising_star_map[hname] = False
        else:
          rising_star_map[hname] = False

      def calc_theories_score(group):
        if "馬名_clean" in group.columns and not group["馬名_clean"].empty:
          h_name = str(group["馬名_clean"].iloc[0])
        elif "馬名" in group.columns and not group["馬名"].empty:
          h_name = normalize_horse_name(str(group["馬名"].iloc[0]))
        else:
          h_name = str(group.name) if group.name else "不明"

        is_rising = rising_star_map.get(h_name, False)

        derived_times = []
        derived_f3s = []

        for _, row in group.iterrows():
          r_course = str(
              row.get("場所", row.get("競馬場", place_name))
          ).strip()
          r_dist = pd.to_numeric(row.get("距離", 0), errors="coerce")
          r_time = pd.to_numeric(row.get("走破タイム", 0), errors="coerce")
          r_f3_time = pd.to_numeric(
              row.get("上がり3Fタイム", 0), errors="coerce"
          )
          r_baba = str(
              row.get("馬場状態", row.get("馬場", "良"))
          ).strip()
          r_surface = str(row.get("芝・ダ", surface)).strip()
          r_class = str(
              row.get("略レース名", row.get("クラス", "OP"))
          ).strip()
          r_surface_keyword = "ダート" if "ダ" in r_surface else "芝"
          r_surface_short = "ダ" if "ダ" in r_surface else "芝"

          if pd.isna(r_dist) or r_dist <= 0:
            continue

          # 【正しい補正係数】小倉は1.10（遅くして割引）、函館・札幌は1.0（速くして救済）
          past_course_multiplier = 1.0
          if "小倉" in r_course:
            past_course_multiplier = 1.10
          elif "函館" in r_course or "札幌" in r_course:
            past_course_multiplier = 1.0

          past_c_rank = class_rank_map.get(r_class.replace("クラス", ""), 1)
          target_c_rank = class_rank_map.get(
              target_cls.replace("クラス", ""), 2
          )
          class_diff = target_c_rank - past_c_rank

          if not pd.isna(r_time) and r_time > 0:
            adjusted_r_time = r_time * past_course_multiplier

            past_base_time = 0.0
            if base_master_df is not None:
              m_match = base_master_df[
                  (base_master_df["競馬場"].str.contains(r_course, na=False))
                  & (base_master_df["芝/ダート"] == r_surface_short)
                  & (base_master_df["距離_num"] == r_dist)
                  & (base_master_df["クラス"].str.contains(class_keyword, na=False))
              ]
              if m_match.empty:
                m_match = base_master_df[
                    (base_master_df["競馬場"].str.contains(r_course, na=False))
                    & (base_master_df["芝/ダート"] == r_surface_short)
                    & (base_master_df["距離_num"] == r_dist)
                ]
              if not m_match.empty:
                b_col = (
                    r_baba if r_baba in ["良", "稍重", "重", "不良"] else "良"
                )
                past_base_time = pd.to_numeric(
                    m_match.iloc[0][b_col], errors="coerce"
                )

            if pd.isna(past_base_time) or past_base_time <= 0:
              past_base_time = (r_dist / 1000.0) * (
                  62.5 if r_surface_short == "ダ" else 59.0
              )

            time_diff = past_base_time - adjusted_r_time
            furlong_diff = (target_distance - r_dist) / 200.0

            if target_distance <= 1400:
              furlong_weight = 1.15
            elif target_distance <= 1800:
              furlong_weight = 1.00
            elif target_distance <= 2200:
              furlong_weight = 0.85
            else:
              furlong_weight = 0.70

            distance_penalty_or_bonus = furlong_diff * furlong_weight

            if is_rising:
              class_level_penalty = 0.0
            else:
              class_level_penalty = (
                  (class_diff * 0.20) if class_diff > 0 else (class_diff * 0.15)
              )

            converted_time = (
                target_base_seconds
                - time_diff
                + distance_penalty_or_bonus
                + class_level_penalty
            )

            if is_rising:
              converted_time -= 0.2

            derived_times.append(converted_time)

          if not pd.isna(r_f3_time) and r_f3_time > 0:
            past_base_f3 = 0.0
            if f3_master_df is not None:
              f3_match = f3_master_df[
                  (f3_master_df["競馬場"].str.contains(r_course, na=False))
                  & (f3_master_df["芝/ダート"] == surface_keyword)
                  & (f3_master_df["距離_num"] == r_dist)
                  & (f3_master_df["クラス"].str.contains(class_keyword, na=False))
              ]
              if f3_match.empty:
                f3_match = f3_master_df[
                    (f3_match["競馬場"].str.contains(r_course, na=False))
                    & (f3_match["芝/ダート"] == surface_keyword)
                    & (f3_match["距離_num"] == r_dist)
                ]
              if not f3_match.empty:
                b_col = (
                    r_baba if r_baba in ["良", "稍重", "重", "不良"] else "良"
                )
                if b_col in f3_match.columns:
                  past_base_f3 = pd.to_numeric(
                      f3_match.iloc[0][b_col], errors="coerce"
                  )

            if pd.isna(past_base_f3) or past_base_f3 <= 0:
              past_base_f3 = 34.5 if r_surface_keyword == "芝" else 37.0

            f3_diff = r_f3_time - past_base_f3
            f3_class_adjustment = 0.0
            if not is_rising:
              if r_surface_keyword == "ダート":
                if class_diff > 0:
                  f3_class_adjustment = class_diff * 0.15
                elif class_diff < 0:
                  f3_class_adjustment = class_diff * 0.1

            converted_f3 = target_base_f3 + f3_diff + f3_class_adjustment
            derived_f3s.append(converted_f3)

        soha_score = 0.0
        if derived_times:
          sorted_times = sorted(derived_times)
          # 【変更】安定感重視のため「中央値（メディアン）」を採用
          val_to_use = float(np.median(sorted_times))

          time_advantage = target_base_seconds - val_to_use
          soha_score = max(-5.0, min(12.0, time_advantage * 3.0))

        f3_score = 0.0
        if derived_f3s:
          sorted_f3s = sorted(derived_f3s)
          # 【変更】上がり3Fも安定感重視で「中央値（メディアン）」を採用
          f3_val_to_use = float(np.median(sorted_f3s))

          f3_advantage = target_base_f3 - f3_val_to_use
          f3_score = max(
              -3.0, min(10.0, f3_advantage * 2.5 * f3_weight_factor)
          )

        if straight_length < 320:
          combined_score = (soha_score * 0.75) + (f3_score * 0.25)
        elif 320 <= straight_length < 400:
          combined_score = (soha_score * 0.7) + (f3_score * 0.3)
        else:
          combined_score = (soha_score * 0.6) + (f3_score * 0.4)

        return pd.Series({
            "soha_score": soha_score,
            "f3_score": f3_score,
            "combined_score": combined_score,
            "is_rising_star": is_rising,
        })

      theories_df = recent_master_data.groupby("馬名_clean").apply(
          calc_theories_score
      )
      if not theories_df.empty:
        if "soha_score" in theories_df.columns:
          horse_soha_theory_map = theories_df["soha_score"].to_dict()
        if "f3_score" in theories_df.columns:
          horse_f3_theory_bonus_map = theories_df["f3_score"].to_dict()
        if "combined_score" in theories_df.columns:
          horse_course_fit_map = theories_df["combined_score"].to_dict()

      if "着順" in recent_master_data.columns:
        recent_master_data["着順_num"] = pd.to_numeric(
            recent_master_data["着順"], errors="coerce"
        )
        avg_finishes = (
            recent_master_data.groupby("馬名_clean")["着順_num"]
            .mean()
            .to_dict()
        )
        for hname, af in avg_finishes.items():
          if not pd.isna(af):
            horse_ability_map[hname] = max(0.0, (15.0 - (af - 1) * 1.2) * 0.5)

    scored_horses = []
    rising_star_flags = []
    for idx, r in res_df.iterrows():
      hname_clean = str(r.get("馬名_clean", ""))
      kyakushitsu = str(r.get("脚質", "差し"))
      tokui_baba = str(r.get("得意馬場", "指定なし"))
      wakuban = int(r.get("枠番", 1)) if pd.notnull(r.get("枠番", 1)) else 1

      ability_bonus = horse_ability_map.get(hname_clean, 2.5)
      soha_theory_bonus = horse_soha_theory_map.get(hname_clean, 0.0)
      f3_theory_bonus = horse_f3_theory_bonus_map.get(hname_clean, 0.0)
      combined_theory_bonus = horse_course_fit_map.get(hname_clean, 0.0)
      is_rising = rising_star_map.get(hname_clean, False)
      rising_star_flags.append("🌟 2連勝中" if is_rising else "-")

      toughness_effect = (toughness_val - 1.0) * 4.0

      raw_index = (
          70.0
          + ability_bonus
          + combined_theory_bonus
          + (soha_theory_bonus * 1.5)
          + (f3_theory_bonus * 1.0)
      )

      if is_rising:
        raw_index += 4.0

      if toughness_val >= 1.2 and kyakushitsu in ["逃げ", "先行"]:
        raw_index += toughness_effect * 1.5

      if straight_length < 320:
        if kyakushitsu in ["逃げ", "先行"]:
          raw_index += 5.0
        elif kyakushitsu in ["差し", "追込"]:
          raw_index -= 2.0

      if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
        raw_index += 3.0
      elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
        raw_index += 4.5 + (f3_theory_bonus * 0.5)

      if bias == "内有利" and wakuban <= 3:
        raw_index += 3.0
      elif bias == "外有利" and wakuban >= 6:
        raw_index += 3.0

      if tokui_baba == condition:
        raw_index += 5.0

      scored_horses.append(raw_index)

    res_df["統合指数"] = scored_horses
    res_df["ライジングスター"] = rising_star_flags
    res_df = res_df.sort_values(by="統合指数", ascending=False).reset_index(
        drop=True
    )
    res_df["着順予測"] = range(1, len(res_df) + 1)

    times = []
    for i in range(len(res_df)):
      hname_clean = str(res_df.iloc[i].get("馬名_clean", ""))
      time_mod = -horse_soha_theory_map.get(hname_clean, 0.0) * 0.1
      t = target_base_seconds - 1.5 + (i * 0.3) + time_mod
      times.append(round(max(target_base_seconds - 3.0, t), 1))

    res_df["予測走破タイム"] = [format_time(t) for t in times]
    return res_df

  st.markdown("<br>", unsafe_allow_html=True)
  if st.button("🚀 走破タイム×上がり3F完全統合シミュレーションを実行"):
    with st.spinner(
        f"{race_place} {race_class}（{race_surface}{race_distance}m）の基準タイム・基準上がり3Fデータを統合して計算中..."
    ):
      st.session_state["df_simulated"] = run_integrated_simulation(
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
      st.session_state["sim_executed"] = True

  if st.session_state.get("sim_executed", False) and "df_simulated" in st.session_state:
    st.markdown(
        f"<br><h3>🏆 総合指数ランキング（{race_place} {race_class} /"
        " ライジングスター対応版）</h3>",
        unsafe_allow_html=True,
    )

    df_simulated = st.session_state["df_simulated"]
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
    display_df = df_simulated[display_columns].copy()

    display_df["統合指数"] = display_df["統合指数"].apply(lambda x: f"{x:.1f}pt")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
  else:
    st.info(
        "👆 設定を確認し、上のボタンを押して統合シミュレーションを実行してください。"
    )

else:
  st.info(
      "👈 サイドバーから出馬表のスクショをアップロードするか、過去データを選択してください。"
  )
