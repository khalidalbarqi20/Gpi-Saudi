"""
نظام تحليل موقع كامل
- يستقبل: رابط Google Maps + صور
- يخرج: تقرير شامل
"""
import os
import re
import requests
import json
from dotenv import load_dotenv
from supabase import create_client
import google.generativeai as genai
from PIL import Image
from io import BytesIO

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def extract_coords(url):
    """استخراج الإحداثيات من رابط Google Maps"""
    if 'goo.gl' in url or 'maps.app' in url:
        r = requests.get(url, allow_redirects=True, timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0'})
        url = r.url
    for p in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',
              r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)',
              r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)']:
        m = re.search(p, url)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def analyze_geo(lat, lng, category_id=8, radius=2000):
    """تحليل جغرافي من Supabase"""
    result = supabase.rpc('full_location_analysis', {
        'lat': lat, 'lng': lng,
        'business_category_id': category_id,
        'analysis_radius': radius
    }).execute()
    return result.data


def analyze_image(image_path_or_url):
    """تحليل صورة واحدة بـ Gemini"""
    if image_path_or_url.startswith('http'):
        r = requests.get(image_path_or_url, 
                         headers={'User-Agent': 'Mozilla/5.0'})
        image = Image.open(BytesIO(r.content))
    else:
        image = Image.open(image_path_or_url)
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """أنت محلل مواقع تجارية محترف.
حلل هذي الصورة وأعطني JSON بهذا الشكل بالضبط:

{
  "area_description": "وصف موجز للمنطقة",
  "traffic_level": "منخفض/متوسط/مرتفع",
  "pedestrian_level": "منخفض/متوسط/مرتفع",
  "parking_availability": "ضعيفة/متوسطة/جيدة",
  "building_types": "نوع المباني",
  "visible_businesses": ["محل1", "محل2"],
  "neighborhood_type": "سكني/تجاري/مختلط",
  "lighting": "جيدة/متوسطة/ضعيفة",
  "suitable_categories": ["مقهى", "مطعم", "..."],
  "concerns": ["تحذير1", "تحذير2"],
  "overall_score": 7
}

أجب بـ JSON فقط بدون أي نص آخر."""
    
    response = model.generate_content([prompt, image])
    text = response.text.strip()
    
    # تنظيف JSON
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]
    
    try:
        return json.loads(text.strip())
    except:
        return {"raw_response": text}


def full_analysis(gmaps_url, image_sources, business_category_id=8):
    """التحليل الشامل"""
    print("=" * 70)
    print("🎯 تحليل موقع شامل")
    print("=" * 70)
    
    # 1. الإحداثيات
    print("\n📍 [1/3] استخراج الإحداثيات...")
    lat, lng = extract_coords(gmaps_url)
    print(f"   ✅ {lat}, {lng}")
    print(f"   🗺️  https://maps.google.com/?q={lat},{lng}")
    
    # 2. التحليل الجغرافي
    print("\n📊 [2/3] التحليل الجغرافي من قاعدة البيانات...")
    geo = analyze_geo(lat, lng, business_category_id)
    print(f"   ✅ {geo['target_business']['category_name']}")
    print(f"   منافسون مباشرون: {geo['competition']['direct_competitors']}")
    print(f"   إجمالي المحلات: {geo['area_activity']['total_places']}")
    print(f"   مستوى النشاط: {geo['area_activity']['activity_level']}")
    
    # 3. تحليل الصور
    print(f"\n📸 [3/3] تحليل {len(image_sources)} صورة بـ Gemini Vision...")
    image_analyses = []
    for i, img in enumerate(image_sources, 1):
        print(f"   🤖 تحليل الصورة {i}/{len(image_sources)}...")
        analysis = analyze_image(img)
        image_analyses.append(analysis)
        if 'overall_score' in analysis:
            print(f"      درجة: {analysis['overall_score']}/10")
    
    # التقرير النهائي
    print("\n" + "=" * 70)
    print("📋 التقرير النهائي")
    print("=" * 70)
    
    print(f"\n🌍 التحليل الجغرافي:")
    print(f"   📍 الموقع: {lat}, {lng}")
    print(f"   🏪 المحلات حولك: {geo['area_activity']['total_places']}")
    print(f"   ⚔️  منافسون: {geo['competition']['direct_competitors']}")
    print(f"   💡 التوصية: {geo['recommendation']['saturation_risk']}")
    
    print(f"\n📸 تحليل الصور:")
    for i, analysis in enumerate(image_analyses, 1):
        print(f"\n   صورة {i}:")
        if 'area_description' in analysis:
            print(f"   • {analysis['area_description']}")
            print(f"   • ازدحام: {analysis.get('traffic_level', '-')}")
            print(f"   • مواقف: {analysis.get('parking_availability', '-')}")
            print(f"   • درجة: {analysis.get('overall_score', '-')}/10")
    
    # الدرجة الإجمالية
    scores = [a.get('overall_score', 5) for a in image_analyses 
              if 'overall_score' in a]
    avg_score = sum(scores) / len(scores) if scores else 5
    
    print(f"\n🎯 الدرجة الإجمالية: {avg_score:.1f}/10")
    print("=" * 70)
    
    return {
        'location': {'lat': lat, 'lng': lng},
        'geographic': geo,
        'images': image_analyses,
        'overall_score': avg_score
    }


# ========== الاختبار ==========
if __name__ == "__main__":
    # رابط موقعك
    url = "https://maps.app.goo.gl/5xsT2YWZaGk16wwo7"
    
    # صور للاختبار (Unsplash - مجاني)
    images = [
        "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1280",
    ]
    
    # category_id 8 = مقهى
    result = full_analysis(url, images, business_category_id=8)
