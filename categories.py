"""
خريطة الفئات الكاملة - مأخوذة من صور التطبيق + إضافات
كل فئة معرّفة بـ OSM tags (Overpass) لتتطابق مع OpenStreetMap
"""

# الفئات الرئيسية - مجمّعة بشكل يطابق صور التطبيق
CATEGORIES = {
    # ========== مطاعم ومقاهي ==========
    "restaurant": {
        "name": "المطاعم",
        "name_en": "Restaurants",
        "icon": "🍽️",
        "color": "#EF4444",
        "group": "food",
        "osm": [("amenity", "restaurant")],
    },
    "fast_food": {
        "name": "الوجبات السريعة",
        "name_en": "Fast Food",
        "icon": "🍔",
        "color": "#F97316",
        "group": "food",
        "osm": [("amenity", "fast_food")],
    },
    "cafe": {
        "name": "المقاهي",
        "name_en": "Cafes",
        "icon": "☕",
        "color": "#A16207",
        "group": "food",
        "osm": [("amenity", "cafe")],
    },
    "delivery": {
        "name": "خدمة التوصيل",
        "name_en": "Delivery",
        "icon": "🛵",
        "color": "#DC2626",
        "group": "food",
        "osm": [("amenity", "food_court")],
    },

    # ========== نشاطات مقترحة (ترفيه/سياحة) ==========
    "park": {
        "name": "المتنزهات",
        "name_en": "Parks",
        "icon": "🌳",
        "color": "#16A34A",
        "group": "leisure",
        "osm": [("leisure", "park"), ("leisure", "garden")],
    },
    "sports_club": {
        "name": "نوادٍ رياضية",
        "name_en": "Sports Clubs",
        "icon": "🏋️",
        "color": "#0EA5E9",
        "group": "leisure",
        "osm": [("leisure", "fitness_centre"), ("leisure", "sports_centre"), ("leisure", "fitness_station")],
    },
    "arts": {
        "name": "فنون",
        "name_en": "Arts",
        "icon": "🎨",
        "color": "#A855F7",
        "group": "leisure",
        "osm": [("amenity", "arts_centre"), ("tourism", "gallery")],
    },
    "tourist_attraction": {
        "name": "معالم الجذب السياحي",
        "name_en": "Tourist Attractions",
        "icon": "🎡",
        "color": "#F59E0B",
        "group": "leisure",
        "osm": [("tourism", "attraction"), ("tourism", "theme_park")],
    },
    "nightlife": {
        "name": "الترفيه الليلي",
        "name_en": "Nightlife",
        "icon": "🌙",
        "color": "#7C3AED",
        "group": "leisure",
        "osm": [("amenity", "nightclub")],
    },
    "museum": {
        "name": "متاحف",
        "name_en": "Museums",
        "icon": "🏛️",
        "color": "#92400E",
        "group": "leisure",
        "osm": [("tourism", "museum")],
    },
    "library": {
        "name": "مكتبات",
        "name_en": "Libraries",
        "icon": "📚",
        "color": "#1E40AF",
        "group": "leisure",
        "osm": [("amenity", "library")],
    },
    "cinema": {
        "name": "الأفلام",
        "name_en": "Cinema",
        "icon": "🎬",
        "color": "#BE185D",
        "group": "leisure",
        "osm": [("amenity", "cinema")],
    },

    # ========== التسوق ==========
    "supermarket": {
        "name": "متاجر البقالة",
        "name_en": "Grocery",
        "icon": "🛒",
        "color": "#F59E0B",
        "group": "shopping",
        "osm": [("shop", "supermarket"), ("shop", "convenience"), ("shop", "grocery")],
    },
    "mall": {
        "name": "مراكز التسوق",
        "name_en": "Malls",
        "icon": "🏬",
        "color": "#8B5CF6",
        "group": "shopping",
        "osm": [("shop", "mall")],
    },
    "beauty": {
        "name": "مستلزمات التجميل",
        "name_en": "Beauty Supplies",
        "icon": "💄",
        "color": "#EC4899",
        "group": "shopping",
        "osm": [("shop", "beauty"), ("shop", "cosmetics"), ("shop", "perfumery")],
    },
    "car_dealer": {
        "name": "تجار سيارات",
        "name_en": "Car Dealers",
        "icon": "🚗",
        "color": "#475569",
        "group": "shopping",
        "osm": [("shop", "car")],
    },
    "electronics": {
        "name": "الأجهزة الإلكترونية",
        "name_en": "Electronics",
        "icon": "💻",
        "color": "#0891B2",
        "group": "shopping",
        "osm": [("shop", "electronics"), ("shop", "mobile_phone"), ("shop", "computer")],
    },
    "home_garden": {
        "name": "منازل وحدائق",
        "name_en": "Home & Garden",
        "icon": "🏡",
        "color": "#65A30D",
        "group": "shopping",
        "osm": [("shop", "furniture"), ("shop", "doityourself"), ("shop", "garden_centre"), ("shop", "houseware")],
    },
    "clothes": {
        "name": "الملابس",
        "name_en": "Clothing",
        "icon": "👕",
        "color": "#DB2777",
        "group": "shopping",
        "osm": [("shop", "clothes"), ("shop", "shoes"), ("shop", "boutique")],
    },
    "sports_goods": {
        "name": "منتجات رياضية",
        "name_en": "Sports Goods",
        "icon": "⚽",
        "color": "#059669",
        "group": "shopping",
        "osm": [("shop", "sports")],
    },
    "convenience": {
        "name": "متاجر صغيرة",
        "name_en": "Convenience Stores",
        "icon": "🏪",
        "color": "#D97706",
        "group": "shopping",
        "osm": [("shop", "convenience"), ("shop", "kiosk")],
    },

    # ========== الخدمات ==========
    "hotel": {
        "name": "الفنادق",
        "name_en": "Hotels",
        "icon": "🏨",
        "color": "#1E3A8A",
        "group": "services",
        "osm": [("tourism", "hotel"), ("tourism", "motel"), ("tourism", "apartment")],
    },
    "atm": {
        "name": "الصراف الآلي",
        "name_en": "ATM",
        "icon": "🏧",
        "color": "#15803D",
        "group": "services",
        "osm": [("amenity", "atm"), ("amenity", "bank")],
    },
    "salon": {
        "name": "مراكز التجميل",
        "name_en": "Beauty Salons",
        "icon": "💇",
        "color": "#E11D48",
        "group": "services",
        "osm": [("shop", "hairdresser"), ("shop", "beauty"), ("amenity", "beauty_salon")],
    },
    "car_rental": {
        "name": "تأجير السيارات",
        "name_en": "Car Rental",
        "icon": "🚙",
        "color": "#4338CA",
        "group": "services",
        "osm": [("amenity", "car_rental")],
    },
    "car_wash": {
        "name": "مغاسل السيارات",
        "name_en": "Car Wash",
        "icon": "🚿",
        "color": "#0284C7",
        "group": "services",
        "osm": [("amenity", "car_wash")],
    },
    "dry_cleaning": {
        "name": "التنظيف الجاف",
        "name_en": "Dry Cleaning",
        "icon": "🧺",
        "color": "#6D28D9",
        "group": "services",
        "osm": [("shop", "dry_cleaning"), ("shop", "laundry")],
    },
    "charging_station": {
        "name": "محطات الشحن",
        "name_en": "Charging Stations",
        "icon": "⚡",
        "color": "#CA8A04",
        "group": "services",
        "osm": [("amenity", "charging_station")],
    },
    "fuel": {
        "name": "وقود",
        "name_en": "Fuel",
        "icon": "⛽",
        "color": "#B91C1C",
        "group": "services",
        "osm": [("amenity", "fuel")],
    },
    "hospital": {
        "name": "مستشفيات وعيادات",
        "name_en": "Hospitals",
        "icon": "🏥",
        "color": "#DC2626",
        "group": "services",
        "osm": [("amenity", "hospital"), ("amenity", "clinic"), ("amenity", "doctors")],
    },
    "post": {
        "name": "البريد والشحن",
        "name_en": "Post & Shipping",
        "icon": "📮",
        "color": "#1D4ED8",
        "group": "services",
        "osm": [("amenity", "post_office"), ("amenity", "post_box")],
    },
    "parking": {
        "name": "مواقف السيارات",
        "name_en": "Parking",
        "icon": "🅿️",
        "color": "#475569",
        "group": "services",
        "osm": [("amenity", "parking")],
    },
    "pharmacy": {
        "name": "صيدليات",
        "name_en": "Pharmacy",
        "icon": "💊",
        "color": "#10B981",
        "group": "services",
        "osm": [("amenity", "pharmacy")],
    },
    "school": {
        "name": "مدارس",
        "name_en": "Schools",
        "icon": "🏫",
        "color": "#0369A1",
        "group": "services",
        "osm": [("amenity", "school"), ("amenity", "kindergarten")],
    },
    "university": {
        "name": "جامعات",
        "name_en": "Universities",
        "icon": "🎓",
        "color": "#1E40AF",
        "group": "services",
        "osm": [("amenity", "university"), ("amenity", "college")],
    },
    "mosque": {
        "name": "المساجد",
        "name_en": "Mosques",
        "icon": "🕌",
        "color": "#047857",
        "group": "services",
        "osm": [("amenity", "place_of_worship")],
    },
}

