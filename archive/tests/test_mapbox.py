"""اختبار Mapbox Search Box API"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("MAPBOX_TOKEN")

if not TOKEN:
    print("❌ MAPBOX_TOKEN مفقود من .env")
    exit()

print(f"✅ Token موجود: {TOKEN[:20]}...\n")

# الموقع
lat, lng = 18.934277, 41.935222

print(f"🔍 البحث في Mapbox حول: {lat}, {lng}")
print(f"📏 نطاق البحث: 1 كم\n")

# Mapbox Search Box API - Category Search
categories = [
    "restaurant",
    "cafe", 
    "shopping",
    "fuel",
    "pharmacy",
    "grocery"
]

all_results = []

for cat in categories:
    url = "https://api.mapbox.com/search/searchbox/v1/category/" + cat
    params = {
        "access_token": TOKEN,
        "proximity": f"{lng},{lat}",
        "limit": 10,
        "language": "ar"
    }
    
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            features = data.get('features', [])
            print(f"📂 {cat}: وجد {len(features)} نتيجة")
            for f in features[:5]:
                props = f.get('properties', {})
                name = props.get('name', '?')
                addr = props.get('full_address', '')
                print(f"   • {name[:30]} - {addr[:40]}")
            all_results.extend(features)
        else:
            print(f"❌ {cat}: خطأ {r.status_code}")
            print(f"   {r.text[:200]}")
    except Exception as e:
        print(f"❌ {cat}: {e}")
    print()

print(f"\n{'='*60}")
print(f"📊 الإجمالي: {len(all_results)} محل من جميع الفئات")
print(f"{'='*60}")
