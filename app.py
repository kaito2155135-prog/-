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
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>本格競馬展開シミュレーター（1万回試行 ＆ スクショ読込）</h2>", unsafe_allow_html=True)

# 1. 画像アップロードによる出馬表自動読み込み
st.sidebar.markdown("### 📥 出馬表スクショから読み込む")
uploaded_image = st.sidebar.file_uploader("出馬表の画像をアップロード", type=['png', 'jpg', 'jpeg'])

df_race = None

if uploaded_image is not None:
    st.sidebar.image(uploaded_image, caption="アップロードされた出馬表", use_container_width=True)
    if st.sidebar.button("✨ 画像からAI解析を実行"):
        with st.spinner("AIが馬名やオッズを読み取っています..."):
            try:
                from google import genai
                image_bytes = uploaded_image.getvalue()
               
                # APIキーの取得（Secrets または 環境変数）
                api_key = None
                try:
                    api_key = st.secrets["GEMINI_API_KEY"]
                except:
                    api_key = os.environ.get("GEMINI_API_KEY")
               
                if not api_key:
                    st.error("⚠️ GEMINI_API_KEY が設定されていません。StreamlitのSecretsに設定してください。")
                else:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[
                            image_bytes,
                            "この画像は競馬の出馬表です。記載されている「枠番」「馬番」「馬名」「オッズ（人気順や倍率など）」をすべて読み取り、以下のJSON配列の形式のみで正確に出力してください。他の余分なテキストやマークダウンのバッククォートは含めないでください。\n"
                            '[{"枠番": 1, "馬番": 1, "馬名": "馬名A", "オッズ": 13.9, "脚質": "差し"}, ...]'
                        ]
                    )
                   
                    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                    parsed_data = json.loads(cleaned_text)
                   
                    df_race = pd.DataFrame(parsed_data)
                    df_race['距離'] = 1600.0 
                    df_race['芝・ダ'] = '芝'
                    df_race['馬場状態'] = '良'
                    df_race['略レース名'] = '解析レース'
                   
                    st.session_state['custom_df_race'] = df_race
                    st.success("出馬表の読み込みに成功しました！")
            except Exception as e:
                st.error(f"解析に失敗しました: {e}")

# セッションにデータがあれば利用
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

    def format_time(seconds):
        m = int(seconds // 60)
        s = seconds % 60
        if m > 0:
            return f"{m}分{s:04.1f}秒"
        else:
            return f"{s:.1f}秒"

    def run_monte_carlo_simulation(df_r, pace, bias, num_simulations=10000):
        res_df = df_r.copy()
        try:
            distance = float(res_df.iloc[0].get('距離', 1600.0))
        except:
            distance = 1600.0
           
        base_seconds = (distance / 1000.0) * 57.2
       
        n_horses = len(res_df)
        win_counts = np.zeros(n_horses)
        place_counts = np.zeros(n_horses)
        show_counts = np.zeros(n_horses)
       
        for _ in range(num_simulations):
            sim_scores = []
            for idx, r in res_df.iterrows():
                kyakushitsu = str(r.get('脚質', '差し'))
                wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1
               
                base_score = np.random.uniform(70, 95) + np.random.normal(0, 3.5)
                if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]:
                    base_score += 8.0
                elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]:
                    base_score += 8.0
                   
                if bias == "内有利" and wakuban <= 3:
                    base_score += 5.0
                elif bias == "外有利" and wakuban >= 6:
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
            kyakushitsu = str(r.get('脚質', '差し'))
            wakuban = int(r.get('枠番', 1)) if pd.notnull(r.get('枠番', 1)) else 1
            b_score = 80.0
            if pace == "S（スロー）" and kyakushitsu in ["逃げ", "先行"]: b_score += 5.0
            elif pace == "H（ハイ）" and kyakushitsu in ["差し", "追込"]: b_score += 5.0
            if bias == "内有利" and wakuban <= 3: b_score += 3.0
            elif bias == "外有利" and wakuban >= 6: b_score += 3.0
            sim_scores_mean.append(b_score)
           
        res_df['temp_score'] = sim_scores_mean
        res_df = res_df.sort_values(by=['勝率(%)', 'temp_score'], ascending=False).reset_index(drop=True)
        res_df['着順予測'] = range(1, len(res_df) + 1)
       
        times = []
        for i in range(len(res_df)):
            t = base_seconds + (i * 0.18) + np.random.uniform(0.0, 0.3)
            times.append(round(t, 1))
           
        res_df['予測走破タイム'] = [format_time(t) for t in times]
        return res_df

    # ボタン式に変更：このボタンを押したときだけ1万回シミュレーションが走る
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 10,000回展開シミュレーションを実行する"):
        with st.spinner("10,000回の展開シミュレーションを実行中..."):
            st.session_state['df_simulated'] = run_monte_carlo_simulation(df_race, selected_pace, selected_bias, num_simulations=10000)
            st.session_state['sim_executed'] = True

    if st.session_state.get('sim_executed', False) and 'df_simulated' in st.session_state:
        st.markdown("<br><h3>🏆 10,000回シミュレーション結果（確率分析）</h3>", unsafe_allow_html=True)
       
        df_simulated = st.session_state['df_simulated']
        display_columns = [c for c in ['着順予測', '馬番', '馬名', 'オッズ', '脚質', '勝率(%)', '連対率(%)', '複勝率(%)', '予測走破タイム'] if c in df_simulated.columns]
        display_df = df_simulated[display_columns].copy()
       
        display_df['勝率(%)'] = display_df['勝率(%)'].apply(lambda x: f"{x:.1f}%")
        display_df['連対率(%)'] = display_df['連対率(%)'].apply(lambda x: f"{x:.1f}%")
        display_df['複勝率(%)'] = display_df['複勝率(%)'].apply(lambda x: f"{x:.1f}%")
       
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("👆 上のボタンを押すと、10,000回シミュレーションと確率分析結果が表示されます。")

else:
    st.info("👈 サイドバーから未来のレースの出馬表スクショをアップロードするか、過去データを選択してください。")
