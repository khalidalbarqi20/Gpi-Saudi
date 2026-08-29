"""اختبار Overpass API - محسّن"""
import requests
import json
import time

def search_overpass(lat, lng, radius=1000):
    """بحث محسّن مع معالجة أخطاء"""
    
    query = f"""[out:json][timeout:60];
(
  node["shop"](around:{radius},{lat},{lng});
  node["amenity"](around:{radius},{lat},{lng});
  way["shop"](around:{radius},{lat},{lng});
  way["amenity"](around:{radius},{lat},{lng});
);
out center;"""
    
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter"
    ]
    
    for i, url in enumerate(servers, 1):
        try:
            print(f"   🔄 محاولة {i}: {url[:40]}...")
            response = requests.post(url, data=query, timeout=60,
                                     headers={'User-Agent': 'GBI-Saudi/1.0'})
            
            print(f"   📊 الحالة: {response.status_code}")
            
            if response.status_code == 200:
                if response.text.strip().startswith('{'):
                    return response.json()
                else:
                    print(f"   ⚠️ رد غير JSON: {response.text[:100]}")
            elif response.status_code == 429:
                print("   ⏳ Rate limit - ننتظر 5 ثواني...")
                time.sleep(5)
            
        except requests.exceptions.Timeout:
            print(f"   ⏱️ timeout")
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
        
        time.sleep(2)
    
    return None


# اختبار - الموقع
lat, lng = 18.934277, 41.935222

print(f"🔍 البحث عن المحلات حول: {lat}, {lng}")
print(f"📏 نطاق البحث: 1 كم\n")
print("⏳ جاري البحث في Overpass API...\n")

result = search_overpass(lat, lng, radius=1000)

if result is None:
    print("\n❌ فشلت كل المحاولات")
    print("💡 ربما Overpass server مشغول، نجرب لاحقاً")
else:
    elements = result.get('elements', [])
    print(f"\n✅ تم العثور على: {len(elements)} عنصر\n")
    
    if elements:
        print("📋 المحلات:\n")
        for i, el in enumerate(elements[:30], 1):
            tags = el.get('tags', {})
            name = tags.get('name', tags.get('name:ar', '(بدون اسم)'))
            kind = (tags.get('shop') or tags.get('amenity') or 'غير محدد')
            print(f"   {i:2}. {str(name)[:30]:30} | {kind}")
    else:
        print("📭 لا توجد محلات - نجرب نطاق 5 كم...\n")
        result2 = search_overpass(lat, lng, radius=5000)
        if result2:
            els = result2.get('elements', [])
            print(f"📊 في 5 كم: {len(els)} عنصر")
            for i, el in enumerate(els[:20], 1):
                tags = el.get('tags', {})
                name = tags.get('name', '(بدون اسم)')
                kind = (tags.get('shop') or tags.get('amenity') or '?')
                print(f"   {i:2}. {str(name)[:30]:30} | {kind}")
