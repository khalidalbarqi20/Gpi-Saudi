import streamlit as st
import os, re, requests, json, math
from dotenv import load_dotenv
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MAPBOX = os.getenv("MAPBOX_TOKEN")

st.set_page_config(page_title="GBI - الاستثمار الذكي", page_icon="📊", layout="wide", initial_sidebar_state="collapsed", menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none;}
    .styles_viewerBadge__1yB5_ {display: none;}
    body, .stApp {direction: rtl; text-align: right; background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%); color: #fff;}
    .main-header {background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 100%); padding: 25px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 8px 32px rgba(255,75,75,0.3);}
    .main-header h1 {color: white; margin: 0; font-size: 32px; font-weight: bold;}
    .main-header p {color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 14px;}
    .metric-card {background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; text-align: center; backdrop-filter: blur(10px);}
    .metric-card h3 {color: #FF6B6B; margin: 0 0 10px 0; font-size: 14px;}
    .metric-card .value {color: white; font-size: 32px; font-weight: bold; margin: 5px 0;}
    .metric-card .sub {color: rgba(255,255,255,0.6); font-size: 12px;}
    .section-title {color: #FF6B6B; font-size: 22px; font-weight: bold; margin: 25px 0 15px 0; border-right: 4px solid #FF4B4B; padding-right: 10px;}
    div[data-testid="stTextInput"] input {background: rgba(255,255,255,0.08) !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 10px !important; padding: 12px !important;}
    .stButton button {background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 100%) !important; color: white !important; border: none !important; padding: 12px 30px !important; border-radius: 10px !important; font-weight: bold !important; width: 100%;}
    div[data-testid="stExpander"] {background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'chat' not in st.session_state:
    st.session_state.chat = []

st.markdown("""
<div class="main-header">
    <h1>🌍 GBI - مستشار الاستثمار الذكي</h1>
    <p>تحليل شامل للمواقع التجارية واكتشاف الفرص الاستثمارية</p>
</div>
""", unsafe_allow_html=True)


def extract_coords(url):
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(url, allow_redirects=True, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
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


def search_places(lat, lng, cat, limit=20):
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
    cats = {
        "restaurant": ("🍽️ مطاعم", "#FF4B4B"),
        "cafe": ("☕ مقاهي", "#FF8C42"),
        "shopping": ("🛍️ تسوق", "#9B59B6"),
        "fuel": ("⛽ وقود", "#2C3E50"),
        "pharmacy": ("💊 صيدليات", "#27AE60"),
        "grocery": ("🛒 بقالات", "#3498DB"),
        "services": ("🔧 خدمات", "#95A5A6"),
    }
    results = {}
    for c, (n, col) in cats.items():
        f = search_places(lat, lng, c, 15)
        p = process(f, lat, lng, radius)
        if p:
            results[c] = {'name': n, 'color': col, 'places': p, 'count': len(p)}
    return results


def make_map(lat, lng, scan, radius):
    m = folium.Map(location=[lat, lng], zoom_start=14, tiles='CartoDB dark_matter')
    folium.Marker([lat, lng], popup="<b>الموقع المحدد</b>", icon=folium.Icon(color='red', icon='star', prefix='fa')).add_to(m)
    folium.Circle([lat, lng], radius=radius*1000, color='#FF4B4B', fill=True, fillOpacity=0.1, weight=2).add_to(m)
    for c, d in scan.items():
        for p in d['places']:
            folium.CircleMarker([p['lat'], p['lng']], radius=7, popup=f"<b>{p['name']}</b><br>{d['name']}<br>📏 {p['dist']:.2f} كم", tooltip=p['name'], color=d['color'], fill=True, fillColor=d['color'], fillOpacity=0.8, weight=2).add_to(m)
    return m


def ai_analyze(scan, lat, lng, radius):
    model = genai.GenerativeModel('gemini-2.5-flash')
    summary = "\n".join([f"- {d['name']}: {d['count']} محل" for c, d in scan.items()])
    prompt = f"""أنت مستشار استثماري خبير. حلل هذا الموقع ({lat}, {lng}) في نطاق {radius} كم.

الأنشطة الموجودة:
{summary}

أعطني JSON:
{{
  "investment_score": 75,
  "area_type": "وصف المنطقة",
  "competition_level": "منخفض/متوسط/مرتفع",
  "best_opportunities": ["نشاط 1", "نشاط 2", "نشاط 3"],
  "missing_services": ["خدمة مفقودة 1", "خدمة 2"],
  "strengths": ["نقطة قوة 1", "2"],
  "warnings": ["تحذير 1"],
  "recommendation": "توصية نهائية بالعربية"
}}
JSON فقط."""
    try:
        text = model.generate_content(prompt).text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except:
        return None


def ai_chat(msg, ctx):
    model = genai.GenerativeModel('gemini-2.5-flash')
    txt = "\n".join([f"- {d['name']}: {d['count']}" for c, d in ctx.get('scan', {}).items()])
    prompt = f"مستشار استثماري. موقع: {ctx.get('lat')}, {ctx.get('lng')}. الأنشطة:\n{txt}\nسؤال: {msg}\nأجب بالعربية باحترافية."
    return model.generate_content(prompt).text


col_input1, col_input2, col_input3 = st.columns([3, 1, 1])

with col_input1:
    url = st.text_input("🔗 أدخل رابط الموقع", placeholder="https://maps.app.goo.gl/...", label_visibility="collapsed")

with col_input2:
    radius = st.selectbox("النطاق", [0.5, 1.0, 2.0, 3.0, 5.0, 10.0], index=2, format_func=lambda x: f"{x} كم")

with col_input3:
    analyze_btn = st.button("🚀 بدء التحليل", type="primary")

if analyze_btn and url:
    with st.spinner("⏳ جاري استخراج الإحداثيات..."):
        lat, lng = extract_coords(url)
    
    if not lat:
        st.error("❌ فشل استخراج الإحداثيات. تأكد من الرابط")
    else:
        with st.spinner("🔍 جاري مسح المنطقة..."):
            scan = scan_area(lat, lng, radius)
        
        with st.spinner("🤖 الذكاء الاصطناعي يحلل..."):
            ai_result = ai_analyze(scan, lat, lng, radius)
        
        st.session_state.analysis = {'lat': lat, 'lng': lng, 'radius': radius, 'scan': scan, 'ai': ai_result}

if st.session_state.analysis:
    a = st.session_state.analysis
    total = sum(d['count'] for d in a['scan'].values())
    ai_r = a.get('ai') or {}
    
    score = ai_r.get('investment_score', 50)
    comp_level = ai_r.get('competition_level', 'متوسط')
    area_type = ai_r.get('area_type', 'منطقة')
    
    st.markdown('<div class="section-title">📊 لوحة المؤشرات الرئيسية</div>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        color = "#27AE60" if score >= 70 else "#F39C12" if score >= 50 else "#E74C3C"
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
            st.markdown("### 💡 توصية المستشار")
            st.info(ai_r.get('recommendation', ''))
            
            if ai_r.get('best_opportunities'):
                st.markdown("### 🎯 أفضل الفرص")
                for opp in ai_r['best_opportunities']:
                    st.success(f"✨ {opp}")
            
            if ai_r.get('missing_services'):
                st.markdown("### 🔍 خدمات مفقودة")
                for s in ai_r['missing_services']:
                    st.warning(f"• {s}")
    
    if a['scan']:
        st.markdown('<div class="section-title">📈 توزيع الأنشطة في المنطقة</div>', unsafe_allow_html=True)
        
        chart_col, list_col = st.columns([1, 1])
        
        with chart_col:
            labels = [d['name'] for c, d in a['scan'].items()]
            values = [d['count'] for c, d in a['scan'].items()]
            colors_list = [d['color'] for c, d in a['scan'].items()]
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker=dict(colors=colors_list, line=dict(color='#1a1f2e', width=2)), textfont=dict(color='white', size=14))])
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
    
    if ai_r and (ai_r.get('strengths') or ai_r.get('warnings')):
        st.markdown('<div class="section-title">⚖️ نقاط القوة والتحذيرات</div>', unsafe_allow_html=True)
        sw1, sw2 = st.columns(2)
        with sw1:
            if ai_r.get('strengths'):
                st.markdown("### ✅ نقاط القوة")
                for s in ai_r['strengths']:
                    st.success(s)
        with sw2:
            if ai_r.get('warnings'):
                st.markdown("### ⚠️ تحذيرات")
                for w in ai_r['warnings']:
                    st.warning(w)
    
    st.markdown('<div class="section-title">💬 اسأل المستشار</div>', unsafe_allow_html=True)
    
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    if ui := st.chat_input("اسأل عن الموقع، الفرص، المنافسة..."):
        st.session_state.chat.append({"role": "user", "content": ui})
        with st.spinner("🤖 المستشار يفكر..."):
            resp = ai_chat(ui, a)
            st.session_state.chat.append({"role": "assistant", "content": resp})
        st.rerun()

else:
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px; background: rgba(255,255,255,0.03); border-radius: 20px; margin-top: 20px;">
        <h2 style="color: #FF6B6B;">👋 مرحباً بك في GBI</h2>
        <p style="color: rgba(255,255,255,0.7); font-size: 16px; margin-top: 15px;">منصة دراسة الجدوى الذكية للمواقع التجارية</p>
        <p style="color: rgba(255,255,255,0.5); margin-top: 30px;">أدخل رابط Google Maps أعلاه لبدء التحليل الشامل</p>
    </div>
    """, unsafe_allow_html=True)
