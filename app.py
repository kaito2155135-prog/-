import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="JRA-VAN 本格競馬展開シミュレーター", layout="wide")

st.title("🐎 JRA-VAN 本格コース＆展開シミュレーション")
st.write("競馬場のコース形状を再現し、脚質別の色分けと、下部での着順一覧表示に対応したシミュレーターです！")

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
   
    if st.button("🚀 レースアニメーションを開始！", type="primary"):
        frames = 50  # アニメーションのコマ数
       
        # 脚質ごとのカラーマップ
        color_map = {
            '逃げ': '#ff4b4b',   # 赤
            '先行': '#ffa500',   # オレンジ
            '差し': '#1f77b4',   # 青
            '追込': '#2ca02c',   # 緑
            '後方': '#7f7f7f',   # グレー
            '不明': '#bcbd22'
        }

        # コースの背景を描くための楕円座標（トラック）
        theta = np.linspace(0, 2 * np.pi, 200)
        track_x = 70 * np.cos(theta)
        track_y = 35 * np.sin(theta)

        sim_data = []
       
        for idx, row in df_race.iterrows():
            h_name = str(row['馬名'])
            h_num = int(row['馬番'])
            finish_rank = int(row['着順']) if row['着順'] > 0 else h_num
            ashishitsu = str(row['脚質']).strip()
            color = color_map.get(ashishitsu, '#1f77b4')
           
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
                # トラック上の位置 (angle)
                angle = prog * 2 * np.pi - np.pi/2
               
                # 順位に応じた内ラチ・外ラチのふくらみ
                rank_offset = (step_ranks[t] - 1) * 0.4
                rx = 70.0 + rank_offset
                ry = 35.0 + rank_offset
               
                x_pos = rx * np.cos(angle)
                y_pos = ry * np.sin(angle)
               
                sim_data.append({
                    'Step': t,
                    '馬名': h_name,
                    '馬番': h_num,
                    'X': x_pos,
                    'Y': y_pos,
                    '脚質': ashishitsu,
                    'カラー': color,
                    'テキスト': str(h_num)
                })
               
        df_sim = pd.DataFrame(sim_data)
       
        # 初期フレーム（Step 0）のデータ
        df_step0 = df_sim[df_sim['Step'] == 0]
       
        fig = go.Figure()
       
        # 1. コースの背景（ラチ線）を描画
        fig.add_trace(go.Scatter(
            x=track_x, y=track_y,
            mode='lines',
            line=dict(color='gray', width=3, dash='dash'),
            name='コース',
            hoverinfo='skip'
        ))
       
        # 2. 馬（マーカー）の描画
        fig.add_trace(go.Scatter(
            x=df_step0['X'],
            y=df_step0['Y'],
            mode='text+markers',
            marker=dict(size=26, color=df_step0['カラー'], line=dict(color='white', width=2)),
            text=df_step0['テキスト'],
            textfont=dict(color='white', size=12, family='Arial Black'),
            name='出走馬'
        ))
       
        # アニメーション用フレームの作成
        frames_list = []
        for step in range(frames):
            df_s = df_sim[df_sim['Step'] == step]
            frames_list.append(
                go.Frame(
                    data=[
                        go.Scatter(x=track_x, y=track_y, mode='lines'), # コースは固定
                        go.Scatter(
                            x=df_s['X'],
                            y=df_s['Y'],
                            mode='text+markers',
                            marker=dict(size=26, color=df_s['カラー'], line=dict(color='white', width=2)),
                            text=df_s['テキスト'],
                            textfont=dict(color='white', size=12, family='Arial Black')
                        )
                    ],
                    name=str(step)
                )
            )
           
        fig.frames = frames_list
       
        fig.update_layout(
            title=f"【{selected_race}】 周回・展開アニメーション（赤:逃げ / 橙:先行 / 青:差し / 緑:追込）",
            xaxis=dict(range=[-90, 90], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(range=[-55, 55], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            height=550,
            showlegend=False,
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
        )
       
        st.plotly_chart(fig, use_container_width=True)
       
        # 3. 下部に綺麗に着順・結果の表を表示する
        st.markdown("---")
        st.subheader("🏆 レース結果・通過順一覧")
       
        # 着順順にソートしてテーブル表示
        df_result = df_race.sort_values('着順').copy()
        df_result['着順'] = df_result['着順'].astype(int)
       
        st.dataframe(
            df_result[['着順', '馬番', '馬名', '脚質', '通過順1角', '通過順2角', '通過順3角', '通過順4角', '上がり3Fタイム', 'タイムS']],
            use_container_width=True,
            hide_index=True
        )
       
        st.success("✨ コースを明示し、脚質別に色分けしたアニメーションと、下部の着順テーブル表示に更新しました！")

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
