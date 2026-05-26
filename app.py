import streamlit as st
import os, re, requests, json, math
from dotenv import load_dotenv
import google.generativeai as genai
import folium
from streamlit_folium import st_folium

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MAPBOX = os.getenv("MAPBOX_TOKEN")

st.set_page_config(page_title="GBI", page_icon="X", layout="wide")
st.markdown("<style>body,.stApp{direction:rtl;text-align:right}</style>", unsafe_allow_html=True)

if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'chat' not in st.session_state:
    st.session_state.chat = []

st.title("GBI - مستشار الاستثمار الذكي")
st.caption("Mapbox + Gemini AI")
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


def dist_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def search_mapbox(lat, lng, cat, limit=20):
    url = f"https://api.mapbox.com/search/searchbox/v1/category/{cat}"
    params = {"access_token": MAPBOX, "proximity": f"{lng},{lat}", "limit": limit, "language": "ar"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get('features', [])
    except:
        pass
    return []


def process(features, tlat, tlng, max_km=5):
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


def scan_area(lat, lng, radius=2):
    cats = {"restaurant": ("مطاعم", "red"), "cafe": ("مقاهي", "orange"), "shopping": ("تسوق", "purple"), "fuel": ("وقود", "black"), "pharmacy": ("صيدليات", "green"), "grocery": ("بقالات", "blue")}
    results = {}
    for c, (n, col) in cats.items():
        f = search_mapbox(lat, lng, c, 15)
        p = process(f, lat, lng, radius)
        if p:
            results[c] = {'name': n, 'color': col, 'places': p, 'count': len(p)}
    return results


def make_map(lat, lng, scan, radius):
    m = folium.Map(location=[lat, lng], zoom_start=14)
    folium.Marker([lat, lng], popup="الموقع", icon=folium.Icon(color='red')).add_to(m)
    folium.Circle([lat, lng], radius=radius*1000, color='red', fill=True, fillOpacity=0.05).add_to(m)
    for c, d in scan.items():
        for p in d['places']:
            folium.CircleMarker([p['lat'], p['lng']], radius=6, popup=f"{p['name']} - {p['dist']:.2f} كم", color=d['color'], fill=True).add_to(m)
    return m


def ai_chat(msg, ctx):
    model = genai.GenerativeModel('gemini-2.5-flash')
    txt = "\n".join([f"- {d['name']}: {d['count']}" for c, d in ctx.get('scan', {}).items()])
    prompt = f"مستشار استثماري. موقع: {ctx.get('lat')}, {ctx.get('lng')}. الأنشطة:\n{txt}\nسؤال: {msg}\nأجب بالعربية."
    return model.generate_content(prompt).text


tab1, tab2, tab3 = st.tabs(["التحليل", "الخريطة", "المحادثة"])

with tab1:
    url = st.text_input("رابط Google Maps:")
    radius = st.slider("النطاق كم:", 0.5, 10.0, 2.0, 0.5)
    if st.button("ابدأ التحليل", type="primary"):
        if url:
            with st.spinner("استخراج..."):
                lat, lng = extract_coords(url)
            if lat:
                st.success(f"الموقع: {lat:.4f}, {lng:.4f}")
                with st.spinner("مسح..."):
                    scan = scan_area(lat, lng, radius)
                st.session_state.analysis = {'lat': lat, 'lng': lng, 'radius': radius, 'scan': scan}
                total = sum(d['count'] for d in scan.values())
                st.metric("إجمالي المحلات", total)
                for c, d in scan.items():
                    with st.expander(f"{d['name']} ({d['count']})"):
                        for p in d['places']:
                            st.write(f"- {p['name']} - {p['dist']:.2f} كم")

with tab2:
    if st.session_state.analysis:
        a = st.session_state.analysis
        m = make_map(a['lat'], a['lng'], a['scan'], a['radius'])
        st_folium(m, width=None, height=500, returned_objects=[])
    else:
        st.warning("حلل موقع أولاً")

with tab3:
    if st.session_state.analysis:
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        if ui := st.chat_input("اسأل..."):
            st.session_state.chat.append({"role": "user", "content": ui})
            with st.spinner("..."):
                resp = ai_chat(ui, st.session_state.analysis)
                st.session_state.chat.append({"role": "assistant", "content": resp})
            st.rerun()
    else:
        st.warning("حلل موقع أولاً")

st.markdown("---")
st.caption("GBI - Mapbox + Gemini AI")
