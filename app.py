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

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>本格競馬展開シミュレーター（条件表示対応版）</h2>", unsafe_allow_html=True)

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
       with st.spinner("AIが馬名やオッズを読み取っています..."):
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
                           "この画像は競馬の出馬表です。記載されている「枠番」「馬番」「馬名」「オッズ（人気順や倍率など）」「脚質」に加え、もし画像内から「場所（競馬場名）」や「距離」や「芝・ダ（ダートか芝か）」が読み取れればそれも含めて、以下のJSON配列の形式のみで正確に出力してください。他の余分なテキストやマークダウンのバッククォートは含めないでください。\n"
                           '[{"枠番": 1, "馬番": 1, "馬名": "馬名A", "オッズ": 13.9, "脚質": "差し", "場所": "東京", "距離": 1800, "芝・ダ": "ダ"}, ...]'
                       ]
                   )

                   cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                   parsed_data = json.loads(cleaned_text)

                   df_race = pd.DataFrame(parsed_data)
                   if '場所' not in df_race.columns:
                       df_race['場所'] = '東京'
                   if '距離' not in df_race.columns:
                       df_race['距離'] = 1800.0 
                   if '芝・ダ' not in df_race.columns:
                       df_race['芝・ダ'] = 'ダ'
                   df_race['馬場状態'] = '良'
                   df_race['略レース名'] = '解析レース'

                   st.session_state['custom_df_race'] = df_race
                   st.success("出馬表の読み込みに成功しました！")
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
   else:
       df_race = None

