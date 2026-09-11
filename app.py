import streamlit as st
import pandas as pd
import numpy as np
import os
import json

st.set_page_config(page_title="本格競馬展開シミュレーター", layout="wide")

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

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>本格競馬展開シミュレーター（コース別・末脚特性連動版）</h2>", unsafe_allow_html=True)

# 1. マスターデータの読み込み準備
master_df = None
csv_filename = "keiba_master_data.csv"
if os.path.exists(csv_filename):
   try:
       master_df = pd.read_csv(csv_filename, encoding='utf-8')
   except:
       master_df = pd.read_csv(csv_filename, encoding='cp932')

# 2. 画像アップロードによる出馬表自動読み込み
st.sidebar.markdown("### 📥 出馬表スクショから読み込む")
uploaded_image = st.sidebar.file_uploader("出馬表の画像をアップロード", type=['png', 'jpg', 'jpeg'])

df_race = None

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
                           model='gemini-3.6-flash',
                           contents=[
                               image_part,
                               "この画像は競馬の出馬表です。上部に記載されている「場所（競馬場名 例:東京、阪神、福島など）」「距離（例:1600m）」「芝・ダ（芝かダートか）」を読み取ってください。\n"
                               "また、各馬の「枠番」「馬番」「馬名」「オッズ（人気・倍率）」、そして右端にある「脚質」の傾向（例: [・先..]なら先行、[..差追]なら差し・追込などから「逃げ」「先行」「中団」「差し」「追込」のいずれかに分類）を読み取ってください。\n"
                               "結果は必ず以下のJSON配列の形式のみで正確に出力してください。他の余分なテキストやマークダウンのバッククォートは含めないでください。\n"
                               '[{"場所": "東京", "距離": 2400, "芝・ダ": "芝", "枠番": 1, "馬番": 1, "馬名": "ラフターラインズ", "オッズ": 3.2, "脚質": "追込"}, ...]'
                           ]
                       )

                       cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                       parsed_data = json.loads(cleaned_text)

                       df_race = pd.DataFrame(parsed_data)
                      
                       if '場所' not in df_race.columns:
                           df_race['場所'] = '東京'
                       if '距離' not in df_race.columns:
                           df_race['距離'] = 2400.0 
                       if '芝・ダ' not in df_race.columns:
                           df_race['芝・ダ'] = '芝'
                       if '脚質' not in df_race.columns:
                           df_race['脚質'] = '追込'
                       if 'オッズ' not in df_race.columns:
                           df_race['オッズ'] = 5.0
                      
                       df_race['得意馬場'] = '指定なし'

                       st.session_state['custom_df_race'] = df_race
                       st.success("出馬表の読み込みに成功しました！下部で各馬の脚質や得意馬場を微調整できます。")
               except Exception as e:
                   st.error(f"解析に失敗しました: {e}")

# セッションまたは過去データ選択
if 'custom_df_race' in st.session_state:
   df_race = st.session_state['custom_df_race']
   selected_race = "アップロードされた未来のレース"
else:
   if master_df is not None and not master_df.empty:
       master_df['レースID'] = master_df['年'].astype(str) + "年" + master_df['月'].astype(str) + "月" + master_df['日'].astype(str) + " " + master_df['場所'] + " " + master_df['レース番号'].astype(str) + "R " + master_df['略レース名'].astype(str)
       race_list = master_df['レースID'].unique()
       selected_race = st.sidebar.selectbox("🎯 過去のレースを選択", race_list)
       df_race = master_df[master_df['レースID'] == selected_race].copy()
       if '得意馬場' not in df_race.columns:
           df_race['得意馬場'] = '指定なし'
   else:
       df_race = None

