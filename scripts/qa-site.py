"""QA for the website in docs/: static checks on every generated page, then every page in headless Chrome at phone and desktop widths.

Static (no browser):
- no "every restaurant" / "all N restaurants"-style overclaims anywhere (text, meta, alt text, JSON-LD, the web app's strings)
- a Content-Security-Policy meta on every page whose hashes match each inline <script>/<style>; no inline style or on* attributes
- titles 50-60 and descriptions 140-160 characters, unique across indexable pages; one <h1>; sitemap = the indexable pages
- city pages: the title, h1 and description name only sections the page has
- JSON-LD parses; ItemList items point to an anchor on the same page; no aggregateRating/review; no empty streetAddress
- the web app keeps its localStorage under "coeats-" (Connecticut Eats uses "ce-" on the same origin)
- the store button carries no Apple logo; no letter-grade CSS; one place per brewpub license in the published data
- no website on pipeline/website_blocklist.json (hacked, expired, directory or another business's) anywhere in docs/, in any
  case, www., http(s) or subdomain form; a missing or empty blocklist fails (check_blocklist)
- no "Confirmed listing" anywhere in docs/ (the label is "High-confidence listing"), and nothing promises or offers a TestFlight
  invite or link (label_and_promise_checks; Nick, 2026-10-13)
Browser (Playwright, channel="chrome"): no horizontal scroll, no console errors, no CSP violations, no broken internal links or
images; the web app loads, searches ("pueblo slopper" finds only slopper places), opens a place, Back closes it, the phone panel is
a modal dialog, a hostile #g= doesn't break it, and saved places use the coeats- prefix. Also (bugs found in sibling web apps):
phone inputs and selects >= 16px, the open place a labelled modal dialog at every width (Back/Forward/Escape/press outside), bad
localStorage values don't stop the app, no "Nearest" without a location, and Near me asks for a fresh fix on every tap.
Round 3: the search placeholder fits the box at 375px (scrollWidth <= clientWidth with its words as the value), and a search that
finds nothing or a few in a guide offers "Search all restaurants (N matches)", which lists them with the same words.

Usage: .venv/bin/python scripts/qa-site.py            (serves docs/ itself on a free localhost port; exits 1 on any problem)
       .venv/bin/python scripts/qa-site.py --static   (static checks only, a few seconds)
Copied from wi-eats/scripts/qa-site.py. Until the custom domain is live the site sits under /colorado-eats/ on github.io, so the
pages are served under that same path here (a temporary folder with docs/ linked in as colorado-eats/).
"""
import base64
import functools
import glob
import hashlib
import html
import html.parser
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.environ.get("QA_DOCS") or os.path.join(ROOT, "docs")   # QA_DOCS: check a copy (used to mutation-test these checks)
DOMAIN = open(os.path.join(DOCS, "CNAME")).read().strip() if os.path.exists(os.path.join(DOCS, "CNAME")) else "nickstrom5.github.io"
BASE = re.search(r'data-base="([^"]*)"', open(os.path.join(DOCS, "index.html")).read()).group(1)
STORAGE_PREFIX = "coeats-"

# claims the lists can't back up: the app lists what was checked or matched, never "every"/"all N" restaurants
OVERCLAIMS = [
    r"\bevery\s+(?:single\s+)?(?:colorado\s+|local\s+|licensed\s+)?(?:restaurant|brewpub|bar|caf[eé]|place to eat|eatery)",
    r"\bevery\s+place\s+in\s+(?:colorado|the\s+state)",
    r"\ball\s+(?:of\s+the\s+)?\d[\d,]*\s+(?:\w+\s+){0,2}(?:restaurants|brewpubs|places|spots|caf[eé]s|bars)\b",
    r"\b(?:all|every)\s+(?:the\s+)?(?:restaurants|brewpubs|places)\s+in\s+(?:the\s+state|colorado|town)\b",
    r"\b(?:all|every)\s+(?:of\s+)?colorado'?s\s+(?:restaurants|brewpubs)\b",
    r"\b(?:confirmed|checked|verified)\s+open\b",            # the research dates show when we checked a source, not that it's open now
    r"\bimminent health hazard at any score\b",              # unconfirmed as Colorado's rule; Boulder County records it (AR-15)
    # the privacy policy says the app's location is never sent to us; Apple Maps handles its own requests, so not "anywhere"
    r"\bnever\s+sent\s+anywhere\b",
    # the 15,716 include the checked lists; 234 of the 252 brewpub licenses matched a listing; not every founding note names a source
    r"\bthe\s+other\s+[\d,]+\s+(?:places|restaurants)\b",
    r"\bthe\s+brewpubs\s+are\s+the\s+restaurants\s+on\b",
    r"\b(?:gives|names)\s+the\s+source\s+of\s+its\s+year\b",
]
# Boulder County's September 2025 system move stamped records with this day: it is not an inspection date and is never shown
MIGRATION_DATES = [r"2025-09-03", r"September 3, 2025", r"Sep 3, 2025"]
# Nick, 2026-10-12: the site's contact is nick@eatsranked.com; the old address must not appear anywhere in docs/
OLD_EMAIL = "work-with-nick@gmail.com"
SITE_EMAIL = "nick@eatsranked.com"
HUB = "https://eatsranked.com/"
# other state apps sharing this family: their app names and repo slugs never appear in this site (4.3(a): each state is its own
# app), and other state names never appear in the page code or comments (place names and cuisines in the data may say "New York")
OTHER_APPS = [r"Wisconsin Eats", r"Connecticut Eats", r"Florida Eats", r"California Eats", r"Washington Eats", r"Maine Eats", r"Idaho Eats",
              r"New York Eats", r"Chicago Restaurants: Ranked", r"Chi Ranked"]
OTHER_SLUGS = [r"(?:wi|ct|fl|ca|wa|me|id|ny|chi)-eats", r"(?:wisconsin|connecticut|florida|california|washington|maine|idaho|new-york)-eats",
               r"chicago-restaurants-ranked"]
OTHER_STATES = r"\b(?:Wisconsin|Connecticut|Florida|California|Washington|Maine|Idaho|New York|Illinois|Chicago)\b"
# city-page words -> the section that backs them
CITY_KEYWORDS = [(r"green chile", "green-chile"), (r"brewpub", "brewpubs"), (r"michelin|james beard|honoree", "honors"),
                 (r"\boldest\b", "oldest"), (r"\bski\b", "ski"), (r"steak|\bgame\b", "game"), (r"inspection", "inspections")]


