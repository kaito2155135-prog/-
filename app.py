import streamlit as st
import pandas as pd
import numpy as np
import os
import json

st.set_page_config(page_title="本格競馬展開シミュレーター（公式基準タイム・距離補正完全版）", layout="wide")

st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>本格競馬展開シミュレーター（公式基準タイム・距離補正完全版）</h2>", unsafe_allow_html=True)

# Excel基準タイムデータの読み込み
@st.cache_data
def load_base_times_excel():
    excel_filename = "JRA全競馬場_芝ダート_クラス別_馬場別基準タイム.xlsx"
    if os.path.exists(excel_filename):
        try:
            df_baba = pd.read_excel(excel_filename, sheet_name="馬場別基準タイム")
            return df_baba
        except Exception:
            return None
    return None

df_base_master = load_base_times_excel()
if df_base_master is not None:
    df_base_master['距離_num'] = pd.to_numeric(df_base_master['距離'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')

# マスターデータの読み込み準備
master_df = None
csv_filename = "keiba_master_data.csv"
if os.path.exists(csv_filename):
   try:
       master_df = pd.read_csv(csv_filename, encoding='utf-8')
   except:
       master_df = pd.read_csv(csv_filename, encoding='cp932')

# 出馬表画像による自動読み込み
st.sidebar.markdown("### 📥 出馬表スクショから読み込む")
uploaded_image = st.sidebar.file_uploader("出馬表の画像をアップロード", type=['png', 'jpg', 'jpeg'])

df_race = None
parsed_race_meta = {}

if uploaded_image is not None:
   st.sidebar.image(uploaded_image, caption="アップロードされた出馬表", use_container_width=True)
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
                       st.error("⚠️ GEMINI_API_KEY が設定されていません。StreamlitのSecretsに設定してください。")
                   else:
                       client = genai.Client(api_key=api_key)
                       image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

                       response = client.models.generate_content(
                           model='gemini-2.5-flash',
                           contents=[
                               image_part,
                               "この画像は競馬の出馬表です。上部に記載されている以下のレース全体情報を必ず読み取ってください。\n"
                               "1. 場所（競馬場名 例:東京、阪神、京都、中山、福島、新潟、中京、札幌、函館、小倉など）\n"
                               "2. 距離（数値のみ 例: 1200）\n"
                               "3. 芝・ダ（「芝」または「ダート」）\n"
                               "4. クラス（例:「新馬」「未勝利」「1勝クラス」「2勝クラス」「3勝クラス」「OP」「G3」「G2」「G1」など）\n"
                               "5. 当日の馬場状態（例:「良」「稍重」「重」「不良」）\n\n"
                               "また、各馬の「枠番」「馬番」「馬名」「オッズ（人気・倍率）」、そして右端にある「脚質」の傾向から「逃げ」「先行」「中団」「差し」「追込」のいずれかに分類してください。\n\n"
                               "出力は必ず以下のJSON形式のみで出力してください。他のテキストやバッククォートは含めないでください。\n"
                               '{\n'
                               '  "race_info": {"場所": "阪神", "距離": 1200, "芝・ダ": "ダート", "クラス": "1勝", "馬場状態": "良"},\n'
                               '  "horses": [\n'
                               '    {"枠番": 1, "馬番": 1, "馬名": "タイセイブロウ", "オッズ": 55.7, "脚質": "差し"}\n'
                               '  ]\n'
                               '}'
                           ]
                       )

                       cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                       parsed_json = json.loads(cleaned_text)

                       meta = parsed_json.get("race_info", {})
                       horses = parsed_json.get("horses", [])

                       df_race = pd.DataFrame(horses)
                       df_race['場所'] = meta.get('場所', '阪神')
                       df_race['距離'] = float(meta.get('距離', 1200))
                       df_race['芝・ダ'] = meta.get('芝・ダ', 'ダート')
                       df_race['クラス'] = meta.get('クラス', '1勝')
                       df_race['当日の馬場'] = meta.get('馬場状態', '良')
                       df_race['得意馬場'] = '指定なし'

                       st.session_state['custom_df_race'] = df_race
                       st.session_state['custom_race_meta'] = meta
                       st.success("出馬表の解析に成功しました！クラスや条件が自動で反映されています。")
               except Exception as e:
                   st.error(f"解析に失敗しました: {e}")

# セッションまたは過去データ選択
if 'custom_df_race' in st.session_state:
   df_race = st.session_state['custom_df_race']
   selected_race = "アップロードされた出馬表レース"
   meta_info = st.session_state.get('custom_race_meta', {})
else:
   if master_df is not None and not master_df.empty:
       master_df['レースID'] = master_df['年'].astype(str) + "年" + master_df['月'].astype(str) + "月" + master_df['日'].astype(str) + " " + master_df['場所'] + " " + master_df['レース番号'].astype(str) + "R " + master_df['略レース名'].astype(str)
       race_list = master_df['レースID'].unique()
       selected_race = st.sidebar.selectbox("🎯 過去のレースを選択", race_list)
       df_race = master_df[master_df['レースID'] == selected_race].copy()
       if '得意馬場' not in df_race.columns:
           df_race['得意馬場'] = '指定なし'
       meta_info = {}
   else:
       df_race = None
       meta_info = {}

if df_race is not None and not df_race.empty:
   st.sidebar.markdown("---")
   st.sidebar.info(f"**{selected_race}**\n\n頭数: {len(df_race)}頭")

   sample_row = df_race.iloc[0]
   race_place = str(sample_row.get('場所', '東京')).strip()
   race_surface = str(sample_row.get('芝・ダ', '芝')).strip()
   race_class = str(sample_row.get('クラス', '1勝')).strip()
   default_baba = str(sample_row.get('当日の馬場', '良')).strip()
   try:
       race_distance = int(float(sample_row.get('距離', 1600)))
   except:
       race_distance = 1600

   straight_lengths_dict = {
       "芝": {
           "新潟": 659.9, "東京": 525.9, "阪神": 473.6, "中京": 412.5,
           "京都": 403.9, "中山": 310.0, "小倉": 293.0, "函館": 262.1,
           "福島": 292.0, "札幌": 266.1
       },
       "ダ": {
           "新潟": 353.9, "東京": 501.6, "阪神": 352.7, "中京": 410.7,
           "京都": 329.1, "中山": 308.0, "小倉": 291.0, "函館": 260.1,
           "福島": 295.7, "札幌": 264.3
       }
   }

   toughness_dict = {
       "中山": 1.15, "札幌": 1.20, "函館": 1.20, "阪神": 1.10,
       "福島": 1.10, "京都": 1.05, "中京": 1.05, "小倉": 1.00,
       "東京": 0.95, "新潟": 0.90
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

   st.markdown(f"""
       <div class="race-info-box">
           <h3 style="margin: 0; color: #f1c40f;">📌 読み込み済みレース条件（公式基準タイム連動）</h3>
           <p style="font-size: 18px; margin: 5px 0 0 0;">
               <b>競馬場:</b> {race_place} (直線: {straight_len}m) &nbsp;|&nbsp;
               <b>馬場種別:</b> {race_surface} &nbsp;|&nbsp;
               <b>距離:</b> {race_distance}m &nbsp;|&nbsp;
               <b>クラス:</b> {race_class} &nbsp;|&nbsp;
               <b>出走頭数:</b> {len(df_race)}頭
           </p>
       </div>
   """, unsafe_allow_html=True)

   st.markdown("### ✍️ 出走出馬データの確認・微調整")
   edit_columns = [c for c in ['枠番', '馬番', '馬名', 'オッズ', '脚質', '得意馬場'] if c in df_race.columns]
  
   for c in ['枠番', '馬番', '馬名', 'オッズ', '脚質', '得意馬場']:
       if c not in df_race.columns:
           if c == '脚質':
               df_race['脚質'] = '差し'
           elif c == '得意馬場':
               df_race['得意馬場'] = '指定なし'
           elif c == 'オッズ':
               df_race['オッズ'] = 10.0
           else:
               df_race[c] = 1

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
           )
       },
       use_container_width=True,
       hide_index=True,
       key="race_data_editor"
   )

   for col in edit_columns:
       df_race[col] = edited_df[col]

   st.markdown("---")
   st.markdown("### ⚙️ コンディション設定")
   col_p1, col_p2, col_p3 = st.columns(3)
   with col_p1:
       selected_pace = st.radio("ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1)
   with col_p2:
       selected_bias = st.radio("トラックバイアス", ["フラット", "内有利", "外有利"], index=0)
   with col_p3:
       baba_default_idx = 0
       if default_baba in ["稍重"]: baba_default_idx = 1
       elif default_baba in ["重"]: baba_default_idx = 2
       elif default_baba in ["不良"]: baba_default_idx = 3
       selected_condition = st.selectbox("当日の馬場状態", ["良", "稍重", "重", "不良"], index=baba_default_idx)

   if race_distance <= 1400:
       race_category = "短距離"
   elif race_distance <= 1800:
       race_category = "マイル"
   elif race_distance <= 2200:
       race_category = "中距離"
   else:
       race_category = "長距離"

   distance_strictness = st.slider("🎯 距離適正フィルターの厳しさ", min_value=0.0, max_value=3.0, value=1.5, step=0.5)

   st.markdown("---")

   def format_time(seconds):
       m = int(seconds // 60)
       s = seconds % 60
       if m > 0:
           return f"{m}分{s:04.1f}秒"
       else:
           return f"{s:.1f}秒"

   def run_monte_carlo_simulation(df_r, pace, bias, condition, master_data, target_cat, strictness, straight_length, place_name, surface_type, toughness_val, target_cls, base_master_df, num_simulations=10000):
       res_df = df_r.copy()
       try:
           target_distance = float(res_df.iloc[0].get('距離', 1600.0))
       except:
           target_distance = 1600.0

       surface = str(surface_type).strip()
       surface_keyword = "ダ" if "ダ" in surface else "芝"
       class_keyword = str(target_cls).strip().replace("クラス", "")

       target_base_seconds = 0.0
       if base_master_df is not None:
           match_target = base_master_df[
               (base_master_df['競馬場'].str.contains(place_name, na=False)) &
               (base_master_df['芝/ダート'] == surface_keyword) &
               (base_master_df['距離_num'] == target_distance) &
               (base_master_df['クラス'].str.contains(class_keyword, na=False))
           ]
           if match_target.empty:
               match_target = base_master_df[
                   (base_master_df['競馬場'].str.contains(place_name, na=False)) &
                   (base_master_df['芝/ダート'] == surface_keyword) &
                   (base_master_df['距離_num'] == target_distance)
               ]

           if not match_target.empty:
               baba_col = condition if condition in ['良', '稍重', '重', '不良'] else '良'
               target_base_seconds = pd.to_numeric(match_target.iloc[0][baba_col], errors='coerce')

       if pd.isna(target_base_seconds) or target_base_seconds <= 0:
           if "ダ" in surface:
               target_base_seconds = (target_distance / 1000.0) * 62.5
           else:
               target_base_seconds = (target_distance / 1000.0) * 59.0

       if 'ダ' in surface:
           f3_weight_factor = max(0.5, min(1.15, straight_length / 450.0))
       else:
           f3_weight_factor = max(0.4, min(1.6, straight_length / 350.0))

       horse_ability_map = {}
       horse_f3_bonus_map = {}
       horse_distance_fit_map = {}
       horse_course_fit_map = {}
       horse_soha_theory_map = {} 

       if master_data is not None and '馬名' in master_data.columns:
           sort_cols = [c for c in ['年', '月', '日'] if c in master_data.columns]
           if sort_cols:
               master_data = master_data.sort_values(by=sort_cols, ascending=False)

           if '芝・ダ' in master_data.columns:
               if "ダ" in surface_keyword:
                   filtered_master = master_data[master_data['芝・ダ'].str.contains("ダ", na=False)].copy()
               else:
                   filtered_master = master_data[~master_data['芝・ダ'].str.contains("ダ", na=False)].copy()
           else:
               filtered_master = master_data.copy()

           recent_master_data = filtered_master.groupby('馬名').head(6).copy()

           class_rank_map = {
               "新馬": 1, "未勝利": 1,
               "1勝": 2, "1勝クラス": 2,
               "2勝": 3, "2勝クラス": 3,
               "3勝": 4, "3勝クラス": 4,
               "OP": 5, "オープン": 5, "リステッド": 5,
               "G3": 6, "G2": 7, "G1": 8
           }

           def calc_soha_theory_score(group):
               derived_times = []
               is_rising_star = False
               if len(group) >= 2:
                   recent_finishes = pd.to_numeric(group.head(2)['着順'], errors='coerce').tolist()
                   if len(recent_finishes) >= 2 and recent_finishes[0] == 1 and recent_finishes[1] == 1:
                       is_rising_star = True

               for _, row in group.iterrows():
                   r_course = str(row.get('場所', row.get('競馬場', place_name))).strip()
                   r_dist = pd.to_numeric(row.get('距離', 0), errors='coerce')
                   r_time = pd.to_numeric(row.get('走破タイム', 0), errors='coerce')
                   r_baba = str(row.get('馬場', row.get('馬場状態', '良'))).strip()
                   r_surface = str(row.get('芝・ダ', surface)).strip()
                   r_class = str(row.get('クラス', 'OP')).strip()
                   r_surface_keyword = "ダ" if "ダ" in r_surface else "芝"
                   r_class_keyword = r_class.replace("クラス", "")

                   if pd.isna(r_dist) or pd.isna(r_time) or r_dist <= 0 or r_time <= 0:
                       continue

                   past_base_time = 0.0
                   if base_master_df is not None:
                       m_match = base_master_df[
                           (base_master_df['競馬場'].str.contains(r_course, na=False)) &
                           (base_master_df['芝/ダート'] == r_surface_keyword) &
                           (base_master_df['距離_num'] == r_dist) &
                           (base_master_df['クラス'].str.contains(r_class_keyword, na=False))
                       ]
                       if m_match.empty:
                           m_match = base_master_df[
                               (base_master_df['競馬場'].str.contains(r_course, na=False)) &
                               (base_master_df['芝/ダート'] == r_surface_keyword) &
                               (base_master_df['距離_num'] == r_dist)
                           ]
                       
                       if not m_match.empty:
                           b_col = r_baba if r_baba in ['良', '稍重', '重', '不良'] else '良'
                           past_base_time = pd.to_numeric(m_match.iloc[0][b_col], errors='coerce')

                   if pd.isna(past_base_time) or past_base_time <= 0:
                       if "ダ" in r_surface_keyword:
                           past_base_time = (r_dist / 1000.0) * 62.5
                       else:
                           past_base_time = (r_dist / 1000.0) * 59.0

                   time_diff = r_time - past_base_time
                   furlong_diff = (target_distance - r_dist) / 200.0
                   distance_penalty_or_bonus = furlong_diff * 1.0

                   past_c_rank = class_rank_map.get(r_class.replace("クラス", ""), 3)
                   target_c_rank = class_rank_map.get(target_cls.replace("クラス", ""), 3)
                   class_diff = target_c_rank - past_c_rank
                   
                   class_level_penalty = 0.0
                   if class_diff > 0:
                       class_level_penalty = class_diff * 0.25 
                   elif class_diff < 0:
                       class_level_penalty = class_diff * 0.20 

                   if is_rising_star:
                       class_level_penalty = 0.0
                       time_diff -= 0.2

                   converted_time = target_base_seconds + time_diff + distance_penalty_or_bonus + class_level_penalty
                   derived_times.append(converted_time)
               
               if not derived_times:
                   return 0.0
               
               median_derived = np.median(derived_times)
               time_advantage = target_base_seconds - median_derived
               return max(-5.0, min(12.0, time_advantage * 3.0))

           soha_scores = recent_master_data.groupby('馬名').apply(calc_soha_theory_score).to_dict()
           for hname, sscore in soha_scores.items():
               horse_soha_theory_map[hname] = sscore

           if '着順' in recent_master_data.columns:
               recent_master_data['着順_num'] = pd.to_numeric(recent_master_data['着順'], errors='coerce')
               avg_finishes = recent_master_data.groupby('馬名')['着順_num'].mean().to_dict()
               for hname, af in avg_finishes.items():
                   if not pd.isna(af):
                       horse_ability_map[hname] = max(0.0, (15.0 - (af - 1) * 1.2) * 0.5)

           if '上がり3Fタイム' in recent_master_data.columns:
               recent_master_data['上がり3F_num'] = pd.to_numeric(recent_master_data['上がり3Fタイム'], errors='coerce')
               avg_f3 = recent_master_data.groupby('馬名')['上がり3F_num'].mean()
               if not avg_f3.empty:
                   mean_all_f3 = avg_f3.mean()
                   f3_diffs = (mean_all_f3 - avg_f3).to_dict()
                   for hname, fd in f3_diffs.items():
                       if not pd.isna(fd):
                           horse_f3_bonus_map[hname] = max(-3.0, min(10.0, fd * 2.5 * f3_weight_factor))

           if '距離' in recent_master_data.columns:
               recent_master_data['距離_num'] = pd.to_numeric(recent_master_data['距離'], errors='coerce')
               def evaluate_distance_fit(group):
                   dists = group['距離_num'].dropna()
                   if len(dists) == 0: return 0.0
                   mean_diff = np.abs(dists - target_distance).mean()
                   if mean_diff <= 300: return 4.0
                   elif mean_diff <= 600: return 1.0
                   else: return -3.0 * strictness

               fit_scores = recent_master_data.groupby('馬名').apply(evaluate_distance_fit).to_dict()
               for hname, fscore in fit_scores.items():
                   horse_distance_fit_map[hname] = fscore

           if '場所' in recent_master_data.columns and '着順' in recent_master_data.columns and '芝・ダ' in recent_master_data.columns:
               def calc_course_fit(group):
                   fit_bonus = 0.0
                   for _, row in group.iterrows():
                       m_place = str(row.get('場所', ''))
                       m_surface = str(row.get('芝・ダ', ''))
                       m_fin = pd.to_numeric(row.get('着順', 99), errors='coerce')
                       if place_name in m_place and surface in m_surface:
                           if m_fin == 1: fit_bonus += 2.0  
                           elif m_fin <= 3: fit_bonus += 1.0  
                   return min(6.0, fit_bonus)

               course_fits = recent_master_data.groupby('馬名').apply(calc_course_fit).to_dict()
               for hname, cfit in course_fits.items():
                   horse_course_fit_map[hname] = cfit

       n_horses = len(res_df)
       win_counts = np.zeros(n_horses)
       place_counts = np.zeros(n_horses)
       show_counts = np.zeros(n_horses)

       for _ in range(num_simulations):
           sim_scores = []
           for idx, r in res_df.iterrows():
               hname = str(r.get('馬名', ''))
               kyakushitsu = str(r.get('脚質', '差し'))
               tokui_baba = str(r.get('得意馬場', '指定なし'))
               wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1

               ability_bonus = horse_ability_map.get(hname, 2.5)
               f3_bonus = horse_f3_bonus_map.get(hname, 0.0)
               dist_fit_bonus = horse_distance_fit_map.get(hname, 0.0)
               course_fit_bonus = horse_course_fit_map.get(hname, 0.0)
               soha_theory_bonus = horse_soha_theory_map.get(hname, 0.0) 

               toughness_effect = (toughness_val - 1.0) * 4.0
               base_score = 70.0 + ability_bonus + soha_theory_bonus + dist_fit_bonus + course_fit_bonus + np.random.normal(0, 3.0)

               if toughness_val >= 1.2 and kyakushitsu in ["逃げ", "先行"]:
                   base_score += toughness_effect * 1.5

               if straight_length <= 320:
                   if kyakushitsu in ["逃げ", "先行"]: base_score += 5.0
                   elif kyakushitsu in ["差し", "追込"]: base_score -= 2.0

               if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
                   base_score += 3.0
               elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
                   base_score += 4.5 + (f3_bonus * 0.9)
               else:
                   base_score += (f3_bonus * 0.6)

               if bias == "内有利" and wakuban <= 3: base_score += 3.0
               elif bias == "外有利" and wakuban >= 6: base_score += 3.0

               if tokui_baba == condition: base_score += 5.0

               sim_scores.append(base_score)

           sorted_indices = np.argsort(sim_scores)[::-1]
           win_counts[sorted_indices[0]] += 1
           if n_horses > 1:
               place_counts[sorted_indices[0]] += 1
               place_counts[sorted_indices[1]] += 1
           if n_horses > 2:
               show_counts[sorted_indices[0]] += 1
               show_counts[sorted_indices[1]] += 1
               show_counts[sorted_indices[2]] += 1

       res_df['勝率(%)'] = (win_counts / num_simulations) * 100
       res_df['連対率(%)'] = (place_counts / num_simulations) * 100
       res_df['複勝率(%)'] = (show_counts / num_simulations) * 100

       sim_scores_mean = []
       for idx, r in res_df.iterrows():
           hname = str(r.get('馬名', ''))
           b_score = 70.0 + horse_ability_map.get(hname, 2.5) + horse_soha_theory_map.get(hname, 0.0) + horse_distance_fit_map.get(hname, 0.0) + horse_course_fit_map.get(hname, 0.0)
           sim_scores_mean.append(b_score)

       res_df['temp_score'] = sim_scores_mean
       res_df = res_df.sort_values(by=['勝率(%)', 'temp_score'], ascending=False).reset_index(drop=True)
       res_df['着順予測'] = range(1, len(res_df) + 1)

       times = []
       for i in range(len(res_df)):
           hname = str(res_df.iloc[i].get('馬名', ''))
           time_mod = -horse_soha_theory_map.get(hname, 0.0) * 0.1
           t = target_base_seconds + (i * 0.25) + time_mod + np.random.uniform(0.0, 0.2)
           times.append(round(max(target_base_seconds - 2.0, t), 1))

       res_df['予測走破タイム'] = [format_time(t) for t in times]
       return res_df

   st.markdown("<br>", unsafe_allow_html=True)
   if st.button("🚀 クラス完全連動・走破タイム理論シミュレーションを実行"):
       with st.spinner(f"{race_place} {race_class}（{race_surface}{race_distance}m）の公式基準タイムと走破タイム理論を反映して10,000回シミュレーションを実行中..."):
           st.session_state['df_simulated'] = run_monte_carlo_simulation(
               df_race, selected_pace, selected_bias, selected_condition, master_df, race_category, 
               distance_strictness, straight_len, race_place, race_surface, course_toughness, race_class, df_base_master, num_simulations=10000
           )
           st.session_state['sim_executed'] = True

   if st.session_state.get('sim_executed', False) and 'df_simulated' in st.session_state:
       st.markdown(f"<br><h3>🏆 10,000回シミュレーション結果（{race_place} {race_class} / 公式基準タイム連動）</h3>", unsafe_allow_html=True)

       df_simulated = st.session_state['df_simulated']
       display_columns = [c for c in ['着順予測', '馬番', '馬名', 'オッズ', '脚質', '得意馬場', '勝率(%)', '連対率(%)', '複勝率(%)', '予測走破タイム'] if c in df_simulated.columns]
       display_df = df_simulated[display_columns].copy()

       display_df['勝率(%)'] = display_df['勝率(%)'].apply(lambda x: f"{x:.1f}%")
       display_df['連対率(%)'] = display_df['連対率(%)'].apply(lambda x: f"{x:.1f}%")
       display_df['複勝率(%)'] = display_df['複勝率(%)'].apply(lambda x: f"{x:.1f}%")

       st.dataframe(display_df, use_container_width=True, hide_index=True)
   else:
       st.info("👆 設定を確認し、上のボタンを押してシミュレーションを実行してください。")

else:
   st.info("👈 サイドバーから出馬表のスクショをアップロードするか、過去データを選択してください。")
