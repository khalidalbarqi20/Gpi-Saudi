"""
GBI - تحليل المواقع التجارية v3
الإصلاحات:
- خفض الثقة لمستوى واقعي
- حذف كثافة الذروة المخمّنة
- حذف "السكان المقدّرون" المخمّن
- حذف مقارنة المدن
- إصلاح التناقض المنطقي
- تحذير شفاف في رأس التقرير
- بيانات سكان حقيقية للمحافظات السعودية (GASTAT 2022)
- نموذج تفاعلي لإدخال البيانات الميدانية
- منطق تحليل ذكي للمدخلات
"""

# ============================================================================
# [الدفعة 1] الاستيراد والإعدادات
# ============================================================================
import os
import re
import json
import math
import time
import html as _html
import requests


def esc(val):
    if val is None:
        return ""
    return _html.escape(str(val), quote=True)
import streamlit as st
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from PIL import Image

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


# ============================================================================
# [الدفعة 1] الفئات (33 فئة من Mapbox canonical IDs)
# ============================================================================
CATEGORIES = {
    # طعام
    "restaurant": {"name": "مطاعم", "icon": "🍽️", "color": "#ef4444", "group": "طعام"},
    "cafe": {"name": "مقاهي", "icon": "☕", "color": "#f59e0b", "group": "طعام"},
    "fast_food": {"name": "وجبات سريعة", "icon": "🍔", "color": "#dc2626", "group": "طعام"},
    # تسوق
    "shopping": {"name": "تسوق", "icon": "🛍️", "color": "#a855f7", "group": "تسوق"},
    "clothing_store": {"name": "ملابس", "icon": "👕", "color": "#c084fc", "group": "تسوق"},
    "electronics_store": {"name": "إلكترونيات", "icon": "📱", "color": "#8b5cf6", "group": "تسوق"},
    "home_garden": {"name": "منازل وحدائق", "icon": "🏡", "color": "#7c3aed", "group": "تسوق"},
    "sporting_goods": {"name": "منتجات رياضية", "icon": "⚽", "color": "#6366f1", "group": "تسوق"},
    # خدمات أساسية
    "fuel": {"name": "محطات وقود", "icon": "⛽", "color": "#64748b", "group": "خدمات"},
    "pharmacy": {"name": "صيدليات", "icon": "💊", "color": "#10b981", "group": "خدمات"},
    "grocery": {"name": "بقالات", "icon": "🛒", "color": "#3b82f6", "group": "خدمات"},
    "services": {"name": "خدمات عامة", "icon": "🔧", "color": "#94a3b8", "group": "خدمات"},
    # سيارات
    "auto_repair": {"name": "صيانة سيارات", "icon": "🔧", "color": "#475569", "group": "سيارات"},
    "car_wash": {"name": "مغاسل سيارات", "icon": "🚿", "color": "#0ea5e9", "group": "سيارات"},
    "car_dealer": {"name": "تجار سيارات", "icon": "🚗", "color": "#0284c7", "group": "سيارات"},
    "car_rental": {"name": "تأجير سيارات", "icon": "🚙", "color": "#0369a1", "group": "سيارات"},
    "ev_charging_station": {"name": "شحن كهربائي", "icon": "🔌", "color": "#06b6d4", "group": "سيارات"},
    "parking": {"name": "مواقف", "icon": "🅿️", "color": "#475569", "group": "سيارات"},
    # صحة
    "hospital": {"name": "مستشفيات ومراكز طبية", "icon": "🏥", "color": "#dc2626", "group": "صحة"},
    "clinic": {"name": "عيادات", "icon": "⚕️", "color": "#ef4444", "group": "صحة"},
    # تجميل
    "beauty_salon": {"name": "صالونات تجميل", "icon": "💅", "color": "#ec4899", "group": "تجميل"},
    # ترفيه وثقافة
    "park": {"name": "حدائق ومتنزهات", "icon": "🌳", "color": "#22c55e", "group": "ترفيه"},
    "fitness_center": {"name": "نوادي رياضية", "icon": "💪", "color": "#16a34a", "group": "ترفيه"},
    "cinema": {"name": "سينما وأفلام", "icon": "🎬", "color": "#7e22ce", "group": "ترفيه"},
    "museum": {"name": "متاحف", "icon": "🏛️", "color": "#9333ea", "group": "ترفيه"},
    "tourist_attraction": {"name": "معالم سياحية", "icon": "🗺️", "color": "#a855f7", "group": "ترفيه"},
    "nightclub": {"name": "ترفيه ليلي", "icon": "🎵", "color": "#be185d", "group": "ترفيه"},
    "library": {"name": "مكتبات", "icon": "📚", "color": "#a16207", "group": "ترفيه"},
    # مالية
    "atm": {"name": "صرّاف آلي", "icon": "🏧", "color": "#059669", "group": "مالية"},
    "bank": {"name": "بنوك", "icon": "🏦", "color": "#047857", "group": "مالية"},
    # سفر
    "hotel": {"name": "فنادق", "icon": "🏨", "color": "#0891b2", "group": "سفر"},
    # تعليم وديني
    "school": {"name": "مدارس", "icon": "🏫", "color": "#ca8a04", "group": "تعليم"},
    "mosque": {"name": "مساجد", "icon": "🕌", "color": "#65a30d", "group": "ديني"},
    # ════════════════════════════════════════════════════════════
    # 🆕 فئات جديدة - تصنيف هرمي (شخص/منزل/سيارة/جوال/خدمات)
    # هذه الفئات تعتمد بشكل رئيسي على OSM (Mapbox لا يدعمها)
    # ════════════════════════════════════════════════════════════
    # 🏠 منزل - صيانة
    "plumber": {"name": "سباك", "icon": "🔧", "color": "#0284c7", "group": "منزل"},
    "electrician": {"name": "كهربائي", "icon": "⚡", "color": "#facc15", "group": "منزل"},
    "carpenter": {"name": "نجار", "icon": "🪚", "color": "#92400e", "group": "منزل"},
    "metalworker": {"name": "ورشة لحام", "icon": "🔥", "color": "#dc2626", "group": "منزل"},
    "ac_repair": {"name": "صيانة تكييف", "icon": "❄️", "color": "#0ea5e9", "group": "منزل"},
    "painter": {"name": "دهان وصبغ", "icon": "🎨", "color": "#a855f7", "group": "منزل"},
    # 🏠 منزل - أثاث وديكور
    "furniture": {"name": "أثاث منزلي", "icon": "🛋️", "color": "#7c3aed", "group": "منزل"},
    "lighting": {"name": "إضاءة", "icon": "💡", "color": "#eab308", "group": "منزل"},
    "curtains": {"name": "ستائر ومفروشات", "icon": "🪟", "color": "#be185d", "group": "منزل"},
    # 🏠 منزل - خدمات
    "gas_supply": {"name": "تبديل غاز", "icon": "🔥", "color": "#f97316", "group": "منزل"},
    "locksmith": {"name": "نسخ مفاتيح", "icon": "🔑", "color": "#78716c", "group": "منزل"},
    "cleaning": {"name": "خدمات نظافة", "icon": "🧹", "color": "#06b6d4", "group": "منزل"},
    "pest_control": {"name": "مكافحة حشرات", "icon": "🐜", "color": "#84cc16", "group": "منزل"},
    # 🚗 سيارات - تكميلي
    "tyre_shop": {"name": "بنشري", "icon": "🛞", "color": "#1f2937", "group": "سيارات"},
    "upholstery": {"name": "تنجيد سيارات", "icon": "💺", "color": "#7c2d12", "group": "سيارات"},
    "car_tinting": {"name": "تظليل سيارات", "icon": "🪟", "color": "#374151", "group": "سيارات"},
    "auto_parts": {"name": "قطع غيار", "icon": "🔩", "color": "#525b76", "group": "سيارات"},
    "oil_change": {"name": "تغيير زيت", "icon": "🛢️", "color": "#451a03", "group": "سيارات"},
    # 📱 جوال وإلكترونيات
    "mobile_repair": {"name": "صيانة جوال", "icon": "📱", "color": "#2563eb", "group": "إلكترونيات"},
    "mobile_accessories": {"name": "إكسسوارات جوال", "icon": "🎧", "color": "#9333ea", "group": "إلكترونيات"},
    # 👕 ملابس متخصصة
    "tailor": {"name": "خياط", "icon": "🧵", "color": "#be123c", "group": "ملابس"},
    "abaya_shop": {"name": "محل عبايات", "icon": "🧕", "color": "#1e293b", "group": "ملابس"},
    "shoe_shop": {"name": "أحذية", "icon": "👟", "color": "#7c3aed", "group": "ملابس"},
    # 🍞 طعام متخصص
    "bakery": {"name": "مخبز", "icon": "🍞", "color": "#d97706", "group": "طعام"},
    "sweets": {"name": "حلويات", "icon": "🍰", "color": "#ec4899", "group": "طعام"},
    "butcher": {"name": "ملحمة / دجاج", "icon": "🥩", "color": "#991b1b", "group": "طعام"},
    "vegetables": {"name": "خضار وفواكه", "icon": "🥬", "color": "#16a34a", "group": "طعام"},
    # 💇 عناية شخصية
    "barber": {"name": "حلاق رجالي", "icon": "✂️", "color": "#1f2937", "group": "عناية"},
    # 🎓 تعليم متخصص
    "quran_school": {"name": "تحفيظ قرآن", "icon": "📖", "color": "#15803d", "group": "تعليم"},
    "training_center": {"name": "مركز تدريب", "icon": "🎓", "color": "#0e7490", "group": "تعليم"},
    # 🏥 صحة متخصصة
    "dentist": {"name": "عيادة أسنان", "icon": "🦷", "color": "#0891b2", "group": "صحة"},
    "medical_lab": {"name": "مختبر طبي", "icon": "🧪", "color": "#7c3aed", "group": "صحة"},
    # 🎮 ترفيه إضافي
    "playground": {"name": "ملاعب", "icon": "⚽", "color": "#16a34a", "group": "ترفيه"},
    "game_center": {"name": "مركز ألعاب", "icon": "🎮", "color": "#a855f7", "group": "ترفيه"},
}

# ════════════════════════════════════════════════════════════════
# 🆕 التصنيف الهرمي - أساسي / احتياج / تكميلي حسب القطاع
# ════════════════════════════════════════════════════════════════
# 🆕 التصنيف الهرمي الشامل — أساسي / احتياج / تكميلي
# منظّم حسب القطاع (الشخص، المنزل، السيارة، الجوال، الترفيه، ...).
# المنطق:
#   essential (أساسي): يجب توفره في أي حي سكني — غيابه نقص حرج.
#   needed (احتياج): يستخدمه السكان بانتظام — غيابه فرصة قوية.
#   extra (تكميلي): يحسّن جودة الحياة — فرصة لكن ليست ضرورة.
# كل فئة في CATEGORIES مصنّفة هنا (لا فئات معلّقة).
# ════════════════════════════════════════════════════════════════
HIERARCHICAL_NEEDS = {
    # ───────────── 👤 الشخص ─────────────
    'person_food': {
        'name': '🍽️ طعام وشراب',
        'sector': 'الشخص',
        'tiers': {
            'essential': ['grocery'],
            'needed': ['restaurant', 'bakery', 'butcher', 'vegetables'],
            'extra': ['cafe', 'fast_food', 'sweets'],
        }
    },
    'person_clothing': {
        'name': '👕 ملابس',
        'sector': 'الشخص',
        'tiers': {
            'essential': ['clothing_store'],
            'needed': ['tailor', 'shoe_shop'],
            'extra': ['abaya_shop'],
        }
    },
    'person_health': {
        'name': '💊 صحة',
        'sector': 'الشخص',
        'tiers': {
            'essential': ['pharmacy'],
            'needed': ['clinic', 'hospital', 'medical_lab', 'dentist'],
            'extra': [],
        }
    },
    'person_education': {
        'name': '🎓 تعليم',
        'sector': 'الشخص',
        'tiers': {
            'essential': ['school'],
            'needed': ['quran_school', 'training_center'],
            'extra': ['library'],
        }
    },
    'person_care': {
        'name': '💇 عناية شخصية',
        'sector': 'الشخص',
        'tiers': {
            'essential': [],
            'needed': ['barber', 'beauty_salon'],
            'extra': [],
        }
    },

    # ───────────── 🏠 المنزل ─────────────
    'home_maintenance': {
        'name': '🔧 صيانة منزل',
        'sector': 'المنزل',
        'tiers': {
            'essential': [],
            'needed': ['plumber', 'electrician'],
            'extra': ['carpenter', 'metalworker', 'ac_repair', 'painter'],
        }
    },
    'home_furniture': {
        'name': '🛋️ أثاث وإضاءة وديكور',
        'sector': 'المنزل',
        'tiers': {
            'essential': [],
            'needed': ['furniture', 'home_garden'],
            'extra': ['lighting', 'curtains'],
        }
    },
    'home_services': {
        'name': '🏠 خدمات منزلية',
        'sector': 'المنزل',
        'tiers': {
            'essential': ['gas_supply'],
            'needed': ['locksmith', 'cleaning'],
            'extra': ['pest_control'],
        }
    },

    # ───────────── 🚗 السيارة ─────────────
    'car_essential': {
        'name': '⛽ سيارة - أساسي',
        'sector': 'السيارة',
        'tiers': {
            'essential': ['fuel'],
            'needed': ['auto_repair', 'tyre_shop', 'oil_change'],
            'extra': [],
        }
    },
    'car_extras': {
        'name': '🚗 سيارة - تكميلي',
        'sector': 'السيارة',
        'tiers': {
            'essential': [],
            'needed': ['auto_parts'],
            'extra': ['car_wash', 'upholstery', 'car_tinting', 'car_rental',
                      'car_dealer', 'ev_charging_station', 'parking'],
        }
    },

    # ───────────── 📱 الجوال والإلكترونيات ─────────────
    'mobile': {
        'name': '📱 جوال وإلكترونيات',
        'sector': 'الإلكترونيات',
        'tiers': {
            'essential': [],
            'needed': ['mobile_repair'],
            'extra': ['mobile_accessories', 'electronics_store'],
        }
    },

    # ───────────── 💰 المالية ─────────────
    'finance': {
        'name': '💰 خدمات مالية',
        'sector': 'مالي',
        'tiers': {
            'essential': ['atm'],
            'needed': ['bank'],
            'extra': [],
        }
    },

    # ───────────── 🕌 الديني والمجتمعي ─────────────
    'religious': {
        'name': '🕌 ديني',
        'sector': 'مجتمعي',
        'tiers': {
            'essential': ['mosque'],
            'needed': [],
            'extra': [],
        }
    },

    # ───────────── 🎭 الترفيه ونمط الحياة ─────────────
    'entertainment': {
        'name': '🎭 ترفيه ونمط حياة',
        'sector': 'الترفيه',
        'tiers': {
            'essential': [],
            'needed': ['park', 'playground'],
            'extra': ['cinema', 'fitness_center', 'shopping', 'game_center',
                      'museum', 'tourist_attraction', 'sporting_goods', 'nightclub'],
        }
    },

    # ───────────── 🏨 السفر والضيافة ─────────────
    'hospitality': {
        'name': '🏨 سفر وضيافة',
        'sector': 'السفر',
        'tiers': {
            'essential': [],
            'needed': ['hotel'],
            'extra': [],
        }
    },

    # ───────────── 🧰 خدمات عامة ─────────────
    'general_services': {
        'name': '🧰 خدمات عامة',
        'sector': 'خدمي',
        'tiers': {
            'essential': [],
            'needed': [],
            'extra': ['services'],
        }
    },
}

ACTIVITY_TYPES = {
    "مطعم": "restaurant",
    "مقهى / كافيه": "cafe",
    "وجبات سريعة": "fast_food",
    "محل تسوق عام": "shopping",
    "محل ملابس": "clothing_store",
    "محل إلكترونيات": "electronics_store",
    "محل منزلي / أثاث": "home_garden",
    "محل رياضي": "sporting_goods",
    "صيدلية": "pharmacy",
    "بقالة / سوبر ماركت": "grocery",
    "محطة وقود": "fuel",
    "خدمات عامة": "services",
    "صيانة سيارات": "auto_repair",
    "مغسلة سيارات": "car_wash",
    "معرض سيارات": "car_dealer",
    "تأجير سيارات": "car_rental",
    "محطة شحن كهربائي": "ev_charging_station",
    "مستشفى / مجمع طبي": "hospital",
    "عيادة": "clinic",
    "صالون تجميل / حلاقة": "beauty_salon",
    "نادي رياضي / جيم": "fitness_center",
    "سينما": "cinema",
    "بنك / صرّاف": "bank",
    "فندق / شقق فندقية": "hotel",
}


# ============================================================================
# 🧪 كيمياء العائلة - قاعدة الترابطات بين الأنشطة
# مبنية على:
#   - Retail Agglomeration Theory
#   - Co-Tenancy Effect (Brown 1987, Konishi 2005)
#   - Trip Chaining Behavior
#   - Central Place Theory
#   - السياق السعودي (مطعم+ديوانية، مغسلة+حلاق، إلخ)
# ============================================================================

# FAMILY_GROUPS: تصنيف الفئات إلى عائلات منطقية
# كل فئة لها عائلة رئيسية، وفي بعض الحالات عائلة ثانوية
FAMILY_GROUPS = {
    # 🍽️ عائلة الطعام والمشروبات
    "food_beverage": {
        "name": "الطعام والضيافة",
        "icon": "🍽️",
        "members": ["restaurant", "cafe", "fast_food"]
    },
    # 🛒 عائلة الاحتياجات اليومية
    "daily_essentials": {
        "name": "الاحتياجات اليومية",
        "icon": "🛒",
        "members": ["grocery", "pharmacy", "atm", "bank"]
    },
    # 🚗 عائلة السيارات
    "automotive": {
        "name": "خدمات السيارات",
        "icon": "🚗",
        "members": ["fuel", "auto_repair", "car_wash", "car_dealer", "car_rental",
                    "ev_charging_station", "parking"]
    },
    # 🛍️ عائلة التسوق
    "shopping_lifestyle": {
        "name": "التسوق ونمط الحياة",
        "icon": "🛍️",
        "members": ["shopping", "clothing_store", "electronics_store",
                    "home_garden", "sporting_goods"]
    },
    # ⚕️ عائلة الصحة والعناية الشخصية
    "health_wellness": {
        "name": "الصحة والعناية",
        "icon": "⚕️",
        "members": ["hospital", "clinic", "pharmacy", "beauty_salon", "fitness_center"]
    },
    # 🎬 عائلة الترفيه
    "entertainment": {
        "name": "الترفيه والثقافة",
        "icon": "🎬",
        "members": ["cinema", "park", "museum", "tourist_attraction", "library", "nightclub"]
    },
    # 🏨 عائلة السفر والضيافة
    "travel_hospitality": {
        "name": "السفر والإقامة",
        "icon": "🏨",
        "members": ["hotel", "tourist_attraction", "car_rental", "restaurant"]
    },
    # 🏫 عائلة التعليم والمجتمع
    "education_community": {
        "name": "التعليم والمجتمع",
        "icon": "🏫",
        "members": ["school", "library", "mosque"]
    },
    # 🔧 عائلة الخدمات
    "services": {
        "name": "الخدمات العامة",
        "icon": "🔧",
        "members": ["services", "atm", "bank"]
    },
}


# ============================================================================
# 🧬 مصفوفة الترابط (Chemistry Matrix)
# تحدد قوة العلاقة بين كل زوج من الفئات.
# المستويات: 'strong', 'medium', 'weak', 'compete', 'neutral'
#   strong   : ترابط قوي جداً - مكمّل مباشر (Trip Chaining واضح)
#   medium   : ترابط متوسط - يستفيدون من نفس الجمهور
#   weak     : ترابط ضعيف - متعايشون لكن لا تأثير ملحوظ
#   compete  : منافسة مباشرة - نفس الزبون والمنتج
#   neutral  : لا علاقة - مستقلون تماماً
# نخزّن فقط العلاقات غير-المحايدة (لتوفير الحجم)
# الشكل: (cat1, cat2): level
# ============================================================================

CHEMISTRY = {
    # ══════════════════════════════════════════════════
    # 🍽️ ترابطات عائلة الطعام
    # ══════════════════════════════════════════════════
    # سعودي تقليدي: عشاء ← قهوة/ديوانية
    ("restaurant", "cafe"): "strong",
    ("cafe", "restaurant"): "strong",
    # وجبات سريعة + قهوة (شباب)
    ("fast_food", "cafe"): "strong",
    ("cafe", "fast_food"): "strong",
    # تنوع طعام - مكمل
    ("restaurant", "fast_food"): "medium",
    ("fast_food", "restaurant"): "medium",
    # مطعم + حلويات/آيس كريم (تكملة الوجبة)
    # (سنضيف لاحقاً إذا توسعنا)

    # ══════════════════════════════════════════════════
    # 🛒 ترابطات الاحتياجات اليومية
    # ══════════════════════════════════════════════════
    # بقالة + صيدلية: رحلة احتياجات يومية
    ("grocery", "pharmacy"): "strong",
    ("pharmacy", "grocery"): "strong",
    # بقالة/صيدلية + صراف
    ("grocery", "atm"): "medium",
    ("atm", "grocery"): "medium",
    ("pharmacy", "atm"): "medium",
    ("atm", "pharmacy"): "medium",
    # بقالة/صيدلية + بنك
    ("grocery", "bank"): "medium",
    ("bank", "grocery"): "medium",
    # بقالة + مخبز/مطعم (شائع في السعودية)
    ("grocery", "restaurant"): "medium",
    ("restaurant", "grocery"): "medium",
    ("grocery", "fast_food"): "medium",
    ("fast_food", "grocery"): "medium",
    # بقالة + خدمات عامة
    ("grocery", "services"): "medium",
    ("services", "grocery"): "medium",

    # ══════════════════════════════════════════════════
    # 🚗 ترابطات عائلة السيارات (قوية جداً)
    # ══════════════════════════════════════════════════
    # محطة وقود + مغسلة (الكلاسيكي)
    ("fuel", "car_wash"): "strong",
    ("car_wash", "fuel"): "strong",
    # محطة وقود + صيانة
    ("fuel", "auto_repair"): "strong",
    ("auto_repair", "fuel"): "strong",
    # وقود + قهوة/سناك (المسافرون)
    ("fuel", "cafe"): "strong",
    ("cafe", "fuel"): "strong",
    ("fuel", "fast_food"): "strong",
    ("fast_food", "fuel"): "strong",
    # وقود + بقالة (محطة شاملة)
    ("fuel", "grocery"): "strong",
    ("grocery", "fuel"): "strong",
    # وقود + شحن كهربائي (تطور النشاط)
    ("fuel", "ev_charging_station"): "medium",
    ("ev_charging_station", "fuel"): "medium",
    # وقود + صراف
    ("fuel", "atm"): "medium",
    ("atm", "fuel"): "medium",
    # المغسلة + الحلاق (مثالك الشهير - الانتظار = خدمة)
    ("car_wash", "beauty_salon"): "strong",
    ("beauty_salon", "car_wash"): "strong",
    # المغسلة + المقهى (انتظار)
    ("car_wash", "cafe"): "strong",
    ("cafe", "car_wash"): "strong",
    ("car_wash", "fast_food"): "strong",
    ("fast_food", "car_wash"): "strong",
    # المغسلة + الصيانة
    ("car_wash", "auto_repair"): "strong",
    ("auto_repair", "car_wash"): "strong",
    # الصيانة + قطع الغيار (نمثلها بـ services)
    ("auto_repair", "services"): "medium",
    ("services", "auto_repair"): "medium",
    # الصيانة + قهوة (الانتظار)
    ("auto_repair", "cafe"): "medium",
    ("cafe", "auto_repair"): "medium",
    ("auto_repair", "fast_food"): "medium",
    ("fast_food", "auto_repair"): "medium",
    # معرض سيارات + تأجير (نفس المهتم)
    ("car_dealer", "car_rental"): "medium",
    ("car_rental", "car_dealer"): "medium",
    # معرض سيارات + تمويل/بنك
    ("car_dealer", "bank"): "medium",
    ("bank", "car_dealer"): "medium",
    # شحن كهربائي + كافيه (الانتظار 30-60 دقيقة)
    ("ev_charging_station", "cafe"): "strong",
    ("cafe", "ev_charging_station"): "strong",
    ("ev_charging_station", "restaurant"): "medium",
    ("restaurant", "ev_charging_station"): "medium",
    ("ev_charging_station", "shopping"): "medium",
    ("shopping", "ev_charging_station"): "medium",

    # ══════════════════════════════════════════════════
    # 🛍️ ترابطات التسوق
    # ══════════════════════════════════════════════════
    # تسوق + كافيه (شائع جداً)
    ("shopping", "cafe"): "strong",
    ("cafe", "shopping"): "strong",
    ("shopping", "restaurant"): "strong",
    ("restaurant", "shopping"): "strong",
    ("shopping", "fast_food"): "medium",
    ("fast_food", "shopping"): "medium",
    # ملابس + أحذية/إكسسوار (نمثلها بـ shopping)
    ("clothing_store", "shopping"): "strong",
    ("shopping", "clothing_store"): "strong",
    # ملابس + صالون تجميل (نفس الجمهور)
    ("clothing_store", "beauty_salon"): "strong",
    ("beauty_salon", "clothing_store"): "strong",
    # ملابس + كافيه
    ("clothing_store", "cafe"): "strong",
    ("cafe", "clothing_store"): "strong",
    ("clothing_store", "restaurant"): "medium",
    ("restaurant", "clothing_store"): "medium",
    # إلكترونيات + خدمات إصلاح (نمثلها بـ services)
    ("electronics_store", "services"): "medium",
    ("services", "electronics_store"): "medium",
    # إلكترونيات + كافيه
    ("electronics_store", "cafe"): "medium",
    ("cafe", "electronics_store"): "medium",
    # منازل وحدائق + إلكترونيات (تجهيز منزلي)
    ("home_garden", "electronics_store"): "medium",
    ("electronics_store", "home_garden"): "medium",
    # رياضي + جيم
    ("sporting_goods", "fitness_center"): "strong",
    ("fitness_center", "sporting_goods"): "strong",

    # ══════════════════════════════════════════════════
    # ⚕️ ترابطات الصحة
    # ══════════════════════════════════════════════════
    # عيادة + صيدلية (الكلاسيكي)
    ("clinic", "pharmacy"): "strong",
    ("pharmacy", "clinic"): "strong",
    # مستشفى + صيدلية
    ("hospital", "pharmacy"): "strong",
    ("pharmacy", "hospital"): "strong",
    # مستشفى + فندق/شقق (المرافقون من خارج المنطقة)
    ("hospital", "hotel"): "strong",
    ("hotel", "hospital"): "strong",
    # مستشفى + مطعم (مرافقون يتعشّون)
    ("hospital", "restaurant"): "medium",
    ("restaurant", "hospital"): "medium",
    ("hospital", "cafe"): "medium",
    ("cafe", "hospital"): "medium",
    ("hospital", "fast_food"): "medium",
    ("fast_food", "hospital"): "medium",
    # مستشفى + عيادات (تخصصات مكملة)
    ("hospital", "clinic"): "medium",
    ("clinic", "hospital"): "medium",
    # صالون + جيم (الصحة والجمال)
    ("beauty_salon", "fitness_center"): "strong",
    ("fitness_center", "beauty_salon"): "strong",
    # جيم + مطعم صحي/بروتين (نمثلها بـ restaurant)
    ("fitness_center", "restaurant"): "medium",
    ("restaurant", "fitness_center"): "medium",
    # جيم + كافيه (بعد التمرين)
    ("fitness_center", "cafe"): "medium",
    ("cafe", "fitness_center"): "medium",

    # ══════════════════════════════════════════════════
    # 🎬 ترابطات الترفيه
    # ══════════════════════════════════════════════════
    # سينما + مطعم/كافيه (قبل/بعد الفيلم)
    ("cinema", "restaurant"): "strong",
    ("restaurant", "cinema"): "strong",
    ("cinema", "cafe"): "strong",
    ("cafe", "cinema"): "strong",
    ("cinema", "fast_food"): "strong",
    ("fast_food", "cinema"): "strong",
    # سينما + تسوق (الخروج العائلي)
    ("cinema", "shopping"): "strong",
    ("shopping", "cinema"): "strong",
    # متنزه/حديقة + كافيه/مطعم
    ("park", "cafe"): "strong",
    ("cafe", "park"): "strong",
    ("park", "restaurant"): "strong",
    ("restaurant", "park"): "strong",
    ("park", "fast_food"): "medium",
    ("fast_food", "park"): "medium",
    # متحف + كافيه/مطعم
    ("museum", "cafe"): "medium",
    ("cafe", "museum"): "medium",
    ("museum", "restaurant"): "medium",
    ("restaurant", "museum"): "medium",
    # متحف + معالم سياحية
    ("museum", "tourist_attraction"): "strong",
    ("tourist_attraction", "museum"): "strong",
    # مكتبة + كافيه (دراسة وقراءة)
    ("library", "cafe"): "strong",
    ("cafe", "library"): "strong",

    # ══════════════════════════════════════════════════
    # 🏨 ترابطات السياحة والسفر
    # ══════════════════════════════════════════════════
    # فندق + مطعم (ضيافة كاملة)
    ("hotel", "restaurant"): "strong",
    ("restaurant", "hotel"): "strong",
    ("hotel", "cafe"): "strong",
    ("cafe", "hotel"): "strong",
    # فندق + معالم سياحية
    ("hotel", "tourist_attraction"): "strong",
    ("tourist_attraction", "hotel"): "strong",
    # فندق + تأجير سيارات
    ("hotel", "car_rental"): "strong",
    ("car_rental", "hotel"): "strong",
    # فندق + متحف
    ("hotel", "museum"): "medium",
    ("museum", "hotel"): "medium",
    # معالم سياحية + مطاعم/كافيهات
    ("tourist_attraction", "restaurant"): "strong",
    ("restaurant", "tourist_attraction"): "strong",
    ("tourist_attraction", "cafe"): "strong",
    ("cafe", "tourist_attraction"): "strong",
    # معالم سياحية + تسوق (تذكارات)
    ("tourist_attraction", "shopping"): "strong",
    ("shopping", "tourist_attraction"): "strong",

    # ══════════════════════════════════════════════════
    # 🏫 ترابطات التعليم والمجتمع
    # ══════════════════════════════════════════════════
    # مدرسة + بقالة/قرطاسية (نمثلها بـ grocery و services)
    ("school", "grocery"): "medium",
    ("grocery", "school"): "medium",
    ("school", "services"): "medium",
    ("services", "school"): "medium",
    # مدرسة + مطعم سريع (وجبات الأطفال)
    ("school", "fast_food"): "medium",
    ("fast_food", "school"): "medium",
    # مكتبة + مدرسة
    ("library", "school"): "strong",
    ("school", "library"): "strong",
    # مسجد + كل شي تقريباً (مركز المجتمع)
    ("mosque", "grocery"): "medium",
    ("grocery", "mosque"): "medium",
    ("mosque", "restaurant"): "medium",
    ("restaurant", "mosque"): "medium",

    # ══════════════════════════════════════════════════
    # 🏦 ترابطات المالية
    # ══════════════════════════════════════════════════
    # بنك + صراف (مكملان)
    ("bank", "atm"): "strong",
    ("atm", "bank"): "strong",
    # بنك + تسوق (سحب نقدي قبل التسوق)
    ("bank", "shopping"): "medium",
    ("shopping", "bank"): "medium",
    ("atm", "shopping"): "medium",
    ("shopping", "atm"): "medium",
    # بنك + مطعم
    ("atm", "restaurant"): "medium",
    ("restaurant", "atm"): "medium",

    # ══════════════════════════════════════════════════
    # ❌ منافسات مباشرة (نفس الزبون والمنتج)
    # ══════════════════════════════════════════════════
    # مهم: التشبع يعكس هذا، لكن نوضحه هنا للتفسير
    # (لا نخصم نقاطاً إضافية، فقط لتمييز "وجود منافسة")
}


# ============================================================================
# 🧪 محرك تحليل الانسجام (Family Chemistry Engine)
# ============================================================================

def get_chemistry(cat_a, cat_b):
    """يرجع مستوى الترابط بين فئتين"""
    if cat_a == cat_b:
        return "compete"  # نفس الفئة = منافسة
    rel = CHEMISTRY.get((cat_a, cat_b))
    if rel:
        return rel
    # محاولة عكسية (للأمان رغم أننا نخزّن الاتجاهين)
    rel = CHEMISTRY.get((cat_b, cat_a))
    if rel:
        return rel
    return "neutral"


def chemistry_score(level):
    """يحوّل مستوى الترابط لنقاط رقمية"""
    return {
        "strong": 10,
        "medium": 5,
        "weak": 1,
        "neutral": 0,
        "compete": -3,  # وجود محل مماثل = ضغط تنافسي
    }.get(level, 0)


def family_chemistry_analysis(target_cat, pbc):
    """
    يحلل مدى انسجام نشاط معين مع المحيط التجاري الموجود.
    
    يرجع dict فيه:
    - harmony_score: 0-100 درجة الانسجام
    - harmony_level: نص توصيفي
    - synergies: قائمة الترابطات القوية (لماذا ينسجم)
    - conflicts: قائمة المنافسات (تنافس مباشر)
    - neutral_count: عدد الأنشطة المحايدة
    - family_alignment: درجة انتماء النشاط للعائلة الغالبة
    """
    if not target_cat or target_cat not in CATEGORIES:
        return None
    
    synergies = []
    medium_links = []
    conflicts = []
    neutral_count = 0
    
    # نحسب القوة المطلقة للترابطات (Synergy Power)
    # بدلاً من قسمة بسيطة، نستخدم منطق "كم محل مكمّل بقوة موجود في المنطقة"
    strong_power = 0  # مجموع المحلات القوية مع وزن
    medium_power = 0
    compete_pressure = 0
    
    for other_cat, places in pbc.items():
        if not places:
            continue
        count = len(places)
        level = get_chemistry(target_cat, other_cat)
        
        # سقف 8 محلات لكل فئة (لتجنب الإفراط)
        effective_count = min(count, 8)
        
        cat_info = CATEGORIES.get(other_cat, {})
        cat_name = cat_info.get("name", other_cat)
        cat_icon = cat_info.get("icon", "")
        
        if level == "strong":
            strong_power += effective_count * 10
            synergies.append({
                "cat": other_cat,
                "icon": cat_icon,
                "name": cat_name,
                "count": count,
                "reason": _explain_synergy(target_cat, other_cat),
            })
        elif level == "medium":
            medium_power += effective_count * 4
            medium_links.append({
                "cat": other_cat,
                "icon": cat_icon,
                "name": cat_name,
                "count": count,
            })
        elif level == "compete":
            compete_pressure += min(count, 5) * 2
            conflicts.append({
                "cat": other_cat,
                "icon": cat_icon,
                "name": cat_name,
                "count": count,
            })
        else:
            neutral_count += count
    
    # المعادلة الجديدة:
    # القوة المطلقة (لها سقف ~80) + بونص العائلة الغالبة - ضغط المنافسة
    # الهدف: نشاط عنده 3+ ترابطات قوية مع 5+ محلات = انسجام ممتاز
    raw_harmony = strong_power + medium_power - compete_pressure
    
    # تطبيع: نقطة كل 1 = راو ~140 = 100%
    # أي: 6 ترابطات قوية × 8 محلات × 10 = 480 (مع سقف معقول)
    # نستخدم تحويل لوغاريتمي مبسّط لتعطي توزيع جيد
    if raw_harmony <= 0:
        harmony = 0
    else:
        # 0-30 → 0-40 (سريع لتمييز "لا انسجام")
        # 30-100 → 40-70 (متوسط)
        # 100-200 → 70-90 (جيد)
        # 200+ → 90-100 (ممتاز)
        if raw_harmony <= 30:
            harmony = int(raw_harmony * 40 / 30)
        elif raw_harmony <= 100:
            harmony = 40 + int((raw_harmony - 30) * 30 / 70)
        elif raw_harmony <= 200:
            harmony = 70 + int((raw_harmony - 100) * 20 / 100)
        else:
            harmony = min(100, 90 + int((raw_harmony - 200) / 20))
    
    # تصنيف الانسجام
    if harmony >= 70:
        harmony_level = "انسجام ممتاز"
        harmony_color = "#10b981"
    elif harmony >= 50:
        harmony_level = "انسجام جيد"
        harmony_color = "#22c55e"
    elif harmony >= 30:
        harmony_level = "انسجام متوسط"
        harmony_color = "#f59e0b"
    elif harmony >= 15:
        harmony_level = "انسجام ضعيف"
        harmony_color = "#f97316"
    else:
        harmony_level = "غريب عن المحيط"
        harmony_color = "#ef4444"
    
    # تحديد العائلة الغالبة في المنطقة
    family_counts = {}
    for other_cat, places in pbc.items():
        for fam_key, fam in FAMILY_GROUPS.items():
            if other_cat in fam["members"]:
                family_counts[fam_key] = family_counts.get(fam_key, 0) + len(places)
    
    dominant_family = None
    if family_counts:
        dominant_family_key = max(family_counts, key=family_counts.get)
        dominant_family = {
            "key": dominant_family_key,
            "name": FAMILY_GROUPS[dominant_family_key]["name"],
            "icon": FAMILY_GROUPS[dominant_family_key]["icon"],
            "count": family_counts[dominant_family_key],
        }
    
    # هل نشاطنا ينتمي لنفس العائلة؟
    target_families = [fk for fk, fam in FAMILY_GROUPS.items() if target_cat in fam["members"]]
    aligned_with_dominant = bool(dominant_family and dominant_family["key"] in target_families)
    
    return {
        "harmony_score": harmony,
        "harmony_level": harmony_level,
        "harmony_color": harmony_color,
        "synergies": sorted(synergies, key=lambda x: -x["count"])[:6],
        "medium_links": sorted(medium_links, key=lambda x: -x["count"])[:4],
        "conflicts": sorted(conflicts, key=lambda x: -x["count"])[:3],
        "neutral_count": neutral_count,
        "dominant_family": dominant_family,
        "aligned_with_dominant": aligned_with_dominant,
        "target_families": target_families,
        "raw_power": raw_harmony,
    }


def _explain_synergy(cat_a, cat_b):
    """يفسّر لماذا الترابط قوي بين فئتين"""
    # قاموس تفسيرات السعودية
    explanations = {
        ("restaurant", "cafe"): "العشاء ثم القهوة/الديوانية - تقليد سعودي",
        ("cafe", "restaurant"): "القهوة قبل أو بعد الوجبة",
        ("car_wash", "beauty_salon"): "اغسل سيارتك وأنت تحلق",
        ("beauty_salon", "car_wash"): "خدمة شخصية + خدمة سيارة في زيارة واحدة",
        ("fuel", "car_wash"): "عبّي البنزين واغسل السيارة",
        ("fuel", "cafe"): "استراحة المسافر",
        ("fuel", "fast_food"): "وجبة سريعة للمسافر",
        ("fuel", "grocery"): "محطة شاملة - وقود وأساسيات",
        ("clinic", "pharmacy"): "الوصفة الطبية → الدواء مباشرة",
        ("hospital", "pharmacy"): "صيدلية للمرضى والمرافقين",
        ("hospital", "hotel"): "إقامة للمرافقين من خارج المنطقة",
        ("ev_charging_station", "cafe"): "وقت الشحن (30-60 دقيقة) = استراحة",
        ("cinema", "restaurant"): "الخروج العائلي - عشاء وفيلم",
        ("cinema", "cafe"): "قبل أو بعد الفيلم",
        ("cinema", "shopping"): "اليوم العائلي الكامل",
        ("park", "cafe"): "نزهة وقهوة",
        ("park", "restaurant"): "العشاء في الحديقة",
        ("hotel", "restaurant"): "ضيافة كاملة للنزلاء",
        ("hotel", "tourist_attraction"): "السياح يحتاجون إقامة قريبة",
        ("tourist_attraction", "shopping"): "تذكارات وهدايا",
        ("car_wash", "cafe"): "انتظار غسيل = وقت قهوة",
        ("auto_repair", "fuel"): "خدمات سيارات متكاملة",
        ("car_wash", "auto_repair"): "كل خدمات السيارة في مكان واحد",
        ("clothing_store", "beauty_salon"): "إطلالة كاملة - ملابس وعناية",
        ("clothing_store", "cafe"): "تسوق وقهوة",
        ("shopping", "cafe"): "استراحة بين المحلات",
        ("shopping", "restaurant"): "تسوق ثم وجبة",
        ("library", "cafe"): "قراءة ومذاكرة وقهوة",
        ("museum", "tourist_attraction"): "محاور ثقافية متكاملة",
        ("sporting_goods", "fitness_center"): "نفس الجمهور الرياضي",
        ("fitness_center", "beauty_salon"): "العناية بالصحة والجمال",
        ("grocery", "pharmacy"): "احتياجات يومية في رحلة واحدة",
        ("bank", "atm"): "خدمات مالية متكاملة",
        ("car_dealer", "car_rental"): "نفس المهتم بالسيارات",
        ("library", "school"): "موارد تعليمية",
    }
    return explanations.get((cat_a, cat_b)) or explanations.get((cat_b, cat_a)) or "تكامل وظيفي بين النشاطين"


# ============================================================================
# [الدفعة 1] بيانات السكان للمحافظات السعودية (GASTAT 2022 + مصادر موثقة)
# ============================================================================
# المصدر: تعداد 2022 - الهيئة العامة للإحصاء + Wikipedia (citypopulation.de)
# البنية: اسم المحافظة بالعربية والإنجليزية -> {السكان, المساحة كم², المنطقة, lat تقريبي, lng تقريبي}
SAUDI_GOVERNORATES = {
    # ========== منطقة الرياض ==========
    "الرياض": {"pop": 7009100, "area": 1913, "region": "الرياض", "lat": 24.7136, "lng": 46.6753, "aliases": ["Riyadh", "ar-Riyad", "الرياض"]},
    "الدرعية": {"pop": 75571, "area": 4500, "region": "الرياض", "lat": 24.7339, "lng": 46.5750, "aliases": ["Diriyah", "Ad-Diriyah", "Dir'iyah"]},
    "الخرج": {"pop": 425300, "area": 19790, "region": "الرياض", "lat": 24.1556, "lng": 47.3120, "aliases": ["Al-Kharj", "Kharj"]},
    "الدوادمي": {"pop": 456684, "area": 27740, "region": "الرياض", "lat": 24.5070, "lng": 44.3927, "aliases": ["Al-Dawadmi", "Dawadmi"]},
    "المجمعة": {"pop": 80300, "area": 30000, "region": "الرياض", "lat": 25.9077, "lng": 45.3667, "aliases": ["Al-Majma'ah", "Majmaah"]},
    "القويعية": {"pop": 100000, "area": 33000, "region": "الرياض", "lat": 24.0830, "lng": 45.2700, "aliases": ["Al-Quwaiiyah", "Quwaiiyah"]},
    "وادي الدواسر": {"pop": 117000, "area": 56000, "region": "الرياض", "lat": 20.4500, "lng": 44.8000, "aliases": ["Wadi ad-Dawasir", "Dawasir"]},
    "الأفلاج": {"pop": 75000, "area": 54000, "region": "الرياض", "lat": 22.2700, "lng": 46.7333, "aliases": ["Al-Aflaj", "Aflaj"]},
    "الزلفي": {"pop": 79000, "area": 4500, "region": "الرياض", "lat": 26.3000, "lng": 44.8167, "aliases": ["Az-Zulfi", "Zulfi"]},
    "شقراء": {"pop": 50000, "area": 7500, "region": "الرياض", "lat": 25.2517, "lng": 45.2520, "aliases": ["Shaqra", "Shaqraa"]},
    "حوطة بني تميم": {"pop": 35000, "area": 2500, "region": "الرياض", "lat": 23.5167, "lng": 46.8500, "aliases": ["Hawtat Bani Tamim"]},
    "عفيف": {"pop": 78000, "area": 12300, "region": "الرياض", "lat": 23.9080, "lng": 42.9170, "aliases": ["Afif"]},
    "حريملاء": {"pop": 27000, "area": 1500, "region": "الرياض", "lat": 25.1167, "lng": 46.1167, "aliases": ["Huraymila"]},
    "ضرما": {"pop": 35000, "area": 4400, "region": "الرياض", "lat": 24.6167, "lng": 46.2167, "aliases": ["Dhurma"]},
    "المزاحمية": {"pop": 50000, "area": 1700, "region": "الرياض", "lat": 24.4667, "lng": 46.2500, "aliases": ["Al-Muzahimiyah"]},
    "ثادق": {"pop": 18000, "area": 3500, "region": "الرياض", "lat": 25.2900, "lng": 45.8600, "aliases": ["Thadiq"]},
    "رماح": {"pop": 22000, "area": 22000, "region": "الرياض", "lat": 25.5667, "lng": 47.1500, "aliases": ["Rumah"]},
    "السليل": {"pop": 38000, "area": 35000, "region": "الرياض", "lat": 20.4667, "lng": 45.5667, "aliases": ["As-Sulayyil"]},
    "الحريق": {"pop": 14000, "area": 3000, "region": "الرياض", "lat": 23.6167, "lng": 46.4833, "aliases": ["Al-Hariq"]},
    "الغاط": {"pop": 14000, "area": 3700, "region": "الرياض", "lat": 26.0167, "lng": 44.9833, "aliases": ["Al-Ghat"]},
    # ========== منطقة مكة المكرمة ==========
    "مكة المكرمة": {"pop": 2427924, "area": 3852, "region": "مكة", "lat": 21.4225, "lng": 39.8262, "aliases": ["Mecca", "Makkah", "Makkah al-Mukarramah"]},
    "جدة": {"pop": 3751700, "area": 5460, "region": "مكة", "lat": 21.4858, "lng": 39.1925, "aliases": ["Jeddah", "Jiddah"]},
    "الطائف": {"pop": 913400, "area": 13800, "region": "مكة", "lat": 21.2840, "lng": 40.4030, "aliases": ["Taif", "At-Ta'if"]},
    "القنفذة": {"pop": 272000, "area": 12500, "region": "مكة", "lat": 19.1268, "lng": 41.0876, "aliases": ["Al-Qunfudhah", "Qunfudhah"]},
    "الليث": {"pop": 200000, "area": 24500, "region": "مكة", "lat": 20.1450, "lng": 40.2810, "aliases": ["Al-Lith", "Lith"]},
    "رابغ": {"pop": 175000, "area": 17000, "region": "مكة", "lat": 22.7989, "lng": 39.0353, "aliases": ["Rabigh"]},
    "خليص": {"pop": 78000, "area": 8500, "region": "مكة", "lat": 22.1500, "lng": 39.3167, "aliases": ["Khulays"]},
    "الكامل": {"pop": 33000, "area": 3500, "region": "مكة", "lat": 22.2500, "lng": 39.6500, "aliases": ["Al-Kamil"]},
    "الجموم": {"pop": 78000, "area": 5000, "region": "مكة", "lat": 21.6167, "lng": 39.6833, "aliases": ["Al-Jumum"]},
    "ميسان": {"pop": 30000, "area": 4500, "region": "مكة", "lat": 21.0000, "lng": 40.7000, "aliases": ["Maysan"]},
    "أضم": {"pop": 18000, "area": 3500, "region": "مكة", "lat": 20.1167, "lng": 41.1833, "aliases": ["Adham"]},
    "تربة": {"pop": 32000, "area": 6500, "region": "مكة", "lat": 21.2167, "lng": 41.6333, "aliases": ["Turabah"]},
    "رنية": {"pop": 32000, "area": 12000, "region": "مكة", "lat": 21.2667, "lng": 42.8500, "aliases": ["Raniyah"]},
    "الخرمة": {"pop": 32000, "area": 11000, "region": "مكة", "lat": 21.9333, "lng": 42.0500, "aliases": ["Al-Khurma", "Khurmah"]},
    # ========== المنطقة الشرقية ==========
    "الدمام": {"pop": 1532300, "area": 800, "region": "الشرقية", "lat": 26.4207, "lng": 50.0888, "aliases": ["Dammam", "Ad-Dammam"]},
    "الأحساء": {"pop": 1104267, "area": 379000, "region": "الشرقية", "lat": 25.3833, "lng": 49.5833, "aliases": ["Al-Ahsa", "Hofuf"]},
    "الخبر": {"pop": 658550, "area": 750, "region": "الشرقية", "lat": 26.2172, "lng": 50.1971, "aliases": ["Khobar", "Al-Khobar"]},
    "القطيف": {"pop": 552442, "area": 1200, "region": "الشرقية", "lat": 26.5650, "lng": 50.0078, "aliases": ["Qatif", "Al-Qatif"]},
    "الجبيل": {"pop": 505162, "area": 1016, "region": "الشرقية", "lat": 27.0046, "lng": 49.6594, "aliases": ["Jubail", "Al-Jubail"]},
    "حفر الباطن": {"pop": 467007, "area": 137600, "region": "الشرقية", "lat": 28.4337, "lng": 45.9601, "aliases": ["Hafar al-Batin"]},
    "الخفجي": {"pop": 84316, "area": 1500, "region": "الشرقية", "lat": 28.4326, "lng": 48.4914, "aliases": ["Khafji", "Al-Khafji"]},
    "رأس تنورة": {"pop": 62314, "area": 800, "region": "الشرقية", "lat": 26.6443, "lng": 50.1599, "aliases": ["Ras Tanura"]},
    "النعيرية": {"pop": 52340, "area": 87000, "region": "الشرقية", "lat": 27.4836, "lng": 48.4836, "aliases": ["Nariyah", "An-Nariyah"]},
    "بقيق": {"pop": 45032, "area": 6000, "region": "الشرقية", "lat": 25.9333, "lng": 49.6667, "aliases": ["Abqaiq", "Buqayq"]},
    "قرية العليا": {"pop": 24634, "area": 4500, "region": "الشرقية", "lat": 27.6500, "lng": 47.5333, "aliases": ["Qaryat al-Ulya"]},
    # ========== منطقة المدينة المنورة ==========
    "المدينة المنورة": {"pop": 1477000, "area": 173000, "region": "المدينة", "lat": 24.5247, "lng": 39.5692, "aliases": ["Medina", "Madinah", "Al-Madinah"]},
    "ينبع": {"pop": 359631, "area": 30000, "region": "المدينة", "lat": 24.0890, "lng": 38.0618, "aliases": ["Yanbu"]},
    "العلا": {"pop": 60103, "area": 22500, "region": "المدينة", "lat": 26.6311, "lng": 37.9220, "aliases": ["Al-Ula", "AlUla"]},
    "بدر": {"pop": 58259, "area": 9500, "region": "المدينة", "lat": 23.7833, "lng": 38.7833, "aliases": ["Badr"]},
    "المهد": {"pop": 48590, "area": 7300, "region": "المدينة", "lat": 23.4861, "lng": 40.8989, "aliases": ["Mahd", "Mahd ad-Dhahab"]},
    "خيبر": {"pop": 45532, "area": 17000, "region": "المدينة", "lat": 25.7029, "lng": 39.2924, "aliases": ["Khaybar"]},
    "الحناكية": {"pop": 43256, "area": 17500, "region": "المدينة", "lat": 24.9000, "lng": 40.5000, "aliases": ["Al-Hunakiyah"]},
    "وادي الفرع": {"pop": 23120, "area": 6800, "region": "المدينة", "lat": 23.6000, "lng": 39.6000, "aliases": ["Wadi al-Fara"]},
    # ========== منطقة عسير ==========
    "أبها": {"pop": 1093705, "area": 80000, "region": "عسير", "lat": 18.2164, "lng": 42.5053, "aliases": ["Abha"]},
    "خميس مشيط": {"pop": 666700, "area": 5300, "region": "عسير", "lat": 18.3000, "lng": 42.7333, "aliases": ["Khamis Mushait", "Khamis Mushayt"]},
    "بيشة": {"pop": 250000, "area": 36500, "region": "عسير", "lat": 19.9744, "lng": 42.5908, "aliases": ["Bisha"]},
    "محايل": {"pop": 192000, "area": 5500, "region": "عسير", "lat": 18.5500, "lng": 42.0500, "aliases": ["Mahayel", "Muhayil"]},
    "أحد رفيدة": {"pop": 102000, "area": 4500, "region": "عسير", "lat": 18.2333, "lng": 42.8500, "aliases": ["Ahad Rufaydah"]},
    "ظهران الجنوب": {"pop": 65000, "area": 5500, "region": "عسير", "lat": 17.6833, "lng": 43.5167, "aliases": ["Dhahran al-Janub"]},
    "النماص": {"pop": 60000, "area": 2200, "region": "عسير", "lat": 19.1500, "lng": 42.1167, "aliases": ["An-Namas"]},
    "تثليث": {"pop": 53224, "area": 10000, "region": "عسير", "lat": 19.5667, "lng": 43.3000, "aliases": ["Tathlith"]},
    "بارق": {"pop": 75432, "area": 6650, "region": "عسير", "lat": 18.9358, "lng": 41.9358, "aliases": ["Bariq", "Bareq"]},
    "بلقرن": {"pop": 70000, "area": 5500, "region": "عسير", "lat": 19.7833, "lng": 41.6167, "aliases": ["Balqarn"]},
    "تنومة": {"pop": 40000, "area": 1800, "region": "عسير", "lat": 19.7500, "lng": 42.1500, "aliases": ["Tanumah"]},
    "رجال ألمع": {"pop": 41000, "area": 1800, "region": "عسير", "lat": 18.2167, "lng": 42.2000, "aliases": ["Rijal Alma"]},
    "سراة عبيدة": {"pop": 65000, "area": 4500, "region": "عسير", "lat": 18.1167, "lng": 42.6667, "aliases": ["Sarat Abidah"]},
    "المجاردة": {"pop": 45000, "area": 5500, "region": "عسير", "lat": 19.1167, "lng": 41.9000, "aliases": ["Al-Majardah"]},
    "البرك": {"pop": 22000, "area": 1500, "region": "عسير", "lat": 18.2167, "lng": 41.5333, "aliases": ["Al-Birk"]},
    # ========== منطقة جازان ==========
    "جازان": {"pop": 200911, "area": 1500, "region": "جازان", "lat": 16.8892, "lng": 42.5511, "aliases": ["Jazan", "Jizan"]},
    "صبيا": {"pop": 235000, "area": 3500, "region": "جازان", "lat": 17.1500, "lng": 42.6167, "aliases": ["Sabya"]},
    "أبو عريش": {"pop": 187060, "area": 1500, "region": "جازان", "lat": 16.9667, "lng": 42.8333, "aliases": ["Abu Arish"]},
    "صامطة": {"pop": 160000, "area": 1200, "region": "جازان", "lat": 16.6000, "lng": 42.9333, "aliases": ["Samtah"]},
    "أحد المسارحة": {"pop": 70000, "area": 800, "region": "جازان", "lat": 16.7167, "lng": 43.0167, "aliases": ["Ahad Al-Masarihah"]},
    "بيش": {"pop": 92000, "area": 1500, "region": "جازان", "lat": 17.3833, "lng": 42.6000, "aliases": ["Baish"]},
    "ضمد": {"pop": 75000, "area": 800, "region": "جازان", "lat": 16.9333, "lng": 42.7500, "aliases": ["Damad"]},
    "فرسان": {"pop": 18000, "area": 700, "region": "جازان", "lat": 16.7100, "lng": 42.1166, "aliases": ["Farasan"]},
    "العارضة": {"pop": 60000, "area": 1500, "region": "جازان", "lat": 16.7333, "lng": 43.0167, "aliases": ["Al-Aridah"]},
    "العيدابي": {"pop": 50000, "area": 900, "region": "جازان", "lat": 17.2167, "lng": 43.0000, "aliases": ["Al-Aydabi"]},
    "هروب": {"pop": 25000, "area": 600, "region": "جازان", "lat": 16.7833, "lng": 43.1000, "aliases": ["Harub"]},
    "الدائر": {"pop": 58320, "area": 1500, "region": "جازان", "lat": 17.3000, "lng": 43.1833, "aliases": ["Al-Dayer"]},
    "الريث": {"pop": 25000, "area": 1500, "region": "جازان", "lat": 17.2000, "lng": 43.0500, "aliases": ["Ar-Reeth"]},
    # ========== منطقة القصيم ==========
    "بريدة": {"pop": 745353, "area": 22500, "region": "القصيم", "lat": 26.3260, "lng": 43.9750, "aliases": ["Buraidah", "Buraydah"]},
    "عنيزة": {"pop": 200000, "area": 4500, "region": "القصيم", "lat": 26.0848, "lng": 43.9869, "aliases": ["Unayzah"]},
    "الرس": {"pop": 133482, "area": 11500, "region": "القصيم", "lat": 25.8721, "lng": 43.4977, "aliases": ["Ar-Rass", "Al-Rass"]},
    "المذنب": {"pop": 50000, "area": 4500, "region": "القصيم", "lat": 25.8625, "lng": 44.2231, "aliases": ["Al-Mithnab"]},
    "البكيرية": {"pop": 70000, "area": 1500, "region": "القصيم", "lat": 26.1399, "lng": 43.6601, "aliases": ["Al-Bukayriyah"]},
    "البدائع": {"pop": 53000, "area": 4500, "region": "القصيم", "lat": 26.0000, "lng": 43.8000, "aliases": ["Al-Bada'i"]},
    "رياض الخبراء": {"pop": 31203, "area": 1707, "region": "القصيم", "lat": 26.5333, "lng": 43.5500, "aliases": ["Riyadh Al Khabra"]},
    "الأسياح": {"pop": 25000, "area": 4500, "region": "القصيم", "lat": 26.4667, "lng": 43.2333, "aliases": ["Al-Asyah"]},
    "النبهانية": {"pop": 16000, "area": 3500, "region": "القصيم", "lat": 25.4833, "lng": 41.5167, "aliases": ["An-Nabhaniyah"]},
    "الشماسية": {"pop": 15000, "area": 1500, "region": "القصيم", "lat": 26.5167, "lng": 43.8333, "aliases": ["Ash-Shamasiyah"]},
    "عيون الجواء": {"pop": 19000, "area": 1500, "region": "القصيم", "lat": 26.4500, "lng": 43.7000, "aliases": ["Uyun al-Jawa"]},
    "ضرية": {"pop": 14000, "area": 5500, "region": "القصيم", "lat": 25.7167, "lng": 42.3500, "aliases": ["Dariyah"]},
    # ========== منطقة تبوك ==========
    "تبوك": {"pop": 803585, "area": 117000, "region": "تبوك", "lat": 28.3998, "lng": 36.5700, "aliases": ["Tabuk"]},
    "أملج": {"pop": 69656, "area": 18000, "region": "تبوك", "lat": 25.0314, "lng": 37.2675, "aliases": ["Umluj"]},
    "الوجه": {"pop": 49948, "area": 18000, "region": "تبوك", "lat": 26.2333, "lng": 36.4500, "aliases": ["Al-Wajh"]},
    "ضباء": {"pop": 54917, "area": 14000, "region": "تبوك", "lat": 27.3500, "lng": 35.7000, "aliases": ["Duba"]},
    "تيماء": {"pop": 42164, "area": 3500, "region": "تبوك", "lat": 27.6310, "lng": 38.5527, "aliases": ["Tayma"]},
    "حقل": {"pop": 27712, "area": 2500, "region": "تبوك", "lat": 29.2876, "lng": 34.9419, "aliases": ["Haql"]},
    "البدع": {"pop": 17973, "area": 5500, "region": "تبوك", "lat": 28.5000, "lng": 35.0833, "aliases": ["Al-Bad"]},
    "نيوم": {"pop": 100000, "area": 26500, "region": "تبوك", "lat": 27.9667, "lng": 35.5333, "aliases": ["Neom", "NEOM"]},
    # ========== منطقة حائل ==========
    "حائل": {"pop": 412758, "area": 103887, "region": "حائل", "lat": 27.5114, "lng": 41.7208, "aliases": ["Hail", "Ha'il"]},
    "بقعاء": {"pop": 56362, "area": 12000, "region": "حائل", "lat": 27.4667, "lng": 42.2333, "aliases": ["Baqaa"]},
    "الشنان": {"pop": 29419, "area": 8500, "region": "حائل", "lat": 27.5500, "lng": 40.5167, "aliases": ["Shanan"]},
    "الشملي": {"pop": 20946, "area": 11500, "region": "حائل", "lat": 27.0667, "lng": 40.6333, "aliases": ["Shamli"]},
    "السميراء": {"pop": 19563, "area": 8500, "region": "حائل", "lat": 27.6333, "lng": 41.2333, "aliases": ["Sumairah"]},
    "الغزالة": {"pop": 12767, "area": 4500, "region": "حائل", "lat": 26.7833, "lng": 41.3833, "aliases": ["Ghazalah"]},
    "موقق": {"pop": 16835, "area": 5500, "region": "حائل", "lat": 27.6500, "lng": 39.8500, "aliases": ["Mawqaq"]},
    "السليمي": {"pop": 17343, "area": 6500, "region": "حائل", "lat": 27.0167, "lng": 41.7333, "aliases": ["Sulaimi"]},
    "حايط": {"pop": 74596, "area": 5500, "region": "حائل", "lat": 26.2333, "lng": 40.4167, "aliases": ["Hait"]},
    # ========== منطقة الحدود الشمالية ==========
    "عرعر": {"pop": 218000, "area": 27500, "region": "الحدود الشمالية", "lat": 30.9753, "lng": 41.0381, "aliases": ["Arar"]},
    "رفحاء": {"pop": 84536, "area": 31500, "region": "الحدود الشمالية", "lat": 29.6320, "lng": 43.4940, "aliases": ["Rafha"]},
    "طريف": {"pop": 66004, "area": 22000, "region": "الحدود الشمالية", "lat": 31.5278, "lng": 38.6634, "aliases": ["Turaif"]},
    "العويقيلة": {"pop": 20318, "area": 23500, "region": "الحدود الشمالية", "lat": 30.3500, "lng": 42.3333, "aliases": ["Al-Uwayqilah"]},
    # ========== منطقة الجوف ==========
    "سكاكا": {"pop": 247549, "area": 33500, "region": "الجوف", "lat": 29.9697, "lng": 40.2064, "aliases": ["Sakaka"]},
    "القريات": {"pop": 175547, "area": 50000, "region": "الجوف", "lat": 31.3325, "lng": 37.3431, "aliases": ["Al-Qurayyat"]},
    "دومة الجندل": {"pop": 50000, "area": 3500, "region": "الجوف", "lat": 29.8128, "lng": 39.8717, "aliases": ["Dumat Al-Jandal"]},
    "طبرجل": {"pop": 30000, "area": 2500, "region": "الجوف", "lat": 30.5036, "lng": 38.2089, "aliases": ["Tabarjal"]},
    # ========== منطقة نجران ==========
    "نجران": {"pop": 505652, "area": 75000, "region": "نجران", "lat": 17.4924, "lng": 44.1277, "aliases": ["Najran"]},
    "شرورة": {"pop": 100199, "area": 75000, "region": "نجران", "lat": 17.4830, "lng": 47.1230, "aliases": ["Sharurah"]},
    "حبونا": {"pop": 24823, "area": 4500, "region": "نجران", "lat": 17.5333, "lng": 44.5333, "aliases": ["Habona"]},
    "ثار": {"pop": 13391, "area": 4500, "region": "نجران", "lat": 17.7000, "lng": 44.7000, "aliases": ["Thar"]},
    "يدمة": {"pop": 16160, "area": 5500, "region": "نجران", "lat": 17.7500, "lng": 45.5500, "aliases": ["Yadamah"]},
    "بدر الجنوب": {"pop": 7991, "area": 3500, "region": "نجران", "lat": 17.9333, "lng": 44.0833, "aliases": ["Badr Al-Janub"]},
    "خباش": {"pop": 7834, "area": 2500, "region": "نجران", "lat": 17.8000, "lng": 44.7833, "aliases": ["Khubash"]},
    # ========== منطقة الباحة ==========
    "الباحة": {"pop": 100000, "area": 1000, "region": "الباحة", "lat": 20.0129, "lng": 41.4677, "aliases": ["Al-Bahah", "Baha"]},
    "بلجرشي": {"pop": 75000, "area": 1200, "region": "الباحة", "lat": 19.8606, "lng": 41.5594, "aliases": ["Baljurashi"]},
    "المندق": {"pop": 35000, "area": 800, "region": "الباحة", "lat": 20.1833, "lng": 41.2833, "aliases": ["Al-Mandaq"]},
    "المخواة": {"pop": 95000, "area": 4500, "region": "الباحة", "lat": 19.7667, "lng": 41.4167, "aliases": ["Al-Mikhwah"]},
    "قلوة": {"pop": 60000, "area": 2500, "region": "الباحة", "lat": 19.5667, "lng": 41.6833, "aliases": ["Qilwah"]},
    "العقيق": {"pop": 45000, "area": 6500, "region": "الباحة", "lat": 20.2667, "lng": 41.6833, "aliases": ["Al-Aqiq"]},
    "القرى": {"pop": 30000, "area": 700, "region": "الباحة", "lat": 20.0000, "lng": 41.4333, "aliases": ["Al-Qura"]},
    "بني حسن": {"pop": 25000, "area": 800, "region": "الباحة", "lat": 20.1167, "lng": 41.5167, "aliases": ["Bani Hassan"]},
    "غامد الزناد": {"pop": 22000, "area": 700, "region": "الباحة", "lat": 19.9667, "lng": 41.5667, "aliases": ["Ghamid Az-Zinad"]},
}

# المتوسطات على مستوى المنطقة الإدارية (13 منطقة) - استرجاع احتياطي
SAUDI_REGIONS = {
    "الرياض": {"pop": 8591748, "area": 380000, "lat": 24.7, "lng": 46.7},
    "مكة": {"pop": 8557766, "area": 153128, "lat": 21.4, "lng": 39.8},
    "الشرقية": {"pop": 5125254, "area": 540000, "lat": 26.4, "lng": 50.0},
    "المدينة": {"pop": 2137983, "area": 150000, "lat": 24.5, "lng": 39.5},
    "عسير": {"pop": 2211875, "area": 76693, "lat": 18.2, "lng": 42.5},
    "جازان": {"pop": 1404997, "area": 13457, "lat": 16.9, "lng": 42.5},
    "القصيم": {"pop": 1336179, "area": 58046, "lat": 26.3, "lng": 43.9},
    "تبوك": {"pop": 886036, "area": 117000, "lat": 28.4, "lng": 36.6},
    "حائل": {"pop": 711018, "area": 103887, "lat": 27.5, "lng": 41.7},
    "نجران": {"pop": 592300, "area": 149511, "lat": 17.5, "lng": 44.1},
    "الجوف": {"pop": 595822, "area": 100212, "lat": 29.8, "lng": 40.2},
    "الباحة": {"pop": 487045, "area": 9921, "lat": 20.0, "lng": 41.5},
    "الحدود الشمالية": {"pop": 388858, "area": 111797, "lat": 30.9, "lng": 41.0},
}


def find_governorate_by_coords(lat, lng):
    """
    يبحث عن أقرب محافظة من الإحداثيات.
    يرجع dict فيه (name, data, distance_km, confidence)
    confidence:
      - 'high' لو ضمن نطاق <30 كم من مركز المحافظة
      - 'medium' لو 30-80 كم
      - 'low' لو 80-200 كم
      - None لو لا توجد محافظة قريبة
    """
    if not lat or not lng:
        return None
    best = None
    best_dist = float('inf')
    for name, data in SAUDI_GOVERNORATES.items():
        # حساب المسافة (haversine)
        R = 6371
        dlat = math.radians(data['lat'] - lat)
        dlng = math.radians(data['lng'] - lng)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(data['lat'])) * math.sin(dlng/2)**2
        dist = R * 2 * math.asin(math.sqrt(a))
        if dist < best_dist:
            best_dist = dist
            best = (name, data)
    if not best:
        return None
    confidence = None
    if best_dist <= 30:
        confidence = 'high'
    elif best_dist <= 80:
        confidence = 'medium'
    elif best_dist <= 200:
        confidence = 'low'
    if not confidence:
        return None
    return {
        'name': best[0],
        'data': best[1],
        'distance_km': round(best_dist, 1),
        'confidence': confidence,
    }
# ============================================================================
# [الدفعة 2] CSS - التصميم الكامل
# ============================================================================
st.markdown("""<style>
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
    div[data-testid="stTextArea"] textarea {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 12px !important;}
    div[data-testid="stSelectbox"] > div > div {background: #131826 !important; border: 1px solid #1f2937 !important; border-radius: 14px !important; min-height: 56px !important; color: white !important;}
    div[data-testid="stSelectbox"] svg {fill: white !important;}
    div[data-testid="stNumberInput"] input {background: #131826 !important; color: white !important; border: 1px solid #1f2937 !important; border-radius: 12px !important;}
    div[data-testid="stRadio"] label {color: #cbd5e1 !important;}
    
    .stButton button {background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important; color: white !important; border: none !important; padding: 14px 24px !important; border-radius: 14px !important; font-weight: 700 !important; font-size: 15px !important; width: 100% !important; height: 56px !important; box-shadow: 0 4px 16px rgba(239,68,68,0.3) !important;}
    .stButton button:hover {transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;}

    /* تحذير الصدق الرئيسي */
    .honesty-warning {
        background: linear-gradient(135deg, rgba(245,158,11,0.12) 0%, rgba(245,158,11,0.05) 100%);
        border: 2px solid rgba(245,158,11,0.4);
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .honesty-warning-icon {font-size: 24px;}
    .honesty-warning-text {color: #fbbf24; font-size: 13px; line-height: 1.6; flex: 1;}
    .honesty-warning-text b {color: #fde68a;}

    /* القرار النهائي */
    .verdict-card {
        background: linear-gradient(135deg, #1a2238 0%, #131826 100%);
        border-radius: 22px;
        padding: 28px;
        margin: 16px 0 24px 0;
        border: 2px solid;
        position: relative;
        overflow: hidden;
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
    .kpi-title {color: #94a3b8; font-size: 13px; font-weight: 500;}
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

    /* بطاقة المحافظة */
    .governorate-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.10) 0%, #131826 100%);
        border: 1px solid rgba(59,130,246,0.3);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .gov-name {color: #93c5fd; font-size: 13px; font-weight: 600; margin-bottom: 4px;}
    .gov-stats {display: flex; gap: 20px; flex-wrap: wrap; margin-top: 8px;}
    .gov-stat-item {color: #cbd5e1; font-size: 13px;}
    .gov-stat-item b {color: white; font-size: 16px;}

    /* قسم البيانات الميدانية */
    .field-section {
        background: linear-gradient(135deg, rgba(168,85,247,0.08) 0%, #131826 100%);
        border: 1px solid rgba(168,85,247,0.3);
        border-radius: 18px;
        padding: 20px;
        margin: 16px 0;
    }
    .field-section-title {color: #c4b5fd; font-size: 18px; font-weight: 700; margin-bottom: 8px;}
    .field-section-sub {color: #94a3b8; font-size: 13px; margin-bottom: 16px; line-height: 1.6;}

    /* مؤشر اكتمال الدراسة */
    .completion-bar {
        background: #131826; border: 1px solid #1f2937; border-radius: 16px;
        padding: 18px; margin-bottom: 16px;
    }
    .completion-title {color: white; font-size: 15px; font-weight: 700; margin-bottom: 12px;}
    .completion-fill {
        height: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; overflow: hidden;
    }
    .completion-fill-inner {
        height: 100%; border-radius: 6px;
        background: linear-gradient(90deg, #ef4444 0%, #f59e0b 50%, #10b981 100%);
    }

    /* قسم "ما يحتاج تحقق" */
    .needs-verification {
        background: rgba(245,158,11,0.06);
        border: 1px dashed rgba(245,158,11,0.4);
        border-radius: 12px;
        padding: 14px 16px;
        margin: 12px 0;
    }
    .needs-verification-title {color: #fbbf24; font-size: 14px; font-weight: 700; margin-bottom: 8px;}
    .needs-verification ul {margin: 0; padding-right: 18px; color: #cbd5e1; font-size: 13px; line-height: 1.7;}

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


# ============================================================================
# [الدفعة 2] حالة الجلسة (Session State)
# ============================================================================
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
if 'field_inputs' not in st.session_state:
    st.session_state.field_inputs = {}
if 'custom_activity' not in st.session_state:
    st.session_state.custom_activity = ""
# ============================================================================
# [الدفعة 3] محرك Mapbox والدوال الأساسية
# ============================================================================
def extract_coords(url):
    """يستخرج إحداثيات من رابط Google Maps أو نص"""
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
    for p in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)',
              r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)', r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)']:
        m = re.search(p, url)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def dist_km(lat1, lng1, lat2, lng2):
    """حساب المسافة بين نقطتين بالكيلومتر"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# ════════════════════════════════════════════════════════════════
# 🔧 إصلاح: الفئات التي يدعمها Mapbox Search Box (canonical category IDs)
# الفئات خارج هذه المجموعة لا يدعمها Mapbox → نجلبها من OSM فقط
# (كان الكود يضرب Mapbox لكل 67 فئة = طلبات ضائعة + نتائج 0 وهمية)
# ════════════════════════════════════════════════════════════════
MAPBOX_SUPPORTED = {
    'restaurant', 'cafe', 'fast_food', 'shopping', 'clothing_store',
    'electronics_store', 'home_garden', 'sporting_goods', 'fuel', 'pharmacy',
    'grocery', 'services', 'auto_repair', 'car_wash', 'car_dealer',
    'car_rental', 'ev_charging_station', 'parking', 'hospital', 'clinic',
    'beauty_salon', 'park', 'fitness_center', 'cinema', 'museum',
    'tourist_attraction', 'nightclub', 'library', 'atm', 'bank',
    'hotel', 'school', 'mosque',
}


def search_mapbox(lat, lng, cat, limit=25, proximity_offset=None):
    """البحث عن محلات في فئة معينة عبر Mapbox Search Box API"""
    plat, plng = lat, lng
    if proximity_offset:
        plat += proximity_offset[0]
        plng += proximity_offset[1]
    url = f"https://api.mapbox.com/search/searchbox/v1/category/{cat}"
    params = {"access_token": MAPBOX, "proximity": f"{plng},{plat}", "limit": limit, "language": "ar"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get('features', [])
    except Exception:
        pass
    return []


def _dedup_features(features, threshold_m=50):
    """إزالة المكررات بناءً على القرب والاسم"""
    unique = []
    seen_coords = []
    seen_names = set()
    for f in features:
        props = f.get('properties', {})
        name = (props.get('name') or '').strip().lower()
        coords = props.get('coordinates', {})
        plat = coords.get('latitude')
        plng = coords.get('longitude')
        if not (plat and plng and name):
            continue
        # ✅ Dedup by name (normalized)
        if name in seen_names:
            continue
        # ✅ Dedup by proximity (~50m)
        is_dup = False
        for slat, slng in seen_coords:
            # تقريباً 1 درجة = 111 كم، 0.0005 درجة ≈ 55 متر
            if abs(plat - slat) < 0.0005 and abs(plng - slng) < 0.0005:
                is_dup = True
                break
        if is_dup:
            continue
        seen_names.add(name)
        seen_coords.append((plat, plng))
        unique.append(f)
    return unique


def search_mapbox_multi(lat, lng, cat, radius_km):
    """
    🔴 إصلاح Mapbox 25-cap:
    بحث متعدد بنقاط بدلاً من نقطة واحدة + توسيع المصطلحات
    يجلب 60-100+ نتيجة بدلاً من 25 لكل فئة
    """
    all_features = []
    
    # 1. النقطة الأصلية
    all_features.extend(search_mapbox(lat, lng, cat, 25))
    
    # 2. لو النطاق كبير (>= 1.5 كم) نضيف بحث من 4 نقاط حول الموقع
    if radius_km >= 1.5:
        # تقريباً: 0.01 درجة ≈ 1.1 كم
        offset = (radius_km * 0.45) / 111.0  # 45% من الشعاع
        offsets = [
            (offset, 0),       # شمال
            (-offset, 0),      # جنوب
            (0, offset),       # شرق
            (0, -offset),      # غرب
        ]
        for off in offsets:
            all_features.extend(search_mapbox(lat, lng, cat, 25, proximity_offset=off))
    
    # 3. dedup
    return _dedup_features(all_features)


def process(features, tlat, tlng, max_km):
    """يفلتر النتائج حسب النطاق ويرجع قائمة مرتبة (مع dedup)"""
    places = []
    seen = set()
    seen_coords = []
    for f in features:
        props = f.get('properties', {})
        name = props.get('name', '')
        if not name:
            continue
        name_norm = name.strip().lower()
        if name_norm in seen:
            continue
        coords = props.get('coordinates', {})
        plat = coords.get('latitude')
        plng = coords.get('longitude')
        if plat and plng:
            # dedup بـ proximity (50m)
            is_dup = False
            for slat, slng in seen_coords:
                if abs(plat - slat) < 0.0005 and abs(plng - slng) < 0.0005:
                    is_dup = True
                    break
            if is_dup:
                continue
            d = dist_km(tlat, tlng, plat, plng)
            if d <= max_km:
                places.append({'name': name, 'addr': props.get('full_address', ''),
                               'dist': d, 'lat': plat, 'lng': plng})
                seen.add(name_norm)
                seen_coords.append((plat, plng))
    places.sort(key=lambda x: x['dist'])
    return places


# ════════════════════════════════════════════════════════════════
# 🔴 score_to_level: تحويل النسب المئوية لمستويات مفهومة
# ════════════════════════════════════════════════════════════════
def score_to_level(score, reverse=False):
    """
    تحول نسبة 0-100 إلى مستوى مفهوم بأيقونة ولون
    reverse=True للمعادلات المعكوسة (تشبع، منافسة - الأعلى = أسوأ)
    """
    score = int(score) if score is not None else 0
    if reverse:
        # تشبع/منافسة - العكس: عالي = سيء
        if score >= 85:
            return {'level': 'ضعيف', 'icon': '🔴', 'color': '#ef4444', 'meaning': 'مشبع - تجنّب'}
        elif score >= 60:
            return {'level': 'متوسط', 'icon': '🟡', 'color': '#f59e0b', 'meaning': 'منافسة عالية'}
        elif score >= 30:
            return {'level': 'جيد', 'icon': '💎', 'color': '#3b82f6', 'meaning': 'منافسة معقولة'}
        else:
            return {'level': 'ممتاز', 'icon': '⭐', 'color': '#10b981', 'meaning': 'سوق مفتوح'}
    else:
        # فرصة/طلب/انسجام - الأعلى = أفضل
        if score >= 75:
            return {'level': 'ممتاز جداً', 'icon': '⭐', 'color': '#10b981', 'meaning': 'فرصة قوية'}
        elif score >= 55:
            return {'level': 'جيد', 'icon': '💎', 'color': '#3b82f6', 'meaning': 'فرصة معقولة'}
        elif score >= 35:
            return {'level': 'متوسط', 'icon': '🟡', 'color': '#f59e0b', 'meaning': 'يحتاج دراسة'}
        else:
            return {'level': 'ضعيف', 'icon': '🔴', 'color': '#ef4444', 'meaning': 'مخاطرة عالية'}


# ════════════════════════════════════════════════════════════════
# 🗺️ OpenStreetMap (Overpass API) Integration
# ════════════════════════════════════════════════════════════════

# تحويل فئات Mapbox → OSM tags
MAPBOX_TO_OSM = {
    'restaurant': [('amenity', 'restaurant')],
    'cafe': [('amenity', 'cafe')],
    'fast_food': [('amenity', 'fast_food')],
    'grocery': [('shop', 'supermarket'), ('shop', 'convenience'), ('shop', 'grocery')],
    'pharmacy': [('amenity', 'pharmacy')],
    'clinic': [('amenity', 'clinic'), ('healthcare', 'clinic')],
    'hospital': [('amenity', 'hospital')],
    'school': [('amenity', 'school'), ('amenity', 'kindergarten')],
    'mosque': [('amenity', 'place_of_worship'), ('religion', 'muslim')],
    'fuel': [('amenity', 'fuel')],
    'bank': [('amenity', 'bank')],
    'atm': [('amenity', 'atm')],
    'hotel': [('tourism', 'hotel'), ('tourism', 'guest_house')],
    'tourist_attraction': [('tourism', 'attraction'), ('tourism', 'museum')],
    'museum': [('tourism', 'museum')],
    'park': [('leisure', 'park'), ('leisure', 'garden')],
    'fitness_center': [('leisure', 'fitness_centre'), ('leisure', 'sports_centre')],
    'shopping': [('shop', 'mall'), ('shop', 'department_store')],
    'clothing_store': [('shop', 'clothes')],
    'electronics_store': [('shop', 'electronics')],
    'auto_repair': [('shop', 'car_repair'), ('amenity', 'car_repair')],
    'car_wash': [('amenity', 'car_wash')],
    'car_rental': [('amenity', 'car_rental')],
    'beauty_salon': [('shop', 'beauty'), ('shop', 'hairdresser')],
    'cinema': [('amenity', 'cinema')],
    'library': [('amenity', 'library')],
    'parking': [('amenity', 'parking')],
    'services': [],  # عام جداً
    # 🆕 الفئات الجديدة - معظمها مدعومة فقط في OSM
    # منزل - صيانة
    'plumber': [('craft', 'plumber'), ('shop', 'plumbing')],
    'electrician': [('craft', 'electrician'), ('shop', 'electrical')],
    'carpenter': [('craft', 'carpenter')],
    'metalworker': [('craft', 'metal_construction'), ('craft', 'blacksmith'), ('craft', 'welder')],
    'ac_repair': [('craft', 'hvac')],
    'painter': [('craft', 'painter')],
    # منزل - أثاث
    'furniture': [('shop', 'furniture')],
    'lighting': [('shop', 'lighting')],
    'curtains': [('shop', 'curtain'), ('shop', 'interior_decoration')],
    # منزل - خدمات
    'gas_supply': [('shop', 'gas')],
    'locksmith': [('shop', 'locksmith'), ('craft', 'locksmith')],
    'cleaning': [('office', 'cleaning'), ('shop', 'cleaning')],
    'pest_control': [('shop', 'pest_control')],
    # سيارات
    'tyre_shop': [('shop', 'tyres')],
    'upholstery': [('craft', 'upholsterer'), ('shop', 'upholstery')],
    'car_tinting': [('shop', 'car_repair'), ('service', 'tinting')],
    'auto_parts': [('shop', 'car_parts')],
    'oil_change': [('shop', 'car_repair'), ('service', 'oil_change')],
    # جوال
    'mobile_repair': [('shop', 'mobile_phone'), ('craft', 'electronics_repair')],
    'mobile_accessories': [('shop', 'mobile_phone')],
    # ملابس
    'tailor': [('shop', 'tailor'), ('craft', 'tailor'), ('craft', 'dressmaker')],
    'abaya_shop': [('shop', 'clothes')],  # لا توجد فئة محددة
    'shoe_shop': [('shop', 'shoes')],
    # طعام متخصص
    'bakery': [('shop', 'bakery'), ('shop', 'pastry')],
    'sweets': [('shop', 'confectionery'), ('shop', 'sweets')],
    'butcher': [('shop', 'butcher')],
    'vegetables': [('shop', 'greengrocer'), ('shop', 'farm')],
    # عناية شخصية
    'barber': [('shop', 'hairdresser'), ('craft', 'hairdresser')],
    # تعليم
    'quran_school': [('amenity', 'school')],  # تحفيظ - يصعب التمييز
    'training_center': [('amenity', 'training'), ('office', 'educational_institution')],
    # صحة
    'dentist': [('amenity', 'dentist'), ('healthcare', 'dentist')],
    'medical_lab': [('healthcare', 'laboratory')],
    # ترفيه
    'playground': [('leisure', 'playground'), ('leisure', 'pitch')],
    'game_center': [('leisure', 'amusement_arcade'), ('leisure', 'adult_gaming_centre')],
    # 🔧 إصلاح: فئات كانت بلا أي مصدر (كانت ترجع 0 دائماً)
    'home_garden': [('shop', 'doityourself'), ('shop', 'hardware'), ('shop', 'garden_centre'), ('shop', 'houseware')],
    'sporting_goods': [('shop', 'sports')],
    'car_dealer': [('shop', 'car')],
    'ev_charging_station': [('amenity', 'charging_station')],
    'nightclub': [('amenity', 'nightclub')],
}


def search_osm(lat, lng, radius_km, cats_to_search=None):
    """
    البحث في OpenStreetMap عبر Overpass API
    مجاني تماماً - بدون API key
    يجرب عدة mirrors لتجاوز IP restrictions
    يرجع dict {cat: [{name, lat, lng, dist, source: 'osm'}]}
    """
    cats_to_search = cats_to_search or list(MAPBOX_TO_OSM.keys())
    radius_m = int(radius_km * 1000)
    
    query_parts = []
    for cat in cats_to_search:
        tags = MAPBOX_TO_OSM.get(cat, [])
        for tag_key, tag_val in tags:
            query_parts.append(f'  node["{tag_key}"="{tag_val}"](around:{radius_m},{lat},{lng});')
            query_parts.append(f'  way["{tag_key}"="{tag_val}"](around:{radius_m},{lat},{lng});')
    
    if not query_parts:
        return {}
    
    query = f"""[out:json][timeout:25];
(
{chr(10).join(query_parts)}
);
out center body;"""
    
    # 🔴 نجرب عدة mirrors لـ Overpass (بعضها يحظر بعض الـ IPs)
    mirrors = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass.openstreetmap.ru/api/interpreter',
        'https://overpass.private.coffee/api/interpreter',
    ]
    headers = {'User-Agent': 'GBI-Investment-Analyzer/1.0'}
    
    data = None
    for mirror in mirrors:
        try:
            r = requests.post(mirror, data={'data': query}, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                break
        except Exception:
            continue
    
    if not data:
        return {}
    
    elements = data.get('elements', [])
    
    # نوزع النتائج على الفئات
    results = {cat: [] for cat in cats_to_search}
    
    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name:ar') or tags.get('name:en') or tags.get('name', '')
        if not name:
            continue
        
        # نحدد الإحداثيات (node = lat/lon مباشر، way = center)
        if el.get('type') == 'node':
            plat = el.get('lat')
            plng = el.get('lon')
        elif el.get('type') == 'way':
            center = el.get('center', {})
            plat = center.get('lat')
            plng = center.get('lon')
        else:
            continue
        
        if not (plat and plng):
            continue
        
        # نحدد إلى أي فئة ينتمي
        matched_cat = None
        for cat in cats_to_search:
            for tag_key, tag_val in MAPBOX_TO_OSM.get(cat, []):
                if tags.get(tag_key) == tag_val:
                    matched_cat = cat
                    break
            if matched_cat:
                break
        
        if not matched_cat:
            continue
        
        d = dist_km(lat, lng, plat, plng)
        if d <= radius_km:
            # 🆕 تقييمات من OSM (مجانية ودائمة): وسوم stars / rating
            osm_rating = None
            raw_rating = tags.get('stars') or tags.get('rating')
            if raw_rating:
                try:
                    val = float(str(raw_rating).split('/')[0].replace(',', '.'))
                    # توحيد على مقياس 0-5 (بعض الوسوم 0-10)
                    if val > 5:
                        val = val / 2
                    osm_rating = round(min(5.0, max(0.0, val)), 1)
                except (ValueError, TypeError):
                    osm_rating = None
            osm_reviews = None
            rev = tags.get('reviews') or tags.get('review_count')
            if rev and str(rev).isdigit():
                osm_reviews = int(rev)

            results[matched_cat].append({
                'name': name,
                'addr': tags.get('addr:full', ''),
                'dist': d,
                'lat': plat,
                'lng': plng,
                'source': 'osm',
                'rating': osm_rating,
                'reviews': osm_reviews,
                'rating_source': 'osm' if osm_rating else None,
            })
    
    # ترتيب
    for cat in results:
        results[cat].sort(key=lambda x: x['dist'])
    
    return results


# ════════════════════════════════════════════════════════════════
# 🛣️ تحليل نوع الشارع (رئيسي / ثانوي / فرعي)
# يعتمد على وسم highway في OpenStreetMap (مجاني ودقيق)
# نوع الشارع يرفع أو يخفض فرصة الموقع بشكل جوهري:
#   - شارع رئيسي = حركة مرور عالية + ظهور = فرصة أعلى (لكن إيجار أعلى)
#   - شارع فرعي = حركة محدودة = فرصة أقل للأنشطة المعتمدة على المارّة
# ════════════════════════════════════════════════════════════════
STREET_HIERARCHY = {
    # tag value : (الفئة, وزن الأهمية, التأثير على الفرصة %)
    'motorway':     ('رئيسي', 6, 10),   # طريق سريع: ظهور عالٍ من طريق الخدمة الموازي
    'trunk':        ('رئيسي', 5, 13),
    'primary':      ('رئيسي', 5, 15),
    'secondary':    ('ثانوي', 3, 8),
    'tertiary':     ('ثانوي', 2, 4),
    'unclassified': ('فرعي', 1, 0),
    'residential':  ('فرعي', 1, -5),
    'living_street':('فرعي', 1, -8),
    'service':      ('فرعي', 0, -3),    # طريق خدمة: غالباً موازٍ لرئيسي، ليس سلبياً جداً
}


def analyze_street_type(lat, lng, search_radius_m=120):
    """
    يحدد نوع الشارع الذي يقع عليه الموقع عبر أقرب طريق مُصنّف في OSM.
    يرجع dict:
      - category: 'رئيسي' / 'ثانوي' / 'فرعي' / 'غير معروف'
      - name: اسم الشارع إن وُجد
      - highway: قيمة الوسم الخام
      - opportunity_modifier: تعديل على نقاط الفرصة (+/- %)
      - nearby: قائمة بأنواع الشوارع القريبة (لتقييم التقاطعات)
      - confidence: مدى الثقة في التحديد
      - explanation: شرح نصي للأثر
    """
    radius = int(search_radius_m)
    # نبحث عن كل الطرق المصنّفة قرب النقطة
    hw_values = '|'.join(STREET_HIERARCHY.keys())
    query = f"""[out:json][timeout:25];
(
  way["highway"~"^({hw_values})$"](around:{radius},{lat},{lng});
);
out tags geom;"""

    mirrors = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass.private.coffee/api/interpreter',
    ]
    headers = {'User-Agent': 'GBI-Investment-Analyzer/1.0'}
    data = None
    for mirror in mirrors:
        try:
            r = requests.post(mirror, data={'data': query}, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                break
        except Exception:
            continue

    if not data or not data.get('elements'):
        return {
            'category': 'غير معروف', 'name': '', 'highway': '',
            'opportunity_modifier': 0, 'nearby': [], 'confidence': 'منخفضة',
            'explanation': 'تعذّر تحديد نوع الشارع آلياً — يُنصح بالتحقق ميدانياً.',
        }

    def _min_dist_to_way(el):
        geom = el.get('geometry', [])
        best = 9e9
        for pt in geom:
            d = dist_km(lat, lng, pt['lat'], pt['lon']) * 1000  # متر
            if d < best:
                best = d
        return best

    candidates = []
    for el in data['elements']:
        tags = el.get('tags', {})
        hw = tags.get('highway')
        if hw not in STREET_HIERARCHY:
            continue
        cat, weight, modifier = STREET_HIERARCHY[hw]
        d = _min_dist_to_way(el)
        name = tags.get('name:ar') or tags.get('name') or ''
        candidates.append({
            'highway': hw, 'category': cat, 'weight': weight,
            'modifier': modifier, 'dist_m': round(d, 1), 'name': name,
        })

    if not candidates:
        return {
            'category': 'غير معروف', 'name': '', 'highway': '',
            'opportunity_modifier': 0, 'nearby': [], 'confidence': 'منخفضة',
            'explanation': 'لا توجد طرق مُصنّفة قرب الموقع في OSM — تحقق ميدانياً.',
        }

    # الشارع الأساسي = الأقرب الذي له أعلى وزن ضمن نطاق قريب جداً (<=40م)
    # نفضّل الأعلى أهمية ضمن أقرب الطرق
    near = [c for c in candidates if c['dist_m'] <= 40] or candidates
    near.sort(key=lambda c: (-c['weight'], c['dist_m']))
    primary_street = near[0]

    # كشف التقاطع: إن وُجد شارعان مختلفان كلاهما قريب (<=35م)
    distinct_near = {}
    for c in candidates:
        if c['dist_m'] <= 35:
            key = c['category']
            if key not in distinct_near or c['dist_m'] < distinct_near[key]['dist_m']:
                distinct_near[key] = c
    is_corner = len(distinct_near) >= 2

    modifier = primary_street['modifier']
    explanation_parts = []
    cat = primary_street['category']

    if cat == 'رئيسي':
        explanation_parts.append('الموقع على شارع رئيسي: حركة مرور وظهور عاليان يرفعان الفرصة، خاصة للمطاعم والمقاهي والتجزئة.')
    elif cat == 'ثانوي':
        explanation_parts.append('الموقع على شارع ثانوي: حركة معتدلة تناسب معظم الأنشطة بإيجار أقل من الرئيسي.')
    elif cat == 'فرعي':
        explanation_parts.append('الموقع على شارع فرعي/سكني: حركة المارّة محدودة، يناسب أنشطة الخدمة المحلية والاحتياج اليومي أكثر من الأنشطة المعتمدة على المرور.')

    # بونص التقاطع
    if is_corner:
        corner_bonus = 5
        modifier += corner_bonus
        explanation_parts.append(f'الموقع قرب تقاطع ({" + ".join(distinct_near.keys())}) — ميزة إضافية للظهور (+{corner_bonus}%).')

    nearby_summary = sorted(
        [{'category': v['category'], 'highway': v['highway'], 'dist_m': v['dist_m'], 'name': v['name']}
         for v in distinct_near.values()],
        key=lambda x: x['dist_m']
    )

    confidence = 'عالية' if primary_street['dist_m'] <= 30 else ('متوسطة' if primary_street['dist_m'] <= 80 else 'منخفضة')

    return {
        'category': cat,
        'name': primary_street['name'],
        'highway': primary_street['highway'],
        'dist_m': primary_street['dist_m'],
        'opportunity_modifier': int(max(-15, min(20, modifier))),
        'is_corner': is_corner,
        'nearby': nearby_summary,
        'confidence': confidence,
        'explanation': ' '.join(explanation_parts),
    }
# ════════════════════════════════════════════════════════════════

# تحويل فئات Mapbox → Foursquare category IDs
MAPBOX_TO_FOURSQUARE = {
    'restaurant': '13065',
    'cafe': '13035',
    'fast_food': '13145',
    'grocery': '17069',
    'pharmacy': '17091',
    'clinic': '15014',
    'hospital': '15014',
    'school': '12058',
    'fuel': '19007',
    'bank': '11045',
    'atm': '11044',
    'hotel': '19014',
    'tourist_attraction': '16041',
    'museum': '10027',
    'park': '16032',
    'fitness_center': '18021',
    'shopping': '17114',
    'clothing_store': '17029',
    'beauty_salon': '11062',
    'cinema': '10024',
    'library': '12080',
}


def search_foursquare(lat, lng, radius_km, api_key, cats_to_search=None):
    """
    البحث في Foursquare Places API.
    🔧 إصلاح: نقاط V3 (api.foursquare.com/v3) تُوقَف في 15 مايو 2026.
       ننتقل إلى endpoint الجديد (places-api.foursquare.com) المبني على FSQ OS Places،
       مع V3 القديم كاحتياطي مؤقت لمن لا يزال مفتاحه يعمل عليه.
    يضيف rating ⭐ + عدد المراجعات للمحلات.
    """
    if not api_key:
        return {}

    cats_to_search = cats_to_search or list(MAPBOX_TO_FOURSQUARE.keys())
    radius_m = int(radius_km * 1000)

    # الترتيب: الجديد أولاً ثم V3 كاحتياطي
    endpoints = [
        {
            'url': 'https://places-api.foursquare.com/places/search',
            'headers': {
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/json',
                'X-Places-Api-Version': '2025-06-17',
            },
        },
        {
            'url': 'https://api.foursquare.com/v3/places/search',
            'headers': {
                'Authorization': api_key,
                'Accept': 'application/json',
            },
        },
    ]

    results = {cat: [] for cat in cats_to_search}

    for cat in cats_to_search:
        fsq_cat = MAPBOX_TO_FOURSQUARE.get(cat)
        if not fsq_cat:
            continue

        data = None
        for ep in endpoints:
            try:
                r = requests.get(
                    ep['url'],
                    params={
                        'll': f'{lat},{lng}',
                        'radius': radius_m,
                        'fsq_category_ids': fsq_cat,
                        'categories': fsq_cat,  # اسم البارامتر القديم في V3
                        'limit': 50,
                        'fields': 'name,geocodes,location,rating,stats,fsq_place_id,fsq_id',
                    },
                    headers=ep['headers'],
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    break
            except Exception:
                continue
        if not data:
            continue

        for place in data.get('results', []):
            name = place.get('name', '')
            if not name:
                continue
            loc = place.get('geocodes', {}).get('main', {})
            plat = loc.get('latitude')
            plng = loc.get('longitude')
            if not (plat and plng):
                continue

            d = dist_km(lat, lng, plat, plng)
            if d > radius_km:
                continue

            # Foursquare rating (مقياس 0-10 → نحول لـ 0-5)
            fsq_rating = place.get('rating')
            rating_5 = round(fsq_rating / 2, 1) if fsq_rating else None
            reviews = (place.get('stats') or {}).get('total_ratings')

            results[cat].append({
                'name': name,
                'addr': place.get('location', {}).get('formatted_address', ''),
                'dist': d,
                'lat': plat,
                'lng': plng,
                'source': 'foursquare',
                'rating': rating_5,
                'reviews': reviews,
                'rating_source': 'foursquare' if rating_5 else None,
                'fsq_id': place.get('fsq_place_id') or place.get('fsq_id'),
            })
    
    return results


# ════════════════════════════════════════════════════════════════
# 🔄 دمج النتائج من مصادر متعددة
# ════════════════════════════════════════════════════════════════
def merge_sources(*results_dicts):
    """
    يدمج نتائج من عدة مصادر مع dedup ذكي
    Dedup بـ: (الاسم المُطبع + قرب الإحداثيات 50m)
    """
    merged = {}
    all_cats = set()
    for d in results_dicts:
        all_cats.update(d.keys())
    
    for cat in all_cats:
        combined = []
        seen_names = set()
        seen_coords = []  # [(lat, lng, place_dict)]
        
        for d in results_dicts:
            for place in d.get(cat, []):
                name_norm = (place.get('name') or '').strip().lower()
                if not name_norm:
                    continue
                
                # Dedup بالاسم
                if name_norm in seen_names:
                    # نجد المحل الموجود ونعزز بياناته
                    for sp in combined:
                        if (sp.get('name') or '').strip().lower() == name_norm:
                            # ندمج المصادر
                            existing_sources = sp.get('sources', [sp.get('source', 'unknown')])
                            new_source = place.get('source', 'unknown')
                            if new_source not in existing_sources:
                                existing_sources.append(new_source)
                            sp['sources'] = existing_sources
                            # نحدث rating لو موجود في الجديد ومش في القديم
                            if place.get('rating') and not sp.get('rating'):
                                sp['rating'] = place['rating']
                                sp['rating_source'] = new_source
                            break
                    continue
                
                # Dedup بالإحداثيات (50m)
                plat = place.get('lat')
                plng = place.get('lng')
                is_dup = False
                if plat and plng:
                    for slat, slng, sp in seen_coords:
                        if abs(plat - slat) < 0.0005 and abs(plng - slng) < 0.0005:
                            # نعزز بدلاً من إضافة
                            existing_sources = sp.get('sources', [sp.get('source', 'unknown')])
                            new_source = place.get('source', 'unknown')
                            if new_source not in existing_sources:
                                existing_sources.append(new_source)
                            sp['sources'] = existing_sources
                            if place.get('rating') and not sp.get('rating'):
                                sp['rating'] = place['rating']
                                sp['rating_source'] = new_source
                            is_dup = True
                            break
                if is_dup:
                    continue
                
                # محل جديد
                place_copy = dict(place)
                place_copy['sources'] = [place.get('source', 'unknown')]
                combined.append(place_copy)
                seen_names.add(name_norm)
                if plat and plng:
                    seen_coords.append((plat, plng, place_copy))
        
        combined.sort(key=lambda x: x.get('dist', 999))
        if combined:
            merged[cat] = combined
    
    return merged


def category_ratings_summary(places):
    """
    🆕 يلخّص تقييمات المحلات داخل فئة واحدة.
    يرجع: متوسط التقييم، عدد المُقيَّمة، إجمالي المراجعات، نسبة التغطية.
    يُستخدم لإضافة بُعد "جودة المنافسين" للتحليل بدلاً من العدد فقط.
    """
    rated = [p for p in places if p.get('rating') is not None]
    total = len(places)
    if not rated:
        return {
            'avg_rating': None, 'rated_count': 0, 'total_count': total,
            'total_reviews': 0, 'coverage': 0.0, 'has_data': False,
        }
    avg = sum(p['rating'] for p in rated) / len(rated)
    total_reviews = sum((p.get('reviews') or 0) for p in rated)
    return {
        'avg_rating': round(avg, 1),
        'rated_count': len(rated),
        'total_count': total,
        'total_reviews': total_reviews,
        'coverage': round(len(rated) / total, 2) if total else 0.0,
        'has_data': True,
    }


def all_ratings_summary(pbc):
    """يطبّق category_ratings_summary على كل الفئات في نتيجة المسح."""
    return {cat: category_ratings_summary(places) for cat, places in pbc.items()}


def comprehensive_scan(lat, lng, radius_km, sources=None, progress_callback=None):
    """
    🔴 فحص شامل محسّن:
    - بحث متعدد بـ proximity points
    - دمج من مصادر متعددة (Mapbox + OSM + Foursquare)
    - dedup صارم
    - كشف اقتطاع API
    
    sources: dict {mapbox: True, osm: bool, foursquare: bool, foursquare_key: str, ...}
    progress_callback: function(stage, percent) لإظهار التقدم
    """
    sources = sources or {'mapbox': True}

    # 🟦 Mapbox (الأساسي) - فقط للفئات التي يدعمها فعلياً
    # 🔧 إصلاح: كان يضرب Mapbox لكل 67 فئة، منها 34 لا يدعمها = طلبات ضائعة
    if progress_callback:
        progress_callback("🌐 جاري المسح من Mapbox...", 30)

    mapbox_results = {}
    truncation_flags = {}
    for cat in CATEGORIES:
        if cat not in MAPBOX_SUPPORTED:
            continue  # سيُجلب من OSM بدلاً من ذلك
        feats = search_mapbox_multi(lat, lng, cat, radius_km)
        places = process(feats, lat, lng, radius_km)
        if places:
            for p in places:
                p['source'] = 'mapbox'
            mapbox_results[cat] = places
            if len(places) >= 100:
                truncation_flags[cat] = True

    # 🗺️ OpenStreetMap
    # 🔧 إصلاح: OSM مجاني وبدون مفتاح، وهو المصدر الوحيد لـ34 فئة جديدة
    #   (بنشري، تنجيد، لحام، نجارة، تبديل غاز، نسخ مفاتيح...).
    #   لذلك نفعّله افتراضياً ما لم يُعطّله المستخدم صراحةً (osm=False).
    osm_results = {}
    if sources.get('osm', True):
        if progress_callback:
            progress_callback("🗺️ جاري المسح من OpenStreetMap...", 50)
        try:
            osm_results = search_osm(lat, lng, radius_km)
        except Exception:
            osm_results = {}
    
    # 🟨 Foursquare (إضافي + تقييمات)
    fsq_results = {}
    if sources.get('foursquare') and sources.get('foursquare_key'):
        if progress_callback:
            progress_callback("🟨 جاري المسح من Foursquare...", 65)
        try:
            fsq_results = search_foursquare(lat, lng, radius_km, sources['foursquare_key'])
        except Exception:
            fsq_results = {}
    
    # 🔄 الدمج
    if progress_callback:
        progress_callback("🔄 جاري دمج النتائج...", 80)
    
    if osm_results or fsq_results:
        results = merge_sources(mapbox_results, osm_results, fsq_results)
        # إعادة حساب الاقتطاع بعد الدمج
        truncation_flags = {}
        for cat, places in results.items():
            # نعتبر الفئة مقصوصة فقط لو معظم النتائج من Mapbox (لم يضف OSM/FSQ شي)
            mapbox_count = sum(1 for p in places if 'mapbox' in p.get('sources', []))
            if mapbox_count >= 100 and len(places) >= 100:
                truncation_flags[cat] = True
    else:
        results = mapbox_results
    
    # ملخص المصادر
    ratings = all_ratings_summary(results)
    rated_total = sum(s['rated_count'] for s in ratings.values())
    source_stats = {
        'mapbox_total': sum(len(v) for v in mapbox_results.values()),
        'osm_total': sum(len(v) for v in osm_results.values()) if osm_results else 0,
        'foursquare_total': sum(len(v) for v in fsq_results.values()) if fsq_results else 0,
        'sources_used': [k for k in ['mapbox', 'osm', 'foursquare']
                         if k == 'mapbox' or (k == 'osm' and sources.get('osm', True)) or sources.get(k)],
        'ratings': ratings,            # 🆕 ملخص تقييمات لكل فئة
        'rated_places_total': rated_total,  # 🆕 إجمالي المحلات المقيَّمة
    }

    return results, truncation_flags, source_stats


# ============================================================================
# [الدفعة 3] DNA الحي (تركيبة محتملة - مع تحذير)
# ============================================================================
def neighborhood_dna(pbc):
    """مؤشر تركيبة الحي (تقديري - مبني على نوع المحلات)"""
    food = sum(len(pbc.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])
    shopping = len(pbc.get('shopping', [])) + len(pbc.get('clothing_store', [])) + len(pbc.get('electronics_store', []))
    grocery = len(pbc.get('grocery', []))
    pharmacy = len(pbc.get('pharmacy', []))
    services = len(pbc.get('services', [])) + len(pbc.get('auto_repair', []))
    fuel = len(pbc.get('fuel', []))
    cafe = len(pbc.get('cafe', []))
    fast_food = len(pbc.get('fast_food', []))
    restaurant = len(pbc.get('restaurant', []))
    fitness = len(pbc.get('fitness_center', []))
    beauty = len(pbc.get('beauty_salon', []))
    total = sum(len(v) for v in pbc.values())

    if total == 0:
        return {'family': 0, 'youth': 0, 'commercial': 0, 'food': 0, 'service': 0, 'main': 'غير محدد'}

    # نسب موزونة
    family_raw = (grocery * 2.5 + pharmacy * 3.0 + restaurant * 1.5) / max(total, 1) * 35
    youth_raw = (cafe * 2.5 + fast_food * 2.5 + shopping * 1.5 + fitness * 2.0 + beauty * 1.5) / max(total, 1) * 35
    commercial_raw = (shopping * 3.0 + services * 2.0) / max(total, 1) * 35 + min(35, total * 1.0)
    food_raw = (food / max(total, 1)) * 100
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


# ============================================================================
# [الدفعة 3] مؤشر الثقة - واقعي ومنخفض السقف
# ============================================================================
def confidence_score(pbc, total_places, radius_km, has_field_data=False, has_gov_data=False):
    """
    مؤشر ثقة واقعي للتحليل.
    السقف الواقعي بدون بيانات إضافية: 55%
    مع بيانات ميدانية: يرتفع إلى 70%
    مع بيانات محافظة + ميدانية: 80% كحد أقصى
    
    لا توجد ثقة 100% بدون:
    - بيانات تقييمات المنافسين (Google Maps)
    - حركة عملاء فعلية (Foot traffic)
    - بيانات إيجارات السوق
    - استبيان ميداني
    """
    factors = {}
    
    # عدد المحلات (الأكثر = بيانات أوفر) - أقصى 15 نقطة
    if total_places >= 50:
        factors['محلات'] = 15
    elif total_places >= 20:
        factors['محلات'] = 12
    elif total_places >= 10:
        factors['محلات'] = 8
    else:
        factors['محلات'] = 4
    
    # تنوع الفئات - أقصى 10 نقاط
    active = len(pbc)
    if active >= 8:
        factors['تنوع'] = 10
    elif active >= 5:
        factors['تنوع'] = 7
    elif active >= 3:
        factors['تنوع'] = 5
    else:
        factors['تنوع'] = 2
    
    # حجم النطاق المناسب - أقصى 8 نقاط
    if 1 <= radius_km <= 3:
        factors['نطاق'] = 8
    elif radius_km <= 5:
        factors['نطاق'] = 5
    else:
        factors['نطاق'] = 3
    
    # بيانات سكان حقيقية (محافظة) - أقصى 12 نقطة
    factors['سكان'] = 12 if has_gov_data else 0
    
    # بيانات ميدانية - أقصى 25 نقطة
    factors['ميدانية'] = 25 if has_field_data else 0
    
    score = sum(factors.values())
    # سقف نهائي 70% (لا نتعدى لأن البيانات الميدانية + السكان ليست بديل عن:
    #   - تقييمات المنافسين الفعلية، حركة فعلية، إيجارات حقيقية)
    score = min(score, 70)
    
    if score >= 55:
        level = "جيدة"
        color = "#10b981"
    elif score >= 35:
        level = "متوسطة"
        color = "#f59e0b"
    elif score >= 20:
        level = "محدودة"
        color = "#f97316"
    else:
        level = "ضعيفة"
        color = "#ef4444"
    
    return {
        'score': score,
        'level': level,
        'color': color,
        'factors': factors,
        'has_field_data': has_field_data,
        'has_gov_data': has_gov_data,
    }


# ============================================================================
# [الدفعة 3] ترتيب الأنشطة (مع تحذير منطقي صادق)
# ============================================================================
def rank_all_activities(pbc, dna, traffic_score, pop_score, acc_score, field_data=None, local_population=None, truncation_flags=None):
    """
    صنّف الأنشطة من الأفضل للأسوأ.
    
    ⚠️ تحذير منطقي:
    - "لا يوجد نشاط X" ≠ "يوجد طلب على X"
    - قد يكون الغياب بسبب عدم وجود طلب أصلاً
    - النتائج اقتراحات مبدئية فقط
    """
    candidates = {
        'cafe': {'demand_map': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'طعام': 60, 'خدماتي': 60, 'غير محدد': 70}, 'cap': 8},
        'restaurant': {'demand_map': {'عائلي': 95, 'شبابي': 80, 'تجاري': 80, 'طعام': 55, 'خدماتي': 65, 'غير محدد': 80}, 'cap': 10},
        'fast_food': {'demand_map': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'طعام': 60, 'خدماتي': 65, 'غير محدد': 75}, 'cap': 8},
        'pharmacy': {'demand_map': {'عائلي': 95, 'شبابي': 70, 'تجاري': 70, 'طعام': 50, 'خدماتي': 90, 'غير محدد': 80}, 'cap': 3},
        'grocery': {'demand_map': {'عائلي': 95, 'شبابي': 75, 'تجاري': 65, 'طعام': 55, 'خدماتي': 80, 'غير محدد': 80}, 'cap': 5},
        'shopping': {'demand_map': {'عائلي': 75, 'شبابي': 90, 'تجاري': 85, 'طعام': 50, 'خدماتي': 65, 'غير محدد': 75}, 'cap': 8},
        'clothing_store': {'demand_map': {'عائلي': 80, 'شبابي': 90, 'تجاري': 80, 'طعام': 40, 'خدماتي': 60, 'غير محدد': 75}, 'cap': 6},
        'electronics_store': {'demand_map': {'عائلي': 70, 'شبابي': 90, 'تجاري': 85, 'طعام': 40, 'خدماتي': 65, 'غير محدد': 70}, 'cap': 4},
        'home_garden': {'demand_map': {'عائلي': 85, 'شبابي': 50, 'تجاري': 70, 'طعام': 40, 'خدماتي': 65, 'غير محدد': 65}, 'cap': 4},
        'sporting_goods': {'demand_map': {'عائلي': 65, 'شبابي': 85, 'تجاري': 60, 'طعام': 35, 'خدماتي': 55, 'غير محدد': 60}, 'cap': 3},
        'auto_repair': {'demand_map': {'عائلي': 75, 'شبابي': 65, 'تجاري': 75, 'طعام': 40, 'خدماتي': 90, 'غير محدد': 70}, 'cap': 5},
        'car_wash': {'demand_map': {'عائلي': 75, 'شبابي': 80, 'تجاري': 80, 'طعام': 45, 'خدماتي': 85, 'غير محدد': 75}, 'cap': 4},
        'car_dealer': {'demand_map': {'عائلي': 60, 'شبابي': 70, 'تجاري': 75, 'طعام': 35, 'خدماتي': 70, 'غير محدد': 60}, 'cap': 3},
        'car_rental': {'demand_map': {'عائلي': 55, 'شبابي': 75, 'تجاري': 85, 'طعام': 50, 'خدماتي': 75, 'غير محدد': 65}, 'cap': 3},
        'ev_charging_station': {'demand_map': {'عائلي': 60, 'شبابي': 75, 'تجاري': 80, 'طعام': 50, 'خدماتي': 75, 'غير محدد': 65}, 'cap': 3},
        'clinic': {'demand_map': {'عائلي': 90, 'شبابي': 70, 'تجاري': 75, 'طعام': 50, 'خدماتي': 85, 'غير محدد': 75}, 'cap': 5},
        'beauty_salon': {'demand_map': {'عائلي': 90, 'شبابي': 95, 'تجاري': 70, 'طعام': 45, 'خدماتي': 75, 'غير محدد': 80}, 'cap': 6},
        'fitness_center': {'demand_map': {'عائلي': 75, 'شبابي': 95, 'تجاري': 75, 'طعام': 50, 'خدماتي': 65, 'غير محدد': 75}, 'cap': 4},
        'hotel': {'demand_map': {'عائلي': 40, 'شبابي': 65, 'تجاري': 85, 'طعام': 55, 'خدماتي': 70, 'غير محدد': 55}, 'cap': 4},
        'services': {'demand_map': {'عائلي': 70, 'شبابي': 60, 'تجاري': 80, 'طعام': 50, 'خدماتي': 90, 'غير محدد': 70}, 'cap': 6},
    }

    main_culture = dna['main']
    results = []
    
    # هل لدينا بيانات ميدانية؟ نستخدمها لتعديل الطلب
    field_demand_boost = 0
    if field_data:
        foot_traffic = field_data.get('foot_traffic_level', '')  # ضعيف/متوسط/قوي
        if foot_traffic == 'قوي':
            field_demand_boost = 10
        elif foot_traffic == 'متوسط':
            field_demand_boost = 5
        elif foot_traffic == 'ضعيف':
            field_demand_boost = -10
    
    for cat, info in candidates.items():
        existing = len(pbc.get(cat, []))
        demand = info['demand_map'].get(main_culture, 65)
        # تعديل بناءً على البيانات الميدانية
        demand = max(0, min(100, demand + field_demand_boost))
        cap = info['cap']
        saturation = min(100, int((existing / cap) * 100)) if cap > 0 else 100
        opportunity = max(0, int(demand - saturation * 0.65))

        # 🔴 إصلاح فجوة البيانات: "0 منافس" في منطقة كثيفة ليس فرصة
        total_in_area = sum(len(v) for v in pbc.values())
        data_gap_zero = False
        if existing == 0 and total_in_area >= 60:
            common_cats = {'cafe', 'restaurant', 'fast_food', 'grocery', 'pharmacy',
                           'beauty_salon', 'clothing_store', 'shopping', 'services',
                           'auto_repair', 'bank', 'atm', 'clinic'}
            if cat in common_cats:
                data_gap_zero = True
                opportunity = min(opportunity, 45)

        # تعديل بناءً على عوامل أخرى
        if traffic_score >= 70 and cat in ('cafe', 'restaurant', 'fast_food'):
            opportunity = min(100, opportunity + 8)
        if pop_score >= 65 and cat in ('grocery', 'pharmacy', 'clinic'):
            opportunity = min(100, opportunity + 10)
        if acc_score < 50:
            opportunity = max(0, opportunity - 10)

        # توليد "لماذا" مع تحذيرات صادقة
        reasons = []
        if existing == 0:
            if data_gap_zero:
                reasons.append("⚠️ غير مسجّل رغم كثافة المنطقة — غالباً فجوة بيانات لا فرصة، تحقق ميدانياً")
            else:
                reasons.append("غير مسجّل في API - قد يكون فرصة أو نقص تسجيل، يحتاج تحقق ميداني")
        elif existing <= 2:
            reasons.append(f"منافسة محدودة ({existing} منافس)")
        elif existing > cap:
            reasons.append(f"السوق مشبع ({existing} منافس)")

        if main_culture in info['demand_map'] and info['demand_map'][main_culture] >= 80:
            reasons.append(f"تركيبة المحلات ({main_culture}) قد تدعم هذا النشاط")
        elif info['demand_map'].get(main_culture, 65) < 60:
            reasons.append(f"تركيبة المحلات ({main_culture}) قد لا تدعمه بقوة")

        if traffic_score >= 70 and cat in ('cafe', 'restaurant', 'fast_food'):
            reasons.append("حركة مرور عالية تجذب العملاء")
        if pop_score >= 65 and cat in ('grocery', 'pharmacy', 'clinic'):
            reasons.append("كثافة سكانية تخلق طلب يومي")

        results.append({
            'cat_key': cat,
            'cat_name': CATEGORIES[cat]['name'],
            'icon': CATEGORIES[cat]['icon'],
            'demand': demand,
            'existing': existing,
            'saturation': saturation,
            'opportunity_score': opportunity,
            'data_gap_zero': data_gap_zero,
            'reasons': reasons[:3] if reasons else ["تحليل قياسي"],
        })

    # ════════════════════════════════════════════════════════════
    # 🧪 دمج كيمياء العائلة + 🚫 فيتو الإشباع الذكي
    # المنطق الجديد:
    #   1. الفرصة النهائية = (الأصلية × 40%) + (الانسجام × 60%)
    #   2. فيتو الإشباع: نحسب "منافسين/1000 نسمة" بناءً على السكان المحليين
    #      - <15 منافس/1000 → منافسة صحية (لا خصم)
    #      - 15-30 → منافسة عالية (خصم 15 نقطة)
    #      - 30-50 → خطر شديد (خصم 30 نقطة + تحذير)
    #      - >50 → كارثة (خصم 50 نقطة + تحويل للقائمة الحمراء)
    # ════════════════════════════════════════════════════════════
    
    # 🔴 إصلاح: فيتو التشبع العام
    # نحسب نسبة الفئات المشبعة (cp_per_1k > 3.5) من إجمالي الفئات المهمة
    # إذا 5+ فئات مشبعة = السوق العام مكتظ → خصم عام من كل النتائج
    # 🔴 معامل تصحيح للبيانات المقصوصة:
    # عندما الفئة تصل لـ 24-25 محل، الرقم الحقيقي قد يكون 2-5× أكبر
    # نضرب العدد بمعامل 2.5 للفئات المقصوصة (تقدير محافظ)
    # 🔴 إضافة مهمة: في الأسواق المكتظة، اقتطاع البيانات نفسه = إشارة للتشبع
    truncation_flags = truncation_flags or {}
    trunc_count = sum(1 for f in truncation_flags.values() if f)
    
    global_saturation_penalty = 0
    heavily_saturated_cats = 0
    if local_population and local_population > 0:
        total_meaningful_cats = 0
        for cat_key, places in pbc.items():
            count = len(places)
            # 🔴 إذا الفئة مقصوصة، نضرب العدد بـ 2.5 للحساب التقريبي
            effective_count = int(count * 2.5) if truncation_flags.get(cat_key) else count
            if effective_count >= 5:
                total_meaningful_cats += 1
                cp1k = (effective_count * 1000) / local_population
                if cp1k > 3.5:
                    heavily_saturated_cats += 1
    
    # 🔴 منطق جديد: اعتبار اقتطاع البيانات في الحساب
    # كل فئة مقصوصة = إشارة قوية على وجود منافسة فعلية كثيفة (Mapbox يقص فقط عند الاكتظاظ الفعلي)
    # 8+ فئات مقصوصة = منطقة كثيفة المنافسة → خصم كبير حتى لو cp1k منخفض
    truncation_penalty_addon = 0
    if trunc_count >= 15:
        truncation_penalty_addon = 25  # كارثة بيانات
    elif trunc_count >= 10:
        truncation_penalty_addon = 18
    elif trunc_count >= 7:
        truncation_penalty_addon = 12
    elif trunc_count >= 5:
        truncation_penalty_addon = 7
    
    # عتبات الخصم العام
    if heavily_saturated_cats >= 15:
        global_saturation_penalty = 40
    elif heavily_saturated_cats >= 10:
        global_saturation_penalty = 30
    elif heavily_saturated_cats >= 7:
        global_saturation_penalty = 20
    elif heavily_saturated_cats >= 5:
        global_saturation_penalty = 12
    elif heavily_saturated_cats >= 3:
        global_saturation_penalty = 6
    
    # نأخذ المجموع الأكبر بين الـ saturation_penalty و truncation_penalty
    global_saturation_penalty = max(global_saturation_penalty, truncation_penalty_addon)
    
    for r in results:
        chem = family_chemistry_analysis(r['cat_key'], pbc)
        if chem:
            r['harmony_score'] = chem['harmony_score']
            r['harmony_level'] = chem['harmony_level']
            r['harmony_color'] = chem['harmony_color']
            r['synergies'] = chem['synergies']
            r['aligned_with_dominant'] = chem['aligned_with_dominant']
            r['dominant_family'] = chem['dominant_family']

            original_opp = r['opportunity_score']
            harmony = chem['harmony_score']

            # المعادلة الأساسية: 40% فرصة + 60% انسجام
            final_opp = int((original_opp * 0.4) + (harmony * 0.6))

            # 🔴 سقف فجوة البيانات: "0 منافس" في منطقة كثيفة لا يُمنح فرصة عالية
            if r.get('data_gap_zero'):
                final_opp = min(final_opp, 50)

            # خصم لعدم وجود ترابطات
            if len(chem['synergies']) == 0:
                final_opp = max(0, final_opp - 15)
            # بونص للترابطات المتعددة
            if len(chem['synergies']) >= 3:
                final_opp = min(100, final_opp + 5)
            # بونص العائلة الغالبة
            if chem.get('aligned_with_dominant'):
                final_opp = min(100, final_opp + 3)
            
            # 🔴 تطبيق فيتو التشبع العام
            # حتى للأنشطة المفقودة (existing=0)، لو السوق العام مشبع → خصم
            # (التحذير العام يظهر كبانر واحد في الأعلى - ليس في كل نشاط)
            if global_saturation_penalty > 0:
                final_opp = max(0, final_opp - global_saturation_penalty)

            # ════════════════════════════════════════════════════
            # 🚫 فيتو الإشباع الذكي - الإصلاح الأهم
            # العتبات معايرة على الواقع السعودي:
            # - متوسط منطقة صحية: مقهى لكل 800-1500 شخص (≈0.7-1.2/1000)
            # - عتبة الإشباع: 3+ منافسين/1000 = منافسة شديدة
            # ════════════════════════════════════════════════════
            existing_count = r['existing']
            saturation_veto = None
            competitors_per_1k = None

            tflags = truncation_flags or {}
            is_truncated = tflags.get(r['cat_key'], False)
            effective_competitors = int(existing_count * 2.5) if is_truncated else existing_count

            if local_population and local_population > 0 and existing_count > 0:
                competitors_per_1k = (effective_competitors * 1000) / local_population
                _disp = f"{existing_count}+ (مقدّر {effective_competitors})" if is_truncated else f"{existing_count}"
                if competitors_per_1k > 7:
                    saturation_veto = "كارثة"
                    final_opp = min(final_opp, 20)
                    r['reasons'].insert(0, f"🚫 كارثة سوقية: {_disp} منافس لـ {local_population:,} نسمة ({competitors_per_1k:.1f}/1000) - السوق مدمّر")
                elif competitors_per_1k > 3.5:
                    saturation_veto = "خطر شديد"
                    final_opp = min(final_opp, 30)
                    r['reasons'].insert(0, f"⚠️ خطر شديد: {_disp} منافس لـ {local_population:,} نسمة ({competitors_per_1k:.1f}/1000) - تشبع مفرط")
                elif competitors_per_1k > 1.5:
                    saturation_veto = "منافسة عالية"
                    final_opp = min(final_opp, 45)
                    r['reasons'].insert(0, f"🟡 منافسة عالية: {competitors_per_1k:.1f} منافس/1000 نسمة - تحتاج تمايز قوي")
                elif competitors_per_1k > 0.7:
                    r['reasons'].insert(0, f"📊 منافسة طبيعية: {competitors_per_1k:.1f} منافس/1000 نسمة")
            elif r['saturation'] >= 100 and existing_count >= 10:
                saturation_veto = "إشباع مطلق"
                final_opp = max(0, final_opp - 25)
                r['reasons'].insert(0, f"⚠️ سوق مشبع: {existing_count} منافس - تحتاج تمايز قوي")

            r['saturation_veto'] = saturation_veto
            r['competitors_per_1k'] = competitors_per_1k
            r['final_opportunity'] = final_opp

            # إضافة سبب الانسجام (إذا لم يكن هناك فيتو)
            if not saturation_veto and chem['synergies']:
                top_syn = chem['synergies'][0]
                synergy_reason = f"🧪 ينسجم مع {top_syn['icon']} {top_syn['name']} ({top_syn['count']} محل) - {top_syn['reason']}"
                r['reasons'].insert(0, synergy_reason)
            elif not saturation_veto and harmony < 15:
                r['reasons'].insert(0, f"⚠️ غريب عن المحيط - لا توجد ترابطات قوية")
            elif not saturation_veto and len(chem['synergies']) == 0:
                r['reasons'].insert(0, f"⚠️ لا توجد ترابطات قوية - يحتاج جهد تسويقي")
            if r.get('data_gap_zero'):
                r['reasons'].insert(0, "⚠️ 0 منافس في منطقة كثيفة = غالباً فجوة بيانات لا فرصة — تحقق ميدانياً")
            r['reasons'] = r['reasons'][:4]  # نسمح بـ 4 أسباب الآن (للفيتو)
        else:
            r['harmony_score'] = 0
            r['harmony_level'] = "غير محدد"
            r['harmony_color'] = "#94a3b8"
            r['synergies'] = []
            r['aligned_with_dominant'] = False
            r['dominant_family'] = None
            r['final_opportunity'] = r['opportunity_score']
            r['saturation_veto'] = None
            r['competitors_per_1k'] = None

    # ترتيب بناءً على الفرصة النهائية (المدموجة مع الانسجام)
    results.sort(key=lambda x: -x['final_opportunity'])
    best = results[:3]
    extras = [r for r in results[3:] if r['final_opportunity'] >= 50]
    best.extend(extras[:2])
    best_keys = {b['cat_key'] for b in best}
    # القائمة الحمراء: نشاطات أقل من 40% أو لديها فيتو
    worst_candidates = [
        r for r in results 
        if r['cat_key'] not in best_keys 
        and (
            r['final_opportunity'] < 40 
            or r.get('saturation_veto') in ('كارثة', 'خطر شديد', 'منافسة عالية', 'إشباع مطلق')
        )
    ]
    # فرز: الأقل فرصة أولاً، ثم الأشد فيتو
    veto_order = {'كارثة': 0, 'خطر شديد': 1, 'منافسة عالية': 2, 'إشباع مطلق': 3, None: 4}
    worst_candidates.sort(key=lambda x: (x['final_opportunity'], veto_order.get(x.get('saturation_veto'), 4)))
    worst = worst_candidates[:7]  # أعلى 7 من الأسوأ
    return best, worst, results
# ============================================================================
# [الدفعة 4] التحليل الرئيسي - منطق صادق وبدون تخمين
# ============================================================================
# ════════════════════════════════════════════════════════════
# 🔴 تحليل SWOT حقيقي مبني على الأرقام
# ════════════════════════════════════════════════════════════
def build_swot_analysis(a, pbc, local_population, area_character, traffic_score, acc_score):
    """يبني تحليل SWOT حقيقي بأرقام محددة من البيانات الفعلية"""
    
    swot = {
        'strengths': [],
        'weaknesses': [],
        'opportunities': [],
        'threats': [],
    }
    
    target_cat = a.get('target_cat')
    
    # ═══ Strengths - نقاط القوة ═══
    if traffic_score >= 75:
        swot['strengths'].append(f"حركة مرور عالية (مؤشر {traffic_score}/100) - يدعم الأنشطة التجارية")
    if acc_score >= 70:
        swot['strengths'].append(f"سهولة وصول ممتازة ({acc_score}/100) - عملاء قادرون على الوصول")
    if a.get('best_activities') and len(a['best_activities']) > 0:
        top = a['best_activities'][0]
        synergies = top.get('synergies', [])
        if synergies:
            syn = synergies[0]
            swot['strengths'].append(f"ترابطات قوية: {syn['icon']} {syn['name']} ({syn['count']} محل) - يدعم نشاطك")
    if a.get('total_places', 0) >= 50:
        swot['strengths'].append(f"بنية تجارية ناضجة ({a['total_places']} محل) - الحركة موجودة")
    
    # ═══ Weaknesses - نقاط الضعف ═══
    opportunity = a.get('opportunity_score', 0)
    saturation = a.get('saturation_score', 0)
    
    # 🔴 حساب عدد الفئات المشبعة بشدة (مع معامل التصحيح للبيانات المقصوصة)
    trunc = a.get('truncation_flags', {})
    trunc_count = sum(1 for f in trunc.values() if f)
    
    heavy_sat_count = 0
    if local_population and local_population > 0:
        for cat_key, places in pbc.items():
            count = len(places)
            # نضرب بـ 2.5 للفئات المقصوصة (تقدير الواقع)
            effective_count = int(count * 2.5) if trunc.get(cat_key) else count
            if effective_count >= 5:
                cp1k = (effective_count * 1000) / local_population
                if cp1k > 3.5:
                    heavy_sat_count += 1
    
    # 🔴 نضع weaknesses قدر الإمكان (الأولوية للأرقام الحقيقية)
    
    # 1) Truncation - هذا الأهم في الأسواق المكتظة
    if trunc_count >= 10:
        swot['weaknesses'].append(f"🚫 اقتطاع بيانات شديد في {trunc_count} فئة - السوق الفعلي أكثف بكثير مما يظهر")
    elif trunc_count >= 5:
        swot['weaknesses'].append(f"📊 اقتطاع بيانات في {trunc_count} فئة - المنافسة الفعلية أعلى")
    elif trunc_count >= 3:
        swot['weaknesses'].append(f"⚠️ اقتطاع بيانات في {trunc_count} فئة - بعض الأرقام قد تكون أقل من الواقع")
    
    # 2) كثافة المحلات العامة - مؤشر على سوق مكتظ
    total_places = a.get('total_places', 0)
    if total_places >= 400:
        swot['weaknesses'].append(f"بنية تجارية كثيفة جداً ({total_places} محل) - منافسة عامة شرسة")
    elif total_places >= 200:
        swot['weaknesses'].append(f"بنية تجارية ناضجة ({total_places} محل) - يحتاج تمايز قوي")
    elif total_places < 20:
        swot['weaknesses'].append(f"بنية تجارية محدودة جداً ({total_places} محل) - سوق صغير")
    
    # 3) فئات مشبعة (محسوبة بمعامل التصحيح)
    if heavy_sat_count >= 5:
        swot['weaknesses'].append(f"⚠️ {heavy_sat_count} فئات مشبعة بشدة - منافسة عامة شرسة")
    elif heavy_sat_count >= 3:
        swot['weaknesses'].append(f"⚠️ {heavy_sat_count} فئات مشبعة - بعض القطاعات مكتظة")
    
    # 4) فرصة منخفضة (للنشاط المختار)
    if target_cat:
        if opportunity < 30:
            swot['weaknesses'].append(f"فرصة دخول منخفضة جداً ({opportunity}%) - الأسواق التقليدية مشبعة")
        elif opportunity < 50:
            swot['weaknesses'].append(f"فرصة دخول متوسطة ({opportunity}%) - يحتاج تمايز")
    
    # 5) تشبع عالٍ (للنشاط المختار)
    if target_cat and saturation >= 85:
        swot['weaknesses'].append(f"تشبع سوقي للنشاط ({saturation}%) - منافسة شرسة")
    
    # 6) منافسة مباشرة للنشاط المختار
    if target_cat and target_cat in pbc:
        comp_count = len(pbc[target_cat])
        if comp_count >= 10 and local_population and local_population > 0:
            cp1k = (comp_count * 1000) / local_population
            if cp1k > 2:
                swot['weaknesses'].append(f"{comp_count} منافس مباشر بنسبة {cp1k:.1f}/1000 نسمة")
        elif comp_count >= 5:
            swot['weaknesses'].append(f"{comp_count} منافس مباشر للنشاط المستهدف")
        if comp_count == 0 and trunc_count >= 5:
            swot['weaknesses'].append(f"النشاط غير ظاهر في API لكن السوق العام مكتظ - يحتاج تحقق ميداني")
    
    # 7) حركة منخفضة
    if traffic_score < 50:
        swot['weaknesses'].append(f"حركة مرور محدودة ({traffic_score}/100) - يحتاج جذب نشط")
    
    # 8) منطقة ريفية/نائية
    if area_character in ('ريفي / أطراف', 'نائي / فارغ'):
        swot['weaknesses'].append(f"المنطقة '{area_character}' - بنية تجارية محدودة")
    
    # ═══ Opportunities - الفرص ═══
    ea = a.get('essential_analysis', {})
    
    # فرص الاحتياجات الضرورية المفقودة
    critical_missing = []
    if 'critical' in ea:
        for s in ea['critical']['services']:
            if s['status'] == 'missing':
                critical_missing.append(f"{s['icon']} {s['name']}")
    if critical_missing:
        swot['opportunities'].append(f"احتياجات ضرورية مفقودة: {' • '.join(critical_missing[:3])} - طلب مضمون")
    
    # فرص الكماليات المفقودة
    lifestyle_missing = []
    if 'lifestyle' in ea:
        for s in ea['lifestyle']['services']:
            if s['status'] == 'missing':
                lifestyle_missing.append(f"{s['icon']} {s['name']}")
    if lifestyle_missing and a.get('total_places', 0) >= 30:
        # فقط في المناطق العامرة، الكماليات المفقودة فرصة
        swot['opportunities'].append(f"كماليات مفقودة (فرص نمط حياة): {' • '.join(lifestyle_missing[:3])}")
    
    # فرص الانسجام
    if a.get('best_activities') and len(a['best_activities']) >= 2:
        top2 = a['best_activities'][:2]
        unique_acts = [f"{x['icon']} {x['cat_name']}" for x in top2]
        swot['opportunities'].append(f"أنشطة منسجمة مع المحيط: {' • '.join(unique_acts)}")
    
    if traffic_score >= 75 and saturation < 50:
        swot['opportunities'].append("حركة عالية + إشباع منخفض = ظرف مثالي للدخول")
    
    # ═══ Threats - التهديدات ═══
    total_places_t = a.get('total_places', 0)
    
    # 1) منافسين مباشرين للنشاط المستهدف
    if target_cat and target_cat in pbc:
        comp_count = len(pbc[target_cat])
        is_target_truncated = trunc.get(target_cat, False)
        if comp_count >= 15:
            top_competitors = pbc[target_cat][:2]
            comp_names = [c.get('name', '?') for c in top_competitors]
            suffix = "+" if is_target_truncated else ""
            swot['threats'].append(f"{comp_count}{suffix} منافس مباشر (مثل: {' • '.join(comp_names)})")
        elif comp_count >= 5:
            swot['threats'].append(f"{comp_count} منافس مباشر في النشاط المستهدف")
    
    # 2) Truncation - علامة قوية على سوق مكتظ فعلياً
    if trunc_count >= 10:
        swot['threats'].append(f"🚫 السوق فعلياً مكتظ - {trunc_count} فئة وصلت لحد API")
    elif trunc_count >= 5:
        swot['threats'].append(f"السوق أكثر اكتظاظاً من الظاهر - {trunc_count} فئة مقصوصة")
    
    # 3) قطاعات مشبعة بشدة (بأسماء)
    if heavy_sat_count >= 3:
        top_saturated_cats = []
        if local_population and local_population > 0:
            cat_cp1k = []
            for cat_key, places in pbc.items():
                count = len(places)
                effective_count = int(count * 2.5) if trunc.get(cat_key) else count
                if effective_count >= 5:
                    cp1k = (effective_count * 1000) / local_population
                    if cp1k > 3.5:
                        cat_info = CATEGORIES.get(cat_key, {})
                        cat_cp1k.append((cat_info.get('name', cat_key), cat_info.get('icon', ''), cp1k))
            cat_cp1k.sort(key=lambda x: -x[2])
            top_saturated_cats = [f"{x[1]} {x[0]}" for x in cat_cp1k[:3]]
        if top_saturated_cats:
            swot['threats'].append(f"قطاعات مشبعة بشدة: {' • '.join(top_saturated_cats)}")
    
    # 4) منطقة كثيفة المحلات
    if total_places_t >= 200 and (trunc_count >= 3 or heavy_sat_count >= 3):
        swot['threats'].append(f"بيئة شديدة المنافسة - {total_places_t}+ محل تتنافس على نفس العملاء")
    
    # 5) منطقة ريفية/نائية
    if area_character in ('ريفي / أطراف', 'نائي / فارغ'):
        swot['threats'].append(f"المنطقة '{area_character}' - حجم سوق محدود")
    
    # 6) منطقة تجارية مشبعة (نشاط محدد)
    if target_cat and a.get('total_places', 0) >= 100 and saturation >= 80:
        swot['threats'].append("منطقة تجارية ناضجة ومشبعة - حصة سوقية محدودة")
    
    # 7) عدم وجود بيانات سكان
    if not a.get('gov_info'):
        swot['threats'].append("غياب البيانات السكانية الرسمية - تقديرات قد تكون غير دقيقة")
    
    # 8) فجوة نسب: تشبع 100% مع فرصة <30%
    if target_cat and saturation >= 95 and opportunity < 30:
        swot['threats'].append(f"تناقض حاد: تشبع {saturation}% مع فرصة {opportunity}% - سوق مكتمل")
    
    # ضمان قوائم غير فارغة
    if not swot['strengths']:
        swot['strengths'].append("لا توجد نقاط قوة واضحة - تحقق ميداني مطلوب")
    if not swot['weaknesses']:
        swot['weaknesses'].append("لا توجد نقاط ضعف ظاهرة من البيانات")
    if not swot['opportunities']:
        swot['opportunities'].append("لا توجد فرص ظاهرة بدون نشاط محدد")
    if not swot['threats']:
        swot['threats'].append("لا توجد تهديدات ظاهرة")
    
    return swot


def analyze(pbc, radius_km, target_cat=None, gov_info=None, field_data=None):
    """
    التحليل الرئيسي للموقع.
    
    التغييرات الحرجة:
    - ✅ كشف تطابق الأرقام (Mapbox truncation عند 25)
    - ✅ ربط investment_score بالتشبع العام
    - ✅ منع توصيات "فرصة!" المضللة في الأسواق المكتظة
    - ✅ تحليل SWOT بدلاً من نص إنشائي
    """
    total = sum(len(v) for v in pbc.values())
    active = len(pbc)

    # ════════════════════════════════════════════════════════════
    # 🚨 إصلاح حرج: كشف بيانات Mapbox المقصوصة
    # Mapbox يرجع 25 محل كحد أقصى لكل فئة. لو كثير من الفئات على 25
    # يعني نحن في منطقة مكتظة والأرقام مكبوتة.
    # ════════════════════════════════════════════════════════════
    MAPBOX_LIMIT = 25
    # عدّ كم فئة وصلت لحد أو قريبة منه (≥23) من بين الفئات الكبيرة (≥10)
    categories_at_limit = sum(1 for places in pbc.values() if len(places) >= 23)
    categories_significant = sum(1 for places in pbc.values() if len(places) >= 10)
    data_is_truncated = False
    truncation_severity = None
    if categories_at_limit >= 5:
        data_is_truncated = True
        truncation_severity = "severe"  # 5+ فئات مقصوصة = منطقة مكتظة جداً
    elif categories_at_limit >= 3:
        data_is_truncated = True
        truncation_severity = "moderate"

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

    # المنافسة
    if target_cat:
        competitors = len(pbc.get(target_cat, []))
        if competitors == 0:
            comp_level, comp_score = "لا منافسة مباشرة", 100
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
        accessibility, acc_score = "تحتاج تحقق ميداني", 40

    # الحركة (مؤشر استدلالي)
    shopping_total = len(pbc.get('shopping', [])) + len(pbc.get('clothing_store', [])) + len(pbc.get('electronics_store', []))
    traffic_ind = food * 2 + shopping_total * 1.5 + len(pbc.get('services', []))
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

    # تعديل الحركة بناءً على البيانات الميدانية (لو موجودة)
    if field_data and field_data.get('foot_traffic_level'):
        ft = field_data['foot_traffic_level']
        if ft == 'قوي':
            traffic_score = min(100, traffic_score + 15)
            traffic_level = "عالية جداً (مؤكدة ميدانياً)"
        elif ft == 'متوسط':
            traffic_level = traffic_level + " (مؤكدة ميدانياً)"
        elif ft == 'ضعيف':
            traffic_score = max(10, traffic_score - 20)
            traffic_level = "ضعيفة (مؤكدة ميدانياً)"

    # ════════════════════════════════════════════════════════════
    # 🔴 إصلاح 1: تقدير السكان المحليين (Catchment Area Estimation)
    # المنطق:
    # - عدد المحلات يعكس نوع المنطقة (حضري/سكني/ريفي)
    # - نقدّر السكان بنسبة من سكان المحافظة + كثافة نوع المنطقة
    # - معايرة على واقع السعودية
    # ════════════════════════════════════════════════════════════
    area_km2_local = math.pi * (radius_km ** 2)

    # 🔴 الإصلاح الجذري: نستخدم total_places (العدد المطلق) كمؤشر أساسي
    # المشكلة السابقة: shop_density (محلات/كم²) في نطاق 10 كم يخفض بشكل مصطنع
    # المنطق الجديد: عدد المحلات الكلي يعكس نشاط المنطقة بغض النظر عن المساحة
    # ثم نتأكد بمؤشر shop_density للحالات الحدية
    shop_density = total / area_km2_local if area_km2_local > 0 else 0

    # نحدد نوع المنطقة بناءً على total_places أولاً، ثم shop_density ثانياً
    if total >= 500:
        # 500+ محل = مدينة كبيرة بدون شك
        area_character = "حضري مكتظ"
        expected_density_per_km2 = 8000
    elif total >= 200:
        # 200+ محل = حضري
        area_character = "حضري"
        expected_density_per_km2 = 4000
    elif total >= 80:
        # 80+ محل = سكني متوسط
        area_character = "سكني متوسط"
        expected_density_per_km2 = 1500
    elif total >= 30:
        # 30+ محل = سكني محدود
        area_character = "سكني محدود"
        expected_density_per_km2 = 400
    elif total >= 8:
        # 8-29 محل = ريفي
        area_character = "ريفي / أطراف"
        expected_density_per_km2 = 100
    else:
        # أقل من 8 محل = نائي
        area_character = "نائي / فارغ"
        expected_density_per_km2 = 20
    
    # 🔴 تعديل ذكي: للنطاقات الصغيرة جداً (< 2 كم) نسمح بكثافات أعلى
    # لأن النطاق الصغير في وسط مدينة قد يحوي كثافة عالية حتى مع محلات أقل
    if radius_km < 2 and shop_density >= 40 and total >= 100:
        area_character = "حضري مكتظ"
        expected_density_per_km2 = 8000

    # تقدير السكان: الكثافة المتوقعة × مساحة النطاق
    local_density = expected_density_per_km2
    local_population_estimate = int(local_density * area_km2_local)
    urban_multiplier = expected_density_per_km2  # للتوافق مع الكود القديم

    # 🔴 cap نسبي ذكي: السكان المحليون لا يتجاوزوا:
    # (أ) 60% من المحافظة (في النطاقات الكبيرة قد نغطي معظم المدينة)
    # (ب) الكثافة المتوسطة للمحافظة × مساحة النطاق × معامل حضري
    # المعامل: 5× للمناطق العادية، 25× للحضرية المكتظة (لأن المحافظات تشمل صحاري)
    if gov_info:
        gov_pop = gov_info['data']['pop']
        gov_area = gov_info['data']['area']
        gov_avg_density = gov_pop / gov_area if gov_area > 0 else 0
        
        # معامل التضخيم يعتمد على نوع المنطقة
        if area_character == "حضري مكتظ":
            urban_factor = 30  # مدن مكتظة بكثافة 30× أعلى من متوسط المحافظة
        elif area_character == "حضري":
            urban_factor = 15
        elif area_character == "سكني متوسط":
            urban_factor = 8
        else:
            urban_factor = 3
        
        # الحد الأقصى: max(60% من المحافظة, الكثافة المتوسطة × مساحة × معامل)
        max_by_share = int(gov_pop * 0.6)
        max_by_density = int(gov_avg_density * area_km2_local * urban_factor)
        max_reasonable = min(max_by_share, max(max_by_density, 5000))
        
        if local_population_estimate > max_reasonable:
            local_population_estimate = max_reasonable
            local_density = int(local_population_estimate / area_km2_local) if area_km2_local > 0 else 0

    # الكثافة السكانية - الآن تستخدم التقدير المحلي
    if local_density:
        if local_density >= 5000:
            pop_density, pop_score = "عالية جداً", 95
        elif local_density >= 1500:
            pop_density, pop_score = "عالية", 80
        elif local_density >= 500:
            pop_density, pop_score = "متوسطة", 60
        elif local_density >= 100:
            pop_density, pop_score = "منخفضة", 40
        else:
            pop_density, pop_score = "ريفية / فارغة", 20
    else:
        pop_density, pop_score = "غير معروفة", 50

    # المؤشرات الثلاث
    if target_cat:
        max_capacity = {'cafe': 8, 'restaurant': 10, 'fast_food': 8, 'pharmacy': 3, 'grocery': 5,
                        'shopping': 8, 'fuel': 4, 'services': 6}.get(target_cat, 6)
        saturation = min(100, int((competitors / max_capacity) * 100))
        demand = int((traffic_score * 0.4 + pop_score * 0.4 + acc_score * 0.2))
        opportunity = max(0, int(demand - saturation * 0.6))
    else:
        avg_per_cat = total / max(active, 1)
        saturation = min(100, int(avg_per_cat * 12))
        demand = int((traffic_score * 0.5 + pop_score * 0.5))
        opportunity = max(0, int(demand - saturation * 0.5))

    # نقاط الاستثمار
    if target_cat:
        score = int(opportunity * 0.40 + traffic_score * 0.20 + acc_score * 0.15 + pop_score * 0.15 + comp_score * 0.10)
    else:
        score = int(demand * 0.35 + traffic_score * 0.25 + acc_score * 0.20 + pop_score * 0.20)

    # ⚠️ إصلاح التناقض المنطقي: 
    # لو الإشباع >85% أو الفرصة <30%، ممنوع أن يكون القرار "افتح بثقة" أو "افتح بشروط"
    contradiction_block = False
    if target_cat:
        if saturation >= 85 or opportunity < 30:
            contradiction_block = True
            # نخفض النقاط لتعكس الواقع
            score = min(score, 55)

    # ════════════════════════════════════════════════════════════
    # 🚫 إصلاح إضافي: investment_score يتأثر بفيتو الإشباع العام
    # لو في 3+ أنشطة مشبعة بشدة (cp_per_1k>3.5)، نخفض النقاط
    # حتى لو ما حدد المستخدم نشاط معين
    # ════════════════════════════════════════════════════════════
    if local_population_estimate and local_population_estimate > 0:
        heavily_saturated_count = 0
        for cat_key, places in pbc.items():
            if len(places) >= 5:  # نتجاهل الفئات الصغيرة
                cp1k = (len(places) * 1000) / local_population_estimate
                if cp1k > 3.5:
                    heavily_saturated_count += 1
        
        # تخفيض نقاط الاستثمار بناءً على عدد الأنشطة المشبعة
        if heavily_saturated_count >= 5:
            score = min(score, 45)  # السوق مكتظ جداً
        elif heavily_saturated_count >= 3:
            score = min(score, 60)  # السوق مكتظ
        elif heavily_saturated_count >= 1 and target_cat:
            # لو في نشاط مشبع والمستخدم اختار شيئاً، نتأكد من المنطق
            target_competitors = len(pbc.get(target_cat, []))
            if target_competitors >= 5:
                target_cp1k = (target_competitors * 1000) / local_population_estimate
                if target_cp1k > 3.5:
                    score = min(score, 35)  # السوق مدمّر للنشاط المختار
                    contradiction_block = True

    # ════════════════════════════════════════════════════════════
    # 🚨 إصلاح إضافي: ربط النقاط بالتشبع العام والبيانات المقصوصة
    # ════════════════════════════════════════════════════════════
    # لو البيانات مقصوصة (مدينة مكتظة) - يعني السوق مشبع فعلياً
    if data_is_truncated:
        if truncation_severity == "severe":
            score = min(score, 50)  # 5+ فئات مقصوصة = منطقة مكتظة جداً
        elif truncation_severity == "moderate":
            score = min(score, 60)
    
    # لو الإشباع العام >= 90% (نشاط محدد)، نخصم بشدة
    if target_cat and saturation >= 90:
        score = min(score, 40)
        contradiction_block = True
    elif target_cat and saturation >= 80:
        score = min(score, 55)

    # القرار النهائي
    # ════════════════════════════════════════════════════════════
    # العتبات المعايرة (فجوات أوسع لتجنب القفز بين القرارات):
    # ⭐ ممتاز (75+) | 💎 جيد (60-74) | 🟡 متوسط (50-59) 
    # 🟠 ضعيف (35-49) | 🔴 غير مناسب (<35)
    # ════════════════════════════════════════════════════════════
    if target_cat:
        if score >= 75 and not contradiction_block:
            decision = "افتح بثقة"
            decision_emoji = "⭐"
            decision_color = "#10b981"
            decision_bg = "rgba(16,185,129,0.12)"
            decision_summary = "هذا الموقع يحقق معظم شروط النجاح لنشاطك. ابدأ مع التركيز على التميز."
        elif score >= 60 and not contradiction_block:
            decision = "افتح بشروط"
            decision_emoji = "💎"
            decision_color = "#22c55e"
            decision_bg = "rgba(34,197,94,0.10)"
            decision_summary = "موقع جيد لنشاطك لكن يحتاج تخطيط دقيق ودراسة ميدانية قبل البدء."
        elif score >= 50:
            decision = "فكّر مرتين"
            decision_emoji = "🟡"
            decision_color = "#f59e0b"
            decision_bg = "rgba(245,158,11,0.10)"
            if contradiction_block and saturation >= 85:
                decision_summary = f"السوق مشبع ({saturation}%) - النجاح يتطلب تميّزاً قوياً وعرض فريد."
            else:
                decision_summary = "الموقع متوسط لنشاطك - تأكد من ميزتك التنافسية قبل الاستثمار."
        elif score >= 35:
            decision = "غير منصوح به"
            decision_emoji = "🟠"
            decision_color = "#f97316"
            decision_bg = "rgba(249,115,22,0.10)"
            decision_summary = "مخاطر عالية لنشاطك هنا. ابحث عن موقع أفضل قبل الالتزام."
        else:
            decision = "تجنّبه"
            decision_emoji = "🔴"
            decision_color = "#ef4444"
            decision_bg = "rgba(239,68,68,0.10)"
            decision_summary = "البيانات لا تدعم نجاح نشاطك في هذا الموقع."
    else:
        # بدون نشاط محدد
        if score >= 75:
            decision = "موقع ممتاز"
            decision_emoji = "⭐"
            decision_color = "#10b981"
            decision_bg = "rgba(16,185,129,0.12)"
            decision_summary = "موقع استثماري ممتاز - الحركة عالية والوصول سهل. النشاط المناسب سيُحدّد أدناه."
        elif score >= 60:
            decision = "موقع جيد"
            decision_emoji = "💎"
            decision_color = "#22c55e"
            decision_bg = "rgba(34,197,94,0.10)"
            decision_summary = "إمكانات استثمارية جيدة - الموقع يستحق الدراسة. اختر نشاطاً من المقترحات أدناه."
        elif score >= 50:
            decision = "موقع متوسط"
            decision_emoji = "🟡"
            decision_color = "#f59e0b"
            decision_bg = "rgba(245,158,11,0.10)"
            decision_summary = "الموقع له إمكانات محدودة. لو قررت الاستثمار، اختر نشاطاً متخصصاً يميّزك."
        elif score >= 35:
            decision = "موقع ضعيف"
            decision_emoji = "🟠"
            decision_color = "#f97316"
            decision_bg = "rgba(249,115,22,0.10)"
            decision_summary = "البنية التجارية محدودة - يحتاج جهد تسويقي مرتفع لجذب العملاء."
        else:
            decision = "موقع غير مناسب"
            decision_emoji = "🔴"
            decision_color = "#ef4444"
            decision_bg = "rgba(239,68,68,0.10)"
            decision_summary = "النشاط التجاري في المنطقة ضعيف جداً - يُنصح بالبحث عن موقع آخر."

    # ════════════════════════════════════════════════════════════
    # 🔴 الخدمات الأساسية الذكية - 3 مستويات (احتياج/أساسي/كمالي)
    # ════════════════════════════════════════════════════════════
    ESSENTIAL_TIERS = {
        'critical': {
            'name': 'احتياجات ضرورية',
            'icon': '🚨',
            'description': 'يجب أن تتوفر في أي منطقة سكنية',
            'categories': [
                ('pharmacy', 'صيدلية', '💊'),
                ('clinic', 'عيادة', '⚕️'),
                ('hospital', 'مستشفى / مركز طبي', '🏥'),
                ('school', 'مدرسة', '🏫'),
            ]
        },
        'essential': {
            'name': 'أساسيات يومية',
            'icon': '📦',
            'description': 'احتياجات يستخدمها السكان يومياً',
            'categories': [
                ('grocery', 'بقالة / سوبرماركت', '🛒'),
                ('fuel', 'محطة وقود', '⛽'),
                ('restaurant', 'مطعم', '🍽️'),
                ('services', 'خدمات عامة', '🔧'),
                ('auto_repair', 'صيانة سيارات', '🔧'),
            ]
        },
        'lifestyle': {
            'name': 'كماليات نمط الحياة',
            'icon': '🎯',
            'description': 'فرص استثمارية تحسّن جودة الحياة',
            'categories': [
                ('cafe', 'مقهى', '☕'),
                ('fast_food', 'وجبات سريعة', '🍔'),
                ('beauty_salon', 'صالون تجميل', '💅'),
                ('fitness_center', 'نادي رياضي', '💪'),
                ('shopping', 'تسوق', '🛍️'),
                ('clothing_store', 'محل ملابس', '👕'),
                ('park', 'حديقة', '🌳'),
                ('cinema', 'سينما', '🎬'),
                ('car_wash', 'مغسلة سيارات', '🚿'),
                ('library', 'مكتبة', '📚'),
            ]
        }
    }

    def _classify_service(cat_key, places_in_cat):
        count = len(places_in_cat)
        if count == 0:
            # ════════════════════════════════════════════════════
            # 🚨 في المنطقة المكتظة (truncated data)، "0 محل" قد يعني:
            #   - فعلاً غير موجود (فرصة حقيقية) - نادر
            #   - أو غياب طلب (في حي مكتظ، عدم الوجود = إشارة سلبية)
            # القرار: في المنطقة المكتظة، نصنّف "missing" كـ "absent" (غياب طلب)
            # في المنطقة الهادئة، يبقى "missing" (فرصة محتملة)
            # ════════════════════════════════════════════════════
            if total >= 200:
                return 'likely_absent'  # غياب طلب وليس فرصة
            return 'missing'
        # 🔴 الفحص الصحيح: نستخدم cp_per_1k فقط (وليس truncation_flag)
        # السبب: البحث المتعدد يعطي 60-120 نتيجة فعلية، فالعدد المعروض قريب من الواقع
        if local_population_estimate and local_population_estimate > 0 and count >= 5:
            cp_1k = (count * 1000) / local_population_estimate
            if cp_1k > 3.5:
                return 'oversaturated'
            elif cp_1k > 1.5:
                return 'high_competition'
        return 'present'

    essential_analysis = {}
    for tier_key, tier_data in ESSENTIAL_TIERS.items():
        tier_result = {
            'name': tier_data['name'],
            'icon': tier_data['icon'],
            'description': tier_data['description'],
            'services': []
        }
        for cat_key, ar_name, icon in tier_data['categories']:
            places = pbc.get(cat_key, [])
            status = _classify_service(cat_key, places)
            cp_1k = 0
            if local_population_estimate and len(places) > 0:
                cp_1k = (len(places) * 1000) / local_population_estimate
            tier_result['services'].append({
                'cat_key': cat_key,
                'name': ar_name,
                'icon': icon,
                'count': len(places),
                'status': status,
                'cp_per_1k': cp_1k,
            })
        essential_analysis[tier_key] = tier_result

    # تحديد الفرص الأهم - فقط فعلاً مفقودة (ليس "غياب طلب")
    top_opportunities = []
    for tier_key in ['critical', 'essential', 'lifestyle']:
        for s in essential_analysis[tier_key]['services']:
            if s['status'] == 'missing':  # فقط الفرص الحقيقية
                top_opportunities.append({**s, 'tier': tier_key})

    # نسخة قديمة للتوافق مع PDF
    missing = []
    for key, label in {'pharmacy': "صيدلية", 'grocery': "بقالة/سوبرماركت", 'fuel': "محطة وقود"}.items():
        if len(pbc.get(key, [])) == 0:
            missing.append(label)

    # نقاط القوة والانتباه
    strengths, cautions = [], []
    
    # حساب أولي: كم نشاط مشبع بشدة في المحيط؟
    heavy_sat_in_area = 0
    if local_population_estimate and local_population_estimate > 0:
        for ck, places in pbc.items():
            if len(places) >= 5:
                cp = (len(places) * 1000) / local_population_estimate
                if cp > 3.5:
                    heavy_sat_in_area += 1
    
    if traffic_score >= 70: strengths.append("حركة مرور عالية (مؤشر استدلالي)")
    if acc_score >= 70: strengths.append("سهولة وصول ممتازة")
    if pop_score >= 65: strengths.append("كثافة سكانية جيدة")
    if comp_score >= 60 and target_cat: strengths.append("مستوى منافسة مقبول")
    
    # "تنوع تجاري" يكون قوة فقط إذا لم يكن السوق مشبعاً
    if active >= 5 and heavy_sat_in_area < 3: 
        strengths.append("تنوع تجاري في المنطقة")
    elif active >= 5 and heavy_sat_in_area >= 3:
        # ⚠️ تنوع لكن مشبع - ليس قوة!
        cautions.append(f"تنوع تجاري لكن مع {heavy_sat_in_area} فئات مشبعة - منافسة قاسية")
    
    if opportunity >= 60: strengths.append("فرصة سوقية مرتفعة")
    if field_data and field_data.get('site_visits') == 'متعدد': strengths.append("بيانات ميدانية مؤكدة")
    
    if comp_score < 40 and target_cat: cautions.append("منافسة مرتفعة في النشاط المستهدف")
    if traffic_score < 40: cautions.append("حركة منخفضة - يحتاج جذب نشط")
    if pop_score < 40: cautions.append("كثافة سكانية محدودة")
    if total < 5: cautions.append("بنية تجارية ضعيفة في المحيط")
    if saturation > 80: cautions.append(f"السوق مشبع بنسبة {saturation}% للنشاط المختار")
    if heavy_sat_in_area >= 5: 
        cautions.append(f"🚫 السوق مكتظ - {heavy_sat_in_area} فئات مشبعة (>3.5 منافس/1000)")
    elif heavy_sat_in_area >= 3:
        cautions.append(f"⚠️ {heavy_sat_in_area} فئات مشبعة في المنطقة - فكّر في التخصص")
    if not gov_info: cautions.append("لا توجد بيانات سكان رسمية للموقع")
    if not field_data: cautions.append("لا توجد بيانات ميدانية - مطلوبة لرفع الدقة")
    
    if not strengths: strengths.append("منطقة بكر تحتاج دراسة ميدانية")
    if not cautions: cautions.append("راقب الإيجارات في المنطقة")

    # أعلى المنافسين
    top_competitors = []
    if target_cat and target_cat in pbc:
        for p in pbc[target_cat][:5]:
            top_competitors.append({
                'name': p['name'], 'dist': round(p['dist'], 2),
                'rating': p.get('rating'), 'reviews': p.get('reviews'),
            })

    # قسم "ما يحتاج تحقق ميداني" - شفافية كاملة
    needs_verification = []
    if not gov_info:
        needs_verification.append("بيانات السكان الفعلية للموقع (المحافظة غير محددة)")
    if not field_data:
        needs_verification.append("الحركة الفعلية للمارّة والسيارات (يحتاج عدّ ميداني)")
        needs_verification.append("قوة المنافسين الحقيقية (تقييماتهم وعدد عملائهم)")
    needs_verification.append("أسعار الإيجارات الفعلية في الموقع")
    needs_verification.append("التركيبة العمرية والدخلية لسكان الحي")
    needs_verification.append("المشاريع التطويرية المستقبلية في المنطقة")
    
    # 🔴 بناء النتائج المرجعية للـ SWOT أولاً
    result_dict = {
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
        'pop_density': pop_density, 'pop_score': pop_score,
        'missing_services': missing,
        'essential_analysis': essential_analysis,
        'top_opportunities': top_opportunities,
        'top_competitors': top_competitors,
        'strengths': strengths, 'cautions': cautions,
        'target_cat': target_cat,
        'gov_info': gov_info,
        'local_population': local_population_estimate,
        'local_density': local_density,
        'area_character': area_character,
        'urban_multiplier': urban_multiplier,
        'data_is_truncated': data_is_truncated,
        'truncation_severity': truncation_severity,
        'categories_at_limit': categories_at_limit,
        'needs_verification': needs_verification,
        'contradiction_block': contradiction_block,
    }
    
    # 🔴 بناء SWOT حقيقي بعد كل الحسابات
    result_dict['swot'] = build_swot_analysis(
        result_dict, pbc, local_population_estimate, area_character, traffic_score, acc_score
    )
    
    return result_dict


# ============================================================================
# [الدفعة 4] التحليل المالي - مع تحذير صريح + benchmarks استقرائية
# ============================================================================

# ════════════════════════════════════════════════════════════
# 🔴 إصلاح 3: قاعدة Benchmarks المالية الاستقرائية
# معايرة على السوق السعودي (تقديرات معقولة - قابلة للتعديل)
# ════════════════════════════════════════════════════════════
ACTIVITY_BENCHMARKS = {
    # avg_ticket = متوسط الفاتورة | daily_customers = عملاء/يوم لحركة متوسطة
    # margin = هامش الربح الإجمالي | rent_factor = معامل الإيجار حسب الفئة
    'cafe': {'avg_ticket': 18, 'daily_customers': 60, 'margin': 0.55, 'name_ar': 'مقهى'},
    'restaurant': {'avg_ticket': 45, 'daily_customers': 50, 'margin': 0.35, 'name_ar': 'مطعم'},
    'fast_food': {'avg_ticket': 25, 'daily_customers': 80, 'margin': 0.45, 'name_ar': 'وجبات سريعة'},
    'grocery': {'avg_ticket': 35, 'daily_customers': 100, 'margin': 0.20, 'name_ar': 'بقالة'},
    'pharmacy': {'avg_ticket': 55, 'daily_customers': 50, 'margin': 0.30, 'name_ar': 'صيدلية'},
    'fuel': {'avg_ticket': 80, 'daily_customers': 150, 'margin': 0.08, 'name_ar': 'محطة وقود'},
    'shopping': {'avg_ticket': 120, 'daily_customers': 30, 'margin': 0.40, 'name_ar': 'محل تسوق'},
    'clothing_store': {'avg_ticket': 200, 'daily_customers': 20, 'margin': 0.50, 'name_ar': 'ملابس'},
    'electronics_store': {'avg_ticket': 450, 'daily_customers': 15, 'margin': 0.25, 'name_ar': 'إلكترونيات'},
    'auto_repair': {'avg_ticket': 250, 'daily_customers': 12, 'margin': 0.45, 'name_ar': 'صيانة سيارات'},
    'car_wash': {'avg_ticket': 30, 'daily_customers': 30, 'margin': 0.60, 'name_ar': 'مغسلة سيارات'},
    'beauty_salon': {'avg_ticket': 65, 'daily_customers': 18, 'margin': 0.65, 'name_ar': 'صالون تجميل'},
    'fitness_center': {'avg_ticket': 250, 'daily_customers': 8, 'margin': 0.60, 'name_ar': 'نادي رياضي'},
    'clinic': {'avg_ticket': 180, 'daily_customers': 20, 'margin': 0.55, 'name_ar': 'عيادة'},
    'hotel': {'avg_ticket': 350, 'daily_customers': 15, 'margin': 0.40, 'name_ar': 'فندق'},
    'services': {'avg_ticket': 60, 'daily_customers': 25, 'margin': 0.40, 'name_ar': 'خدمات'},
    'car_rental': {'avg_ticket': 200, 'daily_customers': 8, 'margin': 0.50, 'name_ar': 'تأجير سيارات'},
    'ev_charging_station': {'avg_ticket': 45, 'daily_customers': 40, 'margin': 0.25, 'name_ar': 'شحن كهربائي'},
}

# معاملات الإيجار السنوي حسب نوع المنطقة (ر.س/م²)
RENT_BY_AREA_TYPE = {
    'حضري مكتظ': {'low': 600, 'mid': 1200, 'high': 2500},  # الرياض/جدة وسط
    'حضري': {'low': 400, 'mid': 800, 'high': 1500},
    'سكني متوسط': {'low': 250, 'mid': 500, 'high': 900},
    'سكني محدود': {'low': 150, 'mid': 300, 'high': 600},
    'ريفي / أطراف': {'low': 80, 'mid': 180, 'high': 350},
    'نائي / فارغ': {'low': 50, 'mid': 100, 'high': 200},
}


# ════════════════════════════════════════════════════════════
# 🔴 إصلاح 6: بدائل التخصص للأنشطة المشبعة
# لكل فئة، قائمة "نسخ متخصصة" تتميّز عن المنافسة العادية
# مبنية على استراتيجية Differentiation و Niche Marketing
# ════════════════════════════════════════════════════════════
SPECIALIZATION_ALTERNATIVES = {
    'cafe': [
        {'name': 'مقهى مختصّ (Specialty Coffee)', 'why': 'تستهدف عشاق القهوة المتميزين، سعر أعلى، منافسة أقل'},
        {'name': 'Drive-Thru فقط', 'why': 'بدون جلسات داخلية - تكلفة أقل، حركة سريعة'},
        {'name': 'كوّيركينق + قهوة', 'why': 'تجذب موظفي العمل عن بُعد + اشتراكات شهرية ثابتة'},
        {'name': 'مقهى ديوانية تراثي', 'why': 'تجربة فريدة للعوائل والمناسبات'},
        {'name': 'Cloud Kitchen + Delivery', 'why': 'بدون موقع للجلوس - عبر التطبيقات فقط'},
    ],
    'restaurant': [
        {'name': 'مطعم مطبخ متخصص (إيطالي/ياباني/كوري)', 'why': 'تنويع المعروض، جذب فئة محددة'},
        {'name': 'مطعم Cloud Kitchen', 'why': 'إيجار منخفض، توصيل عبر التطبيقات'},
        {'name': 'مطعم وجبات صحية / كيتو', 'why': 'جمهور متنامي + هامش ربح أعلى'},
        {'name': 'مطعم عائلي مع منطقة أطفال', 'why': 'جذب العوائل للخروج معاً'},
        {'name': 'مطعم Food Truck', 'why': 'مرونة الموقع + استثمار أقل'},
    ],
    'fast_food': [
        {'name': 'مفهوم وجبات صحية سريعة', 'why': 'بديل صحي لـ KFC وماك'},
        {'name': 'Drive-Thru متخصص (شاورما/برجر)', 'why': 'سرعة + بدون جلسات'},
        {'name': 'Delivery-Only من Cloud Kitchen', 'why': 'تكلفة تشغيل أقل'},
    ],
    'grocery': [
        {'name': 'سوبرماركت منتجات عضوية', 'why': 'جمهور خاص + هامش ربح أعلى'},
        {'name': 'سوبرماركت 24 ساعة', 'why': 'ميزة تنافسية كبيرة (أكثر المنافسين يُغلقون)'},
        {'name': 'بقالة منتجات مستوردة', 'why': 'تنويع المعروض - بدون منافسة مباشرة'},
        {'name': 'متجر صغير + خدمة توصيل سريع', 'why': 'تطبيق + 30 دقيقة توصيل'},
    ],
    'pharmacy': [
        {'name': 'صيدلية متخصصة (بشرة/أعشاب)', 'why': 'منتجات Premium وخبرة متخصصة'},
        {'name': 'صيدلية + عيادة استشارية', 'why': 'تكامل خدمي - تجربة كاملة'},
        {'name': 'صيدلية تخدم 24 ساعة', 'why': 'ميزة فريدة في الأحياء'},
    ],
    'shopping': [
        {'name': 'محل منتجات يدوية / حرفية', 'why': 'منتجات فريدة لا تتوفر في الموالات'},
        {'name': 'محل ماركة محلية صاعدة', 'why': 'دعم العلامات السعودية الناشئة'},
    ],
    'clothing_store': [
        {'name': 'بوتيك تصاميم محلية', 'why': 'تميّز عن العلامات التجارية المعروفة'},
        {'name': 'محل ملابس رياضية متخصصة', 'why': 'يستهدف شريحة محددة (ركض/جيم)'},
        {'name': 'محل ملابس أطفال متخصص', 'why': 'منتجات متميزة للعوائل'},
    ],
    'auto_repair': [
        {'name': 'ورشة سيارات كهربائية', 'why': 'نمو سوق السيارات الكهربائية'},
        {'name': 'ورشة متخصصة (BMW/Lexus/Mercedes)', 'why': 'أسعار أعلى + خبرة متخصصة'},
        {'name': 'ورشة + خدمة استلام وتوصيل', 'why': 'راحة العميل = ميزة تنافسية'},
    ],
    'car_wash': [
        {'name': 'غسيل سيارات بالبخار (Eco)', 'why': 'صديق للبيئة + توفير ماء'},
        {'name': 'مغسلة + كافيه انتظار', 'why': 'كيمياء العائلة - عميل يستفيد من الوقت'},
        {'name': 'غسيل في موقع العميل', 'why': 'خدمة فاخرة - بدون موقع ثابت'},
    ],
    'beauty_salon': [
        {'name': 'صالون أطفال متخصص', 'why': 'فئة قليلة المنافسة - ولاء عالٍ'},
        {'name': 'صالون VIP بالموعد فقط', 'why': 'تجربة فاخرة - أسعار أعلى'},
        {'name': 'صالون رجالي راقي (Barber Shop)', 'why': 'مفهوم حديث - يستهدف الشباب'},
    ],
    'services': [
        {'name': 'مغسلة ملابس + استلام منزلي', 'why': 'بديل للمغاسل التقليدية'},
        {'name': 'مركز خدمات حكومية موحد', 'why': 'تجميع خدمات - يوفر وقت العميل'},
    ],
}


def get_specialization_alternatives(target_cat):
    """يرجع بدائل التخصص لنشاط مشبع"""
    return SPECIALIZATION_ALTERNATIVES.get(target_cat, [])


def get_benchmark_for_activity(target_cat, traffic_score, area_character, competitors_count=0):
    """يرجع تقدير benchmarks لنشاط معيّن بناءً على نوع المنطقة والحركة"""
    if not target_cat or target_cat not in ACTIVITY_BENCHMARKS:
        return None
    
    base = ACTIVITY_BENCHMARKS[target_cat].copy()
    
    # تعديل عدد العملاء بناءً على الحركة
    traffic_multiplier = 1.0
    if traffic_score >= 80:
        traffic_multiplier = 1.5
    elif traffic_score >= 60:
        traffic_multiplier = 1.2
    elif traffic_score >= 40:
        traffic_multiplier = 1.0
    elif traffic_score >= 20:
        traffic_multiplier = 0.7
    else:
        traffic_multiplier = 0.4
    
    # تعديل بناءً على نوع المنطقة (مدن كبيرة = أسعار أعلى وعملاء أكثر)
    area_multiplier = 1.0
    if area_character == 'حضري مكتظ':
        area_multiplier = 1.4
    elif area_character == 'حضري':
        area_multiplier = 1.15
    elif area_character == 'سكني متوسط':
        area_multiplier = 1.0
    elif area_character == 'سكني محدود':
        area_multiplier = 0.75
    elif area_character == 'ريفي / أطراف':
        area_multiplier = 0.5
    else:
        area_multiplier = 0.35
    
    # توزيع نصيب العملاء على المنافسين (الكعكة تُقسّم)
    # لو عندنا 22 مقهى → كل واحد يأخذ نصيبه + جزء من السوق الجديد
    competition_share = 1.0
    if competitors_count > 0:
        # نصيبك ≈ 1 / (عدد المنافسين + 1) + 0.3 (السوق ينمو قليلاً)
        competition_share = (1.0 / (competitors_count + 1)) + 0.3
        competition_share = min(1.0, competition_share)
    
    estimated_daily_customers = int(base['daily_customers'] * traffic_multiplier * area_multiplier * competition_share)
    estimated_avg_ticket = int(base['avg_ticket'] * (1.0 + (area_multiplier - 1.0) * 0.5))  # السعر يرتفع قليلاً في الحضر
    
    return {
        'estimated_avg_ticket': estimated_avg_ticket,
        'estimated_daily_customers': max(1, estimated_daily_customers),
        'margin': base['margin'],
        'activity_name': base['name_ar'],
        'traffic_multiplier': traffic_multiplier,
        'area_multiplier': area_multiplier,
        'competition_share': competition_share,
        'is_estimated': True,
    }


def get_estimated_rent(area_sqm, area_character, traffic_score):
    """يرجع تقدير إيجار سنوي بناءً على المنطقة والمساحة"""
    if not area_sqm or area_sqm <= 0:
        return None
    rent_data = RENT_BY_AREA_TYPE.get(area_character, RENT_BY_AREA_TYPE['سكني محدود'])
    # نختار المتوسط، نعدّل قليلاً حسب الحركة
    if traffic_score >= 75:
        rent_per_sqm = rent_data['high']
    elif traffic_score >= 50:
        rent_per_sqm = rent_data['mid']
    else:
        rent_per_sqm = rent_data['low']
    return int(rent_per_sqm * area_sqm)


# 🔴 إنفاق سنوي تقديري للفرد على كل نشاط (ر.س/سنة)
# مبني على متوسطات السوق السعودي
ANNUAL_SPEND_PER_CAPITA = {
    'cafe': 600,           # 50 ر.س/شهر × 12
    'restaurant': 1800,    # وجبات خارجية
    'fast_food': 1200,
    'grocery': 8000,       # احتياجات يومية
    'pharmacy': 1500,
    'fuel': 4500,
    'shopping': 3000,
    'clothing_store': 2400,
    'electronics_store': 1800,
    'auto_repair': 1500,
    'car_wash': 360,
    'beauty_salon': 1200,
    'fitness_center': 1500,
    'clinic': 800,
    'hospital': 1200,
    'hotel': 2000,
    'services': 800,
    'car_rental': 500,
    'ev_charging_station': 600,
}


def calculate_market_size(target_cat, local_population, competitors_count):
    """
    يحسب حجم السوق المالي السنوي والحصة المتوقعة
    معادلة Market Size: السكان × متوسط الإنفاق السنوي
    معادلة الحصة: حجم السوق / (المنافسين + 1)
    """
    if not target_cat or not local_population or local_population <= 0:
        return None
    
    spend_per_capita = ANNUAL_SPEND_PER_CAPITA.get(target_cat, 600)
    
    # حجم السوق السنوي الإجمالي
    total_market_size = local_population * spend_per_capita
    
    # عدد المتنافسين (بما فيهم أنت)
    n_players = competitors_count + 1
    
    # الحصة المتوقعة (متوسط، بافتراض توزيع عادل)
    expected_share = total_market_size / n_players
    
    # الحصة الواقعية (الواقع: المنافسون الأقدم يأخذون أكثر)
    # العميل الجديد عادة يحصل على 60-80% من المتوسط في السنة الأولى
    realistic_share_y1 = int(expected_share * 0.7)
    realistic_share_y2 = int(expected_share * 0.85)
    realistic_share_y3 = int(expected_share * 0.95)
    
    # متوسط فاتورة وعدد عملاء يومي مشتق
    daily_revenue_y1 = realistic_share_y1 / 365
    
    return {
        'total_market_annual': total_market_size,
        'spend_per_capita': spend_per_capita,
        'competitors_count': competitors_count,
        'players_total': n_players,
        'expected_share_annual': int(expected_share),
        'realistic_share_y1': realistic_share_y1,
        'realistic_share_y2': realistic_share_y2,
        'realistic_share_y3': realistic_share_y3,
        'realistic_monthly_y1': int(realistic_share_y1 / 12),
        'realistic_monthly_y3': int(realistic_share_y3 / 12),
        'daily_revenue_y1': int(daily_revenue_y1),
    }


def financial_analysis(rent_yearly, setup_cost, area_sqm, employees, avg_ticket, daily_customers,
                       target_cat=None, total_places=0, traffic_score=50, area_character='سكني محدود',
                       competitors_count=0):
    """
    التحليل المالي - الآن مع benchmarks استقرائية.
    
    التغييرات (إصلاح 3):
    - ✅ لو المستخدم لم يدخل إيرادات، نستخدم benchmarks
    - ✅ نوضح كل رقم: حقيقي (من المستخدم) أم تقديري
    - ✅ نسمح للتقدير ينتج تحليل أولي مفيد
    """
    benchmark = get_benchmark_for_activity(target_cat, traffic_score, area_character, competitors_count)
    
    # تتبّع المصدر: ما الذي أدخله المستخدم وما الذي قدّرناه
    sources = {}
    
    # متوسط الفاتورة
    if avg_ticket and avg_ticket > 0:
        sources['avg_ticket'] = 'user'
    elif benchmark:
        avg_ticket = benchmark['estimated_avg_ticket']
        sources['avg_ticket'] = 'estimated'
    else:
        avg_ticket = 0
        sources['avg_ticket'] = 'missing'
    
    # عدد العملاء
    if daily_customers and daily_customers > 0:
        sources['daily_customers'] = 'user'
    elif benchmark:
        daily_customers = benchmark['estimated_daily_customers']
        sources['daily_customers'] = 'estimated'
    else:
        daily_customers = 0
        sources['daily_customers'] = 'missing'
    
    # الإيجار
    if rent_yearly and rent_yearly > 0:
        sources['rent_yearly'] = 'user'
    else:
        est_rent = get_estimated_rent(area_sqm, area_character, traffic_score)
        if est_rent:
            rent_yearly = est_rent
            sources['rent_yearly'] = 'estimated'
        else:
            rent_yearly = 0
            sources['rent_yearly'] = 'missing'
    
    # إذا كل شي صفر، نرجع None (لا فائدة)
    if not (rent_yearly or setup_cost or avg_ticket or daily_customers):
        return None

    rent_yearly = rent_yearly or 0
    setup_cost = setup_cost or 0
    avg_ticket = avg_ticket or 0
    daily_customers = daily_customers or 0
    employees = employees or 0
    area_sqm = area_sqm or 0
    
    has_revenue_data = (avg_ticket > 0 and daily_customers > 0)
    has_cost_data = (rent_yearly > 0 or setup_cost > 0)

    rent_monthly = rent_yearly / 12
    salary_per_employee = 4000  # افتراض - قابل للتعديل
    salaries_monthly = employees * salary_per_employee
    utilities = max(800, area_sqm * 8) if area_sqm > 0 else 800
    other_costs = (rent_monthly + salaries_monthly + utilities) * 0.10
    monthly_expenses = rent_monthly + salaries_monthly + utilities + other_costs

    monthly_revenue = avg_ticket * daily_customers * 30
    gross_margin = 0.35 if target_cat in ('restaurant', 'cafe', 'fast_food', 'grocery') else 0.50
    monthly_gross_profit = monthly_revenue * gross_margin

    net_profit_monthly = monthly_gross_profit - monthly_expenses
    total_capital = setup_cost + (rent_monthly * 3)

    breakeven_daily = None
    if avg_ticket > 0 and gross_margin > 0:
        breakeven_daily = math.ceil((monthly_expenses / gross_margin) / 30 / avg_ticket)

    payback_months = None
    if net_profit_monthly > 0:
        payback_months = math.ceil(total_capital / net_profit_monthly)

    rent_per_sqm = None
    rent_assessment = None
    rent_status = None
    if rent_yearly > 0 and area_sqm > 0:
        rent_per_sqm = rent_yearly / area_sqm

    # ✅ المنطق المحسّن مع benchmarks:
    # نحدد ما إذا كانت الأرقام تقديرية بناءً على sources
    revenue_is_estimated = sources.get('avg_ticket') == 'estimated' or sources.get('daily_customers') == 'estimated'
    rent_is_estimated = sources.get('rent_yearly') == 'estimated'
    
    estimate_warning = ""
    if revenue_is_estimated or rent_is_estimated:
        est_parts = []
        if revenue_is_estimated:
            est_parts.append(f"الفاتورة {avg_ticket} ر.س + العملاء {daily_customers}/يوم (تقدير قطاعي)")
        if rent_is_estimated:
            est_parts.append(f"الإيجار {rent_yearly:,.0f} ر.س/سنة (تقدير حسب نوع المنطقة)")
        estimate_warning = f" ⚠️ استخدمنا تقديرات لـ: {' • '.join(est_parts)}. عدّلها لو عندك أرقام أدق."
    
    if not has_revenue_data:
        verdict = "تحليل غير مكتمل ⚠️"
        verdict_status = "warn"
        verdict_detail = ("أدخل متوسط الفاتورة + عدد العملاء أو حدّد نشاطاً نستخدم له تقديرات قياسية.")
    elif not has_cost_data:
        verdict = "بيانات التكلفة ناقصة ⚠️"
        verdict_status = "warn"
        verdict_detail = "أدخل تكاليف الإيجار والتجهيز للحصول على تحليل جدوى كامل."
    elif net_profit_monthly > 0 and payback_months and payback_months <= 24:
        verdict = "مجدي مالياً ✅" if not (revenue_is_estimated or rent_is_estimated) else "مجدي تقديرياً ✅"
        verdict_status = "good"
        verdict_detail = f"الأرباح تغطي رأس المال خلال {payback_months} شهر.{estimate_warning}"
    elif net_profit_monthly > 0 and payback_months and payback_months <= 48:
        verdict = "مجدي لكن استرداد بطيء ⚠️"
        verdict_status = "ok"
        verdict_detail = f"يحتاج {payback_months} شهر لاسترداد رأس المال.{estimate_warning}"
    elif net_profit_monthly > 0:
        verdict = "يحتاج دراسة دقيقة ⚠️"
        verdict_status = "warn"
        verdict_detail = f"ربح ضعيف نسبة لرأس المال - راجع الإيجار أو الإيرادات المتوقعة.{estimate_warning}"
    else:
        verdict = "بحاجة إعادة دراسة الأرقام ⚠️"
        verdict_status = "danger"
        verdict_detail = (f"المصاريف ({monthly_expenses:,.0f}) تتجاوز الأرباح ({monthly_gross_profit:,.0f}). "
                          f"تحقق من توقعات العملاء وأسعارك.{estimate_warning}")

    return {
        'rent_monthly': rent_monthly, 'salaries_monthly': salaries_monthly,
        'utilities': utilities, 'other_costs': other_costs,
        'monthly_expenses': monthly_expenses, 'monthly_revenue': monthly_revenue,
        'monthly_gross_profit': monthly_gross_profit, 'net_profit_monthly': net_profit_monthly,
        'total_capital': total_capital, 'breakeven_daily': breakeven_daily,
        'payback_months': payback_months, 'rent_per_sqm': rent_per_sqm,
        'rent_assessment': rent_assessment, 'rent_status': rent_status,
        'verdict': verdict, 'verdict_status': verdict_status, 'verdict_detail': verdict_detail,
        'has_revenue_data': has_revenue_data, 'has_cost_data': has_cost_data,
        'sources': sources,
        'is_estimated': revenue_is_estimated or rent_is_estimated,
        'benchmark_used': benchmark,
        'assumptions': {
            'salary_per_employee': salary_per_employee,
            'gross_margin': gross_margin,
            'other_costs_pct': 10,
        }
    }


# ============================================================================
# [الدفعة 4] AI helpers
# ============================================================================
def analyze_image_with_ai(image, location_context=""):
    """تحليل صورة الموقع بـ Gemini Vision"""
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
    """دمج نتائج تحليل الصور في التحليل الأساسي"""
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


def analyze_custom_activity(activity_text, analysis, pbc, lat, lng):
    """تحليل نشاط مخصص (يكتبه المستخدم)"""
    if not AI_AVAILABLE:
        total = analysis['total_places']
        return {
            'activity': activity_text,
            'verdict': 'يحتاج دراسة' if total > 10 else 'بيانات محدودة',
            'verdict_color': '#f59e0b',
            'score': 50,
            'reasoning': f"تحليل تلقائي: المنطقة فيها {total} محل تجاري بمستوى حركة {analysis['traffic_level']}. "
                         f"للحصول على تحليل دقيق للنشاط '{activity_text}'، فعّل GEMINI_API_KEY.",
            'similar_competitors': 0,
            'opportunities': ["ضع خطة تسويق قوية", "ركّز على التميّز عن المنافسين"],
            'risks': ["تأكد من دراسة السوق ميدانياً"],
        }
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
        gov_text = ""
        if analysis.get('gov_info'):
            gi = analysis['gov_info']
            gov_text = f"\n- المحافظة: {gi['name']} (سكان: {gi['data']['pop']:,})"
        prompt = f"""أنت خبير تحليل مواقع تجارية في السعودية. حلّل جدوى فتح نشاط محدد:

النشاط المقترح: "{activity_text}"

بيانات الموقع:
- إجمالي المحلات في النطاق: {analysis['total_places']}
- الأنشطة الموجودة: {summary}{gov_text}
- ثقافة الحي: {analysis['dna']['main']} (عائلي:{analysis['dna']['family']}%, شبابي:{analysis['dna']['youth']}%, تجاري:{analysis['dna']['commercial']}%)
- الحركة: {analysis['traffic_level']} ({analysis['traffic_score']}/100)
- سهولة الوصول: {analysis['accessibility']} ({analysis['accessibility_score']}/100)
- نوع المنطقة: {analysis['area_type']}

أعد JSON فقط:
{{
  "verdict": "نص قصير: فرصة ممتازة، مناسب، يحتاج دراسة، غير مناسب، تجنّبه",
  "verdict_color": "#10b981 ممتاز / #3b82f6 جيد / #f59e0b متوسط / #f97316 ضعيف / #ef4444 سيء",
  "score": "رقم من 0-100",
  "reasoning": "شرح 3 جمل: لماذا هذا التقييم؟",
  "similar_competitors": "رقم تقديري للمنافسين المشابهين",
  "opportunities": ["فرصة 1", "فرصة 2", "فرصة 3"],
  "risks": ["تحذير 1", "تحذير 2"]
}}"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        result = json.loads(text.strip())
        result['activity'] = activity_text
        try:
            result['score'] = int(str(result.get('score', 50)).strip())
        except Exception:
            result['score'] = 50
        try:
            result['similar_competitors'] = int(str(result.get('similar_competitors', 0)).strip())
        except Exception:
            result['similar_competitors'] = 0
        return result
    except Exception:
        return {
            'activity': activity_text,
            'verdict': 'تعذّر التحليل',
            'verdict_color': '#94a3b8',
            'score': 50,
            'reasoning': "حدث خطأ في تحليل AI. حاول مرة أخرى.",
            'similar_competitors': 0,
            'opportunities': [],
            'risks': [],
        }


def analyze_field_report(report_text, analysis, pbc, lat, lng):
    """تحليل التقرير الميداني النصي من المستخدم بـ Gemini"""
    if not AI_AVAILABLE or not report_text.strip():
        return None
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
        prompt = f"""أنت خبير تحليل مواقع. اقرأ هذا التقرير الميداني من زائر فعلي للموقع واستخرج رؤى:

التقرير الميداني:
"{report_text}"

السياق الإضافي عن الموقع:
- الأنشطة المكتشفة: {summary}
- نوع المنطقة: {analysis['area_type']}

أعد JSON فقط:
{{
  "key_insights": ["رؤية مهمة 1", "رؤية مهمة 2", "رؤية مهمة 3"],
  "extracted_facts": {{"foot_traffic": "ضعيف/متوسط/قوي", "competitor_strength": "ضعيف/متوسط/قوي", "area_potential": "ضعيف/متوسط/قوي"}},
  "warnings_detected": ["تحذير 1", "تحذير 2"],
  "opportunities_detected": ["فرصة 1", "فرصة 2"],
  "summary": "ملخص في جملتين"
}}"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except Exception:
        return None


def ai_enhance(analysis, pbc, lat, lng):
    """تحسين التحليل بـ Gemini AI - تحليل SWOT منظم بالأرقام"""
    if not AI_AVAILABLE:
        return analysis
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
        gov_text = ""
        if analysis.get('gov_info'):
            gi = analysis['gov_info']
            gov_text = f"\n- المحافظة: {gi['name']} (سكان: {gi['data']['pop']:,})"
        
        local_text = ""
        if analysis.get('local_population'):
            local_text = f"\n- السكان المحليون المقدّرون: {analysis['local_population']:,} ({analysis.get('area_character', '-')})"
        
        # تحذير البيانات المقصوصة
        truncation_warn = ""
        if analysis.get('data_is_truncated'):
            truncation_warn = f"\n⚠️ تنبيه مهم: {analysis.get('categories_at_limit', 0)} فئات وصلت لحد API الأقصى (25 محل) - المنطقة مكتظة جداً والأرقام الحقيقية أكبر."
        
        # أسماء منافسين فعليين
        competitor_names = ""
        target = analysis.get('target_cat')
        if target and target in pbc:
            top5 = pbc[target][:5]
            names = [p.get('name', '?') for p in top5]
            competitor_names = f"\n- أسماء أبرز المنافسين المباشرين ({CATEGORIES[target]['name']}): {' | '.join(names)}"
        
        # كيمياء العائلة + الفرص
        chem_text = ""
        if analysis.get('best_activities'):
            top_act = analysis['best_activities'][0]
            if top_act.get('synergies'):
                top_syn = top_act['synergies'][0]
                chem_text = f"\n- أقوى ترابط: {top_act['icon']} {top_act['cat_name']} ينسجم مع {top_syn['icon']} {top_syn['name']} ({top_syn['count']} محل)"
        
        # ════════════════════════════════════════════════════════════
        # 🚨 prompt صارم جداً - منع التناقضات والأرقام المكررة
        # ════════════════════════════════════════════════════════════
        score = analysis['investment_score']
        sat = analysis['saturation_score']
        opp = analysis['opportunity_score']
        local_pop = analysis.get('local_population', 0)
        
        # نحدد السقف المناسب للتوصية بناءً على الأرقام الحقيقية
        if score < 40 or sat >= 95:
            mandatory_tone = "موقع ضعيف أو غير مناسب - يجب أن تكون التوصية حذرة جداً"
        elif score < 55:
            mandatory_tone = "موقع متوسط الجودة فقط - لا تستخدم 'جيد' أو 'ممتاز'"
        elif score < 70:
            mandatory_tone = "موقع جيد لكن يحتاج دراسة - لا تستخدم 'ممتاز'"
        else:
            mandatory_tone = "موقع جيد"
        
        prompt = f"""أنت محلل استثمار تجاري صارم في السعودية. أنشئ تحليل SWOT دقيق.

📍 الموقع: ({lat:.4f}, {lng:.4f}){gov_text}{local_text}
🏪 المحلات: {summary}
📊 المؤشرات: الفرصة {opp}% | الإشباع {sat}% | الطلب {analysis['demand_score']}%
🎯 التقييم: {analysis['decision']} ({score}/100){competitor_names}{chem_text}{truncation_warn}

🚨 قواعد صارمة - أي مخالفة = رفض الإجابة:
1. كل نقطة SWOT تبدأ برقم محدد أو اسم منافس فعلي
2. **ممنوع** ذكر رقم السكان المحليين ({local_pop:,}) في أكثر من نقطة واحدة في كل القسم
3. **ممنوع** تكرار نفس النقطة بكلمات مختلفة
4. النبرة المطلوبة: {mandatory_tone}
5. لو {sat}% تشبع → احذر من قول "موقع جيد" أو "فرصة كبيرة"
6. لو {opp}% فرصة <30% → احذر من التفاؤل
7. لا تخلط: "نقص الترفيه" يكون **إما** weakness **أو** opportunity (ليس الاثنين)
8. لو البيانات مقصوصة، اذكر "السوق أكبر مما يظهر" في threats فقط
9. كل نقطة جملة قصيرة (≤15 كلمة)
10. لا تستخدم كلام عام أو إنشائي

أعد JSON فقط:
{{
  "ai_recommendation": "ملخص بجملتين بالأرقام - متماشي مع النبرة المطلوبة",
  "swot": {{
    "strengths": ["نقطة 1 برقم", "نقطة 2 برقم", "نقطة 3 برقم"],
    "weaknesses": ["نقطة 1 برقم", "نقطة 2 برقم", "نقطة 3 برقم"],
    "opportunities": ["فرصة 1 محددة", "فرصة 2 محددة", "فرصة 3 محددة"],
    "threats": ["تهديد 1 برقم", "تهديد 2 برقم", "تهديد 3 برقم"]
  }}
}}"""
        text = model.generate_content(prompt).text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        d = json.loads(text.strip())
        
        # 🔴 Validation: نتحقق من التناقض
        ai_rec = d.get('ai_recommendation', '')
        
        # لو AI قال "جيد" أو "ممتاز" والنقاط منخفضة → نستبدل بنص محايد
        if score < 50:
            bad_words = ['جيد', 'ممتاز', 'مثالي', 'فرصة كبيرة', 'موقع رائع', 'إمكانات قوية']
            for word in bad_words:
                if word in ai_rec:
                    ai_rec = f"الموقع يواجه تحديات كبيرة: تشبع {sat}% وفرصة {opp}% فقط. يحتاج تخصصاً قوياً أو نطاقاً أصغر."
                    break
        
        # validation للـ SWOT - منع تكرار رقم السكان
        swot_data = d.get('swot', {})
        for swot_key in ['strengths', 'weaknesses', 'opportunities', 'threats']:
            items = swot_data.get(swot_key, [])
            # نحسب كم مرة ظهر رقم السكان في القسم
            pop_str = f"{local_pop:,}"
            pop_count = sum(1 for item in items if pop_str in str(item))
            if pop_count > 1:
                # نحذف التكرارات (نبقي الأول فقط)
                seen_pop = False
                filtered = []
                for item in items:
                    if pop_str in str(item):
                        if seen_pop:
                            continue
                        seen_pop = True
                    filtered.append(item)
                swot_data[swot_key] = filtered
        
        analysis['ai_recommendation'] = ai_rec
        analysis['swot'] = swot_data
        analysis['ai_enhanced'] = True
    except Exception:
        analysis['ai_enhanced'] = False
    return analysis


def ai_chat(msg, analysis, pbc, lat, lng):
    """محادثة AI مع السياق الكامل"""
    if AI_AVAILABLE:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in pbc.items()])
            gov_text = ""
            if analysis.get('gov_info'):
                gi = analysis['gov_info']
                gov_text = f"\nالمحافظة: {gi['name']} (سكان: {gi['data']['pop']:,})"
            
            local_text = ""
            if analysis.get('local_population'):
                local_text = f"\nالسكان المحليون التقديريون: {analysis['local_population']:,} ({analysis.get('area_character', '-')})"
            
            # أسماء منافسين
            competitor_names = ""
            target = analysis.get('target_cat')
            if target and target in pbc:
                top3 = [p.get('name', '?') for p in pbc[target][:3]]
                competitor_names = f"\nمنافسون مباشرون: {' | '.join(top3)}"
            
            # أفضل الأنشطة المقترحة
            best_acts = ""
            if analysis.get('best_activities'):
                best_acts = "\nأفضل 3 أنشطة مقترحة: " + ", ".join(
                    [f"{b['icon']} {b['cat_name']} ({b.get('final_opportunity', 0)}%)" for b in analysis['best_activities'][:3]]
                )
            
            # تحليل مالي مختصر
            fin_text = ""
            if analysis.get('financial'):
                f = analysis['financial']
                fin_text = f"\nمالي: ربح متوقع {f['net_profit_monthly']:,.0f} ر.س/شهر | حكم: {f['verdict']}"
            
            ctx = f"""أنت مستشار استثمار في السعودية، تجيب باللغة العربية بعمق ووضوح.

موقع: {lat:.4f}, {lng:.4f}{gov_text}{local_text}
الأنشطة في النطاق: {summary}
المؤشرات: استثمار {analysis['investment_score']}/100 | فرصة {analysis['opportunity_score']}% | إشباع {analysis['saturation_score']}% | طلب {analysis['demand_score']}%
المنطقة: {analysis['area_type']} | الحركة: {analysis['traffic_level']}
نوع الشارع: {analysis.get('street_info', {}).get('category', 'غير معروف')} (تأثيره على الفرصة: {analysis.get('street_info', {}).get('opportunity_modifier', 0)}%)
القرار: {analysis['decision']}{competitor_names}{best_acts}{fin_text}

سؤال المستخدم: {msg}

🚨 قواعد:
- استخدم أرقاماً محددة من البيانات أعلاه
- اذكر أسماء منافسين/أنشطة عند الإمكان
- إجابة مختصرة (3-5 جمل) وعملية، ليست عامة
- لو السؤال يحتاج تخمين، وضّح أنه تقدير"""
            return model.generate_content(ctx).text.strip()
        except Exception:
            pass
    return f"📊 {analysis['decision']}: {analysis['decision_summary']}"
# ============================================================================
# [الدفعة 5] تقرير PDF (HTML قابل للطباعة)
# ============================================================================
def build_report_html(a, pbc, lat, lng, radius):
    """يولّد تقرير HTML قابل للطباعة كـ PDF عبر المتصفح"""
    from datetime import datetime
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")

    # تحذير الصدق
    honesty = """
    <div style="background:#fef3c7; border:2px solid #f59e0b; border-radius:12px; padding:14px; margin-bottom:18px;">
        <b style="color:#92400e;">⚠️ تنبيه:</b>
        <span style="color:#78350f; font-size:13px;">
        هذا التقرير أداة استكشاف أولية، وليس دراسة جدوى مهنية معتمدة. 
        لا يحتوي على تقييمات منافسين فعلية ولا حركة عملاء حقيقية.
        مطلوب قبل القرار: زيارة ميدانية + استشارة خبير.
        </span>
    </div>
    """

    # رأس التقرير
    header = f"""
    <div class="report-header">
        <div class="logo">📊 GBI</div>
        <div class="header-info">
            <h1>تقرير تحليل الموقع التجاري</h1>
            <div class="meta">
                <span>📅 {now}</span>
                <span>📍 {lat:.4f}, {lng:.4f}</span>
                <span>📏 نطاق {radius} كم</span>
            </div>
        </div>
    </div>
    """

    # القرار النهائي
    conf = a.get('confidence', {})
    
    # تحذير البيانات المقصوصة (PDF)
    truncation_banner_pdf = ""
    if a.get('data_is_truncated'):
        sev_pdf = a.get('truncation_severity', 'moderate')
        n_lim = a.get('categories_at_limit', 0)
        if sev_pdf == "severe":
            truncation_banner_pdf = f"""<div style="background:#fef2f2; border:2px solid #ef4444; border-radius:10px; padding:14px; margin:14px 0;">
<div style="color:#991b1b; font-size:14px; font-weight:700; margin-bottom:6px;">🚨 منطقة مكتظة - البيانات مقصوصة</div>
<div style="color:#7f1d1d; font-size:12px;">
{n_lim} فئات وصلت لحد API الأقصى (25 محل). الواقع: المنطقة بها أعداد أكبر بكثير.
الأرقام المعروضة <b>أقل من الواقع</b>. ينصح بنطاق أصغر للدقة.
</div>
</div>"""
        else:
            truncation_banner_pdf = f"""<div style="background:#fffbeb; border:1px solid #f59e0b; border-radius:10px; padding:12px; margin:14px 0;">
<div style="color:#92400e; font-size:13px; font-weight:600;">⚠️ {n_lim} فئات قد تكون مقصوصة</div>
<div style="color:#78350f; font-size:11px; margin-top:4px;">الأرقام قد تكون أقل من الواقع. جرّب نطاق أصغر.</div>
</div>"""
    
    decision_section = f"""
    <div class="section verdict" style="border-color: {a['decision_color']}; background: {a['decision_bg']};">
        <div class="verdict-label">🎯 القرار النهائي</div>
        <h2 style="color: {a['decision_color']};">{a['decision_emoji']} {a['decision']}</h2>
        <div class="verdict-score">نقاط الاستثمار: <b>{a['investment_score']}/100</b>
            &nbsp;|&nbsp; ثقة التحليل: <b style="color:{conf.get('color', '#94a3b8')}">{conf.get('score', 0)}% ({conf.get('level', '-')})</b>
        </div>
        <div class="verdict-score" style="margin-top:6px;">🛣️ نوع الشارع: <b>{a.get('street_info', {}).get('category', 'غير معروف')}</b>{(' (' + a['street_info']['name'] + ')') if a.get('street_info', {}).get('name') else ''}
            &nbsp;|&nbsp; تأثيره على الفرصة: <b>{a.get('street_info', {}).get('opportunity_modifier', 0)}%</b>
        </div>
        <p class="verdict-text">{esc(a.get('ai_recommendation') if a.get('ai_enhanced') else a['decision_summary'])}</p>
    </div>
    {truncation_banner_pdf}
    """
    
    # SWOT في PDF
    swot_section_pdf = ""
    if a.get('swot') and isinstance(a['swot'], dict):
        swot_d = a['swot']
        def _build_swot_list(items, color):
            if not items:
                return '<li style="color:#9ca3af; font-size:12px;">لا يوجد</li>'
            return "".join(f'<li style="padding:4px 0; color:#374151; font-size:13px;">{itm}</li>' for itm in items)
        
        s_items = _build_swot_list(swot_d.get('strengths', []), '#10b981')
        w_items = _build_swot_list(swot_d.get('weaknesses', []), '#f59e0b')
        o_items = _build_swot_list(swot_d.get('opportunities', []), '#3b82f6')
        t_items = _build_swot_list(swot_d.get('threats', []), '#ef4444')
        
        swot_section_pdf = f"""<div class="section page-break"><h3>📊 تحليل SWOT الاستثماري</h3>
        <table style="width:100%; border-collapse:separate; border-spacing:8px;">
        <tr>
            <td style="vertical-align:top; background:#ecfdf5; border:1px solid #10b981; border-right:4px solid #10b981; border-radius:8px; padding:12px; width:50%;">
                <div style="color:#047857; font-weight:700; margin-bottom:6px;">💪 نقاط القوة</div>
                <ul style="list-style:none; padding:0; margin:0;">{s_items}</ul>
            </td>
            <td style="vertical-align:top; background:#fffbeb; border:1px solid #f59e0b; border-right:4px solid #f59e0b; border-radius:8px; padding:12px; width:50%;">
                <div style="color:#92400e; font-weight:700; margin-bottom:6px;">⚠️ نقاط الضعف</div>
                <ul style="list-style:none; padding:0; margin:0;">{w_items}</ul>
            </td>
        </tr>
        <tr>
            <td style="vertical-align:top; background:#eff6ff; border:1px solid #3b82f6; border-right:4px solid #3b82f6; border-radius:8px; padding:12px;">
                <div style="color:#1e40af; font-weight:700; margin-bottom:6px;">🌟 الفرص</div>
                <ul style="list-style:none; padding:0; margin:0;">{o_items}</ul>
            </td>
            <td style="vertical-align:top; background:#fef2f2; border:1px solid #ef4444; border-right:4px solid #ef4444; border-radius:8px; padding:12px;">
                <div style="color:#991b1b; font-weight:700; margin-bottom:6px;">🚨 التهديدات</div>
                <ul style="list-style:none; padding:0; margin:0;">{t_items}</ul>
            </td>
        </tr>
        </table>
        </div>"""

    # تحذير الإشباع + بدائل التخصص للنشاط المختار
    saturation_warning_pdf = ""
    target_cat_pdf = a.get('target_cat')
    if target_cat_pdf and a.get('local_population') and a['local_population'] > 0:
        comp_count_pdf = len(pbc.get(target_cat_pdf, []))
        if comp_count_pdf > 0:
            cp_pdf = (comp_count_pdf * 1000) / a['local_population']
            warn_html = ""
            severity_color = "#10b981"
            if cp_pdf > 7:
                severity_color = "#dc2626"
                warn_html = f"""🚫 <b>كارثة سوقية متوقعة!</b><br>
                {comp_count_pdf} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_pdf:.1f} منافس/1000 نسمة</b><br>
                الحد الصحي < 1.5/1000. هذا السوق <b>مدمّر تماماً</b> للنشاط العادي."""
            elif cp_pdf > 3.5:
                severity_color = "#dc2626"
                warn_html = f"""⚠️ <b>خطر شديد!</b><br>
                {comp_count_pdf} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_pdf:.1f}/1000</b><br>
                الفرص للنشاط العادي محدودة - <b>التخصص ضروري</b>."""
            elif cp_pdf > 1.5:
                severity_color = "#f59e0b"
                warn_html = f"""🟡 <b>منافسة عالية</b><br>
                {comp_count_pdf} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_pdf:.1f}/1000</b><br>
                الدخول يتطلب تمايز قوي."""
            
            if warn_html:
                alts_pdf = get_specialization_alternatives(target_cat_pdf)
                alts_html = ""
                if alts_pdf:
                    alt_items = "".join(
                        f'<li style="padding:8px 0; border-bottom:1px solid #e5e7eb;"><b>{i+1}. {alt["name"]}</b><br><span style="color:#6b7280; font-size:13px;">💡 {alt["why"]}</span></li>'
                        for i, alt in enumerate(alts_pdf[:5])
                    )
                    alts_html = f"""
                    <div style="background:#f3e8ff; border:1px solid #a855f7; border-radius:10px; padding:14px; margin-top:14px;">
                        <h4 style="color:#7c3aed; margin-bottom:10px;">💡 بدائل التخصص - كيف تنجح في سوق مشبع؟</h4>
                        <ul style="list-style:none; padding:0; margin:0;">{alt_items}</ul>
                    </div>
                    """
                
                saturation_warning_pdf = f"""
                <div class="section" style="border:2px solid {severity_color}; background:rgba(239,68,68,0.05);">
                    <div style="color:{severity_color}; font-size:16px; line-height:1.7;">{warn_html}</div>
                    {alts_html}
                </div>
                """

    # بيانات المحافظة (لو موجودة)
    gov_section = ""
    if a.get('gov_info'):
        gi = a['gov_info']
        conf_text = {"high": "عالية", "medium": "متوسطة", "low": "محدودة"}.get(gi['confidence'], '-')
        
        local_html = ""
        if a.get('local_population'):
            local_html = f"""
            <div style="background:#ecfdf5; border-right:3px solid #10b981; padding:12px; border-radius:8px; margin-top:12px;">
                <div style="color:#047857; font-weight:700; font-size:13px; margin-bottom:6px;">📊 التقدير المحلي (داخل نطاق التحليل)</div>
                <div style="color:#4b5563; font-size:13px;">
                    👥 السكان المحليون: <b>~{a['local_population']:,}</b> | 
                    📊 الكثافة: <b>{a.get('local_density', 0):,}</b> ن/كم² | 
                    🏘️ نوع المنطقة: <b>{a.get('area_character', '-')}</b>
                </div>
                <div style="color:#6b7280; font-size:11px; margin-top:4px;">
                    💡 تقدير مبني على عدد المحلات في النطاق ({a['total_places']} محل)
                </div>
            </div>
            """
        
        gov_section = f"""
        <div class="section" style="border-color:#3b82f6;">
            <h3>🏛️ بيانات المحافظة (تعداد GASTAT 2022)</h3>
            <div class="gov-stats">
                <div><b>المحافظة:</b> {gi['name']}</div>
                <div><b>سكان المحافظة:</b> {gi['data']['pop']:,}</div>
                <div><b>المساحة:</b> {gi['data']['area']:,} كم²</div>
                <div><b>المنطقة:</b> {gi['data']['region']}</div>
                <div><b>المسافة من المركز:</b> {gi['distance_km']} كم (ثقة: {conf_text})</div>
            </div>
            {local_html}
            <p style="color:#666; font-size:12px; margin-top:10px;">
                ⚠️ التقدير المحلي تقريبي - الكثافة الفعلية قد تختلف. للدقة الكاملة: استبيان ميداني.
            </p>
        </div>
        """

    # أفضل نشاط (لو ما اختار) - مع كيمياء العائلة
    best_act_highlight = ""
    if not a.get('target_cat') and a.get('best_activities'):
        top_act = a['best_activities'][0]
        reasons_text = " • ".join(top_act['reasons'])
        final_score = top_act.get('final_opportunity', top_act['opportunity_score'])
        harmony = top_act.get('harmony_score', 0)
        harmony_level = top_act.get('harmony_level', '-')
        synergies = top_act.get('synergies', [])
        dom_fam = top_act.get('dominant_family')
        
        synergies_html = ""
        if synergies:
            synergies_html = '<div style="margin-top:12px; padding:12px; background:#ecfdf5; border-radius:8px; border-right:3px solid #10b981;">'
            synergies_html += '<div style="color:#047857; font-weight:700; font-size:13px; margin-bottom:6px;">🧪 ترابطات قوية مع المحيط:</div>'
            for syn in synergies[:3]:
                synergies_html += f'<div style="color:#4b5563; font-size:12px; padding:2px 0;">✓ {syn["icon"]} {syn["name"]} ({syn["count"]} محل) — {syn["reason"]}</div>'
            synergies_html += '</div>'
        
        dom_fam_html = ""
        if dom_fam:
            dom_fam_html = f'<p style="color:#3b82f6; font-size:13px; margin-top:6px;">🏆 العائلة الغالبة: <b>{dom_fam["icon"]} {dom_fam["name"]}</b> ({dom_fam["count"]} محل)</p>'
        
        # 🔴 عنوان ديناميكي
        if final_score >= 60:
            pdf_section_title = "🎯 أفضل نشاط مقترح لهذا الموقع"
            pdf_section_subtitle = ""
        elif final_score >= 40:
            pdf_section_title = "⚠️ الأقل مخاطرة (السوق مكتظ نسبياً)"
            pdf_section_subtitle = '<p style="color:#dc2626; font-size:11px;">تحذير: لا توجد فرص قوية، هذا أفضل ما هو متاح</p>'
        else:
            pdf_section_title = "🚨 الأقل مخاطرة (السوق مشبع)"
            pdf_section_subtitle = '<p style="color:#dc2626; font-size:11px;">تحذير: كل الأنشطة عالية المخاطرة - يُنصح بموقع آخر</p>'
        
        best_act_highlight = f"""
        <div class="section" style="border-color:#a855f7; background:rgba(168,85,247,0.05);">
            <div style="color:#7c3aed; font-size:13px; font-weight:600; margin-bottom:6px;">{pdf_section_title}</div>
            {pdf_section_subtitle}
            <h2 style="color:#1f2937;">{top_act['icon']} {top_act['cat_name']} <span style="background:#d1fae5; color:#047857; padding:6px 14px; border-radius:999px; font-size:18px;">{final_score}%</span></h2>
            <p style="margin-top:10px; color:#4b5563;"><b>لماذا هذا النشاط؟</b> {reasons_text}</p>
            <p style="color:#6b7280; font-size:13px; margin-top:6px;">
                🧪 الانسجام مع المحيط: <b style="color:#10b981;">{harmony}% ({harmony_level})</b>
            </p>
            {dom_fam_html}
            {synergies_html}
            <p style="color:#9ca3af; font-size:12px; margin-top:8px;">⚠️ اقتراح مبني على تحليل ترابطات حقيقية - يحتاج تحقق ميداني</p>
        </div>
        """

    # تحليل النشاط المخصص
    custom_act_section = ""
    if a.get('custom_activity_analysis'):
        ca = a['custom_activity_analysis']
        vc = ca.get('verdict_color', '#94a3b8')
        opps = "".join(f"<li>✨ {o}</li>" for o in ca.get('opportunities', []))
        risks = "".join(f"<li>⚠️ {r}</li>" for r in ca.get('risks', []))
        custom_act_section = f"""
        <div class="section" style="border-color:#3b82f6; background:rgba(59,130,246,0.05);">
            <div style="color:#1d4ed8; font-size:13px; font-weight:600; margin-bottom:6px;">✍️ تحليل AI للنشاط المخصص</div>
            <h2 style="color:#1f2937;">"{ca['activity']}" <span style="background:rgba(255,255,255,0.5); color:{vc}; padding:6px 14px; border-radius:999px; font-size:16px;">{ca['verdict']} ({ca.get('score', 50)}/100)</span></h2>
            <p style="margin-top:10px; color:#4b5563; line-height:1.7;"><b>التحليل:</b> {ca['reasoning']}</p>
            <p style="color:#6b7280; font-size:13px; margin-top:6px;">🏪 منافسون مشابهون: <b>{ca.get('similar_competitors', 0)}</b></p>
            {f'<div style="margin-top:10px;"><h4 style="color:#047857;">الفرص:</h4><ul class="point-list good">{opps}</ul></div>' if opps else ''}
            {f'<div style="margin-top:10px;"><h4 style="color:#b45309;">التحذيرات:</h4><ul class="point-list warn">{risks}</ul></div>' if risks else ''}
        </div>
        """

    # المؤشرات الثلاث
    opp = a['opportunity_score']; sat = a['saturation_score']; dem = a['demand_score']
    metrics_section = f"""
    <div class="section">
        <h3>📊 المؤشرات الأساسية</h3>
        <div class="metrics-grid">
            <div class="metric"><div class="metric-icon">🎯</div><div class="metric-label">فرصة الدخول</div><div class="metric-value" style="color:{'#10b981' if opp>=60 else '#f59e0b' if opp>=35 else '#ef4444'};">{opp}%</div></div>
            <div class="metric"><div class="metric-icon">📈</div><div class="metric-label">تشبع السوق</div><div class="metric-value" style="color:{'#ef4444' if sat>=70 else '#f59e0b' if sat>=40 else '#10b981'};">{sat}%</div></div>
            <div class="metric"><div class="metric-icon">🔥</div><div class="metric-label">الطلب المتوقع</div><div class="metric-value" style="color:{'#10b981' if dem>=65 else '#f59e0b' if dem>=40 else '#ef4444'};">{dem}%</div></div>
        </div>
    </div>
    """

    # 🔴 تحليل SWOT حقيقي (PDF)
    swot = a.get('swot', {})
    strengths_html = "".join(f"<li>✓ {s}</li>" for s in swot.get('strengths', a.get('strengths', [])))
    weaknesses_html = "".join(f"<li>⚠ {w}</li>" for w in swot.get('weaknesses', a.get('cautions', [])))
    opportunities_html = "".join(f"<li>💎 {o}</li>" for o in swot.get('opportunities', []))
    threats_html = "".join(f"<li>🚨 {t}</li>" for t in swot.get('threats', []))
    
    points_section = f"""
    <div class="section page-break">
        <h3>⚖️ تحليل SWOT - دراسة شاملة للموقع</h3>
        <p style="color:#6b7280; font-size:13px; margin-bottom:14px;">تحليل مبني على الأرقام الفعلية - يساعدك في اتخاذ القرار</p>
        <table style="width:100%; border-collapse:separate; border-spacing:8px;">
            <tr>
                <td style="background:#ecfdf5; border:1px solid #10b981; border-right:4px solid #10b981; border-radius:10px; padding:12px; vertical-align:top; width:50%;">
                    <h4 style="color:#047857; margin:0 0 8px 0;">✅ نقاط القوة (Strengths)</h4>
                    <ul style="margin:0; padding-right:18px; color:#374151; font-size:13px; line-height:1.7;">{strengths_html}</ul>
                </td>
                <td style="background:#fffbeb; border:1px solid #f59e0b; border-right:4px solid #f59e0b; border-radius:10px; padding:12px; vertical-align:top; width:50%;">
                    <h4 style="color:#92400e; margin:0 0 8px 0;">⚠️ نقاط الضعف (Weaknesses)</h4>
                    <ul style="margin:0; padding-right:18px; color:#374151; font-size:13px; line-height:1.7;">{weaknesses_html}</ul>
                </td>
            </tr>
            <tr>
                <td style="background:#eff6ff; border:1px solid #3b82f6; border-right:4px solid #3b82f6; border-radius:10px; padding:12px; vertical-align:top;">
                    <h4 style="color:#1e40af; margin:0 0 8px 0;">💎 الفرص (Opportunities)</h4>
                    <ul style="margin:0; padding-right:18px; color:#374151; font-size:13px; line-height:1.7;">{opportunities_html}</ul>
                </td>
                <td style="background:#fef2f2; border:1px solid #ef4444; border-right:4px solid #ef4444; border-radius:10px; padding:12px; vertical-align:top;">
                    <h4 style="color:#991b1b; margin:0 0 8px 0;">🚨 التهديدات (Threats)</h4>
                    <ul style="margin:0; padding-right:18px; color:#374151; font-size:13px; line-height:1.7;">{threats_html}</ul>
                </td>
            </tr>
        </table>
    </div>
    """

    # ما يحتاج تحقق ميداني - شفافية كاملة
    needs_section = ""
    if a.get('needs_verification'):
        items_html = "".join(f"<li>🔍 {v}</li>" for v in a['needs_verification'])
        needs_section = f"""
        <div class="section" style="border-color:#f59e0b; background:rgba(245,158,11,0.05);">
            <h3>🔍 ما يحتاج تحقق ميداني (لرفع دقة التحليل)</h3>
            <p style="color:#6b7280; font-size:13px;">هذه البيانات غير متوفرة آلياً وتحتاج جمعاً ميدانياً منك:</p>
            <ul class="point-list warn">{items_html}</ul>
        </div>
        """

    # أفضل الأنشطة - مع كيمياء العائلة
    best_html = ""
    if a.get('best_activities'):
        for i, act in enumerate(a['best_activities'], 1):
            reasons = " • ".join(act['reasons'])
            final_score = act.get('final_opportunity', act['opportunity_score'])
            harmony = act.get('harmony_score', 0)
            harmony_level = act.get('harmony_level', '-')
            harmony_color = act.get('harmony_color', '#94a3b8')
            best_html += f"""<div class="activity-card good">
                <div class="rank">{i}</div>
                <div class="activity-info">
                    <div class="activity-name">{act['icon']} {act['cat_name']}</div>
                    <div class="activity-reason">💡 {reasons}</div>
                    <div class="activity-meta">طلب: {act['demand']}% | منافسين: {act['existing']} | إشباع: {act['saturation']}% | <span style="color:{harmony_color};">🧪 انسجام: {harmony}% ({harmony_level})</span></div>
                </div>
                <div class="activity-score">{final_score}%</div>
            </div>"""
    best_section = f"""<div class="section page-break"><h3>✅ أفضل الأنشطة المقترحة <span style="font-size:12px; color:#9ca3af;">(مدعومة بكيمياء العائلة)</span></h3>{best_html}</div>""" if best_html else ""

    # أسوأ الأنشطة
    worst_html = ""
    if a.get('worst_activities'):
        for act in a['worst_activities']:
            reasons = " • ".join(act['reasons'])
            final_score = act.get('final_opportunity', act['opportunity_score'])
            harmony = act.get('harmony_score', 0)
            harmony_color = act.get('harmony_color', '#94a3b8')
            worst_html += f"""<div class="activity-card bad">
                <div class="rank" style="color:#ef4444;">✗</div>
                <div class="activity-info">
                    <div class="activity-name">{act['icon']} {act['cat_name']}</div>
                    <div class="activity-reason">⚠️ {reasons}</div>
                    <div class="activity-meta">منافسين: {act['existing']} | إشباع: {act['saturation']}% | <span style="color:{harmony_color};">🧪 انسجام: {harmony}%</span></div>
                </div>
                <div class="activity-score bad">{final_score}%</div>
            </div>"""
    worst_section = f"""<div class="section"><h3>🚫 أنشطة عالية المخاطرة</h3>{worst_html}</div>""" if worst_html else ""

    # التحليل المالي
    financial_section = ""
    if a.get('financial'):
        f = a['financial']
        vc_map = {'good': '#10b981', 'ok': '#3b82f6', 'warn': '#f59e0b', 'danger': '#ef4444'}
        vc = vc_map.get(f['verdict_status'], '#94a3b8')

        extras = []
        if f.get('breakeven_daily'):
            extras.append(f"<div class='kpi-small'><div class='kpi-small-label'>نقطة التعادل</div><div class='kpi-small-value'>{f['breakeven_daily']} عميل/يوم</div></div>")
        if f.get('payback_months'):
            extras.append(f"<div class='kpi-small'><div class='kpi-small-label'>استرداد رأس المال</div><div class='kpi-small-value'>{f['payback_months']} شهر</div></div>")
        extras_html = "<div class='kpis-row'>" + "".join(extras) + "</div>" if extras else ""

        financial_section = f"""
        <div class="section page-break">
            <h3>💰 التحليل المالي والجدوى</h3>
            <div class="verdict-box" style="border-color:{vc}; background:rgba(0,0,0,0.05);">
                <h4 style="color:{vc};">{f['verdict']}</h4>
                <p>{f['verdict_detail']}</p>
            </div>
            <div class="metrics-grid">
                <div class="metric"><div class="metric-label">💰 رأس المال المطلوب</div><div class="metric-value">{f['total_capital']:,.0f}</div><div class="metric-sub">ر.س</div></div>
                <div class="metric"><div class="metric-label">📈 الإيرادات الشهرية</div><div class="metric-value" style="color:#10b981;">{f['monthly_revenue']:,.0f}</div><div class="metric-sub">ر.س</div></div>
                <div class="metric"><div class="metric-label">📉 المصاريف الشهرية</div><div class="metric-value" style="color:#ef4444;">{f['monthly_expenses']:,.0f}</div><div class="metric-sub">ر.س</div></div>
                <div class="metric"><div class="metric-label">💵 صافي الربح</div><div class="metric-value" style="color:{'#10b981' if f['net_profit_monthly']>0 else '#ef4444'};">{f['net_profit_monthly']:,.0f}</div><div class="metric-sub">ر.س/شهر</div></div>
            </div>
            {extras_html}
            <p style="margin-top:14px; font-size:12px; color:#9ca3af;">
                ⚠️ بناءً على أرقامك. الافتراضات: راتب موظف 4,000 ر.س، هامش ربح 35-50%، فواتير = مساحة × 8.
            </p>
        </div>
        """

    # DNA الحي
    dna_section = ""
    if a.get('dna'):
        d = a['dna']
        colors = {'family': '#10b981', 'youth': '#a855f7', 'commercial': '#3b82f6', 'food': '#ef4444', 'service': '#f59e0b'}
        labels = {'family': 'عائلي', 'youth': 'شبابي', 'commercial': 'تجاري', 'food': 'طعام', 'service': 'خدماتي'}
        dna_bars = ""
        for k in ['family', 'youth', 'commercial', 'food', 'service']:
            val = d.get(k, 0)
            dna_bars += f"""
            <div class="dna-row">
                <span class="dna-label">{labels[k]}</span>
                <div class="dna-bar"><div class="dna-fill" style="width:{val}%; background:{colors[k]};"></div></div>
                <span class="dna-val" style="color:{colors[k]};">{val}%</span>
            </div>"""
        dna_section = f"""
        <div class="section">
            <h3>🏪 تركيبة المحلات في المحيط <span style="font-size:12px; color:#9ca3af;">(تحليل العرض - وليس الطلب)</span></h3>
            <div class="dna-main">الطابع الأقوى للمحلات الموجودة: <b>{d['main']}</b></div>
            {dna_bars}
            <p style="font-size:12px; color:#9ca3af; margin-top:10px;">
                📊 هذا يصف <b>نوع المحلات الموجودة في المحيط</b> (العرض)، وليس تركيبة سكان الحي (الطلب).
                مثال: حي عائلي قد يكون "تجاري" حسب هذا المؤشر بسبب وجود ورش/خدمات.
            </p>
        </div>
        """

    # المنافسين
    competitors_section = ""
    target = a.get('target_cat')
    if target and a.get('top_competitors'):
        comp_rows = ""
        for i, c in enumerate(a['top_competitors'][:5], 1):
            comp_rows += f"<tr><td>{i}</td><td>{c['name']}</td><td>{c['dist']} كم</td></tr>"
        competitors_section = f"""
        <div class="section">
            <h3>🏆 أعلى المنافسين ({CATEGORIES[target]['name']})</h3>
            <table class="comp-table">
                <thead><tr><th>#</th><th>المنافس</th><th>المسافة</th></tr></thead>
                <tbody>{comp_rows}</tbody>
            </table>
            <p style="font-size:12px; color:#9ca3af; margin-top:10px;">
                ⚠️ تقييمات وعدد المراجعات والقوة الفعلية للمنافسين غير متاحة (تحتاج Google Places API).
            </p>
        </div>
        """

    # الأنشطة في المنطقة - مع علامة اقتطاع البيانات
    activities_section = ""
    if pbc:
        trunc_flags = a.get('truncation_flags', {})
        truncated_count = sum(1 for f in trunc_flags.values() if f)
        rows = ""
        for cat_key, places in sorted(pbc.items(), key=lambda x: -len(x[1])):
            cat = CATEGORIES[cat_key]
            is_trunc = trunc_flags.get(cat_key, False)
            count_str = f"{len(places)}+ محل" if is_trunc else f"{len(places)} محل"
            count_style = ' style="color:#dc2626; font-weight:700;"' if is_trunc else ''
            rows += f"<tr><td>{cat['icon']} {cat['name']}</td><td{count_style}>{count_str}</td></tr>"
        
        truncation_warning = ""
        if truncated_count >= 3:
            truncation_warning = f"""
            <div style="background:#fef2f2; border:1px solid #ef4444; border-radius:8px; padding:10px; margin-bottom:10px;">
                <div style="color:#991b1b; font-size:13px; font-weight:700;">⚠️ بيانات هذه المنطقة مكثّفة</div>
                <div style="color:#7f1d1d; font-size:12px; margin-top:4px;">
                    {truncated_count} فئة قد يكون الواقع فيها أكبر مما يظهر. الأعداد الفعلية قد تكون أعلى.
                </div>
            </div>
            """
        
        activities_section = f"""
        <div class="section">
            <h3>🏪 الأنشطة في المنطقة (إجمالي {a['total_places']}{'+' if truncated_count >= 3 else ''} محل)</h3>
            {truncation_warning}
            <table class="comp-table">
                <thead><tr><th>الفئة</th><th>العدد</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """

    # الخدمات الأساسية الذكية (PDF) - 3 مستويات
    missing_section = ""
    if a.get('essential_analysis') and a['total_places'] >= 5 and not a.get('target_cat'):
        ea = a['essential_analysis']
        tier_colors_pdf = {
            'critical': {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#991b1b'},
            'essential': {'bg': '#fffbeb', 'border': '#f59e0b', 'text': '#92400e'},
            'lifestyle': {'bg': '#f0fdf4', 'border': '#10b981', 'text': '#065f46'},
        }
        tiers_html = ""
        for tier_key in ['critical', 'essential', 'lifestyle']:
            tier = ea[tier_key]
            cdef = tier_colors_pdf[tier_key]
            n_missing = sum(1 for s in tier['services'] if s['status'] == 'missing')
            n_saturated = sum(1 for s in tier['services'] if s['status'] in ('oversaturated', 'high_competition'))
            n_present = sum(1 for s in tier['services'] if s['status'] == 'present')

            svc_rows = ""
            for s in tier['services']:
                if s['status'] == 'missing':
                    icon_s, label = ("❌", "مفقود") if tier_key != 'lifestyle' else ("🎯", "فرصة!")
                    color = "#ef4444" if tier_key in ('critical', 'essential') else "#10b981"
                    detail = "ضروري" if tier_key == 'critical' else ("يومي" if tier_key == 'essential' else "فرصة جديدة")
                elif s['status'] == 'likely_absent':
                    icon_s, label, color, detail = "⚪", "غير مكتشف", "#6b7280", "غير مسجّل - يحتاج تحقق ميداني"
                elif s['status'] == 'truncated_likely_saturated':
                    icon_s, label, color, detail = "🔴", f"{s['count']}+ (مشبع)", "#dc2626", "السوق ممتلئ"
                elif s['status'] == 'oversaturated':
                    icon_s, label, color, detail = "🚫", f"{s['count']} (مشبع)", "#dc2626", f"{s['cp_per_1k']:.1f}/1000"
                elif s['status'] == 'high_competition':
                    icon_s, label, color, detail = "⚠️", f"{s['count']} موجود", "#f59e0b", f"{s['cp_per_1k']:.1f}/1000"
                else:
                    icon_s, label, color, detail = "✅", f"{s['count']} موجود", "#10b981", "متوفر"
                svc_rows += f"""<tr>
<td style="padding:6px; font-size:13px;">{s['icon']} {s['name']}</td>
<td style="padding:6px; color:{color}; font-weight:700; font-size:13px;">{icon_s} {label}</td>
<td style="padding:6px; color:#6b7280; font-size:12px;">{detail}</td>
</tr>"""

            tiers_html += f"""<div style="background:{cdef['bg']}; border:1px solid {cdef['border']}; border-right:4px solid {cdef['border']}; border-radius:10px; padding:14px; margin-bottom:14px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
<div style="color:{cdef['text']}; font-size:15px; font-weight:700;">{tier['icon']} {tier['name']}</div>
<div style="color:#6b7280; font-size:12px;">❌ {n_missing} • ⚠️ {n_saturated} • ✅ {n_present}</div>
</div>
<div style="color:#6b7280; font-size:12px; margin-bottom:8px;">{tier['description']}</div>
<table style="width:100%; border-collapse:collapse;">{svc_rows}</table>
</div>"""

        # ملخص الفرص
        top_opps_pdf = a.get('top_opportunities', [])
        opps_html_pdf = ""
        if top_opps_pdf:
            opp_items = "".join(
                f'<li style="padding:6px 0; font-size:13px;">{op["icon"]} <b>{op["name"]}</b> - {"🚨 احتياج" if op["tier"]=="critical" else "📦 أساسي" if op["tier"]=="essential" else "🎯 كمالي"}</li>'
                for op in top_opps_pdf[:6]
            )
            opps_html_pdf = f"""<div style="background:#f5f3ff; border:1px solid #a855f7; border-radius:10px; padding:14px; margin-top:14px;">
<h4 style="color:#7c3aed; margin-bottom:8px;">💎 أبرز الفرص المتاحة (مفقودة)</h4>
<ul style="list-style:none; padding:0; margin:0;">{opp_items}</ul>
</div>"""

        missing_section = f"""<div class="section page-break">
<h3>🎯 الخدمات في المنطقة - فرص واحتياجات</h3>
<p style="color:#6b7280; font-size:13px; margin-bottom:14px;">تحليل لما هو موجود ومفقود حسب أولوية الاحتياج</p>
{tiers_html}
{opps_html_pdf}
</div>"""
    elif a.get('missing_services') and a.get('target_cat'):
        # نسخة قديمة مختصرة مع تحديد نشاط
        items = "".join(f"<li>⚠️ {s}</li>" for s in a['missing_services'])
        missing_section = f"""<div class="section"><h3>🔍 خدمات أساسية مفقودة</h3><ul class="point-list warn">{items}</ul></div>"""

    # تحليل الصور
    img_section = ""
    if a.get('image_results'):
        img_blocks = ""
        for idx, ir in enumerate(a['image_results'], 1):
            sc = ir.get('overall_score', '-')
            img_blocks += f"""
            <div class="img-block">
                <h4>📷 صورة {idx} — تقييم {sc}/10</h4>
                <p><b>الوصف:</b> {ir.get('area_description', '-')}</p>
                <p><b>الحركة:</b> {ir.get('traffic_level', '-')} | <b>المواقف:</b> {ir.get('parking_availability', '-')} | <b>الحي:</b> {ir.get('neighborhood_type', '-')}</p>
                {f"<p style='color:#10b981;'>✓ {', '.join(ir.get('suitable_activities', []))}</p>" if ir.get('suitable_activities') else ""}
                {f"<p style='color:#f59e0b;'>⚠️ {', '.join(ir.get('concerns', []))}</p>" if ir.get('concerns') else ""}
            </div>
            """
        img_section = f"""<div class="section page-break"><h3>📸 تحليل صور الموقع</h3>{img_blocks}</div>"""

    # تحليل التقرير الميداني
    field_report_section = ""
    if a.get('field_report_analysis'):
        fra = a['field_report_analysis']
        insights = "".join(f"<li>💡 {i}</li>" for i in fra.get('key_insights', []))
        warnings = "".join(f"<li>⚠️ {w}</li>" for w in fra.get('warnings_detected', []))
        opps = "".join(f"<li>✨ {o}</li>" for o in fra.get('opportunities_detected', []))
        field_report_section = f"""
        <div class="section" style="border-color:#a855f7;">
            <h3>📝 تحليل التقرير الميداني (AI)</h3>
            <p style="color:#4b5563;"><b>الملخص:</b> {fra.get('summary', '-')}</p>
            {f'<h4 style="color:#1d4ed8; margin-top:14px;">رؤى رئيسية:</h4><ul class="point-list">{insights}</ul>' if insights else ''}
            {f'<h4 style="color:#047857; margin-top:14px;">فرص مكتشفة:</h4><ul class="point-list good">{opps}</ul>' if opps else ''}
            {f'<h4 style="color:#b45309; margin-top:14px;">تحذيرات مكتشفة:</h4><ul class="point-list warn">{warnings}</ul>' if warnings else ''}
        </div>
        """

    # CSS
    css = """
    <style>
        @media print {
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .no-print { display: none !important; }
            .page-break { page-break-before: always; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            direction: rtl; text-align: right;
            font-family: 'Tahoma', 'Arial', sans-serif;
            background: white; color: #1f2937;
            padding: 30px; line-height: 1.6;
            max-width: 1000px; margin: 0 auto;
        }
        .print-banner {
            position: fixed; top: 0; left: 0; right: 0;
            background: #ef4444; color: white;
            padding: 12px 20px; text-align: center;
            font-weight: bold; z-index: 999;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .print-banner button {
            background: white; color: #ef4444; border: none;
            padding: 8px 24px; border-radius: 8px; margin-right: 12px;
            cursor: pointer; font-weight: bold; font-size: 14px;
        }
        .report-header {
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 4px solid #ef4444; padding-bottom: 20px; margin-bottom: 30px;
            margin-top: 60px;
        }
        .logo { font-size: 42px; font-weight: 900; color: #ef4444; letter-spacing: 2px; }
        .header-info h1 { font-size: 24px; color: #1f2937; margin-bottom: 8px; }
        .meta { display: flex; gap: 16px; color: #6b7280; font-size: 13px; flex-wrap: wrap; }
        .section {
            background: #f9fafb; border: 1px solid #e5e7eb;
            border-radius: 12px; padding: 20px; margin-bottom: 20px;
        }
        .section h3 {
            color: #1f2937; font-size: 18px; margin-bottom: 14px;
            padding-right: 12px; border-right: 4px solid #ef4444;
        }
        .section.verdict {
            border: 3px solid; border-radius: 16px; padding: 24px;
            text-align: center;
        }
        .verdict-label { color: #6b7280; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
        .verdict h2 { font-size: 32px; margin: 8px 0 12px 0; }
        .verdict-score { color: #4b5563; font-size: 14px; margin-bottom: 14px; }
        .verdict-text { color: #374151; font-size: 14px; line-height: 1.8; }
        .gov-stats { display: flex; gap: 20px; flex-wrap: wrap; color: #4b5563; font-size: 13px; }
        .gov-stats > div { padding: 8px 12px; background: white; border-radius: 8px; }
        .metrics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }
        .metric {
            background: white; border: 1px solid #e5e7eb;
            border-radius: 10px; padding: 16px; text-align: center;
        }
        .metric-icon { font-size: 24px; margin-bottom: 4px; }
        .metric-label { color: #6b7280; font-size: 12px; margin-bottom: 6px; }
        .metric-value { font-size: 28px; font-weight: 800; color: #1f2937; }
        .metric-sub { color: #9ca3af; font-size: 11px; margin-top: 2px; }
        .two-col, .three-col { display: grid; gap: 14px; }
        .two-col { grid-template-columns: 1fr 1fr; }
        .three-col { grid-template-columns: 1fr 1fr 1fr; }
        .col { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
        .col h4 { font-size: 14px; margin-bottom: 8px; }
        .point-list { list-style: none; padding: 0; }
        .point-list li { padding: 6px 0; font-size: 13px; color: #374151; }
        .point-list.good li { color: #047857; }
        .point-list.warn li { color: #b45309; }
        .activity-card {
            display: flex; align-items: center; gap: 14px;
            background: white; border: 1px solid #e5e7eb; border-radius: 10px;
            padding: 14px; margin-bottom: 10px;
        }
        .activity-card.good { border-right: 4px solid #10b981; }
        .activity-card.bad { border-right: 4px solid #ef4444; background: #fef2f2; }
        .rank { font-size: 24px; font-weight: 900; color: #f59e0b; min-width: 36px; }
        .activity-info { flex: 1; }
        .activity-name { font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 4px; }
        .activity-reason { color: #6b7280; font-size: 12px; margin-bottom: 4px; }
        .activity-meta { color: #9ca3af; font-size: 11px; }
        .activity-score {
            background: #d1fae5; color: #047857;
            padding: 8px 14px; border-radius: 999px;
            font-weight: 800; font-size: 16px; min-width: 60px; text-align: center;
        }
        .activity-score.bad { background: #fee2e2; color: #b91c1c; }
        .verdict-box { border: 2px solid; border-radius: 10px; padding: 14px; margin-bottom: 14px; }
        .verdict-box h4 { font-size: 18px; margin-bottom: 6px; }
        .verdict-box p { color: #4b5563; font-size: 13px; }
        .kpis-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }
        .kpi-small { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center; }
        .kpi-small-label { color: #6b7280; font-size: 12px; margin-bottom: 4px; }
        .kpi-small-value { font-size: 16px; font-weight: 700; color: #1f2937; }
        .comp-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        .comp-table td, .comp-table th { padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right; font-size: 13px; }
        .comp-table th { background: #f3f4f6; color: #374151; font-weight: 700; }
        .dna-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
        .dna-label { min-width: 70px; color: #374151; font-size: 13px; font-weight: 600; }
        .dna-bar { flex: 1; background: #e5e7eb; border-radius: 6px; height: 10px; overflow: hidden; }
        .dna-fill { height: 100%; border-radius: 6px; }
        .dna-val { min-width: 40px; text-align: left; font-weight: 700; font-size: 13px; }
        .dna-main { color: #4b5563; margin-bottom: 12px; font-size: 14px; }
        .img-block { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin-bottom: 10px; }
        .img-block h4 { font-size: 15px; margin-bottom: 8px; color: #1f2937; }
        .img-block p { color: #4b5563; font-size: 13px; margin-bottom: 4px; }
        .footer {
            margin-top: 40px; padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center; color: #9ca3af; font-size: 12px;
        }
    </style>
    """

    footer = """
    <div class="footer">
        <p>📊 <b>تقرير GBI الاستثماري</b></p>
        <p>⚠️ تحليل أولي - لا يغني عن دراسة جدوى مهنية وزيارة ميدانية</p>
    </div>
    """

    print_banner = """
    <div class="print-banner no-print">
        💡 لحفظ التقرير كـ PDF: اضغط الزر ثم اختر "Save as PDF"
        <button onclick="window.print()">🖨️ اطبع / احفظ PDF</button>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تقرير GBI - {now}</title>
    {css}
</head>
<body>
    {print_banner}
    {header}
    {honesty}
    {decision_section}
    {saturation_warning_pdf}
    {swot_section_pdf}
    {gov_section}
    {best_act_highlight}
    {custom_act_section}
    {metrics_section}
    {best_section}
    {worst_section}
    {financial_section}
    {field_report_section}
    {needs_section}
    {dna_section}
    {competitors_section}
    {activities_section}
    {missing_section}
    {img_section}
    {footer}
</body>
</html>
"""
    return html
# ============================================================================
# [الدفعة 6] Top Bar + الواجهة
# ============================================================================
api_badge = ""  # تم إخفاء بادجات Mapbox/AI من الواجهة (تفاصيل تقنية)

st.markdown(f"""<div class="top-bar">
    <div>
        <div class="brand">📊 GBI</div>
        <div class="brand-sub">الاستثمار الذكي v3</div>
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

# تحذير الصدق في الأعلى
st.markdown("""<div class="honesty-warning">
    <div class="honesty-warning-icon">⚠️</div>
    <div class="honesty-warning-text">
        <b>تنبيه:</b> هذا التحليل أداة استكشاف أولية، <b>وليس دراسة جدوى مهنية</b>. 
        لا يحتوي على تقييمات منافسين فعلية أو حركة عملاء حقيقية. 
        <b>أكمل النموذج التفاعلي أدناه لرفع الثقة، وقم بزيارة ميدانية قبل القرار.</b>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""<div class="page-title">
    <h1>لوحة التحكم</h1>
    <p>أدخل البيانات أعلاه واملأ النموذج التفاعلي لرفع جودة الدراسة</p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# [الدفعة 6] Search Row
# ============================================================================
sc1, sc2, sc3 = st.columns([5, 2, 2])
with sc1:
    url = st.text_input("url", placeholder="📍 أدخل رابط Google Maps أو إحداثيات (lat, lng)...",
                        label_visibility="collapsed", key="url_input")
with sc2:
    radius = st.selectbox("النطاق", [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0], index=2,
                          format_func=lambda x: f"📏 نطاق {x} كم", label_visibility="collapsed")
with sc3:
    analyze_btn = st.button("🚀 بدء التحليل", type="primary", use_container_width=True)


# ============================================================================
# [الدفعة 6] الخيارات المتقدمة + النموذج التفاعلي
# ============================================================================
with st.expander("⚙️ الخيارات المتقدمة - النشاط + البيانات المالية + الصور + مصادر البيانات"):
    tab_act, tab_money, tab_img, tab_sources = st.tabs(["🎯 النشاط المستهدف", "💰 البيانات المالية", "📸 صور الموقع", "🗂️ مصادر البيانات"])

    with tab_act:
        target_options = [("", "🤖 اقترح الأنسب تلقائياً (بناء على تحليل السوق)")]
        for name, cat in ACTIVITY_TYPES.items():
            target_options.append((cat, f"{CATEGORIES[cat]['icon']} {name}"))
        target_options.append(("__custom__", "✍️ نشاط مخصص (اكتبه بنفسي)"))

        target_idx = st.selectbox("target", options=range(len(target_options)),
                                  format_func=lambda i: target_options[i][1],
                                  label_visibility="collapsed", key="target_select")
        selected_target = target_options[target_idx][0]

        custom_activity = ""
        if selected_target == "__custom__":
            custom_activity = st.text_input(
                "اكتب نشاطك التجاري بالتفصيل",
                placeholder="مثال: محل عطور رجالية فاخرة | مشغل خياطة | محل تأجير دراجات...",
                key="custom_activity_input",
            )
            if custom_activity:
                st.info(f"🤖 سيقوم الذكاء الاصطناعي بتحليل '{custom_activity}'")

        st.session_state.target_activity = selected_target if selected_target not in ("", "__custom__") else None
        st.session_state.custom_activity = custom_activity.strip() if selected_target == "__custom__" else ""

        st.caption("💡 اختر من القائمة، أو اكتب نشاطك بالتفصيل، أو اتركه ليقترح النظام الأنسب.")

    with tab_money:
        st.caption("📊 املأ ما تعرفه. الحقول الفارغة تُتجاهل.")
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
        st.caption("📸 ارفع صور للموقع (الواجهة، الشارع، المنطقة)")
        if not AI_AVAILABLE:
            st.warning("⚠️ تحليل الصور يحتاج GEMINI_API_KEY")
        uploaded_images = st.file_uploader("اختر صور", type=['jpg', 'jpeg', 'png'],
                                            accept_multiple_files=True, key="img_upload",
                                            label_visibility="collapsed")
        if uploaded_images:
            st.success(f"✅ {len(uploaded_images)} صورة جاهزة")
        st.session_state.uploaded_images = uploaded_images or []

    # ════════════════════════════════════════════════════════════
    # 🗂️ tab مصادر البيانات
    # ════════════════════════════════════════════════════════════
    with tab_sources:
        st.markdown("""<div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.3); border-radius:12px; padding:14px; margin-bottom:16px;">
<div style="color:#93c5fd; font-weight:600; font-size:14px; margin-bottom:6px;">💡 كيف تعمل مصادر البيانات؟</div>
<div style="color:#cbd5e1; font-size:13px; line-height:1.6;">
أضف مصادر إضافية لـ <b>توسيع نطاق التحليل</b> وزيادة دقته.<br>
كل مصدر يضيف وقت إضافي لكن يكشف محلات أكثر و(أحياناً) تقييمات.
</div>
</div>""", unsafe_allow_html=True)
        
        st.markdown('<div style="color:#86efac; font-size:14px; font-weight:700; margin:14px 0 8px 0;">🆓 مصادر مجانية</div>', unsafe_allow_html=True)
        
        # Mapbox - الافتراضي (مفعّل دائماً)
        st.markdown("""<div style="background:rgba(16,185,129,0.10); border:1px solid #10b981; border-radius:10px; padding:12px; margin-bottom:10px;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div>
<div style="color:white; font-weight:700; font-size:14px;">✅ Mapbox (الأساسي)</div>
<div style="color:#94a3b8; font-size:12px;">مفعّل دائماً • مجاني • ⏱️ ~20-30 ثانية</div>
</div>
<div style="background:rgba(16,185,129,0.2); color:#10b981; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:600;">مفعّل</div>
</div>
</div>""", unsafe_allow_html=True)
        
        # OpenStreetMap (مجاني)
        use_osm = st.checkbox(
            "🗺️ **OpenStreetMap (Overpass)** - يكشف محلات إضافية لم يجدها Mapbox",
            value=False,
            key="use_osm",
            help="مجاني تماماً • لا يحتاج API key • قد يضيف 15-30% محلات إضافية • ⏱️ +20-40 ثانية"
        )
        if use_osm:
            st.caption("✅ سيتم الاستعلام من OpenStreetMap Overpass API")
        
        # Foursquare (مجاني مع API key)
        st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
        fsq_api_key = st.text_input(
            "🔑 Foursquare API Key (اختياري)",
            value="",
            type="password",
            key="fsq_api_key",
            help="مجاني حتى 1000 طلب/يوم • يضيف تقييمات لبعض المحلات • سجل في: foursquare.com/developers"
        )
        use_foursquare = bool(fsq_api_key.strip())
        if use_foursquare:
            st.caption("✅ Foursquare API key موجود - سيتم استخدامه")
        else:
            st.caption("⚪ Foursquare غير مفعّل (يحتاج API key مجاني)")
        
        st.markdown('<div style="color:#fbbf24; font-size:14px; font-weight:700; margin:20px 0 8px 0;">💰 مصادر مدفوعة (للتقييمات الكاملة من Google)</div>', unsafe_allow_html=True)
        
        # Outscraper
        outscraper_api_key = st.text_input(
            "🔑 Outscraper API Key (اختياري - مدفوع)",
            value="",
            type="password",
            key="outscraper_api_key",
            help="$3-5 لكل 1000 طلب • تقييمات Google كاملة + مراجعات • سجل في: outscraper.com"
        )
        use_outscraper = bool(outscraper_api_key.strip())
        if use_outscraper:
            st.caption("✅ Outscraper API key موجود - سيُستخدم لتعزيز تقييمات النشاط المختار (~$0.05/تحليل)")
        else:
            st.caption("⚪ Outscraper غير مفعّل (يحتاج اشتراك مدفوع)")
        
        # Apify
        apify_api_key = st.text_input(
            "🔑 Apify API Token (اختياري - $5 رصيد مجاني)",
            value="",
            type="password",
            key="apify_api_key",
            help="$5 رصيد شهري مجاني • Google Maps Scraper • سجل في: apify.com"
        )
        use_apify = bool(apify_api_key.strip())
        if use_apify:
            st.caption("✅ Apify token موجود - سيُستخدم كخيار ثانوي للتقييمات")
        else:
            st.caption("⚪ Apify غير مفعّل")
        
        # ملخص المصادر المختارة + الوقت المتوقع
        active_count = 1  # Mapbox
        time_estimate = 30  # base
        if use_osm:
            active_count += 1
            time_estimate += 30
        if use_foursquare:
            active_count += 1
            time_estimate += 15
        if use_outscraper:
            active_count += 1
            time_estimate += 45
        if use_apify:
            active_count += 1
            time_estimate += 30
        
        st.markdown(f"""<div style="background:rgba(168,85,247,0.08); border:1px solid #a855f7; border-radius:10px; padding:14px; margin-top:16px;">
<div style="color:#c4b5fd; font-size:13px; font-weight:600;">📊 ملخص الإعدادات</div>
<div style="color:#cbd5e1; font-size:13px; margin-top:6px; line-height:1.8;">
🗂️ المصادر المفعّلة: <b style="color:white;">{active_count}</b><br>
⏱️ الوقت المتوقع: <b style="color:white;">~{time_estimate} ثانية</b><br>
💡 <span style="color:#94a3b8; font-size:12px;">أكثر المصادر = أدق التحليل (لكن أبطأ)</span>
</div>
</div>""", unsafe_allow_html=True)
        
        # نخزن في session_state
        st.session_state['data_sources'] = {
            'mapbox': True,
            'osm': use_osm,
            'foursquare': use_foursquare,
            'foursquare_key': fsq_api_key.strip() if fsq_api_key else '',
            'outscraper': use_outscraper,
            'outscraper_key': outscraper_api_key.strip() if outscraper_api_key else '',
            'apify': use_apify,
            'apify_key': apify_api_key.strip() if apify_api_key else '',
        }


# ============================================================================
# [الدفعة 6] النموذج التفاعلي الكبير (يرفع جودة الدراسة)
# ============================================================================
with st.expander("📋 ارفع جودة الدراسة - أدخل ما تعرفه عن الموقع ميدانياً (مهم جداً)"):
    st.markdown("""<div style="background:rgba(168,85,247,0.08); border:1px solid rgba(168,85,247,0.3); border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="color:#c4b5fd; font-weight:600; font-size:14px; margin-bottom:6px;">💡 لماذا هذا النموذج؟</div>
        <div style="color:#94a3b8; font-size:13px; line-height:1.6;">
            <b>أنت تعرف الموقع أكثر</b> من أي تحليل آلي.
            كل سؤال تجيب عليه يرفع دقة التحليل من 35% إلى 70%.
            <br>كل الحقول <b>اختيارية</b> - أجب على ما تعرفه فقط.
        </div>
    </div>
    """, unsafe_allow_html=True)

    field_tabs = st.tabs([
        "🚶 المشاهدات الميدانية",
        "🏢 المنافسين",
        "💰 السوق المالي",
        "🎯 تفاصيل النشاط",
        "📝 تقرير ميداني نصي"
    ])

    # ============== المشاهدات الميدانية ==============
    with field_tabs[0]:
        st.markdown('<div class="field-section-sub">معلومات من زيارتك للموقع - تساعد على تأكيد الحركة الفعلية</div>',
                    unsafe_allow_html=True)
        mc1, mc2 = st.columns(2)
        with mc1:
            site_visits = st.radio(
                "🚶 كم مرة زرت الموقع؟",
                ["لم أزره بعد", "مرة واحدة", "2-3 مرات", "4 مرات أو أكثر"],
                key="fld_visits", horizontal=False)
            visit_times = st.radio(
                "⏰ في أي أوقات زرته؟",
                ["لم أزره", "صباحاً فقط", "مساءً فقط", "صباحاً + مساءً", "كل الأوقات"],
                key="fld_visit_times")
            foot_traffic_level = st.radio(
                "👥 كثافة المارّة (مشاة + سيارات) في الذروة",
                ["لا أعرف", "ضعيف", "متوسط", "قوي"],
                key="fld_foot_traffic")
        with mc2:
            people_counted = st.number_input(
                "🔢 لو عددت المارّة في 30 دقيقة - كم العدد؟ (اتركه 0 لو ما عددت)",
                min_value=0, value=0, step=5, key="fld_people_count")
            pedestrians = st.radio(
                "🚶‍♂️ نسبة المشاة مقابل السيارات",
                ["لا أعرف", "أغلبهم سيارات", "متوازن", "أغلبهم مشاة"],
                key="fld_pedestrians")
            parking_actual = st.radio(
                "🅿️ توفر المواقف فعلياً",
                ["لا أعرف", "شحيحة جداً", "محدودة", "كافية", "وفيرة"],
                key="fld_parking")

        mc3, mc4 = st.columns(2)
        with mc3:
            visibility = st.radio(
                "👀 ظهور الموقع من الشارع الرئيسي",
                ["لا أعرف", "غير واضح", "متوسط", "بارز جداً"],
                key="fld_visibility")
            facade_quality = st.radio(
                "🏪 جودة واجهة المحل المتاحة",
                ["لا أعرف", "تحتاج تجهيز كامل", "متوسطة", "جيدة"],
                key="fld_facade")
        with mc4:
            street_type = st.radio(
                "🛣️ نوع الشارع",
                ["لا أعرف", "فرعي ضيق", "فرعي عادي", "رئيسي ثنائي", "شارع تجاري رئيسي"],
                key="fld_street")
            future_projects = st.radio(
                "🏗️ هل تعرف عن مشاريع تطوير قادمة؟",
                ["لا أعرف", "لا يوجد", "مشاريع صغيرة", "مشاريع كبيرة"],
                key="fld_future")

    # ============== المنافسين ==============
    with field_tabs[1]:
        st.markdown('<div class="field-section-sub">معرفتك بالمنافسين تساعد في تقدير الخطر الفعلي</div>',
                    unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            comp_visible = st.number_input(
                "🏪 كم منافس شفته فعلياً مفتوح في المنطقة؟",
                min_value=0, value=0, step=1, key="fld_comp_visible")
            comp_strength = st.radio(
                "💪 قوة المنافسين الموجودين",
                ["لا أعرف", "ضعيف (أغلبهم محلات صغيرة)", "متوسط", "قوي (علامات معروفة)"],
                key="fld_comp_strength")
            comp_prices = st.radio(
                "💵 مستوى أسعار المنافسين",
                ["لا أعرف", "منخفض", "متوسط", "مرتفع", "متنوع"],
                key="fld_comp_prices")
        with cc2:
            top_competitor_name = st.text_input(
                "🏆 أقوى منافس حسب رأيك (الاسم)",
                placeholder="مثال: Coffee F9", key="fld_top_comp")
            comp_traffic = st.radio(
                "👥 كثافة العملاء عند المنافسين",
                ["لا أعرف", "هادئة", "متوسطة", "ممتلئة دائماً"],
                key="fld_comp_traffic")
            comp_weaknesses = st.text_area(
                "🔍 نقاط ضعف المنافسين التي لاحظتها",
                placeholder="مثال: خدمة بطيئة، أسعار مرتفعة، ساعات عمل محدودة...",
                key="fld_comp_weak", height=80)

    # ============== السوق المالي ==============
    with field_tabs[2]:
        st.markdown('<div class="field-section-sub">معلومات فعلية عن أسعار السوق</div>',
                    unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        with sc1:
            rent_market = st.radio(
                "🏠 مستوى الإيجارات في الحي",
                ["لا أعرف", "منخفض", "متوسط", "مرتفع", "مرتفع جداً"],
                key="fld_rent_market")
            actual_rent_known = st.number_input(
                "💰 لو تواصلت مع المالك - كم الإيجار السنوي؟ (ر.س)",
                min_value=0, value=0, step=5000, key="fld_actual_rent")
            setup_estimate = st.radio(
                "🏗️ تقدير تكلفة التجهيز",
                ["لم أحسب", "بسيط (<50 ألف)", "متوسط (50-150 ألف)", "كبير (150-500 ألف)", "ضخم (>500 ألف)"],
                key="fld_setup_est")
        with sc2:
            local_costs = st.radio(
                "💵 تكاليف التشغيل في الحي مقارنة بمدن أخرى",
                ["لا أعرف", "أقل من المعتاد", "معتاد", "أعلى من المعتاد"],
                key="fld_local_costs")
            avg_local_income = st.radio(
                "💸 مستوى الدخل المتوقع لسكان الحي",
                ["لا أعرف", "منخفض", "متوسط", "مرتفع", "مرتفع جداً"],
                key="fld_income")
            spending_power = st.radio(
                "🛒 القدرة الشرائية في النشاط المستهدف",
                ["لا أعرف", "ضعيفة", "متوسطة", "قوية"],
                key="fld_spending")

    # ============== تفاصيل النشاط ==============
    with field_tabs[3]:
        st.markdown('<div class="field-section-sub">معلومات عن نشاطك الشخصي</div>',
                    unsafe_allow_html=True)
        nc1, nc2 = st.columns(2)
        with nc1:
            target_audience = st.radio(
                "🎯 الفئة المستهدفة",
                ["لم أحدد", "شباب 15-30", "عائلات", "موظفون", "كبار السن", "متنوعة"],
                key="fld_audience")
            experience_level = st.radio(
                "📚 خبرتك في النشاط",
                ["لا خبرة", "خبرة محدودة", "خبرة جيدة", "خبرة واسعة"],
                key="fld_experience")
            competitive_advantage = st.text_area(
                "✨ ميزتك التنافسية (ما يميّزك عن المنافسين)",
                placeholder="مثال: منتج عضوي 100%، خدمة 24 ساعة، أسعار أقل بـ20%...",
                key="fld_advantage", height=80)
        with nc2:
            available_capital = st.radio(
                "💼 رأس المال المتاح",
                ["لم أحدد", "أقل من 50 ألف", "50-150 ألف", "150-500 ألف", "أكثر من 500 ألف"],
                key="fld_capital")
            backup_capital = st.radio(
                "💰 احتياطي مالي لـ 6 شهور",
                ["لا يوجد", "احتياطي محدود", "احتياطي كافٍ", "احتياطي ممتاز"],
                key="fld_backup")
            marketing_plan = st.radio(
                "📣 خطة التسويق",
                ["لا توجد", "بسيطة (سوشال ميديا)", "متوسطة", "احترافية"],
                key="fld_marketing")

    # ============== التقرير الميداني النصي ==============
    with field_tabs[4]:
        st.markdown("""<div class="field-section-sub">
        اكتب وصفاً نصياً للموقع (200-500 كلمة).
        كل ما لاحظته من زيارتك: الحركة، المنافسة، الفرص، التحديات.
        <b>AI سيحلل النص ويستخرج منه رؤى تُضاف للتحليل.</b>
        </div>
        """, unsafe_allow_html=True)

        field_report = st.text_area(
            "📝 تقرير ميداني (نص حر)",
            placeholder="""مثال:
زرت الموقع 3 مرات في أوقات مختلفة. لاحظت أن الحركة في المساء أعلى بكثير من الصباح.
يوجد مقهيين قريبين لكن واحد منهم خدمته بطيئة.
الشارع رئيسي والمواقف كافية. هناك مشروع تجاري قادم على بُعد 200 متر.
الفئة الغالبة شباب، والقدرة الشرائية تبدو متوسطة...""",
            key="fld_report_text", height=200)
        if field_report and AI_AVAILABLE:
            st.info(f"🤖 AI سيحلل تقريرك ({len(field_report.split())} كلمة) ويستخرج رؤى مفيدة.")

    # حفظ كل البيانات الميدانية
    st.session_state.field_inputs = {
        'site_visits': site_visits,
        'visit_times': visit_times,
        'foot_traffic_level': foot_traffic_level if foot_traffic_level != "لا أعرف" else "",
        'people_counted': people_counted,
        'pedestrians': pedestrians,
        'parking_actual': parking_actual,
        'visibility': visibility,
        'facade_quality': facade_quality,
        'street_type': street_type,
        'future_projects': future_projects,
        'comp_visible': comp_visible,
        'comp_strength': comp_strength,
        'comp_prices': comp_prices,
        'top_competitor_name': top_competitor_name,
        'comp_traffic': comp_traffic,
        'comp_weaknesses': comp_weaknesses,
        'rent_market': rent_market,
        'actual_rent_known': actual_rent_known,
        'setup_estimate': setup_estimate,
        'local_costs': local_costs,
        'avg_local_income': avg_local_income,
        'spending_power': spending_power,
        'target_audience': target_audience,
        'experience_level': experience_level,
        'competitive_advantage': competitive_advantage,
        'available_capital': available_capital,
        'backup_capital': backup_capital,
        'marketing_plan': marketing_plan,
        'field_report_text': field_report,
    }

    # مؤشر اكتمال الدراسة
    filled = sum(1 for v in st.session_state.field_inputs.values()
                 if v and str(v) not in ["", "لا أعرف", "لم أحدد", "لم أزره بعد", "لا توجد", "لا يوجد", "0", "لم أحسب", "لا خبرة"])
    total_fields = len(st.session_state.field_inputs)
    completion_pct = int((filled / total_fields) * 100) if total_fields else 0
    
    st.markdown(f"""<div class="completion-bar">
        <div class="completion-title">
            📊 اكتمال البيانات الميدانية: <b>{completion_pct}%</b> ({filled}/{total_fields} حقل)
        </div>
        <div class="completion-fill">
            <div class="completion-fill-inner" style="width:{completion_pct}%;"></div>
        </div>
        <div style="color:#94a3b8; font-size:12px; margin-top:8px;">
            💡 كلما زادت البيانات الميدانية، ارتفعت ثقة التحليل (سقف +25%)
        </div>
    </div>
    """, unsafe_allow_html=True)
# ============================================================================
# [الدفعة 7] محرّك التحليل - عند ضغط الزر
# ============================================================================
if analyze_btn:
    if not MAPBOX:
        st.error("❌ MAPBOX_TOKEN غير موجود. أضفه في secrets ثم أعد المحاولة.")
        st.stop()
    if not url:
        st.warning("⚠️ أدخل رابط أو إحداثيات الموقع.")
        st.stop()

    lat, lng = extract_coords(url)
    if not (lat and lng):
        st.error("❌ تعذّر استخراج الإحداثيات. تأكد من صحة الرابط.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    status.markdown('<p class="progress-msg">🔍 5% - استخراج الإحداثيات...</p>', unsafe_allow_html=True)
    progress.progress(5)

    # تحديد المحافظة
    status.markdown('<p class="progress-msg">🏛️ 12% - تحديد المحافظة...</p>', unsafe_allow_html=True)
    progress.progress(12)
    gov_info = find_governorate_by_coords(lat, lng)

    # المسح الشامل من المصادر المختارة
    sources = st.session_state.get('data_sources', {'mapbox': True})
    
    def _progress_update(msg, pct):
        try:
            status.markdown(f'<p class="progress-msg">{msg}</p>', unsafe_allow_html=True)
            progress.progress(pct)
        except Exception:
            pass
    
    _progress_update("🌐 25% - بدء مسح المحلات...", 25)
    pbc, truncation_flags, source_stats = comprehensive_scan(lat, lng, radius, sources=sources, progress_callback=_progress_update)
    if not pbc:
        progress.empty(); status.empty()
        st.warning("⚠️ لم نعثر على محلات في النطاق المحدد. جرّب نطاقاً أوسع.")
        st.stop()
    
    # نخزن truncation_flags و source_stats في session للاستخدام لاحقاً
    st.session_state.truncation_flags = truncation_flags
    st.session_state.source_stats = source_stats

    # 🛣️ تحليل نوع الشارع (رئيسي/ثانوي/فرعي) — يؤثر على الفرصة
    status.markdown('<p class="progress-msg">🛣️ 52% - تحليل نوع الشارع...</p>', unsafe_allow_html=True)
    progress.progress(52)
    try:
        street_info = analyze_street_type(lat, lng)
    except Exception:
        street_info = {
            'category': 'غير معروف', 'name': '', 'highway': '',
            'opportunity_modifier': 0, 'nearby': [], 'confidence': 'منخفضة',
            'explanation': 'تعذّر تحديد نوع الشارع.',
        }
    st.session_state.street_info = street_info

    status.markdown('<p class="progress-msg">📊 55% - تحليل البيانات...</p>', unsafe_allow_html=True)
    progress.progress(55)

    # هل توجد بيانات ميدانية مفيدة؟
    fi = st.session_state.field_inputs
    has_field_data = bool(
        (fi.get('site_visits') and fi.get('site_visits') != 'لم أزره بعد') or
        fi.get('foot_traffic_level') or
        fi.get('comp_visible', 0) > 0 or
        fi.get('actual_rent_known', 0) > 0 or
        fi.get('field_report_text', '').strip()
    )

    a = analyze(pbc, radius, target_cat=st.session_state.target_activity, gov_info=gov_info, field_data=fi)
    a['dna'] = neighborhood_dna(pbc)
    # 🔴 إضافة truncation_flags للوصول لها في العرض والـ PDF
    a['truncation_flags'] = truncation_flags

    # 🛣️ دمج تأثير نوع الشارع في النقاط
    a['street_info'] = street_info
    street_mod = street_info.get('opportunity_modifier', 0)
    if street_mod:
        base_inv = a.get('investment_score', 0)
        base_opp = a.get('opportunity_score', 0)
        # الشارع يعدّل النقاط نسبياً (سقف ±20%)
        a['investment_score'] = int(max(0, min(100, base_inv + base_inv * street_mod / 100)))
        a['opportunity_score'] = int(max(0, min(100, base_opp + base_opp * street_mod / 100)))
        a['street_score_effect'] = {
            'investment_before': base_inv,
            'investment_after': a['investment_score'],
            'opportunity_before': base_opp,
            'opportunity_after': a['opportunity_score'],
            'modifier': street_mod,
        }

    status.markdown('<p class="progress-msg">🎯 65% - تصنيف الأنشطة...</p>', unsafe_allow_html=True)
    progress.progress(65)
    best, worst, all_ranked = rank_all_activities(pbc, a['dna'], a['traffic_score'], a['pop_score'], a['accessibility_score'], field_data=fi, local_population=a.get('local_population'), truncation_flags=truncation_flags)
    a['best_activities'] = best
    a['worst_activities'] = worst
    a['all_ranked_activities'] = all_ranked

    # التحليل المالي (إن وجدت أرقام)
    fin_in = st.session_state.fin_inputs
    # نشغّل التحليل المالي إذا: المستخدم أدخل أرقام، أو حدد نشاطاً (لاستخدام benchmarks)
    if any(fin_in.values()) or st.session_state.target_activity:
        status.markdown('<p class="progress-msg">💰 75% - تحليل مالي (مع benchmarks)...</p>', unsafe_allow_html=True)
        progress.progress(75)
        # نحدد عدد المنافسين الحاليين للنشاط المستهدف
        comp_count = 0
        if st.session_state.target_activity:
            comp_count = len(pbc.get(st.session_state.target_activity, []))
        a['financial'] = financial_analysis(
            rent_yearly=fin_in.get('rent_yearly', 0),
            setup_cost=fin_in.get('setup_cost', 0),
            area_sqm=fin_in.get('area_sqm', 0) or 80,  # افتراضي 80 م²
            employees=fin_in.get('employees', 0) or 2,  # افتراضي 2 موظف
            avg_ticket=fin_in.get('avg_ticket', 0),
            daily_customers=fin_in.get('daily_customers', 0),
            target_cat=st.session_state.target_activity,
            total_places=a['total_places'],
            traffic_score=a.get('traffic_score', 50),
            area_character=a.get('area_character', 'سكني محدود'),
            competitors_count=comp_count,
        )

    # تحليل الصور
    if st.session_state.uploaded_images and AI_AVAILABLE:
        status.markdown(f'<p class="progress-msg">📸 82% - تحليل {len(st.session_state.uploaded_images)} صورة...</p>',
                        unsafe_allow_html=True)
        progress.progress(82)
        image_results = []
        ctx = f"الموقع: {lat:.4f}, {lng:.4f}، النطاق {radius} كم"
        if gov_info:
            ctx += f"، المحافظة: {gov_info['name']}"
        for img_file in st.session_state.uploaded_images:
            try:
                img = Image.open(img_file)
                result = analyze_image_with_ai(img, ctx)
                if result:
                    image_results.append(result)
            except Exception:
                pass
        if image_results:
            a = integrate_image_analysis(image_results, a)

    # AI enhancement
    if AI_AVAILABLE:
        status.markdown('<p class="progress-msg">✨ 88% - معالجة التحليل النهائي...</p>', unsafe_allow_html=True)
        progress.progress(88)
        a = ai_enhance(a, pbc, lat, lng)

    # تحليل النشاط المخصص
    custom_act = st.session_state.get('custom_activity', '').strip()
    if custom_act:
        status.markdown(f'<p class="progress-msg">✍️ 92% - معالجة نشاطك المخصص...</p>',
                        unsafe_allow_html=True)
        progress.progress(92)
        a['custom_activity_analysis'] = analyze_custom_activity(custom_act, a, pbc, lat, lng)

    # تحليل التقرير الميداني النصي
    field_report_text = fi.get('field_report_text', '').strip()
    if field_report_text and AI_AVAILABLE and len(field_report_text.split()) >= 20:
        status.markdown('<p class="progress-msg">📝 96% - تحليل تقريرك الميداني...</p>',
                        unsafe_allow_html=True)
        progress.progress(96)
        fra = analyze_field_report(field_report_text, a, pbc, lat, lng)
        if fra:
            a['field_report_analysis'] = fra

    # حساب الثقة النهائية
    a['confidence'] = confidence_score(
        pbc, a['total_places'], radius,
        has_field_data=has_field_data,
        has_gov_data=bool(gov_info)
    )

    st.session_state.analysis = {
        'lat': lat, 'lng': lng, 'radius': radius,
        'places_by_cat': pbc, 'analysis': a
    }
    st.session_state.chat = []

    status.markdown('<p class="progress-msg">✅ 100% - اكتمل التحليل!</p>', unsafe_allow_html=True)
    progress.progress(100)
    time.sleep(0.4)
    progress.empty(); status.empty()
    st.rerun()


# ============================================================================
# [الدفعة 7] عرض النتائج
# ============================================================================
if not st.session_state.analysis:
    # رسالة ترحيب
    st.markdown("""<div style="text-align:center; padding:60px 20px; background:#131826; border-radius:18px; margin-top:20px; border:1px solid #1f2937;">
        <div style="font-size:64px; margin-bottom:16px;">📊</div>
        <h2 style="color:white; margin-bottom:12px;">ابدأ تحليلك الآن</h2>
        <p style="color:#94a3b8; font-size:15px; max-width:600px; margin:0 auto; line-height:1.7;">
            أدخل رابط Google Maps أو إحداثيات الموقع في الأعلى.<br>
            <b style="color:#fbbf24;">لرفع جودة التحليل: املأ النموذج التفاعلي ببياناتك الميدانية.</b>
        </p>
        <div style="margin-top:24px; display:flex; gap:14px; justify-content:center; flex-wrap:wrap;">
            <div style="background:#1f2937; padding:10px 18px; border-radius:999px; color:#cbd5e1; font-size:13px;">
                ✓ تحليل 134 محافظة
            </div>
            <div style="background:#1f2937; padding:10px 18px; border-radius:999px; color:#cbd5e1; font-size:13px;">
                ✓ 33 نوع نشاط
            </div>
            <div style="background:#1f2937; padding:10px 18px; border-radius:999px; color:#cbd5e1; font-size:13px;">
                ✓ بيانات السكان الرسمية
            </div>
            <div style="background:#1f2937; padding:10px 18px; border-radius:999px; color:#cbd5e1; font-size:13px;">
                ✓ تحليل تفاعلي
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    data = st.session_state.analysis
    a = data['analysis']
    pbc = data['places_by_cat']
    lat, lng = data['lat'], data['lng']
    radius = data['radius']
    conf = a.get('confidence', {})

    # ═══════════════════════════════════════════════════════
    # 🎯 القرار النهائي
    # ═══════════════════════════════════════════════════════
    # تحذير: البيانات مقصوصة
    if a.get('data_is_truncated'):
        sev = a.get('truncation_severity', 'moderate')
        n_at_limit = a.get('categories_at_limit', 0)
        if sev == "severe":
            st.markdown(f"""<div style="background:rgba(239,68,68,0.12); border:2px solid #ef4444; border-radius:14px; padding:16px; margin-bottom:14px;">
<div style="color:#fca5a5; font-size:15px; font-weight:700; margin-bottom:8px;">🚨 منطقة مكتظة جداً</div>
<div style="color:#cbd5e1; font-size:13px; line-height:1.7;">
<b>{n_at_limit} فئة</b> تحتوي على عدد كبير جداً من المحلات. الواقع: <b>المنطقة بها مئات المحلات حقيقياً</b>.<br>
<b>⚠️ ما يعنيه هذا لقرارك:</b><br>
• الإشباع الفعلي أعلى مما يظهر<br>
• "فرصة" قد تعني <b>غياب طلب</b> (وليس فرصة حقيقية)<br>
• ينصح بـ <b>نطاق أصغر</b> (1-2 كم) لدقة أفضل
</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:rgba(245,158,11,0.10); border:1px solid #f59e0b; border-radius:12px; padding:14px; margin-bottom:14px;">
<div style="color:#fbbf24; font-size:14px; font-weight:600;">⚠️ تنبيه: {n_at_limit} فئة قد يكون فيها محلات أكثر مما يظهر</div>
<div style="color:#cbd5e1; font-size:13px; margin-top:6px;">
الأرقام قد تكون أقل من الواقع. للدقة الأعلى، جرّب نطاق أصغر.
</div>
</div>""", unsafe_allow_html=True)
    
    decision_text = a.get('ai_recommendation') if a.get('ai_enhanced') else a['decision_summary']
    target_cat_name = ""
    if a.get('target_cat'):
        target_cat_name = f' • النشاط: {CATEGORIES[a["target_cat"]]["icon"]} {CATEGORIES[a["target_cat"]]["name"]}'

    # 🔴 بانر علوي مختصر فقط - القرار الكامل في الأسفل
    teaser_banner = f"""<div style="background:linear-gradient(90deg, {a['decision_bg']} 0%, transparent 100%); border-right:4px solid {a['decision_color']}; padding:14px 18px; border-radius:12px; margin-bottom:18px;">
        <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
            <div style="font-size:28px;">{a['decision_emoji']}</div>
            <div style="flex:1;">
                <div style="color:{a['decision_color']}; font-size:18px; font-weight:800;">{a['decision']}</div>
                <div style="color:#94a3b8; font-size:12px;">📍 {lat:.4f}, {lng:.4f} • {radius} كم • {a['total_places']} محل • {a.get('area_character', '-')}</div>
            </div>
            <div style="color:#94a3b8; font-size:11px; text-align:left;">⬇️ اقرأ التحليل التفصيلي<br>للقرار الكامل في الأسفل</div>
        </div>
    </div>"""
    st.markdown(teaser_banner, unsafe_allow_html=True)
    
    # 🔴 ملخص المصادر المستخدمة (إذا أكثر من Mapbox)
    source_stats = st.session_state.get('source_stats', {})
    sources_used = source_stats.get('sources_used', [])
    if len(sources_used) > 1:
        source_badges = []
        if 'mapbox' in sources_used:
            source_badges.append(f"<span style='background:rgba(59,130,246,0.15); color:#93c5fd; padding:4px 10px; border-radius:999px; font-size:12px;'>🟦 Mapbox: {source_stats.get('mapbox_total', 0)} محل</span>")
        if 'osm' in sources_used:
            source_badges.append(f"<span style='background:rgba(16,185,129,0.15); color:#86efac; padding:4px 10px; border-radius:999px; font-size:12px;'>🗺️ OSM: +{source_stats.get('osm_total', 0)} محل</span>")
        if 'foursquare' in sources_used:
            source_badges.append(f"<span style='background:rgba(245,158,11,0.15); color:#fcd34d; padding:4px 10px; border-radius:999px; font-size:12px;'>🟨 Foursquare: +{source_stats.get('foursquare_total', 0)} محل</span>")
        
        st.markdown(f"""<div style="background:rgba(168,85,247,0.06); border:1px solid rgba(168,85,247,0.2); border-radius:10px; padding:10px 14px; margin-bottom:14px;">
<div style="color:#c4b5fd; font-size:12px; font-weight:600; margin-bottom:6px;">📊 المصادر المستخدمة (دمج)</div>
<div style="display:flex; gap:8px; flex-wrap:wrap;">
{''.join(source_badges)}
</div>
</div>""", unsafe_allow_html=True)
    
    # نخزن القرار الكامل لعرضه في الأسفل
    full_decision_card = f"""
    <div class="verdict-card" style="border-color:{a['decision_color']}; background:linear-gradient(135deg, {a['decision_bg']} 0%, #131826 100%);">
        <div class="verdict-header">
            <div>
                <div style="color:#94a3b8; font-size:13px; font-weight:600;">🎯 القرار النهائي</div>
                <div class="verdict-title" style="color:{a['decision_color']};">{a['decision_emoji']} {a['decision']}</div>
                <div class="verdict-score">نقاط الاستثمار: <b style="color:white;">{a['investment_score']}/100</b>
                    &nbsp;|&nbsp; ثقة التحليل: <b style="color:{conf.get('color', '#94a3b8')};">{conf.get('score', 0)}% ({conf.get('level', '-')})</b>
                </div>
            </div>
            <div class="verdict-emoji">{a['decision_emoji']}</div>
        </div>
        <div class="verdict-reason">{esc(decision_text)}</div>
        <div class="verdict-tags">
            <div class="verdict-tag">📍 {lat:.4f}, {lng:.4f}</div>
            <div class="verdict-tag">📏 {radius} كم</div>
            <div class="verdict-tag">🏪 {a['total_places']} محل</div>
            <div class="verdict-tag">🌆 {a['area_type']}</div>"""
    if a.get('target_cat'):
        full_decision_card += f'<div class="verdict-tag">{target_cat_name.replace(" • النشاط:", "🎯")}</div>'
    if a.get('gov_info'):
        full_decision_card += f'<div class="verdict-tag">🏛️ {a["gov_info"]["name"]}</div>'
    full_decision_card += "</div></div>"
    # نخزن للعرض في الأسفل
    st.session_state['_full_decision_card_html'] = full_decision_card

    # ═══════════════════════════════════════════════════════
    # 🚨 بانر تحذيرات السوق الموحّد (مرة واحدة - لا تكرار في كل نشاط)
    # ═══════════════════════════════════════════════════════
    trunc_flags = a.get('truncation_flags', {})
    truncated_count = sum(1 for f in trunc_flags.values() if f)
    
    # حساب الفئات المشبعة بشدة
    heavy_sat = 0
    if a.get('local_population') and a['local_population'] > 0:
        for ck, places in pbc.items():
            count = len(places)
            effective = int(count * 2.5) if trunc_flags.get(ck) else count
            if effective >= 5:
                cp1k = (effective * 1000) / a['local_population']
                if cp1k > 3.5:
                    heavy_sat += 1
    
    if truncated_count >= 5 or heavy_sat >= 5:
        warnings_html = ""
        if truncated_count >= 5:
            warnings_html += f'<div style="color:#fca5a5; font-size:13px; padding:4px 0;">📊 <b>{truncated_count} فئة</b> وصلت لحد API (25 محل) - الأعداد الفعلية أعلى</div>'
        if heavy_sat >= 5:
            warnings_html += f'<div style="color:#fca5a5; font-size:13px; padding:4px 0;">🚫 <b>{heavy_sat} فئة مشبعة</b> بشدة - السوق العام مكتظ</div>'
        
        st.markdown(f"""<div style="background:rgba(239,68,68,0.10); border:1px solid #ef4444; border-right:4px solid #ef4444; border-radius:12px; padding:14px; margin-bottom:18px;">
<div style="color:#fecaca; font-size:14px; font-weight:700; margin-bottom:8px;">⚠️ تحذيرات السوق</div>
{warnings_html}
<div style="color:#94a3b8; font-size:11px; margin-top:8px;">💡 جرّب نطاقاً أصغر (2-3 كم) للحصول على بيانات أدق</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🛣️ بطاقة تحليل نوع الشارع
    # ═══════════════════════════════════════════════════════
    si = a.get('street_info') or st.session_state.get('street_info')
    if si and si.get('category'):
        _cat = si['category']
        _color = {'رئيسي': '#10b981', 'ثانوي': '#f59e0b', 'فرعي': '#f97316', 'غير معروف': '#64748b'}.get(_cat, '#64748b')
        _icon = {'رئيسي': '🛣️', 'ثانوي': '🚦', 'فرعي': '🏘️', 'غير معروف': '❓'}.get(_cat, '🛣️')
        _mod = si.get('opportunity_modifier', 0)
        _mod_txt = f'+{_mod}%' if _mod > 0 else (f'{_mod}%' if _mod < 0 else 'بدون تأثير')
        _mod_color = '#10b981' if _mod > 0 else ('#ef4444' if _mod < 0 else '#94a3b8')
        _name_txt = f' — {esc(si["name"])}' if si.get('name') else ''
        _corner_txt = ' • قرب تقاطع ✚' if si.get('is_corner') else ''
        _eff = a.get('street_score_effect')
        _eff_html = ''
        if _eff:
            _eff_html = (
                f'<div style="color:#cbd5e1; font-size:12px; margin-top:8px;">'
                f'أثر الشارع على نقاط الاستثمار: <b>{_eff["investment_before"]}</b> ← '
                f'<b style="color:{_mod_color};">{_eff["investment_after"]}</b> / 100</div>'
            )
        st.markdown(f"""<div style="background:rgba(255,255,255,0.04); border:1px solid {_color}; border-right:4px solid {_color}; border-radius:12px; padding:16px; margin-bottom:18px;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
  <div style="color:white; font-size:15px; font-weight:700;">{_icon} نوع الشارع: <span style="color:{_color};">{_cat}</span>{_name_txt}{_corner_txt}</div>
  <div style="background:rgba(0,0,0,0.25); padding:4px 12px; border-radius:999px; color:{_mod_color}; font-size:13px; font-weight:700;">تأثير الفرصة: {_mod_txt}</div>
</div>
<div style="color:#cbd5e1; font-size:13px; margin-top:10px; line-height:1.7;">{esc(si.get('explanation',''))}</div>
{_eff_html}
<div style="color:#64748b; font-size:11px; margin-top:8px;">🔎 المصدر: OpenStreetMap • الثقة: {si.get('confidence','—')} • للدقة الكاملة تحقق ميدانياً من واجهة الشارع وعرضه.</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 📊 تحليل SWOT - مصفوفة قرار بالأرقام (من AI)
    # ═══════════════════════════════════════════════════════
    if a.get('swot') and isinstance(a['swot'], dict):
        swot = a['swot']
        st.markdown('<div class="section-title">📊 تحليل SWOT الاستثماري</div>', unsafe_allow_html=True)
        st.caption("تحليل منظّم بالأرقام - الأساس لقرار استثماري سليم")
        
        sc1, sc2 = st.columns(2)
        with sc1:
            # نقاط القوة
            strengths_items = "".join(f'<li style="padding:6px 0; color:#cbd5e1; font-size:13px;">✓ {s}</li>' for s in swot.get('strengths', []))
            st.markdown(f"""<div style="background:rgba(16,185,129,0.10); border:1px solid #10b981; border-right:4px solid #10b981; border-radius:12px; padding:16px; margin-bottom:14px;">
<div style="color:#86efac; font-size:14px; font-weight:700; margin-bottom:10px;">💪 نقاط القوة (Strengths)</div>
<ul style="list-style:none; padding:0; margin:0;">{strengths_items or '<li style="color:#94a3b8; font-size:12px;">لا يوجد</li>'}</ul>
</div>""", unsafe_allow_html=True)
            
            # الفرص
            opps_items = "".join(f'<li style="padding:6px 0; color:#cbd5e1; font-size:13px;">🎯 {o}</li>' for o in swot.get('opportunities', []))
            st.markdown(f"""<div style="background:rgba(59,130,246,0.10); border:1px solid #3b82f6; border-right:4px solid #3b82f6; border-radius:12px; padding:16px;">
<div style="color:#93c5fd; font-size:14px; font-weight:700; margin-bottom:10px;">🌟 الفرص (Opportunities)</div>
<ul style="list-style:none; padding:0; margin:0;">{opps_items or '<li style="color:#94a3b8; font-size:12px;">لا يوجد</li>'}</ul>
</div>""", unsafe_allow_html=True)
        
        with sc2:
            # نقاط الضعف
            weaks_items = "".join(f'<li style="padding:6px 0; color:#cbd5e1; font-size:13px;">⚠️ {w}</li>' for w in swot.get('weaknesses', []))
            st.markdown(f"""<div style="background:rgba(245,158,11,0.10); border:1px solid #f59e0b; border-right:4px solid #f59e0b; border-radius:12px; padding:16px; margin-bottom:14px;">
<div style="color:#fbbf24; font-size:14px; font-weight:700; margin-bottom:10px;">⚠️ نقاط الضعف (Weaknesses)</div>
<ul style="list-style:none; padding:0; margin:0;">{weaks_items or '<li style="color:#94a3b8; font-size:12px;">لا يوجد</li>'}</ul>
</div>""", unsafe_allow_html=True)
            
            # التهديدات
            threats_items = "".join(f'<li style="padding:6px 0; color:#cbd5e1; font-size:13px;">🚨 {t}</li>' for t in swot.get('threats', []))
            st.markdown(f"""<div style="background:rgba(239,68,68,0.10); border:1px solid #ef4444; border-right:4px solid #ef4444; border-radius:12px; padding:16px;">
<div style="color:#fca5a5; font-size:14px; font-weight:700; margin-bottom:10px;">🚨 التهديدات (Threats)</div>
<ul style="list-style:none; padding:0; margin:0;">{threats_items or '<li style="color:#94a3b8; font-size:12px;">لا يوجد</li>'}</ul>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # ⚠️ تحذير: نطاق فارغ أو محدود
    # ═══════════════════════════════════════════════════════
    if a['total_places'] < 5:
        st.markdown(f"""<div style="background:rgba(239,68,68,0.15); border:2px solid #ef4444; border-radius:14px; padding:18px; margin-bottom:18px;">
<div style="color:#fca5a5; font-size:16px; font-weight:700; margin-bottom:8px;">⚠️ نطاق فارغ - بيانات غير كافية للتحليل</div>
<div style="color:#cbd5e1; font-size:14px; line-height:1.7;">
الموقع المحدد يحتوي على <b>{a['total_places']} محل فقط</b> في نطاق {radius} كم.<br>
هذا قد يعني أنك في منطقة <b>نائية أو على أطراف المدينة</b>.<br><br>
<b>💡 ماذا تفعل؟</b><br>
• جرّب <b>نطاق أوسع</b> (5 أو 10 كم) لتحليل المحيط الأكبر<br>
• تأكد من أن إحداثيات الموقع <b>صحيحة وفي وسط المدينة</b><br>
• إذا كنت تستهدف هذا الموقع فعلاً، النتائج أدناه <b>تقديرية محدودة الدقة</b>
</div>
</div>""", unsafe_allow_html=True)
    elif a['total_places'] < 20:
        st.markdown(f"""<div style="background:rgba(245,158,11,0.10); border:1px solid #f59e0b; border-radius:12px; padding:14px; margin-bottom:14px;">
<div style="color:#fbbf24; font-size:14px; font-weight:600;">⚠️ منطقة محدودة - {a['total_places']} محل فقط في نطاق {radius} كم</div>
<div style="color:#cbd5e1; font-size:13px; margin-top:6px;">
هذا قد يكون موقع على <b>أطراف المنطقة</b>. للحصول على صورة أوضح، جرّب نطاق أوسع (3-5 كم).
</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🎯 الخدمات الأساسية - 3 مستويات (يعرض دائماً عند عدم تحديد نشاط)
    # ═══════════════════════════════════════════════════════
    target_cat_str_check = a.get('target_cat')
    if not target_cat_str_check and a.get('essential_analysis') and a['total_places'] >= 5:
        ea = a['essential_analysis']
        st.markdown('<div class="section-title">🎯 الخدمات في المنطقة - فرص واحتياجات</div>', unsafe_allow_html=True)
        st.caption("تحليل لما هو موجود ومفقود حسب أولوية الاحتياج - يساعدك تختار النشاط الأنسب")

        # نعرض كل tier في expandable section
        tier_colors = {
            'critical': {'bg': 'rgba(239,68,68,0.10)', 'border': '#ef4444', 'text': '#fca5a5'},
            'essential': {'bg': 'rgba(245,158,11,0.10)', 'border': '#f59e0b', 'text': '#fbbf24'},
            'lifestyle': {'bg': 'rgba(16,185,129,0.10)', 'border': '#10b981', 'text': '#86efac'},
        }

        for tier_key in ['critical', 'essential', 'lifestyle']:
            tier = ea[tier_key]
            colors = tier_colors[tier_key]
            
            # تقسيم الخدمات حسب الحالة
            missing_svcs = [s for s in tier['services'] if s['status'] == 'missing']
            present_svcs = [s for s in tier['services'] if s['status'] == 'present']
            saturated_svcs = [s for s in tier['services'] if s['status'] in ('oversaturated', 'high_competition')]
            
            # نبني الجدول داخلياً
            services_html = ""
            for s in tier['services']:
                if s['status'] == 'missing':
                    icon_status = "❌"
                    label = "مفقود" if tier_key != 'lifestyle' else "🎯 فرصة!"
                    color = "#ef4444" if tier_key in ('critical', 'essential') else "#10b981"
                    detail = "ضروري" if tier_key == 'critical' else ("يومي" if tier_key == 'essential' else "فرصة جديدة")
                elif s['status'] == 'likely_absent':
                    icon_status = "⚪"
                    label = "غير مكتشف"
                    color = "#6b7280"
                    detail = "غير مسجّل في API - يحتاج تحقق ميداني"
                elif s['status'] == 'truncated_likely_saturated':
                    icon_status = "🔴"
                    label = f"{s['count']}+ موجود (مشبع)"
                    color = "#dc2626"
                    detail = "السوق ممتلئ (بيانات مقصوصة)"
                elif s['status'] == 'oversaturated':
                    icon_status = "🚫"
                    label = f"{s['count']} موجود (مشبع)"
                    color = "#dc2626"
                    detail = f"{s['cp_per_1k']:.1f}/1000 - تجنّب"
                elif s['status'] == 'high_competition':
                    icon_status = "⚠️"
                    label = f"{s['count']} موجود"
                    color = "#f59e0b"
                    detail = f"{s['cp_per_1k']:.1f}/1000 - تحتاج تمايز"
                else:
                    icon_status = "✅"
                    label = f"{s['count']} موجود"
                    color = "#10b981"
                    detail = "متوفر"
                
                services_html += f"""<div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.03); border-radius:8px; margin-bottom:6px;">
<span style="font-size:18px;">{s['icon']}</span>
<span style="color:white; flex:1; font-size:14px;">{s['name']}</span>
<span style="color:{color}; font-size:12px; font-weight:600;">{icon_status} {label}</span>
<span style="color:#94a3b8; font-size:11px; min-width:80px; text-align:left;">{detail}</span>
</div>"""
            
            # ملخص فوقي
            n_missing = len(missing_svcs)
            n_saturated = len(saturated_svcs)
            n_present = len(present_svcs)
            
            summary = []
            if n_missing:
                summary.append(f"❌ {n_missing} مفقود")
            if n_saturated:
                summary.append(f"⚠️ {n_saturated} مشبع")
            if n_present:
                summary.append(f"✅ {n_present} متوفر")
            
            st.markdown(f"""<div style="background:{colors['bg']}; border:1px solid {colors['border']}; border-right:4px solid {colors['border']}; border-radius:12px; padding:14px; margin-bottom:14px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
<div style="color:{colors['text']}; font-size:15px; font-weight:700;">{tier['icon']} {tier['name']}</div>
<div style="color:#94a3b8; font-size:12px;">{' • '.join(summary)}</div>
</div>
<div style="color:#94a3b8; font-size:12px; margin-bottom:10px;">{tier['description']}</div>
{services_html}
</div>""", unsafe_allow_html=True)
        
        # ملخص الفرص الأهم
        top_opps = a.get('top_opportunities', [])
        if top_opps:
            opportunity_items = ""
            for opp in top_opps[:6]:
                tier_label = {'critical': '🚨 احتياج', 'essential': '📦 أساسي', 'lifestyle': '🎯 كمالي'}.get(opp['tier'], '')
                opportunity_items += f"""<div style="display:flex; align-items:center; gap:10px; padding:10px; background:rgba(168,85,247,0.08); border-radius:10px; margin-bottom:8px;">
<span style="font-size:22px;">{opp['icon']}</span>
<div style="flex:1;">
<div style="color:white; font-weight:700; font-size:14px;">{opp['name']}</div>
<div style="color:#c4b5fd; font-size:11px;">{tier_label}</div>
</div>
</div>"""
            
            st.markdown(f"""<div style="background:linear-gradient(135deg, rgba(168,85,247,0.10) 0%, #131826 100%); border:2px solid #a855f7; border-radius:14px; padding:18px; margin-bottom:18px;">
<div style="color:#c4b5fd; font-size:15px; font-weight:700; margin-bottom:6px;">💎 أبرز الفرص المتاحة (خدمات مفقودة)</div>
<div style="color:#94a3b8; font-size:12px; margin-bottom:12px;">هذه أنشطة غير موجودة في المنطقة - قد تكون فرصاً ذهبية:</div>
{opportunity_items}
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 💰 تحليل حجم السوق المالي - يظهر مع نشاط محدد
    # ═══════════════════════════════════════════════════════
    target_cat_str = a.get('target_cat')
    if target_cat_str and a.get('local_population') and a['local_population'] > 0:
        comp_count = len(pbc.get(target_cat_str, []))
        market = calculate_market_size(target_cat_str, a['local_population'], comp_count)
        if market:
            cat_info = CATEGORIES.get(target_cat_str, {})
            st.markdown('<div class="section-title">💰 تحليل حجم السوق المالي</div>', unsafe_allow_html=True)
            st.caption("تقدير حجم السوق المتاح وحصتك المتوقعة بناءً على السكان والمنافسة")
            
            # 4 بطاقات: حجم السوق | عدد المتنافسين | حصتك المتوقعة (سنة 1) | متوسط شهري
            mc1, mc2 = st.columns(2)
            
            with mc1:
                st.markdown(f"""<div style="background:rgba(59,130,246,0.10); border:1px solid #3b82f6; border-right:4px solid #3b82f6; padding:16px; border-radius:12px; margin-bottom:10px;">
<div style="color:#93c5fd; font-size:13px; font-weight:600; margin-bottom:4px;">📊 حجم السوق السنوي الإجمالي</div>
<div style="color:white; font-size:22px; font-weight:800;">{market['total_market_annual']:,.0f} <span style="font-size:14px; color:#94a3b8;">ر.س/سنة</span></div>
<div style="color:#94a3b8; font-size:12px; margin-top:6px;">
{a['local_population']:,} نسمة × {market['spend_per_capita']:,} ر.س/سنة إنفاق على {cat_info.get('name', target_cat_str)}
</div>
</div>""", unsafe_allow_html=True)
            
            with mc2:
                st.markdown(f"""<div style="background:rgba(168,85,247,0.10); border:1px solid #a855f7; border-right:4px solid #a855f7; padding:16px; border-radius:12px; margin-bottom:10px;">
<div style="color:#c4b5fd; font-size:13px; font-weight:600; margin-bottom:4px;">⚔️ السوق مقسّم على</div>
<div style="color:white; font-size:22px; font-weight:800;">{market['players_total']} <span style="font-size:14px; color:#94a3b8;">منافس (بما فيك)</span></div>
<div style="color:#94a3b8; font-size:12px; margin-top:6px;">
{comp_count} منافس موجود + أنت = {market['players_total']} متنافسين
</div>
</div>""", unsafe_allow_html=True)
            
            # حصص متوقعة 3 سنوات
            mc3, mc4, mc5 = st.columns(3)
            
            with mc3:
                st.markdown(f"""<div style="background:rgba(245,158,11,0.10); border:1px solid #f59e0b; padding:14px; border-radius:12px; text-align:center;">
<div style="color:#fcd34d; font-size:12px; font-weight:600; margin-bottom:4px;">السنة الأولى</div>
<div style="color:white; font-size:18px; font-weight:800;">{market['realistic_share_y1']:,}</div>
<div style="color:#94a3b8; font-size:11px;">ر.س/سنة (70%)</div>
<div style="color:#fcd34d; font-size:11px; margin-top:4px;">~{market['realistic_monthly_y1']:,}/شهر</div>
</div>""", unsafe_allow_html=True)
            
            with mc4:
                st.markdown(f"""<div style="background:rgba(59,130,246,0.10); border:1px solid #3b82f6; padding:14px; border-radius:12px; text-align:center;">
<div style="color:#93c5fd; font-size:12px; font-weight:600; margin-bottom:4px;">السنة الثانية</div>
<div style="color:white; font-size:18px; font-weight:800;">{market['realistic_share_y2']:,}</div>
<div style="color:#94a3b8; font-size:11px;">ر.س/سنة (85%)</div>
<div style="color:#93c5fd; font-size:11px; margin-top:4px;">~{int(market['realistic_share_y2']/12):,}/شهر</div>
</div>""", unsafe_allow_html=True)
            
            with mc5:
                st.markdown(f"""<div style="background:rgba(16,185,129,0.10); border:1px solid #10b981; padding:14px; border-radius:12px; text-align:center;">
<div style="color:#86efac; font-size:12px; font-weight:600; margin-bottom:4px;">السنة الثالثة</div>
<div style="color:white; font-size:18px; font-weight:800;">{market['realistic_share_y3']:,}</div>
<div style="color:#94a3b8; font-size:11px;">ر.س/سنة (95%)</div>
<div style="color:#86efac; font-size:11px; margin-top:4px;">~{market['realistic_monthly_y3']:,}/شهر</div>
</div>""", unsafe_allow_html=True)
            
            # ملاحظات
            st.markdown(f"""<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); padding:12px; border-radius:10px; margin-top:12px; color:#94a3b8; font-size:12px; line-height:1.7;">
💡 <b>كيف يُحسب؟</b><br>
• <b>حجم السوق</b> = السكان المحليون × متوسط الإنفاق السنوي للفرد على هذا النشاط<br>
• <b>حصتك</b> = حجم السوق ÷ (المنافسين + 1) × معامل النضوج (70% سنة 1، 85% سنة 2، 95% سنة 3)<br>
• الأرقام <b>تقديرية</b> - النجاح يعتمد على الموقع والتميّز والتسويق
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🚫 تحذير شديد لو النشاط المختار مشبع + بدائل التخصص
    # ═══════════════════════════════════════════════════════
    if target_cat_str and a.get('local_population') and a['local_population'] > 0:
        comp_count = len(pbc.get(target_cat_str, []))
        if comp_count > 0:
            cp_per_1k = (comp_count * 1000) / a['local_population']
            warning_severity = None
            warning_msg = ""
            
            if cp_per_1k > 7:
                warning_severity = "danger"
                warning_msg = f"🚫 <b>كارثة سوقية متوقعة!</b><br>{comp_count} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_per_1k:.1f} منافس لكل 1000 نسمة</b><br>الحد الصحي < 1.5/1000. هذا السوق <b>مدمّر تماماً</b> للنشاط العادي."
            elif cp_per_1k > 3.5:
                warning_severity = "danger"
                warning_msg = f"⚠️ <b>خطر شديد!</b><br>{comp_count} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_per_1k:.1f}/1000</b><br>الفرص للنشاط العادي محدودة جداً - <b>التخصص ضروري</b>."
            elif cp_per_1k > 1.5:
                warning_severity = "warn"
                warning_msg = f"🟡 <b>منافسة عالية</b><br>{comp_count} منافس لـ {a['local_population']:,} نسمة محليين = <b>{cp_per_1k:.1f}/1000</b><br>الدخول يتطلب تمايز قوي."
            
            if warning_severity:
                bg_color = "rgba(239,68,68,0.15)" if warning_severity == "danger" else "rgba(245,158,11,0.12)"
                border = "#ef4444" if warning_severity == "danger" else "#f59e0b"
                st.markdown(f"""<div style="background:{bg_color}; border:2px solid {border}; border-radius:14px; padding:18px; margin-bottom:18px;">
                    <div style="color:white; font-size:15px; line-height:1.8;">{warning_msg}</div>
                </div>""", unsafe_allow_html=True)
                
                # عرض بدائل التخصص
                alternatives = get_specialization_alternatives(target_cat_str)
                if alternatives:
                    st.markdown(f"""<div style="background:rgba(168,85,247,0.10); border:1px solid #a855f7; border-radius:14px; padding:18px; margin-bottom:18px;">
                        <div style="color:#c4b5fd; font-size:15px; font-weight:700; margin-bottom:10px;">💡 بدائل التخصص - كيف تنجح في سوق مشبع؟</div>
                        <div style="color:#94a3b8; font-size:13px; margin-bottom:14px;">بدلاً من فتح نشاط عادي يضيع في زحام المنافسة، فكّر في هذه البدائل المتخصصة:</div>
                    </div>""", unsafe_allow_html=True)
                    
                    for i, alt in enumerate(alternatives[:5], 1):
                        st.markdown(f"""<div style="background:#131826; border:1px solid #1f2937; border-radius:12px; padding:14px; margin-bottom:8px; border-right:4px solid #a855f7;">
                            <div style="color:white; font-size:15px; font-weight:700; margin-bottom:4px;">{i}. {alt['name']}</div>
                            <div style="color:#94a3b8; font-size:13px;">💡 <b>لماذا؟</b> {alt['why']}</div>
                        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # ✍️ تحليل النشاط المخصص
    # ═══════════════════════════════════════════════════════
    if a.get('custom_activity_analysis'):
        ca = a['custom_activity_analysis']
        vc = ca.get('verdict_color', '#94a3b8')
        sc = ca.get('score', 50)
        opps_html = "".join(f'<li style="color:#10b981; padding:4px 0; font-size:13px;">✨ {o}</li>' for o in ca.get('opportunities', []))
        risks_html = "".join(f'<li style="color:#f59e0b; padding:4px 0; font-size:13px;">⚠️ {r}</li>' for r in ca.get('risks', []))

        st.markdown(f"""<div style="background:linear-gradient(135deg, rgba(59,130,246,0.12) 0%, #131826 100%);
            border:2px solid #3b82f6; border-radius:18px; padding:22px; margin-bottom:18px;">
            <div style="color:#93c5fd; font-size:13px; font-weight:600; margin-bottom:6px;">✍️ تحليل AI لنشاطك المخصص</div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; margin-bottom:14px;">
                <div style="color:white; font-size:22px; font-weight:800;">"{ca['activity']}"</div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <div style="background:rgba(255,255,255,0.06); color:{vc}; padding:8px 16px; border-radius:999px; font-size:14px; font-weight:700;">
                        {ca['verdict']}
                    </div>
                    <div style="background:rgba(255,255,255,0.06); color:{vc}; padding:8px 16px; border-radius:999px; font-size:18px; font-weight:800;">
                        {sc}<span style="font-size:12px;">/100</span>
                    </div>
                </div>
            </div>
            <div style="color:#cbd5e1; font-size:14px; line-height:1.7; margin-bottom:14px;">
                🧠 <b>التحليل:</b> {ca['reasoning']}
            </div>
            <div style="color:#94a3b8; font-size:13px; margin-bottom:8px;">
                🏪 منافسون مشابهون مقدّرون: <b style="color:#f59e0b;">{ca.get('similar_competitors', 0)}</b>
            </div>
            {f'<div style="margin-top:12px;"><div style="color:#10b981; font-size:13px; font-weight:600; margin-bottom:6px;">✨ الفرص:</div><ul style="margin:0; padding-right:18px;">{opps_html}</ul></div>' if opps_html else ''}
            {f'<div style="margin-top:12px;"><div style="color:#f59e0b; font-size:13px; font-weight:600; margin-bottom:6px;">⚠️ التحذيرات:</div><ul style="margin:0; padding-right:18px;">{risks_html}</ul></div>' if risks_html else ''}
            </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 📊 المؤشرات الثلاث - بالمستويات (4 درجات)
    # ═══════════════════════════════════════════════════════
    st.markdown('<div class="section-title">📊 المؤشرات الأساسية</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    opp = a['opportunity_score']; sat = a['saturation_score']; dem = a['demand_score']
    
    opp_lvl = score_to_level(opp)
    sat_lvl = score_to_level(sat, reverse=True)  # التشبع معكوس
    dem_lvl = score_to_level(dem)
    
    with m1:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">🎯</div>
            <div class="big-metric-label">فرصة الدخول</div>
            <div style="font-size:28px; font-weight:900; color:{opp_lvl['color']}; line-height:1.1; margin:8px 0;">{opp_lvl['icon']} {opp_lvl['level']}</div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{opp}%; background:{opp_lvl['color']};"></div></div>
            <div class="big-metric-sub">{opp_lvl['meaning']}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">📈</div>
            <div class="big-metric-label">تشبع السوق</div>
            <div style="font-size:28px; font-weight:900; color:{sat_lvl['color']}; line-height:1.1; margin:8px 0;">{sat_lvl['icon']} {sat_lvl['level']}</div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{sat}%; background:{sat_lvl['color']};"></div></div>
            <div class="big-metric-sub">{sat_lvl['meaning']}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="big-metric">
            <div class="big-metric-icon">🔥</div>
            <div class="big-metric-label">الطلب المتوقع</div>
            <div style="font-size:28px; font-weight:900; color:{dem_lvl['color']}; line-height:1.1; margin:8px 0;">{dem_lvl['icon']} {dem_lvl['level']}</div>
            <div class="big-metric-bar"><div class="big-metric-bar-fill" style="width:{dem}%; background:{dem_lvl['color']};"></div></div>
            <div class="big-metric-sub">{dem_lvl['meaning']}</div>
        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🏛️ بطاقة المحافظة - تظهر هنا فقط مع نشاط محدد (سياق مهم للقرار)
    # عند عدم تحديد نشاط، تظهر في الأسفل (الخدمات المفقودة أهم)
    # ═══════════════════════════════════════════════════════
    if a.get('gov_info') and a.get('target_cat'):
        gi = a['gov_info']
        conf_label = {"high": "✅ مطابقة عالية", "medium": "⚠️ مطابقة متوسطة", "low": "⚠️ مطابقة محدودة"}.get(gi['confidence'], '-')
        gov_density = gi['data']['pop'] / gi['data']['area'] if gi['data']['area'] > 0 else 0
        
        # عرض البطاقة الأساسية للمحافظة
        st.markdown(f"""<div class="governorate-card">
<div class="gov-name">🏛️ بيانات المحافظة</div>
<div style="color:white; font-size:20px; font-weight:800; margin-bottom:6px;">{gi['name']}</div>
<div class="gov-stats">
<div class="gov-stat-item">👥 سكان المحافظة: <b>{gi['data']['pop']:,}</b></div>
<div class="gov-stat-item">📐 المساحة: <b>{gi['data']['area']:,}</b> كم²</div>
<div class="gov-stat-item">📊 الكثافة العامة: <b>{gov_density:.1f}</b> ن/كم²</div>
<div class="gov-stat-item">🗺️ المنطقة: <b>{gi['data']['region']}</b></div>
<div class="gov-stat-item">📍 المسافة: <b>{gi['distance_km']}</b> كم ({conf_label})</div>
</div>
</div>""", unsafe_allow_html=True)
        
        # السكان المحليون المقدّرون - بطاقة منفصلة (تجنب التداخل)
        local_pop = a.get('local_population')
        local_density_val = a.get('local_density', 0)
        area_char = a.get('area_character', '-')
        if local_pop:
            st.markdown(f"""<div style="background:rgba(16,185,129,0.10); border:1px solid rgba(16,185,129,0.3); border-right:4px solid #10b981; padding:14px; border-radius:12px; margin-bottom:14px;">
<div style="color:#86efac; font-size:13px; font-weight:700; margin-bottom:8px;">📊 التقدير المحلي (داخل نطاق التحليل)</div>
<div style="color:#cbd5e1; font-size:13px; line-height:2;">
👥 السكان المحليون: <b style="color:white;">~{local_pop:,}</b> &nbsp;|&nbsp;
🏘️ نوع المنطقة: <b style="color:white;">{area_char}</b>
</div>
<div style="color:#fbbf24; font-size:11px; margin-top:6px;">
⚠️ تقدير تقريبي - للدقة الكاملة يحتاج استبيان ميداني.
</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🧪 كيمياء العائلة - تحليل الانسجام مع المحيط
    # ═══════════════════════════════════════════════════════
    if a.get('best_activities'):
        # نحدد العائلة الغالبة من أول نشاط
        top_act_for_family = a['best_activities'][0]
        dom_fam = top_act_for_family.get('dominant_family')
        
        st.markdown('<div class="section-title">🧪 الانسجام مع المحيط</div>',
                    unsafe_allow_html=True)
        
        # العائلة الغالبة
        if dom_fam:
            st.markdown(f"""<div style="background:rgba(59,130,246,0.08); border-right:4px solid #3b82f6; 
                padding:14px 18px; border-radius:10px; margin-bottom:14px;">
                <div style="color:#93c5fd; font-size:13px; font-weight:600;">🏆 الطابع التجاري الغالب في المنطقة</div>
                <div style="color:white; font-size:20px; font-weight:800; margin-top:6px;">
                    {dom_fam['icon']} {dom_fam['name']} <span style="color:#94a3b8; font-size:14px; font-weight:400;">({dom_fam['count']} محل)</span>
                </div>
                <div style="color:#94a3b8; font-size:12px; margin-top:6px;">
                    💡 الأنشطة المنسجمة مع هذا الطابع لها فرصة أعلى للنجاح
                </div>
            </div>""", unsafe_allow_html=True)
        
    
    # ═══════════════════════════════════════════════════════
    # ✅ أفضل الأنشطة المقترحة + ❌ أسوأها (مدعومة بكيمياء العائلة)
    # ═══════════════════════════════════════════════════════
    _target = a.get('target_cat')
    if _target:
        all_ranked = a.get('all_ranked_activities', []) or a.get('best_activities', [])
        chosen = next((r for r in all_ranked if r['cat_key'] == _target), None)
        st.markdown('<div class="section-title">🎯 نشاطك المختار</div>', unsafe_allow_html=True)
        if chosen:
            reasons = " • ".join(chosen['reasons'])
            final_score = chosen.get('final_opportunity', chosen['opportunity_score'])
            harmony = chosen.get('harmony_score', 0)
            final_lvl = score_to_level(final_score)
            harmony_lvl = score_to_level(harmony)
            st.markdown(f"""<div class="activity-rank-card" style="border-color:{final_lvl['color']};">
                <div class="rank-number" style="color:{final_lvl['color']};">🎯</div>
                <div class="rank-content">
                    <div class="rank-name">{chosen['icon']} {chosen['cat_name']}</div>
                    <div class="rank-reason">💡 {reasons}<br>
                        <span style="color:#64748b; font-size:11px;">منافسين: {chosen['existing']} | 
                        <span style="color:{harmony_lvl['color']};">🧪 الانسجام: {harmony_lvl['icon']} {harmony_lvl['level']}</span></span>
                    </div>
                </div>
                <div style="background:{final_lvl['color']}22; color:{final_lvl['color']}; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap;">{final_lvl['icon']} {final_lvl['level']}</div>
            </div>""", unsafe_allow_html=True)
        chosen_score = chosen.get('final_opportunity', 0) if chosen else 0
        alternatives = [r for r in all_ranked
                        if r['cat_key'] != _target
                        and r.get('final_opportunity', 0) > chosen_score][:3]
        if alternatives:
            st.markdown('<div class="section-title">💡 فرص قد تكون أفضل</div>', unsafe_allow_html=True)
            st.caption("أنشطة منسجمة مع نفس المحيط بفرصة أعلى من نشاطك المختار")
            for i, act in enumerate(alternatives, 1):
                reasons = " • ".join(act['reasons'])
                final_score = act.get('final_opportunity', act['opportunity_score'])
                harmony = act.get('harmony_score', 0)
                final_lvl = score_to_level(final_score)
                harmony_lvl = score_to_level(harmony)
                st.markdown(f"""<div class="activity-rank-card">
                    <div class="rank-number">{i}</div>
                    <div class="rank-content">
                        <div class="rank-name">{act['icon']} {act['cat_name']}</div>
                        <div class="rank-reason">💡 {reasons}<br>
                            <span style="color:#64748b; font-size:11px;">منافسين: {act['existing']} | 
                            <span style="color:{harmony_lvl['color']};">🧪 الانسجام: {harmony_lvl['icon']} {harmony_lvl['level']}</span></span>
                        </div>
                    </div>
                    <div style="background:{final_lvl['color']}22; color:{final_lvl['color']}; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap;">{final_lvl['icon']} {final_lvl['level']}</div>
                </div>""", unsafe_allow_html=True)
    else:
        col_best, col_worst = st.columns(2)
        with col_best:
            best_acts = a.get('best_activities', [])
            if best_acts:
                top_final = best_acts[0].get('final_opportunity', best_acts[0]['opportunity_score'])
                if top_final >= 55:
                    col_best_title = "✅ أفضل الأنشطة المقترحة"
                elif top_final >= 35:
                    col_best_title = "⚠️ الأقل مخاطرة"
                else:
                    col_best_title = "🚨 الأقل سوءاً (الكل مخاطرة)"
            else:
                col_best_title = "✅ أفضل الأنشطة المقترحة"
            st.markdown(f'<div class="section-title">{col_best_title}</div>', unsafe_allow_html=True)
            st.caption("🧪 مرتّبة حسب الانسجام مع المحيط")
            for i, act in enumerate(a.get('best_activities', [])[:5], 1):
                reasons = " • ".join(act['reasons'])
                final_score = act.get('final_opportunity', act['opportunity_score'])
                harmony = act.get('harmony_score', 0)
                final_lvl = score_to_level(final_score)
                harmony_lvl = score_to_level(harmony)
                st.markdown(f"""<div class="activity-rank-card">
                    <div class="rank-number">{i}</div>
                    <div class="rank-content">
                        <div class="rank-name">{act['icon']} {act['cat_name']}</div>
                        <div class="rank-reason">💡 {reasons}<br>
                            <span style="color:#64748b; font-size:11px;">منافسين: {act['existing']} | 
                            <span style="color:{harmony_lvl['color']};">🧪 الانسجام: {harmony_lvl['icon']} {harmony_lvl['level']}</span></span>
                        </div>
                    </div>
                    <div style="background:{final_lvl['color']}22; color:{final_lvl['color']}; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap;">{final_lvl['icon']} {final_lvl['level']}</div>
                </div>""", unsafe_allow_html=True)
        with col_worst:
            st.markdown('<div class="section-title">🚫 أنشطة عالية المخاطرة</div>', unsafe_allow_html=True)
            if a.get('worst_activities'):
                st.caption("غير منسجمة مع المحيط أو السوق مشبع")
                for act in a['worst_activities']:
                    reasons = " • ".join(act['reasons'])
                    final_score = act.get('final_opportunity', act['opportunity_score'])
                    harmony = act.get('harmony_score', 0)
                    final_lvl = score_to_level(final_score)
                    harmony_lvl = score_to_level(harmony)
                    st.markdown(f"""<div class="activity-rank-card" style="border-color:rgba(239,68,68,0.3);">
                        <div class="rank-number" style="color:#ef4444;">✗</div>
                        <div class="rank-content">
                            <div class="rank-name">{act['icon']} {act['cat_name']}</div>
                            <div class="rank-reason">⚠️ {reasons}<br>
                                <span style="color:#64748b; font-size:11px;">منافسين: {act['existing']} | 
                                <span style="color:{harmony_lvl['color']};">🧪 الانسجام: {harmony_lvl['icon']} {harmony_lvl['level']}</span></span>
                            </div>
                        </div>
                        <div style="background:{final_lvl['color']}22; color:{final_lvl['color']}; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap;">{final_lvl['icon']} {final_lvl['level']}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("لا توجد أنشطة بفرصة منخفضة جداً - كل الأنشطة لها إمكانات")

    if not a.get('target_cat'):
        st.markdown('<div class="section-title">🏪 المحلات حسب التصنيف</div>', unsafe_allow_html=True)
        st.caption("اضغط أي تصنيف لعرض كل المحلات المُكتشفة تحته (الاسم • المسافة • التقييم إن توفّر)")
        _tflags = a.get('truncation_flags', {})
        for cat_key, places in sorted(pbc.items(), key=lambda x: -len(x[1])):
            cat = CATEGORIES[cat_key]
            cnt = len(places)
            mark = "+" if _tflags.get(cat_key) else ""
            with st.expander(f"{cat['icon']} {cat['name']} — {cnt}{mark} محل"):
                if _tflags.get(cat_key):
                    st.caption("⚠️ هذا التصنيف وصل لحد المصدر — العدد الفعلي أكبر.")
                rated = [p for p in places if p.get('rating')]
                if rated:
                    avg = sum(p['rating'] for p in rated) / len(rated)
                    st.caption(f"⭐ متوسط تقييم {len(rated)} محل: {avg:.1f}/5 (من OpenStreetMap)")
                rows = []
                for idx, p in enumerate(places, 1):
                    rate_txt = ""
                    if p.get('rating'):
                        rev = f" / {p['reviews']} مراجعة" if p.get('reviews') else ""
                        rate_txt = f' — <span style="color:#f59e0b;">⭐ {p["rating"]}{rev}</span>'
                    rows.append(
                        f'<div style="display:flex; justify-content:space-between; gap:10px; '
                        f'padding:7px 10px; border-bottom:1px solid rgba(255,255,255,0.06); font-size:13px;">'
                        f'<span style="color:#e2e8f0;">{idx}. {esc(p["name"])}{rate_txt}</span>'
                        f'<span style="color:#f59e0b; white-space:nowrap;">{p["dist"]:.2f} كم</span></div>'
                    )
                st.markdown("".join(rows), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 🎯 القرار النهائي الكامل - في الأسفل (بعد قراءة كل المحتوى)
    # ═══════════════════════════════════════════════════════
    st.markdown('<div class="section-title">🎯 القرار النهائي</div>', unsafe_allow_html=True)
    st.caption("بناءً على كل التحليل أعلاه، إليك القرار التفصيلي:")
    
    full_card = st.session_state.get('_full_decision_card_html', '')
    if full_card:
        st.markdown(full_card, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # 📄 زر تصدير PDF - في الأسفل بعد كل المحتوى
    # ═══════════════════════════════════════════════════════
    from datetime import datetime
    st.markdown('<div class="section-title">📄 تصدير التقرير</div>', unsafe_allow_html=True)
    report_filename = f"GBI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    report_html = build_report_html(a, pbc, lat, lng, radius)
    ec1, ec2, ec3 = st.columns([1, 2, 1])
    with ec2:
        st.download_button(
            label="📄 تصدير التقرير الكامل (HTML قابل للطباعة PDF)",
            data=report_html.encode('utf-8'),
            file_name=report_filename,
            mime="text/html",
            use_container_width=True,
        )
    st.caption("💡 افتح الملف المُحمّل ثم اضغط 'اطبع / احفظ PDF' بالأعلى")

    # ═══════════════════════════════════════════════════════
    # 💬 المستشار الذكي
    # ═══════════════════════════════════════════════════════
    st.markdown('<div class="section-title">💬 المستشار الذكي</div>', unsafe_allow_html=True)
    if not AI_AVAILABLE:
        st.warning("⚠️ المستشار الذكي يحتاج GEMINI_API_KEY")
    else:
        for msg in st.session_state.chat:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
        user_msg = st.chat_input("اسأل المستشار عن أي تفصيل في التحليل...")
        if user_msg:
            st.session_state.chat.append({'role': 'user', 'content': user_msg})
            with st.chat_message('user'):
                st.markdown(user_msg)
            with st.chat_message('assistant'):
                with st.spinner("..."):
                    reply = ai_chat(user_msg, a, pbc, lat, lng)
                    st.markdown(reply)
            st.session_state.chat.append({'role': 'assistant', 'content': reply})
            st.rerun()
