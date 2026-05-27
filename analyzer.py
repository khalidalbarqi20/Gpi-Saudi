"""
محرك تحليل المواقع - GBI Saudi
- يعتمد على OpenStreetMap (Overpass API) - مجاني وتغطيته ممتازة في السعودية
- خوارزمية تحليل قائمة على القواعد (Rule-based) مع AI اختياري
"""

import re
import math
import json
import time
import requests
from typing import Optional
from categories import CATEGORIES, GROUPS, build_overpass_query, classify_osm_element


# ============================================================
# 1) استخراج الإحداثيات من رابط Google Maps
# ============================================================
def extract_coords(url: str):
    """
    استخراج (lat, lng) من رابط Google Maps - يدعم:
    - الروابط المختصرة (goo.gl, maps.app.goo.gl)
    - الروابط الكاملة (@lat,lng)
    - place/lat,lng
    - !3dLAT!4dLNG
    - إحداثيات مباشرة "24.7136,46.6753"
    """
    if not url:
        return None, None

    url = url.strip()

    # إحداثيات مباشرة
    direct = re.match(r'^\s*(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)\s*$', url)
    if direct:
        return float(direct.group(1)), float(direct.group(2))

    # روابط مختصرة - فك التحويل
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(
                url, allow_redirects=True, timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            url = r.url
        except Exception:
            return None, None

    patterns = [
        r'@(-?\d+\.?\d+),(-?\d+\.?\d+)',
        r'place/[^/]*/@(-?\d+\.?\d+),(-?\d+\.?\d+)',
        r'!3d(-?\d+\.?\d+)!4d(-?\d+\.?\d+)',
        r'q=(-?\d+\.?\d+),(-?\d+\.?\d+)',
        r'/(-?\d+\.?\d+),(-?\d+\.?\d+)',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            try:
                lat = float(m.group(1))
                lng = float(m.group(2))
                # تحقق منطقي من الإحداثيات
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
            except ValueError:
                continue
    return None, None


# ============================================================
# 2) حساب المسافة (Haversine)
# ============================================================
def dist_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ============================================================
# 3) جلب المحلات من Overpass API
# ============================================================
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def fetch_places(lat: float, lng: float, radius_km: float, category_keys: list):
    """
    جلب كل المحلات في الفئات المطلوبة ضمن نطاق معين
    يجرب أكثر من سيرفر تلقائياً ليكون موثوق
    """
    radius_m = int(radius_km * 1000)
    query = build_overpass_query(lat, lng, radius_m, category_keys)

    last_error = None
    for server in OVERPASS_SERVERS:
        try:
            r = requests.post(
                server,
                data={'data': query},
                timeout=60,
                headers={'User-Agent': 'GBI-Saudi/2.0'}
            )
            if r.status_code == 200:
                if r.text.strip().startswith('{'):
                    return r.json().get('elements', []), None
            elif r.status_code == 429:
                time.sleep(3)
                continue
            last_error = f"HTTP {r.status_code}"
        except requests.exceptions.Timeout:
            last_error = "timeout"
        except Exception as e:
            last_error = str(e)[:80]
        time.sleep(1)

    return [], last_error or "كل السيرفرات فشلت"


def process_elements(elements: list, target_lat: float, target_lng: float, max_km: float):
    """
    معالجة عناصر OSM وتصنيفها وفق فئاتنا
    """
    by_cat = {}
    seen_coords = set()

    for el in elements:
        tags = el.get('tags', {})
        if not tags:
            continue

        # الحصول على إحداثيات
        if el.get('type') == 'node':
            plat = el.get('lat')
            plng = el.get('lon')
        else:  # way / relation
            center = el.get('center', {})
            plat = center.get('lat')
            plng = center.get('lon')

        if not plat or not plng:
            continue

        # منع التكرار (نفس المكان من tags متعددة)
        key = (round(plat, 5), round(plng, 5))
        if key in seen_coords:
            continue
        seen_coords.add(key)

        # حساب المسافة
        d = dist_km(target_lat, target_lng, plat, plng)
        if d > max_km:
            continue

        # تصنيف
        cat_key = classify_osm_element(tags)
        if not cat_key:
            continue

        # اسم
        name = (tags.get('name:ar') or tags.get('name') or tags.get('name:en') or '').strip()
        if not name:
            name = f"({CATEGORIES[cat_key]['name']} بدون اسم)"

        # عنوان
        addr_parts = []
        for k in ('addr:street', 'addr:district', 'addr:city'):
            v = tags.get(k)
            if v:
                addr_parts.append(v)
        addr = " - ".join(addr_parts)

        # تقييم (إن وُجد)
        brand = tags.get('brand') or tags.get('operator') or ''

        place = {
            'name': name,
            'cat': cat_key,
            'lat': plat,
            'lng': plng,
            'dist': d,
            'addr': addr,
            'brand': brand,
            'tags': tags,
        }
        by_cat.setdefault(cat_key, []).append(place)

    # ترتيب كل فئة حسب المسافة
    for cat_key in by_cat:
        by_cat[cat_key].sort(key=lambda x: x['dist'])

    return by_cat


# ============================================================
# 4) خوارزمية التحليل الأساسية (Rule-based - بدون AI)
# ============================================================
def analyze_location(places_by_cat: dict, radius_km: float, target_cat: Optional[str] = None) -> dict:
    """
    خوارزمية تحليل قائمة على القواعد - تعمل بدون AI

    Inputs:
        places_by_cat: dict من category_key إلى list of places
        radius_km: نصف القطر بالكيلومتر
        target_cat: النشاط المستهدف (اختياري) - إذا تم تحديده نحلل المنافسة له

    Outputs: dict كامل بكل المؤشرات
    """
    total_places = sum(len(v) for v in places_by_cat.values())
    active_cat_count = len([v for v in places_by_cat.values() if len(v) > 0])

    # ===== 1) تحديد طبيعة المنطقة =====
    # نحسب الكثافة لكل كم² (المساحة = π × r²)
    area_km2 = math.pi * (radius_km ** 2)
    density = total_places / area_km2 if area_km2 > 0 else 0

    if total_places == 0:
        area_type = "منطقة فارغة"
        area_nature = "نائية"
    elif density < 2:
        area_type = "منطقة هادئة"
        area_nature = "هادئة"
    elif density < 8:
        area_type = "منطقة سكنية"
        area_nature = "سكنية"
    elif density < 20:
        area_type = "منطقة متوسطة النشاط"
        area_nature = "مختلطة"
    elif density < 50:
        area_type = "منطقة تجارية نشطة"
        area_nature = "تجارية"
    else:
        area_type = "منطقة تجارية مكتظة"
        area_nature = "تجارية مكتظة"

    # ===== 2) تحديد ثقافة الحي =====
    food_count = sum(len(places_by_cat.get(k, [])) for k in ['restaurant', 'cafe', 'fast_food'])
    leisure_count = sum(len(places_by_cat.get(k, [])) for k in ['park', 'sports_club', 'tourist_attraction', 'cinema', 'museum'])
    shopping_count = sum(len(places_by_cat.get(k, [])) for k in ['mall', 'clothes', 'electronics', 'beauty'])
    services_count = sum(len(places_by_cat.get(k, [])) for k in ['hospital', 'pharmacy', 'atm', 'fuel', 'parking'])
    family_count = sum(len(places_by_cat.get(k, [])) for k in ['park', 'school', 'university', 'mosque', 'supermarket'])
    youth_count = sum(len(places_by_cat.get(k, [])) for k in ['cafe', 'fast_food', 'nightlife', 'cinema', 'sports_club'])

    culture_scores = {
        'عائلي': family_count * 1.2,
        'شبابي': youth_count * 1.5,
        'تجاري': shopping_count * 1.3,
        'سياحي': leisure_count * 1.4,
        'خدمي': services_count * 1.0,
        'طعام': food_count * 1.1,
    }
    if total_places > 0:
        neighborhood_type = max(culture_scores, key=culture_scores.get)
    else:
        neighborhood_type = "غير محدد"

    # ===== 3) مستوى المنافسة =====
    if target_cat:
        competitor_count = len(places_by_cat.get(target_cat, []))
        if competitor_count == 0:
            competition_level = "لا منافسة"
            competition_score = 100
        elif competitor_count <= 2:
            competition_level = "منخفض"
            competition_score = 75
        elif competitor_count <= 5:
            competition_level = "متوسط"
            competition_score = 50
        elif competitor_count <= 10:
            competition_level = "مرتفع"
            competition_score = 25
        else:
            competition_level = "مرتفع جداً"
            competition_score = 10
    else:
        # متوسط المنافسة عبر كل الفئات النشطة
        if active_cat_count == 0:
            competition_level = "منخفض"
            competition_score = 80
        elif total_places / max(active_cat_count, 1) < 3:
            competition_level = "منخفض"
            competition_score = 75
        elif total_places / max(active_cat_count, 1) < 7:
            competition_level = "متوسط"
            competition_score = 55
        else:
            competition_level = "مرتفع"
            competition_score = 30
        competitor_count = 0

    # ===== 4) سهولة الوصول =====
    parking_count = len(places_by_cat.get('parking', []))
    fuel_count = len(places_by_cat.get('fuel', []))

    if parking_count >= 3 and fuel_count >= 1:
        accessibility = "ممتازة"
        accessibility_score = 90
    elif parking_count >= 1:
        accessibility = "جيدة"
        accessibility_score = 70
    elif fuel_count >= 1 or total_places > 10:
        accessibility = "متوسطة"
        accessibility_score = 55
    else:
        accessibility = "تحتاج تحقق"
        accessibility_score = 40

    # ===== 5) مستوى الحركة (تقدير) =====
    # نقدّر الحركة من كثافة الطعام والتسوق والترفيه
    traffic_indicator = food_count * 2 + shopping_count * 1.5 + leisure_count
    if traffic_indicator >= 30:
        traffic_level = "عالية جداً"
        traffic_score = 95
    elif traffic_indicator >= 15:
        traffic_level = "عالية"
        traffic_score = 80
    elif traffic_indicator >= 7:
        traffic_level = "متوسطة"
        traffic_score = 60
    elif traffic_indicator >= 2:
        traffic_level = "منخفضة"
        traffic_score = 40
    else:
        traffic_level = "منخفضة جداً"
        traffic_score = 20

    # ===== 6) الكثافة السكانية (تقدير من البنية التحتية) =====
    pop_indicator = (
        len(places_by_cat.get('mosque', [])) * 3 +   # مسجد لكل ~1000 شخص في السعودية
        len(places_by_cat.get('school', [])) * 5 +
        len(places_by_cat.get('supermarket', [])) * 4
    )
    if pop_indicator >= 25:
        pop_density = "عالية"
        pop_score = 90
    elif pop_indicator >= 12:
        pop_density = "متوسطة"
        pop_score = 65
    elif pop_indicator >= 4:
        pop_density = "منخفضة"
        pop_score = 40
    else:
        pop_density = "قليلة"
        pop_score = 20

    # تقدير السكان (تقريبي جداً - ١٠٠٠ شخص لكل مسجد)
    est_population = max(1000, pop_indicator * 350) if pop_indicator > 0 else 0

    # ===== 7) نقاط الاستثمار الشاملة (0-100) =====
    # وزن العوامل
    if target_cat:
        # عند وجود نشاط مستهدف: المنافسة + الحركة + الوصول + ملاءمة الحي
        suitability = _calc_suitability(target_cat, places_by_cat, neighborhood_type)
        investment_score = int(
            competition_score * 0.30 +
            traffic_score * 0.25 +
            accessibility_score * 0.15 +
            suitability * 0.20 +
            pop_score * 0.10
        )
    else:
        # بدون نشاط مستهدف: تقييم عام للموقع
        investment_score = int(
            traffic_score * 0.30 +
            accessibility_score * 0.20 +
            pop_score * 0.25 +
            competition_score * 0.15 +
            (min(active_cat_count * 5, 100)) * 0.10
        )

    # ===== 8) الفرص (الفئات الناقصة أو القليلة) =====
    opportunities = []
    missing_services = []

    # خدمات أساسية ناقصة
    essential = {
        'pharmacy': "صيدلية - خدمة أساسية مفقودة",
        'supermarket': "بقالة/سوبر ماركت",
        'atm': "صراف آلي",
        'fuel': "محطة وقود",
    }
    for key, label in essential.items():
        if len(places_by_cat.get(key, [])) == 0:
            missing_services.append(label)

    # فرص استثمارية حسب نوع الحي
    opp_by_culture = {
        'عائلي': ['مطعم عائلي', 'سوبر ماركت', 'مركز ترفيه أطفال', 'مدرسة خاصة'],
        'شبابي': ['كافيه متخصص', 'مطعم وجبات سريعة', 'صالة رياضية', 'محل إلكترونيات'],
        'تجاري': ['مكتب خدمات', 'مطعم سريع للموظفين', 'مقهى عمل', 'مغسلة سيارات'],
        'سياحي': ['مطعم تجربة', 'متجر هدايا', 'كافيه ذو إطلالة', 'خدمات تأجير'],
        'طعام': ['نشاط متخصص (حلويات/مخبز)', 'مقهى بمفهوم مختلف', 'مطبخ سحابي'],
    }
    base_opps = opp_by_culture.get(neighborhood_type, ['دراسة ميدانية للموقع'])

    # فلترة الفرص حسب المنافسة
    for opp in base_opps:
        opportunities.append(opp)

    # ===== 9) أقوى المنافسين =====
    top_competitors = []
    if target_cat and target_cat in places_by_cat:
        for p in places_by_cat[target_cat][:5]:
            top_competitors.append({
                'name': p['name'],
                'dist': round(p['dist'], 2),
                'brand': p.get('brand', ''),
            })

    # ===== 10) التوصية النصية =====
    if investment_score >= 75:
        recommendation = (
            f"موقع ممتاز! فرصة استثمارية قوية في {area_type}. "
            f"الحركة {traffic_level} ومستوى المنافسة {competition_level}."
        )
        risk_level = "منخفض"
    elif investment_score >= 55:
        recommendation = (
            f"موقع جيد بإمكانيات واعدة. {area_type} مع منافسة {competition_level}. "
            f"يُنصح بدراسة ميدانية قبل الالتزام."
        )
        risk_level = "متوسط"
    elif investment_score >= 35:
        recommendation = (
            f"موقع متوسط - يحتاج دراسة دقيقة. النشاط محدود ({total_places} محل في {radius_km} كم). "
            f"قد تكون فرصة لمن يبحث عن سوق غير مشبع."
        )
        risk_level = "متوسط-عالي"
    else:
        recommendation = (
            f"منطقة قليلة النشاط - تحتاج دراسة متعمقة. "
            f"{total_places} محل فقط في {radius_km} كم. "
            f"المخاطرة عالية للأنشطة التي تعتمد على الحركة."
        )
        risk_level = "عالي"

    # نقاط القوة والاتباه
    strengths = []
    cautions = []

    if traffic_score >= 70:
        strengths.append("حركة مرور عالية")
    if accessibility_score >= 70:
        strengths.append("سهولة وصول ممتازة")
    if pop_score >= 70:
        strengths.append("كثافة سكانية عالية")
    if competition_score >= 60:
        strengths.append("مستوى منافسة مقبول")
    if active_cat_count >= 5:
        strengths.append("تنوع تجاري في المنطقة")

    if competition_score < 40:
        cautions.append("منافسة مرتفعة في المنطقة")
    if traffic_score < 40:
        cautions.append("حركة منخفضة - يحتاج جذب نشط")
    if pop_score < 40:
        cautions.append("كثافة سكانية محدودة")
    if total_places < 5:
        cautions.append("بنية تجارية ضعيفة في المحيط")

    if not strengths:
        strengths.append("منطقة بكر تحتاج دراسة")
    if not cautions:
        cautions.append("راقب الإيجارات في المنطقة")

    return {
        'investment_score': investment_score,
        'total_places': total_places,
        'active_cat_count': active_cat_count,
        'area_type': area_type,
        'area_nature': area_nature,
        'neighborhood_type': neighborhood_type,
        'competition_level': competition_level,
        'competition_score': competition_score,
        'competitor_count': competitor_count,
        'traffic_level': traffic_level,
        'traffic_score': traffic_score,
        'accessibility': accessibility,
        'accessibility_score': accessibility_score,
        'pop_density': pop_density,
        'pop_score': pop_score,
        'est_population': est_population,
        'parking_count': parking_count,
        'opportunities': opportunities[:5],
        'missing_services': missing_services[:5],
        'top_competitors': top_competitors,
        'recommendation': recommendation,
        'risk_level': risk_level,
        'strengths': strengths,
        'cautions': cautions,
        'target_cat': target_cat,
    }


def _calc_suitability(target_cat: str, places_by_cat: dict, neighborhood_type: str) -> float:
    """حساب ملاءمة النشاط للحي"""
    suitability_map = {
        'restaurant': {'عائلي': 90, 'شبابي': 80, 'تجاري': 85, 'سياحي': 95, 'طعام': 60, 'خدمي': 70},
        'cafe': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'سياحي': 85, 'طعام': 75, 'خدمي': 60},
        'fast_food': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'سياحي': 70, 'طعام': 60, 'خدمي': 70},
        'pharmacy': {'عائلي': 95, 'شبابي': 70, 'تجاري': 75, 'سياحي': 60, 'طعام': 50, 'خدمي': 90},
        'supermarket': {'عائلي': 95, 'شبابي': 75, 'تجاري': 70, 'سياحي': 50, 'طعام': 60, 'خدمي': 80},
        'car_wash': {'عائلي': 80, 'شبابي': 75, 'تجاري': 85, 'سياحي': 50, 'طعام': 40, 'خدمي': 90},
        'beauty': {'عائلي': 85, 'شبابي': 90, 'تجاري': 80, 'سياحي': 70, 'طعام': 50, 'خدمي': 75},
        'clothes': {'عائلي': 80, 'شبابي': 90, 'تجاري': 85, 'سياحي': 80, 'طعام': 50, 'خدمي': 60},
    }
    return suitability_map.get(target_cat, {}).get(neighborhood_type, 70)


