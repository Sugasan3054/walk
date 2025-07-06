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
import math

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

# GPS関連のセッション状態
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
if 'generated_routes' not in st.session_state:
    st.session_state.generated_routes = []

# 🆕 GPS位置に基づくルート生成関数
def generate_routes_from_gps(current_lat, current_lon, preferences):
    """GPS位置に基づいて散歩ルートを生成"""
    routes = []
    walking_time = preferences.get('walking_time', 30)
    interests = preferences.get('interests', [])
    mobility = preferences.get('mobility', '普通')
    
    # 歩行速度を設定（km/h）
    speed_map = {
        'ゆっくり歩き': 3.0,
        '普通': 4.0,
        '元気に歩く': 5.0
    }
    speed = speed_map.get(mobility, 4.0)
    
    # 最大歩行距離を計算（km）
    max_distance = (walking_time / 60) * speed
    
    # 複数のルート候補を生成
    route_types = [
        {'name': '近所散策', 'distance_factor': 0.3, 'loop': True},
        {'name': '公園探索', 'distance_factor': 0.5, 'loop': True},
        {'name': '街歩き', 'distance_factor': 0.7, 'loop': False},
        {'name': '長距離散歩', 'distance_factor': 1.0, 'loop': True}
    ]
    
    for route_type in route_types:
        target_distance = max_distance * route_type['distance_factor']
        
        # ルート生成
        route_coords = generate_route_coordinates(
            current_lat, current_lon, target_distance, route_type['loop']
        )
        
        # ルート情報を作成
        route_info = create_route_info(
            route_type['name'], route_coords, target_distance, 
            walking_time * route_type['distance_factor'], interests
        )
        
        routes.append(route_info)
    
    return routes

def generate_route_coordinates(start_lat, start_lon, target_distance_km, is_loop=True):
    """指定された距離のルート座標を生成"""
    coords = [[start_lat, start_lon]]
    
    # 1km = 約0.009度 (緯度方向)
    # 1km = 約0.011度 (経度方向、東京近郊)
    lat_per_km = 0.009
    lon_per_km = 0.011
    
    current_lat, current_lon = start_lat, start_lon
    remaining_distance = target_distance_km
    
    if is_loop:
        # ループルートの場合
        num_points = max(4, int(target_distance_km * 2))  # 距離に応じてポイント数を決定
        angle_step = 2 * math.pi / num_points
        
        # 楕円状のルートを生成
        radius_lat = target_distance_km * lat_per_km / 4
        radius_lon = target_distance_km * lon_per_km / 4
        
        for i in range(1, num_points + 1):
            angle = i * angle_step
            # 少しランダムネスを追加して自然なルートに
            noise_lat = random.uniform(-0.001, 0.001)
            noise_lon = random.uniform(-0.001, 0.001)
            
            lat = start_lat + radius_lat * math.cos(angle) + noise_lat
            lon = start_lon + radius_lon * math.sin(angle) + noise_lon
            coords.append([lat, lon])
        
        # 最後にスタート地点に戻る
        coords.append([start_lat, start_lon])
    
    else:
        # 往復ルートの場合
        num_segments = max(3, int(target_distance_km))
        distance_per_segment = target_distance_km / (num_segments * 2)  # 往復考慮
        
        # 一方向に進む
        for i in range(num_segments):
            # ランダムな方向を選択
            angle = random.uniform(0, 2 * math.pi)
            
            lat_change = distance_per_segment * lat_per_km * math.cos(angle)
            lon_change = distance_per_segment * lon_per_km * math.sin(angle)
            
            current_lat += lat_change
            current_lon += lon_change
            coords.append([current_lat, current_lon])
        
        # 復路を追加（逆順）
        for i in range(len(coords) - 2, 0, -1):
            coords.append(coords[i])
    
    return coords

def create_route_info(name, coords, distance_km, time_minutes, interests):
    """ルート情報を作成"""
    # 興味に基づいて見どころを生成
    highlights = generate_highlights_by_interests(interests)
    
    # 安全度を距離と時間に基づいて計算
    safety_score = calculate_safety_score(distance_km, time_minutes)
    
    # 熱中症リスクを評価
    heatstroke_risk = evaluate_heatstroke_risk(time_minutes)
    
    # 施設情報を生成
    facilities = generate_facilities_along_route(coords)
    
    return {
        'id': f"gps_{name.lower().replace(' ', '_')}",
        'name': f"{name}（GPS生成）",
        'description': f"現在地から{distance_km:.1f}km、約{time_minutes:.0f}分の散歩コース",
        'distance': f"{distance_km:.1f}km",
        'time': f"{time_minutes:.0f}分",
        'difficulty': get_difficulty_level(distance_km, time_minutes),
        'safety_score': safety_score,
        'heatstroke_risk': heatstroke_risk,
        'coordinates': coords,
        'features': [
            f"GPS最適化ルート",
            f"推定歩数{int(distance_km * 1300)}歩",
            f"消費カロリー{int(time_minutes * 3)}kcal"
        ],
        'highlights': highlights,
        'toilets': facilities['toilets'],
        'rest_spots': facilities['rest_spots']
    }

