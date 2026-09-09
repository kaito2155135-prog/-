import streamlit as st
import pandas as pd
import numpy as np
import os
import streamlit.components.v1 as components

st.set_page_config(page_title="本格競馬展開シミュレーター", layout="wide")

# スタイリングの適用
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
   
    # 未来予測用の設定コントロール
    st.markdown("### ⚙️ 展開・馬場コンディション設定（予想シミュレート）")
   
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_pace = st.radio(
            "ペース想定",
            ["S（スロー）", "M（ミドル）", "H（ハイ）"],
            index=1,
            horizontal=True,
            help="ペースを変更すると、先行馬や差し馬の有利不利が変わり着順や走破タイムが変動します。"
        )
    with col_p2:
        selected_bias = st.radio(
            "トラックバイアス（馬場・傾向）",
            ["フラット", "内有利", "外有利"],
            index=0,
            horizontal=True,
            help="馬場傾向を選択することで、バイアスに応じた補正が着順予測に反映されます。"
        )
   
    st.markdown("---")

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

    # 設定値に応じたシミュレーション・着順計算ロジック
    def simulate_race_results(df_r, pace, bias):
        res_df = df_r.copy()
       
        # 安全な乱数シードの指定
        seed_val = abs(len(res_df) + hash(pace) + hash(bias)) % (2**31)
        np.random.seed(seed_val)
       
        sim_scores = []
        for idx, r in res_df.iterrows():
            kyakushitsu = str(r.get('脚質', '差し'))
            wakuban = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else 1
           
            base_score = np.random.uniform(70, 95)
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
       
        base_time = 68.0 + (len(res_df) * 0.2)
        res_df['予測走破タイム'] = [round(base_time + (i * 0.25) + np.random.uniform(-0.1, 0.1), 1) for i in range(len(res_df))]
       
        return res_df

    df_simulated = simulate_race_results(df_race, selected_pace, selected_bias)

    # JavaScriptアニメーション付きコースボードのHTML生成
    def render_animated_course_board(df_s):
        # 馬のデータをJSへ渡すためにJSONに変換
        horses_data = []
        for idx, r in df_s.iterrows():
            hn = int(r['馬番'])
            wk = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else ((hn - 1)//2)+1
            bg_c = get_waku_color(wk)
            txt_c = "#000000" if wk == 1 else "#ffffff"
            # 予測着順が早いほどゴール（進捗1.0）に早く到達するようにスピードを調整
            rank = idx + 1
            speed = 1.0 + ((len(df_s) - rank) * 0.05) + (np.random.random() * 0.1)
            horses_data.append({
                "hn": hn,
                "name": str(r['馬名']),
                "bg": bg_c,
                "txt": txt_c,
                "speed": speed,
                "rank": rank
            })
           
        import json
        horses_json = json.dumps(horses_data)

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{
                background-color: #0b0b0b;
                margin: 0;
                font-family: sans-serif;
            }}
            .board-container {{
                background: linear-gradient(135deg, #111e17 0%, #08110c 100%);
                border: 2px solid #333333;
                border-radius: 12px;
                padding: 10px;
                position: relative;
                width: 100%;
                height: 420px;
                box-sizing: border-box;
                box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
                overflow: hidden;
            }}
            .horse-icon {{
                position: absolute;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: 2px solid #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 12px;
                box-shadow: 0 3px 6px rgba(0,0,0,0.6);
                transform: translate(-50%, -50%);
                z-index: 10;
                cursor: pointer;
            }}
            .controls {{
                text-align: center;
                margin-top: 10px;
            }}
            .start-btn {{
                background: linear-gradient(to bottom, #2ecc71, #27ae60);
                color: white;
                border: none;
                padding: 10px 24px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }}
            .start-btn:hover {{
                background: linear-gradient(to bottom, #27ae60, #1e8449);
            }}
        </style>
        </head>
        <body>
            <div class="board-container" id="board">
                <svg style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" viewBox="0 0 600 360" preserveAspectRatio="none">
                    <!-- コースの外枠・内パドック -->
                    <path id="trackPath" d="M 120,75 C 60,75 30,120 40,190 C 50,260 160,310 320,310 C 470,310 540,250 530,180 C 520,110 410,75 300,75 Z"
                          fill="none" stroke="#1e5638" stroke-width="36" stroke-linejoin="round" />
                    <path d="M 120,75 C 60,75 30,120 40,190 C 50,260 160,310 320,310 C 470,310 540,250 530,180 C 520,110 410,75 300,75 Z"
                          fill="none" stroke="#f1c40f" stroke-width="1.5" stroke-dasharray="6,4" stroke-linejoin="round" />
                </svg>

                <div style="position: absolute; left: 12%; top: 35%; background: rgba(0,0,0,0.8); border: 1px solid #fff; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 12px;">S (スタート)</div>
                <div style="position: absolute; left: 28%; top: 78%; background: rgba(0,0,0,0.8); border: 2px solid #f1c40f; color: #f1c40f; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 12px;">G (ゴール)</div>
               
                <div id="horses-wrapper"></div>
            </div>

            <div class="controls">
                <button class="start-btn" onclick="startRace()">🚀 レーススタート！</button>
            </div>

            <script>
                const horses = {horses_json};
                const wrapper = document.getElementById('horses-wrapper');
               
                // コース上の大まかな座標ポイント（楕円トラックに合わせた簡易パス補間用）
                // スタート地点(120, 75)から反時計回りに一周してゴール(300, 75)に向かう軌道
                function getTrackCoordinates(progress) {{
                    // progress: 0.0 (スタート) 〜 1.0 (ゴール)
                    // 1周のなめらかな楕円軌道上の座標を計算
                    let angle = Math.PI * 0.75 - (progress * Math.PI * 2.0);
                    let cx = 300, cy = 190;
                    let rx = 210, ry = 100;
                   
                    // 多少のレーンばらつき（内ラチ・外ラチの差）
                    let x = cx + Math.cos(angle) * rx;
                    let y = cy - Math.sin(angle) * ry;
                    return {{ x: x, y: y }};
                }}

                // 馬要素の初期配置（スタート位置）
                let horseElements = [];
                horses.forEach((h, index) => {{
                    let el = document.createElement('div');
                    el.className = 'horse-icon';
                    el.style.backgroundColor = h.bg;
                    el.style.color = h.txt;
                    el.innerText = h.hn;
                    el.title = `${{h.name}} (馬番:${{h.hn}} / 予想:${{h.rank}}着)`;
                   
                    // スタート位置に並べる（少しずつずらす）
                    let startOffset = (index * 4);
                    el.style.left = (120 + startOffset) + 'px';
                    el.style.top = (75 + (index * 2)) + 'px';
                   
                    wrapper.appendChild(el);
                    horseElements.push({{ element: el, data: h, progress: 0.0 }});
                }});

                let isRacing = false;

                function startRace() {{
                    if (isRacing) return;
                    isRacing = true;
                   
                    // 位置をリセット
                    horseElements.forEach((item, index) => {{
                        item.progress = 0.0;
                    }});

                    let startTime = null;
                    const duration = 5000; // 5秒で一周

                    function animate(timestamp) {{
                        if (!startTime) startTime = timestamp;
                        let elapsed = timestamp - startTime;
                        let rawProgress = Math.min(elapsed / duration, 1.0);

                        let allFinished = true;
                        horseElements.forEach((item) => {{
                            // 個別の馬のスピード係数を反映
                            let p = Math.min(rawProgress * item.data.speed, 1.0);
                            if (p < 1.0) allFinished = false;
                           
                            // 軌道座標を取得 (SVGの viewBox 600x360 に対する割合pxに変換)
                            let coords = getTrackCoordinates(p);
                           
                            // パーセンテージ換算 (SVG viewBox = 600 * 360)
                            let leftPercent = (coords.x / 600) * 100;
                            let topPercent = (coords.y / 360) * 100;
                           
                            item.element.style.left = leftPercent + '%';
                            item.element.style.top = topPercent + '%';
                        }});

                        if (!allFinished && rawProgress < 1.0) {{
                            requestAnimationFrame(animate);
                        }} else {{
                            isRacing = false;
                        }}
                    }}

                    requestAnimationFrame(animate);
                }}
            </script>
        </body>
        </html>
        """
        return html_code

    # 1. アニメーション付きコースビジュアル
    components.html(render_animated_course_board(df_simulated), height=480)
   
    # 2. 馬番ごとの丸アイコンバー
    waku_bar_html = "<div style='display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; background-color: #161616; padding: 10px; border-radius: 8px; border: 1px solid #333;'>"
    for _, r in df_simulated.sort_values('馬番').iterrows():
        hn = int(r['馬番'])
        wk = int(r['枠番']) if '枠番' in r and pd.notnull(r['枠番']) else ((hn - 1)//2)+1
        bg_c = get_waku_color(wk)
        txt_c = "#000000" if wk == 1 else "#ffffff"
        waku_bar_html += f"<div style='background-color: {bg_c}; color: {txt_c}; border: 1px solid #fff; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px;'>{hn}</div>"
    waku_bar_html += "</div>"
    components.html(waku_bar_html, height=70)
   
    # 3. 再シミュレートボタン
    if st.button("▶ 別の展開で再シミュレート"):
        st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

    # 4. 結果一覧リスト
    st.markdown("<br><h3>🏆 設定反映後の着順予測・シミュレーション結果</h3>", unsafe_allow_html=True)
   
    display_df = df_simulated[['着順予測', '馬番', '馬名', '脚質', '予測走破タイム']].copy()
    display_df.columns = ['予想着順', '馬番', '馬名', '脚質', '予測タイム(秒)']
   
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

else:
    st.error(f"⚠️ リポジトリ内に `{csv_filename}` が見つかりません。")
