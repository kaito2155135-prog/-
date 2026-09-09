import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="JRA-VAN リアル周回コース展開シミュレーター", layout="wide")

st.title("🐎 JRA-VAN 周回コース連動 展開シミュレーション")
st.write("実際のコーナー通過順（1角〜4角）と着順を反映した、周回コースアニメーションです！")

csv_filename = "keiba_master_data.csv"

if os.path.exists(csv_filename):
    try:
        df = pd.read_csv(csv_filename, encoding='utf-8')
    except:
        df = pd.read_csv(csv_filename, encoding='cp932')
       
    df['レースID'] = df['年'].astype(str) + "年" + df['月'].astype(str) + "月" + df['日'].astype(str) + " " + df['場所'] + " " + df['レース番号'].astype(str) + "R " + df['略レース名'].astype(str)
   
    race_list = df['レースID'].unique()
    selected_race = st.sidebar.selectbox("🎯 再現するレースを選択", race_list)
   
    df_race = df[df['レースID'] == selected_race].copy()
    row_info = df_race.iloc[0]
   
    st.markdown(f"### 🏟️ {selected_race}")
    st.info(f"**条件:** {row_info['芝・ダ']} {row_info['距離']}m | **馬場:** {row_info['馬場状態']} | **頭数:** {row_info['頭数']}頭")
   
    with st.expander("📋 このレースの出走馬データ"):
        st.dataframe(df_race[['馬番', '馬名', '脚質', '通過順1角', '通過順2角', '通過順3角', '通過順4角', '上がり3Fタイム', '着順']])
       
    if st.button("🚀 周回コースシミュレーションを開始！", type="primary"):
        frames = 50  # アニメーションのコマ数
       
        # 楕円形の周回コースの座標を生成する関数
        def get_track_coords(progress):
            angle = progress * 2 * np.pi
            rx = 40.0 # 横幅
            ry = 20.0 # 縦幅
            x = rx * np.cos(angle - np.pi/2)
            y = ry * np.sin(angle - np.pi/2)
            return x, y

        sim_data = []
       
        for idx, row in df_race.iterrows():
            h_name = str(row['馬名'])
            h_num = int(row['馬番'])
            finish_rank = int(row['着順']) if row['着順'] > 0 else h_num
           
            p1 = float(row['通過順1角']) if row['通過順1角'] > 0 else float(row['頭数'])/2
            p2 = float(row['通過順2角']) if row['通過順2角'] > 0 else p1
            p3 = float(row['通過順3角']) if row['通過順3角'] > 0 else p2
            p4 = float(row['通過順4角']) if row['通過順4角'] > 0 else p3
           
            progress_checkpoints = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            rank_checkpoints = [h_num, p1, p2, p3, p4, finish_rank]
           
            step_progresses = np.linspace(0.0, 1.0, frames)
            step_ranks = np.interp(step_progresses, progress_checkpoints, rank_checkpoints)
           
            for t in range(frames):
                prog = step_progresses[t]
                base_x, base_y = get_track_coords(prog)
               
                rank_offset = (step_ranks[t] - 1) * 0.8
                x_pos = base_x + (rank_offset * 0.5)
                y_pos = base_y + (rank_offset * 0.5)
               
                if t == frames - 1:
                    label_text = f"<b>{h_num}</b><br>({finish_rank}着: {h_name})"
                else:
                    label_text = f"<b>{h_num}</b>"
               
                sim_data.append({
                    'Step': t,
                    '馬名': h_name,
                    '馬番': h_num,
                    'X': x_pos,
                    'Y': y_pos,
                    'テキスト': label_text,
                    '脚質': row['脚質']
                })
               
        df_sim = pd.DataFrame(sim_data)
       
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=df_sim[df_sim['Step'] == 0]['X'],
                    y=df_sim[df_sim['Step'] == 0]['Y'],
                    mode='text+markers',
                    marker=dict(size=28, color='lightblue', line=dict(color='darkblue', width=2)),
                    text=df_sim[df_sim['Step'] == 0]['テキスト'],
                    textfont=dict(color='black', size=11, family='Arial Black')
                )
            ],
            layout=go.Layout(
                title=f"【{selected_race}】 周回コース展開アニメーション",
                xaxis=dict(range=[-60, 60], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(range=[-40, 40], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
                height=600,
                updatemenus=[dict(
                    type="buttons",
                    buttons=[
                        dict(label="▶ 再生",
                             method="animate",
                             args=[None, {"frame": {"duration": 150, "redraw": True}, "fromcurrent": True}]),
                        dict(label="⏸ 停止",
                             method="animate",
                             args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}])
                    ]
                )]
            ),
            frames=[
                go.Frame(
                    data=[
                        go.Scatter(
                            x=df_sim[df_sim['Step'] == step]['X'],
                            y=df_sim[df_sim['Step'] == step]['Y'],
                            mode='text+markers',
                            marker=dict(size=28, color='lightblue', line=dict(color='darkblue', width=2)),
                            text=df_sim[df_sim['Step'] == step]['テキスト'],
                            textfont=dict(color='black', size=11, family='Arial Black')
                        )
                    ],
                    name=str(step)
                )
                for step in range(frames)
            ]
        )
       
        st.plotly_chart(fig, use_container_width=True)
        st.success("✨ 周回コースでの展開再現＆ゴール時の着順表示が完了しました！")

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
