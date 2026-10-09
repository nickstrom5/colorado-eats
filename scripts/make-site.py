"""Writes the public website in docs/ from the same data file the app ships (data/app/places.json).

Pages: the landing page, six statewide guides (green chile, brewpubs, ski-town dining, game & steakhouses, MICHELIN & James Beard,
oldest places), the Boulder County inspections page, one page per big city or resort town plus a cities index, the web app
(/explore/), privacy, terms, 404, plus sitemap.xml, robots.txt and site.webmanifest. Everything listed is hand-checked research or
licensed open data; nothing comes from Google, Yelp or any ratings site, and nothing is ranked by ratings. Adapted from
wi-eats/scripts/make-site.py.

Rules the copy keeps (scripts/qa-site.py checks them):
- Every number is counted from the data here, never typed in, and no sentence claims "every" or "all N" restaurants: the lists
  are what we checked or what an official list matched, not the whole state.
- "Checked" only for the hand-checked lists (green chile, ski towns, game, oldest when every entry is hand-checked). Brewpubs are
  a state license list with its date; inspections are Boulder County's recorded results with their "through" date, never a grade.
- A place whose latest Boulder County inspection is Re-Inspection Required or Closure is never named in a title, description,
  lede or other promotional spot (the factual inspection tables still list it).
- Every page carries a hash-pinned Content-Security-Policy; inline scripts and styles are hashed after the page is final.

Usage (from co-eats/): .venv/bin/python scripts/make-site.py
Re-run it after every data rebuild, then check the pages with scripts/qa-site.py. Never hand-edit docs/*.html.
"""
import base64
import difflib
import hashlib
import html
import json
import math
import os
import re
import struct
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = f"{ROOT}/docs"
# Where the site lives. Until Nick's Cloudflare record (CNAME colorado -> nickstrom5.github.io, DNS only) resolves, GitHub Pages
# serves the project address. When `dig colorado.eatsranked.com` shows the CNAME, set CUSTOM_DOMAIN = "colorado.eatsranked.com",
# re-run and push: this writes docs/CNAME, and GitHub then forwards the old github.io links (the ones inside shipped app builds).
CUSTOM_DOMAIN = os.environ.get("CO_DOMAIN", "")
REPO = "colorado-eats"
DOMAIN = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else f"https://nickstrom5.github.io/{REPO}"
BASE = "" if CUSTOM_DOMAIN else f"/{REPO}"     # path prefix for root-relative links
BRAND = "Colorado Eats"
TAGLINE = "Green chile & brewpub guide"
EMAIL = "work-with-nick@gmail.com"
PUBLISHED = "2026-10-05"        # the site's first publication (Article datePublished)
SITE_REV = "2026-10-07"         # the last change to this generator's own copy or code: bump it when you change the words
POLICY_UPDATED = "2026-10-07"   # privacy policy and terms: bump only when their text changes
CHECKED = "fall 2026"

D = json.load(open(f"{ROOT}/data/app/places.json"))
TODAY = max(str(D.get("generated") or SITE_REV)[:10], SITE_REV)   # sitemap lastmod and dateModified move with the data or the copy
LIQUOR_DATE = D.get("liquor_updated") or ""
INS_THROUGH = D.get("inspections_through") or ""
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
CHILE, BREWPUB, GAME, SKITOWN, OLDEST, SKIDINING = 1, 2, 4, 8, 16, 32
MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"]
RESULTS = ["Pass", "Re-Inspection Required", "Closure"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
# the CDPHE retail food inspection tiers, worded as Boulder County records them (AR-15)
# Boulder County's September 2025 move to a new records system stamped hundreds of inspections 2025-09-03 (15:03-15:17): that day
# is not an inspection date, so it is never printed; the pipeline also nulls it. Dates can be missing; they read "not published".
MIGRATION_DAY = "2025-09-03"
NO_DATE = "Date not published"
NO_DATE_NOTE = ("“Not published” in the Date column marks results Boulder County recorded during its September 2025 move to a new records system, "
                "which carry no real inspection date.")


def ins_date(d):
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(d or ""))
    return m[0] if m and not m[0].startswith(MIGRATION_DAY) else None


def clean_ins(i):
    """An inspection record with only real dates left in it (None where the county published none)."""
    if not isinstance(i, dict):
        return None
    out = dict(i)
    out["d"] = ins_date(i.get("d"))
    out["h"] = [dict(h, d=ins_date(h.get("d"))) for h in (i.get("h") or []) if isinstance(h, dict)]
    return out


TIERS = ("Pass (0–49 risk points), Re-Inspection Required (50–109) or Closure (110+ points). Boulder County also records a Closure when "
         "it closes a place for an imminent health hazard, such as a sewage backup, whatever the points. Fewer points is better.")


def hdate(iso):
    """2026-09-24 -> September 24, 2026"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {int(m[3])}, {m[1]}" if m else str(iso or "")


def hdate_short(iso):
    """2026-10-23 -> Oct 23, 2026 (tables on phones)"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1][:3]} {int(m[3])}, {m[1]}" if m else str(iso or "")


def hmonth(iso):
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(iso or "")


