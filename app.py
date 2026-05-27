"""
GBI Saudi - تحليل المواقع الذكي
نسخة محسّنة وشاملة - تطابق التصميم المرجعي

الميزات:
- يستخدم OpenStreetMap (Overpass) - مجاني وتغطية ممتازة في السعودية
- تحليل قائم على القواعد (يعمل بدون AI)
- تحليل ذكاء اصطناعي اختياري عبر Gemini
- تصميم احترافي يطابق Dashboard المرجعي
- ٣٥+ فئة نشاط تجاري
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

from categories import CATEGORIES, GROUPS, get_categories_by_group
from analyzer import (
    extract_coords,
    fetch_all_places,
    analyze_location,
    suggest_best_activity,
    ai_enhance_analysis,
    ai_chat,
)

# ============================================================
# Configuration
# ============================================================
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
FOURSQUARE_KEY = os.getenv("FOURSQUARE_API_KEY", "").strip()

AI_AVAILABLE = False
genai = None
if GEMINI_KEY:
    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=GEMINI_KEY)
        # اختبار سريع
        AI_AVAILABLE = True
        genai = genai_module
    except Exception as e:
        AI_AVAILABLE = False

st.set_page_config(
    page_title="GBI - الاستثمار الذكي",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# ============================================================
# CSS - تصميم احترافي يطابق المرجع
# ============================================================
st.markdown("""
<style>
    /* إخفاء Streamlit الأصلي */
    #MainMenu, header, footer, .stDeployButton {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__1QSob, ._profileContainer_gzau3_53, ._terminalButton_rix23_138 {display: none !important;}
    a[href*="streamlit.io"], a[href*="share.streamlit"] {display: none !important;}

    /* خلفية وخط RTL */
    body, .stApp {
        direction: rtl;
        text-align: right;
        background: #0a0e1a !important;
        color: #fff;
        font-family: 'Segoe UI', 'Tahoma', sans-serif;
    }
    .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important;}

    /* الشريط العلوي */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 24px;
        background: #131826;
        border-radius: 16px;
        margin-bottom: 20px;
        border: 1px solid #1f2937;
    }
    .top-bar-right {display: flex; align-items: center; gap: 12px;}
    .brand {
        font-size: 28px;
        font-weight: 900;
        color: #ef4444;
        letter-spacing: 2px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-sub {color: #94a3b8; font-size: 12px; margin-top: 2px;}
    .top-bar-left {display: flex; align-items: center; gap: 16px;}
    .badge-connected {
        background: rgba(16,185,129,0.15);
        color: #10b981;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-disconnected {
        background: rgba(239,68,68,0.15);
        color: #ef4444;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
    }
    .user-pill {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #1f2937;
        padding: 6px 12px;
        border-radius: 30px;
    }
    .user-avatar {
        width: 32px; height: 32px;
        background: #ef4444;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
    }

    /* عنوان الصفحة */
    .page-title {
        text-align: right;
        padding: 8px 20px 16px 20px;
        margin-bottom: 20px;
    }
    .page-title h1 {
        color: white;
        font-size: 32px;
        margin: 0;
        font-weight: 700;
    }
    .page-title p {
        color: #94a3b8;
        margin: 6px 0 0 0;
        font-size: 14px;
    }

    /* صندوق البحث */
    .search-row {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
        align-items: stretch;
    }
    div[data-testid="stTextInput"] input {
        background: #131826 !important;
        color: white !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        font-size: 15px !important;
        height: 56px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #ef4444 !important;
        box-shadow: 0 0 0 3px rgba(239,68,68,0.15) !important;
    }
    div[data-testid="stSelectbox"] > div > div {
        background: #131826 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
        min-height: 56px !important;
        color: white !important;
    }
    div[data-testid="stSelectbox"] svg {fill: white !important;}

    /* الزر الأساسي */
    .stButton button {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        color: white !important;
        border: none !important;
        padding: 14px 24px !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        width: 100% !important;
        height: 56px !important;
        box-shadow: 0 4px 16px rgba(239,68,68,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;
    }

    /* بطاقات المؤشرات الرئيسية */
    .kpi-card {
        background: #131826;
        border: 1px solid #1f2937;
        border-radius: 18px;
        padding: 20px;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s;
    }
    .kpi-card:hover {transform: translateY(-2px);}
    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .kpi-title {color: #94a3b8; font-size: 13px; font-weight: 500;}
    .kpi-icon {
        width: 48px; height: 48px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }
    .kpi-value {color: white; font-size: 26px; font-weight: 800; margin: 4px 0;}
    .kpi-value-sm {color: white; font-size: 20px; font-weight: 700; margin: 4px 0;}
    .kpi-sub {color: #64748b; font-size: 12px;}

    /* البطاقات الجانبية والمعلوماتية */
    .info-card {
        background: #131826;
        border: 1px solid #1f2937;
        border-radius: 18px;
        padding: 22px;
        height: 100%;
    }
    .info-card-title {
        color: white;
        font-size: 17px;
        font-weight: 700;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* AI Recommendation card - مميز */
    .ai-card {
        background: linear-gradient(135deg, #1a2238 0%, #131826 100%);
        border: 1px solid rgba(139,92,246,0.3);
        border-radius: 18px;
        padding: 22px;
    }
    .ai-title-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .ai-title {color: #c4b5fd; font-size: 15px; font-weight: 600;}
    .ai-headline {
        color: #10b981;
        font-size: 24px;
        font-weight: 800;
        margin: 8px 0 12px 0;
    }
    .ai-headline.warning {color: #f59e0b;}
    .ai-headline.danger {color: #ef4444;}
    .ai-desc {color: #cbd5e1; font-size: 13px; line-height: 1.7;}

    /* نقاط قوة / انتباه */
    .point-section {margin-top: 14px;}
    .point-title {color: #94a3b8; font-size: 13px; margin-bottom: 8px; font-weight: 600;}
    .point-item {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #e2e8f0;
        font-size: 13px;
        padding: 4px 0;
    }
    .point-good {color: #10b981; font-size: 14px;}
    .point-warn {color: #f59e0b; font-size: 14px;}

    /* جدول المنافسين */
    .competitor-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px;
        background: rgba(31,41,55,0.5);
        border-radius: 10px;
        margin-bottom: 8px;
        font-size: 13px;
    }
    .competitor-rank {
        color: #64748b;
        font-weight: 700;
        width: 24px;
    }
    .competitor-name {color: #e2e8f0; flex: 1; padding: 0 8px;}
    .competitor-dist {color: #f59e0b; font-weight: 600;}

    /* القسم الصغير */
    .quick-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 11px 0;
        border-bottom: 1px solid #1f2937;
    }
    .quick-row:last-child {border-bottom: none;}
    .quick-label {color: #94a3b8; font-size: 13px; display: flex; align-items: center; gap: 8px;}
    .quick-value {color: white; font-size: 14px; font-weight: 600;}
    .quick-value.green {color: #10b981;}

    /* الفئات (checkboxes) */
    div[data-testid="stCheckbox"] label {
        background: #131826 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 999px !important;
        padding: 8px 14px !important;
        color: #cbd5e1 !important;
        font-size: 13px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        margin: 4px 6px 4px 0 !important;
        cursor: pointer !important;
    }
    div[data-testid="stCheckbox"] label:hover {border-color: #ef4444 !important;}
    div[data-testid="stCheckbox"] input:checked + div {background: rgba(239,68,68,0.15) !important;}

    /* expander style */
    div[data-testid="stExpander"] {
        background: #131826 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
    }
    div[data-testid="stExpander"] summary {color: white !important; font-weight: 600 !important;}

    /* progress */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #ef4444 0%, #f87171 100%) !important;
    }
    .progress-msg {
        color: #fca5a5;
        font-size: 14px;
        text-align: center;
        margin: 8px 0;
        font-weight: 500;
    }

    /* alert overrides */
    .stAlert {
        background: #131826 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }

    /* chat styling */
    [data-testid="stChatMessage"] {
        background: #131826 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: #131826 !important;
        color: white !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
    }

    /* tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #131826;
        border-radius: 14px;
        padding: 6px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #94a3b8 !important;
        border-radius: 10px !important;
        padding: 10px 18px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #1f2937 !important;
        color: white !important;
    }

    /* عناوين الأقسام */
    .section-title {
        color: white;
        font-size: 20px;
        font-weight: 700;
        margin: 28px 0 14px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-title::before {
        content: '';
        width: 4px;
        height: 22px;
        background: #ef4444;
        border-radius: 2px;
    }

    /* لوحة اقتراح النشاط */
    .activity-suggest-card {
        background: linear-gradient(135deg, #1e293b 0%, #131826 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
        transition: all 0.2s;
    }
    .activity-suggest-card:hover {
        border-color: #ef4444;
        transform: translateY(-2px);
    }
    .activity-suggest-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    .activity-name {color: white; font-size: 17px; font-weight: 700;}
    .activity-score {
        background: rgba(16,185,129,0.15);
        color: #10b981;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 700;
    }
    .activity-reason {color: #cbd5e1; font-size: 13px; line-height: 1.6; margin-top: 8px;}
    .activity-meta {
        display: flex;
        gap: 14px;
        margin-top: 10px;
        font-size: 12px;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# State
# ============================================================
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'chat' not in st.session_state:
    st.session_state.chat = []
if 'selected_cats' not in st.session_state:
    # افتراضياً نختار الفئات الأساسية
    st.session_state.selected_cats = list(CATEGORIES.keys())
if 'target_activity' not in st.session_state:
    st.session_state.target_activity = None

# ============================================================
# Top Bar
# ============================================================
badges = []
if FOURSQUARE_KEY:
    badges.append('<span class="badge-connected">● Foursquare</span>')
if GOOGLE_PLACES_KEY:
    badges.append('<span class="badge-connected">● Google Places</span>')
if not FOURSQUARE_KEY and not GOOGLE_PLACES_KEY:
    badges.append('<span class="badge-disconnected">○ OSM فقط</span>')

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

# ============================================================
# Title
# ============================================================
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
    url = st.text_input(
        "url",
        placeholder="📍 أدخل رابط Google Maps أو إحداثيات (lat, lng)...",
        label_visibility="collapsed",
        key="url_input"
    )
with sc2:
    radius = st.selectbox(
        "النطاق",
        [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0],
        index=2,
        format_func=lambda x: f"📏 نطاق {x} كم",
        label_visibility="collapsed"
    )
with sc3:
    analyze_btn = st.button("🚀 بدء التحليل", type="primary", use_container_width=True)

# ============================================================
# Categories Selection (in expander)
# ============================================================
with st.expander("⚙️ خيارات متقدمة: اختر الفئات والنشاط المستهدف"):
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("**🎯 النشاط المستهدف (اختياري):**")
        target_options = [("", "🤖 اقترح الأنسب تلقائياً")]
        for k, v in CATEGORIES.items():
            target_options.append((k, f"{v['icon']} {v['name']}"))

        target_idx = st.selectbox(
            "target",
            options=range(len(target_options)),
            format_func=lambda i: target_options[i][1],
            label_visibility="collapsed",
            key="target_select"
        )
        st.session_state.target_activity = target_options[target_idx][0] or None

    with col_b:
        st.markdown("**📊 الفئات التي يتم تحليلها:**")
        all_selected = st.checkbox("تحليل جميع الفئات", value=True, key="select_all_cats")

    if not all_selected:
        st.markdown("---")
        # عرض الفئات حسب المجموعة
        for group_key, group_info in GROUPS.items():
            st.markdown(f"**{group_info['icon']} {group_info['name']}**")
            cats_in_group = get_categories_by_group(group_key)
            cols = st.columns(4)
            for i, (cat_key, cat_info) in enumerate(cats_in_group.items()):
                with cols[i % 4]:
                    checked = st.checkbox(
                        f"{cat_info['icon']} {cat_info['name']}",
                        value=(cat_key in st.session_state.selected_cats),
                        key=f"cat_{cat_key}"
                    )
                    if checked and cat_key not in st.session_state.selected_cats:
                        st.session_state.selected_cats.append(cat_key)
                    elif not checked and cat_key in st.session_state.selected_cats:
                        st.session_state.selected_cats.remove(cat_key)
    else:
        st.session_state.selected_cats = list(CATEGORIES.keys())

# ============================================================
# Analysis Trigger
# ============================================================
if analyze_btn:
    if not url:
        st.error("⚠️ الرجاء إدخال رابط Google Maps أو إحداثيات.")
    elif not st.session_state.selected_cats:
        st.error("⚠️ اختر فئة واحدة على الأقل للتحليل.")
    else:
        progress = st.progress(0)
        status = st.empty()

        # 1) استخراج الإحداثيات
        status.markdown('<p class="progress-msg">⏳ 5% - استخراج الإحداثيات...</p>', unsafe_allow_html=True)
        progress.progress(5)
        lat, lng = extract_coords(url)

        if not lat:
            progress.empty()
            status.empty()
            st.error("❌ تعذّر استخراج الإحداثيات. تأكد من الرابط أو أدخل إحداثيات مباشرة مثل: 24.7136, 46.6753")
        else:
            status.markdown(f'<p class="progress-msg">📍 15% - الموقع: {lat:.5f}, {lng:.5f}</p>', unsafe_allow_html=True)
            progress.progress(15)
            time.sleep(0.2)

            # 2) جلب المحلات من كل المصادر المتاحة
            sources_list = ["OpenStreetMap"]
            if FOURSQUARE_KEY:
                sources_list.append("Foursquare")
            if GOOGLE_PLACES_KEY:
                sources_list.append("Google Places")
            sources_label = " + ".join(sources_list)
            status.markdown(f'<p class="progress-msg">🔍 30% - جلب البيانات من {sources_label}...</p>', unsafe_allow_html=True)
            progress.progress(30)

            result = fetch_all_places(
                lat, lng, radius,
                google_api_key=GOOGLE_PLACES_KEY or None,
                foursquare_api_key=FOURSQUARE_KEY or None,
            )
            places_by_cat = result['places_by_cat']

            total_found = sum(len(v) for v in places_by_cat.values())

            if total_found == 0 and result['errors']:
                progress.empty()
                status.empty()
                err_msg = " | ".join(result['errors'])
                st.error(f"❌ لم نعثر على بيانات: {err_msg}")
                st.info("💡 الحلول: 1) جرب نطاق أوسع (5 كم)  2) أضف FOURSQUARE_API_KEY (مجاني) في .env  3) تأكد من الإحداثيات")
                st.stop()

            status.markdown(f'<p class="progress-msg">🗂️ 60% - تم العثور على {total_found} محل في {len(places_by_cat)} فئة...</p>', unsafe_allow_html=True)
            progress.progress(60)

            status.markdown('<p class="progress-msg">🧠 80% - التحليل الذكي...</p>', unsafe_allow_html=True)
            progress.progress(80)

            # 3) تحليل
            analysis = analyze_location(places_by_cat, radius, st.session_state.target_activity)
            analysis['sources_used'] = result['sources_used']

            # 4) اقتراح أفضل نشاط
            analysis['suggested_activities'] = suggest_best_activity(places_by_cat, analysis)

            # 5) AI
            if AI_AVAILABLE:
                status.markdown('<p class="progress-msg">✨ 90% - تحسين عبر AI...</p>', unsafe_allow_html=True)
                progress.progress(90)
                analysis = ai_enhance_analysis(analysis, places_by_cat, lat, lng, AI_AVAILABLE, genai)

            st.session_state.analysis = {
                'lat': lat, 'lng': lng, 'radius': radius,
                'places_by_cat': places_by_cat,
                'analysis': analysis,
            }
            st.session_state.chat = []

            status.markdown('<p class="progress-msg">✅ 100% - اكتمل التحليل!</p>', unsafe_allow_html=True)
            progress.progress(100)
            time.sleep(0.3)
            progress.empty()
            status.empty()
            st.rerun()

# ============================================================
# Display Results
# ============================================================
if st.session_state.analysis:
    data = st.session_state.analysis
    a = data['analysis']
    pbc = data['places_by_cat']
    lat, lng, radius = data['lat'], data['lng'], data['radius']

    # ----- KPI Cards Row -----
    score = a['investment_score']
    score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
    score_bg = "rgba(16,185,129,0.15)" if score >= 70 else "rgba(245,158,11,0.15)" if score >= 50 else "rgba(239,68,68,0.15)"

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <div>
                    <div class="kpi-title">نقاط الاستثمار</div>
                    <div class="kpi-value" style="color:{score_color}">{score}<span style="font-size:14px; color:#64748b;">/100</span></div>
                </div>
                <div class="kpi-icon" style="background:{score_bg}; color:{score_color}">📈</div>
            </div>
            <div class="kpi-sub">{'فرصة استثمار ممتازة' if score>=70 else 'تحتاج دراسة' if score>=50 else 'مخاطرة عالية'}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        traffic_color = "#a855f7"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <div>
                    <div class="kpi-title">حركة المرور</div>
                    <div class="kpi-value-sm" style="color:{traffic_color}">{a['traffic_level']}</div>
                </div>
                <div class="kpi-icon" style="background:rgba(168,85,247,0.15); color:{traffic_color}">🚦</div>
            </div>
            <div class="kpi-sub">مستوى الحركة المقدّر</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        comp_color = "#10b981" if a['competition_score'] >= 60 else "#f59e0b" if a['competition_score'] >= 35 else "#ef4444"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <div>
                    <div class="kpi-title">المنافسة</div>
                    <div class="kpi-value-sm" style="color:{comp_color}">{a['competition_level']}</div>
                </div>
                <div class="kpi-icon" style="background:rgba(245,158,11,0.15); color:#f59e0b">🏆</div>
            </div>
            <div class="kpi-sub">مستوى المنافسة</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <div>
                    <div class="kpi-title">الكثافة السكانية</div>
                    <div class="kpi-value-sm" style="color:#3b82f6">{a['pop_density']}</div>
                </div>
                <div class="kpi-icon" style="background:rgba(59,130,246,0.15); color:#3b82f6">👥</div>
            </div>
            <div class="kpi-sub">~{a['est_population']:,} نسمة مقدّرة</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        acc_color = "#10b981" if a['accessibility_score'] >= 70 else "#f59e0b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <div>
                    <div class="kpi-title">سهولة الوصول</div>
                    <div class="kpi-value-sm" style="color:{acc_color}">{a['accessibility']}</div>
                </div>
                <div class="kpi-icon" style="background:rgba(16,185,129,0.15); color:#10b981">🚗</div>
            </div>
            <div class="kpi-sub">سهولة الوصول للموقع</div>
        </div>
        """, unsafe_allow_html=True)

    # ----- Map + AI Recommendation Row -----
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    map_col, info_col, ai_col = st.columns([3, 2, 3])

    # === Quick stats card ===
    with info_col:
        with st.container(border=False):
            html = f"""
            <div class="info-card">
                <div class="info-card-title">📊 مؤشرات سريعة</div>
                <div class="quick-row">
                    <span class="quick-label">👥 السكان المقدّرون</span>
                    <span class="quick-value">{a['est_population']:,}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">🏪 إجمالي المحلات</span>
                    <span class="quick-value">{a['total_places']}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">📂 الفئات النشطة</span>
                    <span class="quick-value">{a['active_cat_count']}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">🏙️ طبيعة المنطقة</span>
                    <span class="quick-value">{a['area_type']}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">🏘️ ثقافة الحي</span>
                    <span class="quick-value">{a['neighborhood_type']}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">🅿️ مواقف السيارات</span>
                    <span class="quick-value {'green' if a['parking_count']>0 else ''}">{'متوفرة' if a['parking_count']>0 else 'غير معروفة'}</span>
                </div>
                <div class="quick-row">
                    <span class="quick-label">⚠️ مستوى المخاطرة</span>
                    <span class="quick-value">{a['risk_level']}</span>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    # === Map ===
    with map_col:
        st.markdown('<div class="info-card-title" style="margin-right: 12px;">🗺️ الخريطة التفاعلية</div>', unsafe_allow_html=True)

        m = folium.Map(location=[lat, lng], zoom_start=14, tiles='CartoDB dark_matter')

        # دائرة النطاق
        folium.Circle(
            [lat, lng], radius=radius * 1000,
            color='#ef4444', fill=True, fillOpacity=0.08, weight=2
        ).add_to(m)

        # علامة الموقع
        folium.Marker(
            [lat, lng],
            popup="<b>📍 الموقع المحدد</b>",
            icon=folium.Icon(color='red', icon='star', prefix='fa')
        ).add_to(m)

        # كل المحلات
        for cat_key, places in pbc.items():
            color = CATEGORIES[cat_key]['color']
            icon = CATEGORIES[cat_key]['icon']
            cat_name = CATEGORIES[cat_key]['name']
            for p in places:
                folium.CircleMarker(
                    [p['lat'], p['lng']],
                    radius=6,
                    popup=f"<b>{p['name']}</b><br>{icon} {cat_name}<br>📏 {p['dist']:.2f} كم",
                    tooltip=f"{icon} {p['name']}",
                    color=color, fill=True, fillColor=color,
                    fillOpacity=0.85, weight=1.5
                ).add_to(m)

        st_folium(m, width=None, height=480, returned_objects=[], key="main_map")

    # === AI Recommendation Card ===
    with ai_col:
        headline_class = "" if score >= 70 else "warning" if score >= 50 else "danger"
        headline_text = "فرصة استثمار ممتازة" if score >= 70 else "فرصة تحتاج دراسة" if score >= 50 else "موقع قليل النشاط"

        # استخدم رد AI إذا متوفر
        if a.get('ai_enhanced') and a.get('ai_recommendation'):
            rec_text = a['ai_recommendation']
        else:
            rec_text = a['recommendation']

        strengths_html = ""
        for s in a['strengths']:
            strengths_html += f'<div class="point-item"><span class="point-good">✓</span> {s}</div>'

        cautions_html = ""
        for c in a['cautions']:
            cautions_html += f'<div class="point-item"><span class="point-warn">⚠</span> {c}</div>'

        ai_label = "توصية الذكاء الاصطناعي" if a.get('ai_enhanced') else "توصية النظام الذكي"

        st.markdown(f"""
        <div class="ai-card">
            <div class="ai-title-row">
                <div class="ai-title">✨ {ai_label}</div>
                <div style="background:rgba(139,92,246,0.2); color:#c4b5fd; padding:4px 10px; border-radius:999px; font-size:11px;">
                    {'AI' if a.get('ai_enhanced') else 'Rule-Based'}
                </div>
            </div>
            <div class="ai-headline {headline_class}">{headline_text}</div>
            <div class="ai-desc">{rec_text}</div>
            <div class="point-section">
                <div class="point-title">نقاط القوة</div>
                {strengths_html}
            </div>
            <div class="point-section">
                <div class="point-title">نقاط الانتباه</div>
                {cautions_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ----- Best Activities Suggestion -----
    if a.get('suggested_activities') and not a.get('target_cat'):
        st.markdown('<div class="section-title">🎯 أفضل الأنشطة المقترحة لهذا الموقع</div>', unsafe_allow_html=True)

        suggested = a['suggested_activities'][:3]
        cols = st.columns(3)
        for i, s in enumerate(suggested):
            with cols[i]:
                st.markdown(f"""
                <div class="activity-suggest-card">
                    <div class="activity-suggest-header">
                        <div class="activity-name">{s['icon']} {s['cat_name']}</div>
                        <div class="activity-score">{s['opportunity_score']}/100</div>
                    </div>
                    <div class="activity-reason">{s['reason']}</div>
                    <div class="activity-meta">
                        <span>📊 الطلب: {s['demand']}%</span>
                        <span>🏪 المنافسين: {s['existing']}</span>
                        <span>📈 الإشباع: {s['saturation']}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ----- Charts Section -----
    if pbc:
        st.markdown('<div class="section-title">📈 توزيع الأنشطة والتحليلات</div>', unsafe_allow_html=True)

        chart_col, factors_col, comp_col = st.columns([1, 1, 1])

        # Donut chart - توزيع الأنشطة
        with chart_col:
            st.markdown('<div class="info-card-title">🍩 توزيع الأنشطة التجارية</div>', unsafe_allow_html=True)
            labels = [CATEGORIES[k]['name'] for k in pbc.keys()]
            values = [len(v) for v in pbc.values()]
            colors_list = [CATEGORIES[k]['color'] for k in pbc.keys()]

            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values, hole=0.55,
                marker=dict(colors=colors_list, line=dict(color='#0a0e1a', width=2)),
                textfont=dict(color='white', size=12),
                textinfo='percent',
                hoverinfo='label+value+percent'
            )])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                legend=dict(font=dict(color='white', size=11), orientation='v', x=1.0, y=0.5),
                height=380, margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Radar chart - تحليل العوامل
        with factors_col:
            st.markdown('<div class="info-card-title">🎯 تحليل العوامل</div>', unsafe_allow_html=True)
            radar_labels = ['حركة المرور', 'الكثافة السكانية', 'المنافسة', 'سهولة الوصول', 'القوة الشرائية']
            radar_values = [
                a['traffic_score'],
                a['pop_score'],
                a['competition_score'],
                a['accessibility_score'],
                min(100, a['active_cat_count'] * 12),  # تقدير القوة الشرائية
            ]

            fig2 = go.Figure(data=go.Scatterpolar(
                r=radar_values + [radar_values[0]],
                theta=radar_labels + [radar_labels[0]],
                fill='toself',
                fillcolor='rgba(239,68,68,0.25)',
                line=dict(color='#ef4444', width=2),
                marker=dict(size=8, color='#ef4444')
            ))
            fig2.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                    gridcolor='rgba(148,163,184,0.2)'),
                    angularaxis=dict(tickfont=dict(color='white', size=11),
                                     gridcolor='rgba(148,163,184,0.2)'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                height=380, margin=dict(t=30, b=30, l=40, r=40)
            )
            st.plotly_chart(fig2, use_container_width=True)

        # أعلى المنافسين / أكثر الفئات
        with comp_col:
            target = a.get('target_cat')
            if target and a.get('top_competitors'):
                st.markdown(f'<div class="info-card-title">🏆 أعلى المنافسين ({CATEGORIES[target]["name"]})</div>', unsafe_allow_html=True)
                competitors_html = "<div>"
                for i, c in enumerate(a['top_competitors'][:5], 1):
                    brand_suffix = f" • {c['brand']}" if c.get('brand') else ""
                    competitors_html += f"""
                    <div class="competitor-row">
                        <span class="competitor-rank">{i}</span>
                        <span class="competitor-name">{c['name']}{brand_suffix}</span>
                        <span class="competitor-dist">{c['dist']} كم</span>
                    </div>
                    """
                competitors_html += "</div>"
                st.markdown(competitors_html, unsafe_allow_html=True)
            else:
                # أكثر الفئات
                st.markdown('<div class="info-card-title">🏪 أكثر الفئات نشاطاً</div>', unsafe_allow_html=True)
                top_cats = sorted(pbc.items(), key=lambda x: -len(x[1]))[:5]
                competitors_html = "<div>"
                for i, (ck, places) in enumerate(top_cats, 1):
                    competitors_html += f"""
                    <div class="competitor-row">
                        <span class="competitor-rank">{i}</span>
                        <span class="competitor-name">{CATEGORIES[ck]['icon']} {CATEGORIES[ck]['name']}</span>
                        <span class="competitor-dist">{len(places)} محل</span>
                    </div>
                    """
                competitors_html += "</div>"
                st.markdown(competitors_html, unsafe_allow_html=True)

    # ----- Opportunities & Missing Services -----
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

    # ----- Detailed places list -----
    if pbc:
        st.markdown('<div class="section-title">🏪 تفاصيل المحلات في المنطقة</div>', unsafe_allow_html=True)

        sorted_cats = sorted(pbc.items(), key=lambda x: -len(x[1]))
        for cat_key, places in sorted_cats:
            cat = CATEGORIES[cat_key]
            with st.expander(f"{cat['icon']} {cat['name']} — {len(places)} محل"):
                for p in places[:20]:
                    brand = f" • 🏷️ {p['brand']}" if p.get('brand') else ""
                    addr = f"<br><span style='color:#64748b; font-size:12px;'>📍 {p['addr']}</span>" if p.get('addr') else ""
                    st.markdown(
                        f"<div style='padding:8px 0; border-bottom:1px solid #1f2937;'>"
                        f"<b style='color:#e2e8f0;'>{p['name']}</b>"
                        f" <span style='color:#f59e0b;'>{p['dist']:.2f} كم</span>{brand}{addr}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

    # ----- AI Chat -----
    st.markdown('<div class="section-title">💬 اسأل المستشار</div>', unsafe_allow_html=True)

    if not AI_AVAILABLE:
        st.info("ℹ️ المستشار يعمل بوضع القواعد الذكية (Rule-based). لتفعيل الذكاء الاصطناعي الكامل أضف GEMINI_API_KEY في ملف .env")

    # عرض المحادثة
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.write(msg["content"])

    # input
    user_msg = st.chat_input("اسأل عن الموقع، الفرص، المنافسة...")
    if user_msg:
        st.session_state.chat.append({"role": "user", "content": user_msg})
        with st.spinner("جارٍ التفكير..."):
            response = ai_chat(user_msg, a, pbc, lat, lng, AI_AVAILABLE, genai)
        st.session_state.chat.append({"role": "assistant", "content": response})
        st.rerun()

else:
    # ----- Welcome State -----
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; background:#131826; border-radius:18px; border:1px solid #1f2937; margin-top:24px;">
        <div style="font-size:64px; margin-bottom:20px;">🗺️</div>
        <h2 style="color:white; margin-bottom:10px;">ابدأ بتحليل موقعك</h2>
        <p style="color:#94a3b8; margin-bottom:24px;">
            أدخل رابط Google Maps أعلاه واضغط على "بدء التحليل" للحصول على تحليل شامل ودقيق للموقع.
        </p>
        <div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap; margin-top:30px;">
            <div style="background:#1f2937; padding:14px 20px; border-radius:14px; color:#e2e8f0; font-size:13px;">
                🎯 تحليل المنافسة
            </div>
            <div style="background:#1f2937; padding:14px 20px; border-radius:14px; color:#e2e8f0; font-size:13px;">
                📊 تقييم الموقع
            </div>
            <div style="background:#1f2937; padding:14px 20px; border-radius:14px; color:#e2e8f0; font-size:13px;">
                💡 اقتراح أفضل نشاط
            </div>
            <div style="background:#1f2937; padding:14px 20px; border-radius:14px; color:#e2e8f0; font-size:13px;">
                🗺️ خريطة تفاعلية
            </div>
            <div style="background:#1f2937; padding:14px 20px; border-radius:14px; color:#e2e8f0; font-size:13px;">
                🤖 مستشار AI
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
