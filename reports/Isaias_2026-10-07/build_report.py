"""Assemble the Isaias alert report data from the snapshot in data/.

Exposure method (same as the HealthCast app, but at finer grain):
  * every NWS alert with a polygon -> 2020 block-group population centroids inside it
  * zone-based alerts (no polygon) -> every block group in the alert's counties
  * each block group gets the most severe tropical alert tier covering it
  * demographics / health = ACS 2023 tract shares x CDC PLACES 2025 tract prevalence,
    applied to the block-group people in each tract that fall in the slice

Outputs (read by index.html):
  report_data.json   headline numbers, tiers, forecast table, county table, top-tract lists
  tracts.geojson     tracts touching the cone or any tropical alert, with all attributes
  bgs.geojson        block groups in alerted counties: population, density, tier, cone, 64-kt
  blocks.json        2020 census block points in Hurricane/Storm-Surge Warning counties
  wind_swaths.geojson union of NHC forecast wind radii at 34 / 50 / 64 kt
"""
import csv, json, os, sys, datetime
from collections import defaultdict
import numpy as np
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import contains_xy, prepare

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
ROOT = os.path.join(HERE, "..", "..", "data")
J = lambda *p: json.load(open(os.path.join(*p), encoding="utf-8"))
def dump(obj, name):
    json.dump(obj, open(os.path.join(HERE, name), "w", encoding="utf-8"), separators=(",", ":"))
    print(f"wrote {name} ({os.path.getsize(os.path.join(HERE, name))/1e6:.1f} MB)", file=sys.stderr)

TIERS = ["Hurricane Warning", "Storm Surge Warning", "Hurricane Watch", "Tropical Storm Warning",
         "Storm Surge Watch", "Tropical Storm Watch", "Tropical Cyclone Local Statement"]
TIER_SHORT = ["HW", "SSW", "HWa", "TSW", "SSWa", "TSWa", "TCLS"]

# ---------------------------------------------------------------- inputs
alerts = J(D, "alerts_active.json")["features"]
cone_f = J(D, "nhc_86.geojson")["features"][0]
cone = shape(cone_f["geometry"]); prepare(cone)
points = J(D, "nhc_84.geojson")["features"]
radii = J(D, "nhc_94.geojson")["features"]
county_pop = J(ROOT, "county_pop.json")        # fips -> [name, state, pop]
county_acs = J(ROOT, "county_acs.json")
county_health = J(ROOT, "county_health.json")
acs_tr = J(D, "acs_tracts.json")
tracts_fc = J(D, "tracts_cone.geojson")
bgs_fc = J(D, "bg_alerts.geojson")
blocks = J(D, "blocks_warning.json")["rows"]