# مجموعات الفئات (تطابق التابات في الصور)
GROUPS = {
    "food": {"name": "مطاعم ومقاهي", "icon": "🍽️"},
    "leisure": {"name": "نشاطات مقترحة", "icon": "🎯"},
    "shopping": {"name": "التسوّق", "icon": "🛍️"},
    "services": {"name": "الخدمات", "icon": "🛎️"},
}


def get_categories_by_group(group_key):
    """ارجع الفئات حسب المجموعة"""
    return {k: v for k, v in CATEGORIES.items() if v["group"] == group_key}


def build_overpass_query(lat, lng, radius_m, category_keys):
    """
    بناء استعلام Overpass QL لجلب جميع المحلات للفئات المختارة
    """
    parts = []
    for key in category_keys:
        if key not in CATEGORIES:
            continue
        for osm_key, osm_value in CATEGORIES[key]["osm"]:
            parts.append(f'  node["{osm_key}"="{osm_value}"](around:{radius_m},{lat},{lng});')
            parts.append(f'  way["{osm_key}"="{osm_value}"](around:{radius_m},{lat},{lng});')

    query = "[out:json][timeout:60];\n(\n" + "\n".join(parts) + "\n);\nout center tags;"
    return query


def classify_osm_element(tags):
    """
    صنف عنصر OSM إلى أي فئة من فئاتنا ينتمي
    """
    for key, cat in CATEGORIES.items():
        for osm_key, osm_value in cat["osm"]:
            if tags.get(osm_key) == osm_value:
                return key
    return None