if df_race is not None and not df_race.empty:
   st.sidebar.markdown("---")
   st.sidebar.info(f"**{selected_race}**\n\n頭数: {len(df_race)}頭")

   # レース情報（場所・芝/ダ・距離）の抽出
   sample_row = df_race.iloc[0]
   race_place = sample_row.get('場所', '不明')
   race_surface = sample_row.get('芝・ダ', 'ダ')
   try:
       race_distance = int(float(sample_row.get('距離', 1800)))
   except:
       race_distance = 1800

   # 画面上部にレース条件パネルを表示
   st.markdown(f"""
       <div class="race-info-box">
           <h3 style="margin: 0; color: #f1c40f;">📌 選択中レース情報</h3>
           <p style="font-size: 18px; margin: 5px 0 0 0;">
               <b>競馬場:</b> {race_place} &nbsp;|&nbsp;
               <b>馬場種別:</b> {race_surface} &nbsp;|&nbsp;
               <b>距離:</b> {race_distance}m &nbsp;|&nbsp;
               <b>出走頭数:</b> {len(df_race)}頭
           </p>
       </div>
   """, unsafe_allow_html=True)

   st.markdown("### ⚙️ 展開・馬場コンディション設定")
   col_p1, col_p2, col_p3 = st.columns(3)
   with col_p1:
       selected_pace = st.radio("ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1)
   with col_p2:
       selected_bias = st.radio("トラックバイアス", ["フラット", "内有利", "外有利"], index=0)
   with col_p3:
       selected_condition = st.selectbox("馬場状態", ["良", "稍重", "重", "不良"], index=0)

   st.markdown("---")

   def format_time(seconds):
       m = int(seconds // 60)
       s = seconds % 60
       if m > 0:
           return f"{m}分{s:04.1f}秒"
       else:
           return f"{s:.1f}秒"

   def run_monte_carlo_simulation(df_r, pace, bias, condition, master_data, num_simulations=10000):
       res_df = df_r.copy()
       try:
           distance = float(res_df.iloc[0].get('距離', 1800.0))
       except:
           distance = 1800.0

       surface = str(res_df.iloc[0].get('芝・ダ', 'ダ')).strip()

       # 基本のタイム基準（良馬場をベースにする）
       if 'ダ' in surface:
           base_seconds = (distance / 1000.0) * 61.5
           # ダート：重・不良ほど脚抜きが良くなり時計が「速く（マイナスに）」なる
           condition_time_add = {
               "良": 0.0,
               "稍重": -0.8,
               "重": -1.8,
               "不良": -3.0
           }.get(condition, 0.0)
       else:
           # 芝：重・不良ほどタフになりタイムがかかる（プラス）
           base_seconds = (distance / 1000.0) * 58.0
           condition_time_add = {
               "良": 0.0,
               "稍重": 0.8,
               "重": 1.8,
               "不良": 3.0
           }.get(condition, 0.0)

       base_seconds += condition_time_add

       # マスターデータから各馬の過去実績（平均着順など）を計算して辞書にする
       horse_ability_map = {}
       if master_data is not None and '馬名' in master_data.columns and '着順' in master_data.columns:
           master_data['着順_num'] = pd.to_numeric(master_data['着順'], errors='coerce')
           avg_finishes = master_data.groupby('馬名')['着順_num'].mean().to_dict()
           for hname, af in avg_finishes.items():
               if not pd.isna(af):
                   horse_ability_map[hname] = max(0.0, 15.0 - (af - 1) * 1.2)

       n_horses = len(res_df)
       win_counts = np.zeros(n_horses)
       place_counts = np.zeros(n_horses)
       show_counts = np.zeros(n_horses)

       for _ in range(num_simulations):
           sim_scores = []
           for idx, r in res_df.iterrows():
               hname = str(r.get('name') or r.get('馬名', ''))
               kyakushitsu = str(r.get('脚質', '差し'))
               wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1
               try:
                   odds = float(r.get('オッズ', 10.0))
               except:
                   odds = 10.0

               ability_bonus = horse_ability_map.get(hname, 5.0)
               odds_bonus = max(0.0, 12.0 - np.log(max(odds, 1.1)) * 3.5)
               base_score = 70.0 + ability_bonus + odds_bonus + np.random.normal(0, 3.0)

               # ペース補正
               if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
                   base_score += 6.0
               elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
                   base_score += 6.0

               # バイアス補正
               if bias == "内有利" and wakuban <= 3:
                   base_score += 4.0
               elif bias == "外有利" and wakuban >= 6:
                   base_score += 4.0

               # ダート等で重・不良（脚抜きが良い高速馬場）のときは、前目（逃げ・先行）に有利な補正
               if 'ダ' in surface and condition in ["重", "不良"]:
                   if kyakushitsu in ["逃げ", "先行"]:
                       base_score += 3.0

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

       # ソート用の一時スコア計算
       sim_scores_mean = []
       for idx, r in res_df.iterrows():
           hname = str(r.get('馬名', ''))
           kyakushitsu = str(r.get('脚質', '差し'))
           wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1
           try:
               odds = float(r.get('オッズ', 10.0))
           except:
               odds = 10.0

           b_score = 70.0 + horse_ability_map.get(hname, 5.0) + max(0.0, 12.0 - np.log(max(odds, 1.1)) * 3.5)
           if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]: b_score += 4.0
           elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]: b_score += 4.0
           if bias == "内有利" and wakuban <= 3: b_score += 2.0
           elif bias == "外有利" and wakuban >= 6: b_score += 2.0
           if 'ダ' in surface and condition in ["重", "不良"] and kyakushitsu in ["逃げ", "先行"]:
               b_score += 2.0
           sim_scores_mean.append(b_score)

       res_df['temp_score'] = sim_scores_mean
       res_df = res_df.sort_values(by=['勝率(%)', 'temp_score'], ascending=False).reset_index(drop=True)
       res_df['着順予測'] = range(1, len(res_df) + 1)

       times = []
       for i in range(len(res_df)):
           t = base_seconds + (i * 0.3) + np.random.uniform(0.0, 0.4)
           times.append(round(t, 1))

       res_df['予測走破タイム'] = [format_time(t) for t in times]
       return res_df

   st.markdown("<br>", unsafe_allow_html=True)
   if st.button("🚀 10,000回展開シミュレーションを実行する"):
       with st.spinner("シミュレーションを実行中..."):
           st.session_state['df_simulated'] = run_monte_carlo_simulation(df_race, selected_pace, selected_bias, selected_condition, master_df, num_simulations=10000)
           st.session_state['sim_executed'] = True

   if st.session_state.get('sim_executed', False) and 'df_simulated' in st.session_state:
       st.markdown(f"<br><h3>🏆 10,000回シミュレーション結果（{race_place} {race_surface}{race_distance}m / 馬場: {selected_condition}）</h3>", unsafe_allow_html=True)

       df_simulated = st.session_state['df_simulated']
       display_columns = [c for c in ['着順予測', '馬番', '馬名', 'オッズ', '脚質', '勝率(%)', '連対率(%)', '複勝率(%)', '予測走破タイム'] if c in df_simulated.columns]
       display_df = df_simulated[display_columns].copy()

       display_df['勝率(%)'] = display_df['勝率(%)'].apply(lambda x: f"{x:.1f}%")
       display_df['連対率(%)'] = display_df['連対率(%)'].apply(lambda x: f"{x:.1f}%")
       display_df['複勝率(%)'] = display_df['複勝率(%)'].apply(lambda x: f"{x:.1f}%")

       st.dataframe(display_df, use_container_width=True, hide_index=True)
   else:
       st.info("👆 条件を確認・調整してボタンを押すとシミュレーションが実行されます。")

else:
   st.info("👈 サイドバーから未来のレースの出馬表スクショをアップロードするか、過去データを選択してください。")
