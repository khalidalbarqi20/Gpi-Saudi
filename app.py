import streamlit as st
import os, re, requests, json, math
import concurrent.futures
import time
from dotenv import load_dotenv
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MAPBOX = os.getenv("MAPBOX_TOKEN")

st.set_page_config(page_title="GBI", page_icon="📊", layout="wide", initial_sidebar_state="collapsed", menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

st.markdown("""
<style>
    #MainMenu, header, footer, .stDeployButton {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, ._profileContainer_gzau3_53, ._terminalButton_rix23_138 {display: none !important;}
    div[data-testid="stStatusWidget"], div[data-testid="stDecoration"] {display: none !important;}
    .stApp > header {background-color: transparent;}
    iframe[title="streamlit_app"] + div, div[class*="viewerBadge"] {display: none !important;}
    a[href*="streamlit.io"], a[href*="share.streamlit"] {display: none !important;}
    
    body, .stApp {direction: rtl; text-align: right; background: linear-gradient(135deg, #1a0033 0%, #2d1b4e 50%, #1a0033 100%) !important; color: #fff;}
    
    .main-title {text-align: center; padding: 40px 20px 30px 20px;}
    .main-title h1 {color: white; margin: 0; font-size: 72px; font-weight: bold; letter-spacing: 8px; text-shadow: 0 4px 20px rgba(168, 85, 247, 0.4);}
    .main-title p {color: rgba(255,255,255,0.7); margin: 10px 0 0 0; font-size: 14px;}
    
    .metric-card {background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.2); padding: 20px; border-radius: 15px; text-align: center;}
    .metric-card h3 {color: #C084FC; margin: 0 0 10px 0; font-size: 14px;}
    .metric-card .value {color: white; font-size: 32px; font-weight: bold; margin: 5px 0;}
    .metric-card .sub {color: rgba(255,255,255,0.6); font-size: 12px;}
    
    .section-title {color: #C084FC; font-size: 22px; font-weight: bold; margin: 25px 0 15px 0; border-right: 4px solid #A855F7; padding-right: 10px;}
    
    div[data-testid="stTextInput"] input {background: rgba(168, 85, 247, 0.1) !important; color: white !important; border: 1px solid rgba(168, 85, 247, 0.3) !important; border-radius: 10px !important; padding: 12px !important;}
    
    div[data-testid="stSelectbox"] > div {background: rgba(168, 85, 247, 0.1) !important; border: 1px solid rgba(168, 85, 247, 0.3) !important; border-radius: 10px !important;}
    
    .stButton button {background: linear-gradient(90deg, #A855F7 0%, #C084FC 100%) !important; color: white !important; border: none !important; padding: 12px 30px !important; border-radius: 10px !important; font-weight: bold !important; width: 100%; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);}
    
    div[data-testid="stExpander"] {background: rgba(168, 85, 247, 0.05); border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 10px;}
    
    .stAlert {background: rgba(168, 85, 247, 0.1) !important; border: 1px solid rgba(168, 85, 247, 0.3) !important;}
    
    .stProgress > div > div > div > div {background: linear-gradient(90deg, #A855F7 0%, #C084FC 100%) !important;}
    
    .progress-text {color: #C084FC; font-size: 16px; text-align: center; margin: 10px 0; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'chat' not in st.session_state:
    st.session_state.chat = []

st.markdown('<div class="main-title"><h1>GBI</h1><p>تحليل شامل للمواقع التجارية واكتشاف الفرص الاستثمارية</p></div>', unsafe_allow_html=True)


def extract_coords(url):
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(url, allow_redirects=True, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
            url = r.url
        except:
            return None, None
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


def search_places(lat, lng, cat, limit=15):
    url = f"https://api.mapbox.com/search/searchbox/v1/category/{cat}"
    params = {"access_token": MAPBOX, "proximity": f"{lng},{lat}", "limit": limit, "language": "ar"}
    try:
        r = requests.get(url, params=params, timeout=10)
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


def make_map(lat, lng, scan, radius):
    m = folium.Map(location=[lat, lng], zoom_start=14, tiles='CartoDB dark_matter')
    folium.Marker([lat, lng], popup="<b>الموقع</b>", icon=folium.Icon(color='purple', icon='star', prefix='fa')).add_to(m)
    folium.Circle([lat, lng], radius=radius*1000, color='#A855F7', fill=True, fillOpacity=0.1, weight=2).add_to(m)
    for c, d in scan.items():
        for p in d['places']:
            folium.CircleMarker([p['lat'], p['lng']], radius=7, popup=f"<b>{p['name']}</b><br>{d['name']}<br>📏 {p['dist']:.2f} كم", tooltip=p['name'], color=d['color'], fill=True, fillColor=d['color'], fillOpacity=0.8, weight=2).add_to(m)
    return m


def ai_analyze(scan, lat, lng, radius):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{d['name']}({d['count']})" for c, d in scan.items()])
        prompt = f"""موقع ({lat}, {lng}) {radius}كم. الأنشطة: {summary}
JSON قصير:
{{"score": 75, "type": "نوع المنطقة", "competition": "منخفض/متوسط/مرتفع", "opportunities": ["فرصة 1", "2", "3"], "missing": ["مفقود 1"], "recommendation": "توصية قصيرة"}}"""
        text = model.generate_content(prompt).text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except Exception as e:
        return None


def ai_chat(msg, ctx):
    model = genai.GenerativeModel('gemini-2.5-flash')
    txt = ", ".join([f"{d['name']}({d['count']})" for c, d in ctx.get('scan', {}).items()])
    prompt = f"موقع: {ctx.get('lat')}, {ctx.get('lng')}. الأنشطة: {txt}\nسؤال: {msg}\nأجب بإيجاز بالعربية."
    return model.generate_content(prompt).text


col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    url = st.text_input("رابط", placeholder="https://maps.app.goo.gl/...", label_visibility="collapsed")

with col2:
    radius = st.selectbox("النطاق", [0.5, 1.0, 2.0, 3.0, 5.0], index=2, format_func=lambda x: f"{x} كم")

with col3:
    analyze_btn = st.button("🚀 بدء التحليل", type="primary")

if analyze_btn and url:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.markdown('<p class="progress-text">⏳ 5% - استخراج الإحداثيات...</p>', unsafe_allow_html=True)
    progress_bar.progress(5)
    
    lat, lng = extract_coords(url)
    
    if not lat:
        progress_bar.empty()
        status_text.empty()
        st.error("❌ فشل استخراج الإحداثيات. تأكد من الرابط")
    else:
        status_text.markdown(f'<p class="progress-text">📍 10% - الموقع: {lat:.4f}, {lng:.4f}</p>', unsafe_allow_html=True)
        progress_bar.progress(10)
        
        cats = {
            "restaurant": ("🍽️ مطاعم", "#A855F7"),
            "cafe": ("☕ مقاهي", "#EC4899"),
            "shopping": ("🛍️ تسوق", "#8B5CF6"),
            "fuel": ("⛽ وقود", "#6366F1"),
            "pharmacy": ("💊 صيدليات", "#10B981"),
            "grocery": ("🛒 بقالات", "#F59E0B"),
        }
        
        scan = {}
        total_cats = len(cats)
        progress_per_cat = 70 / total_cats
        current_progress = 10
        
        for i, (c, (n, col)) in enumerate(cats.items(), 1):
            status_text.markdown(f'<p class="progress-text">🔍 {int(current_progress)}% - البحث عن {n} ({i}/{total_cats})...</p>', unsafe_allow_html=True)
            
            f = search_places(lat, lng, c, 15)
            p = process(f, lat, lng, radius)
            if p:
                scan[c] = {'name': n, 'color': col, 'places': p, 'count': len(p)}
            
            current_progress += progress_per_cat
            progress_bar.progress(int(current_progress))
        
        status_text.markdown('<p class="progress-text">🤖 85% - التحليل الذكي بالذكاء الاصطناعي...</p>', unsafe_allow_html=True)
        progress_bar.progress(85)
        
        ai_result = ai_analyze(scan, lat, lng, radius)
        
        status_text.markdown('<p class="progress-text">🗺️ 95% - إعداد الخريطة والنتائج...</p>', unsafe_allow_html=True)
        progress_bar.progress(95)
        
        st.session_state.analysis = {'lat': lat, 'lng': lng, 'radius': radius, 'scan': scan, 'ai': ai_result}
        
        status_text.markdown('<p class="progress-text">✅ 100% - اكتمل التحليل!</p>', unsafe_allow_html=True)
        progress_bar.progress(100)
        
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        st.rerun()

if st.session_state.analysis:
    a = st.session_state.analysis
    total = sum(d['count'] for d in a['scan'].values())
    ai_r = a.get('ai') or {}
    
    score = ai_r.get('score', 50)
    comp_level = ai_r.get('competition', 'متوسط')
    area_type = ai_r.get('type', 'منطقة')
    
    st.markdown('<div class="section-title">📊 لوحة المؤشرات</div>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        color = "#10B981" if score >= 70 else "#F59E0B" if score >= 50 else "#EF4444"
        st.markdown(f'<div class="metric-card"><h3>نقاط الاستثمار</h3><div class="value" style="color:{color}">{score}/100</div><div class="sub">فرصة استثمارية</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><h3>إجمالي المحلات</h3><div class="value">{total}</div><div class="sub">في نطاق {a["radius"]} كم</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><h3>مستوى المنافسة</h3><div class="value" style="font-size:24px">{comp_level}</div><div class="sub">{len(a["scan"])} فئة نشطة</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><h3>طبيعة المنطقة</h3><div class="value" style="font-size:18px">{area_type[:20]}</div><div class="sub">تحليل ذكي</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">🗺️ الخريطة التفاعلية</div>', unsafe_allow_html=True)
    
    map_col, info_col = st.columns([2, 1])
    
    with map_col:
        m = make_map(a['lat'], a['lng'], a['scan'], a['radius'])
        st_folium(m, width=None, height=500, returned_objects=[])
    
    with info_col:
        if ai_r:
            st.markdown("### 💡 التوصية")
            st.info(ai_r.get('recommendation', ''))
            
            if ai_r.get('opportunities'):
                st.markdown("### 🎯 أفضل الفرص")
                for opp in ai_r['opportunities']:
                    st.success(f"✨ {opp}")
            
            if ai_r.get('missing'):
                st.markdown("### 🔍 خدمات مفقودة")
                for s in ai_r['missing']:
                    st.warning(f"• {s}")
        else:
            st.info("💡 التحليل الذكي غير متاح حالياً")
    
    if a['scan']:
        st.markdown('<div class="section-title">📈 توزيع الأنشطة</div>', unsafe_allow_html=True)
        
        chart_col, list_col = st.columns([1, 1])
        
        with chart_col:
            labels = [d['name'] for c, d in a['scan'].items()]
            values = [d['count'] for c, d in a['scan'].items()]
            colors_list = [d['color'] for c, d in a['scan'].items()]
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker=dict(colors=colors_list, line=dict(color='#1a0033', width=2)), textfont=dict(color='white', size=14))])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), showlegend=True, legend=dict(font=dict(color='white')), height=400, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with list_col:
            st.markdown("### 🏪 تفاصيل المحلات")
            for c, d in sorted(a['scan'].items(), key=lambda x: -x[1]['count']):
                with st.expander(f"{d['name']} ({d['count']})"):
                    for p in d['places'][:8]:
                        st.write(f"• **{p['name']}** - {p['dist']:.2f} كم")
                        if p['addr']:
                            st.caption(f"  📍 {p['addr']}")
    
    st.markdown('<div class="section-title">💬 اسأل المستشار</div>', unsafe_allow_html=True)
    
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    if ui := st.chat_input("اسأل عن الموقع، الفرص، المنافسة..."):
        st.session_state.chat.append({"role": "user", "content": ui})
        with st.spinner(""):
            resp = ai_chat(ui, a)
            st.session_state.chat.append({"role": "assistant", "content": resp})
        st.rerun()
