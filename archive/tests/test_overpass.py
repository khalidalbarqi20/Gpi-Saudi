"""اختبار Overpass API - بحث مباشر في OSM"""
import requests
import json

def search_places_overpass(lat, lng, radius=1000):
    """بحث عن المحلات باستخدام Overpass API"""
    
    query = f"""
    [out:json][timeout:25];
    (
      node["shop"](around:{radius},{lat},{lng});
      node["amenity"~"restaurant|cafe|fast_food|pharmacy|bank|fuel|hospital|school"](around:{radius},{lat},{lng});
      node["office"](around:{radius},{lat},{lng});
      node["leisure"](around:{radius},{lat},{lng});
      way["shop"](around:{radius},{lat},{lng});
      way["amenity"~"restaurant|cafe|fast_food|pharmacy|bank"](around:{radius},{lat},{lng});
    );
    out body;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data=query, timeout=30)
    return response.json()


# اختبار - الموقع الذي اختبرناه
lat, lng = 18.934277, 41.935222

print(f"🔍 البحث عن المحلات حول: {lat}, {lng}")
print(f"📏 نطاق البحث: 1 كم\n")
print("⏳ جاري البحث في Overpass API...\n")

result = search_places_overpass(lat, lng, radius=1000)

elements = result.get('elements', [])
print(f"✅ تم العثور على: {len(elements)} عنصر\n")

if elements:
    print("📋 المحلات الموجودة:\n")
    for i, el in enumerate(elements[:20], 1):
        tags = el.get('tags', {})
        name = tags.get('name', tags.get('name:ar', '(بدون اسم)'))
        
        # تحديد النوع
        kind = (tags.get('shop') or 
                tags.get('amenity') or 
                tags.get('office') or 
                tags.get('leisure') or 'غير محدد')
        
        print(f"   {i:2}. {name[:30]:30} | {kind}")
else:
    print("📭 لم يُعثر على أي محلات في Overpass API")
    print("\nنحاول نطاق أوسع: 5 كم...")
    result2 = search_places_overpass(lat, lng, radius=5000)
    elements2 = result2.get('elements', [])
    print(f"📊 في 5 كم: {len(elements2)} عنصر")
