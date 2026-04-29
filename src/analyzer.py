from math import radians, sin, cos, sqrt, atan2
from collections import Counter, defaultdict
from ports import ZONES


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def detect_sea(lat, lon):
    if 34 <= lon <= 43 and 12 <= lat <= 31:
        return "البحر الأحمر"

    if 47 <= lon <= 59 and 19 <= lat <= 30:
        return "الخليج العربي"

    return "غير محدد"


def find_zone(lat, lon):
    matches = []

    for zone in ZONES:
        distance = haversine_km(lat, lon, zone["lat"], zone["lon"])

        if distance <= zone["radius_km"]:
            matches.append({
                "name": zone["name"],
                "sea": zone["sea"],
                "type": zone["type"],
                "distance": round(distance, 1),
                "radius": zone["radius_km"],
            })

    if not matches:
        return {
            "name": "خارج نطاق الموانئ المحددة",
            "sea": detect_sea(lat, lon),
            "type": "Offshore / Transit",
            "distance": None,
        }

    # الأولوية للموانئ الصغيرة إذا كانت قريبة جدًا
    port_matches = [m for m in matches if m["type"] == "Port"]
    if port_matches:
        nearest_port = min(port_matches, key=lambda x: x["distance"])
        if nearest_port["distance"] <= 5:
            return nearest_port

    # بعد ذلك نعطي الأولوية لمناطق الانتظار لأنها أدق للحركة البحرية خارج الأرصفة
    anchorage_matches = [m for m in matches if m["type"] == "Anchorage"]
    if anchorage_matches:
        return min(anchorage_matches, key=lambda x: x["distance"])

    return min(matches, key=lambda x: x["distance"])


def classify_speed(sog):
    if sog is None:
        return "غير متاح"

    if sog > 35:
        return "شاذة"

    if sog == 0:
        return "متوقفة"

    if 0 < sog <= 1:
        return "بطيئة"

    if 1 < sog <= 15:
        return "متوسطة"

    if 15 < sog <= 35:
        return "سريعة"

    return "غير متاح"


def analyze_vessels(vessels):
    cleaned = []
    seen = set()
    abnormal_count = 0

    for v in vessels:
        mmsi = v.get("mmsi")
        lat = v.get("lat")
        lon = v.get("lon")
        sog = v.get("sog")

        if lat is None or lon is None:
            continue

        key = (mmsi, round(lat, 4), round(lon, 4))
        if key in seen:
            continue

        seen.add(key)

        speed_class = classify_speed(sog)

        if speed_class == "شاذة":
            abnormal_count += 1
            continue

        zone = find_zone(lat, lon)

        cleaned.append({
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "sog": sog,
            "speed_class": speed_class,
            "port": zone["name"],
            "zone_type": zone["type"],
            "sea": zone["sea"],
            "distance_km": zone["distance"],
        })

    total = len(cleaned)

    sea_counter = Counter(v["sea"] for v in cleaned)
    speed_counter = Counter(v["speed_class"] for v in cleaned)
    port_counter = Counter(v["port"] for v in cleaned)
    zone_type_counter = Counter(v["zone_type"] for v in cleaned)

    port_speed = defaultdict(Counter)
    for v in cleaned:
        port_speed[v["port"]][v["speed_class"]] += 1

    return {
        "total": total,
        "abnormal": abnormal_count,
        "sea_counter": sea_counter,
        "speed_counter": speed_counter,
        "port_counter": port_counter,
        "zone_type_counter": zone_type_counter,
        "port_speed": port_speed,
        "vessels": cleaned,
    }


def congestion_status(waiting_ratio):
    if waiting_ratio >= 70:
        return "🔴 ازدحام عالي"
    if waiting_ratio >= 40:
        return "🟡 متابعة تشغيلية"
    return "🟢 طبيعي"
