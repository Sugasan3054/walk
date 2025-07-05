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
st.success(f"✅ {route['name']}を選択しました！")
                        st.rerun()
                    
                    # ルート詳細の表示
                    if st.button(f"詳細を見る", key=f"detail_{route['id']}"):
                        st.markdown("#### 🚻 トイレ・休憩所")
                        for toilet in route['toilets']:
                            st.markdown(f"• 🚻 {toilet}")
                        for rest in route['rest_spots']:
                            st.markdown(f"• 🪑 {rest}")
                
                # ルート地図の表示
                route_map = create_map(route)
                st_folium(route_map, width=600, height=300, key=f"map_{route['id']}")

def show_route_details():
    """ルート詳細画面"""
    if not st.session_state.selected_route:
        st.error("ルートが選択されていません。")
        return
    
    route = st.session_state.selected_route
    
    st.header(f"📍 {route['name']}")
    st.markdown(f"**{route['description']}**")
    
    # 基本情報
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("距離", route['distance'])
    with col2:
        st.metric("時間", route['time'])
    with col3:
        st.metric("難易度", route['difficulty'])
    with col4:
        risk_color = "🟢" if route['heatstroke_risk'] == 'low' else "🟡" if route['heatstroke_risk'] == 'medium' else "🔴"
        st.markdown(f"**熱中症リスク**<br>{risk_color}", unsafe_allow_html=True)
    
    # 天候情報
    weather = get_weather_condition()
    st.markdown("### 🌤️ 現在の天候")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**{weather['color']} {weather['condition']}**")
        st.markdown(f"**気温:** {weather['temp']}°C")
        st.markdown(f"**湿度:** {weather['humidity']}%")
    with col2:
        if weather['risk'] == 'high':
            st.warning("⚠️ 熱中症のリスクが高いです。十分な水分補給と休憩を心がけてください。")
        elif weather['risk'] == 'medium':
            st.info("ℹ️ 適度な休憩と水分補給を心がけてください。")
        else:
            st.success("✅ 散歩に適した天候です。")
    
    # 地図表示
    st.markdown("### 🗺️ ルート地図")
    route_map = create_map(route)
    st_folium(route_map, width=700, height=400)
    
    # 詳細情報
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌟 見どころ")
        for highlight in route['highlights']:
            st.markdown(f"• {highlight}")
        
        st.markdown("### 🏢 特徴")
        for feature in route['features']:
            st.markdown(f"• {feature}")
    
    with col2:
        st.markdown("### 🚻 トイレ・休憩所")
        st.markdown("**トイレ:**")
        for toilet in route['toilets']:
            st.markdown(f"• {toilet}")
        
        st.markdown("**休憩所:**")
        for rest in route['rest_spots']:
            st.markdown(f"• {rest}")
    
    # 散歩開始ボタン
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔙 ルート選択に戻る", type="secondary"):
            st.session_state.current_step = 'gps_routes'
            st.rerun()
    
    with col2:
        if st.button("🚶 散歩を開始", type="primary"):
            st.session_state.walking_start_time = time.time()
            st.session_state.walking_progress = 0
            st.session_state.walking_path = []
            st.session_state.current_step = 'walking'
            st.success("🎉 散歩を開始しました！")
            st.rerun()
    
    with col3:
        if st.button("📱 別のルートを検索"):
            st.session_state.current_step = 'gps_routes'
            st.session_state.generated_routes = []
            st.rerun()

