import os
import json
import websocket


def get_ais_data(limit=50):
    api_key = os.getenv("AISSTREAM_API_KEY")

    if not api_key:
        raise ValueError("AISSTREAM_API_KEY not found")

    url = "wss://stream.aisstream.io/v0/stream"

    vessels = []

    def on_message(ws, message):
        data = json.loads(message)

        if "Message" not in data:
            return

        msg = data["Message"]

        if "PositionReport" in msg:
            pos = msg["PositionReport"]

            vessel = {
                "mmsi": pos.get("UserID"),
                "lat": pos.get("Latitude"),
                "lon": pos.get("Longitude"),
                "sog": pos.get("Sog"),
            }

            vessels.append(vessel)

        if len(vessels) >= limit:
            ws.close()

    def on_open(ws):
        sub_msg = {
            "APIKey": api_key,
            "BoundingBoxes": [[[12, 34], [31, 57]]]  # البحر الأحمر + الخليج
        }
        ws.send(json.dumps(sub_msg))

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
    )

    ws.run_forever()

    return vessels
