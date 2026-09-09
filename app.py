import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="JRA-VAN 本格競馬展開シミュレーター", layout="wide")

st.title("🐎 JRA-VAN 本格コース＆展開シミュレーター")
st.write("競馬場コース再現、JRA枠番カラー分け、馬の重なり防止ロジック、正しいカラム名（走破タイム）対応版です！")

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
   
    if st.button("🚀 本格レースアニメーションを開始！", type="primary"):
        frames = 60  # アニメーションのコマ数
       
        # JRA枠番カラーの定義 (1枠〜8枠)
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

        # 競馬場らしいトラック形状（直線の長いオーバル型）を生成する関数
        def get_field_coords(progress):
            angle = progress * 2 * np.pi
            rx = 55.0
            ry = 28.0
            x = rx * np.cos(angle - np.pi/2)
            y = ry * np.sin(angle - np.pi/2)
            return x, y

        # トラックの背景線を描くための座標データ
        track_theta = np.linspace(0, 2 * np.pi, 300)
        track_x = 55.0 * np.cos(track_theta - np.pi/2)
        track_y = 28.0 * np.sin(track_theta - np.pi/2)
       
        inner_x = 48.0 * np.cos(track_theta - np.pi/2)
        inner_y = 22.0 * np.sin(track_theta - np.pi/2)
        outer_x = 62.0 * np.cos(track_theta - np.pi/2)
        outer_y = 34.0 * np.sin(track_theta - np.pi/2)

        sim_data = []
       
        for idx, row in df_race.iterrows():
            h_name = str(row['馬名'])
            h_num = int(row['馬番'])
           
            # 枠番の取得
            if '枠番' in row and pd.notnull(row['枠番']):
                waku = int(row['枠番'])
            else:
                waku = ((h_num - 1) // 2) + 1
                if waku > 8: waku = 8
               
            color = get_waku_color(waku)
            text_color = "black" if waku == 1 else "white"
           
            finish_rank = int(row['着順']) if row['着順'] > 0 else h_num
           
            p1 = float(row['通過順1角']) if '通過順1角' in row and pd.notnull(row['通過順1角']) and row['通過順1角'] > 0 else float(row['頭数'])/2
            p2 = float(row['通過順2角']) if '通過順2角' in row and pd.notnull(row['通過順2角']) and row['通過順2角'] > 0 else p1
            p3 = float(row['通過順3角']) if '通過順3角' in row and pd.notnull(row['通過順3角']) and row['通過順3角'] > 0 else p2
            p4 = float(row['通過順4角']) if '通過順4角' in row and pd.notnull(row['通過順4角']) and row['通過順4角'] > 0 else p3
           
            progress_checkpoints = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            rank_checkpoints = [h_num, p1, p2, p3, p4, finish_rank]
           
            step_progresses = np.linspace(0.0, 1.0, frames)
            step_ranks = np.interp(step_progresses, progress_checkpoints, rank_checkpoints)
           
            # 馬同士が重ならないように、馬番ごとに固有の「バラケ係数」を付与
            np.random.seed(h_num * 99)
            spread_offset = ((h_num % 4) - 1.5) * 1.5 + np.random.uniform(-0.5, 0.5)
           
            for t in range(frames):
                prog = step_progresses[t]
                base_x, base_y = get_field_coords(prog)
               
                rank_val = step_ranks[t]
                lane_width = (rank_val - 1) * 0.8 + spread_offset
               
                angle_tangent = prog * 2 * np.pi - np.pi/2
                x_pos = base_x + lane_width * np.cos(angle_tangent + np.pi/2)
                y_pos = base_y + lane_width * np.sin(angle_tangent + np.pi/2)
               
                sim_data.append({
                    'Step': t,
                    '馬名': h_name,
                    '馬番': h_num,
                    '枠番': waku,
                    'X': x_pos,
                    'Y': y_pos,
                    'カラー': color,
                    '文字色': text_color,
                    'テキスト': f"{h_num}"
                })
               
        df_sim = pd.DataFrame(sim_data)
        df_step0 = df_sim[df_sim['Step'] == 0]
       
        fig = go.Figure()
       
        # 1. コース背景
        fig.add_trace(go.Scatter(
            x=track_x, y=track_y,
            mode='lines',
            line=dict(color='#2E7D32', width=22),
            name='コースベース',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=outer_x, y=outer_y,
            mode='lines',
            line=dict(color='white', width=2, dash='dot'),
            name='外ラチ',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=inner_x, y=inner_y,
            mode='lines',
            line=dict(color='white', width=2, dash='dot'),
            name='内ラチ',
            hoverinfo='skip'
        ))
       
        # 2. 出走馬マーカー
        fig.add_trace(go.Scatter(
            x=df_step0['X'],
            y=df_step0['Y'],
            mode='text+markers',
            marker=dict(
                size=28,
                color=df_step0['カラー'],
                line=dict(color='black', width=2)
            ),
            text=df_step0['テキスト'],
            textfont=dict(color=df_step0['文字色'], size=13, family='Arial Black'),
            name='出走馬'
        ))
       
        # アニメーションフレーム作成
        frames_list = []
        for step in range(frames):
            df_s = df_sim[df_sim['Step'] == step]
            frames_list.append(
                go.Frame(
                    data=[
                        go.Scatter(x=track_x, y=track_y),
                        go.Scatter(x=outer_x, y=outer_y),
                        go.Scatter(x=inner_x, y=inner_y),
                        go.Scatter(
                            x=df_s['X'],
                            y=df_s['Y'],
                            mode='text+markers',
                            marker=dict(
                                size=28,
                                color=df_s['カラー'],
                                line=dict(color='black', width=1.5)
                            ),
                            text=df_s['テキスト'],
                            textfont=dict(color=df_s['文字色'], size=13, family='Arial Black')
                        )
                    ],
                    name=str(step)
                )
            )
           
        fig.frames = frames_list
       
        fig.update_layout(
            title=f"【{selected_race}】 本格コース展開アニメーション（JRA枠番カラー対応・重なり防止）",
            xaxis=dict(range=[-75, 75], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(range=[-45, 45], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            height=600,
            showlegend=False,
            plot_bgcolor='#1b4d3e',
            paper_bgcolor='#f9f9f9',
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
       
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
       
        # 3. 下部に結果テーブルを表示（走破タイムに対応）
        st.markdown("---")
        st.subheader("🏆 レース結果・通過順一覧")
       
        df_result = df_race.sort_values('着順').copy()
        df_result['着順'] = df_result['着順'].astype(int)
       
        # 走破タイムが含まれるようにカラムを指定
        possible_cols = ['着順', '馬番', '馬名', '脚質', '走破タイム', '通過順1角', '通過順2角', '通過順3角', '通過順4角', '上がり3Fタイム']
        available_cols = [c for c in possible_cols if c in df_result.columns]
       
        st.dataframe(
            df_result[available_cols],
            use_container_width=True,
            hide_index=True
        )
       
        st.success("✨ 走破タイム表示への修正、枠番カラー分け、コース背景・重なり防止の適用が完了しました！")

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