def show_walking_progress():
    """散歩進行画面"""
    if not st.session_state.selected_route:
        st.error("ルートが選択されていません。")
        return
    
    route = st.session_state.selected_route
    
    st.header(f"🚶 散歩中: {route['name']}")
    
    # 散歩時間の計算
    if st.session_state.walking_start_time:
        elapsed_time = time.time() - st.session_state.walking_start_time
        elapsed_minutes = int(elapsed_time / 60)
        elapsed_seconds = int(elapsed_time % 60)
        
        # 進捗バーの更新
        total_time = int(route['time'].replace('分', ''))
        progress = min(elapsed_time / (total_time * 60), 1.0)
        st.session_state.walking_progress = progress
        
        # 進捗表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("経過時間", f"{elapsed_minutes}:{elapsed_seconds:02d}")
        with col2:
            st.metric("進捗", f"{progress * 100:.1f}%")
        with col3:
            distance_walked = st.session_state.total_distance / 1000  # km
            st.metric("歩行距離", f"{distance_walked:.2f}km")
        
        # 進捗バー
        st.progress(progress, text=f"散歩進捗: {progress * 100:.1f}%")
    
    # 現在の位置情報とマップ
    st.markdown("### 🗺️ 現在位置")
    
    # GPS位置の更新シミュレーション
    if st.button("📍 位置を更新"):
        if st.session_state.current_location:
            # 前回の位置から少し移動したランダムな位置を生成
            new_location = {
                'lat': st.session_state.current_location['lat'] + random.uniform(-0.001, 0.001),
                'lon': st.session_state.current_location['lon'] + random.uniform(-0.001, 0.001),
                'accuracy': random.randint(5, 15),
                'timestamp': time.time()
            }
            
            # 歩行経路に追加
            st.session_state.walking_path.append([new_location['lat'], new_location['lon']])
            st.session_state.location_history.append(new_location)
            st.session_state.current_location = new_location
            
            # 歩行距離を更新
            st.session_state.total_distance = calculate_walking_distance()
            
            st.success("✅ 位置が更新されました！")
            st.rerun()
    
    # 自動更新の設定
    if st.checkbox("📡 自動位置更新（10秒間隔）", value=False):
        time.sleep(10)
        st.rerun()
    
    # 地図表示
    walking_map = create_map(route)
    st_folium(walking_map, width=700, height=400)
    
    # 近くの施設情報
    if st.session_state.current_location:
        st.markdown("### 🏢 近くの施設")
        facilities = find_nearby_facilities(
            st.session_state.current_location['lat'],
            st.session_state.current_location['lon']
        )
        
        for facility in facilities[:5]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{facility['name']}** ({facility['type']})")
            with col2:
                st.markdown(f"{facility['distance']}m")
    
    # 健康状態モニタリング
    st.markdown("### 💪 健康状態")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        steps = int(st.session_state.total_distance * 1.3)  # 1mあたり約1.3歩
        st.metric("推定歩数", f"{steps:,}歩")
    
    with col2:
        calories = int(elapsed_minutes * 3) if st.session_state.walking_start_time else 0
        st.metric("消費カロリー", f"{calories}kcal")
    
    with col3:
        avg_pace = (elapsed_minutes / (st.session_state.total_distance / 1000)) if st.session_state.total_distance > 0 else 0
        st.metric("平均ペース", f"{avg_pace:.1f}分/km")
    
    # 水分補給リマインダー
    if elapsed_minutes > 20 and elapsed_minutes % 20 == 0:
        st.warning("💧 水分補給の時間です！")
    
    # 散歩完了・一時停止ボタン
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⏸️ 散歩を一時停止"):
            st.session_state.current_step = 'details'
            st.info("散歩を一時停止しました。")
            st.rerun()
    
    with col2:
        if st.button("🏁 散歩を完了", type="primary"):
            st.session_state.current_step = 'summary'
            st.success("🎉 散歩が完了しました！")
            st.rerun()
    
    with col3:
        if st.button("🚨 緊急時サポート", type="secondary"):
            st.error("🚨 緊急時サポートが要請されました。")
            st.markdown("**緊急連絡先:** 110 (警察) / 119 (消防)")

def show_walking_summary():
    """散歩完了サマリー画面"""
    if not st.session_state.selected_route:
        st.error("ルートが選択されていません。")
        return
    
    route = st.session_state.selected_route
    
    st.header("🎉 散歩完了！")
    st.balloons()
    
    # 散歩の結果
    if st.session_state.walking_start_time:
        total_time = time.time() - st.session_state.walking_start_time
        total_minutes = int(total_time / 60)
        total_seconds = int(total_time % 60)
        
        st.success(f"素晴らしい散歩でした！ {route['name']}を完歩しました。")
        
        # 結果サマリー
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("散歩時間", f"{total_minutes}:{total_seconds:02d}")
        with col2:
            distance = st.session_state.total_distance / 1000
            st.metric("歩行距離", f"{distance:.2f}km")
        with col3:
            steps = int(st.session_state.total_distance * 1.3)
            st.metric("歩数", f"{steps:,}歩")
        with col4:
            calories = int(total_minutes * 3)
            st.metric("消費カロリー", f"{calories}kcal")
        
        # 歩行経路の地図
        st.markdown("### 🗺️ 歩行経路")
        summary_map = create_map(route)
        st_folium(summary_map, width=700, height=400)
        
        # 健康効果
        st.markdown("### 💪 健康効果")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**今日の成果:**")
            st.markdown(f"• 心拍数向上: 約{total_minutes * 2}回")
            st.markdown(f"• 血流改善: {distance:.1f}km分")
            st.markdown(f"• ストレス軽減: 散歩効果")
            st.markdown(f"• 日光浴: 約{total_minutes}分")
        
        with col2:
            st.markdown("**継続効果:**")
            st.markdown("• 心肺機能の向上")
            st.markdown("• 筋力の維持・向上")
            st.markdown("• 免疫力の向上")
            st.markdown("• 睡眠の質の改善")
        
        # 記録保存
        st.markdown("### 📊 記録")
        
        walking_record = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'route_name': route['name'],
            'duration': f"{total_minutes}:{total_seconds:02d}",
            'distance': f"{distance:.2f}km",
            'steps': f"{steps:,}歩",
            'calories': f"{calories}kcal",
            'weather': get_weather_condition()['condition']
        }
        
        st.json(walking_record)
        
        # 次回への提案
        st.markdown("### 🌟 次回の散歩提案")
        if distance < 1.0:
            st.info("💡 次回はもう少し長い距離にチャレンジしてみませんか？")
        elif distance > 3.0:
            st.info("💡 素晴らしい長距離散歩でした！定期的な運動を続けましょう。")
        else:
            st.info("💡 理想的な散歩距離です！この調子で続けましょう。")
    
    # アクションボタン
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 別の散歩を計画"):
            # セッション状態をリセット
            st.session_state.current_step = 'gps_routes'
            st.session_state.selected_route = None
            st.session_state.walking_start_time = None
            st.session_state.walking_progress = 0
            st.session_state.walking_path = []
            st.session_state.total_distance = 0
            st.session_state.generated_routes = []
            st.rerun()
    
    with col2:
        if st.button("🏠 ホームに戻る"):
            st.session_state.current_step = 'home'
            st.rerun()
    
    with col3:
        if st.button("📱 記録を共有"):
            st.info("📱 散歩記録の共有機能は今後実装予定です。")

