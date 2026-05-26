"""تحليل موقع متقدم - يقبل صور متعددة (محلية أو روابط)"""
import os
import re
import requests
import json
import glob
from dotenv import load_dotenv
from supabase import create_client
import google.generativeai as genai
from PIL import Image
from io import BytesIO

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def extract_coords(url):
    if 'goo.gl' in url or 'maps.app' in url:
        r = requests.get(url, allow_redirects=True, timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0'})
        url = r.url
    for p in [r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',
              r'place/(-?\d+\.?\d*),(-?\d+\.?\d*)',
              r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)']:
        m = re.search(p, url)
        if m: return float(m.group(1)), float(m.group(2))
    return None, None


def analyze_image(src):
    """تحليل صورة (محلية أو رابط)"""
    if src.startswith('http'):
        r = requests.get(src, headers={'User-Agent': 'Mozilla/5.0'})
        image = Image.open(BytesIO(r.content))
    else:
        image = Image.open(src)
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = """حلل هذي الصورة كمحلل مواقع تجارية. أعطني JSON:
{
  "area_description": "وصف موجز",
  "traffic_level": "منخفض/متوسط/مرتفع",
  "parking": "ضعيفة/متوسطة/جيدة",
  "neighborhood_type": "سكني/تجاري/مختلط",
  "visible_businesses": ["محل1"],
  "suitable_for": ["مقهى", "مطعم"],
  "concerns": ["تحذير"],
  "score": 7
}
JSON فقط."""
    
    text = model.generate_content([prompt, image]).text.strip()
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]
    elif '```' in text:
        text = text.split('```')[1].split('```')[0]
    try:
        return json.loads(text.strip())
    except:
        return {"raw": text, "score": 5}


def full_analysis(url, images, category_id=8):
    print("=" * 70)
    print("🎯 تحليل موقع شامل - النسخة 2")
    print("=" * 70)
    
    # الإحداثيات
    print("\n📍 [1/3] استخراج الإحداثيات...")
    lat, lng = extract_coords(url)
    print(f"   ✅ {lat}, {lng}")
    
    # التحليل الجغرافي
    print("\n📊 [2/3] التحليل الجغرافي...")
    geo = supabase.rpc('full_location_analysis', {
        'lat': lat, 'lng': lng,
        'business_category_id': category_id,
        'analysis_radius': 2000
    }).execute().data
    print(f"   منافسون: {geo['competition']['direct_competitors']}")
    print(f"   المنطقة: {geo['area_activity']['activity_level']}")
    
    # تحليل الصور
    print(f"\n📸 [3/3] تحليل {len(images)} صورة...")
    analyses = []
    for i, img in enumerate(images, 1):
        src_name = os.path.basename(img) if not img.startswith('http') else 'web'
        print(f"   🤖 {i}/{len(images)} - {src_name}")
        a = analyze_image(img)
        analyses.append(a)
        if 'score' in a:
            print(f"      درجة: {a['score']}/10")
    
    # التقرير
    print("\n" + "=" * 70)
    print("📋 التقرير النهائي")
    print("=" * 70)
    
    print(f"\n🌍 الجغرافيا:")
    print(f"   📍 {lat}, {lng}")
    print(f"   🏪 محلات: {geo['area_activity']['total_places']}")
    print(f"   ⚔️  منافسون: {geo['competition']['direct_competitors']}")
    print(f"   💡 {geo['recommendation']['saturation_risk']}")
    
    print(f"\n📸 الصور ({len(analyses)}):")
    for i, a in enumerate(analyses, 1):
        print(f"\n   صورة {i}:")
        if 'area_description' in a:
            print(f"   • {a.get('area_description', '')[:80]}")
            print(f"   • ازدحام: {a.get('traffic_level', '-')}")
            print(f"   • مواقف: {a.get('parking', '-')}")
            print(f"   • نوع: {a.get('neighborhood_type', '-')}")
            if a.get('visible_businesses'):
                print(f"   • محلات مرئية: {', '.join(a['visible_businesses'])}")
            print(f"   • درجة: {a.get('score', '-')}/10")
    
    # المتوسط
    scores = [a.get('score', 5) for a in analyses]
    avg = sum(scores) / len(scores) if scores else 5
    print(f"\n🎯 الدرجة الإجمالية: {avg:.1f}/10")
    print("=" * 70)
    
    return {
        'location': {'lat': lat, 'lng': lng},
        'geographic': geo,
        'images': analyses,
        'score': avg
    }


if __name__ == "__main__":
    url = "https://maps.app.goo.gl/5xsT2YWZaGk16wwo7"
    
    # ابحث عن صور محلية في test_photos
    local_images = glob.glob('test_photos/*.jpg') + glob.glob('test_photos/*.png')
    
    if local_images:
        print(f"✅ وجدت {len(local_images)} صورة محلية!")
        images = local_images
    else:
        print("⚠️  لا توجد صور محلية، نستخدم صورة اختبار")
        images = ["https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1280"]
    
    full_analysis(url, images, category_id=8)
