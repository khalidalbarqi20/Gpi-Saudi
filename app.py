"""
GBI - تحليل المواقع التجارية
نسخة موحّدة: التصميم الاحترافي + محرك Mapbox الشغّال
- البحث عبر Mapbox Search Box API (تغطية ممتازة في السعودية)
- تحليل قائم على القواعد + AI اختياري عبر Gemini
- خريطة تفاعلية + رسوم بيانية
ملف واحد مستقل (لا يحتاج analyzer.py أو categories.py)
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
# الفئات (canonical Mapbox category IDs + اسم عربي + لون + أيقونة)
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

# النشاط المستهدف → فئة Mapbox للمنافسين
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

# ============================================================
# CSS - التصميم الاحترافي
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
    .brand {font-size: 28px; font-weight: 900; color: #ef4444; letter-spacing: 2px; display: flex; align-items: center; gap: 8px;}
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

    .stButton button {background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important; color: white !important; border: none !important; padding: 14px 24px !important; border-radius: 14px !important; font-weight: 700 !important; font-size: 15px !important; width: 100% !important; height: 56px !important; box-shadow: 0 4px 16px rgba(239,68,68,0.3) !important; transition: all 0.2s !important;}
    .stButton button:hover {transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;}

    .kpi-card {background: #131826; border: 1px solid #1f2937; border-radius: 18px; padding: 20px; transition: transform 0.2s;}
    .kpi-card:hover {transform: translateY(-2px);}
    .kpi-header {display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;}
    .kpi-title {color: #94a3b8; font-size: 13px; font-weight: 500;}
    .kpi-icon {width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 22px;}
    .kpi-value {color: white; font-size: 26px; font-weight: 800; margin: 4px 0;}
    .kpi-value-sm {color: white; font-size: 20px; font-weight: 700; margin: 4px 0;}
    .kpi-sub {color: #64748b; font-size: 12px;}

    .info-card {background: #131826; border: 1px solid #1f2937; border-radius: 18px; padding: 22px; height: 100%;}
    .info-card-title {color: white; font-size: 17px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 8px;}

    .ai-card {background: linear-gradient(135deg, #1a2238 0%, #131826 100%); border: 1px solid rgba(139,92,246,0.3); border-radius: 18px; padding: 22px;}
    .ai-title-row {display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;}
    .ai-title {color: #c4b5fd; font-size: 15px; font-weight: 600;}
    .ai-headline {color: #10b981; font-size: 24px; font-weight: 800; margin: 8px 0 12px 0;}
    .ai-headline.warning {color: #f59e0b;}
    .ai-headline.danger {color: #ef4444;}
    .ai-desc {color: #cbd5e1; font-size: 13px; line-height: 1.7;}

    .point-section {margin-top: 14px;}
    .point-title {color: #94a3b8; font-size: 13px; margin-bottom: 8px; font-weight: 600;}
    .point-item {display: flex; align-items: center; gap: 8px; color: #e2e8f0; font-size: 13px; padding: 4px 0;}
    .point-good {color: #10b981; font-size: 14px;}
    .point-warn {color: #f59e0b; font-size: 14px;}

    .competitor-row {display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: rgba(31,41,55,0.5); border-radius: 10px; margin-bottom: 8px; font-size: 13px;}
    .competitor-rank {color: #64748b; font-weight: 700; width: 24px;}
    .competitor-name {color: #e2e8f0; flex: 1; padding: 0 8px;}
    .competitor-dist {color: #f59e0b; font-weight: 600;}

    .quick-row {display: flex; align-items: center; justify-content: space-between; padding: 11px 0; border-bottom: 1px solid #1f2937;}
    .quick-row:last-child {border-bottom: none;}
    .quick-label {color: #94a3b8; font-size: 13px; display: flex; align-items: center; gap: 8px;}
    .quick-value {color: white; font-size: 14px; font-weight: 600;}
    .quick-value.green {color: #10b981;}

    div[data-testid="stExpander"] {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important;}
    div[data-testid="stExpander"] summary {color: white !important; font-weight: 600 !important;}

    .stProgress > div > div > div > div {background: linear-gradient(90deg, #ef4444 0%, #f87171 100%) !important;}
    .progress-msg {color: #fca5a5; font-size: 14px; text-align: center; margin: 8px 0; font-weight: 500;}

    .stAlert {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 12px !important; color: #e2e8f0 !important;}
    [data-testid="stChatMessage"] {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important; margin-bottom: 8px !important;}
    [data-testid="stChatInput"] textarea {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 14px !important;}

    .section-title {color: white; font-size: 20px; font-weight: 700; margin: 28px 0 14px 0; display: flex; align-items: center; gap: 10px;}
    .section-title::before {content: ''; width: 4px; height: 22px; background: #ef4444; border-radius: 2px;}

    .activity-suggest-card {background: linear-gradient(135deg, #1e293b 0%, #131826 100%); border: 1px solid #334155; border-radius: 16px; padding: 18px; margin-bottom: 12px; transition: all 0.2s;}
    .activity-suggest-card:hover {border-color: #ef4444; transform: translateY(-2px);}
    .activity-suggest-header {display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;}
    .activity-name {color: white; font-size: 17px; font-weight: 700;}
    .activity-score {background: rgba(16,185,129,0.15); color: #10b981; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 700;}
    .activity-reason {color: #cbd5e1; font-size: 13px; line-height: 1.6; margin-top: 8px;}
    .activity-meta {display: flex; gap: 14px; margin-top: 10px; font-size: 12px; color: #94a3b8;}
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


# ============================================================
# المحرك: Mapbox (من النسخة الشغّالة)
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
# التحليل القائم على القواعد
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
        area_type = "منطقة متوسطة النشاط"
    elif density < 50:
        area_type = "منطقة تجارية نشطة"
    else:
        area_type = "منطقة تجارية مكتظة"

    food = sum(len(pbc.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])
    shopping = sum(len(pbc.get(k, [])) for k in ['shopping'])
    services = sum(len(pbc.get(k, [])) for k in ['pharmacy', 'fuel', 'services', 'grocery'])

    culture = {
        'عائلي': len(pbc.get('grocery', [])) * 1.2 + len(pbc.get('pharmacy', [])) * 1.1,
        'شبابي': len(pbc.get('cafe', [])) * 1.5 + len(pbc.get('fast_food', [])) * 1.3,
        'تجاري': shopping * 1.4 + len(pbc.get('services', [])) * 1.0,
        'طعام': food * 1.1,
    }
    neighborhood = max(culture, key=culture.get) if total > 0 else "غير محدد"

    if target_cat:
        competitors = len(pbc.get(target_cat, []))
        if competitors == 0:
            comp_level, comp_score = "لا منافسة", 100
        elif competitors <= 2:
            comp_level, comp_score = "منخفض", 75
        elif competitors <= 5:
            comp_level, comp_score = "متوسط", 50
        elif competitors <= 10:
            comp_level, comp_score = "مرتفع", 25
        else:
            comp_level, comp_score = "مرتفع جداً", 10
    else:
        competitors = 0
        if active == 0 or total / max(active, 1) < 3:
            comp_level, comp_score = "منخفض", 75
        elif total / max(active, 1) < 7:
            comp_level, comp_score = "متوسط", 55
        else:
            comp_level, comp_score = "مرتفع", 30

    fuel_count = len(pbc.get('fuel', []))
    if fuel_count >= 2 or total > 20:
        accessibility, acc_score = "ممتازة", 90
    elif fuel_count >= 1 or total > 10:
        accessibility, acc_score = "جيدة", 70
    elif total > 5:
        accessibility, acc_score = "متوسطة", 55
    else:
        accessibility, acc_score = "تحتاج تحقق", 40

    traffic_ind = food * 2 + shopping * 1.5 + services
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

    if target_cat:
        score = int(comp_score * 0.30 + traffic_score * 0.25 + acc_score * 0.15 + pop_score * 0.15 + min(active * 12, 100) * 0.15)
    else:
        score = int(traffic_score * 0.30 + acc_score * 0.20 + pop_score * 0.25 + comp_score * 0.10 + min(active * 12, 100) * 0.15)

    missing = []
    for key, label in {'pharmacy': "صيدلية", 'grocery': "بقالة/سوبرماركت", 'fuel': "محطة وقود"}.items():
        if len(pbc.get(key, [])) == 0:
            missing.append(label)

    opp_by_culture = {
        'عائلي': ['مطعم عائلي', 'سوبر ماركت', 'مركز ترفيه أطفال'],
        'شبابي': ['كافيه متخصص', 'مطعم وجبات سريعة', 'صالة رياضية'],
        'تجاري': ['مكتب خدمات', 'مقهى عمل', 'مطعم سريع'],
        'طعام': ['حلويات/مخبز', 'مقهى بمفهوم مختلف', 'مطبخ سحابي'],
    }
    opportunities = opp_by_culture.get(neighborhood, ['دراسة ميدانية للموقع'])

    if score >= 70:
        recommendation = f"موقع ممتاز! فرصة استثمارية قوية في {area_type}. الحركة {traffic_level} والمنافسة {comp_level}."
        risk = "منخفض"
    elif score >= 50:
        recommendation = f"موقع جيد بإمكانيات واعدة. {area_type} مع منافسة {comp_level}. يُنصح بدراسة ميدانية."
        risk = "متوسط"
    else:
        recommendation = f"موقع يحتاج دراسة دقيقة. النشاط محدود ({total} محل في {radius_km} كم)."
        risk = "متوسط-عالي"

    strengths, cautions = [], []
    if traffic_score >= 70:
        strengths.append("حركة مرور عالية")
    if acc_score >= 70:
        strengths.append("سهولة وصول ممتازة")
    if pop_score >= 65:
        strengths.append("كثافة سكانية جيدة")
    if comp_score >= 60:
        strengths.append("مستوى منافسة مقبول")
    if active >= 5:
        strengths.append("تنوع تجاري في المنطقة")
    if comp_score < 40:
        cautions.append("منافسة مرتفعة")
    if traffic_score < 40:
        cautions.append("حركة منخفضة - يحتاج جذب نشط")
    if pop_score < 40:
        cautions.append("كثافة سكانية محدودة")
    if total < 5:
        cautions.append("بنية تجارية ضعيفة في المحيط")
    if not strengths:
        strengths.append("منطقة بكر تحتاج دراسة")
    if not cautions:
        cautions.append("راقب الإيجارات في المنطقة")

    top_competitors = []
    if target_cat and target_cat in pbc:
        for p in pbc[target_cat][:5]:
            top_competitors.append({'name': p['name'], 'dist': round(p['dist'], 2)})

    return {
        'investment_score': score, 'total_places': total, 'active_cat_count': active,
        'area_type': area_type, 'neighborhood_type': neighborhood,
        'competition_level': comp_level, 'competition_score': comp_score, 'competitor_count': competitors,
        'traffic_level': traffic_level, 'traffic_score': traffic_score,
        'accessibility': accessibility, 'accessibility_score': acc_score,
        'pop_density': pop_density, 'pop_score': pop_score, 'est_population': est_pop,
        'opportunities': opportunities, 'missing_services': missing,
        'top_competitors': top_competitors, 'recommendation': recommendation,
        'risk_level': risk, 'strengths': strengths, 'cautions': cautions,
        'target_cat': target_cat,
    }


def suggest_best_activity(pbc, analysis):
    neighborhood = analysis['neighborhood_type']
    total = analysis['total_places']
    candidates = {
        'cafe': {'demand': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'طعام': 60, 'غير محدد': 70}, 'cap': 8},
        'restaurant': {'demand': {'عائلي': 95, 'شبابي': 80, 'تجاري': 80, 'طعام': 55, 'غير محدد': 80}, 'cap': 10},
        'fast_food': {'demand': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'طعام': 60, 'غير محدد': 75}, 'cap': 8},
        'pharmacy': {'demand': {'عائلي': 95, 'شبابي': 70, 'تجاري': 70, 'طعام': 50, 'غير محدد': 80}, 'cap': 3},
        'grocery': {'demand': {'عائلي': 95, 'شبابي': 75, 'تجاري': 65, 'طعام': 55, 'غير محدد': 80}, 'cap': 5},
        'shopping': {'demand': {'عائلي': 75, 'شبابي': 90, 'تجاري': 85, 'طعام': 50, 'غير محدد': 75}, 'cap': 8},
    }
    scores = []
    for cat, info in candidates.items():
        existing = len(pbc.get(cat, []))
        demand = info['demand'].get(neighborhood, 65)
        cap = info['cap']
        saturation = min(100, (existing / cap) * 100) if cap > 0 else 100
        opportunity = max(0, demand - saturation * 0.7)
        if total < 5 and cat in ('grocery', 'pharmacy', 'restaurant'):
            opportunity += 15
        if existing == 0:
            reason = f"لا يوجد {CATEGORIES[cat]['name']} في المنطقة، والطلب في حي {neighborhood} مرتفع"
        elif saturation < 40:
            reason = f"{existing} منافس فقط - السوق غير مشبع وملاءمته لحي {neighborhood} جيدة"
        elif saturation < 70:
            reason = f"{existing} منافسين - السوق متوسط الإشباع، تحتاج تميّز"
        else:
            reason = f"{existing} منافس - السوق مشبع، يحتاج خدمة فريدة"
        scores.append({
            'cat_key': cat, 'cat_name': CATEGORIES[cat]['name'], 'icon': CATEGORIES[cat]['icon'],
            'demand': demand, 'existing': existing, 'saturation': int(saturation),
            'opportunity_score': int(opportunity), 'reason': reason,
        })
    scores.sort(key=lambda x: -x['opportunity_score'])
    return scores[:3]


# ============================================================
# AI
# ============================================================
def ai_enhance(analysis, pbc, lat, lng):
    if not AI_AVAILABLE:
        return analysis
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
        prompt = f"""أنت خبير تحليل مواقع تجارية في السعودية. الموقع ({lat},{lng}).
