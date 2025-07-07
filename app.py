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
if 'detailed_location' not in st.session_state:
    st.session_state.detailed_location = None
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
if 'gps_accuracy' not in st.session_state:
    st.session_state.gps_accuracy = None

# 🆕 高精度GPS位置情報システム
def get_detailed_location_info(lat, lon):
    """詳細な位置情報を取得"""
    try:
        # 実際のアプリケーションでは逆ジオコーディングAPIを使用
        # ここでは詳細な位置情報をシミュレート
        
        # 緯度経度から詳細な地域情報を生成
        location_info = analyze_coordinates(lat, lon)
        
        # 近隣の詳細情報を取得
        neighborhood_info = get_neighborhood_details(lat, lon)
        
        # 標高情報を取得
        elevation = get_elevation(lat, lon)
        
        return {
            'coordinates': {'lat': lat, 'lon': lon},
            'prefecture': location_info['prefecture'],
            'city': location_info['city'],
            'ward': location_info['ward'],
            'district': location_info['district'],
            'neighborhood': location_info['neighborhood'],
            'nearest_station': neighborhood_info['nearest_station'],
            'nearest_landmark': neighborhood_info['nearest_landmark'],
            'elevation': elevation,
            'area_type': location_info['area_type'],
            'population_density': location_info['population_density'],
            'safety_rating': calculate_area_safety_rating(lat, lon),
            'walkability_score': calculate_walkability_score(lat, lon),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        st.error(f"位置情報の詳細取得に失敗: {str(e)}")
        return None

def analyze_coordinates(lat, lon):
    """座標から詳細な地域情報を分析"""
    # 日本の主要都市の詳細座標データ
    city_zones = {
        # 東京23区
        (35.6580, 35.7320, 139.6910, 139.7910): {
            'prefecture': '東京都',
            'city': '新宿区',
            'area_type': '商業・オフィス街',
            'population_density': 'very_high'
        },
        (35.6390, 35.6890, 139.6910, 139.7910): {
            'prefecture': '東京都',
            'city': '渋谷区',
            'area_type': '商業・エンタメ街',
            'population_density': 'very_high'
        },
        (35.6490, 35.6990, 139.7210, 139.7910): {
            'prefecture': '東京都',
            'city': '中央区',
            'area_type': 'ビジネス街',
            'population_density': 'high'
        },
        
        # 川崎市
        (35.5100, 35.5700, 139.6700, 139.7400): {
            'prefecture': '神奈川県',
            'city': '川崎市川崎区',
            'area_type': '工業・住宅地',
            'population_density': 'high'
        },
        (35.5500, 35.6000, 139.6500, 139.7200): {
            'prefecture': '神奈川県',
            'city': '川崎市幸区',
            'area_type': '住宅・商業地',
            'population_density': 'high'
        },
        (35.5600, 35.6100, 139.6200, 139.6900): {
            'prefecture': '神奈川県',
            'city': '川崎市中原区',
            'area_type': '住宅地',
            'population_density': 'medium'
        },
        
        # 横浜市
        (35.4400, 35.4900, 139.6200, 139.6700): {
            'prefecture': '神奈川県',
            'city': '横浜市西区',
            'area_type': '商業・オフィス街',
            'population_density': 'high'
        },
        (35.4300, 35.4800, 139.6000, 139.6500): {
            'prefecture': '神奈川県',
            'city': '横浜市中区',
            'area_type': '観光・商業地',
            'population_density': 'medium'
        },
        
        # 大阪市
        (34.6700, 34.7200, 135.4900, 135.5400): {
            'prefecture': '大阪府',
            'city': '大阪市北区',
            'area_type': '商業・オフィス街',
            'population_density': 'very_high'
        },
        (34.6600, 34.7100, 135.4800, 135.5300): {
            'prefecture': '大阪府',
            'city': '大阪市中央区',
            'area_type': 'ビジネス街',
            'population_density': 'high'
        },
        
        # 京都市
        (35.0000, 35.0500, 135.7500, 135.8000): {
            'prefecture': '京都府',
            'city': '京都市下京区',
            'area_type': '観光・商業地',
            'population_density': 'medium'
        },
        (35.0100, 35.0600, 135.7600, 135.8100): {
            'prefecture': '京都府',
            'city': '京都市中京区',
            'area_type': '住宅・商業地',
            'population_density': 'medium'
        }
    }
    
    # 座標に基づいて最適な地域を特定
    for (min_lat, max_lat, min_lon, max_lon), info in city_zones.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            # より詳細な区分を計算
            ward = get_ward_from_coordinates(lat, lon, info['city'])
            district = get_district_from_coordinates(lat, lon)
            neighborhood = get_neighborhood_from_coordinates(lat, lon)
            
            return {
                'prefecture': info['prefecture'],
                'city': info['city'],
                'ward': ward,
                'district': district,
                'neighborhood': neighborhood,
                'area_type': info['area_type'],
                'population_density': info['population_density']
            }
    
    # デフォルト値（該当地域が見つからない場合）
    return {
        'prefecture': '不明',
        'city': f'座標地点 ({lat:.4f}, {lon:.4f})',
        'ward': '未特定',
        'district': '未特定',
        'neighborhood': '未特定',
        'area_type': '一般住宅地',
        'population_density': 'medium'
    }

def get_ward_from_coordinates(lat, lon, city):
    """座標から区・町を特定"""
    # 簡易的な区分け（実際のアプリではより詳細なデータを使用）
    lat_decimal = lat - int(lat)
    lon_decimal = lon - int(lon)
    
    if '川崎' in city:
        if lat_decimal < 0.55:
            return '川崎区'
        elif lat_decimal < 0.57:
            return '幸区'
        elif lat_decimal < 0.59:
            return '中原区'
        else:
            return '高津区'
    elif '横浜' in city:
        if lat_decimal < 0.45:
            return '西区'
        elif lat_decimal < 0.47:
            return '中区'
        else:
            return '港北区'
    elif '東京' in city or '新宿' in city or '渋谷' in city:
        if lon_decimal < 0.72:
            return '西部'
        elif lon_decimal < 0.75:
            return '中央部'
        else:
            return '東部'
    
    return '中央部'

def get_district_from_coordinates(lat, lon):
    """座標から地区を特定"""
    # 緯度経度の小数部を使用して地区を推定
    lat_decimal = (lat * 1000) % 100
    lon_decimal = (lon * 1000) % 100
    
    districts = ['一丁目', '二丁目', '三丁目', '四丁目', '五丁目']
    district_index = int((lat_decimal + lon_decimal) / 40) % len(districts)
    
    return districts[district_index]

def get_neighborhood_from_coordinates(lat, lon):
    """座標から近隣地域を特定"""
    # 座標に基づいて近隣の特徴的な地域名を生成
    lat_hash = int((lat * 10000) % 1000)
    lon_hash = int((lon * 10000) % 1000)
    
    prefixes = ['新', '本', '東', '西', '南', '北', '中']
    suffixes = ['町', '通り', '台', '丘', '坂', '橋']
    
    prefix = prefixes[lat_hash % len(prefixes)]
    suffix = suffixes[lon_hash % len(suffixes)]
    
    return f"{prefix}{suffix}"

def get_neighborhood_details(lat, lon):
    """近隣の詳細情報を取得"""
    # 最寄り駅を計算
    nearest_station = find_nearest_station(lat, lon)
    
    # 最寄りランドマークを計算
    nearest_landmark = find_nearest_landmark(lat, lon)
    
    return {
        'nearest_station': nearest_station,
        'nearest_landmark': nearest_landmark
    }

def find_nearest_station(lat, lon):
    """最寄り駅を検索"""
    # 主要駅のデータ
    stations = [
        {'name': '川崎駅', 'lat': 35.5308, 'lon': 139.7029},
        {'name': '新宿駅', 'lat': 35.6896, 'lon': 139.7006},
        {'name': '渋谷駅', 'lat': 35.6580, 'lon': 139.7016},
        {'name': '横浜駅', 'lat': 35.4657, 'lon': 139.6220},
        {'name': '品川駅', 'lat': 35.6289, 'lon': 139.7390},
        {'name': '東京駅', 'lat': 35.6812, 'lon': 139.7671},
        {'name': '大阪駅', 'lat': 34.7024, 'lon': 135.4959},
        {'name': '京都駅', 'lat': 34.9859, 'lon': 135.7581},
        {'name': '武蔵小杉駅', 'lat': 35.5777, 'lon': 139.6565},
        {'name': '溝の口駅', 'lat': 35.6017, 'lon': 139.6106}
    ]
    
    # 最寄り駅を計算
    min_distance = float('inf')
    nearest_station = None
    
    for station in stations:
        distance = geodesic((lat, lon), (station['lat'], station['lon'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_station = station['name']
    
    return {
        'name': nearest_station,
        'distance': f"{min_distance:.1f}km"
    }

def find_nearest_landmark(lat, lon):
    """最寄りランドマークを検索"""
    landmarks = [
        {'name': 'ラゾーナ川崎', 'lat': 35.5308, 'lon': 139.7029},
        {'name': '川崎大師', 'lat': 35.5344, 'lon': 139.7394},
        {'name': '多摩川', 'lat': 35.5500, 'lon': 139.6500},
        {'name': '等々力競技場', 'lat': 35.5647, 'lon': 139.6567},
        {'name': '新宿御苑', 'lat': 35.6851, 'lon': 139.7101},
        {'name': '代々木公園', 'lat': 35.6719, 'lon': 139.6968},
        {'name': '皇居', 'lat': 35.6852, 'lon': 139.7528},
        {'name': '東京タワー', 'lat': 35.6586, 'lon': 139.7454},
        {'name': '横浜中華街', 'lat': 35.4426, 'lon': 139.6496}
    ]
    
    # 最寄りランドマークを計算
    min_distance = float('inf')
    nearest_landmark = None
    
    for landmark in landmarks:
        distance = geodesic((lat, lon), (landmark['lat'], landmark['lon'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_landmark = landmark['name']
    
    return {
        'name': nearest_landmark,
        'distance': f"{min_distance:.1f}km"
    }

def get_elevation(lat, lon):
    """標高を取得"""
    # 簡易的な標高計算（実際のアプリでは標高APIを使用）
    base_elevation = 10  # 海抜10mをベースとする
    
    # 座標に基づいて標高を推定
    lat_factor = (lat - 35.0) * 100
    lon_factor = (lon - 139.0) * 50
    
    elevation = base_elevation + lat_factor + lon_factor
    return max(0, int(elevation))

def calculate_area_safety_rating(lat, lon):
    """エリアの安全度を計算"""
    # 人口密度、交通量、照明設備などを考慮した安全度計算
    base_score = 80
    
    # 座標に基づいて安全度を調整
    lat_decimal = lat - int(lat)
    lon_decimal = lon - int(lon)
    
    # 市街地中心部は安全度が高い
    if lat_decimal > 0.6 and lon_decimal > 0.7:
        base_score += 10
    
    # 工業地帯は安全度が低め
    if lat_decimal < 0.53:
        base_score -= 5
    
    return min(100, max(60, base_score))

def calculate_walkability_score(lat, lon):
    """歩きやすさスコアを計算"""
    base_score = 75
    
    # 座標に基づいて歩きやすさを調整
    lat_decimal = lat - int(lat)
    lon_decimal = lon - int(lon)
    
    # 住宅街は歩きやすい
    if 0.55 < lat_decimal < 0.65:
        base_score += 15
    
    # 商業地は歩きやすい
    if lon_decimal > 0.72:
        base_score += 10
    
    return min(100, max(50, base_score))

def get_precise_gps_location():
    """高精度GPS位置を取得"""
    # 実際の環境では、高精度GPSサービスを使用
    # デモ用に詳細な位置情報をシミュレート
    
    # より現実的な座標を生成
    base_locations = [
        # 川崎市の詳細エリア
        {'lat': 35.5308, 'lon': 139.7029, 'name': '川崎駅周辺'},
        {'lat': 35.5777, 'lon': 139.6565, 'name': '武蔵小杉'},
        {'lat': 35.5647, 'lon': 139.6567, 'name': '等々力'},
        {'lat': 35.5500, 'lon': 139.6800, 'name': '川崎区東部'},
        {'lat': 35.5600, 'lon': 139.6500, 'name': '中原区'},
        
        # 東京都の詳細エリア
        {'lat': 35.6896, 'lon': 139.7006, 'name': '新宿'},
        {'lat': 35.6580, 'lon': 139.7016, 'name': '渋谷'},
        {'lat': 35.6812, 'lon': 139.7671, 'name': '東京駅'},
        {'lat': 35.6289, 'lon': 139.7390, 'name': '品川'},
        
        # 横浜市の詳細エリア
        {'lat': 35.4657, 'lon': 139.6220, 'name': '横浜駅'},
        {'lat': 35.4426, 'lon': 139.6496, 'name': '中華街'},
    ]
    
    # ランダムに基準位置を選択
    base_location = random.choice(base_locations)
    
    # 基準位置から50-200m以内の詳細な位置を生成
    offset_lat = random.uniform(-0.002, 0.002)  # 約±200m
    offset_lon = random.uniform(-0.002, 0.002)  # 約±200m
    
    precise_lat = base_location['lat'] + offset_lat
    precise_lon = base_location['lon'] + offset_lon
    
    # GPS精度をシミュレート
    accuracy = random.randint(3, 12)  # 3-12m の精度
    
    return {
        'lat': precise_lat,
        'lon': precise_lon,
        'accuracy': accuracy,
        'timestamp': time.time(),
        'base_location': base_location['name'],
        'gps_quality': 'high' if accuracy < 8 else 'medium'
    }

def generate_detailed_routes_from_gps(detailed_location, preferences):
    """詳細位置情報に基づいて散歩ルートを生成"""
    routes = []
    current_lat = detailed_location['coordinates']['lat']
    current_lon = detailed_location['coordinates']['lon']
    
    walking_time = preferences.get('walking_time', 30)
    interests = preferences.get('interests', [])
    mobility = preferences.get('mobility', 'normal')
    
    # 歩行速度を設定（km/h）
    speed_map = {
        'slow': 3.0,
        'normal': 4.0,
        'fast': 5.0
    }
    speed = speed_map.get(mobility, 4.0)
    
    # 地域の特性を考慮したルート生成
    area_type = detailed_location['area_type']
    walkability = detailed_location['walkability_score']
    
    # エリアタイプに応じたルート種類
    if area_type == '住宅地':
        route_types = [
            {'name': '住宅街巡り', 'factor': 0.4, 'safety': 95},
            {'name': '近所の公園', 'factor': 0.3, 'safety': 90},
            {'name': '商店街探訪', 'factor': 0.6, 'safety': 85},
            {'name': '健康ウォーキング', 'factor': 0.8, 'safety': 88}
        ]
    elif area_type == '商業・オフィス街':
        route_types = [
            {'name': 'ビル街散策', 'factor': 0.5, 'safety': 90},
            {'name': '都市公園巡り', 'factor': 0.4, 'safety': 85},
            {'name': 'グルメ街歩き', 'factor': 0.7, 'safety': 80},
            {'name': '歴史散策', 'factor': 0.6, 'safety': 85}
        ]
    else:
        route_types = [
            {'name': '地域探索', 'factor': 0.5, 'safety': 80},
            {'name': '自然散策', 'factor': 0.4, 'safety': 90},
            {'name': '文化散歩', 'factor': 0.6, 'safety': 85},
            {'name': '健康コース', 'factor': 0.8, 'safety': 88}
        ]
    
    for route_type in route_types:
        # 最大歩行距離を計算
        max_distance = (walking_time / 60) * speed * route_type['factor']
        
        # 地域特性を考慮したルート座標生成
        route_coords = generate_area_aware_route(
            current_lat, current_lon, max_distance, area_type, detailed_location
        )
        
        # 詳細なルート情報を作成
        route_info = create_detailed_route_info(
            route_type['name'], route_coords, max_distance,
            walking_time * route_type['factor'], interests, 
            detailed_location, route_type['safety']
        )
        
        routes.append(route_info)
    
    return routes

def generate_area_aware_route(start_lat, start_lon, distance_km, area_type, location_info):
    """エリアの特性を考慮したルート生成"""
    coords = [[start_lat, start_lon]]
    
    # エリアタイプに応じたルート形状
    if area_type == '住宅地':
        # 住宅街は格子状の道路が多い
        return generate_grid_route(start_lat, start_lon, distance_km)
    elif area_type == '商業・オフィス街':
        # 商業地は放射状の道路が多い
        return generate_radial_route(start_lat, start_lon, distance_km)
    else:
        # 一般的な循環ルート
        return generate_circular_route(start_lat, start_lon, distance_km)

def generate_grid_route(start_lat, start_lon, distance_km):
    """格子状ルートの生成"""
    coords = [[start_lat, start_lon]]
    
    # 1km = 約0.009度 (緯度), 約0.011度 (経度)
    lat_per_km = 0.009
    lon_per_km = 0.011
    
    segment_distance = distance_km / 8  # 8セグメントに分割
    
    current_lat, current_lon = start_lat, start_lon
    
    # 格子状に移動
    directions = [
        (0, 1),   # 東
        (1, 0),   # 北
        (0, -1),  # 西
        (-1, 0),  # 南
        (0, 1),   # 東
        (1, 0),   # 北
        (0, -1),  # 西
        (-1, 0)   # 南（スタートに戻る）
    ]
    
    for i, (lat_dir, lon_dir) in enumerate(directions):
        # 少しランダムネスを追加
        noise = random.uniform(0.5, 1.5)
        
        lat_change = lat_dir * segment_distance * lat_per_km * noise
        lon_change = lon_dir * segment_distance * lon_per_km * noise
        
        current_lat += lat_change
        current_lon += lon_change
        coords.append([current_lat, current_lon])
    
    return coords

def generate_radial_route(start_lat, start_lon, distance_km):
    """放射状ルートの生成"""
    coords = [[start_lat, start_lon]]
    
    lat_per_km = 0.009
    lon_per_km = 0.011
    
    num_spokes = 6  # 6方向に放射
    spoke_distance = distance_km / (num_spokes * 2)  # 往復考慮
    
    current_lat, current_lon = start_lat, start_lon
    
    for i in range(num_spokes):
        angle = (i * 2 * math.pi) / num_spokes
        
        # 外向きに移動
        lat_change = spoke_distance * lat_per_km * math.cos(angle)
        lon_change = spoke_distance * lon_per_km * math.sin(angle)
        
        current_lat += lat_change
        current_lon += lon_change
        coords.append([current_lat, current_lon])
        
        # 中心に戻る
        coords.append([start_lat, start_lon])
        current_lat, current_lon = start_lat, start_lon
    
    return coords

def generate_circular_route(start_lat, start_lon, distance_km):
    """円形ルートの生成"""
    coords = [[start_lat, start_lon]]
    
    lat_per_km = 0.009
    lon_per_km = 0.011
    
    num_points = max(8, int(distance_km * 4))
    radius = distance_km / (2 * math.pi)
    
    for i in range(1, num_points + 1):
        angle = (i * 2 * math.pi) / num_points
        
        # 楕円形にして自然な形に
        lat_radius = radius * lat_per_km * random.uniform(0.8, 1.2)
        lon_radius = radius * lon_per_km * random.uniform(0.8, 1.2)
        
        lat = start_lat + lat_radius * math.cos(angle)
        lon = start_lon + lon_radius * math.sin(angle)
        
        coords.append([lat, lon])
    
    # スタート地点に戻る
    coords.append([start_lat, start_lon])
    return coords

def create_detailed_route_info(name, coords, distance_km, time_minutes, interests, location_info, base_safety):
    """詳細なルート情報を作成"""
    # 地域情報を反映した見どころ
    area_highlights = generate_area_specific_highlights(interests, location_info)
    
    # 地域の特性を反映した施設情報
    local_facilities = generate_local_facilities(coords, location_info)
    
    # 安全度を地域特性で調整
    adjusted_safety = min(100, base_safety + (location_info['safety_rating'] - 80) * 0.5)
    
    return {'id': f"detailed_{name.lower().replace(' ', '_')}",
        'name': f"{name}（{location_info['neighborhood']}発）",
        'description': f"{location_info['district']}周辺の{distance_km:.1f}km散歩コース",
        'distance': f"{distance_km:.1f}km",
        'time': f"{time_minutes:.0f}分",
        'difficulty': get_difficulty_level(distance_km, time_minutes),
        'safety_score': adjusted_safety,
        'walkability_score': location_info['walkability_score'],
        'heatstroke_risk': evaluate_heatstroke_risk(time_minutes),
        'coordinates': coords,
        'elevation_gain': calculate_elevation_gain(coords, location_info['elevation']),
        'area_info': {
            'prefecture': location_info['prefecture'],
            'city': location_'area_info': {
            'prefecture': location_info['prefecture'],
            'city': location_info['city'],
            'ward': location_info['ward'],
            'district': location_info['district'],
            'neighborhood': location_info['neighborhood'],
            'area_type': location_info['area_type'],
            'nearest_station': location_info['nearest_station'],
            'nearest_landmark': location_info['nearest_landmark']
        },
        'highlights': area_highlights,
        'facilities': local_facilities,
        'weather_consideration': get_weather_recommendations(time_minutes),
        'accessibility': evaluate_accessibility(location_info['walkability_score']),
        'best_time': get_best_walking_time(location_info['area_type']),
        'traffic_info': get_traffic_safety_info(coords, location_info)
    }

def generate_area_specific_highlights(interests, location_info):
    """地域特有の見どころを生成"""
    highlights = []
    area_type = location_info['area_type']
    
    base_highlights = {
        '住宅地': [
            '静かな住宅街の風景',
            '地域の小さな神社',
            '近所の公園',
            '古い商店街',
            '桜並木（季節限定）'
        ],
        '商業・オフィス街': [
            '高層ビル群の景観',
            '都市公園',
            '歴史的建造物',
            'アートインスタレーション',
            '商業施設'
        ],
        '工業・住宅地': [
            '多摩川の景色',
            '工場夜景',
            '地域の歴史',
            '橋からの眺望',
            '季節の花々'
        ],
        '観光・商業地': [
            '観光名所',
            '文化施設',
            'グルメスポット',
            '伝統的建築',
            '写真映えスポット'
        ]
    }
    
    # 地域タイプに応じた基本的な見どころ
    if area_type in base_highlights:
        highlights.extend(random.sample(base_highlights[area_type], min(3, len(base_highlights[area_type]))))
    
    # 興味に応じた追加見どころ
    if '歴史・文化' in interests:
        highlights.append(f"{location_info['neighborhood']}の歴史的背景")
    if '自然・公園' in interests:
        highlights.append('季節の植物観察')
    if 'グルメ' in interests:
        highlights.append('地元のお店')
    if '写真撮影' in interests:
        highlights.append('フォトスポット')
    
    return highlights[:4]  # 最大4つまで

def generate_local_facilities(coords, location_info):
    """地域の施設情報を生成"""
    facilities = []
    
    # 基本施設
    basic_facilities = [
        {'type': 'コンビニ', 'distance': '150m', 'name': 'セブンイレブン'},
        {'type': 'コンビニ', 'distance': '200m', 'name': 'ローソン'},
        {'type': 'トイレ', 'distance': '300m', 'name': '公衆トイレ'},
        {'type': '自動販売機', 'distance': '100m', 'name': '飲み物'},
        {'type': 'ベンチ', 'distance': '250m', 'name': '休憩所'}
    ]
    
    # 地域特有の施設
    area_specific = {
        '住宅地': [
            {'type': '薬局', 'distance': '400m', 'name': 'ドラッグストア'},
            {'type': '公園', 'distance': '500m', 'name': '近隣公園'},
            {'type': '交番', 'distance': '600m', 'name': '地域交番'}
        ],
        '商業・オフィス街': [
            {'type': 'カフェ', 'distance': '200m', 'name': 'スターバックス'},
            {'type': '銀行', 'distance': '300m', 'name': 'ATM'},
            {'type': '病院', 'distance': '800m', 'name': '総合病院'}
        ],
        '工業・住宅地': [
            {'type': 'スーパー', 'distance': '500m', 'name': '地元スーパー'},
            {'type': 'ガソリンスタンド', 'distance': '600m', 'name': 'ENEOS'},
            {'type': '郵便局', 'distance': '700m', 'name': '川崎郵便局'}
        ]
    }
    
    # 基本施設をランダムに選択
    facilities.extend(random.sample(basic_facilities, 3))
    
    # 地域特有施設を追加
    area_type = location_info['area_type']
    if area_type in area_specific:
        facilities.extend(random.sample(area_specific[area_type], 2))
    
    return facilities

def get_difficulty_level(distance_km, time_minutes):
    """難易度レベルを判定"""
    if distance_km < 2 and time_minutes < 30:
        return "初心者向け"
    elif distance_km < 4 and time_minutes < 60:
        return "中級者向け"
    else:
        return "上級者向け"

def evaluate_heatstroke_risk(time_minutes):
    """熱中症リスクを評価"""
    current_hour = datetime.now().hour
    
    if 11 <= current_hour <= 15:  # 日中の暑い時間
        if time_minutes > 45:
            return "高リスク"
        elif time_minutes > 30:
            return "中リスク"
        else:
            return "低リスク"
    else:
        return "低リスク"

def calculate_elevation_gain(coords, base_elevation):
    """標高差を計算"""
    # 簡易的な標高変化計算
    total_gain = 0
    prev_elevation = base_elevation
    
    for i, coord in enumerate(coords[1:], 1):
        # 座標変化に基づいて標高変化を推定
        lat_change = coord[0] - coords[i-1][0]
        elevation_change = lat_change * 1000  # 簡易計算
        
        current_elevation = max(0, prev_elevation + elevation_change)
        if current_elevation > prev_elevation:
            total_gain += current_elevation - prev_elevation
        
        prev_elevation = current_elevation
    
    return max(0, int(total_gain))

def get_weather_recommendations(time_minutes):
    """天気に応じた推奨事項"""
    current_hour = datetime.now().hour
    
    recommendations = []
    
    if 6 <= current_hour <= 18:  # 日中
        recommendations.append("帽子と日焼け止めを忘れずに")
        recommendations.append("水分補給を定期的に")
    else:  # 夜間
        recommendations.append("反射材付きの服装を推奨")
        recommendations.append("懐中電灯やスマホライトを準備")
    
    if time_minutes > 30:
        recommendations.append("途中で休憩を取りましょう")
    
    return recommendations

def evaluate_accessibility(walkability_score):
    """アクセシビリティを評価"""
    if walkability_score >= 80:
        return {
            'level': '良好',
            'description': '歩道が整備されており、車椅子でも通行しやすい'
        }
    elif walkability_score >= 60:
        return {
            'level': '普通',
            'description': '一般的な歩行者向け。一部段差あり'
        }
    else:
        return {
            'level': '注意',
            'description': '歩道が狭い箇所や段差があります'
        }

def get_best_walking_time(area_type):
    """最適な散歩時間を提案"""
    current_hour = datetime.now().hour
    
    if area_type == '商業・オフィス街':
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            return "通勤ラッシュ時間のため、10時頃または15時頃がおすすめ"
        else:
            return "現在の時間帯は散歩に適しています"
    elif area_type == '住宅地':
        if 22 <= current_hour or current_hour <= 6:
            return "住宅街のため、日中（7時～21時）の散歩がおすすめ"
        else:
            return "静かな住宅街での散歩に適した時間です"
    else:
        return "いつでも散歩をお楽しみいただけます"

def get_traffic_safety_info(coords, location_info):
    """交通安全情報を取得"""
    safety_info = {
        'traffic_volume': 'medium',
        'crosswalk_count': len(coords) // 4,  # 大雑把な横断歩道数
        'safety_tips': []
    }
    
    area_type = location_info['area_type']
    
    if area_type == '商業・オフィス街':
        safety_info['traffic_volume'] = 'high'
        safety_info['safety_tips'] = [
            '交差点では信号をしっかり確認',
            '歩道を歩き、車道に出ないよう注意',
            '自転車との接触に注意'
        ]
    elif area_type == '住宅地':
        safety_info['traffic_volume'] = 'low'
        safety_info['safety_tips'] = [
            '住宅街では車の出入りに注意',
            '子どもの飛び出しに注意',
            '夜間は明るい道を選択'
        ]
    else:
        safety_info['safety_tips'] = [
            '歩行者優先の道路を選択',
            '見通しの良い道を歩く',
            '不明な場所では地図を確認'
        ]
    
    return safety_info

# 🆕 リアルタイム散歩追跡システム
def start_walking_session(selected_route):
    """散歩セッションを開始"""
    st.session_state.walking_start_time = datetime.now()
    st.session_state.walking_progress = 0
    st.session_state.selected_route = selected_route
    st.session_state.current_step = 'walking'
    st.session_state.walking_path = []
    st.session_state.total_distance = 0
    st.session_state.location_history = []
    
    # 散歩開始ログ
    st.session_state.walking_log = {
        'start_time': st.session_state.walking_start_time,
        'route_name': selected_route['name'],
        'planned_distance': selected_route['distance'],
        'planned_time': selected_route['time'],
        'checkpoints': []
    }

def update_walking_progress():
    """散歩進捗を更新"""
    if st.session_state.walking_start_time:
        # 新しい位置を取得
        new_location = get_precise_gps_location()
        
        if new_location:
            # 移動距離を計算
            if st.session_state.walking_path:
                last_pos = st.session_state.walking_path[-1]
                distance_moved = geodesic(
                    (last_pos['lat'], last_pos['lon']),
                    (new_location['lat'], new_location['lon'])
                ).meters
                
                # 50m以上移動した場合のみ記録（GPS誤差を考慮）
                if distance_moved > 50:
                    st.session_state.total_distance += distance_moved / 1000  # km単位
                    st.session_state.walking_path.append(new_location)
                    
                    # 詳細位置情報を更新
                    detailed_location = get_detailed_location_info(
                        new_location['lat'], new_location['lon']
                    )
                    st.session_state.location_history.append(detailed_location)
                    
                    # 進捗率を計算
                    planned_distance = float(st.session_state.selected_route['distance'].replace('km', ''))
                    st.session_state.walking_progress = min(100, 
                        (st.session_state.total_distance / planned_distance) * 100)
            else:
                # 最初の位置を記録
                st.session_state.walking_path.append(new_location)
                detailed_location = get_detailed_location_info(
                    new_location['lat'], new_location['lon']
                )
                st.session_state.location_history.append(detailed_location)

def get_walking_stats():
    """散歩統計を取得"""
    if not st.session_state.walking_start_time:
        return None
    
    elapsed_time = datetime.now() - st.session_state.walking_start_time
    elapsed_minutes = elapsed_time.total_seconds() / 60
    
    # 平均速度を計算
    if elapsed_minutes > 0 and st.session_state.total_distance > 0:
        avg_speed = (st.session_state.total_distance / elapsed_minutes) * 60  # km/h
    else:
        avg_speed = 0
    
    # 消費カロリーを推定（簡易計算）
    calories = st.session_state.total_distance * 50  # 1kmあたり50kcal
    
    return {
        'elapsed_time': elapsed_minutes,
        'elapsed_time_str': f"{int(elapsed_minutes)}分{int((elapsed_minutes % 1) * 60)}秒",
        'distance': st.session_state.total_distance,
        'progress': st.session_state.walking_progress,
        'avg_speed': avg_speed,
        'calories': calories,
        'checkpoints': len(st.session_state.walking_path)
    }

def create_walking_progress_map():
    """散歩進捗マップを作成"""
    if not st.session_state.walking_path:
        return None
    
    # 最新の位置を中心とした地図
    latest_pos = st.session_state.walking_path[-1]
    m = folium.Map(
        location=[latest_pos['lat'], latest_pos['lon']],
        zoom_start=16,
        tiles='OpenStreetMap'
    )
    
    # 歩いた経路を描画
    if len(st.session_state.walking_path) > 1:
        route_coords = [[pos['lat'], pos['lon']] for pos in st.session_state.walking_path]
        folium.PolyLine(
            route_coords,
            color='blue',
            weight=6,
            opacity=0.8,
            popup='歩いた経路'
        ).add_to(m)
    
    # 開始地点をマーク
    start_pos = st.session_state.walking_path[0]
    folium.Marker(
        [start_pos['lat'], start_pos['lon']],
        popup='散歩開始地点',
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    # 現在地をマーク
    folium.Marker(
        [latest_pos['lat'], latest_pos['lon']],
        popup=f'現在地 (精度: {latest_pos["accuracy"]}m)',
        icon=folium.Icon(color='red', icon='user')
    ).add_to(m)
    
    # 予定ルートを表示（薄い色で）
    if st.session_state.selected_route and 'coordinates' in st.session_state.selected_route:
        planned_coords = st.session_state.selected_route['coordinates']
        folium.PolyLine(
            planned_coords,
            color='gray',
            weight=3,
            opacity=0.4,
            popup='予定ルート'
        ).add_to(m)
    
    return m

def finish_walking_session():
    """散歩セッションを終了"""
    if st.session_state.walking_start_time:
        end_time = datetime.now()
        stats = get_walking_stats()
        
        # 散歩記録を保存
        walking_record = {
            'date': st.session_state.walking_start_time.strftime('%Y-%m-%d'),
            'start_time': st.session_state.walking_start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'route_name': st.session_state.selected_route['name'],
            'planned_distance': st.session_state.selected_route['distance'],
            'actual_distance': f"{stats['distance']:.2f}km",
            'duration': stats['elapsed_time_str'],
            'avg_speed': f"{stats['avg_speed']:.1f}km/h",
            'calories': f"{stats['calories']:.0f}kcal",
            'checkpoints': stats['checkpoints'],
            'locations_visited': len(st.session_state.location_history)
        }
        
        # セッション状態をクリア
        st.session_state.walking_start_time = None
        st.session_state.walking_progress = 0
        st.session_state.walking_path = []
        st.session_state.total_distance = 0
        st.session_state.current_step = 'completed'
        
        return walking_record
    
    return None

# 🆕 メイン画面表示関数
def show_main_interface():
    """メイン画面を表示"""
    st.title("🚶 安心散歩ナビ")
    st.markdown("---")
    
    # 現在のステップに応じた画面表示
    if st.session_state.current_step == 'home':
        show_home_screen()
    elif st.session_state.current_step == 'location_setup':
        show_location_setup_screen()
    elif st.session_state.current_step == 'route_selection':
        show_route_selection_screen()
    elif st.session_state.current_step == 'walking':
        show_walking_screen()
    elif st.session_state.current_step == 'completed':
        show_completion_screen()

def show_home_screen():
    """ホーム画面を表示"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📍 現在地の詳細情報")
        
        # GPS取得ボタン
        if st.button("📡 高精度GPS位置を取得", type="primary", use_container_width=True):
            with st.spinner("GPS位置を取得中..."):
                time.sleep(2)  # GPS取得のシミュレーション
                gps_location = get_precise_gps_location()
                detailed_location = get_detailed_location_info(gps_location['lat'], gps_location['lon'])
                
                st.session_state.current_location = gps_location
                st.session_state.detailed_location = detailed_location
                st.session_state.gps_enabled = True
                st.session_state.gps_accuracy = gps_location['accuracy']
                st.rerun()
        
        # 位置情報が取得済みの場合
        if st.session_state.gps_enabled and st.session_state.detailed_location:
            loc = st.session_state.detailed_location
            
            # 詳細位置情報を表示
            st.success(f"📍 位置情報を取得しました (精度: {st.session_state.gps_accuracy}m)")
            
            # 位置情報詳細
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                st.info(f"""
                **📍 現在地詳細**
                - 都道府県: {loc['prefecture']}
                - 市区町村: {loc['city']}
                - 地区: {loc['district']}
                - 近隣: {loc['neighborhood']}
                """)
            
            with col1_2:
                st.info(f"""
                **🏢 エリア情報**
                - 種別: {loc['area_type']}
                - 標高: {loc['elevation']}m
                - 最寄り駅: {loc['nearest_station']['name']} ({loc['nearest_station']['distance']})
                - 最寄り施設: {loc['nearest_landmark']['name']} ({loc['nearest_landmark']['distance']})
                """)
            
            # 安全度と歩きやすさ
            col1_3, col1_4 = st.columns(2)
            with col1_3:
                st.metric("🛡️ 安全度", f"{loc['safety_rating']}/100")
            with col1_4:
                st.metric("🚶 歩きやすさ", f"{loc['walkability_score']}/100")
            
            # 散歩ルート生成ボタン
            if st.button("🗺️ この場所からの散歩ルートを生成", type="primary", use_container_width=True):
                st.session_state.current_step = 'route_selection'
                st.rerun()
    
    with col2:
        st.header("⚙️ 散歩設定")
        
        # ユーザー設定
        mobility = st.selectbox(
            "歩行ペース",
            ["slow", "normal", "fast"],
            format_func=lambda x: {"slow": "ゆっくり", "normal": "普通", "fast": "速め"}[x],
            index=["slow", "normal", "fast"].index(st.session_state.user_preferences['mobility'])
        )
        
        walking_time = st.slider(
            "散歩時間（分）",
            min_value=15,
            max_value=120,
            value=st.session_state.user_preferences['walking_time'],
            step=15
        )
        
        interests = st.multiselect(
            "興味のあるもの",
            ["自然・公園", "歴史・文化", "グルメ", "写真撮影", "健康・運動", "ショッピング"],
            default=st.session_state.user_preferences['interests']
        )
        
        safety_level = st.selectbox(
            "安全重視度",
            ["low", "medium", "high"],
            format_func=lambda x: {"low": "低", "medium": "中", "high": "高"}[x],
            index=["low", "medium", "high"].index(st.session_state.user_preferences['safety_level'])
        )
        
        # 設定を保存
        st.session_state.user_preferences.update({
            'mobility': mobility,
            'walking_time': walking_time,
            'interests': interests,
            'safety_level': safety_level
        })
        
        # 設定確認
        st.markdown("---")
        st.write("**現在の設定:**")
        st.write(f"- ペース: {{'slow': 'ゆっくり', 'normal': '普通', 'fast': '速め'}}[mobility]")
        st.write(f"- 時間: {walking_time}分")
        st.write(f"- 興味: {', '.join(interests) if interests else 'なし'}")
        st.write(f"- 安全重視: {{'low': '低', 'medium': '中', 'high': '高'}}[safety_level]")

def show_route_selection_screen():
    """ルート選択画面を表示"""
    st.header("🗺️ 散歩ルート選択")
    
    # 戻るボタン
    if st.button("← ホームに戻る"):
        st.session_state.current_step = 'home'
        st.rerun()
    
    # ルート生成
    if not st.session_state.generated_routes:
        with st.spinner("あなたの現在地に最適な散歩ルートを生成中..."):
            time.sleep(3)  # ルート生成のシミュレーション
            routes = generate_detailed_routes_from_gps(
                st.session_state.detailed_location,
                st.session_state.user_preferences
            )
            st.session_state.generated_routes = routes
            st.rerun()
    
    # 生成されたルートを表示
    if st.session_state.generated_routes:
        st.success(f"🎉 {len(st.session_state.generated_routes)}つの散歩ルートを生成しました！")
        
        # ルート一覧
        for i, route in enumerate(st.session_state.generated_routes):
            with st.expander(f"📍 {route['name']}", expanded=i==0):
                
                # ルート基本情報
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📏 距離", route['distance'])
                with col2:
                    st.metric("⏱️ 時間", route['time'])
                with col3:
                    st.metric("🛡️ 安全度", f"{route['safety_score']}/100")
                with col4:
                    st.metric("🚶 歩きやすさ", f"{route['walkability_score']}/100")
                
                # ルート詳細情報
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**📍 エリア情報**")
                    st.write(f"- 都道府県: {route['area_info']['prefecture']}")
                    st.write(f"- 市区町村: {route['area_info']['city']}")
                    st.write(f"- 地区: {route['area_info']['district']}")
                    st.write(f"- エリア種別: {route['area_info']['area_type']}")
                    
                    st.write("**🏢 周辺施設**")
                    for facility in route['facilities'][:3]:
                        st.write(f"- {facility['type']}: {facility['name']} ({facility['distance']})")
                
                with col2:
                    st.write("**✨ 見どころ**")
                    for highlight in route['highlights']:
                        st.write(f"- {highlight}")
                    
                    st.write("**⚠️ 注意事項**")
                    st.write(f"- 難易度: {route['difficulty']}")
                    st.write(f"- 熱中症リスク: {route['heatstroke_risk']}")
                    st.write(f"- 標高差: {route['elevation_gain']}m")
                
                # 天気と安全情報
                st.write("**🌤️ 天気に関する推奨事項**")
                for rec in route['weather_consideration']:
                    st.write(f"- {rec}")
                
                st.write("**🚦 交通安全情報**")
                for tip in route['traffic_info']['safety_tips']:
                    st.write(f"- {tip}")
                
                # ルート選択ボタン
                if st.button(f"この散歩ルートを選択", key=f"select_route_{i}", type="primary"):
                    st.session_state.selected_route = route
                    start_walking_session(route)
                    st.rerun()

def show_walking_screen():
    """散歩中画面を表示"""
    st.header("🚶 散歩中")
    
    # 進捗更新
    update_walking_progress()
    stats = get_walking_stats()
    
    if stats:
        # 進捗表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ 経過時間", stats['elapsed_time_str'])
        with col2:
            st.metric("📏 歩行距離", f"{stats['distance']:.2f}km")
        with col3:
            st.metric("🔥 消費カロリー", f"{stats['calories']:.0f}kcal")
        with col4:
            st.metric("🏃 平均速度", f"{stats['avg_speed']:.1f}km/h")
        
        # 進捗バー
        st.progress(stats['progress'] / 100)
        st.write(f"ルート進捗: {stats['progress']:.1f}% ({stats['checkpoints']} チェックポイント通過)")
        
        # リアルタイム地図
        walking_map = create_walking_progress_map()
        if walking_map:
            st.subheader("🗺️ リアルタイム散歩マップ")
            st_folium(walking_map, width=700, height=400)
        
        # 現在地情報
        if st.session_state.location_history:
            current_location = st.session_state.location_history[-1]
            st.subheader("📍 現在地情報")
            st.write(f"**現在地**: {current_location['city']} {current_location['district']}")
            st.write(f"**エリア**: {current_location['area_type']}")
	# 制御ボタン
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏸️ 散歩を一時停止", type="secondary", use_container_width=True):
                st.session_state.walking_paused = True
                st.info("散歩を一時停止しました。再開ボタンを押して続行してください。")
        
        with col2:
            if st.button("🏁 散歩を終了", type="primary", use_container_width=True):
                walking_record = finish_walking_session()
                if walking_record:
                    st.session_state.last_walking_record = walking_record
                st.rerun()
        
        # 散歩中のヒントとアドバイス
        st.subheader("💡 散歩中のヒント")
        
        # 時間に応じたアドバイス
        if stats['elapsed_time'] > 30:
            st.info("🚰 30分以上歩いています。水分補給を忘れずに！")
        
        if stats['elapsed_time'] > 60:
            st.warning("⚠️ 1時間以上歩いています。適度な休憩を取りましょう。")
        
        # 速度に応じたアドバイス
        if stats['avg_speed'] > 6:
            st.info("🏃 ペースが速めです。無理をせず、景色を楽しみましょう。")
        elif stats['avg_speed'] < 3:
            st.info("🐌 ゆっくりペースですね。周りの景色をじっくり楽しめます。")
        
        # 現在地周辺の情報
        if st.session_state.location_history:
            current_area = st.session_state.location_history[-1]
            st.subheader("📍 周辺情報")
            
            # 近くの休憩場所
            if current_area['area_type'] == '商業・オフィス街':
                st.write("☕ 近くにカフェやコンビニがあります。休憩にどうぞ。")
            elif current_area['area_type'] == '住宅地':
                st.write("🏞️ 静かな住宅街です。小さな公園や神社があるかもしれません。")
            elif current_area['area_type'] == '観光・商業地':
                st.write("📸 観光地です。写真撮影スポットを探してみてください。")
    
    # 自動更新
    if not st.session_state.get('walking_paused', False):
        time.sleep(1)
        st.rerun()

def show_completion_screen():
    """散歩完了画面を表示"""
    st.header("🎉 散歩完了！")
    
    # 散歩記録の表示
    if st.session_state.get('last_walking_record'):
        record = st.session_state.last_walking_record
        
        st.success("散歩お疲れ様でした！")
        
        # 散歩サマリー
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 散歩記録")
            st.write(f"**日付**: {record['date']}")
            st.write(f"**時間**: {record['start_time']} - {record['end_time']}")
            st.write(f"**ルート**: {record['route_name']}")
            st.write(f"**予定距離**: {record['planned_distance']}")
            st.write(f"**実際の距離**: {record['actual_distance']}")
            st.write(f"**所要時間**: {record['duration']}")
        
        with col2:
            st.subheader("📈 パフォーマンス")
            st.write(f"**平均速度**: {record['avg_speed']}")
            st.write(f"**消費カロリー**: {record['calories']}")
            st.write(f"**チェックポイント**: {record['checkpoints']}箇所")
            st.write(f"**訪問地点**: {record['locations_visited']}箇所")
        
        # 散歩評価
        st.subheader("⭐ 散歩の評価")
        rating = st.slider("今回の散歩はいかがでしたか？", 1, 5, 4)
        
        # コメント
        comment = st.text_area("感想やコメント（任意）")
        
        # 写真アップロード
        st.subheader("📸 散歩中の写真")
        uploaded_photos = st.file_uploader(
            "散歩中に撮影した写真をアップロード",
            accept_multiple_files=True,
            type=['jpg', 'jpeg', 'png']
        )
        
        if uploaded_photos:
            st.write(f"📷 {len(uploaded_photos)}枚の写真がアップロードされました")
            
            # 写真のプレビュー
            cols = st.columns(min(3, len(uploaded_photos)))
            for i, photo in enumerate(uploaded_photos[:3]):
                with cols[i]:
                    st.image(photo, caption=f"写真 {i+1}", use_column_width=True)
        
        # 記録保存
        if st.button("📝 記録を保存", type="primary"):
            # 散歩記録を保存（実際の実装では データベースやファイルに保存）
            walking_history = {
                'record': record,
                'rating': rating,
                'comment': comment,
                'photos': len(uploaded_photos) if uploaded_photos else 0
            }
            
            # セッション状態に保存
            if 'walking_history' not in st.session_state:
                st.session_state.walking_history = []
            st.session_state.walking_history.append(walking_history)
            
            st.success("散歩記録を保存しました！")
            
            # 統計情報
            st.subheader("📊 あなたの散歩統計")
            total_walks = len(st.session_state.walking_history)
            total_distance = sum(
                float(h['record']['actual_distance'].replace('km', '')) 
                for h in st.session_state.walking_history
            )
            total_calories = sum(
                float(h['record']['calories'].replace('kcal', '')) 
                for h in st.session_state.walking_history
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🚶 総散歩回数", f"{total_walks}回")
            with col2:
                st.metric("📏 総距離", f"{total_distance:.1f}km")
            with col3:
                st.metric("🔥 総消費カロリー", f"{total_calories:.0f}kcal")
    
    # 次の散歩への誘導
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 ホームに戻る", type="secondary", use_container_width=True):
            st.session_state.current_step = 'home'
            st.rerun()
    
    with col2:
        if st.button("🔄 もう一度散歩する", type="primary", use_container_width=True):
            # 状態をリセット
            st.session_state.current_step = 'home'
            st.session_state.generated_routes = []
            st.session_state.selected_route = None
            st.rerun()

# 🆕 散歩履歴表示機能
def show_walking_history():
    """散歩履歴を表示"""
    st.subheader("📚 散歩履歴")
    
    if 'walking_history' in st.session_state and st.session_state.walking_history:
        for i, history in enumerate(reversed(st.session_state.walking_history)):
            record = history['record']
            with st.expander(f"散歩 #{len(st.session_state.walking_history) - i}: {record['date']} {record['route_name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**時間**: {record['start_time']} - {record['end_time']}")
                    st.write(f"**距離**: {record['actual_distance']}")
                    st.write(f"**時間**: {record['duration']}")
                    st.write(f"**速度**: {record['avg_speed']}")
                
                with col2:
                    st.write(f"**カロリー**: {record['calories']}")
                    st.write(f"**評価**: {'⭐' * history['rating']}")
                    st.write(f"**写真**: {history['photos']}枚")
                    if history['comment']:
                        st.write(f"**コメント**: {history['comment']}")
    else:
        st.info("まだ散歩記録がありません。最初の散歩を始めてみましょう！")

# 🆕 天気情報表示機能
def show_weather_info():
    """天気情報を表示"""
    st.subheader("🌤️ 現在の天気")
    
    # 模擬天気データ
    weather_data = {
        'temperature': 24,
        'humidity': 65,
        'wind_speed': 2.5,
        'uv_index': 3,
        'condition': 'partly_cloudy',
        'precipitation': 0
    }
    
    # 天気アイコンと基本情報
    weather_icons = {
        'sunny': '☀️',
        'partly_cloudy': '⛅',
        'cloudy': '☁️',
        'rainy': '🌧️',
        'snowy': '🌨️'
    }
    
    icon = weather_icons.get(weather_data['condition'], '⛅')
    st.write(f"{icon} **現在の天気**: {'晴れ時々曇り' if weather_data['condition'] == 'partly_cloudy' else '晴れ'}")
    
    # 天気詳細
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌡️ 気温", f"{weather_data['temperature']}°C")
    with col2:
        st.metric("💧 湿度", f"{weather_data['humidity']}%")
    with col3:
        st.metric("💨 風速", f"{weather_data['wind_speed']}m/s")
    with col4:
        st.metric("☀️ UV指数", weather_data['uv_index'])
    
    # 散歩に関する天気アドバイス
    st.subheader("🚶 散歩アドバイス")
    
    advice = []
    if weather_data['temperature'] > 30:
        advice.append("🔥 気温が高いです。水分補給と日陰での休憩を心がけてください。")
    elif weather_data['temperature'] < 5:
        advice.append("🧥 気温が低いです。暖かい服装で散歩してください。")
    else:
        advice.append("👍 散歩に適した気温です。")
    
    if weather_data['humidity'] > 80:
        advice.append("💧 湿度が高いです。汗をかきやすいので注意してください。")
    
    if weather_data['wind_speed'] > 5:
        advice.append("💨 風が強いです。帽子や軽い物に注意してください。")
    
    if weather_data['uv_index'] > 6:
        advice.append("☀️ UV指数が高いです。日焼け止めと帽子を着用してください。")
    
    if weather_data['precipitation'] > 0:
        advice.append("🌧️ 雨が降っています。傘を持参するか、屋内での運動を検討してください。")
    
    for adv in advice:
        st.info(adv)

# 🆕 設定画面
def show_settings():
    """設定画面を表示"""
    st.subheader("⚙️ アプリ設定")
    
    # 通知設定
    st.write("**📱 通知設定**")
    notification_walk_reminder = st.checkbox("散歩リマインダー", value=True)
    notification_weather_alert = st.checkbox("天気アラート", value=True)
    notification_achievement = st.checkbox("達成記録通知", value=True)
    
    # 表示設定
    st.write("**🎨 表示設定**")
    theme = st.selectbox("テーマ", ["light", "dark", "auto"], index=0)
    language = st.selectbox("言語", ["日本語", "English"], index=0)
    
    # プライバシー設定
    st.write("**🔒 プライバシー設定**")
    location_sharing = st.checkbox("位置情報の共有", value=False)
    data_collection = st.checkbox("使用データの収集", value=True)
    
    # データ管理
    st.write("**📊 データ管理**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 データをエクスポート"):
            st.info("散歩データをCSVファイルでダウンロードできます。")
    with col2:
        if st.button("🗑️ データをクリア", type="secondary"):
            if st.confirm("すべての散歩データを削除しますか？"):
                st.session_state.walking_history = []
                st.success("データを削除しました。")

# 🆕 サイドバー表示
def show_sidebar():
    """サイドバーを表示"""
    with st.sidebar:
        st.title("📱 メニュー")
        
        # 現在のステップ表示
        step_names = {
            'home': '🏠 ホーム',
            'location_setup': '📍 位置設定',
            'route_selection': '🗺️ ルート選択',
            'walking': '🚶 散歩中',
            'completed': '🎉 完了'
        }
        
        current_step_name = step_names.get(st.session_state.current_step, '🏠 ホーム')
        st.write(f"**現在の画面**: {current_step_name}")
        
        st.markdown("---")
        
        # 天気情報
        show_weather_info()
        
        st.markdown("---")
        
        # 散歩履歴
        show_walking_history()
        
        st.markdown("---")
        
        # 設定
        with st.expander("⚙️ 設定"):
            show_settings()
        
        st.markdown("---")
        
        # アプリ情報
        st.write("**📱 アプリ情報**")
        st.write("安心散歩ナビ v1.0")
        st.write("© 2024 Walking Navigator")

# 🆕 メイン実行関数
def main():
    """メイン実行関数"""
    # セッション状態を初期化
    initialize_session_state()
    
    # サイドバーを表示
    show_sidebar()
    
    # メイン画面を表示
    show_main_interface()

# アプリを実行
if __name__ == "__main__":
    main()