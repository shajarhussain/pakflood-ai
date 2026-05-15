"""One-shot diagnostic — list ALL Pakistan flood events in EONET, full history."""
import json
import urllib.request

url = "https://eonet.gsfc.nasa.gov/api/v3/events?category=floods&status=all&limit=2000"
d = json.loads(urllib.request.urlopen(url, timeout=60).read())
events = d["events"]
print(f"total flood events: {len(events)}")

pak = []
for ev in events:
    for g in ev.get("geometry", []):
        c = g.get("coordinates") or []
        if len(c) >= 2 and 60.0 <= c[0] <= 78.0 and 22.0 <= c[1] <= 38.0:
            pak.append({"title": ev["title"], "date": g.get("date"), "coords": c, "id": ev.get("id")})

print(f"pakistan flood event-points: {len(pak)}")
for p in pak[:30]:
    title = p["title"][:55]
    print(f"  - {p['date'][:10]}  ({p['coords'][1]:.2f}, {p['coords'][0]:.2f})  {title}")
