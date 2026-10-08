"""Official records for Colorado -> one table of licensed / inspected food and drink businesses.

Sources (all public domain or open, see data/raw/official/SOURCES.md):
- "den": City and County of Denver, Active Business Licenses (ArcGIS, daily): Retail Food, Combined License, Liquor, Commissary.
- "liq": Colorado Department of Revenue, Liquor Enforcement Division, "Liquor Licenses in Colorado" (data.colorado.gov ier5-5ms2,
         monthly): every active state liquor license. Statewide, but only businesses with a liquor license, and no coordinates.
- "bou": Boulder County Public Health inspections: the 2025-present set (6ytb-f2cq, one row per violation, with the official
         Pass / Reinspection Required / Closure result) and the 2013-Aug 2025 archive (tuvj-xz3m, no result column).
         The two systems number facilities differently (the same FA id is a different business in each), so they are joined
         by name and address, never by id.

load() returns: jur, lic (our id), name, keys (name keys), addr, city, zip, num, street, lat, lon, kind, active.
kind: restaurant | bar | brewery | retail | venue | other.
"""
import os, re, json
import numpy as np, pandas as pd
from common import norm_name, RAW, name_sim, _stems, GENERIC

OFF = os.path.join(RAW, "official")
DIRS = {"N": "N", "S": "S", "E": "E", "W": "W", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
TYPES = set("ST STREET AVE AV AVENUE BLVD BOULEVARD RD ROAD DR DRIVE LN LANE CT COURT PL PLACE PKWY PARKWAY TER TRL TRAIL WAY HWY CIR "
            "CIRCLE PLZ SQ MALL BND PASS XING RUN ROW WALK RDG LOOP".split())


def road(a):
    """One spelling for numbered roads: 'US HIGHWAY 6' = 'US-6' = 'Hwy 6'; 'STATE HIGHWAY 119' = 'CO-119' = 'SH 119'; 'COUNTY ROAD 5' = 'CR 5'."""
    a = re.sub(r"(\d)\s*&\s*(\d)", r"\1-\2", a.upper())
    a = re.sub(r"\b(US|CO|SH|CR|I)-(\w)", r"\1 \2", a)
    a = re.sub(r"\b(?:US|U S)\s+(?:HIGHWAY|HWY)\b", "US", a)
    a = re.sub(r"\b(?:STATE (?:HIGHWAY|HWY|ROAD|RD)|SH|COLORADO (?:HIGHWAY|HWY|STATE HIGHWAY)|CO (?:HIGHWAY|HWY))\b", "COH", a)
    a = re.sub(r"\b(?:COUNTY (?:HIGHWAY|HWY|ROAD|RD)|CO RD|CTY (?:HWY|RD)|CR)\b", "CR", a)
    a = re.sub(r"\bHIGHWAY\b", "HWY", a)
    return re.sub(r"\b(US|COH|CR|HWY) (\w+)\s*-\s*\w+", r"\1 \2", a)


ORD = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH",
       "EIGHTH": "8TH", "NINTH": "9TH", "TENTH": "10TH", "ELEVENTH": "11TH", "TWELFTH": "12TH"}


def street_key(a):
    """'2505 Monroe St' -> ('2505', 'MONROE'); '1000 OSAGE STREET' -> ('1000', 'OSAGE'); 'E Colfax Ave' keeps 'COLFAX'."""
    if not isinstance(a, str):
        return None, None
    a = re.sub(r"[.,#]", " ", road(a))
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*\d+[A-Z]?)?\s+(.*)$", a)
    if not m:
        return None, None
    words = [w for w in m.group(2).split() if w]
    if len(words) > 1 and words[0] in DIRS:
        words = words[1:]
    core = []
    for w in words:
        if w in TYPES and core:
            break
        core.append(w)
    core = [ORD.get(w, w) for w in core]
    return m.group(1), " ".join(core[:3]) or None


def street_compat(a, b):
    """Same street, or one is a whole-word prefix of the other: Boulder's 2025 set sometimes truncates ("1206 CENTAUR" = Centaur Village Dr)."""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return False
    return a == b or a.startswith(b + " ") or b.startswith(a + " ")


