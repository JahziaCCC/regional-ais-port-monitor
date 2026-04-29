import os
import requests
import numpy as np
import cv2
from datetime import datetime, timedelta, timezone


def get_token():
    url = "https://services.sentinel-hub.com/oauth/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("SH_CLIENT_ID"),
        "client_secret": os.getenv("SH_CLIENT_SECRET"),
    }

    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def get_sar_image():
    token = get_token()

    url = "https://services.sentinel-hub.com/api/v1/process"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/png",
    }

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=5)

    payload = {
        "input": {
            "bounds": {
                "bbox": [34.0, 12.0, 43.0, 30.0],
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        },
                        "acquisitionMode": "IW",
                    },
                }
            ],
        },
        "output": {
            "width": 1024,
            "height": 1024,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/png"},
                }
            ],
        },
        "evalscript": """
        //VERSION=3
        function setup() {
            return {
                input: ["VV"],
                output: { bands: 1, sampleType: "UINT8" }
            };
        }

        function evaluatePixel(sample) {
            let vv = sample.VV;
            let value = Math.log(vv + 0.0001) * 35 + 220;
            value = Math.max(0, Math.min(255, value));
            return [value];
        }
        """,
    }

    r = requests.post(url, json=payload, headers=headers, timeout=60)

    if r.status_code != 200:
        print("Sentinel Hub error:", r.status_code, r.text[:500])
        return None

    return np.frombuffer(r.content, dtype=np.uint8)


def detect_ship_targets(image_bytes):
    if image_bytes is None:
        return {
            "targets": 0,
            "confidence": "منخفضة",
            "note": "تعذر تحميل صورة SAR",
        }

    img = cv2.imdecode(image_bytes, cv2.IMREAD_GRAYSCALE)

    if img is None:
        return {
            "targets": 0,
            "confidence": "منخفضة",
            "note": "تعذر قراءة صورة SAR",
        }

    # تحسين التباين
    img = cv2.equalizeHist(img)

    # تقليل الضوضاء
    blur = cv2.GaussianBlur(img, (3, 3), 0)

    # Threshold ذكي بدل الرقم الثابت
    mean = np.mean(blur)
    std = np.std(blur)
    threshold_value = min(255, max(180, mean + 2.8 * std))

    _, thresh = cv2.threshold(
        blur,
        threshold_value,
        255,
        cv2.THRESH_BINARY
    )

    # تنظيف الضوضاء الصغيرة
    kernel = np.ones((2, 2), np.uint8)
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(
        clean,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    valid_targets = []

    for c in contours:
        area = cv2.contourArea(c)

        if area < 4:
            continue

        if area > 250:
            continue

        x, y, w, h = cv2.boundingRect(c)
        ratio = max(w, h) / max(1, min(w, h))

        if ratio > 8:
            continue

        valid_targets.append(c)

    count = len(valid_targets)

    if count >= 20:
        confidence = "متوسطة"
        note = "تم رصد عدد مرتفع من الأهداف اللامعة المحتملة."
    elif count >= 5:
        confidence = "منخفضة إلى متوسطة"
        note = "تم رصد أهداف بحرية محتملة، مع احتمال وجود ضوضاء SAR."
    elif count > 0:
        confidence = "منخفضة"
        note = "تم رصد أهداف محدودة تحتاج تحقق."
    else:
        confidence = "منخفضة"
        note = "لم يتم رصد أهداف واضحة."

    return {
        "targets": count,
        "confidence": confidence,
        "note": note,
    }


def build_sentinel_report():
    image = get_sar_image()
    detection = detect_ship_targets(image)

    lines = []
    lines.append("🛰️ تقرير Sentinel SAR — كشف السفن في البحر الأحمر")
    lines.append("════════════════════")
    lines.append(f"🚢 أهداف بحرية محتملة: {detection['targets']}")
    lines.append(f"📊 ثقة الكشف: {detection['confidence']}")
    lines.append("════════════════════")
    lines.append("🧾 التفسير:")
    lines.append(detection["note"])
    lines.append("ملاحظة: هذا كشف مجاني محسّن باستخدام معالجة صورة SAR محليًا، وليس نموذج AI مدفوع.")

    return "\n".join(lines)
