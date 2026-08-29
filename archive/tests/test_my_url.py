import re
import requests

def extract_coords_from_url(url):
    """استخراج الإحداثيات من رابط Google Maps"""
    
    if 'goo.gl' in url or 'maps.app' in url:
        try:
            r = requests.get(url, allow_redirects=True, timeout=10,
                             headers={'User-Agent': 'Mozilla/5.0'})
            url = r.url
            print(f"📌 الرابط الكامل بعد التوسيع:")
            print(f"   {url[:100]}...")
            print()
        except Exception as e:
            return {"error": f"فشل فك الرابط: {e}"}
    
    pattern1 = r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
    pattern2 = r'[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
    pattern3 = r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)'
    
    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, url)
        if match:
            lat, lng = float(match.group(1)), float(match.group(2))
            return {"latitude": lat, "longitude": lng}
    
    return {"error": "لم يتم العثور على إحداثيات"}


# رابطك المختصر
my_url = "https://maps.app.goo.gl/5xsT2YWZaGk16wwo7"

print("🧪 اختبار الرابط المختصر:\n")
print(f"الرابط الأصلي: {my_url}\n")

result = extract_coords_from_url(my_url)
print(f"🎯 النتيجة: {result}")
