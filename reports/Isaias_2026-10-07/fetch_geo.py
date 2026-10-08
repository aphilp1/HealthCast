"""Fetch sub-county geometry for the Isaias report from Census TIGERweb (keyless).
  tracts_cone.geojson   - ACS2023 tracts (500K generalized) intersecting the NHC forecast cone
  bg_alerts.geojson     - block groups (500K) in every county under a tropical alert
  blocks_warning.json   - 2020 census blocks (centroid + POP100/HU100, no polygons) in
                          Hurricane Warning / Storm Surge Warning counties
"""
import json, os, sys, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
T = "https://tigerweb.geo.census.gov/arcgis/rest/services"
TRACTS = T + "/Generalized_ACS2023/Tracts_Blocks/MapServer/4/query"
BGS = T + "/Generalized_ACS2023/Tracts_Blocks/MapServer/6/query"
BLOCKS = T + "/TIGERweb/tigerWMS_Census2020/MapServer/10/query"
TROP = ("Hurricane Warning", "Hurricane Watch", "Storm Surge Warning", "Storm Surge Watch",
        "Tropical Storm Warning", "Tropical Storm Watch", "Tropical Cyclone Local Statement")
WARN_TIER = ("Hurricane Warning", "Storm Surge Warning")


def post(url, params, tries=3):
    data = urllib.parse.urlencode(params).encode()
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=300) as r:
                j = json.loads(r.read())
            if "error" in j:
                raise RuntimeError(j["error"])
            return j
        except Exception as e:
            print("  retry", k + 1, e, file=sys.stderr); time.sleep(3)
    raise RuntimeError("gave up: " + url)


def to_geojson(f):
    """Esri JSON feature -> GeoJSON Feature (rings kept as one Polygon; Leaflet fills even-odd)."""
    g = f.get("geometry") or {}
    return {"type": "Feature", "properties": f["attributes"],
            "geometry": {"type": "Polygon", "coordinates": g.get("rings", [])} if g.get("rings") else None}

def fetch_all(url, where, geometry=None, out_fields="*", geojson=True, precision=5, extra=None):
    """Page through a layer query (resultOffset) and return features (GeoJSON when geojson=True)."""
    feats, offset = [], 0
    while True:
        p = {"where": where, "outFields": out_fields, "outSR": 4326, "resultOffset": offset,
             "resultRecordCount": 5000, "geometryPrecision": precision,
             "f": "json", "returnGeometry": "true" if geojson else "false"}
        if geometry:
            p.update({"geometry": json.dumps(geometry), "geometryType": "esriGeometryPolygon",
                      "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"})
        if extra:
            p.update(extra)
        j = post(url, p)
        batch = j.get("features", [])
        feats += [to_geojson(f) for f in batch] if geojson else batch
        print(f"  {url.split('/')[-3]}/{url.split('/')[-2]} offset {offset}: +{len(batch)} (total {len(feats)})", file=sys.stderr)
        more = j.get("exceededTransferLimit") or (j.get("properties") or {}).get("exceededTransferLimit")
        if len(batch) < 5000 and not more:
            break
        offset += len(batch)
        if not batch:
            break
    return feats


# --- county lists from the NWS alert snapshot ------------------------------
alerts = json.load(open(os.path.join(D, "alerts_active.json")))["features"]
real_counties = set(json.load(open(os.path.join(HERE, "..", "..", "data", "county_pop.json"))))
def counties_for(events):
    s = set()
    for a in alerts:
        if a["properties"]["event"] not in events:
            continue
        for c in (a["properties"].get("geocode") or {}).get("SAME", []):
            f = c[1:] if len(c) == 6 else c
            if f in real_counties: s.add(f)
    return sorted(s)
alert_counties = counties_for(TROP)
warn_counties = counties_for(WARN_TIER)
print("alert counties:", len(alert_counties), "warning-tier counties:", len(warn_counties), file=sys.stderr)
json.dump({"alert_counties": alert_counties, "warning_counties": warn_counties},
          open(os.path.join(D, "county_lists.json"), "w"))

def by_state(fips_list):
    out = {}
    for f in fips_list:
        out.setdefault(f[:2], []).append(f[2:])
    return out

# --- 1. tracts in every county touching the cone or under a tropical alert ----
# (TIGERweb rejects polygon-filtered geometry queries on this layer; a county
#  WHERE clause works, and the cone fraction is computed per tract in build_report.)
from shapely.geometry import shape
from shapely import prepare
cone = shape(json.load(open(os.path.join(D, "nhc_86.geojson")))["features"][0]["geometry"]); prepare(cone)
counties_gj = json.load(open(os.path.join(HERE, "..", "..", "data", "counties.geojson")))
cone_counties = sorted(f["properties"]["GEOID"] for f in counties_gj["features"] if cone.intersects(shape(f["geometry"])))
tract_counties = sorted(set(cone_counties) | set(alert_counties))
json.dump({"alert_counties": alert_counties, "warning_counties": warn_counties, "cone_counties": cone_counties,
           "tract_counties": tract_counties}, open(os.path.join(D, "county_lists.json"), "w"))
print("cone counties:", len(cone_counties), "tract counties:", len(tract_counties), file=sys.stderr)
tr = []
for st, cos in by_state(tract_counties).items():
    where = f"STATE='{st}' AND COUNTY IN ({','.join(repr(c) for c in cos)})"
    tr += fetch_all(TRACTS, where, out_fields="*")
if tr: print("tract attrs:", list(tr[0]["properties"].keys()), file=sys.stderr)
json.dump({"type": "FeatureCollection", "features": tr}, open(os.path.join(D, "tracts_cone.geojson"), "w"), separators=(",", ":"))
print("tracts_cone:", len(tr), file=sys.stderr)

# --- 2. block groups in alerted counties ----------------------------------
print("block groups in alert counties…", file=sys.stderr)
bgf = []
for st, cos in by_state(alert_counties).items():
    where = f"STATE='{st}' AND COUNTY IN ({','.join(repr(c) for c in cos)})"
    bgf += fetch_all(BGS, where, out_fields="*")
json.dump({"type": "FeatureCollection", "features": bgf}, open(os.path.join(D, "bg_alerts.geojson"), "w"), separators=(",", ":"))
print("bg_alerts:", len(bgf), file=sys.stderr)

# --- 3. 2020 blocks (points only) in warning-tier counties ----------------
if os.path.exists(os.path.join(D, "blocks_warning.json")):
    print("blocks already downloaded — skipping", file=sys.stderr); sys.exit(0)
print("2020 blocks in warning counties…", file=sys.stderr)
blk = []
for st, cos in by_state(warn_counties).items():
    where = f"STATE='{st}' AND COUNTY IN ({','.join(repr(c) for c in cos)})"
    blk += fetch_all(BLOCKS, where, geojson=False, out_fields="GEOID,CENTLAT,CENTLON,POP100,HU100,AREALAND")
rows = []
if blk: print("block attrs:", list(blk[0]["attributes"].keys()), file=sys.stderr)
for f in blk:
    a = f["attributes"]
    if (a.get("POP100") or 0) > 0:
        rows.append([a["GEOID"], round(float(a["CENTLAT"]), 5), round(float(a["CENTLON"]), 5), int(a["POP100"]), int(a.get("HU100") or 0)])
json.dump({"fields": ["GEOID", "lat", "lon", "pop", "hu"], "rows": rows}, open(os.path.join(D, "blocks_warning.json"), "w"), separators=(",", ":"))
print("blocks_warning:", len(blk), "total,", len(rows), "populated, pop sum", sum(r[3] for r in rows), file=sys.stderr)