places = {}
with open(os.path.join(ROOT, "places_tract_2025.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        def fl(k):
            try: return float(r[k])
            except (ValueError, TypeError): return None
        places[r["tractfips"].zfill(11)] = {"adults": fl("totalpop18plus") or 0, "diab": fl("diabetes_crudeprev"),
                                            "copd": fl("copd_crudeprev"), "chd": fl("chd_crudeprev"), "bp": fl("bphigh_crudeprev")}

# 2020 block-group centroids with full GEOID, scaled to county 2023 estimates (app method)
scale = {}
with open(os.path.join(ROOT, "co-est2023-alldata.csv"), encoding="latin-1") as f:
    for r in csv.DictReader(f):
        if r["COUNTY"] == "000": continue
        g = r["STATE"].zfill(2) + r["COUNTY"].zfill(3)
        base, est = float(r["ESTIMATESBASE2020"] or 0), float(r["POPESTIMATE2023"] or 0)
        scale[g] = est / base if base > 0 else 1.0
bg_g, lat, lon, pop = [], [], [], []
with open(os.path.join(ROOT, "CenPop2020_Mean_BG.txt"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        p = int(r["POPULATION"])
        if p <= 0: continue
        c = r["STATEFP"] + r["COUNTYFP"]
        bg_g.append(c + r["TRACTCE"] + r["BLKGRPCE"]); lat.append(float(r["LATITUDE"])); lon.append(float(r["LONGITUDE"]))
        pop.append(int(round(p * scale.get(c, 1.0))))
bg_g = np.array(bg_g); lat = np.array(lat); lon = np.array(lon); pop = np.array(pop)
bg_county = np.array([g[:5] for g in bg_g]); bg_tract = np.array([g[:11] for g in bg_g])
N = len(bg_g)
print("block groups:", N, "pop", int(pop.sum()), file=sys.stderr)
county_idx = defaultdict(list)
for i, c in enumerate(bg_county): county_idx[c].append(i)

# ---------------------------------------------------------------- per-BG alert tier (polygon-exact where NWS gives one)
bg_tier = np.full(N, 99, dtype=np.int16)
alert_masks = []     # (tier, event, mask) for every tropical alert
for a in alerts:
    ev = a["properties"]["event"]
    if ev not in TIERS: continue
    t = TIERS.index(ev)
    m = np.zeros(N, dtype=bool)
    if a["geometry"]:
        try:
            g = shape(a["geometry"]).buffer(0); prepare(g)
            bb = g.bounds
            cand = (lon >= bb[0]) & (lon <= bb[2]) & (lat >= bb[1]) & (lat <= bb[3])
            idx = np.nonzero(cand)[0]
            if len(idx): m[idx] = contains_xy(g, lon[idx], lat[idx])
        except Exception as e:
            print("bad geometry", ev, e, file=sys.stderr)
    else:
        for c in (a["properties"].get("geocode") or {}).get("SAME", []):
            fips = c[1:] if len(c) == 6 else c
            for i in county_idx.get(fips, []): m[i] = True
    alert_masks.append((t, ev, m))
    bg_tier[m & (bg_tier > t)] = t
tier_counts = {TIERS[t]: int(pop[bg_tier == t].sum()) for t in range(len(TIERS))}
print("people by best tier:", tier_counts, file=sys.stderr)

# ---------------------------------------------------------------- cone + wind swaths
in_cone = contains_xy(cone, lon, lat)
# NHC gives wind radii at 12-hour forecast points only. Sweeping each radii polygon to the
# next hour's polygon (or to the next forecast center once the radii end) gives the
# continuous swath the storm is forecast to trace — the same idea as NHC's cumulative
# wind swath graphic. Without this, a landfall between two forecast hours leaves a gap.
from shapely.geometry import Point, MultiPoint
pt_by_tau = {int(f["properties"].get("tau") or 0): Point(f["geometry"]["coordinates"]) for f in points}
taus = sorted(pt_by_tau)
swaths = {}
for kt in (64, 50, 34):
    by_tau = {}
    for f in radii:
        if int(float(f["properties"]["radii"])) == kt:
            by_tau[int(f["properties"].get("tau") or 0)] = shape(f["geometry"]).buffer(0)
    if not by_tau: continue
    pieces = list(by_tau.values())
    for t in sorted(by_tau):
        nxt = [x for x in taus if x > t]
        if not nxt: continue
        t2 = nxt[0]
        target = by_tau.get(t2) or pt_by_tau.get(t2)
        if target is not None:
            pieces.append(unary_union([by_tau[t], target]).convex_hull)
    u = unary_union(pieces).buffer(0); prepare(u); swaths[kt] = u
    print(f"swath {kt} kt: {len(by_tau)} radii polygons, bounds {[round(b,2) for b in u.bounds]}", file=sys.stderr)
sw_mask = {kt: contains_xy(u, lon, lat) for kt, u in swaths.items()}
dump({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"kt": kt}, "geometry": mapping(u.simplify(0.003))} for kt, u in swaths.items()]},
    "wind_swaths.geojson")

# ---------------------------------------------------------------- slice = people + demographics for any BG mask
tract_bgpop = defaultdict(int)
for i in range(N): tract_bgpop[bg_tract[i]] += int(pop[i])

def slice_of(mask):
    """Population + demographics + health for the block groups in `mask` (tract shares)."""
    s = dict(people=0, a65=0.0, u5=0.0, mob=0.0, povn=0.0, povu=0.0, novh=0.0, hh=0.0,
             adults=0.0, diab=0.0, copd=0.0, chd=0.0, bp=0.0)
    by_tract = defaultdict(int)
    for i in np.nonzero(mask)[0]:
        by_tract[bg_tract[i]] += int(pop[i])
    counties = set(); tracts_cov = 0
    for t, p in by_tract.items():
        s["people"] += p; counties.add(t[:5])
        tot = tract_bgpop.get(t, 0)
        a = acs_tr.get(t); pl = places.get(t)
        sh = min(1.0, p / tot) if tot else 0.0
        if a and a.get("pop"):
            tracts_cov += 1
            s["a65"] += a["a65"] * sh; s["u5"] += a["u5"] * sh; s["mob"] += a["mob"] * sh
            s["povn"] += a["povn"] * sh; s["povu"] += a["povu"] * sh; s["novh"] += a["novh"] * sh; s["hh"] += a["hh"] * sh
        else:   # fall back to county shares (outside the 8 states pulled)
            ca = county_acs.get(t[:5]) or {}
            if ca.get("pop"):
                csh = p / ca["pop"]
                s["a65"] += (ca.get("age65") or 0) * csh; s["u5"] += (ca.get("under5") or 0) * csh; s["mob"] += (ca.get("mobile") or 0) * csh
                if ca.get("pov_pct") is not None: s["povn"] += ca["pov_pct"] / 100 * p; s["povu"] += p
                if ca.get("noveh") is not None: s["novh"] += ca["noveh"] / 100 * p; s["hh"] += p
        if pl and pl["adults"]:
            ad = pl["adults"] * sh; s["adults"] += ad
            for k in ("diab", "copd", "chd", "bp"):
                if pl[k] is not None: s[k] += ad * pl[k] / 100
    P = s["people"] or 1; AD = s["adults"] or 1
    return {"people": int(s["people"]), "counties": len(counties), "tracts": len(by_tract),
            "a65": int(s["a65"]), "a65_pct": round(100 * s["a65"] / P, 1), "u5": int(s["u5"]),
            "mob": int(s["mob"]), "mob_per_1000": round(1000 * s["mob"] / P),
            "pov_pct": round(100 * s["povn"] / s["povu"], 1) if s["povu"] else None,
            "noveh_pct": round(100 * s["novh"] / s["hh"], 1) if s["hh"] else None,
            "adults": int(s["adults"]), "diab": int(s["diab"]), "diab_pct": round(100 * s["diab"] / AD, 1),
            "copd": int(s["copd"]), "copd_pct": round(100 * s["copd"] / AD, 1),
            "chd": int(s["chd"]), "chd_pct": round(100 * s["chd"] / AD, 1),
            "bp": int(s["bp"]), "bp_pct": round(100 * s["bp"] / AD, 1)}

tiers = []
for t, name in enumerate(TIERS):
    m = bg_tier == t
    if not m.any(): continue
    row = slice_of(m); row["tier"] = name; row["short"] = TIER_SHORT[t]
    row["cum_people"] = int(pop[bg_tier <= t].sum())
    tiers.append(row)
any_alert = slice_of(bg_tier < 99)
warn_tier = slice_of(bg_tier <= 1)
hw_only = slice_of(bg_tier == 0)
per_event = {ev: 0 for ev in TIERS}
for t, ev, m in alert_masks: per_event[ev] = per_event.get(ev, 0)
ev_union = defaultdict(lambda: np.zeros(N, dtype=bool))
for t, ev, m in alert_masks: ev_union[ev] |= m
per_event = {ev: {"alerts": sum(1 for x in alert_masks if x[1] == ev), "people": int(pop[m].sum())} for ev, m in ev_union.items()}
cone_slice = slice_of(in_cone)
wind_slices = {str(kt): slice_of(m) for kt, m in sw_mask.items()}
cone_warn = slice_of(in_cone & (bg_tier <= 1))

# national baseline from county files (continental + HI/AK, no PR)
def nat():
    P = a65 = u5 = mob = povw = novw = ad = diab = copd = chd = bp = 0.0
    for g, a in county_acs.items():
        if g.startswith("72") or not a.get("pop"): continue
        P += a["pop"]; a65 += a.get("age65") or 0; u5 += a.get("under5") or 0; mob += a.get("mobile") or 0
        if a.get("pov_pct") is not None: povw += a["pov_pct"] * a["pop"]
        if a.get("noveh") is not None: novw += a["noveh"] * a["pop"]
        h = county_health.get(g) or {}
        if h.get("adults"):
            ad += h["adults"]
            diab += h["adults"] * (h.get("diab") or 0) / 100; copd += h["adults"] * (h.get("copd") or 0) / 100
            chd += h["adults"] * (h.get("chd") or 0) / 100; bp += h["adults"] * (h.get("bphigh") or 0) / 100
    return {"people": int(P), "a65_pct": round(100 * a65 / P, 1), "mob_per_1000": round(1000 * mob / P), "pov_pct": round(povw / P, 1),
            "noveh_pct": round(novw / P, 1), "diab_pct": round(100 * diab / ad, 1), "copd_pct": round(100 * copd / ad, 1),
            "chd_pct": round(100 * chd / ad, 1), "bp_pct": round(100 * bp / ad, 1)}
national = nat()

# ---------------------------------------------------------------- per-tract / per-county exposure aggregates
tr_cone = defaultdict(int); tr_w64 = defaultdict(int); tr_tier = defaultdict(lambda: 99); tr_tierpop = defaultdict(lambda: defaultdict(int))
co_cone = defaultdict(int); co_w64 = defaultdict(int); co_tier = defaultdict(lambda: 99); co_tierpop = defaultdict(lambda: defaultdict(int))
for i in range(N):
    t, c, p = bg_tract[i], bg_county[i], int(pop[i])
    if in_cone[i]: tr_cone[t] += p; co_cone[c] += p
    if 64 in sw_mask and sw_mask[64][i]: tr_w64[t] += p; co_w64[c] += p
    if bg_tier[i] < 99:
        tr_tier[t] = min(tr_tier[t], int(bg_tier[i])); co_tier[c] = min(co_tier[c], int(bg_tier[i]))
        tr_tierpop[t][int(bg_tier[i])] += p; co_tierpop[c][int(bg_tier[i])] += p

# ---------------------------------------------------------------- tracts
tr_out, tract_rows = [], []
for f in tracts_fc["features"]:
    pr = f["properties"]; g = pr["GEOID"]
    a = acs_tr.get(g) or {}; pl = places.get(g) or {}
    P = a.get("pop") or 0
    area = (pr.get("AREALAND") or 0) / 1e6
    tot = tract_bgpop.get(g, 0)
    cone_frac = tr_cone.get(g, 0) / tot if tot else 0.0
    w64_frac = tr_w64.get(g, 0) / tot if tot else 0.0
    tier = tr_tier.get(g, 99)
    tier_frac = (tr_tierpop[g][tier] / tot) if (tot and tier < 99) else 0.0
    adults = pl.get("adults") or 0
    rec = county_pop.get(g[:5], ["?", "?", 0])
    props = {"g": g, "name": pr.get("NAME"), "co": g[:5], "coname": rec[0], "st": rec[1].replace(" (2020 Census)", ""),
             "tier": tier if tier < 99 else None, "tierFrac": round(tier_frac, 2),
             "pop": P, "dens": round(P / area, 1) if area else None,
             "a65": a.get("a65") or 0, "a65p": round(100 * (a.get("a65") or 0) / P, 1) if P else None,
             "u5": a.get("u5") or 0, "mob": a.get("mob") or 0, "mobp": round(1000 * (a.get("mob") or 0) / P) if P else None,
             "povp": round(100 * a["povn"] / a["povu"], 1) if a.get("povu") else None,
             "novp": round(100 * a["novh"] / a["hh"], 1) if a.get("hh") else None, "inc": a.get("inc"),
             "adults": int(adults), "diab": pl.get("diab"), "copd": pl.get("copd"), "chd": pl.get("chd"), "bp": pl.get("bp"),
             "diabn": int(adults * (pl.get("diab") or 0) / 100), "copdn": int(adults * (pl.get("copd") or 0) / 100),
             "chdn": int(adults * (pl.get("chd") or 0) / 100), "bpn": int(adults * (pl.get("bp") or 0) / 100),
             "cone": round(cone_frac, 2), "popCone": int(P * cone_frac), "w64": round(w64_frac, 2), "popW64": int(P * w64_frac)}
    tr_out.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
    tract_rows.append(props)
dump({"type": "FeatureCollection", "features": tr_out}, "tracts.geojson")

# ---------------------------------------------------------------- block groups
bgpop = dict(zip(bg_g.tolist(), pop.tolist())); bgt = dict(zip(bg_g.tolist(), bg_tier.tolist()))
bgc = dict(zip(bg_g.tolist(), in_cone.tolist())); bgw = dict(zip(bg_g.tolist(), sw_mask[64].tolist())) if 64 in sw_mask else {}
bg_out = []
for f in bgs_fc["features"]:
    pr = f["properties"]; g = pr["GEOID"]
    P = bgpop.get(g, 0); area = (pr.get("AREALAND") or 0) / 1e6
    t = bgt.get(g, 99)
    bg_out.append({"type": "Feature", "geometry": f["geometry"], "properties": {
        "g": g, "co": g[:5], "tier": t if t < 99 else None, "pop": P, "dens": round(P / area) if area else None,
        "cone": 1 if bgc.get(g) else 0, "w64": 1 if bgw.get(g) else 0}})
dump({"type": "FeatureCollection", "features": bg_out}, "bgs.geojson")

# ---------------------------------------------------------------- blocks (points)
bl_lat = np.array([r[1] for r in blocks]); bl_lon = np.array([r[2] for r in blocks]); bl_pop = np.array([r[3] for r in blocks])
bl_cone = contains_xy(cone, bl_lon, bl_lat)
bl_w64 = contains_xy(swaths[64], bl_lon, bl_lat) if 64 in swaths else np.zeros(len(blocks), bool)
# best tier per block = tier of the polygon alerts containing it (zone alerts: county)
bl_tier = np.full(len(blocks), 99, dtype=np.int16)
bl_county = np.array([r[0][:5] for r in blocks])
for a in alerts:
    ev = a["properties"]["event"]
    if ev not in TIERS: continue
    t = TIERS.index(ev)
    if a["geometry"]:
        g = shape(a["geometry"]).buffer(0); prepare(g); bb = g.bounds
        cand = (bl_lon >= bb[0]) & (bl_lon <= bb[2]) & (bl_lat >= bb[1]) & (bl_lat <= bb[3])
        idx = np.nonzero(cand)[0]
        if len(idx):
            hit = idx[contains_xy(g, bl_lon[idx], bl_lat[idx])]
            bl_tier[hit[bl_tier[hit] > t]] = t
    else:
        cos = {c[1:] if len(c) == 6 else c for c in (a["properties"].get("geocode") or {}).get("SAME", [])}
        m = np.isin(bl_county, list(cos)) & (bl_tier > t); bl_tier[m] = t
blocks_summary = {"n": len(blocks), "pop": int(bl_pop.sum()), "pop_cone": int(bl_pop[bl_cone].sum()),
                  "pop_w64": int(bl_pop[bl_w64].sum()), "pop_hw": int(bl_pop[bl_tier == 0].sum()),
                  "pop_ssw_or_hw": int(bl_pop[bl_tier <= 1].sum()), "counties": sorted(set(bl_county.tolist()))}
dump({**blocks_summary, "rows": [[r[1], r[2], r[3], int(bl_tier[i]) if bl_tier[i] < 99 else -1, int(bl_cone[i]), int(bl_w64[i])]
                                 for i, r in enumerate(blocks)]}, "blocks.json")

# ---------------------------------------------------------------- top lists + county table
def top(rows, key, n=12, where=lambda r: True):
    rs = [r for r in rows if where(r) and r.get(key) is not None]
    rs.sort(key=lambda r: -r[key])
    return [{k: r.get(k) for k in ("g", "name", "coname", "st", "tier", "pop", "a65", "mob", "copdn", "diabn", "povp", "novp", "dens", "popW64", "popCone", key)} for r in rs[:n]]
warn = lambda r: r["tier"] is not None and r["tier"] <= 1
top_lists = {
    "warn_a65": top(tract_rows, "a65", where=warn), "warn_mob": top(tract_rows, "mob", where=warn),
    "warn_copdn": top(tract_rows, "copdn", where=warn), "warn_diabn": top(tract_rows, "diabn", where=warn),
    "warn_povp": top(tract_rows, "povp", where=lambda r: warn(r) and r["pop"] >= 1500),
    "warn_novp": top(tract_rows, "novp", where=lambda r: warn(r) and r["pop"] >= 1500),
    "warn_dens": top(tract_rows, "dens", where=warn),
    "w64_pop": top(tract_rows, "popW64"), "cone_pop": top(tract_rows, "popCone"),
}
county_rows = []
for c, t in co_tier.items():
    rec = county_pop.get(c)
    if not rec: continue
    a = county_acs.get(c) or {}; h = county_health.get(c) or {}
    county_rows.append({"fips": c, "name": rec[0], "st": rec[1].replace(" (2020 Census)", ""), "tier": t, "tierName": TIERS[t],
                        "pop": rec[2], "popTier": int(co_tierpop[c][t]), "popAny": int(sum(co_tierpop[c].values())),
                        "popCone": co_cone.get(c, 0), "popW64": co_w64.get(c, 0),
                        "a65p": round(100 * a["age65"] / a["pop"], 1) if a.get("pop") and a.get("age65") else None,
                        "mobp": round(1000 * a["mobile"] / a["pop"]) if a.get("pop") and a.get("mobile") is not None else None,
                        "povp": a.get("pov_pct"), "novp": a.get("noveh"), "copd": h.get("copd"), "diab": h.get("diab")})
county_rows.sort(key=lambda r: (r["tier"], -r["popTier"]))

# forecast table
fc = []
for f in sorted(points, key=lambda f: (f["properties"].get("tau") or 0, f["properties"]["objectid"])):
    p = f["properties"]
    fc.append({k: p.get(k) for k in ("datelbl", "validtime", "fcsthr", "tau", "stormtype", "maxwind", "gust", "mslp", "ssnum", "dvlbl", "tcdvlp", "dateLbl")}
              | {"lat": round(f["geometry"]["coordinates"][1], 2), "lon": round(f["geometry"]["coordinates"][0], 2)})
cp = cone_f["properties"]
meta = {"storm": cp["stormname"], "type_now": cp["stormtype"], "advisory": cp["advisnum"], "advdate": cp["advdate"],
        "fcstprd": cp["fcstprd"], "alerts_snapshot_utc": "2026-10-08T04:22:59Z", "alerts_total": len(alerts),
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tract_count": len(tr_out), "bg_count": len(bg_out), "block_count": len(blocks), "wind_swaths": sorted(swaths)}
dump({"meta": meta, "forecast": fc, "tiers": tiers, "per_event": per_event, "any_alert": any_alert, "warn_tier": warn_tier,
      "hw_only": hw_only, "national": national, "cone": cone_slice, "cone_warn": cone_warn, "wind": wind_slices,
      "blocks": blocks_summary, "counties": county_rows, "top": top_lists, "tier_names": TIERS, "tier_short": TIER_SHORT},
     "report_data.json")
print("DONE", file=sys.stderr)
