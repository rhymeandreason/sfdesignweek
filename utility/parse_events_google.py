import json
import sys
import urllib.parse
from datetime import datetime, timedelta

from geopy.exc import GeocoderQueryError, GeocoderTimedOut
from geopy.geocoders import GoogleV3

# ==========================================
# 🔑 PUT YOUR GOOGLE MAPS API KEY HERE
# ==========================================
GOOGLE_API_KEY = "AIzaSyCv89jgro-2OmWax1v4I52-Pw2nDN6Fbj8"


def parse_ics(file_path):
    events = []
    current_event = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("BEGIN:VEVENT"):
                current_event = {}
            elif line.startswith("END:VEVENT"):
                if current_event:
                    events.append(current_event)
            elif ":" in line:
                parts = line.split(":", 1)
                key, val = parts[0].strip(), parts[1].strip()

                if key in ["DESCRIPTION", "SUMMARY", "LOCATION"]:
                    current_event[key] = val.replace("\\,", ",")
                elif key in ["DTSTART", "DTEND", "URL"]:
                    current_event[key] = val
    return events


def categorize(summary, desc):
    text = (summary + " " + desc).lower()
    if "workshop" in text:
        return "workshop", "Workshop"
    if "artist talk" in text:
        return "artist talk", "Artist Talk"
    if "panel" in text:
        return "panel", "Panel"
    if "open studio" in text or "studio crawl" in text:
        return "open studio", "Open Studio"
    if "open house" in text:
        return "open house", "Open House"
    if "immersive" in text:
        return "immersive", "Immersive"
    if "exhibition" in text or "showcase" in text or "gallery" in text:
        return "exhibition", "Exhibition"
    if "talk" in text or "conversation" in text or "lecture" in text:
        return "talk", "Talk"
    return "social", "Social"


def get_coordinates(address, geolocator, cache):
    if not address or address == "CA":
        return 37.7749, -122.4194

    if address in cache:
        return cache[address]

    try:
        location = geolocator.geocode(address, timeout=10)

        if location:
            cache[address] = (location.latitude, location.longitude)
            print(
                f"✅ Mapped: {address} \n   -> {location.latitude}, {location.longitude}"
            )
            return cache[address]

    except (GeocoderTimedOut, GeocoderQueryError) as e:
        print(f"⚠️ Error mapping {address}: {e}")

    print(f"❌ FAILED to map: {address}")
    cache[address] = (37.7749, -122.4194)
    return cache[address]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 parse_events.py <path_to_ics_file>")
        sys.exit(1)

    if GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print(
            "❌ ERROR: You need to paste your Google API key into the GOOGLE_API_KEY variable at the top of the script."
        )
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"Reading events from: {file_path}")
    events = parse_ics(file_path)

    filtered_events = []
    event_id = 1

    geolocator = GoogleV3(api_key=GOOGLE_API_KEY)
    coord_cache = {}

    print("Parsing events and fetching coordinates via Google Maps...")

    for evt in events:
        if "DTSTART" not in evt:
            continue

        try:
            dtstart_utc = datetime.strptime(evt["DTSTART"], "%Y%m%dT%H%M%SZ")
            dtend_utc = (
                datetime.strptime(evt["DTEND"], "%Y%m%dT%H%M%SZ")
                if "DTEND" in evt
                else dtstart_utc
            )
        except ValueError:
            continue

        dtstart_pdt = dtstart_utc - timedelta(hours=7)
        dtend_pdt = dtend_utc - timedelta(hours=7)

        if datetime(2026, 6, 5) <= dtstart_pdt <= datetime(2026, 6, 12, 23, 59, 59):
            cat_type, cat_tag = categorize(
                evt.get("SUMMARY", ""), evt.get("DESCRIPTION", "")
            )

            raw_address = evt.get("LOCATION", "")
            venue_name = raw_address.split(",")[0].strip() if raw_address else "TBD"

            lat, lng = get_coordinates(raw_address, geolocator, coord_cache)

            # Generate the Google Maps Link using the exact coordinates
            gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

            filtered_events.append(
                {
                    "id": event_id,
                    "date": dtstart_pdt.strftime("%Y-%m-%d"),
                    "start": dtstart_pdt.strftime("%H:%M"),
                    "end": dtend_pdt.strftime("%H:%M"),
                    "name": evt.get("SUMMARY", ""),
                    "venue": venue_name,
                    "address": raw_address,
                    "lat": lat,
                    "lng": lng,
                    "type": cat_type,
                    "tag": cat_tag,
                    "desc": evt.get("DESCRIPTION", ""),
                    "url": evt.get("URL", ""),
                    "gmaps_link": gmaps_url,
                }
            )
            event_id += 1

    with open("sfdw_events_mapped.json", "w", encoding="utf-8") as f:
        json.dump(filtered_events, f, indent=4)

    print(
        f"\n🎉 Successfully exported {len(filtered_events)} mapped events to sfdw_events_mapped.json"
    )


if __name__ == "__main__":
    main()
