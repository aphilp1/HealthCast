"""Tract-level demographics -> tract_demo.json (finer grain for inside-polygon demographics).

Per state (50+DC+PR), two ACS 2023 5-year tract queries:
  acs/acs5:         B01003_001E pop, B25024_010E mobile homes, B17001_002E below poverty (count)
  acs/acs5/subject: S0101_C01_030E age 65+, S0101_C01_002E under 5
Joined to CenPop2020_Mean_TR.txt tract population-weighted centroids (2020 boundaries = ACS 2023 tracts).

Output parallel arrays: {"fips":[county5],"lat":[],"lon":[],"pop":[],"a65":[],"u5":[],"mob":[],"povn":[]}
"""
import csv, json, os, urllib.request

here = os.path.dirname(os.path.abspath(__file__))
key = None
with open(os.path.join(here, "..", ".env")) as f:
    for line in f:
        if line.startswith("CENSUS_API_KEY="):
            key = line.strip().split("=", 1)[1]
assert key

cent = {}
with open(os.path.join(here, "CenPop2020_Mean_TR.txt"), encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        geoid = row["STATEFP"] + row["COUNTYFP"] + row["TRACTCE"]
        cent[geoid] = (round(float(row["LATITUDE"]), 4), round(float(row["LONGITUDE"]), 4))
states = sorted({g[:2] for g in cent})
print(f"tract centroids: {len(cent)}, states: {len(states)}")

# CDC PLACES 2025 tract prevalence -> estimated adult counts per tract
places = {}
with open(os.path.join(here, "places_tract_2025.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try:
            adults = int(row["totalpop18plus"])
        except (ValueError, KeyError):
            continue
        def cnt(col):
            try:
                return int(round(adults * float(row[col]) / 100))
            except (ValueError, KeyError):
                return 0
        places[row["tractfips"].zfill(11)] = (
            cnt("diabetes_crudeprev"), cnt("copd_crudeprev"),
            cnt("chd_crudeprev"), cnt("bphigh_crudeprev"))
print(f"PLACES tracts joined-ready: {len(places)}")

def pull(dataset, variables, state):
    url = (f"https://api.census.gov/data/2023/{dataset}?get={','.join(variables)}"
           f"&for=tract:*&in=state:{state}&key={key}")
    with urllib.request.urlopen(url, timeout=180) as r:
        data = json.load(r)
    hdr, rows = data[0], data[1:]
    out = {}
    for row in rows:
        d = dict(zip(hdr, row))
        out[d["state"] + d["county"] + d["tract"]] = d
    return out

def num(v):
    if v is None: return 0
    x = int(v)
    return 0 if x < 0 else x

fips, lat, lon, pop, a65, u5, mob, povn = [], [], [], [], [], [], [], []
diabn, copdn, chdn, bphighn = [], [], [], []
missing_cent = 0
for st in states:
    base = pull("acs/acs5", ["B01003_001E", "B25024_010E", "B17001_002E"], st)
    subj = pull("acs/acs5/subject", ["S0101_C01_030E", "S0101_C01_002E"], st)
    n = 0
    for geoid, d in base.items():
        p = num(d.get("B01003_001E"))
        if p == 0: continue
        c = cent.get(geoid)
        if not c:
            missing_cent += 1
            continue
        s = subj.get(geoid, {})
        fips.append(geoid[:5]); lat.append(c[0]); lon.append(c[1]); pop.append(p)
        a65.append(num(s.get("S0101_C01_030E"))); u5.append(num(s.get("S0101_C01_002E")))
        mob.append(num(d.get("B25024_010E"))); povn.append(num(d.get("B17001_002E")))
        h = places.get(geoid, (0, 0, 0, 0))
        diabn.append(h[0]); copdn.append(h[1]); chdn.append(h[2]); bphighn.append(h[3])
        n += 1
    print(f"  state {st}: {n} tracts")

with open(os.path.join(here, "tract_demo.json"), "w") as f:
    json.dump({"fips": fips, "lat": lat, "lon": lon, "pop": pop,
               "a65": a65, "u5": u5, "mob": mob, "povn": povn,
               "diabn": diabn, "copdn": copdn, "chdn": chdn, "bphighn": bphighn},
              f, separators=(",", ":"))
print(f"Wrote tract_demo.json: {len(fips)} tracts (no centroid: {missing_cent})")
print(f"totals: pop {sum(pop):,}, 65+ {sum(a65):,}, mobile {sum(mob):,}, poverty {sum(povn):,}")
print(f"health totals: diabetes {sum(diabn):,}, COPD {sum(copdn):,}, CHD {sum(chdn):,}, highBP {sum(bphighn):,}")
