"""
economic_intelligence.py
═══════════════════════════════════════════════════════════════════════
الذكاء الاقتصادي - فهم لماذا توجد الأنشطة، وليس فقط ماذا يوجد
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

يطبّق نظرياً:
  - Retail Agglomeration Theory
  - Trip Chaining Behavior (رحلة العميل)
  - Central Place Theory
  - Hierarchy of Needs (هرم الاحتياجات التجاري)
  - Comparative Area Analysis (مقارنة المناطق المشابهة)
  - Need Score vs Availability Score
═══════════════════════════════════════════════════════════════════════
"""

import math
from typing import Dict, List, Optional, Tuple, Any

# ══════════════════════════════════════════════════════════════════════
# 1. قاعدة علاقات النشاط الاقتصادي الموسّعة
#    كل نشاط له "مغناطيس" - أنشطة تجذب بعضها البعض بسبب:
#    (أ) رحلة العميل الواحدة (Trip Chaining)
#    (ب) نفس الفئة المستهدفة (Same Audience)
#    (ج) الخدمات التكميلية (Complementary Services)
# ══════════════════════════════════════════════════════════════════════

ACTIVITY_ECOSYSTEM = {
    # ────────────────────────────────────────────────────
    # 🏫 المدرسة - نظام بيئي كامل
    # ────────────────────────────────────────────────────
    "school": {
        "name": "مدرسة",
        "icon": "🏫",
        "expected_companions": [
            {"cat": "grocery", "weight": 85, "reason": "أولياء الأمور يمرون بالبقالة أثناء إيصال الأطفال"},
            {"cat": "bakery", "weight": 90, "reason": "وجبة الصباح + الاستراحة"},
            {"cat": "sweets", "weight": 75, "reason": "مكافأة الأطفال بعد المدرسة"},
            {"cat": "services", "weight": 70, "reason": "قرطاسية + مستلزمات مدرسية"},
            {"cat": "fast_food", "weight": 65, "reason": "وجبات الطلاب بعد الدوام"},
            {"cat": "pharmacy", "weight": 60, "reason": "احتياجات صحية متكررة"},
            {"cat": "cafe", "weight": 55, "reason": "انتظار أولياء الأمور"},
            {"cat": "mobile_repair", "weight": 50, "reason": "طلاب يكسرون شاشاتهم"},
        ],
        "trip_chains": [
            ["school", "bakery", "grocery"],           # رحلة صباحية كلاسيكية
            ["school", "fast_food", "sweets"],          # رحلة ما بعد المدرسة
            ["school", "pharmacy", "grocery"],          # رحلة الاحتياجات
        ],
        "population_type": "families",
        "peak_hours": "07:00-09:00, 13:00-15:00",
    },

    # ────────────────────────────────────────────────────
    # 🏥 المستشفى - نظام بيئي طبي
    # ────────────────────────────────────────────────────
    "hospital": {
        "name": "مستشفى",
        "icon": "🏥",
        "expected_companions": [
            {"cat": "pharmacy", "weight": 95, "reason": "وصفات طبية فورية - ارتباط مباشر"},
            {"cat": "medical_lab", "weight": 85, "reason": "تحاليل مرافقة للعلاج"},
            {"cat": "restaurant", "weight": 80, "reason": "المرافقون يحتاجون الطعام"},
            {"cat": "fast_food", "weight": 75, "reason": "وجبات سريعة للمرافقين"},
            {"cat": "cafe", "weight": 70, "reason": "انتظار طويل = قهوة"},
            {"cat": "hotel", "weight": 65, "reason": "مرافقون من خارج المدينة"},
            {"cat": "grocery", "weight": 60, "reason": "تموين للمرضى المزمنين"},
            {"cat": "atm", "weight": 55, "reason": "دفع فواتير طبية"},
            {"cat": "flower_shop", "weight": 50, "reason": "هدايا للمرضى"},
            {"cat": "optician", "weight": 45, "reason": "عيادات تكميلية"},
        ],
        "trip_chains": [
            ["hospital", "pharmacy", "restaurant"],     # رحلة العلاج الكاملة
            ["hospital", "medical_lab", "pharmacy"],    # رحلة التشخيص
            ["hospital", "cafe", "atm"],                # رحلة الانتظار
        ],
        "population_type": "all",
        "peak_hours": "08:00-14:00",
    },

    # ────────────────────────────────────────────────────
    # ⛽ محطة الوقود - نظام خدمات السفر
    # ────────────────────────────────────────────────────
    "fuel": {
        "name": "محطة وقود",
        "icon": "⛽",
        "expected_companions": [
            {"cat": "cafe", "weight": 90, "reason": "استراحة المسافر - القهوة أثناء التعبئة"},
            {"cat": "fast_food", "weight": 85, "reason": "وجبة سريعة على الطريق"},
            {"cat": "car_wash", "weight": 80, "reason": "خدمة السيارة الكاملة في مكان واحد"},
            {"cat": "auto_repair", "weight": 75, "reason": "تدارك الأعطال أثناء التنقل"},
            {"cat": "grocery", "weight": 70, "reason": "محطة شاملة للاحتياجات"},
            {"cat": "tyre_shop", "weight": 65, "reason": "طوارئ السفر"},
            {"cat": "atm", "weight": 60, "reason": "الدفع النقدي للوقود"},
            {"cat": "oil_change", "weight": 55, "reason": "صيانة دورية في نفس الوقفة"},
        ],
        "trip_chains": [
            ["fuel", "car_wash", "cafe"],               # خدمة السيارة الكاملة
            ["fuel", "fast_food", "grocery"],           # محطة شاملة
            ["fuel", "auto_repair", "tyre_shop"],       # طوارئ السيارة
        ],
        "population_type": "commuters",
        "peak_hours": "07:00-09:00, 16:00-19:00",
    },

    # ────────────────────────────────────────────────────
    # 🕌 المسجد - مركز اجتماعي
    # ────────────────────────────────────────────────────
    "mosque": {
        "name": "مسجد",
        "icon": "🕌",
        "expected_companions": [
            {"cat": "restaurant", "weight": 85, "reason": "وجبة ما بعد الجمعة - تقليد راسخ"},
            {"cat": "grocery", "weight": 80, "reason": "مشتريات الجمعة الأسبوعية"},
            {"cat": "bakery", "weight": 70, "reason": "كعك وحلوى موسمية"},
            {"cat": "sweets", "weight": 65, "reason": "حلوى المناسبات والأعياد"},
            {"cat": "cafe", "weight": 60, "reason": "قهوة ما بعد الصلاة"},
            {"cat": "clothing_store", "weight": 55, "reason": "ملابس المناسبات الدينية"},
            {"cat": "services", "weight": 50, "reason": "طباعة وتصوير مستندات"},
        ],
        "trip_chains": [
            ["mosque", "restaurant", "grocery"],        # رحلة الجمعة
            ["mosque", "cafe", "sweets"],               # رحلة اجتماعية
        ],
        "population_type": "all",
        "peak_hours": "11:30-14:00 (Fri), prayer_times",
    },

    # ────────────────────────────────────────────────────
    # 🛒 سوبرماركت - مركز الاحتياجات اليومية
    # ────────────────────────────────────────────────────
    "grocery": {
        "name": "سوبرماركت",
        "icon": "🛒",
        "expected_companions": [
            {"cat": "pharmacy", "weight": 88, "reason": "احتياجات يومية في رحلة واحدة"},
            {"cat": "bakery", "weight": 82, "reason": "خبز طازج مع البقالة"},
            {"cat": "butcher", "weight": 78, "reason": "مشتريات الطعام الكاملة"},
            {"cat": "vegetables", "weight": 75, "reason": "تتكامل - كل احتياجات المطبخ"},
            {"cat": "atm", "weight": 70, "reason": "سحب نقدي للتسوق"},
            {"cat": "cleaning", "weight": 60, "reason": "مواد التنظيف مع البقالة"},
        ],
        "trip_chains": [
            ["grocery", "pharmacy", "bakery"],          # رحلة الاحتياجات الأساسية
            ["grocery", "butcher", "vegetables"],       # رحلة التسوق الغذائي
        ],
        "population_type": "families",
        "peak_hours": "16:00-20:00",
    },
}