def street_nums(a):
    """'157-159 W Main St' -> {'157', '159'}; '2505 Monroe St' -> {'2505'}."""
    if not isinstance(a, str):
        return set()
    a = road(a)
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(\d+)[A-Z]?)?\s", a.upper() + " ")
    if not m:
        return set()
    lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:   # "1500-02"
        hi = int(str(lo)[: len(str(lo)) - len(m.group(2))] + m.group(2)) if m.group(2) else lo
    return {str(x) for x in range(lo, hi + 1, 2 if (hi - lo) % 2 == 0 else 1)} if 0 <= hi - lo <= 12 else {str(lo)}


def _names(*vals):
    out = []
    for v in vals:
        if not isinstance(v, str):
            continue
        v = re.sub(r"\s*\((?:MOBILE|MOBILE UNIT|COMMISSARY|CATERING|SPECIAL EVENT|SPEC EVENT|TEMP(?:ORARY)? EVENT|CP|INSIDE [^)]*)\)\s*$", "", v, flags=re.I)
        for part in re.split(r"\s*/\s*|\s+\bdba\b\s+|\s+&\s+(?=[A-Z][a-z])", v, flags=re.I):
            k = norm_name(re.sub(r"\b(?:LLC|INC|CORP|CORPORATION|LTD|CO)\b\.?", "", part, flags=re.I))
            if k and k not in out:
                out.append(k)
    return out


# state liquor license types -> kind. On-premises licenses mean a bar or restaurant serving alcohol; the rest are stores, makers,
# event venues or add-on permits (a "Takeout & Delivery Permit" rides on another license; FMB and Wine covers grocery stores).
LIQ_KIND = [
    (r"^Hotel & Restaurant", "restaurant"), (r"^Vintner's Restaurant", "restaurant"), (r"^Brew Pub", "brewery"),
    (r"^Distillery Pub", "brewery"), (r"^Tavern", "bar"), (r"^Retail Gaming Tavern", "bar"), (r"^Beer & Wine", "restaurant"),
    (r"^Fermented Malt Beverage On\b", "bar"), (r"^Club License", "venue"), (r"^Manufacturer \((?:brewery|distillery)", "brewery"),
    (r"^Limited Winery", "brewery"), (r"^Retail Liquor Store|^Liquor Licensed Drug Store|^Fermented Malt Beverage and Wine", "retail"),
    (r"^Entertainment Facility|^Lodging Facility|^Resort Complex|^Arts License|^Campus Liquor|^Racetrack|^Bed & Breakfast|^Public Transportation", "venue"),
]
ONPREM = ("restaurant", "bar", "brewery")


def liq_kind(t):
    for pat, k in LIQ_KIND:
        if re.search(pat, t or ""):
            return k
    return None


def load_liquor():
    d = pd.DataFrame(json.load(open(f"{OFF}/liquor_active.json")))
    d["kind"] = d.license_type.map(liq_kind)
    d = d[d.kind.notna()].copy()
    rows = []
    for _, r in d.iterrows():
        num, st = street_key(r.street_address)
        z = str(r.zip or "")[:5]
        rows.append({"jur": "liq", "lic": "LIQ-" + r.license_number, "name": r.doing_business_as or r.licensee_name,
                     "dba": r.doing_business_as or None, "holder": r.licensee_name or None,
                     "keys": _names(r.doing_business_as, r.licensee_name), "addr": r.street_address, "city": r.city, "zip": z,
                     "num": num, "street": st, "lat": np.nan, "lon": np.nan, "kind": r.kind, "active": True,
                     "ltype": re.sub(r"\s*\((?:city|county|City|County|State)\)\s*$", "", r.license_type).replace("Fermented Malt Beverage and Wine(county)", "Fermented Malt Beverage and Wine"),
                     "expires": str(r.expiration)[:10]})
    return pd.DataFrame(rows)