الأنشطة المحيطة: {summary}
نوع الحي: {analysis['neighborhood_type']} | نقاط أولية: {analysis['investment_score']}/100
أعد JSON فقط:
{{"ai_recommendation":"توصية محسّنة في جملتين","growth_potential":"منخفض/متوسط/عالي"}}"""
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
نقاط: {analysis['investment_score']}/100 | المنطقة: {analysis['area_type']} | الحي: {analysis['neighborhood_type']}
المنافسة: {analysis['competition_level']} | الحركة: {analysis['traffic_level']}
السؤال: {msg}
أجب بالعربية بإيجاز ووضوح مستنداً للأرقام أعلاه."""
            return model.generate_content(ctx).text.strip()
        except Exception:
            pass
    # fallback
    m = msg.lower()
    total = analysis['total_places']
    if 'منافس' in m:
        t = analysis.get('target_cat')
        if t and t in pbc:
            n = len(pbc[t])
            if n == 0:
                return f"ممتاز! لا يوجد منافسون مباشرون في {CATEGORIES[t]['name']}."
            return f"يوجد {n} منافسين في {CATEGORIES[t]['name']}. أقربهم: {pbc[t][0]['name']} على بعد {pbc[t][0]['dist']:.2f} كم."
        return f"مستوى المنافسة الإجمالي: {analysis['competition_level']}."
    if 'كم محل' in m or 'عدد' in m:
        return f"يوجد {total} محل في المحيط، موزعة على {analysis['active_cat_count']} فئة."
    if 'فرص' in m or 'نشاط' in m:
        return "أفضل الفرص:\n" + "\n".join(f"• {o}" for o in analysis['opportunities'][:3])
    if 'حركة' in m:
        return f"مستوى الحركة: {analysis['traffic_level']}."
    return f"📊 {analysis['recommendation']}\n\nاسأل عن: المنافسة، الفرص، الحركة، السكان."


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
    <div class="top-bar-right">
        <div>
            <div class="brand">📊 GBI</div>
            <div class="brand-sub">الاستثمار الذكي</div>
        </div>
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

