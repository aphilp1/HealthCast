# PeopleWatch — Smoke/Heat × Chronic Disease Risk: Research Notes

**Date:** 2026-07-19 · **Status:** ⚠️ Sources gathered, claims extracted, **verification NOT completed**
(deep-research run hit the account monthly spend limit during the adversarial-verification phase:
28 sources fetched, 133 claims extracted, 25 sent to verify, **0 confirmed / 0 refuted / 25 unverified**).
Everything below is *extracted from primary sources but not independently fact-checked.*
**Do not put these numbers in the app until confirmed against the cited source.**

---

## 1. The core scientific caveat (read this first)

The thing we want to say — *"N adults with COPD face X% higher ER risk"* — is **not** what the
literature directly supports, and getting this wrong would be the project's biggest credibility risk.

- Published relative risks are almost always **outcome-level**, not **condition-stratified**:
  e.g. "respiratory ED visits rise ~4% per 10 µg/m³" across the whole population — NOT
  "people who have COPD have 4% higher risk than they otherwise would."
- Per one extracted claim from EPA's own framework, pre-existing cardiovascular disease and
  respiratory disease are rated only **"suggestive evidence"** of *increased susceptibility*,
  while "adequate evidence" exists only for lifestage (children) and race. Another extracted claim
  from the ISA chapters says EPA "formally identifies people with preexisting cardiovascular and
  respiratory diseases as a population at disproportionately increased risk." **These two are in
  tension — resolve by reading the ISA directly before building.**
- Wildfire-specific **cardiovascular** evidence is weak/inconclusive: CV ED visits RR 1.01
  (95% CI 0.98–1.04, crosses 1.0); the meta-analysis authors label CV associations "inconclusive."
  Respiratory is much stronger (below).

**Defensible phrasing** (recommended): frame the population as *who the excess visits come from*,
not as a personal risk multiplier —
> "Air quality here is Unhealthy (AQI 178). ~X adults in this area live with COPD and ~Y with asthma —
> the groups EPA identifies as at risk at this level. Studies associate each 10 µg/m³ of wildfire
> PM2.5 with about a 4% rise in respiratory ER visits. [source]"

---

## 2. Extracted quantitative claims (UNVERIFIED — confirm before use)

### Wildfire-specific PM2.5 — meta-analysis, Environmental Research 2025 (45 studies)
Source: https://www.sciencedirect.com/science/article/pii/S0013935125004724
- Respiratory **ED visits**: RR **1.04** (1.02–1.06) per 10 µg/m³ ← strongest usable number
- Respiratory **hospital admissions**: RR 1.04 (1.02–1.05) per 10 µg/m³
- **All-cause mortality**: RR 1.02 (1.01–1.03) per 10 µg/m³
- CV mortality RR 1.02 (1.01–1.03); CV admissions RR 1.01 (1.00–1.02); **CV ED visits RR 1.01 (0.98–1.04) = null**

### Wildfire PM2.5 → respiratory hospitalization (Nature Sustainability 2025)
Source: https://www.nature.com/articles/s41893-025-01533-9
- +0.36% respiratory hospitalization risk per **1** µg/m³ wildfire PM2.5 (≈ +3.6% per 10 µg/m³)
- NOTE: this was the ONE claim with a partial verify signal — 1 valid vote, and that vote leaned *refute*. Treat as suspect.

### Out-of-hospital cardiac arrest, CA wildfires 2015–17 (JAHA)
Source: https://www.ahajournals.org/doi/10.1161/JAHA.119.014125
- **Heavy** smoke density: OHCA odds ~+48–70% (peak OR 1.70 at lag day 2)
- Light/medium smoke: null or negative → **threshold-like response, not linear per-µg/m³**

### General (non-wildfire) short-term PM2.5, per 10 µg/m³
Source: EPA ISA chapters via NCBI — https://www.ncbi.nlm.nih.gov/books/NBK588512/
- CVD hospital admissions, Medicaid population: OR 1.09 (1.06–1.11)
- Heart failure: Medicare 30-day readmission HR 1.10 (1.03–1.19); Medicaid admissions OR 1.10 (1.04–1.16)
- AMI: Medicaid OR 1.1 (1.03–1.7)
- ESRD/hemodialysis patients, HF readmission: RR 1.37 (1.14–1.60)
- JACC 2018 review: short-term PM2.5 raises acute CV event risk **1–3%**; long-term ~10%

### EPA causality determinations (ISA)
Source: https://www.ncbi.nlm.nih.gov/books/NBK588510/
- PM2.5 → **cardiovascular effects: "CAUSAL"** (strongest tier), short- and long-term
- PM2.5 → **respiratory effects: "LIKELY to be causal"** (weaker tier) — explicitly naming
  asthma exacerbation and COPD exacerbation
