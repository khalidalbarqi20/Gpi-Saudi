import os
import re
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def extract_coords(url):
    if 'goo.gl' in url or 'maps.app' in url:
        r = requests.get(url, allow_redirects=True, timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0'})
        url = r.url
    for pattern in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',
                    r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)',
                    r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',
                    r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)']:
        match = re.search(pattern, url)
        if match:
            return float(match.group(1)), float(match.group(2))
    return None, None


# الخطوة 1: استخراج الإحداثيات
my_url = "https://maps.app.goo.gl/5xsT2YWZaGk16wwo7"
print("📍 الخطوة 1: استخراج الإحداثيات...")
lat, lng = extract_coords(my_url)
print(f"   ✅ lat={lat}, lng={lng}\n")

# الخطوة 2: الاتصال بـ Supabase
print("📊 الخطوة 2: التحليل الجغرافي...")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# تحليل كثافة المنطقة
result = supabase.rpc('analyze_density', {'lat': lat, 'lng': lng}).execute()
print("\n🏘️ كثافة المنطقة:")
for row in result.data:
    print(f"   {row['radius_label']:8} | "
          f"{row['total_places']:4} محل | "
          f"{row['unique_categories']:2} فئة")

# المنافسون في 2 كم
print("\n⚔️ المنافسون في 2 كم:")
result = supabase.rpc('count_competitors', 
                       {'lat': lat, 'lng': lng, 
                        'radius_meters': 2000,
                        'target_category_id': None}).execute()
if result.data:
    for row in result.data[:5]:
        print(f"   {row['category_name_ar']:25} | "
              f"{row['competitor_count']:3} محل | "
              f"أقرب: {row['nearest_distance']}م")
else:
    print("   📭 لا توجد محلات في 2 كم")

# تحليل شامل لمقهى (مثال)
print("\n🎯 تحليل شامل لـ 'مقهى':")
result = supabase.rpc('full_location_analysis',
                       {'lat': lat, 'lng': lng,
                        'business_category_id': 8,
                        'analysis_radius': 2000}).execute()
import json
print(json.dumps(result.data, ensure_ascii=False, indent=2))

print("\n" + "=" * 60)
print("🎉 الاختبار اكتمل!")
print("=" * 60)