def load_denver():
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:2232", "EPSG:4326", always_xy=True)   # Colorado Central State Plane, US survey feet
    d = pd.DataFrame(json.load(open(f"{OFF}/denver_licenses.json")))
    rows = []
    for _, r in d.iterrows():
        num, st = street_key(r.ADDRESS)
        lat = lon = np.nan
        if r.X_COORD and r.X_COORD > 1e6 and r.Y_COORD and r.Y_COORD > 1e6:
            lon, lat = tr.transform(r.X_COORD, r.Y_COORD)
        kind = {"Retail Food": "restaurant", "Combined License": "restaurant", "Liquor": "bar", "Retail Food - Commissary": "other"}[r.LICENSE_TYPE]
        rows.append({"jur": "den", "lic": "DEN-" + r.BFN, "name": r.TRADE_NAME or r.ENTITY_NAME, "keys": _names(r.TRADE_NAME, r.ENTITY_NAME),
                     "dba": r.TRADE_NAME or None, "holder": r.ENTITY_NAME or None,
                     "addr": r.AddressNoUnit or r.ADDRESS, "city": "Denver", "zip": str(r.ZIP or "")[:5], "num": num, "street": st,
                     "lat": lat, "lon": lon, "kind": kind, "active": True, "ltype": r.LICENSE_TYPE})
    return pd.DataFrame(rows)


BOU_KIND = {"FULL SERVICE FULL MENU": "restaurant", "FAST FOOD LIMITED MENU": "restaurant", "FULL MENU LIMITED SERVICE": "restaurant",
            "BARS FRATERNAL ORGANIZATIONS": "bar", "GROCERY FINISHED FOODS": "retail", "CONVENIENCE STORES": "retail"}
BOU_OTHER = re.compile(r"\((?:MOBILE|MOBILE UNIT|COMMISSARY|CATERING|SPECIAL EVENT|SPEC EVENT|TEMP(?:ORARY)? EVENT)\)|\b(?:SCHOOL|ELEMENTARY|"
                       r"MIDDLE|HIGH SCHOOL|ACADEMY|PRESCHOOL|CHILDCARE|DAYCARE|HOSPITAL|JAIL|FOOD BANK|SENIOR)\b", re.I)


def _pt(loc):
    if isinstance(loc, dict) and loc.get("coordinates"):
        lo, la = loc["coordinates"][:2]
        if la and lo:
            return float(la), float(lo)
    return np.nan, np.nan


def load_boulder():
    """Every facility Boulder County Public Health inspected since 2024: the archive (Jan 2024-Aug 2025, typed) and the new system
    (Sep 2025-, untyped). One row per facility per system."""
    rows = []
    a = pd.DataFrame(json.load(open(f"{OFF}/boulder_archive_2023.json")))
    a = a[a.inspectiondate >= "2024-01-01"]
    for fid, g in a.groupby("facilityid"):
        r = g.iloc[0]
        la, lo = _pt(r.location)
        num, st = street_key(r.siteaddress)
        kind = BOU_KIND.get(r.categoryoffacility, "other")
        if BOU_OTHER.search(r.facilityname or ""):
            kind = "other"
        rows.append({"jur": "bou", "lic": "BOUA-" + fid, "name": r.facilityname, "keys": _names(r.facilityname), "addr": r.siteaddress,
                     "city": r.city, "zip": str(r.zip or "")[:5], "num": num, "street": st, "lat": la, "lon": lo, "kind": kind,
                     "active": g.inspectiondate.max() >= "2024-09-01", "ltype": r.categoryoffacility, "sys": "archive"})
    n = pd.DataFrame(json.load(open(f"{OFF}/boulder_2025.json")))
    for bid, g in n.groupby("business_id"):
        r = g.iloc[0]
        la, lo = _pt(r.location)
        num, st = street_key(r.address)
        rows.append({"jur": "bou", "lic": "BOU-" + bid, "name": r["name"], "keys": _names(r["name"]), "addr": r.address,
                     "city": r.b1_situs_city.title() if isinstance(r.b1_situs_city, str) else None, "zip": str(r.b1_situs_zip or "")[:5], "num": num, "street": st, "lat": la, "lon": lo,
                     "kind": "other" if BOU_OTHER.search(r["name"] or "") else "food", "active": True, "ltype": None, "sys": "new"})
    return pd.DataFrame(rows)