- Mortality effects documented at 24-h means mostly **below 20 µg/m³** — i.e. well under "Unhealthy"

### EPA BenMAP concentration-response betas (per 1 µg/m³, log-linear: %Δ = exp(10β)−1 per 10 µg/m³)
Source: https://www.epa.gov/system/files/documents/2024-06/estimating-pm2.5-and-ozone-attributable-health-benefits-tsd-2024.pdf
- Respiratory hospital admissions 65+ (incl. COPD ICD 490-492, asthma 493): β = 0.00025 → ≈ +0.25%/10 µg/m³
- Respiratory ED visits (Krall 2013, region-specific, COPD 491/492/496 + asthma 493): β = 0.00055 (GA) to 0.00135 (TX) → ≈ **+0.55% to +1.4% per 10 µg/m³**
- CV hospital admissions 65+: β = 0.00065 → ≈ +0.65%/10 µg/m³
- CV ED visits: β = 0.00061 → ≈ +0.61%/10 µg/m³
- AMI: β = 0.02412 → the extracted claim's "+27.3% per 10 µg/m³" **looks implausible vs. all other
  literature (1–10%) — almost certainly a units/derivation error. Verify or discard.**

---

## 3. ✅ The method question — ANSWERED, and this is the practical win

**EPA BenMAP-CE health impact function** is the published, citable way to do exactly what we want,
so we do NOT have to invent a multiplier:

    Δcases = baseline_incidence_rate × population × (1 − exp(−β × ΔPM2.5))

with age- and geography-stratified rates summed across groups. EPA itself uses **disease prevalence
rates to define the at-risk population inside the function** (e.g. NHIS asthma prevalence by age
band) — which is precedent for using **CDC PLACES prevalence as our at-risk denominator**.
- Method: https://www.epa.gov/benmap/how-benmap-ce-estimates-health-and-economic-effects-air-pollution
- Manual: https://www.epa.gov/system/files/documents/2025-07/benmap_user_manual_v1.0_508.pdf

⚠️ Gap: BenMAP needs a **baseline incidence rate** (ER visits per person-year), which PLACES does
not provide (PLACES = prevalence, not incidence). Need HCUP/NEDS or state ED-visit rates to close this.

---

## 4. ✅ Live PM2.5 data — VERIFIED HANDS-ON (I tested these myself)

| Source | Access | Verdict |
|---|---|---|
| `airnowapi.org` REST API | **HTTP 401 without key** | needs free key; server-side only |
| **`files.airnowtech.org/airnow/today/reportingarea.dat`** | **HTTP 200, no key, `Access-Control-Allow-Origin: *`** | ⭐ **browser-fetchable directly** |
| `files.airnowtech.org/.../daily_data.dat` | 200, no key | monitor-level daily values |
| contours_pm25.json | 404 | not at that path |

**reportingarea.dat** — pipe-delimited, 6,829 rows, **615 reporting areas with current-hour observed
PM2.5**, 54 states/provinces. Fields: `issueDate|validDate|validTime|TZ|?|O(bserved)/F(orecast)|primary?|area|state|lat|lon|pollutant|AQI|category|actionDay|?|agency`

**Live check 2026-07-19 (this is a real, active smoke event):**
- Good 325 · Moderate 222 · **Unhealthy for Sensitive Groups 42 · Unhealthy 24 · Very Unhealthy 2**
- Worst: Driftless Area North WI **AQI 222 (Very Unhealthy)**, Central Waters North WI 203,
  W Upper Peninsula MI 190, Northwoods East WI 186, Chippewa Valley WI 180, Grants Pass OR 176

→ A Midwest smoke episode is underway right now = ideal live test case for this feature.

---

## 5. Still to research (verification never ran on these angles)
- EPA AQI **breakpoint table** (exact µg/m³ per category) — source found, claims not extracted/verified:
  https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.html
- CDC/EPA definition of "sensitive groups" per AQI category: https://www.airnow.gov/aqi/aqi-basics/
- **Extreme heat**: CDC clinical overview for CVD patients
  (https://www.cdc.gov/heat-health/hcp/clinical-overview/heat-and-people-with-cardiovascular-disease.html),
  CDC MMWR (https://www.cdc.gov/mmwr/volumes/74/wr/mm7418a2.htm), NWS HeatRisk mapping — **no
  quantified heat numbers were extracted before the run died.**

## Next steps
1. Re-run verification (needs spend-limit headroom) OR hand-verify the ~8 numbers we'd actually use.
2. Read the EPA ISA directly to settle the "suggestive vs. at-risk population" tension.
3. Get AQI breakpoints + heat numbers (angle 3 never completed).
4. Then build: AirNow reportingarea.dat layer → AQI category per area → PLACES prevalence in that
   area → carefully-worded exposure statement citing EPA/meta-analysis.
