import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="競馬展開シミュレーター", layout="wide")

st.title("🐎 競馬リアルタイム展開シミュレーション")
st.write("各馬の脚質・前半3F・上がり3Fのデータをもとに、レース中の位置取りの変動を可視化します！")

# サイドバー設定
st.sidebar.header("⚙️ レース条件設定")
track_type = st.sidebar.selectbox("コース", ["東京 芝 2000m", "中山 芝 1800m", "阪神 ダ 1800m"])
total_distance = 2000 if "2000" in track_type else 1800

st.sidebar.markdown("---")
st.sidebar.subheader("📋 出走馬データ（CSVまたは手動調整）")

# サンプルデータの作成
if "df_horses" not in st.session_state:
    st.session_state.df_horses = pd.DataFrame({
        '馬番': [1, 2, 3, 4, 5, 6],
        '馬名': ['サイレンス級', 'イクイ級', 'ディープ級', 'ゴルシ級', 'ウオッカ級', 'テイオー級'],
        '脚質': ['逃げ', '先行', '差し', '追込', '先行', '差し'],
        '前半3F': [33.5, 34.5, 35.5, 37.0, 34.8, 35.2],
        '上がり3F': [35.0, 33.5, 33.0, 32.5, 34.0, 33.2],
    })

# データ編集テーブル
edited_df = st.data_editor(st.session_state.df_horses, num_rows="dynamic")

if st.button("🚀 レースシミュレーション開始！", type="primary"):
    # シミュレーションのフレーム計算（スタート〜4コーナー〜ゴール）
    frames = 50  # タイムステップ数
   
    # 各馬の移動軌跡データを生成
    sim_data = []
    np.random.seed(42)
   
    for idx, row in edited_df.iterrows():
        h_name = row['馬名']
        h_type = row['脚質']
       
        # 脚質に応じた位置取りのベースカーブ
        if h_type == '逃げ':
            # スタート直後一気に前へ、後半少しバテるか粘る
            positions = np.linspace(0, total_distance, frames) * 0.95 + np.sin(np.linspace(0, np.pi, frames)) * 50
            positions = np.clip(positions, 0, total_distance)
        elif h_type == '先行':
            positions = np.linspace(0, total_distance, frames) * 0.9 + np.sin(np.linspace(0, np.pi, frames)) * 80
            positions = np.clip(positions, 0, total_distance)
        elif h_type == '差し':
            # 中団から後半スパート
            positions = np.linspace(0, total_distance, frames) * 0.8 + (1 - np.cos(np.linspace(0, np.pi, frames))) * 150
            positions = np.clip(positions, 0, total_distance)
        else:  # 追込
            # 後方から一気
            positions = np.linspace(0, total_distance, frames) * 0.75 + (1 - np.cos(np.linspace(0, np.pi, frames))) * 220
            positions = np.clip(positions, 0, total_distance)
           
        # 若干のランダムノイズを足す
        positions += np.random.normal(0, 15, frames)
        positions = np.sort(positions) # 逆走防止
        positions[-1] = total_distance * (0.95 + np.random.uniform(0, 0.05)) # ゴール付近
       
        for t in range(frames):
            sim_data.append({
                'Step': t,
                '馬名': f"{row['馬番']}. {h_name} ({h_type})",
                '距離地点(m)': min(total_distance, max(0, positions[t])),
                '仮想Y軸': row['馬番'] * 10
            })

    df_sim = pd.DataFrame(sim_data)

    # Plotlyでアニメーション表示
    fig = px.scatter(
        df_sim,
        x='距離地点(m)',
        y='仮想Y軸',
        animation_frame='Step',
        color='馬名',
        range_x=[-50, total_distance + 100],
        range_y=[0, (len(edited_df) + 1) * 10],
        title=f"【{track_type}】 展開アニメーションシミュレーション"
    )
   
    fig.update_traces(marker=dict(size=20))
    fig.update_layout(
        xaxis_title="ゴールまでの距離 (スタート 0m → ゴール)",
        yaxis_showticklabels=False,
        height=400
    )

    # 画面上のアニメーション描画枠
    plot_placeholder = st.empty()
    plot_placeholder.plotly_chart(fig, use_container_width=True)
   
    st.success("🎉 シミュレーション完了！ご自身の穴馬の「差し・追込」がどこから届くか確認できましたか？")