# ══════════════════════════════════════════════════════════════════════
# 2. النشاط الناقص الذكي: Need Score vs Availability Score
#    لا نكتفي بـ "يوجد / لا يوجد" بل نحسب:
#    - Need Score: هل السكان يحتاجونه فعلاً؟
#    - Supply Score: كم هو متوفر؟
#    - Gap Score: الفجوة الفعلية بين الحاجة والعرض
# ══════════════════════════════════════════════════════════════════════

# الوزن الديموغرافي لكل نشاط حسب نوع السكان
DEMOGRAPHIC_NEED_WEIGHTS = {
    # النشاط: {عائلي, شبابي, تجاري, خدماتي, سياحي}
    "pharmacy":     {"families": 95, "youth": 60, "workers": 70, "elderly": 90, "tourists": 40},
    "grocery":      {"families": 98, "youth": 70, "workers": 75, "elderly": 85, "tourists": 30},
    "school":       {"families": 90, "youth": 20, "workers": 10, "elderly": 5,  "tourists": 5},
    "clinic":       {"families": 85, "youth": 55, "workers": 65, "elderly": 90, "tourists": 35},
    "mosque":       {"families": 90, "youth": 70, "workers": 80, "elderly": 90, "tourists": 30},
    "bakery":       {"families": 88, "youth": 75, "workers": 80, "elderly": 80, "tourists": 50},
    "cafe":         {"families": 65, "youth": 95, "workers": 85, "elderly": 55, "tourists": 90},
    "restaurant":   {"families": 85, "youth": 80, "workers": 85, "elderly": 70, "tourists": 90},
    "fast_food":    {"families": 75, "youth": 90, "workers": 80, "elderly": 45, "tourists": 65},
    "barber":       {"families": 80, "youth": 85, "workers": 85, "elderly": 75, "tourists": 40},
    "beauty_salon": {"families": 85, "youth": 90, "workers": 70, "elderly": 50, "tourists": 45},
    "fuel":         {"families": 90, "youth": 85, "workers": 90, "elderly": 75, "tourists": 70},
    "car_wash":     {"families": 75, "youth": 80, "workers": 75, "elderly": 60, "tourists": 40},
    "auto_repair":  {"families": 80, "youth": 70, "workers": 80, "elderly": 65, "tourists": 30},
    "atm":          {"families": 85, "youth": 75, "workers": 85, "elderly": 80, "tourists": 70},
    "fitness_center":{"families": 60, "youth": 90, "workers": 70, "elderly": 35, "tourists": 40},
    "clothing_store":{"families": 80, "youth": 85, "workers": 70, "elderly": 60, "tourists": 70},
    "electronics_store":{"families": 70, "youth": 85, "workers": 75, "elderly": 40, "tourists": 40},
    "hotel":        {"families": 45, "youth": 55, "workers": 80, "elderly": 50, "tourists": 95},
    "park":         {"families": 90, "youth": 75, "workers": 50, "elderly": 70, "tourists": 60},
    "library":      {"families": 70, "youth": 80, "workers": 45, "elderly": 60, "tourists": 20},
    "cinema":       {"families": 80, "youth": 90, "workers": 60, "elderly": 40, "tourists": 60},
    "tyre_shop":    {"families": 80, "youth": 75, "workers": 85, "elderly": 65, "tourists": 30},
    "gas_supply":   {"families": 90, "youth": 60, "workers": 70, "elderly": 85, "tourists": 10},
    "dentist":      {"families": 85, "youth": 65, "workers": 70, "elderly": 80, "tourists": 20},
    "furniture":    {"families": 85, "youth": 50, "workers": 55, "elderly": 70, "tourists": 10},
    "butcher":      {"families": 90, "youth": 55, "workers": 65, "elderly": 80, "tourists": 20},
    "vegetables":   {"families": 92, "youth": 55, "workers": 60, "elderly": 85, "tourists": 15},
    "sweets":       {"families": 85, "youth": 80, "workers": 70, "elderly": 75, "tourists": 60},
    "quran_school": {"families": 75, "youth": 50, "workers": 30, "elderly": 60, "tourists": 5},
}

