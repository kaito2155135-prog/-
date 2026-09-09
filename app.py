import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="JRA-VAN リアルレース展開シミュレーター", layout="wide")

st.title("🐎 JRA-VAN 実データ連動 展開シミュレーション")
st.write("JRA-VANから出力したマスターデータCSVを読み込んで、実際のレースの通過順位や展開をアニメーションで再現します！")

# サイドバー：CSVファイルアップロード
st.sidebar.header("📂 データ読み込み")
uploaded_file = st.sidebar.file_uploader("keiba_master_data.csv をアップロード", type=['csv'])

if uploaded_file is not None:
    # CSVの読み込み（文字コードの自動判定またはutf-8/cp932）
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='cp932')
       
    st.sidebar.success("✅ データの読み込みに成功しました！")
   
    # レース選択の準備（年月日 + 場所 + レース番号 + 略レース名 で一意に特定）
    df['レースID'] = df['年'].astype(str) + "年" + df['月'].astype(str) + "月" + df['日'].astype(str) + " " + df['場所'] + " " + df['レース番号'].astype(str) + "R " + df['略レース名'].astype(str)
   
    race_list = df['レースID'].unique()
    selected_race = st.sidebar.selectbox("🎯 再現するレースを選択", race_list)
   
    # 選択されたレースのデータを抽出
    df_race = df[df['レースID'] == selected_race].copy()
   
    # レース基本情報の表示
    row_info = df_race.iloc[0]
    st.markdown(f"### 🏟️ {selected_race}")
    st.info(f"**条件:** {row_info['芝・ダ']} {row_info['距離']}m | **馬場:** {row_info['馬場状態']} | **頭数:** {row_info['頭数']}頭")
   
    # 出走馬一覧の表示
    with st.expander("📋 このレースの出走馬・通過順データを確認する"):
        st.dataframe(df_race[['馬番', '馬名', '脚質', '通過順1角', '通過順2角', '通過順3角', '通過順4角', '上がり3Fタイム', '着順']])
       
    if st.button("🚀 このレースの展開シミュレーションを開始！", type="primary"):
        total_distance = int(row_info['距離'])
        frames = 40  # アニメーションのコマ数
       
        sim_data = []
       
        for idx, row in df_race.iterrows():
            h_name = str(row['馬名'])
            h_num = int(row['馬番'])
           
            # 各コーナーの通過順位を取得（0の場合は推定、またはスタート位置・ゴール位置として処理）
            p1 = float(row['通過順1角']) if row['通過順1角'] > 0 else float(row['頭数']) / 2
            p2 = float(row['通過順2角']) if row['通過順2角'] > 0 else p1
            p3 = float(row['通過順3角']) if row['通過順3角'] > 0 else p2
            p4 = float(row['通過順4角']) if row['通過順4角'] > 0 else p3
            finish = float(row['着順']) if row['着順'] > 0 else h_num
           
            # 順位（1〜頭数）をコース上の距離（0m 〜 total_distance）にざっくり変換
            # スタート(0m) -> 1角(距離の25%) -> 2角(50%) -> 3角(75%) -> 4角/直線(90%) -> ゴール(100%)
            dist_checkpoints = [
                0,
                total_distance * 0.25,
                total_distance * 0.50,
                total_distance * 0.75,
                total_distance * 0.90,
                total_distance
            ]
           
            # 各チェックポイントでの「順位（何番手か）」
            # 順位を位置座標（馬番によるY軸や、先頭からの差）に落とし込む
            # ここでは簡易的に、通過順位を元にしたポジションの推移を作る
            rank_checkpoints = [
                h_num, # スタート直後は馬番順などのイーブン
                p1,
                p2,
                p3,
                p4,
                finish
            ]
           
            # 補間して滑らかな動き（フレームごと）を作る
            step_distances = np.linspace(0, total_distance, frames)
            step_ranks = np.interp(
                np.linspace(0, 5, frames),
                range(6),
                rank_checkpoints
            )
           
            for t in range(frames):
                # 順位が小さいほどゴール（total_distance）に近い、あるいは前方にいる表現にする
                # ここではシンプルに距離を進行させつつ、順位に応じて前後に揺らす
                progress_dist = (step_distances[t] / total_distance) * total_distance
                # 順位による前後の位置調整（1着に近いほど前にいる）
                position_offset = (row['頭数'] - step_ranks[t]) * 2.0
               
                current_pos = min(total_distance, max(0, progress_dist + position_offset))
               
                sim_data.append({
                    'Step': t,
                    '馬名': f"{h_num}. {h_name} ({row['脚質']})",
                    '距離地点(m)': current_pos,
                    '仮想Y軸': h_num * 10
                })
               
        df_sim = pd.DataFrame(sim_data)
       
        # Plotlyアニメーション描画
        fig = px.scatter(
            df_sim,
            x='距離地点(m)',
            y='仮想Y軸',
            animation_frame='Step',
            color='馬名',
            range_x=[-50, total_distance + 100],
            range_y=[0, (int(row_info['頭数']) + 1) * 10],
            title=f"【{selected_race}】 実データ再現アニメーション"
        )
       
        fig.update_traces(marker=dict(size=18))
        fig.update_layout(
            xaxis_title="コース進行度 (スタート 0m → ゴール)",
            yaxis_showticklabels=False,
            height=450
        )
       
        st.plotly_chart(fig, use_container_width=True)
        st.success("✨ 実際の通過順データに基づくアニメーション再生が完了しました！")

else:
    st.warning("⚠️ まずはサイドバーから `keiba_master_data.csv` をアップロードしてください。")
