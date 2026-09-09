import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="本格競馬展開シミュレーター", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #ffffff; }
    h1, h2, h3 { color: #f1c40f !important; }
    .stAlert { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

st.title("🐎 本格競馬コース＆レース展開シミュレーター")
st.write("左上のスタートポケット、立体感のあるトラック形状、馬群の重なりを完全に解消した分散配置に対応しています。")

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
   
    if st.button("▶ シミュレーション開始 / 再生", type="primary"):
        frames = 70  # アニメーションのコマ数
       
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

        # 【ポケット付き本格コース形状】左上に引き込み線（ポケット）を持つレイアウト
        def get_track_coords(progress):
            # progress: 0.0 ~ 1.0
            if progress < 0.12:
                # 左上のポケット（スタート地点の引き込み線）
                t = progress / 0.12
                x = -42.0 - t * 15.0
                y = 15.0 + t * 8.0
            else:
                # メインのオーバルコース
                p_main = (progress - 0.12) / 0.88
                angle = p_main * 2 * np.pi
                rx = 48.0
                ry = 25.0
                x = rx * np.cos(angle - np.pi/2)
                y = ry * np.sin(angle - np.pi/2)
            return x, y

        # コース描画用のパスデータ
        path_t = np.linspace(0, 1.0, 400)
        track_pts_x, track_pts_y = [], []
        for pt in path_t:
            px, py = get_track_coords(pt)
            track_pts_x.append(px)
            track_pts_y.append(py)
           
        inner_x = [p * 0.85 for p in track_pts_x]
        inner_y = [p * 0.85 for p in track_pts_y]
        outer_x = [p * 1.15 for p in track_pts_x]
        outer_y = [p * 1.15 for p in track_pts_y]

        sim_data = []
       
        for idx, row in df_race.iterrows():
            h_name = str(row['馬名'])
            h_num = int(row['馬番'])
           
            if '枠番' in row and pd.notnull(row['枠番']):
                waku = int(row['枠番'])
            else:
                waku = ((h_num - 1) // 2) + 1
                if waku > 8: waku = 8
               
            color = get_waku_color(waku)
            text_color = "#000000" if waku == 1 else "#ffffff"
           
            finish_rank = int(row['着順']) if row['着順'] > 0 else h_num
           
            p1 = float(row['通過順1角']) if '通過順1角' in row and pd.notnull(row['通過順1角']) and row['通過順1角'] > 0 else float(row['頭数'])/2
            p2 = float(row['通過順2角']) if '通過順2角' in row and pd.notnull(row['通過順2角']) and row['通過順2角'] > 0 else p1
            p3 = float(row['通過順3角']) if '通過順3角' in row and pd.notnull(row['通過順3角']) and row['通過順3角'] > 0 else p2
            p4 = float(row['通過順4角']) if '通過順4角' in row and pd.notnull(row['通過順4角']) and row['通過順4角'] > 0 else p3
           
            progress_checkpoints = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            rank_checkpoints = [h_num, p1, p2, p3, p4, finish_rank]
           
            step_progresses = np.linspace(0.0, 1.0, frames)
            step_ranks = np.interp(step_progresses, progress_checkpoints, rank_checkpoints)
           
            # 馬ごとの重なりを防ぐため、馬番ごとに固有の「前後ズレ」と「横方向の複層ズレ」を完全に固定付与
            np.random.seed(h_num * 43)
            longitudinal_spread = ((h_num % 3) - 1) * 0.012  # 進行方向（前後）のバラケ
            lateral_spread = (((h_num - 1) // 3) * 1.4) - 1.2  # 横方向（外ラチ・内ラチの幅）のバラケ
           
            for t in range(frames):
                raw_prog = step_progresses[t]
                # 前後の微小ズレを反映
                prog = np.clip(raw_prog + longitudinal_spread, 0.0, 1.0)
               
                base_x, base_y = get_track_coords(prog)
               
                rank_val = step_ranks[t]
                position_offset = (rank_val - 1) * 0.5 + lateral_spread
               
                norm = np.hypot(base_x, base_y)
                if norm > 0:
                    nx, ny = base_x / norm, base_y / norm
                else:
                    nx, ny = 1.0, 0.0
                   
                x_pos = base_x + nx * position_offset
                y_pos = base_y + ny * position_offset
               
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
       
        # 1. 立体感を持たせたコース背景とポケット
        fig.add_trace(go.Scatter(
            x=track_pts_x, y=track_pts_y,
            mode='lines',
            line=dict(color='#144531', width=34),
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=outer_x, y=outer_y,
            mode='lines',
            line=dict(color='#ffffff', width=1.5, dash='dot'),
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=inner_x, y=inner_y,
            mode='lines',
            line=dict(color='#ffffff', width=1.5, dash='dot'),
            hoverinfo='skip'
        ))
       
        # スタート (S) とゴール (G) の位置マーカー
        sx, sy = get_track_coords(0.0)
        gx, gy = get_track_coords(0.97)
       
        fig.add_trace(go.Scatter(
            x=[sx, gx], y=[sy, gy],
            mode='text',
            text=['S', 'G'],
            textfont=dict(color=['#ffffff', '#f1c40f'], size=22, family='Arial Black'),
            hoverinfo='skip'
        ))
       
        # 2. 出走馬の丸アイコン（視認性の高いデザイン）
        fig.add_trace(go.Scatter(
            x=df_step0['X'],
            y=df_step0['Y'],
            mode='text+markers',
            marker=dict(
                size=28,
                color=df_step0['カラー'],
                line=dict(color='#ffffff', width=2)
            ),
            text=df_step0['テキスト'],
            textfont=dict(color=df_step0['文字色'], size=12, family='Arial Black')
        ))
       
        # アニメーションフレーム作成
        frames_list = []
        for step in range(frames):
            df_s = df_sim[df_sim['Step'] == step]
            frames_list.append(
                go.Frame(
                    data=[
                        go.Scatter(x=track_pts_x, y=track_pts_y),
                        go.Scatter(x=outer_x, y=outer_y),
                        go.Scatter(x=inner_x, y=inner_y),
                        go.Scatter(x=[sx, gx], y=[sy, gy], mode='text', text=['S', 'G']),
                        go.Scatter(
                            x=df_s['X'],
                            y=df_s['Y'],
                            mode='text+markers',
                            marker=dict(size=28, color=df_s['カラー'], line=dict(color='#ffffff', width=2)),
                            text=df_s['テキスト'],
                            textfont=dict(color=df_s['文字色'], size=12, family='Arial Black')
                        )
                    ],
                    name=str(step)
                )
            )
           
        fig.frames = frames_list
       
        fig.update_layout(
            title=dict(text=f"【{selected_race}】 レースシミュレーション", font=dict(color='#f1c40f', size=18)),
            xaxis=dict(range=[-70, 70], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(range=[-42, 42], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            height=600,
            showlegend=False,
            plot_bgcolor='#07160f',
            paper_bgcolor='#121212',
            updatemenus=[dict(
                type="buttons",
                x=0.5, y=-0.08, xanchor='center', yanchor='top',
                buttons=[
                    dict(label="▶ 再生",
                         method="animate",
                         args=[None, {"frame": {"duration": 140, "redraw": True}, "fromcurrent": True}]),
                    dict(label="⏸ 停止",
                         method="animate",
                         args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}])
                ]
            )]
        )
       
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
       
        # 3. 馬番一覧のアイコンバー
        st.markdown("---")
        waku_html = "<div style='display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px;'>"
        for _, r in df_race.sort_values('馬番').iterrows():
            hn = int(r['馬番'])
            wk = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else ((hn - 1)//2)+1
            bg_c = get_waku_color(wk)
            txt_c = "#000000" if wk == 1 else "#ffffff"
            waku_html += f"<div style='background-color: {bg_c}; color: {txt_c}; border: 1px solid #fff; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;'>{hn}</div>"
        waku_html += "</div>"
        st.markdown(waku_html, unsafe_allow_html=True)
       
        # 4. 下部にきれいな着順リストを表示
        st.subheader("🏆 レース結果・着順一覧")
       
        df_result = df_race.sort_values('着順').copy()
        df_result['着順'] = df_result['着順'].astype(int)
       
        possible_cols = ['着順', '馬番', '馬名', '脚質', '走破タイム', '通過順4角', '上がり3Fタイム']
        available_cols = [c for c in possible_cols if c in df_result.columns]
       
        st.dataframe(
            df_result[available_cols],
            use_container_width=True,
            hide_index=True
        )
       
        st.success("✨ 左上のポケット、S/G表示、馬同士が重ならない分散処理を反映した本格レイアウトに更新しました！")

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
