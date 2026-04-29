from datetime import datetime, timezone, timedelta
from analyzer import analyze_vessels, congestion_status
from telegram import send_telegram_message
from aisstream import get_ais_data


def ksa_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=3)))


def build_report(result):
    now = ksa_now().strftime("%Y-%m-%d %H:%M KSA")

    total = result["total"]
    abnormal = result["abnormal"]

    stopped = result["speed_counter"].get("متوقفة", 0)
    slow = result["speed_counter"].get("بطيئة", 0)
    medium = result["speed_counter"].get("متوسطة", 0)
    fast = result["speed_counter"].get("سريعة", 0)

    waiting = stopped + slow
    waiting_ratio = round((waiting / total) * 100, 1) if total else 0
    status = congestion_status(waiting_ratio)

    gulf = result["sea_counter"].get("الخليج العربي", 0)
    red = result["sea_counter"].get("البحر الأحمر", 0)
    unknown = result["sea_counter"].get("غير محدد", 0)

    top_ports = result["port_counter"].most_common(5)

    lines = []
    lines.append("📡 تقرير حركة السفن AIS — الخليج والبحر الأحمر")
    lines.append(f"🕒 وقت التحديث: {now}")
    lines.append("════════════════════")
    lines.append(f"🚢 إجمالي السفن بعد التنظيف: {total}")
    lines.append(f"🌊 الخليج العربي: {gulf}")
    lines.append(f"🌊 البحر الأحمر: {red}")
    lines.append(f"❔ غير محدد: {unknown}")
    lines.append(f"⚫ قراءات شاذة مستبعدة: {abnormal}")
    lines.append("════════════════════")
    lines.append("📊 تحليل السرعات")
    lines.append(f"🟥 متوقفة: {stopped}")
    lines.append(f"🟧 بطيئة 0–1 kn: {slow}")
    lines.append(f"🟨 متوسطة 1–15 kn: {medium}")
    lines.append(f"🟩 سريعة 15–35 kn: {fast}")
    lines.append("════════════════════")
    lines.append("📍 أعلى الموانئ / النطاقات نشاطًا")

    if top_ports:
        for i, (port, count) in enumerate(top_ports, 1):
            lines.append(f"{i}) {port}: {count} سفن")
    else:
        lines.append("لا توجد بيانات كافية.")

    lines.append("════════════════════")
    lines.append(f"📊 مؤشر التوقف/الانتظار: {waiting_ratio}%")
    lines.append(f"📌 الحالة: {status}")
    lines.append("════════════════════")

    if waiting_ratio >= 70:
        interpretation = "ارتفاع كبير في السفن المتوقفة أو البطيئة، وقد يشير إلى ضغط تشغيلي في مناطق الانتظار أو قرب الموانئ."
    elif waiting_ratio >= 40:
        interpretation = "يوجد ارتفاع نسبي في السفن المتوقفة أو البطيئة، ويوصى بمتابعة النافذة القادمة."
    else:
        interpretation = "الحركة ضمن النطاق الطبيعي ولا توجد مؤشرات ازدحام واضحة."

    lines.append("🧾 التفسير:")
    lines.append(interpretation)

    return "\n".join(lines)


def main():
    vessels = get_ais_data(limit=50)
    result = analyze_vessels(vessels)
    report = build_report(result)

    print(report)
    send_telegram_message(report)


if __name__ == "__main__":
    main()