# ============================================================
# 5) اقتراح أفضل نشاط للموقع (عندما لا يحدد المستخدم نشاطاً)
# ============================================================
def suggest_best_activity(places_by_cat: dict, analysis: dict) -> list:
    """
    اقتراح أفضل ٣ أنشطة للموقع بناءً على المعطيات
    """
    neighborhood = analysis['neighborhood_type']
    total = analysis['total_places']

    # كل نشاط محتمل + معامل القاعدة + سعة السوق المعتادة
    candidates = {
        'cafe':       {'demand': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'سياحي': 85, 'طعام': 60, 'خدمي': 65}, 'cap': 8},
        'restaurant': {'demand': {'عائلي': 95, 'شبابي': 80, 'تجاري': 80, 'سياحي': 95, 'طعام': 55, 'خدمي': 70}, 'cap': 10},
        'fast_food':  {'demand': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'سياحي': 70, 'طعام': 60, 'خدمي': 70}, 'cap': 8},
        'pharmacy':   {'demand': {'عائلي': 95, 'شبابي': 70, 'تجاري': 70, 'سياحي': 50, 'طعام': 50, 'خدمي': 90}, 'cap': 3},
        'supermarket':{'demand': {'عائلي': 95, 'شبابي': 75, 'تجاري': 65, 'سياحي': 45, 'طعام': 55, 'خدمي': 80}, 'cap': 5},
        'car_wash':   {'demand': {'عائلي': 80, 'شبابي': 75, 'تجاري': 85, 'سياحي': 45, 'طعام': 40, 'خدمي': 90}, 'cap': 4},
        'salon':      {'demand': {'عائلي': 85, 'شبابي': 90, 'تجاري': 75, 'سياحي': 70, 'طعام': 50, 'خدمي': 70}, 'cap': 6},
        'beauty':     {'demand': {'عائلي': 80, 'شبابي': 90, 'تجاري': 75, 'سياحي': 65, 'طعام': 50, 'خدمي': 65}, 'cap': 4},
        'clothes':    {'demand': {'عائلي': 75, 'شبابي': 90, 'تجاري': 80, 'سياحي': 80, 'طعام': 50, 'خدمي': 55}, 'cap': 6},
        'sports_club':{'demand': {'عائلي': 80, 'شبابي': 90, 'تجاري': 70, 'سياحي': 50, 'طعام': 40, 'خدمي': 55}, 'cap': 3},
    }

    scores = []
    for cat_key, info in candidates.items():
        existing = len(places_by_cat.get(cat_key, []))
        demand = info['demand'].get(neighborhood, 60)
        cap = info['cap']

        # درجة الفرصة = الطلب - الإشباع
        saturation = min(100, (existing / cap) * 100) if cap > 0 else 100
        opportunity = max(0, demand - saturation * 0.7)

        # تعديل: لو المنطقة فارغة جداً، نرفع الأنشطة الأساسية
        if total < 5 and cat_key in ('supermarket', 'pharmacy', 'restaurant'):
            opportunity += 15

        scores.append({
            'cat_key': cat_key,
            'cat_name': CATEGORIES[cat_key]['name'],
            'icon': CATEGORIES[cat_key]['icon'],
            'demand': demand,
            'existing': existing,
            'saturation': int(saturation),
            'opportunity_score': int(opportunity),
            'reason': _build_reason(cat_key, existing, demand, saturation, neighborhood),
        })

    scores.sort(key=lambda x: -x['opportunity_score'])
    return scores[:5]


