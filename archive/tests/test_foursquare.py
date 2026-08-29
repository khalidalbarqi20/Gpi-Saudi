"""
اختبار اتصال Foursquare OS Places - الإصدار المحسّن
"""
import os
from dotenv import load_dotenv
import duckdb

load_dotenv()

print("=" * 50)
print("🚀 بدء اختبار Foursquare OS Places")
print("=" * 50)

# الاتصال بـ DuckDB
print("📡 تهيئة DuckDB...")
con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
print("✅ DuckDB جاهز")
print()

# جلب آخر تاريخ متوفر
print("🔍 البحث عن آخر تاريخ متوفر للبيانات...")
try:
    dates_query = """
    SELECT DISTINCT regexp_extract(file, 'dt=([^/]+)', 1) as date
    FROM glob('s3://fsq-os-places-us-east-1/release/dt=*/places/parquet/')
    ORDER BY date DESC
    LIMIT 5;
    """
    dates = con.execute(dates_query).fetchall()
    
    if not dates:
        print("⚠️ ما قدرنا نلقى تواريخ، نجرب طريقة ثانية...")
        # طريقة بديلة: جرب تواريخ معروفة
        test_dates = [
            "2025-11-05", "2025-10-08", "2025-09-03", 
            "2025-08-06", "2025-07-09"
        ]
        latest_date = None
        for test_date in test_dates:
            try:
                test_query = f"""
                SELECT COUNT(*) FROM read_parquet(
                    's3://fsq-os-places-us-east-1/release/dt={test_date}/places/parquet/*.parquet'
                ) LIMIT 1;
                """
                con.execute(test_query).fetchall()
                latest_date = test_date
                print(f"✅ التاريخ المتوفر: {latest_date}")
                break
            except:
                continue
        
        if not latest_date:
            print("❌ ما قدرنا نلقى أي تاريخ صالح")
            exit(1)
    else:
        latest_date = dates[0][0]
        print(f"✅ آخر تاريخ متوفر: {latest_date}")
        print()
        print("📅 آخر 5 تواريخ:")
        for d in dates:
            print(f"   - {d[0]}")
    
    print()
    print("🇸🇦 جلب عينة من محلات السعودية...")
    print("⏳ هذا قد يأخذ دقيقة أو دقيقتين...")
    print()
    
    query = f"""
    SELECT 
        fsq_place_id,
        name,
        latitude,
        longitude,
        locality,
        region,
        country
    FROM read_parquet('s3://fsq-os-places-us-east-1/release/dt={latest_date}/places/parquet/*.parquet')
    WHERE country = 'SA'
    LIMIT 5;
    """
    
    result = con.execute(query).fetchall()
    
    if result:
        print("✅ نجح الاتصال! إليك أول 5 محلات في السعودية:")
        print("-" * 80)
        
        for i, row in enumerate(result, 1):
            print(f"المحل #{i}:")
            print(f"  📍 الاسم: {row[1]}")
            print(f"  🌍 المدينة: {row[4]}")
            print(f"  🗺️  المنطقة: {row[5]}")
            print(f"  📌 الإحداثيات: ({row[2]}, {row[3]})")
            print(f"  🆔 ID: {row[0]}")
            print("-" * 80)
        
        print()
        print("🎉 الاختبار نجح! Foursquare يعمل بشكل ممتاز!")
        print(f"💾 احفظ هذا التاريخ للاستخدام لاحقًا: {latest_date}")
    else:
        print("⚠️ ما وجدنا محلات، جرب تاريخ آخر")

except Exception as e:
    print(f"❌ خطأ: {e}")
    print()
    print("💡 نصائح:")
    print("   - تأكد من اتصال الإنترنت")
    print("   - جرب مرة ثانية")