# الكثافة المثلى (عدد المحلات لكل 1000 نسمة) - معايرة على السوق السعودي
IDEAL_DENSITY_PER_1K = {
    "pharmacy":     0.5,   # صيدلية لكل 2000 نسمة
    "grocery":      0.8,   # سوبرماركت لكل 1250 نسمة
    "restaurant":   1.2,   # مطعم لكل 830 نسمة
    "cafe":         0.7,   # مقهى لكل 1430 نسمة
    "fast_food":    0.9,   # وجبات سريعة لكل 1110 نسمة
    "barber":       0.6,   # حلاق لكل 1670 نسمة
    "beauty_salon": 0.5,   # صالون لكل 2000 نسمة
    "fuel":         0.3,   # محطة لكل 3333 نسمة
    "car_wash":     0.3,
    "auto_repair":  0.4,
    "clinic":       0.4,
    "atm":          0.6,
    "bakery":       0.5,
    "butcher":      0.4,
    "vegetables":   0.4,
    "clothing_store": 0.5,
    "mosque":       0.8,   # مسجد لكل 1250 نسمة
    "school":       0.3,
    "dentist":      0.25,
    "tyre_shop":    0.25,
    "sweets":       0.3,
    "fitness_center": 0.2,
    "electronics_store": 0.3,
    "hotel":        0.15,
    "library":      0.1,
    "cinema":       0.05,
    "park":         0.2,
    "mobile_repair": 0.4,
    "gas_supply":   0.2,
}


def calculate_need_score(
    cat: str,
    local_population: int,
    dna: dict,
    area_character: str
) -> dict:
    """
    يحسب Need Score الحقيقي لنشاط ما بناءً على:
    - تركيبة السكان (DNA)
    - حجم السكان
    - نوع المنطقة
    
    يرجع: need_score (0-100), explanation, demographic_fit
    """
    # تحديد نوع السكان الغالب
    dna_scores = {
        "families": dna.get("family", 50),
        "youth": dna.get("youth", 50),
        "workers": dna.get("commercial", 50),
        "elderly": 30,  # افتراض معتدل
        "tourists": 10,  # افتراض منخفض ما لم يكن موقع سياحي
    }
    
    # تعديل حسب نوع المنطقة
    if "سياحي" in area_character.lower() or "فندق" in area_character.lower():
        dna_scores["tourists"] = 70
    if area_character in ("حضري مكتظ", "حضري"):
        dna_scores["workers"] = max(dna_scores["workers"], 70)
    
    # الوزن الديموغرافي للنشاط
    weights = DEMOGRAPHIC_NEED_WEIGHTS.get(cat, {})
    if not weights:
        return {"need_score": 50, "explanation": "لا توجد بيانات ديموغرافية كافية", "demographic_fit": "متوسط"}
    
    # حساب Need Score كمتوسط مرجّح
    total_weight = sum(dna_scores.values())
    weighted_need = 0
    for demo_type, demo_score in dna_scores.items():
        cat_weight = weights.get(demo_type, 50)
        weighted_need += (demo_score / total_weight) * cat_weight
    
    need_score = int(weighted_need)
    
    # تعديل حسب حجم السكان
    if local_population and local_population > 0:
        ideal_density = IDEAL_DENSITY_PER_1K.get(cat, 0.5)
        ideal_count = (local_population / 1000) * ideal_density
        if ideal_count >= 1:
            pop_bonus = min(15, int(math.log(ideal_count) * 5))
            need_score = min(100, need_score + pop_bonus)
    
    # التفسير
    if need_score >= 80:
        demographic_fit = "مرتفع جداً"
        explanation = f"السكان يحتاجون هذا النشاط بشدة (الديموغرافيا: {max(dna_scores, key=dna_scores.get)})"
    elif need_score >= 60:
        demographic_fit = "مرتفع"
        explanation = "الطلب الديموغرافي جيد على هذا النشاط"
    elif need_score >= 40:
        demographic_fit = "متوسط"
        explanation = "طلب معتدل - تحتاج دراسة إضافية"
    else:
        demographic_fit = "منخفض"
        explanation = "الديموغرافيا لا تدعم هذا النشاط بقوة"
    
    return {
        "need_score": need_score,
        "explanation": explanation,
        "demographic_fit": demographic_fit,
        "top_demographic": max(dna_scores, key=dna_scores.get),
    }


