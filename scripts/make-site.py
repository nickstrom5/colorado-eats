"""Writes the public website in docs/ from the same data file the app ships (data/app/places.json).

Pages: the landing page, six statewide guides (green chile, brewpubs, ski-town dining, game & steakhouses, MICHELIN & James Beard,
oldest places), one page per big city or resort town, the web app (/explore/), privacy, terms, 404, plus sitemap.xml, robots.txt
and site.webmanifest. Everything listed is hand-checked research or licensed open data; nothing comes from Google, Yelp or any
ratings site, and nothing is ranked by ratings. Adapted from wi-eats/scripts/make-site.py.

Usage (from co-eats/): .venv/bin/python scripts/make-site.py
Re-run it after every data rebuild, then check the pages with scripts/qa-site.py. Never hand-edit docs/*.html.
"""
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
TODAY = "2026-10-05"
CHECKED = "fall 2026"

D = json.load(open(f"{ROOT}/data/app/places.json"))
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
CHILE, BREWPUB, GAME, SKITOWN, OLDEST, SKIDINING = 1, 2, 4, 8, 16, 32
MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"]


class P:
    """One place, with the same meaning the app gives each field (ColoradoEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = r["n"]
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]].replace(" County", "") if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = r.get("a") or ""
        self.zip = r.get("z") or ""
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.ip = r.get("ip")
        self.founded = r.get("f")
        self.dishes = (r.get("dish") or "").replace("; ", ", ")
        self.season = r.get("seas") or ""
        self.note = r.get("note") or ""
        self.site = r.get("w") or ""
        self.jbf = r.get("jbf") or ""
        self.h = r.get("h") or 0
        self.mi = r.get("mi") or 0
        self.liq = r.get("liq") or ""
        self.hc = r.get("hc") == 1   # hand-checked open with a 2025-26 source; the only places the checked guides list

    def featured_key(self):
        # the app's "Featured first": honored places, then verified founding year, then name
        return (-(self.ip if self.ip is not None else -1), self.founded or 9999, self.name.lower())

    def jb_label(self):
        return ("America's Classic" if self.h & 1 else "James Beard winner" if self.h & 2 else "James Beard finalist" if self.h & 4
                else "James Beard semifinalist" if self.h & 8 else None)


PLACES = [P(r) for r in D["places"]]
REST = [p for p in PLACES if not p.venue]
CHILE_L = sorted([p for p in REST if p.hc and p.tags & CHILE], key=P.featured_key)
BREW_L = sorted([p for p in REST if p.tags & BREWPUB], key=lambda p: (p.city, p.name.lower()))
SKI_L = sorted([p for p in REST if p.hc and p.tags & SKIDINING], key=P.featured_key)
GAME_L = sorted([p for p in REST if p.hc and p.tags & GAME], key=P.featured_key)
HON_L = sorted([p for p in REST if p.mi or p.jbf], key=P.featured_key)
OLD_L = sorted([p for p in REST if p.founded], key=lambda p: (p.founded, p.name.lower()))

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


APPLE = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.4 12.6c0-2.5 2-3.7 2.1-3.8-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.3 1-4.1 2.5-1.8 3.1-.5 7.6 1.3 10.1.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8 1.6 0 2 .8 3.3.8 1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9 0 0-2.7-1-2.9-4zM14 5.2c.7-.8 1.2-2 1-3.2-1 0-2.2.7-2.9 1.5-.6.7-1.2 1.9-1.1 3.1 1.1.1 2.3-.6 3-1.4z"/></svg>'
# the app icon in miniature: a Palisade peach on flag blue over a Front Range ridge
LOGO = '<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#002868"/><path d="M6 55 L12 51 L19 53 L26 46 L31 49 L37 43 L43 48 L50 45 L58 50 V58 Q58 64 52 64 H12 Q6 64 6 58 Z" fill="#173A80"/><circle cx="32" cy="34" r="15" fill="#FF9D52"/><path d="M32 21 C27 28 27 40 30 48" stroke="#C9443A" stroke-width="2" fill="none" opacity=".6"/><path d="M33 20 C37 12 46 12 50 15 C45 20 38 21 33 20 Z" fill="#4C9A35"/></svg>'
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

CSS = """
  :root {
    --bg: #f7f8fb; --surface: #fff; --surface2: #eef1f7; --rule: #dde2ec;
    --ink: #0f1b33; --ink2: #2a3a5a; --muted: #55627a;
    --green: #002868; --green2: #1c3f86; --gold: #ffd700; --goldsoft: #fff1a6; --red: #bf0a30;
    --radius: 16px;
    --display: "Avenir Next Condensed", "HelveticaNeue-CondensedBold", "Arial Narrow", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0d1424; --surface: #141d31; --surface2: #1b2640; --rule: #2a3654; --ink: #eef1f8; --ink2: #cfd6e6; --muted: #9aa6bf; --green: #a9c1ff; --green2: #8aa8f0; --red: #ff6b86; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--green); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible { outline: 3px solid var(--gold); outline-offset: 3px; border-radius: 6px; }
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
  h1 .kicker { display: block; font: 700 15px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .06em; color: var(--muted); margin-bottom: 12px; }
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
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .link { font-size: 14px; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--goldsoft); color: #0f1b33; border-radius: 6px; padding: 1px 6px; margin-right: 4px; }
  .tag-mi { background: #bf0a30; color: #fff; }
  .tag-jb { background: #002868; color: #fff; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); }
  td.n { text-align: right; font-variant-numeric: tabular-nums; }
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
  }
"""


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    return ('<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
            + "\n</script>")


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Get early access"):
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=Colorado%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'{APPLE}<span class="store-label">{label}</span></a>')


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css=""):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. Colorado restaurants, with hand-checked green chile, ski-town dining and the state's oldest places."
    ld = "\n".join(jsonld(x) for x in lds)
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#002868">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="{'website' if path == 'index.html' else 'article'}">
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
      <a href="/#cities">Cities</a>
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
      <a href="/colorado-michelin-james-beard.html">MICHELIN &amp; James Beard</a>
      <a href="/colorado-oldest-restaurants.html">Oldest restaurants</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>Place data: hand-checked research by {BRAND} ({CHECKED}); Overture Maps Foundation (CDLA Permissive 2.0); © OpenStreetMap contributors (ODbL); Colorado Department of Revenue liquor licenses and Boulder County Public Health inspections (data.colorado.gov, public domain); City and County of Denver Open Data. Not affiliated with or endorsed by any restaurant, team, chain or government agency, the MICHELIN Guide or the James Beard Foundation. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Places open and close, so check before you go.</p>
    <p>© 2026 {BRAND}.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Get early access" to "Download on the App Store" automatically.
  // Also fill in the apple-itunes-app meta tag in <head> on every page (re-run scripts/make-site.py after editing it there).
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
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    return path


def place_item(p, show_town=True, extra=None):
    facts = []
    if p.dishes:
        facts.append(f"<b>On the menu:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {p.founded}")
    if p.season:
        facts.append(f"<b>Season:</b> {e(p.season)}")
    kinds = []
    if p.mi:
        kinds.append(('<span class="tag tag-mi">', MI[p.mi]))
    if p.jb_label():
        kinds.append(('<span class="tag tag-jb">', p.jb_label()))
    for bit, k, need_hc in ((CHILE, "Green chile", True), (BREWPUB, "Brewpub", False), (GAME, "Game &amp; steak", True)):
        if p.tags & bit and (p.hc or not need_hc):
            kinds.append(('<span class="tag">', k))
    where = ", ".join(x for x in (p.addr, p.city) if x)
    if extra:
        where += f" · {extra}"
    out = [f"<li><h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f"{tag}{k}</span>" for tag, k in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p):
    x = {"@type": "Restaurant", "name": p.name,
         "address": {"@type": "PostalAddress", "streetAddress": p.addr, "addressLocality": p.city, "addressRegion": "CO", "addressCountry": "US"}}
    if p.zip:
        x["address"]["postalCode"] = p.zip
    if p.site:
        x["url"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("Other", "Restaurant"):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url):
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p)} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": TODAY, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/", "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png"}}}


def fit(options, lo, hi):
    for o in options:
        if lo <= len(o) <= hi:
            return o
    raise ValueError(f"nothing fits {lo}-{hi}: {[(len(o), o) for o in options]}")


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
N_JBF = sum(1 for p in HON_L if p.jbf)


def by_region(places, key=lambda p: (p.city, p.name.lower())):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere in Colorado"].append(p)
    order = list(REGIONS) + ["Elsewhere in Colorado"]
    return [(r, sorted(groups[r], key=key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural=None):
    plural = plural or noun + "s"
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{len(ps)} {noun if len(ps) == 1 else plural}, by town.</p><ol class="places">'
                    + "".join(place_item(p) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


CITY_PAGES = ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Boulder", "Pueblo", "Lakewood", "Longmont", "Greeley", "Golden",
              "Grand Junction", "Durango", "Aspen", "Breckenridge", "Steamboat Springs", "Vail"]
assert all(any(p.city == c for p in REST) for c in CITY_PAGES), [c for c in CITY_PAGES if not any(p.city == c for p in REST)]


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links():
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES) + "</ul>"


GUIDE_LINKS = [("/colorado-green-chile.html", "Colorado green chile guide"), ("/colorado-brewpubs.html", "Colorado brewpubs"),
               ("/colorado-ski-town-restaurants.html", "Ski town dining"), ("/colorado-game-steakhouses.html", "Game & steakhouses"),
               ("/colorado-michelin-james-beard.html", "MICHELIN & James Beard restaurants"), ("/colorado-oldest-restaurants.html", "Oldest restaurants")]


def other_guides(skip):
    return "Other guides: " + ", ".join(f'<a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS if u != skip) + "."


written = []


def guide_page(path, h1, kicker, title_opts, desc_opts, lede, about_html, places, noun, plural, list_name, region=True):
    url = f"{DOMAIN}/{path}"
    title, desc = fit(title_opts, 50, 60), fit(desc_opts, 140, 160)
    nav, bc = crumbs([("Home", "/"), (h1, "/" + path)])
    if region:
        toc, secs = region_sections(places, noun, plural)
        jump = f"<h2>Jump to a region</h2>\n    {toc}"
    else:
        secs = f'<section id="list"><ol class="places">{"".join(place_item(p) for p in places)}</ol></section>'
        jump = ""
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{kicker}</span>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">Free for iPhone and iPad. Coming to the App Store.</span></div>
  </section>
  <section id="about">
    {about_html}
    <p class="fine">{other_guides("/" + path)} City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
    {jump}
  </section>
{secs}
  </main>"""
    written.append(page(path, title, desc, body, [article_ld(url, h1, desc), bc, item_list(list_name, places, url)]))


# ---------------------------------------------------------------- green chile
top_dish = ", ".join(f"{d} ({n})" for d, n in DISH_WORDS.most_common(6))
guide_page("colorado-green-chile.html", "Colorado green chile guide", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Green Chile Guide: {len(CHILE_L)} Checked Places | {BRAND}", f"Colorado Green Chile: {len(CHILE_L)} Checked Places | {BRAND}",
            f"Colorado Green Chile Guide: {len(CHILE_L)} Places & Pueblo Sloppers"],
           [f"{len(CHILE_L)} Colorado green chile spots checked open in {CHECKED}: smothered burritos, breakfast burritos, Pueblo sloppers and chile by the bowl, by region.",
            f"{len(CHILE_L)} Colorado places for green chile, checked open in {CHECKED}: smothered and breakfast burritos, Pueblo sloppers, chile by the bowl. Free app."],
           f"{len(CHILE_L)} restaurants, diners and taverns across Colorado known for green chile, each confirmed open in {CHECKED} on its own menu or recent local news. For each one: what's on the menu, and how long it's been there when we could verify it.",
           f"""<h2>Colorado green chile, briefly</h2>
    <p>Colorado green chile is a pork-and-roasted-pepper stew, thicker and often hotter than New Mexico's, ladled over almost everything: smothered burritos, breakfast burritos, chile rellenos and fries. In Pueblo it tops a hamburger in a bowl, the slopper. Peppers come from Pueblo and the San Luis Valley, and late summer smells like chile roasters outside grocery stores.</p>
    <h2>What's on the list</h2>
    <p>{N_PUEBLO_CHILE} of the {len(CHILE_L)} are in Pueblo County, and {N_SLOPPER} serve a slopper. The dishes we found most often: {e(top_dish)}.</p>
    <p>How the list was built: every place was checked against a 2025 or 2026 source, such as its own menu page or a dated local news story. Places with no current source, a dead website or green chile only mentioned in passing were left out. Nothing here comes from review sites, and the order is by region and town, not by anyone's rating. Menus change, so check before you go.</p>
    <p>In the {BRAND} app, the same list sorts by distance from you, and each place opens Apple Maps' own card for live hours, photos and directions.</p>""",
           CHILE_L, "green chile spot", "green chile spots", "Colorado green chile restaurants")

# ---------------------------------------------------------------- brewpubs
top_brew = ", ".join(f"{c} ({n})" for c, n in BREW_TOWNS.most_common(6))
guide_page("colorado-brewpubs.html", "Colorado brewpubs", f"{BRAND} guide · state licenses as of {D['liquor_updated']}",
           [f"Colorado Brewpubs: {len(BREW_L)} Licensed Brewpubs by Town | {BRAND}", f"Colorado Brewpubs: {len(BREW_L)} Licensed by Town | {BRAND}",
            f"Colorado Brewpubs: All {len(BREW_L)} with a State Brew Pub License"],
           [f"All {len(BREW_L)} Colorado restaurants with a state Brew Pub or Distillery Pub license, where the beer or spirits are made on site, listed by region and town.",
            f"The {len(BREW_L)} Colorado restaurants holding a state Brew Pub or Distillery Pub license, making beer or spirits on site, by region and town. Free app."],
           f"Every place in Colorado that holds a state Brew Pub or Distillery Pub license, which lets a restaurant brew beer or distill spirits on site and serve them with food: {len(BREW_L)} in all, matched to their addresses.",
           f"""<h2>What a brewpub license means</h2>
    <p>Colorado's Liquor Enforcement Division issues a Brew Pub license to a restaurant that brews its own beer on the premises, and a Distillery Pub license to one that distills. That's different from a production brewery's taproom, which holds a manufacturer license and doesn't have to serve food. So this list is the brewpubs in the legal sense: places to eat where the beer is made in house.</p>
    <p>The towns with the most: {e(top_brew)}.</p>
    <p>How the list was built: from the Colorado Department of Revenue's list of active liquor licenses on data.colorado.gov ({e(D['liquor_updated'])}), matched to each place's map listing by name and street address. The order is by region and town.</p>""",
           BREW_L, "brewpub", "brewpubs", "Colorado brewpubs")

# ---------------------------------------------------------------- ski towns
ski_towns = Counter(p.city for p in SKI_L)
guide_page("colorado-ski-town-restaurants.html", "Colorado ski town restaurants", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Ski Town Restaurants: {len(SKI_L)} Checked Places | {BRAND}", f"Colorado Ski Town Dining: {len(SKI_L)} Places | {BRAND}",
            f"Colorado Ski Town Restaurants: {len(SKI_L)} Checked Places"],
           [f"{len(SKI_L)} restaurants in Aspen, Vail, Breckenridge, Telluride, Steamboat and other Colorado ski towns, checked open in {CHECKED}, with seasonal hours noted.",
            f"{len(SKI_L)} Colorado ski town restaurants in Aspen, Vail, Breckenridge, Telluride and Steamboat, checked open in {CHECKED}, seasons noted. Free app."],
           f"{len(SKI_L)} restaurants in Colorado's ski towns, from slopeside lodges to downtown institutions, each confirmed open in {CHECKED}. On-mountain places that only open in winter are marked.",
           f"""<h2>Eating in the mountains</h2>
    <p>Colorado's resort towns have more good restaurants per resident than anywhere else in the state, and many keep their own schedule: on-mountain lodges open only in ski season, and lots of town restaurants close for a few weeks of "mud season" in spring and fall. Those closures are not permanent, and the list marks seasonal places when they say so.</p>
    <p>By town: {e(", ".join(f"{c} ({n})" for c, n in ski_towns.most_common(10)))}.</p>
    <p>How the list was built: each place was checked against a 2025 or 2026 source, usually its own site or menu or a dated story in the local paper. Places with no current source were left out. MICHELIN Guide Colorado restaurants in these towns are included. The order is by region and town, never by rating.</p>""",
           SKI_L, "restaurant", "restaurants", "Colorado ski town restaurants")

