"""
رفع بيانات OSM السعودية إلى Supabase - النسخة المبسطة
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 60)
print("🚀 رفع بيانات السعودية إلى Supabase")
print("=" * 60)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ تأكد من SUPABASE_URL و SUPABASE_KEY في .env")
    exit(1)

print(f"📡 الاتصال بـ Supabase...")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ تم الاتصال بنجاح!")
    print()
except Exception as e:
    print(f"❌ فشل الاتصال: {e}")
    exit(1)

# جلب الفئات
print("📋 جلب الفئات من قاعدة البيانات...")
try:
    response = supabase.table('categories').select('id, osm_tag').execute()
    categories_map = {}
    for row in response.data:
        if row.get('osm_tag'):
            categories_map[row['osm_tag']] = row['id']
    print(f"✅ تم جلب {len(categories_map)} فئة")
    print()
except Exception as e:
    print(f"❌ خطأ في جلب الفئات: {e}")
    exit(1)

# تخمين المدينة
def guess_city(lat, lng):
    cities = {
        "Riyadh": (24.7, 46.7, 1.0),
        "Jeddah": (21.5, 39.2, 1.0),
        "Mecca": (21.4, 39.8, 0.5),
        "Medina": (24.5, 39.6, 0.5),
        "Dammam": (26.4, 50.1, 0.5),
        "Khobar": (26.3, 50.2, 0.3),
        "Taif": (21.3, 40.4, 0.5),
        "Tabuk": (28.4, 36.6, 0.5),
        "Abha": (18.2, 42.5, 0.5),
        "Buraidah": (26.3, 43.9, 0.5),
        "Hail": (27.5, 41.7, 0.5),
        "Najran": (17.5, 44.1, 0.5),
        "Jubail": (27.0, 49.6, 0.3),
        "Yanbu": (24.0, 38.0, 0.3),
    }
    for city, (clat, clng, radius) in cities.items():
        if abs(lat - clat) < radius and abs(lng - clng) < radius:
            return city
    return None

# قراءة GeoJSON
print("📂 قراءة ملف saudi-places.geojsonseq...")
places_to_insert = []
total_read = 0
matched = 0

with open('saudi-places.geojsonseq', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            feature = json.loads(line)
            total_read += 1
            
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            
            if geom.get('type') != 'Point':
                continue
            
            coords = geom.get('coordinates', [])
            if len(coords) < 2:
                continue
            
            lng, lat = coords[0], coords[1]
            
            if not (16.0 <= lat <= 33.0 and 34.0 <= lng <= 56.0):
                continue
            
            category_id = None
            for key, value in props.items():
                tag = f"{key}={value}"
                if tag in categories_map:
                    category_id = categories_map[tag]
                    matched += 1
                    break
            
            if not category_id:
                continue
            
            name_ar = props.get('name:ar') or props.get('name')
            name_en = props.get('name:en') or props.get('name')
            city = props.get('addr:city') or guess_city(lat, lng)
            osm_id = str(props.get('@id', f"node_{total_read}"))
            
            places_to_insert.append({
                'name_ar': name_ar,
                'name_en': name_en,
                'category_id': category_id,
                'location': f"POINT({lng} {lat})",
                'city': city,
                'neighborhood': props.get('addr:suburb'),
                'address': props.get('addr:full') or props.get('addr:street'),
                'phone': props.get('phone'),
                'website': props.get('website'),
                'osm_id': osm_id,
                'data_source': 'openstreetmap'
            })
            
            if total_read % 10000 == 0:
                print(f"   📊 قُرئ: {total_read:,} | مطابق: {matched:,}")
        except:
            continue

print()
print(f"✅ تمت قراءة {total_read:,} عنصر")
print(f"✅ تم مطابقة {matched:,} محل")
print(f"📦 جاهز للرفع: {len(places_to_insert):,} محل")
print()

if not places_to_insert:
    print("❌ لا يوجد بيانات للرفع!")
    exit(1)

# الرفع على دفعات
print("📤 رفع البيانات إلى Supabase...")
print("⏳ كل دفعة 500 محل...")
print()

batch_size = 500
total_uploaded = 0
errors = 0

for i in range(0, len(places_to_insert), batch_size):
    batch = places_to_insert[i:i+batch_size]
    try:
        response = supabase.table('places').insert(batch).execute()
        total_uploaded += len(batch)
        print(f"   ✅ رُفع: {total_uploaded:,} / {len(places_to_insert):,}")
    except Exception as e:
        errors += 1
        print(f"   ⚠️ خطأ في الدفعة {i//batch_size + 1}: {str(e)[:80]}")
        if errors > 3:
            print("❌ كثرة الأخطاء، نتوقف")
            break

print()
print("🎉" * 20)
print(f"🎊 تم رفع {total_uploaded:,} محل بنجاح!")
print("🎉" * 20)