def _build_reason(cat_key, existing, demand, saturation, neighborhood):
    cat_name = CATEGORIES[cat_key]['name']
    if existing == 0:
        return f"لا يوجد {cat_name} في المنطقة، والطلب المتوقع في حي {neighborhood} مرتفع"
    if saturation < 30:
        return f"{existing} منافس فقط - السوق غير مشبع وملاءمته لحي {neighborhood} جيدة"
    if saturation < 60:
        return f"{existing} منافسين - السوق متوسط الإشباع، تحتاج تميّز"
    return f"{existing} منافس - السوق مشبع، يحتاج خدمة فريدة"


# ============================================================
# 6) AI متقدّم (اختياري - عبر Gemini)
# ============================================================
def ai_enhance_analysis(analysis: dict, places_by_cat: dict, lat: float, lng: float, ai_available: bool, genai_module=None):
    """
    تحسين التحليل عبر AI (اختياري)
    لو AI غير متاح، نرجع التحليل الأساسي كما هو
    """
    if not ai_available or not genai_module:
        return analysis

    try:
        model = genai_module.GenerativeModel('gemini-2.0-flash-exp')
        summary = ", ".join([
            f"{CATEGORIES[k]['name']}({len(v)})"
            for k, v in places_by_cat.items() if len(v) > 0
        ])

        prompt = f"""أنت خبير تحليل مواقع تجارية في السعودية. حلل هذا الموقع:
- الإحداثيات: {lat}, {lng}
- الأنشطة المحيطة: {summary}
- نوع الحي المُكتشف: {analysis['neighborhood_type']}
- نقاط الاستثمار الحالية: {analysis['investment_score']}/100

أعد JSON فقط بهذا الشكل (لا تكتب شيئاً قبله أو بعده):
{{
  "ai_recommendation": "توصية محسّنة من خبير في ٢-٣ جمل",
  "best_activities": ["نشاط 1", "نشاط 2", "نشاط 3"],
  "key_risks": ["مخاطرة 1", "مخاطرة 2"],
  "growth_potential": "منخفض/متوسط/عالي"
}}"""

        response = model.generate_content(prompt, request_options={"timeout": 20})
        text = response.text.strip()

        # تنظيف
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]

        ai_data = json.loads(text.strip())

        # دمج مع التحليل الأساسي
        analysis['ai_recommendation'] = ai_data.get('ai_recommendation', '')
        analysis['ai_best_activities'] = ai_data.get('best_activities', [])
        analysis['ai_key_risks'] = ai_data.get('key_risks', [])
        analysis['ai_growth_potential'] = ai_data.get('growth_potential', 'متوسط')
        analysis['ai_enhanced'] = True
    except Exception as e:
        analysis['ai_enhanced'] = False
        analysis['ai_error'] = str(e)[:100]

    return analysis