# ---------------------------------------------------------------- game & steakhouses
guide_page("colorado-game-steakhouses.html", "Colorado game & steakhouses", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado Steakhouses & Game: {len(GAME_L)} Checked Places | {BRAND}", f"Colorado Bison, Elk & Steakhouses: {len(GAME_L)} Places",
            f"Colorado Game & Steakhouses: {len(GAME_L)} Places | {BRAND}"],
           [f"{len(GAME_L)} Colorado restaurants serving bison, elk, trout and steak, checked open in {CHECKED}, from the Buckhorn Exchange to mountain-town lodges, by region.",
            f"{len(GAME_L)} Colorado places for bison, elk, trout and steak, checked open in {CHECKED}, from the Buckhorn Exchange to ski-town lodges, by region. Free app."],
           f"{len(GAME_L)} restaurants with bison, elk, venison, trout or a classic steakhouse menu, each confirmed open in {CHECKED} on its current menu or recent local news.",
           f"""<h2>Colorado on the plate</h2>
    <p>Bison and elk ranch across the state, Rocky Mountain trout comes out of its rivers, and steakhouses have fed Denver since the stockyards. The dishes listed with each place are from its current menu when we checked.</p>
    <p>How the list was built: every place was checked against a 2025 or 2026 source. Menus change with the season, so check before you go. The order is by region and town, never by rating.</p>""",
           GAME_L, "place", "places", "Colorado game and steakhouse restaurants")

