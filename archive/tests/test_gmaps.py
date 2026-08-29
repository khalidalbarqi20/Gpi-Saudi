import re
import requests

def extract_coords_from_url(url):
    """استخراج الإحداثيات من رابط Google Maps"""
    
    # لو رابط مختصر (goo.gl)، نتبعه
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(url, allow_redirects=True, timeout=5)
            url = r.url
            print(f"📌 الرابط الكامل: {url[:80]}...")
        except Exception as e:
            return {"error": f"فشل فك الرابط: {e}"}
    
    # نمط 1: @lat,lng
    pattern1 = r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
    # نمط 2: ?q=lat,lng  
    pattern2 = r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
    # نمط 3: !3d{lat}!4d{lng}
    pattern3 = r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)'
    
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, url)
        if match:
            lat, lng = float(match.group(1)), float(match.group(2))
            return {"latitude": lat, "longitude": lng, "url": url}
    
    return {"error": "لم يتم العثور على إحداثيات"}


# اختبار بعدة روابط
test_urls = [
    "https://www.google.com/maps/@24.7891,46.6234,15z",
    "https://maps.google.com/?q=24.7891,46.6234",
    "https://www.google.com/maps/place/Kingdom+Centre/@24.7117,46.6745,17z/data=!3m1!4b1!4m6!3m5!1s0x3e2ee01e1c3d0001:0x0!8m2!3d24.7117!4d46.6745",
]

print("🧪 اختبار استخراج إحداثيات Google Maps:\n")
for i, url in enumerate(test_urls, 1):
    print(f"الاختبار {i}:")
    print(f"  الرابط: {url[:60]}...")
    result = extract_coords_from_url(url)
    print(f"  النتيجة: {result}\n")