def load():
    df = pd.concat([load_denver(), load_liquor(), load_boulder()], ignore_index=True)
    # one business can hold several licenses (Denver's food license and the state's liquor license): same address and a name in common
    df["biz"] = np.arange(len(df))
    town = df.city.fillna("").str.upper().str.strip()
    for num, g in df[df.num.notna() & df.street.notna()].groupby("num"):
        idx = list(g.index)
        if len(idx) < 2:
            continue
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = idx[x], idx[y]
                if not street_compat(df.at[a, "street"], df.at[b, "street"]):
                    continue
                if not ((df.at[a, "zip"] and df.at[a, "zip"] == df.at[b, "zip"]) or (town[a] and town[a] == town[b])):
                    continue
                ka, kb = df.at[a, "keys"], df.at[b, "keys"]
                if not ka or not kb:
                    continue
                if any(name_sim(p, q) >= 85 or ((_stems(p) - GENERIC) & (_stems(q) - GENERIC)) for p in ka for q in kb):
                    old, new = df.at[b, "biz"], df.at[a, "biz"]
                    df.loc[df.biz == old, "biz"] = new
    return df


def boulder_inspections():
    """Boulder County's 2025-present inspections, one row per inspection (business_id + inspection date), with the official result.

    The set has one row per violation. rec_date is the record's creation (one per business, bunched at the September 2025 move to the
    new system); rec_date_1 is the inspection date. Score and result are constant within an inspection. The result is Colorado's
    inspection rating (CDPHE Interpretive Memo 19-09, under C.R.S. 25-4-1607.7(2)): Pass (0-49 risk points), Re-Inspection Required
    (50-109) or Closure (110+). Boulder's records also show Closures at 20 and 42 points, so the result is always read from the record,
    never derived from the points."""
    n = pd.DataFrame(json.load(open(f"{OFF}/boulder_2025.json")))
    n["score"] = pd.to_numeric(n.score, errors="coerce")
    ts = pd.to_datetime(n.rec_date_1)
    n["d"] = ts.dt.strftime("%Y-%m-%d")
    n["ts"] = n.rec_date_1.astype(str)
    # The county's move to its new system stamped 853 violation rows of 257 businesses 2025-09-03 15:03-15:17: that is the import, not
    # an inspection date (inspectors' notes on those rows cite dates as late as March 2026). Those records keep their result and
    # points but have no date ("nd"); they count as older than any dated inspection.
    n["nd"] = n.d.eq("2025-09-03") & ts.dt.hour.eq(15) & ts.dt.minute.le(30)
    n["code"] = n.comment.fillna("").str.extract(r"^\s*(\d-\d{3}\.\d+)")[0]
    # the section title only (e.g. "4-203.12 Temperature Measuring Devices, Ambient Air"), never the inspector's notes: titles come from the
    # comments whose first line is just the code and title, and a code without one shows as the bare code
    first = n.comment.fillna("").str.split("\n").str[0].str.strip()
    clean = first[n.comment.fillna("").str.contains("\n") & first.str.len().le(90) & n.code.notna()]
    code_title = {c: t.mode().iat[0] for c, t in clean.groupby(n.code[clean.index])}
    n["title"] = [code_title.get(c, c) if isinstance(c, str) else "" for c in n.code]
    # one row per inspection: two on one day (a routine inspection and its re-inspection) stay two, the re-inspection second
    g = n.groupby(["business_id", "ts"])
    ins = g.agg(d=("d", "first"), nd=("nd", "first"), score=("score", "first"), result=("result", "first"), typ=("g6_act_typ", "first"),
                n_items=("code", lambda s: int(s.notna().sum())), titles=("title", lambda s: list(dict.fromkeys(t for t in s if re.match(r"^\d-\d{3}", t))))).reset_index()
    ins["result"] = ins.result.replace({"Reinspection Required": "Re-Inspection Required"})
    ins["re"] = ins.typ.eq("Re-Inspection")
    # oldest first: undated import records, then by day, a routine inspection before that day's re-inspection, then by time
    return ins.sort_values(["business_id", "nd", "d", "re", "ts"], ascending=[True, False, True, True, True]).reset_index(drop=True)