# ---------------------------------------------------------------- MICHELIN & James Beard
mi_line = ", ".join(f"{n} {k}" for k, n in sorted(MI_COUNT.items(), key=lambda kv: -["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars"].index(kv[0])))
guide_page("colorado-michelin-james-beard.html", "Colorado MICHELIN & James Beard restaurants", f"{BRAND} guide · honors as of {CHECKED}",
           [f"Colorado MICHELIN & James Beard Restaurants | {BRAND}", f"Colorado MICHELIN Guide & James Beard Restaurants List",
            f"MICHELIN & James Beard Restaurants in Colorado | {BRAND}"],
           [f"Every Colorado restaurant in the MICHELIN Guide Colorado 2026 or honored by the James Beard Foundation from 2023 to 2026: {len(HON_L)} places, by region and town.",
            f"The {len(HON_L)} Colorado restaurants in the MICHELIN Guide Colorado 2026 or honored by the James Beard Foundation from 2023 to 2026, listed by region and town."],
           f"{len(HON_L)} Colorado restaurants with an honor: the MICHELIN Guide Colorado 2026 selection ({e(mi_line)}) and {N_JBF} James Beard Foundation award winners, finalists, semifinalists and America's Classics from 2023 to 2026.",
           f"""<h2>What's here, and what isn't</h2>
    <p>These are facts from the honoring organizations, not ratings: a MICHELIN distinction or a James Beard Foundation award or nomination, checked against the official announcements. Restaurants that have closed since their honor are left out. Readers' polls, "best of" lists and star ratings from review sites are never included.</p>
    <p>MICHELIN's Colorado guide covered Denver, Boulder and the resort towns from 2023 and expanded statewide in 2026. The Green Star was retired worldwide in June 2026, so none is shown.</p>
    <p class="fine">MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with either.</p>""",
           HON_L, "restaurant", "restaurants", "Colorado MICHELIN Guide and James Beard restaurants")

