import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import time
from datetime import datetime, timedelta
import random
import requests
import json
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# ページ設定
st.set_page_config(
    page_title="安心散歩ナビ",
    page_icon="🚶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化（元の内容 + GPS関連追加）
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

# 🆕 GPS関連のセッション状態を追加
if 'current_location' not in st.session_state:
    st.session_state.current_location = None
if 'walking_path' not in st.session_state:
    st.session_state.walking_path = []
if 'location_history' not in st.session_state:
    st.session_state.location_history = []
if 'gps_enabled' not in st.session_state:
    st.session_state.gps_enabled = False
if 'total_distance' not in st.session_state:
    st.session_state.total_distance = 0

# 元のデータ定義（変更なし）
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

# 🆕 GPS関連の新しい関数を追加
def get_current_location_js():
    """GPS位置取得用JavaScript"""
    return """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const accuracy = position.coords.accuracy;
                    
                    // 位置情報を表示
                    document.getElementById('location-info').innerHTML = 
                        `<p style="color: green;">✅ 位置情報を取得しました</p>
                         <p>緯度: ${lat.toFixed(6)}</p>
                         <p>経度: ${lon.toFixed(6)}</p>
                         <p>精度: ${accuracy.toFixed(0)}m</p>`;
                },
                function(error) {
                    document.getElementById('location-info').innerHTML = 
                        `<p style="color: red;">❌ 位置情報の取得に失敗: ${error.message}</p>`;
                }
            );
        } else {
            document.getElementById('location-info').innerHTML = 
                '<p style="color: red;">❌ このブラウザは位置情報に対応していません</p>';
        }
    }
    
    // 自動実行
    getLocation();
    </script>
    <div id="location-info">📍 位置情報を取得中...</div>
    """

def simulate_gps_location():
    """GPS位置をシミュレート（デモ用）"""
    # 東京駅周辺のランダムな位置
    base_lat, base_lon = 35.6762, 139.6503
    lat = base_lat + random.uniform(-0.01, 0.01)
    lon = base_lon + random.uniform(-0.01, 0.01)
    
    return {
        'lat': lat,
        'lon': lon,
        'accuracy': random.randint(5, 50),
        'timestamp': time.time()
    }

def calculate_walking_distance():
    """歩行距離を計算"""
    if len(st.session_state.location_history) < 2:
        return 0
    
    total_distance = 0
    for i in range(1, len(st.session_state.location_history)):
        prev_point = (
            st.session_state.location_history[i-1]['lat'],
            st.session_state.location_history[i-1]['lon']
        )
        curr_point = (
            st.session_state.location_history[i]['lat'],
            st.session_state.location_history[i]['lon']
        )
        total_distance += geodesic(prev_point, curr_point).meters
    
    return total_distance

def find_nearby_facilities(lat, lon, radius=500):
    """近くの施設を検索（シミュレート）"""
    # 実際の実装では OpenStreetMap API を使用
    facilities = [
        {'name': 'セブンイレブン', 'type': 'コンビニ', 'distance': 150, 'lat': lat+0.001, 'lon': lon+0.001},
        {'name': '公園トイレ', 'type': 'トイレ', 'distance': 230, 'lat': lat-0.001, 'lon': lon+0.002},
        {'name': 'ベンチ', 'type': '休憩所', 'distance': 80, 'lat': lat+0.0005, 'lon': lon-0.001},
        {'name': 'バス停', 'type': '交通', 'distance': 320, 'lat': lat-0.002, 'lon': lon-0.001},
    ]
    
    return sorted(facilities, key=lambda x: x['distance'])

def get_weather_condition():
    """天候状況を取得（元のコードと同じ）"""
    conditions = [
        {'condition': '快適', 'temp': 22, 'humidity': 60, 'risk': 'low', 'color': '🟢'},
        {'condition': '注意', 'temp': 28, 'humidity': 75, 'risk': 'medium', 'color': '🟡'},
        {'condition': '警戒', 'temp': 32, 'humidity': 80, 'risk': 'high', 'color': '🔴'}
    ]
    return random.choice(conditions)

def create_map(route_data=None):
    """地図を作成（GPS対応に改良）"""
    # 🆕 GPS位置がある場合はそれを中心に、なければデフォルト位置
    if st.session_state.current_location:
        center_lat = st.session_state.current_location['lat']
        center_lon = st.session_state.current_location['lon']
        zoom = 16
    else:
        center_lat, center_lon = 35.6762, 139.6503
        zoom = 14
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
    
    # 🆕 現在位置マーカーを追加
    if st.session_state.current_location:
        folium.Marker(
            [st.session_state.current_location['lat'], st.session_state.current_location['lon']],
            popup="📍 現在位置",
            icon=folium.Icon(color='red', icon='user')
        ).add_to(m)
    
    # 🆕 歩行経路を表示
    if len(st.session_state.walking_path) > 1:
        folium.PolyLine(
            st.session_state.walking_path,
            color='blue',
            weight=4,
            opacity=0.8,
            popup="歩行経路"
        ).add_to(m)
    
    # 元のルート表示（変更なし）
    if route_data:
        route_coords = [
            [center_lat, center_lon],
            [center_lat + 0.01, center_lon + 0.01],
            [center_lat + 0.015, center_lon + 0.005],
            [center_lat + 0.02, center_lon - 0.01]
        ]
        
        folium.PolyLine(
            route_coords,
            color='green',
            weight=3,
            opacity=0.6,
            popup="計画ルート"
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
    
    # 🆕 近くの施設を表示
    if st.session_state.current_location:
        facilities = find_nearby_facilities(
            st.session_state.current_location['lat'],
            st.session_state.current_location['lon']
        )
        
        for facility in facilities:
            color = 'blue' if facility['type'] == 'コンビニ' else 'green'
            folium.Marker(
                [facility['lat'], facility['lon']],
                popup=f"{facility['name']} ({facility['distance']}m)",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
    
    return m

def main():
    st.title("🚶 安心散歩ナビ")
    st.markdown("---")
    
    # 🆕 GPS許可確認を最初に追加
    if not st.session_state.gps_enabled:
        st.info("📱 より安全で正確な散歩のため、位置情報の使用を許可してください")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌐 実際のGPS位置を取得", type="primary"):
                st.session_state.gps_enabled = True
                st.components.v1.html(get_current_location_js(), height=200)
        
        with col2:
            if st.button("🎯 デモ用位置を使用"):
                st.session_state.gps_enabled = True
                st.session_state.current_location = simulate_gps_location()
                st.success("📍 デモ用位置を設定しました")
                st.rerun()
    
    # サイドバーに設定（GPS情報を追加）
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 🆕 GPS情報を追加
        if st.session_state.current_location:
            st.markdown("### 📍 現在位置")
            st.success("✅ GPS接続中")
            st.write(f"緯度: {st.session_state.current_location['lat']:.6f}")
            st.write(f"経度: {st.session_state.current_location['lon']:.6f}")
            
            # 🆕 位置更新ボタン
            if st.button("🔄 位置を更新"):
                st.session_state.current_location = simulate_gps_location()
                st.rerun()
        else:
            st.markdown("### 📍 現在位置")
            st.warning("❌ GPS未接続")
        
        st.markdown("---")
        
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
            st.session_state.walking_path = []
            st.session_state.location_history = []
            st.session_state.total_distance = 0
            st.rerun()
    
    # メインコンテンツ（元のコードと同じ構造）
    if st.session_state.current_step == 'home':
        show_destination_selection()
    elif st.session_state.current_step == 'route':
        show_route_selection()
    elif st.session_state.current_step == 'details':
        show_route_details()
    elif st.session_state.current_step == 'walking':
        show_walking_progress()  # 🆕 GPS対応版に変更

def show_destination_selection():
    """目的地選択画面（元のコードと同じ）"""
    st.header("🗺️ どちらに向かいますか？")
    
    st.markdown("今日の散歩先を選んでください。安全で楽しいルートをご提案します。")
    
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
    """ルート選択画面（元のコードと同じ）"""
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
                    
                    risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
                    st.markdown(f"**安全度:** {route['safety_score']}% | **熱中症リスク:** {risk_color}")
                
                with col2:
                    if st.button(f"このルートを選択", key=f"route_{route['id']}"):
                        st.session_state.selected_route = route
                        st.session_state.current_step = 'details'
                        st.rerun()
                
                st.markdown("**🏢 設備・特徴:**")
                st.markdown(" • ".join(route['features']))
                
                st.markdown("**🌟 見どころ:**")
                st.markdown(" • ".join(route['highlights']))
                
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
    """ルート詳細画面（元のコードと同じ）"""
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
        
        if weather['risk'] == 'high':
            st.warning("⚠️ 熱中症リスクが高いです。十分な水分補給と休憩を心がけてください。")
        elif weather['risk'] == 'medium':
            st.info("ℹ️ 適度に暑いので、こまめな水分補給を忘れずに。")
        else:
            st.success("✅ 散歩に適した天候です！")
    
    st.markdown("### 🗺️ ルート地図")
    route_map = create_map(route)
    st_folium(route_map, width=700, height=400)
    
    st.markdown("---")
    if st.button("🚶 散歩を開始する", type="primary"):
        st.session_state.walking_start_time = datetime.now()
        st.session_state.current_step = 'walking'
        st.rerun()

def show_walking_progress():
    """🆕 GPS対応の散歩進捗画面"""
    route = st.session_state.selected_route
    start_time = st.session_state.walking_start_time
    
    st.header(f"🚶 散歩中: {route['name']}")
    
    # 🆕 GPS位置追跡
    if st.session_state.current_location:
        # 位置履歴を更新
        current_time = time.time()
        location_data = {
            'lat': st.session_state.current_location['lat'],
            'lon': st.session_state.current_location['lon'],
            'timestamp': current_time
        }
        
        # 新しい位置を追加（重複を避ける）
        if not st.session_state.location_history or \
           st.session_state.location_history[-1]['lat'] != location_data['lat']:
            st.session_state.location_history.append(location_data)
            st.session_state.walking_path.append([location_data['lat'], location_data['lon']])
        
        # 距離計算
        st.session_state.total_distance = calculate_walking_distance()
    
    # 経過時間を計算
    if start_time:
        elapsed = datetime.now() - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        estimated_minutes = int(route['time'].split('分')[0])
        progress = min(elapsed_minutes / estimated_minutes, 1.0)
        
        st.markdown(f"**⏱️ 経過時間:** {elapsed_minutes:.1f}分 / {estimated_minutes}分")
        st.progress(progress)
        
        # 🆕 GPS対応統計情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.session_state.total_distance > 0:
                st.metric("歩行距離", f"{st.session_state.total_distance:.0f}m")
            else:
                st.metric("歩数", f"{int(elapsed_minutes * 50)}")
        
        with col2:
            st.metric("消費カロリー", f"{int(elapsed_minutes * 3)}")
        
        with col3:
            if st.session_state.total_distance > 0:
                speed = st.session_state.total_distance / max(elapsed_minutes, 1) * 60 / 1000
                st.metric("平均速度", f"{speed:.1f}km/h")
            else:
                st.metric("進捗", f"{progress * 100:.0f}%")
        
        with col4:
            st.metric("記録ポイント", len(st.session_state.location_history))
    
    # 🆕 GPS地図表示
    st.markdown("### 🗺️ リアルタイム地図")
    gps_map = create_map(route)
    st_folium(gps_map, width=700, height=400)
    
    # 🆕 近くの施設情報
    if st.session_state.current_location:
        st.markdown("### 🏪 近くの施設")
        facilities = find_nearby_facilities(
            st.session_state.current_location['lat'],
            st.session_state.current_location['lon']
        )
# 近くの施設を表示
        facility_cols = st.columns(len(facilities[:4]))
        for i, facility in enumerate(facilities[:4]):
            with facility_cols[i]:
                st.markdown(f"**{facility['name']}**")
                st.markdown(f"{facility['type']} • {facility['distance']}m")
    
    # 🆕 安全確認とアラート
    st.markdown("### 🛡️ 安全確認")
    safety_col1, safety_col2 = st.columns(2)
    
    with safety_col1:
        weather = get_weather_condition()
        if weather['risk'] == 'high':
            st.warning("🔥 熱中症警戒レベル！こまめな水分補給を忘れずに")
        elif weather['risk'] == 'medium':
            st.info("💧 適度に暑いです。水分補給をお忘れなく")
        else:
            st.success("✅ 快適な散歩日和です")
    
    with safety_col2:
        st.markdown("**緊急時の連絡先**")
        st.markdown("🚨 救急: 119")
        st.markdown("👮 警察: 110")
        st.markdown("🏥 医療相談: #8000")
    
    # 🆕 散歩記録とメモ
    st.markdown("### 📝 散歩メモ")
    
    # 気づきや発見を記録
    discovery_note = st.text_area(
        "今日の発見や気づきをメモしてください",
        placeholder="例: 桜のつぼみが膨らんできた、新しいお店を発見した、など...",
        height=100
    )
    
    # 体調チェック
    condition_col1, condition_col2 = st.columns(2)
    with condition_col1:
        energy_level = st.select_slider(
            "体調・元気度",
            options=["疲れた", "普通", "元気", "とても元気"],
            value="元気"
        )
    
    with condition_col2:
        satisfaction = st.select_slider(
            "散歩満足度",
            options=["😞", "😐", "😊", "😍"],
            value="😊"
        )
    
    # 🆕 位置情報更新ボタン
    st.markdown("---")
    update_col1, update_col2, update_col3 = st.columns(3)
    
    with update_col1:
        if st.button("🔄 現在位置を更新"):
            if st.session_state.gps_enabled:
                st.session_state.current_location = simulate_gps_location()
                st.success("📍 位置を更新しました")
                st.rerun()
            else:
                st.error("GPS機能を有効にしてください")
    
    with update_col2:
        if st.button("⏸️ 散歩を一時停止"):
            st.info("散歩を一時停止しました。休憩をお取りください。")
            time.sleep(2)
    
    with update_col3:
        if st.button("✅ 散歩を完了"):
            st.session_state.current_step = 'complete'
            st.rerun()
    
    # 🆕 自動位置更新（5秒間隔）
    if st.session_state.gps_enabled:
        time.sleep(5)
        st.session_state.current_location = simulate_gps_location()
        st.rerun()

def show_walking_complete():
    """🆕 散歩完了画面"""
    route = st.session_state.selected_route
    start_time = st.session_state.walking_start_time
    
    st.header("🎉 散歩完了！お疲れ様でした")
    
    # 散歩統計の表示
    if start_time:
        elapsed = datetime.now() - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        st.markdown("### 📊 今日の散歩記録")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総歩行時間", f"{elapsed_minutes:.1f}分")
        with col2:
            if st.session_state.total_distance > 0:
                st.metric("歩行距離", f"{st.session_state.total_distance:.0f}m")
            else:
                st.metric("推定歩数", f"{int(elapsed_minutes * 50)}歩")
        with col3:
            st.metric("消費カロリー", f"{int(elapsed_minutes * 3)}kcal")
    
    # 🆕 散歩ルートの振り返り
    st.markdown("### 🗺️ 今日の散歩ルート")
    complete_map = create_map(route)
    st_folium(complete_map, width=700, height=400)
    
    # 🆕 成果とバッジ
    st.markdown("### 🏆 獲得バッジ")
    badges = []
    
    if elapsed_minutes >= 30:
        badges.append("🥇 30分完歩")
    if st.session_state.total_distance >= 1000:
        badges.append("🚶 1km歩行")
    if len(st.session_state.location_history) >= 10:
        badges.append("📍 位置記録マスター")
    
    if badges:
        for badge in badges:
            st.success(badge)
    else:
        st.info("🌟 散歩完了バッジ")
    
    # 🆕 次回の提案
    st.markdown("### 💡 次回の散歩提案")
    
    next_suggestions = [
        "🌸 季節の花を見に行く散歩",
        "🌅 朝の爽やかな散歩",
        "🌆 夕方の涼しい散歩",
        "🏞️ 違うルートで新発見散歩"
    ]
    
    for suggestion in next_suggestions:
        st.markdown(f"• {suggestion}")
    
    # 🆕 散歩データの保存
    st.markdown("### 💾 記録を保存")
    
    walking_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'route': route['name'],
        'duration': elapsed_minutes,
        'distance': st.session_state.total_distance,
        'locations': len(st.session_state.location_history)
    }
    
    if st.button("📁 散歩記録をダウンロード"):
        # JSON形式で記録をダウンロード
        st.download_button(
            label="📋 記録をダウンロード",
            data=json.dumps(walking_data, indent=2, ensure_ascii=False),
            file_name=f"walking_record_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    
    # 🆕 アンケート
    st.markdown("### 📝 散歩の感想")
    
    feedback_col1, feedback_col2 = st.columns(2)
    
    with feedback_col1:
        route_rating = st.select_slider(
            "ルートの満足度",
            options=[1, 2, 3, 4, 5],
            value=4,
            format_func=lambda x: "⭐" * x
        )
    
    with feedback_col2:
        safety_rating = st.select_slider(
            "安全度の評価",
            options=[1, 2, 3, 4, 5],
            value=5,
            format_func=lambda x: "🛡️" * x
        )
    
    feedback_text = st.text_area(
        "改善点やご意見をお聞かせください",
        placeholder="例: トイレの案内がわかりやすかった、もう少し日陰が欲しい、など...",
        height=80
    )
    
    if st.button("📤 フィードバックを送信"):
        st.success("📨 フィードバックを送信しました。ありがとうございます！")
    
    st.markdown("---")
    
    # 🆕 アクションボタン
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔄 別のルートを探す"):
            st.session_state.current_step = 'home'
            st.session_state.selected_destination = None
            st.session_state.selected_route = None
            st.rerun()
    
    with action_col2:
        if st.button("📱 散歩記録を共有"):
            st.info("📲 SNS共有機能は開発中です")
    
    with action_col3:
        if st.button("🏠 ホームに戻る"):
            # セッションをクリア
            for key in ['walking_start_time', 'walking_progress', 'walking_path', 
                       'location_history', 'total_distance']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = 'home'
            st.rerun()

# 🆕 メイン関数の修正（完了画面の追加）
def main():
    st.title("🚶 安心散歩ナビ")
    st.markdown("---")
    
    # GPS許可確認を最初に追加
    if not st.session_state.gps_enabled:
        st.info("📱 より安全で正確な散歩のため、位置情報の使用を許可してください")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌐 実際のGPS位置を取得", type="primary"):
                st.session_state.gps_enabled = True
                st.components.v1.html(get_current_location_js(), height=200)
        
        with col2:
            if st.button("🎯 デモ用位置を使用"):
                st.session_state.gps_enabled = True
                st.session_state.current_location = simulate_gps_location()
                st.success("📍 デモ用位置を設定しました")
                st.rerun()
    
    # サイドバーに設定（GPS情報を追加）
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # GPS情報を追加
        if st.session_state.current_location:
            st.markdown("### 📍 現在位置")
            st.success("✅ GPS接続中")
            st.write(f"緯度: {st.session_state.current_location['lat']:.6f}")
            st.write(f"経度: {st.session_state.current_location['lon']:.6f}")
            
            # 位置更新ボタン
            if st.button("🔄 位置を更新"):
                st.session_state.current_location = simulate_gps_location()
                st.rerun()
        else:
            st.markdown("### 📍 現在位置")
            st.warning("❌ GPS未接続")
        
        st.markdown("---")
        
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
            st.session_state.walking_path = []
            st.session_state.location_history = []
            st.session_state.total_distance = 0
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
    elif st.session_state.current_step == 'complete':  # 🆕 完了画面を追加
        show_walking_complete()

# 🆕 アプリケーションの実行
if __name__ == "__main__":
    main()