def generate_highlights_by_interests(interests):
    """興味に基づいて見どころを生成"""
    interest_highlights = {
        'nature': ['季節の花々', '街路樹観察', '小さな庭園'],
        'animals': ['猫スポット', '犬の散歩道', '鳥の観察'],
        'photography': ['フォトスポット', '建物の美しい角度', '光と影の演出'],
        'social': ['地域の人との出会い', '商店街の賑わい', '公園での交流'],
        'exercise': ['坂道チャレンジ', '歩数稼ぎポイント', '健康遊具'],
        'culture': ['古い建物', '地域の歴史', '神社・お寺']
    }
    
    highlights = []
    for interest in interests:
        if interest in interest_highlights:
            highlights.extend(interest_highlights[interest])
    
    # 興味が選択されていない場合のデフォルト
    if not highlights:
        highlights = ['自然散策', '街並み観察', '新発見探し']
    
    return highlights[:4]  # 最大4つまで

def calculate_safety_score(distance_km, time_minutes):
    """安全度を計算"""
    base_score = 90
    
    # 距離による減点
    if distance_km > 3:
        base_score -= (distance_km - 3) * 5
    
    # 時間による減点
    if time_minutes > 60:
        base_score -= (time_minutes - 60) * 0.2
    
    # 最低点を確保
    return max(base_score, 70)

def evaluate_heatstroke_risk(time_minutes):
    """熱中症リスクを評価"""
    if time_minutes > 60:
        return 'high'
    elif time_minutes > 30:
        return 'medium'
    else:
        return 'low'

def get_difficulty_level(distance_km, time_minutes):
    """難易度レベルを決定"""
    if distance_km < 1.0 and time_minutes < 20:
        return '易'
    elif distance_km < 2.0 and time_minutes < 40:
        return '中'
    else:
        return '難'

def generate_facilities_along_route(coords):
    """ルート沿いの施設情報を生成"""
    toilets = []
    rest_spots = []
    
    # 座標の数に応じて施設を配置
    num_coords = len(coords)
    
    if num_coords > 5:
        toilets.extend(['コンビニ(500m地点)', '公園トイレ(1.2km地点)'])
        rest_spots.extend(['ベンチ(300m)', '公園休憩所(1.0km)', 'バス停(1.5km)'])
    elif num_coords > 3:
        toilets.append('コンビニ(中間地点)')
        rest_spots.extend(['ベンチ(400m)', '公園(800m)'])
    else:
        toilets.append('近隣コンビニ')
        rest_spots.append('休憩ベンチ')
    
    return {
        'toilets': toilets,
        'rest_spots': rest_spots
    }

def find_nearby_poi(lat, lon, interests):
    """興味に基づいて近くのPOIを検索"""
    # 実際の実装では地図APIを使用
    poi_types = {
        'nature': ['公園', '緑地', '花壇'],
        'animals': ['ペットショップ', '動物病院', '公園'],
        'photography': ['展望台', '歴史的建物', '美しい橋'],
        'social': ['商店街', 'カフェ', '集会所'],
        'exercise': ['健康遊具', '運動施設', 'ジョギングコース'],
        'culture': ['神社', '寺院', '歴史的建造物']
    }
    
    pois = []
    for interest in interests:
        if interest in poi_types:
            for poi_type in poi_types[interest]:
                # シミュレートされたPOI
                distance = random.randint(100, 800)
                direction = random.choice(['北', '南', '東', '西', '北東', '南西'])
                pois.append({
                    'name': poi_type,
                    'distance': distance,
                    'direction': direction,
                    'lat': lat + random.uniform(-0.005, 0.005),
                    'lon': lon + random.uniform(-0.005, 0.005)
                })
    
    return sorted(pois, key=lambda x: x['distance'])[:5]