# ---------------------------------------------------------------- oldest
old_pre1950 = sum(1 for p in OLD_L if p.founded < 1950)
guide_page("colorado-oldest-restaurants.html", "Colorado's oldest restaurants", f"{BRAND} guide · checked {CHECKED}",
           [f"Colorado's Oldest Restaurants & Saloons: {len(OLD_L)} Places | {BRAND}", f"Oldest Restaurants in Colorado: {len(OLD_L)} Places | {BRAND}",
            f"Colorado's Oldest Restaurants and Saloons, Year by Year"],
           [f"{len(OLD_L)} Colorado restaurants and saloons with a verified founding year at their current address, oldest first, from 1870s mining-town saloons to Denver's classics.",
            f"Colorado's oldest restaurants and saloons: {len(OLD_L)} places with a verified founding year at the same address, oldest first. Checked open in {CHECKED}."],
           f"{len(OLD_L)} Colorado restaurants and saloons with a founding year we could verify at their current address, oldest first. {old_pre1950} opened before 1950.",
           f"""<h2>How a founding year is checked</h2>
    <p>A founding year here means the year the place opened at this address: not the year a brand started, not the year the building went up, and not before a move. When a claim couldn't be confirmed (a building's date, a "since" line that counts an earlier business), the year is left off.</p>
    <p>Every place was confirmed open in {CHECKED} against a 2025 or 2026 source.</p>""",
           OLD_L, "place", "places", "Colorado's oldest restaurants", region=False)

