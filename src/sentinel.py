from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import requests


CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


def utc_now():
    return datetime.now(timezone.utc)


def search_sentinel1_red_sea(days_back=3, limit=5):
    end = utc_now()
    start = end - timedelta(days=days_back)

    footprint = (
        "geography'SRID=4326;"
        "POLYGON((34 12, 43 12, 43 30, 34 30, 34 12))'"
    )

    start_s = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_s = end.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    filters = (
        "Collection/Name eq 'SENTINEL-1' "
        f"and ContentDate/Start gt {start_s} "
        f"and ContentDate/Start lt {end_s} "
        "and contains(Name,'GRD') "
        f"and OData.CSC.Intersects(area={footprint})"
    )

    # ✅ هنا الإصلاح: نفصل الترميز عن f-string
    encoded_filters = quote(filters, safe="()'=, /:.")

    url = (
        CATALOGUE_URL
        + "?$filter=" + encoded_filters
        + "&$orderby=ContentDate/Start desc"
        + f"&$top={limit}"
        + "&$select=Id,Name,ContentDate,Online,S3Path"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    return response.json().get("value", [])


def build_sentinel_report(products):
    lines = []
    lines.append("🛰️ تقرير Sentinel-1 SAR — البحر الأحمر")
    lines.append("════════════════════")

    if not products:
        lines.append("لا توجد مشاهد Sentinel-1 متاحة خلال الفترة المحددة.")
        return "\n".join(lines)

    lines.append(f"عدد المشاهد المتاحة: {len(products)}")
    lines.append("════════════════════")

    for i, p in enumerate(products, 1):
        name = p.get("Name", "غير متاح")
        online = p.get("Online", "غير متاح")
        content_date = p.get("ContentDate", {})
        start = content_date.get("Start", "غير متاح")

        lines.append(f"{i}) {name}")
        lines.append(f"   🕒 وقت المشهد: {start}")
        lines.append(f"   📦 Online: {online}")

    lines.append("════════════════════")
    lines.append("🧾 التفسير:")
    lines.append("هذه مشاهد SAR حديثة للبحر الأحمر (ليست كشف سفن مباشر بعد).")

    return "\n".join(lines)