def plural(n, one, many=None):
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def words_num(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else f"{n:,}"


def safe_url(u):
    """Only http(s) links leave the site; a bare host ("example.com/menu") gets https://. Anything else is dropped."""
    u = str(u or "").strip()
    if re.fullmatch(r"https?://[^\s\"'<>\\]+", u, re.I):
        return u
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?:[/?#][^\s\"'<>\\]*)?", u, re.I):
        return "https://" + u
    return ""


class P:
    """One place, with the same meaning the app gives each field (ColoradoEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = str(r["n"])
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]].replace(" County", "") if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = r.get("a") or ""
        self.zip = str(r.get("z") or "")
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.ip = r.get("ip")
        self.founded = r.get("f") if isinstance(r.get("f"), int) else None
        self.fn = r.get("fn") or ""
        self.dishes = (r.get("dish") or "").replace("; ", ", ")
        self.season = r.get("seas") or ""
        self.note = r.get("note") or ""
        self.site = safe_url(r.get("w"))
        self.jbf = r.get("jbf") or ""
        self.h = r.get("h") or 0
        self.mi = r.get("mi") if r.get("mi") in range(1, len(MI)) else 0
        self.liq = r.get("liq") or ""
        self.hc = r.get("hc") == 1   # hand-checked in fall 2026 against a 2025-26 source; the only places the checked guides list
        ins = clean_ins(r.get("in"))
        self.ins = ins if ins and ins.get("r") in (0, 1, 2) else None
        self.brewpub = bool(self.tags & BREWPUB)   # cleared below for a duplicate holder of a shared license

    def featured_key(self):
        # the app's "Featured first": honored places, then documented founding year, then name
        return (-(self.ip if self.ip is not None else -1), self.founded or 9999, self.name.lower())

    def jb_label(self):
        return ("America's Classic" if self.h & 1 else "James Beard winner" if self.h & 2 else "James Beard finalist" if self.h & 4
                else "James Beard semifinalist" if self.h & 8 else None)

    def promo_ok(self):
        """Never name a place with a Re-Inspection Required or Closure on record in a title, description or hero."""
        return not (self.ins and self.ins.get("r") in (1, 2))


PLACES = [P(r) for r in D["places"]]
REST = [p for p in PLACES if not p.venue]

# ---------------------------------------------------------------- brewpubs: one place per state license
# The pipeline can attach one Brew Pub license to two or three listings at an address (a twin listing, an owner's entity name).
# Keep one holder per license id: the best match to the license's trade name when we have it (the place's license entry, or the
# state's list on disk), otherwise the first listing.
BREW_TYPES = ("Brew Pub", "Distillery Pub")


def brew_lics(p):
    return [l for l in (p.r.get("lic") or []) if str(l.get("type", "")).startswith(BREW_TYPES) and l.get("id")]


DBA = {}
_raw = f"{ROOT}/data/raw/official/liquor_active.json"
if os.path.exists(_raw):
    for x in json.load(open(_raw)):
        if str(x.get("license_type", "")).startswith(BREW_TYPES):
            DBA[str(x.get("license_number"))] = x.get("doing_business_as") or ""


def _norm(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", str(s).lower().replace("&", " and ").replace("'", ""))
    return " ".join(w for w in s.split() if w not in {"the", "and", "llc", "inc", "co", "company", "corp", "ltd"})


def name_match(p, lic):
    dba = lic.get("dba") or lic.get("name") or DBA.get(str(lic.get("id"))) or ""
    if not dba:
        return 0.0
    a, b = _norm(p.name), _norm(dba)
    overlap = len(set(a.split()) & set(b.split())) / max(1, len(set(b.split())))
    return max(difflib.SequenceMatcher(None, a, b).ratio(), overlap)


_holders = defaultdict(list)
for p in REST:
    if p.brewpub:
        for l in brew_lics(p):
            _holders[str(l["id"])].append((p, l))
_winners = set()
for lid, hs in _holders.items():
    best = max(hs, key=lambda pl: name_match(*pl))   # max keeps the first on a tie (no trade name: the first listing)
    _winners.add(id(best[0]))
for p in REST:
    if p.brewpub and brew_lics(p) and id(p) not in _winners:
        p.brewpub = False   # its license is shown on the better-matched listing
N_BREW_DROPPED = sum(1 for p in REST if p.tags & BREWPUB and not p.brewpub)
# total active Brew Pub + Distillery Pub licenses, if the pipeline records it (then the copy can say "matched to the state's N")
_lic_total = D.get("brewpub_licenses", D.get("n_brewpub_licenses"))
N_BREW_LICENSES = _lic_total if isinstance(_lic_total, int) and _lic_total > 0 else None

CHILE_L = sorted([p for p in REST if p.hc and p.tags & CHILE], key=P.featured_key)
BREW_L = sorted([p for p in REST if p.brewpub], key=lambda p: (p.city, p.name.lower()))
SKI_L = sorted([p for p in REST if p.hc and p.tags & SKIDINING], key=P.featured_key)
GAME_L = sorted([p for p in REST if p.hc and p.tags & GAME], key=P.featured_key)
HON_L = sorted([p for p in REST if p.mi or p.jbf], key=P.featured_key)
OLD_L = sorted([p for p in REST if p.founded], key=lambda p: (p.founded, p.name.lower()))
OLD_ALL_HC = bool(OLD_L) and all(p.hc for p in OLD_L)
INS_L = sorted([p for p in REST if p.ins and p.county == "Boulder"], key=lambda p: (p.city, p.name.lower(), p.addr))

# ---------------------------------------------------------------- regions (by county; all 64 counties)
REGIONS = {
    "Denver": "Denver",
    "Denver suburbs": "Adams Arapahoe Jefferson Douglas Broomfield",
    "Boulder and the northern Front Range": "Boulder Larimer Weld",
    "Colorado Springs and Pueblo": "El_Paso Teller Pueblo Fremont Custer",
    "Mountain towns": "Pitkin Eagle Summit Routt Grand Gunnison San_Miguel Clear_Creek Gilpin Lake Park Chaffee Jackson",
    "Western Slope": "Mesa Garfield Delta Montrose Ouray Moffat Rio_Blanco",
    "Southwest Colorado": "La_Plata Montezuma Archuleta San_Juan Dolores Hinsdale Mineral",
    "San Luis Valley and the south": "Alamosa Rio_Grande Saguache Conejos Costilla Huerfano Las_Animas",
    "Eastern Plains": "Morgan Logan Sedgwick Phillips Yuma Washington Kit_Carson Lincoln Elbert Cheyenne Kiowa Crowley Otero Bent Prowers Baca",
}
REGION_OF = {c.replace("_", " "): r for r, cs in REGIONS.items() for c in cs.split()}
assert len(REGION_OF) == 64, len(REGION_OF)
for p in PLACES:
    p.region = REGION_OF.get(p.county) if p.county else None


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- html helpers
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def join_words(xs, conj="and"):
    xs = [x for x in xs if x]
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + f" {conj} " + xs[-1]


def first_fit(cands, lo, hi, what=""):
    seen = []
    for o in cands:
        if lo <= len(o) <= hi:
            return o
        seen.append(o)
    raise ValueError(f"nothing fits {lo}-{hi} for {what}: {[(len(o), o) for o in seen[:12]]}")


fit = first_fit

# the app icon in miniature: a Pueblo green chile lying level on flag blue (redrawn 2026-10-09 in the shared Eats Ranked style; the clip keeps the darker underside inside the pod)
LOGO = '<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><defs><clipPath id="co-pod"><path d="M16.6 22.1 C27.5 22.1 40.0 23.2 54.5 37.6 A2.94 2.94 0 0 1 51.8 42.6 C38.0 39.7 35.8 47.7 16.6 47.7 C11.5 47.7 8.6 43.1 8.6 34.9 C8.6 26.8 11.5 22.1 16.6 22.1Z"/></clipPath></defs><rect width="64" height="64" rx="14" fill="#002868"/><path d="M16.6 22.1 C27.5 22.1 40.0 23.2 54.5 37.6 A2.94 2.94 0 0 1 51.8 42.6 C38.0 39.7 35.8 47.7 16.6 47.7 C11.5 47.7 8.6 43.1 8.6 34.9 C8.6 26.8 11.5 22.1 16.6 22.1Z" fill="#4E9A2E"/><path d="M-0.7 38.8 L16.6 38.8 C32.9 38.8 38.7 33.9 52.7 40.9 L64.2 46.6 L60.7 63.7 L-0.7 63.7Z" fill="#3A7A21" clip-path="url(#co-pod)"/><path d="M13.0 22.1 C12.2 19.9 10.8 18.6 11.7 16.1 C12.7 13.8 16.2 13.2 17.8 14.8" stroke="#5A8A2A" stroke-width="2.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M17.9 22.4 C14.7 18.6 8.8 20.5 8.8 29.2 C9.5 32.1 12.2 31.1 13.5 26.0 C14.8 30.5 17.5 25.0 17.9 22.4Z" fill="#2F5E1A"/></svg>'
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

CSS = """
  :root {
    --bg: #f7f8fb; --surface: #fff; --surface2: #eef1f7; --rule: #dde2ec;
    --ink: #0f1b33; --ink2: #2a3a5a; --muted: #55627a;
    --green: #002868; --green2: #1c3f86; --on-green: #fff; --gold: #ffd700; --goldsoft: #fff1a6; --red: #bf0a30;
    --focus: #002868;
    --radius: 16px;
    --display: "Avenir Next Condensed", "HelveticaNeue-CondensedBold", "Arial Narrow", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0d1424; --surface: #141d31; --surface2: #1b2640; --rule: #2a3654; --ink: #eef1f8; --ink2: #cfd6e6; --muted: #9aa6bf; --green: #a9c1ff; --green2: #8aa8f0; --on-green: #0d1424; --red: #ff6b86; --focus: #ffd700; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--green); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible, select:focus-visible, input:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
  .skip { position: absolute; left: -9999px; top: 0; background: var(--gold); color: #0f1b33; padding: 10px 14px; font-weight: 700; z-index: 10; }
  .skip:focus { left: 8px; top: 8px; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
  header.site { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 0; border-bottom: 4px solid var(--gold); box-shadow: 0 3px 0 var(--red); }
  .logo { display: flex; align-items: center; gap: 10px; font: 800 22px/1 var(--display); text-transform: uppercase; letter-spacing: .01em; color: var(--green); text-decoration: none; }
  header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; justify-content: flex-end; }
  header.site nav a { color: var(--ink2); text-decoration: none; font-size: 15px; }
  header.site nav a:hover { color: var(--green); text-decoration: underline; }
  h1, h2 { font-family: var(--display); font-weight: 800; color: var(--green); letter-spacing: -.005em; }
  h1 { font-size: clamp(36px, 7.5vw, 56px); line-height: 1.02; margin: 0 0 16px; text-transform: uppercase; }
  .kicker { font: 700 15px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 0 0 12px; }
  h2 { font-size: 32px; line-height: 1.1; margin: 0 0 10px; }
  h3 { font-size: 18px; margin: 0; line-height: 1.3; }
  .lede { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
  .hero { padding: 44px 0 28px; }
  section { padding: 36px 0; border-top: 1px solid var(--rule); }
  section.hero { border: 0; }
  .sub { color: var(--ink2); margin: 0 0 22px; }
  .cta-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 10px; background: var(--gold); color: #0f1b33; font-weight: 700; padding: 14px 20px; border-radius: 14px; text-decoration: none; font-size: 17px; }
  .btn svg { width: 22px; height: 22px; }
  .btn-ghost { background: transparent; color: var(--green); border: 2px solid var(--green); }
  .pill { font-size: 14px; color: var(--muted); }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .stats li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px; }
  .stats b { display: block; font: 800 30px/1 var(--display); color: var(--green); }
  .stats span { font-size: 14px; color: var(--muted); }
  .steps { display: grid; gap: 12px; list-style: none; margin: 0; padding: 0; }
  .step { display: flex; gap: 14px; background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .step .n { flex: 0 0 32px; height: 32px; border-radius: 50%; background: var(--gold); color: #0f1b33; font-weight: 800; display: grid; place-items: center; }
  .step p { margin: 4px 0 0; color: var(--ink2); }
  .shots { display: flex; gap: 14px; overflow-x: auto; margin: 0 -20px; padding: 4px 20px 14px; scroll-snap-type: x proximity; list-style: none; }
  .shots li { flex: 0 0 auto; width: 210px; scroll-snap-align: start; }
  .shots img { display: block; width: 210px; height: auto; border-radius: 24px; border: 1px solid var(--rule); background: var(--surface2); }
  .shots p { font-size: 14px; color: var(--muted); margin: 8px 2px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .card p { margin: 6px 0 0; color: var(--ink2); }
  a.card { display: block; text-decoration: none; color: var(--ink); }
  a.card:hover h3 { text-decoration: underline; color: var(--green); }
  .cities { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }
  .cities a { display: inline-block; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--rule); background: var(--surface); text-decoration: none; color: var(--ink); font-size: 15px; }
  .cities a:hover { border-color: var(--green); }
  .cities a[aria-current] { border-color: var(--green); font-weight: 700; }
  details { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 2px 18px; margin-bottom: 10px; }
  summary { cursor: pointer; padding: 14px 0; font-weight: 600; list-style: none; display: flex; justify-content: space-between; gap: 12px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "+"; color: var(--green); font-weight: 800; }
  details[open] summary::after { content: "\\2013"; }
  details p { margin: 0 0 16px; color: var(--ink2); }
  .final { text-align: center; }
  .final .cta-row { justify-content: center; }
  nav.crumbs { font-size: 14px; color: var(--muted); padding: 16px 0 0; }
  nav.crumbs ol { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  nav.crumbs li + li::before { content: "/"; margin-right: 6px; color: var(--rule); }
  nav.crumbs a { color: var(--muted); }
  .places { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; scroll-margin-top: 12px; }
  .places li:target { border-color: var(--green); box-shadow: 0 0 0 2px var(--green); }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .fine { margin: 6px 0 0; }
  .places .link { font-size: 14px; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--goldsoft); color: #0f1b33; border-radius: 6px; padding: 1px 6px; margin-right: 4px; }
  .tag-mi { background: #bf0a30; color: #fff; }
  .tag-jb { background: #002868; color: #fff; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .tbl { overflow-x: auto; }
  .tbl th[scope=row] { font-weight: 600; overflow-wrap: anywhere; }
  .tbl .addr { display: block; font-size: 13px; font-weight: 400; color: var(--muted); }
  .res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 2px 6px; border-radius: 6px; }
  .res-0 { background: #ddefe3; color: #0e5a2b; } .res-1 { background: #ffe9c2; color: #6b3a00; } .res-2 { background: #f9d5db; color: #7a0019; }
  .fine { font-size: 14px; color: var(--muted); }
  .legal h2 { font-size: 26px; margin-top: 28px; }
  .legal p, .legal li { color: var(--ink2); }
  footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--rule); margin-top: 20px; }
  footer nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
  footer a { color: var(--muted); }
  footer p { margin: 12px 0 0; }
  @media (max-width: 600px) {
    .grid2 { grid-template-columns: 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .toc { columns: 1; }
    header.site { flex-direction: column; align-items: flex-start; }
    header.site nav { justify-content: flex-start; }
    header.site nav a, footer nav a, nav.crumbs a { display: inline-block; padding: 10px 0; }
    footer nav { gap: 0 18px; }
    th, td { padding: 8px 4px; font-size: 14px; }
    .tbl th, .tbl td { padding: 8px 3px; font-size: 13px; }
    .res { font-size: 11px; letter-spacing: .02em; padding: 2px 4px; }
    nav.crumbs ol { align-items: center; }
  }
"""


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    raw = json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
    return '<script type="application/ld+json">\n' + raw.replace("<", "\\u003c") + "\n</script>"   # a "</script>" in a name can't break out


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Get early access"):
    # A plain mailto button until launch: no Apple logo (Apple's marketing rules allow it only in the official badge). When
    # APP_STORE_URL is set in page() below, swap this for Apple's "Download on the App Store" badge artwork.
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=Colorado%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'<span class="store-label">{label}</span></a>')


STORE_NOTE = "Free iPhone and iPad app, coming soon to the App Store."


def sha256_src(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def csp_for(doc):
    """A strict policy for one finished page: only its own inline <script>/<style> blocks (by hash), same-origin data and images."""
    scripts = re.findall(r"<script>(.*?)</script>", doc, re.S)          # executable inline scripts (JSON-LD blocks are data, not run)
    styles = re.findall(r"<style>(.*?)</style>", doc, re.S)
    return ("default-src 'none'; "
            f"script-src {' '.join(sha256_src(s) for s in scripts) or chr(39) + 'none' + chr(39)}; "
            f"style-src {' '.join(sha256_src(s) for s in styles) or chr(39) + 'none' + chr(39)}; "
            "img-src 'self' data:; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'")


CSP_SLOT = "__CSP__"
written, noindexed = [], []


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css="", og_type="article"):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    assert 'style="' not in body, f"{path}: inline style attributes break the CSP"
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    indexed = "noindex" not in robots
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. Colorado restaurants, with hand-checked green chile, ski-town dining and the state's oldest places."
    ld = "\n".join(jsonld(x) for x in lds)
    canon = f'<link rel="canonical" href="{url}">\n' if indexed else ""
    og_url = f'<meta property="og:url" content="{url}">\n' if indexed else ""
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP_SLOT}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}<meta name="robots" content="{robots}">
<meta name="theme-color" content="#002868">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
{og_url}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{DOMAIN}/og.png">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}{extra_css}</style>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  <header class="site">
    <a class="logo" href="/" aria-label="{BRAND} home">{LOGO}{BRAND}</a>
    <nav aria-label="Main">
      <a href="/colorado-green-chile.html">Green chile</a>
      <a href="/colorado-brewpubs.html">Brewpubs</a>
      <a href="/colorado-ski-town-restaurants.html">Ski towns</a>
      <a href="/cities/">Cities</a>
      <a href="/explore/">Search</a>
    </nav>
  </header>
{body}
  <footer>
    <nav aria-label="Footer">
      <a href="/">{BRAND} app</a>
      <a href="/explore/">Search Colorado restaurants</a>
      <a href="/colorado-green-chile.html">Colorado green chile</a>
      <a href="/colorado-brewpubs.html">Colorado brewpubs</a>
      <a href="/colorado-ski-town-restaurants.html">Ski town dining</a>
      <a href="/colorado-game-steakhouses.html">Game &amp; steakhouses</a>
      <a href="/colorado-michelin-james-beard.html">MICHELIN &amp; James Beard</a>
      <a href="/colorado-oldest-restaurants.html">Oldest restaurants</a>
      <a href="/{INS_PATH}">Boulder County inspections</a>
      <a href="/cities/">Cities and towns</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>{SOURCES_LINE}</p>
    <p>© 2026 {BRAND}.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Get early access" to "Download on the App Store" automatically (then use Apple's badge artwork,
  // see store_button() in scripts/make-site.py). Also fill in the apple-itunes-app meta tag in <head> on every page, and put the
  // MobileApplication "offers" back in the landing page's JSON-LD (re-run scripts/make-site.py after editing it there).
  var APP_STORE_URL = "";
  if (APP_STORE_URL) {{
    document.querySelectorAll(".store-btn").forEach(function (b) {{ b.href = APP_STORE_URL; b.rel = "noopener"; }});
    document.querySelectorAll(".store-label").forEach(function (l) {{ l.textContent = "Download on the App Store"; }});
    document.querySelectorAll(".store-note").forEach(function (n) {{ n.textContent = "Free for iPhone and iPad."; }});
  }}
</script>
</body>
</html>
"""
    if BASE:   # served under /colorado-eats/: every root-relative link and asset gets the prefix
        doc = re.sub(r'(href|src|srcset)="/', rf'\1="{BASE}/', doc)
    doc = doc.replace(CSP_SLOT, csp_for(doc), 1)   # hashed last, over the exact bytes the browser will see
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    (written if indexed else noindexed).append(path)
    return path


class Anchors:
    """Gives each place an id (name-zip) the first time it appears on a page, so ItemList items can point to page#id."""
    RESERVED = {"main", "about", "list", "green-chile", "ski", "honors", "brewpubs", "game", "oldest", "inspections", "cuisines", "more",
                "towns", "how", "what", "guides", "cities", "faq", "download", "screens", "pricing", "privacy", "tiers"}

    def __init__(self, page_url):
        self.page_url, self.used, self.of = page_url, set(self.RESERVED), {}

    def take(self, p):
        if id(p) in self.of:
            return None
        base = slug(p.name + (" " + p.zip if p.zip else "")) or "place"
        a, n = base, 2
        while a in self.used:
            a, n = f"{base}-{n}", n + 1
        self.used.add(a)
        self.of[id(p)] = a
        return a

    def url(self, p):
        return f"{self.page_url}#{self.of[id(p)]}"


def place_item(p, anchors=None, extra=None, show_fn=False, honors=False):
    facts = []
    if p.dishes:
        facts.append(f"<b>On the menu:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {e(str(p.founded))}")
    if p.season:
        facts.append(f"<b>Season:</b> {e(p.season)}")
    kinds = []
    if p.mi:
        kinds.append(('<span class="tag tag-mi">', e(MI[p.mi])))
    if p.jb_label():
        kinds.append(('<span class="tag tag-jb">', e(p.jb_label())))
    for ok, k in ((p.tags & CHILE and p.hc, "Green chile"), (p.brewpub, "Brewpub"), (p.tags & GAME and p.hc, "Game &amp; steak")):
        if ok:
            kinds.append(('<span class="tag">', k))
    where = ", ".join(x for x in (p.addr, p.city) if x)
    if extra:
        where += f" · {extra}"
    aid = anchors.take(p) if anchors else None
    out = [f'<li id="{e(aid)}">' if aid else "<li>", f"<h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f"{tag}{k}</span>" for tag, k in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if show_fn and p.fn:
        out.append(f'<p class="fine">{e(p.fn)}</p>')
    if honors and p.jbf:   # restaurateur-level honors have no chip, so say what the honor is
        out.append('<p class="fine">' + e("; ".join("James Beard: " + x for x in p.jbf.split("; "))) + "</p>")
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site, flags=re.I).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p, item_url):
    addr = {"@type": "PostalAddress"}
    if p.addr:
        addr["streetAddress"] = p.addr
    if p.city:
        addr["addressLocality"] = p.city
    addr["addressRegion"] = "CO"
    if p.zip:
        addr["postalCode"] = p.zip
    addr["addressCountry"] = "US"
    x = {"@type": "Restaurant", "name": p.name, "url": item_url, "address": addr}
    if p.lat is not None and p.lon is not None:
        x["geo"] = {"@type": "GeoCoordinates", "latitude": p.lat, "longitude": p.lon}
    if p.site:
        x["sameAs"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("Other", "Restaurant", "American & Other"):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url, anchors):
    """An all-on-one-page list: each item's url is its anchor on this page; the restaurant's own site goes in sameAs."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p, anchors.url(p))} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": PUBLISHED, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/", "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png"}}}


# ---------------------------------------------------------------- counts shared by several pages
N_REST = len(REST)
N_TOWNS = len({p.city for p in REST if p.city})
N_COUNTIES = len({p.county for p in REST if p.county})
DISH_WORDS = Counter()
for p in CHILE_L:
    for d in {x.strip().lower() for x in p.dishes.split(",") if x.strip()}:
        DISH_WORDS[d] += 1
N_SLOPPER = sum(1 for p in CHILE_L if "slopper" in p.dishes.lower())
N_PUEBLO_CHILE = sum(1 for p in CHILE_L if p.county == "Pueblo")
BREW_TOWNS = Counter(p.city for p in BREW_L)
MI_COUNT = Counter(MI[p.mi] for p in HON_L if p.mi)
MI_N = Counter(p.mi for p in HON_L if p.mi)
N_JBF = sum(1 for p in HON_L if p.jbf)
INS_PATH = "boulder-county-restaurant-inspections.html"
INS_RES = Counter(p.ins["r"] for p in INS_L)

SOURCES_LINE = (f"Place data: hand-checked research by {BRAND} ({CHECKED}); Overture Maps Foundation places (CDLA Permissive 2.0) and addresses "
                "(open address sources under permissive licenses, docs.overturemaps.org/attribution); © OpenStreetMap contributors (ODbL); "
                "U.S. Census Bureau Geocoder (public domain); Colorado Department of Revenue liquor licenses and Boulder County Public Health "
                "inspections (data.colorado.gov, public domain); City and County of Denver Open Data. Not affiliated with or endorsed by any "
                "restaurant, team, chain or government agency, the MICHELIN Guide or the James Beard Foundation. MICHELIN and the MICHELIN Guide "
                "are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Places "
                "open and close, so check before you go.")


def by_region(places, key=lambda p: (p.city, p.name.lower())):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere in Colorado"].append(p)
    order = list(REGIONS) + ["Elsewhere in Colorado"]
    return [(r, sorted(groups[r], key=key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural_noun, anchors, **item_kw):
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        anchors.used.update({slug(r), "h-" + slug(r)})
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{plural(len(ps), noun, plural_noun)}, by town.</p><ol class="places">'
                    + "".join(place_item(p, anchors, **item_kw) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


CITY_WANTED = ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Boulder", "Pueblo", "Lakewood", "Longmont", "Greeley", "Golden",
               "Grand Junction", "Durango", "Aspen", "Breckenridge", "Steamboat Springs", "Vail"]
CITY_PAGES = [c for c in CITY_WANTED if any(p.city == c and p.lat is not None for p in REST)]   # a town the data lost gets no page


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links(current=None):
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}"{" aria-current=" + chr(34) + "page" + chr(34) if c == current else ""}>{e(c)}</a></li>'
                                           for c in CITY_PAGES) + "</ul>"


GUIDE_LINKS = [("/colorado-green-chile.html", "Colorado green chile guide"), ("/colorado-brewpubs.html", "Colorado brewpubs"),
               ("/colorado-ski-town-restaurants.html", "Ski town dining"), ("/colorado-game-steakhouses.html", "Colorado game & steakhouses"),
               ("/colorado-michelin-james-beard.html", "MICHELIN & James Beard restaurants"), ("/colorado-oldest-restaurants.html", "Oldest restaurants"),
               ("/" + INS_PATH, "Boulder County restaurant inspections")]


def other_guides(skip):
    return "Other guides: " + ", ".join(f'<a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS if u != skip) + "."


def guide_page(path, h1, kicker, title_opts, desc_opts, lede, about_html, places, noun, plural_noun, list_name, region=True, **item_kw):
    url = f"{DOMAIN}/{path}"
    title, desc = fit(title_opts, 50, 60, path + " title"), fit(desc_opts, 140, 160, path + " description")
    nav, bc = crumbs([("Home", "/"), (h1, "/" + path)])
    anchors = Anchors(url)
    if region:
        toc, secs = region_sections(places, noun, plural_noun, anchors, **item_kw)
        jump = f"<h2>Jump to a region</h2>\n    {toc}"
    else:
        secs = (f'<section id="list" aria-labelledby="h-list"><h2 id="h-list">Oldest first</h2><ol class="places">'
                f'{"".join(place_item(p, anchors, **item_kw) for p in places)}</ol></section>')
        jump = ""
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{kicker}</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>
  <section id="about">
    {about_html}
    <p class="fine">{other_guides("/" + path)} City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
    {jump}
  </section>
{secs}
  </main>"""
    page(path, title, desc, body, [article_ld(url, h1, desc), bc, item_list(list_name, places, url, anchors)])


def towns_text(counter, k):
    return ", ".join(t for t, _ in counter.most_common(k))


# ---------------------------------------------------------------- green chile
top_dish = ", ".join(f"{d} ({n})" for d, n in DISH_WORDS.most_common(6))
slop = ", Pueblo sloppers" if N_SLOPPER else ""
guide_page("colorado-green-chile.html", "Colorado green chile guide", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Green Chile Guide: {len(CHILE_L)} Checked Places | {BRAND}", f"Colorado Green Chile: {len(CHILE_L)} Checked Places | {BRAND}",
            f"Colorado Green Chile Guide: {len(CHILE_L)} Hand-Checked Places"]
           + ([f"Colorado Green Chile Guide: {len(CHILE_L)} Places & Pueblo Sloppers"] if N_SLOPPER else []),
           [f"{plural(len(CHILE_L), 'Colorado green chile spot')}, checked in {CHECKED} against a 2025–26 source: smothered burritos, breakfast burritos{slop} and chile by the bowl.",
            f"{plural(len(CHILE_L), 'Colorado green chile spot')} checked in {CHECKED}: smothered burritos, breakfast burritos{slop} and chile by the bowl, by region.",
            f"{plural(len(CHILE_L), 'Colorado place')} for green chile, checked in {CHECKED}: smothered and breakfast burritos{slop}, chile by the bowl. By region and town.",
            f"{plural(len(CHILE_L), 'Colorado place')} for green chile, hand-checked in {CHECKED}: smothered burritos, breakfast burritos and chile by the bowl, listed by region and town."],
           f"{plural(len(CHILE_L), 'restaurant')}, diners and taverns across Colorado known for green chile, each checked in {CHECKED} against a 2025–26 source: its own menu or recent local news. For each one: what's on the menu, and how long it's been at this address when that's documented.",
           f"""<h2>Colorado green chile, briefly</h2>
    <p>Colorado green chile is a pork-and-roasted-pepper stew, thicker and often hotter than New Mexico's, ladled over almost everything: smothered burritos, breakfast burritos, chile rellenos and fries. In Pueblo it tops a hamburger in a bowl, the slopper. Peppers come from Pueblo and the San Luis Valley, and late summer smells like chile roasters outside grocery stores.</p>
    <h2>What's on the list</h2>
    <p>{N_PUEBLO_CHILE:,} of the {len(CHILE_L):,} are in Pueblo County, and {N_SLOPPER:,} serve a slopper. The dishes we found most often: {e(top_dish)}.</p>
    <p>How the list was built: each place was checked against a 2025 or 2026 source, such as its own menu page or a dated local news story. Places with no current source, a dead website or green chile only mentioned in passing were left out. Nothing here comes from review sites, and the order is by region and town, not by anyone's rating. Menus change, so check before you go.</p>
    <p>In the {BRAND} app, the same list sorts by distance from you, and each place opens Apple Maps' own card for live hours, photos and directions.</p>""",
           CHILE_L, "green chile spot", "green chile spots", "Colorado green chile restaurants")

# ---------------------------------------------------------------- brewpubs
top_brew = ", ".join(f"{c} ({n})" for c, n in BREW_TOWNS.most_common(6))
NB = len(BREW_L)
LIQ = hdate(LIQUOR_DATE)
if N_BREW_LICENSES:
    brew_lede = (f"{plural(NB, 'place')} matched to the state's {N_BREW_LICENSES:,} active Brew Pub and Distillery Pub licenses (the list of {LIQ}). "
                 "A Brew Pub license lets a restaurant brew beer on site and serve it with food; a Distillery Pub license does the same for spirits.")
    brew_desc = [f"{plural(NB, 'Colorado place')} matched to the state's {N_BREW_LICENSES:,} active Brew Pub and Distillery Pub licenses, beer or spirits made on site, by region and town."]
else:
    brew_lede = (f"{plural(NB, 'place')} with a state Brew Pub or Distillery Pub license, from the state's active license list of {LIQ}, matched to their "
                 "addresses. A Brew Pub license lets a restaurant brew beer on site and serve it with food; a Distillery Pub license does the same for spirits.")
    brew_desc = []
brew_desc += [f"{plural(NB, 'Colorado place')} with a state Brew Pub or Distillery Pub license, where beer or spirits are made on site, by region and town. Licenses as of {hmonth(LIQUOR_DATE)}.",
              f"{plural(NB, 'Colorado place')} with a state Brew Pub or Distillery Pub license, where the beer or spirits are made on site, listed by region and town.",
              f"{plural(NB, 'Colorado place')} holding a state Brew Pub or Distillery Pub license, making beer or spirits on site, by region and town. State list of {hmonth(LIQUOR_DATE)}."]
guide_page("colorado-brewpubs.html", "Colorado brewpubs", f"{BRAND} guide · state licenses as of {e(LIQ)}",
           [f"Colorado Brewpubs: {NB} Licensed Brewpubs by Town | {BRAND}", f"Colorado Brewpubs: {NB} Licensed by Town | {BRAND}",
            f"Colorado Brewpubs by Town: {NB} Licensed Places | {BRAND}", f"Colorado Brewpubs: {NB} Places with a Brew Pub License"],
           brew_desc, brew_lede,
           f"""<h2>What a brewpub license means</h2>
    <p>Colorado's Liquor Enforcement Division issues a Brew Pub license to a restaurant that brews its own beer on the premises, and a Distillery Pub license to one that distills. That's different from a production brewery's taproom, which holds a manufacturer license and doesn't have to serve food. So this list is the brewpubs in the legal sense: places to eat where the beer is made in house.</p>
    <p>The towns with the most: {e(top_brew)}.</p>
    <p>How the list was built: from the Colorado Department of Revenue's list of active liquor licenses on data.colorado.gov ({e(LIQ)}), matched to each place's map listing by name and street address. A license that matched two listings at one address is shown once, on the listing whose name matches the license. A licensed brewpub can be missing when its address couldn't be matched to a listing. The order is by region and town.</p>""",
           BREW_L, "brewpub", "brewpubs", "Colorado brewpubs")

# ---------------------------------------------------------------- ski towns
ski_towns = Counter(p.city for p in SKI_L)
ski_opts = []
for k in (5, 4, 3, 2):
    t = towns_text(ski_towns, k)
    ski_opts += [f"{plural(len(SKI_L), 'restaurant')} in {t} and other Colorado ski towns, checked in {CHECKED}, with seasonal hours noted.",
                 f"{plural(len(SKI_L), 'Colorado ski town restaurant')} in {t} and more, checked in {CHECKED}, seasons noted, by region and town."]
guide_page("colorado-ski-town-restaurants.html", "Colorado ski town restaurants", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Ski Town Restaurants: {len(SKI_L)} Checked Places | {BRAND}", f"Colorado Ski Town Dining: {len(SKI_L)} Places | {BRAND}",
            f"Colorado Ski Town Restaurants: {len(SKI_L)} Checked Places"],
           ski_opts,
           f"{plural(len(SKI_L), 'restaurant')} in Colorado's ski towns, from slopeside lodges to downtown institutions, each checked in {CHECKED} against a 2025–26 source. On-mountain places that only open in winter are marked.",
           f"""<h2>Eating in the mountains</h2>
    <p>Colorado's resort towns have more good restaurants per resident than anywhere else in the state, and many keep their own schedule: on-mountain lodges open only in ski season, and lots of town restaurants close for a few weeks of "mud season" in spring and fall. Those closures are not permanent, and the list marks seasonal places when they say so.</p>
    <p>By town: {e(", ".join(f"{c} ({n})" for c, n in ski_towns.most_common(10)))}.</p>
    <p>How the list was built: each place was checked against a 2025 or 2026 source, usually its own site or menu or a dated story in the local paper. Places with no current source were left out. MICHELIN Guide Colorado restaurants in these towns are included. The order is by region and town, never by rating.</p>""",
           SKI_L, "restaurant", "restaurants", "Colorado ski town restaurants")

# ---------------------------------------------------------------- game & steakhouses
buck = next((p for p in GAME_L if p.name.lower().startswith("buckhorn exchange") and p.promo_ok()), None)
from_buck = f"from the {buck.name} to mountain-town lodges" if buck else "from Denver steakhouses to mountain-town lodges"
guide_page("colorado-game-steakhouses.html", "Colorado game & steakhouses", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Steakhouses & Game: {len(GAME_L)} Checked Places | {BRAND}", f"Colorado Bison, Elk & Steakhouses: {len(GAME_L)} Places",
            f"Colorado Game & Steakhouses: {len(GAME_L)} Places | {BRAND}"],
           [f"{plural(len(GAME_L), 'Colorado restaurant')} serving bison, elk, trout and steak, checked in {CHECKED}, {from_buck}, by region.",
            f"{plural(len(GAME_L), 'Colorado place')} for bison, elk, trout and steak, checked in {CHECKED}, {from_buck}, by region and town.",
            f"{plural(len(GAME_L), 'Colorado place')} for bison, elk, venison, trout and steak, each checked in {CHECKED} against a 2025–26 menu or news source, by region and town."],
           f"{plural(len(GAME_L), 'restaurant')} with bison, elk, venison, trout or a classic steakhouse menu, each checked in {CHECKED} against a 2025–26 source: its menu or recent local news.",
           f"""<h2>Colorado on the plate</h2>
    <p>Bison and elk ranch across the state, Rocky Mountain trout comes out of its rivers, and steakhouses have fed Denver since the stockyards. The dishes listed with each place are from its current menu when we checked.</p>
    <p>How the list was built: each place was checked against a 2025 or 2026 source. Menus change with the season, so check before you go. The order is by region and town, never by rating.</p>""",
           GAME_L, "place", "places", "Colorado game and steakhouse restaurants")

# ---------------------------------------------------------------- MICHELIN & James Beard
MI_SHORT = {5: "3-Star", 4: "2-Star", 3: "1-Star", 2: "Bib Gourmand", 1: "Recommended"}
mi_parts = [f"{words_num(MI_N[k])} {MI_SHORT[k]}" for k in (5, 4, 3, 2, 1) if MI_N.get(k)]
mi_line = (join_words(mi_parts) + (" restaurants" if sum(MI_N.values()) != 1 else " restaurant")) if mi_parts else ""
honors_mi = f"the MICHELIN Guide Colorado 2026 selection ({e(mi_line)})" if mi_line else "the MICHELIN Guide Colorado 2026"
guide_page("colorado-michelin-james-beard.html", "Colorado MICHELIN & James Beard restaurants", f"{BRAND} guide · honors as of {CHECKED}",
           [f"Colorado MICHELIN & James Beard Restaurants | {BRAND}", f"Colorado MICHELIN Guide & James Beard Restaurants List",
            f"MICHELIN & James Beard Restaurants in Colorado | {BRAND}"],
           [f"{plural(len(HON_L), 'Colorado restaurant')} in the MICHELIN Guide Colorado 2026 or honored by the James Beard Foundation from 2023 to 2026, by region and town.",
            f"{plural(len(HON_L), 'Colorado restaurant')} in the MICHELIN Guide Colorado 2026 or honored by the James Beard Foundation, 2023 to 2026, listed by region and town.",
            f"{plural(len(HON_L), 'Colorado restaurant')} with a MICHELIN Guide Colorado 2026 distinction or a 2023–2026 James Beard honor, listed by region and town."],
           f"{plural(len(HON_L), 'Colorado restaurant')} with an honor: {honors_mi}, and {plural(N_JBF, 'place')} with a James Beard Foundation award, nomination or America's Classic from 2023 to 2026.",
           f"""<h2>What's here, and what isn't</h2>
    <p>These are facts from the honoring organizations, not ratings: a MICHELIN distinction or a James Beard Foundation award or nomination, checked against the official announcements. Restaurants that have closed since their honor are left out. Readers' polls, "best of" lists and star ratings from review sites are never included.</p>
    <p>MICHELIN's Colorado guide covered Denver, Boulder and the resort towns from 2023 and expanded statewide in 2026. The Green Star was retired worldwide in June 2026, so none is shown.</p>
    <p class="fine">MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with either.</p>""",
           HON_L, "restaurant", "restaurants", "Colorado MICHELIN Guide and James Beard restaurants", honors=True)

# ---------------------------------------------------------------- oldest
old_pre1950 = sum(1 for p in OLD_L if p.founded < 1950)
old_checked = f" Each was checked in {CHECKED} against a 2025–26 source." if OLD_ALL_HC else ""
guide_page("colorado-oldest-restaurants.html", "Colorado's oldest restaurants", f"{BRAND} guide · checked {CHECKED}" if OLD_ALL_HC else f"{BRAND} guide",
           [f"Colorado's Oldest Restaurants & Saloons: {len(OLD_L)} Places | {BRAND}", f"Oldest Restaurants in Colorado: {len(OLD_L)} Places | {BRAND}",
            f"Colorado's Oldest Restaurants and Saloons, Year by Year"],
           [f"{plural(len(OLD_L), 'Colorado restaurant')} and saloons with a documented founding year at their current address, oldest first, with what each year rests on.",
            f"Colorado's oldest restaurants and saloons: {plural(len(OLD_L), 'place')} with a documented founding year at the same address, oldest first, sources noted.",
            f"Colorado's oldest restaurants and saloons: {plural(len(OLD_L), 'place')} with a documented founding year at this address, oldest first, and the story behind each date."],
           f"{plural(len(OLD_L), 'Colorado restaurant')} and saloons with a documented founding year at their current address, oldest first. {old_pre1950:,} opened before 1950. Under each one, a note says what the year rests on.",
           f"""<h2>How a founding year is chosen</h2>
    <p>A founding year here means the year the place opened at this address in its present form, as the place itself or a published history documents it; for a hotel's bar or dining room that opened with the hotel, the hotel's year. It is never the year a brand started elsewhere, and never a year before a move. Earlier history on the same lot, like a tent saloon, is in the note under the place. When sources disagree we use the later date, and when the year rests on the place's own account, the note under it says so.{old_checked}</p>""",
           OLD_L, "place", "places", "Colorado's oldest restaurants", region=False, show_fn=True)

# ---------------------------------------------------------------- Boulder County inspections
INS_TOWNS = Counter(p.city or "Unincorporated Boulder County" for p in INS_L)


def ins_table(places, caption_id, show_town=False):
    rows = []
    for p in places:
        i = p.ins
        where = ", ".join(x for x in (p.addr, p.city if show_town else "") if x)
        rows.append(f'<tr><th scope="row">{e(p.name)}<span class="addr">{e(where)}</span></th>'
                    f'<td><span class="res res-{i["r"]}">{e(RESULTS[i["r"]])}</span></td>'
                    f'<td class="n">{e(str(i.get("p") if i.get("p") is not None else ""))}</td><td class="d">{e(hdate_short(i["d"]) if i.get("d") else "Not published")}</td></tr>')
    return (f'<div class="tbl" role="region" aria-labelledby="{caption_id}" tabindex="0"><table><thead><tr><th scope="col">Place</th>'
            f'<th scope="col">Latest result</th><th scope="col" class="n">Points</th><th scope="col">Date</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


if INS_L:
    url = f"{DOMAIN}/{INS_PATH}"
    n_ins = len(INS_L)
    INS_DATE = hdate(INS_THROUGH)
    nav, bc = crumbs([("Home", "/"), ("Boulder County restaurant inspections", "/" + INS_PATH)])
    title = fit(["Boulder County Restaurant Inspections: Latest Results", "Boulder County, CO Restaurant Inspections: Latest Results"], 50, 60, "inspections title")
    desc = fit([f"The latest recorded Boulder County Public Health inspection result for {plural(n_ins, 'restaurant')}: Pass, Re-Inspection Required or Closure, with points.",
                f"Boulder County Public Health's latest recorded inspection result for {plural(n_ins, 'restaurant')}: Pass, Re-Inspection Required or Closure, with the points.",
                f"Latest recorded inspection results for {plural(n_ins, 'Boulder County restaurant')}: Pass, Re-Inspection Required or Closure, with risk points and dates."],
               140, 160, "inspections description")
    res_line = join_words([f"{plural(INS_RES.get(k, 0), 'place')} {RESULTS[k]}" for k in (0, 1, 2) if INS_RES.get(k)])
    tocs = '<ul class="toc">' + "".join(f'<li><a href="#town-{slug(t)}">{e(t)}</a> ({n})</li>' for t, n in sorted(INS_TOWNS.items())) + "</ul>"
    town_secs = []
    for t in sorted(INS_TOWNS):
        ps = sorted([p for p in INS_L if (p.city or "Unincorporated Boulder County") == t], key=lambda p: (p.name.lower(), p.addr))
        town_secs.append(f'<section id="town-{slug(t)}" aria-labelledby="h-town-{slug(t)}"><h2 id="h-town-{slug(t)}">{e(t)}</h2>'
                         f'<p class="sub">{plural(len(ps), "place")}, A to Z.</p>{ins_table(ps, "h-town-" + slug(t))}</section>')
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} guide · records through {e(INS_DATE)}</p>
    <h1>Boulder County restaurant inspections</h1>
    <p class="lede">The latest recorded inspection result for {plural(n_ins, 'restaurant')}, cafés and bars in Boulder County, from Boulder County Public Health's records through {e(INS_DATE)}: the result, the risk points and the date. We show the results as recorded and never compute a grade of our own.</p>
  </section>
  <section id="tiers">
    <h2>How Colorado scores an inspection</h2>
    <p>Colorado's retail food inspections, set by the Colorado Department of Public Health and Environment, end in one of three results: {e(TIERS)}</p>
    <p>At their latest recorded inspection: {e(res_line)}. A Re-Inspection Required result means the inspector comes back to check the fixes; it is not a closure.</p>
    <p>Each row is one place's latest inspection. One inspection is a snapshot of one day, and the published records can lag behind the county's own files. Boulder County is the only Colorado county that publishes its inspections in bulk, so other counties aren't covered here. Source: Boulder County Public Health on data.colorado.gov (public domain). For the agency's own records, contact Boulder County Public Health.</p>
    {f'<p class="fine">{e(NO_DATE_NOTE)}</p>' if any(not p.ins.get("d") for p in INS_L) else ""}
    <p class="fine">{other_guides("/" + INS_PATH)}</p>
    <h2>Jump to a town</h2>
    {tocs}
  </section>
{chr(10).join(town_secs)}
  </main>"""
    page(INS_PATH, title, desc, body, [article_ld(url, "Boulder County restaurant inspections", desc), bc])

# ---------------------------------------------------------------- city pages
city_stats = {}
CENTER, N_TOWN = {}, {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c and p.lat is not None]
    CENTER[c] = (sorted(p.lat for p in here)[len(here) // 2], sorted(p.lon for p in here)[len(here) // 2])
    N_TOWN[c] = sum(1 for p in REST if p.city == c)
# A city page within 15 miles of a bigger one (Lakewood, Aurora and Golden by Denver; Longmont by Boulder) lists its own town only,
# and points to the bigger page, so suburb pages don't repeat the core city's listings.
METRO = {}
for c in CITY_PAGES:
    bigger = [(N_TOWN[o], o) for o in CITY_PAGES if o != c and N_TOWN[o] > N_TOWN[c] and miles(CENTER[c], CENTER[o]) <= 15]
    if bigger:
        METRO[c] = max(bigger)[1]

CITY_INFO = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c and p.lat is not None]
    n_town = N_TOWN[c]
    center = CENTER[c]
    suburb = c in METRO

    def near(ps, radius):
        out = []
        for p in ps:
            if p.lat is None:
                continue
            d = miles(center, (p.lat, p.lon))
            if p.city == c or (radius and d <= radius):
                out.append((0 if p.city == c else 1, d, p))
        out.sort(key=lambda x: (x[0], x[1] if x[0] else 0, x[2].name.lower()))
        return [(d, p) for _, d, p in out]

    R_WIDE, R_NEAR = (0, 0) if suburb else (12, 8)
    gc, bp, sk, gm = near(CHILE_L, R_WIDE), near(BREW_L, R_NEAR), near(SKI_L, R_NEAR), near(GAME_L, R_WIDE)
    hon = sorted([p for p in here if p.mi or p.jbf], key=P.featured_key)
    oldest = sorted([p for p in here if p.founded], key=lambda p: (p.founded, p.name.lower()))[:10]
    insp = sorted([p for p in INS_L if p.city == c], key=lambda p: (p.name.lower(), p.addr))
    cuis = Counter(p.cuisine for p in REST if p.city == c and p.cuisine and p.cuisine not in ("Other", "American & Other")).most_common(10)
    listed, seen = [], set()
    for p in [p for _, p in gc] + [p for _, p in sk] + hon + [p for _, p in bp] + [p for _, p in gm] + oldest:
        if id(p) not in seen:
            seen.add(id(p)); listed.append(p)
    n_listed = len(seen | {id(p) for p in insp})
    CITY_INFO[c] = dict(gc=gc, bp=bp, sk=sk, gm=gm, hon=hon, oldest=oldest, insp=insp, cuis=cuis, listed=listed, n_listed=n_listed,
                        n_town=n_town, suburb=suburb)
    city_stats[c] = {"restaurants": n_town, "green_chile_near": len(gc), "brewpubs_near": len(bp), "ski_near": len(sk), "honors": len(hon),
                     "game_near": len(gm), "oldest": len(oldest), "inspections": len(insp), "listed": n_listed, "indexed": n_listed >= 5}


def hon_labels(hon):
    has_mi, has_jb = any(p.mi for p in hon), any(p.jbf for p in hon)
    long = "MICHELIN & James Beard" if has_mi and has_jb else "MICHELIN" if has_mi else "James Beard"
    return long, ("MICHELIN" if has_mi else "James Beard")


def city_sections(info):
    """The sections a city page actually has, most searched first: each with title (long, short), h1 and description phrases."""
    out = []
    n = lambda k: len(info[k])
    if info["gc"]:
        out.append(("gc", "Green Chile", "Green Chile", "green chile", plural(n("gc"), "hand-checked green chile spot")))
    if info["bp"]:
        bpw = "Brewpubs" if n("bp") > 1 else "Brewpub"
        out.append(("bp", bpw, bpw, bpw.lower(), plural(n("bp"), "licensed brewpub")))
    if info["hon"]:
        long, short = hon_labels(info["hon"])
        out.append(("hon", long, short, long if long != "James Beard" else "James Beard honorees", plural(n("hon"), "MICHELIN or James Beard honoree")))
    if info["oldest"]:
        out.append(("oldest", "Oldest Restaurants", "Oldest Places", "oldest restaurants", f"the oldest restaurants (back to {info['oldest'][0].founded})"))
    if info["sk"]:
        out.append(("sk", "Ski Town Dining", "Ski Dining", "ski town dining", plural(n("sk"), "ski-town restaurant")))
    if info["gm"]:
        out.append(("gm", "Game & Steakhouses", "Steakhouses", "game & steakhouses", plural(n("gm"), "game or steak restaurant")))
    if info["insp"]:
        out.append(("insp", "Restaurant Inspections", "Inspections", "restaurant inspections", f"Boulder County inspection results for {plural(n('insp'), 'place')}"))
    # what leads the title: a ski town's dining, then green chile, brewpubs, honors, inspections (a keyword nothing else here
    # targets), the oldest places, game
    rank = {"gc": 1, "bp": 2, "hon": 3, "insp": 4, "oldest": 5, "gm": 6, "sk": 7 if n("sk") < 3 else 0}
    return sorted(out, key=lambda s: rank[s[0]])


def tjoin(xs):
    if len(xs) == 1:
        return xs[0]
    conj = " and " if any("&" in x for x in xs) else " & "
    return ", ".join(xs[:-1]) + conj + xs[-1]


def city_title(c, secs):
    cands = []
    for k in range(len(secs), 0, -1):
        for col in (1, 2):
            J = tjoin([s[col] for s in secs[:k]])
            forms = [f"{c} {J} | {BRAND}", f"{c}, CO {J} | {BRAND}", f"{c}, Colorado {J}", f"{c}, CO {J}", f"{c} {J}"]
            if "Restaurant" not in J:
                forms += [f"{c} {J} & Restaurants", f"{c} Restaurants: {J}", f"{c}, CO Restaurants: {J}", f"{c} Restaurants: {J} | {BRAND}",
                          f"{c}, Colorado Restaurants: {J}", f"{c} {J} & Restaurants | {BRAND}", f"{c}, Colorado {J} & Restaurants",
                          f"{c}, CO {J} & Restaurants | {BRAND}", f"{c}, Colorado {J} & Restaurants | {BRAND}"]
            cands += forms
    cands += [f"{c} Restaurants: What {c} Eats | {BRAND}", f"{c}, Colorado Restaurants by Kind | {BRAND}", f"{c}, CO Restaurants, Cafés & Bars | {BRAND}",
              f"{c}, Colorado Restaurants, Cafés and Bars", f"{c} Restaurants, Cafés & Bars | {BRAND}"]
    return fit(cands, 50, 60, c + " title")


def city_desc(c, info, secs):
    n_town = info["n_town"]
    top = info["cuis"][0][0].lower() if info["cuis"] else ""
    leads = ([f"In {c}, Colorado"] if info["suburb"] else [f"In and near {c}, Colorado"]) + [f"{c}, Colorado", f"{c}, CO"]
    tails = [f". Search {n_town:,} {c} restaurants, cafés and bars", f". Search {n_town:,} local places to eat",
             f", plus {n_town:,} local places to eat on a searchable map", f", plus {n_town:,} more local places to eat",
             f", plus what {c} eats, by kind of restaurant", f". Most common kind of place here: {top}" if top else "", ""]
    ex1 = [x for x in (" Checked in " + CHECKED + "." if any(s[0] in ("gc", "sk", "gm") for s in secs) else "",
                       f" Brewpub licenses as of {hmonth(LIQUOR_DATE)}." if any(s[0] == "bp" for s in secs) else "",
                       f" Inspection records through {hmonth(INS_THROUGH)}." if any(s[0] == "insp" for s in secs) else "",
                       " Free iPhone app coming soon.") if x]
    extras = [""] + ex1 + [a + b for i, a in enumerate(ex1) for b in ex1[i + 1:]]

    def gen():
        for k in range(len(secs), 0, -1):
            J = join_words([s[4] for s in secs[:k]])
            for lead in leads:
                for tail in tails:
                    for x in extras:
                        yield f"{lead}: {J}{tail}.{x}"
        for tail in tails:   # a town with none of the guides' places: what it eats
            for x in extras + [f" Free Colorado restaurant guide for iPhone and iPad, coming soon."]:
                yield f"Restaurants in {c}, Colorado: the kinds of places {c} eats at most{tail}.{x}"
    return fit(list(dict.fromkeys(s.replace("..", ".") for s in gen())), 140, 160, c + " description")


for c in CITY_PAGES:
    info = CITY_INFO[c]
    gc, bp, sk, gm, hon, oldest, insp, cuis, n_town = (info[k] for k in ("gc", "bp", "sk", "gm", "hon", "oldest", "insp", "cuis", "n_town"))
    suburb, metro = info["suburb"], METRO.get(c)
    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    anchors = Anchors(url)
    secs = city_sections(info)
    title = city_title(c, secs)
    desc = city_desc(c, info, secs)
    k = 3
    while k > 1 and len(join_words([s[3] for s in secs[:k]])) > 48:   # a heading, not the whole table of contents
        k -= 1
    h1_bits = [s[3] for s in secs[:k]] + (["restaurants"] if len(secs) == 1 and "restaurant" not in secs[0][3] else [])
    h1 = f"{c} " + (join_words(h1_bits) + (", and more" if len(secs) > k else "") if secs else "restaurants")
    nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/"), (c, "/" + path)])
    area = f"In {c}" if suburb else f"In and around {c}"
    counts = [x for x in (plural(len(gc), "green chile spot") if gc else "", plural(len(bp), "brewpub") if bp else "",
                          plural(len(hon), "MICHELIN or James Beard honoree") if hon else "", plural(len(sk), "ski-town restaurant") if sk else "",
                          plural(len(gm), "game and steak place") if gm else "",
                          f"Boulder County inspection results for {plural(len(insp), 'place')}" if insp else "") if x]
    notes = []
    checked_lists = [n for n, l in (("green chile", gc), ("ski-town", sk), ("game and steak", gm)) if l]
    if checked_lists:
        notes.append(f"The {join_words(checked_lists)} {'list was' if len(checked_lists) == 1 else 'lists were'} hand-checked in {CHECKED} against 2025–26 sources.")
    if bp:
        notes.append(f"Brewpubs come from the state's Brew Pub and Distillery Pub license list of {e(LIQ)}.")
    if insp:
        notes.append(f"Inspection results are Boulder County Public Health's records through {e(hdate(INS_THROUGH))}.")
    lede = ((f"{area}: {e(join_words(counts))}. " if counts else "") + " ".join(notes) + ("" if not notes else " ")
            + f"The {BRAND} app lists {n_town:,} restaurants, cafés, bars and bakeries in {e(c)} and sorts them by distance from you.")
    metro_note = (f'<p class="fine">These lists stay inside {e(c)}. For {e(metro)}, {miles(CENTER[c], CENTER[metro]):.0f} miles away, see the '
                  f'<a href="{city_url(metro)}">{e(metro)} page</a>.</p>') if metro else ""
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · {e(c)}, Colorado</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
    {metro_note}
  </section>"""]

    def items(lst, **kw):
        return "".join(place_item(p, anchors, extra=None if p.city == c else f"{d:.0f} mi from {c}", **kw) for d, p in lst)

    scope = lambda r: f"Places in {e(c)}" if suburb else f"Places in {e(c)} first, then others within {r} miles, closest first"
    if gc:
        parts.append(f'<section id="green-chile"><h2>Green chile in {"" if suburb else "and near "}{e(c)}</h2><p class="sub">{scope(12)}, hand-checked in {CHECKED} against a 2025–26 source. Statewide: <a href="/colorado-green-chile.html">{plural(len(CHILE_L), "Colorado green chile spot")}</a>.</p><ol class="places">{items(gc)}</ol></section>')
    if sk:
        parts.append(f'<section id="ski"><h2>{e(c)} ski town dining</h2><p class="sub">{scope(8)}, hand-checked in {CHECKED} against a 2025–26 source. Seasonal places are marked. Statewide: <a href="/colorado-ski-town-restaurants.html">{plural(len(SKI_L), "Colorado ski town restaurant")}</a>.</p><ol class="places">{items(sk)}</ol></section>')
    if hon:
        parts.append(f'<section id="honors"><h2>MICHELIN &amp; James Beard in {e(c)}</h2><p class="sub">MICHELIN Guide Colorado 2026 and James Beard Foundation honorees, 2023–26. Honors are facts, not ratings. Statewide: <a href="/colorado-michelin-james-beard.html">{plural(len(HON_L), "Colorado MICHELIN and James Beard restaurant")}</a>.</p><ol class="places">'
                     + "".join(place_item(p, anchors, honors=True) for p in hon) + "</ol></section>")
    if bp:
        parts.append(f'<section id="brewpubs"><h2>Brewpubs in {"" if suburb else "and near "}{e(c)}</h2><p class="sub">{scope(8)}: places with a Colorado Brew Pub or Distillery Pub license on the state\'s list of {e(LIQ)}. Statewide: <a href="/colorado-brewpubs.html">{plural(len(BREW_L), "licensed Colorado brewpub")}</a>.</p><ol class="places">{items(bp)}</ol></section>')
    if gm:
        parts.append(f'<section id="game"><h2>Game &amp; steakhouses {"in" if suburb else "near"} {e(c)}</h2><p class="sub">{scope(12)}: bison, elk, trout and steak, hand-checked in {CHECKED} against a 2025–26 source. Statewide: <a href="/colorado-game-steakhouses.html">{plural(len(GAME_L), "Colorado game and steak place")}</a>.</p><ol class="places">{items(gm)}</ol></section>')
    if oldest:
        parts.append(f'<section id="oldest"><h2>Oldest restaurants in {e(c)}</h2><p class="sub">Founding years at the current address, as each place or a published history documents them, oldest first. The note under each says what the year rests on. Statewide: <a href="/colorado-oldest-restaurants.html">Colorado\'s oldest restaurants</a>.</p><ol class="places">'
                     + "".join(place_item(p, anchors, show_fn=True) for p in oldest) + "</ol></section>")
    if insp:
        parts.append(f'<section id="inspections" aria-labelledby="h-insp"><h2 id="h-insp">Restaurant inspections in {e(c)}</h2><p class="sub">Boulder County Public Health\'s latest recorded result for {plural(len(insp), "place")} in {e(c)}, records through {e(hdate(INS_THROUGH))}. {e(TIERS)} These are the county\'s recorded results, not a grade.{" " + e(NO_DATE_NOTE) if any(not p.ins.get("d") for p in insp) else ""} All of Boulder County: <a href="/{INS_PATH}">Boulder County restaurant inspections</a>.</p>'
                     + ins_table(insp, "h-insp") + "</section>")
    if cuis:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in cuis)
        parts.append(f'<section id="cuisines"><h2>What {e(c)} eats</h2><p class="sub">The most common kinds of restaurant among the {n_town:,} in {e(c)}, from open map data and the state and city license lists.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more"><h2>More Colorado cities and towns</h2>{city_links(current=c)}<p class="fine"><a href="/cities/">All city pages</a></p></section>\n  </main>')
    listed = info["listed"]
    lds = [article_ld(url, h1, desc), bc]
    if listed:
        lds.append(item_list(f"{c}: " + join_words([s[3] for s in secs if s[0] != "insp"]), listed, url, anchors))
    thin = info["n_listed"] < 5   # a near-empty page stays out of search until it has real content
    page(path, title, desc, "\n".join(parts), lds, robots="noindex,follow" if thin else "index,follow,max-image-preview:large")

# ---------------------------------------------------------------- cities index
url = f"{DOMAIN}/cities/"
nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/")])
cards = []
for c in CITY_PAGES:
    info = CITY_INFO[c]
    bits = [f"{s[3]} ({len(info[s[0]]) if s[0] != 'oldest' else len(info['oldest'])})" for s in city_sections(info)]
    line = (join_words(bits) + ". " if bits else "") + f"{info['n_town']:,} places to eat in all."
    cards.append(f'<a class="card" href="{city_url(c)}"><h3>{e(c)}</h3><p>{e(line[0].upper() + line[1:])}</p></a>')
first, last = CITY_PAGES[:2], CITY_PAGES[-2:]
title = fit([f"Colorado Cities & Towns: Restaurant Guides | {BRAND}", f"Colorado City Restaurant Guides: {len(CITY_PAGES)} Towns | {BRAND}"], 50, 60, "cities title")
desc = fit([f"Restaurant guides for {len(CITY_PAGES)} Colorado cities and resort towns, from {join_words(first)} to {join_words(last)}: green chile, brewpubs, honors and more.",
            f"Restaurant guides for {len(CITY_PAGES)} Colorado cities and resort towns, from {join_words(first)} to {join_words(last)}: green chile, brewpubs and the oldest places.",
            f"City-by-city Colorado restaurant guides for {len(CITY_PAGES)} cities and resort towns: green chile, brewpubs, MICHELIN and James Beard honorees and the oldest places."],
           140, 160, "cities description")
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · cities and towns</p>
    <h1>Colorado cities and towns</h1>
    <p class="lede">A page for each of Colorado's biggest cities and resort towns, with the green chile, brewpubs, MICHELIN and James Beard honorees, oldest restaurants and, in Boulder County, inspection results that are actually there.</p>
  </section>
  <section id="cities-list">
    <h2>Pick a town</h2>
    <div class="grid2">{"".join(cards)}</div>
  </section>
  </main>"""
page("cities/index.html", title, desc, body, [bc], og_type="website")

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
os.makedirs(f"{DOCS}/data", exist_ok=True)
CORE_KEYS = ["id", "n", "c", "co", "cu", "t", "s", "a", "z", "la", "lo", "b", "ch", "v", "g", "hc", "ip", "f", "h", "j", "mi", "dish"]
cols = {k: [] for k in CORE_KEYS + ["jb", "ir", "ipt", "idt"]}
detail = []
for p, r in zip(PLACES, D["places"]):
    for k in CORE_KEYS:
        v = r.get(k)
        if k == "g" and v and not p.venue and (v & BREWPUB) and not p.brewpub:
            v = v & ~BREWPUB or None   # same one-place-per-license rule as the Brewpubs page
        cols[k].append(round(v, 4) if k in ("la", "lo") and v is not None else v)
    i = clean_ins(r.get("in")) or {}
    cols["jb"].append(1 if r.get("jbf") else None)
    cols["ir"].append(i.get("r")); cols["ipt"].append(i.get("p")); cols["idt"].append(i.get("d"))
    d = {k: r[k] for k in ("ph", "w", "note", "dish", "seas", "fn", "jbf", "lic", "liq") if r.get(k)}
    if "w" in d:
        d["w"] = safe_url(d["w"])
        if not d["w"]:
            del d["w"]
    if i: d["in"] = i
    detail.append(d or None)
core = {"generated": D["generated"], "cities": CITIES, "cuisines": CUISINES, "counties": COUNTIES, "brands": D["brands"], "srcs": D["srcs"],
        "calibration": D.get("calibration", {}), "cols": cols}
json.dump(core, open(f"{DOCS}/data/core.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(detail, open(f"{DOCS}/data/detail.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(json.load(open(f"{ROOT}/data/co/co_shapes.json")), open(f"{DOCS}/data/co_shapes.json", "w"), separators=(",", ":"))

EXPLORE_CSS = """
  [hidden] { display: none !important; }
  .ex-hero { padding: 28px 0 8px; }
  .ex-hero h1 { font-size: clamp(30px, 6vw, 44px); }
  .ex-controls { background: var(--bg); padding: 10px 0 8px; border-bottom: 1px solid var(--rule); }
  .ex-guides { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
  @media (min-width: 601px) { .ex-guides { flex-wrap: wrap; overflow: visible; } }
  @media (max-width: 600px) { .ex-guides { padding-right: 32px; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); } }
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--green); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 system-ui, sans-serif; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--green); color: var(--on-green); border-color: var(--green); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 system-ui, sans-serif; font-family: inherit; padding: 10px 12px; border: 2px solid var(--green); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px system-ui, sans-serif; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
  .ex-view { margin-left: auto; display: flex; gap: 4px; }
  #ex-count { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
  #ex-sub { margin: 4px 0 0; font-size: 14px; color: var(--ink2); }
  #ex-locmsg { font-size: 13px; color: var(--muted); margin: 4px 0 0; }
  .ex-list { list-style: none; padding: 0; margin: 10px 0; }
  .ex-list li + li { border-top: 1px solid var(--rule); }
  .ex-row { width: 100%; display: flex; gap: 12px; align-items: center; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer; color: var(--ink); font: inherit; }
  .ex-row:hover { background: var(--surface2); }
  .ex-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
  .ex-main b { font-weight: 650; }
  .ex-town { font-size: 14px; color: var(--muted); }
  .ex-chips .tag { margin: 0 4px 2px 0; }
  .tag-jb { background: var(--green); color: var(--on-green); }
  .tag-plain { background: var(--surface2); color: var(--green); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--green); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--green); border-radius: 8px; }
  .ex-rank.top { background: var(--gold); color: #0f1b33; }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(72vh, 720px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #dfe6f2; }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 38px; height: 38px; border-radius: 10px; border: 1px solid #dde2ec; background: #fff; color: #002868; font: 700 20px/1 system-ui, sans-serif; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; bottom: 8px; margin: 0; font-size: 13px; background: #fff; padding: 3px 8px; border-radius: 999px; color: #2a3a5a; }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--gold); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--green2); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--green); font: 600 14px system-ui, sans-serif; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--goldsoft); color: #0f1b33; }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-result { display: flex; align-items: center; gap: 10px; font-weight: 600; flex-wrap: wrap; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  @media (min-width: 601px) { body.ex-open { overflow: auto; } }
  .tag-mi { background: #bf0a30; color: #fff; }
  .ex-res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; }
  .ex-res-0 { background: #ddefe3; color: #0e5a2b; } .ex-res-1 { background: #ffe9c2; color: #6b3a00; } .ex-res-2 { background: #f9d5db; color: #7a0019; }
"""
url = f"{DOMAIN}/explore/"
title = fit(["Search Colorado Restaurants, Green Chile & Brewpubs", "Colorado Restaurant Search & Map | Colorado Eats"], 50, 60, "explore title")
desc = fit([f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and map {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} licensed brewpubs.",
            f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and browse {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} brewpubs on a map.",
            f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and map {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} brewpubs. Free."]
           + [f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and map {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} licensed brewpubs{x}."
              for x in (" in your browser", ", free in your browser", ", free and in your browser", " right in your browser, free")]
           + [f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and browse {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} brewpubs on a map{x}."
              for x in (", free", " in your browser", ", free in your browser")], 140, 160, "explore description")
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        (("greenchile", "Green chile"), ("brewpubs", "Brewpubs"), ("ski", "Ski towns"), ("game", "Game & steak"),
                         ("honors", "MICHELIN & James Beard"), ("oldest", "Oldest"), ("inspections", "Inspections"), ("all", "All restaurants"), ("saved", "Saved")))
explore_js = open(f"{ROOT}/scripts/explore.js").read()
assert "</script" not in explore_js.lower()
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <p class="kicker">{BRAND} · on the web</p>
    <h1>Search Colorado restaurants</h1>
    <p class="sub">{N_REST:,} restaurants, cafés, bars and bakeries, with {len(CHILE_L)} hand-checked green chile spots, {len(BREW_L)} licensed brewpubs, {len(SKI_L)} ski-town restaurants and Boulder County's recorded inspection results. The same data as the iPhone and iPad app, which is coming soon. Nothing about you is stored anywhere but this browser.</p>
  </section>
  <p id="ex-loading" hidden>Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: <a href="/colorado-green-chile.html">green chile</a>, <a href="/colorado-brewpubs.html">brewpubs</a>, <a href="/colorado-ski-town-restaurants.html">ski towns</a>, <a href="/{INS_PATH}">Boulder County inspections</a>.</p></noscript>
  <div id="ex-app" hidden>
    <div class="ex-controls">
      <div class="ex-guides" role="group" aria-label="Guides">{guide_buttons}</div>
      <div class="ex-row1">
        <label class="skip" for="ex-q">Search</label>
        <input id="ex-q" type="search" placeholder="Name, town, street, zip or dish" autocomplete="off" enterkeyhint="search">
        <button type="button" id="ex-locate" class="ex-small">Near me</button>
      </div>
      <div class="ex-row2">
        <label>Sort <select id="ex-sort" aria-label="Sort"></select></label>
        <select id="ex-town" aria-label="Town"></select>
        <select id="ex-cuisine" aria-label="Kind of place"></select>
        <label><input type="checkbox" id="ex-chains"> Hide chains</label>
        <button type="button" id="ex-clear" class="ex-small" hidden>Clear filters</button>
        <div class="ex-view" role="group" aria-label="View"><button type="button" data-v="list" aria-pressed="true">List</button><button type="button" data-v="map" aria-pressed="false">Map</button></div>
      </div>
      <p id="ex-sub"></p>
      <p id="ex-count" aria-live="polite"></p>
      <p id="ex-locmsg"></p>
    </div>
    <div id="ex-listwrap"><ol id="ex-list" class="ex-list"></ol><button type="button" id="ex-more" class="ex-small" hidden></button></div>
    <div id="ex-mapwrap" hidden>
      <canvas id="ex-map" aria-label="Map of Colorado with a dot for each place in the list. The list view has the same places."></canvas>
      <div class="ex-zoom"><button type="button" id="ex-zin" aria-label="Zoom in">+</button><button type="button" id="ex-zout" aria-label="Zoom out">−</button></div>
      <p id="ex-maphint"></p>
    </div>
  </div>
  <aside id="ex-panel" class="ex-panel" hidden aria-labelledby="ex-pname"></aside>
  </main>
<script>
{explore_js}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
             "publisher": {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/"}}
page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS, og_type="website")

# ---------------------------------------------------------------- landing page
shots = [("home", "Colorado Eats home screen: Green Chile, Brewpubs, Ski Town Dining, Game & Steakhouses, MICHELIN & James Beard, Oldest Places and Inspections guides, with a search box for Colorado restaurants.", "Guides for green chile, brewpubs and ski towns."),
         ("greenchile", "The hand-checked Green Chile list in Colorado Eats, sorted by distance from downtown Denver.", "Green chile nearest you first."),
         ("detail", "The Buckhorn Exchange in Denver in Colorado Eats: address, a button for ratings, hours and photos in Apple Maps, bison and elk on the menu, open since 1893.", "Each place, with live Apple Maps hours and photos."),
         ("map", "Colorado Eats map of Colorado with pins for green chile spots.", "The map, by guide."),
         ("honors", "MICHELIN & James Beard list in Colorado Eats.", "MICHELIN Guide and James Beard honorees.")]
shot_html = []
for i, (name, alt, cap) in enumerate(shots):
    png = f"{DOCS}/img/screen-{name}.png"
    if not os.path.exists(png):
        continue
    w, h = png_size(png)
    lazy = ' loading="lazy"' if i > 1 else ""
    webp = os.path.exists(f"{DOCS}/img/screen-{name}.webp")
    src = (f'<source srcset="/img/screen-{name}.webp" type="image/webp">' if webp else "")
    shot_html.append(f'<li><picture>{src}<img src="/img/screen-{name}.png" alt="{e(alt)}" width="{w}" height="{h}"{lazy} decoding="async"></picture><p>{e(cap)}</p></li>')

checked_lists = ["green chile", "game and steakhouse", "ski-town"] + (["oldest"] if OLD_ALL_HC else [])
faq = [
    ("Is Colorado Eats free?", "Yes. The app is free, with no ads, no in-app purchases and no account. It's coming soon to the App Store; the web search works today."),
    ("Where do the green chile spots and ski-town restaurants come from?", f"We checked them by hand in {CHECKED}: each place on the {join_words(checked_lists)} lists has a 2025 or 2026 source such as its own menu page or a dated local news story. Brewpubs are places matched to a state Brew Pub or Distillery Pub license. The other {N_REST:,} restaurants come from Overture Maps' open place data, Denver's business licenses and the state's liquor licenses, placed on the map with Overture's address points and the U.S. Census Bureau Geocoder."),
    ("Does the app show ratings and reviews?", "Not its own. Tap a place and Apple Maps' own place card opens inside the app with Apple's current ratings, hours, photos and directions. Our lists are never ordered by ratings."),
    ("Does it need my location?", "Only if you want lists sorted by distance. Your location stays on your iPhone or iPad and is never sent to us. Everything else works without it. On the website, Near me uses your location only inside your browser."),
    ("What are the inspection results?", f"For Boulder County, the app and the Boulder County inspections page show Boulder County Public Health's result at each place's latest recorded inspection: Pass, Re-Inspection Required or Closure, with the risk points behind it (records through {hdate(INS_THROUGH)}). We never compute a grade of our own. Other counties don't publish inspections in bulk."),
    ("A place closed or is missing. How do I tell you?", f"Email {EMAIL} with the name and town. Corrections go into the next update."),
    ("Is there an Android version?", f"Not yet. Colorado Eats is for iPhone and iPad. If enough people ask at {EMAIL}, it moves up the list."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    # No "offers" until the app is on the App Store (put it back with the listing URL: price 0, USD).
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": "Colorado Eats: Restaurants",
     "alternateName": ["Colorado Eats", "CO Eats", "Colorado Eats: Green Chile & Brewpub Guide"],
     "description": f"A free guide to {N_REST:,} Colorado restaurants, with hand-checked lists of {len(CHILE_L)} green chile spots, {len(SKI_L)} ski-town restaurants and the state's oldest places, {len(BREW_L)} licensed brewpubs and the MICHELIN Guide and James Beard honorees. Sort by distance, open Apple Maps' live place card for hours and photos, and save places for your next trip.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}},
    {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"}},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["CO Eats", "Colorado Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-home.png"
title = "Colorado Eats: Green Chile, Brewpub & Restaurant App"
desc = fit([f"Free iPhone and iPad guide to {N_REST:,} Colorado restaurants, with {len(CHILE_L)} hand-checked green chile spots, {len(BREW_L)} brewpubs and ski-town dining.",
            f"A free iPhone and iPad guide to {N_REST:,} Colorado restaurants, with hand-checked green chile spots, {len(BREW_L)} licensed brewpubs and ski-town dining."], 140, 160, "landing description")
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
screens = f"""
  <section id="screens">
    <h2>What it looks like</h2>
    <ul class="shots" tabindex="0" aria-label="Colorado Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>""" if shot_html else ""
ins_card = (f'<a class="card" href="/{INS_PATH}"><h3>Boulder County inspections</h3><p>Latest recorded results for {plural(len(INS_L), "place")}, records through {e(hdate(INS_THROUGH))}.</p></a>'
            if INS_L else "")
body = f"""  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND}: the {TAGLINE.lower()} for iPhone and iPad</p>
    <h1>Colorado's restaurants, and the green chile worth the drive</h1>
    <p class="lede">{BRAND} is a free Colorado restaurant guide. Find a smothered burrito near you, a brewpub for after the hike and a dining room in the next ski town, from hand-checked lists and the state's own license records, plus {N_REST:,} restaurants, cafés, bars and bakeries in {N_TOWNS:,} towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">Free. No ads, no account. Coming soon to the App Store.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{len(CHILE_L)}</b><span>green chile spots</span></li>
      <li><b>{len(BREW_L)}</b><span>licensed brewpubs</span></li>
      <li><b>{len(HON_L)}</b><span>MICHELIN &amp; James Beard</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>A Colorado restaurant guide that knows what's smothered</h2>
    <p class="sub">General restaurant apps rank by star ratings and can't tell you where the slopper is. {BRAND} starts from the things people here look for: green chile, a brewpub that makes its own beer, a dining room in a ski town, bison and elk, and the saloons that have been open since the mining days. The hand-checked lists were checked in {CHECKED} against 2025–26 sources, and the brewpubs come from the state's own license list. For ratings, hours and photos, each place opens Apple Maps' own live card.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Pick a guide.</h3><p>Green Chile, Brewpubs, Ski Town Dining, Game &amp; Steakhouses, MICHELIN &amp; James Beard, Oldest Places, or search {N_REST:,} restaurants by name, town, street or dish.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>See what's near you.</h3><p>Sort by distance, filter by town or cuisine, or browse the map.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Go.</h3><p>Open Apple Maps' place card for live hours and photos, call, get directions, or save it for your next trip.</p></div></li>
    </ol>
  </section>
{screens}
  <section id="guides">
    <h2>Colorado food guides</h2>
    <p class="sub">The app's lists, readable on the web.</p>
    <div class="grid2">
      <a class="card" href="/colorado-green-chile.html"><h3>Colorado green chile guide</h3><p>{plural(len(CHILE_L), "hand-checked place")}{", Pueblo sloppers included" if N_SLOPPER else ""}.</p></a>
      <a class="card" href="/colorado-brewpubs.html"><h3>Colorado brewpubs</h3><p>{plural(len(BREW_L), "place")} with a state Brew Pub or Distillery Pub license.</p></a>
      <a class="card" href="/colorado-ski-town-restaurants.html"><h3>Ski town dining</h3><p>{plural(len(SKI_L), "restaurant")} in {e(towns_text(ski_towns, 4))} and more.</p></a>
      <a class="card" href="/colorado-game-steakhouses.html"><h3>Game &amp; steakhouses</h3><p>{plural(len(GAME_L), "place")} for bison, elk, trout and steak.</p></a>
      <a class="card" href="/colorado-michelin-james-beard.html"><h3>MICHELIN &amp; James Beard</h3><p>{plural(len(HON_L), "honored Colorado restaurant")}.</p></a>
      <a class="card" href="/colorado-oldest-restaurants.html"><h3>Colorado's oldest restaurants</h3><p>{plural(len(OLD_L), "place")} with a documented founding year.</p></a>
      {ins_card}
    </div>
  </section>

  <section id="cities">
    <h2>Green chile, brewpubs and more by city</h2>
    <p class="sub">The guides for Colorado's biggest cities and resort towns. <a href="/cities/">See what each city page has</a>.</p>
    <ul class="cities">{city_cards}</ul>
  </section>

  <section id="pricing">
    <h2>Free, and staying that way</h2>
    <p class="sub">No ads, no subscription, no in-app purchases, no account. The whole guide is built into the app, so lists open instantly and work with a weak signal in the mountains.</p>
  </section>

  <section id="privacy">
    <h2>Your plans are your business</h2>
    <p class="sub">{BRAND} collects nothing. If you allow location, it only sorts lists by distance on your device. Saved places stay on your device. This website sets no cookies and runs no trackers. <a href="/privacy.html">Read the privacy policy</a>.</p>
  </section>

  <section id="faq">
    <h2>Questions</h2>
    {faq_html}
  </section>

  <section id="download" class="final">
    <h2>Find your next green chile</h2>
    <p class="sub">{BRAND} is coming soon to the App Store for iPhone and iPad. Free.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
page("index.html", title, desc, body, [app_ld, faq_ld], og_type="website")

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>The app</h2>
    <ul>
      <li><b>No account, no analytics, no ads.</b> The app has no sign-in, no advertising and no analytics or crash-reporting code. We receive no data from it.</li>
      <li><b>Location.</b> If you allow it, your location is used on your device to sort places by distance and show where you are on the map. It is never sent to us. You can turn it off in Settings at any time.</li>
      <li><b>Saved places and filters</b> are stored only on your device and are deleted when you delete the app.</li>
      <li><b>Apple Maps.</b> When you open a place's ratings, hours and photos, or ask for directions, the app asks Apple Maps for that place. Apple handles that request under <a href="https://www.apple.com/legal/privacy/" rel="noopener">Apple's privacy policy</a>, as it does for any app that shows a map.</li>
      <li><b>Spotlight.</b> The app adds its hand-checked and honored places to your device's search index so you can find them from Spotlight. That index stays on your device.</li>
      <li><b>Calls, websites and email</b> you start from a place open in the Phone app, your browser or Mail, and are handled by them.</li>
    </ul>
    <p>When the app is on the App Store, its privacy label will be "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else.</p>
    <ul>
      <li><b>Saved places and your last guide.</b> The search page (<a href="/explore/">/explore/</a>) keeps the places you save and the last guide you opened in your browser's local storage, on this device only. Nothing is sent to us. Clearing this site's data in your browser removes them.</li>
      <li><b>Location.</b> If you tap Near me or choose the Nearest sort, your browser asks whether to share your location. If you allow it, the location is used only inside your browser to sort places by distance and is never sent to us or anyone else.</li>
    </ul>
    <p>GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
page("privacy.html", "Privacy Policy: Colorado Eats Green Chile & Restaurant App",
     fit(["The Colorado Eats privacy policy: the app collects no data, keeps your location and saved places on your device, and this website sets no cookies at all."], 140, 160),
     body, [bc])

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in Colorado. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus, and mountain-town places close for part of spring and fall. Dishes, seasons and founding years are what each place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Inspection results</h2>
    <p>The Inspections guide and the Boulder County inspections page show Boulder County Public Health's official result at each place's latest inspection, as published on data.colorado.gov: {e(TIERS)} We show the results as recorded and compute no grade of our own. An inspection is a snapshot of one day, and the published records can lag. For the agency's own records, contact Boulder County Public Health.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with any restaurant, team, chain, award body or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0; boundaries and water under the Open Database License. © OpenStreetMap contributors, Overture Maps Foundation.</li>
      <li>Overture Maps Foundation addresses data, compiled from open address sources under permissive licenses (see docs.overturemaps.org/attribution), used to place official records on the map.</li>
      <li>U.S. Census Bureau Geocoder (public domain), used for addresses Overture's address points don't cover.</li>
      <li>Colorado Department of Revenue, Liquor Enforcement Division: active liquor licenses (data.colorado.gov, public domain).</li>
      <li>Boulder County Public Health: restaurant inspections (data.colorado.gov, public domain).</li>
      <li>City and County of Denver Open Data: active business licenses, provided as is without warranty.</li>
      <li>MICHELIN Guide Colorado 2026 and the James Beard Foundation's award, finalist and semifinalist history: honors reported as facts.</li>
      <li>Green chile, game and steakhouses, ski-town dining and founding years: our own research, with a source recorded for every place.</li>
    </ul>
    <h2>Corrections</h2>
    <p>If a listing is wrong, or you own a restaurant and want something fixed, email <a href="mailto:{EMAIL}">{EMAIL}</a>. We fix mistakes in the next update.</p>
    <h2>Liability</h2>
    <p>To the extent the law allows, we are not liable for any loss arising from use of the app or site, including a wasted drive to a closed restaurant.</p>
    <h2>Changes</h2>
    <p>We may update these terms; the current version and its date are always on this page. See also the <a href="/privacy.html">privacy policy</a>.</p>
  </section>
  </main>"""
page("terms.html", "Terms of Use: Colorado Eats Green Chile & Restaurant App",
     fit(["The Colorado Eats terms of use: a free Colorado restaurant guide, provided as is. Check before you go, and see where each listing and result comes from."], 140, 160),
     body, [bc])

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">That page isn't here. Try the <a href="/">{BRAND} home page</a>, the <a href="/colorado-green-chile.html">green chile guide</a> or the <a href="/colorado-brewpubs.html">brewpubs</a>.</p>
  </section>
  </main>"""
page("404.html", f"Page not found | {BRAND}", "This page doesn't exist.", body, robots="noindex,follow")
noindexed.remove("404.html")


# ---------------------------------------------------------------- plumbing
for f in os.listdir(f"{DOCS}/cities"):   # a city the data lost: drop its old page instead of leaving it live and stale
    if f.endswith(".html") and f"cities/{f}" not in written + noindexed:
        os.remove(f"{DOCS}/cities/{f}")
        print("removed stale", f"cities/{f}")
urls = ["" if w == "index.html" else w.replace("index.html", "") for w in written]
urls.sort(key=lambda u: (u != "", u.startswith("cities/"), u))
open(f"{DOCS}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{DOCS}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
json.dump({"name": BRAND, "short_name": "CO Eats", "description": f"{TAGLINE}, plus {N_REST:,} Colorado restaurants.", "start_url": f"{BASE}/", "display": "browser",
           "background_color": "#f7f8fb", "theme_color": "#002868",
           "icons": [{"src": f"{BASE}/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{DOCS}/site.webmanifest", "w"), indent=2)
if CUSTOM_DOMAIN:
    open(f"{DOCS}/CNAME", "w").write(CUSTOM_DOMAIN + "\n")
elif os.path.exists(f"{DOCS}/CNAME"):
    os.remove(f"{DOCS}/CNAME")   # no custom domain yet: GitHub serves the project address
open(f"{DOCS}/.nojekyll", "w").write("")
os.makedirs(f"{ROOT}/playbook", exist_ok=True)
json.dump({"generated": TODAY, "domain": DOMAIN, "restaurants": N_REST, "towns": N_TOWNS, "counties": N_COUNTIES, "green_chile": len(CHILE_L),
           "brewpubs": len(BREW_L), "brewpub_duplicates_hidden": N_BREW_DROPPED, "ski_town": len(SKI_L), "game": len(GAME_L), "honors": len(HON_L),
           "michelin": dict(MI_COUNT), "james_beard": N_JBF, "oldest": len(OLD_L), "pueblo_green_chile": N_PUEBLO_CHILE, "sloppers": N_SLOPPER,
           "boulder_county_inspections": len(INS_L), "inspections_through": INS_THROUGH, "cities": city_stats,
           "noindex_pages": noindexed},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1)
print("wrote", len(written) + len(noindexed) + 1, "pages:", ", ".join(written))
if noindexed:
    print("noindex (fewer than 5 listed places, left out of the sitemap):", ", ".join(noindexed))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | green chile {len(CHILE_L)} | brewpubs {len(BREW_L)} (hid {N_BREW_DROPPED} duplicate license holders) | "
      f"ski {len(SKI_L)} | game {len(GAME_L)} | honors {len(HON_L)} | oldest {len(OLD_L)} | Boulder County inspections {len(INS_L)}")
