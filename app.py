import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import time
from datetime import datetime, timedelta
import random

# ページ設定
st.set_page_config(
    page_title="安心散歩ナビ",
    page_icon="🚶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'current_step' not in st.session_state:
    st.session_state.current_step = 'home'
if 'selected_destination' not in st.session_state:
    st.session_state.selected_destination = None
if 'selected_route' not in st.session_state:
    st.session_state.selected_route = None
if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {
        'mobility': 'normal',
        'walking_time': 30,
        'interests': [],
        'safety_level': 'high'
    }
if 'walking_start_time' not in st.session_state:
    st.session_state.walking_start_time = None
if 'walking_progress' not in st.session_state:
    st.session_state.walking_progress = 0

# データ定義
destinations = {
    'home': {
        'name': '家の周り',
        'distance': '0.5km',
        'time': '10-15分',
        'icon': '🏠',
        'description': '住宅街の安全な道のり'
    },
    'park': {
        'name': '近所の公園',
        'distance': '1.2km',
        'time': '20-30分',
        'icon': '🌳',
        'description': '緑豊かな癒やしの空間'
    },
    'shopping': {
        'name': 'ショッピングセンター',
        'distance': '2km',
        'time': '30-45分',
        'icon': '🛒',
        'description': '買い物も楽しめる便利なルート'
    },
    'station': {
        'name': '駅周辺',
        'distance': '1.8km',
        'time': '25-40分',
        'icon': '🚉',
        'description': '人通りが多く安心'
    },
    'riverside': {
        'name': '川沿い散歩道',
        'distance': '2.5km',
        'time': '40-60分',
        'icon': '🌊',
        'description': '自然を感じる爽やかなコース'
    },
    'temple': {
        'name': '神社・お寺',
        'distance': '1.5km',
        'time': '20-35分',
        'icon': '⛩️',
        'description': '静寂な空間でリフレッシュ'
    }
}

routes_data = {
    'home': [
        {
            'id': 'home-easy',
            'name': '家周り安全ルート',
            'description': '住宅街の静かな道を通る短めのコース',
            'distance': '500m',
            'time': '12分',
            'difficulty': '易',
            'safety_score': 95,
            'heatstroke_risk': 'low',
            'features': ['日陰多め', 'トイレ2箇所', '休憩ベンチ3箇所'],
            'highlights': ['季節の花壇', 'かわいい猫スポット', '静かな住宅街'],
            'toilets': ['コンビニ(100m)', '公園トイレ(300m)'],
            'rest_spots': ['ベンチ(150m)', 'バス停(250m)', '小公園(400m)']
        }
    ],
    'park': [
        {
            'id': 'park-scenic',
            'name': '公園散策ルート',
            'description': '緑豊かな公園を中心とした癒やしのコース',
            'distance': '1.2km',
            'time': '25分',
            'difficulty': '易',
            'safety_score': 92,
            'heatstroke_risk': 'low',
            'features': ['日陰豊富', 'トイレ3箇所', '休憩ベンチ5箇所'],
            'highlights': ['四季の花々', '池の鯉', '野鳥観察', '健康遊具'],
            'toilets': ['公園入口トイレ', '中央広場トイレ', '池の近くトイレ'],
            'rest_spots': ['展望ベンチ', '藤棚', '芝生広場', '池のそば', '健康遊具エリア']
        },
        {
            'id': 'park-exercise',
            'name': '公園運動ルート',
            'description': '軽い運動も取り入れた健康重視のコース',
            'distance': '1.5km',
            'time': '35分',
            'difficulty': '中',
            'safety_score': 88,
            'heatstroke_risk': 'medium',
            'features': ['運動施設', 'トイレ2箇所', '水飲み場'],
            'highlights': ['健康器具', 'ジョギングコース', '体操広場'],
            'toilets': ['スポーツ施設', '公園管理棟'],
            'rest_spots': ['健康器具エリア', '体操広場', '水飲み場']
        }
    ],
    'shopping': [
        {
            'id': 'shopping-safe',
            'name': 'ショッピング安全ルート',
            'description': '歩道が広く、休憩場所の多い安心コース',
            'distance': '2km',
            'time': '40分',
            'difficulty': '易',
            'safety_score': 90,
            'heatstroke_risk': 'low',
            'features': ['屋根付き通路', 'トイレ4箇所', '休憩スポット多数'],
            'highlights': ['商店街散策', 'カフェ休憩', '季節イベント'],
            'toilets': ['コンビニ3箇所', 'ショッピングセンター'],
            'rest_spots': ['商店街ベンチ', 'カフェ', 'ショッピングセンター休憩所']
        }
    ]
}

interests_list = [
    {'id': 'nature', 'name': '自然・花', 'icon': '🌸'},
    {'id': 'animals', 'name': '動物', 'icon': '🐱'},
    {'id': 'photography', 'name': '写真撮影', 'icon': '📸'},
    {'id': 'social', 'name': '人との交流', 'icon': '👥'},
    {'id': 'exercise', 'name': '軽い運動', 'icon': '🏃'},
    {'id': 'culture', 'name': '文化・歴史', 'icon': '🏛️'}
]

def get_weather_condition():
    """天候状況を取得（シミュレーション）"""
    conditions = [
        {'condition': '快適', 'temp': 22, 'humidity': 60, 'risk': 'low', 'color': '🟢'},
        {'condition': '注意', 'temp': 28, 'humidity': 75, 'risk': 'medium', 'color': '🟡'},
        {'condition': '警戒', 'temp': 32, 'humidity': 80, 'risk': 'high', 'color': '🔴'}
    ]
    return random.choice(conditions)

def create_map(route_data=None):
    """地図を作成"""
    # 東京駅を中心とした地図
    center_lat, center_lon = 35.6762, 139.6503
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    
    if route_data:
        # サンプルルートを追加
        route_coords = [
            [center_lat, center_lon],
            [center_lat + 0.01, center_lon + 0.01],
            [center_lat + 0.015, center_lon + 0.005],
            [center_lat + 0.02, center_lon - 0.01]
        ]
        
        folium.PolyLine(
            route_coords,
            color='blue',
            weight=4,
            opacity=0.8
        ).add_to(m)
        
        # トイレの位置をマーカーで表示
        for i, toilet in enumerate(route_data['toilets']):
            folium.Marker(
                [center_lat + 0.005 * (i + 1), center_lon + 0.005 * (i + 1)],
                popup=f"🚻 {toilet}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
        
        # 休憩スポットをマーカーで表示
        for i, spot in enumerate(route_data['rest_spots']):
            folium.Marker(
                [center_lat + 0.008 * (i + 1), center_lon - 0.005 * (i + 1)],
                popup=f"🪑 {spot}",
                icon=folium.Icon(color='green', icon='pause')
            ).add_to(m)
    
    return m

def main():
    st.title("🚶 安心散歩ナビ")
    st.markdown("---")
    
    # サイドバーに設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 天候情報
        weather = get_weather_condition()
        st.markdown(f"### 🌤️ 天候状況")
        st.markdown(f"{weather['color']} **{weather['condition']}** (気温: {weather['temp']}°C)")
        
        st.markdown("---")
        
        # ユーザー設定
        st.markdown("### 👤 あなたの設定")
        
        mobility = st.selectbox(
            "歩行レベル",
            ["ゆっくり歩き", "普通", "元気に歩く"],
            index=1
        )
        
        walking_time = st.slider(
            "希望歩行時間（分）",
            min_value=10,
            max_value=90,
            value=30,
            step=5
        )
        
        st.markdown("**興味のあること**")
        selected_interests = []
        for interest in interests_list:
            if st.checkbox(f"{interest['icon']} {interest['name']}", key=interest['id']):
                selected_interests.append(interest['id'])
        
        # セッション状態を更新
        st.session_state.user_preferences.update({
            'mobility': mobility,
            'walking_time': walking_time,
            'interests': selected_interests
        })
        
        st.markdown("---")
        
        # リセットボタン
        if st.button("🔄 最初から始める"):
            st.session_state.current_step = 'home'
            st.session_state.selected_destination = None
            st.session_state.selected_route = None
            st.rerun()
    
    # メインコンテンツ
    if st.session_state.current_step == 'home':
        show_destination_selection()
    elif st.session_state.current_step == 'route':
        show_route_selection()
    elif st.session_state.current_step == 'details':
        show_route_details()
    elif st.session_state.current_step == 'walking':
        show_walking_progress()

def show_destination_selection():
    st.header("🗺️ どちらに向かいますか？")
    
    st.markdown("今日の散歩先を選んでください。安全で楽しいルートをご提案します。")
    
    # 目的地を3列で表示
    cols = st.columns(3)
    
    for i, (dest_id, dest_info) in enumerate(destinations.items()):
        with cols[i % 3]:
            st.markdown(f"### {dest_info['icon']} {dest_info['name']}")
            st.markdown(f"**距離:** {dest_info['distance']}")
            st.markdown(f"**時間:** {dest_info['time']}")
            st.markdown(f"*{dest_info['description']}*")
            
            if st.button(f"選択", key=f"dest_{dest_id}"):
                st.session_state.selected_destination = dest_id
                st.session_state.current_step = 'route'
                st.rerun()
            
            st.markdown("---")

def show_route_selection():
    dest_id = st.session_state.selected_destination
    dest_info = destinations[dest_id]
    
    st.header(f"🛤️ {dest_info['icon']} {dest_info['name']} へのルート")
    
    if dest_id in routes_data:
        routes = routes_data[dest_id]
        
        for route in routes:
            with st.expander(f"📍 {route['name']} - {route['time']}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**説明:** {route['description']}")
                    st.markdown(f"**距離:** {route['distance']} | **時間:** {route['time']} | **難易度:** {route['difficulty']}")
                    
                    # 安全情報
                    risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
                    st.markdown(f"**安全度:** {route['safety_score']}% | **熱中症リスク:** {risk_color}")
                
                with col2:
                    if st.button(f"このルートを選択", key=f"route_{route['id']}"):
                        st.session_state.selected_route = route
                        st.session_state.current_step = 'details'
                        st.rerun()
                
                # 設備情報
                st.markdown("**🏢 設備・特徴:**")
                st.markdown(" • ".join(route['features']))
                
                # 見どころ
                st.markdown("**🌟 見どころ:**")
                st.markdown(" • ".join(route['highlights']))
                
                # トイレと休憩スポット
                col3, col4 = st.columns(2)
                with col3:
                    st.markdown("**🚻 トイレ:**")
                    for toilet in route['toilets']:
                        st.markdown(f"• {toilet}")
                
                with col4:
                    st.markdown("**🪑 休憩スポット:**")
                    for spot in route['rest_spots']:
                        st.markdown(f"• {spot}")
    else:
        st.warning("このルートの詳細情報はまだ準備中です。")

def show_route_details():
    route = st.session_state.selected_route
    
    st.header(f"📋 {route['name']} - 散歩準備")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ 持ち物チェック")
        items = [
            "水分補給用の飲み物",
            "帽子または日傘",
            "携帯電話",
            "小銭（緊急時用）",
            "薬（必要な場合）",
            "タオル",
            "マスク"
        ]
        
        checked_items = []
        for item in items:
            if st.checkbox(item, key=f"item_{item}"):
                checked_items.append(item)
        
        completion_rate = len(checked_items) / len(items) * 100
        st.progress(completion_rate / 100)
        st.markdown(f"準備完了率: {completion_rate:.0f}%")
    
    with col2:
        st.markdown("### 🛡️ 安全確認")
        weather = get_weather_condition()
        
        st.markdown(f"**🌡️ 現在の気温:** {weather['temp']}°C")
        st.markdown(f"**💧 湿度:** {weather['humidity']}%")
        st.markdown(f"**🛡️ 安全度:** {route['safety_score']}%")
        st.markdown(f"**⏰ 推定所要時間:** {route['time']}")
        
        # 安全レベルに応じたアドバイス
        if weather['risk'] == 'high':
            st.warning("⚠️ 熱中症リスクが高いです。十分な水分補給と休憩を心がけてください。")
        elif weather['risk'] == 'medium':
            st.info("ℹ️ 適度に暑いので、こまめな水分補給を忘れずに。")
        else:
            st.success("✅ 散歩に適した天候です！")
    
    # ルート地図
    st.markdown("### 🗺️ ルート地図")
    route_map = create_map(route)
    st_folium(route_map, width=700, height=400)
    
    # 散歩開始ボタン
    st.markdown("---")
    if st.button("🚶 散歩を開始する", type="primary"):
        st.session_state.walking_start_time = datetime.now()
        st.session_state.current_step = 'walking'
        st.rerun()

def show_walking_progress():
    route = st.session_state.selected_route
    start_time = st.session_state.walking_start_time
    
    st.header(f"🚶 散歩中: {route['name']}")
    
    # 経過時間を計算
    if start_time:
        elapsed = datetime.now() - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        # 推定時間（分）
        estimated_minutes = int(route['time'].split('分')[0])
        progress = min(elapsed_minutes / estimated_minutes, 1.0)
        
        st.markdown(f"**⏱️ 経過時間:** {elapsed_minutes:.1f}分 / {estimated_minutes}分")
        st.progress(progress)
        
        # 統計情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("歩数", f"{int(elapsed_minutes * 50)}")
        with col2:
            st.metric("消費カロリー", f"{int(elapsed_minutes * 3)}")
        with col3:
            st.metric("距離", f"{progress * float(route['distance'].replace('km', '').replace('m', '')):.1f}km")
        with col4:
            st.metric("進捗", f"{progress * 100:.0f}%")
    
    # 現在の状況
    st.markdown("### 📍 現在の状況")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("🚻 **次のトイレ:** 200m先のコンビニ")
        st.success("🪑 **次の休憩スポット:** 150m先のベンチ")
    
    with col2:
        st.markdown("🌟 **今の見どころ:**")
        st.markdown("左手に季節の花壇があります")
        st.markdown("右手に小さな公園が見えます")
    
    # アクション ボタン
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📸 写真を撮る"):
            st.success("📷 素敵な写真が撮れました！")
    
    with col2:
        if st.button("☕ 休憩する"):
            st.info("🪑 ゆっくり休んでください")
    
    with col3:
        if st.button("🏁 散歩を終了"):
            show_walking_summary()
            st.session_state.current_step = 'home'
            st.rerun()

def show_walking_summary():
    """散歩の総括を表示"""
    st.success("🎉 お疲れ様でした！素晴らしい散歩でした！")
    
    # 今日の記録をまとめて表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総歩数", "1,250歩")
    with col2:
        st.metric("総時間", "25分")
    with col3:
        st.metric("撮影枚数", "3枚")
    
    st.markdown("### 🌟 今日の良かった点")
    st.markdown("• 予定時間内で完歩できました")
    st.markdown("• 季節の花を楽しめました")
    st.markdown("• 適度な運動ができました")

if __name__ == "__main__":
    main()