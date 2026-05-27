"""
محرك تحليل المواقع - GBI Saudi (Hybrid v4)
المصادر:
1. Overpass API (OpenStreetMap) - مجاني، استعلام واسع
2. Foursquare Places API - مجاني (50k/شهر)، تغطية ممتازة، Gmail عادي
3. Google Places API - اختياري (يحتاج CNTXT للسعوديين)
"""

import os
import re
import math
import json
import time
import requests
from typing import Optional
from categories import CATEGORIES, classify_osm_element


# ============================================================
# 1) استخراج الإحداثيات
# ============================================================
def extract_coords(url: str):
    if not url:
        return None, None
    url = url.strip()

    direct = re.match(r'^\s*(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)\s*$', url)
    if direct:
        return float(direct.group(1)), float(direct.group(2))

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
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
            except ValueError:
                continue
    return None, None


# ============================================================
# 2) Haversine
# ============================================================
def dist_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ============================================================
# 3) Overpass - استعلام واسع
# ============================================================
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def build_broad_overpass_query(lat: float, lng: float, radius_m: int) -> str:
    """استعلام واسع يجلب أي محل في المنطقة (يحل مشكلة بيانات OSM الناقصة)"""
    return f"""[out:json][timeout:90];
(
  node["shop"](around:{radius_m},{lat},{lng});
  way["shop"](around:{radius_m},{lat},{lng});
  node["amenity"](around:{radius_m},{lat},{lng});
  way["amenity"](around:{radius_m},{lat},{lng});
  node["tourism"](around:{radius_m},{lat},{lng});
  way["tourism"](around:{radius_m},{lat},{lng});
  node["leisure"](around:{radius_m},{lat},{lng});
  way["leisure"](around:{radius_m},{lat},{lng});
  node["office"](around:{radius_m},{lat},{lng});
  way["office"](around:{radius_m},{lat},{lng});
  node["craft"](around:{radius_m},{lat},{lng});
  way["craft"](around:{radius_m},{lat},{lng});
  node["healthcare"](around:{radius_m},{lat},{lng});
  way["healthcare"](around:{radius_m},{lat},{lng});
);
out center tags;"""


def fetch_overpass(lat: float, lng: float, radius_km: float):
    radius_m = int(radius_km * 1000)
    query = build_broad_overpass_query(lat, lng, radius_m)

    for server in OVERPASS_SERVERS:
        try:
            r = requests.post(
                server, data={'data': query},
                timeout=90,
                headers={'User-Agent': 'GBI-Saudi/3.0'}
            )
            if r.status_code == 200 and r.text.strip().startswith('{'):
                return r.json().get('elements', []), None
            elif r.status_code == 429:
                time.sleep(3)
                continue
        except Exception:
            continue
        time.sleep(1)
    return [], "كل سيرفرات Overpass فشلت"


# ============================================================
# 4) Google Places API
# ============================================================
def google_type_to_category(types: list, name: str = "") -> Optional[str]:
    """تحويل Google Places types إلى فئتنا"""
    name_lower = name.lower()
    type_map = {
        "restaurant": "restaurant", "meal_takeaway": "restaurant", "meal_delivery": "delivery",
        "cafe": "cafe", "bakery": "cafe",
        "bar": "fast_food", "night_club": "nightlife",
        "supermarket": "supermarket", "grocery_or_supermarket": "supermarket",
        "convenience_store": "convenience",
        "shopping_mall": "mall",
        "clothing_store": "clothes", "shoe_store": "clothes",
        "department_store": "mall", "store": "convenience",
        "electronics_store": "electronics",
        "furniture_store": "home_garden", "hardware_store": "home_garden",
        "florist": "home_garden",
        "book_store": "library",
        "jewelry_store": "beauty",
        "pharmacy": "pharmacy",
        "hospital": "hospital", "doctor": "hospital", "dentist": "hospital", "veterinary_care": "hospital",
        "atm": "atm", "bank": "atm",
        "post_office": "post",
        "gas_station": "fuel",
        "car_repair": "car_wash", "car_wash": "car_wash",
        "car_dealer": "car_dealer", "car_rental": "car_rental",
        "lodging": "hotel",
        "tourist_attraction": "tourist_attraction", "museum": "museum",
        "park": "park",
        "gym": "sports_club",
        "spa": "salon", "beauty_salon": "salon", "hair_care": "salon",
        "laundry": "dry_cleaning",
        "school": "school", "university": "university",
        "mosque": "mosque", "place_of_worship": "mosque",
        "library": "library",
        "movie_theater": "cinema",
        "parking": "parking",
    }
    for t in types:
        if t in type_map:
            return type_map[t]

    # محاولة من الاسم
    if any(w in name_lower for w in ['مطعم', 'restaurant', 'مطاعم']):
        return 'restaurant'
    if any(w in name_lower for w in ['كافيه', 'قهوة', 'cafe', 'coffee', 'مقهى']):
        return 'cafe'
    if any(w in name_lower for w in ['صيدلية', 'pharmacy', 'النهدي', 'الدواء']):
        return 'pharmacy'
    if any(w in name_lower for w in ['بقالة', 'بنده', 'لولو', 'كارفور', 'هايبر', 'تموينات']):
        return 'supermarket'
    if any(w in name_lower for w in ['ماكدونالدز', 'برغر', 'كنتاكي', 'الباك', 'بيتزا', 'pizza', 'burger']):
        return 'fast_food'
    return None


