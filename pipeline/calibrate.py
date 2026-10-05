"""How often is a map listing a real, licensed restaurant? Measured where official lists exist -> data/co/calibration*.json

Adapted from wi-eats/pipeline/calibrate.py.
- Denver (the City and County): every Overture eating/drinking listing checked against Denver's active Retail Food, Combined and
  Liquor licenses plus the state's liquor licenses at Denver addresses. Denver licenses every food business, so this is the full test.
- Boulder County: against every facility Boulder County Public Health inspected since September 2024, plus state liquor licenses.
- Statewide, county by county: against the state's on-premises liquor licenses only (restaurants, taverns, brewpubs). Many
  restaurants don't serve alcohol, so these rates are lower bounds; they compare listing sources, they don't measure them.
A match is the same business name nearby, or the same street address with a distinctive name word in common.
"""
import json
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep
from common import CO
from listings_util import official_match

o = pd.read_pickle(f"{CO}/stage1.pkl")
F = pd.read_pickle(f"{CO}/official.pkl")
CTY = {n: prep(shape(g).buffer(0.0003)) for n, g in json.load(open(f"{CO}/co_counties_detail.geojson")).items()}


def county_of(la, lo):
    if la != la:
        return None
    p = Point(lo, la)
    return next((n for n, g in CTY.items() if g.contains(p)), None)


o["county"] = [county_of(la, lo) for la, lo in zip(o.lat, o.lon)]
F["county"] = [county_of(la, lo) for la, lo in zip(F.lat, F.lon)]
o.to_pickle(f"{CO}/stage1.pkl")
F.to_pickle(f"{CO}/official.pkl")
base = ~o.j_junk & ~o.j_outside
print("listings with a county:", int(o.county.notna().sum()), "of", len(o))


def groups(L, app=False):
    s = L.src.fillna("none")
    if app:
        conf = L.confidence.fillna(0)
        return np.select([L.ov_closed | L.j_closedname, (s == "meta") & (conf >= 0.95), (s == "meta") & (conf >= 0.9),
                          s.isin(["AllThePlaces", "DAC"]), (s == "BrightQuery") & (conf >= 0.95), s == "meta"],
                         ["closed per Overture/name", "meta_high", "meta_mid", "brand_feed", "bq_high", "meta_low"], "other_sources")
    return np.select([L.closed21, L.ov_closed, (s == "meta") & L.in21, s == "meta", s.isin(["AllThePlaces", "DAC"]) & L.in21,
                      s.isin(["AllThePlaces", "DAC"]), L.in21, s == "Foursquare", s == "BrightQuery", s == "Microsoft"],
                     ["Google 2021 says closed", "Overture says closed", "Meta + open in Google 2021", "Meta only",
                      "brand feed + Google 2021", "brand feed only", "Foursquare/BrightQuery/Microsoft + Google 2021",
                      "Foursquare only", "BrightQuery only", "Microsoft only"], "other")


AREAS = {"Denver": ("Denver", F.jur.isin(["den", "liq"]) & F.active),
         "Boulder County": ("Boulder County", F.jur.isin(["bou", "liq"]) & F.active)}
res, app = {}, {}
for label, (cty, sel) in AREAS.items():
    L = o[base & (o.county == cty)].reset_index(drop=True)
    R = F[sel & (F.county == cty)].reset_index(drop=True)
    m = official_match(L, R)
    L["hit"] = L.index.map(lambda i: i in m)
    L["hit_food"] = L.index.map(lambda i: i in m and R.kind.iat[m[i]] in ("restaurant", "bar", "brewery", "food"))
    for mode, store in ((False, res), (True, app)):
        L["grp"] = groups(L, mode)
        t = L.groupby("grp").agg(n=("id", "size"), official=("hit", "mean"), food=("hit_food", "mean")).sort_values("n", ascending=False)
        print(f"\n== {label} ({'app grouping' if mode else 'web grouping'}): {len(L)} listings, {len(R)} official records")
        print(t.assign(official=(t.official * 100).round(1), food=(t.food * 100).round(1)).to_string())
        store[label] = {"listings": int(len(L)), "official_records": int(len(R)),
                        "groups": {g: {"n": int(r.n), "official": round(float(r.official), 3), "food": round(float(r.food), 3)} for g, r in t.iterrows()}}
    # the other direction: how many official restaurants/bars do the (cleaned, open) map listings hold?
    keepish = ~(L.ov_closed | L.j_closedname | L.closed21)
    got = set(R.biz.iloc[[m[i] for i in L.index[keepish] if i in m]])
    own = "den" if cty == "Denver" else "bou"
    Rr = R[(R.jur == own) & R.kind.isin(["restaurant", "bar", "food"])].drop_duplicates("biz")
    cover = float(np.mean([b in got for b in Rr.biz])) if len(Rr) else None
    print(f"{label}: official food businesses found among open map listings: {cover*100:.1f}% of {len(Rr)}")
    res[label]["coverage"] = round(cover, 3)
    res[label]["official_food"] = int(len(Rr))

# statewide, per county: share of open, cleaned listings matched to an on-premises state liquor license (a lower bound)
LQ = F[(F.jur == "liq") & F.kind.isin(["restaurant", "bar", "brewery"])].reset_index(drop=True)
L = o[base & o.county.notna() & ~o.ov_closed & ~o.j_closedname].reset_index(drop=True)
m = official_match(L, LQ)
L["liq"] = L.index.map(lambda i: i in m)
L["grp"] = groups(L, True)
per = L.groupby("county").agg(listings=("id", "size"), liq_match=("liq", "mean"))
per["liq_onprem_records"] = LQ.groupby("county").size().reindex(per.index).fillna(0).astype(int)
got_l = L[L.liq].index.map(lambda i: LQ.biz.iat[m[i]])
per["liq_found"] = [float(np.mean([b in set(got_l) for b in LQ[LQ.county == c].drop_duplicates("biz").biz])) if (LQ.county == c).any() else None
                    for c in per.index]
bygrp = L.groupby("grp").liq.agg(["size", "mean"])
print("\n== statewide, matched to an on-premises liquor license, by app grouping\n" + bygrp.assign(mean=(bygrp["mean"] * 100).round(1)).to_string())
print("\n== per county\n" + per.sort_values("listings", ascending=False).round(3).to_string())
json.dump({"areas": res, "statewide_liquor_by_group": {g: {"n": int(r["size"]), "liq": round(float(r["mean"]), 3)} for g, r in bygrp.iterrows()},
           "per_county": {c: {k: (round(float(v), 3) if isinstance(v, float) else int(v)) for k, v in r.items() if v == v}
                          for c, r in per.iterrows()},
           "unplaced_liquor_records": int((F.jur.eq("liq") & F.lat.isna()).sum())},
          open(f"{CO}/calibration.json", "w"), indent=1)
json.dump(app, open(f"{CO}/calibration_app.json", "w"), indent=1)
