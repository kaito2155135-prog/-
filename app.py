import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import streamlit.components.v1 as components
from google import genai  # 画像解析用

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
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>未来のレース予想（出馬表スクショ読込）</h2>", unsafe_allow_html=True)

# 1. 画像アップロードによる出馬表自動読み込み
st.sidebar.markdown("### 📥 出馬表スクショから読み込む")
uploaded_image = st.sidebar.file_uploader("出馬表の画像をアップロード", type=['png', 'jpg', 'jpeg'])

df_race = None

if uploaded_image is not None:
    st.sidebar.image(uploaded_image, caption="アップロードされた出馬表", use_column_width=True)
    if st.sidebar.button("✨ 画像からAI解析を実行"):
        with st.spinner("AIが馬名やオッズを読み取っています..."):
            try:
                # 画像をバイトデータとして読み込み
                image_bytes = uploaded_image.getvalue()
               
                # Geminiモデルで画像を解析して構造化データ（JSON）に変換
                client = genai.Client()
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        image_bytes,
                        "この画像は競馬の出馬表です。記載されている「枠番」「馬番」「馬名」「オッズ（人気順や倍率など）」をすべて読み取り、以下のJSON配列の形式のみで正確に出力してください。他の余分なテキストやマークダウンのバッククォートは含めないでください。\n"
                        '[{"枠番": 1, "馬番": 1, "馬名": "馬名A", "オッズ": 13.9, "脚質": "差し"}, ...]'
                    ]
                )
               
                # レスポンスからJSONを抽出
                cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                parsed_data = json.loads(cleaned_text)
               
                df_race = pd.DataFrame(parsed_data)
                df_race['距離'] = 1600.0  # デフォルト（必要に応じて画像から読み取ることも可能）
                df_race['芝・ダ'] = '芝'
                df_race['馬場状態'] = '良'
                df_race['略レース名'] = '解析レース'
               
                st.session_state['custom_df_race'] = df_race
                st.success("出馬表の読み込みに成功しました！")
            except Exception as e:
                st.error(f"解析に失敗しました: {e}")

# セッションにデータがあればそれを利用、なければ既存のCSVフォールバック
if 'custom_df_race' in st.session_state:
    df_race = st.session_state['custom_df_race']
    selected_race = "アップロードされた未来のレース"
else:
    csv_filename = "keiba_master_data.csv"
    if os.path.exists(csv_filename):
        try:
            df = pd.read_csv(csv_filename, encoding='utf-8')
        except:
            df = pd.read_csv(csv_filename, encoding='cp932')
        df['レースID'] = df['年'].astype(str) + "年" + df['月'].astype(str) + "月" + df['日'].astype(str) + " " + df['場所'] + " " + df['レース番号'].astype(str) + "R " + df['略レース名'].astype(str)
        race_list = df['レースID'].unique()
        selected_race = st.sidebar.selectbox("🎯 過去のレースを選択", race_list)
        df_race = df[df['レースID'] == selected_race].copy()
    else:
        df_race = None

if df_race is not None and not df_race.empty:
    row_info = df_race.iloc[0]
    st.sidebar.markdown("---")
    st.sidebar.info(f"**{selected_race}**\n\n頭数: {len(df_race)}頭")
   
    st.markdown("### ⚙️ 展開・馬場コンディション設定")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_pace = st.radio("ペース想定", ["S（スロー）", "M（ミドル）", "H（ハイ）"], index=1, horizontal=True)
    with col_p2:
        selected_bias = st.radio("トラックバイアス（馬場・傾向）", ["フラット", "内有利", "外有利"], index=0, horizontal=True)
   
    st.markdown("---")

    def get_waku_color(wakuban):
        waku_colors = {
            1: "#ffffff", 2: "#333333", 3: "#d9381e", 4: "#1f77b4",
            5: "#e5c100", 6: "#2ca02c", 7: "#ff7f0e", 8: "#9467bd"
        }
        return waku_colors.get(int(wakuban) if pd.notnull(wakuban) else 1, "#1f77b4")

    def format_time(seconds):
        m = int(seconds // 60)
        s = seconds % 60
        if m > 0:
            return f"{m}分{s:04.1f}秒"
        else:
            return f"{s:.1f}秒"

    def simulate_single_race(df_r, pace, bias):
        res_df = df_r.copy()
        try:
            distance = float(res_df.iloc[0].get('距離', 1600.0))
        except:
            distance = 1600.0
           
        base_seconds = (distance / 1000.0) * 57.2 # G1/重賞基準
           
        sim_scores = []
        for idx, r in res_df.iterrows():
            kyakushitsu = str(r.get('脚質', '差し'))
            wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1
           
            base_score = np.random.uniform(70, 95) + np.random.normal(0, 3.0)
            if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
                base_score += 8.0
            elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
                base_score += 8.0
               
            if bias == "内有利" and wakuban <= 3:
                base_score += 5.0
            elif bias == "外有利" and wakuban >= 6:
                base_score += 5.0
               
            sim_scores.append(base_score)
           
        res_df['sim_score'] = sim_scores
        res_df = res_df.sort_values(by='sim_score', ascending=False).reset_index(drop=True)
        res_df['着順予測'] = range(1, len(res_df) + 1)
       
        times = []
        for i in range(len(res_df)):
            t = base_seconds + (i * 0.2) + np.random.uniform(0.0, 0.4)
            times.append(round(t, 1))
           
        res_df['予測走破秒'] = times
        res_df['予測走破タイム'] = [format_time(t) for t in times]
        return res_df

    df_simulated = simulate_single_race(df_race, selected_pace, selected_bias)

    # 予測結果一覧
    st.markdown("<br><h3>🏆 今回の個別レース予測結果</h3>", unsafe_allow_html=True)
    display_columns = [c for c in ['着順予測', '馬番', '馬名', '脚質', '予測走破タイム'] if c in df_simulated.columns]
    display_df = df_simulated[display_columns].copy()
   
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("👈 サイドバーから未来のレースの出馬表スクショをアップロードするか、過去データを選択してください。")