def calculate_gap_score(
    cat: str,
    existing_count: int,
    local_population: int,
    need_score: int
) -> dict:
    """
    يحسب فجوة الطلب/العرض الحقيقية.
    Gap = Need - Supply (الحاجة - التوفر)
    """
    if not local_population or local_population <= 0:
        return {"gap_score": 50, "gap_type": "غير محدد", "explanation": "لا توجد بيانات سكانية"}
    
    # Supply Score: كم التوفر مقارنة بالمثالي
    ideal_density = IDEAL_DENSITY_PER_1K.get(cat, 0.5)
    ideal_count = max(1, (local_population / 1000) * ideal_density)
    
    if existing_count == 0:
        supply_score = 0
    else:
        supply_ratio = existing_count / ideal_count
        if supply_ratio <= 0.5:
            supply_score = int(supply_ratio * 60)      # 0-30: شُح
        elif supply_ratio <= 1.0:
            supply_score = int(30 + supply_ratio * 40) # 30-70: عادي
        elif supply_ratio <= 2.0:
            supply_score = int(70 + (supply_ratio - 1) * 20)  # 70-90: مشبع
        else:
            supply_score = min(100, int(90 + (supply_ratio - 2) * 5))  # 90+: مشبع جداً
    
    # Gap = Need - Supply (مطبّع على 0-100)
    gap = need_score - supply_score
    
    # gap موجب = فرصة، gap سالب = تشبع
    if gap >= 50:
        gap_type = "فرصة قوية"
        gap_color = "#10b981"
        recommendation = "السوق يحتاج هذا النشاط وهو غير متوفر بشكل كافٍ"
    elif gap >= 20:
        gap_type = "فرصة معقولة"
        gap_color = "#22c55e"
        recommendation = "يوجد طلب أكثر من العرض - فرصة دخول"
    elif gap >= -10:
        gap_type = "توازن"
        gap_color = "#f59e0b"
        recommendation = "السوق متوازن - تحتاج ميزة تنافسية للنجاح"
    elif gap >= -30:
        gap_type = "تشبع معتدل"
        gap_color = "#f97316"
        recommendation = "العرض يفوق الطلب قليلاً - مخاطرة متوسطة"
    else:
        gap_type = "تشبع شديد"
        gap_color = "#ef4444"
        recommendation = "السوق مشبع - تجنّب الدخول بدون تخصص قوي"
    
    return {
        "gap_score": gap,
        "gap_type": gap_type,
        "gap_color": gap_color,
        "need_score": need_score,
        "supply_score": supply_score,
        "existing_count": existing_count,
        "ideal_count": round(ideal_count, 1),
        "recommendation": recommendation,
    }


# ══════════════════════════════════════════════════════════════════════
# 3. رحلة العميل (Customer Journey / Trip Chaining)
#    استنتاج الأنماط السلوكية من الأنشطة الموجودة
# ══════════════════════════════════════════════════════════════════════

