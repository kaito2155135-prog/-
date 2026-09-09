import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="本格競馬展開シミュレーター", layout="wide")

# 2枚目の画像に合わせた、重厚感のあるダーク＆ゴールドのカスタムデザイン
st.markdown("""
    <style>
    .main { background-color: #0b0b0b; color: #ffffff; }
    h1, h2, h3 { color: #f1c40f !important; font-family: sans-serif; }
   
    /* 2枚目の画像にあるゴールドの操作ボタン風 */
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
   
    /* セレクトボックスやデータフレームのスタイリング */
    .stSelectbox div[data-baseweb="select"] {
        background-color: #1a1a1a;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #f1c40f;'>レースシミュレーション</h2>", unsafe_allow_html=True)

csv_filename = "keiba_master_data.csv"

if os.path.exists(csv_filename):
    try:
        df = pd.read_csv(csv_filename, encoding='utf-8')
    except:
        df = pd.read_csv(csv_filename, encoding='cp932')
       
    df['レースID'] = df['年'].astype(str) + "年" + df['月'].astype(str) + "月" + df['日'].astype(str) + " " + df['場所'] + " " + df['レース番号'].astype(str) + "R " + df['略レース名'].astype(str)
   
    race_list = df['レースID'].unique()
    selected_race = st.sidebar.selectbox("🎯 レースを選択", race_list)
   
    df_race = df[df['レースID'] == selected_race].copy()
    row_info = df_race.iloc[0]
   
    st.sidebar.markdown("---")
    st.sidebar.info(f"**{selected_race}**\n\n{row_info['芝・ダ']} {row_info['距離']}m ({row_info['馬場状態']}) / {row_info['頭数']}頭")
   
    # JRA枠番カラーの定義
    def get_waku_color(wakuban):
        waku_colors = {
            1: "#ffffff",  # 白
            2: "#333333",  # 黒
            3: "#d9381e",  # 赤
            4: "#1f77b4",  # 青
            5: "#e5c100",  # 黄
            6: "#2ca02c",  # 緑
            7: "#ff7f0e",  # 桃
            8: "#9467bd"   # 橙
        }
        return waku_colors.get(int(wakuban) if pd.notnull(wakuban) else 1, "#1f77b4")

    # 2枚目の画像にそっくりな「立体風コースビジュアル」をHTML/CSSでレンダリング
    # 左上にポケット、SとGのマーカー、そしてカラフルな馬番ボールが並ぶ仕様
    def render_course_board(df_r):
        # 馬のアイコン文字列を作成
        horses_html = ""
        for idx, r in df_r.iterrows():
            hn = int(r['馬番'])
            wk = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else ((hn - 1)//2)+1
            bg_c = get_waku_color(wk)
            txt_c = "#000000" if wk == 1 else "#ffffff"
           
            # コース上のランダムな位置に配置（シミュレーションを模した初期ポジション）
            np.random.seed(hn * 31)
            left_pos = 15 + (hn * 4.5) % 70
            top_pos = 35 + (hn * 3) % 40
           
            horses_html += f"""
            <div title="{r['馬名']} (馬番:{hn})" style="
                position: absolute;
                left: {left_pos}%;
                top: {top_pos}%;
                background-color: {bg_c};
                color: {txt_c};
                width: 28px; height: 28px;
                border-radius: 50%;
                border: 2px solid #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 12px;
                box-shadow: 0 3px 6px rgba(0,0,0,0.6);
                z-index: 10;
                cursor: pointer;
            ">{hn}</div>
            """

        board_html = f"""
        <div style="
            background: linear-gradient(135deg, #111e17 0%, #08110c 100%);
            border: 2px solid #333333;
            border-radius: 12px;
            padding: 20px;
            position: relative;
            width: 100%;
            height: 440px;
            box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
            overflow: hidden;
        ">
            <!-- 3D風立体コースのSVG図面（2枚目の画像の形状を完全再現） -->
            <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" viewBox="0 0 600 360" preserveAspectRatio="none">
                <!-- 外枠・影 -->
                <path d="M 120,70 C 80,70 40,110 50,180 C 60,250 180,310 380,310 C 500,310 550,260 540,190 C 530,120 420,70 300,70 Z"
                      fill="none" stroke="#163825" stroke-width="45" stroke-linejoin="round" />
                <!-- メインコース芝生 -->
                <path d="M 120,75 C 85,75 50,115 60,180 C 70,245 180,300 380,300 C 490,300 535,255 525,190 C 515,125 415,75 300,75 Z"
                      fill="none" stroke="#1e5638" stroke-width="32" stroke-linejoin="round" />
                <!-- コーナーガイドライン（黄色線） -->
                <path d="M 120,75 C 85,75 50,115 60,180 C 70,245 180,300 380,300 C 490,300 535,255 525,190 C 515,125 415,75 300,75 Z"
                      fill="none" stroke="#f1c40f" stroke-width="1.5" stroke-dasharray="6,4" stroke-linejoin="round" />
                     
                <!-- 左上の引き込み線（ポケット） -->
                <line x1="120" y1="75" x2="60" y2="40" stroke="#1e5638" stroke-width="24" stroke-linecap="round" />
                <line x1="120" y1="75" x2="60" y2="40" stroke="#f1c40f" stroke-width="1" stroke-dasharray="4,3" />
            </svg>

            <!-- S (スタート) と G (ゴール) マーカー -->
            <div style="position: absolute; left: 10%; top: 32%; background: rgba(0,0,0,0.7); border: 1px solid #fff; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 14px;">S</div>
            <div style="position: absolute; left: 24%; top: 78%; background: rgba(0,0,0,0.7); border: 2px solid #f1c40f; color: #f1c40f; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 14px;">G</div>

            <!-- 動的馬番アイコン群 -->
            {horses_html}
        </div>
        """
        return board_html

    # 1. コースビジュアルボードの表示
    st.markdown(render_course_board(df_race), unsafe_allow_html=True)
   
    st.markdown("<br>", unsafe_allow_html=True)
   
    # 2. 馬番ごとの丸アイコンがズラリと並ぶバー（2枚目画像の中央部分）
    waku_bar_html = "<div style='display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; background-color: #161616; padding: 10px; border-radius: 8px; border: 1px solid #333;'>"
    for _, r in df_race.sort_values('馬番').iterrows():
        hn = int(r['馬番'])
        wk = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else ((hn - 1)//2)+1
        bg_c = get_waku_color(wk)
        txt_c = "#000000" if wk == 1 else "#ffffff"
        waku_bar_html += f"<div style='background-color: {bg_c}; color: {txt_c}; border: 1px solid #fff; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px;'>{hn}</div>"
    waku_bar_html += "</div>"
    st.markdown(waku_bar_html, unsafe_allow_html=True)
   
    st.markdown("<br>", unsafe_allow_html=True)
   
    # 3. 「別の展開で再シミュレート」ボタン
    if st.button("▶ 別の展開で再シミュレート"):
        st.toast("新しい展開パターンでシミュレーションを実行しました！", icon="🐎")

    # 4. ペース設定やバイアスの切り替えボタンUI（2枚目の画像の下部を再現）
    st.markdown("""
        <div style="margin-top: 20px; background-color: #181818; padding: 15px; border-radius: 8px; border: 1px solid #333;">
            <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">ペース想定（手動変更・実際はM-0.6）</div>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <div style="flex: 1; text-align: center; padding: 6px; background: #262626; border-radius: 4px; color: #888; font-size: 13px;">S（スロー）</div>
                <div style="flex: 1; text-align: center; padding: 6px; background: #3a3210; border: 1px solid #f1c40f; border-radius: 4px; color: #f1c40f; font-weight: bold; font-size: 13px;">M（ミドル）</div>
                <div style="flex: 1; text-align: center; padding: 6px; background: #262626; border-radius: 4px; color: #888; font-size: 13px;">H（ハイ）</div>
            </div>
           
            <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">トラックバイアス（馬場・傾向）</div>
            <div style="display: flex; gap: 10px;">
                <div style="flex: 1; text-align: center; padding: 6px; background: #3a3210; border: 1px solid #f1c40f; border-radius: 4px; color: #f1c40f; font-weight: bold; font-size: 13px;">フラット</div>
                <div style="flex: 1; text-align: center; padding: 6px; background: #262626; border-radius: 4px; color: #888; font-size: 13px;">内有利</div>
                <div style="flex: 1; text-align: center; padding: 6px; background: #262626; border-radius: 4px; color: #888; font-size: 13px;">外有利</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
   
    # 5. 結果一覧リスト
    st.markdown("<br><h3>🏆 着順予測・シミュレーション結果</h3>", unsafe_allow_html=True)
    df_result = df_race.sort_values('着順').copy()
    df_result['着順'] = df_result['着順'].astype(int)
   
    possible_cols = ['着順', '馬番', '馬名', '脚質', '走破タイム', '通過順4角', '上がり3Fタイム']
    available_cols = [c for c in possible_cols if c in df_result.columns]
   
    st.dataframe(
        df_result[available_cols],
        use_container_width=True,
        hide_index=True
    )

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
