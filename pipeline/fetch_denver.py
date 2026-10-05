"""Denver's open "Active Business Licenses" (City and County of Denver, ArcGIS item 5793f5349ad448b3b916a555b8f77ddf, updated daily)
-> data/raw/official/denver_licenses.json. Only the food and liquor license types. Polite: one request at a time, honest UA."""
import json, os, time, urllib.parse, requests
B = "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_active_business_licenses/FeatureServer/42/query"
UA = {"User-Agent": "COEatsResearch/1.0 (work-with-nick@gmail.com)"}
TYPES = ("Retail Food", "Combined License", "Liquor", "Retail Food - Commissary")
where = "LICENSE_TYPE IN (" + ",".join(f"'{t}'" for t in TYPES) + ")"
rows, off = [], 0
while True:
    r = requests.get(B, params={"where": where, "outFields": "*", "f": "json", "resultOffset": off, "resultRecordCount": 2000,
                                "orderByFields": "OBJECTID"}, headers=UA, timeout=60).json()
    feats = [f["attributes"] for f in r.get("features", [])]
    rows += feats
    if not feats or not r.get("exceededTransferLimit"):
        break
    off += len(feats); time.sleep(1)
out = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "official", "denver_licenses.json")
json.dump(rows, open(out, "w"))
print(len(rows), "Denver food/liquor licenses")