def discover_trip_chains(pbc: dict) -> List[dict]:
    """
    يستنتج رحلات العميل الفعلية من الأنشطة الموجودة.
    
    مثال: لو وجدنا [مدرسة + بقالة + صيدلية]
    نستنتج: رحلة "أولياء الأمور الصباحية"
    
    يرجع: قائمة من رحلات مكتملة / ناقصة + فرص إكمالها
    """
    present_cats = set(pbc.keys())
    chains_found = []
    
    # تعريف رحلات العملاء الكلاسيكية في السعودية
    SAUDI_TRIP_CHAINS = [
        {
            "id": "morning_family",
            "name": "رحلة الصباح العائلية",
            "icon": "🌅",
            "description": "الأب يوصل الأطفال للمدرسة ثم يشتري احتياجاته",
            "stops": ["school", "bakery", "grocery", "pharmacy"],
            "time": "07:00 - 09:30",
            "population": "families",
        },
        {
            "id": "after_school",
            "name": "رحلة ما بعد المدرسة",
            "icon": "🎒",
            "description": "الأطفال يتوقفون في طريق العودة",
            "stops": ["school", "fast_food", "sweets", "grocery"],
            "time": "13:00 - 15:30",
            "population": "youth + families",
        },
        {
            "id": "hospital_journey",
            "name": "رحلة الرعاية الصحية",
            "icon": "🏥",
            "description": "المريض وأسرته يحتاجون خدمات متعددة",
            "stops": ["clinic", "pharmacy", "medical_lab", "cafe"],
            "time": "08:00 - 14:00",
            "population": "all",
        },
        {
            "id": "friday_journey",
            "name": "رحلة الجمعة",
            "icon": "🕌",
            "description": "ما بعد صلاة الجمعة - أكثر رحلة متكررة في السعودية",
            "stops": ["mosque", "restaurant", "grocery", "sweets"],
            "time": "12:00 - 15:00",
            "population": "all",
        },
        {
            "id": "car_service",
            "name": "رحلة خدمة السيارة",
            "icon": "🚗",
            "description": "العميل يغسل سيارته ويستغل الوقت في خدمات أخرى",
            "stops": ["fuel", "car_wash", "cafe", "auto_repair"],
            "time": "flexible",
            "population": "commuters",
        },
        {
            "id": "shopping_outing",
            "name": "رحلة التسوق",
            "icon": "🛍️",
            "description": "خروج العائلة للتسوق والترفيه",
            "stops": ["shopping", "restaurant", "cafe", "cinema"],
            "time": "15:00 - 22:00",
            "population": "families + youth",
        },
        {
            "id": "evening_social",
            "name": "السهرة الاجتماعية",
            "icon": "☕",
            "description": "جلسة شباب أو عائلية مسائية",
            "stops": ["cafe", "restaurant", "sweets", "shopping"],
            "time": "20:00 - 00:00",
            "population": "youth + families",
        },
        {
            "id": "daily_essentials",
            "name": "رحلة الاحتياجات اليومية",
            "icon": "📦",
            "description": "شراء الاحتياجات الأساسية في رحلة واحدة",
            "stops": ["grocery", "pharmacy", "bakery", "butcher"],
            "time": "16:00 - 20:00",
            "population": "families",
        },
        {
            "id": "health_wellness",
            "name": "رحلة الصحة والعناية",
            "icon": "💪",
            "description": "رحلة عناية بالجسم والمظهر",
            "stops": ["fitness_center", "beauty_salon", "cafe", "clothing_store"],
            "time": "07:00 - 11:00, 17:00 - 21:00",
            "population": "youth",
        },
    ]
    
    for chain in SAUDI_TRIP_CHAINS:
        stops = chain["stops"]
        present_stops = [s for s in stops if s in present_cats]
        missing_stops = [s for s in stops if s not in present_cats]
        
        completion_rate = len(present_stops) / len(stops)
        
        chain_result = {
            **chain,
            "present_stops": present_stops,
            "missing_stops": missing_stops,
            "completion_rate": round(completion_rate, 2),
            "completion_pct": int(completion_rate * 100),
            "is_complete": len(missing_stops) == 0,
            "is_partial": 0.25 <= completion_rate < 1.0,
            "opportunity": missing_stops,  # هذه الأنشطة المفقودة = فرص
        }
        chains_found.append(chain_result)
    
    # ترتيب: الأكثر اكتمالاً أولاً (لأنها تكشف الفرص الحقيقية)
    chains_found.sort(key=lambda x: -x["completion_rate"])
    
    return chains_found


def get_journey_opportunities(chains: List[dict]) -> List[dict]:
    """
    يستخرج الفرص من رحلات العملاء الناقصة.
    الفرصة = نشاط ناقص من رحلة مكتملة جزئياً (50%+)
    """
    opportunity_scores: Dict[str, dict] = {}
    
    for chain in chains:
        if chain["completion_rate"] < 0.4:
            continue  # الرحلة غير محتملة أصلاً
        
        for missing_cat in chain["missing_stops"]:
            if missing_cat not in opportunity_scores:
                opportunity_scores[missing_cat] = {
                    "cat": missing_cat,
                    "appears_in_journeys": [],
                    "total_score": 0,
                    "max_completion": 0,
                }
            
            journey_score = chain["completion_rate"] * 100
            opportunity_scores[missing_cat]["appears_in_journeys"].append({
                "journey_name": chain["name"],
                "journey_icon": chain["icon"],
                "completion_pct": chain["completion_pct"],
            })
            opportunity_scores[missing_cat]["total_score"] += journey_score
            opportunity_scores[missing_cat]["max_completion"] = max(
                opportunity_scores[missing_cat]["max_completion"],
                chain["completion_rate"]
            )
    
    # تحويل للقائمة وترتيب
    result = list(opportunity_scores.values())
    result.sort(key=lambda x: -(x["total_score"] + x["max_completion"] * 50))
    
    return result[:10]  # أفضل 10 فرص


# ══════════════════════════════════════════════════════════════════════
# 4. هوية المنطقة الاقتصادية (Area Economic Identity)
#    لا نكتفي بـ DNA المحلات، بل نفهم "شخصية" المنطقة الاقتصادية
# ══════════════════════════════════════════════════════════════════════

