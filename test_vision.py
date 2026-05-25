import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from io import BytesIO

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# صورة شارع تجاري من Unsplash (مجاني)
image_url = "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1280"

print("📥 تنزيل الصورة...")
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(image_url, headers=headers)
print(f"✅ حالة التنزيل: {response.status_code}")
print(f"✅ حجم الصورة: {len(response.content)} bytes")

image = Image.open(BytesIO(response.content))
print(f"✅ الصورة جاهزة: {image.size}")

# تحليل بـ Gemini
print("\n🤖 إرسال للتحليل بـ Gemini...\n")
model = genai.GenerativeModel('gemini-2.5-flash')

prompt = """أنت محلل مواقع تجارية محترف.

حلل هذي الصورة وأعطني:
1. وصف المنطقة (نوعها، طابعها)
2. مستوى الازدحام
3. نوع المباني والمحلات
4. هل المنطقة مناسبة لمشاريع تجارية؟
5. الفئات التجارية المناسبة

أجب بالعربي بشكل مختصر ومنظم."""

response = model.generate_content([prompt, image])

print("✅ التحليل اكتمل!")
print("=" * 60)
print(response.text)
print("=" * 60)
