import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

lat, lng = 18.934277, 41.935222

print(f"📍 الإحداثيات: {lat}, {lng}")
print(f"🗺️  Google Maps: https://www.google.com/maps?q={lat},{lng}")
print()

print("🔍 البحث في نطاق 10 كم...")
result = supabase.rpc('get_nearby_places',
                       {'lat': lat, 'lng': lng,
                        'radius_meters': 10000}).execute()

print(f"\n📊 عدد المحلات في OSM: {len(result.data)}\n")

if result.data:
    print("📋 المحلات:")
    for i, p in enumerate(result.data[:20], 1):
        name = p.get('name_ar') or '(بدون اسم)'
        cat = p.get('category_name_ar', '-')
        dist = p.get('distance_meters', 0)
        print(f"  {i:2}. {str(name)[:25]:25} | {str(cat)[:12]:12} | {dist}م")
else:
    print("📭 لا توجد محلات في OSM لهذا الموقع")
