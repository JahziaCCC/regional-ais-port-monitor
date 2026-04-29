from math import radians, sin, cos, sqrt, atan2
from collections import Counter, defaultdict
from ports import PORTS


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


def find_nearest_port(lat, lon):
    nearest = None
    nearest_distance = None

    for port in PORTS:
        distance = haversine_km(lat, lon, port["lat"], port["lon"])

        if nearest_distance is None or distance < nearest_distance:
            nearest = port
            nearest_distance = distance

    if nearest and nearest_distance <= nearest["radius_km"]:
        return nearest["name"], nearest["sea"], round(nearest_distance, 1)

    return "خارج نطاق الموانئ المحددة", detect_sea(lat, lon), None


def detect_sea(lat, lon):
    if 34 <= lon <= 43 and 12 <= lat <= 31:
        return "البحر الأحمر"

    if 47 <= lon <= 57 and 23 <= lat <= 30:
        return "الخليج العربي"

    return "غير محدد"


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

        port_name, sea, distance = find_nearest_port(lat, lon)

        cleaned.append({
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "sog": sog,
            "speed_class": speed_class,
            "port": port_name,
            "sea": sea,
            "distance_km": distance,
        })

    total = len(cleaned)

    sea_counter = Counter(v["sea"] for v in cleaned)
    speed_counter = Counter(v["speed_class"] for v in cleaned)
    port_counter = Counter(v["port"] for v in cleaned)

    port_speed = defaultdict(Counter)
    for v in cleaned:
        port_speed[v["port"]][v["speed_class"]] += 1

    return {
        "total": total,
        "abnormal": abnormal_count,
        "sea_counter": sea_counter,
        "speed_counter": speed_counter,
        "port_counter": port_counter,
        "port_speed": port_speed,
        "vessels": cleaned,
    }


def congestion_status(waiting_ratio):
    if waiting_ratio >= 70:
        return "🔴 ازدحام عالي"
    if waiting_ratio >= 40:
        return "🟡 متابعة تشغيلية"
    return "🟢 طبيعي"