AREA_IDENTITY_PATTERNS = {
    "educational_hub": {
        "name": "حي تعليمي",
        "icon": "📚",
        "indicators": ["school", "library", "training_center", "quran_school", "services"],
        "min_indicators": 2,
        "description": "منطقة تعليمية - الطلاب وأولياء الأمور هم المحرك الرئيسي",
        "strong_opportunities": ["bakery", "fast_food", "sweets", "mobile_repair", "services"],
        "weak_opportunities": ["hotel", "car_rental", "fitness_center"],
    },
    "medical_district": {
        "name": "حي طبي",
        "icon": "⚕️",
        "indicators": ["hospital", "clinic", "pharmacy", "medical_lab", "dentist"],
        "min_indicators": 2,
        "description": "منطقة طبية - المرضى والمرافقون يحركون الاقتصاد",
        "strong_opportunities": ["pharmacy", "restaurant", "cafe", "hotel", "flower_shop"],
        "weak_opportunities": ["cinema", "nightclub", "game_center"],
    },
    "automotive_corridor": {
        "name": "ممر السيارات",
        "icon": "🚗",
        "indicators": ["fuel", "auto_repair", "car_wash", "car_dealer", "tyre_shop", "oil_change"],
        "min_indicators": 3,
        "description": "منطقة خدمات سيارات - حركة مرور عالية مع وقفات قصيرة",
        "strong_opportunities": ["cafe", "fast_food", "auto_parts", "car_tinting"],
        "weak_opportunities": ["clothing_store", "furniture", "beauty_salon"],
    },
    "food_destination": {
        "name": "وجهة طعام",
        "icon": "🍽️",
        "indicators": ["restaurant", "cafe", "fast_food", "bakery", "sweets"],
        "min_indicators": 4,
        "description": "منطقة ترفيه غذائي - العملاء يأتون للتجربة والاستمتاع",
        "strong_opportunities": ["entertainment", "shopping", "parking"],
        "weak_opportunities": ["auto_repair", "industrial"],
    },
    "residential_service": {
        "name": "حي سكني خدماتي",
        "icon": "🏘️",
        "indicators": ["grocery", "pharmacy", "mosque", "school", "bakery"],
        "min_indicators": 3,
        "description": "حي سكني متكامل - الاحتياجات اليومية تحرك الاقتصاد",
        "strong_opportunities": ["clinic", "barber", "beauty_salon", "cleaning", "gas_supply"],
        "weak_opportunities": ["hotel", "cinema", "museum"],
    },
    "commercial_center": {
        "name": "مركز تجاري",
        "icon": "🏬",
        "indicators": ["shopping", "clothing_store", "electronics_store", "bank", "atm"],
        "min_indicators": 3,
        "description": "منطقة تجارية - التسوق والأعمال هو المحرك الرئيسي",
        "strong_opportunities": ["restaurant", "cafe", "parking", "services"],
        "weak_opportunities": ["school", "mosque", "residential"],
    },
    "tourism_area": {
        "name": "منطقة سياحية",
        "icon": "🗺️",
        "indicators": ["hotel", "tourist_attraction", "museum", "restaurant", "shopping"],
        "min_indicators": 2,
        "description": "منطقة سياحية - الزوار هم المستهدف الرئيسي",
        "strong_opportunities": ["cafe", "souvenir", "car_rental", "tour_guide"],
        "weak_opportunities": ["auto_repair", "school", "industrial"],
    },
}


def identify_area_identity(pbc: dict) -> dict:
    """
    يحدد الهوية الاقتصادية للمنطقة بناءً على الأنشطة الموجودة.
    يمكن أن تكون للمنطقة هويات متعددة.
    """
    present_cats = set(pbc.keys())
    matches = []
    
    for identity_key, identity in AREA_IDENTITY_PATTERNS.items():
        indicators_present = [ind for ind in identity["indicators"] if ind in present_cats]
        match_count = len(indicators_present)
        
        if match_count >= identity["min_indicators"]:
            strength = min(100, int((match_count / len(identity["indicators"])) * 100))
            matches.append({
                "key": identity_key,
                "name": identity["name"],
                "icon": identity["icon"],
                "description": identity["description"],
                "strength": strength,
                "indicators_present": indicators_present,
                "strong_opportunities": identity["strong_opportunities"],
                "weak_opportunities": identity["weak_opportunities"],
            })
    
    matches.sort(key=lambda x: -x["strength"])
    
    primary_identity = matches[0] if matches else {
        "key": "undefined",
        "name": "منطقة غير محددة الهوية",
        "icon": "🏙️",
        "description": "تركيبة تجارية متنوعة بدون هوية واضحة",
        "strength": 0,
        "indicators_present": [],
        "strong_opportunities": [],
        "weak_opportunities": [],
    }
    
    return {
        "primary": primary_identity,
        "all_matches": matches,
        "has_clear_identity": len(matches) > 0,
        "is_mixed": len(matches) > 1,
    }


# ══════════════════════════════════════════════════════════════════════
# 5. مقارنة المناطق المشابهة (Comparative Area Analysis)
#    أفضل طريقة لاكتشاف الفرص: ما ينجح في مناطق مشابهة وغير موجود هنا
# ══════════════════════════════════════════════════════════════════════