# ============================================================
# 7) دردشة AI
# ============================================================
def ai_chat(message: str, analysis: dict, places_by_cat: dict, lat: float, lng: float,
            ai_available: bool, genai_module=None) -> str:
    """
    رد على سؤال المستخدم - يستخدم AI لو متاح، ويرد ذكي حتى بدون AI
    """
    if ai_available and genai_module:
        try:
            model = genai_module.GenerativeModel('gemini-2.0-flash-exp')
            summary = ", ".join([
                f"{CATEGORIES[k]['name']}({len(v)})"
                for k, v in places_by_cat.items() if len(v) > 0
            ])
            context = f"""موقع: {lat}, {lng}
الأنشطة في المحيط: {summary or 'لا توجد محلات في المحيط القريب'}
نقاط الاستثمار: {analysis['investment_score']}/100
نوع المنطقة: {analysis['area_type']}
طبيعة الحي: {analysis['neighborhood_type']}
مستوى المنافسة: {analysis['competition_level']}
مستوى الحركة: {analysis['traffic_level']}
التوصية: {analysis['recommendation']}

السؤال: {message}

أجب بالعربية بإيجاز ووضوح، مستنداً للأرقام أعلاه فقط."""

            response = model.generate_content(context, request_options={"timeout": 20})
            return response.text.strip()
        except Exception as e:
            pass  # fallback للرد الذكي

    # ====== رد ذكي بدون AI (Rule-based) ======
    return _smart_fallback_chat(message, analysis, places_by_cat)


