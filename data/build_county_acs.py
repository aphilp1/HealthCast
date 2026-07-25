"""Pull county-level ACS 2023 5-year demographics for ALL counties (incl. PR) -> county_acs.json

Variables:
  acs/acs5:         B01003_001E total pop, B25024_010E mobile homes, B19013_001E median HH income
  acs/acs5/subject: S0101_C01_030E age 65+, S0101_C01_002E under 5
  acs/acs5/profile: DP03_0128PE % below poverty

Output: county_acs.json {GEOID: {"pop":n,"age65":n,"under5":n,"mobile":n,"income":n,"pov_pct":x}}
"""
import json, os, urllib.request

key = None
with open(os.path.join(os.path.dirname(__file__), "..", ".env")) as f:
    for line in f:
        if line.startswith("CENSUS_API_KEY="):
            key = line.strip().split("=", 1)[1]
assert key, "no CENSUS_API_KEY in .env"

def pull(dataset, variables):
    url = (f"https://api.census.gov/data/2023/{dataset}?get={','.join(variables)}"
           f"&for=county:*&key={key}")
    with urllib.request.urlopen(url, timeout=120) as r:
        data = json.load(r)
    hdr, rows = data[0], data[1:]
    out = {}
    for row in rows:
        d = dict(zip(hdr, row))
        geoid = d["state"] + d["county"]
        out[geoid] = d
    print(f"{dataset}: {len(out)} counties")
    return out

def num(v, is_float=False):
    if v is None:
        return None
    x = float(v) if is_float else int(v)
    return None if x < 0 else x   # Census sentinel values are large negatives

base = pull("acs/acs5", ["B01003_001E", "B25024_010E", "B19013_001E", "B01002_001E"])
subj = pull("acs/acs5/subject", ["S0101_C01_030E", "S0101_C01_002E"])
prof = pull("acs/acs5/profile", ["DP03_0128PE", "DP04_0058PE",
    "DP02_0068PE",   # % bachelor's degree or higher
    "DP03_0009PE",   # unemployment rate
    "DP04_0047PE",   # % renter-occupied
    "DP03_0096PE",   # % with health insurance
    "DP02_0114PE",   # % language other than English at home
    "DP05_0076PE",   # % Hispanic or Latino
    "DP05_0037PE",   # % White alone
    "DP05_0038PE",   # % Black alone
    "DP05_0047PE",   # % Asian alone
])

acs = {}
for geoid, d in base.items():
    s, p = subj.get(geoid, {}), prof.get(geoid, {})
    acs[geoid] = {
        "pop":     num(d.get("B01003_001E")),
        "mobile":  num(d.get("B25024_010E")),
        "income":  num(d.get("B19013_001E")),
        "medage":  num(d.get("B01002_001E"), True),
        "age65":   num(s.get("S0101_C01_030E")),
        "under5":  num(s.get("S0101_C01_002E")),
        "pov_pct": num(p.get("DP03_0128PE"), True),
        "noveh":   num(p.get("DP04_0058PE"), True),
        "edu":     num(p.get("DP02_0068PE"), True),
        "unemp":   num(p.get("DP03_0009PE"), True),
        "renter":  num(p.get("DP04_0047PE"), True),
        "insured": num(p.get("DP03_0096PE"), True),
        "lang":    num(p.get("DP02_0114PE"), True),
        "hisp":    num(p.get("DP05_0076PE"), True),
        "white":   num(p.get("DP05_0037PE"), True),
        "black":   num(p.get("DP05_0038PE"), True),
        "asian":   num(p.get("DP05_0047PE"), True),
    }

with open(os.path.join(os.path.dirname(__file__), "county_acs.json"), "w") as f:
    json.dump(acs, f, separators=(",", ":"))

n_pr = sum(1 for g in acs if g.startswith("72"))
tot65 = sum(v["age65"] or 0 for v in acs.values())
print(f"Wrote county_acs.json: {len(acs)} counties ({n_pr} PR), US+PR 65+ total {tot65:,}")