# نماذج مناطق ناجحة في السعودية (معايرة استقرائية)
# كل نموذج يمثل "بروفايل" منطقة ناجحة مع الأنشطة المميزة لها
SUCCESSFUL_AREA_PROFILES = {
    "residential_riyadh": {
        "name": "حي سكني متوسط - الرياض",
        "population_range": (20000, 80000),
        "density": "سكني متوسط",
        "typical_activities": {
            "grocery": 3, "pharmacy": 2, "restaurant": 5,
            "cafe": 4, "fast_food": 3, "school": 2, "mosque": 3,
            "bakery": 2, "barber": 2, "beauty_salon": 1, "clinic": 2,
            "auto_repair": 2, "fuel": 1, "atm": 2, "cleaning": 1,
        },
        "success_indicators": ["cafe", "grocery", "bakery"],
        "unique_to_profile": ["quran_school", "gas_supply", "cleaning"],
    },
    "commercial_strip": {
        "name": "شارع تجاري رئيسي",
        "population_range": (50000, 200000),
        "density": "حضري",
        "typical_activities": {
            "restaurant": 10, "cafe": 8, "fast_food": 6, "shopping": 5,
            "clothing_store": 4, "electronics_store": 3, "bank": 3,
            "atm": 5, "beauty_salon": 3, "fitness_center": 2,
            "fuel": 2, "auto_repair": 3, "car_wash": 2, "services": 4,
        },
        "success_indicators": ["cafe", "restaurant", "shopping"],
        "unique_to_profile": ["ev_charging_station", "mobile_repair"],
    },
    "university_area": {
        "name": "منطقة جامعية",
        "population_range": (30000, 100000),
        "density": "سكني متوسط",
        "typical_activities": {
            "cafe": 10, "fast_food": 8, "restaurant": 6, "grocery": 4,
            "bakery": 3, "fitness_center": 3, "library": 1,
            "mobile_repair": 4, "clothing_store": 3, "atm": 4,
            "beauty_salon": 3, "barber": 3, "services": 3,
        },
        "success_indicators": ["cafe", "fast_food", "mobile_repair"],
        "unique_to_profile": ["coworking", "printing", "student_housing"],
    },
    "medical_zone": {
        "name": "منطقة طبية",
        "population_range": (10000, 50000),
        "density": "سكني محدود",
        "typical_activities": {
            "pharmacy": 6, "clinic": 8, "hospital": 2, "medical_lab": 3,
            "cafe": 4, "restaurant": 5, "fast_food": 3, "hotel": 2,
            "atm": 3, "grocery": 2, "dentist": 3,
        },
        "success_indicators": ["pharmacy", "cafe", "restaurant"],
        "unique_to_profile": ["medical_supply", "optician", "rehabilitation"],
    },
}


def find_comparable_areas(
    area_character: str,
    local_population: int,
    pbc: dict
) -> dict:
    """
    يجد المناطق المشابهة ويستخرج الأنشطة الناجحة هناك لكن غير موجودة هنا.
    هذا هو أقوى محرك لاكتشاف الفرص.
    """
    present_cats = set(pbc.keys())
    comparable_profiles = []
    
    for profile_key, profile in SUCCESSFUL_AREA_PROFILES.items():
        pop_min, pop_max = profile["population_range"]
        
        # تطابق نوع المنطقة
        density_match = False
        if profile["density"] == "حضري" and area_character in ("حضري مكتظ", "حضري"):
            density_match = True
        elif profile["density"] == "سكني متوسط" and area_character == "سكني متوسط":
            density_match = True
        elif profile["density"] == "سكني محدود" and area_character in ("سكني محدود", "ريفي / أطراف"):
            density_match = True
        
        # تطابق حجم السكان (إذا متوفر)
        pop_match = True
        if local_population and local_population > 0:
            pop_match = pop_min <= local_population <= pop_max * 2
        
        if density_match and pop_match:
            # الأنشطة الناجحة في المنطقة المشابهة لكن غير موجودة هنا
            missing_from_profile = []
            for cat, expected_count in profile["typical_activities"].items():
                if cat not in present_cats and expected_count >= 2:
                    missing_from_profile.append({
                        "cat": cat,
                        "expected_count": expected_count,
                        "is_success_indicator": cat in profile["success_indicators"],
                        "is_unique": cat in profile["unique_to_profile"],
                    })
            
            comparable_profiles.append({
                "profile_key": profile_key,
                "profile_name": profile["name"],
                "missing_activities": sorted(
                    missing_from_profile,
                    key=lambda x: -(x["expected_count"] + (10 if x["is_success_indicator"] else 0))
                )[:8],
                "similarity_score": 70 if (density_match and pop_match) else 50,
            })
    
    if not comparable_profiles:
        return {
            "found": False,
            "message": "لم نجد مناطق مشابهة كافية للمقارنة",
            "opportunities": [],
        }
    
    # دمج الفرص من كل المناطق المشابهة
    all_opportunities: Dict[str, dict] = {}
    for profile in comparable_profiles:
        for act in profile["missing_activities"]:
            cat = act["cat"]
            if cat not in all_opportunities:
                all_opportunities[cat] = {
                    "cat": cat,
                    "appears_in_profiles": 0,
                    "total_expected": 0,
                    "is_success_indicator": False,
                }
            all_opportunities[cat]["appears_in_profiles"] += 1
            all_opportunities[cat]["total_expected"] += act["expected_count"]
            if act["is_success_indicator"]:
                all_opportunities[cat]["is_success_indicator"] = True
    
    sorted_opps = sorted(
        all_opportunities.values(),
        key=lambda x: -(x["appears_in_profiles"] * 10 + x["total_expected"] + (20 if x["is_success_indicator"] else 0))
    )
    
    return {
        "found": True,
        "comparable_profiles": comparable_profiles,
        "opportunities": sorted_opps[:8],
        "primary_profile": comparable_profiles[0]["profile_name"],
    }


# ══════════════════════════════════════════════════════════════════════
# 6. التوصية الشاملة المبنية على الذكاء الاقتصادي
# ══════════════════════════════════════════════════════════════════════