def show_settings():
    """設定画面"""
    st.header("⚙️ 設定")
    
    # GPS設定
    st.markdown("### 📍 GPS・位置情報")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📍 現在位置を取得", type="primary"):
            with st.spinner("🔍 位置情報を取得中..."):
                # 実際の実装ではブラウザのGeolocation APIを使用
                simulated_location = simulate_gps_location()
                st.session_state.current_location = simulated_location
                st.session_state.gps_enabled = True
                st.success(f"✅ 位置情報を取得しました: {simulated_location.get('city', '不明')}")
        
        # GPS JavaScript（実際のブラウザ環境での使用）
        if st.checkbox("🔧 実際のGPS位置を使用（ブラウザ）", value=False):
            st.markdown(get_current_location_js(), unsafe_allow_html=True)
    
    with col2:
        if st.session_state.current_location:
            st.success("✅ GPS有効")
            st.markdown(f"**位置:** {st.session_state.current_location.get('city', '不明')}")
            st.markdown(f"**精度:** {st.session_state.current_location.get('accuracy', 'N/A')}m")
        else:
            st.error("❌ GPS無効")
    
    # デモ用位置設定
    st.markdown("### 🎯 デモ用位置設定")
    demo_cities = [
        {'name': '東京駅周辺', 'lat': 35.6762, 'lon': 139.6503},
        {'name': '渋谷駅周辺', 'lat': 35.6580, 'lon': 139.7016},
        {'name': '新宿駅周辺', 'lat': 35.6896, 'lon': 139.7006},
        {'name': '川崎駅周辺', 'lat': 35.5308, 'lon': 139.7029},
        {'name': '横浜駅周辺', 'lat': 35.4437, 'lon': 139.6380}
    ]
    
    selected_city = st.selectbox(
        "デモ用位置を選択",
        options=demo_cities,
        format_func=lambda x: x['name']
    )
    
    if st.button("📍 デモ位置を設定"):
        st.session_state.current_location = {
            'lat': selected_city['lat'],
            'lon': selected_city['lon'],
            'accuracy': 10,
            'timestamp': time.time(),
            'city': selected_city['name']
        }
        st.session_state.gps_enabled = True
        st.success(f"✅ デモ位置を設定しました: {selected_city['name']}")
    
    # ユーザー設定
    st.markdown("### 👤 ユーザー設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        mobility = st.selectbox(
            "歩行レベル",
            ["ゆっくり歩き", "普通", "元気に歩く"],
            index=1
        )
        
        walking_time = st.slider(
            "好みの散歩時間（分）",
            min_value=15,
            max_value=120,
            value=st.session_state.user_preferences.get('walking_time', 30),
            step=15
        )
        
        safety_level = st.selectbox(
            "安全レベル",
            ["低", "中", "高"],
            index=2
        )
    
    with col2:
        st.markdown("**興味のあること**")
        selected_interests = []
        for interest in interests_list:
            if st.checkbox(f"{interest['icon']} {interest['name']}", 
                         key=f"settings_{interest['id']}", 
                         value=interest['id'] in st.session_state.user_preferences.get('interests', [])):
                selected_interests.append(interest['id'])
    
    # 設定保存
    if st.button("💾 設定を保存"):
        st.session_state.user_preferences.update({
            'mobility': mobility,
            'walking_time': walking_time,
            'safety_level': safety_level,
            'interests': selected_interests
        })
        st.success("✅ 設定を保存しました！")
    
    # システム情報
    st.markdown("### 💻 システム情報")
    st.markdown(f"**現在のステップ:** {st.session_state.current_step}")
    st.markdown(f"**GPS状態:** {'有効' if st.session_state.gps_enabled else '無効'}")
    st.markdown(f"**位置履歴:** {len(st.session_state.location_history)}件")
    st.markdown(f"**歩行経路:** {len(st.session_state.walking_path)}ポイント")
    
    # データリセット
    st.markdown("### 🔄 データリセット")
    if st.button("⚠️ 全データをリセット", type="secondary"):
        # 確認
        if st.button("本当にリセットしますか？"):
            for key in list(st.session_state.keys()):
                if key != 'current_step':
                    del st.session_state[key]
            st.session_state.current_step = 'home'
            st.success("✅ データをリセットしました。")
            st.rerun()

