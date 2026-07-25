"""Build compact block-group centroid population file for census.html.

Inputs (same folder):
  CenPop2020_Mean_BG.txt   - Census 2020 population-weighted block-group centroids (national, incl. PR)
  co-est2023-alldata.csv   - Vintage 2023 county estimates (for 2020->2023 county scale factors)
  counties_5m_raw.geojson  - for PR municipio names

Outputs:
  bg_centroids.json - {"fips":[county GEOIDs], "lat":[], "lon":[], "pop":[]} parallel arrays
  county_pop.json   - updated: PR municipios added (2020 Census totals, flagged)
"""
import csv, json

# County scale factors: 2023 estimate / 2020 base
scale = {}
with open("co-est2023-alldata.csv", encoding="latin-1") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] != "050":
            continue
        geoid = row["STATE"].zfill(2) + row["COUNTY"].zfill(3)
        base = int(row["ESTIMATESBASE2020"])
        est = int(row["POPESTIMATE2023"])
        scale[geoid] = est / base if base > 0 else 1.0

fips, lat, lon, pop = [], [], [], []
pr_county_totals = {}
total_raw = total_scaled = 0
with open("CenPop2020_Mean_BG.txt", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        cfips = row["STATEFP"] + row["COUNTYFP"]
        p = int(row["POPULATION"])
        total_raw += p
        sp = int(round(p * scale.get(cfips, 1.0)))
        total_scaled += sp
        if p == 0:
            continue
        fips.append(cfips)
        lat.append(round(float(row["LATITUDE"]), 4))
        lon.append(round(float(row["LONGITUDE"]), 4))
        pop.append(sp)
        if row["STATEFP"] == "72":
            pr_county_totals[cfips] = pr_county_totals.get(cfips, 0) + p

print(f"Block groups kept: {len(fips)} (nonzero pop), raw 2020 total {total_raw:,}, scaled-to-2023 total {total_scaled:,}")

with open("bg_centroids.json", "w") as f:
    json.dump({"fips": fips, "lat": lat, "lon": lon, "pop": pop}, f, separators=(",", ":"))

# Add PR municipios to county_pop.json using 2020 Census sums (no 2023 estimates exist)
with open("counties_5m_raw.geojson", encoding="utf-8") as f:
    names = {ft["properties"]["GEOID"]: ft["properties"].get("BASENAME", "?")
             for ft in json.load(f)["features"]}
with open("county_pop.json", encoding="utf-8") as f:
    cp = json.load(f)
added = 0
for g, p in sorted(pr_county_totals.items()):
    if g not in cp:
        cp[g] = [names.get(g, "?") + " Municipio", "Puerto Rico (2020 Census)", p]
        added += 1
with open("county_pop.json", "w", encoding="utf-8") as f:
    json.dump(cp, f, separators=(",", ":"))
print(f"PR municipios added to county_pop.json: {added}, PR total {sum(pr_county_totals.values()):,}")
