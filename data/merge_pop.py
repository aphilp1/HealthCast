"""Join Census Vintage 2023 county population estimates onto TIGERweb county boundaries.

Inputs (same folder):
  co-est2023-alldata.csv   - Census Population Estimates Program, Vintage 2023
  counties_5m_raw.geojson  - TIGERweb Generalized_ACS2023 Counties 5M

Outputs:
  counties.geojson  - boundaries with POP2023/CTYNAME/STNAME merged into properties
  county_pop.json   - compact {GEOID: [name, state, pop2023]} lookup for SAME-code sums
"""
import csv, json

pop = {}
with open("co-est2023-alldata.csv", encoding="latin-1") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] != "050":
            continue
        geoid = row["STATE"].zfill(2) + row["COUNTY"].zfill(3)
        pop[geoid] = (row["CTYNAME"], row["STNAME"], int(row["POPESTIMATE2023"]))

print(f"CSV counties: {len(pop)}")

with open("counties_5m_raw.geojson", encoding="utf-8") as f:
    gj = json.load(f)

matched = unmatched = 0
un_list = []
for feat in gj["features"]:
    geoid = feat["properties"]["GEOID"]
    if geoid in pop:
        name, state, p = pop[geoid]
        feat["properties"] = {"GEOID": geoid, "NAME": name, "STATE": state, "POP2023": p}
        matched += 1
    else:
        feat["properties"] = {"GEOID": geoid, "NAME": feat["properties"].get("BASENAME", "?"),
                              "STATE": "?", "POP2023": None}
        unmatched += 1
        un_list.append((geoid, feat["properties"]["NAME"]))

print(f"Geometry features: {len(gj['features'])}, matched: {matched}, unmatched: {unmatched}")
for g, n in un_list[:20]:
    print("  UNMATCHED:", g, n)

with open("counties.geojson", "w", encoding="utf-8") as f:
    json.dump(gj, f, separators=(",", ":"))

lookup = {g: [v[0], v[1], v[2]] for g, v in pop.items()}
with open("county_pop.json", "w", encoding="utf-8") as f:
    json.dump(lookup, f, separators=(",", ":"))

total = sum(v[2] for v in pop.values())
print(f"US total from county sum: {total:,}")