def fetch_google_places(lat: float, lng: float, radius_km: float, api_key: str):
    """جلب الأماكن من Google Places API"""
    if not api_key:
        return [], "لا يوجد مفتاح Google"

    radius_m = min(int(radius_km * 1000), 50000)
    all_results = []
    seen_ids = set()

    type_groups = [
        "restaurant", "cafe", "bakery",
        "supermarket", "convenience_store", "shopping_mall",
        "clothing_store", "electronics_store",
        "pharmacy", "hospital",
        "atm", "bank",
        "gas_station", "car_repair", "car_wash",
        "lodging", "tourist_attraction",
        "gym", "beauty_salon", "hair_care",
        "school", "mosque",
        "parking", "movie_theater", "park",
    ]

    for ptype in type_groups:
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius_m,
                "type": ptype,
                "key": api_key,
                "language": "ar",
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get("status") in ("REQUEST_DENIED", "INVALID_REQUEST"):
                return all_results, data.get("error_message", data.get("status"))

            for result in data.get("results", []):
                pid = result.get("place_id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                all_results.append(result)

            # next_page_token
            next_token = data.get("next_page_token")
            if next_token:
                time.sleep(2)
                r2 = requests.get(url, params={"pagetoken": next_token, "key": api_key}, timeout=15)
                if r2.status_code == 200:
                    for result in r2.json().get("results", []):
                        pid = result.get("place_id")
                        if pid not in seen_ids:
                            seen_ids.add(pid)
                            all_results.append(result)
        except Exception:
            continue

    return all_results, None


# ============================================================
# 5) Text Search من Google (يجلب نتائج أكثر بـ keywords عربية)
# ============================================================
def fetch_google_text_search(lat: float, lng: float, radius_km: float, api_key: str):
    """بحث نصي بكلمات عربية شائعة للحصول على تغطية أفضل"""
    if not api_key:
        return []

    queries = [
        "مطعم", "كافيه", "مقهى", "وجبات سريعة",
        "صيدلية", "سوبر ماركت", "بقالة", "محل",
        "مغسلة سيارات", "مغسلة", "تجميل", "حلاق",
        "ATM", "صراف", "بنك", "محطة وقود",
        "مستشفى", "عيادة", "صالون",
    ]

    radius_m = min(int(radius_km * 1000), 50000)
    all_results = []
    seen_ids = set()

    for query in queries:
        try:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                "query": query,
                "location": f"{lat},{lng}",
                "radius": radius_m,
                "key": api_key,
                "language": "ar",
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            for result in data.get("results", []):
                pid = result.get("place_id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                # تحقق المسافة قبل الإضافة
                geo = result.get("geometry", {}).get("location", {})
                plat = geo.get("lat")
                plng = geo.get("lng")
                if plat and plng:
                    d = dist_km(lat, lng, plat, plng)
                    if d <= radius_km:
                        all_results.append(result)
        except Exception:
            continue

    return all_results


# ============================================================
# 5.5) Foursquare Places API - البديل الأفضل (مجاني 50k/شهر)
# ============================================================
FOURSQUARE_CATEGORIES = {
    # Foursquare category IDs → category key in our system
    # Reference: https://docs.foursquare.com/data-products/docs/categories
    13065: "restaurant",      # Restaurant
    13035: "cafe",            # Café
    13145: "fast_food",       # Fast Food Restaurant
    13002: "fast_food",       # Bakery
    17069: "supermarket",     # Supermarket
    17070: "convenience",     # Convenience Store
    17114: "mall",            # Shopping Mall
    17027: "clothes",         # Clothing Store
    17035: "clothes",         # Shoe Store
    17043: "electronics",     # Electronics Store
    17082: "home_garden",     # Furniture Store
    17085: "beauty",          # Cosmetics Store
    17018: "beauty",          # Jewelry Store
    17120: "sports_goods",    # Sporting Goods Shop
    11045: "pharmacy",        # Pharmacy
    15014: "hospital",        # Hospital
    15016: "hospital",        # Medical Center
    11044: "atm",             # ATM / Bank
    19009: "fuel",            # Gas Station
    19014: "car_wash",        # Car Wash
    19015: "car_dealer",      # Car Dealership
    19018: "car_rental",      # Car Rental
    19013: "hotel",           # Hotel (corrected)
    19021: "hotel",           # Resort
    16031: "tourist_attraction",  # Tourist Attraction
    10027: "museum",          # Museum
    16032: "park",            # Park
    18021: "sports_club",     # Gym / Fitness Center
    11062: "salon",           # Beauty Salon
    11063: "salon",           # Barber Shop
    11058: "dry_cleaning",    # Laundry Service
    12058: "school",          # School
    12061: "university",      # University
    14005: "mosque",          # Mosque
    12064: "library",         # Library
    10024: "cinema",          # Movie Theater
    10032: "nightlife",       # Nightclub
    19022: "parking",         # Parking
    13000: "restaurant",      # Food generic
    17000: "convenience",     # Retail generic
}


def foursquare_category_to_ours(fsq_categories: list, name: str = "") -> Optional[str]:
    """تحويل فئات Foursquare إلى فئاتنا"""
    name_lower = name.lower() if name else ""

    # ابحث في الـ category IDs
    for cat in fsq_categories:
        cat_id = cat.get('id')
        if cat_id in FOURSQUARE_CATEGORIES:
            return FOURSQUARE_CATEGORIES[cat_id]

        # ابحث بالاسم لو ما طابق ID
        cat_name = (cat.get('name', '') or '').lower()
        if 'restaurant' in cat_name or 'مطعم' in cat_name:
            return 'restaurant'
        if 'cafe' in cat_name or 'café' in cat_name or 'coffee' in cat_name or 'مقهى' in cat_name:
            return 'cafe'
        if 'fast food' in cat_name or 'burger' in cat_name or 'pizza' in cat_name:
            return 'fast_food'
        if 'pharmacy' in cat_name or 'صيدلية' in cat_name:
            return 'pharmacy'
        if 'super' in cat_name or 'grocery' in cat_name or 'بقالة' in cat_name:
            return 'supermarket'
        if 'mall' in cat_name or 'shopping center' in cat_name:
            return 'mall'
        if 'clothing' in cat_name or 'shoe' in cat_name or 'fashion' in cat_name:
            return 'clothes'
        if 'electronic' in cat_name or 'mobile' in cat_name:
            return 'electronics'
        if 'gas' in cat_name or 'fuel' in cat_name or 'بنزين' in cat_name:
            return 'fuel'
        if 'atm' in cat_name or 'bank' in cat_name or 'صراف' in cat_name:
            return 'atm'
        if 'hotel' in cat_name or 'فندق' in cat_name:
            return 'hotel'
        if 'car wash' in cat_name or 'مغسلة' in cat_name:
            return 'car_wash'
        if 'gym' in cat_name or 'fitness' in cat_name or 'نادي' in cat_name:
            return 'sports_club'
        if 'salon' in cat_name or 'barber' in cat_name or 'beauty' in cat_name:
            return 'salon'
        if 'hospital' in cat_name or 'clinic' in cat_name or 'doctor' in cat_name:
            return 'hospital'
        if 'school' in cat_name or 'مدرسة' in cat_name:
            return 'school'
        if 'mosque' in cat_name or 'مسجد' in cat_name:
            return 'mosque'
        if 'park' in cat_name or 'حديقة' in cat_name:
            return 'park'
        if 'parking' in cat_name or 'موقف' in cat_name:
            return 'parking'

    # محاولة أخيرة من اسم المكان نفسه
    if 'مطعم' in name_lower or 'restaurant' in name_lower:
        return 'restaurant'
    if 'كافيه' in name_lower or 'قهوة' in name_lower or 'cafe' in name_lower or 'مقهى' in name_lower:
        return 'cafe'
    if 'صيدلية' in name_lower or 'النهدي' in name_lower or 'الدواء' in name_lower:
        return 'pharmacy'
    if 'بنده' in name_lower or 'لولو' in name_lower or 'كارفور' in name_lower or 'العثيم' in name_lower or 'تموينات' in name_lower:
        return 'supermarket'
    if 'ماكدونالدز' in name_lower or 'كنتاكي' in name_lower or 'الباك' in name_lower or 'هرفي' in name_lower:
        return 'fast_food'

    return None


def fetch_foursquare(lat: float, lng: float, radius_km: float, api_key: str):
    """
    جلب الأماكن من Foursquare Places API
    - مجاني 50,000 طلب شهرياً
    - تغطيته ممتازة في السعودية
    - يقبل Gmail عادي بدون CNTXT
    """
    if not api_key:
        return [], "لا يوجد مفتاح Foursquare"

    radius_m = min(int(radius_km * 1000), 100000)  # حد Foursquare 100km

    all_results = []
    seen_ids = set()

    # نبحث بفئات مختلفة لضمان التغطية الشاملة
    # Category IDs من Foursquare docs
    category_groups = [
        "13065,13145,13035,13002",      # Food (restaurant, fast_food, cafe, bakery)
        "17069,17070,17114",             # Shopping core (supermarket, convenience, mall)
        "17027,17035,17043,17082",       # Retail (clothes, shoes, electronics, furniture)
        "17085,17018,17120",             # Specialty (cosmetics, jewelry, sports)
        "11045,15014,15016",             # Health (pharmacy, hospital, medical)
        "11044,19009",                   # Services (ATM, gas station)
        "19014,19015,19018",             # Auto (wash, dealer, rental)
        "16031,10027,16032",             # Leisure (attraction, museum, park)
        "18021,11062,11063,11058",       # Personal (gym, salon, barber, laundry)
        "12058,12061,12064,14005",       # Edu/religious (school, uni, library, mosque)
        "10024,10032,19022",             # Entertainment (cinema, nightclub, parking)
    ]

    # ============================================================
    # ملاحظة: نستخدم الـ endpoint الجديد places-api.foursquare.com
    # القديم api.foursquare.com/v3 أصبح deprecated وقد يعطي 410
    # المفاتيح الجديدة تعمل فقط مع الـ endpoint الجديد
    # ============================================================
    NEW_URL = "https://places-api.foursquare.com/places/search"
    headers_common = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Places-Api-Version": "2025-06-17",
    }

    for cat_str in category_groups:
        try:
            params = {
                "ll": f"{lat},{lng}",
                "radius": radius_m,
                "fsq_category_ids": cat_str,   # اسم الـ parameter تغيّر في الجديد
                "limit": 50,
                "sort": "DISTANCE",
                "fields": "fsq_place_id,name,location,categories,latitude,longitude,distance,rating,stats",
            }
            r = requests.get(NEW_URL, params=params, headers=headers_common, timeout=20)
            if r.status_code == 200:
                data = r.json()
                for place in data.get("results", []):
                    # الجديد يستخدم fsq_place_id بدل fsq_id
                    pid = place.get("fsq_place_id") or place.get("fsq_id")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_results.append(place)
            elif r.status_code == 401:
                return all_results, "مفتاح Foursquare غير صالح (401)"
            elif r.status_code == 410:
                # الـ endpoint القديم - تجاهل ولا تكرر المحاولة
                return all_results, "Foursquare: endpoint قديم"
            elif r.status_code == 429:
                time.sleep(2)
        except Exception:
            continue

    # بحث نصي إضافي بكلمات عربية شائعة (يحصل المحلات السعودية بدقة)
    text_queries = [
        "مطعم", "كافيه", "قهوة", "صيدلية", "بقالة", "سوبر ماركت",
        "مغسلة", "صالون", "ATM", "محطة وقود", "حلاق", "تجميل",
    ]

    for query in text_queries:
        try:
            params = {
                "ll": f"{lat},{lng}",
                "radius": radius_m,
                "query": query,
                "limit": 50,
                "fields": "fsq_place_id,name,location,categories,latitude,longitude,distance,rating,stats",
            }
            r = requests.get(NEW_URL, params=params, headers=headers_common, timeout=15)
            if r.status_code == 200:
                for place in r.json().get("results", []):
                    pid = place.get("fsq_place_id") or place.get("fsq_id")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_results.append(place)
        except Exception:
            continue

    return all_results, None


# ============================================================
# 6) دمج النتائج
# ============================================================
def merge_and_process(osm_elements: list, google_places: list, foursquare_places: list,
                      target_lat: float, target_lng: float, max_km: float):
    """دمج كل النتائج من المصادر الثلاثة وتصنيفها"""
    by_cat = {}
    seen_coords = set()
    seen_names = set()

    # ===== OSM =====
    for el in osm_elements:
        tags = el.get('tags', {})
        if not tags:
            continue

        if el.get('type') == 'node':
            plat = el.get('lat')
            plng = el.get('lon')
        else:
            center = el.get('center', {})
            plat = center.get('lat')
            plng = center.get('lon')

        if not plat or not plng:
            continue

        key = (round(plat, 4), round(plng, 4))
        if key in seen_coords:
            continue

        d = dist_km(target_lat, target_lng, plat, plng)
        if d > max_km:
            continue

        cat_key = classify_osm_element(tags)
        if not cat_key:
            name_full = (tags.get('name', '') + ' ' + tags.get('brand', '')).lower()
            cat_key = google_type_to_category([], name_full)
            if not cat_key:
                continue

        name = (tags.get('name:ar') or tags.get('name') or tags.get('name:en') or '').strip()
        if not name:
            name = f"({CATEGORIES[cat_key]['name']} بدون اسم)"

        seen_coords.add(key)
        norm_name = name.lower().strip()
        if norm_name in seen_names and not name.startswith('('):
            continue
        seen_names.add(norm_name)

        addr_parts = []
        for k in ('addr:street', 'addr:district', 'addr:city'):
            v = tags.get(k)
            if v:
                addr_parts.append(v)
        addr = " - ".join(addr_parts)

        brand = tags.get('brand') or tags.get('operator') or ''

        by_cat.setdefault(cat_key, []).append({
            'name': name, 'cat': cat_key,
            'lat': plat, 'lng': plng, 'dist': d,
            'addr': addr, 'brand': brand,
            'rating': 0, 'user_ratings': 0,
            'source': 'osm',
        })

    # ===== Google =====
    for place in google_places:
        geo = place.get("geometry", {}).get("location", {})
        plat = geo.get("lat")
        plng = geo.get("lng")
        if not plat or not plng:
            continue

        key = (round(plat, 4), round(plng, 4))
        if key in seen_coords:
            continue

        d = dist_km(target_lat, target_lng, plat, plng)
        if d > max_km:
            continue

        name = place.get("name", "").strip()
        types = place.get("types", [])
        cat_key = google_type_to_category(types, name)
        if not cat_key:
            continue

        norm_name = name.lower().strip()
        if norm_name in seen_names:
            continue

        seen_coords.add(key)
        seen_names.add(norm_name)

        by_cat.setdefault(cat_key, []).append({
            'name': name, 'cat': cat_key,
            'lat': plat, 'lng': plng, 'dist': d,
            'addr': place.get("vicinity", ""),
            'brand': '',
            'rating': place.get("rating", 0),
            'user_ratings': place.get("user_ratings_total", 0),
            'source': 'google',
        })

    # ===== Foursquare =====
    for place in foursquare_places:
        # الـ API الجديد يضع latitude/longitude مباشرة في الـ root
        # القديم كان يضعها في geocodes.main
        plat = place.get("latitude")
        plng = place.get("longitude")

        # fallback للـ API القديم لو ظهر
        if not plat or not plng:
            geocodes = place.get("geocodes", {}) or {}
            main = geocodes.get("main", {}) or {}
            plat = main.get("latitude")
            plng = main.get("longitude")

        # fallback إضافي للـ location object
        if not plat or not plng:
            loc = place.get("location", {}) or {}
            plat = loc.get("latitude") or loc.get("lat")
            plng = loc.get("longitude") or loc.get("lng")

        if not plat or not plng:
            continue

        key = (round(plat, 4), round(plng, 4))
        if key in seen_coords:
            continue

        d = dist_km(target_lat, target_lng, plat, plng)
        if d > max_km:
            continue

        name = (place.get("name") or "").strip()
        if not name:
            continue

        cats = place.get("categories", []) or []
        cat_key = foursquare_category_to_ours(cats, name)
        if not cat_key:
            continue

        norm_name = name.lower().strip()
        if norm_name in seen_names:
            continue

        seen_coords.add(key)
        seen_names.add(norm_name)

        # العنوان
        loc = place.get("location", {}) or {}
        addr_parts = []
        for k in ('address', 'locality', 'region'):
            v = loc.get(k)
            if v:
                addr_parts.append(v)
        addr = " - ".join(addr_parts) if addr_parts else loc.get("formatted_address", "")

        # التقييم
        rating = place.get("rating", 0) or 0
        stats = place.get("stats", {}) or {}
        total_ratings = stats.get("total_ratings", 0) or 0

        by_cat.setdefault(cat_key, []).append({
            'name': name, 'cat': cat_key,
            'lat': plat, 'lng': plng, 'dist': d,
            'addr': addr,
            'brand': '',
            'rating': rating,
            'user_ratings': total_ratings,
            'source': 'foursquare',
        })

    for cat_key in by_cat:
        by_cat[cat_key].sort(key=lambda x: x['dist'])
    return by_cat


# ============================================================
# 7) الواجهة الموحدة
# ============================================================
def fetch_all_places(lat: float, lng: float, radius_km: float,
                     google_api_key: Optional[str] = None,
                     foursquare_api_key: Optional[str] = None):
    """جلب من كل المصادر المتاحة (OSM + Google + Foursquare)"""
    osm_elements = []
    google_places = []
    foursquare_places = []
    errors = []
    sources_used = []

    # 1) Overpass (OSM)
    osm_elements, osm_err = fetch_overpass(lat, lng, radius_km)
    if osm_elements:
        sources_used.append(f"OpenStreetMap ({len(osm_elements)} عنصر)")
    if osm_err:
        errors.append(f"OSM: {osm_err}")

    # 2) Foursquare (الأفضل للسعودية - مجاني وبسيط)
    if foursquare_api_key:
        foursquare_places, fsq_err = fetch_foursquare(lat, lng, radius_km, foursquare_api_key)
        if foursquare_places:
            sources_used.append(f"Foursquare ({len(foursquare_places)} مكان)")
        if fsq_err:
            errors.append(f"Foursquare: {fsq_err}")

    # 3) Google Places (لو وفّر مفتاحاً - معقد للسعوديين بسبب CNTXT)
    if google_api_key:
        nearby, gerr = fetch_google_places(lat, lng, radius_km, google_api_key)
        text_results = fetch_google_text_search(lat, lng, radius_km, google_api_key)
        seen_ids = set()
        for p in nearby + text_results:
            pid = p.get("place_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                google_places.append(p)
        if google_places:
            sources_used.append(f"Google Places ({len(google_places)} مكان)")
        if gerr:
            errors.append(f"Google: {gerr}")

    # دمج
    by_cat = merge_and_process(osm_elements, google_places, foursquare_places,
                               lat, lng, radius_km)

    return {
        'places_by_cat': by_cat,
        'sources_used': sources_used,
        'errors': errors,
        'osm_count': len(osm_elements),
        'google_count': len(google_places),
        'foursquare_count': len(foursquare_places),
    }


# ============================================================
# 8) خوارزمية التحليل (Rule-based)
# ============================================================
def analyze_location(places_by_cat: dict, radius_km: float, target_cat: Optional[str] = None) -> dict:
    total_places = sum(len(v) for v in places_by_cat.values())
    active_cat_count = len([v for v in places_by_cat.values() if len(v) > 0])

    area_km2 = math.pi * (radius_km ** 2)
    density = total_places / area_km2 if area_km2 > 0 else 0

    if total_places == 0:
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
    neighborhood_type = max(culture_scores, key=culture_scores.get) if total_places > 0 else "غير محدد"

    if target_cat:
        competitor_count = len(places_by_cat.get(target_cat, []))
        if competitor_count == 0:
            competition_level, competition_score = "لا منافسة", 100
        elif competitor_count <= 2:
            competition_level, competition_score = "منخفض", 75
        elif competitor_count <= 5:
            competition_level, competition_score = "متوسط", 50
        elif competitor_count <= 10:
            competition_level, competition_score = "مرتفع", 25
        else:
            competition_level, competition_score = "مرتفع جداً", 10
    else:
        if active_cat_count == 0:
            competition_level, competition_score = "منخفض", 80
        elif total_places / max(active_cat_count, 1) < 3:
            competition_level, competition_score = "منخفض", 75
        elif total_places / max(active_cat_count, 1) < 7:
            competition_level, competition_score = "متوسط", 55
        else:
            competition_level, competition_score = "مرتفع", 30
        competitor_count = 0

    parking_count = len(places_by_cat.get('parking', []))
    fuel_count = len(places_by_cat.get('fuel', []))

    if parking_count >= 3 and fuel_count >= 1:
        accessibility, accessibility_score = "ممتازة", 90
    elif parking_count >= 1:
        accessibility, accessibility_score = "جيدة", 70
    elif fuel_count >= 1 or total_places > 10:
        accessibility, accessibility_score = "متوسطة", 55
    else:
        accessibility, accessibility_score = "تحتاج تحقق", 40

    traffic_indicator = food_count * 2 + shopping_count * 1.5 + leisure_count
    if traffic_indicator >= 30:
        traffic_level, traffic_score = "عالية جداً", 95
    elif traffic_indicator >= 15:
        traffic_level, traffic_score = "عالية", 80
    elif traffic_indicator >= 7:
        traffic_level, traffic_score = "متوسطة", 60
    elif traffic_indicator >= 2:
        traffic_level, traffic_score = "منخفضة", 40
    else:
        traffic_level, traffic_score = "منخفضة جداً", 20

    pop_indicator = (
        len(places_by_cat.get('mosque', [])) * 3
        + len(places_by_cat.get('school', [])) * 5
        + len(places_by_cat.get('supermarket', [])) * 4
    )
    if pop_indicator >= 25:
        pop_density, pop_score = "عالية", 90
    elif pop_indicator >= 12:
        pop_density, pop_score = "متوسطة", 65
    elif pop_indicator >= 4:
        pop_density, pop_score = "منخفضة", 40
    else:
        pop_density, pop_score = "قليلة", 20

    est_population = max(1000, pop_indicator * 350) if pop_indicator > 0 else 0

    if target_cat:
        suitability = _calc_suitability(target_cat, places_by_cat, neighborhood_type)
        investment_score = int(
            competition_score * 0.30 + traffic_score * 0.25
            + accessibility_score * 0.15 + suitability * 0.20
            + pop_score * 0.10
        )
    else:
        investment_score = int(
            traffic_score * 0.30 + accessibility_score * 0.20
            + pop_score * 0.25 + competition_score * 0.15
            + min(active_cat_count * 5, 100) * 0.10
        )

    opportunities = []
    missing_services = []
    essential = {
        'pharmacy': "صيدلية - خدمة أساسية مفقودة",
        'supermarket': "بقالة/سوبر ماركت",
        'atm': "صراف آلي",
        'fuel': "محطة وقود",
    }
    for key, label in essential.items():
        if len(places_by_cat.get(key, [])) == 0:
            missing_services.append(label)

    opp_by_culture = {
        'عائلي': ['مطعم عائلي', 'سوبر ماركت', 'مركز ترفيه أطفال', 'مدرسة خاصة'],
        'شبابي': ['كافيه متخصص', 'مطعم وجبات سريعة', 'صالة رياضية', 'محل إلكترونيات'],
        'تجاري': ['مكتب خدمات', 'مطعم سريع للموظفين', 'مقهى عمل', 'مغسلة سيارات'],
        'سياحي': ['مطعم تجربة', 'متجر هدايا', 'كافيه ذو إطلالة', 'خدمات تأجير'],
        'طعام': ['نشاط متخصص (حلويات/مخبز)', 'مقهى بمفهوم مختلف', 'مطبخ سحابي'],
    }
    base_opps = opp_by_culture.get(neighborhood_type, ['دراسة ميدانية للموقع'])
    opportunities.extend(base_opps)

    top_competitors = []
    if target_cat and target_cat in places_by_cat:
        for p in places_by_cat[target_cat][:5]:
            top_competitors.append({
                'name': p['name'], 'dist': round(p['dist'], 2),
                'brand': p.get('brand', ''), 'rating': p.get('rating', 0),
            })

    if investment_score >= 75:
        recommendation = f"موقع ممتاز! فرصة استثمارية قوية في {area_type}. الحركة {traffic_level} ومستوى المنافسة {competition_level}."
        risk_level = "منخفض"
    elif investment_score >= 55:
        recommendation = f"موقع جيد بإمكانيات واعدة. {area_type} مع منافسة {competition_level}. يُنصح بدراسة ميدانية قبل الالتزام."
        risk_level = "متوسط"
    elif investment_score >= 35:
        recommendation = f"موقع متوسط - يحتاج دراسة دقيقة. النشاط محدود ({total_places} محل في {radius_km} كم)."
        risk_level = "متوسط-عالي"
    else:
        recommendation = f"منطقة قليلة النشاط - تحتاج دراسة متعمقة. {total_places} محل فقط في {radius_km} كم."
        risk_level = "عالي"

    strengths, cautions = [], []
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


def _calc_suitability(target_cat, places_by_cat, neighborhood_type):
    m = {
        'restaurant': {'عائلي': 90, 'شبابي': 80, 'تجاري': 85, 'سياحي': 95, 'طعام': 60, 'خدمي': 70},
        'cafe': {'عائلي': 70, 'شبابي': 95, 'تجاري': 90, 'سياحي': 85, 'طعام': 75, 'خدمي': 60},
        'fast_food': {'عائلي': 75, 'شبابي': 95, 'تجاري': 85, 'سياحي': 70, 'طعام': 60, 'خدمي': 70},
        'pharmacy': {'عائلي': 95, 'شبابي': 70, 'تجاري': 75, 'سياحي': 60, 'طعام': 50, 'خدمي': 90},
        'supermarket': {'عائلي': 95, 'شبابي': 75, 'تجاري': 70, 'سياحي': 50, 'طعام': 60, 'خدمي': 80},
        'car_wash': {'عائلي': 80, 'شبابي': 75, 'تجاري': 85, 'سياحي': 50, 'طعام': 40, 'خدمي': 90},
        'beauty': {'عائلي': 85, 'شبابي': 90, 'تجاري': 80, 'سياحي': 70, 'طعام': 50, 'خدمي': 75},
        'clothes': {'عائلي': 80, 'شبابي': 90, 'تجاري': 85, 'سياحي': 80, 'طعام': 50, 'خدمي': 60},
    }
    return m.get(target_cat, {}).get(neighborhood_type, 70)


def suggest_best_activity(places_by_cat: dict, analysis: dict) -> list:
    neighborhood = analysis['neighborhood_type']
    total = analysis['total_places']

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
        saturation = min(100, (existing / cap) * 100) if cap > 0 else 100
        opportunity = max(0, demand - saturation * 0.7)
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
# 9) AI
# ============================================================
def ai_enhance_analysis(analysis, places_by_cat, lat, lng, ai_available, genai_module=None):
    if not ai_available or not genai_module:
        return analysis
    try:
        model = genai_module.GenerativeModel('gemini-2.0-flash-exp')
        summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in places_by_cat.items() if len(v) > 0])

        prompt = f"""أنت خبير تحليل مواقع تجارية في السعودية. حلل هذا الموقع:
- الإحداثيات: {lat}, {lng}
- الأنشطة المحيطة: {summary}
- نوع الحي: {analysis['neighborhood_type']}
- نقاط الاستثمار: {analysis['investment_score']}/100

أعد JSON فقط:
{{"ai_recommendation":"توصية محسّنة","best_activities":["نشاط 1","نشاط 2","نشاط 3"],"key_risks":["مخاطرة 1","مخاطرة 2"],"growth_potential":"منخفض/متوسط/عالي"}}"""

        response = model.generate_content(prompt, request_options={"timeout": 20})
        text = response.text.strip()
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        ai_data = json.loads(text.strip())
        analysis['ai_recommendation'] = ai_data.get('ai_recommendation', '')
        analysis['ai_best_activities'] = ai_data.get('best_activities', [])
        analysis['ai_key_risks'] = ai_data.get('key_risks', [])
        analysis['ai_growth_potential'] = ai_data.get('growth_potential', 'متوسط')
        analysis['ai_enhanced'] = True
    except Exception as e:
        analysis['ai_enhanced'] = False
        analysis['ai_error'] = str(e)[:100]
    return analysis