def _smart_fallback_chat(message: str, analysis: dict, places_by_cat: dict) -> str:
    """رد ذكي بدون AI - يفهم الأسئلة الشائعة"""
    msg = message.lower()

    # كم محل / عدد المحلات
    if any(w in msg for w in ['كم محل', 'عدد المحلات', 'كم عدد']):
        total = analysis['total_places']
        cats = analysis['active_cat_count']
        return f"يوجد {total} محل في المحيط، موزعة على {cats} فئة نشاط."

    # المنافسة
    if any(w in msg for w in ['منافس', 'منافسة', 'كم محل قريب']):
        target = analysis.get('target_cat')
        if target and target in places_by_cat:
            n = len(places_by_cat[target])
            if n == 0:
                return f"ممتاز! لا يوجد منافسون مباشرون في {CATEGORIES[target]['name']} ضمن النطاق المحدد."
            nearest = places_by_cat[target][0]
            return f"يوجد {n} منافسين في {CATEGORIES[target]['name']}. أقربهم: {nearest['name']} على بعد {nearest['dist']:.2f} كم."
        return f"مستوى المنافسة الإجمالي: {analysis['competition_level']}."

    # الفرص
    if any(w in msg for w in ['فرصة', 'فرص', 'اقتراح', 'افضل نشاط', 'أفضل نشاط']):
        opps = analysis.get('opportunities', [])
        if opps:
            return "أفضل الفرص المتاحة في هذا الموقع:\n" + "\n".join(f"• {o}" for o in opps[:3])
        return "تحتاج دراسة ميدانية لتحديد أفضل الفرص."

    # السكان
    if any(w in msg for w in ['سكان', 'كثافة']):
        return f"الكثافة السكانية المقدّرة: {analysis['pop_density']}. التقدير: حوالي {analysis['est_population']:,} نسمة في النطاق."

    # الحركة
    if any(w in msg for w in ['حركة', 'ازدحام', 'زحمة']):
        return f"مستوى حركة المرور: {analysis['traffic_level']}."

    # الوصول
    if any(w in msg for w in ['وصول', 'مواقف', 'موقف']):
        return f"سهولة الوصول: {analysis['accessibility']}. عدد مواقف السيارات المعروفة: {analysis['parking_count']}."

    # النقاط / السكور
    if any(w in msg for w in ['نقاط', 'سكور', 'تقييم', 'درجة']):
        return f"نقاط الاستثمار: {analysis['investment_score']}/100. مستوى المخاطرة: {analysis['risk_level']}."

    # المخاطر
    if any(w in msg for w in ['مخاطر', 'تحذير', 'مشكلة']):
        cautions = analysis.get('cautions', [])
        if cautions:
            return "نقاط الانتباه:\n" + "\n".join(f"⚠️ {c}" for c in cautions)
        return f"مستوى المخاطرة العام: {analysis['risk_level']}."

    # توصية
    if any(w in msg for w in ['توصية', 'رأي', 'نصيحة', 'تنصح']):
        return analysis['recommendation']

    # رد عام
    return (
        f"📊 ملخص الموقع: {analysis['recommendation']}\n\n"
        f"للحصول على تحليل أعمق يمكنك السؤال عن: المنافسة، الفرص، الحركة، السكان، أو المخاطر."
    )
