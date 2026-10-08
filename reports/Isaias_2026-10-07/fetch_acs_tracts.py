"""Tract-level ACS 2023 5-year for the Isaias region states -> data/acs_tracts.json
Keyed by 11-digit tract GEOID. Variables:
  pop B01003_001E · mobile homes B25024_010E · poverty universe/below B17001_001E/_002E
  median income B19013_001E · households B25044_001E · no vehicle B25044_003E+B25044_010E
  age 65+ S0101_C01_030E · under 5 S0101_C01_002E · median age B01002_001E
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
env = os.path.join(HERE, "..", "..", ".env")
KEY = [l.split("=", 1)[1].strip() for l in open(env) if l.startswith("CENSUS_API_KEY=")][0]
STATES = ["01", "12", "22", "28", "47", "05", "21", "13"]   # AL FL LA MS TN AR KY GA
BASE = "https://api.census.gov/data/2023/acs/acs5"
DET = "B01003_001E,B25024_010E,B17001_001E,B17001_002E,B19013_001E,B25044_001E,B25044_003E,B25044_010E,B01002_001E"
SUB = "S0101_C01_030E,S0101_C01_002E"

def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        rows = json.loads(r.read())
    hdr = rows[0]
    return [dict(zip(hdr, r)) for r in rows[1:]]

def num(v):
    try:
        v = float(v)
        return None if v < -1e8 else v
    except (TypeError, ValueError):
        return None

out = {}
for st in STATES:
    det = get(f"{BASE}?get={DET}&for=tract:*&in=state:{st}&key={KEY}")
    sub = get(f"{BASE}/subject?get={SUB}&for=tract:*&in=state:{st}&key={KEY}")
    subm = {r["state"] + r["county"] + r["tract"]: r for r in sub}
    for r in det:
        g = r["state"] + r["county"] + r["tract"]
        s = subm.get(g, {})
        hh = num(r["B25044_001E"]) or 0
        nov = (num(r["B25044_003E"]) or 0) + (num(r["B25044_010E"]) or 0)
        out[g] = {"pop": int(num(r["B01003_001E"]) or 0), "mob": int(num(r["B25024_010E"]) or 0),
                  "povu": int(num(r["B17001_001E"]) or 0), "povn": int(num(r["B17001_002E"]) or 0),
                  "inc": num(r["B19013_001E"]), "hh": int(hh), "novh": int(nov),
                  "medage": num(r["B01002_001E"]),
                  "a65": int(num(s.get("S0101_C01_030E")) or 0), "u5": int(num(s.get("S0101_C01_002E")) or 0)}
    print(st, len(det), "tracts", file=sys.stderr)
json.dump(out, open(os.path.join(HERE, "data", "acs_tracts.json"), "w"), separators=(",", ":"))
print("acs_tracts:", len(out), "tracts, pop", sum(v["pop"] for v in out.values()), file=sys.stderr)