class Page(html.parser.HTMLParser):
    """The facts the static checks need from one HTML file."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.robots, self.canonical, self.csp = "", None, "", None, None
        self.h1s, self.ids, self.section_ids, self.alts = [], [], set(), []
        self.scripts, self.styles, self.ldjson, self.bad_attrs = [], [], [], []
        self._in, self._buf, self._h1 = None, [], None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k == "style" or k.startswith("on"):
                self.bad_attrs.append(f"<{tag} {k}=…>")
        if "id" in a:
            self.ids.append(a["id"])
            if tag == "section":
                self.section_ids.add(a["id"])
        if tag == "img":
            self.alts.append(a.get("alt"))
        if tag == "meta":
            if a.get("name") == "description":
                self.desc = a.get("content", "")
            elif a.get("name") == "robots":
                self.robots = a.get("content", "")
            elif (a.get("http-equiv") or "").lower() == "content-security-policy":
                self.csp = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag in ("script", "style", "title"):
            self._in, self._buf = (tag, a.get("type")), []
        if tag == "h1":
            self._h1 = []

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            text = "".join(self._buf)
            kind, typ = self._in
            if kind == "title":
                self.title = text
            elif kind == "style":
                self.styles.append(text)
            elif typ == "application/ld+json":
                self.ldjson.append(text)
            elif typ in (None, "", "text/javascript", "module"):
                self.scripts.append(text)
            self._in = None
        if tag == "h1" and self._h1 is not None:
            self.h1s.append("".join(self._h1).strip())
            self._h1 = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
        if self._h1 is not None:
            self._h1.append(data)


def sha(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "." + k, k, v
            yield from walk(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


def doc_files():
    return sorted(f for f in glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True) if "/screenshots/" not in f)


def rel(f):
    return os.path.relpath(f, DOCS)


def page_url(path):
    full = f"https://{DOMAIN}{BASE}" if DOMAIN.endswith("github.io") else f"https://{DOMAIN}"
    return full + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))


def sitemap_paths():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(os.path.join(DOCS, "sitemap.xml")).getroot().findall("s:url/s:loc", ns)]
    out = []
    for u in locs:
        p = urllib.parse.urlparse(u).path
        if BASE and p.startswith(BASE):
            p = p[len(BASE):]
        p = p.lstrip("/")
        out.append(p + "index.html" if p == "" or p.endswith("/") else p)
    return out


def static_checks():
    problems = []
    pages = {rel(f): open(f, encoding="utf-8").read() for f in doc_files()}
    parsed = {p: Page(t) for p, t in pages.items()}
    in_sitemap = set(sitemap_paths())
    titles, descs = {}, {}
    for path, text in pages.items():
        pg = parsed[path]
        where = path
        indexed = "noindex" not in pg.robots
        # --- overclaims: everything a reader or a crawler sees (CSS aside)
        visible = html.unescape(re.sub(r"<style>.*?</style>", " ", text, flags=re.S))
        visible = re.sub(r"\s+", " ", visible.replace("\\u003c", "<"))
        for rx in OVERCLAIMS:
            for m in re.finditer(rx, visible, re.I):
                problems.append(f"{where}: overclaim \"{m.group(0)}\" (…{visible[max(0, m.start() - 40):m.end() + 20]}…)")
        # --- CSP
        if not pg.csp:
            problems.append(f"{where}: no Content-Security-Policy meta")
        else:
            pol = {d.split()[0]: d.split()[1:] for d in (x.strip() for x in pg.csp.split(";")) if d}
            if pol.get("default-src") != ["'none'"]:
                problems.append(f"{where}: CSP default-src isn't 'none'")
            for name, blocks in (("script-src", pg.scripts), ("style-src", pg.styles)):
                allowed = pol.get(name, [])
                if any(x in allowed for x in ("'unsafe-inline'", "'unsafe-eval'", "*", "https:", "data:")):
                    problems.append(f"{where}: CSP {name} is loose: {allowed}")
                for b in blocks:
                    if sha(b) not in allowed:
                        problems.append(f"{where}: an inline {name.split('-')[0]} block isn't in the CSP (hash {sha(b)[:20]}…)")
            for need in ("base-uri", "form-action", "connect-src", "img-src"):
                if need not in pol:
                    problems.append(f"{where}: CSP has no {need}")
        shown = re.sub(r"<script>.*?</script>", " ", visible, flags=re.S)   # the web app's code names the stamp in order to hide it
        for rx in MIGRATION_DATES:
            if re.search(rx, shown):
                problems.append(f"{where}: shows {rx}, the county's records-migration stamp, as a date")
        if pg.bad_attrs:
            problems.append(f"{where}: inline style/event attributes break the CSP: {pg.bad_attrs[:3]}")
        # --- titles, descriptions, headings, sitemap
        if len(pg.h1s) != 1:
            problems.append(f"{where}: {len(pg.h1s)} <h1>")
        if path != "404.html":
            if not 50 <= len(pg.title) <= 60:
                problems.append(f"{where}: title is {len(pg.title)} characters: {pg.title}")
            if pg.desc is None or not 140 <= len(pg.desc) <= 160:
                problems.append(f"{where}: description is {len(pg.desc or '')} characters")
        if indexed and path != "404.html":
            if pg.title in titles:
                problems.append(f"{where}: same title as {titles[pg.title]}")
            if pg.desc in descs:
                problems.append(f"{where}: same description as {descs[pg.desc]}")
            titles[pg.title], descs[pg.desc] = path, path
            if path not in in_sitemap:
                problems.append(f"{where}: indexable but not in sitemap.xml")
            if pg.canonical != page_url(path):
                problems.append(f"{where}: canonical {pg.canonical} != {page_url(path)}")
        elif path in in_sitemap:
            problems.append(f"{where}: noindex page is in sitemap.xml")
        for a in pg.alts:
            if not a:
                problems.append(f"{where}: an <img> has no alt text")
        dup_ids = {i for i in pg.ids if pg.ids.count(i) > 1}
        if dup_ids:
            problems.append(f"{where}: duplicate ids {sorted(dup_ids)[:5]}")
        # --- city pages: the title, h1 and description promise only what's on the page
        if path.startswith("cities/") and path != "cities/index.html":
            promise = " ".join([pg.title, pg.h1s[0] if pg.h1s else "", pg.desc or ""]).lower()
            for rx, sec in CITY_KEYWORDS:
                if re.search(rx, promise) and sec not in pg.section_ids:
                    problems.append(f"{where}: title/h1/description mention {rx!r} but the page has no #{sec} section")
        # --- JSON-LD
        for raw in pg.ldjson:
            try:
                ld = json.loads(raw)
            except ValueError as ex:
                problems.append(f"{where}: bad JSON-LD ({ex})")
                continue
            if "</" in raw:
                problems.append(f"{where}: JSON-LD contains a raw '</'")
            for p, k, v in walk(ld):
                if k in ("aggregateRating", "review", "reviewRating", "ratingValue"):
                    problems.append(f"{where}: JSON-LD has {k} at {p}")
                if k == "streetAddress" and not str(v).strip():
                    problems.append(f"{where}: empty streetAddress at {p}")
            for block in ([ld] + ld.get("@graph", [])) if isinstance(ld, dict) else []:
                if block.get("@type") != "ItemList":
                    continue
                own_url = pg.canonical or page_url(path)
                items = block.get("itemListElement", [])
                if block.get("numberOfItems") != len(items):
                    problems.append(f"{where}: ItemList numberOfItems {block.get('numberOfItems')} != {len(items)}")
                for li in items:
                    it = li.get("item", {})
                    u = it.get("url", "")
                    if not u.startswith(own_url + "#"):
                        problems.append(f"{where}: ItemList item {it.get('name')!r} url {u!r} isn't on this page")
                    elif u.split("#", 1)[1] not in pg.ids:
                        problems.append(f"{where}: ItemList item {it.get('name')!r} points to #{u.split('#', 1)[1]}, which isn't on the page")
                    s = it.get("sameAs")
                    if s and not re.match(r"https?://", s):
                        problems.append(f"{where}: sameAs {s!r} isn't http(s)")
        # --- links: only http(s), mailto and tel leave the site
        for href in re.findall(r'href="([^"]*)"', text):
            if re.match(r"\s*(javascript|data|vbscript):", href, re.I) and not href.startswith("data:image/svg+xml"):
                problems.append(f"{where}: unsafe link {href[:40]}")
        # --- the App Store button has no Apple logo until it's Apple's own badge
        for m in re.finditer(r'<a class="btn store-btn"[^>]*>(.*?)</a>', text, re.S):
            if "<svg" in m.group(1):
                problems.append(f"{where}: the early-access button carries an Apple logo")
        if re.search(r"\.ex-g-[A-F]\b|\bletter grade\b", text):
            problems.append(f"{where}: letter-grade CSS or wording")
    # --- the contact address, the Eats Ranked family link, other states' names
    for path, text in pages.items():
        if not re.search(r'<p>[^<]*Part of <a href="' + re.escape(HUB) + r'">Eats Ranked</a>, restaurant apps state by state\.</p>', text):
            problems.append(f"{path}: footer has no 'Part of Eats Ranked' link to {HUB}")
        orgs = [b for raw in parsed[path].ldjson for b in (lambda d: d.get("@graph", [d]) if isinstance(d, dict) else [])(json.loads(raw))
                if b.get("@type") == "Organization" and str(b.get("@id", "")).endswith("/#org")]
        if not orgs or any((o.get("parentOrganization") or {}).get("@id") != HUB + "#organization" for o in orgs):
            problems.append(f"{path}: no #org Organization with parentOrganization {HUB}#organization")
        if SITE_EMAIL not in text:
            problems.append(f"{path}: doesn't show the contact address {SITE_EMAIL}")
        if not re.search(r'<head>.*?<!--[^>]*?<meta name="apple-itunes-app" content="app-id=[^"]+">.*?-->.*?</head>', text, re.S):
            problems.append(f"{path}: no apple-itunes-app placeholder in <head>")
        code = "\n".join(parsed[path].scripts) + "\n".join(re.findall(r"<!--(.*?)-->", text, re.S))
        for m in re.finditer(OTHER_STATES, code):
            problems.append(f"{path}: page code or a comment names another state: {m.group(0)!r}")
    for f in glob.glob(os.path.join(DOCS, "**", "*"), recursive=True):
        if os.path.isfile(f) and f.rsplit(".", 1)[-1] in ("html", "json", "xml", "txt", "webmanifest", "js", "css", "md"):
            body = open(f, encoding="utf-8", errors="replace").read()
            if OLD_EMAIL in body:
                problems.append(f"{rel(f)}: still has the old contact address {OLD_EMAIL}")
            for rx in OTHER_APPS + OTHER_SLUGS:
                for m in re.finditer(r"(?<![\w-])" + rx + r"(?![\w-])", body):
                    problems.append(f"{rel(f)}: names another state's app or repo: {m.group(0)!r}")
    # --- SEO: og:url is the canonical; breadcrumbs point at real pages; the FAQ's JSON-LD says exactly what the page shows
    for path, text in pages.items():
        pg = parsed[path]
        og = re.search(r'<meta property="og:url" content="([^"]*)"', text)
        if pg.canonical and (not og or og.group(1) != pg.canonical):
            problems.append(f"{path}: og:url {og and og.group(1)} != canonical {pg.canonical}")
        shown_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S))))
        for raw in pg.ldjson:
            d = json.loads(raw)
            for b in (d.get("@graph", [d]) if isinstance(d, dict) else []):
                if b.get("@type") == "BreadcrumbList":
                    for it in b.get("itemListElement", []):
                        tp = urllib.parse.urlparse(it.get("item", "")).path
                        tp = tp[len(BASE):] if BASE and tp.startswith(BASE) else tp
                        if not local_exists(tp or "/"):
                            problems.append(f"{path}: breadcrumb {it.get('item')} isn't a page")
                if b.get("@type") == "FAQPage":
                    for q in b.get("mainEntity", []):
                        for t in (q.get("name", ""), q.get("acceptedAnswer", {}).get("text", "")):
                            if re.sub(r"\s+", " ", t) not in shown_text:
                                problems.append(f"{path}: FAQPage text isn't on the page as written: {t[:60]!r}")
    # --- green chile: each dish counted once, whatever the spelling ("green chili", "breakfast burrito" vs "...burritos")
    gc = pages.get("colorado-green-chile.html", "")
    m = re.search(r"The dishes we found most often: ([^<]*)\.", gc)
    if m:
        keys = [re.sub(r"s\b", "", re.sub(r"\bgreen chil+i\b", "green chile", re.sub(r"\s*\(\d+\)", "", d).strip().lower()))
                for d in html.unescape(m.group(1)).split(", ")]
        if len(keys) != len(set(keys)):
            problems.append(f"colorado-green-chile.html: a dish is counted twice under two spellings: {m.group(1)}")
        try:   # the same six, in the same order, as the green chile places' dishes in the published data (a tie goes by name)
            C = json.load(open(os.path.join(DOCS, "data", "core.json")))["cols"]
            fold = lambda x: re.sub(r"s\b", "", x)
            n, forms = {}, {}
            for i in range(len(C["id"])):
                if C["hc"][i] == 1 and (C["g"][i] or 0) & 1 and C["v"][i] != 1:
                    fs = {re.sub(r"\bgreen chil+i\b", "green chile", x.strip().lower()) for x in str(C["dish"][i] or "").replace("; ", ", ").split(",") if x.strip()}
                    for k in {fold(f) for f in fs}:
                        n[k] = n.get(k, 0) + 1
                    for f in fs:
                        forms.setdefault(fold(f), {}).setdefault(f, 0)
                        forms[fold(f)][f] += 1
            shown_as = {k: max(forms[k].items(), key=lambda kv: (kv[1], kv[0]))[0] for k in n}
            want = ", ".join(f"{shown_as[k]} ({c})" for k, c in sorted(n.items(), key=lambda kv: (-kv[1], shown_as[kv[0]]))[:6])
            if html.unescape(m.group(1)) != want:
                problems.append(f"colorado-green-chile.html: the most common dishes read {html.unescape(m.group(1))!r}, the data gives {want!r}")
        except (OSError, ValueError, KeyError) as ex:
            problems.append(f"colorado-green-chile.html: couldn't recount the dishes ({ex})")
    # --- the web app's storage keys
    ex = parsed.get("explore/index.html")
    if ex:
        js = "\n".join(ex.scripts)
        if f'"{STORAGE_PREFIX}"' not in js:
            problems.append(f"explore/index.html: localStorage prefix {STORAGE_PREFIX!r} not found")
        for m in re.finditer(r"""localStorage\.(?:get|set|remove)Item\(\s*(["'`])([^"'`]*)\1""", js):
            if not m.group(2).startswith(STORAGE_PREFIX):
                problems.append(f"explore/index.html: localStorage key {m.group(2)!r} doesn't start with {STORAGE_PREFIX!r}")
        if re.search(r"""["'`]ce-["'`]""", js):
            problems.append("explore/index.html: still uses another site's \"ce-\" storage prefix")
        priv = html.unescape(re.sub(r"<[^>]+>", " ", pages.get("privacy.html", "")))
        for k in re.findall(r'store\.set\("([^"]+)"', js):
            if STORAGE_PREFIX + k not in priv:
                problems.append(f"privacy.html: doesn't name the web app's localStorage key {STORAGE_PREFIX + k!r}")
    else:
        problems.append("explore/index.html is missing")
    # --- one place per brewpub license in the published data (the Brewpubs page and the web app agree)
    try:
        core = json.load(open(os.path.join(DOCS, "data", "core.json")))
        detail = json.load(open(os.path.join(DOCS, "data", "detail.json")))
        seen = {}
        for i, g in enumerate(core["cols"]["g"]):
            if g and g & 2 and core["cols"]["v"][i] != 1:
                for l in (detail[i] or {}).get("lic", []):
                    if str(l.get("type", "")).startswith(("Brew Pub", "Distillery Pub")):
                        if l["id"] in seen:
                            problems.append(f"data: brewpub license {l['id']} on two places: {core['cols']['n'][seen[l['id']]]!r} and {core['cols']['n'][i]!r}")
                        seen[l["id"]] = i
        for i, dt in enumerate(core["cols"].get("idt", [])):
            if dt and str(dt).startswith("2025-09-03"):
                problems.append(f"data: core.json gives {core['cols']['n'][i]!r} the migration stamp 2025-09-03 as its inspection date")
        for i, d in enumerate(detail):
            ins = (d or {}).get("in") or {}
            if any(str(x.get("d") or "").startswith("2025-09-03") for x in [ins] + list(ins.get("h") or [])):
                problems.append(f"data: detail.json gives {core['cols']['n'][i]!r} the migration stamp 2025-09-03 as an inspection date")
            w = (d or {}).get("w")
            if w and not re.match(r"https?://", w):
                problems.append(f"data: website {w!r} for {core['cols']['n'][i]!r} isn't http(s)")
    except (OSError, ValueError, KeyError) as ex:
        problems.append(f"data: couldn't read core/detail.json ({ex})")
    check_blocklist(problems)
    label_and_promise_checks(problems)
    return problems, len(pages)


# Nick, 2026-10-13 (family-wide): the web app's middle tier is a "High-confidence listing", never a "Confirmed listing"; and since only
# his internal TestFlight group exists, the site never promises or offers a TestFlight invite or link: the early-access copy ends at an ask.
OLD_LABEL = re.compile(r"confirmed\s+listing", re.I)
PROMISES = [re.compile(r"\b(?:we|you)(?:\\?['’]ll|\s+will)\b[^.!?]{0,60}?(?:invit\w*|testflight(?:\s+(?:invit\w*|links?))?|\bbeta\b)", re.I),  # "we'll email you a TestFlight invite"
            re.compile(r"\btestflight\s+(?:invit\w*|links?)\b", re.I)]                                           # "the button asks for a TestFlight invite"


def label_and_promise_checks(problems):
    """No "Confirmed listing" (any case) in any file in docs/, the web app's script and data included; and nothing a visitor reads
    (page text, meta descriptions, alt and aria text, JSON-LD, the web app's strings) promises or offers a TestFlight invite or link.
    A mailto: link whose body asks for access is fine, so mailto hrefs are left out of the promise check."""
    for f in glob.glob(os.path.join(DOCS, "**", "*"), recursive=True):
        if not (os.path.isfile(f) and f.rsplit(".", 1)[-1] in ("html", "json", "xml", "txt", "webmanifest", "svg", "js", "css", "md")):
            continue
        s = open(f, encoding="utf-8", errors="replace").read()
        m = OLD_LABEL.search(s)
        if m:
            problems.append(f"{rel(f)}: says {m.group(0)!r} (the label is 'High-confidence listing')")
        raw = html.unescape(re.sub(r'href="mailto:[^"]*"', 'href=""', s))
        found = [m.group(0) for text in (raw, re.sub(r"<[^>]+>", " ", raw))   # as written, and with inline tags out of the way
                 for rx in PROMISES for m in [rx.search(text)] if m]
        if found:
            problems.append(f"{rel(f)}: promises a TestFlight invite or link: {' '.join(found[0].split())!r}")


# Websites the site never links (hacked, expired, a directory or another business's site): pipeline/website_blocklist.json, which
# scripts/make-site.py drops from every page and data file. QA_BLOCKLIST points at another copy (used to mutation-test this check).
BLOCKLIST = os.environ.get("QA_BLOCKLIST") or os.path.join(ROOT, "pipeline", "website_blocklist.json")
BINARY = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".ico", ".pdf", ".woff", ".woff2", ".mp4", ".mov", ".zip")


def blocked_patterns(entries):
    """One case-insensitive pattern per blocklist entry. A "domain" entry (the default) matches the domain and every subdomain,
    www. included, with or without a scheme; a "url" entry matches that URL with http or https, with or without www. and the
    trailing slash, and nothing else on its (shared) host. Returns (patterns, problems with the entries themselves)."""
    out, bad = [], []
    for n, b in enumerate(entries):
        kind = b.get("match", "domain") if isinstance(b, dict) else None
        if kind == "url":
            u = urllib.parse.urlsplit(str(b.get("url") or "").strip())
            host = (u.hostname or "").lower().removeprefix("www.")
            if u.scheme not in ("http", "https") or "." not in host:
                bad.append(f"entry {n} ({b.get('place')}): a \"url\" entry needs an http(s) \"url\", got {b.get('url')!r}")
                continue
            path = re.escape(u.path.rstrip("/")) + (r"\?" + re.escape(u.query) if u.query else "")
            out.append((b, re.compile(rf"(?<![\w.-])(?:www\.)?{re.escape(host)}{path}/?(?=$|[\"'<>\s?#)\\,&])", re.I)))
        elif kind == "domain":
            d = re.sub(r"^[a-z]+://", "", str(b.get("domain") or "").strip().lower()).split("/")[0].rstrip(".").removeprefix("www.")
            if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", d):
                bad.append(f"entry {n} ({b.get('place')}): \"domain\" {b.get('domain')!r} isn't a domain name")
                continue
            out.append((b, re.compile(rf"(?<![\w-])(?:[\w-]+\.)*{re.escape(d)}(?![\w-])", re.I)))
        else:
            bad.append(f"entry {n}: \"match\" must be \"domain\" or \"url\", got {kind!r} in {str(b)[:80]}")
    return out, bad


def check_blocklist(problems):
    """No blocklisted website anywhere in docs/: pages, JSON-LD, the web app's data files, the sitemap, any text file. A missing,
    unreadable or empty blocklist fails too, so this check can never pass by having nothing to look for."""
    name = os.path.relpath(BLOCKLIST, ROOT)
    try:
        entries = json.load(open(BLOCKLIST, encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{name} is missing: the site has no list of websites it must never link")
        return
    except ValueError as ex:
        problems.append(f"{name} isn't valid JSON ({ex})")
        return
    if not isinstance(entries, list) or not entries:
        problems.append(f"{name} is empty (or not a list): the blocklist check would pass with nothing to look for")
        return
    pats, bad = blocked_patterns(entries)
    problems += [f"{name}: {x}" for x in bad]
    scanned = 0
    for d, _, files in os.walk(DOCS):
        for x in sorted(files):
            if x.lower().endswith(BINARY):
                continue
            scanned += 1
            raw = open(os.path.join(d, x), encoding="utf-8", errors="replace").read()
            text = html.unescape(raw.replace("\\/", "/"))   # JSON's escaped slashes and HTML entities read as the URL they are
            for b, pat in pats:
                hits = pat.findall(text)
                if hits:
                    problems.append(f"{os.path.relpath(os.path.join(d, x), DOCS)}: links a blocklisted website ({b.get('severity')}, "
                                    f"{str(b.get('reason'))[:60]}): {len(hits)} × {b.get('url') or b.get('domain')} ({b.get('place')})")
    if not scanned:
        problems.append(f"blocklist check: no files to scan in {DOCS}")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    root = DOCS
    if BASE:   # serve docs/ at /colorado-eats/, the path GitHub Pages will use
        root = tempfile.mkdtemp()
        os.symlink(os.path.abspath(DOCS), os.path.join(root, BASE.strip("/")))
    # QA_PORT pins the port (the machine is shared: each session keeps to its own range); default: any free port
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("QA_PORT") or 0)), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def local_exists(path):
    path = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    if BASE and path.startswith(BASE + "/"):
        path = path[len(BASE):]
    f = os.path.join(DOCS, path.lstrip("/"))
    return os.path.isfile(f) or os.path.isfile(os.path.join(f, "index.html"))


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", s.replace("'", "")).strip() + " "


def expected_slopper_hits():
    """Green chile places a search for "slopper" should find: the ones whose name, dishes or address say slopper."""
    core = json.load(open(os.path.join(DOCS, "data", "core.json")))
    C = core["cols"]
    return sum(1 for i in range(len(C["id"])) if C["hc"][i] == 1 and (C["g"][i] or 0) & 1 and C["v"][i] != 1
               and " slopper" in norm(" ".join(str(x) for x in (C["n"][i], C["dish"][i], C["a"][i]) if x)))


def expected_bib():
    """Bib Gourmand places (MICHELIN level 2) the web app's box should list, non-restaurants left out like the app."""
    C = json.load(open(os.path.join(DOCS, "data", "core.json")))["cols"]
    return sum(1 for i in range(len(C["id"])) if C["mi"][i] == 2 and C["v"][i] != 1)


def bib_problems(page, ex, width):
    """The Bib Gourmand box keeps every Bib Gourmand and nothing else: the count is core.json's, every row says Bib Gourmand,
    and unticking it brings the whole guide back."""
    want, out = expected_bib(), []
    if not want:
        return [f"explore @{width}: core.json has no Bib Gourmand (mi 2) places"]
    page.goto(ex + "#g=all&bib=1", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=20000)
    box = page.locator("#ex-bibwrap")
    if not box.is_visible() or box.inner_text().strip() != f"Bib Gourmand ({want:,})" or not page.locator("#ex-bib").is_checked():
        out.append(f"explore @{width}: the Bib Gourmand box isn't shown ticked as 'Bib Gourmand ({want:,})' ({box.inner_text().strip()!r})")
    count = page.locator("#ex-count").inner_text()
    if not count.startswith(f"{want:,} place"):
        out.append(f"explore @{width}: Bib Gourmand lists {count!r}, expected the {want} in core.json")
    tags = page.evaluate("[...document.querySelectorAll('.ex-row')].map(r => [...r.querySelectorAll('.tag-mi')].map(t => t.textContent).join('|'))")
    if len(tags) != min(want, 100):
        out.append(f"explore @{width}: Bib Gourmand shows {len(tags)} rows, expected {min(want, 100)}")
    wrong = [t for t in tags if t != "Bib Gourmand"]
    if wrong:
        out.append(f"explore @{width}: Bib Gourmand lists places that aren't Bib Gourmands: {wrong[:3]}")
    page.locator("#ex-bib").uncheck()
    page.wait_for_timeout(300)
    if page.locator("#ex-count").inner_text().startswith(f"{want:,} place"):
        out.append(f"explore @{width}: unticking Bib Gourmand didn't bring the whole guide back")
    return out


WIDER_PROBE = "casa bonita"   # a famous place no guide lists (Lakewood): a first visit's search for it starts in Green Chile
WIDER_FEW = "santiagos"       # one hand-checked Santiago's on the Green Chile list, dozens of the chain statewide


def wider_probe_problems():
    """The probe must be a real listing that the opening guide (Green Chile: hand-checked + the green chile tag) doesn't list."""
    C = json.load(open(os.path.join(DOCS, "data", "core.json")))["cols"]
    hits = [i for i in range(len(C["id"])) if norm(C["n"][i]) == f" {WIDER_PROBE} " and C["v"][i] != 1]
    if not hits:
        return [f"explore: the probe {WIDER_PROBE!r} is no longer in the data; pick another famous place that no guide lists"]
    if any(C["hc"][i] == 1 and (C["g"][i] or 0) & 1 for i in hits):
        return [f"explore: {WIDER_PROBE!r} is now on the Green Chile list; pick another famous place that no guide lists"]
    return []


CSP_PROBE = """window.__csp = []; document.addEventListener("securitypolicyviolation",
  e => window.__csp.push(e.violatedDirective + " " + (e.blockedURI || "inline") + " @" + (e.sourceFile || "") + ":" + e.lineNumber));"""


def browser_checks(problems):
    from playwright.sync_api import sync_playwright
    base = serve()
    paths = [rel(f) for f in doc_files()]
    urls = [base + BASE + "/" + ("" if p == "index.html" else p.removesuffix("index.html")) for p in paths]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        for width in (375, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            ctx.add_init_script(CSP_PROBE)
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for url in urls:
                errors.clear()
                page.goto(url, wait_until="networkidle")
                where = f"{urllib.parse.urlparse(url).path} @{width}"
                over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    problems.append(f"{where}: scrolls sideways by {over}px")
                if page.locator("h1").count() != 1:
                    problems.append(f"{where}: {page.locator('h1').count()} <h1>")
                problems += [f"{where}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
                if width == 1280:   # links are the same at both widths
                    refs = page.evaluate("""[...document.querySelectorAll('a[href],img[src],link[href],script[src]')]
                        .map(e => e.getAttribute('href') || e.getAttribute('src'))""")
                    for ref in refs:
                        full = urllib.parse.urljoin(url, ref)
                        p = urllib.parse.urlparse(full)
                        if p.scheme in ("mailto", "tel", "data"):
                            continue
                        if p.netloc in (urllib.parse.urlparse(base).netloc, DOMAIN) and not local_exists(p.path):
                            problems.append(f"{where}: broken link {ref}")
                        if p.fragment and p.netloc == urllib.parse.urlparse(base).netloc and p.path == urllib.parse.urlparse(url).path:
                            if not page.evaluate("(id) => !!document.getElementById(id)", urllib.parse.unquote(p.fragment)):
                                problems.append(f"{where}: link to missing #{p.fragment}")
                    imgs = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                    problems += [f"{where}: image didn't load {s}" for s in imgs]
                problems += [f"{where}: console error: {e}" for e in errors]
            # ------------------------------------------------ the web app
            errors.clear()
            ex = base + BASE + "/explore/"
            page.goto(base + BASE + "/", wait_until="networkidle")             # a page before it, so Back has somewhere to leave to
            page.goto(ex + "#g=greenchile", wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=20000)
            search = page.locator('#ex-q').first
            search.fill("slopper")
            page.wait_for_timeout(500)
            want, got = expected_slopper_hits(), page.locator(".ex-row").count()
            if got != want:
                problems.append(f"explore @{width}: 'slopper' listed {got} green chile places, expected the {want} that serve one")
            search.fill("pueblo slopper")
            page.wait_for_timeout(500)
            if not page.locator(".ex-row").count():
                problems.append(f"explore @{width}: search 'pueblo slopper' found nothing")
            else:
                page.locator(".ex-row").first.click()
                page.wait_for_timeout(700)
                panel = page.locator("#ex-panel")
                if not panel.is_visible() or not panel.locator("a", has_text="Directions").count():
                    problems.append(f"explore @{width}: opening a place showed no details")
                else:
                    if width == 375:
                        modal = page.evaluate("""[document.querySelector('#ex-panel').getAttribute('role'),
                            document.querySelector('#ex-panel').getAttribute('aria-modal'), document.querySelector('#ex-app').inert,
                            document.querySelector('footer').inert]""")
                        if modal != ["dialog", "true", True, True]:
                            problems.append(f"explore @{width}: the open place sheet isn't a modal dialog with the page behind it inert: {modal}")
                    page.locator("#ex-save").click()
                    keys = page.evaluate("Object.keys(localStorage)")
                    bad = [k for k in keys if not k.startswith(STORAGE_PREFIX)]
                    if bad or not keys:
                        problems.append(f"explore @{width}: localStorage keys {keys} (want all to start {STORAGE_PREFIX!r})")
                    page.locator("#ex-save").click()
                    page.go_back()
                    page.wait_for_timeout(600)
                    if not page.url.startswith(ex) or panel.is_visible():
                        problems.append(f"explore @{width}: Back with a place open didn't just close it (now at {page.url}, panel visible: {panel.is_visible()})")
                    elif width == 375 and page.evaluate("document.querySelector('#ex-app').inert"):
                        problems.append(f"explore @{width}: the page stayed inert after the sheet closed")
            # ---- the web-app bugs found in sibling sites (addendum 2, 2026-10-12)
            # phones: the search box and the selects are 16px or more, or iOS Safari zooms the page when one gets focus
            if width == 375:
                small = page.evaluate("""[...document.querySelectorAll('#ex-q, .ex-controls select')].map(e => [e.id, parseFloat(getComputedStyle(e).fontSize)]).filter(x => !(x[1] >= 16))""")
                if small:
                    problems.append(f"explore @{width}: inputs under 16px make iOS Safari zoom on focus: {small}")
            # the search box's placeholder isn't cut off (California's read "…zip or d" at 375px): with its own words as the value,
            # the box doesn't scroll (a search box also keeps room for its clear button, so this leaves a margin); 16px or more
            ph = page.evaluate("""(() => { const i = document.querySelector('#ex-q'), v = i.value; i.value = i.placeholder;
                const r = [i.placeholder, i.scrollWidth, i.clientWidth, parseFloat(getComputedStyle(i, '::placeholder').fontSize)]; i.value = v; return r; })()""")
            if not ph[0] or ph[1] > ph[2] or ph[3] < 16:
                problems.append(f"explore @{width}: the search placeholder {ph[0]!r} is cut off or small (scrollWidth {ph[1]} > clientWidth {ph[2]}, {ph[3]}px)")
            # the open place is a labelled modal dialog at every width (on wide screens the side sheet covers Near me and List/Map):
            # the page behind is inert and focus is inside; Back closes it, Forward reopens it with the search kept, Escape closes it and
            # returns focus to its row, and a press outside it closes it
            page.goto(ex + "#g=greenchile", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            search.fill("pueblo")
            page.wait_for_timeout(500)
            page.locator(".ex-row").first.click()
            page.wait_for_timeout(600)
            dlg = page.evaluate("""(() => { const p = document.querySelector('#ex-panel'), l = document.getElementById(p.getAttribute('aria-labelledby') || '');
                return [p.getAttribute('role'), p.getAttribute('aria-modal'), !!(l && p.contains(l) && l.textContent.trim()),
                        document.querySelector('#ex-app').inert, p.contains(document.activeElement)]; })()""")
            if dlg != ["dialog", "true", True, True, True]:
                problems.append(f"explore @{width}: the open place isn't a labelled modal dialog (role, aria-modal, label, page inert, focus inside): {dlg}")
            page.go_back()
            page.wait_for_timeout(500)
            page.go_forward()
            page.wait_for_timeout(700)
            if not page.locator("#ex-panel").is_visible() or page.input_value("#ex-q") != "pueblo":
                problems.append(f"explore @{width}: Forward after Back didn't reopen the place with the search kept ({page.url})")
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            if page.locator("#ex-panel").is_visible() or "ex-row" not in (page.evaluate("document.activeElement && document.activeElement.className") or ""):
                problems.append(f"explore @{width}: Escape didn't close the place and put focus back on its row")
            page.locator(".ex-row").first.click()
            page.wait_for_timeout(500)
            page.mouse.click(5, 40)
            page.wait_for_timeout(500)
            if page.locator("#ex-panel").is_visible():
                problems.append(f"explore @{width}: a press outside the open place (on the inert page) didn't close it")
            # ---- a search inside a guide that the rest of the state answers (ME-V08 / WI-V-03): a first visit opens on Green Chile, where
            # "casa bonita" finds nothing, so the page offers "Search all restaurants (N matches)", and one press lists it, N places,
            # with the same words and focus on the first result. Then a search that finds a few in the guide offers the same.
            problems += [f"{p} @{width}" for p in wider_probe_problems()]
            wider = page.get_by_role("button", name=re.compile(r"^Search all restaurants \(\d[\d,]* match(?:es)?\)$"))
            page.evaluate("localStorage.clear()")
            page.goto(ex, wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            opening = page.evaluate("new URLSearchParams(location.hash.slice(1)).get('g')")
            search.fill(WIDER_PROBE)
            page.wait_for_timeout(500)
            if opening != "greenchile":
                problems.append(f"explore @{width}: a first visit opened on {opening!r}, not Green Chile")
            elif page.locator(".ex-row").count():
                problems.append(f"explore @{width}: {WIDER_PROBE!r} is listed in Green Chile, so it can't test the way out of an empty guide search")
            elif wider.count() != 1 or not wider.is_visible():
                problems.append(f"explore @{width}: {WIDER_PROBE!r} finds nothing in Green Chile and offers no 'Search all restaurants (N matches)' button "
                                f"(the page says {page.locator('#ex-list').inner_text()[:80]!r})")
            else:
                promised = int(re.search(r"\((\d[\d,]*)", wider.inner_text()).group(1).replace(",", ""))
                wider.click()
                page.wait_for_timeout(500)
                h = page.evaluate("Object.fromEntries(new URLSearchParams(location.hash.slice(1)))")
                names = page.locator(".ex-row .ex-main > b").all_inner_texts()
                listed = int(re.match(r"[\d,]+", page.locator("#ex-count").inner_text()).group(0).replace(",", ""))
                focus_first = page.evaluate("document.activeElement === document.querySelector('.ex-row')")
                if h.get("g") != "all" or h.get("q") != WIDER_PROBE or norm(names[0] if names else "") != f" {WIDER_PROBE} " or listed != promised or not focus_first:
                    problems.append(f"explore @{width}: 'Search all restaurants' didn't list {WIDER_PROBE!r} first in All restaurants with the same words "
                                    f"(hash {h}, first rows {names[:3]}, {listed} listed vs {promised} promised, focus on the first row: {focus_first})")
                if wider.count():
                    problems.append(f"explore @{width}: the 'Search all restaurants' button is still there in All restaurants")
            page.goto(ex + "#g=greenchile&q=" + urllib.parse.quote(WIDER_FEW), wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(700)
            few = page.locator(".ex-row").count()
            if not 0 < few < 5:
                problems.append(f"explore @{width}: {WIDER_FEW!r} lists {few} in Green Chile; pick a search that finds one to four there")
            elif wider.count() != 1:
                problems.append(f"explore @{width}: {WIDER_FEW!r} finds only {few} in Green Chile and offers no 'Search all restaurants' button")
            else:
                promised = int(re.search(r"\((\d[\d,]*)", wider.inner_text()).group(1).replace(",", ""))
                wider.click()
                page.wait_for_timeout(500)
                listed = int(re.match(r"[\d,]+", page.locator("#ex-count").inner_text()).group(0).replace(",", ""))
                if promised <= few or listed != promised:
                    problems.append(f"explore @{width}: {WIDER_FEW!r}: the button promised {promised} matches (the guide had {few}) and All restaurants lists {listed}")
            # bad values under this site's keys (any page on the shared github.io origin can write them) don't stop the app
            for key, bad in (("saved", '{"x":1}'), ("saved", "not json"), ("saved", "[null, 5, {}]"), ("guide", '{"x":1}'), ("guide", '"__proto__"')):
                errors.clear()
                page.evaluate("([k, v]) => localStorage.setItem(k, v)", [STORAGE_PREFIX + key, bad])
                page.goto(ex, wait_until="networkidle")
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(500)
                if not page.locator(".ex-row").count() or errors:
                    problems.append(f"explore @{width}: {STORAGE_PREFIX}{key} = {bad} stopped the app ({errors[:1]})")
                page.evaluate("(k) => localStorage.removeItem(k)", STORAGE_PREFIX + key)
            search.fill("🍕")
            page.wait_for_timeout(400)
            if page.locator(".ex-row").count():
                problems.append(f"explore @{width}: an emoji search listed places")
            for hostile in ("#g=constructor", "#g=__proto__&sort=toString"):
                errors.clear()
                page.goto(ex + hostile, wait_until="networkidle")
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(500)
                if not page.locator(".ex-row").count() or errors:
                    problems.append(f"explore @{width}: {hostile} broke the list ({errors[:1]})")
            # ---- location outside Colorado (App Review is usually in California): say so, and keep the map on the state
            ctx.grant_permissions(["geolocation"], origin=base)
            ctx.set_geolocation({"latitude": 37.7749, "longitude": -122.4194})
            page.goto(ex + "#g=greenchile", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            page.locator('.ex-view button[data-v="map"]').click()
            page.wait_for_timeout(500)
            page.locator("#ex-locate").click()
            page.wait_for_timeout(1200)
            msg = page.locator("#ex-locmsg").inner_text()
            if "outside Colorado" not in msg:
                problems.append(f"explore @{width}: Near me from San Francisco doesn't say it's outside Colorado ({msg!r})")
            white = page.evaluate("""(() => { const c = document.querySelector('#ex-map'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] === 255 && d[i + 1] === 255 && d[i + 2] === 255) n++; return n; })()""")
            if white < 2000:
                problems.append(f"explore @{width}: Near me from outside Colorado left the map off the state ({white} state-fill pixels)")
            # a map zoomed and dragged away from every dot says so, instead of "tap a dot"
            for _ in range(6):
                page.locator("#ex-zin").click()
            box = page.locator("#ex-map").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + 5, box["y"] + 5, steps=4)
            page.mouse.up()
            page.wait_for_timeout(300)
            hint = page.locator("#ex-maphint").inner_text()
            if "tap a dot" in hint and not page.evaluate("""(() => { const c = document.querySelector('#ex-map'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                    for (let i = 0; i < d.length; i += 4) if (d[i] < 10 && d[i + 1] < 60 && d[i + 2] > 90 && d[i + 2] < 120 || d[i] > 250 && d[i + 1] > 200 && d[i + 1] < 225 && d[i + 2] < 20) return true; return false; })()"""):
                problems.append(f"explore @{width}: the map shows no dots but its hint says {hint!r}")
            ctx.clear_permissions()
            # no location (denied): the list doesn't claim to be sorted by distance
            page.goto(ex + "#g=brewpubs", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            page.select_option("#ex-sort", "nearest")
            page.wait_for_timeout(1200)
            if "Nearest" in page.locator("#ex-count").inner_text():
                problems.append(f"explore @{width}: says 'Nearest' after location was denied ({page.locator('#ex-count').inner_text()!r})")
            # ---- a location timeout isn't "location is off"
            page.add_init_script("""navigator.geolocation.getCurrentPosition = (ok, fail) => setTimeout(() => fail({ code: 3, message: 'Timeout expired' }), 50);""")
            page.goto(ex + "#g=greenchile", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            page.locator("#ex-locate").click()
            page.wait_for_timeout(500)
            if "Location is off" in page.locator("#ex-locmsg").inner_text():
                problems.append(f"explore @{width}: a location timeout reads as 'Location is off' ({page.locator('#ex-locmsg').inner_text()!r})")
            page.select_option("#ex-sort", "nearest")   # asking for Nearest asks for a location, which times out too
            page.wait_for_timeout(500)
            if "Nearest" in page.locator("#ex-count").inner_text():
                problems.append(f"explore @{width}: says 'Nearest' after a location timeout ({page.locator('#ex-count').inner_text()!r})")
            problems += bib_problems(page, ex, width)
            # ---- aria-label only where it counts (a span, div, p or canvas needs a role for it to be read)
            page.goto(ex + "#g=oldest", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".ex-row", timeout=20000)
            stray = page.evaluate("""[...document.querySelectorAll('[aria-label]')].filter(e => ['SPAN', 'DIV', 'P', 'CANVAS', 'B', 'SMALL'].includes(e.tagName)
                && !e.getAttribute('role')).map(e => e.tagName + '.' + e.className + ' ' + e.getAttribute('aria-label')).slice(0, 3)""")
            if stray:
                problems.append(f"explore @{width}: aria-label on elements with no role (screen readers skip it): {stray}")
            page.goto(ex + "#g=honors&sort=nearest", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=20000)
            if "Nearest" in page.locator("#ex-count").inner_text():
                problems.append(f"explore @{width}: says 'Nearest' with no location")
            problems += [f"explore @{width}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
            problems += [f"explore @{width}: console error: {e}" for e in errors]
            # Near me asks for a fresh fix on every tap (one from earlier can be a drive away) and stays there to ask again
            fresh = ctx.new_page()
            fresh.add_init_script("""window.__geo = []; navigator.geolocation.getCurrentPosition = (ok, fail, o) => { window.__geo.push(o || {});
                setTimeout(() => ok({ coords: { latitude: 39.74, longitude: -104.99 } }), 20); };""")
            fresh.goto(ex + "#g=greenchile", wait_until="networkidle")
            fresh.wait_for_selector(".ex-row", timeout=20000)
            fresh.locator("#ex-locate").click()
            fresh.wait_for_timeout(400)
            if fresh.locator("#ex-locate").is_visible():
                fresh.locator("#ex-locate").click()
                fresh.wait_for_timeout(400)
            geo = fresh.evaluate("window.__geo")
            if len(geo) < 2 or any((o.get("maximumAge") or 0) > 60000 for o in geo):
                problems.append(f"explore @{width}: Near me doesn't ask for a fresh location on every tap (requests: {geo})")
            fresh.close()
            ctx.close()
        browser.close()
    return len(urls)


def app_data_checks(problems):
    """docs/data/app/, the app's data updates (scripts/publish_app_data.py, OTA-DATA.md): every manifest entry's hash, size and
    row count match its file, the head file's date matches, and no old copy lingers."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from publish_app_data import check_app_data, app_data_dir
    found, notes = check_app_data(DOCS, app_data_dir())
    problems.extend("app data: " + x for x in found)
    for x in notes:
        print("  note: app data:", x)


def main():
    problems, n = static_checks()
    app_data_checks(problems)
    if "--static" in sys.argv:
        print(f"{n} pages, static checks")
    else:
        n = browser_checks(problems)
        print(f"{n} pages × 2 widths + the web app")
    for p in problems:
        print("  ✗", p)
    print("OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
