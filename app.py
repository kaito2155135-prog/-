import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="JRA-VAN 本格競馬コースシミュレーター", layout="wide")

st.title("🐎 JRA-VAN 本格コース＆展開シミュレーター")
st.write("直線の長いスタジアム型コース、JRA枠番カラー、馬群の重なり防止を完全にブラッシュアップしたプロ仕様です！")

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
        frames = 70  # アニメーションのコマ数
       
        # JRA枠番カラーの定義 (1枠〜8枠)
        def get_waku_color(wakuban):
            waku_colors = {
                1: "#ffffff",  # 白
                2: "#222222",  # 黒
                3: "#d9381e",  # 赤
                4: "#1f77b4",  # 青
                5: "#e5c100",  # 黄
                6: "#2ca02c",  # 緑
                7: "#ff7f0e",  # 桃
                8: "#9467bd"   # 橙
            }
            return waku_colors.get(int(wakuban) if pd.notnull(wakuban) else 1, "#1f77b4")

        # 【本格コース形状】角丸長方形（スタジアム型）の座標生成関数
        def get_track_coords(progress):
            # progress: 0.0 ~ 1.0
            # 競馬場は「向こう正面直線」「第3・4コーナー」「ホーム直線」「第1・2コーナー」で構成
            angle = progress * 2 * np.pi
           
            # スーパー楕円（スーパーカプセル型）に近い軌道を作ることで、直線とコーナーのメリハリを出す
            # X方向の幅、Y方向の幅
            w = 50.0
            h = 25.0
           
            # スムーズかつ角がある本格コースのパラメトリック方程式
            # コサイン・サインのべき乗で直線をフラットにする
            t = angle
            # 基本の楕円ベースに少し変形を加えて直線部分を作る
            x = w * np.cos(t)
            y = h * np.sin(t)
           
            # 直線をフラットにする補正（上下の直線区間を平行にする）
            if np.sin(t) > 0.3:
                y = h * 0.95
                x = w * np.sign(np.cos(t)) * (1.0 - abs(np.cos(t))*0.2)
            elif np.sin(t) < -0.3:
                y = -h * 0.95
                x = w * np.sign(np.cos(t)) * (1.0 - abs(np.cos(t))*0.2)
               
            return x, y

        # コース描画用のパスデータ
        path_t = np.linspace(0, 2 * np.pi, 400)
        track_pts_x = []
        track_pts_y = []
        for pt in path_t:
            px, py = get_track_coords(pt / (2*np.pi))
            track_pts_x.append(px)
            track_pts_y.append(py)
           
        # 内ラチ・外ラチのオフセット線
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
           
            # 馬同士が重ならないように、馬番ごとに固有のレーン幅＆縦方向の微小ズレを付与
            np.random.seed(h_num * 37)
            lane_spread = ((h_num - 1) % 4) * 1.2 + np.random.uniform(-0.3, 0.3)
           
            for t in range(frames):
                prog = step_progresses[t]
                base_x, base_y = get_track_coords(prog)
               
                # 順位に応じたイン・アウトのポジション（1着が最内、後ろの馬ほど外ラチ側へ）
                rank_val = step_ranks[t]
                position_offset = (rank_val - 1) * 0.5 + lane_spread
               
                # 重なり防止の放射状オフセット
                norm = np.hypot(base_x, base_y)
                if norm > 0:
                    nx = base_x / norm
                    ny = base_y / norm
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
       
        # 1. 本格的な競馬場コース背景（ターフ、ダート・芝のフェンスライン）
        fig.add_trace(go.Scatter(
            x=track_pts_x, y=track_pts_y,
            mode='lines',
            line=dict(color='#145A32', width=28),
            name='コース本線',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=outer_x, y=outer_y,
            mode='lines',
            line=dict(color='white', width=1.5, dash='dot'),
            name='外ラチ',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=inner_x, y=inner_y,
            mode='lines',
            line=dict(color='white', width=1.5, dash='dot'),
            name='内ラチ',
            hoverinfo='skip'
        ))
       
        # 2. 出走馬のマーカー（視認性を高めたデザイン）
        fig.add_trace(go.Scatter(
            x=df_step0['X'],
            y=df_step0['Y'],
            mode='text+markers',
            marker=dict(
                size=26,
                color=df_step0['カラー'],
                line=dict(color='#111111', width=2)
            ),
            text=df_step0['テキスト'],
            textfont=dict(color=df_step0['文字色'], size=12, family='Arial Black'),
            name='出走馬'
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
                        go.Scatter(
                            x=df_s['X'],
                            y=df_s['Y'],
                            mode='text+markers',
                            marker=dict(
                                size=26,
                                color=df_s['カラー'],
                                line=dict(color='#111111', width=2)
                            ),
                            text=df_s['テキスト'],
                            textfont=dict(color=df_s['文字色'], size=12, family='Arial Black')
                        )
                    ],
                    name=str(step)
                )
            )
           
        fig.frames = frames_list
       
        fig.update_layout(
            title=f"【{selected_race}】 本格スタジアムコース展開アニメーション",
            xaxis=dict(range=[-70, 70], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(range=[-40, 40], autorange=False, showgrid=False, zeroline=False, showticklabels=False),
            height=620,
            showlegend=False,
            plot_bgcolor='#0b3b24',  # 深みのある美しいターフグリーン
            paper_bgcolor='#f8f9fa',
            updatemenus=[dict(
                type="buttons",
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
       
        # 3. 下部に結果テーブルを表示
        st.markdown("---")
        st.subheader("🏆 レース結果・通過順一覧")
       
        df_result = df_race.sort_values('着順').copy()
        df_result['着順'] = df_result['着順'].astype(int)
       
        possible_cols = ['着順', '馬番', '馬名', '脚質', '走破タイム', '通過順1角', '通過順2角', '通過順3角', '通過順4角', '上がり3Fタイム']
        available_cols = [c for c in possible_cols if c in df_result.columns]
       
        st.dataframe(
            df_result[available_cols],
            use_container_width=True,
            hide_index=True
        )
       
        st.success("✨ 直線とコーナーのメリハリがある本格的なスタジアム型コースデザインへ完全に刷新しました！")

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