# ---------------------------------------------------------------- city pages
city_stats = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c and p.lat is not None]
    n_town = sum(1 for p in REST if p.city == c)
    lat = sorted(p.lat for p in here)[len(here) // 2]
    lon = sorted(p.lon for p in here)[len(here) // 2]
    center = (lat, lon)

    def near(ps, radius):
        out = []
        for p in ps:
            if p.lat is None:
                continue
            d = miles(center, (p.lat, p.lon))
            if p.city == c or d <= radius:
                out.append((0 if p.city == c else 1, d, p))
        out.sort(key=lambda x: (x[0], x[1] if x[0] else 0, x[2].name.lower()))
        return [(d, p) for _, d, p in out]

    gc, bp, sk, gm = near(CHILE_L, 12), near(BREW_L, 8), near(SKI_L, 8), near(GAME_L, 12)
    hon = sorted([p for p in here if p.mi or p.jbf], key=P.featured_key)
    oldest = sorted([p for p in here if p.founded], key=lambda p: (p.founded, p.name.lower()))[:10]
    cuis = Counter(p.cuisine for p in REST if p.city == c and p.cuisine and p.cuisine not in ("Other", "American & Other")).most_common(10)
    city_stats[c] = {"restaurants": n_town, "green_chile_near": len(gc), "brewpubs_near": len(bp), "ski_near": len(sk), "honors": len(hon)}

    def items(lst):
        return "".join(place_item(p, extra=None if p.city == c else f"{d:.0f} mi from {c}") for d, p in lst)

    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    title = fit([f"{c} Green Chile, Brewpubs & Restaurants | {BRAND}", f"{c} Restaurants, Green Chile & Brewpubs Guide",
                 f"{c}, CO Green Chile, Brewpubs & Restaurants", f"{c}, Colorado Restaurants, Green Chile & Brewpubs"], 50, 60)
    desc = fit([f"Green chile, brewpubs, MICHELIN and James Beard honorees and the oldest restaurants in and near {c}, Colorado, checked in {CHECKED}, plus local places.",
                f"Green chile, brewpubs, honored restaurants and the oldest places in and near {c}, Colorado, checked in {CHECKED}, plus all {n_town:,} local restaurants.",
                f"Green chile, brewpubs, MICHELIN and James Beard places and the oldest restaurants in {c}, CO, checked in {CHECKED}, with all {n_town:,} local spots.",
                f"Green chile spots, brewpubs, honored restaurants and the oldest places in and near {c}, Colorado, checked in {CHECKED}. Free iPhone and iPad app."], 140, 160)
    nav, bc = crumbs([("Home", "/"), ("Cities", "/#cities"), (c, "/" + path)])
    counts = [x for x in (f"{len(gc)} green chile spots" if gc else "", f"{len(bp)} brewpubs" if bp else "", f"{len(hon)} honored restaurants" if hon else "",
                          f"{len(sk)} ski-town restaurants" if sk else "") if x]
    lede_counts = (", ".join(counts[:-1]) + " and " + counts[-1]) if len(counts) > 1 else (counts[0] if counts else "")
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} · {e(c)}, Colorado</span>{e(c)} green chile, brewpubs &amp; restaurants</h1>
    <p class="lede">{"In and around " + e(c) + ": " + e(lede_counts) + ", each checked in " + CHECKED + ". " if lede_counts else ""}The {BRAND} app has all {n_town:,} restaurants, cafés, bars and bakeries in {e(c)} and sorts them by distance from you.</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">Free for iPhone and iPad. Coming to the App Store.</span></div>
  </section>"""]
    if gc:
        parts.append(f'<section id="green-chile"><h2>Green chile in and near {e(c)}</h2><p class="sub">Places in {e(c)} first, then others within 12 miles, closest first. <a href="/colorado-green-chile.html">All {len(CHILE_L)} Colorado green chile spots</a>.</p><ol class="places">{items(gc)}</ol></section>')
    if sk:
        parts.append(f'<section id="ski"><h2>{e(c)} ski town dining</h2><p class="sub">Hand-checked restaurants in and around {e(c)}. Seasonal places are marked. <a href="/colorado-ski-town-restaurants.html">All {len(SKI_L)} ski town restaurants</a>.</p><ol class="places">{items(sk)}</ol></section>')
    if hon:
        parts.append(f'<section id="honors"><h2>MICHELIN &amp; James Beard in {e(c)}</h2><p class="sub">MICHELIN Guide Colorado 2026 and James Beard Foundation honorees, 2023–26. Honors are facts, not ratings. <a href="/colorado-michelin-james-beard.html">All {len(HON_L)} in Colorado</a>.</p><ol class="places">'
                     + "".join(place_item(p) for p in hon) + "</ol></section>")
    if bp:
        parts.append(f'<section id="brewpubs"><h2>Brewpubs in and near {e(c)}</h2><p class="sub">Restaurants with a Colorado Brew Pub or Distillery Pub license, within 8 miles. <a href="/colorado-brewpubs.html">All {len(BREW_L)} Colorado brewpubs</a>.</p><ol class="places">{items(bp)}</ol></section>')
    if gm:
        parts.append(f'<section id="game"><h2>Game &amp; steakhouses near {e(c)}</h2><p class="sub">Bison, elk, trout and steak, hand-checked, within 12 miles. <a href="/colorado-game-steakhouses.html">All {len(GAME_L)} in Colorado</a>.</p><ol class="places">{items(gm)}</ol></section>')
    if oldest:
        parts.append(f'<section id="oldest"><h2>Oldest restaurants in {e(c)}</h2><p class="sub">Founding years at the current address, checked against the restaurant\'s own history page or local news, oldest first.</p><ol class="places">'
                     + "".join(place_item(p) for p in oldest) + "</ol></section>")
    if cuis:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in cuis)
        parts.append(f'<section id="cuisines"><h2>What {e(c)} eats</h2><p class="sub">The most common kinds of restaurant among the {n_town:,} in {e(c)}, from open map data and the state and city license lists.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more"><h2>More Colorado cities and towns</h2>{city_links()}</section>\n  </main>')
    listed, seen = [], set()
    for p in [p for _, p in gc] + [p for _, p in sk] + hon + [p for _, p in bp] + [p for _, p in gm]:
        if id(p) not in seen:
            seen.add(id(p)); listed.append(p)
    written.append(page(path, title, desc, "\n".join(parts),
                        [article_ld(url, f"{c} green chile, brewpubs and restaurants", desc), bc, item_list(f"Green chile, brewpubs and honored restaurants near {c}", listed, url)]))

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
os.makedirs(f"{DOCS}/data", exist_ok=True)
CORE_KEYS = ["id", "n", "c", "co", "cu", "t", "s", "a", "z", "la", "lo", "b", "ch", "v", "g", "hc", "ip", "f", "h", "j", "mi", "dish"]
cols = {k: [] for k in CORE_KEYS + ["jb", "ir", "ipt", "idt"]}
detail = []
for r in D["places"]:
    for k in CORE_KEYS:
        v = r.get(k)
        cols[k].append(round(v, 4) if k in ("la", "lo") and v is not None else v)
    i = r.get("in") or {}
    cols["jb"].append(1 if r.get("jbf") else None)
    cols["ir"].append(i.get("r")); cols["ipt"].append(i.get("p")); cols["idt"].append(i.get("d"))
    d = {k: r[k] for k in ("ph", "w", "note", "dish", "seas", "fn", "jbf", "lic", "liq") if r.get(k)}
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
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--green); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 inherit; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--green); color: #fff; border-color: var(--green); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 inherit; font-family: inherit; padding: 10px 12px; border: 2px solid var(--green); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px inherit; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
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
  .tag-jb { background: var(--green); color: #fff; }
  .tag-plain { background: var(--surface2); color: var(--green); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--green); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--green); border-radius: 8px; }
  .ex-rank.top { background: var(--gold); color: #16211d; }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(72vh, 720px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #cfe3ea; }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 38px; height: 38px; border-radius: 10px; border: 1px solid var(--rule); background: var(--surface); color: var(--green); font: 700 20px/1 inherit; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; bottom: 8px; margin: 0; font-size: 13px; background: var(--surface); padding: 3px 8px; border-radius: 999px; color: var(--ink2); }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--gold); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--green2); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--green); font: 600 14px inherit; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--goldsoft); }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-grade { display: flex; align-items: center; gap: 10px; font-weight: 600; }
  .ex-g { display: inline-grid; place-items: center; width: 40px; height: 40px; border-radius: 10px; color: #fff; font: 800 24px var(--display); }
  .ex-g-A { background: #12733a; } .ex-g-B { background: #4b7a1b; } .ex-g-C { background: #f2b01e; color: #16211d; } .ex-g-D { background: #e8804f; } .ex-g-F { background: #c1302f; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  @media (min-width: 601px) { body.ex-open { overflow: auto; } }
"""

EXPLORE_CSS = EXPLORE_CSS.replace("#cfe3ea", "#dfe6f2").replace("color: #16211d", "color: #0f1b33") + """
  .tag-mi { background: #bf0a30; color: #fff; }
  .ex-res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; }
  .ex-res-0 { background: #ddefe3; color: #0e5a2b; } .ex-res-1 { background: #ffe9c2; color: #6b3a00; } .ex-res-2 { background: #f9d5db; color: #7a0019; }
"""
url = f"{DOMAIN}/explore/"
title = fit(["Search Colorado Restaurants, Green Chile & Brewpubs", "Colorado Restaurant Search & Map | Colorado Eats"], 50, 60)
desc = fit([f"Search all {N_REST:,} Colorado restaurants by name, town, street or dish, and browse {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} brewpubs on a map.",
            f"Search {N_REST:,} Colorado restaurants by name, town, street or dish, and map {len(CHILE_L)} hand-checked green chile spots and {len(BREW_L)} brewpubs. Free."], 140, 160)
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        (("greenchile", "Green chile"), ("brewpubs", "Brewpubs"), ("ski", "Ski towns"), ("game", "Game & steak"),
                         ("honors", "MICHELIN & James Beard"), ("oldest", "Oldest"), ("inspections", "Inspections"), ("all", "All restaurants"), ("saved", "Saved")))
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <h1><span class="kicker">{BRAND} · on the web</span>Search Colorado restaurants</h1>
    <p class="sub">{N_REST:,} restaurants, cafés, bars and bakeries, with {len(CHILE_L)} hand-checked green chile spots, {len(BREW_L)} licensed brewpubs, {len(SKI_L)} ski-town restaurants and Boulder County's official inspection results. The same data as the free iPhone and iPad app. Nothing about you is stored anywhere but this browser.</p>
  </section>
  <p id="ex-loading">Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: <a href="/colorado-green-chile.html">green chile</a>, <a href="/colorado-brewpubs.html">brewpubs</a>, <a href="/colorado-ski-town-restaurants.html">ski towns</a>.</p></noscript>
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
{open(f"{ROOT}/scripts/explore.js").read()}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": {"@id": f"{DOMAIN}/#org"}}
written.append(page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS))

