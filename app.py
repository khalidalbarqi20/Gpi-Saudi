"""
GBI - تحليل المواقع التجارية (نسخة محسّنة v2)
- محرك Mapbox شغّال + تصميم احترافي
- ميزات جديدة: قرار نهائي، مؤشرات Opportunity/Saturation/Demand، DNA الحي،
  لماذا اقترحنا، أسوأ الأنشطة، مؤشر الثقة، تحليل مالي، تحليل صور، مواقف وذروة
ملف مستقل واحد
"""

import os
import re
import json
import math
import time
import requests
import streamlit as st
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from PIL import Image

# ============================================================
# Configuration
# ============================================================
load_dotenv()


def _read_key(name: str) -> str:
    try:
        val = st.secrets.get(name, "")
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.getenv(name, "").strip()


GEMINI_KEY = _read_key("GEMINI_API_KEY")
MAPBOX = _read_key("MAPBOX_TOKEN")

AI_AVAILABLE = False
genai = None
if GEMINI_KEY:
    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=GEMINI_KEY)
        AI_AVAILABLE = True
        genai = genai_module
    except Exception:
        AI_AVAILABLE = False

st.set_page_config(
    page_title="GBI - الاستثمار الذكي",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# ============================================================
# الفئات
# ============================================================
CATEGORIES = {
    "restaurant": {"name": "مطاعم", "icon": "🍽️", "color": "#ef4444"},
    "cafe": {"name": "مقاهي", "icon": "☕", "color": "#f59e0b"},
    "fast_food": {"name": "وجبات سريعة", "icon": "🍔", "color": "#dc2626"},
    "shopping": {"name": "تسوق", "icon": "🛍️", "color": "#a855f7"},
    "fuel": {"name": "محطات وقود", "icon": "⛽", "color": "#64748b"},
    "pharmacy": {"name": "صيدليات", "icon": "💊", "color": "#10b981"},
    "grocery": {"name": "بقالات", "icon": "🛒", "color": "#3b82f6"},
    "services": {"name": "خدمات", "icon": "🔧", "color": "#94a3b8"},
}

ACTIVITY_TYPES = {
    "مطعم": "restaurant",
    "مقهى": "cafe",
    "وجبات سريعة": "fast_food",
    "محل تسوق": "shopping",
    "صيدلية": "pharmacy",
    "بقالة / سوبر ماركت": "grocery",
    "محطة وقود": "fuel",
    "خدمات": "services",
}

# متوسطات تقديرية للسعودية (لمقارنة المدينة)
SA_AVG_PLACES_PER_KM = 30  # متوسط محلات في كم2 للمدن المتوسطة

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    #MainMenu, header, footer, .stDeployButton {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__1QSob, ._profileContainer_gzau3_53, ._terminalButton_rix23_138 {display: none !important;}
    a[href*="streamlit.io"], a[href*="share.streamlit"] {display: none !important;}

    body, .stApp {
        direction: rtl; text-align: right;
        background: #0a0e1a !important; color: #fff;
        font-family: 'Segoe UI', 'Tahoma', sans-serif;
    }
    .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important;}

    .top-bar {display: flex; align-items: center; justify-content: space-between;
        padding: 16px 24px; background: #131826; border-radius: 16px; margin-bottom: 20px; border: 1px solid #1f2937;}
    .brand {font-size: 28px; font-weight: 900; color: #ef4444; letter-spacing: 2px;}
    .brand-sub {color: #94a3b8; font-size: 12px; margin-top: 2px;}
    .top-bar-left {display: flex; align-items: center; gap: 16px;}
    .badge-connected {background: rgba(16,185,129,0.15); color: #10b981; padding: 6px 12px; border-radius: 20px; font-size: 12px;}
    .badge-disconnected {background: rgba(239,68,68,0.15); color: #ef4444; padding: 6px 12px; border-radius: 20px; font-size: 12px;}
    .user-pill {display: flex; align-items: center; gap: 8px; background: #1f2937; padding: 6px 12px; border-radius: 30px;}
    .user-avatar {width: 32px; height: 32px; background: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;}

    .page-title {text-align: right; padding: 8px 20px 16px 20px; margin-bottom: 20px;}
    .page-title h1 {color: white; font-size: 32px; margin: 0; font-weight: 700;}
    .page-title p {color: #94a3b8; margin: 6px 0 0 0; font-size: 14px;}

    div[data-testid="stTextInput"] input {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 14px !important; padding: 16px 20px !important; font-size: 15px !important; height: 56px !important;}
    div[data-testid="stTextInput"] input:focus {border-color: #ef4444 !important; box-shadow: 0 0 0 3px rgba(239,68,68,0.15) !important;}
    div[data-testid="stSelectbox"] > div > div {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important; min-height: 56px !important; color: white !important;}
    div[data-testid="stSelectbox"] svg {fill: white !important;}
    div[data-testid="stNumberInput"] input {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 12px !important;}

    .stButton button {background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important; color: white !important; border: none !important; padding: 14px 24px !important; border-radius: 14px !important; font-weight: 700 !important; font-size: 15px !important; width: 100% !important; height: 56px !important; box-shadow: 0 4px 16px rgba(239,68,68,0.3) !important;}
    .stButton button:hover {transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;}

    /* القرار النهائي - أهم بطاقة */
    .verdict-card {
        background: linear-gradient(135deg, #1a2238 0%, #131826 100%);
        border-radius: 22px;
        padding: 28px;
        margin: 16px 0 24px 0;
        border: 2px solid;
        position: relative;
        overflow: hidden;
    }
    .verdict-card::before {
        content: '';
        position: absolute;
        top: 0; right: 0; bottom: 0;
        width: 6px;
    }
    .verdict-header {display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;}
    .verdict-emoji {font-size: 56px; line-height: 1;}
    .verdict-title {font-size: 32px; font-weight: 900; margin: 4px 0;}
    .verdict-score {font-size: 18px; color: #94a3b8;}
    .verdict-score b {font-size: 22px;}
    .verdict-reason {color: #cbd5e1; font-size: 15px; line-height: 1.7; margin: 14px 0;}
    .verdict-tags {display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px;}
    .verdict-tag {background: rgba(255,255,255,0.06); padding: 6px 14px; border-radius: 999px; font-size: 13px; color: #e2e8f0;}

    /* المؤشرات الثلاث الكبيرة */
    .big-metric {background: #131826; border: 1px solid #1f2937; border-radius: 18px; padding: 22px; text-align: center;}
    .big-metric-icon {font-size: 32px; margin-bottom: 8px;}
    .big-metric-label {color: #94a3b8; font-size: 13px; font-weight: 600; margin-bottom: 8px;}
    .big-metric-value {font-size: 42px; font-weight: 900; line-height: 1;}
    .big-metric-bar {background: rgba(255,255,255,0.05); border-radius: 8px; height: 8px; margin-top: 12px; overflow: hidden;}
    .big-metric-bar-fill {height: 100%; border-radius: 8px;}
    .big-metric-sub {color: #64748b; font-size: 12px; margin-top: 8px;}

    .kpi-card {background: #131826; border: 1px solid #1f2937; border-radius: 18px; padding: 20px;}
    .kpi-header {display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;}
    .kpi-title {color: #94a3b8; font-size: 13px; font-weight: 500;}
    .kpi-icon {width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 22px;}
    .kpi-value {color: white; font-size: 26px; font-weight: 800; margin: 4px 0;}
    .kpi-value-sm {color: white; font-size: 20px; font-weight: 700; margin: 4px 0;}
    .kpi-sub {color: #64748b; font-size: 12px;}

    .info-card {background: #131826; border: 1px solid #1f2937; border-radius: 18px; padding: 22px; height: 100%;}
    .info-card-title {color: white; font-size: 17px; font-weight: 700; margin-bottom: 14px;}

    /* بطاقة النشاط مرتبة */
    .activity-rank-card {
        background: linear-gradient(135deg, #1e293b 0%, #131826 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 16px;
        transition: all 0.2s;
    }
    .activity-rank-card:hover {border-color: #ef4444; transform: translateX(-4px);}
    .rank-number {
        font-size: 28px; font-weight: 900;
        color: #f59e0b; min-width: 40px;
    }
    .rank-content {flex: 1;}
    .rank-name {color: white; font-size: 17px; font-weight: 700; margin-bottom: 6px;}
    .rank-reason {color: #94a3b8; font-size: 12px; line-height: 1.5;}
    .rank-score-pill {
        background: rgba(16,185,129,0.15); color: #10b981;
        padding: 8px 14px; border-radius: 999px;
        font-size: 18px; font-weight: 800; min-width: 70px; text-align: center;
    }
    .rank-score-pill.bad {background: rgba(239,68,68,0.15); color: #ef4444;}
    .rank-score-pill.warn {background: rgba(245,158,11,0.15); color: #f59e0b;}

    /* DNA الحي */
    .dna-row {display: flex; align-items: center; gap: 12px; padding: 10px 0;}
    .dna-label {color: #cbd5e1; min-width: 80px; font-size: 13px;}
    .dna-bar {flex: 1; background: rgba(255,255,255,0.05); border-radius: 6px; height: 10px; overflow: hidden;}
    .dna-fill {height: 100%; border-radius: 6px; transition: width 0.4s;}
    .dna-value {color: white; font-weight: 700; min-width: 40px; text-align: left; font-size: 13px;}

    .quick-row {display: flex; align-items: center; justify-content: space-between; padding: 11px 0; border-bottom: 1px solid #1f2937;}
    .quick-row:last-child {border-bottom: none;}
    .quick-label {color: #94a3b8; font-size: 13px;}
    .quick-value {color: white; font-size: 14px; font-weight: 600;}

    div[data-testid="stExpander"] {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important;}
    div[data-testid="stExpander"] summary {color: white !important; font-weight: 600 !important;}

    .stProgress > div > div > div > div {background: linear-gradient(90deg, #ef4444 0%, #f87171 100%) !important;}
    .progress-msg {color: #fca5a5; font-size: 14px; text-align: center; margin: 8px 0; font-weight: 500;}

    .stAlert {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 12px !important; color: #e2e8f0 !important;}
    [data-testid="stChatMessage"] {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important;}
    [data-testid="stChatInput"] textarea {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 14px !important;}

    .section-title {color: white; font-size: 20px; font-weight: 700; margin: 28px 0 14px 0; display: flex; align-items: center; gap: 10px;}
    .section-title::before {content: ''; width: 4px; height: 22px; background: #ef4444; border-radius: 2px;}

    .competitor-row {display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: rgba(31,41,55,0.5); border-radius: 10px; margin-bottom: 8px; font-size: 13px;}
    .competitor-rank {color: #64748b; font-weight: 700; width: 24px;}
    .competitor-name {color: #e2e8f0; flex: 1; padding: 0 8px;}
    .competitor-dist {color: #f59e0b; font-weight: 600;}

    /* تبويبات */
    .stTabs [data-baseweb="tab-list"] {background: #131826; border-radius: 14px; padding: 6px; gap: 4px;}
    .stTabs [data-baseweb="tab"] {background: transparent !important; color: #94a3b8 !important; border-radius: 10px !important; padding: 10px 18px !important;}
    .stTabs [aria-selected="true"] {background: #1f2937 !important; color: white !important;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# State
# ============================================================
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'chat' not in st.session_state:
    st.session_state.chat = []
if 'target_activity' not in st.session_state:
    st.session_state.target_activity = None
if 'fin_inputs' not in st.session_state:
    st.session_state.fin_inputs = {}
if 'uploaded_images' not in st.session_state:
    st.session_state.uploaded_images = []


# ============================================================
# المحرك (Mapbox)
# ============================================================
def extract_coords(url):
    url = url.strip()
    direct = re.match(r'^\s*(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)\s*$', url)
    if direct:
        return float(direct.group(1)), float(direct.group(2))
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(url, allow_redirects=True, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            url = r.url
        except Exception:
            return None, None
    for p in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)', r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)', r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)']:
        m = re.search(p, url)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def dist_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def search_mapbox(lat, lng, cat, limit=25):
    url = f"https://api.mapbox.com/search/searchbox/v1/category/{cat}"
    params = {"access_token": MAPBOX, "proximity": f"{lng},{lat}", "limit": limit, "language": "ar"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get('features', [])
    except Exception:
        pass
    return []


def process(features, tlat, tlng, max_km):
    places = []
    seen = set()
    for f in features:
        props = f.get('properties', {})
        name = props.get('name', '')
        if not name or name in seen:
            continue
        seen.add(name)
        coords = props.get('coordinates', {})
        plat = coords.get('latitude')
        plng = coords.get('longitude')
        if plat and plng:
            d = dist_km(tlat, tlng, plat, plng)
            if d <= max_km:
                places.append({'name': name, 'addr': props.get('full_address', ''), 'dist': d, 'lat': plat, 'lng': plng})
    places.sort(key=lambda x: x['dist'])
    return places


def comprehensive_scan(lat, lng, radius_km):
    results = {}
    for cat in CATEGORIES:
        feats = search_mapbox(lat, lng, cat, 25)
        places = process(feats, lat, lng, radius_km)
        if places:
            results[cat] = places
    return results


# ============================================================
# DNA الحي - جديد
# ============================================================
def neighborhood_dna(pbc):
    """تحليل ثقافة وطبيعة الحي بشكل متعدد الأبعاد"""
    food = sum(len(pbc.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])
    shopping = len(pbc.get('shopping', []))
    grocery = len(pbc.get('grocery', []))
    pharmacy = len(pbc.get('pharmacy', []))
    services = len(pbc.get('services', []))
    fuel = len(pbc.get('fuel', []))
    cafe = len(pbc.get('cafe', []))
    fast_food = len(pbc.get('fast_food', []))
    restaurant = len(pbc.get('restaurant', []))
    total = sum(len(v) for v in pbc.values())

    if total == 0:
        return {'family': 0, 'youth': 0, 'commercial': 0, 'food': 0, 'service': 0, 'main': 'غير محدد'}

    # نسب موزونة (كل نسبة تعكس مدى تواجد عوامل ذلك الطابع كنسبة من الإجمالي)
    # عائلي: بقالة + صيدلية + مطاعم (طابع عائلي قوي)
    family_raw = (grocery * 2.5 + pharmacy * 3.0 + restaurant * 1.5) / max(total, 1) * 35
    # شبابي: كافيهات + وجبات سريعة + تسوق
    youth_raw = (cafe * 2.5 + fast_food * 2.5 + shopping * 1.5) / max(total, 1) * 35
    # تجاري: تسوق + خدمات + إجمالي عالي
    commercial_raw = (shopping * 3.0 + services * 2.0) / max(total, 1) * 35 + min(35, total * 1.0)
    # طعام: نسبة الطعام من الإجمالي
    food_raw = (food / max(total, 1)) * 100
    # خدماتي: صيدليات + خدمات + وقود
    service_raw = (services * 2.0 + pharmacy * 2.0 + fuel * 2.5) / max(total, 1) * 35

    family = min(100, int(family_raw))
    youth = min(100, int(youth_raw))
    commercial = min(100, int(commercial_raw))
    food_score = min(100, int(food_raw))
    service = min(100, int(service_raw))

    scores = {'عائلي': family, 'شبابي': youth, 'تجاري': commercial, 'طعام': food_score, 'خدماتي': service}
    main = max(scores, key=scores.get)

    return {
        'family': family, 'youth': youth, 'commercial': commercial,
        'food': food_score, 'service': service, 'main': main
    }


# ============================================================
# مقارنة مع متوسط المدينة - جديد
# ============================================================
def city_comparison(total_places, radius_km):
    """مقارنة كثافة الموقع بمتوسط المدن السعودية"""
    area_km2 = math.pi * (radius_km ** 2)
    density = total_places / area_km2 if area_km2 > 0 else 0
    expected = SA_AVG_PLACES_PER_KM
    if density == 0:
        return None
    pct_diff = ((density - expected) / expected) * 100
    if pct_diff > 50:
        status = "أعلى بكثير من المتوسط"
        color = "#10b981"
    elif pct_diff > 15:
        status = "أعلى من المتوسط"
        color = "#3b82f6"
    elif pct_diff > -15:
        status = "قريب من المتوسط"
        color = "#94a3b8"
    elif pct_diff > -50:
        status = "أقل من المتوسط"
        color = "#f59e0b"
    else:
        status = "أقل بكثير"
        color = "#ef4444"
    return {
        'density': round(density, 1),
        'expected': expected,
        'pct_diff': round(pct_diff, 0),
        'status': status,
        'color': color,
    }


# ============================================================
# مؤشر الثقة - جديد
# ============================================================
def confidence_score(pbc, total_places, radius_km):
    """مؤشر ثقة في التحليل بناءً على اكتمال البيانات"""
    factors = []
    # عدد المحلات (الأكثر = ثقة أعلى)
    if total_places >= 50:
        factors.append(35)
    elif total_places >= 20:
        factors.append(25)
    elif total_places >= 10:
        factors.append(15)
    else:
        factors.append(5)
    # عدد الفئات النشطة
    active = len(pbc)
    if active >= 6:
        factors.append(30)
    elif active >= 4:
        factors.append(22)
    elif active >= 2:
        factors.append(12)
    else:
        factors.append(5)
    # حجم المنطقة (نطاق مناسب)
    if 0.5 <= radius_km <= 3:
        factors.append(20)
    elif radius_km <= 5:
        factors.append(15)
    else:
        factors.append(10)
    # تنوع الفئات (فيها مأكولات + خدمات أساسية)
    has_food = any(k in pbc for k in ['restaurant', 'cafe', 'fast_food'])
    has_essential = any(k in pbc for k in ['pharmacy', 'grocery'])
    diversity = (10 if has_food else 0) + (5 if has_essential else 0)
    factors.append(diversity)

    score = sum(factors)
    if score >= 80:
        level = "عالية"
        color = "#10b981"
    elif score >= 55:
        level = "جيدة"
        color = "#3b82f6"
    elif score >= 30:
        level = "متوسطة"
        color = "#f59e0b"
    else:
        level = "منخفضة"
        color = "#ef4444"
    return {'score': score, 'level': level, 'color': color, 'factors': {
        'محلات': factors[0], 'فئات': factors[1], 'نطاق': factors[2], 'تنوع': factors[3]
    }}


# ============================================================
# تحليل المواقف والوصول والذروة
# ============================================================
def analyze_parking_and_access(pbc):
    fuel_count = len(pbc.get('fuel', []))
    shopping = len(pbc.get('shopping', []))
    total = sum(len(v) for v in pbc.values())

    if shopping >= 5 or fuel_count >= 2:
        parking_status = "متوفرة بكثرة"
        parking_score = 90
        parking_detail = "وجود مراكز تسوق ومحطات وقود قريبة يدل على توفر مواقف عامة وخاصة"
    elif shopping >= 2 or fuel_count >= 1:
        parking_status = "متوفرة"
        parking_score = 70
        parking_detail = "مواقف متوفرة في المنطقة، يُفضل التحقق ميدانياً من السعة"
    elif total >= 10:
        parking_status = "محدودة"
        parking_score = 50
        parking_detail = "المنطقة تجارية لكن المواقف قد تكون محدودة في أوقات الذروة"
    else:
        parking_status = "غير مؤكدة"
        parking_score = 35
        parking_detail = "تحتاج زيارة ميدانية للتحقق من توفر المواقف"

    if fuel_count >= 2 and total >= 20:
        access_status = "ممتازة"
        access_score = 95
        access_detail = "محطات وقود متعددة + نشاط مرتفع = شوارع رئيسية وسهولة وصول عالية"
    elif fuel_count >= 1 or total >= 15:
        access_status = "جيدة جداً"
        access_score = 80
        access_detail = "الموقع على طرق رئيسية أو قريب منها"
    elif total >= 8:
        access_status = "جيدة"
        access_score = 65
        access_detail = "الوصول معقول، قد يحتاج المرور بطرق فرعية"
    else:
        access_status = "متوسطة - تحتاج تحقق"
        access_score = 45
        access_detail = "نشاط تجاري محدود قد يدل على موقع داخلي"

    food = sum(len(pbc.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])
    grocery = len(pbc.get('grocery', []))
    pharmacy = len(pbc.get('pharmacy', []))

    morning_score = min(100, fuel_count * 15 + grocery * 8 + pharmacy * 10)
    noon_score = min(100, food * 6 + shopping * 4)
    evening_score = min(100, food * 5 + shopping * 6 + grocery * 4 + total * 2)

    def lvl(s):
        if s >= 75: return "عالية جداً"
        if s >= 50: return "عالية"
        if s >= 30: return "متوسطة"
        if s >= 15: return "منخفضة"
        return "هادئة"

    peak_hours = {
        'morning': {'score': morning_score, 'level': lvl(morning_score), 'label': '🌅 الصباح (7-9 ص)'},
        'noon': {'score': noon_score, 'level': lvl(noon_score), 'label': '☀️ الظهر (12-2 ظ)'},
        'evening': {'score': evening_score, 'level': lvl(evening_score), 'label': '🌃 المساء (6-10 م)'},
    }
    busiest = max(peak_hours.values(), key=lambda x: x['score'])

    return {
        'parking_status': parking_status, 'parking_score': parking_score, 'parking_detail': parking_detail,
        'access_status': access_status, 'access_score': access_score, 'access_detail': access_detail,
        'peak_hours': peak_hours, 'busiest_period': busiest['label'],
    }


# ============================================================
# التحليل المالي
# ============================================================
def financial_analysis(rent_yearly, setup_cost, area_sqm, employees, avg_ticket, daily_customers, target_cat=None, total_places=0):
    if not (rent_yearly or setup_cost or avg_ticket or daily_customers):
        return None

    rent_yearly = rent_yearly or 0
    setup_cost = setup_cost or 0
    avg_ticket = avg_ticket or 0
    daily_customers = daily_customers or 0
    employees = employees or 0
    area_sqm = area_sqm or 0

    rent_monthly = rent_yearly / 12
    salary_per_employee = 4000
    salaries_monthly = employees * salary_per_employee
    utilities = max(800, area_sqm * 8)
    other_costs = (rent_monthly + salaries_monthly + utilities) * 0.10
    monthly_expenses = rent_monthly + salaries_monthly + utilities + other_costs

    monthly_revenue = avg_ticket * daily_customers * 30
    gross_margin = 0.35 if target_cat in ('restaurant', 'cafe', 'fast_food', 'grocery') else 0.50
    monthly_gross_profit = monthly_revenue * gross_margin

    net_profit_monthly = monthly_gross_profit - monthly_expenses
    total_capital = setup_cost + (rent_monthly * 3)

    breakeven_daily = math.ceil((monthly_expenses / gross_margin) / 30 / avg_ticket) if avg_ticket > 0 and gross_margin > 0 else None
    payback_months = math.ceil(total_capital / net_profit_monthly) if net_profit_monthly > 0 else None

    rent_per_sqm = None
    rent_assessment = None
    rent_status = None
    if rent_yearly > 0 and area_sqm > 0:
        rent_per_sqm = rent_yearly / area_sqm
        if total_places > 30:
            expected_min, expected_max = 800, 2500
            zone = "تجارية نشطة"
        elif total_places > 10:
            expected_min, expected_max = 500, 1500
            zone = "متوسطة"
        else:
            expected_min, expected_max = 200, 800
            zone = "هادئة"
        if rent_per_sqm < expected_min:
            rent_assessment, rent_status = "منخفض - فرصة جيدة", "good"
        elif rent_per_sqm <= expected_max:
            rent_assessment, rent_status = f"معقول للمنطقة ({zone})", "ok"
        else:
            rent_assessment, rent_status = "مرتفع - فاوض على السعر", "warn"

    if net_profit_monthly > 0 and payback_months and payback_months <= 24:
        verdict, verdict_status = "مجدي مالياً ✅", "good"
        verdict_detail = f"الأرباح تغطي رأس المال خلال {payback_months} شهر."
    elif net_profit_monthly > 0 and payback_months and payback_months <= 48:
        verdict, verdict_status = "مجدي لكن استرداد بطيء ⚠️", "ok"
        verdict_detail = f"يحتاج {payback_months} شهر لاسترداد رأس المال."
    elif net_profit_monthly > 0:
        verdict, verdict_status = "يحتاج دراسة دقيقة ⚠️", "warn"
        verdict_detail = "ربح ضعيف نسبة لرأس المال."
    else:
        verdict, verdict_status = "غير مجدي بالأرقام الحالية ❌", "danger"
        verdict_detail = f"المصاريف ({monthly_expenses:,.0f}) تتجاوز الأرباح ({monthly_gross_profit:,.0f})."

    return {
        'rent_monthly': rent_monthly, 'salaries_monthly': salaries_monthly,
        'utilities': utilities, 'other_costs': other_costs,
        'monthly_expenses': monthly_expenses, 'monthly_revenue': monthly_revenue,
        'monthly_gross_profit': monthly_gross_profit, 'net_profit_monthly': net_profit_monthly,
        'total_capital': total_capital, 'breakeven_daily': breakeven_daily,
        'payback_months': payback_months, 'rent_per_sqm': rent_per_sqm,
        'rent_assessment': rent_assessment, 'rent_status': rent_status,
        'verdict': verdict, 'verdict_status': verdict_status, 'verdict_detail': verdict_detail,
    }


# ============================================================
# التحليل الأساسي + Opportunity/Saturation/Demand
# ============================================================
def analyze(pbc, radius_km, target_cat=None):
    total = sum(len(v) for v in pbc.values())
    active = len(pbc)

    area_km2 = math.pi * (radius_km ** 2)
    density = total / area_km2 if area_km2 > 0 else 0
    if total == 0:
        area_type = "منطقة فارغة"
    elif density < 2:
        area_type = "منطقة هادئة"
    elif density < 8:
        area_type = "منطقة سكنية"
    elif density < 20:
        area_type = "متوسطة النشاط"
    elif density < 50:
        area_type = "تجارية نشطة"
    else:
        area_type = "تجارية مكتظة"

    food = sum(len(pbc.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])

    # المنافسة والمنافسين
    if target_cat:
        competitors = len(pbc.get(target_cat, []))
        if competitors == 0:
            comp_level, comp_score = "لا منافسة", 100
        elif competitors <= 2:
            comp_level, comp_score = "منخفض", 80
        elif competitors <= 5:
            comp_level, comp_score = "متوسط", 55
        elif competitors <= 10:
            comp_level, comp_score = "مرتفع", 30
        else:
            comp_level, comp_score = "مرتفع جداً", 12
    else:
        competitors = 0
        comp_level, comp_score = "غير محدد", 60

    # سهولة الوصول
    fuel_count = len(pbc.get('fuel', []))
    if fuel_count >= 2 or total > 20:
        accessibility, acc_score = "ممتازة", 90
    elif fuel_count >= 1 or total > 10:
        accessibility, acc_score = "جيدة", 70
    elif total > 5:
        accessibility, acc_score = "متوسطة", 55
    else:
        accessibility, acc_score = "تحتاج تحقق", 40

    # الحركة
    traffic_ind = food * 2 + len(pbc.get('shopping', [])) * 1.5 + len(pbc.get('services', []))
    if traffic_ind >= 30:
        traffic_level, traffic_score = "عالية جداً", 95
    elif traffic_ind >= 15:
        traffic_level, traffic_score = "عالية", 80
    elif traffic_ind >= 7:
        traffic_level, traffic_score = "متوسطة", 60
    elif traffic_ind >= 2:
        traffic_level, traffic_score = "منخفضة", 40
    else:
        traffic_level, traffic_score = "منخفضة جداً", 20

    # السكان
    pop_ind = len(pbc.get('grocery', [])) * 4 + len(pbc.get('pharmacy', [])) * 3
    if pop_ind >= 25:
        pop_density, pop_score = "عالية", 90
    elif pop_ind >= 12:
        pop_density, pop_score = "متوسطة", 65
    elif pop_ind >= 4:
        pop_density, pop_score = "منخفضة", 40
    else:
        pop_density, pop_score = "قليلة", 20
    est_pop = max(1000, pop_ind * 400) if pop_ind > 0 else 0

    # ===== المؤشرات الثلاث الجديدة (Opportunity / Saturation / Demand) =====
    if target_cat:
        # Saturation = نسبة الإشباع للنشاط المستهدف
        max_capacity = {'cafe': 8, 'restaurant': 10, 'fast_food': 8, 'pharmacy': 3, 'grocery': 5, 'shopping': 8, 'fuel': 4, 'services': 6}.get(target_cat, 6)
        saturation = min(100, int((competitors / max_capacity) * 100))
        # Demand = الطلب المتوقع (بناءً على الحركة + السكان + ثقافة الحي)
        demand = int((traffic_score * 0.4 + pop_score * 0.4 + acc_score * 0.2))
        # Opportunity = الفرصة (الطلب ناقص الإشباع المؤثر)
        opportunity = max(0, int(demand - saturation * 0.6))
    else:
        # بدون نشاط محدد، نحسب متوسط عام
        avg_per_cat = total / max(active, 1)
        saturation = min(100, int(avg_per_cat * 12))
        demand = int((traffic_score * 0.5 + pop_score * 0.5))
        opportunity = max(0, int(demand - saturation * 0.5))

    # ===== نقاط الاستثمار النهائية =====
    if target_cat:
        score = int(opportunity * 0.40 + traffic_score * 0.20 + acc_score * 0.15 + pop_score * 0.15 + comp_score * 0.10)
    else:
        score = int(demand * 0.35 + traffic_score * 0.25 + acc_score * 0.20 + pop_score * 0.20)

    # ===== القرار النهائي (جديد) =====
    if score >= 75:
        decision = "افتح بثقة"
        decision_emoji = "🟢"
        decision_color = "#10b981"
        decision_bg = "rgba(16,185,129,0.12)"
        decision_summary = "هذا الموقع يحقق معظم شروط النجاح. ابدأ مع التركيز على التميز."
    elif score >= 60:
        decision = "افتح بشروط"
        decision_emoji = "🟢"
        decision_color = "#10b981"
        decision_bg = "rgba(16,185,129,0.10)"
        decision_summary = "موقع جيد لكن يحتاج تخطيط دقيق ودراسة ميدانية قبل البدء."
    elif score >= 45:
        decision = "فكّر مرتين"
        decision_emoji = "🟡"
        decision_color = "#f59e0b"
        decision_bg = "rgba(245,158,11,0.10)"
        decision_summary = "الموقع متوسط - تأكد من ميزتك التنافسية قبل الاستثمار."
    elif score >= 30:
        decision = "غير منصوح به"
        decision_emoji = "🟠"
        decision_color = "#f97316"
        decision_bg = "rgba(249,115,22,0.10)"
        decision_summary = "مخاطر عالية. ابحث عن موقع أفضل قبل الالتزام."
    else:
        decision = "تجنّبه"
        decision_emoji = "🔴"
        decision_color = "#ef4444"
        decision_bg = "rgba(239,68,68,0.10)"
        decision_summary = "البيانات لا تدعم نجاح المشروع هنا."

    # الخدمات المفقودة
    missing = []
    for key, label in {'pharmacy': "صيدلية", 'grocery': "بقالة/سوبرماركت", 'fuel': "محطة وقود"}.items():
        if len(pbc.get(key, [])) == 0:
            missing.append(label)

    # نقاط القوة والضعف
    strengths, cautions = [], []
    if traffic_score >= 70: strengths.append("حركة مرور عالية")
    if acc_score >= 70: strengths.append("سهولة وصول ممتازة")
    if pop_score >= 65: strengths.append("كثافة سكانية جيدة")
    if comp_score >= 60: strengths.append("مستوى منافسة مقبول")
    if active >= 5: strengths.append("تنوع تجاري في المنطقة")
    if opportunity >= 60: strengths.append("فرصة سوقية مرتفعة")
    if comp_score < 40: cautions.append("منافسة مرتفعة في النشاط المستهدف")
    if traffic_score < 40: cautions.append("حركة منخفضة - يحتاج جذب نشط")
    if pop_score < 40: cautions.append("كثافة سكانية محدودة")
    if total < 5: cautions.append("بنية تجارية ضعيفة في المحيط")
    if saturation > 80: cautions.append(f"السوق مشبع بنسبة {saturation}%")
    if not strengths: strengths.append("منطقة بكر تحتاج دراسة")
    if not cautions: cautions.append("راقب الإيجارات في المنطقة")

    # أعلى المنافسين
    top_competitors = []
    if target_cat and target_cat in pbc:
        for p in pbc[target_cat][:5]:
            top_competitors.append({'name': p['name'], 'dist': round(p['dist'], 2)})

    return {
        'investment_score': score,
        'decision': decision, 'decision_emoji': decision_emoji,
        'decision_color': decision_color, 'decision_bg': decision_bg,
        'decision_summary': decision_summary,
        'opportunity_score': opportunity, 'saturation_score': saturation, 'demand_score': demand,
        'total_places': total, 'active_cat_count': active,
        'area_type': area_type,
        'competition_level': comp_level, 'competition_score': comp_score, 'competitor_count': competitors,
        'traffic_level': traffic_level, 'traffic_score': traffic_score,
        'accessibility': accessibility, 'accessibility_score': acc_score,
        'pop_density': pop_density, 'pop_score': pop_score, 'est_population': est_pop,
        'missing_services': missing,
        'top_competitors': top_competitors,
        'strengths': strengths, 'cautions': cautions,
        'target_cat': target_cat,
    }


# ============================================================
# اقتراحات الأنشطة (أفضل وأسوأ) + لماذا - جديد
# ============================================================
def rank_all_activities(pbc, dna, traffic_score, pop_score, acc_score):
    """صنّف كل النشاطات من الأفضل للأسوأ مع شرح"""
    candidates = {
        'cafe': {
            'demand_map': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'طعام': 60, 'خدماتي': 60, 'غير محدد': 70},
            'cap': 8,
        },
        'restaurant': {
            'demand_map': {'عائلي': 95, 'شبابي': 80, 'تجاري': 80, 'طعام': 55, 'خدماتي': 65, 'غير محدد': 80},
            'cap': 10,
        },
        'fast_food': {
            'demand_map': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'طعام': 60, 'خدماتي': 65, 'غير محدد': 75},
            'cap': 8,
        },
        'pharmacy': {
            'demand_map': {'عائلي': 95, 'شبابي': 70, 'تجاري': 70, 'طعام': 50, 'خدماتي': 90, 'غير محدد': 80},
            'cap': 3,
        },
        'grocery': {
            'demand_map': {'عائلي': 95, 'شبابي': 75, 'تجاري': 65, 'طعام': 55, 'خدماتي': 80, 'غير محدد': 80},
            'cap': 5,
        },
        'shopping': {
            'demand_map': {'عائلي': 75, 'شبابي': 90, 'تجاري': 85, 'طعام': 50, 'خدماتي': 65, 'غير محدد': 75},
            'cap': 8,
        },
        'services': {
            'demand_map': {'عائلي': 70, 'شبابي': 60, 'تجاري': 80, 'طعام': 50, 'خدماتي': 90, 'غير محدد': 70},
            'cap': 6,
        },
    }

    main_culture = dna['main']
    results = []
    for cat, info in candidates.items():
        existing = len(pbc.get(cat, []))
        demand = info['demand_map'].get(main_culture, 65)
        cap = info['cap']
        saturation = min(100, int((existing / cap) * 100)) if cap > 0 else 100
        opportunity = max(0, int(demand - saturation * 0.65))

        # تعديل بناءً على عوامل أخرى
        if traffic_score >= 70 and cat in ('cafe', 'restaurant', 'fast_food'):
            opportunity = min(100, opportunity + 8)
        if pop_score >= 65 and cat in ('grocery', 'pharmacy'):
            opportunity = min(100, opportunity + 10)
        if acc_score < 50:
            opportunity = max(0, opportunity - 10)

        # توليد "لماذا"
        reasons = []
        if existing == 0:
            reasons.append(f"لا يوجد {CATEGORIES[cat]['name']} في المنطقة")
        elif existing <= 2:
            reasons.append(f"منافسة محدودة ({existing} منافس)")
        elif existing > cap:
            reasons.append(f"السوق مشبع ({existing} منافس)")

        if main_culture in info['demand_map'] and info['demand_map'][main_culture] >= 80:
            reasons.append(f"الحي {main_culture} يدعم هذا النشاط")
        elif info['demand_map'].get(main_culture, 65) < 60:
            reasons.append(f"الحي {main_culture} لا يدعم بقوة")

        if traffic_score >= 70 and cat in ('cafe', 'restaurant', 'fast_food'):
            reasons.append("حركة مرور عالية تجذب العملاء")
        if pop_score >= 65 and cat in ('grocery', 'pharmacy'):
            reasons.append("كثافة سكانية تخلق طلب يومي")

        results.append({
            'cat_key': cat,
            'cat_name': CATEGORIES[cat]['name'],
            'icon': CATEGORIES[cat]['icon'],
            'demand': demand,
            'existing': existing,
            'saturation': saturation,
            'opportunity_score': opportunity,
            'reasons': reasons[:3] if reasons else ["تحليل قياسي"],
        })

    results.sort(key=lambda x: -x['opportunity_score'])
    # دائماً أعلى 3 (حتى لو فرصتها متوسطة)، ومن 4-5 لو فرصتهم >= 50
    best = results[:3]
    extras = [r for r in results[3:] if r['opportunity_score'] >= 50]
    best.extend(extras[:2])
    best_keys = {b['cat_key'] for b in best}
    # الأسوأ: الأقل فرصة فقط من الأنشطة اللي ما ظهرت في الأفضل
    worst_candidates = [r for r in results if r['cat_key'] not in best_keys and r['opportunity_score'] < 35]
    worst = worst_candidates[-5:] if len(worst_candidates) > 5 else worst_candidates
    return best, worst


# ============================================================
# تحليل الصور
# ============================================================
def analyze_image_with_ai(image, location_context=""):
    if not AI_AVAILABLE:
        return None
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""أنت محلل مواقع تجارية محترف في السعودية. حلل هذه الصورة وأعطني JSON فقط:
{{
  "area_description": "وصف موجز للمنطقة بالعربية (سطر واحد)",
  "traffic_level": "منخفض/متوسط/مرتفع/مرتفع جداً",
  "pedestrian_level": "منخفض/متوسط/مرتفع",
  "parking_availability": "ضعيفة/متوسطة/جيدة/ممتازة",
  "parking_detail": "وصف للمواقف الظاهرة",
  "road_access": "ضيق/متوسط/واسع",
  "neighborhood_type": "سكني/تجاري/مختلط/صناعي",
  "building_condition": "قديم/جديد/متوسط",
  "lighting": "ضعيفة/جيدة/ممتازة",
  "visible_businesses": ["محل 1", "محل 2"],
  "suitable_activities": ["نشاط 1", "نشاط 2"],
  "concerns": ["تحذير 1"],
  "strengths": ["نقطة قوة 1"],
  "overall_score": 7
}}
السياق: {location_context}
JSON فقط."""
        response = model.generate_content([prompt, image])
        text = response.text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except Exception:
        return None


def integrate_image_analysis(image_results, base_analysis):
    if not image_results:
        return base_analysis
    scores = [r.get('overall_score', 5) for r in image_results if isinstance(r.get('overall_score'), (int, float))]
    avg_image_score = sum(scores) / len(scores) if scores else 5
    extra_strengths = []
    extra_cautions = []
    for r in image_results:
        for s in (r.get('strengths') or [])[:2]:
            if s and s not in base_analysis['strengths']:
                extra_strengths.append(s)
        for c in (r.get('concerns') or [])[:2]:
            if c and c not in base_analysis['cautions']:
                extra_cautions.append(c)
    base_analysis['strengths'].extend(extra_strengths[:3])
    base_analysis['cautions'].extend(extra_cautions[:3])
    original_score = base_analysis['investment_score']
    base_analysis['investment_score'] = int(original_score * 0.85 + (avg_image_score * 10) * 0.15)
    base_analysis['image_avg_score'] = round(avg_image_score, 1)
    base_analysis['image_results'] = image_results
    return base_analysis


# ============================================================
# AI
# ============================================================
def ai_enhance(analysis, pbc, lat, lng):
    if not AI_AVAILABLE:
        return analysis
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
        prompt = f"""أنت خبير تحليل مواقع في السعودية. الموقع ({lat},{lng}).
الأنشطة: {summary}
نقاط الاستثمار: {analysis['investment_score']}/100
الفرصة: {analysis['opportunity_score']}, الإشباع: {analysis['saturation_score']}, الطلب: {analysis['demand_score']}
أعد JSON فقط:
{{"ai_recommendation":"توصية محسّنة في 3 جمل مفيدة وواقعية"}}"""
        text = model.generate_content(prompt).text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        d = json.loads(text.strip())
        analysis['ai_recommendation'] = d.get('ai_recommendation', '')
        analysis['ai_enhanced'] = True
    except Exception:
        analysis['ai_enhanced'] = False
    return analysis


def ai_chat(msg, analysis, pbc, lat, lng):
    if AI_AVAILABLE:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
            ctx = f"""موقع: {lat},{lng} | الأنشطة: {summary}
نقاط: {analysis['investment_score']}/100 | القرار: {analysis['decision']}
الفرصة: {analysis['opportunity_score']} | الإشباع: {analysis['saturation_score']} | الطلب: {analysis['demand_score']}
المنطقة: {analysis['area_type']} | الحركة: {analysis['traffic_level']}
السؤال: {msg}
أجب بالعربية بإيجاز ووضوح."""
            return model.generate_content(ctx).text.strip()
        except Exception:
            pass
    return f"📊 {analysis['decision']}: {analysis['decision_summary']}"


# ============================================================
# Top Bar
# ============================================================
badges = []
if MAPBOX:
    badges.append('<span class="badge-connected">● Mapbox</span>')
else:
    badges.append('<span class="badge-disconnected">○ Mapbox مفقود</span>')
if AI_AVAILABLE:
    badges.append('<span class="badge-connected">● AI</span>')
else:
    badges.append('<span class="badge-disconnected">○ AI غير مفعّل</span>')
api_badge = " ".join(badges)

st.markdown(f"""
<div class="top-bar">
    <div>
        <div class="brand">📊 GBI</div>
        <div class="brand-sub">الاستثمار الذكي</div>
    </div>
    <div class="top-bar-left">
        {api_badge}
        <div class="user-pill">
            <div class="user-avatar">G</div>
            <div>
                <div style="color:white; font-size:13px; font-weight:600;">المستثمر</div>
                <div style="color:#94a3b8; font-size:11px;">Guest</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-title">
    <h1>لوحة التحكم</h1>
    <p>نظرة عامة على الموقع المختار وتحليل الاستثمار الذكي</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Search Row
# ============================================================
sc1, sc2, sc3 = st.columns([5, 2, 2])
with sc1:
    url = st.text_input("url", placeholder="📍 أدخل رابط Google Maps أو إحداثيات (lat, lng)...", label_visibility="collapsed", key="url_input")
with sc2:
    radius = st.selectbox("النطاق", [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0], index=2, format_func=lambda x: f"📏 نطاق {x} كم", label_visibility="collapsed")
with sc3:
    analyze_btn = st.button("🚀 بدء التحليل", type="primary", use_container_width=True)

# الخيارات المتقدمة
with st.expander("⚙️ خيارات متقدمة - النشاط المستهدف + بيانات مالية + صور (اختياري)"):
    tab_act, tab_money, tab_img = st.tabs(["🎯 النشاط المستهدف", "💰 البيانات المالية", "📸 صور الموقع"])

    with tab_act:
        target_options = [("", "🤖 اقترح الأنسب تلقائياً")]
        for name, cat in ACTIVITY_TYPES.items():
            target_options.append((cat, f"{CATEGORIES[cat]['icon']} {name}"))
        target_idx = st.selectbox("target", options=range(len(target_options)),
                                  format_func=lambda i: target_options[i][1], label_visibility="collapsed", key="target_select")
        st.session_state.target_activity = target_options[target_idx][0] or None
        st.caption("اختر نوع نشاطك ليحلل النظام منافسيك بدقة، أو دعه يقترح الأنسب.")

    with tab_money:
        st.caption("📊 املأ ما تعرفه - النظام يحسب الجدوى المالية تلقائياً. الحقول الفارغة تُتجاهل.")
        fc1, fc2 = st.columns(2)
        with fc1:
            rent_yearly = st.number_input("💰 الإيجار السنوي المتوقع (ر.س)", min_value=0, value=0, step=5000, key="rent")
            setup_cost = st.number_input("🏗️ تكلفة تجهيز المحل (ر.س)", min_value=0, value=0, step=10000, key="setup")
            area_sqm = st.number_input("📏 مساحة المحل (م²)", min_value=0, value=0, step=10, key="area")
            employees = st.number_input("👥 عدد الموظفين", min_value=0, value=0, step=1, key="employees")
        with fc2:
            avg_ticket = st.number_input("💵 متوسط الفاتورة (ر.س)", min_value=0, value=0, step=5, key="ticket")
            daily_customers = st.number_input("📅 عدد العملاء يومياً", min_value=0, value=0, step=10, key="customers")

        st.session_state.fin_inputs = {
            'rent_yearly': rent_yearly, 'setup_cost': setup_cost, 'area_sqm': area_sqm,
            'employees': employees, 'avg_ticket': avg_ticket, 'daily_customers': daily_customers,
        }

    with tab_img:
        st.caption("📸 ارفع صور للموقع (واجهة المحل، الشارع، المنطقة) ليحللها AI ويربطها بالتحليل.")
        if not AI_AVAILABLE:
            st.warning("⚠️ تحليل الصور يحتاج GEMINI_API_KEY في Secrets.")
        uploaded_images = st.file_uploader("اختر صور", type=['jpg', 'jpeg', 'png'],
                                            accept_multiple_files=True, key="img_upload",
                                            label_visibility="collapsed")
        if uploaded_images:
            st.success(f"✅ {len(uploaded_images)} صورة جاهزة.")
        st.session_state.uploaded_images = uploaded_images or []

# ============================================================
# Analysis Trigger
# ============================================================
if analyze_btn:
    if not MAPBOX:
        st.error("⚠️ مفتاح MAPBOX_TOKEN غير موجود.")
    elif not url:
        st.error("⚠️ الرجاء إدخال رابط أو إحداثيات.")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.markdown('<p class="progress-msg">⏳ 5% - استخراج الإحداثيات...</p>', unsafe_allow_html=True)
        progress.progress(5)
        lat, lng = extract_coords(url)
        if not lat:
            progress.empty(); status.empty()
            st.error("❌ تعذّر استخراج الإحداثيات.")
        else:
            status.markdown(f'<p class="progress-msg">📍 15% - الموقع: {lat:.5f}, {lng:.5f}</p>', unsafe_allow_html=True)
            progress.progress(15)
            status.markdown('<p class="progress-msg">🔍 35% - البحث عبر Mapbox...</p>', unsafe_allow_html=True)
            progress.progress(35)
            pbc = comprehensive_scan(lat, lng, radius)
            status.markdown('<p class="progress-msg">🧠 55% - التحليل...</p>', unsafe_allow_html=True)
            progress.progress(55)
            a = analyze(pbc, radius, st.session_state.target_activity)

            # DNA الحي
            a['dna'] = neighborhood_dna(pbc)

            # ترتيب كل الأنشطة
            best_acts, worst_acts = rank_all_activities(pbc, a['dna'], a['traffic_score'], a['pop_score'], a['accessibility_score'])
            a['best_activities'] = best_acts
            a['worst_activities'] = worst_acts

            # مؤشر الثقة
            a['confidence'] = confidence_score(pbc, a['total_places'], radius)

            # مقارنة المدينة
            a['city_comparison'] = city_comparison(a['total_places'], radius)

            # مواقف وذروة
            status.markdown('<p class="progress-msg">🚗 70% - المواقف والوصول...</p>', unsafe_allow_html=True)
            progress.progress(70)
            a['site_details'] = analyze_parking_and_access(pbc)

            # مالي
            fin = st.session_state.get('fin_inputs', {})
            if fin and any(fin.values()):
                status.markdown('<p class="progress-msg">💰 80% - التحليل المالي...</p>', unsafe_allow_html=True)
                progress.progress(80)
                a['financial'] = financial_analysis(
                    fin.get('rent_yearly'), fin.get('setup_cost'), fin.get('area_sqm'),
                    fin.get('employees'), fin.get('avg_ticket'), fin.get('daily_customers'),
                    target_cat=st.session_state.target_activity, total_places=a['total_places']
                )

            # صور
            imgs = st.session_state.get('uploaded_images', [])
            if imgs and AI_AVAILABLE:
                status.markdown(f'<p class="progress-msg">📸 85% - تحليل {len(imgs)} صورة...</p>', unsafe_allow_html=True)
                progress.progress(85)
                image_results = []
                ctx = f"الموقع: {a['total_places']} محل، {a['area_type']}"
                for img_file in imgs:
                    try:
                        pil_img = Image.open(img_file)
                        result = analyze_image_with_ai(pil_img, ctx)
                        if result:
                            image_results.append(result)
                    except Exception:
                        continue
                if image_results:
                    a = integrate_image_analysis(image_results, a)

            if AI_AVAILABLE:
                status.markdown('<p class="progress-msg">✨ 95% - تحسين عبر AI...</p>', unsafe_allow_html=True)
                progress.progress(95)
                a = ai_enhance(a, pbc, lat, lng)
            st.session_state.analysis = {'lat': lat, 'lng': lng, 'radius': radius, 'places_by_cat': pbc, 'analysis': a}
            st.session_state.chat = []
            status.markdown('<p class="progress-msg">✅ 100% - اكتمل!</p>', unsafe_allow_html=True)
            progress.progress(100)
            time.sleep(0.3)
            progress.empty(); status.empty()
            st.rerun()

# ============================================================
# Display Results - بترتيب جديد (الأهم في الأعلى)
# ============================================================
if st.session_state.analysis:
    data = st.session_state.analysis
    a = data['analysis']
    pbc = data['places_by_cat']
    lat, lng, radius = data['lat'], data['lng'], data['radius']

    # ════════════════════════════════════════════════════
    # 1️⃣ القرار النهائي (الأهم) + نطاق التحليل + الثقة
    # ════════════════════════════════════════════════════
    score = a['investment_score']
    conf = a.get('confidence', {'score': 50, 'level': 'متوسطة', 'color': '#94a3b8'})

    ai_rec = a.get('ai_recommendation') if a.get('ai_enhanced') else a['decision_summary']

    # شريط معلومات سريع: النطاق + الثقة
    info_bar_html = f"""
    <div style="display:flex; gap:12px; margin-bottom:14px; flex-wrap:wrap;">
        <div style="background:#131826; border:1px solid #1f2937; padding:8px 16px; border-radius:999px; color:#94a3b8; font-size:13px;">
            📏 نطاق التحليل: <b style="color:white;">{radius} كم</b>
        </div>
        <div style="background:#131826; border:1px solid #1f2937; padding:8px 16px; border-radius:999px; color:#94a3b8; font-size:13px;">
            🎯 ثقة التحليل: <b style="color:{conf['color']};">{conf['score']}% ({conf['level']})</b>
        </div>
        <div style="background:#131826; border:1px solid #1f2937; padding:8px 16px; border-radius:999px; color:#94a3b8; font-size:13px;">
            📍 الموقع: <b style="color:white;">{lat:.4f}, {lng:.4f}</b>
        </div>
    </div>
    """
    st.markdown(info_bar_html, unsafe_allow_html=True)

    # بطاقة القرار الكبيرة
    decision_card = f"""
    <div class="verdict-card" style="border-color: {a['decision_color']}; background: linear-gradient(135deg, {a['decision_bg']} 0%, #131826 100%);">
        <div class="verdict-header">
            <div>
                <div style="color:#94a3b8; font-size:13px; font-weight:600; margin-bottom:4px;">🎯 القرار النهائي</div>
                <div class="verdict-title" style="color:{a['decision_color']};">{a['decision_emoji']} {a['decision']}</div>
                <div class="verdict-score">نقاط الاستثمار: <b style="color:white;">{score}/100</b></div>
            </div>
            <div class="verdict-emoji">{a['decision_emoji']}</div>
        </div>
        <div class="verdict-reason">{ai_rec}</div>
        <div class="verdict-tags">
    """
    for s in a['strengths'][:3]:
        decision_card += f'<span class="verdict-tag" style="border-right: 3px solid #10b981;">✓ {s}</span>'
    for c in a['cautions'][:2]:
        decision_card += f'<span class="verdict-tag" style="border-right: 3px solid #f59e0b;">⚠ {c}</span>'
    decision_card += "</div></div>"
    st.markdown(decision_card, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 2️⃣ المؤشرات الثلاث الرئيسية (Opportunity/Saturation/Demand)
    # ════════════════════════════════════════════════════
    st.markdown('<div class="section-title">📊 المؤشرات الأساسية للموقع</div>', unsafe_allow_html=True)

    opp = a['opportunity_score']
    sat = a['saturation_score']
    dem = a['demand_score']

    opp_c = "#10b981" if opp >= 60 else "#f59e0b" if opp >= 35 else "#ef4444"
    sat_c = "#ef4444" if sat >= 70 else "#f59e0b" if sat >= 40 else "#10b981"
    dem_c = "#10b981" if dem >= 65 else "#f59e0b" if dem >= 40 else "#ef4444"

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">🎯</div>
            <div class="big-metric-label">فرصة الدخول</div>
            <div class="big-metric-value" style="color:{opp_c};">{opp}<span style="font-size:20px;color:#64748b;">%</span></div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{opp}%; background:{opp_c};"></div></div>
            <div class="big-metric-sub">{'فرصة قوية للدخول' if opp>=60 else 'فرصة متوسطة' if opp>=35 else 'فرصة ضعيفة'}</div>
            </div>""", unsafe_allow_html=True)
    with bc2:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">📈</div>
            <div class="big-metric-label">تشبع السوق</div>
            <div class="big-metric-value" style="color:{sat_c};">{sat}<span style="font-size:20px;color:#64748b;">%</span></div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{sat}%; background:{sat_c};"></div></div>
            <div class="big-metric-sub">{'سوق مشبع' if sat>=70 else 'إشباع متوسط' if sat>=40 else 'سوق منفتح'}</div>
            </div>""", unsafe_allow_html=True)
    with bc3:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">🔥</div>
            <div class="big-metric-label">الطلب المتوقع</div>
            <div class="big-metric-value" style="color:{dem_c};">{dem}<span style="font-size:20px;color:#64748b;">%</span></div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{dem}%; background:{dem_c};"></div></div>
            <div class="big-metric-sub">{'طلب مرتفع' if dem>=65 else 'طلب متوسط' if dem>=40 else 'طلب ضعيف'}</div>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 3️⃣ أفضل الأنشطة المرتبة + لماذا
    # ════════════════════════════════════════════════════
    if a.get('best_activities'):
        st.markdown('<div class="section-title">✅ أفضل الأنشطة المقترحة (مرتبة بالفرصة)</div>', unsafe_allow_html=True)
        for i, act in enumerate(a['best_activities'], 1):
            sc_class = "" if act['opportunity_score'] >= 70 else "warn"
            reasons_html = " • ".join(act['reasons'])
            st.markdown(f"""<div class="activity-rank-card">
                <div class="rank-number">{i}</div>
                <div class="rank-content">
                    <div class="rank-name">{act['icon']} {act['cat_name']}</div>
                    <div class="rank-reason">💡 <b>لماذا؟</b> {reasons_html}</div>
                    <div style="display:flex; gap:14px; margin-top:8px; font-size:11px; color:#64748b;">
                        <span>📊 الطلب: {act['demand']}%</span>
                        <span>🏪 المنافسين: {act['existing']}</span>
                        <span>📈 الإشباع: {act['saturation']}%</span>
                    </div>
                </div>
                <div class="rank-score-pill {sc_class}">{act['opportunity_score']}%</div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 4️⃣ أسوأ الأنشطة (التي يجب تجنبها) - جديد
    # ════════════════════════════════════════════════════
    if a.get('worst_activities'):
        st.markdown('<div class="section-title">❌ أنشطة يُنصح بتجنبها هنا</div>', unsafe_allow_html=True)
        for act in a['worst_activities']:
            reasons_html = " • ".join(act['reasons'])
            st.markdown(f"""<div class="activity-rank-card" style="border-color:#7f1d1d;">
                <div class="rank-number" style="color:#ef4444;">✗</div>
                <div class="rank-content">
                    <div class="rank-name">{act['icon']} {act['cat_name']}</div>
                    <div class="rank-reason">⚠️ <b>السبب:</b> {reasons_html}</div>
                    <div style="display:flex; gap:14px; margin-top:8px; font-size:11px; color:#64748b;">
                        <span>📊 الطلب: {act['demand']}%</span>
                        <span>🏪 المنافسين: {act['existing']}</span>
                        <span>📈 الإشباع: {act['saturation']}%</span>
                    </div>
                </div>
                <div class="rank-score-pill bad">{act['opportunity_score']}%</div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 5️⃣ التحليل المالي (لو موجود)
    # ════════════════════════════════════════════════════
    if a.get('financial'):
        f = a['financial']
        st.markdown('<div class="section-title">💰 التحليل المالي والجدوى</div>', unsafe_allow_html=True)

        vcolors = {'good': '#10b981', 'ok': '#3b82f6', 'warn': '#f59e0b', 'danger': '#ef4444'}
        vbgs = {'good': 'rgba(16,185,129,0.12)', 'ok': 'rgba(59,130,246,0.12)', 'warn': 'rgba(245,158,11,0.12)', 'danger': 'rgba(239,68,68,0.12)'}
        vc = vcolors.get(f['verdict_status'], '#94a3b8')
        vbg = vbgs.get(f['verdict_status'], 'rgba(148,163,184,0.1)')
        st.markdown(f"""<div style="background:{vbg}; border:2px solid {vc}; border-radius:16px; padding:22px; margin-bottom:16px;">
            <div style="color:{vc}; font-size:24px; font-weight:800; margin-bottom:8px;">{f['verdict']}</div>
            <div style="color:#cbd5e1; font-size:14px;">{f['verdict_detail']}</div>
            </div>""", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-title">💰 رأس المال المطلوب</div>
                <div class="kpi-value-sm" style="color:white">{f['total_capital']:,.0f}</div>
                <div class="kpi-sub">ر.س (تجهيز + 3 شهور إيجار)</div></div>""", unsafe_allow_html=True)
        with m2:
            rc = "#10b981" if f['monthly_revenue'] > 0 else "#94a3b8"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-title">📈 الإيرادات الشهرية</div>
                <div class="kpi-value-sm" style="color:{rc}">{f['monthly_revenue']:,.0f}</div>
                <div class="kpi-sub">ر.س متوقعة</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-title">📉 المصاريف الشهرية</div>
                <div class="kpi-value-sm" style="color:#ef4444">{f['monthly_expenses']:,.0f}</div>
                <div class="kpi-sub">ر.س (إيجار+رواتب+فواتير)</div></div>""", unsafe_allow_html=True)
        with m4:
            pc = "#10b981" if f['net_profit_monthly'] > 0 else "#ef4444"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-title">💵 صافي الربح الشهري</div>
                <div class="kpi-value-sm" style="color:{pc}">{f['net_profit_monthly']:,.0f}</div>
                <div class="kpi-sub">ر.س متوقع</div></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        with d1:
            if f['breakeven_daily']:
                st.markdown(f"""<div class="info-card">
                    <div class="info-card-title">⚖️ نقطة التعادل</div>
                    <div style="color:#a855f7; font-size:28px; font-weight:800;">{f['breakeven_daily']}</div>
                    <div style="color:#94a3b8; font-size:13px;">عميل/يوم لتغطية المصاريف</div>
                    </div>""", unsafe_allow_html=True)
        with d2:
            if f['payback_months']:
                pbc_c = "#10b981" if f['payback_months'] <= 18 else "#f59e0b" if f['payback_months'] <= 36 else "#ef4444"
                yrs = f['payback_months'] / 12
                st.markdown(f"""<div class="info-card">
                    <div class="info-card-title">📅 استرداد رأس المال</div>
                    <div style="color:{pbc_c}; font-size:28px; font-weight:800;">{f['payback_months']} شهر</div>
                    <div style="color:#94a3b8; font-size:13px;">~{yrs:.1f} سنة</div>
                    </div>""", unsafe_allow_html=True)
        with d3:
            if f['rent_assessment']:
                rc = {'good': '#10b981', 'ok': '#3b82f6', 'warn': '#f59e0b'}.get(f['rent_status'], '#94a3b8')
                st.markdown(f"""<div class="info-card">
                    <div class="info-card-title">🏠 تقييم الإيجار</div>
                    <div style="color:{rc}; font-size:18px; font-weight:700;">{f['rent_assessment']}</div>
                    <div style="color:#94a3b8; font-size:13px;">{f['rent_per_sqm']:,.0f} ر.س / م² سنوياً</div>
                    </div>""", unsafe_allow_html=True)

        with st.expander("📊 تفاصيل المصاريف الشهرية"):
            st.markdown(f"""
            - 🏠 **الإيجار:** {f['rent_monthly']:,.0f} ر.س
            - 👥 **الرواتب:** {f['salaries_monthly']:,.0f} ر.س
            - 💡 **الفواتير:** {f['utilities']:,.0f} ر.س
            - 🔧 **مصاريف تشغيل متنوعة (10%):** {f['other_costs']:,.0f} ر.س
            - **─────**
            - **📉 الإجمالي:** {f['monthly_expenses']:,.0f} ر.س
            """)

    # ════════════════════════════════════════════════════
    # 6️⃣ مواقف + وصول + كثافة الذروة
    # ════════════════════════════════════════════════════
    if a.get('site_details'):
        sd = a['site_details']
        st.markdown('<div class="section-title">🚗 تحليل الموقع: المواقف والوصول والكثافة</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)

        with sc1:
            p_c = "#10b981" if sd['parking_score'] >= 70 else "#f59e0b" if sd['parking_score'] >= 50 else "#ef4444"
            st.markdown(f"""<div class="info-card">
                <div class="info-card-title">🅿️ مواقف السيارات</div>
                <div style="color:{p_c}; font-size:22px; font-weight:800; margin:8px 0;">{sd['parking_status']}</div>
                <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{sd['parking_score']}%; background:{p_c};"></div></div>
                <div style="color:#94a3b8; font-size:13px; line-height:1.6; margin-top:10px;">{sd['parking_detail']}</div>
                </div>""", unsafe_allow_html=True)

        with sc2:
            a_c = "#10b981" if sd['access_score'] >= 70 else "#f59e0b" if sd['access_score'] >= 50 else "#ef4444"
            st.markdown(f"""<div class="info-card">
                <div class="info-card-title">🚗 سهولة الوصول</div>
                <div style="color:{a_c}; font-size:22px; font-weight:800; margin:8px 0;">{sd['access_status']}</div>
                <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{sd['access_score']}%; background:{a_c};"></div></div>
                <div style="color:#94a3b8; font-size:13px; line-height:1.6; margin-top:10px;">{sd['access_detail']}</div>
                </div>""", unsafe_allow_html=True)

        with sc3:
            ph = sd['peak_hours']
            peak_html = '<div class="info-card"><div class="info-card-title">⏰ كثافة الذروة</div>'
            for key in ['morning', 'noon', 'evening']:
                period = ph[key]
                pc = "#10b981" if period['score'] >= 70 else "#f59e0b" if period['score'] >= 40 else "#94a3b8"
                peak_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #1f2937;">
                    <span style="color:#cbd5e1; font-size:13px;">{period['label']}</span>
                    <span style="color:{pc}; font-weight:700; font-size:13px;">{period['level']}</span>
                    </div>"""
            peak_html += f'<div style="color:#94a3b8; font-size:12px; margin-top:10px;">🔥 الأشد: <b style="color:#ef4444;">{sd["busiest_period"]}</b></div></div>'
            st.markdown(peak_html, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 7️⃣ DNA الحي - جديد
    # ════════════════════════════════════════════════════
    if a.get('dna'):
        d = a['dna']
        st.markdown('<div class="section-title">🧬 DNA الحي (تركيبة ثقافة المنطقة)</div>', unsafe_allow_html=True)
        dna_colors = {
            'family': ('عائلي', '#10b981'),
            'youth': ('شبابي', '#a855f7'),
            'commercial': ('تجاري', '#3b82f6'),
            'food': ('طعام', '#ef4444'),
            'service': ('خدماتي', '#f59e0b'),
        }
        dna_html = f'<div class="info-card"><div style="color:#94a3b8; font-size:13px; margin-bottom:12px;">الطابع الأقوى: <b style="color:white;">{d["main"]}</b></div>'
        for key, (label, color) in dna_colors.items():
            val = d.get(key, 0)
            dna_html += f"""<div class="dna-row">
                <span class="dna-label">{label}</span>
                <div class="dna-bar"><div class="dna-fill" style="width:{val}%; background:{color};"></div></div>
                <span class="dna-value" style="color:{color};">{val}%</span>
                </div>"""
        dna_html += '</div>'
        st.markdown(dna_html, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 8️⃣ مقارنة مع متوسط المدينة - جديد
    # ════════════════════════════════════════════════════
    if a.get('city_comparison'):
        cc = a['city_comparison']
        st.markdown('<div class="section-title">🏙️ مقارنة مع متوسط المدن السعودية</div>', unsafe_allow_html=True)
        sign = "+" if cc['pct_diff'] >= 0 else ""
        st.markdown(f"""<div class="info-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                <div>
                    <div style="color:#94a3b8; font-size:13px;">كثافة موقعك</div>
                    <div style="color:white; font-size:32px; font-weight:800;">{cc['density']} <span style="font-size:14px; color:#64748b;">محل/كم²</span></div>
                </div>
                <div>
                    <div style="color:#94a3b8; font-size:13px;">متوسط المدن السعودية</div>
                    <div style="color:#94a3b8; font-size:32px; font-weight:800;">{cc['expected']} <span style="font-size:14px;">محل/كم²</span></div>
                </div>
                <div style="text-align:center;">
                    <div style="color:{cc['color']}; font-size:32px; font-weight:900;">{sign}{cc['pct_diff']:.0f}%</div>
                    <div style="color:{cc['color']}; font-size:14px; font-weight:600;">{cc['status']}</div>
                </div>
            </div>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 9️⃣ المنافسين الأقرب
    # ════════════════════════════════════════════════════
    target = a.get('target_cat')
    if target and a.get('top_competitors'):
        st.markdown(f'<div class="section-title">🏆 أعلى المنافسين ({CATEGORIES[target]["name"]})</div>', unsafe_allow_html=True)
        comp_html = '<div class="info-card">'
        for i, c in enumerate(a['top_competitors'][:5], 1):
            comp_html += f'<div class="competitor-row"><span class="competitor-rank">{i}</span><span class="competitor-name">{c["name"]}</span><span class="competitor-dist">{c["dist"]} كم</span></div>'
        comp_html += '<div style="color:#64748b; font-size:12px; margin-top:12px;">ℹ️ تقييمات وعدد المراجعات قيد التطوير (Mapbox لا يوفرها)</div></div>'
        st.markdown(comp_html, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 🔟 تحليل الصور (لو موجود)
    # ════════════════════════════════════════════════════
    if a.get('image_results'):
        st.markdown('<div class="section-title">📸 تحليل صور الموقع بالذكاء الاصطناعي</div>', unsafe_allow_html=True)
        img_score = a.get('image_avg_score', 5)
        ic = "#10b981" if img_score >= 7 else "#f59e0b" if img_score >= 5 else "#ef4444"
        st.markdown(f"""<div style="background:rgba(168,85,247,0.08); border:1px solid rgba(168,85,247,0.3); border-radius:14px; padding:16px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#c4b5fd; font-weight:600;">✨ متوسط تقييم الصور</span>
                <span style="color:{ic}; font-size:24px; font-weight:800;">{img_score}/10</span>
            </div>
            <div style="color:#94a3b8; font-size:12px; margin-top:6px;">دُمجت نتائج الصور في نقاط الاستثمار العامة</div>
            </div>""", unsafe_allow_html=True)

        for idx, ir in enumerate(a['image_results'], 1):
            score_val = ir.get('overall_score', '-')
            with st.expander(f"📷 صورة {idx} — تقييم {score_val}/10"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown(f"**🌆 الوصف:** {ir.get('area_description', '-')}")
                    st.markdown(f"**🚦 الحركة:** {ir.get('traffic_level', '-')}")
                    st.markdown(f"**🚶 المشاة:** {ir.get('pedestrian_level', '-')}")
                    st.markdown(f"**🅿️ المواقف:** {ir.get('parking_availability', '-')}")
                    if ir.get('parking_detail'):
                        st.caption(f"💬 {ir['parking_detail']}")
                with cc2:
                    st.markdown(f"**🛣️ الشارع:** {ir.get('road_access', '-')}")
                    st.markdown(f"**🏘️ نوع الحي:** {ir.get('neighborhood_type', '-')}")
                    st.markdown(f"**🏗️ المباني:** {ir.get('building_condition', '-')}")
                    st.markdown(f"**💡 الإضاءة:** {ir.get('lighting', '-')}")
                if ir.get('visible_businesses'):
                    st.markdown(f"**🏪 محلات مرئية:** {', '.join(ir['visible_businesses'])}")
                if ir.get('suitable_activities'):
                    st.success("✨ **أنشطة مناسبة:** " + "، ".join(ir['suitable_activities']))
                if ir.get('strengths'):
                    for s in ir['strengths']:
                        st.markdown(f'<div style="color:#10b981; padding:4px 0;">✓ {s}</div>', unsafe_allow_html=True)
                if ir.get('concerns'):
                    for c in ir['concerns']:
                        st.markdown(f'<div style="color:#f59e0b; padding:4px 0;">⚠️ {c}</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 1️⃣1️⃣ الخريطة التفاعلية
    # ════════════════════════════════════════════════════
    st.markdown('<div class="section-title">🗺️ الخريطة التفاعلية</div>', unsafe_allow_html=True)
    m = folium.Map(location=[lat, lng], zoom_start=14, tiles='CartoDB dark_matter')
    folium.Circle([lat, lng], radius=radius * 1000, color='#ef4444', fill=True, fillOpacity=0.08, weight=2).add_to(m)
    folium.Marker([lat, lng], popup="<b>📍 الموقع المحدد</b>", icon=folium.Icon(color='red', icon='star', prefix='fa')).add_to(m)
    for cat_key, places in pbc.items():
        color = CATEGORIES[cat_key]['color']
        icon = CATEGORIES[cat_key]['icon']
        cat_name = CATEGORIES[cat_key]['name']
        for p in places:
            folium.CircleMarker([p['lat'], p['lng']], radius=6,
                popup=f"<b>{p['name']}</b><br>{icon} {cat_name}<br>📏 {p['dist']:.2f} كم",
                tooltip=f"{icon} {p['name']}", color=color, fill=True, fillColor=color, fillOpacity=0.85, weight=1.5).add_to(m)
    st_folium(m, width=None, height=500, returned_objects=[], key="main_map")

    # ════════════════════════════════════════════════════
    # 1️⃣2️⃣ الرسوم البيانية
    # ════════════════════════════════════════════════════
    if pbc:
        st.markdown('<div class="section-title">📈 توزيع الأنشطة وتحليل العوامل</div>', unsafe_allow_html=True)
        chart_col, factors_col = st.columns(2)
        with chart_col:
            st.markdown('<div class="info-card-title">🍩 توزيع الأنشطة</div>', unsafe_allow_html=True)
            labels = [CATEGORIES[k]['name'] for k in pbc.keys()]
            values = [len(v) for v in pbc.values()]
            colors_list = [CATEGORIES[k]['color'] for k in pbc.keys()]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55,
                marker=dict(colors=colors_list, line=dict(color='#0a0e1a', width=2)),
                textfont=dict(color='white', size=12), textinfo='percent')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                showlegend=True, legend=dict(font=dict(color='white', size=11)),
                height=380, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        with factors_col:
            st.markdown('<div class="info-card-title">🎯 تحليل العوامل</div>', unsafe_allow_html=True)
            radar_labels = ['الحركة', 'الكثافة', 'الفرصة', 'الوصول', 'الطلب']
            radar_values = [a['traffic_score'], a['pop_score'], a['opportunity_score'], a['accessibility_score'], a['demand_score']]
            fig2 = go.Figure(data=go.Scatterpolar(r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]],
                fill='toself', fillcolor='rgba(239,68,68,0.25)', line=dict(color='#ef4444', width=2)))
            fig2.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
                angularaxis=dict(tickfont=dict(color='white', size=11)), bgcolor='rgba(0,0,0,0)'),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=380)
            st.plotly_chart(fig2, use_container_width=True)

    # ════════════════════════════════════════════════════
    # 1️⃣3️⃣ الخدمات المفقودة
    # ════════════════════════════════════════════════════
    if a['missing_services']:
        st.markdown('<div class="section-title">🔍 خدمات أساسية مفقودة</div>', unsafe_allow_html=True)
        miss_html = '<div class="info-card">'
        for s in a['missing_services']:
            miss_html += f'<div style="background:rgba(245,158,11,0.1); color:#f59e0b; padding:10px 14px; border-radius:10px; margin-bottom:8px;">⚠️ {s}</div>'
        miss_html += '</div>'
        st.markdown(miss_html, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 1️⃣4️⃣ تفاصيل المحلات
    # ════════════════════════════════════════════════════
    if pbc:
        st.markdown('<div class="section-title">🏪 تفاصيل المحلات في المنطقة</div>', unsafe_allow_html=True)
        for cat_key, places in sorted(pbc.items(), key=lambda x: -len(x[1])):
            cat = CATEGORIES[cat_key]
            with st.expander(f"{cat['icon']} {cat['name']} — {len(places)} محل"):
                for p in places[:25]:
                    addr = f"<br><span style='color:#64748b; font-size:12px;'>📍 {p['addr']}</span>" if p.get('addr') else ""
                    st.markdown(f"<div style='padding:8px 0; border-bottom:1px solid #1f2937;'><b style='color:#e2e8f0;'>{p['name']}</b> <span style='color:#f59e0b;'>{p['dist']:.2f} كم</span>{addr}</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 1️⃣5️⃣ المستشار الذكي
    # ════════════════════════════════════════════════════
    st.markdown('<div class="section-title">💬 اسأل المستشار</div>', unsafe_allow_html=True)
    if not AI_AVAILABLE:
        st.info("ℹ️ المستشار يعمل بالقواعد الذكية. لتفعيل AI أضف GEMINI_API_KEY.")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.write(msg["content"])
    user_msg = st.chat_input("اسأل عن الموقع، الفرص، المنافسة...")
    if user_msg:
        st.session_state.chat.append({"role": "user", "content": user_msg})
        with st.spinner("جارٍ التفكير..."):
            response = ai_chat(user_msg, a, pbc, lat, lng)
        st.session_state.chat.append({"role": "assistant", "content": response})
        st.rerun()

else:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; background:#131826; border-radius:18px; border:1px solid #1f2937; margin-top:24px;">
        <div style="font-size:64px; margin-bottom:20px;">🗺️</div>
        <h2 style="color:white; margin-bottom:10px;">ابدأ بتحليل موقعك</h2>
        <p style="color:#94a3b8; margin-bottom:24px;">أدخل رابط Google Maps أو إحداثيات أعلاه واضغط "بدء التحليل".</p>
    </div>
    """, unsafe_allow_html=True)
