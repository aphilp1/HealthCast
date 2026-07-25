# HealthCast — Project Log (read this first)

**PROJECT NAME (user-chosen 2026-07-25): HealthCast** — the NWS × US Census project
(previously PeopleWatch 2026-07-19, RouteWatch-family naming).
Folder stays `Documents\Census`; app display title stays the long official one below.

**App name (user-chosen 2026-07-25): "HealthCast"** — header `<h1>` + `<title>` both say
just "HealthCast"; NOAA + NWS logos stay in the header. (Supersedes the long official
title chosen 2026-07-18.)

**Started:** 2026-07-18
**Folder:** `C:\Users\aphil\Documents\Census` (local, not OneDrive)
**Mission:** Combine official U.S. Census Bureau population data with live weather hazards —
answer *"how many people are inside this hazard?"* for NWS warning polygons, fire zones,
and hurricane cones. Companion to StormWatch Live and RapidWatch.

**Standing rules that apply here:** real data only (no placeholders/representative data);
develop locally; preview UI on localhost before any public push.

---

## The backbone: official Census Bureau MCP server

Repo (cloned here): `us-census-bureau-data-api-mcp\` — github.com/uscensusbureau/us-census-bureau-data-api-mcp
License CC0-1.0, TypeScript, MCP SDK, built by the Census Bureau itself.

### Architecture (studied 2026-07-18)
- `mcp-server\` — the actual MCP server. Plain Node stdio server (`dist/index.js`).
  Registers 5 tools + 1 prompt. `CENSUS_API_KEY` read from process env (checked per-tool).
- `mcp-db\` — optional PostgreSQL 16 sidecar (Docker). Migrations + seeds pull Census
  metadata into local Postgres: all geographies (nation/region/division/state/county/
  county-subdivision/place/ZCTA) and 32,000+ data-table records for search.
- `docker-compose.yml` — profiles: `prod` (db + db-init + mcp-server), `dev`, `test`.
- `scripts\mcp-connect.sh` — the documented client launcher (bash + Docker).
- `scripts\dev\` — CLI helper scripts (census-mcp.sh etc.) for testing tools by hand.

### The 5 tools
| Tool | Needs API key | Needs Postgres | What it does |
|---|---|---|---|
| `fetch-aggregate-data` | YES | no | The workhorse. GET `api.census.gov/data/{year}/{dataset}` with `get` (variables and/or `group(TABLE)`), `for`, `in`, `ucgid`, predicates, `descriptive` labels. Returns rows + citation. |
| `list-datasets` | yes | no | Metadata for all Census API datasets. |
| `fetch-dataset-geography` | yes | no | Which geography levels a dataset supports (e.g. can I query acs/acs5 at tract level?). |
| `resolve-geography-fips` | no | **YES** | Name → FIPS + ready-to-use query params ("Cook County" → `for=county:031&in=state:17`). |
| `search-data-tables` | no | **YES** | Topic → table ID ("income by race" → B19001B…). 32k+ tables, ~83% ACS. |

Prompt: `get_population_data(geography_name)` — instruction template chaining resolve-fips → fetch.

### KEY FINDING — runs WITHOUT Docker
Docker is NOT installed on this machine, but the server builds and runs natively
(Node v24 present). Verified 2026-07-18: `npm install && npm run build` in `mcp-server\`,
then `tools/list` over stdio returns all 5 tools. The 3 API-backed tools work fine with
just an API key; the 2 Postgres-backed search tools fail gracefully ("Database connection
failed") until Docker/Postgres exists. Claude can supply FIPS codes and table IDs from
its own knowledge in the meantime, so degraded mode is fully workable.

### How it's wired into Claude Code (DONE)
- User-scope MCP server `census-api` → `cmd /c C:\Users\aphil\Documents\Census\census-mcp.cmd`
- `census-mcp.cmd` loads `CENSUS_API_KEY` from `Census\.env`, then runs `node mcp-server\dist\index.js`
- Status: ✔ Connected (verified with `claude mcp list`)
- Gotcha: registering via Git Bash mangled `/c` → `C:/`; use PowerShell for `claude mcp add`.

### USER TODO (blocking full use)
1. **Get free API key**: https://api.census.gov/data/key_signup.html (emailed in minutes)
   → paste into `C:\Users\aphil\Documents\Census\.env` replacing `PASTE_YOUR_KEY_HERE`.
   Without it the API discovery/metadata tools and `fetch-aggregate-data` return
   "CENSUS_API_KEY is not set" (the raw API itself now REQUIRES a key — verified: keyless
   requests redirect to missing_key.html).
2. **Optional, later**: install Docker Desktop → `docker compose --profile prod run --rm
   census-mcp-db-init sh -c "npm run migrate:up && npm run seed"` (one-time) to light up
   the two search tools the documented way.

---

## Data inventory (`data\`, all real, all keyless official sources)
- `co-est2023-alldata.csv` — Census Population Estimates Program, Vintage 2023, all counties.
- `counties_5m_raw.geojson` — TIGERweb `Generalized_ACS2023/State_County` layer 12
  (Counties 1:5M generalized), all 3,235 features, GeoJSON, precision 4. (Layer 13 = 20M
  coarser, layer 11 = 500K finer, maxRecordCount 100k = one request gets everything.)
- `counties.geojson` (4.8 MB) — merge of the two: every feature has GEOID/NAME/STATE/POP2023.
  **All 3,144 stateside counties matched; sum = 334,914,895 = official US 2023 pop.** The 91
  unmatched features are PR municipios + island territories (no vintage-2023 estimates file
  found yet — get PR populations via ACS through the MCP server later; matters for hurricanes).
- `county_pop.json` (139 KB) — compact `{GEOID: [county, state, pop2023]}` lookup. Built for
  summing NWS alert SAME/FIPS codes (zone-based alerts list county FIPS in
  `properties.geocode.SAME` — exact county populations, no geometry math needed).
- `merge_pop.py` — rebuilds both outputs from the raw files.

## App concept (v0, next up)
Single-file `census.html` (StormWatch style: Leaflet, dark high-contrast UI, no build step):
1. County population choropleth (counties.geojson).
2. Live NWS alerts (api.weather.gov, CORS-friendly, same as StormWatch).
3. Click an alert → population inside:
   - zone/county alerts: sum `county_pop.json` over `geocode.SAME` FIPS → exact.
   - polygon alerts (tornado/flash-flood warnings): turf.js county intersection,
     area-weighted population (label as estimate; uniform-density assumption).
4. Later: tract-level accuracy (85k tract centroids), hurricane cone exposure in RapidWatch,
   demographic depth via MCP (age 65+, mobile homes — hazard-vulnerability relevant tables).

## Session log
- **2026-07-25 (RESUMED — renamed HealthCast)** — project renamed **HealthCast** (was
  PeopleWatch); app header + <title> changed to "HealthCast", NOAA/NWS logos kept.
  Favicon added: `assets/healthcast_icon.svg` (navy rounded square, gold EKG pulse,
  blue broadcast arcs), linked via `<link rel="icon">` — **user-confirmed working +
  looks good**. v14 county-highlight/Map-Layer styling **approved by Alex**.
  **GIT INIT done**: local repo, root commit `0d12fcb` (27 files); .gitignore excludes
  `.env` (API key) + `us-census-bureau-data-api-mcp/` (re-clonable). Server restarted on :8020.
  **PUBLISHED (Alex's call, "so anyone can see it")**: public repo
  https://github.com/aphilp1/HealthCast + GitHub Pages LIVE at
  **https://aphilp1.github.io/HealthCast/** (root index.html redirects to census.html;
  .nojekyll added per StormWatch lesson). Verified on the public URL via in-page JS:
  450 alerts / 114.4M headline / cards rendered / no console errors. Screenshot tooling
  timed out (hidden-tab throttling — known limit), page state verified instead.
- **2026-07-19 (PAUSED — backup taken)** — v14 visual pass, then paused on Alex's cue.
  Changes since v13, **none visually confirmed by Alex** (my screenshot tooling failed):
  · Basemap switcher M/L/D (CARTO voyager / positron / dark_all), **Muted = default per Alex**
    ("M is best"); county edge colors adapt per basemap.
  · Base map was "too dark/black" — no-alert counties now 0.06 opacity so the basemap reads;
    only alerted counties carry color.
  · County click highlight: halo (weight 9, .4) + ring (3.5) + **dark navy fill .75**.
  · Group/polygon alert selection: halo (weight 8, .28) + severity fill **.72** (was .42).
  · Map Layer panel restyled: 232px, frosted blur, uppercase header, larger select + legend chips.
  · BUG FIXED mid-pass: `typeof countyLayer` on a `let` in its temporal dead zone THREW and killed
    the whole app (blank page, no buttons/cards) → wrapped in try/catch.
  **BACKUP:** `Documents\PeopleWatch_backups\PeopleWatch_2026-07-19_2330.zip` (13.8 MB, 26 entries,
  verified: census.html + all data/*.json + .env; excludes re-clonable MCP repo) + Desktop copy.
  **RESUME:** cue "resume peoplewatch" → memory `peoplewatch_resume_cue.md`.
  **FIRST QUESTION ON RESUME:** does the county highlight / Map Layer panel look right?
- **2026-07-19 (v13 - "not seeing anything" FIX + performance)** — user reported a blank
  app. Root causes + fixes:
  (1) **BROWSER CACHE** — census.html itself was never cache-busted (only data/*.json
  were), so Chrome could serve a STALE copy — including the broken 1:15 AM SyntaxError
  build, whose dead JS = empty shell. FIX: `serve_peoplewatch.py` sends
  `Cache-Control: no-store, no-cache, must-revalidate` (verified in response headers);
  start-peoplewatch.cmd now launches it. ⚠️ user needs ONE hard refresh (Ctrl+Shift+R)
  to escape the already-cached copy; after that it stays fresh automatically.
  (2) **MAIN-THREAD SATURATION** — polygonExposure scanned ALL 240,942 bg centroids per
  alert (350 alerts = tens of millions of ops), freezing paint; screenshots timed out.
  FIX: 1-degree GRID SPATIAL INDEX (bgGrid/trGrid, buildBgIndex(), candidates(bbox))
  used by polygonExposure + tractDemographics; unionPop no longer full-scans (county
  sums precomputed into _fipsPop Map, polygon indices deduped).
  MEASURED AFTER: polygon exposure = **14 ms** for a 403,950-person alert (was a full
  240k scan); app loads 350 alerts / 26 type cards / map tiles, headline 141.1M, no new
  console errors. NOT verified: visual screenshot (CDP injection kept timing out — a
  tooling limit, page itself answers JS queries instantly).
- **2026-07-19 (v12 - ALERTS-FIRST DISPLAY + county alert detail) - PeopleWatch named**
  (1) Display inversion per user ("alerts come through, Census below"): default map
  mode = "Active alerts (by severity)" - counties filled red/orange/gold/blue by worst
  active alert (SEV_FILL via coverageWorst from ALL alerts' SAME codes), no-alert
  counties near-black; Census layers still in MAP LAYER picker, and in those modes
  alerts show as severity OUTLINES (renderCoverage). Legend adapts per mode.
  (2) County click now leads with "Active NWS alerts - N": full cards per alert
  (severity color bar, timing from onset/ends, NWS headline, expandable FULL alert
  text incl description + "WHAT TO DO" instruction), Census sections below. Verified:
  Carlton Co MN = 5 alerts, Heat Advisory "Sun 10AM-7PM", 1,013-char description
  expands. GOTCHA: python-replace with \n inside heredoc wrote literal newlines into
  a JS string -> SyntaxError killed whole app; check console after every batch edit.
  (3) PROJECT NAMED **PeopleWatch** (user, joins *Watch family); app display title
  unchanged.
- **2026-07-19 (v11 - coverage tint + TRACT-LEVEL PLACES)** - (1) user: "why are some
  warnings highlighted on the base map and not all?" -> NWS only gives polygons to
  storm-scale warnings; zone alerts (most of them) were invisible until clicked. FIX =
  COVERAGE LAYER: new pane p-coverage (z400, pointer-events none, dims in focus mode);
  drawCoverage() tints every county under >=1 zone alert by worst severity (SAME codes,
  fillOpacity .22, per-severity geoJSON batches). Verified: 4 severity groups drawn.
  (2) TRACT-LEVEL PLACES (user approved): places_tract_2025.csv via Socrata $select
  (yjkw-uj5s, 83,522 tracts, 4 measures + adults, 3.8MB); build_tract_demo.py joins by
  tract GEOID -> tract_demo.json gains diabn/copdn/chdn/bphighn (precomputed adult
  counts; US totals verified: diabetes 29.0M, COPD 16.0M, CHD 15.0M, highBP 82.3M);
  tractDemographics() sums them inside polygons -> alert health grid now TRACT-precise
  (verified: Marine Weather Statement 847K people -> 96K diabetes/62K COPD/65K CHD/290K
  highBP); county-share fallback kept for zone alerts. No console errors. NOTE:
  screenshot injection kept timing out (user actively using tab ~12:40 AM) - verified
  via page-state JS instead.
- **2026-07-19 (v10 - CHRONIC DISEASE)** - user wanted COPD/CAD/diabetes "from US
  Census" -> Census does NOT collect disease data; authoritative source = CDC PLACES
  2025 (model-based BRFSS estimates on Census denominators). data/build: places_county_
  2025.csv (Socrata id i46a-9kgh, data.cdc.gov, keyless, 3,143 counties x 40 measures)
  -> county_health.json (9 conditions: diab/copd/chd/asthma/bphigh/stroke/obesity/
  cancer/depr + TotalPop18plus adults; US adults 262,083,004 verified; Holmes MS
  diabetes 23.3%, obesity 50.7% = published values; 2,956 counties full data, rest
  suppressed-null). APP: (1) county card new "Chronic disease - %% of adults" section
  (9 rows); (2) three new map layers: %% diabetes (amber) / %% COPD (steel) / %% CHD
  (rose) - 10 modes total; (3) alert + group panels: SECOND grid = est. ADULT COUNTS
  (adults x share x prevalence): verified Heat Advisory 32.0M -> ~2.9M diabetes, ~1.7M
  COPD, ~1.6M heart disease, ~8.8M high BP. All browser-verified; diabetes layer shows
  correct Deep-South belt. Cite CDC PLACES 2025 in method lines. NOTE: app name kept
  ("...Extreme Weather..."), renames earlier in day: NOAA dropped, Severe->Extreme.
- **2026-07-18 (v9b - county click bug #2)** - user "still cant click on a county":
  SECOND blocker found - the SELECTION HIGHLIGHT overlay (p-selection SVG) captured
  clicks over every highlighted county (user had a group selected covering their whole
  view). interactive:false on L.geoJSON did NOT propagate to child paths; the
  bulletproof fix = pane-level `map.getPane('p-selection').style.pointerEvents='none'`
  (selection is display-only). VERIFIED real-mouse: county click through active group
  highlight opens county card (Mercer Co KY); hover tooltips pierce highlight too.
  County-click fix = TWO stacked bugs total: (1) alerts canvas swallowed all map clicks
  -> SVG renderer; (2) selection overlay swallowed clicks in highlighted areas -> pane
  pointer-events none. Gotcha: map coords go stale during fitBounds animation - wait
  for settle before computing click targets in tests.
- **2026-07-18 (v9 - county-click ROOT CAUSE + Hawaii)** - user: "Does not work to click
  on a county" - CONFIRMED by real map click (my v8 QA had only called the function via
  JS = inadequate). ROOT CAUSE: two stacked CANVAS renderers - the alerts canvas (pane
  z420) swallows ALL pointer events for the counties canvas beneath (z350), even where
  no alert is painted. FIX: alerts render as SVG (L.svg renderer) - SVG only captures
  events on painted shapes, empty areas pass through. VERIFIED with real mouse clicks:
  county click -> detail card (Logan Co KS, Mason Co TX), alert-path click -> alert
  panel (Flash Flood Warning), water click -> nothing. NOTE: only ~29 polygon alerts
  at night, tiny at national zoom - misses near small polygons are geometry not bugs.
  HAWAII: all data was already present (5 counties, 1,050 BGs, 427 tracts, Honolulu
  1,003,666 verified) - added REGION BUTTONS US/AK/HI/PR (left edge, under zoom) that
  jump the view; HI renders w/ choropleth, verified. LESSON: QA must use REAL clicks
  (computer tool), not JS function calls - and the user may be USING the tab while I
  test (state changed under me at 11:41 PM = user interaction, not a bug; earlier
  "Dense Smoke group panel" anomaly = same cause).
- **2026-07-18 (v8 - QA sweep + county deep-dive)** - user angry ("producing junk you
  aren't even checking"): Alaska Heat Advisory made group-zoom frame the whole planet;
  panel not draggable; "+392 counties" dead text; wanted StormWatch-style county detail.
  FIXES (all QA'd): (1) Alaska zoom guard - group bounds wider than 65 lon / 30 lat deg
  -> keep national frame (verified zoom stays 5); map minZoom 3. (2) #expo panel
  restructured: drag header (pointer capture) + scrollable body + close btn; verified
  real drag. (3) countyTable() with "+N more - show all"/"top 10 only" toggle (verified
  426-row expand). (4) COUNTY DEEP-DIVE: click county -> detailed census card, 16 rows
  / 5 sections (People, Race&ethnicity, Economy, Housing&access, Education/language/
  health) from 9 NEW verified ACS profile vars (DP02_0068PE edu, DP03_0009PE unemp,
  DP04_0047PE renter, DP03_0096PE insured, DP02_0114PE lang, DP05_0076PE hisp,
  DP05_0037/38/47PE white/black/asian - all sanity-checked vs SF/Cook knowns; DP05
  probing needed, first Hispanic guess was wrong). (5) ROOT-CAUSE BUG: Chrome
  heuristic-caches data/*.json -> rebuilt county_acs.json never loaded (panel showed 7
  rows) -> cache-busters (?v=Date.now()) on all 5 data fetches. LESSON: after any data
  rebuild, hard-reload + verify field presence in-browser.
- **2026-07-18 (v7 - GROUPED ALERTS)** - user: "dozens and dozens of heat advisories...
  show all of them at the same time". List now GROUPS BY EVENT TYPE: 324 alerts -> 17
  type cards (e.g. "Air Quality Alert - 62 alerts - 47.9M", union pop per group, worst
  severity color). Click a group card -> ALL its alerts light up on the map at once
  (focus mode; polygons + deduped counties in one selection layer) + group panel:
  union total ("~20,183,101 under at least one Heat Advisory"), aggregate demographics,
  top counties merged across members (max-per-county, counted once). "individual
  alerts" expander inside each card -> member rows (areaDesc + pop) -> single-alert
  view unchanged. Verified in browser: Heat Advisory group = 29 alerts, two glowing
  regions (N Plains + Gulf Coast), expander 29 rows, member click OK, no console errors.
- **2026-07-18 (v6 - legend overhaul)** - user: legend swatches invisible (ROOT CAUSE:
  CSS selector `.legend i` no longer matched after layer control got class map-ctl -
  chips had zero size), colors didn't match map, box fixed in place. FIX: MAP LAYER box
  rebuilt as plain div in #map - DRAGGABLE (pointer events on header, map.dragging
  toggled), COLLAPSIBLE (-), CLOSEABLE (x -> "Map layer" reopen pill); legend rows =
  18x14 chips + labels; chips use blendToMap() = ramp color composited at the county
  fill opacity (0.7) over dark base so LEGEND == MAP exactly; county fillOpacity
  0.6->0.7. Sample question placeholder = "Ask: How many people are at risk for air
  quality?" (verified working, risk/danger added to stopwords). All verified in browser
  incl real mouse drag.
- **2026-07-18 (v5 - robust ask box + reset, FULL TEST PASS)** - user's typo'd question
  ("bering") zeroed out results -> parser hardened: Levenshtein typo-correction vs
  vocab (bering->being, flod->flood), unknown tokens IGNORED not required (shown as
  'ignored: "x"'), generic questions -> national union total, content-words-matched-
  nothing -> honest no-match (never a misleading fallback), STATE NAMES resolved
  structurally vs county FIPS (texas/new jersey work even though NWS areaDesc lacks
  state names). RESET: X-in-searchbox + Esc + "Reset" chip (clears question/filters/
  selection + re-centers). 12-case test battery ALL PASS incl ground-truth checks
  (NJ no-match verified = NJ truly has 0 alerts tonight; MO heat 6.15M = 3 advisories).
  MCP server re-verified live: MO 65+ = 1,079,129; San Juan Municipio 338,661; Cook Co
  median income $81,797. App name final: "NOAA National Weather Service Severe Weather
  Forecast Impacts on US Populations".
- **2026-07-18 (v4 - ASK BOX + branding)** - user typed "how many people are affected
  right now by smoke" into search -> got nothing (was a literal substring filter; NWS
  calls smoke events "Air Quality Alert"). FIX: search box is now a question box -
  strips question stopwords, expands hazard synonyms (smoke->air quality/dense smoke,
  fire->red flag, winter->snow/ice/blizzard, ...), AND-matches remaining tokens, shows
  an ANSWER BAR: "~N people are under M matching alerts" (union via cached per-alert
  block-group footprints _bgIdx + county sets - instant). VERIFIED with the user's
  exact question: ~101,533,941 people under 133 smoke alerts (AQ Alert + Dense Smoke
  Advisory). Also: app renamed (FINAL): "NOAA National Weather Service Severe Weather
  Forecasted Impact on US Populations" - VERBATIM, no taglines (user rejected my
  paraphrase twice); NOAA + NWS logos (public-domain SVGs, Wikimedia) in assets\,
  44px in header. NWS logo URL gotcha: use commons.wikimedia.org/wiki/Special:FilePath/.
- **2026-07-18 (v3 — upgrades + FOCUS MODE)** — user: implement upgrades + "when I click
  an alert the map should clearly show it" + "unintelligible nonsense" (map color chaos).
  ✅ **Focus mode** (THE fix): separate Leaflet panes (p-counties 350 / p-alerts 420 /
  p-selection 450, canvas renderers per pane); selecting an alert dims counties to 0.3
  and other alerts to 0.12 opacity (CSS pane opacity, instant), selection glows in
  severity color (Unknown→gold) w/ thin white edges as ONE region. clearSelection() on ✕.
  Verified: 9.2M IL Air Quality Alert = clear gold Chicago-area region on dark map.
  ✅ **Click race FIXED**: list clicks died when renderAlertList rebuilt DOM mid-click →
  delegated click listener on #alert-list + in-place badge updates during compute
  (no rebuild until final re-sort). Synthetic + real click verified.
  ✅ **Tract demographics**: build_tract_demo.py → tract_demo.json (83,656 tracts, 2 ACS
  calls/state × 52; totals verified 332M/56.0M 65+/8.1M mobile/41.4M poverty); polygon
  alerts + cones now sum ACS tract values inside polygon (county-share fallback kept).
  ✅ **Live NHC cones**: NOAA tropical MapServer (mapservices.weather.noaa.gov) Forecast
  Cone layers [8,34,...372], f=geojson, CORS OK (needs Origin header — browser sends it);
  purple dashed cones, click → exposure panel; verified TS Elida (EP5) renders.
  ✅ **2 new map layers**: median age (B01002_001E), % no-vehicle households (DP04_0058PE,
  Manhattan sanity 77.7% ✓) → 7 modes total.
  GOTCHA: automation ref-clicks after scroll_to use stale coords (2 false alarms) — app
  click handling was fine; verify with synthetic dispatch before touching code.
- **2026-07-18** — Project created. County pop + boundaries downloaded/merged/verified.
  MCP repo cloned, studied end-to-end, built natively (no Docker), smoke-tested,
  registered as user-scope `census-api` server. Blocked on user's API key for live data.
- **2026-07-18 (later)** — ✅ API KEY ACTIVE (in `.env`; note: file needs `CENSUS_API_KEY=`
  prefix — user pasted bare key, fixed). MCP verified end-to-end: fetch-aggregate-data
  returns Butte County CA = 209,470 (ACS 2023 5yr) with citation.
  ✅ **census.html v0 BUILT + BROWSER-TESTED** on http://localhost:8020/census.html
  (serve: `python -m http.server 8020` in Census folder). Verified live: choropleth
  renders all counties; 480 live NWS alerts; polygon path (PA Flash Flood Warning →
  ~38,486 people, area-weighted per-county table) and SAME-code path (ND Heat Advisory →
  ~228,698 people, exact 20-county sum) both compute correct, plausible numbers.
  GOTCHA: api.weather.gov `/alerts/active` no longer accepts `limit` param (HTTP 400).
- **2026-07-18 (v1 rebuild)** — User feedback: compute by POLYGON not county area-weight;
  presentation "very poor"; wants LLM interaction via the Census MCP tools.
  ✅ **Block-group engine**: `data/bg_centroids.json` (240,942 CenPop2020 block-group
  population-weighted centroids, national incl PR, scaled to county 2023 estimates via
  `build_blockgroups.py`; totals verified 334.7M raw / 338.2M scaled = US+PR).
  Polygon exposure = centroids inside polygon (the NWS method). PR municipios added to
  `county_pop.json` (2020 Census, 78 munis, 3,285,874).
  ✅ **census.html v1**: auto-computes ALL alerts on load (chunked), headline "people
  under ≥1 alert" (union, no double-count), list ranked by population, search + filter
  chips, pop badges, zone alerts (smoke/air quality/heat) highlight + zoom to their
  counties, 5-min auto-refresh. Browser-verified: 531 alerts, 165.3M union headline,
  NYC Air Quality Alert = exact 13,000,074 w/ county highlight.
  ✅ **/census SKILL** (user-scope, `~\.claude\skills\census\SKILL.md`): plain-English
  Census×weather questions → MCP orchestration. DEMO VERIFIED (`demo_llm_query.py`):
  "people 65+ under Heat Advisories right now" = **6,423,927** (566 counties/20 states,
  S0101_C01_030E acs/acs5/subject 2023 via MCP). GOTCHA: piping JSON-RPC to the MCP cmd
  from python needs trailing `\n`.
  OPEN: user unhappy with visual design → next session = design overhaul (direction TBD:
  possibly chat-first UI, which would need a small backend + Anthropic API key = paid).
- **2026-07-18 (v2 polish + ACS)** — User chose: polish current app + leverage Census
  (no paid chat backend). ✅ `data/build_county_acs.py` → `county_acs.json`: ACS 2023
  5-yr for all 3,222 counties incl 78 PR munis (65+, under-5, mobile homes B25024_010E,
  median income B19013_001E, poverty DP03_0128PE; 65+ total 56,710,444 ✓).
  ✅ census.html v2 (browser-verified, no console errors):
  · MAP LAYER switcher: population / % 65+ / median income / mobile homes / % poverty —
    per-mode sequential single-hue ramps (dataviz skill method), runtime quantile bins,
    auto-rebuilt legend. Poverty layer verified (Deep South/Appalachia/border pattern).
  · County hover tooltip (current-mode value) + full ACS census card popup per county.
  · Exposure panel now has demographics grid: est. 65+/under-5/mobile homes/poverty%
    inside EACH alert (county ACS shares × county's people-in-alert; assumption stated).
    Verified: Tornado Watch 12.4M → ~2.2M 65+, ~675K under 5, ~97K mobile homes, 10% pov.
  · Typography/spacing/hover polish, tabular numerals throughout.
  NOTE: layer restyle takes a few seconds (3,235 canvas polygons) — brief freeze normal.
  AWAITING user review of v2.