# ---------------------------------------------------------------- landing page
shots = [("home", "Colorado Eats home screen: Green Chile, Brewpubs, Ski Town Dining, Game & Steakhouses, MICHELIN & James Beard, Oldest Places and Inspections guides, with a search box for every restaurant in the state.", "Guides for green chile, brewpubs and ski towns."),
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

faq = [
    ("Is Colorado Eats free?", "Yes. The app is free, with no ads, no in-app purchases and no account."),
    ("Where do the green chile spots and ski-town restaurants come from?", f"We checked each one by hand in {CHECKED}: every place on the green chile, game and steakhouse, ski-town and oldest lists has a 2025 or 2026 source such as its own menu page or a dated local news story. Brewpubs are the places with a state Brew Pub license. The rest of the {N_REST:,} restaurants come from Overture Maps' open place data, Denver's business licenses and the state's liquor licenses."),
    ("Does the app show ratings and reviews?", "Not its own. Tap a place and Apple Maps' own place card opens inside the app with Apple's current ratings, hours, photos and directions. Our lists are never ordered by ratings."),
    ("Does it need my location?", "Only if you want lists sorted by distance. Your location stays on your iPhone or iPad and is never sent to us. Everything else works without it."),
    ("What are the inspection results?", "For Boulder County, the app shows Boulder County Public Health's official result at each place's latest inspection, as recorded: Pass, Re-Inspection Required or Closure, with the risk points behind it. We never compute a grade of our own. Other counties don't publish inspections in bulk."),
    ("A place closed or is missing. How do I tell you?", f"Email {EMAIL} with the name and town. Corrections go into the next update."),
    ("Is there an Android version?", f"Not yet. Colorado Eats is for iPhone and iPad. If enough people ask at {EMAIL}, it moves up the list."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": "Colorado Eats: Restaurants",
     "alternateName": ["Colorado Eats", "CO Eats", "Colorado Eats: Green Chile & Brewpub Guide"],
     "description": f"A free guide to {N_REST:,} Colorado restaurants, with hand-checked lists of {len(CHILE_L)} green chile spots, {len(SKI_L)} ski-town restaurants and the state's oldest places, {len(BREW_L)} licensed brewpubs and the MICHELIN Guide and James Beard honorees. Sort by distance, open Apple Maps' live place card for hours and photos, and save places for your next trip.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"},
     "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "category": "free"}},
    {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"}},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["CO Eats", "Colorado Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-home.png"
title = "Colorado Eats: Green Chile, Brewpub & Restaurant App"
desc = fit([f"Free iPhone and iPad guide to {N_REST:,} Colorado restaurants, with {len(CHILE_L)} hand-checked green chile spots, {len(BREW_L)} brewpubs and ski-town dining.",
            f"A free iPhone and iPad guide to {N_REST:,} Colorado restaurants, with hand-checked green chile spots, {len(BREW_L)} licensed brewpubs and ski-town dining."], 140, 160)
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
screens = f"""
  <section id="screens">
    <h2>What it looks like</h2>
    <ul class="shots" tabindex="0" aria-label="Colorado Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>""" if shot_html else ""
body = f"""  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND}: the {TAGLINE.lower()} for iPhone and iPad</span>Colorado's restaurants, and the green chile worth the drive</h1>
    <p class="lede">{BRAND} is a free Colorado restaurant guide. Find a smothered burrito near you, a brewpub for after the hike and a dining room in the next ski town, from lists we checked by hand, plus {N_REST:,} restaurants, cafés, bars and bakeries in {N_TOWNS:,} towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">Free. No ads, no account. Coming to the App Store.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{len(CHILE_L)}</b><span>green chile spots</span></li>
      <li><b>{len(BREW_L)}</b><span>brewpubs</span></li>
      <li><b>{len(HON_L)}</b><span>MICHELIN &amp; James Beard</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>A Colorado restaurant guide that knows what's smothered</h2>
    <p class="sub">General restaurant apps rank by star ratings and can't tell you where the slopper is. {BRAND} starts from the things people here look for: green chile, a brewpub that makes its own beer, a dining room in a ski town, bison and elk, and the saloons that have been open since the mining days. The hand-checked lists were checked open in {CHECKED}, and the brewpubs come from the state's own license list. For ratings, hours and photos, each place opens Apple Maps' own live card.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Pick a guide.</h3><p>Green Chile, Brewpubs, Ski Town Dining, Game &amp; Steakhouses, MICHELIN &amp; James Beard, Oldest Places, or search every restaurant by name, town, street or dish.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>See what's near you.</h3><p>Sort by distance, filter by town or cuisine, or browse the map.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Go.</h3><p>Open Apple Maps' place card for live hours and photos, call, get directions, or save it for your next trip.</p></div></li>
    </ol>
  </section>
{screens}
  <section id="guides">
    <h2>Colorado food guides</h2>
    <p class="sub">The app's lists, readable on the web.</p>
    <div class="grid2">
      <a class="card" href="/colorado-green-chile.html"><h3>Colorado green chile guide</h3><p>{len(CHILE_L)} hand-checked places, Pueblo sloppers included.</p></a>
      <a class="card" href="/colorado-brewpubs.html"><h3>Colorado brewpubs</h3><p>All {len(BREW_L)} restaurants with a state Brew Pub license.</p></a>
      <a class="card" href="/colorado-ski-town-restaurants.html"><h3>Ski town dining</h3><p>{len(SKI_L)} restaurants in Aspen, Vail, Breckenridge, Telluride and more.</p></a>
      <a class="card" href="/colorado-game-steakhouses.html"><h3>Game &amp; steakhouses</h3><p>{len(GAME_L)} places for bison, elk, trout and steak.</p></a>
      <a class="card" href="/colorado-michelin-james-beard.html"><h3>MICHELIN &amp; James Beard</h3><p>{len(HON_L)} honored Colorado restaurants.</p></a>
      <a class="card" href="/colorado-oldest-restaurants.html"><h3>Colorado's oldest restaurants</h3><p>{len(OLD_L)} places with a verified founding year.</p></a>
    </div>
  </section>

  <section id="cities">
    <h2>Green chile, brewpubs and more by city</h2>
    <p class="sub">The guides for Colorado's biggest cities and resort towns.</p>
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
    <p class="sub">{BRAND} is coming to the App Store for iPhone and iPad. Free.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
written.append(page("index.html", title, desc, body, [app_ld, faq_ld]))

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {TODAY}.</p>
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
    <p>On the App Store, the app's privacy label is "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else. GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
written.append(page("privacy.html", "Privacy Policy: Colorado Eats Green Chile & Restaurant App",
                    fit(["The Colorado Eats privacy policy: the app collects no data, keeps your location and saved places on your device, and this website sets no cookies at all."], 140, 160),
                    body, [bc]))

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {TODAY}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in Colorado. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus, and mountain-town places close for part of spring and fall. Dishes, seasons and founding years are what each place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Inspection results</h2>
    <p>The Inspections guide shows Boulder County Public Health's official result at each place's latest inspection, as published on data.colorado.gov: Pass, Re-Inspection Required or Closure, with the risk points recorded. We show the results as recorded and compute no grade of our own. An inspection is a snapshot of one day, and the published records can lag. For the agency's own records, contact Boulder County Public Health.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. MICHELIN and the MICHELIN Guide are trademarks of Michelin; James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with any restaurant, team, chain, award body or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0; boundaries and water under the Open Database License. © OpenStreetMap contributors, Overture Maps Foundation.</li>
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
written.append(page("terms.html", "Terms of Use: Colorado Eats Green Chile & Restaurant App",
                    fit(["The Colorado Eats terms of use: a free Colorado restaurant guide, provided as is. Check before you go, and see where each listing and result comes from."], 140, 160),
                    body, [bc]))

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">That page isn't here. Try the <a href="/">{BRAND} home page</a>, the <a href="/colorado-green-chile.html">green chile guide</a> or the <a href="/colorado-brewpubs.html">brewpubs</a>.</p>
  </section>
  </main>"""
page("404.html", f"Page not found | {BRAND}", "This page doesn't exist.", body, robots="noindex,follow")


# ---------------------------------------------------------------- plumbing
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
           "brewpubs": len(BREW_L), "ski_town": len(SKI_L), "game": len(GAME_L), "honors": len(HON_L), "michelin": dict(MI_COUNT), "james_beard": N_JBF,
           "oldest": len(OLD_L), "pueblo_green_chile": N_PUEBLO_CHILE, "sloppers": N_SLOPPER, "cities": city_stats},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1)
print("wrote", len(written) + 1, "pages:", ", ".join(written))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | green chile {len(CHILE_L)} | brewpubs {len(BREW_L)} | ski {len(SKI_L)} | game {len(GAME_L)} | honors {len(HON_L)} | oldest {len(OLD_L)}")