def simulate_gps_location():
    """GPS位置をシミュレート"""
    # 日本の主要都市の座標
    cities = [
        {'name': '東京', 'lat': 35.6762, 'lon': 139.6503},
        {'name': '大阪', 'lat': 34.6937, 'lon': 135.5023},
        {'name': '京都', 'lat': 35.0116, 'lon': 135.7681},
        {'name': '川崎', 'lat': 35.5308, 'lon': 139.7029},
        {'name': '横浜', 'lat': 35.4437, 'lon': 139.6380}
    ]
    
    # ランダムに都市を選択
    city = random.choice(cities)
    
    # 選択された都市の周辺でランダムな位置を生成
    lat = city['lat'] + random.uniform(-0.02, 0.02)
    lon = city['lon'] + random.uniform(-0.02, 0.02)
    
    return {
        'lat': lat,
        'lon': lon,
        'accuracy': random.randint(5, 30),
        'timestamp': time.time(),
        'city': city['name']
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
    """近くの施設を検索"""
    facilities = [
        {'name': 'セブンイレブン', 'type': 'コンビニ', 'distance': 150, 'lat': lat+0.001, 'lon': lon+0.001},
        {'name': 'ファミリーマート', 'type': 'コンビニ', 'distance': 280, 'lat': lat-0.002, 'lon': lon+0.001},
        {'name': '公園トイレ', 'type': 'トイレ', 'distance': 230, 'lat': lat-0.001, 'lon': lon+0.002},
        {'name': '休憩ベンチ', 'type': '休憩所', 'distance': 80, 'lat': lat+0.0005, 'lon': lon-0.001},
        {'name': '自動販売機', 'type': '自販機', 'distance': 120, 'lat': lat+0.001, 'lon': lon+0.0005},
        {'name': 'バス停', 'type': '交通', 'distance': 320, 'lat': lat-0.002, 'lon': lon-0.001},
        {'name': '小さな公園', 'type': '公園', 'distance': 450, 'lat': lat+0.003, 'lon': lon-0.002},
    ]
    
    return sorted(facilities, key=lambda x: x['distance'])

def get_weather_condition():
    """天候状況を取得"""
    conditions = [
        {'condition': '快適', 'temp': 22, 'humidity': 60, 'risk': 'low', 'color': '🟢'},
        {'condition': '注意', 'temp': 28, 'humidity': 75, 'risk': 'medium', 'color': '🟡'},
        {'condition': '警戒', 'temp': 32, 'humidity': 80, 'risk': 'high', 'color': '🔴'}
    ]
    return random.choice(conditions)

def create_map(route_data=None):
    """地図を作成"""
    if st.session_state.current_location:
        center_lat = st.session_state.current_location['lat']
        center_lon = st.session_state.current_location['lon']
        zoom = 15
    else:
        center_lat, center_lon = 35.6762, 139.6503
        zoom = 12
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
    
    # 現在位置マーカー
    if st.session_state.current_location:
        folium.Marker(
            [st.session_state.current_location['lat'], st.session_state.current_location['lon']],
            popup=f"📍 現在位置<br>{st.session_state.current_location.get('city', '不明')}",
            icon=folium.Icon(color='red', icon='user')
        ).add_to(m)
    
    # 歩行経路を表示
    if len(st.session_state.walking_path) > 1:
        folium.PolyLine(
            st.session_state.walking_path,
            color='blue',
            weight=4,
            opacity=0.8,
            popup="実際の歩行経路"
        ).add_to(m)
    
    # 計画されたルートを表示
    if route_data and 'coordinates' in route_data:
        folium.PolyLine(
            route_data['coordinates'],
            color='green',
            weight=3,
            opacity=0.7,
            popup=f"計画ルート: {route_data['name']}"
        ).add_to(m)
        
        # ルート上のポイントにマーカーを追加
        for i, coord in enumerate(route_data['coordinates']):
            if i == 0:
                # スタート地点
                folium.Marker(
                    coord,
                    popup="🚩 スタート",
                    icon=folium.Icon(color='green', icon='play')
                ).add_to(m)
            elif i == len(route_data['coordinates']) - 1:
                # ゴール地点
                folium.Marker(
                    coord,
                    popup="🏁 ゴール",
                    icon=folium.Icon(color='red', icon='stop')
                ).add_to(m)
    
    # 近くの施設を表示
    if st.session_state.current_location:
        facilities = find_nearby_facilities(
            st.session_state.current_location['lat'],
            st.session_state.current_location['lon']
        )
        
        facility_colors = {
            'コンビニ': 'blue',
            'トイレ': 'green',
            '休憩所': 'orange',
            '自販機': 'purple',
            '交通': 'gray',
            '公園': 'darkgreen'
        }
        
        for facility in facilities[:6]:  # 最大6つまで表示
            color = facility_colors.get(facility['type'], 'blue')
            folium.Marker(
                [facility['lat'], facility['lon']],
                popup=f"{facility['name']}<br>{facility['type']}<br>{facility['distance']}m",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
    
    return m

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
                        `<div style="padding: 10px; border: 1px solid #4CAF50; border-radius: 5px; background-color: #f0f8f0;">
                            <h4 style="color: #4CAF50; margin: 0;">✅ 位置情報を取得しました</h4>
                            <p><strong>緯度:</strong> ${lat.toFixed(6)}</p>
                            <p><strong>経度:</strong> ${lon.toFixed(6)}</p>
                            <p><strong>精度:</strong> ${accuracy.toFixed(0)}m</p>
                            <p style="font-size: 12px; color: #666;">この位置情報を使用して最適なルートを生成します</p>
                        </div>`;
                    
                    // Streamlitに位置情報を送信（実際の実装では別の方法を使用）
                    console.log('位置情報取得完了:', lat, lon, accuracy);
                },
                function(error) {
                    let errorMessage = '';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage = '位置情報の使用が拒否されました';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage = '位置情報が利用できません';
                            break;
                        case error.TIMEOUT:
                            errorMessage = '位置情報の取得がタイムアウトしました';
                            break;
                        default:
                            errorMessage = '不明なエラーが発生しました';
                    }
                    
                    document.getElementById('location-info').innerHTML = 
                        `<div style="padding: 10px; border: 1px solid #f44336; border-radius: 5px; background-color: #fef0f0;">
                            <h4 style="color: #f44336; margin: 0;">❌ 位置情報の取得に失敗</h4>
                            <p>${errorMessage}</p>
                            <p style="font-size: 12px; color: #666;">デモ用位置を使用してお試しください</p>
                        </div>`;
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000
                }
            );
        } else {
            document.getElementById('location-info').innerHTML = 
                `<div style="padding: 10px; border: 1px solid #f44336; border-radius: 5px; background-color: #fef0f0;">
                    <h4 style="color: #f44336; margin: 0;">❌ 位置情報に対応していません</h4>
                    <p>このブラウザは位置情報機能に対応していません</p>
                </div>`;
        }
    }
    
    // 自動実行
    getLocation();
    </script>
    <div id="location-info" style="margin: 10px 0;">
        <div style="padding: 10px; border: 1px solid #2196F3; border-radius: 5px; background-color: #f0f8ff;">
            <h4 style="color: #2196F3; margin: 0;">📍 位置情報を取得中...</h4>
            <p>位置情報の使用を許可してください</p>
        </div>
    </div>
    """

interests_list = [
    {'id': 'nature', 'name': '自然・花', 'icon': '🌸'},
    {'id': 'animals', 'name': '動物', 'icon': '🐱'},
    {'id': 'photography', 'name': '写真撮影', 'icon': '📸'},
    {'id': 'social', 'name': '人との交流', 'icon': '👥'},
    {'id': 'exercise', 'name': '軽い運動', 'icon': '🏃'},
    {'id': 'culture', 'name': '文化・歴史', 'icon': '🏛️'}
]

def show_gps_route_generation():
    """GPS位置に基づくルート生成画面"""
    st.header("🎯 GPS位置に基づくルート生成")
    
    if not st.session_state.current_location:
        st.warning("📍 位置情報が取得されていません。設定から位置情報を有効にしてください。")
        return
    
    # 現在位置の表示
    st.success(f"📍 現在位置: {st.session_state.current_location.get('city', '不明な場所')}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🗺️ 現在位置周辺")
        current_map = create_map()
        st_folium(current_map, width=500, height=300)
    
    with col2:
        st.markdown("### ⚙️ ルート設定")
        
        # 歩行時間の設定
        walking_time = st.slider(
            "散歩時間（分）",
            min_value=15,
            max_value=120,
            value=st.session_state.user_preferences.get('walking_time', 30),
            step=15
        )
        
        # 歩行レベルの設定
        mobility = st.selectbox(
            "歩行レベル",
            ["ゆっくり歩き", "普通", "元気に歩く"],
            index=1
        )
        
        # 興味の設定
        selected_interests = []
        st.markdown("**興味のあること**")
        for interest in interests_list:
            if st.checkbox(f"{interest['icon']} {interest['name']}", key=f"route_{interest['id']}"):
                selected_interests.append(interest['id'])
        
        # 設定を更新
        preferences = {
            'walking_time': walking_time,
            'mobility': mobility,
            'interests': selected_interests
        }
        st.session_state.user_preferences.update(preferences)
    
    st.markdown("---")
    
    # ルート生成ボタン
    if st.button("🚀 最適なルートを生成", type="primary"):
        with st.spinner("🔄 GPS位置に基づいてルートを生成中..."):
            generated_routes = generate_routes_from_gps(
                st.session_state.current_location['lat'],
                st.session_state.current_location['lon'],
                preferences
            )
            st.session_state.generated_routes = generated_routes
            st.success("✅ ルートが生成されました！")
            time.sleep(1)
            st.rerun()
    
    # 生成されたルートの表示
    if st.session_state.generated_routes:
        st.markdown("### 🛤️ 生成されたルート")
        
        for i, route in enumerate(st.session_state.generated_routes):
            with st.expander(f"📍 {route['name']} - {route['time']}", expanded=i==0):
                route_col1, route_col2 = st.columns([3, 1])
                
                with route_col1:
                    st.markdown(f"**説明:** {route['description']}")
                    st.markdown(f"**距離:** {route['distance']} | **時間:** {route['time']} | **難易度:** {route['difficulty']}")
                    
                    risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
                    st.markdown(f"**安全度:** {route['safety_score']:.0f}% | **熱中症リスク:** {risk_color}")
                    
                    # 特徴の表示
                    st.markdown("**🏢 特徴:**")
                    for feature in route['features']:
                        st.markdown(f"• {feature}")
                    
                    # 見どころの表示
                    st.markdown("**🌟 見どころ:**")
                    for highlight in route['highlights']:
                        st.markdown(f"• {highlight}")
                
                with route_col2:
                    if st.button(f"このルートを選択", key=f"select_{route['id']}"):
                        st.session_state.selected_route = route
                        st.session_state.current_step = 'details'
                        st.success(f"✅ {route['name']}' を選択しました！")
                        st.rerun()
                    
                    # ルートのプレビュー地図
                    preview_map = create_map(route)
                    st_folium(preview_map, width=250, height=200)
                
                # 施設情報の表示
                if route.get('toilets') or route.get('rest_spots'):
                    st.markdown("**🏪 利用可能な施設:**")
                    facilities_col1, facilities_col2 = st.columns(2)
                    
                    with facilities_col1:
                        if route.get('toilets'):
                            st.markdown("**🚻 トイレ:**")
                            for toilet in route['toilets']:
                                st.markdown(f"• {toilet}")
                    
                    with facilities_col2:
                        if route.get('rest_spots'):
                            st.markdown("**🪑 休憩所:**")
                            for rest_spot in route['rest_spots']:
                                st.markdown(f"• {rest_spot}")

def show_home():
    """ホーム画面"""
    st.title("🚶 安心散歩ナビ")
    st.markdown("### あなたの安全で楽しい散歩をサポートします")
    
    # 天候情報の表示
    weather = get_weather_condition()
    weather_container = st.container()
    with weather_container:
        st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin: 10px 0;">
            <h4 style="color: #2c3e50; margin: 0;">🌤️ 今日の散歩状況</h4>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div>温度: {weather['temp']}°C</div>
                <div>湿度: {weather['humidity']}%</div>
                <div>状況: {weather['color']} {weather['condition']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # メインメニュー
    st.markdown("### 🎯 何をお探しですか？")
    
    menu_col1, menu_col2 = st.columns(2)
    
    with menu_col1:
        if st.button("🗺️ GPS位置からルート生成", use_container_width=True):
            st.session_state.current_step = 'gps_route'
            st.rerun()
        
        if st.button("📋 事前設定済みルート", use_container_width=True):
            st.session_state.current_step = 'preset_routes'
            st.rerun()
    
    with menu_col2:
        if st.button("⚙️ 設定・プロフィール", use_container_width=True):
            st.session_state.current_step = 'settings'
            st.rerun()
        
        if st.button("📊 歩行履歴", use_container_width=True):
            st.session_state.current_step = 'history'
            st.rerun()
    
    # 現在の状況表示
    if st.session_state.current_location:
        st.markdown("### 📍 現在の状況")
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            st.metric("現在地", st.session_state.current_location.get('city', '不明'))
        
        with status_col2:
            st.metric("総歩行距離", f"{st.session_state.total_distance:.1f}m")
        
        with status_col3:
            walking_time = 0
            if st.session_state.walking_start_time:
                walking_time = time.time() - st.session_state.walking_start_time
            st.metric("散歩時間", f"{walking_time/60:.0f}分")

def show_settings():
    """設定画面"""
    st.header("⚙️ 設定・プロフィール")
    
    # GPS設定セクション
    st.markdown("### 📍 GPS設定")
    
    gps_col1, gps_col2 = st.columns([2, 1])
    
    with gps_col1:
        st.markdown("**位置情報サービス**")
        
        # GPS有効化ボタン
        if st.button("📍 位置情報を取得", type="primary"):
            # 実際のGPS取得（デモ用にシミュレート）
            with st.spinner("位置情報を取得中..."):
                time.sleep(2)
                location = simulate_gps_location()
                st.session_state.current_location = location
                st.session_state.gps_enabled = True
                st.success(f"✅ 位置情報を取得しました: {location['city']}")
        
        # デモ用位置設定
        if st.button("🎯 デモ用位置を使用"):
            demo_location = {
                'lat': 35.6762,
                'lon': 139.6503,
                'accuracy': 10,
                'city': '東京（デモ）',
                'timestamp': time.time()
            }
            st.session_state.current_location = demo_location
            st.session_state.gps_enabled = True
            st.success("✅ デモ用位置を設定しました")
    
    with gps_col2:
        if st.session_state.current_location:
            st.success(f"📍 現在位置: {st.session_state.current_location.get('city', '不明')}")
            st.info(f"精度: {st.session_state.current_location.get('accuracy', 0)}m")
        else:
            st.warning("位置情報が設定されていません")
    
    # JavaScript GPS取得
    st.markdown("### 🌐 ブラウザGPS（実験的）")
    st.components.v1.html(get_current_location_js(), height=200)
    
    st.markdown("---")
    
    # ユーザー設定
    st.markdown("### 👤 ユーザー設定")
    
    prefs_col1, prefs_col2 = st.columns(2)
    
    with prefs_col1:
        mobility = st.selectbox(
            "歩行レベル",
            ["ゆっくり歩き", "普通", "元気に歩く"],
            index=1 if st.session_state.user_preferences.get('mobility') == 'normal' else 0
        )
        
        walking_time = st.slider(
            "希望散歩時間（分）",
            min_value=15,
            max_value=120,
            value=st.session_state.user_preferences.get('walking_time', 30),
            step=15
        )
        
        safety_level = st.selectbox(
            "安全重視度",
            ["低", "中", "高"],
            index=2
        )
    
    with prefs_col2:
        st.markdown("**興味のあること**")
        selected_interests = []
        for interest in interests_list:
            key = f"settings_{interest['id']}"
            if st.checkbox(f"{interest['icon']} {interest['name']}", key=key):
                selected_interests.append(interest['id'])
    
    # 設定保存
    if st.button("💾 設定を保存"):
        st.session_state.user_preferences.update({
            'mobility': 'slow' if mobility == 'ゆっくり歩き' else 'normal' if mobility == '普通' else 'fast',
            'walking_time': walking_time,
            'interests': selected_interests,
            'safety_level': safety_level.lower()
        })
        st.success("✅ 設定を保存しました")
    
    st.markdown("---")
    
    # データ管理
    st.markdown("### 📊 データ管理")
    
    data_col1, data_col2 = st.columns(2)
    
    with data_col1:
        if st.button("🗑️ 歩行履歴をクリア"):
            st.session_state.location_history = []
            st.session_state.walking_path = []
            st.session_state.total_distance = 0
            st.success("✅ 歩行履歴をクリアしました")
    
    with data_col2:
        if st.button("🔄 アプリをリセット"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ アプリをリセットしました")
            st.rerun()

def show_preset_routes():
    """事前設定済みルート画面"""
    st.header("📋 事前設定済みルート")
    
    # サンプルルートデータ
    preset_routes = [
        {
            'id': 'park_walk',
            'name': '近所の公園散歩',
            'description': '住宅街の公園を巡るのんびりコース',
            'distance': '1.2km',
            'time': '20分',
            'difficulty': '易',
            'safety_score': 95,
            'heatstroke_risk': 'low',
            'features': ['緑が多い', 'トイレあり', 'ベンチ多数'],
            'highlights': ['季節の花', '池の鯉', '遊具エリア'],
            'coordinates': [
                [35.6762, 139.6503],
                [35.6772, 139.6513],
                [35.6782, 139.6503],
                [35.6772, 139.6493],
                [35.6762, 139.6503]
            ]
        },
        {
            'id': 'shopping_street',
            'name': '商店街散策',
            'description': '地元の商店街を楽しむコース',
            'distance': '2.1km',
            'time': '35分',
            'difficulty': '中',
            'safety_score': 88,
            'heatstroke_risk': 'medium',
            'features': ['お店多数', 'カフェあり', '人通り多い'],
            'highlights': ['老舗店舗', 'パン屋', 'お惣菜店'],
            'coordinates': [
                [35.6762, 139.6503],
                [35.6742, 139.6523],
                [35.6722, 139.6543],
                [35.6762, 139.6503]
            ]
        },
        {
            'id': 'riverside_walk',
            'name': '川沿い散歩',
            'description': '川沿いの遊歩道を歩くコース',
            'distance': '3.5km',
            'time': '50分',
            'difficulty': '中',
            'safety_score': 92,
            'heatstroke_risk': 'medium',
            'features': ['景色良好', '涼しい', 'ジョギングコース'],
            'highlights': ['橋からの眺め', '水鳥観察', '桜並木'],
            'coordinates': [
                [35.6762, 139.6503],
                [35.6802, 139.6523],
                [35.6842, 139.6543],
                [35.6882, 139.6563],
                [35.6762, 139.6503]
            ]
        }
    ]
    
    # フィルター機能
    st.markdown("### 🔍 ルートを絞り込み")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        difficulty_filter = st.selectbox("難易度", ["全て", "易", "中", "難"])
    
    with filter_col2:
        time_filter = st.selectbox("時間", ["全て", "30分以下", "30-60分", "60分以上"])
    
    with filter_col3:
        safety_filter = st.selectbox("安全度", ["全て", "90%以上", "80%以上", "70%以上"])
    
    # ルート表示
    st.markdown("### 🛤️ 利用可能なルート")
    
    for route in preset_routes:
        # フィルタリング
        if difficulty_filter != "全て" and route['difficulty'] != difficulty_filter:
            continue
        
        with st.expander(f"📍 {route['name']} - {route['time']}", expanded=False):
            route_detail_col1, route_detail_col2 = st.columns([3, 1])
            
            with route_detail_col1:
                st.markdown(f"**説明:** {route['description']}")
                st.markdown(f"**距離:** {route['distance']} | **時間:** {route['time']} | **難易度:** {route['difficulty']}")
                
                risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
                st.markdown(f"**安全度:** {route['safety_score']}% | **熱中症リスク:** {risk_color}")
                
                st.markdown("**特徴:**")
                for feature in route['features']:
                    st.markdown(f"• {feature}")
                
                st.markdown("**見どころ:**")
                for highlight in route['highlights']:
                    st.markdown(f"• {highlight}")
            
            with route_detail_col2:
                if st.button(f"このルートを選択", key=f"preset_{route['id']}"):
                    st.session_state.selected_route = route
                    st.session_state.current_step = 'details'
                    st.success(f"✅ {route['name']} を選択しました！")
                    st.rerun()

def show_route_details():
    """ルート詳細画面"""
    if not st.session_state.selected_route:
        st.error("ルートが選択されていません。")
        return
    
    route = st.session_state.selected_route
    
    st.header(f"🗺️ {route['name']}")
    
    # ルート詳細情報
    detail_col1, detail_col2 = st.columns([2, 1])
    
    with detail_col1:
        st.markdown("### 📋 ルート詳細")
        
        # 基本情報
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.metric("距離", route['distance'])
        with info_col2:
            st.metric("時間", route['time'])
        with info_col3:
            st.metric("難易度", route['difficulty'])
        
        # 地図表示
        st.markdown("### 🗺️ ルートマップ")
        route_map = create_map(route)
        st_folium(route_map, width=600, height=400)
    
    with detail_col2:
        st.markdown("### 🎯 散歩開始")
        
        # 天候チェック
        weather = get_weather_condition()
        if weather['risk'] == 'high':
            st.warning("⚠️ 熱中症注意報が発令されています")
        elif weather['risk'] == 'medium':
            st.info("💧 水分補給をお忘れなく")
        else:
            st.success("✅ 散歩に適した天候です")
        
        # 散歩開始ボタン
        if st.button("🚶 散歩を開始", type="primary", use_container_width=True):
            st.session_state.walking_start_time = time.time()
            st.session_state.current_step = 'walking'
            st.success("✅ 散歩を開始しました！")
            st.rerun()
        
        # 他のルートを見る
        if st.button("🔄 他のルートを見る", use_container_width=True):
            st.session_state.selected_route = None
            st.session_state.current_step = 'home'
            st.rerun()
        
        # 安全情報
        st.markdown("### 🛡️ 安全情報")
        st.markdown(f"**安全度:** {route['safety_score']}%")
        
        risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
        st.markdown(f"**熱中症リスク:** {risk_color}")
        
        # 緊急連絡先
        st.markdown("### 📞 緊急連絡先")
        st.markdown("**救急:** 119")
        st.markdown("**警察:** 110")

def show_walking_mode():
    """散歩中画面"""
    if not st.session_state.selected_route:
        st.error("ルートが選択されていません。")
        return
    
    route = st.session_state.selected_route
    
    st.header(f"🚶 散歩中: {route['name']}")
    
    # 歩行状況
    if st.session_state.walking_start_time:
        elapsed_time = time.time() - st.session_state.walking_start_time
        progress = min(elapsed_time / (int(route['time'].replace('分', '')) * 60), 1.0)
        st.progress(progress)
        
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            st.metric("経過時間", f"{elapsed_time/60:.0f}分")
        with status_col2:
            st.metric("進捗", f"{progress*100:.0f}%")
        with status_col3:
            remaining_time = max(0, int(route['time'].replace('分', '')) - elapsed_time/60)
            st.metric("残り時間", f"{remaining_time:.0f}分")
    
    # 現在地マップ
    map_col1, map_col2 = st.columns([3, 1])
    
    with map_col1:
        st.markdown("### 🗺️ 現在地")
        walking_map = create_map(route)
        st_folium(walking_map, width=500, height=400)
    
    with map_col2:
        st.markdown("### 🎯 散歩管理")
        
        # 位置更新ボタン
        if st.button("📍 位置を更新", use_container_width=True):
            if st.session_state.current_location:
                location = st.session_state.current_location.copy()
                location['timestamp'] = time.time()
                st.session_state.location_history.append(location)
                st.session_state.walking_path.append([location['lat'], location['lon']])
                st.session_state.total_distance = calculate_walking_distance()
                st.success("✅ 位置を更新しました")
        
        # 休憩ボタン
        if st.button("☕ 休憩", use_container_width=True):
            st.info("😌 休憩中です。水分補給をお忘れなく！")
        
        # 散歩完了ボタン
        if st.button("🏁 散歩完了", type="primary", use_container_width=True):
            st.session_state.walking_start_time = None
            st.session_state.current_step = 'complete'
            st.success("✅ 散歩が完了しました！")
            st.rerun()
        
        # 緊急時
        st.markdown("### 🚨 緊急時")
        if st.button("🚨 緊急通報", use_container_width=True):
            st.error("🚨 緊急通報機能が有効化されました")
            st.markdown("**救急:** 119 | **警察:** 110")
    
    # 近くの施設情報
    if st.session_state.current_location:
        st.markdown("### 🏪 近くの施設")
        facilities = find_nearby_facilities(
            st.session_state.current_location['lat'],
            st.session_state.current_location['lon']
        )
        
        facility_cols = st.columns(3)
        for i, facility in enumerate(facilities[:6]):
            with facility_cols[i % 3]:
                st.markdown(f"**{facility['name']}**")
                st.markdown(f"{facility['type']} - {facility['distance']}m")

def show_completion():
    """散歩完了画面"""
    st.header("🎉 散歩完了！")
    st.balloons()
    
    # 完了統計
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    with stats_col1:
        st.metric("総距離", f"{st.session_state.total_distance:.0f}m")
    with stats_col2:
        if st.session_state.location_history:
            total_time = len(st.session_state.location_history) * 5  # 5分間隔と仮定
            st.metric("散歩時間", f"{total_time}分")
        else:
            st.metric("散歩時間", "記録なし")
    with stats_col3:
        calories = int(st.session_state.total_distance * 0.05)  # 大雑把な計算
        st.metric("消費カロリー", f"{calories}kcal")
    
    # 散歩の感想
    st.markdown("### 📝 散歩の感想")
    rating = st.slider("今日の散歩を評価してください", 1, 5, 5)
    comment = st.text_area("感想やメモ", placeholder="今日の散歩はいかがでしたか？")
    
    if st.button("💾 記録を保存"):
        # 散歩記録を保存（実際のアプリでは永続化）
        st.success("✅ 散歩記録を保存しました")
    
    # 次のアクション
    st.markdown("### 🎯 次のアクション")
    
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("🏠 ホームに戻る", use_container_width=True):
            st.session_state.current_step = 'home'
            st.rerun()
    
    with action_col2:
        if st.button("🚶 もう一度散歩", use_container_width=True):
            st.session_state.current_step = 'home'
            st.rerun()

def show_history():
    """歩行履歴画面"""
    st.header("📊 歩行履歴")
    
    # サンプルデータ
    history_data = [
        {"date": "2024-01-15", "route": "近所の公園散歩", "distance": 1200, "time": 20, "rating": 5},
        {"date": "2024-01-12", "route": "商店街散策", "distance": 2100, "time": 35, "rating": 4},
        {"date": "2024-01-10", "route": "川沿い散歩", "distance": 3500, "time": 50, "rating": 5},
        {"date": "2024-01-08", "route": "GPS生成ルート", "distance": 1800, "time": 30, "rating": 4},
        {"date": "2024-01-05", "route": "近所の公園散歩", "distance": 1200, "time": 18, "rating": 5}
    ]
    
    # 統計情報
    st.markdown("### 📈 統計情報")
    
    total_distance = sum(record['distance'] for record in history_data)
    total_time = sum(record['time'] for record in history_data)
    avg_rating = sum(record['rating'] for record in history_data) / len(history_data)
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("総散歩回数", len(history_data))
    with metric_col2:
        st.metric("総距離", f"{total_distance/1000:.1f}km")
    with metric_col3:
        st.metric("総時間", f"{total_time}分")
    with metric_col4:
        st.metric("平均評価", f"{avg_rating:.1f}⭐")
    
    # 履歴リスト
    st.markdown("### 📋 散歩履歴")
    
    for record in history_data:
        with st.expander(f"{record['date']} - {record['route']}"):
            record_col1, record_col2 = st.columns([2, 1])
            
            with record_col1:
                st.markdown(f"**距離:** {record['distance']}m")
                st.markdown(f"**時間:** {record['time']}分")
                st.markdown(f"**評価:** {'⭐' * record['rating']}")
            
            with record_col2:
                if st.button(f"再実行", key=f"repeat_{record['date']}"):
                    st.info("同じルートを再実行します")

# メイン関数
def main():
    """メイン関数"""
    
    # サイドバー
    with st.sidebar:
        st.markdown("### 🧭 ナビゲーション")
        
        # 現在のステップ表示
        steps = {
            'home': '🏠 ホーム',
            'gps_route': '🎯 GPS ルート',
            'preset_routes': '📋 事前設定',
            'settings': '⚙️ 設定',
            'details': '📝 詳細',
            'walking': '🚶 散歩中',
            'complete': '🎉 完了',
            'history': '📊 履歴'
        }
        
        current_step_name = steps.get(st.session_state.current_step, '不明')
        st.markdown(f"**現在:** {current_step_name}")
        
        st.markdown("---")
        
        # ナビゲーションメニュー
        if st.button("🏠 ホーム"):
            st.session_state.current_step = 'home'
            st.rerun()
        
        if st.button("🎯 GPS ルート"):
            st.session_state.current_step = 'gps_route'
            st.rerun()
        
        if st.button("📋 事前設定"):
            st.session_state.current_step = 'preset_routes'
            st.rerun()
        
        if st.button("⚙️ 設定"):
            st.session_state.current_step = 'settings'
            st.rerun()
        
        if st.button("📊 履歴"):
            st.session_state.current_step = 'history'
            st.rerun()
        
        st.markdown("---")
        
        # 現在の状態表示
        if st.session_state.current_location:
            st.success(f"📍 {st.session_state.current_location.get('city', '不明')}")
        else:
            st.warning("📍 位置情報なし")
        
        if st.session_state.selected_route:
            st.info(f"🛤️ {st.session_state.selected_route['name']}")
        
        st.markdown("---")
        
        # アプリ情報
        st.markdown("### ℹ️ アプリ情報")
        st.markdown("**バージョン:** 1.0.0")
        st.markdown("**作者:** 散歩愛好家")
        st.markdown("**サポート:** support@walkapp.com")
    
    # メインコンテンツ
    if st.session_state.current_step == 'home':
        show_home()
    elif st.session_state.current_step == 'gps_route':
        show_gps_route_generation()
    elif st.session_state.current_step == 'preset_routes':
        show_preset_routes()
    elif st.session_state.current_step == 'settings':
        show_settings()
    elif st.session_state.current_step == 'details':
        show_route_details()
    elif st.session_state.current_step == 'walking':
        show_walking_mode()
    elif st.session_state.current_step == 'complete':
        show_completion()
    elif st.session_state.current_step == 'history':
        show_history()

if __name__ == "__main__":
    main()