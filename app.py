import streamlit as st
import os, re, requests, json, math
from dotenv import load_dotenv
from supabase import create_client
import google.generativeai as genai
from PIL import Image
import folium
from streamlit_folium import st_folium

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
MAPBOX = os.getenv("MAPBOX_TOKEN")

st.set_page_config(page_title="GBI", page_icon="🌍", layout="wide")
st.markdown("<style>body,.stApp{direction:rtl;text-align:right}</style>", unsafe_allow_html=True)

if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'analysis_b' not in st.session_state:
    st.session_state.analysis_b = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'project_details' not in st.session_state:
    st.session_state.project_details = {}

st.title("🌍 GBI - مستشار الاستثمار الذكي")
st.caption("تحليل، خرائط، مقارنة، محادثة - كل شيء بالذكاء الاصطناعي")
st.markdown("---")


def extract_coords(url):
    if 'goo.gl' in url or 'maps.app' in url:
        r = requests.get(url, allow_redirects=True, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        url = r.url
    for p in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)', r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)']:
        m = re.search(p, url)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def distance_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def search_mapbox(lat, lng, category, limit=20):
    url = f"https://api.mapbox.com/search/searchbox/v1/category/{category}"
    params = {"access_token": MAPBOX, "proximity": f"{lng},{lat}", "limit": limit, "language": "ar"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get('features', [])
    except:
        pass
    return []


def process_places(features, target_lat, target_lng, max_km=5):
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
            dist = distance_km(target_lat, target_lng, plat, plng)
            if dist <= max_km:
                places.append({'name': name, 'address': props.get('full_address', ''), 'distance': dist, 'lat': plat, 'lng': plng})
    places.sort(key=lambda x: x['distance'])
    return places


def comprehensive_scan(lat, lng, radius_km=2):
    categories = {"restaurant": ("🍽️ مطاعم", "red"), "cafe": ("☕ مقاهي", "orange"), "fast_food": ("🍔 وجبات سريعة", "darkred"), "shopping": ("🛍️ تسوق", "purple"), "fuel": ("⛽ محطات وقود", "black"), "pharmacy": ("💊 صيدليات", "green"), "grocery": ("🛒 بقالات", "blue"), "services": ("🔧 خدمات", "gray"), "entertainment": ("🎮 ترفيه", "pink"), "school": ("🏫 مدارس", "darkblue"), "hospital": ("🏥 مستشفيات", "darkgreen"), "bank": ("🏦 بنوك", "cadetblue")}
    results = {}
    for cat, (name_ar, color) in categories.items():
        features = search_mapbox(lat, lng, cat, limit=15)
        places = process_places(features, lat, lng, max_km=radius_km)
        if places:
            results[cat] = {'name_ar': name_ar, 'color': color, 'places': places, 'count': len(places)}
    return results


def ai_discover(scan_results, lat, lng, radius_km):
    model = genai.GenerativeModel('gemini-2.5-flash')
    summary = "\n".join([f"- {data['name_ar']}: {data['count']} محل" for cat, data in scan_results.items()])
    prompt = f"""أنت مستشار استثماري. موقع ({lat}, {lng}) نطاق {radius_km} كم.
الأنشطة:
{summary}
JSON: {{"area_character": "وصف", "activity_level": "نشطة/متوسطة/هادئة", "market_saturation": "مشبع/متوسط/فرص", "missing_services": ["خدمة"], "best_opportunities": [{{"activity": "نشاط", "reason": "السبب", "success_probability": 75, "competition_level": "منخفض", "investment_size": "متوسط", "target_customers": "الفئة"}}], "warnings": ["تحذير"], "overall_recommendation": "ملخص"}}
JSON فقط."""
    text = model.generate_content(prompt).text.strip()
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]
    try:
        return json.loads(text.strip())
    except:
        return None


def ai_chat(user_message, context):
    model = genai.GenerativeModel('gemini-2.5-flash')
    scan_text = "\n".join([f"- {d['name_ar']}: {d['count']} محل" for c, d in context.get('scan', {}).items()])
    prompt = f"""مستشار استثماري. موقع: {context.get('lat')}, {context.get('lng')} نطاق {context.get('radius')} كم
الأنشطة: {scan_text}
تفاصيل: {json.dumps(context.get('details', {}), ensure_ascii=False)}
سؤال: {user_message}
أجب باحترافية بالعربية."""
    return model.generate_content(prompt).text


def ai_compare(a, b):
    model = genai.GenerativeModel('gemini-2.5-flash')
    a_sum = f"A ({a['lat']}, {a['lng']}):\n" + "\n".join([f"- {d['name_ar']}: {d['count']}" for c, d in a['scan'].items()])
    b_sum = f"B ({b['lat']}, {b['lng']}):\n" + "\n".join([f"- {d['name_ar']}: {d['count']}" for c, d in b['scan'].items()])
    prompt = f"""قارن موقعين.
{a_sum}
{b_sum}
JSON: {{"winner": "A أو B", "winner_reason": "السبب", "a_strengths": ["قوة"], "a_weaknesses": ["ضعف"], "b_strengths": ["قوة"], "b_weaknesses": ["ضعف"], "recommended_activities_a": ["نشاط"], "recommended_activities_b": ["نشاط"], "final_verdict": "ملخص"}}
JSON فقط."""
    text = model.generate_content(prompt).text.strip()
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]
    try:
        return json.loads(text.strip())
    except:
        return None


def create_map(lat, lng, scan, radius_km, label="الموقع"):
    m = folium.Map(location=[lat, lng], zoom_start=14, tiles='OpenStreetMap')
    folium.Marker([lat, lng], popup=f"<b>📍 {label}</b><br>{lat:.4f}, {lng:.4f}", tooltip=f"📍 {label}", icon=folium.Icon(color='red', icon='star', prefix='fa')).add_to(m)
    folium.Circle(location=[lat, lng], radius=radius_km * 1000, color='red', fill=True, fillOpacity=0.05, popup=f"نطاق {radius_km} كم").add_to(m)
    for cat, data in scan.items():
        for p in data['places']:
            folium.CircleMarker(location=[p['lat'], p['lng']], radius=6, popup=f"<b>{p['name']}</b><br>{data['name_ar']}<br>📏 {p['distance']:.2f} كم", tooltip=p['name'], color=data['color'], fill=True, fillColor=data['color'], fillOpacity=0.7).add_to(m)
    return m

✅ Part 1 savedcat
