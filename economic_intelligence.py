"""
economic_intelligence.py  v2
═══════════════════════════════════════════════════════════════════════
المحركات السبعة:
  1. محرك الطابع الاقتصادي للمحافظة (يدوي - 134 محافظة)
  2. محرك اختبار الطلب الحقيقي
  3. محرك المجاورات (جيدة وسيئة)
  4. محرك هوية المنطقة
  5. محرك رحلة العميل
  6. محرك المقارنة بالمناطق المشابهة
  7. محرك الثقة بالأدلة
═══════════════════════════════════════════════════════════════════════
"""

import math
from typing import Dict, List, Optional, Any


# ══════════════════════════════════════════════════════════════════════
# 1. الطابع الاقتصادي للمحافظات السعودية - يدوي
# ══════════════════════════════════════════════════════════════════════

GOVERNORATE_ECONOMIC_PROFILE: Dict[str, dict] = {

    # ─── منطقة الرياض ───────────────────────────────────────────────
    "الرياض": {
        "economic_base": "إداري + تجاري + خدمي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": True, "has_industrial": True, "agricultural": False,
        "ev_readiness": "high", "income_level": "high", "population_type": "mixed",
        "notes": "العاصمة - أعلى قوة شرائية - منافسة شديدة - الفرصة في التخصص",
        "strong_sectors": ["cafe","restaurant","fitness_center","beauty_salon","electronics_store","ev_charging_station"],
        "weak_sectors": ["agricultural_equipment","fishing"],
    },
    "الخرج": {
        "economic_base": "زراعي + صناعي + سكني",
        "is_transit": True, "tourism_level": "low",
        "has_university": True, "has_industrial": True, "agricultural": True,
        "ev_readiness": "low", "income_level": "medium", "population_type": "mixed",
        "notes": "زراعة مكثفة - قرب الرياض - طريق عبور للجنوب",
        "strong_sectors": ["grocery","auto_repair","fuel","restaurant","agricultural_equipment","tyre_shop"],
        "weak_sectors": ["ev_charging_station","cinema","luxury_retail"],
    },
    "الدوادمي": {
        "economic_base": "خدمي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "نقطة عبور على طريق الرياض-مكة - اقتصاد الطريق قوي",
        "strong_sectors": ["fuel","restaurant","fast_food","auto_repair","tyre_shop","grocery"],
        "weak_sectors": ["ev_charging_station","fitness_center","luxury"],
    },
    "المجمعة": {
        "economic_base": "زراعي + خدمي + جامعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "مدينة جامعية - شباب كثير - خدمات الطلاب فرصة",
        "strong_sectors": ["cafe","fast_food","grocery","pharmacy","services","barber"],
        "weak_sectors": ["ev_charging_station","hotel","luxury_retail"],
    },
    "الزلفي": {
        "economic_base": "زراعي + خدمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة وتمور - خدمات محلية أساسية",
        "strong_sectors": ["grocery","pharmacy","auto_repair","fuel","bakery"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","hotel"],
    },
    "القويعية": {
        "economic_base": "زراعي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "طريق الرياض-الطائف - خدمات العبور مربحة",
        "strong_sectors": ["fuel","restaurant","fast_food","auto_repair","grocery"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "وادي الدواسر": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة وتمور - بعيدة عن المراكز - احتياجات أساسية أولاً",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair","bakery","hardware"],
        "weak_sectors": ["ev_charging_station","fitness_center","cinema","hotel"],
    },
    "الأفلاج": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "محافظة زراعية بامتياز - خدمات الزراعة أهم شيء",
        "strong_sectors": ["grocery","pharmacy","fuel","hardware","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","hotel","cafe"],
    },
    "شقراء": {
        "economic_base": "زراعي + خدمي + جامعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "جامعة شقراء - شباب وطلاب - فرص الخدمات الجامعية",
        "strong_sectors": ["cafe","fast_food","grocery","pharmacy","services"],
        "weak_sectors": ["ev_charging_station","hotel","luxury"],
    },
    "عفيف": {
        "economic_base": "عبور + خدمي",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "محطة على طريق الرياض-مكة - خدمات الطريق فرصة كبيرة",
        "strong_sectors": ["fuel","restaurant","fast_food","auto_repair","tyre_shop"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "الدرعية": {
        "economic_base": "سياحي + تاريخي",
        "is_transit": False, "tourism_level": "very_high",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "high", "income_level": "high", "population_type": "mixed",
        "notes": "مقصد سياحي عالمي - رؤية 2030 - فنادق ومطاعم وتجربة",
        "strong_sectors": ["hotel","restaurant","cafe","souvenir","car_rental"],
        "weak_sectors": ["agricultural_equipment","industrial"],
    },
    "حوطة بني تميم": {
        "economic_base": "زراعي + خدمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "زراعة - تمور - خدمات محلية",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "ثادق": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية زراعية صغيرة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },

    # ─── منطقة مكة المكرمة ──────────────────────────────────────────
    "مكة المكرمة": {
        "economic_base": "ديني + سياحي + خدمي",
        "is_transit": False, "tourism_level": "very_high",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "medium", "income_level": "high", "population_type": "pilgrims",
        "notes": "موسمية شديدة - ذروة في الحج والعمرة - فرص الضيافة والخدمة الدينية",
        "strong_sectors": ["hotel","restaurant","fast_food","pharmacy","grocery","services","clothing_store"],
        "weak_sectors": ["fitness_center","cinema","ev_charging_station"],
    },
    "جدة": {
        "economic_base": "تجاري + صناعي + سياحي + ميناء",
        "is_transit": False, "tourism_level": "high",
        "has_university": True, "has_industrial": True, "agricultural": False,
        "ev_readiness": "high", "income_level": "very_high", "population_type": "mixed",
        "notes": "ثاني أكبر مدينة - منفتحة ثقافياً - قوة شرائية عالية - منافسة شديدة",
        "strong_sectors": ["cafe","restaurant","fitness_center","beauty_salon","shopping","ev_charging_station","hotel"],
        "weak_sectors": ["agricultural_equipment"],
    },
    "الطائف": {
        "economic_base": "سياحي صيفي + زراعي + جامعي",
        "is_transit": False, "tourism_level": "high",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "medium", "income_level": "medium", "population_type": "mixed",
        "notes": "عاصمة الصيف - سياحة مكثفة - زراعة الورود والعسل",
        "strong_sectors": ["hotel","restaurant","cafe","grocery","pharmacy","souvenir","honey_shop"],
        "weak_sectors": ["ev_charging_station","industrial"],
    },
    "القنفذة": {
        "economic_base": "صيد + خدمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "ساحلية - صيد أسماك - خدمات أساسية",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair","restaurant","fish_market"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","hotel"],
    },
    "الليث": {
        "economic_base": "صيد + زراعي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "ساحلية - طريق عبور - خدمات أساسية فقط",
        "strong_sectors": ["fuel","grocery","pharmacy","auto_repair","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","hotel"],
    },
    "رابغ": {
        "economic_base": "صناعي + بتروكيماوي + سكني",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": True, "agricultural": False,
        "ev_readiness": "low", "income_level": "medium", "population_type": "workers",
        "notes": "مدينة صناعية - عمالة - طريق جدة-المدينة",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","fuel","services"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "الجموم": {
        "economic_base": "سكني + زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "بين مكة وجدة - سكن عائلي - خدمات يومية",
        "strong_sectors": ["grocery","pharmacy","bakery","fast_food","barber"],
        "weak_sectors": ["ev_charging_station","hotel","luxury"],
    },
    "خليص": {
        "economic_base": "سكني + زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "بين جدة والمدينة - خدمات يومية",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "الكامل": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية صغيرة - زراعة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },

    # ─── المنطقة الشرقية ─────────────────────────────────────────────
    "الدمام": {
        "economic_base": "نفطي + صناعي + تجاري",
        "is_transit": False, "tourism_level": "medium",
        "has_university": True, "has_industrial": True, "agricultural": False,
        "ev_readiness": "high", "income_level": "very_high", "population_type": "mixed",
        "notes": "عاصمة الشرقية - نفط - دخل مرتفع - مقر شركات كبرى",
        "strong_sectors": ["cafe","restaurant","fitness_center","ev_charging_station","electronics_store","beauty_salon","hotel"],
        "weak_sectors": ["agricultural_equipment"],
    },
    "الأحساء": {
        "economic_base": "زراعي + نفطي + سياحي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "low", "income_level": "medium", "population_type": "families",
        "notes": "أكبر واحة في العالم - تمور - تراث - سياحة متنامية",
        "strong_sectors": ["grocery","pharmacy","restaurant","souvenir","dates_shop","hotel","agricultural_equipment"],
        "weak_sectors": ["ev_charging_station","cinema"],
    },
    "الخبر": {
        "economic_base": "تجاري + خدمي + سكني راقٍ",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "high", "income_level": "very_high", "population_type": "mixed",
        "notes": "سكن الشركات - دخل مرتفع جداً - طلب على الفخامة",
        "strong_sectors": ["cafe","restaurant","fitness_center","ev_charging_station","beauty_salon","hotel","shopping"],
        "weak_sectors": ["agricultural_equipment","industrial"],
    },
    "القطيف": {
        "economic_base": "نفطي + خدمي + سكني",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "medium", "income_level": "high", "population_type": "families",
        "notes": "سكن عمال أرامكو - دخل مرتفع - طلب على الخدمات الجيدة",
        "strong_sectors": ["grocery","pharmacy","restaurant","cafe","auto_repair"],
        "weak_sectors": ["agricultural_equipment","hotel"],
    },
    "الجبيل": {
        "economic_base": "صناعي + بتروكيماوي",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": True, "agricultural": False,
        "ev_readiness": "medium", "income_level": "high", "population_type": "workers",
        "notes": "مدينة صناعية بامتياز - عمالة كثيفة",
        "strong_sectors": ["grocery","restaurant","fast_food","pharmacy","auto_repair","barber","services"],
        "weak_sectors": ["ev_charging_station","luxury","cinema"],
    },
    "حفر الباطن": {
        "economic_base": "عسكري + خدمي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "قرب الحدود - وجود عسكري كبير - خدمات متنوعة",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","fuel","services"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "الخفجي": {
        "economic_base": "نفطي + صناعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": True, "agricultural": False,
        "ev_readiness": "low", "income_level": "high", "population_type": "workers",
        "notes": "نفط - عمالة - قرب الكويت",
        "strong_sectors": ["grocery","pharmacy","restaurant","services"],
        "weak_sectors": ["ev_charging_station","hotel","cinema"],
    },
    "الرياض الخبراء": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "قرية في القصيم - زراعة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },

    # ─── منطقة المدينة المنورة ────────────────────────────────────────
    "المدينة المنورة": {
        "economic_base": "ديني + سياحي + خدمي",
        "is_transit": False, "tourism_level": "very_high",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "medium", "income_level": "medium", "population_type": "pilgrims",
        "notes": "ثاني الحرمين - زوار على مدار العام - أقل موسمية من مكة",
        "strong_sectors": ["hotel","restaurant","fast_food","pharmacy","grocery","services","clothing_store","souvenir"],
        "weak_sectors": ["ev_charging_station","fitness_center","cinema"],
    },
    "ينبع": {
        "economic_base": "صناعي + بتروكيماوي + ميناء",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": True, "agricultural": False,
        "ev_readiness": "low", "income_level": "high", "population_type": "workers",
        "notes": "مدينة صناعية - ميناء - عمالة - دخل جيد",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","fuel","services"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "العلا": {
        "economic_base": "سياحي + تراثي",
        "is_transit": False, "tourism_level": "very_high",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "medium", "income_level": "medium", "population_type": "mixed",
        "notes": "وجهة سياحية عالمية - مدائن صالح - فنادق فاخرة - رؤية 2030",
        "strong_sectors": ["hotel","restaurant","cafe","car_rental","souvenir","ev_charging_station"],
        "weak_sectors": ["agricultural_equipment","industrial","tyre_shop"],
    },
    "خيبر": {
        "economic_base": "زراعي + سياحي تراثي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "تمور خيبر الشهيرة - بدايات سياحة تراثية",
        "strong_sectors": ["grocery","fuel","auto_repair","dates_shop"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "وادي الفرع": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية زراعية صغيرة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "بدر": {
        "economic_base": "ديني + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "أهمية دينية تاريخية - زوار - زراعة",
        "strong_sectors": ["grocery","pharmacy","restaurant","fuel","souvenir"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },

    # ─── منطقة عسير ──────────────────────────────────────────────────
    "أبها": {
        "economic_base": "سياحي صيفي + إداري + زراعي + جامعي",
        "is_transit": False, "tourism_level": "very_high",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "medium", "income_level": "medium", "population_type": "mixed",
        "notes": "عروس الجبال - سياحة صيفية مكثفة - جامعة الملك خالد",
        "strong_sectors": ["hotel","restaurant","cafe","souvenir","honey_shop","grocery","pharmacy"],
        "weak_sectors": ["ev_charging_station","industrial","fishing"],
    },
    "خميس مشيط": {
        "economic_base": "عسكري + خدمي + تجاري",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "low", "income_level": "medium", "population_type": "mixed",
        "notes": "قاعدة عسكرية كبيرة - مدينة تجارية نشطة",
        "strong_sectors": ["grocery","pharmacy","restaurant","cafe","shopping","auto_repair","services"],
        "weak_sectors": ["ev_charging_station","hotel"],
    },
    "بيشة": {
        "economic_base": "زراعي + رعوي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة وادي بيشة - ماشية - عبور بين عسير ونجد",
        "strong_sectors": ["fuel","grocery","restaurant","auto_repair","pharmacy"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "النماص": {
        "economic_base": "سياحي جبلي + زراعي",
        "is_transit": False, "tourism_level": "high",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "وجهة صيفية - عسل - رمان - مناخ بارد",
        "strong_sectors": ["hotel","restaurant","cafe","souvenir","honey_shop","grocery","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","industrial"],
    },
    "بارق": {
        "economic_base": "زراعي + سياحي جبلي محدود",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "زراعة جبلية - عسل - سياحة طبيعية محدودة - سيارات كهربائية شبه معدومة",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair","honey_shop","restaurant","bakery"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","luxury","electronics_store"],
    },
    "تنومة": {
        "economic_base": "زراعي + رعوي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية جبلية - زراعة وعسل - احتياجات أساسية فقط",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },
    "محايل": {
        "economic_base": "زراعي + خدمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة ساحلية وجبلية - خدمات يومية",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair","bakery"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "أحد رفيدة": {
        "economic_base": "زراعي + خدمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "مدينة صغيرة في منطقة عسير",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "ظهران الجنوب": {
        "economic_base": "زراعي + قبلي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "منطقة جبلية - قرب اليمن - خدمات أساسية",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },
    "سراة عبيدة": {
        "economic_base": "زراعي + سياحي جبلي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "مرتفعات جبلية - مناطق طبيعية - سياحة محدودة",
        "strong_sectors": ["grocery","pharmacy","fuel","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },
    "رجال ألمع": {
        "economic_base": "سياحي + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرى تراثية - سياحة جبلية - عسل",
        "strong_sectors": ["grocery","fuel","restaurant","honey_shop"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },

    # ─── منطقة جازان ─────────────────────────────────────────────────
    "جازان": {
        "economic_base": "صناعي + ميناء + صيد + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": True, "has_industrial": True, "agricultural": False,
        "ev_readiness": "low", "income_level": "medium", "population_type": "mixed",
        "notes": "ميناء وصناعة - جامعة - كثافة سكانية عالية",
        "strong_sectors": ["grocery","pharmacy","restaurant","cafe","auto_repair","services","clothing_store"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "صبيا": {
        "economic_base": "زراعي + تجاري",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة جازان - موز وقهوة خضراء - سوق محلي نشط",
        "strong_sectors": ["grocery","pharmacy","restaurant","fuel","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "أبو عريش": {
        "economic_base": "تجاري + زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "مدينة تجارية في جازان",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","services"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "الدرب": {
        "economic_base": "زراعي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "طريق يمن - زراعة",
        "strong_sectors": ["fuel","grocery","pharmacy","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "فيفا": {
        "economic_base": "زراعي + سياحي جبلي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "جبال خضراء - سياحة طبيعية متنامية",
        "strong_sectors": ["grocery","fuel","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },
    "فرسان": {
        "economic_base": "صيد + سياحي جزيري",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "جزر فرسان - غوص - صيد - سياحة بيئية",
        "strong_sectors": ["grocery","pharmacy","fuel","fish_market","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },

    # ─── منطقة القصيم ────────────────────────────────────────────────
    "بريدة": {
        "economic_base": "تجاري + زراعي + ديني",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": True, "agricultural": True,
        "ev_readiness": "low", "income_level": "medium", "population_type": "families",
        "notes": "عاصمة القصيم - محافظة بطبعها - تجارة تمور - سوق ماشية",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","services","dates_shop","hardware","clothing_store"],
        "weak_sectors": ["ev_charging_station","cinema","nightclub","luxury"],
    },
    "عنيزة": {
        "economic_base": "تجاري + زراعي + علمي",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "low", "income_level": "medium", "population_type": "families",
        "notes": "مدينة العلم - علماء - تجارة - تمور",
        "strong_sectors": ["grocery","pharmacy","services","restaurant","dates_shop"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "الرس": {
        "economic_base": "زراعي + تجاري + جامعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة التمر - جامعة القصيم",
        "strong_sectors": ["grocery","pharmacy","restaurant","services"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "البكيرية": {
        "economic_base": "زراعي + تجاري",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "زراعة القصيم - تمور",
        "strong_sectors": ["grocery","pharmacy","fuel","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "عيون الجواء": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية زراعية",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },

    # ─── منطقة تبوك ──────────────────────────────────────────────────
    "تبوك": {
        "economic_base": "عسكري + تجاري + سياحي (نيوم)",
        "is_transit": False, "tourism_level": "high",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "medium", "income_level": "medium", "population_type": "mixed",
        "notes": "بوابة نيوم - نمو متسارع - استثمارات ضخمة",
        "strong_sectors": ["hotel","restaurant","cafe","grocery","pharmacy","ev_charging_station","auto_repair"],
        "weak_sectors": ["agricultural_equipment","fishing"],
    },
    "أملج": {
        "economic_base": "سياحي ساحلي + صيد",
        "is_transit": False, "tourism_level": "high",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "low", "income_level": "medium", "population_type": "mixed",
        "notes": "شواطئ البحر الأحمر - غوص - سياحة بحرية",
        "strong_sectors": ["hotel","restaurant","cafe","souvenir","car_rental","fuel"],
        "weak_sectors": ["ev_charging_station","industrial","agricultural_equipment"],
    },
    "ضباء": {
        "economic_base": "صيد + عبور + ميناء",
        "is_transit": True, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "ميناء - صيد - طريق مصر عبر السفن",
        "strong_sectors": ["fuel","grocery","restaurant","auto_repair","pharmacy"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "حقل": {
        "economic_base": "سياحي + عبور + صيد",
        "is_transit": True, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "أقصى شمال غرب السعودية - حدود الأردن - خليج العقبة",
        "strong_sectors": ["hotel","restaurant","fuel","car_rental","grocery"],
        "weak_sectors": ["ev_charging_station","industrial","agricultural_equipment"],
    },
    "شرما": {
        "economic_base": "سياحي ساحلي",
        "is_transit": False, "tourism_level": "high",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "low", "income_level": "medium", "population_type": "mixed",
        "notes": "قرب نيوم - سياحة ساحلية",
        "strong_sectors": ["hotel","restaurant","cafe","car_rental"],
        "weak_sectors": ["agricultural_equipment","industrial"],
    },

    # ─── منطقة حائل ──────────────────────────────────────────────────
    "حائل": {
        "economic_base": "إداري + زراعي + سياحي صحراوي",
        "is_transit": True, "tourism_level": "medium",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "عاصمة الفروسية - صحراء النفود - جامعة حائل",
        "strong_sectors": ["grocery","pharmacy","restaurant","cafe","auto_repair","hotel","services"],
        "weak_sectors": ["ev_charging_station","cinema","luxury","fishing"],
    },
    "بقعاء": {
        "economic_base": "زراعي + رعوي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "ريف حائل",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "الغزالة": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية زراعية",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },

    # ─── منطقة الحدود الشمالية ───────────────────────────────────────
    "عرعر": {
        "economic_base": "نفطي + تجاري حدودي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "حدود العراق - تجارة عبور - نفط",
        "strong_sectors": ["fuel","grocery","restaurant","auto_repair","pharmacy","services"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center","luxury"],
    },
    "رفحاء": {
        "economic_base": "عبور + خدمي",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "طريق عبور العراق - خدمات الطريق",
        "strong_sectors": ["fuel","restaurant","grocery","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "طريف": {
        "economic_base": "عبور + خدمي + نفطي",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "أقصى الشمال الغربي - حدود الأردن - طريق دولي",
        "strong_sectors": ["fuel","restaurant","auto_repair","grocery"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },

    # ─── منطقة الجوف ─────────────────────────────────────────────────
    "سكاكا": {
        "economic_base": "زراعي + إداري + طاقة شمسية",
        "is_transit": False, "tourism_level": "low",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "عاصمة الجوف - زيتون وتمر - جامعة الجوف",
        "strong_sectors": ["grocery","pharmacy","restaurant","services","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","luxury","fishing"],
    },
    "القريات": {
        "economic_base": "زراعي + عبور",
        "is_transit": True, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "حدود الأردن - زراعة - تمور",
        "strong_sectors": ["fuel","grocery","pharmacy","restaurant","auto_repair"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "دومة الجندل": {
        "economic_base": "تراثي + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "آثار تاريخية - سياحة تراثية - زراعة",
        "strong_sectors": ["grocery","pharmacy","fuel","restaurant"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },

    # ─── منطقة نجران ─────────────────────────────────────────────────
    "نجران": {
        "economic_base": "تجاري + زراعي + تراثي + حدودي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "قرب اليمن - تجارة حدودية - تراث عريق - جامعة",
        "strong_sectors": ["grocery","pharmacy","restaurant","auto_repair","fuel","services","clothing_store"],
        "weak_sectors": ["ev_charging_station","cinema","luxury"],
    },
    "شرورة": {
        "economic_base": "نفطي + عسكري",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": False,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "workers",
        "notes": "قاعدة عسكرية - نفط - بعيدة - خدمات أساسية فقط",
        "strong_sectors": ["grocery","pharmacy","restaurant","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","luxury"],
    },
    "حبونا": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية صغيرة - زراعة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },

    # ─── منطقة الباحة ────────────────────────────────────────────────
    "الباحة": {
        "economic_base": "سياحي جبلي + زراعي + عسل + جامعي",
        "is_transit": False, "tourism_level": "high",
        "has_university": True, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "mixed",
        "notes": "سياحة جبلية - عسل مشهور - مناخ معتدل - جامعة الباحة",
        "strong_sectors": ["hotel","restaurant","cafe","souvenir","honey_shop","grocery","pharmacy"],
        "weak_sectors": ["ev_charging_station","cinema","industrial"],
    },
    "بلجرشي": {
        "economic_base": "سياحي + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "منطقة جبلية - سياحة داخلية - زراعة",
        "strong_sectors": ["grocery","restaurant","fuel","pharmacy","honey_shop"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "المخواة": {
        "economic_base": "زراعي + رعوي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "زراعة وعسل - قرية صغيرة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel","fitness_center"],
    },
    "العقيق": {
        "economic_base": "زراعي + سياحي جبلي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "مرتفعات الباحة - سياحة محدودة",
        "strong_sectors": ["grocery","fuel","restaurant","honey_shop"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
    "غامد الزناد": {
        "economic_base": "سياحي + زراعي",
        "is_transit": False, "tourism_level": "medium",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "medium", "population_type": "families",
        "notes": "منطقة جبلية - شلالات - سياحة طبيعية",
        "strong_sectors": ["grocery","restaurant","fuel","honey_shop"],
        "weak_sectors": ["ev_charging_station","cinema","fitness_center"],
    },
    "قلوة": {
        "economic_base": "زراعي",
        "is_transit": False, "tourism_level": "low",
        "has_university": False, "has_industrial": False, "agricultural": True,
        "ev_readiness": "very_low", "income_level": "low", "population_type": "families",
        "notes": "قرية صغيرة - زراعة",
        "strong_sectors": ["grocery","pharmacy","fuel"],
        "weak_sectors": ["ev_charging_station","cinema","hotel"],
    },
}


def get_governorate_profile(gov_name: str) -> Optional[dict]:
    if not gov_name:
        return None
    if gov_name in GOVERNORATE_ECONOMIC_PROFILE:
        return GOVERNORATE_ECONOMIC_PROFILE[gov_name]
    for key, profile in GOVERNORATE_ECONOMIC_PROFILE.items():
        if key in gov_name or gov_name in key:
            return profile
    return None


# ══════════════════════════════════════════════════════════════════════
# 2. محرك اختبار الطلب الحقيقي
#    السؤال: هل غياب النشاط = فرصة؟ أم = غياب طلب؟
# ══════════════════════════════════════════════════════════════════════

DEMAND_PREREQUISITES = {
    "ev_charging_station": {
        "name": "شحن كهربائي",
        "conditions": [
            {"check": "ev_readiness", "required": ["medium","high"], "weight": 60,
             "fail": "السيارات الكهربائية شبه معدومة في هذه المحافظة - غياب المحطة = غياب طلب"},
            {"check": "is_transit", "required": True, "weight": 25,
             "fail": "المنطقة ليست نقطة عبور - أسطول كهربائي محدود جداً"},
            {"check": "income_level", "required": ["high","very_high"], "weight": 15,
             "fail": "مستوى الدخل لا يدعم انتشار السيارات الكهربائية"},
        ],
        "min_score": 40,
    },
    "cinema": {
        "name": "سينما",
        "conditions": [
            {"check": "pop_min", "required": 50000, "weight": 50,
             "fail": "السكان أقل من 50,000 - السينما لن تجد جمهوراً"},
            {"check": "income_level", "required": ["medium","high","very_high"], "weight": 30,
             "fail": "مستوى الدخل لا يدعم الإنفاق على الترفيه"},
            {"check": "tourism_level", "required": ["medium","high","very_high"], "weight": 20,
             "fail": "منطقة منخفضة السياحة - قاعدة عملاء محدودة"},
        ],
        "min_score": 50,
    },
    "fitness_center": {
        "name": "نادٍ رياضي",
        "conditions": [
            {"check": "pop_min", "required": 20000, "weight": 40,
             "fail": "السكان أقل من 20,000 - قاعدة اشتراكات غير كافية"},
            {"check": "income_level", "required": ["medium","high","very_high"], "weight": 40,
             "fail": "الدخل المنخفض يجعل الاشتراك الشهري عبئاً"},
            {"check": "has_university", "required": True, "weight": 20,
             "fail": "غياب الجامعة = قلة الشباب المستهدف"},
        ],
        "min_score": 40,
    },
    "hotel": {
        "name": "فندق",
        "conditions": [
            {"check": "tourism_level", "required": ["medium","high","very_high"], "weight": 50,
             "fail": "السياحة منخفضة - الفندق لن يجد نزلاء"},
            {"check": "is_transit", "required": True, "weight": 30,
             "fail": "المنطقة ليست نقطة عبور - ليالي الإقامة قليلة"},
            {"check": "has_industrial", "required": True, "weight": 20,
             "fail": "لا يوجد نشاط أعمال يجذب المسافرين"},
        ],
        "min_score": 30,
    },
    "car_rental": {
        "name": "تأجير سيارات",
        "conditions": [
            {"check": "tourism_level", "required": ["high","very_high"], "weight": 60,
             "fail": "السياحة منخفضة - الطلب على التأجير هزيل"},
            {"check": "has_industrial", "required": True, "weight": 40,
             "fail": "لا يوجد نشاط أعمال يستدعي تأجير السيارات"},
        ],
        "min_score": 40,
    },
    "beauty_salon": {
        "name": "صالون تجميل",
        "conditions": [
            {"check": "female_proxy", "required": True, "weight": 50,
             "fail": "لا توجد مؤشرات كافية على كثافة نسائية (مدارس بنات؟ أحياء عائلية؟)"},
            {"check": "income_level", "required": ["medium","high","very_high"], "weight": 50,
             "fail": "مستوى الدخل لا يدعم الإنفاق على التجميل بانتظام"},
        ],
        "min_score": 50,
    },
    "agricultural_equipment": {
        "name": "معدات زراعية",
        "conditions": [
            {"check": "agricultural", "required": True, "weight": 100,
             "fail": "المحافظة غير زراعية - لا طلب على معدات الزراعة"},
        ],
        "min_score": 70,
    },
    "souvenir": {
        "name": "تذكارات",
        "conditions": [
            {"check": "tourism_level", "required": ["medium","high","very_high"], "weight": 100,
             "fail": "لا يوجد سياحة كافية لمحل تذكارات"},
        ],
        "min_score": 50,
    },
    "museum": {
        "name": "متحف",
        "conditions": [
            {"check": "tourism_level", "required": ["high","very_high"], "weight": 70,
             "fail": "السياحة منخفضة - المتحف لن يجد زواراً"},
            {"check": "pop_min", "required": 30000, "weight": 30,
             "fail": "السكان أقل من الحد الأدنى لاستدامة متحف"},
        ],
        "min_score": 50,
    },
}


def validate_demand(cat: str, gov_profile: Optional[dict], local_population: int, pbc: dict) -> dict:
    """يختبر إذا كان الطلب على نشاط ما حقيقياً قبل اعتباره فرصة."""
    if cat not in DEMAND_PREREQUISITES:
        return {"is_valid": True, "score": 80, "verdict": "طلب مضمون",
                "verdict_color": "#10b981", "pass_reasons": [], "fail_reasons": [],
                "has_prerequisite": False}

    prereq = DEMAND_PREREQUISITES[cat]
    conditions = prereq["conditions"]
    total_weight = sum(c["weight"] for c in conditions)
    earned = 0
    pass_reasons, fail_reasons = [], []

    for c in conditions:
        check = c["check"]
        required = c["required"]
        passed = False

        if check == "ev_readiness" and gov_profile:
            passed = gov_profile.get("ev_readiness") in required
        elif check == "is_transit" and gov_profile:
            passed = gov_profile.get("is_transit") == required
        elif check == "income_level" and gov_profile:
            passed = gov_profile.get("income_level") in required
        elif check == "pop_min":
            passed = (local_population or 0) >= required
        elif check == "tourism_level" and gov_profile:
            passed = gov_profile.get("tourism_level") in required
        elif check == "has_university" and gov_profile:
            passed = gov_profile.get("has_university") == required
        elif check == "has_industrial" and gov_profile:
            passed = gov_profile.get("has_industrial") == required
        elif check == "agricultural" and gov_profile:
            passed = gov_profile.get("agricultural") == required
        elif check == "female_proxy":
            schools = len(pbc.get("school", []))
            pop_type = (gov_profile or {}).get("population_type", "mixed")
            passed = schools >= 2 or pop_type in ("families", "mixed")
        else:
            passed = True

        if passed:
            earned += c["weight"]
            pass_reasons.append(f"✓ شرط مكتمل")
        else:
            fail_reasons.append(f"✗ {c['fail']}")

    score = int((earned / total_weight) * 100) if total_weight > 0 else 0
    is_valid = score >= prereq["min_score"]

    if is_valid:
        verdict, color = "طلب موجود", "#10b981"
    elif score >= prereq["min_score"] * 0.6:
        verdict, color = "طلب محدود - يحتاج دراسة", "#f59e0b"
    else:
        verdict, color = "غياب طلب - ليس فرصة", "#ef4444"

    return {
        "is_valid": is_valid,
        "score": score,
        "verdict": verdict,
        "verdict_color": color,
        "pass_reasons": pass_reasons,
        "fail_reasons": fail_reasons,
        "has_prerequisite": True,
        "activity_name": prereq["name"],
    }


# ══════════════════════════════════════════════════════════════════════
# 3. محرك المجاورات (الجيدة والسيئة)
# ══════════════════════════════════════════════════════════════════════

GOOD_NEIGHBORS: Dict[str, List[dict]] = {
    "cafe": [
        {"cat": "car_wash", "reason": "وقت الانتظار = قهوة", "boost": 20},
        {"cat": "fitness_center", "reason": "بعد التمرين = قهوة", "boost": 15},
        {"cat": "clothing_store", "reason": "راحة أثناء التسوق", "boost": 15},
        {"cat": "ev_charging_station", "reason": "انتظار الشحن = قهوة", "boost": 18},
        {"cat": "bank", "reason": "انتظار الدور", "boost": 10},
        {"cat": "bookstore", "reason": "ثقافة القراءة والقهوة", "boost": 15},
    ],
    "pharmacy": [
        {"cat": "clinic", "reason": "الوصفة الطبية مباشرة", "boost": 25},
        {"cat": "hospital", "reason": "احتياجات المرضى", "boost": 25},
        {"cat": "dentist", "reason": "دواء أسنان فوري", "boost": 18},
        {"cat": "medical_lab", "reason": "رحلة العلاج المتكاملة", "boost": 15},
        {"cat": "grocery", "reason": "رحلة الاحتياجات اليومية", "boost": 12},
    ],
    "restaurant": [
        {"cat": "cinema", "reason": "الخروج العائلي", "boost": 20},
        {"cat": "mosque", "reason": "وجبة ما بعد الصلاة", "boost": 18},
        {"cat": "hotel", "reason": "ضيافة النزلاء", "boost": 20},
        {"cat": "hospital", "reason": "طعام المرافقين", "boost": 15},
        {"cat": "shopping", "reason": "وجبة أثناء التسوق", "boost": 15},
    ],
    "auto_repair": [
        {"cat": "fuel", "reason": "خدمة متكاملة للسيارة", "boost": 20},
        {"cat": "tyre_shop", "reason": "نفس العميل", "boost": 22},
        {"cat": "car_wash", "reason": "إكمال الصيانة بالغسيل", "boost": 15},
    ],
    "clothing_store": [
        {"cat": "beauty_salon", "reason": "إطلالة كاملة", "boost": 18},
        {"cat": "shoe_shop", "reason": "تنسيق الملابس والأحذية", "boost": 20},
        {"cat": "cafe", "reason": "راحة أثناء التسوق", "boost": 12},
    ],
    "barber": [
        {"cat": "cafe", "reason": "انتظار الدور = قهوة", "boost": 18},
        {"cat": "car_wash", "reason": "اغسل سيارتك وأنت تحلق", "boost": 20},
    ],
    "beauty_salon": [
        {"cat": "clothing_store", "reason": "إطلالة كاملة", "boost": 20},
        {"cat": "cafe", "reason": "انتظار الدور", "boost": 15},
        {"cat": "fitness_center", "reason": "نفس الاهتمام بالمظهر", "boost": 15},
    ],
    "grocery": [
        {"cat": "pharmacy", "reason": "رحلة احتياجات يومية", "boost": 20},
        {"cat": "bakery", "reason": "خبز طازج مع البقالة", "boost": 18},
        {"cat": "butcher", "reason": "مشتريات المطبخ الكاملة", "boost": 18},
        {"cat": "atm", "reason": "سحب نقدي للتسوق", "boost": 12},
    ],
    "services": [
        {"cat": "school", "reason": "طلاب يحتاجون قرطاسية وطباعة", "boost": 22},
        {"cat": "bank", "reason": "توثيق + طباعة", "boost": 18},
        {"cat": "government_office", "reason": "معاملات تحتاج طباعة", "boost": 20},
    ],
    "fuel": [
        {"cat": "car_wash", "reason": "عبّي البنزين واغسل السيارة", "boost": 22},
        {"cat": "cafe", "reason": "استراحة المسافر", "boost": 20},
        {"cat": "auto_repair", "reason": "خدمات سيارات متكاملة", "boost": 18},
        {"cat": "fast_food", "reason": "وجبة الطريق", "boost": 18},
    ],
}

BAD_NEIGHBORS: Dict[str, List[dict]] = {
    "beauty_salon": [
        {"cat": "metalworker", "reason": "ضوضاء + شرر + صورة سيئة", "penalty": -35},
        {"cat": "auto_repair", "reason": "زيوت + ضوضاء + عملاء مختلفون", "penalty": -25},
        {"cat": "tyre_shop", "reason": "ضوضاء + روائح مطاط", "penalty": -28},
        {"cat": "gas_supply", "reason": "خطر + روائح", "penalty": -30},
        {"cat": "pest_control", "reason": "صورة سلبية + كيماويات", "penalty": -25},
    ],
    "restaurant": [
        {"cat": "metalworker", "reason": "ضوضاء + شرر يؤثر على تجربة الطعام", "penalty": -30},
        {"cat": "auto_repair", "reason": "روائح زيوت تؤثر على رائحة الطعام", "penalty": -25},
        {"cat": "tyre_shop", "reason": "روائح مطاط + ضوضاء", "penalty": -20},
        {"cat": "gas_supply", "reason": "خطر حريق + روائح", "penalty": -35},
        {"cat": "pest_control", "reason": "صورة نفسية سلبية", "penalty": -22},
    ],
    "clinic": [
        {"cat": "metalworker", "reason": "ضوضاء تؤثر على المرضى", "penalty": -30},
        {"cat": "auto_repair", "reason": "ضوضاء + روائح لا تناسب البيئة الطبية", "penalty": -25},
        {"cat": "tyre_shop", "reason": "ضوضاء مرتفعة", "penalty": -22},
        {"cat": "gas_supply", "reason": "خطر + روائح + بيئة غير طبية", "penalty": -30},
    ],
    "jewelry": [
        {"cat": "auto_repair", "reason": "بيئة غير آمنة + عملاء مختلفون", "penalty": -25},
        {"cat": "tyre_shop", "reason": "صورة لا تليق بمحل ذهب", "penalty": -18},
        {"cat": "gas_supply", "reason": "خطر + بيئة غير مناسبة", "penalty": -30},
    ],
    "school": [
        {"cat": "gas_supply", "reason": "خطر على الأطفال", "penalty": -30},
        {"cat": "pest_control", "reason": "كيماويات قرب الأطفال", "penalty": -25},
        {"cat": "metalworker", "reason": "شرر + ضوضاء قرب الأطفال", "penalty": -28},
        {"cat": "auto_repair", "reason": "زيوت + بيئة غير مناسبة", "penalty": -20},
    ],
    "cafe": [
        {"cat": "metalworker", "reason": "ضوضاء تدمر جو القهوة الهادئ", "penalty": -30},
        {"cat": "auto_repair", "reason": "روائح + ضوضاء", "penalty": -22},
        {"cat": "gas_supply", "reason": "روائح وقود مع القهوة", "penalty": -28},
    ],
    "pharmacy": [
        {"cat": "metalworker", "reason": "ضوضاء تؤثر على التركيز والصحة", "penalty": -18},
        {"cat": "gas_supply", "reason": "خطر + روائح قرب الدواء", "penalty": -20},
    ],
    "grocery": [
        {"cat": "pest_control", "reason": "صورة سلبية تجاور الغذاء", "penalty": -25},
        {"cat": "gas_supply", "reason": "خطر حريق قرب الأغذية", "penalty": -30},
        {"cat": "metalworker", "reason": "تلوث + روائح", "penalty": -20},
    ],
}


def analyze_neighbors(target_cat: str, pbc: dict, radius_km: float = 2.0) -> dict:
    """يحلل تأثير الجيران على نشاط معين."""
    good_list = GOOD_NEIGHBORS.get(target_cat, [])
    bad_list = BAD_NEIGHBORS.get(target_cat, [])

    found_good, found_bad = [], []
    net_effect = 0

    for item in good_list:
        if item["cat"] in pbc and pbc[item["cat"]]:
            count = len(pbc[item["cat"]])
            found_good.append({**item, "count": count})
            net_effect += min(item["boost"], item["boost"] * (1 + count * 0.1))

    for item in bad_list:
        if item["cat"] in pbc and pbc[item["cat"]]:
            count = len(pbc[item["cat"]])
            found_bad.append({**item, "count": count})
            net_effect += item["penalty"]

    net_effect = int(max(-60, min(50, net_effect)))

    if net_effect >= 20:
        verdict, color = "محيط ممتاز ✓", "#10b981"
    elif net_effect >= 5:
        verdict, color = "محيط جيد", "#22c55e"
    elif net_effect >= -10:
        verdict, color = "محيط محايد", "#94a3b8"
    elif net_effect >= -30:
        verdict, color = "محيط غير مناسب ⚠", "#f97316"
    else:
        verdict, color = "محيط سيء - خطر ✗", "#ef4444"

    return {
        "good_neighbors": found_good,
        "bad_neighbors": found_bad,
        "net_effect": net_effect,
        "verdict": verdict,
        "verdict_color": color,
        "has_bad": len(found_bad) > 0,
        "has_good": len(found_good) > 0,
    }


# ══════════════════════════════════════════════════════════════════════
# 4. هوية المنطقة الاقتصادية
# ══════════════════════════════════════════════════════════════════════

AREA_IDENTITY_PATTERNS = {
    "educational_hub": {
        "name": "حي تعليمي", "icon": "📚",
        "indicators": ["school","library","training_center","quran_school","services"],
        "min_indicators": 2,
        "description": "الطلاب وأولياء الأمور هم المحرك الرئيسي",
        "strong_opportunities": ["bakery","fast_food","sweets","mobile_repair","services"],
        "weak_opportunities": ["hotel","car_rental","fitness_center"],
    },
    "medical_district": {
        "name": "حي طبي", "icon": "⚕️",
        "indicators": ["hospital","clinic","pharmacy","medical_lab","dentist"],
        "min_indicators": 2,
        "description": "المرضى والمرافقون يحركون الاقتصاد",
        "strong_opportunities": ["pharmacy","restaurant","cafe","hotel"],
        "weak_opportunities": ["cinema","nightclub","game_center"],
    },
    "automotive_corridor": {
        "name": "ممر السيارات", "icon": "🚗",
        "indicators": ["fuel","auto_repair","car_wash","car_dealer","tyre_shop","oil_change"],
        "min_indicators": 3,
        "description": "حركة مرور عالية - وقفات قصيرة - خدمات السيارة تسيطر",
        "strong_opportunities": ["cafe","fast_food","auto_parts"],
        "weak_opportunities": ["clothing_store","furniture","beauty_salon"],
    },
    "food_destination": {
        "name": "وجهة طعام", "icon": "🍽️",
        "indicators": ["restaurant","cafe","fast_food","bakery","sweets"],
        "min_indicators": 4,
        "description": "تنافسية عالية - العملاء يأتون للتجربة لا للاحتياج",
        "strong_opportunities": ["dessert","juice","shisha"],
        "weak_opportunities": ["auto_repair","hardware"],
    },
    "residential_service": {
        "name": "حي سكني خدماتي", "icon": "🏘️",
        "indicators": ["grocery","pharmacy","mosque","school","bakery"],
        "min_indicators": 3,
        "description": "حي سكني متكامل - الاحتياجات اليومية تحرك الاقتصاد",
        "strong_opportunities": ["clinic","barber","beauty_salon","cleaning","gas_supply"],
        "weak_opportunities": ["hotel","cinema","museum"],
    },
    "commercial_center": {
        "name": "مركز تجاري", "icon": "🏬",
        "indicators": ["shopping","clothing_store","electronics_store","bank","atm"],
        "min_indicators": 3,
        "description": "التسوق والأعمال هو المحرك",
        "strong_opportunities": ["restaurant","cafe","parking","services"],
        "weak_opportunities": ["school","agricultural_equipment"],
    },
    "tourism_area": {
        "name": "منطقة سياحية", "icon": "🗺️",
        "indicators": ["hotel","tourist_attraction","museum","restaurant","shopping"],
        "min_indicators": 2,
        "description": "الزوار هم المستهدف - موسمية عالية",
        "strong_opportunities": ["cafe","car_rental","souvenir"],
        "weak_opportunities": ["auto_repair","school","hardware"],
    },
    "government_hub": {
        "name": "منطقة حكومية", "icon": "🏛️",
        "indicators": ["bank","services","atm","government_office"],
        "min_indicators": 3,
        "description": "موظفون وأصحاب معاملات - حركة صباحية",
        "strong_opportunities": ["cafe","fast_food","services","pharmacy"],
        "weak_opportunities": ["cinema","fitness_center","hotel"],
    },
}


def identify_area_identity(pbc: dict) -> dict:
    present = set(pbc.keys())
    matches = []
    for key, identity in AREA_IDENTITY_PATTERNS.items():
        found = [i for i in identity["indicators"] if i in present]
        if len(found) >= identity["min_indicators"]:
            strength = min(100, int(len(found) / len(identity["indicators"]) * 100))
            matches.append({
                "key": key, "name": identity["name"], "icon": identity["icon"],
                "description": identity["description"], "strength": strength,
                "indicators_present": found,
                "strong_opportunities": identity["strong_opportunities"],
                "weak_opportunities": identity["weak_opportunities"],
            })
    matches.sort(key=lambda x: -x["strength"])
    primary = matches[0] if matches else {
        "key": "undefined", "name": "منطقة متنوعة بلا هوية واضحة",
        "icon": "🏙️", "description": "تركيبة تجارية متنوعة", "strength": 0,
        "indicators_present": [], "strong_opportunities": [], "weak_opportunities": [],
    }
    return {"primary": primary, "all_matches": matches,
            "has_clear_identity": len(matches) > 0, "is_mixed": len(matches) > 1}


# ══════════════════════════════════════════════════════════════════════
# 5. رحلات العملاء
# ══════════════════════════════════════════════════════════════════════

SAUDI_TRIP_CHAINS = [
    {"id":"morning_family","name":"رحلة الصباح العائلية","icon":"🌅",
     "description":"إيصال الأطفال للمدرسة + شراء احتياجات",
     "stops":["school","bakery","grocery","pharmacy"],"time":"07:00-09:30"},
    {"id":"after_school","name":"رحلة ما بعد المدرسة","icon":"🎒",
     "description":"الأطفال يتوقفون في طريق العودة",
     "stops":["school","fast_food","sweets","grocery"],"time":"13:00-15:30"},
    {"id":"hospital_journey","name":"رحلة الرعاية الصحية","icon":"🏥",
     "description":"مريض + مرافقون = احتياجات متعددة",
     "stops":["clinic","pharmacy","medical_lab","cafe"],"time":"08:00-14:00"},
    {"id":"friday_journey","name":"رحلة الجمعة","icon":"🕌",
     "description":"ما بعد صلاة الجمعة",
     "stops":["mosque","restaurant","grocery","sweets"],"time":"12:00-15:00"},
    {"id":"car_service","name":"رحلة خدمة السيارة","icon":"🚗",
     "description":"غسيل + صيانة + قهوة",
     "stops":["fuel","car_wash","cafe","auto_repair"],"time":"مرنة"},
    {"id":"shopping_outing","name":"رحلة التسوق العائلي","icon":"🛍️",
     "description":"تسوق + طعام + ترفيه",
     "stops":["shopping","restaurant","cafe","cinema"],"time":"15:00-22:00"},
    {"id":"evening_social","name":"السهرة الاجتماعية","icon":"☕",
     "description":"جلسة شباب أو عائلية مسائية",
     "stops":["cafe","restaurant","sweets","shopping"],"time":"20:00-00:00"},
    {"id":"daily_essentials","name":"رحلة الاحتياجات اليومية","icon":"📦",
     "description":"تسوق أسبوعي في رحلة واحدة",
     "stops":["grocery","pharmacy","bakery","butcher"],"time":"16:00-20:00"},
    {"id":"health_wellness","name":"رحلة الصحة والعناية","icon":"💪",
     "description":"رياضة + عناية + قهوة",
     "stops":["fitness_center","beauty_salon","cafe","clothing_store"],"time":"07:00-11:00"},
    {"id":"government_trip","name":"رحلة المعاملات","icon":"🏛️",
     "description":"بنك + طباعة + كافيه",
     "stops":["bank","services","cafe","fast_food"],"time":"08:00-14:00"},
]


def discover_trip_chains(pbc: dict) -> List[dict]:
    present = set(pbc.keys())
    results = []
    for chain in SAUDI_TRIP_CHAINS:
        stops = chain["stops"]
        p = [s for s in stops if s in present]
        m = [s for s in stops if s not in present]
        rate = len(p) / len(stops)
        results.append({**chain, "present_stops": p, "missing_stops": m,
                        "completion_rate": round(rate, 2), "completion_pct": int(rate * 100),
                        "is_complete": len(m) == 0, "is_partial": 0.4 <= rate < 1.0})
    results.sort(key=lambda x: -x["completion_rate"])
    return results


def get_journey_opportunities(chains: List[dict]) -> List[dict]:
    scores: Dict[str, dict] = {}
    for chain in chains:
        if chain["completion_rate"] < 0.4:
            continue
        for cat in chain["missing_stops"]:
            if cat not in scores:
                scores[cat] = {"cat": cat, "journeys": [], "score": 0}
            scores[cat]["journeys"].append({"name": chain["name"], "icon": chain["icon"],
                                            "pct": chain["completion_pct"]})
            scores[cat]["score"] += chain["completion_rate"] * 100
    return sorted(scores.values(), key=lambda x: -x["score"])[:8]


# ══════════════════════════════════════════════════════════════════════
# 6. مقارنة المناطق المشابهة
# ══════════════════════════════════════════════════════════════════════

SUCCESSFUL_AREA_PROFILES = {
    "residential_riyadh": {
        "name": "حي سكني متوسط - الرياض", "density": "سكني متوسط",
        "pop_range": (20000, 80000),
        "typical": {"grocery":3,"pharmacy":2,"restaurant":5,"cafe":4,"fast_food":3,
                    "school":2,"mosque":3,"bakery":2,"barber":2,"beauty_salon":1,"clinic":2},
        "success_keys": ["cafe","grocery","bakery"],
    },
    "commercial_strip": {
        "name": "شارع تجاري رئيسي", "density": "حضري",
        "pop_range": (50000, 200000),
        "typical": {"restaurant":10,"cafe":8,"fast_food":6,"shopping":5,"clothing_store":4,
                    "bank":3,"atm":5,"beauty_salon":3,"fitness_center":2,"services":4},
        "success_keys": ["cafe","restaurant","shopping"],
    },
    "university_area": {
        "name": "منطقة جامعية", "density": "سكني متوسط",
        "pop_range": (30000, 100000),
        "typical": {"cafe":10,"fast_food":8,"restaurant":6,"grocery":4,"bakery":3,
                    "fitness_center":3,"mobile_repair":4,"clothing_store":3,"atm":4,"barber":3},
        "success_keys": ["cafe","fast_food","mobile_repair"],
    },
    "medical_zone": {
        "name": "منطقة طبية", "density": "سكني محدود",
        "pop_range": (10000, 50000),
        "typical": {"pharmacy":6,"clinic":8,"hospital":2,"medical_lab":3,
                    "cafe":4,"restaurant":5,"fast_food":3,"hotel":2,"atm":3},
        "success_keys": ["pharmacy","cafe","restaurant"],
    },
    "transit_town": {
        "name": "مدينة عبور على طريق رئيسي", "density": "ريفي / أطراف",
        "pop_range": (5000, 40000),
        "typical": {"fuel":4,"restaurant":6,"fast_food":4,"auto_repair":3,"tyre_shop":2,"grocery":3},
        "success_keys": ["fuel","restaurant","auto_repair"],
    },
    "tourism_hub": {
        "name": "مدينة سياحية", "density": "سكني متوسط",
        "pop_range": (10000, 100000),
        "typical": {"hotel":6,"restaurant":10,"cafe":8,"souvenir":3,"car_rental":2,"grocery":3},
        "success_keys": ["hotel","cafe","restaurant"],
    },
}


def find_comparable_areas(area_character: str, local_population: int, pbc: dict) -> dict:
    present = set(pbc.keys())
    matches = []
    for key, profile in SUCCESSFUL_AREA_PROFILES.items():
        density_ok = profile["density"] in area_character or area_character in profile["density"]
        pop_min, pop_max = profile["pop_range"]
        pop_ok = not local_population or (pop_min <= local_population <= pop_max * 2)
        if density_ok and pop_ok:
            missing = [
                {"cat": cat, "expected": exp, "is_key": cat in profile["success_keys"]}
                for cat, exp in profile["typical"].items()
                if cat not in present and exp >= 2
            ]
            matches.append({
                "profile_name": profile["name"],
                "missing": sorted(missing, key=lambda x: -(x["expected"] + (10 if x["is_key"] else 0)))[:6],
            })
    if not matches:
        return {"found": False, "opportunities": []}
    merged: Dict[str, dict] = {}
    for m in matches:
        for item in m["missing"]:
            cat = item["cat"]
            if cat not in merged:
                merged[cat] = {"cat": cat, "count": 0, "is_key": False}
            merged[cat]["count"] += 1
            if item["is_key"]:
                merged[cat]["is_key"] = True
    opps = sorted(merged.values(), key=lambda x: -(x["count"] * 10 + (20 if x["is_key"] else 0)))
    return {"found": True, "primary_profile": matches[0]["profile_name"], "opportunities": opps[:6]}


# ══════════════════════════════════════════════════════════════════════
# 7. التقرير الشامل
# ══════════════════════════════════════════════════════════════════════

def generate_economic_intelligence_report(
    pbc: dict, a: dict, local_population: int, dna: dict,
    gov_name: str = "", target_cat: str = "", radius_km: float = 2.0,
) -> dict:
    area_character = a.get("area_character", "سكني محدود")
    gov_profile = get_governorate_profile(gov_name)
    identity = identify_area_identity(pbc)
    chains = discover_trip_chains(pbc)
    journey_opps = get_journey_opportunities(chains)
    comparable = find_comparable_areas(area_character, local_population, pbc)

    demand_validation = None
    if target_cat:
        demand_validation = validate_demand(target_cat, gov_profile, local_population, pbc)

    neighbor_analysis = None
    if target_cat:
        neighbor_analysis = analyze_neighbors(target_cat, pbc, radius_km)

    evidence_recs = _build_evidence_recs(pbc, gov_profile, identity, journey_opps, comparable)
    zero_demand = _check_zero_demand(pbc, gov_profile, local_population)
    summary = _build_summary(gov_profile, gov_name, identity, chains, comparable)

    return {
        "gov_profile": gov_profile,
        "gov_name": gov_name,
        "area_identity": identity,
        "trip_chains": chains,
        "journey_opportunities": journey_opps,
        "comparable_areas": comparable,
        "demand_validation": demand_validation,
        "neighbor_analysis": neighbor_analysis,
        "evidence_recommendations": evidence_recs,
        "economic_summary": summary,
        "zero_demand_warnings": zero_demand,
        "has_gov_profile": gov_profile is not None,
    }


def _build_evidence_recs(pbc, gov_profile, identity, journey_opps, comparable) -> List[dict]:
    seen: set = set()
    recs = []
    for opp in journey_opps[:3]:
        cat = opp["cat"]
        if cat not in seen:
            recs.append({"cat": cat, "source": "رحلة عميل", "source_icon": "🛤️",
                         "confidence": min(85, int(opp["score"])),
                         "reason": f"يكمل: {', '.join([j['name'] for j in opp['journeys'][:2]])}"})
            seen.add(cat)
    if comparable["found"]:
        for opp in comparable["opportunities"][:3]:
            cat = opp["cat"]
            if cat not in seen:
                recs.append({"cat": cat, "source": "منطقة مشابهة", "source_icon": "📊",
                             "confidence": 60 if opp["is_key"] else 50,
                             "reason": f"ينجح في {comparable['primary_profile']}"})
                seen.add(cat)
    for cat in identity["primary"].get("strong_opportunities", [])[:2]:
        if cat not in seen and cat not in pbc:
            recs.append({"cat": cat, "source": "هوية المنطقة", "source_icon": "🏙️",
                         "confidence": 55,
                         "reason": f"يناسب {identity['primary']['name']}"})
            seen.add(cat)
    if gov_profile:
        for cat in gov_profile.get("strong_sectors", [])[:2]:
            if cat not in seen and cat not in pbc:
                recs.append({"cat": cat, "source": "طابع المحافظة", "source_icon": "🏛️",
                             "confidence": 75,
                             "reason": f"قطاع قوي: {gov_profile.get('economic_base','')}"})
                seen.add(cat)
    recs.sort(key=lambda x: -x["confidence"])
    return recs[:6]


def _check_zero_demand(pbc, gov_profile, local_population) -> List[dict]:
    warnings = []
    if not gov_profile:
        return warnings
    checks = {
        "ev_charging_station": (
            gov_profile.get("ev_readiness") in ("very_low","low"),
            "السيارات الكهربائية نادرة في هذه المحافظة - الغياب = غياب طلب وليس فرصة"
        ),
        "cinema": (
            (local_population or 0) < 50000,
            f"السكان ({(local_population or 0):,}) أقل من الحد الأدنى للسينما (50,000)"
        ),
        "fitness_center": (
            gov_profile.get("income_level") == "low",
            "مستوى الدخل المنخفض يجعل الاشتراك الشهري عبئاً"
        ),
        "hotel": (
            gov_profile.get("tourism_level") in ("none","low")
            and not gov_profile.get("is_transit")
            and not gov_profile.get("has_industrial"),
            "لا سياحة ولا عبور ولا صناعة - من سيقيم في الفندق؟"
        ),
    }
    for cat, (condition, msg) in checks.items():
        if cat not in pbc and condition:
            warnings.append({"cat": cat, "message": msg, "severity": "high"})
    return warnings


def _build_summary(gov_profile, gov_name, identity, chains, comparable) -> str:
    parts = []
    if gov_profile and gov_name:
        parts.append(f"محافظة {gov_name}: {gov_profile.get('economic_base','')}. {gov_profile.get('notes','')}")
    if identity["has_clear_identity"]:
        parts.append(f"طابع المنطقة: {identity['primary']['name']} — {identity['primary']['description']}")
    complete = [c for c in chains if c["is_complete"]]
    partial = [c for c in chains if c["is_partial"]]
    if complete:
        parts.append(f"رحلات مكتملة: {', '.join([c['name'] for c in complete[:2]])}")
    if partial:
        top = partial[0]
        parts.append(f"رحلة '{top['name']}' مكتملة {top['completion_pct']}% — فرصة إكمال الناقص")
    if comparable["found"]:
        parts.append(f"تشابه مع '{comparable['primary_profile']}' — أنشطة ناجحة هناك غير موجودة هنا")
    return " • ".join(parts) if parts else "لا توجد بيانات كافية للتحليل الاقتصادي"