# النشاط المستهدف
with st.expander("⚙️ خيارات متقدمة: حدد النشاط المستهدف (اختياري)"):
    target_options = [("", "🤖 اقترح الأنسب تلقائياً")]
    for name, cat in ACTIVITY_TYPES.items():
        target_options.append((cat, f"{CATEGORIES[cat]['icon']} {name}"))
    target_idx = st.selectbox("target", options=range(len(target_options)),
                              format_func=lambda i: target_options[i][1], label_visibility="collapsed", key="target_select")
    st.session_state.target_activity = target_options[target_idx][0] or None

# ============================================================
# Analysis Trigger
# ============================================================
if analyze_btn:
    if not MAPBOX:
        st.error("⚠️ مفتاح MAPBOX_TOKEN غير موجود. أضفه في Secrets.")
    elif not url:
        st.error("⚠️ الرجاء إدخال رابط Google Maps أو إحداثيات.")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.markdown('<p class="progress-msg">⏳ 5% - استخراج الإحداثيات...</p>', unsafe_allow_html=True)
        progress.progress(5)
        lat, lng = extract_coords(url)
        if not lat:
            progress.empty(); status.empty()
            st.error("❌ تعذّر استخراج الإحداثيات. جرّب إحداثيات مباشرة مثل: 24.7136, 46.6753")
        else:
            status.markdown(f'<p class="progress-msg">📍 20% - الموقع: {lat:.5f}, {lng:.5f}</p>', unsafe_allow_html=True)
            progress.progress(20)
            status.markdown('<p class="progress-msg">🔍 45% - البحث عن المحلات عبر Mapbox...</p>', unsafe_allow_html=True)
            progress.progress(45)
            pbc = comprehensive_scan(lat, lng, radius)
            status.markdown('<p class="progress-msg">🧠 70% - التحليل...</p>', unsafe_allow_html=True)
            progress.progress(70)
            a = analyze(pbc, radius, st.session_state.target_activity)
            a['suggested_activities'] = suggest_best_activity(pbc, a)
            if AI_AVAILABLE:
                status.markdown('<p class="progress-msg">✨ 90% - تحسين عبر AI...</p>', unsafe_allow_html=True)
                progress.progress(90)
                a = ai_enhance(a, pbc, lat, lng)
            st.session_state.analysis = {'lat': lat, 'lng': lng, 'radius': radius, 'places_by_cat': pbc, 'analysis': a}
            st.session_state.chat = []
            status.markdown('<p class="progress-msg">✅ 100% - اكتمل!</p>', unsafe_allow_html=True)
            progress.progress(100)
            time.sleep(0.3)
            progress.empty(); status.empty()
            st.rerun()