def generate_economic_intelligence_report(
    pbc: dict,
    a: dict,
    local_population: int,
    dna: dict
) -> dict:
    """
    يولّد تقرير الذكاء الاقتصادي الشامل:
    - هوية المنطقة
    - رحلات العملاء
    - فجوات الطلب والعرض
    - مقارنة المناطق المشابهة
    - التوصيات المبنية على الأدلة
    """
    area_character = a.get("area_character", "سكني محدود")
    
    # 1. هوية المنطقة
    identity = identify_area_identity(pbc)
    
    # 2. رحلات العملاء
    trip_chains = discover_trip_chains(pbc)
    journey_opportunities = get_journey_opportunities(trip_chains)
    
    # 3. مقارنة المناطق
    comparable = find_comparable_areas(area_character, local_population, pbc)
    
    # 4. Need Score لأهم الأنشطة الغائبة
    missing_cats = []
    common_cats = list(IDEAL_DENSITY_PER_1K.keys())
    for cat in common_cats:
        if cat not in pbc or len(pbc.get(cat, [])) == 0:
            need = calculate_need_score(cat, local_population, dna, area_character)
            gap = calculate_gap_score(cat, 0, local_population, need["need_score"])
            
            if need["need_score"] >= 55:  # فقط الأنشطة ذات الطلب المعقول
                missing_cats.append({
                    "cat": cat,
                    "need_score": need["need_score"],
                    "gap_score": gap["gap_score"],
                    "gap_type": gap["gap_type"],
                    "gap_color": gap["gap_color"],
                    "explanation": need["explanation"],
                    "ideal_count": gap["ideal_count"],
                })
    
    missing_cats.sort(key=lambda x: -(x["need_score"] + max(0, x["gap_score"])))
    top_missing = missing_cats[:6]
    
    # 5. تجميع التوصيات المبنية على أدلة متعددة
    evidence_based_recommendations = []
    seen_cats = set()
    
    # من رحلات العملاء (الأقوى)
    for opp in journey_opportunities[:4]:
        cat = opp["cat"]
        if cat not in seen_cats:
            journeys_text = ", ".join([j["journey_name"] for j in opp["appears_in_journeys"][:2]])
            evidence_based_recommendations.append({
                "cat": cat,
                "evidence_type": "رحلة عميل",
                "evidence_icon": "🛤️",
                "evidence_strength": "قوي",
                "explanation": f"يكمل رحلة العميل في: {journeys_text}",
                "confidence": min(90, int(opp["total_score"])),
            })
            seen_cats.add(cat)
    
    # من المناطق المشابهة
    if comparable["found"]:
        for opp in comparable["opportunities"][:3]:
            cat = opp["cat"]
            if cat not in seen_cats:
                evidence_based_recommendations.append({
                    "cat": cat,
                    "evidence_type": "مناطق مشابهة",
                    "evidence_icon": "📊",
                    "evidence_strength": "متوسط-قوي",
                    "explanation": f"ينجح في {comparable['primary_profile']} - غير موجود هنا",
                    "confidence": 65,
                })
                seen_cats.add(cat)
    
    # من تحليل الفجوة
    for item in top_missing[:3]:
        cat = item["cat"]
        if cat not in seen_cats and item["gap_score"] > 20:
            evidence_based_recommendations.append({
                "cat": cat,
                "evidence_type": "فجوة الطلب",
                "evidence_icon": "📈",
                "evidence_strength": "متوسط",
                "explanation": item["explanation"],
                "confidence": min(75, 50 + item["gap_score"] // 3),
            })
            seen_cats.add(cat)
    
    # ترتيب نهائي
    evidence_based_recommendations.sort(key=lambda x: -x["confidence"])
    
    return {
        "area_identity": identity,
        "trip_chains": trip_chains,
        "journey_opportunities": journey_opportunities,
        "comparable_areas": comparable,
        "need_gap_analysis": top_missing,
        "evidence_based_recommendations": evidence_based_recommendations[:6],
        "has_clear_story": identity["has_clear_identity"],
        "economic_summary": _build_economic_summary(identity, trip_chains, comparable),
    }


def _build_economic_summary(identity: dict, chains: List[dict], comparable: dict) -> str:
    """يبني ملخصاً نصياً لقصة المنطقة الاقتصادية"""
    parts = []
    
    if identity["has_clear_identity"]:
        parts.append(f"المنطقة ذات هوية {identity['primary']['name']} ({identity['primary']['description']})")
    else:
        parts.append("المنطقة بدون هوية اقتصادية واضحة - تجارة متنوعة غير متخصصة")
    
    complete_chains = [c for c in chains if c["is_complete"]]
    partial_chains = [c for c in chains if c["is_partial"]]
    
    if complete_chains:
        parts.append(f"رحلات العملاء المكتملة: {', '.join([c['name'] for c in complete_chains[:2]])}")
    
    if partial_chains:
        top_partial = partial_chains[0]
        parts.append(f"رحلة '{top_partial['name']}' مكتملة {top_partial['completion_pct']}% - فرصة إكمالها")
    
    if comparable["found"]:
        parts.append(f"تشابه مع '{comparable['primary_profile']}' - أنشطة ناجحة هناك يمكن تطبيقها هنا")
    
    return " • ".join(parts)