if df_race is not None and not df_race.empty:
   st.sidebar.markdown("---")
   st.sidebar.info(f"**{selected_race}**\n\n頭数: {len(df_race)}頭")

   sample_row = df_race.iloc[0]
   race_place = str(sample_row.get('場所', '東京')).strip()
   race_surface = str(sample_row.get('芝・ダ', '芝')).strip()
   try:
       race_distance = int(float(sample_row.get('距離', 1600)))
   except:
       race_distance = 1600

   # 競馬場ごとの直線の長さ（m）を芝・ダート別に定義
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

   # 各競馬場ごとのタフさ係数（坂のキツさ、洋芝の重さ、コーナリング負荷など / 数値が大きいほどタフ・パワー要求）
   toughness_dict = {
       "中山": 1.35, "札幌": 1.30, "函館": 1.25, "阪神": 1.20,
       "福島": 1.15, "京都": 1.10, "中京": 1.05, "小倉": 1.00,
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
           <h3 style="margin: 0; color: #f1c40f;">📌 選択中レース情報</h3>
           <p style="font-size: 18px; margin: 5px 0 0 0;">
               <b>競馬場:</b> {race_place} (直線: {straight_len}m / タフ度: {course_toughness}) &nbsp;|&nbsp;
               <b>馬場種別:</b> {race_surface} &nbsp;|&nbsp;
               <b>距離:</b> {race_distance}m &nbsp;|&nbsp;
               <b>出走頭数:</b> {len(df_race)}頭
           </p>
       </div>
   """, unsafe_allow_html=True)

   st.markdown("### ✍️ 出走出馬データの確認・手動微調整（脚質・得意馬場）")
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
               help="馬の脚質を選択してください",
               options=["逃げ", "先行", "差し", "追込"],
               required=True,
           ),
           "得意馬場": st.column_config.SelectboxColumn(
               "得意馬場",
               help="この馬が最も得意とする馬場状態を選択",
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
   st.markdown("### ⚙️ 全体コンディション設定 & 距離適正フィルター詳細")
   col_p1, col_p2, col_p3 = st.columns(3)
   with col_p1:
       selected_pace = st.radio("ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1)
   with col_p2:
       selected_bias = st.radio("トラックバイアス", ["フラット", "内有利", "外有利"], index=0)
   with col_p3:
       selected_condition = st.selectbox("当日の馬場状態", ["良", "稍重", "重", "不良"], index=1)

   if race_distance <= 1400:
       race_category = "短距離"
   elif race_distance <= 1800:
       race_category = "マイル"
   elif race_distance <= 2200:
       race_category = "中距離"
   else:
       race_category = "長距離"

   st.info(f"💡 現在のレース設定距離（{race_distance}m）は **『{race_category}』** です。また、**『{race_place}』（直線 {straight_len}m / タフ度 {course_toughness}）** のコース特性に合わせて末脚やパワー（タフさ）の補正が自動調整されます。")
   distance_strictness = st.slider("🎯 距離適正フィルターの厳しさ（距離カテゴリ不適合のペナルティ倍率）", min_value=0.0, max_value=3.0, value=1.5, step=0.5)

   st.markdown("---")

   def format_time(seconds):
       m = int(seconds // 60)
       s = seconds % 60
       if m > 0:
           return f"{m}分{s:04.1f}秒"
       else:
           return f"{s:.1f}秒"

   def run_monte_carlo_simulation(df_r, pace, bias, condition, master_data, target_cat, strictness, straight_length, place_name, surface_type, toughness_val, num_simulations=10000):
       res_df = df_r.copy()
       try:
           target_distance = float(res_df.iloc[0].get('距離', 1600.0))
       except:
           target_distance = 1600.0

       surface = str(surface_type).strip()

       if 'ダ' in surface:
           if target_distance <= 1400:
               base_rate_per_1000 = 60.5
           elif target_distance <= 1800:
               base_rate_per_1000 = 62.5
           elif target_distance <= 2200:
               base_rate_per_1000 = 64.0
           else:
               base_rate_per_1000 = 65.5

           base_seconds = (target_distance / 1000.0) * base_rate_per_1000
           condition_time_add = {"良": 0.0, "稍重": -0.5, "重": -1.5, "不良": -3.0}.get(condition, 0.0)
       else:
           if target_distance <= 1400:
               base_rate_per_1000 = 57.5
           elif target_distance <= 1800:
               base_rate_per_1000 = 59.0
           elif target_distance <= 2200:
               base_rate_per_1000 = 60.5
           else:
               base_rate_per_1000 = 62.0

           base_seconds = (target_distance / 1000.0) * base_rate_per_1000
           condition_time_add = {"良": 0.0, "稍重": 1.0, "重": 2.5, "不良": 4.5}.get(condition, 0.0)

       base_seconds += condition_time_add

       course_speed_factor = 1.0
       if "中山" in place_name or "福島" in place_name:
           course_speed_factor = 0.992
       elif "京都" in place_name or "東京" in place_name:
           course_speed_factor = 0.985
       elif "阪神" in place_name:
           course_speed_factor = 0.988
       elif "小倉" in place_name:
           course_speed_factor = 0.986
       else:
           course_speed_factor = 1.0

       base_seconds = base_seconds * course_speed_factor

       if 'ダ' in surface:
           f3_weight_factor = max(0.5, min(1.15, straight_length / 450.0))
       else:
           f3_weight_factor = max(0.4, min(1.6, straight_length / 350.0))

       horse_ability_map = {}
       horse_speed_bonus_map = {}
       horse_f3_bonus_map = {}
       horse_distance_fit_map = {}
       horse_grade_bonus_map = {}
       horse_course_fit_map = {}

       if master_data is not None and '馬名' in master_data.columns:
           sort_cols = [c for c in ['年', '月', '日'] if c in master_data.columns]
           if sort_cols:
               master_data = master_data.sort_values(by=sort_cols, ascending=False)

           if '芝・ダ' in master_data.columns:
               target_surface_keyword = "ダ" if "ダ" in surface else "芝"
               if "ダ" in target_surface_keyword:
                   filtered_master = master_data[master_data['芝・ダ'].str.contains("ダ", na=False)].copy()
               else:
                   filtered_master = master_data[~master_data['芝・ダ'].str.contains("ダ", na=False)].copy()
              
               if len(filtered_master) < 5:
                   filtered_master = master_data.copy()
           else:
               filtered_master = master_data.copy()

           recent_master_data = filtered_master.groupby('馬名').head(6).copy()

           if '着順' in recent_master_data.columns:
               recent_master_data['着順_num'] = pd.to_numeric(recent_master_data['着順'], errors='coerce')
               avg_finishes = recent_master_data.groupby('馬名')['着順_num'].mean().to_dict()
               for hname, af in avg_finishes.items():
                   if not pd.isna(af):
                       horse_ability_map[hname] = max(0.0, (15.0 - (af - 1) * 1.2) * 0.5)

           if '走破タイム' in recent_master_data.columns and '距離' in recent_master_data.columns:
               recent_master_data['走破タイム_num'] = pd.to_numeric(recent_master_data['走破タイム'], errors='coerce')
               recent_master_data['距離_num'] = pd.to_numeric(recent_master_data['距離'], errors='coerce')
               recent_master_data['speed_per_1000m'] = recent_master_data['走破タイム_num'] / (recent_master_data['距離_num'] / 1000.0)
              
               avg_speeds = recent_master_data.groupby('馬名')['speed_per_1000m'].mean()
               if not avg_speeds.empty:
                   mean_all_speed = avg_speeds.mean()
                   speed_diffs = (mean_all_speed - avg_speeds).to_dict()
                   for hname, sd in speed_diffs.items():
                       if not pd.isna(sd):
                           horse_speed_bonus_map[hname] = max(-3.0, min(10.0, sd * (target_distance / 1000.0) * 2.5))

           if '上がり3Fタイム' in recent_master_data.columns:
               recent_master_data['上がり3F_num'] = pd.to_numeric(recent_master_data['上がり3Fタイム'], errors='coerce')
               avg_f3 = recent_master_data.groupby('馬名')['上がり3F_num'].mean()
               if not avg_f3.empty:
                   mean_all_f3 = avg_f3.mean()
                   f3_diffs = (mean_all_f3 - avg_f3).to_dict()
                   for hname, fd in f3_diffs.items():
                       if not pd.isna(fd):
                           horse_f3_bonus_map[hname] = max(-3.0, min(10.0, fd * 2.5 * f3_weight_factor))

           if '略レース名' in recent_master_data.columns and '着順' in recent_master_data.columns:
               def calc_grade_bonus(group):
                   bonus = 0.0
                   for _, row in group.iterrows():
                       rname = str(row.get('略レース名', ''))
                       fin = pd.to_numeric(row.get('着順', 99), errors='coerce')
                       if any(g in rname for g in ['G1', 'Ｇ１', '優駿牝馬', 'オークス', 'ダービー', '桜花賞']):
                           if fin <= 3: bonus += 4.0
                           elif fin <= 5: bonus += 2.0
                       elif any(g in rname for g in ['G2', 'Ｇ２', 'フローラ', '弥生賞', '青葉賞']):
                           if fin <= 3: bonus += 3.0
                           elif fin <= 5: bonus += 1.5
                       elif any(g in rname for g in ['G3', 'Ｇ３', 'きさらぎ', '共同通信']):
                           if fin <= 3: bonus += 2.0
                   return bonus

               grade_bonuses = recent_master_data.groupby('馬名').apply(calc_grade_bonus).to_dict()
               for hname, gbonus in grade_bonuses.items():
                   horse_grade_bonus_map[hname] = gbonus

           if '距離' in recent_master_data.columns:
               recent_master_data['距離_num'] = pd.to_numeric(recent_master_data['距離'], errors='coerce')
               
               def evaluate_distance_fit(group):
                   dists = group['距離_num'].dropna()
                   if len(dists) == 0:
                       return 0.0
                   mean_diff = np.abs(dists - target_distance).mean()
                   if target_cat == "長距離":
                       avg_run_dist = dists.mean()
                       if avg_run_dist < 2100: return -8.0 * strictness
                       elif avg_run_dist >= 2300: return 5.0
                       else: return 0.0
                   else:
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
                           if m_fin == 1:
                               fit_bonus += 3.5
                           elif m_fin <= 3:
                               fit_bonus += 1.5
                   return min(5.0, fit_bonus)

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
               speed_bonus = horse_speed_bonus_map.get(hname, 0.0)
               f3_bonus = horse_f3_bonus_map.get(hname, 0.0)
               dist_fit_bonus = horse_distance_fit_map.get(hname, 0.0)
               grade_bonus = horse_grade_bonus_map.get(hname, 0.0)
               course_fit_bonus = horse_course_fit_map.get(hname, 0.0)

               # タフ度（パワー・スタミナの要求度）に応じた補正
               # タフな競馬場（中山・札幌など）では、スピードだけに頼る馬が減点され、パワー型や好走実績のある馬が相対的に浮上
               toughness_effect = (toughness_val - 1.0) * 4.0
               base_score = 70.0 + ability_bonus + speed_bonus + dist_fit_bonus + grade_bonus + course_fit_bonus + np.random.normal(0, 3.0)

               if toughness_val >= 1.2:
                   # タフな馬場やコースでは、末脚一辺倒より前目（逃げ・先行）やパワータイプに恩恵、または馬場コンディション連動
                   if kyakushitsu in ["逃げ", "先行"]:
                       base_score += toughness_effect * 1.5

               if straight_length <= 320:
                   if kyakushitsu in ["逃げ", "先行"]:
                       base_score += 5.0
                   elif kyakushitsu in ["差し", "追込"]:
                       base_score -= 2.0

               if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
                   base_score += 3.0
               elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
                   base_score += 4.5 + (f3_bonus * 0.9)
               else:
                   base_score += (f3_bonus * 0.6)

               if bias == "内有利" and wakuban <= 3:
                   base_score += 3.0
               elif bias == "外有利" and wakuban >= 6:
                   base_score += 3.0

               if tokui_baba == condition:
                   base_score += 5.0

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
           kyakushitsu = str(r.get('脚質', '差し'))
           tokui_baba = str(r.get('得意馬場', '指定なし'))
           wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1

           b_score = 70.0 + horse_ability_map.get(hname, 2.5) + horse_speed_bonus_map.get(hname, 0.0) + horse_distance_fit_map.get(hname, 0.0) + horse_grade_bonus_map.get(hname, 0.0) + horse_course_fit_map.get(hname, 0.0)
          
           if straight_length <= 320 and kyakushitsu in ["逃げ", "先行"]: b_score += 3.0
           if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]: b_score += 3.0
           elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]: b_score += 3.5 + (horse_f3_bonus_map.get(hname, 0.0) * 0.5)
           if bias == "内有利" and wakuban <= 3: b_score += 1.5
           elif bias == "外有利" and wakuban >= 6: b_score += 1.5
           if tokui_baba == condition: b_score += 4.0
           sim_scores_mean.append(b_score)

       res_df['temp_score'] = sim_scores_mean
       res_df = res_df.sort_values(by=['勝率(%)', 'temp_score'], ascending=False).reset_index(drop=True)
       res_df['着順予測'] = range(1, len(res_df) + 1)

       times = []
       for i in range(len(res_df)):
           hname = str(res_df.iloc[i].get('馬名', ''))
           time_mod = -horse_speed_bonus_map.get(hname, 0.0) * 0.15
           t = base_seconds + (i * 0.3) + time_mod + np.random.uniform(0.0, 0.3)
           times.append(round(max(base_seconds - 2.0, t), 1))

       res_df['予測走破タイム'] = [format_time(t) for t in times]
       return res_df

   st.markdown("<br>", unsafe_allow_html=True)
   if st.button("🚀 コース特性（直線長・タフ度）連動シミュレーションを実行"):
       with st.spinner(f"{race_place}（直線 {straight_len}m / タフ度 {course_toughness}）の特性を反映して10,000回シミュレーションを実行中..."):
           st.session_state['df_simulated'] = run_monte_carlo_simulation(df_race, selected_pace, selected_bias, selected_condition, master_df, race_category, distance_strictness, straight_len, race_place, race_surface, course_toughness, num_simulations=10000)
           st.session_state['sim_executed'] = True

   if st.session_state.get('sim_executed', False) and 'df_simulated' in st.session_state:
       st.markdown(f"<br><h3>🏆 10,000回シミュレーション結果（{race_place} 直線:{straight_len}m / タフ度:{course_toughness} / {race_surface}{race_distance}m）</h3>", unsafe_allow_html=True)

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
   st.info("👈 サイドバーから未来のレースの出馬表スクショをアップロードするか、過去データを選択してください。")