# ============================================================
# Display Results
# ============================================================
if st.session_state.analysis:
    data = st.session_state.analysis
    a = data['analysis']
    pbc = data['places_by_cat']
    lat, lng, radius = data['lat'], data['lng'], data['radius']

    score = a['investment_score']
    score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
    score_bg = "rgba(16,185,129,0.15)" if score >= 70 else "rgba(245,158,11,0.15)" if score >= 50 else "rgba(239,68,68,0.15)"

    # KPI Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><div>
            <div class="kpi-title">نقاط الاستثمار</div>
            <div class="kpi-value" style="color:{score_color}">{score}<span style="font-size:14px; color:#64748b;">/100</span></div>
            </div><div class="kpi-icon" style="background:{score_bg}; color:{score_color}">📈</div></div>
            <div class="kpi-sub">{'فرصة ممتازة' if score>=70 else 'تحتاج دراسة' if score>=50 else 'مخاطرة عالية'}</div></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><div>
            <div class="kpi-title">حركة المرور</div>
            <div class="kpi-value-sm" style="color:#a855f7">{a['traffic_level']}</div>
            </div><div class="kpi-icon" style="background:rgba(168,85,247,0.15); color:#a855f7">🚦</div></div>
            <div class="kpi-sub">مستوى الحركة المقدّر</div></div>""", unsafe_allow_html=True)
    with k3:
        comp_color = "#10b981" if a['competition_score'] >= 60 else "#f59e0b" if a['competition_score'] >= 35 else "#ef4444"
        st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><div>
            <div class="kpi-title">المنافسة</div>
            <div class="kpi-value-sm" style="color:{comp_color}">{a['competition_level']}</div>
            </div><div class="kpi-icon" style="background:rgba(245,158,11,0.15); color:#f59e0b">🏆</div></div>
            <div class="kpi-sub">مستوى المنافسة</div></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><div>
            <div class="kpi-title">الكثافة السكانية</div>
            <div class="kpi-value-sm" style="color:#3b82f6">{a['pop_density']}</div>
            </div><div class="kpi-icon" style="background:rgba(59,130,246,0.15); color:#3b82f6">👥</div></div>
            <div class="kpi-sub">~{a['est_population']:,} نسمة مقدّرة</div></div>""", unsafe_allow_html=True)
    with k5:
        acc_color = "#10b981" if a['accessibility_score'] >= 70 else "#f59e0b"
        st.markdown(f"""<div class="kpi-card"><div class="kpi-header"><div>
            <div class="kpi-title">سهولة الوصول</div>
            <div class="kpi-value-sm" style="color:{acc_color}">{a['accessibility']}</div>
            </div><div class="kpi-icon" style="background:rgba(16,185,129,0.15); color:#10b981">🚗</div></div>
            <div class="kpi-sub">سهولة الوصول للموقع</div></div>""", unsafe_allow_html=True)

    # Map + Quick stats + AI
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    map_col, info_col, ai_col = st.columns([3, 2, 3])

    with info_col:
        st.markdown(f"""<div class="info-card"><div class="info-card-title">📊 مؤشرات سريعة</div>
            <div class="quick-row"><span class="quick-label">👥 السكان المقدّرون</span><span class="quick-value">{a['est_population']:,}</span></div>
            <div class="quick-row"><span class="quick-label">🏪 إجمالي المحلات</span><span class="quick-value">{a['total_places']}</span></div>
            <div class="quick-row"><span class="quick-label">📂 الفئات النشطة</span><span class="quick-value">{a['active_cat_count']}</span></div>
            <div class="quick-row"><span class="quick-label">🏙️ طبيعة المنطقة</span><span class="quick-value">{a['area_type']}</span></div>
            <div class="quick-row"><span class="quick-label">🏘️ ثقافة الحي</span><span class="quick-value">{a['neighborhood_type']}</span></div>
            <div class="quick-row"><span class="quick-label">⚠️ مستوى المخاطرة</span><span class="quick-value">{a['risk_level']}</span></div>
            </div>""", unsafe_allow_html=True)

    with map_col:
        st.markdown('<div class="info-card-title" style="margin-right: 12px;">🗺️ الخريطة التفاعلية</div>', unsafe_allow_html=True)
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
        st_folium(m, width=None, height=480, returned_objects=[], key="main_map")

    with ai_col:
        headline_class = "" if score >= 70 else "warning" if score >= 50 else "danger"
        headline_text = "فرصة استثمار ممتازة" if score >= 70 else "فرصة تحتاج دراسة" if score >= 50 else "موقع قليل النشاط"
        rec_text = a.get('ai_recommendation') if a.get('ai_enhanced') and a.get('ai_recommendation') else a['recommendation']
        strengths_html = "".join(f'<div class="point-item"><span class="point-good">✓</span> {s}</div>' for s in a['strengths'])
        cautions_html = "".join(f'<div class="point-item"><span class="point-warn">⚠</span> {c}</div>' for c in a['cautions'])
        ai_label = "توصية الذكاء الاصطناعي" if a.get('ai_enhanced') else "توصية النظام الذكي"
        st.markdown(f"""<div class="ai-card">
            <div class="ai-title-row"><div class="ai-title">✨ {ai_label}</div>
            <div style="background:rgba(139,92,246,0.2); color:#c4b5fd; padding:4px 10px; border-radius:999px; font-size:11px;">{'AI' if a.get('ai_enhanced') else 'Rule-Based'}</div></div>
            <div class="ai-headline {headline_class}">{headline_text}</div>
            <div class="ai-desc">{rec_text}</div>
            <div class="point-section"><div class="point-title">نقاط القوة</div>{strengths_html}</div>
            <div class="point-section"><div class="point-title">نقاط الانتباه</div>{cautions_html}</div>
            </div>""", unsafe_allow_html=True)

    # Best activities
    if a.get('suggested_activities') and not a.get('target_cat'):
        st.markdown('<div class="section-title">🎯 أفضل الأنشطة المقترحة لهذا الموقع</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, s in enumerate(a['suggested_activities'][:3]):
            with cols[i]:
                st.markdown(f"""<div class="activity-suggest-card">
                    <div class="activity-suggest-header"><div class="activity-name">{s['icon']} {s['cat_name']}</div>
                    <div class="activity-score">{s['opportunity_score']}/100</div></div>
                    <div class="activity-reason">{s['reason']}</div>
                    <div class="activity-meta"><span>📊 الطلب: {s['demand']}%</span><span>🏪 المنافسين: {s['existing']}</span><span>📈 الإشباع: {s['saturation']}%</span></div>
                    </div>""", unsafe_allow_html=True)

    # Charts
    if pbc:
        st.markdown('<div class="section-title">📈 توزيع الأنشطة والتحليلات</div>', unsafe_allow_html=True)
        chart_col, factors_col, comp_col = st.columns([1, 1, 1])
        with chart_col:
            st.markdown('<div class="info-card-title">🍩 توزيع الأنشطة التجارية</div>', unsafe_allow_html=True)
            labels = [CATEGORIES[k]['name'] for k in pbc.keys()]
            values = [len(v) for v in pbc.values()]
            colors_list = [CATEGORIES[k]['color'] for k in pbc.keys()]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55,
                marker=dict(colors=colors_list, line=dict(color='#0a0e1a', width=2)),
                textfont=dict(color='white', size=12), textinfo='percent', hoverinfo='label+value+percent')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                showlegend=True, legend=dict(font=dict(color='white', size=11), orientation='v', x=1.0, y=0.5),
                height=380, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        with factors_col:
            st.markdown('<div class="info-card-title">🎯 تحليل العوامل</div>', unsafe_allow_html=True)
            radar_labels = ['حركة المرور', 'الكثافة السكانية', 'المنافسة', 'سهولة الوصول', 'القوة الشرائية']
            radar_values = [a['traffic_score'], a['pop_score'], a['competition_score'], a['accessibility_score'], min(100, a['active_cat_count'] * 12)]
            fig2 = go.Figure(data=go.Scatterpolar(r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]],
                fill='toself', fillcolor='rgba(239,68,68,0.25)', line=dict(color='#ef4444', width=2), marker=dict(size=8, color='#ef4444')))
            fig2.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='rgba(148,163,184,0.2)'),
                angularaxis=dict(tickfont=dict(color='white', size=11), gridcolor='rgba(148,163,184,0.2)'), bgcolor='rgba(0,0,0,0)'),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=380, margin=dict(t=30, b=30, l=40, r=40))
            st.plotly_chart(fig2, use_container_width=True)
        with comp_col:
            target = a.get('target_cat')
            if target and a.get('top_competitors'):
                st.markdown(f'<div class="info-card-title">🏆 أعلى المنافسين ({CATEGORIES[target]["name"]})</div>', unsafe_allow_html=True)
                html = "<div>"
                for i, c in enumerate(a['top_competitors'][:5], 1):
                    html += f'<div class="competitor-row"><span class="competitor-rank">{i}</span><span class="competitor-name">{c["name"]}</span><span class="competitor-dist">{c["dist"]} كم</span></div>'
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="info-card-title">🏪 أكثر الفئات نشاطاً</div>', unsafe_allow_html=True)
                top_cats = sorted(pbc.items(), key=lambda x: -len(x[1]))[:5]
                html = "<div>"
                for i, (ck, places) in enumerate(top_cats, 1):
                    html += f'<div class="competitor-row"><span class="competitor-rank">{i}</span><span class="competitor-name">{CATEGORIES[ck]["icon"]} {CATEGORIES[ck]["name"]}</span><span class="competitor-dist">{len(places)} محل</span></div>'
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

    # Opportunities & Missing
    st.markdown('<div class="section-title">💡 الفرص والخدمات المفقودة</div>', unsafe_allow_html=True)
    opp_col, miss_col = st.columns(2)
    with opp_col:
        opp_html = '<div class="info-card"><div class="info-card-title">🎯 أفضل الفرص</div>'
        for o in a['opportunities']:
            opp_html += f'<div style="background:rgba(16,185,129,0.1); color:#10b981; padding:10px 14px; border-radius:10px; margin-bottom:8px; font-size:14px;">✨ {o}</div>'
        opp_html += '</div>'
        st.markdown(opp_html, unsafe_allow_html=True)
    with miss_col:
        miss_html = '<div class="info-card"><div class="info-card-title">🔍 خدمات مفقودة</div>'
        if a['missing_services']:
            for s in a['missing_services']:
                miss_html += f'<div style="background:rgba(245,158,11,0.1); color:#f59e0b; padding:10px 14px; border-radius:10px; margin-bottom:8px; font-size:14px;">⚠️ {s}</div>'
        else:
            miss_html += '<div style="background:rgba(16,185,129,0.1); color:#10b981; padding:10px 14px; border-radius:10px; font-size:14px;">✓ الخدمات الأساسية موجودة</div>'
        miss_html += '</div>'
        st.markdown(miss_html, unsafe_allow_html=True)

    # Detailed places
    if pbc:
        st.markdown('<div class="section-title">🏪 تفاصيل المحلات في المنطقة</div>', unsafe_allow_html=True)
        for cat_key, places in sorted(pbc.items(), key=lambda x: -len(x[1])):
            cat = CATEGORIES[cat_key]
            with st.expander(f"{cat['icon']} {cat['name']} — {len(places)} محل"):
                for p in places[:25]:
                    addr = f"<br><span style='color:#64748b; font-size:12px;'>📍 {p['addr']}</span>" if p.get('addr') else ""
                    st.markdown(f"<div style='padding:8px 0; border-bottom:1px solid #1f2937;'><b style='color:#e2e8f0;'>{p['name']}</b> <span style='color:#f59e0b;'>{p['dist']:.2f} كم</span>{addr}</div>", unsafe_allow_html=True)

    # AI Chat
    st.markdown('<div class="section-title">💬 اسأل المستشار</div>', unsafe_allow_html=True)
    if not AI_AVAILABLE:
        st.info("ℹ️ المستشار يعمل بوضع القواعد الذكية. لتفعيل AI الكامل أضف GEMINI_API_KEY.")
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
        <p style="color:#94a3b8; margin-bottom:24px;">أدخل رابط Google Maps أعلاه واضغط "بدء التحليل".</p>
    </div>
    """, unsafe_allow_html=True)
