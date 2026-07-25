"""Demo of the /census LLM interaction: 'How many people 65+ are under Heat Advisories right now?'

1. Live NWS feed -> Heat Advisory county FIPS (SAME codes)
2. census-api MCP server (official Census Bureau) -> S0101_C01_030E (65+) per county
3. Sum + top counties
"""
import json, subprocess, urllib.request
from collections import defaultdict

req = urllib.request.Request(
    "https://api.weather.gov/alerts/active?status=actual&event=Heat%20Advisory",
    headers={"User-Agent": "census-project-demo (aphilp1@gmail.com)"})
feed = json.load(urllib.request.urlopen(req))

by_state = defaultdict(set)
n_alerts = 0
for a in feed.get("features", []):
    same = (a["properties"].get("geocode") or {}).get("SAME") or []
    if same:
        n_alerts += 1
    for code in same:
        fips = code[1:] if len(code) == 6 else code
        by_state[fips[:2]].add(fips[2:])

print(f"Heat Advisories with county codes: {n_alerts}, states: {len(by_state)}, counties: {sum(len(v) for v in by_state.values())}")

MCP = r"C:\Users\aphil\Documents\Census\census-mcp.cmd"
def mcp_fetch(state, counties):
    call = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "fetch-aggregate-data",
                       "arguments": {"dataset": "acs/acs5/subject", "year": 2023,
                                     "get": {"variables": ["NAME", "S0101_C01_030E"]},
                                     "for": "county:" + ",".join(sorted(counties)),
                                     "in": "state:" + state}}}
    out = subprocess.run(["cmd", "/c", MCP], input=json.dumps(call) + "\n",
                         capture_output=True, text=True, timeout=120).stdout
    resp = json.loads(out.strip().splitlines()[-1])
    text = resp["result"]["content"][0]["text"]
    rows = []
    for line in text.splitlines():
        if "S0101_C01_030E:" in line:
            parts = dict(seg.split(": ", 1) for seg in line.split(", ") if ": " in seg)
            rows.append((parts["NAME"], int(parts["S0101_C01_030E"])))
    return rows

total = 0
all_rows = []
for state, counties in sorted(by_state.items()):
    rows = mcp_fetch(state, counties)
    all_rows.extend(rows)
    total += sum(v for _, v in rows)
    print(f"  state {state}: {len(rows)} counties, 65+ = {sum(v for _, v in rows):,}")

all_rows.sort(key=lambda r: -r[1])
print(f"\nTOTAL people 65+ currently under Heat Advisories: {total:,}")
print("Top counties:")
for name, v in all_rows[:8]:
    print(f"  {name}: {v:,}")