def main():
    """メイン関数"""
    st.title("🚶 安心散歩ナビ")
    st.markdown("**GPS位置情報を活用した高齢者向け散歩支援アプリ**")
    
    # サイドバー
    with st.sidebar:
        st.markdown("### 📋 メニュー")
        
        # 現在の状態表示
        if st.session_state.current_location:
            st.success(f"📍 位置: {st.session_state.current_location.get('city', '不明')}")
        else:
            st.warning("📍 位置情報なし")
        
        # メニューボタン
        if st.button("🏠 ホーム"):
            st.session_state.current_step = 'home'
            st.rerun()
        
        if st.button("🎯 GPS散歩ルート"):
            st.session_state.current_step = 'gps_routes'
            st.rerun()
        
        if st.button("⚙️ 設定"):
            st.session_state.current_step = 'settings'
            st.rerun()
        
        # 散歩中の場合
        if st.session_state.current_step == 'walking':
            st.markdown("---")
            st.markdown("### 🚶 散歩中")
            if st.session_state.walking_start_time:
                elapsed = time.time() - st.session_state.walking_start_time
                st.markdown(f"**経過時間:** {int(elapsed/60)}:{int(elapsed%60):02d}")
            if st.button("🏁 散歩完了"):
                st.session_state.current_step = 'summary'
                st.rerun()
    
    # メインコンテンツ
    if st.session_state.current_step == 'home':
        show_home()
    elif st.session_state.current_step == 'gps_routes':
        show_gps_route_generation()
    elif st.session_state.current_step == 'details':
        show_route_details()
    elif st.session_state.current_step == 'walking':
        show_walking_progress()
    elif st.session_state.current_step == 'summary':
        show_walking_summary()
    elif st.session_state.current_step == 'settings':
        show_settings()

def show_home():
    """ホーム画面"""
    st.markdown("### 🌟 ようこそ！")
    st.markdown("安心散歩ナビは、GPS位置情報を活用してあなたに最適な散歩ルートを提案します。")
    
    # 現在位置の状態
    if st.session_state.current_location:
        st.success(f"📍 現在位置: {st.session_state.current_location.get('city', '不明')}")
        
        # 天候情報
        weather = get_weather_condition()
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"### 🌤️ 天候: {weather['color']} {weather['condition']}")
        with col2:
            st.markdown(f"気温: {weather['temp']}°C | 湿度: {weather['humidity']}%")
        
        # 散歩開始ボタン
        if st.button("🚀 散歩ルートを生成", type="primary", key="home_start"):
            st.session_state.current_step = 'gps_routes'
            st.rerun()
    else:
        st.warning("📍 位置情報が取得されていません。")
        st.markdown("散歩ルートを生成するには、まず設定画面で位置情報を有効にしてください。")
        
        if st.button("⚙️ 設定に移動", type="primary"):
            st.session_state.current_step = 'settings'
            st.rerun()
    
    # 機能説明
    st.markdown("### 🔧 主な機能")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🎯 GPS最適化**
        - 現在位置から最適なルートを生成
        - 個人の歩行レベルに合わせた提案
        - 興味に基づいた見どころ情報
        """)
    
    with col2:
        st.markdown("""
        **🛡️ 安全サポート**
        - 歩行中の位置追跡
        - 熱中症リスク評価
        - 近くの休憩所・トイレ情報
        """)
    
    with col3:
        st.markdown("""
        **📊 健康管理**
        - 歩数・距離・消費カロリー
        - 散歩記録の保存
        - 継続支援機能
        """)

if __name__ == "__main__":
    main()