def ai_chat(message, analysis, places_by_cat, lat, lng, ai_available, genai_module=None):
    if ai_available and genai_module:
        try:
            model = genai_module.GenerativeModel('gemini-2.0-flash-exp')
            summary = ", ".join([f"{CATEGORIES[k]['name']}({len(v)})" for k, v in places_by_cat.items() if len(v) > 0])
            context = f"""موقع: {lat}, {lng}
الأنشطة في المحيط: {summary or 'لا توجد محلات'}
نقاط الاستثمار: {analysis['investment_score']}/100
نوع المنطقة: {analysis['area_type']}
طبيعة الحي: {analysis['neighborhood_type']}
مستوى المنافسة: {analysis['competition_level']}
مستوى الحركة: {analysis['traffic_level']}
التوصية: {analysis['recommendation']}

السؤال: {message}

أجب بالعربية بإيجاز ووضوح."""
            response = model.generate_content(context, request_options={"timeout": 20})
            return response.text.strip()
        except Exception:
            pass
    return _smart_fallback_chat(message, analysis, places_by_cat)


def _smart_fallback_chat(message, analysis, places_by_cat):
    msg = message.lower()

    if any(w in msg for w in ['كم محل', 'عدد المحلات', 'كم عدد']):
        return f"يوجد {analysis['total_places']} محل في المحيط، موزعة على {analysis['active_cat_count']} فئة نشاط."

    if any(w in msg for w in ['منافس', 'منافسة', 'مافيه ولا محل', 'محل قريب']):
        target = analysis.get('target_cat')
        if target and target in places_by_cat:
            n = len(places_by_cat[target])
            if n == 0:
                return f"ممتاز! لا يوجد منافسون مباشرون في {CATEGORIES[target]['name']} ضمن النطاق."
            nearest = places_by_cat[target][0]
            return f"يوجد {n} منافسين في {CATEGORIES[target]['name']}. أقربهم: {nearest['name']} على بعد {nearest['dist']:.2f} كم."
        return f"مستوى المنافسة الإجمالي: {analysis['competition_level']}."

    if any(w in msg for w in ['فرصة', 'فرص', 'اقتراح', 'افضل نشاط', 'أفضل نشاط']):
        opps = analysis.get('opportunities', [])
        if opps:
            return "أفضل الفرص المتاحة:\n" + "\n".join(f"• {o}" for o in opps[:3])
        return "تحتاج دراسة ميدانية لتحديد أفضل الفرص."

    if any(w in msg for w in ['سكان', 'كثافة']):
        return f"الكثافة السكانية المقدّرة: {analysis['pop_density']}. التقدير: حوالي {analysis['est_population']:,} نسمة."

    if any(w in msg for w in ['حركة', 'ازدحام', 'زحمة']):
        return f"مستوى حركة المرور: {analysis['traffic_level']}."

    if any(w in msg for w in ['وصول', 'مواقف', 'موقف']):
        return f"سهولة الوصول: {analysis['accessibility']}. عدد المواقف المعروفة: {analysis['parking_count']}."

    if any(w in msg for w in ['نقاط', 'سكور', 'تقييم', 'درجة']):
        return f"نقاط الاستثمار: {analysis['investment_score']}/100. مستوى المخاطرة: {analysis['risk_level']}."

    if any(w in msg for w in ['مخاطر', 'تحذير']):
        c = analysis.get('cautions', [])
        if c:
            return "نقاط الانتباه:\n" + "\n".join(f"⚠️ {x}" for x in c)
        return f"مستوى المخاطرة: {analysis['risk_level']}."

    if any(w in msg for w in ['توصية', 'رأي', 'نصيحة', 'تنصح']):
        return analysis['recommendation']

    return f"📊 ملخص: {analysis['recommendation']}\n\nاسأل عن: المنافسة، الفرص، الحركة، السكان، أو المخاطر."
